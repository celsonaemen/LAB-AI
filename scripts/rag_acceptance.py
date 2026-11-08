"""Real HTTP acceptance. Writes fictional PDFs and evidence; never mocks embeddings/storage.

Requires running .NET -> Python -> PostgreSQL. DATABASE_URL is used only by this
engineering verification script to independently check persisted source/vector rows.
"""
import argparse
import base64
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def write_pdf(path, lines):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica'), NameObject('/Encoding'): NameObject('/WinAnsiEncoding')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    commands = ['BT /F1 11 Tf 36 740 Td 16 TL']
    for line in lines:
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        commands.append(f'({escaped}) Tj T*')
    stream.set_data(('\n'.join(commands) + '\nET').encode('cp1252'))
    page[NameObject('/Contents')] = stream
    writer.write(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5080')
    parser.add_argument('--output', default='.artifacts/rag')
    parser.add_argument('--unavailable-api', help='Optional real .NET instance pointing to an unused runtime port')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    corpus = str(uuid4())
    report = {'corpus': corpus, 'baseUrl': args.base_url, 'checks': [], 'searches': []}
    policies = {
        'credit-policy.pdf': ['AEGIS AGENT LAB - dados fictícios / fictional data', f'Corpus {corpus}',
                              'A política de crédito exige garantias para limitar perdas por inadimplência.',
                              'Para reduzir o risco de crédito, diversifique a carteira e revise as garantias.',
                              'Credit policy requires collateral to limit losses from borrower defaults.',
                              'To reduce credit risk, diversify the portfolio and review collateral.'],
        'cafeteria.pdf': ['AEGIS AGENT LAB - fictional cafeteria menu', f'Corpus {corpus}',
                         'O restaurante oferece massas e sobremesas. The restaurant serves pasta and cake.']}
    with httpx.Client(base_url=args.base_url, timeout=150) as client:
        def call(method, route, body=None, status=200):
            response = client.request(method, route, json=body) if body is not None else client.request(method, route)
            assert response.status_code == status, (route, response.status_code, response.text[:500])
            return response.json()

        receipts = []
        for filename, lines in policies.items():
            path = output / filename
            write_pdf(path, lines)
            payload = {'title': filename, 'source': f'demo/{filename}', 'filename': filename,
                       'contentBase64': base64.b64encode(path.read_bytes()).decode(),
                       'metadata': {'corpus': corpus, 'area': 'demo'}, 'chunkSize': 350, 'chunkOverlap': 60}
            receipt = call('POST', '/api/v1/knowledge/documents', payload, 201)
            assert receipt['chunks'] > 0 and receipt['status'] == 'indexed'
            assert receipt['metadata']['corpus'] == corpus
            assert not receipt['deduplicated']
            receipts.append(receipt)
            duplicate = call('POST', '/api/v1/knowledge/documents', payload | {'metadata': {'area': 'changed'}}, 201)
            assert duplicate['documentId'] == receipt['documentId'] and duplicate['deduplicated']
            assert duplicate['metadata'] == receipt['metadata']
            details = call('GET', '/api/v1/knowledge/documents/' + receipt['documentId'])
            assert details['source'] == payload['source'] and details['metadata'] == payload['metadata']
        report['checks'].extend(['real_pdf_ingestion', 'duplicate_preserves_original_metadata', 'document_details'])
        listed = call('GET', '/api/v1/knowledge/documents?limit=100')
        assert {r['documentId'] for r in receipts} <= {d['documentId'] for d in listed}
        with psycopg.connect(os.environ['DATABASE_URL']) as connection:
            rows = connection.execute('SELECT id::text, document_id::text, content, vector_dims(embedding) FROM knowledge.document_chunks WHERE document_id = ANY(%s::uuid[])',
                                      ([r['documentId'] for r in receipts],)).fetchall()
            assert len(rows) == sum(r['chunks'] for r in receipts)
            assert all(row[3] == 384 for row in rows)
            assert any('garantias' in row[2] for row in rows)
            sources = {row[0]: row for row in rows}
            report['persistedChunks'] = len(rows)
            report['dimensions'] = 384
        report['checks'].extend(['pdf_extraction_in_database', 'real_embedding_dimensions', 'atomic_chunk_count'])
        for language, query in [('pt', 'Como reduzir o risco de crédito?'), ('en', 'How can we reduce credit risk?')]:
            result = call('POST', '/api/v1/knowledge/search', {'query': query, 'top_k': 3, 'minScore': 0,
                          'metadataFilter': {'corpus': corpus}, 'maxContextChars': 6000})
            assert result['dimensions'] == 384
            assert result['results'][0]['documentId'] == receipts[0]['documentId']
            assert result['context']['status'] == 'evidence_available'
            assert result['context']['generatedAnswer'] is None
            assert result['context']['references']
            for hit in result['results']:
                row = sources[hit['chunkId']]
                assert row[1] == hit['documentId'] and row[2] == hit['content']
                assert hit['metadata']['corpus'] == corpus
            hits = {hit['chunkId']: hit for hit in result['results']}
            for ref in result['context']['references']:
                hit = hits[ref['chunkId']]
                assert ref['source'] == hit['source'] and ref['documentId'] == hit['documentId']
            report['searches'].append({'language': language, 'response': result})
        report['checks'].extend(['portuguese_semantic_search', 'english_semantic_search', 'verifiable_sources'])
        empty = call('POST', '/api/v1/knowledge/search', {'query': 'credit risk', 'metadataFilter': {'corpus': str(uuid4())}})
        assert empty['results'] == [] and empty['context']['status'] == 'insufficient_evidence'
        assert empty['context']['references'] == []
        call('GET', '/api/v1/knowledge/documents/' + str(uuid4()), status=404)
        for filename, content in [('bad.pdf', b'not a PDF'), ('bad.exe', b'x')]:
            call('POST', '/api/v1/knowledge/documents', {'title': 'Invalid', 'source': 'invalid', 'filename': filename,
                 'contentBase64': base64.b64encode(content).decode()}, 400)
        report['checks'].extend(['insufficient_evidence', 'missing_document_404', 'invalid_pdf_400', 'invalid_extension_400'])
        if args.unavailable_api:
            with httpx.Client(base_url=args.unavailable_api, timeout=15) as broken:
                response = broken.post('/api/v1/knowledge/search', json={'query': 'credit risk'})
                assert response.status_code == 503 and response.json()['status'] == 503
            report['checks'].append('real_runtime_connection_failure_503')
        report['documents'] = receipts
        report['passed'] = True
        (output / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': True, 'checks': report['checks'], 'documents': receipts, 'evidence': str(output / 'acceptance.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
