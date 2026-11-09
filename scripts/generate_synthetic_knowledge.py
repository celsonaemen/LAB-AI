"""Generate deterministic fictional PDF/TXT/Markdown fixtures using installed pypdf.

This script only creates document files and their manifest. It does not ingest
data, create embeddings, or modify the database. Use the real public API for that.
"""
import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = ROOT / 'datasets' / 'synthetic-knowledge'


def write_pdf(path: Path, title: str, content: str) -> dict:
    """Render bounded monospaced lines on letter pages and verify extraction."""
    lines = []
    for paragraph in content.splitlines():
        lines.extend(textwrap.wrap(paragraph, width=80, break_long_words=False,
                                   break_on_hyphens=False) or [''])
    assert max(map(len, lines)) <= 80, 'PDF source has an overlong unbreakable word'
    pages = [lines[offset:offset + 44] for offset in range(0, len(lines), 44)]
    writer = PdfWriter()
    writer.add_metadata({'/Title': title, '/Author': 'Aegis Agent Lab',
                         '/Subject': 'Synthetic fictional knowledge dataset'})
    for index, page_lines in enumerate(pages, start=1):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'),
            NameObject('/BaseFont'): NameObject('/Courier'),
            NameObject('/Encoding'): NameObject('/WinAnsiEncoding')})
        page[NameObject('/Resources')] = DictionaryObject({
            NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        commands = ['BT /F1 10 Tf 54 740 Td 14 TL']
        for line in page_lines:
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({escaped}) Tj T*')
        commands.extend(['ET', 'BT /F1 9 Tf 54 38 Td',
                         f'(Aegis Agent Lab - synthetic fixture - page {index}/{len(pages)}) Tj ET'])
        stream = DecodedStreamObject()
        stream.set_data('\n'.join(commands).encode('cp1252'))
        page[NameObject('/Contents')] = stream
    writer.write(path)
    reader = PdfReader(path, strict=True)
    extracted = '\n'.join(page.extract_text() for page in reader.pages)
    # Wrapping and page footers alter whitespace only; no source word may disappear.
    source_words = content.split()
    recovered = extracted.split()
    cursor = 0
    for word in source_words:
        while cursor < len(recovered) and recovered[cursor] != word:
            cursor += 1
        if cursor == len(recovered):
            raise ValueError(f'Missing PDF source word: {word}')
        cursor += 1
    return {'pages': len(reader.pages), 'sourceCharacters': len(content),
            'extractedCharacters': len(extracted), 'verifiedSourceWords': len(source_words),
            'maxLineCharacters': max(map(len, lines)),
            'layout': 'Courier 10pt; 80 columns; 44 lines/page; 54pt left margin; body baseline 740..138pt'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    source_path = DEFAULT_DIRECTORY / 'sources.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {key: source[key] for key in ('corpus', 'organization', 'notice')}
    manifest['generator'] = 'scripts/generate_synthetic_knowledge.py'
    manifest['documents'] = []
    pdf_checks = {}
    for document in source['documents']:
        path = output / document['file']
        if path.parent != output:
            raise ValueError('Fixture filename must not leave the selected output directory')
        content = document['content'].strip() + '\n'
        if document['format'] == 'pdf':
            pdf_checks[document['logicalId']] = write_pdf(path, document['title'], content)
        elif document['format'] in ('txt', 'markdown'):
            path.write_text(content, encoding='utf-8', newline='\n')
        else:
            raise ValueError('Unsupported fixture format')
        item = {key: value for key, value in document.items() if key != 'content'}
        item['attack'] = document.get('attack', False)
        item['metadata'] = {'corpus': source['corpus'], 'logicalId': document['logicalId'],
                            'theme': document['theme'], 'organization': source['organization'],
                            'synthetic': 'true', 'attack': str(item['attack']).lower()}
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest['documents'].append(item)
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    counts = {format_: sum(item['format'] == format_ for item in manifest['documents'])
              for format_ in ('pdf', 'txt', 'markdown')}
    print(json.dumps({'corpus': source['corpus'], 'documents': len(manifest['documents']),
                      'formats': counts, 'manifest': str(manifest_path), 'pdfChecks': pdf_checks},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
