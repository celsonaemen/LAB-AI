# Stage 2 — native agent demonstration

Prerequisites: the Stage1 native PostgreSQL/pgvector, installed Python environment, .NET 10, Angular/Node24. No Docker, WSL, cloud API key or message broker is required for deterministic mode. Use only fictional data.

## Start

From repository root, use separate PowerShell terminals:

```powershell
./scripts/native.ps1 Database
# Terminal 1: applies versioned migrations and starts the runtime/worker
$env:AEGIS_LLM_PROVIDER = 'deterministic'
./scripts/native.ps1 Runtime
# Terminal 2
./scripts/native.ps1 Api
# Terminal 3
./scripts/native.ps1 Web
```

Open http://127.0.0.1:4200 and select the agents section. The knowledge section remains available. Select a workflow, type a request, choose the fictional balanced/concentrated portfolio, and optionally require approval before the report. The console shows agent states, timings, structured outputs and event/tool/evidence details. Deterministic reports are explicitly labeled as not LLM generated.

## HTTP proof and history

```powershell
apps/ai-runtime/.venv/Scripts/python.exe scripts/orchestrator_acceptance.py
# Exercise same-origin frontend proxy too:
apps/ai-runtime/.venv/Scripts/python.exe scripts/orchestrator_acceptance.py --base-url http://127.0.0.1:4200 --output .artifacts/orchestrator-proxy
```

The proof uploads a fictional knowledge document through .NET, runs all four agents with real local tools and RAG, pauses/approves, verifies durable SSE replay, runs document review and insufficient-evidence cases, cancels at the approval gate, checks terminal transition guards and history. It retains the demo documents/executions and writes `.artifacts/orchestrator/acceptance.json` (ignored by Git).

Manual request:

```powershell
$body = @{ task='Analise os riscos da carteira fictícia'; workflow='portfolio-review'; portfolioId='concentrated'; requireApproval=$true; metadataFilter=@{} } | ConvertTo-Json
$run = Invoke-RestMethod http://127.0.0.1:5080/api/v1/executions -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
Invoke-RestMethod "http://127.0.0.1:5080/api/v1/executions/$($run.id)" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:5080/api/v1/executions/$($run.id)/events?after=0" | ConvertTo-Json -Depth 20
# Once state is AwaitingApproval:
Invoke-RestMethod "http://127.0.0.1:5080/api/v1/executions/$($run.id)/approve" -Method Post
# For a nonterminal execution, cancellation is explicit:
# Invoke-RestMethod "http://127.0.0.1:5080/api/v1/executions/$($run.id)/cancel" -Method Post
Invoke-RestMethod http://127.0.0.1:5080/api/v1/executions
```

SSE is `/api/v1/executions/{id}/events/stream`; events are named `execution` and IDs are persisted sequence numbers. Reconnect with `Last-Event-ID`; terminal streams close. Closing the browser does not cancel a persisted execution.

## Optional real model provider

Ollama must be separately installed and a compatible model already available. Configure the runtime terminal before startup:

```powershell
$env:AEGIS_LLM_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = '<name of your installed model>'
./scripts/native.ps1 Runtime
```

The adapter calls Ollama's documented [`POST /api/chat`](https://docs.ollama.com/api/chat) with `stream:false`. Planning and tool permissions remain deterministic; only the final prose uses the model. The provider is recorded on each execution. The default path needs no key and does not perform LLM inference. No silent fallback is allowed when Ollama fails.

No Ollama executable/listener/model was found in the audited environment; real model inference must not be described as validated unless the Stage2 report explicitly records a later successful real call. Provider adapter tests with controlled responses are not evidence of actual model inference. Source references remain persisted tool results; model prose still requires human review.

This is a localhost single-user demonstration. Tool permissions do not replace user authentication/RBAC, and it is not suitable for public deployment.
