import base64
import binascii
import io
import re
import unicodedata
from pathlib import PurePath


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if "\x00" in text:
        raise ValueError("Document contains invalid null characters")
    if not text:
        raise ValueError("Document is empty after extraction")
    if len(text) > 20000:
        raise ValueError("Extracted text exceeds 20000 characters")
    return text


def extract_text(filename: str, content_base64: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md", ".markdown"}:
        raise ValueError("Supported formats: PDF, UTF-8 TXT and Markdown")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("File content must be valid base64") from error
    if not data or len(data) > 2_000_000:
        raise ValueError("File size must be 1..2000000 bytes")
    if suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        if not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF header")
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted or len(reader.pages) > 100:
                raise ValueError("Encrypted PDFs and PDFs over 100 pages are unsupported")
            return normalize_text("\n\n".join(page.extract_text() or "" for page in reader.pages))
        except PdfReadError as error:
            raise ValueError("PDF cannot be parsed") from error
    try:
        return normalize_text(data.decode("utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ValueError("Text files must use UTF-8") from error
