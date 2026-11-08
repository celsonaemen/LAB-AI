# ADR 0003 — durable agent orchestration in the existing runtime

Status: accepted for Stage 2, 2026-11-07. Implements the user-approved orchestrator scope without another service or message broker.

## Audit and decision before implementation

Stage 1 has four typed .NET knowledge routes, Python-owned RAG and psycopg persistence, and Angular same-origin HTTP. Domain is currently an empty boundary. No durable execution infrastructure exists. The existing native PostgreSQL 18 instance is operational; Docker/WSL are excluded.

Place the coordinator and specialized agents in Python alongside RAG. A bounded background worker claims persisted Pending executions; PostgreSQL is the durable work source. .NET Domain owns public workflow admission (supported workflows and task bounds), Application owns typed execution contracts/use cases, Infrastructure implements the runtime HTTP port, and API exposes JSON/SSE. The runtime independently enforces its tool policy and dependency ordering. This reuses the persistence adapter and avoids splitting one execution state machine across languages.

Alternative: a .NET coordinator with Python calls per agent would require an additional .NET database adapter and distributed partial-step recovery now. Alternative: RabbitMQ would add operational cost without removing transactional state requirements. Both remain unnecessary for this single-worker local demonstration.

## Execution and tools

Two fixed workflows: `portfolio-review` and `document-review`. Both execute `data-agent`, `risk-agent`, `analytics-agent`, `report-agent` in dependency order. Portfolio inputs are built-in fictional fixtures, never real banking data. Document review uses the validated RAG and reports insufficient evidence explicitly.

Execution states: Pending, Running, AwaitingApproval, Completed, Failed, Cancelled. Optional human gate pauses before the report; explicit approve resumes it. Cancellation is persisted and checked between bounded read-only operations, with a terminal-state guard preventing completion after cancellation. Each step, tool invocation, result/evidence, error, timestamp and duration is stored. A runtime restart marks interrupted Running work Failed; it must never silently execute a claimed run twice. Pending/approval records survive restart.

Tools have IDs, descriptions, JSON input schemas, validated arguments, per-agent server-side permissions and structured results. No arbitrary Python, shell, SQL, executable names or URLs are accepted from users/models. Internal read/calculation tools prepare the boundary for future Tool Calling/MCP without implementing a server.

Planning is deterministic from the admitted workflow; tool execution is a separate validated dispatcher; report language generation is an optional provider. Default deterministic report is explicitly labeled and does not claim LLM inference. `AEGIS_LLM_PROVIDER=ollama` uses an operator-configured local Ollama chat endpoint/model; provider errors/limits/timeouts fail the run visibly, with no silent deterministic fallback. Only fictional/evidence inputs should be used in this local demo.

## Public contract frozen for implementation

Create JSON: `{task, workflow:"portfolio-review"|"document-review", portfolioId:"balanced"|"concentrated", requireApproval:false, metadataFilter:{}}`. Task max500 (RAG query bound); string metadata same Stage1 limits. No caller-supplied tool permissions or model endpoint.

Execution JSON: `{id,task,workflow,portfolioId,state,agents:[{id,state,startedAt,finishedAt,durationMs,result,error}],createdAt,startedAt,finishedAt,durationMs,result,error,provider,requireApproval}`. Results are structured agent-specific JSON; errors are sanitized strings/null. Provider label is `deterministic` or `ollama`.

Events: `{sequence,executionId,type,agentId,timestamp,data}` with monotonic per-execution sequence. History returns execution arrays with `limit`/`offset`. Events endpoint returns arrays after `after`; SSE wraps the same persisted events, supports Last-Event-ID and closes at terminal states. Browser uses only public .NET routes.

POST `/api/v1/executions` ->202 snapshot/Location; GET collection ->200 history; GET `/{id}` ->200/404; GET `/{id}/events?after=0` ->200 array; GET `/{id}/events/stream` ->SSE; POST `/{id}/cancel` and `/{id}/approve` ->200 snapshot/409 invalid transition. Runtime mirrors JSON routes under `/internal/v1/executions`; no runtime SSE required.

## Validation and limits

Preserve Stage1 tests and rerun real PDF acceptance. Add state/order/tool-permission/fault/timeout/cancel/insufficient-evidence tests, native database history/event tests, public HTTP completed/approval/cancel scenarios and browser monitoring. Real LLM inference is reported as unverified unless an actual configured model responds; automated tests require no API keys. Existing localhost demo still has no user authentication: workflow/tool permissions are application capabilities, not user RBAC. Do not expose publicly.
