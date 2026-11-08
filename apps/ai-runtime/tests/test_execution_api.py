from fastapi.testclient import TestClient
from app.main import app


def test_health_reports_configured_provider(monkeypatch):
    monkeypatch.setenv('AEGIS_LLM_PROVIDER', 'ollama')
    assert TestClient(app).get('/health').json()['provider'] == 'ollama'


def test_execution_admission_validates_without_database():
    client = TestClient(app)
    assert client.post('/internal/v1/executions', json={'task': 'review', 'workflow': 'shell'}).status_code == 422
    assert client.get('/internal/v1/executions/not-a-uuid').status_code == 422
