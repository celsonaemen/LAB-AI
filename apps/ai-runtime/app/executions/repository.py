import json
import os
from datetime import datetime, timezone
from uuid import uuid4
import psycopg
from app.rag.store import _connect
from app.rag.store import KnowledgeUnavailable
from app.executions.models import AGENTS, TERMINAL
from app.executions.guardrails import redact


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


def database_ready():
    try:
        with _connect() as connection:
            return connection.execute("SELECT to_regclass('knowledge.agent_executions') IS NOT NULL AND "
                                      "to_regclass('knowledge.agent_execution_events') IS NOT NULL AND EXISTS "
                                      "(SELECT 1 FROM knowledge.schema_migrations WHERE version='V003__agent_executions.sql') AS ready").fetchone()['ready']
    except (psycopg.Error, KnowledgeUnavailable):
        return False


def now():
    return datetime.now(timezone.utc).isoformat()


def duration(start, end):
    return max(0, int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() * 1000)) if start else 0


def event(connection, row, kind, agent=None, data=None):
    value = {'sequence': row['next_sequence'], 'executionId': str(row['id']), 'type': kind,
             'agentId': agent, 'timestamp': now(), 'data': redact(data or {})}
    connection.execute('INSERT INTO knowledge.agent_execution_events(execution_id,sequence,event) VALUES(%s,%s,%s::jsonb)',
                       (row['id'], row['next_sequence'], json.dumps(value)))
    row['next_sequence'] += 1


def save(connection, row):
    row['snapshot'] = redact(row['snapshot'])
    connection.execute('UPDATE knowledge.agent_executions SET state=%s,snapshot=%s::jsonb,next_sequence=%s WHERE id=%s',
                       (row['snapshot']['state'], json.dumps(row['snapshot']), row['next_sequence'], row['id']))


def create(request):
    provider = os.getenv('AEGIS_LLM_PROVIDER', 'deterministic')
    if provider not in ('deterministic', 'ollama'):
        raise ValueError('Unsupported report provider configuration')
    if provider == 'ollama' and not os.getenv('OLLAMA_MODEL'):
        raise ValueError('Ollama model is not configured')
    identifier = str(uuid4())
    snapshot = {'id': identifier, 'task': request.task, 'workflow': request.workflow,
                'portfolioId': request.portfolioId, 'state': 'Pending', 'createdAt': now(),
                'startedAt': None, 'finishedAt': None, 'durationMs': None, 'result': None, 'error': None,
                'provider': provider, 'requireApproval': request.requireApproval,
                'agents': [{'id': agent, 'state': 'Pending', 'startedAt': None, 'finishedAt': None,
                            'durationMs': None, 'result': None, 'error': None} for agent in AGENTS]}
    with _connect() as connection:
        connection.execute('INSERT INTO knowledge.agent_executions(id,state,snapshot,request) VALUES(%s,%s,%s::jsonb,%s::jsonb)',
                           (identifier, 'Pending', json.dumps(redact(snapshot)), json.dumps(redact(request.model_dump()))))
        row = {'id': identifier, 'snapshot': snapshot, 'next_sequence': 1}
        event(connection, row, 'ExecutionCreated')
        save(connection, row)
    return redact(snapshot)


def get(identifier):
    with _connect() as connection:
        row = connection.execute('SELECT snapshot FROM knowledge.agent_executions WHERE id=%s', (identifier,)).fetchone()
    if not row:
        raise NotFound()
    return redact(row['snapshot'])


def history(limit, offset):
    with _connect() as connection:
        return [redact(r['snapshot']) for r in connection.execute('SELECT snapshot FROM knowledge.agent_executions ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s', (limit, offset)).fetchall()]


def events(identifier, after):
    get(identifier)
    with _connect() as connection:
        return [redact(r['event']) for r in connection.execute('SELECT event FROM knowledge.agent_execution_events WHERE execution_id=%s AND sequence>%s ORDER BY sequence', (identifier, after)).fetchall()]


def mutate(identifier, change):
    with _connect() as connection:
        row = connection.execute('SELECT * FROM knowledge.agent_executions WHERE id=%s FOR UPDATE', (identifier,)).fetchone()
        if not row:
            raise NotFound()
        change(connection, row)
        save(connection, row)
        return row['snapshot']


def finish(snapshot, state, error=None):
    timestamp = now()
    snapshot.update(state=state, finishedAt=timestamp, durationMs=duration(snapshot['startedAt'], timestamp), error=error)
    for agent in snapshot['agents']:
        if agent['state'] in ('Running', 'Pending'):
            agent.update(state=state if state == 'Cancelled' or agent['state'] == 'Running' else 'Skipped',
                         finishedAt=timestamp, durationMs=duration(agent['startedAt'], timestamp), error=error)


def transition(identifier, action):
    def change(connection, row):
        snapshot = row['snapshot']
        if action == 'cancel' and snapshot['state'] not in TERMINAL:
            finish(snapshot, 'Cancelled')
            event(connection, row, 'ExecutionCancelled')
        elif action == 'approve' and snapshot['state'] == 'AwaitingApproval':
            snapshot['state'] = 'Pending'
            # Approval is persisted separately from the original immutable request.
            connection.execute("UPDATE knowledge.agent_executions SET request=jsonb_set(request,'{approved}','true'::jsonb) WHERE id=%s", (identifier,))
            event(connection, row, 'ExecutionApproved')
        else:
            raise Conflict('Invalid execution transition')
    return mutate(identifier, change)


def claim(identifier=None):
    with _connect() as connection:
        row = connection.execute("SELECT * FROM knowledge.agent_executions WHERE state='Pending' " +
                                 ('AND id=%s ' if identifier else '') + 'ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1',
                                 (identifier,) if identifier else ()).fetchone()
        if row is None:
            return None
        row['snapshot']['state'] = 'Running'
        row['snapshot']['startedAt'] = row['snapshot']['startedAt'] or now()
        event(connection, row, 'ExecutionStarted')
        save(connection, row)
        return row


def recover_interrupted():
    # Caller MUST own the session-level worker advisory lock.
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM knowledge.agent_executions WHERE state='Running' FOR UPDATE").fetchall()
        for row in rows:
            finish(row['snapshot'], 'Failed', 'Execution interrupted by runtime restart')
            event(connection, row, 'ExecutionFailed', data={'error': row['snapshot']['error']})
            save(connection, row)
