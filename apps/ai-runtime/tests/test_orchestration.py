import pytest
from pydantic import ValidationError


def test_tool_permission_and_argument_validation():
    from app.executions.tools import dispatch
    with pytest.raises(PermissionError):
        dispatch('report-agent', 'portfolio.read', {'portfolioId': 'balanced'})
    with pytest.raises(ValidationError):
        dispatch('data-agent', 'portfolio.read', {'portfolioId': 'unknown'})
    with pytest.raises(ValueError):
        dispatch('data-agent', 'shell', {})


def test_fictional_portfolio_calculations():
    from app.executions.tools import dispatch
    data = dispatch('data-agent', 'portfolio.read', {'portfolioId': 'concentrated'})
    risk = dispatch('risk-agent', 'risk.calculate', {'data': data})
    metrics = dispatch('analytics-agent', 'metrics.calculate', {'data': data})
    assert data['fictional'] is True
    assert risk['concentrationRisk'] == 'high'
    assert metrics['totalValue'] == 100000


def test_insufficient_evidence_survives_report():
    from app.executions.tools import dispatch
    from app.executions.providers import generate
    data = {'kind': 'documents', 'context': {'status': 'insufficient_evidence', 'text': 'Insufficient evidence', 'references': []}, 'results': []}
    risk = dispatch('risk-agent', 'risk.calculate', {'data': data})
    metrics = dispatch('analytics-agent', 'metrics.calculate', {'data': data})
    result = generate('deterministic', 'review', {'data-agent': data, 'risk-agent': risk, 'analytics-agent': metrics})
    assert result['evidenceStatus'] == 'insufficient_evidence'
    assert 'deterministic' in result['summary'].lower()


def test_ollama_timeout_is_visible(monkeypatch):
    from app.executions import providers
    monkeypatch.setenv('OLLAMA_MODEL', 'test-model')
    def timeout(*args, **kwargs):
        raise TimeoutError('sensitive endpoint')
    monkeypatch.setattr(providers, 'urlopen', timeout)
    with pytest.raises(RuntimeError, match='timed out'):
        providers.generate('ollama', 'review', {})


def test_public_admission_rejects_tools_and_blank_task():
    from app.executions.models import CreateExecution
    with pytest.raises(ValidationError):
        CreateExecution(task=' ', workflow='portfolio-review')
    with pytest.raises(ValidationError):
        CreateExecution(task='review', workflow='portfolio-review', tools=['shell'])


def test_calculation_schema_rejects_untrusted_invalid_data():
    from app.executions.tools import dispatch
    with pytest.raises(ValidationError):
        dispatch('risk-agent', 'risk.calculate', {'data': {'kind': 'portfolio', 'positions': [{'value': -1}]}})


def test_unknown_provider_rejected_before_persistence(monkeypatch):
    from app.executions.repository import create
    from app.executions.models import CreateExecution
    monkeypatch.setenv('AEGIS_LLM_PROVIDER', 'unknown')
    with pytest.raises(ValueError, match='Unsupported'):
        create(CreateExecution(task='review', workflow='portfolio-review'))


def test_bounded_read_timeout():
    import threading
    from app.executions.worker import bounded, _operation_slot
    release = threading.Event()
    try:
        with pytest.raises(TimeoutError):
            bounded(lambda: release.wait(1), timeout=.01)
        with pytest.raises(RuntimeError, match='not stopped'):
            bounded(lambda: None)
    finally:
        release.set()
        assert _operation_slot.acquire(timeout=2)
        _operation_slot.release()
