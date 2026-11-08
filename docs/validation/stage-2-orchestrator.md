# Stage 2 — Agent Orchestrator validation

Date: 2026-11-07. **Complete for the deterministic local demonstration.** Real HTTP requests through .NET and the Angular proxy executed four specialized agents, permission-controlled internal tools and actual RAG, with durable results/events, approval, cancellation and SSE replay. Actual Ollama inference is **not validated**; no model was installed/configured.

## Architecture and audit

Before implementation, read the Stage1 validation report, ADRs, API contracts, runtime/database implementation, .NET composition root and Angular application. [ADR 0003](../adr/0003-agent-orchestration.md) was written before code. It explicitly supersedes ADR0001's unimplemented plan to place execution state in .NET: Python now coordinates beside its existing persistence/RAG; .NET Domain validates public admission, Application defines typed ports, Infrastructure forwards JSON, API provides JSON/SSE. No existing execution implementation was replaced. The Stage1 routes and V001/V002 migrations remain intact.

The plan/ledger is [stage-2-orchestrator.md](../plans/stage-2-orchestrator.md); detailed diagrams, agent contracts and operational limits are in [agent architecture](../architecture/agent-orchestrator.md).

## Actual checks

| Check | Result |
|---|---|
| V003 migration on native PostgreSQL18/pgvector | Applied successfully; subsequent startup returned no pending migrations |
| Python full suite with real embeddings/native dedicated test database | **52 passed**, none skipped, one existing AnyIO deprecation warning; final run8.03s with external Ollama mode set to verify test isolation |
| .NET full suite | **38 passed**, including all17 Stage1 tests |
| Angular ChromeHeadless | **17 passed**, including all7 Stage1 tests |
| Angular production build | Passed,353.86kB initial /94.23kB estimated transfer |
| Agent acceptance through API5080 | **12 check categories passed**, four persisted runs |
| Same agent acceptance through web proxy4200 | **12 check categories passed**, four persisted runs |
| Stage1 real PDF regression after Stage2 | **13 check categories passed**, actual PDFs/384-dimensional vectors/PT+EN references |
| Stage1 smoke script | Six HTTP readiness/liveness/web/invalid-input checks passed |
| Browser | Actual create, live agent states, approval gate, approve, final result and named SSE requests verified; deterministic label visible; no console errors/warnings |
| Independent review | Three UI findings reproduced/fixed; scoped re-review found no remaining substantial issue |

The12 HTTP categories: four-agent order/dependencies, approval pause/resume, real tool execution, actual RAG source, durations/final result, persisted SSE replay/terminal closure, document workflow, insufficient evidence without fabrication, cancellation/terminal guards, persisted history/events, workflow allowlist, missing execution404.

Unit/native tests additionally cover tool permissions and schema rejection, tool fault with sanitized durable error, report-provider timeout without fallback, bounded operation timeout, cancellation inside a tool without later completion, restart recovery preserving Pending, history/replay, second-worker lock exclusion, provider misconfiguration, upstream error mappings, malformed DTOs and SSE cursor validation. Faults/timeouts in these tests are controlled injections; they are not claimed as real Ollama inference or live production outages.

## Concrete persisted evidence

Direct HTTP run:

| ID | Scenario | Final state | Events |
|---|---|---|---|
| `b17c2068-bd83-42e6-bf7d-6cc2229586dd` | Concentrated portfolio, approval | Completed |24|
| `c32dd9f9-796a-4d34-84b6-d400da82bd05` | Document review with matching evidence | Completed |19|
| `910f6996-edec-434d-a8d9-50b30a61f1de` | Document review with empty filter corpus | Completed, insufficient evidence |19|
| `961fdb45-be83-4fe1-b963-c41c0e7a8e59` | Cancel at approval gate | Cancelled |18|

The portfolio returned total fictional value100000BRL, largest weight0.85, HHI approximately0.735 and high concentration. These are deterministic calculations from the fixture, not market predictions. Data Agent retrieved document `93cda5e3-a4e4-47aa-b360-1d3b11379633`, chunk `e8b5a401-9e65-4b0c-9907-59d5aaef7591`, source `demo/stage2-credit.md`, cosine similarity approximately0.682368.

Proxy completed run: `160ead7e-d28d-48da-a804-6886bf977210`; proxy cancelled run: `8bf5b15b-adb2-40c2-bc02-c9f2d0fe0d60`. Full snapshots/events are in [direct evidence](stage-2-direct-evidence.json) and [proxy evidence](stage-2-proxy-evidence.json), using only fictional records. The acceptance script retains them for history inspection.

Browser run `89b0f0d1-0b9d-4a80-8390-f145d16e3e1a` visibly paused with the first three agents Completed and Report Pending, then completed after clicking **Aprovar relatório**. The UI displayed all four agents Completed, final structured analysis, `ExecutionCompleted`, and “Determinístico · relatório por regras, sem inferência de LLM.” A separate ungated browser run also completed. All observed execution requests used same-origin `/api/v1/executions` on4200.

Browser run `01a86461-068b-4f6f-870a-6d93b9048e44` was cancelled at the approval gate. The UI showed Cancelada, Report Agent Cancelled, and the final persisted `ExecutionCancelled` event, validating the review fix in the live application.

The Stage1 regression retained a real PDF document `12b13a13-70ba-48dc-ae49-d99bdd3e17e2`, with two credit chunks and an unrelated cafeteria document, verified at384 dimensions. The old unavailable-runtime scenario was not repeated in that particular regression invocation; .NET error mapping tests ran separately.

## Files created

- `apps/api/src/Aegis.Domain/ExecutionPolicy.cs`
- `apps/api/src/Aegis.Application/ExecutionContracts.cs`
- `apps/api/src/Aegis.Infrastructure/ExecutionRuntimeClient.cs`
- `apps/api/src/Aegis.Api/ExecutionEndpoints.cs`
- `apps/api/tests/Aegis.Api.Tests/ExecutionTests.cs`
- `apps/api/tests/Aegis.Api.Tests/ExecutionGatewayTests.cs`
- `apps/ai-runtime/app/api/executions.py`
- `apps/ai-runtime/app/executions/__init__.py`
- `apps/ai-runtime/app/executions/models.py`
- `apps/ai-runtime/app/executions/repository.py`
- `apps/ai-runtime/app/executions/tools.py`
- `apps/ai-runtime/app/executions/providers.py`
- `apps/ai-runtime/app/executions/worker.py`
- `apps/ai-runtime/tests/test_orchestration.py`
- `apps/ai-runtime/tests/test_execution_api.py`
- `apps/ai-runtime/tests/test_execution_store.py`
- `apps/web/src/app/executions.ts`
- `apps/web/src/app/executions.html`
- `apps/web/src/app/executions.css`
- `apps/web/src/app/executions.spec.ts`
- `infrastructure/database/migrations/V003__agent_executions.sql`
- `scripts/orchestrator_acceptance.py`
- `docs/adr/0003-agent-orchestration.md`
- `docs/plans/stage-2-orchestrator.md`
- `docs/architecture/agent-orchestrator.md`
- `docs/demo-orchestrator.md`
- `docs/validation/stage-2-orchestrator.md`
- `docs/validation/stage-2-direct-evidence.json`
- `docs/validation/stage-2-proxy-evidence.json`

## Existing files modified

- `.env.example` — explicit provider variables without credentials.
- `apps/api/src/Aegis.Api/Program.cs` — execution client/routes registration.
- `apps/ai-runtime/app/main.py` — worker lifecycle, execution routes, truthful provider health and V003 readiness.
- `apps/ai-runtime/tests/test_health.py` — explicitly selects deterministic mode for the retained default health test, independently of the developer's external provider configuration.
- `apps/web/src/app/app.ts`, `app.html`, `app.css` — agents section alongside the unchanged knowledge workflow.
- `README.md` — current delivery and demo/evidence links.
- `docs/adr/0001-hybrid-runtime.md` — explicit ownership amendment reference.
- `docs/architecture/overview.md` — implemented coordination diagram/boundaries.
- `docs/api/contracts.md` — active execution routes and obsolete-plan distinction.
- `docs/engineering-log/2026-11-07.md` — actual results/failures/resolutions.

Git still marks the initial scaffold untracked; this inventory distinguishes this stage's additions from edits to pre-existing files. No commit, push, public deployment, global installation, Docker/WSL action or user-data deletion occurred.

## Reproduction commands actually used

```powershell
# Existing native database, separate service terminals:
./scripts/native.ps1 Database
$env:AEGIS_LLM_PROVIDER='deterministic'
./scripts/native.ps1 Runtime
./scripts/native.ps1 Api
./scripts/native.ps1 Web

# Native tests; run from repository root:
$env:AEGIS_TEST_DATABASE_URL='postgresql://aegis_dev@127.0.0.1:55432/aegis_test'
$env:AEGIS_REAL_EMBEDDINGS='1'
$env:EMBEDDING_CACHE_DIR=Join-Path $env:LOCALAPPDATA 'AegisAgentLabNative/models'
apps/ai-runtime/.venv/Scripts/python.exe -m pytest apps/ai-runtime/tests -q --junitxml=.artifacts/stage2-python.xml
.tools/dotnet/dotnet.exe test apps/api/Aegis.slnx --no-restore --verbosity quiet
# Final repeat used --no-build because the verified API binary was already running.

apps/ai-runtime/.venv/Scripts/python.exe scripts/orchestrator_acceptance.py
apps/ai-runtime/.venv/Scripts/python.exe scripts/orchestrator_acceptance.py --base-url http://127.0.0.1:4200 --output .artifacts/orchestrator-proxy
$env:DATABASE_URL='postgresql://aegis_dev@127.0.0.1:55432/aegis'
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py --output .artifacts/stage2-rag-regression
apps/ai-runtime/.venv/Scripts/python.exe scripts/smoke.py

# From apps/web:
$env:CHROME_BIN='C:/Program Files/Google/Chrome/Application/chrome.exe'
npx.cmd --yes --package=node@24 -- node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless
npx.cmd --yes --package=node@24 -- node node_modules/@angular/cli/bin/ng.js build
```

Existing environments/packages/model cache were reused. [Demo instructions](../demo-orchestrator.md) include manual create/history/approve/cancel and optional provider setup.

## Failures resolved and limitations

- Auxiliary work was interrupted by a usage limit. The coordinator inspected saved partial files and resumed; no partial implementation was declared complete.
- .NET initially serialized absent metadata as null and rejected Skipped agent states. Regression tests failed first; serialization and state validation were fixed before HTTP acceptance.
- Review found stale action responses could change the selected run, cancellation could omit its final event, and in-flight refresh could hide AwaitingApproval. Tests reproduced these; generation guards, final-event retrieval and coalesced refresh fixed them. Independent re-review passed.
- Browser form automation expected option text rather than its HTML value. The first attempt used the balanced ungated flow; the subsequent correctly selected concentrated/approval run was separately verified. This was an automation input issue, not an application failure.
- **Real Ollama inference not tested.** Adapter supports configured endpoint/model with size/time bounds and no silent fallback. Deterministic output is explicitly labeled. Model prose is not guaranteed grounded; review it against persisted references.
- The worker is single-process/local-demo scope. A session advisory lock prevents ordinary concurrent ownership, not every network-partition scenario. Interrupted Running runs fail rather than automatically replaying side effects. Pending/approval survive.
- A45-second operation timeout stops waiting, not the native thread. One outstanding read-only slot limits accumulation; a hung operation can make subsequent runs fail until it returns/restart. Process isolation remains future work.
- No user authentication/RBAC, production quotas, event retention, process sandbox or telemetry exporter. Tool capabilities are server checks, not tenant security.
- Python retains one dependency deprecation warning. Earlier Angular development dependency audit findings remain outside scope; no fresh clean security-audit claim is made.
- No autonomous LLM planning, MCP server or messaging broker; these were intentionally excluded. The fixed agent responsibilities and real tool/RAG operations are verifiable in the event trace.
