"""End-to-end SudAI analysis pipeline.

Public entry points:

* :func:`analyze_document` — bytes from storage + filename → full result.
  Reads the file via ``aiofiles`` so it does not block the event loop.
* :func:`analyze_text` — raw text → full result. Useful for tests and
  for inline AI panels that already have the text in memory.

The orchestrator follows the order from the original standalone MVP:
load → anonymize → classify → extract → retrieve → reason.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import aiofiles

from app.api.schemas.ai_analysis import (
    AIAnalysisResponse,
    AIDocumentMetadata,
)
from app.core.enums import DocumentLanguage
from app.services.ai_law.anonymizer import anonymize
from app.services.ai_law.classifier import classify, detect_document_type
from app.services.ai_law.document_loader import extract_text_from_file
from app.services.ai_law.extractor import extract_legal_objects
from app.services.ai_law.rag import retrieve_sources
from app.services.ai_law.reasoner import build_explanation, build_recommendation


async def analyze_document(
    file_path: Path,
    filename: str,
) -> AIAnalysisResponse:
    """Read ``file_path`` and run the full SudAI pipeline.

    ``file_path`` is the absolute resolved storage path. For seeded
    documents with no on-disk bytes the caller should fail fast and
    never reach this function.
    """
    async with aiofiles.open(file_path, "rb") as f:
        content = await f.read()
    text, ocr_required, pages = extract_text_from_file(content, filename)
    return _analyze(text, filename=filename, pages=pages, ocr_required=ocr_required)


async def analyze_text(
    text: str,
    filename: Optional[str] = None,
) -> AIAnalysisResponse:
    """Run the pipeline against pre-extracted text (no file IO)."""
    return _analyze(text, filename=filename or "plain-text", pages=1, ocr_required=False)


def _analyze(text: str, filename: str, pages: int, ocr_required: bool) -> AIAnalysisResponse:
    anonymized_text, entities = anonymize(text)
    classification = classify(anonymized_text)
    category_hint = " ".join(
        [
            classification.main_category.value,
            classification.sub_category,
            classification.procedure_type.value,
        ]
    )
    matched_sources = retrieve_sources(anonymized_text, category_hint=category_hint)

    metadata = AIDocumentMetadata(
        document_type=detect_document_type(anonymized_text),
        language=_detect_language(anonymized_text),
        pages=pages,
        ocr_required=ocr_required or _looks_like_image(filename),
    )

    return AIAnalysisResponse(
        metadata=metadata,
        anonymized_text=anonymized_text,
        anonymized_entities=entities,
        extracted_objects=extract_legal_objects(anonymized_text),
        classification=classification,
        matched_sources=matched_sources,
        explanation=build_explanation(classification, matched_sources),
        confidence_percent=round(classification.confidence * 100),
        human_review=build_recommendation(classification),
    )


def _detect_language(text: str) -> DocumentLanguage:
    cyrillic = sum(1 for c in text.lower() if "а" <= c <= "я")
    latin = sum(1 for c in text.lower() if "a" <= c <= "z")
    if cyrillic > latin:
        return DocumentLanguage.UZBEK_CYRILLIC_OR_RUSSIAN
    return DocumentLanguage.UZBEK_LATIN


def _looks_like_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in {
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".webp",
    }
