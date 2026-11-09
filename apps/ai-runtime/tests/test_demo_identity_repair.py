import hashlib
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('demo_identity_repair', Path(__file__).resolve().parents[3] / 'scripts' / 'repair_demo_identity.py')
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def fixture(text):
    from app.rag.knowledge import chunk_text
    text = text.strip()
    document = {'source': 'demo/credit-policy.pdf', 'metadata': {'area': 'demo'},
                'chunk_size': 100, 'chunk_overlap': 20,
                'content_hash': hashlib.sha256(text.encode()).hexdigest()}
    rows = [{'ordinal': ordinal, 'content': content} for ordinal, content in enumerate(chunk_text(text, 100, 20))]
    return document, rows


def test_repair_reconstructs_overlap_and_preserves_content():
    text = ('Retired Lab. ' + 'Fictional credit controls and collateral evidence. ' * 5).strip()
    document, rows = fixture(text)
    corrected, chunks = repair.corrected_chunks(document, rows, 'Retired Lab', 'Aegis Lab')
    assert corrected == text.replace('Retired Lab', 'Aegis Lab')
    assert len(chunks) == len(rows)
    assert all('Retired Lab' not in chunk for chunk in chunks)


def test_repair_refuses_inconsistent_source_hash():
    document, rows = fixture('Retired Lab. Fictional evidence.')
    rows[0]['content'] += 'altered'
    with pytest.raises(ValueError, match='hash'):
        repair.corrected_chunks(document, rows, 'Retired Lab', 'Aegis Lab')


def test_repair_refuses_non_demo_documents():
    document, rows = fixture('Retired Lab. Fictional evidence.')
    document['source'] = 'synthetic/new-corpus/policy.pdf'
    with pytest.raises(ValueError, match='synthetic demo'):
        repair.corrected_chunks(document, rows, 'Retired Lab', 'Aegis Lab')
