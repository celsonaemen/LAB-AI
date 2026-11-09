import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import ServiceAuthentication


def secured_app(monkeypatch):
    monkeypatch.setenv("AEGIS_SECURITY_ENABLED", "true")
    monkeypatch.setenv("AEGIS_ENVIRONMENT", "Homologation")
    monkeypatch.setenv("AEGIS_SERVICE_TOKEN", "s" * 40)
    app = FastAPI()
    app.add_middleware(ServiceAuthentication)
    app.get("/health")(lambda: {"status": "ok"})
    app.get("/internal")(lambda: {"status": "authorized"})
    return TestClient(app)


def test_internal_routes_require_exactly_one_service_token(monkeypatch):
    client = secured_app(monkeypatch)
    assert client.get("/internal").status_code == 401
    assert client.get("/internal", headers={"X-Aegis-Service-Token": "wrong"}).status_code == 401
    accepted = client.get("/internal", headers={"X-Aegis-Service-Token": "s" * 40})
    assert accepted.status_code == 200
    assert accepted.json() == {"status": "authorized"}


def test_liveness_does_not_require_gateway_token(monkeypatch):
    assert secured_app(monkeypatch).get("/health").status_code == 200


def test_non_development_runtime_fails_closed_when_authentication_is_disabled(monkeypatch):
    monkeypatch.setenv("AEGIS_SECURITY_ENABLED", "false")
    monkeypatch.setenv("AEGIS_ENVIRONMENT", "Homologation")
    with pytest.raises(RuntimeError, match="required outside Development"):
        ServiceAuthentication(lambda *_: None)
