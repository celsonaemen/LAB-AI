"""Repair a retired label in local demo documents with real re-embedding.

Defaults to a read-only plan. --apply requires an exact document allowlist.
Document/chunk IDs are preserved; historical execution evidence is not rewritten.
An ignored local backup is created before the atomic database update.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'ai-runtime'))

from app.rag import embeddings
from app.rag.knowledge import chunk_text, validate_vector
from app.rag.store import _connect, _vector_literal


def corrected_chunks(document, rows, old_label, new_label):
    if not old_label.strip() or old_label.casefold() == new_label.casefold():
        raise ValueError('Provide distinct nonempty labels')
    if document['source'] not in {'demo/credit-policy.pdf', 'demo/cafeteria.pdf'} or document['metadata'].get('area') != 'demo':
        raise ValueError('Only the existing synthetic demo PDF sources may be repaired')
    overlap = document['chunk_overlap']
    if not rows or [row['ordinal'] for row in rows] != list(range(len(rows))):
        raise ValueError('Chunks must have contiguous ordinals')
    text = rows[0]['content']
    for previous, current in zip(rows, rows[1:]):
        if overlap and previous['content'][-overlap:] != current['content'][:overlap]:
            raise ValueError('Stored chunk overlap is inconsistent')
        text += current['content'][overlap:]
    if hashlib.sha256(text.strip().encode('utf-8')).hexdigest() != document['content_hash']:
        raise ValueError('Reconstructed text does not match original document hash')
    if chunk_text(text, document['chunk_size'], overlap) != [row['content'] for row in rows]:
        raise ValueError('Reconstructed chunk boundaries differ')
    corrected = re.sub(re.escape(old_label), lambda match: new_label, text, flags=re.I)
    chunks = chunk_text(corrected, document['chunk_size'], overlap)
    if len(chunks) != len(rows):
        raise ValueError('Repair would change chunk count; refusing to remove or replace source IDs')
    return corrected, chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-label', required=True)
    parser.add_argument('--new-label', default='AEGIS AGENT LAB')
    parser.add_argument('--document-id', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with _connect() as connection:
        connection.read_only = True
        documents = connection.execute(
            'SELECT DISTINCT d.* FROM knowledge.documents d JOIN knowledge.document_chunks c ON c.document_id=d.id '
            'WHERE position(lower(%s) in lower(c.content))>0 ORDER BY d.id', (args.old_label,)).fetchall()
        plans = []
        for document in documents:
            rows = connection.execute(
                'SELECT id,ordinal,content,embedding::text AS embedding FROM knowledge.document_chunks '
                'WHERE document_id=%s ORDER BY ordinal', (document['id'],)).fetchall()
            text, chunks = corrected_chunks(document, rows, args.old_label, args.new_label)
            plans.append({'document': document, 'originalRows': rows, 'text': text, 'chunks': chunks})
    ids = {str(plan['document']['id']) for plan in plans}
    print(json.dumps({'documents': len(plans), 'chunks': sum(len(p['chunks']) for p in plans),
                      'documentIds': sorted(ids), 'apply': args.apply}), flush=True)
    if not args.apply or not plans:
        return
    if ids != set(args.document_id):
        raise ValueError('Apply requires the exact affected document UUID allowlist from the dry run')
    # The same configured FastEmbed engine used by ingestion supplies actual vectors.
    for plan in plans:
        plan['vectors'] = embeddings.embed(plan['chunks'])
        for vector in plan['vectors']:
            validate_vector(vector)
    backup = ROOT / '.artifacts' / 'identity-repair' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True, exist_ok=False)
    (backup / 'original-documents.json').write_text(json.dumps([
        {'document': plan['document'], 'chunks': plan['originalRows']} for plan in plans
    ], default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with _connect() as connection:
        for plan in plans:
            document = plan['document']
            current = connection.execute('SELECT content_hash FROM knowledge.documents WHERE id=%s FOR UPDATE',
                                         (document['id'],)).fetchone()
            if current['content_hash'] != document['content_hash']:
                raise ValueError('Document changed during repair; transaction rolled back')
            for original, content, vector in zip(plan['originalRows'], plan['chunks'], plan['vectors'], strict=True):
                connection.execute('UPDATE knowledge.document_chunks SET content=%s,embedding=%s::vector WHERE id=%s AND document_id=%s',
                                   (content, _vector_literal(vector), original['id'], document['id']))
            connection.execute('UPDATE knowledge.documents SET content_hash=%s,updated_at=now() WHERE id=%s',
                               (hashlib.sha256(plan['text'].strip().encode('utf-8')).hexdigest(), document['id']))
    (backup / 'result.json').write_text(json.dumps({'documents': len(plans), 'documentIds': sorted(ids),
        'embeddings': sum(len(p['vectors']) for p in plans), 'dimensions': 384,
        'historicalExecutionsModified': False}, indent=2), encoding='utf-8')
    print('Repair committed atomically; source IDs preserved; private backup created.', flush=True)


if __name__ == '__main__':
    main()
