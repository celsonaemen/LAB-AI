# Service contracts

## Implemented foundation

- API `GET /health`: 200 `{ "status": "ok", "service": "aegis-api" }`.
- API `GET /health/ready`: 200 when runtime `/health/ready` confirms database/migration readiness; 503 otherwise. Timeout: 3 seconds.
- Runtime `GET /health`: 200 `{ "status": "ok", "service": "ai-runtime", "provider": "deterministic" }`.
- Web `/health`: static reverse-proxy liveness response in the container.

## Historical planned execution API (superseded by Stage 2)

`POST /api/v1/executions`: authenticated user sends `{ "conversationId": "demo-001", "task": "Analyze fictional portfolio", "mode": "multi-agent", "agents": ["data-agent", "risk-agent", "analytics-agent", "report-agent"] }`. The API derives user and tenant from validated identity, validates the allowlist and task length (1–4000), persists PENDING plus audit event, then returns 202 with execution id and Location header. Idempotency-Key must be scoped to caller identity.

`GET /api/v1/executions/{id}` enforces ownership. Events endpoint uses SSE with monotonic persisted event ids, replay via Last-Event-ID and heartbeat comments. Terminal state closes the stream. PENDING → RUNNING → COMPLETED/FAILED; RUNNING may enter WAITING_APPROVAL or CANCELLED. Transitions are validated in Domain when implemented.

Internal `POST /internal/v1/runs` uses runtime-request.schema.json and runtime-response.schema.json. The API supplies correlation id and approved tool names. Runtime has no authority to approve tools. This endpoint is reserved, not active in this increment.

Errors use Problem Details at the public API. Map upstream timeout to 504, unavailable runtime to 503, invalid upstream output to 502. Never forward exception details to browsers. Private service calls must gain authenticated transport before deployment beyond local development.

Other planned public resources: GET /api/v1/agents, GET /api/v1/tools, GET /api/v1/audit. They remain unavailable until authorization and persistence exist.

The historical execution sketch above is not an active contract. Stage2 implements the smaller fixed-workflow contract below; the old `runtime-request.schema.json` and `runtime-response.schema.json` remain unused planning artifacts. No duplicate `/internal/v1/runs` endpoint was created.

## Implemented Stage 2 execution API

| Method / public route | Behavior |
|---|---|
| POST `/api/v1/executions` | 202 snapshot and Location after durable creation |
| GET `/api/v1/executions?limit=20&offset=0` | History array, limit1..100/offset0..100000 |
| GET `/api/v1/executions/{id}` | Snapshot or404 |
| GET `/api/v1/executions/{id}/events?after=0` | Ordered persisted event array |
| GET `/api/v1/executions/{id}/events/stream` | SSE `event: execution`, sequence ID, heartbeat, terminal close |
| POST `/api/v1/executions/{id}/cancel` | Cancel nonterminal execution;409 for terminal |
| POST `/api/v1/executions/{id}/approve` | Resume AwaitingApproval;409 otherwise |

```json
{"task":"Analise a carteira fictícia e consulte garantias documentadas","workflow":"portfolio-review","portfolioId":"concentrated","requireApproval":true,"metadataFilter":{"area":"demo"}}
```

Task is nonblank/max500. Workflow: `portfolio-review` (public default) or `document-review`. Portfolio: `balanced` (default) or `concentrated`. All flows select the fixed Data/Risk/Analytics/Report dependency plan. MetadataFilter is a bounded string dictionary; arbitrary extra fields/tool permissions are rejected. `requireApproval` defaults false. Both POST action routes take no body.

Snapshot fields: `id, task, workflow, portfolioId, state, agents, createdAt, startedAt, finishedAt, durationMs, result, error, provider, requireApproval`. Each agent has `id, state, startedAt, finishedAt, durationMs, result, error`. Execution states are Pending/Running/AwaitingApproval/Completed/Failed/Cancelled; unexecuted agents can be Skipped after failure. Results are agent-specific structured JSON. Error text is sanitized.

Events contain `sequence, executionId, type, agentId, timestamp, data`. ToolStarted/ToolCompleted/ToolFailed data includes toolId, arguments/result/error and duration as applicable. Provider events are separate from tool events. SSE accepts nonnegative `after` and `Last-Event-ID`, choosing the larger cursor. Closing a stream never cancels the run. Missing resources404; invalid inputs400; invalid transitions409; upstream invalid502, unavailable503, timeout504.

Internal runtime JSON routes mirror these under `/internal/v1/executions` (no runtime SSE). .NET JSON calls have 15-second timeout and 8MB response bound. No browser accesses Python/PostgreSQL directly. Identity/RBAC remain unimplemented; bind to localhost. Full shapes and actual examples are in [Stage2 validation](../validation/stage-2-orchestrator.md).

## Implemented knowledge gateway

POST /api/v1/knowledge/documents, POST /api/v1/knowledge/search, GET /api/v1/knowledge/documents, and GET /api/v1/knowledge/documents/{id} are implemented as typed .NET-to-Python calls. They require a running, migrated PostgreSQL/pgvector database for successful storage/retrieval. See [RAG pipeline](../architecture/rag-pipeline.md) for exact request examples and limitations. The current demo has no authentication; it is bound to localhost.

### Stage 1 public contracts

| Method / route | Result |
|---|---|
| POST `/api/v1/knowledge/documents` | 201, Location header and receipt after transaction commit |
| POST `/api/v1/knowledge/search` | 200, ranked chunks and bounded evidence context |
| GET `/api/v1/knowledge/documents?limit=20&offset=0` | 200, document metadata; limit 1..100 |
| GET `/api/v1/knowledge/documents/{uuid}` | 200 document details or 404 |

File request: `title`, `source`, `filename`, `contentBase64`, optional string-valued `metadata` (20 entries / 4000 serialized characters), `chunkSize` (350 default), `chunkOverlap` (60 default). Plain text input uses `text` instead of file content. Exactly one input form is accepted. Decoded file limit: 2,000,000 bytes; supported PDF/TXT/MD/Markdown. No multipart endpoint was added.

Receipt example:

```json
{"documentId":"9fdf5f01-b6c2-4bc3-9221-a053edb91e3a","chunks":2,"deduplicated":false,"model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2","status":"indexed","metadata":{"area":"demo"}}
```

Duplicate requests also return 201 with `deduplicated: true`, the original ID and original stored metadata. GET details adds title, source, filename, contentHash, chunk configuration and timestamps.

Search: nonblank `query` (max 500 characters), `top_k` (1..20; overrides legacy `limit`), `minScore` (-1..1), optional string-valued `metadataFilter`, `maxContextChars` (200..12000). No matching evidence returns HTTP 200 with empty results/references and `context.status: "insufficient_evidence"`; `generatedAnswer` is null.

Public validation errors use Problem Details 400, missing document 404, malformed/incomplete upstream response 502, unavailable dependency 503, timeout 504. Kestrel rejects a request body over 3,000,000 bytes with 413 before application processing. Python performs the same knowledge operations under `/internal/v1/knowledge`; it is not a browser-facing API.
