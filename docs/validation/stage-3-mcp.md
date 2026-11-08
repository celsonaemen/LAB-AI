# Stage 3 validation — MCP, Tool Calling and guardrails

Date: 2026-11-08. Aegis Agent Lab is an independent educational platform using fictional data.

## Implemented

- Official Python MCP SDK pinned at `mcp==1.30.0`, using a fixed local stdio subprocess.
- Four read-only tools: `search_knowledge`, `get_document`, `list_documents`, and approval-gated `get_execution_history`.
- Typed schemas, dual client/server authorization, bounded time/calls/rounds/output and stable error mapping.
- Ollama chat/tool-call adapter without deterministic fallback.
- Prompt-injection quarantine, recursive redaction, metadata-scope enforcement and citation validation.
- Public `GET /api/v1/tools` through .NET; Angular catalog and trace presentation.

## Executed results

- Python: `64 passed, 11 skipped`.
- .NET: `47 passed` using the project-local .NET 10 SDK/runtime.
- Angular: `20 passed` in Chrome 157.
- Dependency check: no broken Python requirements; MCP 1.30.0, FastAPI 0.121.0 and Pydantic 2.14.3.
- Native database: PostgreSQL 18.6 and pgvector 0.8.7.
- Live discovery passed at `/internal/v1/tools` and public `/api/v1/tools`, returning all four schemas and permissions.
- A public deterministic execution persisted `McpDiscovered`, `ToolCallRequested` and `McpToolStarted`. The semantic call exceeded the worker's 45-second cold-start timeout while loading FastEmbed, then failed safely with persisted failure events.

## Explicit limitations

Stage 3 strict acceptance is **not complete**. No Ollama executable/model/listener was available, so no real model-selected tool invocation is claimed. The deterministic path is clearly labeled and is not LLM inference. The cold-start timeout requires a persistent MCP connection or model warm-up before the complete MCP semantic-search flow can be claimed.

No commit, push, publication, Docker reinstall or WSL modification was performed.
