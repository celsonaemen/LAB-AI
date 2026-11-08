import os
import pytest
from pathlib import Path


@pytest.fixture
def store(monkeypatch):
    dsn = os.getenv('AEGIS_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('AEGIS_TEST_DATABASE_URL required for native PostgreSQL tests')
    monkeypatch.setenv('DATABASE_URL', dsn)
    monkeypatch.setenv('AEGIS_LLM_PROVIDER', 'deterministic')
    from app.migrate import migrate
    migrate(Path(__file__).resolve().parents[3] / 'infrastructure/database/migrations')
    from app.executions import repository
    return repository


def test_order_approval_resume_and_terminal_guard(store):
    from app.executions.models import CreateExecution, AGENTS
    from app.executions.worker import execute
    snapshot = store.create(CreateExecution(task='review', workflow='portfolio-review', requireApproval=True))
    claimed = store.claim(snapshot['id'])
    execute(claimed)
    paused = store.get(snapshot['id'])
    assert paused['state'] == 'AwaitingApproval'
    assert [a['state'] for a in paused['agents']] == ['Completed'] * 3 + ['Pending']
    store.transition(snapshot['id'], 'approve')
    execute(store.claim(snapshot['id']))
    done = store.get(snapshot['id'])
    assert done['state'] == 'Completed'
    events = store.events(snapshot['id'], 0)
    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1))
    assert [e['agentId'] for e in events if e['type'] == 'AgentStarted'] == list(AGENTS)
    assert all(a['durationMs'] >= 0 for a in done['agents'])
    with pytest.raises(store.Conflict):
        store.transition(snapshot['id'], 'cancel')


def test_cancel_during_tool_cannot_complete(store, monkeypatch):
    from app.executions.models import CreateExecution
    from app.executions import worker
    snapshot = store.create(CreateExecution(task='review', workflow='portfolio-review'))
    original = worker.dispatch
    def cancelling(*args):
        result = original(*args)
        store.transition(snapshot['id'], 'cancel')
        return result
    monkeypatch.setattr(worker, 'dispatch', cancelling)
    worker.execute(store.claim(snapshot['id']))
    assert store.get(snapshot['id'])['state'] == 'Cancelled'
    assert not any(e['type'] == 'ExecutionCompleted' for e in store.events(snapshot['id'], 0))


def test_tool_failure_is_sanitized_and_durable(store, monkeypatch):
    from app.executions.models import CreateExecution
    from app.executions import worker
    snapshot = store.create(CreateExecution(task='review', workflow='portfolio-review'))
    def fail(*args):
        raise ValueError('secret password')
    monkeypatch.setattr(worker, 'dispatch', fail)
    worker.execute(store.claim(snapshot['id']))
    result = store.get(snapshot['id'])
    assert result['state'] == 'Failed'
    assert 'secret' not in str(result)
    assert any(e['type'] == 'ToolFailed' for e in store.events(snapshot['id'], 0))


def test_report_provider_failure_has_no_fallback(store, monkeypatch):
    from app.executions.models import CreateExecution
    from app.executions import worker
    snapshot = store.create(CreateExecution(task='review', workflow='portfolio-review'))
    def fail(*args):
        raise TimeoutError('private model endpoint')
    monkeypatch.setattr(worker, 'generate', fail)
    worker.execute(store.claim(snapshot['id']))
    result = store.get(snapshot['id'])
    assert result['state'] == 'Failed'
    assert result['result'] is None
    assert result['agents'][3]['state'] == 'Failed'
    assert result['agents'][3]['error'] == 'Operation timed out'
    assert any(e['type'] == 'ProviderFailed' for e in store.events(snapshot['id'], 0))


def test_recovery_keeps_pending_and_prevents_live_second_owner(store):
    from app.executions.models import CreateExecution
    from app.executions.worker import WORKER_LOCK
    from app.rag.store import _connect
    pending = store.create(CreateExecution(task='pending recovery', workflow='portfolio-review'))
    running = store.create(CreateExecution(task='running recovery', workflow='portfolio-review'))
    store.claim(running['id'])
    with _connect() as owner, _connect() as second:
        assert owner.execute('SELECT pg_try_advisory_lock(%s) AS locked', (WORKER_LOCK,)).fetchone()['locked']
        assert not second.execute('SELECT pg_try_advisory_lock(%s) AS locked', (WORKER_LOCK,)).fetchone()['locked']
        store.recover_interrupted()
    assert store.get(pending['id'])['state'] == 'Pending'
    assert store.get(running['id'])['state'] == 'Failed'
    assert any(s['id'] == running['id'] for s in store.history(100, 0))
    all_events = store.events(running['id'], 0)
    assert store.events(running['id'], all_events[-2]['sequence']) == all_events[-1:]
    store.transition(pending['id'], 'cancel')
