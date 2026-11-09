# Local privacy hardening

Date: 2026-11-08 (America/Sao_Paulo).

## Scope and design

The requested operating model is internal inference with synthetic data while bank security requirements are developed. This bounded change closes concrete outbound paths in the existing architecture. It does not introduce a new RAG, agent service, encryption format or identity provider.

Use a numeric loopback origin for the model, bypass proxies, reject redirects, require cached embeddings, disable browser voice and sanitize validation errors. Existing typed APIs, tool authorization and RAG are preserved. This intentionally prevents remote Ollama endpoints. A future remote internal model gateway needs a separate explicit destination policy and authenticated TLS design. LM Studio is not integrated by this change.

Alternatives considered: relying only on operator environment variables (insufficient protection against proxy/URL mistakes); adding an application-wide monkey-patched network sandbox (fragile and does not contain native libraries/subprocesses); introducing a new network proxy (unnecessary for this code patch). Production still needs an infrastructure egress policy.

## Reproduced failures before changes

- Python privacy suite: 19 failed, 5 passed. Tests demonstrated unvalidated model destinations, use of a configured local test proxy, rejected-value reflection and missing offline constructor enforcement.
- Browser privacy test: failed because synthesis/recognition were enabled.
- .NET redirect test: failed because a 302 was followed and returned the destination's 200.

All transport probes used synthetic strings and loopback listeners. Invalid remote addresses were intercepted before transport in tests. No real customer data or real external recipient was used.

## Verification

Executed results:

- Focused Python privacy/tool-calling/orchestration regression: 39 passed.
- Full Python regression with existing native pgvector test database, real embeddings opt-in and the pre-provisioned offline cache: 107 passed, 1 third-party Starlette/AnyIO deprecation warning, 66.23 seconds.
- Full .NET regression: 55 passed, 0 failed, 0 skipped. Includes a real loopback HTTP request proving the typed knowledge client receives the runtime credential while an unrelated client does not.
- Angular regression: 25 passed, 0 failed.
- Angular production build: passed; initial bundle 377.42 kB, estimated transfer 98.89 kB.

Model/network transport fixtures prove request routing, not real model inference. Real FastEmbed/pgvector tests remain separately identifiable by their opt-in variables.

```powershell
# From apps/ai-runtime:
.\.venv\Scripts\python.exe -m pytest tests/test_local_privacy.py tests/test_tool_calling.py tests/test_orchestration.py -q --tb=short

# Full real-model and native pgvector regression, using an existing test database:
$env:AEGIS_TEST_DATABASE_URL = '<existing isolated test database DSN>'
$env:AEGIS_REAL_EMBEDDINGS = '1'
$env:EMBEDDING_CACHE_DIR = (Resolve-Path '..\..\.model-cache').Path
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -m pytest -q --tb=short

# From repository root:
.tools\dotnet\dotnet.exe test apps/api/Aegis.slnx --nologo --no-restore

# From apps/web:
npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

The cache must already contain the multilingual 384-dimensional model. The runtime fails if artifacts are missing; it no longer downloads them. No dependencies were installed for this change.

## Explicit exclusions

No host firewall, network segmentation, TLS certificates, production database grants, at-rest encryption, corporate IdP, key management, backup policy or model-server configuration was changed. The running services need a controlled restart/rebuild to use the changes. A real Ollama/LM Studio inference and host-wide traffic capture were not performed. Existing generic document/execution access and MCP list/get/history remain workspace-level rather than per-customer boundaries.

The security model and blocking production gaps are documented in `../security/threat-model.md`. “Impenetrable”, “zero leakage”, “bank certified” and unspecified “SPICE” compliance are not validated outcomes.
