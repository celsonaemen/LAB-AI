import pytest

from app.rag.knowledge import chunk_text, validate_vector


def test_chunking_preserves_text_and_has_bounded_overlapping_chunks():
    text = "a" * 800
    chunks = chunk_text(text)
    assert all(0 < len(chunk) <= 350 for chunk in chunks)
    assert chunks[0][-60:] == chunks[1][:60]
    assert chunks[-1].endswith(text[-100:])


def test_chunking_rejects_empty_documents():
    with pytest.raises(ValueError, match="empty"):
        chunk_text("   ")


def test_chunk_configuration_is_applied_and_validated():
    assert [len(c) for c in chunk_text("a" * 120, 50, 10)] == [50, 50, 40]
    with pytest.raises(ValueError):
        chunk_text("text", 50, 50)


def test_excessive_chunk_count_is_rejected_before_embedding():
    with pytest.raises(ValueError, match="128"):
        chunk_text("a" * 20000, 50, 49)


@pytest.mark.parametrize("vector", [[0.0] * 384, [float("nan")] * 384, [1.0] * 3])
def test_invalid_embeddings_are_rejected(vector):
    with pytest.raises(ValueError):
        validate_vector(vector)
