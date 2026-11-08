import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from app.api.knowledge import SearchRequest, SearchResponse, DocumentDetails

MAX_OUTPUT_BYTES = 131072
TOOL_AGENTS = {
    'search_knowledge': ['data-agent', 'report-agent'],
    'get_document': ['data-agent', 'report-agent'],
    'list_documents': ['data-agent', 'report-agent'],
    'get_execution_history': ['report-agent'],
}


class MCPToolError(RuntimeError):
    pass


class Pagination(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(default=20, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=100000)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: UUID


class HistorySummary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    state: str
    workflow: str
    provider: str
    createdAt: str
    startedAt: str | None
    finishedAt: str | None


INPUTS = {'search_knowledge': SearchRequest, 'get_document': DocumentInput,
          'list_documents': Pagination, 'get_execution_history': Pagination}
OUTPUTS = {'search_knowledge': TypeAdapter(SearchResponse), 'get_document': TypeAdapter(DocumentDetails),
           'list_documents': TypeAdapter(list[DocumentDetails]),
           'get_execution_history': TypeAdapter(list[HistorySummary])}


def authorize(name, agent_id, approved):
    if name not in TOOL_AGENTS:
        raise MCPToolError('unknown_tool')
    if agent_id not in TOOL_AGENTS[name]:
        raise MCPToolError('tool_not_allowed')
    if name == 'get_execution_history' and approved is not True:
        raise MCPToolError('approval_required')


def validate_output(name, result):
    if len(json.dumps(result, ensure_ascii=False).encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise MCPToolError('output_limit_exceeded')
    return OUTPUTS[name].dump_python(OUTPUTS[name].validate_python(result), mode='json')
