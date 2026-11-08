# Verification report — foundation and semantic retrieval

Date: 2026-11-07. Branch: chore/architecture-bootstrap. Initial repository had no tracked files or commits. All listed files are newly created in this session; some were iterated during implementation. User-provided vacancy HTML/assets were not edited. No commit, push or LinkedIn publication was performed.

## Delivered source

Angular 20 strict scaffold; net10.0 Clean Architecture solution; Python FastAPI service; typed .NET knowledge gateway; PDF/TXT/Markdown extraction; normalization, configurable overlapping chunks and SHA-256 deduplication; real multilingual FastEmbed model with 384-dimensional vectors; PostgreSQL knowledge schema, foreign keys, metadata indexes and HNSW cosine index; versioned checksummed migration runner; metadata-filtered retrieval; source-attributed context with explicit insufficient evidence and no LLM generation; Compose/Dockerfiles, CI and documentation.

## Observed results

| Check | Actual result |
|---|---|
| Python suite with real-model opt-in | 34 passed, 3 skipped, 1 dependency deprecation warning |
| Real Portuguese/English model tests | Both passed within Python suite; actual model inference, 384 dimensions |
| Native PostgreSQL integration | NOT RUN: all 3 database cases skipped, no server available |
| SQL migration execution / HNSW runtime validation | NOT RUN: requires PostgreSQL; no claim of successful database migration |
| .NET tests | 10 passed, 0 failed |
| Angular production build under isolated Node 24 | Passed; initial bundle 247.68 kB |
| Angular ChromeHeadless tests | 2 passed |
| Local HTTP smoke checks | 7 passed: Python/API health, runtime readiness, Angular root, API/proxied validation, explicit 503 without database |
| Docker Compose configuration | Passed using copied standalone Compose v5.6.1 binary, exit 0 |
| Docker Engine / container build / startup | NOT PASSED: Engine absent after partial failed installation |
| npm audit | 16 moderate issues in development CLI dependency tree; major upgrade proposed by npm not automatically applied |
| Git ignores | .env, .tools, .model-cache, .venv and node_modules correctly ignored |

The small Portuguese model example gave cosine similarity 0.498236 for related credit/default text versus 0.173405 for unrelated food text. This is evidence of inference and a smoke example, not a quality benchmark. Database tests separately cover migration repeatability, HNSW presence, atomic storage, duplicate ids, missing documents, source attribution and real Portuguese/English search, but they still need a running PostgreSQL instance.

## Environment blocker: Docker installation

Authorized Docker Desktop installation via winget. Download hash verified; Desktop 4.98.0 installer failed enabling VirtualMachinePlatform / Microsoft-Windows-Subsystem-Linux with Windows DISM 0x800f0806 (pending operations). Copied Docker CLI 29.9.2 and Compose v5.6.1 binaries exist, but docker info fails with no Engine pipe. Separate Microsoft.WSL 2.7.14 installation failed with 0x80073d28 (administrator privileges required). No computer restart was performed. Resolve pending Windows operations, enable WSL 2 as administrator, finish Desktop installation, then test containers and PostgreSQL.

## Commands and engineering decisions

See [engineering log](engineering-log/2026-11-07.md) for grouped executed commands, failures/resolutions and dependencies, [RAG pipeline](architecture/rag-pipeline.md) for API examples, [vector database](architecture/vector-database.md) for migrations, and [ADR 0002](adr/0002-semantic-search.md) for alternatives. Local test artifacts are in ignored .tools/test-results.

## Exact created file inventory

- `.dockerignore`
- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.nvmrc`
- `README.md`
- `apps/ai-runtime/app/__init__.py`
- `apps/ai-runtime/app/agents/.gitkeep`
- `apps/ai-runtime/app/api/.gitkeep`
- `apps/ai-runtime/app/api/__init__.py`
- `apps/ai-runtime/app/api/knowledge.py`
- `apps/ai-runtime/app/context/.gitkeep`
- `apps/ai-runtime/app/guardrails/.gitkeep`
- `apps/ai-runtime/app/logging.json`
- `apps/ai-runtime/app/logging_config.py`
- `apps/ai-runtime/app/main.py`
- `apps/ai-runtime/app/migrate.py`
- `apps/ai-runtime/app/orchestration/.gitkeep`
- `apps/ai-runtime/app/providers/.gitkeep`
- `apps/ai-runtime/app/rag/.gitkeep`
- `apps/ai-runtime/app/rag/__init__.py`
- `apps/ai-runtime/app/rag/context.py`
- `apps/ai-runtime/app/rag/embeddings.py`
- `apps/ai-runtime/app/rag/knowledge.py`
- `apps/ai-runtime/app/rag/processing.py`
- `apps/ai-runtime/app/rag/store.py`
- `apps/ai-runtime/app/tools/.gitkeep`
- `apps/ai-runtime/pyproject.toml`
- `apps/ai-runtime/requirements.lock.txt`
- `apps/ai-runtime/tests/test_context.py`
- `apps/ai-runtime/tests/test_health.py`
- `apps/ai-runtime/tests/test_knowledge.py`
- `apps/ai-runtime/tests/test_knowledge_api.py`
- `apps/ai-runtime/tests/test_logging.py`
- `apps/ai-runtime/tests/test_pgvector_integration.py`
- `apps/ai-runtime/tests/test_processing.py`
- `apps/ai-runtime/tests/test_real_embeddings.py`
- `apps/api/Directory.Build.props`
- `apps/api/Aegis.slnx`
- `apps/api/src/Aegis.Api/KnowledgeEndpoints.cs`
- `apps/api/src/Aegis.Api/Aegis.Api.csproj`
- `apps/api/src/Aegis.Api/Program.cs`
- `apps/api/src/Aegis.Application/IRuntimeHealth.cs`
- `apps/api/src/Aegis.Application/KnowledgeContracts.cs`
- `apps/api/src/Aegis.Application/Aegis.Application.csproj`
- `apps/api/src/Aegis.Domain/Aegis.Domain.csproj`
- `apps/api/src/Aegis.Infrastructure/KnowledgeRuntimeClient.cs`
- `apps/api/src/Aegis.Infrastructure/Aegis.Infrastructure.csproj`
- `apps/api/src/Aegis.Infrastructure/RuntimeHealthClient.cs`
- `apps/api/tests/Aegis.Api.Tests/HealthTests.cs`
- `apps/api/tests/Aegis.Api.Tests/KnowledgeClientTests.cs`
- `apps/api/tests/Aegis.Api.Tests/KnowledgeTests.cs`
- `apps/api/tests/Aegis.Api.Tests/Aegis.Api.Tests.csproj`
- `apps/web/.editorconfig`
- `apps/web/.gitignore`
- `apps/web/.vscode/extensions.json`
- `apps/web/.vscode/launch.json`
- `apps/web/.vscode/tasks.json`
- `apps/web/README.md`
- `apps/web/angular.json`
- `apps/web/package-lock.json`
- `apps/web/package.json`
- `apps/web/proxy.conf.json`
- `apps/web/public/favicon.ico`
- `apps/web/src/app/app.config.ts`
- `apps/web/src/app/app.css`
- `apps/web/src/app/app.html`
- `apps/web/src/app/app.routes.ts`
- `apps/web/src/app/app.spec.ts`
- `apps/web/src/app/app.ts`
- `apps/web/src/app/core/.gitkeep`
- `apps/web/src/app/features/agents/.gitkeep`
- `apps/web/src/app/features/audit/.gitkeep`
- `apps/web/src/app/features/dashboard/.gitkeep`
- `apps/web/src/app/features/executions/.gitkeep`
- `apps/web/src/app/features/knowledge/.gitkeep`
- `apps/web/src/app/shared/.gitkeep`
- `apps/web/src/index.html`
- `apps/web/src/main.ts`
- `apps/web/src/styles.css`
- `apps/web/tsconfig.app.json`
- `apps/web/tsconfig.json`
- `apps/web/tsconfig.spec.json`
- `docker-compose.yml`
- `docs/adr/0001-hybrid-runtime.md`
- `docs/adr/0002-semantic-search.md`
- `docs/api/contracts.md`
- `docs/api/runtime-request.schema.json`
- `docs/api/runtime-response.schema.json`
- `docs/architecture/overview.md`
- `docs/architecture/rag-pipeline.md`
- `docs/architecture/vector-database.md`
- `docs/bootstrap-report.md`
- `docs/diagrams/.gitkeep`
- `docs/engineering-log/2026-11-07.md`
- `docs/linkedin-draft.md`
- `docs/plans/bootstrap.md`
- `docs/security/threat-model.md`
- `infrastructure/database/001-extensions.sql`
- `infrastructure/database/002-knowledge.sql`
- `infrastructure/database/migrations/V001__knowledge_schema.sql`
- `infrastructure/database/migrations/V002__knowledge_hnsw.sql`
- `infrastructure/docker/api.Dockerfile`
- `infrastructure/docker/nginx.conf`
- `infrastructure/docker/runtime.Dockerfile`
- `infrastructure/docker/web.Dockerfile`
- `infrastructure/observability/collector.yaml`
- `mcp/server/README.md`
- `scripts/.gitkeep`
- `scripts/smoke.py`

## Latest Windows setup status

The subsequent elevated installation succeeded for WSL 2.7.14. `wsl --version` confirms it. Docker Desktop is still incomplete: enabling VirtualMachinePlatform fails on pending Windows servicing operations, and the per-user installer refuses to proceed without that feature. A Windows restart is the next required recovery step; no restart has been executed by the agent.
