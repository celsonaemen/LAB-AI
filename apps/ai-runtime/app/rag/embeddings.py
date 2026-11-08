import os
from functools import lru_cache
from threading import Lock

from app.rag.knowledge import MODEL, validate_vector

_load_lock = Lock()


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    return TextEmbedding(
        model_name=MODEL,
        cache_dir=os.getenv("EMBEDDING_CACHE_DIR", ".model-cache"),
        threads=2,
    )


def embed(texts: list[str]) -> list[list[float]]:
    # Also serializes first-time model initialization across FastAPI worker threads.
    with _load_lock:
        model = _model()
        vectors = [validate_vector(vector.tolist()) for vector in model.embed(texts, batch_size=16)]
    if len(vectors) != len(texts):
        raise ValueError("Embedding provider returned an unexpected vector count")
    return vectors
