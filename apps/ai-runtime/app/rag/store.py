import hashlib
import os
import json
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.rag.knowledge import MODEL, validate_vector


class KnowledgeUnavailable(Exception):
    pass


def _connect():
    dsn = os.getenv("DATABASE_URL")
    if not dsn and not os.getenv("PGHOST"):
        raise KnowledgeUnavailable("Knowledge database is not configured")
    return psycopg.connect(dsn or "", connect_timeout=3, options="-c statement_timeout=10000", row_factory=dict_row)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in validate_vector(vector)) + "]"


def database_ready() -> bool:
    try:
        with _connect() as connection:
            row = connection.execute(
                "SELECT count(*)=2 AND to_regclass('knowledge.documents') IS NOT NULL "
                "AND to_regclass('knowledge.document_chunks') IS NOT NULL AS ready "
                "FROM knowledge.schema_migrations WHERE version IN "
                "('V001__knowledge_schema.sql','V002__knowledge_hnsw.sql')"
            ).fetchone()
            return bool(row["ready"])
    except (psycopg.Error, KnowledgeUnavailable):
        return False


def save_document(title: str, source: str, text: str, chunks: list[str], vectors: list[list[float]],
                  metadata: dict | None = None, filename: str | None = None,
                  chunk_size: int = 350, chunk_overlap: int = 60) -> dict:
    if len(chunks) != len(vectors) or not chunks:
        raise ValueError("Chunks and embeddings must have matching nonzero counts")
    document_id = uuid4()
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    with _connect() as connection:
        # Conflict handling serializes concurrent ingestion of identical content.
        row = connection.execute(
            "INSERT INTO knowledge.documents (id,title,source,content_hash,embedding_model,metadata,filename,chunk_size,chunk_overlap) "
            "VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s) "
            "ON CONFLICT (content_hash,embedding_model,chunk_size,chunk_overlap) DO NOTHING RETURNING id",
            (document_id, title, source, digest, MODEL, json.dumps(metadata or {}), filename, chunk_size, chunk_overlap),
        ).fetchone()
        if row is None:
            existing = connection.execute(
                "SELECT d.id, d.metadata, count(c.id) AS chunks FROM knowledge.documents d "
                "JOIN knowledge.document_chunks c ON c.document_id = d.id "
                "WHERE d.content_hash=%s AND d.embedding_model=%s AND d.chunk_size=%s AND d.chunk_overlap=%s GROUP BY d.id",
                (digest, MODEL, chunk_size, chunk_overlap),
            ).fetchone()
            return {"documentId": str(existing["id"]), "chunks": existing["chunks"], "deduplicated": True, "model": MODEL,
                    "status": "indexed", "metadata": existing["metadata"]}
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO knowledge.document_chunks (id, document_id, ordinal, content, embedding) VALUES (%s, %s, %s, %s, %s::vector)",
                [(uuid4(), document_id, index, chunk, _vector_literal(vector))
                 for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))],
            )
    return {"documentId": str(document_id), "chunks": len(chunks), "deduplicated": False, "model": MODEL,
            "status": "indexed", "metadata": metadata or {}}


def search(vector: list[float], limit: int, min_score: float, metadata_filter: dict | None = None) -> list[dict]:
    if not 1 <= limit <= 20 or not -1 <= min_score <= 1:
        raise ValueError("Invalid search bounds")
    literal = _vector_literal(vector)
    with _connect() as connection:
        rows = connection.execute(
            "SELECT c.id AS chunk_id, d.id AS document_id, d.title, d.source, d.metadata, d.filename, c.ordinal, c.content, "
            "1 - (c.embedding <=> %s::vector) AS score "
            "FROM knowledge.document_chunks c JOIN knowledge.documents d ON d.id = c.document_id "
            "WHERE d.embedding_model = %s AND d.metadata @> %s::jsonb AND 1 - (c.embedding <=> %s::vector) >= %s "
            "ORDER BY c.embedding <=> %s::vector, c.id LIMIT %s",
            (literal, MODEL, json.dumps(metadata_filter or {}), literal, min_score, literal, limit),
        ).fetchall()
    return [{"chunkId": str(row["chunk_id"]), "documentId": str(row["document_id"]),
             "title": row["title"], "source": row["source"], "ordinal": row["ordinal"],
             "metadata": row["metadata"], "filename": row["filename"],
             "content": row["content"], "score": max(-1.0, min(1.0, float(row["score"])))} for row in rows]


def list_documents(limit: int = 20, offset: int = 0) -> list[dict]:
    if not 1 <= limit <= 100 or not 0 <= offset <= 100000:
        raise ValueError("Invalid pagination bounds")
    with _connect() as connection:
        rows = connection.execute(
            "SELECT d.*, (SELECT count(*) FROM knowledge.document_chunks c WHERE c.document_id=d.id) AS chunks "
            "FROM knowledge.documents d ORDER BY d.created_at DESC,d.id LIMIT %s OFFSET %s", (limit, offset),
        ).fetchall()
    return [_document(row) for row in rows]


def get_document(document_id: str) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT d.*, (SELECT count(*) FROM knowledge.document_chunks c WHERE c.document_id=d.id) AS chunks "
            "FROM knowledge.documents d WHERE d.id=%s::uuid", (document_id,),
        ).fetchone()
    return _document(row) if row else None


def _document(row: dict) -> dict:
    return {"documentId": str(row["id"]), "title": row["title"], "source": row["source"],
            "filename": row["filename"], "metadata": row["metadata"], "contentHash": row["content_hash"],
            "model": row["embedding_model"], "chunks": row["chunks"], "chunkSize": row["chunk_size"],
            "chunkOverlap": row["chunk_overlap"], "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat()}
