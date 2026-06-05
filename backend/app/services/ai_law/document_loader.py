"""Bytes → text extraction for PDF, DOCX, and TXT files.

Behaviour matches the original ``sudai-research-raw`` loader. Returns
``(text, ocr_required, pages)`` — when ``ocr_required`` is True the
caller should hand off to the OCR pipeline (currently a CP2 stub in
``app.cp2_stubs.ocr_service``).
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Tuple


def extract_text_from_file(content: bytes, filename: str) -> Tuple[str, bool, int]:
    """Extract text from the file. Falls back to UTF-8 decode on unknown
    extensions and flags the document as OCR-required.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return content.decode("utf-8", errors="ignore"), False, 1

    if suffix == ".pdf":
        return _extract_pdf_text(content)

    if suffix == ".docx":
        return _extract_docx_text(content)

    # Unknown extension: best-effort decode, mark as OCR-required.
    return content.decode("utf-8", errors="ignore"), True, 1


def _extract_pdf_text(content: bytes) -> Tuple[str, bool, int]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[PDF matnini ajratish uchun pypdf paketini o'rnating.]", True, 1

    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    text = "\n".join(pages).strip()
    return text, not bool(text), max(len(reader.pages), 1)


def _extract_docx_text(content: bytes) -> Tuple[str, bool, int]:
    try:
        from docx import Document
    except ImportError:
        return "[DOCX matnini ajratish uchun python-docx paketini o'rnating.]", True, 1

    document = Document(BytesIO(content))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs), False, 1
