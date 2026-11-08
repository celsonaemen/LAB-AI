CREATE TABLE IF NOT EXISTS knowledge_documents (
    id uuid PRIMARY KEY,
    title varchar(200) NOT NULL,
    source varchar(500) NOT NULL,
    content_hash char(64) NOT NULL,
    model varchar(200) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_hash, model)
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    content text NOT NULL,
    embedding vector(384) NOT NULL,
    UNIQUE (document_id, ordinal)
);

-- Exact cosine nearest-neighbor search is intentional for the demo corpus.
-- Add an ANN index only after measuring recall and latency with realistic data.
