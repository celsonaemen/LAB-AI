# Native RAG demonstration — PowerShell

Run from the repository root. Requires the existing isolated PostgreSQL 18 cluster at `$env:LOCALAPPDATA/AegisAgentLabNative`, pgvector 0.8.7, the installed Python virtual environment, .NET 10 SDK and Node 24. The helper uses the project-local SDK when available. It never initializes/replaces a database. On another machine install the prerequisites and configure your own PostgreSQL connection; the local cluster and model cache are not committed.

## Start services

```powershell
./scripts/native.ps1 Database
# Terminal 1: applies migrations, warms the real model, starts FastAPI
./scripts/native.ps1 Runtime
# Terminal 2
./scripts/native.ps1 Api
# Terminal 3
./scripts/native.ps1 Web
# Terminal 4
./scripts/native.ps1 Check
```

Open http://127.0.0.1:4200. Runtime 8000, public API 5080, PostgreSQL 55432. Stop foreground services with Ctrl+C. Do not terminate the existing database during requests. No Docker or WSL command is required.

## Reproduce the complete proof

```powershell
$env:DATABASE_URL = 'postgresql://aegis_dev@127.0.0.1:55432/aegis'
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py
# Include Angular's same-origin development proxy:
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py --base-url http://127.0.0.1:4200 --output .artifacts/rag-proxy
```

This creates actual fictional PDFs in `.artifacts/rag`, sends their bytes through .NET, verifies real extracted text and vector dimensions in PostgreSQL, queries in Portuguese and English, checks references against persisted chunks, tests duplicates/original metadata, invalid files, missing documents and insufficient evidence. Each run uses a new corpus identifier and leaves its fictional documents available for inspection. It does not delete data. Full responses are in `.artifacts/rag/acceptance.json`; generated artifacts are ignored by Git.

## Manual PDF upload and search

After the proof generated the PDF:

```powershell
$pdf = (Resolve-Path .artifacts/rag/credit-policy.pdf).Path
$payload = @{
    title = 'Política de crédito fictícia'
    source = 'demo/credit-policy.pdf'
    filename = 'credit-policy.pdf'
    contentBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($pdf))
    metadata = @{ area = 'demo' }
} | ConvertTo-Json -Depth 5
$receipt = Invoke-RestMethod http://127.0.0.1:5080/api/v1/knowledge/documents -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
$receipt | ConvertTo-Json -Depth 5
# Duplicate ingestion preserves the original corpus metadata:
$document = Invoke-RestMethod "http://127.0.0.1:5080/api/v1/knowledge/documents/$($receipt.documentId)"
$query = @{ query = 'Como reduzir o risco de crédito?'; top_k = 3; minScore = 0.35; metadataFilter = @{ corpus = $document.metadata.corpus } } | ConvertTo-Json -Depth 5
$result = Invoke-RestMethod http://127.0.0.1:5080/api/v1/knowledge/search -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($query))
$result.results | Select-Object documentId,chunkId,source,score,content | Format-List
$result.context.references | Format-Table
```

For UI demonstration select the same PDF, enter a title/source, click **Adicionar à base**, then search. A duplicate receipt is expected after the automated proof. The original source label is retained. Search evidence is not an LLM answer.

## Real unavailable-runtime scenario

In an extra terminal, ensure port 8001 has no listener, then start a separate .NET process (the working API is untouched):

```powershell
$env:AiRuntime__BaseUrl = 'http://127.0.0.1:8001'
.tools/dotnet/dotnet.exe apps/api/src/Aegis.Api/bin/Debug/net10.0/Aegis.Api.dll --urls http://127.0.0.1:5081
```

In the verification terminal:

```powershell
apps/ai-runtime/.venv/Scripts/python.exe scripts/rag_acceptance.py --unavailable-api http://127.0.0.1:5081
```

The script asserts a real HTTP 503 Problem Details response from the second .NET instance. Stop that process with Ctrl+C afterward. Timeout and invalid upstream JSON are separately tested by controlled .NET tests; these are not represented as real-runtime fault injections.
