# ADR 0002: local multilingual embeddings with pgvector

Status: Accepted, 2026-11-07.

The user expanded the foundation scope to include vector persistence, embeddings, semantic search and a public development narrative.

Use FastEmbed with sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, 384 dimensions, running locally on CPU via ONNX. No paid API key is required. Model files are downloaded on first use and cached; initial use requires outbound network access. Unlike the future deterministic agent provider, this is a real embedding model.

Store document title, source label, JSON metadata, content hash and text chunks with model id in PostgreSQL's knowledge schema. Retrieve by cosine distance through pgvector. The approved expanded scope explicitly requires an HNSW cosine index, provided by V002; it trades recall for throughput and must be benchmarked as the corpus grows. PostgreSQL may choose exact scans for small tables. Enforce a fixed model id/dimension and avoid mixing incompatible embedding spaces. This supersedes the earlier bootstrap choice to defer HNSW.

Alternative: external embedding APIs simplify CPU setup but introduce credentials, cost and data egress. Hash-based text vectors work for lexical similarity but would not demonstrate semantic understanding. A dedicated vector database adds an unnecessary service for the first corpus.

Keep ingestion and retrieval behind .NET's public API. Accept JSON plain text or base64-encoded PDF/TXT/Markdown; sources are labels and never fetched as URLs. Base64 JSON keeps one typed gateway contract without multipart forwarding at the cost of roughly 33% transfer overhead. The demo limits files to 2 MB and extracted text to 20,000 characters. Bootstrap remains a single-user localhost demo without JWT/RBAC. Do not describe it as tenant-isolated or production-ready. The database adapter uses parameterized SQL and atomic writes. Identical normalized content, model id and chunk configuration are idempotent; the original source/metadata are retained on duplicate ingestion. Different content creates a new document version.

Chunk sizes are character-based (default 350 with 60 overlap), bounded to 50..1500 characters and overlap below size. This keeps configuration easy to inspect. The tokenizer may truncate unusually dense or large configured chunks; token-aware chunking is a future improvement. PDF extraction uses pypdf, preserves extracted text order and rejects encrypted/image-only documents; OCR is outside scope. Markdown is indexed as text, including headings.

RAG context is retrieval-only: reference labels are constructed from actual selected chunks, excerpts are JSON-escaped and labeled untrusted, and insufficient evidence yields no citations or generated answer. This reduces delimiter/instruction confusion but cannot guarantee protection against every prompt injection. A future LLM layer must enforce tool authorization and output grounding separately.

Sources: [FastEmbed models](https://qdrant.github.io/fastembed/examples/Supported_Models/), [pgvector distance operators](https://github.com/pgvector/pgvector), [Psycopg installation](https://www.psycopg.org/install/).
