import os
import asyncio
import pytest

from app.mcp_tools.client import call_tool, discover, MCPToolError


@pytest.mark.parametrize('agent,name,args', [
    ('risk-agent', 'list_documents', {}),
    ('report-agent', 'get_execution_history', {}),
    ('data-agent', 'list_documents', {'approved': True}),
    ('data-agent', 'shell', {}),
    ('data-agent', 'get_document', {'document_id': 'invalid'}),
])
def test_real_server_rejects_direct_sdk_calls(agent, name, args):
    from app.mcp_tools.client import connection
    async def run():
        async with connection(agent) as session:
            return await session.call_tool(name, args)
    assert asyncio.run(run()).isError


def test_real_stdio_discovery():
    catalog = discover()
    assert {t['id'] for t in catalog} == {'search_knowledge', 'get_document', 'list_documents', 'get_execution_history'}
    assert all(t['inputSchema']['additionalProperties'] is False for t in catalog)
    history = next(t for t in catalog if t['id'] == 'get_execution_history')
    assert history['requiresApproval'] and history['allowedAgents'] == ['report-agent']


@pytest.mark.parametrize('name,args,agent,approved', [
    ('shell', {}, 'data-agent', False),
    ('list_documents', {}, 'risk-agent', False),
    ('get_execution_history', {}, 'report-agent', False),
    ('list_documents', {'limit': 21}, 'data-agent', False),
    ('list_documents', {'approved': True}, 'data-agent', False),
    ('get_document', {'document_id': '../../secret'}, 'data-agent', False),
])
def test_rejected_calls(name, args, agent, approved):
    with pytest.raises(MCPToolError):
        call_tool(name, args, agent, approved)


def test_real_stdio_missing_database(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://aegis_dev@127.0.0.1:1/missing')
    with pytest.raises(MCPToolError, match='tool_failed'):
        call_tool('list_documents', {})


def test_real_stdio_native_rag(monkeypatch):
    dsn = os.getenv('AEGIS_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('AEGIS_TEST_DATABASE_URL required')
    monkeypatch.setenv('DATABASE_URL', dsn)
    documents = call_tool('list_documents', {'limit': 2})
    assert isinstance(documents, list)
    if documents:
        result = call_tool('get_document', {'document_id': documents[0]['documentId']})
        assert result['documentId'] == documents[0]['documentId']
    result = call_tool('search_knowledge', {'query': 'risco de carteira', 'limit': 2})
    assert set(result) >= {'model', 'results', 'context'}
    assert len(result['results']) <= 2
    history = call_tool('get_execution_history', {'limit': 2}, 'report-agent', True)
    assert all(set(row) == {'id', 'state', 'workflow', 'provider', 'createdAt', 'startedAt', 'finishedAt'} for row in history)
