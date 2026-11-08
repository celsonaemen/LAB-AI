import base64
import io

import pytest
from pypdf import PdfWriter

from app.rag.processing import extract_text, normalize_text


def test_normalization_preserves_portuguese_and_paragraphs():
    assert normalize_text("  Crédito\t\t e risco\r\n\r\n\r\n  Política  ") == "Crédito e risco\n\nPolítica"


@pytest.mark.parametrize("filename", ["policy.txt", "policy.md", "policy.markdown"])
def test_utf8_text_and_markdown_extraction(filename):
    content = base64.b64encode("# Política\nCrédito e garantias".encode()).decode()
    assert "Crédito" in extract_text(filename, content)


def test_pdf_text_extraction():
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=400)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 30 300 Td (Credit policy fictional data) Tj ET")
    page[NameObject("/Contents")] = stream
    buffer = io.BytesIO()
    writer.write(buffer)
    assert "Credit policy" in extract_text("policy.pdf", base64.b64encode(buffer.getvalue()).decode())


@pytest.mark.parametrize("filename,content", [("x.exe", "eA=="), ("x.txt", "!invalid!"), ("x.pdf", "eA=="), ("x.txt", "")])
def test_invalid_file_content_is_rejected(filename, content):
    with pytest.raises(ValueError):
        extract_text(filename, content)


def test_image_only_pdf_is_explicitly_empty():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(ValueError, match="empty"):
        extract_text("scan.pdf", base64.b64encode(buffer.getvalue()).decode())
