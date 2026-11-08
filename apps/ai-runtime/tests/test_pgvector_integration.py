import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from app.migrate import migrate

from app.rag import store


@pytest.mark.skipif(not os.getenv("AEGIS_TEST_DATABASE_URL"), reason="Requires dedicated pgvector test database")
def test_postgres_persists_deduplicates_and_ranks_by_cosine(monkeypatch):
    dsn = os.environ["AEGIS_TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", dsn)
    schema = Path(__file__).resolve().parents[3] / "infrastructure/database/migrations"
    migrate(schema)
    assert migrate(schema) == []
    with psycopg.connect(dsn) as connection:
        assert connection.execute("SELECT count(*) FROM pg_indexes WHERE schemaname='knowledge' AND indexdef LIKE '%hnsw%'").fetchone()[0] == 1
    first_text = f"Fictional risk policy {uuid4()}"
    second_text = f"Fictional cafeteria menu {uuid4()}"
    first_vector = [1.0] + [0.0] * 383
    second_vector = [0.0, 1.0] + [0.0] * 382
    ids = []
    try:
        first = store.save_document("Risk", "risk.txt", first_text, [first_text], [first_vector])
        ids.append(first["documentId"])
        second = store.save_document("Menu", "menu.txt", second_text, [second_text], [second_vector])
        ids.append(second["documentId"])
        duplicate = store.save_document("Risk", "risk.txt", first_text, [first_text], [first_vector])
        assert duplicate["documentId"] == first["documentId"]
        assert duplicate["deduplicated"] is True
        assert store.get_document(first["documentId"])["source"] == "risk.txt"
        assert store.get_document(str(uuid4())) is None
        hits = store.search(first_vector, 20, 0.99)
        assert any(hit["documentId"] == first["documentId"] and hit["score"] > 0.99 for hit in hits)
        assert not any(hit["documentId"] == second["documentId"] for hit in hits)
    finally:
        with psycopg.connect(dsn) as connection:
            connection.execute("DELETE FROM knowledge.documents WHERE id = ANY(%s::uuid[])", (ids,))


@pytest.mark.skipif(not os.getenv("AEGIS_TEST_DATABASE_URL") or os.getenv("AEGIS_REAL_EMBEDDINGS") != "1",
                    reason="Requires pgvector database and real model opt-in")
@pytest.mark.parametrize("query,relevant,irrelevant", [
    ("Como reduzir o risco de crédito?", "A política de crédito exige garantias para limitar perdas por inadimplência.", "O restaurante oferece massas e sobremesas."),
    ("How can we reduce credit risk?", "Credit policy requires collateral to limit losses from borrower defaults.", "The restaurant offers pasta and desserts."),
])
def test_real_semantic_retrieval_with_postgres_metadata_and_sources(monkeypatch, query, relevant, irrelevant):
    from app.rag.embeddings import embed
    monkeypatch.setenv("DATABASE_URL", os.environ["AEGIS_TEST_DATABASE_URL"])
    migrate(Path(__file__).resolve().parents[3] / "infrastructure/database/migrations")
    corpus = str(uuid4())
    vectors = embed([query, relevant, irrelevant])
    ids = []
    try:
        for title, content, vector in [("Risk", relevant, vectors[1]), ("Menu", irrelevant, vectors[2])]:
            receipt = store.save_document(title, f"{title}.md", content + corpus, [content], [vector], {"testCorpus": corpus})
            ids.append(receipt["documentId"])
        hits = store.search(vectors[0], 2, -1.0, {"testCorpus": corpus})
        assert len(hits) == 2
        assert hits[0]["documentId"] == ids[0]
        assert hits[0]["score"] > hits[1]["score"]
        assert hits[0]["source"] == "Risk.md"
        assert hits[0]["metadata"] == {"testCorpus": corpus}
    finally:
        with psycopg.connect(os.environ["AEGIS_TEST_DATABASE_URL"]) as connection:
            connection.execute("DELETE FROM knowledge.documents WHERE id=ANY(%s::uuid[])", (ids,))
