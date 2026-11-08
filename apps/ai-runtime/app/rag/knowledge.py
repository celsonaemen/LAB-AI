import math

DIMENSIONS = 384
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def chunk_text(text: str, size: int = 350, overlap: int = 60) -> list[str]:
    if not 50 <= size <= 1500 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be 50..1500 and overlap must be smaller than size")
    text = text.strip()
    if not text:
        raise ValueError("Document is empty")
    if len(text) > size and 1 + math.ceil((len(text) - size) / (size - overlap)) > 128:
        raise ValueError("Document produces more than 128 chunks; reduce overlap or increase chunk size")
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks


def validate_vector(vector: list[float]) -> list[float]:
    if len(vector) != DIMENSIONS or not all(math.isfinite(value) for value in vector):
        raise ValueError("Embedding must contain 384 finite values")
    if not any(value != 0 for value in vector):
        raise ValueError("Zero embedding cannot be searched with cosine distance")
    return vector
