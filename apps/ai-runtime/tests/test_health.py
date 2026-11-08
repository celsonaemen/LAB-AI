from fastapi.testclient import TestClient

from app.main import app


def test_health_identifies_the_service_and_demo_provider(monkeypatch):
    monkeypatch.setenv('AEGIS_LLM_PROVIDER', 'deterministic')
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-runtime",
        "provider": "deterministic",
    }


def test_readiness_returns_unavailable_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PGHOST", raising=False)
    assert TestClient(app).get("/health/ready").status_code == 503
