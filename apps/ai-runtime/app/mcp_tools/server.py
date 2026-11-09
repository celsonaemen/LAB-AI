"""Official SDK stdio server; authority comes only from its trusted launcher."""
import os

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated
from uuid import UUID

from app.api.knowledge import SearchRequest, SearchResponse, DocumentDetails, semantic_search
from app.executions import repository
from app.executions.guardrails import check_request, filter_evidence, redact
from app.mcp_tools.contracts import authorize, validate_output, INPUTS, HistorySummary
from app.rag import store

mcp = FastMCP('Aegis local knowledge', log_level='ERROR')


def _run(name, arguments):
    authorize(name, os.getenv('AEGIS_MCP_AGENT', ''), os.getenv('AEGIS_MCP_APPROVED') == 'true')
    request = INPUTS[name].model_validate(arguments)
    if name == 'search_knowledge':
        check_request(request.query)
        result = filter_evidence(semantic_search(request), request.maxContextChars)
    elif name == 'get_document':
        result = store.get_document(str(request.document_id))
        if result is None:
            raise ValueError('document_not_found')
    elif name == 'list_documents':
        result = store.list_documents(request.limit, request.offset)
    else:
        fields = HistorySummary.model_fields
        result = [{key: row[key] for key in fields} for row in repository.history(request.limit, request.offset)]
    return validate_output(name, redact(result))


@mcp.tool()
def search_knowledge(query: Annotated[str, Field(min_length=1, max_length=500)],
                     limit: Annotated[int, Field(ge=1, le=20)] = 5,
                     top_k: Annotated[int | None, Field(ge=1, le=20)] = None,
                     minScore: Annotated[float, Field(ge=-1, le=1)] = 0.0,
                     metadataFilter: dict[str, str] | None = None,
                     maxContextChars: Annotated[int, Field(ge=200, le=12000)] = 6000) -> SearchResponse:
    """Retrieve bounded untrusted knowledge evidence and actual chunk references."""
    return _run('search_knowledge', dict(query=query, limit=limit, top_k=top_k, minScore=minScore,
                                       metadataFilter=metadataFilter or {}, maxContextChars=maxContextChars))


@mcp.tool()
def get_document(document_id: UUID) -> DocumentDetails:
    """Read indexed document metadata by UUID; never read arbitrary files."""
    return _run('get_document', {'document_id': document_id})


@mcp.tool()
def list_documents(limit: Annotated[int, Field(ge=1, le=20)] = 20,
                   offset: Annotated[int, Field(ge=0, le=100000)] = 0) -> list[DocumentDetails]:
    """List at most twenty indexed document metadata records."""
    return _run('list_documents', dict(limit=limit, offset=offset))


@mcp.tool()
def get_execution_history(limit: Annotated[int, Field(ge=1, le=20)] = 20,
                          offset: Annotated[int, Field(ge=0, le=100000)] = 0) -> list[HistorySummary]:
    """Read local operator history summaries after report approval; no tasks or results."""
    return _run('get_execution_history', dict(limit=limit, offset=offset))


# FastMCP generates Pydantic argument models. Require extras to be rejected by
# the protocol handler itself, before the function signature could discard them.
for tool in mcp._tool_manager.list_tools():
    tool.fn_metadata.arg_model.model_config['extra'] = 'forbid'
    tool.fn_metadata.arg_model.model_rebuild(force=True)
    tool.parameters = tool.fn_metadata.arg_model.model_json_schema()

if __name__ == '__main__':
    # Import native numerical extensions before the SDK starts its event loop.
    # Lazy first import inside a tool callback can stall extension loading.
    import fastembed

    mcp.run(transport='stdio')
