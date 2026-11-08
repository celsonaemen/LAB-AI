# Architecture Bootstrap Implementation Plan

Goal: create the approved monorepo foundation without implementing the complete product.

Architecture: Angular calls the .NET composition root. Application ports isolate an internal Python runtime. PostgreSQL is prepared for later persistence.

Spec: ../architecture/overview.md

## Tasks

- [x] Initialize Git on a bootstrap branch and generate strict Angular routing application in apps/web.
- [x] Create net10.0 solution and Domain/Application/Infrastructure/API references and HTTP health integration tests.
- [x] Create Python package and health contract test before FastAPI health handler; install dependencies into project-local virtual environment.
- [x] Define versioned runtime request/response JSON schema, ownership and error semantics in docs/api.
- [x] Add container builds, same-origin reverse proxy, database initialization and health checks. Require a database password from the environment.
- [x] Build Angular and .NET, run runtime and API tests, validate Compose configuration with the copied Compose binary, and record limitations.
- [x] Expanded scope: implement document extraction, multilingual embeddings, knowledge gateway, source context and versioned pgvector/HNSW migrations.
- [ ] Execute migrations and PostgreSQL integration tests against a running server; blocked by Windows Docker/WSL installation failure.
- [ ] Build and start all containers; requires the same environment repair.

Verification commands: dotnet test apps/api/Aegis.slnx; apps/ai-runtime/.venv/Scripts/python -m pytest apps/ai-runtime/tests; npm --prefix apps/web run build; docker compose config --quiet.
