# AEGIS AGENT LAB

Enterprise AI agent orchestration platform — independent technical portfolio project using fictional financial data.

Independent educational project. It is not affiliated with, endorsed by, or based on the internal architecture of any financial institution.

## Start here — technical portfolio

AEGIS helps an analyst retrieve documentary evidence, review a synthetic customer case and follow a traceable Data → Risk → Analytics → Report workflow. It demonstrates full-stack engineering, real vector retrieval, MCP tools and explicit human approval using fictional data.

| Layer | Implementation |
|---|---|
| Interface | Angular 20 + TypeScript, document ingestion/search, customer cases, execution history and SSE monitoring |
| Public API | ASP.NET Core .NET 10, Clean Architecture, typed Python gateway, JWT permission policies for configured environments |
| AI runtime | Python + FastAPI, four agents, bounded tools, MCP over local stdio |
| Retrieval | PostgreSQL + pgvector, HNSW cosine index, multilingual FastEmbed vectors with 384 dimensions |
| Model | Deterministic provider for reproducible workflows; optional Ollama adapter, real LLM inference still unvalidated |

The customer workspace contains three fictional customers and a six-document fixture. The broader knowledge fixture contains twelve synthetic PDF/TXT/Markdown documents. Ingestion and retrieval use the existing application pipeline.

Latest local verification: **107 Python tests, 55 .NET tests and 25 Angular tests passed; production frontend build passed**. Python verification included the existing native pgvector test database and real cached embeddings. GitHub Actions results must be checked separately.

Security hardening restricts the LLM endpoint to loopback, blocks model proxies/redirects, disables runtime embedding downloads and browser voice, limits the internal credential to dedicated clients, and removes sensitive rejected values from validation responses. See the [executed validation](docs/validation/local-privacy-hardening.md) and [current threat model](docs/security/threat-model.md).

**Readiness:** demonstration/homologation with synthetic data. Customer-level isolation across generic knowledge/execution/MCP access, corporate browser sign-in/SSE, infrastructure egress restrictions, key management and independent security assessment remain required before real bank data. No certification or invulnerability claim is made. LM Studio integration is pending.

For a technical review, start with the [RAG architecture](docs/architecture/rag-pipeline.md), [agent orchestration](docs/architecture/agent-orchestrator.md), [synthetic end-to-end evidence](docs/validation/synthetic-knowledge-mcp.md), and [security validation](docs/validation/local-privacy-hardening.md). The implementation was developed with AI assistance; automated checks and documented decisions are provided for review.

## Preserved delivery: Stage 3 — MCP, Tool Calling and guardrails

The platform exposes a real local MCP server through the official Python SDK (`mcp==1.30.0`). Four bounded read-only tools are discoverable through FastAPI and the public .NET gateway: `search_knowledge`, `get_document`, `list_documents` and approval-gated `get_execution_history`. Tool schemas, permissions, results and security blocks are persisted and displayed by Angular.

Guardrails detect selected prompt-injection patterns and reject unauthorized tools, invalid arguments, authority overrides, metadata-scope widening, unknown citation IDs and excessive calls, rounds or output. Retrieved documents remain untrusted evidence. These checks do not guarantee complete injection resistance or the correctness of every generated statement.

Latest local validation on 2026-11-08: **77 Python, 47 .NET and 20 Angular tests passed**. A corpus of **12 synthetic PDF/TXT/Markdown documents produced 68 persisted chunks and real 384-dimensional embeddings**. All **27 end-to-end acceptance checks passed**, including .NET ingestion, pgvector verification, the four MCP tools, client/server security, document quarantine, multiagent evidence, live SSE, approval and cancellation. The Angular interface also completed an observed browser execution through approval to all four agents completing.

The earlier MCP startup, structured-output and context-budget failures were reproduced and corrected. See the [synthetic knowledge validation and reproduction commands](docs/validation/synthetic-knowledge-mcp.md), [manifest](datasets/synthetic-knowledge/manifest.json) and [browser evidence](docs/validation/synthetic-knowledge-browser.json). The [earlier Stage 3 report](docs/validation/stage-3-mcp.md) records the preceding state. No Ollama model is configured, so real LLM-selected Tool Calling remains **unvalidated**; these executions explicitly use the deterministic provider.

## Preserved delivery: Stage 2 — traceable agent orchestration

The local application now runs Data, Risk, Analytics and Report agents using safe internal tools, actual RAG evidence, durable PostgreSQL execution/event records, approval/cancellation and an Angular SSE console. Native HTTP acceptance passed through both .NET and the Angular proxy. Validation: **52 Python, 38 .NET and 17 Angular tests passed**, with the Stage1 PDF pipeline rechecked.

Start services as below, open http://127.0.0.1:4200 and select **Execuções de agentes**. Read [architecture and boundaries](docs/architecture/agent-orchestrator.md), [Stage 2 validation](docs/validation/stage-2-orchestrator.md), and the [PowerShell agent demo](docs/demo-orchestrator.md).

The default report is explicitly **deterministic, not LLM generated**. An optional Ollama adapter is implemented; actual Ollama inference was not verified because no local model was configured. Authorization remains deterministic in both modes. The earlier Stage 2 did not include authentication; current security controls and remaining gaps are documented above.

## Preserved delivery: Stage 1 — real HTTP RAG integration

Validated on 2026-11-07 using native PostgreSQL 18.6 + pgvector 0.8.7, with real FastEmbed embeddings. A PDF traversed the public .NET API, FastAPI, extraction, chunking and vector persistence, and returned verifiable sources for Portuguese and English searches. The same acceptance checks passed through Angular's development proxy. Angular now includes document upload and semantic search; browser search was verified against the real services.

Start with the [PowerShell demonstration](docs/demo-rag.md). Read [Stage 1 validation and exact change inventory](docs/validation/stage-1-rag.md). Docker and WSL are not required for this route and were not modified in this stage.

Implemented in source: strict Angular 20 scaffold, ASP.NET Core net10.0 Clean Architecture solution, FastAPI runtime, health probes, JSON logging, versioned knowledge migrations, vector(384) storage and HNSW index, local multilingual FastEmbed embeddings, PDF/TXT/Markdown extraction, chunking, metadata filtering, document deduplication, typed .NET knowledge gateway, and bounded retrieval context with source references. See the verification report for what has actually run.

At the Stage 1 checkpoint, authentication and production hardening were not implemented. Current security controls and remaining gaps are documented above; application OpenTelemetry instrumentation is still pending. Stage 1 retrieval returns evidence without an LLM answer; Stage 2 can separately consolidate it through a configured report provider.

## Prerequisites

- Native PostgreSQL 18 with pgvector (validated route on this workstation). Docker Compose remains an optional, unvalidated runtime alternative.
- Local development: Node 24, .NET 10 SDK, Python 3.12–3.14.
- No LLM API key is required. The planned initial provider is deterministic.

Use Node 24 for Angular 20 ([compatibility table](https://angular.dev/reference/versions)). A later .NET SDK can target an earlier framework ([SDK selection](https://learn.microsoft.com/en-us/dotnet/core/versions/selection)), but stable SDK 10 is recommended and used in containers/CI.

## Optional Docker Compose configuration (not validated end to end)

The checked-in Compose template is not a turnkey deployment: its Production API requires explicit identity/security configuration and the runtime needs a pre-provisioned model volume. The commands below describe the infrastructure template, not a validated one-command demo. Use the native demonstration route for the validated environment.

```powershell
Copy-Item .env.example .env
# Edit .env and set POSTGRES_PASSWORD to a local development password.
docker compose config --quiet
docker compose up --build -d --wait
```

Open http://localhost:4200. API liveness: http://localhost:5080/health; runtime readiness: http://localhost:5080/health/ready. PostgreSQL and Python are internal containers, with no published ports. Database volumes persist across restarts. The extension SQL runs only when a new volume is initialized; subsequent schema changes require migrations.

`docker compose stop` stops services while retaining the database. Optional collector: `docker compose --profile observability up -d`. No application traces are exported yet.

## Run locally on this workstation (PowerShell)

From the repository root, first run `./scripts/native.ps1 Database`. Then use three separate terminals:

```powershell
./scripts/native.ps1 Runtime
# Terminal 2:
./scripts/native.ps1 Api
# Terminal 3:
./scripts/native.ps1 Web
```

Open http://127.0.0.1:4200. The runtime script applies migrations and warms the real model before serving. Native cluster location defaults to `$env:LOCALAPPDATA/AegisAgentLabNative`; it is an existing local development cluster, not something bundled in Git. See the demonstration for acceptance commands and setup assumptions.

### Generic local dependency installation

Runtime:

```powershell
python -m venv apps/ai-runtime/.venv
apps/ai-runtime/.venv/Scripts/python -m pip install -e './apps/ai-runtime[test]'
# Separate setup phase: download only approved public model artifacts, before serving data.
$env:EMBEDDING_CACHE_DIR = Join-Path (Get-Location) '.model-cache'
apps/ai-runtime/.venv/Scripts/python -c "import os; from fastembed import TextEmbedding; from app.rag.knowledge import MODEL; TextEmbedding(model_name=MODEL, cache_dir=os.environ['EMBEDDING_CACHE_DIR'])"
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
cd apps/ai-runtime
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-config app/logging.json
```

API (repository root):

```powershell
dotnet run --project apps/api/src/Aegis.Api --urls http://localhost:5080
```

Frontend (repository root):

```powershell
npm --prefix apps/web ci
npm --prefix apps/web start
```

On Linux/macOS use `.venv/bin/python` instead of `.venv/Scripts/python`. Local health tests require no database. Knowledge endpoints require a pgvector database and versioned migrations; configure DATABASE_URL privately and run `python -m app.migrate` from the repository root before using them. This workstation also has a project-local SDK at `.tools/dotnet/dotnet.exe` because the globally installed SDK was a preview with no ASP.NET Core 10 runtime.

## Verify

```powershell
dotnet test apps/api/Aegis.slnx
apps/ai-runtime/.venv/Scripts/python -m pytest apps/ai-runtime/tests -q
npm --prefix apps/web run build
npm --prefix apps/web test -- --watch=false --browsers=ChromeHeadless
docker compose config --quiet
```

Frontend tests require Chrome/Chromium. Builds use the production configuration; no backend URL or secret is bundled, as `/api` uses same-origin routing. Development proxy configuration is never used as a production server.

## Repository map

| Path | Responsibility |
|---|---|
| apps/web | Angular application |
| apps/api/src | API, Application, Domain, Infrastructure |
| apps/api/tests | HTTP contract integration tests |
| apps/ai-runtime | FastAPI service and tests |
| mcp/server | Documented future tool boundary |
| infrastructure | Container builds, database initialization, collector |
| docs | Architecture, ADR, API contracts, security, delivery plan |

Read [architecture](docs/architecture/overview.md), [ADR 0001](docs/adr/0001-hybrid-runtime.md), [contracts](docs/api/contracts.md), [threat model](docs/security/threat-model.md), and [verification report](docs/bootstrap-report.md).

For the implemented knowledge API, file ingestion examples, source references and model limitations, read [RAG pipeline](docs/architecture/rag-pipeline.md), [vector database](docs/architecture/vector-database.md), [ADR 0002](docs/adr/0002-semantic-search.md), and the [engineering log](docs/engineering-log/2026-11-07.md).

Real-model tests require a pre-provisioned cache: set `AEGIS_REAL_EMBEDDINGS=1` and an absolute `EMBEDDING_CACHE_DIR`. Serving and tests do not download missing weights. Database integration tests additionally require `AEGIS_TEST_DATABASE_URL` pointing to a dedicated disposable pgvector database; these tests clean up only their own inserted rows. Never point integration tests at production. CI provisions model artifacts in a separate setup step before offline tests; a configured workflow is not evidence of a successful CI run.
