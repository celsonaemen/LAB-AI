# Vector database design

The validated native deployment uses PostgreSQL 18.6 with pgvector 0.8.7; the optional Compose configuration remains separate. PostgreSQL stores relational source metadata and 384-dimensional dense vectors together, supporting SQL filtering, foreign keys and transactional ingestion. The embedding model is fixed to `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; changing it requires explicit re-embedding/versioning, not mixing vectors.

## Versioned schema

`infrastructure/database/migrations/V001__knowledge_schema.sql` creates `knowledge.documents` and `knowledge.document_chunks`. Documents contain UUID, title, source, optional filename, JSON metadata, normalized content SHA-256, embedding model, chunk configuration, created_at and updated_at. Chunks contain UUID, document foreign key, unique ordinal per document, text, vector(384) and timestamp. A metadata GIN index and created-at index support filtering/listing; the unique (document_id, ordinal) index also serves foreign-key lookups.

`V002__knowledge_hnsw.sql` creates `document_chunks_embedding_hnsw` using `vector_cosine_ops`. Retrieval orders by `<=>` ascending and returns `1 - distance`. HNSW is approximate; filters can reduce returned result count and tiny corpora may use sequential scans. Benchmark EXPLAIN ANALYZE, recall and ef_search before making latency claims. No performance benchmark has been executed yet.

The original bootstrap `001-extensions.sql` / `002-knowledge.sql` are retained for compatibility with the initial draft. Their public-schema draft tables are not used by the new pipeline and are not dropped. The runtime's versioned migrations own the new schema. There is no claimed migration of historical data because no persisted corpus existed in the inspected repository.

## Migration execution

The runtime container executes `python -m app.migrate` before Uvicorn. It reads `/app/migrations`, acquires an advisory transaction lock, creates a checksummed `knowledge.schema_migrations` ledger, and applies each new immutable script in a transaction. A changed checksum fails startup. Repeated runs skip matching scripts. Existing volumes receive migrations on every runtime start; database init scripts alone are insufficient for upgrades.

Local execution from the repository root, after configuring DATABASE_URL privately:

```powershell
apps/ai-runtime/.venv/Scripts/python -m app.migrate
```

The runner accepts DATABASE_URL or standard PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD environment variables. Compose uses split variables to avoid URL password escaping. Never record the password in logs or commands checked into Git. The local Compose database initialization account can create extensions; production should separate migration privileges from the application role.

## Consistency

Document insertion and all chunk writes share one transaction. A uniqueness constraint over normalized content hash, model and chunk settings prevents duplicate rows under concurrent requests. Duplicate sources preserve the first document metadata. A new chunk configuration creates a distinct indexed representation. Metadata filtering is exact JSON containment and is scoped to this single-user demo; it does not provide row-level authorization.

No PostgreSQL success claim is valid until migrations and integration tests have executed against a running server. See the engineering log for actual local results and environment blockers.

Stage 1 executed those checks successfully against the isolated native cluster on 127.0.0.1:55432. See [validation evidence](../validation/stage-1-rag.md). Local trust authentication is limited to loopback development; it is not a production security configuration. Existing PostgreSQL services and databases were preserved.
