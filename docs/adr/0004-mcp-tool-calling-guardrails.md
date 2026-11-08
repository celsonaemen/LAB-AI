# ADR 0004 — scoped MCP and guarded tool calling

Status: accepted implementation plan, 2026-11-07. Read Stage2 validation and audited registry, provider facade, worker/state/events before code. Preserve the coordinator and Stage1 RAG.

## Decision

Use the official `mcp==1.30.0` Python SDK, a pinned supported v1 maintenance release compatible with existing FastAPI/Starlette/Pydantic. pip dry-run resolves without replacing those packages. v2.3.0 is available, but avoiding a transport/API migration minimizes this increment; reconsider v2 separately. Sources: [official v1 README](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0), [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling).

Use a fixed local stdio subprocess launched by the runtime interpreter, never a model/user-supplied command. The server reuses Python RAG/store rather than exposing SQL/files/shell. Official ClientSession initializes, discovers and calls tools. No extra listening port, broker, Docker or WSL. MCP is a protocol boundary, not a trust boundary by itself.

## Tools and authority

Four tools: search_knowledge (same bounded RAG request), get_document (UUID), list_documents (bounded pagination), get_execution_history (bounded history summaries). Server and client both enforce fixed agent capabilities. Data Agent can search/get/list; Report Agent can search/get/list and history only after explicit approval; Risk/Analytics retain their existing validated calculation tools. History is scoped to the local single-user operator; there is no claim of multi-tenant/user RBAC.

Approval is the existing persisted pre-report gate. An unapproved history call is blocked, not silently approved or queued as a new arbitrary action. Model/user arguments cannot supply agent identity, approval, commands, connection strings or permissions. Child-process authority is supplied by trusted client environment, and tools expose only approved schemas.

## Integration seams

- `app/mcp_tools/client.py`: `discover(agent_id='data-agent', approved=False)` synchronous catalog, and `call_tool(name, arguments, agent_id='data-agent', approved=False)` synchronous structured result via real SDK session. Also expose async connection/session if needed for bounded multi-call reuse. Names are exact four IDs above. Catalog items `{id,description,inputSchema,allowedAgents,requiresApproval}`.
- `app/mcp_tools/server.py`: SDK FastMCP stdio server with validated bounded handlers reusing RAG/store. Outputs keep existing RAG result shape (`model,results,context`) and metadata shapes. History summaries omit task/raw results by default.
- `app/executions/guardrails.py`: `GuardrailViolation(code)` and `redact(value)` plus request/evidence checks. MCP/server/client may call these helpers; secrets and obvious injection attempts never become privileged instructions. Defense is layered and explicitly heuristic, not a claim to eliminate all prompt injection.
- `app/executions/tool_calling.py`: guarded Data Agent retrieval through MCP. Deterministic mode deliberately selects search_knowledge and is labeled as such. Ollama mode sends discovered permitted schemas, reads actual tool_calls, validates/authorizes bounded calls, returns role=tool results to the model and loops within round/call/time/output limits. No fallback to deterministic on model failure.
- Existing worker uses this retrieval seam in Data Agent, keeping fixed agent dependencies/calculations/report gate. Tool/discovery/guardrail/model events use existing persistence. Existing tool traces remain compatible; security-sensitive arguments/results are redacted before display/persistence.
- Runtime GET `/internal/v1/tools` returns actual MCP discovery catalog; .NET GET `/api/v1/tools` forwards it. Angular displays discovery, MCP/model/guardrail events, sanitized payloads and existing approval controls.

## Grounding and controls

Treat retrieved excerpts as untrusted data. Detect and block clear instruction-overriding requests and quarantine suspicious document chunks; apply immutable tool allowlists/schema checks regardless of text. Mask known secret/token/password patterns and sensitive identifiers in traces/results. Reject schema extras, invalid UUIDs, oversized inputs/outputs, excessive tool rounds/calls and unauthorized actions. Only actual returned chunk/document references can be cited. Insufficient evidence produces an explicit status; model-proposed references must be validated, never invented. Model prose remains subject to human review.

## Validation and completion boundary

Run real SDK stdio discovery/calls, native PostgreSQL/RAG, permission/approval/injection/redaction/failure tests and full Stage1/2 regressions. No Ollama executable/listener/model was detected. Keep deterministic tests plus opt-in real inference probe. Without an actual model-selected MCP call and grounded response, the user's strict Stage3 completion criterion is **not met**, even if protocol/guardrail code passes. Document that limit, never label a scripted provider as real inference. No push/publication.
