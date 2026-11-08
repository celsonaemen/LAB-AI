"""Bounded real SDK sessions against one fixed local Python module."""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.mcp_tools.contracts import MCPToolError, INPUTS, TOOL_AGENTS, authorize, validate_output

SESSION_TIMEOUT_SECONDS = 60


@asynccontextmanager
async def connection(agent_id='data-agent', approved=False):
    env = {key: value for key, value in os.environ.items()
           if key in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA', 'HOME',
                      'DATABASE_URL', 'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE',
                      'EMBEDDING_CACHE_DIR', 'HF_HUB_OFFLINE'}}
    env.update(AEGIS_MCP_AGENT=agent_id, AEGIS_MCP_APPROVED='true' if approved is True else 'false')
    parameters = StdioServerParameters(command=sys.executable, args=['-m', 'app.mcp_tools.server'],
                                       cwd=str(Path(__file__).resolve().parents[2]), env=env)
    # Server errors can contain backend exception details; never forward stderr
    # to user-visible traces. Protocol failures are mapped to stable codes below.
    with open(os.devnull, 'w') as errlog:
        async with stdio_client(parameters, errlog=errlog) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=SESSION_TIMEOUT_SECONDS)) as session:
                await session.initialize()
                yield session


async def _request(name=None, arguments=None, agent_id='data-agent', approved=False):
    try:
        async with asyncio.timeout(SESSION_TIMEOUT_SECONDS):
            async with connection(agent_id, approved) as session:
                discovered = await session.list_tools()
                if name is None:
                    return [{'id': tool.name, 'description': tool.description or '', 'inputSchema': tool.inputSchema,
                             'allowedAgents': TOOL_AGENTS[tool.name],
                             'requiresApproval': tool.name == 'get_execution_history'}
                            for tool in discovered.tools if tool.name in TOOL_AGENTS]
                if name not in {tool.name for tool in discovered.tools}:
                    raise MCPToolError('unknown_tool')
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise MCPToolError('tool_failed')
                value = result.structuredContent
                if name in {'list_documents', 'get_execution_history'} and isinstance(value, dict):
                    value = value.get('result')
                from app.executions.guardrails import redact, filter_evidence
                value = filter_evidence(value) if name == 'search_knowledge' else value
                return validate_output(name, redact(value))
    except Exception as error:
        # Context-manager TaskGroups wrap handler errors in ExceptionGroups.
        def code(exc):
            if isinstance(exc, MCPToolError):
                return str(exc)
            for child in getattr(exc, 'exceptions', ()):
                found = code(child)
                if found:
                    return found
            return None
        raise MCPToolError(code(error) or 'mcp_connection_failed') from None


def discover(agent_id='data-agent', approved=False):
    return asyncio.run(_request(agent_id=agent_id, approved=approved))


def call_tool(name, arguments, agent_id='data-agent', approved=False):
    authorize(name, agent_id, approved)
    try:
        arguments = INPUTS[name].model_validate(arguments).model_dump(mode='json')
    except Exception:
        raise MCPToolError('invalid_tool_arguments') from None
    return asyncio.run(_request(name, arguments, agent_id, approved))
