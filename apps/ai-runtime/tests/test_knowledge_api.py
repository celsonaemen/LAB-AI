import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import embeddings, store
from app.rag.knowledge import validate_vector

client = TestClient(app)


@pytest.mark.parametrize("text", ["", "  ", "a" * 20001])
def test_document_validation_rejects_blank_or_oversized_text(text):
    response = client.post("/internal/v1/knowledge/documents", json={"title": "Policy", "source": "demo.txt", "text": text})
    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{"query": " "}, {"query": "risk", "limit": 21}, {"query": "risk", "minScore": 2}])
def test_search_validates_input_bounds(payload):
    assert client.post("/internal/v1/knowledge/search", json=payload).status_code == 422


def test_ingestion_passes_validated_chunks_and_metadata_to_the_store(monkeypatch):
    vector = [1.0] + [0.0] * 383
    monkeypatch.setattr(embeddings, "embed", lambda texts: [vector for _ in texts])
    captured = {}
    def persist(title, source, text, chunks, vectors, metadata, filename, size, overlap):
        assert all(validate_vector(v) for v in vectors)
        captured.update(metadata=metadata, source=source, chunks=chunks)
        return {"documentId": "demo-id", "chunks": len(chunks), "deduplicated": False, "model": "fake-test-only"}
    monkeypatch.setattr(store, "save_document", persist)
    result = client.post("/internal/v1/knowledge/documents", json={"title": "Policy", "source": "risk.md", "text": "Fictional credit policy", "metadata": {"area": "risk"}})
    assert result.status_code == 201
    assert captured == {"metadata": {"area": "risk"}, "source": "risk.md", "chunks": ["Fictional credit policy"]}


def test_missing_document_returns_404(monkeypatch):
    monkeypatch.setattr(store, "get_document", lambda identifier: None)
    assert client.get("/internal/v1/knowledge/documents/00000000-0000-0000-0000-000000000001").status_code == 404


def test_retrieval_preserves_source_attribution_and_does_not_generate_answer(monkeypatch):
    monkeypatch.setattr(embeddings, "embed", lambda texts: [[1.0] + [0.0] * 383])
    def retrieve(vector, limit, score, metadata_filter):
        assert limit == 2 and metadata_filter == {"area": "risk"}
        return [{"chunkId": "chunk", "documentId": "doc", "title": "Policy", "source": "policy.md", "ordinal": 0, "content": "Credit policy", "score": 0.9, "metadata": {"area": "risk"}}]
    monkeypatch.setattr(store, "search", retrieve)
    result = client.post("/internal/v1/knowledge/search", json={"query": "credit risk", "top_k": 2, "metadataFilter": {"area": "risk"}}).json()
    assert result["results"][0]["source"] == "policy.md"
    assert result["context"]["references"][0]["chunkId"] == "chunk"
    assert result["context"]["generatedAnswer"] is None
