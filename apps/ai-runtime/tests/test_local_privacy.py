"""Exercise outbound boundaries using local listeners, never external services."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.executions import providers
from app.main import app


@contextmanager
def local_server(status=200, location=None):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            self.send_response(status)
            if location:
                self.send_header('Location', location)
            self.end_headers()
            self.wfile.write(json.dumps({'done': True, 'message': {'role': 'assistant', 'content': 'local'}}).encode())

        do_GET = do_POST

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('operation', ['chat', 'report'])
@pytest.mark.parametrize('endpoint', [
    'https://external.example', 'http://169.254.169.254', 'http://10.0.0.1',
    'http://localhost.attacker.test', 'http://user:password@127.0.0.1',
    'file:///tmp/model', 'http://127.0.0.1/escape', 'http://127.0.0.1?token=secret',
])
def test_model_rejects_nonlocal_or_ambiguous_endpoint_before_transport(monkeypatch, endpoint, operation):
    monkeypatch.setenv('OLLAMA_MODEL', 'test-only')
    monkeypatch.setenv('OLLAMA_BASE_URL', endpoint)

    def transport_must_not_run(*_, **__):
        pytest.fail('Rejected endpoint reached the network transport')

    monkeypatch.setattr(providers, 'urlopen', transport_must_not_run)
    with pytest.raises(RuntimeError, match='loopback'):
        if operation == 'chat':
            providers.chat([{'role': 'user', 'content': 'sensitive'}], [])
        else:
            providers.generate('ollama', 'sensitive', {})


def test_local_model_bypasses_environment_proxy(monkeypatch):
    with local_server() as (proxy, proxy_received), local_server() as (model, model_received):
        monkeypatch.setenv('http_proxy', proxy)
        monkeypatch.setenv('HTTP_PROXY', proxy)
        monkeypatch.setenv('no_proxy', '')
        monkeypatch.setenv('NO_PROXY', '')
        monkeypatch.setenv('OLLAMA_MODEL', 'test-only')
        monkeypatch.setenv('OLLAMA_BASE_URL', model)
        result = providers.chat([{'role': 'user', 'content': 'private-test'}], [])
        assert result['content'] == 'local'
        assert b'private-test' in model_received[0]
        assert proxy_received == []


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_model_never_follows_redirects(monkeypatch, status):
    with local_server() as (sink, sink_received), local_server(status, sink) as (model, _):
        monkeypatch.setenv('OLLAMA_MODEL', 'test-only')
        monkeypatch.setenv('OLLAMA_BASE_URL', model)
        with pytest.raises(RuntimeError):
            providers.chat([{'role': 'user', 'content': 'private-test'}], [])
        assert sink_received == []


def test_invalid_request_does_not_echo_sensitive_values():
    response = TestClient(app).post('/internal/v1/knowledge/search', json={
        'query': 'private-customer-marker', 'unexpected': 'private-secret-marker',
    })
    assert response.status_code == 422
    assert 'private-customer-marker' not in response.text
    assert 'private-secret-marker' not in response.text


def test_embedding_loader_requires_local_cache(monkeypatch, tmp_path):
    import fastembed
    from app.rag import embeddings

    # The model constructor is the external download boundary. Actual model
    # dimensions/ranking are covered separately by opt-in integration tests.
    captured = {}
    sentinel = object()
    def construct(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(fastembed, 'TextEmbedding', construct)
    monkeypatch.setenv('EMBEDDING_CACHE_DIR', str(tmp_path))
    embeddings._model.cache_clear()
    try:
        assert embeddings._model() is sentinel
        assert captured['local_files_only'] is True
        assert captured['cache_dir'] == str(tmp_path)
    finally:
        embeddings._model.cache_clear()
