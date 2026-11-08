import math
import os

import pytest

from app.rag.embeddings import embed


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b)))


@pytest.mark.skipif(os.getenv("AEGIS_REAL_EMBEDDINGS") != "1", reason="Opt-in: downloads real model")
@pytest.mark.parametrize("query,relevant,irrelevant", [
    ("A carteira possui alto risco de crédito.", "Exposição à inadimplência de devedores.", "O cardápio do restaurante inclui massas."),
    ("The portfolio has high credit risk.", "Borrower default exposure and loan losses.", "The restaurant serves pasta for lunch."),
])
def test_real_multilingual_model_ranks_related_evidence_first(query, relevant, irrelevant):
    vectors = embed([query, relevant, irrelevant])
    assert all(len(vector) == 384 for vector in vectors)
    assert cosine(vectors[0], vectors[1]) > cosine(vectors[0], vectors[2])
