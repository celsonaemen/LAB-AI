import pytest


def catalog():
    return [{'id': 'search_knowledge', 'description': 'search', 'allowedAgents': ['data-agent'],
             'inputSchema': {'type': 'object', 'properties': {
                 'query': {'type': 'string'}, 'metadataFilter': {'type': 'object', 'additionalProperties': {'type': 'string'}}
             }, 'required': ['query'], 'additionalProperties': False}}]


def test_model_multiple_calls_receive_real_tool_results(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: catalog())
    hit = {'chunkId': 'c', 'documentId': 'd', 'title': 't', 'source': 's', 'score': .9, 'content': 'Evidence'}
    monkeypatch.setattr(tc, 'call_tool', lambda *a, **kw: {'model': 'm', 'results': [hit], 'context': {}})
    seen = []
    def fake_chat(messages, tools):
        seen.append(list(messages))
        return {'role': 'assistant', 'tool_calls': [{'function': {'name': 'search_knowledge', 'arguments': {'query': 'review'}}}]} if len(seen) < 3 else {'role': 'assistant', 'content': 'done'}
    monkeypatch.setattr(tc, 'chat', fake_chat)
    result = tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)
    assert [m['role'] for m in seen[1][-2:]] == ['assistant', 'tool']
    assert 'Evidence' in seen[1][-1]['content']
    assert len(result['results']) == 1


def test_round_limit_and_schema_extra_are_blocked(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: catalog())
    monkeypatch.setattr(tc, 'call_tool', lambda *a, **kw: {'results': [], 'context': {}})
    monkeypatch.setattr(tc, 'chat', lambda *a: {'role': 'assistant', 'tool_calls': [{'function': {'name': 'search_knowledge', 'arguments': {'query': 'review', 'approved': True}}}]})
    with pytest.raises(tc.GuardrailViolation, match='invalid_tool_arguments'):
        tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)
    monkeypatch.setattr(tc, 'chat', lambda *a: {'role': 'assistant', 'tool_calls': [{'function': {'name': 'search_knowledge', 'arguments': {'query': 'review'}}}]})
    with pytest.raises(tc.GuardrailViolation, match='tool_round_limit'):
        tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)


def test_provider_failure_never_falls_back(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: catalog())
    def fail(*args):
        raise RuntimeError('provider unavailable')
    monkeypatch.setattr(tc, 'chat', fail)
    with pytest.raises(RuntimeError, match='provider unavailable'):
        tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)


def test_unknown_report_reference_rejected(monkeypatch):
    from app.executions import providers
    import json
    monkeypatch.setenv('OLLAMA_MODEL', 'unit-test-only')
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return json.dumps({'done': True, 'message': {'content': 'Claim [S999]'}}).encode()
    monkeypatch.setattr(providers, 'urlopen', lambda *a, **kw: Response())
    with pytest.raises(ValueError, match='unsupported_citation'):
        providers.generate('ollama', 'review', {'data-agent': {'context': {'status': 'insufficient_evidence', 'references': []}}})


def test_model_no_calls_is_not_scripted_retrieval(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: [])
    monkeypatch.setattr(tc, 'chat', lambda *a, **kw: {'role': 'assistant', 'content': 'done'})
    with pytest.raises(tc.GuardrailViolation, match='no_tool_evidence'):
        tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)


def test_model_unauthorized_call_blocked(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: [])
    monkeypatch.setattr(tc, 'chat', lambda *a, **kw: {'role': 'assistant', 'tool_calls': [{'function': {'name': 'get_execution_history', 'arguments': {}}}]})
    with pytest.raises(tc.GuardrailViolation, match='unauthorized_tool'):
        tc.retrieve('ollama', 'review', {}, lambda *a: None, lambda: None)


def test_model_cannot_widen_trusted_metadata_scope(monkeypatch):
    from app.executions import tool_calling as tc
    monkeypatch.setattr(tc, 'discover', lambda **kw: catalog())
    monkeypatch.setattr(tc, 'chat', lambda *a, **kw: {
        'role': 'assistant',
        'tool_calls': [{'function': {'name': 'search_knowledge', 'arguments': {
            'query': 'review', 'metadataFilter': {'tenant': 'other'}
        }}}],
    })
    with pytest.raises(tc.GuardrailViolation, match='metadata_scope_override'):
        tc.retrieve('ollama', 'review', {'tenant': 'authorized'}, lambda *a: None, lambda: None)
