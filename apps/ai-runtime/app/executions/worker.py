import logging
import os
import queue
import threading
import time
from copy import deepcopy
from app.executions import repository as repo
from app.executions.models import AGENTS
from app.executions.tools import dispatch
from app.executions.providers import generate
from app.executions.tool_calling import retrieve
from app.executions.guardrails import check_request, GuardrailViolation
from app.rag.store import _connect

logger = logging.getLogger(__name__)
WORKER_LOCK = 714210030
_operation_slot = threading.BoundedSemaphore(1)


class Cancelled(Exception):
    pass


def bounded(operation, timeout=45):
    # At most one outstanding read-only operation, even after a timeout. A stuck
    # embedding/provider call cannot accumulate unbounded threads across runs.
    if not _operation_slot.acquire(blocking=False):
        raise RuntimeError('Previous operation has not stopped')
    output = queue.Queue(maxsize=1)
    def invoke():
        try:
            output.put((True, operation()))
        except Exception as error:
            output.put((False, error))
        finally:
            _operation_slot.release()
    threading.Thread(target=invoke, daemon=True, name='execution-operation').start()
    try:
        ok, value = output.get(timeout=timeout)
    except queue.Empty as error:
        raise TimeoutError('Operation timed out') from error
    if not ok:
        raise value
    return value


def update(identifier, kind, agent_id=None, data=None, modify=None):
    def change(connection, row):
        if row['snapshot']['state'] != 'Running':
            raise Cancelled()
        if modify:
            modify(row['snapshot'])
        repo.event(connection, row, kind, agent_id, data)
    return repo.mutate(identifier, change)


def execute(row):
    identifier = str(row['id'])
    snapshot = row['snapshot']
    request = row['request']
    active = None
    tool = None
    provider_active = False
    results = {a['id']: a['result'] for a in snapshot['agents'] if a['state'] == 'Completed'}
    try:
        check_request(snapshot['task'])
        for index, active in enumerate(AGENTS):
            if active in results:
                continue
            if active == 'report-agent' and snapshot['requireApproval'] and not request.get('approved'):
                update(identifier, 'ApprovalRequested', modify=lambda s: s.update(state='AwaitingApproval'))
                return
            def start(s):
                s['agents'][index].update(state='Running', startedAt=repo.now())
            update(identifier, 'AgentStarted', active, modify=start)
            if active == 'report-agent':
                provider_active = True
                update(identifier, 'ProviderStarted', active, {'provider': snapshot['provider']})
                started = time.monotonic()
                result = bounded(lambda: generate(snapshot['provider'], snapshot['task'], deepcopy(results)))
                update(identifier, 'ProviderCompleted', active, {'provider': snapshot['provider'], 'result': result, 'durationMs': int((time.monotonic()-started)*1000)})
                provider_active = False
            else:
                if active == 'data-agent':
                    operations = []
                    if snapshot['workflow'] == 'portfolio-review':
                        operations.append(('portfolio.read', {'portfolioId': snapshot['portfolioId']}))
                    operations.append(('knowledge.search', {'query': snapshot['task'], 'metadataFilter': request['metadataFilter'], 'minScore': .35}))
                else:
                    operations = [('risk.calculate' if active == 'risk-agent' else 'metrics.calculate', {'data': results['data-agent']})]
                result = None
                for tool, arguments in operations:
                    update(identifier, 'ToolStarted', active, {'toolId': tool, 'arguments': arguments})
                    started = time.monotonic()
                    def check_cancel():
                        if repo.get(identifier)['state'] != 'Running':
                            raise Cancelled()
                    check_cancel()
                    if tool == 'knowledge.search':
                        output = bounded(lambda: retrieve(snapshot['provider'], snapshot['task'], request['metadataFilter'],
                            lambda kind, data: update(identifier, kind, active, data), check_cancel))
                    else:
                        output = bounded(lambda: dispatch(active, tool, arguments))
                    update(identifier, 'ToolCompleted', active, {'toolId': tool, 'result': output, 'durationMs': int((time.monotonic()-started)*1000)})
                    if result is not None and tool == 'knowledge.search':
                        result.update(context=output['context'], results=output['results'])
                    else:
                        result = output
                    tool = None
            results[active] = result
            def complete(s):
                agent = s['agents'][index]
                timestamp = repo.now()
                agent.update(state='Completed', result=result, finishedAt=timestamp,
                             durationMs=repo.duration(agent['startedAt'], timestamp))
            update(identifier, 'AgentCompleted', active, {'result': result}, complete)
        def finish(s):
            s['result'] = results['report-agent']
            repo.finish(s, 'Completed')
        update(identifier, 'ExecutionCompleted', data={'result': results['report-agent']}, modify=finish)
    except Cancelled:
        return
    except Exception as error:
        # Never expose raw database/provider errors, URLs or credentials.
        message = 'Operation timed out' if isinstance(error, TimeoutError) else 'Agent operation failed; check runtime configuration and dependencies'
        logger.warning('Execution operation failed: %s', type(error).__name__)
        try:
            if isinstance(error, GuardrailViolation):
                update(identifier, 'GuardrailBlocked', active, {'code': error.code})
            if tool:
                update(identifier, 'ToolFailed', active, {'toolId': tool, 'error': message, 'durationMs': int((time.monotonic()-started)*1000)})
            if provider_active:
                update(identifier, 'ProviderFailed', active, {'provider': snapshot['provider'], 'error': message, 'durationMs': int((time.monotonic()-started)*1000)})
            if active:
                update(identifier, 'AgentFailed', active, {'error': message})
            update(identifier, 'ExecutionFailed', active, {'error': message}, lambda s: repo.finish(s, 'Failed', message))
        except Cancelled:
            pass


def run(stop):
    while not stop.is_set():
        try:
            # The dedicated session owns the singleton lock throughout recovery
            # and processing. Another live runtime therefore cannot fail its runs.
            with _connect() as lock_connection:
                lock_connection.autocommit = True
                locked = lock_connection.execute('SELECT pg_try_advisory_lock(%s) AS locked', (WORKER_LOCK,)).fetchone()['locked']
                if not locked:
                    stop.wait(1)
                    continue
                repo.recover_interrupted()
                while not stop.is_set():
                    lock_connection.execute('SELECT 1')
                    row = repo.claim()
                    if row:
                        execute(row)
                    else:
                        stop.wait(.25)
        except Exception as error:
            logger.warning('Execution worker unavailable: %s', type(error).__name__)
            stop.wait(1)


def start_worker():
    stop = threading.Event()
    if os.getenv('DATABASE_URL') or os.getenv('PGHOST'):
        thread = threading.Thread(target=run, args=(stop,), daemon=True, name='execution-worker')
        thread.start()
        return stop, thread
    return stop, None
