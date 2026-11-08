# Stage 1 — real HTTP RAG validation

Date: 2026-11-07. Result: the required PDF -> .NET -> FastAPI -> real FastEmbed -> native PostgreSQL/pgvector -> semantic retrieval path **passed**. No embedding or storage mock was used in HTTP acceptance. No push/publication was performed.

## Audit before modification

Inspected the repository tree, architecture overview, RAG/vector design, ADR 0002, service contracts, README, .NET composition root/client/DTOs/endpoints/tests, Python extraction/store/model configuration/tests, Angular scaffold/proxy, environment template and native database readiness. Work remained in the existing `chore/architecture-bootstrap` checkout: the repository still has an uncommitted initial scaffold, so no alternate empty worktree or monorepo was created.

Existing four knowledge routes were retained. .NET's typed HttpClient forwards to `/internal/v1/knowledge` with a 120-second timeout; Python owns extraction, embeddings and persistence. Database connection comes from runtime environment, not Angular. Native PostgreSQL 18.6 with pgvector 0.8.7 was confirmed at 127.0.0.1:55432, separate from pre-existing PostgreSQL installations/databases.

Gaps found: generated Angular page had no knowledge flow; .NET checked encoded length but not file extension/decoded length; valid JSON with missing response fields could silently deserialize; ingestion receipt lacked stored metadata/status; no repeatable full HTTP proof. These were addressed without new routes, schema changes, agents, MCP or messaging.

## Executed verification

| Check | Actual result |
|---|---|
| `native.ps1 Database` | PostgreSQL 18.6, pgvector 0.8.7, existing cluster healthy |
| `native.ps1 Runtime` | Migrations returned `[]` (already applied), real model warmed to 384 dimensions, Uvicorn started |
| `native.ps1 Api` / `native.ps1 Web` | Both started successfully with existing dependencies |
| `native.ps1 Check` | Runtime and API readiness 200 |
| Python pytest with real embeddings and dedicated native test DB | **37 passed**, none skipped, one Starlette/AnyIO deprecation warning |
| .NET test suite | **17 passed**; initial regression run had 2 failing incomplete-response tests, then passed after fix |
| Angular ChromeHeadless | **7 passed**, including retained creation/title checks and upload/search/error cases |
| Angular production build via Node 24 | Passed; initial bundle 314.27 kB |
| HTTP acceptance against public API :5080 | All 14 check categories passed |
| HTTP acceptance through Angular proxy :4200 | All 14 check categories passed |
| `scripts/smoke.py` | Six HTTP checks passed: liveness/readiness, web, invalid-input public/proxy responses |
| Manual PowerShell PDF upload/search commands | Passed: duplicate receipt preserved corpus metadata and returned S1/S2 source references |
| Real browser | Search displayed persisted excerpts/sources; network showed POST same-origin `/api/v1/knowledge/search` 200; no console errors/warnings |
| Narrow browser layout | Effective viewport 500px, content width 485px, no horizontal overflow; desktop screenshot inspected |
| Independent code review | No blocking findings; timeout/browser-upload evidence limits recorded below |

The 14 categories cover PDF ingestion, duplicate metadata preservation, details, extraction in PostgreSQL, actual dimensions, chunk counts, Portuguese retrieval, English retrieval, verified source references, insufficient evidence, missing document 404, invalid PDF 400, unsupported extension 400, and actual refused runtime connection 503.

## Persisted evidence

Direct API run: credit document `9fdf5f01-b6c2-4bc3-9221-a053edb91e3a`, cafeteria document `61f0ed7c-5729-476f-b78a-4936e4d801c2`. Three chunks total, each vector dimension verified by SQL. The best credit chunk was `8177b664-300d-4a38-9134-be784d7da661`, source `demo/credit-policy.pdf`; scores approximately 0.692357 (Portuguese) and 0.691235 (English).

Proxy run: credit document `74662dfd-8161-4f4e-9a70-e42a9b00bdc1`, cafeteria document `91d73abf-3cbf-4f7d-b4e5-71a71ba4e9f4`; three chunks, 384 dimensions. Each reported reference was checked against the chunk/document IDs, original content and source of a returned persisted hit. Duplicate ingestion reused the ID and original metadata even when the repeated request supplied different metadata.

Full fictional responses are preserved in [direct API evidence](stage-1-direct-evidence.json) and [proxy evidence](stage-1-proxy-evidence.json). Generated PDFs and rerunnable result files live under ignored `.artifacts/`. No credentials are included. Small-corpus scores demonstrate integration, not a retrieval benchmark or financial recommendation.

## Exact stage file inventory

Modified existing files:

- `.gitignore` — ignore generated acceptance artifacts.
- `README.md` — native start path, current delivered behavior and evidence links.
- `apps/api/src/Aegis.Api/KnowledgeEndpoints.cs` — file validation at public boundary.
- `apps/api/src/Aegis.Infrastructure/KnowledgeRuntimeClient.cs` — required/non-null upstream DTO fields.
- `apps/api/src/Aegis.Application/KnowledgeContracts.cs` — additive receipt status/metadata.
- `apps/api/tests/Aegis.Api.Tests/KnowledgeClientTests.cs` — incomplete responses and timeout mapping.
- `apps/api/tests/Aegis.Api.Tests/KnowledgeTests.cs` — extension, base64, decoded size validation.
- `apps/ai-runtime/app/api/knowledge.py` — receipt response fields.
- `apps/ai-runtime/app/rag/store.py` — original persisted metadata in duplicate receipts.
- `apps/web/src/app/app.ts` — typed upload/search component, validation and states.
- `apps/web/src/app/app.html` — document/search forms and source results.
- `apps/web/src/app/app.css` — responsive knowledge screen styles.
- `apps/web/src/app/app.config.ts` — HttpClient provider.
- `apps/web/src/app/app.spec.ts` — preserved original tests plus knowledge UI tests.
- `apps/web/src/styles.css` — page defaults.
- `apps/web/src/index.html` — Portuguese language and product title.
- `docs/architecture/overview.md` — implemented runtime/database boundary.
- `docs/architecture/rag-pipeline.md` — stage decisions and evidence links.
- `docs/architecture/vector-database.md` — actual native version and validation.
- `docs/api/contracts.md` — receipts, errors, limits and routes.
- `docs/engineering-log/2026-11-07.md` — commands, findings and results.

Created:

- `scripts/native.ps1` — foreground native service startup and readiness.
- `scripts/rag_acceptance.py` — real PDF fixture generation and HTTP/database assertions.
- `docs/demo-rag.md` — reproducible PowerShell walkthrough.
- `docs/validation/stage-1-rag.md` — this report.
- `docs/validation/stage-1-direct-evidence.json` — captured real response evidence.
- `docs/validation/stage-1-proxy-evidence.json` — captured real proxy response evidence.

The repository has no committed baseline yet, so Git labels initial files untracked; this inventory distinguishes modifications to existing files from new stage artifacts. Existing user-provided saved vacancy HTML/assets were not edited.

## Commands

See [demonstration](../demo-rag.md) for complete startup/manual upload/search commands. Verification commands actually executed:

```powershell
.tools/dotnet/dotnet.exe test apps/api/Aegis.slnx --no-restore --verbosity quiet
$env:AEGIS_TEST_DATABASE_URL='postgresql://aegis_dev@127.0.0.1:55432/aegis_test'
$env:AEGIS_REAL_EMBEDDINGS='1'
$env:EMBEDDING_CACHE_DIR=Join-Path $env:LOCALAPPDATA 'AegisAgentLabNative/models'
apps/ai-runtime/.venv/Scripts/python.exe -m pytest apps/ai-runtime/tests -q
$env:DATABASE_URL='postgresql://aegis_dev@127.0.0.1:55432/aegis'
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py --unavailable-api http://127.0.0.1:5081
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py --base-url http://127.0.0.1:4200 --output .artifacts/rag-proxy --unavailable-api http://127.0.0.1:5081
apps/ai-runtime/.venv/Scripts/python.exe scripts/smoke.py
# From apps/web, using CHROME_BIN set to the installed Chrome:
npx.cmd --yes --package=node@24 -- node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless
npx.cmd --yes --package=node@24 -- node node_modules/@angular/cli/bin/ng.js build
```

No new dependency or global package installation was required. Existing model cache, virtual environment and SDK were reused; Node 24 was invoked through the existing npx workflow.

## Limitations

- Browser automation denied local file selection because its configured workspace roots did not include this repository. Actual HTTP PDF upload was verified directly and through the web proxy; Angular file reading/receipt rendering was tested with HttpTestingController. The browser file-picker-to-backend interaction has **not** been fully automated. Browser search was real.
- 504 timeout and invalid upstream JSON are covered by controlled .NET tests, not delayed/corrupted live runtime experiments. Live refused connection 503 was exercised using a second .NET instance pointing to unused port 8001.
- Local single-user demo only: no auth/RBAC, rate limiting, hardened PDF sandbox, production deployment or Docker validation. Native trust authentication is loopback development configuration.
- PDF text only, no OCR/page-level citation; character chunking may truncate model input. No broad retrieval relevance/performance benchmark.
- One Python deprecation warning remains. Earlier npm audit reported 16 moderate development-tool findings; dependency remediation was outside this stage and no clean audit is claimed.
- No LLM answers, agents, MCP or messaging. Next engineering work should address access controls, PDF robustness and retrieval evaluation before public deployment.
