"""Document text extraction for the local SudAI pipeline.

Text-based PDF and DOCX files keep their lightweight in-memory parsers.
Images and PDFs without meaningful embedded text are delegated to the existing
local OCR adapter.  Raw image bytes are never decoded as UTF-8 text.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Tuple

from app.config import get_settings
from app.services.ocr_service import process_document


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
_MIN_MEANINGFUL_CHARS = 20
_MIN_MEANINGFUL_WORDS = 3


class DocumentExtractionError(RuntimeError):
    """Raised when no meaningful text can be extracted from a document."""


@dataclass(frozen=True)
class ExtractedDocumentText:
    text: str
    pages: int
    extraction_method: str
    ocr_used: bool


def has_meaningful_text(text: str) -> bool:
    """Return whether text is substantial enough to analyse.

    The threshold avoids treating a PDF artefact or an empty OCR result as a
    successful analysis while still allowing ordinary multi-word legal text.
    """
    normalized = " ".join(text.split())
    words = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
    return len(normalized) >= _MIN_MEANINGFUL_CHARS and len(words) >= _MIN_MEANINGFUL_WORDS


def extract_text_from_file(content: bytes, filename: str) -> Tuple[str, bool, int]:
    """Fast text-only extractor kept for existing PDF/DOCX callers.

    Image files deliberately return no text; their binary content must pass
    through :func:`extract_text_for_analysis` and OCR instead.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return content.decode("utf-8", errors="ignore"), False, 1

    if suffix == ".pdf":
        return _extract_pdf_text(content)

    if suffix == ".docx":
        return _extract_docx_text(content)

    if suffix in _IMAGE_SUFFIXES:
        return "", True, 1

    # Plain-text fallback is appropriate only for a non-image unknown file.
    return content.decode("utf-8", errors="ignore"), True, 1


async def extract_text_for_analysis(
    content: bytes,
    file_path: Path,
    filename: str,
) -> ExtractedDocumentText:
    """Extract meaningful text for AI analysis, invoking local OCR if needed."""
    suffix = Path(filename).suffix.lower()
    text, _ocr_required, pages = extract_text_from_file(content, filename)

    if suffix == ".pdf":
        # A normal PDF stays on the fast pypdf path.  OCR is a fallback only
        # when the aggregate text layer is absent or practically empty.
        if has_meaningful_text(text):
            return ExtractedDocumentText(text, pages, "text", False)
        return await _extract_with_local_ocr(file_path, suffix)

    if suffix in _IMAGE_SUFFIXES:
        return await _extract_with_local_ocr(file_path, suffix)

    if suffix in {".docx", ".txt"}:
        if has_meaningful_text(text):
            return ExtractedDocumentText(text, pages, "text", False)
        raise DocumentExtractionError("document_text_is_empty")

    raise DocumentExtractionError(f"unsupported_document_type:{suffix or 'unknown'}")


async def _extract_with_local_ocr(file_path: Path, suffix: str) -> ExtractedDocumentText:
    """Run the project's existing OCR service without any cloud backend."""
    result = await process_document(
        str(file_path),
        suffix.lstrip("."),
        lang=get_settings().ocr_lang,
        local_only=True,
        # Pre-processing otherwise writes a sibling ``*_pre.png`` next to the
        # stored upload.  Tesseract still applies its in-memory variants.
        preprocess=False,
    )
    pages = result.get("pages", [])
    text = "\n".join(
        str(page.get("text") or "").strip() for page in pages if page.get("text")
    ).strip()
    if not has_meaningful_text(text):
        raise DocumentExtractionError("ocr_text_is_empty")
    return ExtractedDocumentText(text, max(len(pages), 1), "ocr", True)


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
