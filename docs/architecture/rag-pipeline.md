# Document ingestion and semantic retrieval

## Implemented flow

```mermaid
sequenceDiagram
  participant C as HTTP client / Angular
  participant A as .NET API
  participant P as Python runtime
  participant E as FastEmbed / ONNX
  participant D as PostgreSQL / pgvector
  C->>A: POST /api/v1/knowledge/documents
  A->>A: Check input sizes and typed contract
  A->>P: Internal typed HTTP request
  P->>P: Extract, normalize, chunk, hash
  P->>E: Batch embed chunks
  E-->>P: 384-dimensional vectors
  P->>D: Atomic document + chunk insert / duplicate lookup
  D-->>C: Document receipt via Python and .NET
  C->>A: POST /api/v1/knowledge/search
  A->>P: Query, top_k, metadata filters, limits
  P->>E: Embed query using same model
  P->>D: Cosine distance search + metadata filter
  P->>P: Assemble bounded untrusted evidence context
  P-->>C: Hits, scores, source references; no generated answer
```

## API examples

All public endpoints are under .NET. Python's internal routes are not published by Compose. No frontend database driver or connection string is used.

`POST /api/v1/knowledge/documents` (JSON):

```json
{
  "title": "Fictional credit policy",
  "source": "demo/credit-policy.md",
  "text": "A política fictícia exige revisão das garantias quando aumenta a inadimplência da carteira.",
  "metadata": {"area": "risk", "language": "pt"},
  "chunkSize": 350,
  "chunkOverlap": 60
}
```

For files replace `text` with `filename` and `contentBase64`. Supported extensions: `.pdf`, `.txt`, `.md`, `.markdown`. TXT/Markdown must be UTF-8. The ingestion response returns `documentId`, `chunks`, `deduplicated`, model id, `status: "indexed"`, and persisted `metadata`. Duplicates return the existing document id and original metadata; the first source remains authoritative. The operation is synchronous: a successful receipt is emitted after commit, not when a job is merely queued.

`GET /api/v1/knowledge/documents?limit=20&offset=0` returns metadata with chunk counts and timestamps, without raw embedding vectors. `GET /api/v1/knowledge/documents/{uuid}` returns one document or 404.

`POST /api/v1/knowledge/search`:

```json
{
  "query": "Como lidar com o aumento do risco de crédito?",
  "top_k": 5,
  "minScore": 0.35,
  "metadataFilter": {"area": "risk"},
  "maxContextChars": 6000
}
```

`limit` remains a compatibility alias for top_k; top_k takes precedence if both are provided. Result count is 1..20. Scores are cosine similarity in [-1,1], not probabilities or calibrated confidence. Filters use exact JSON containment and are not an authorization mechanism. `minScore` defaults to 0; choose a threshold for the dataset before treating evidence as relevant.

Each hit includes documentId, chunkId, ordinal, content, title, source, filename, metadata, and score. Context includes only references to excerpts that fit its 200..12000 character budget. Empty hits or no fitting excerpts produce `insufficient_evidence` with empty references. `generatedAnswer` is always null; retrieval and LLM generation are explicitly distinct.

## Processing and failures

NFKC normalization, normalized line endings and collapsed horizontal whitespace precede SHA-256 hashing and configurable overlapping character chunks. Embeddings are generated locally by FastEmbed using the fixed multilingual MiniLM model; batch size 16, CPU threads 2, persistent model cache. Validate count, 384 dimensions, finite values and nonzero norm before persistence. First use downloads weights and may take longer than a warm request; prewarm before the demo with `python -c "from app.rag.embeddings import embed; embed(['warmup'])"`.

The gateway caps requests at 3 MB and upstream buffers at 4 MB, validates text/file/metadata bounds, and waits up to 120 seconds. Runtime connection timeout is 3 seconds and SQL statement timeout 10 seconds. Invalid input yields 400 at .NET / 422 internally; missing document 404; unavailable database/model 503; invalid upstream response 502; upstream timeout 504. Exceptions and credentials are not returned to clients.

## Security limits

The current API is a localhost single-user demo without authentication, RBAC or tenant isolation. Source names are labels, never remotely fetched. SQL is parameterized. No model inference occurs in the browser. Retrieved excerpts are untrusted JSON strings; citations come from actual database rows, not a language model. Prompt injection resistance is a context design measure, not a security guarantee. Production requires authenticated internal calls, hardened PDF isolation, rate limits, ownership policy and model artifact verification.

## Validation

Unit tests use deterministic vectors and controlled store boundaries. Opt-in tests use real multilingual weights for Portuguese/English ranking. PostgreSQL integration tests require `AEGIS_TEST_DATABASE_URL` pointing at a dedicated disposable pgvector database; they apply migrations, test repeatability, persistence, duplicates, ranking and clean up only their own rows. Their status must be read separately from unit/model tests.

## Stage 1 integration decisions

- Retain the existing base64 JSON upload contract; no duplicate multipart endpoint or service was added. Angular uses same-origin `/api`, which is forwarded to .NET by its proxy.
- Validate extension, base64 and decoded 2,000,000-byte maximum at .NET; Python still validates file contents and performs extraction. Angular mirrors the file bound for early feedback.
- Require non-null, required constructor fields when decoding runtime responses in .NET. Previously `{}` could deserialize as a success DTO with null/default fields; a regression test reproduced this before the fix. Malformed/incomplete response maps to 502; transport failure 503; timeout 504.
- Add status and stored metadata to the existing receipt without removing fields. Duplicate receipt metadata is selected from the original database document, not copied from the new request.
- Retain character chunking, model, schema and HNSW migrations. No re-embedding migration is needed.
- Use native services and foreground PowerShell commands for reproducibility; no Docker/WSL changes. The engineering acceptance script verifies source rows and vector dimensions directly, while application browser traffic still uses only .NET.

See [Stage 1 validation](../validation/stage-1-rag.md) and [demo commands](../demo-rag.md). The small fictional corpus verifies integration, not general retrieval quality or HNSW performance.
