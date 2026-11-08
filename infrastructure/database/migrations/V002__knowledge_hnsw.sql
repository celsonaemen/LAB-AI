CREATE INDEX document_chunks_embedding_hnsw
ON knowledge.document_chunks USING hnsw (embedding vector_cosine_ops);
