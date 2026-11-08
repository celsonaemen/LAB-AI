CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE TABLE knowledge.documents (
    id uuid PRIMARY KEY,
    title varchar(200) NOT NULL,
    source varchar(500) NOT NULL,
    filename varchar(255),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    content_hash char(64) NOT NULL,
    embedding_model varchar(200) NOT NULL,
    chunk_size integer NOT NULL CHECK (chunk_size BETWEEN 50 AND 1500),
    chunk_overlap integer NOT NULL CHECK (chunk_overlap >= 0 AND chunk_overlap < chunk_size),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_hash, embedding_model, chunk_size, chunk_overlap)
);
CREATE TABLE knowledge.document_chunks (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES knowledge.documents(id) ON DELETE CASCADE,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    content text NOT NULL CHECK (length(content) > 0),
    embedding vector(384) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, ordinal)
);
CREATE INDEX documents_metadata_gin ON knowledge.documents USING gin(metadata jsonb_path_ops);
CREATE INDEX documents_created_at ON knowledge.documents (created_at DESC, id);
