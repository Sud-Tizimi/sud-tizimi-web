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

from hashlib import sha256
from pathlib import Path
from typing import Optional

import aiofiles
from pydantic import ValidationError

from app.api.schemas.ai_analysis import (
    AIAnalysisResponse,
    AIAnalysisTechnicalMetadata,
    AIDocumentMetadata,
    AIReasoningOutput,
)
from app.config import get_settings
from app.core.enums import DocumentLanguage
from app.services.ai_law.anonymizer import anonymize
from app.services.ai_law.classifier import classify, detect_document_type
from app.services.ai_law.document_loader import extract_text_for_analysis
from app.services.ai_law.extractor import extract_legal_objects
from app.services.ai_law.providers import (
    AIProviderRequest,
    LegalContextSource,
    ProviderResponseError,
    build_ai_provider,
)
from app.services.ai_law.rag import retrieve_sources


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
    extracted = await extract_text_for_analysis(content, file_path, filename)
    return await _analyze(
        extracted.text,
        filename=filename,
        pages=extracted.pages,
        ocr_required=extracted.ocr_used,
        extraction_method=extracted.extraction_method,
        ocr_used=extracted.ocr_used,
    )


async def analyze_text(
    text: str,
    filename: Optional[str] = None,
) -> AIAnalysisResponse:
    """Run the pipeline against pre-extracted text (no file IO)."""
    return await _analyze(
        text,
        filename=filename or "plain-text",
        pages=1,
        ocr_required=False,
        extraction_method="text",
        ocr_used=False,
    )


async def _analyze(
    text: str,
    filename: str,
    pages: int,
    ocr_required: bool,
    extraction_method: str,
    ocr_used: bool,
) -> AIAnalysisResponse:
    """Run deterministic extraction/retrieval, then provider reasoning.

    `matched_sources` remains the exact trusted list returned by RAG.  The
    provider can only refer to those records by a generated internal ID and
    never constructs sources for the API response itself.
    """
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
        ocr_required=ocr_required,
        extraction_method=extraction_method,
        ocr_used=ocr_used,
    )

    extracted_objects = extract_legal_objects(anonymized_text)
    legal_context = [_legal_context_source(index, source) for index, source in enumerate(matched_sources)]
    request = AIProviderRequest(
        document_text=anonymized_text,
        metadata=metadata,
        classification=classification,
        extracted_objects=extracted_objects,
        legal_context=legal_context,
    )
    provider_result = await build_ai_provider(get_settings()).analyze(request)
    try:
        reasoning = AIReasoningOutput.model_validate(provider_result.payload)
    except ValidationError as exc:
        raise ProviderResponseError("remote_provider_schema_error") from exc
    _assert_trusted_citations(reasoning, legal_context)

    return AIAnalysisResponse(
        metadata=metadata,
        anonymized_text=anonymized_text,
        anonymized_entities=entities,
        extracted_objects=extracted_objects,
        classification=classification,
        matched_sources=matched_sources,
        explanation=reasoning.explanation,
        confidence_percent=reasoning.confidence_percent,
        human_review=reasoning.human_review,
        findings=reasoning.findings,
        technical_metadata=AIAnalysisTechnicalMetadata(
            analysis_mode="local" if provider_result.provider == "local" else "llm",
            provider=provider_result.provider,
            model=provider_result.model,
            latency_ms=provider_result.latency_ms,
            token_usage=provider_result.token_usage,
        ),
    )


def _legal_context_source(index: int, source) -> LegalContextSource:
    """Assign a stable private ID even to fallback RAG records without DB IDs."""
    stable = source.source_id or sha256(
        f"{source.law}|{source.article}|{source.title}".encode("utf-8")
    ).hexdigest()[:16]
    return LegalContextSource(
        source_id=f"rag:{index}:{stable}",
        law=source.law,
        article=source.article,
        title=source.title,
        excerpt=source.excerpt,
        relevance=source.relevance,
    )


def _assert_trusted_citations(
    reasoning: AIReasoningOutput, legal_context: list[LegalContextSource]
) -> None:
    allowed = {source.source_id for source in legal_context}
    for finding in reasoning.findings:
        unknown = set(finding.source_ids).difference(allowed)
        if unknown:
            # Reject the whole response instead of silently displaying an
            # unsupported assertion.  `matched_sources` is never model-owned.
            raise ProviderResponseError("remote_provider_untrusted_citation")
    if not legal_context and (
        reasoning.context_sufficient
        or not any(finding.kind == "insufficient_context" for finding in reasoning.findings)
    ):
        raise ProviderResponseError("remote_provider_missing_context_disclosure")


def _detect_language(text: str) -> DocumentLanguage:
    cyrillic = sum(1 for c in text.lower() if "а" <= c <= "я")
    latin = sum(1 for c in text.lower() if "a" <= c <= "z")
    if cyrillic > latin:
        return DocumentLanguage.UZBEK_CYRILLIC_OR_RUSSIAN
    return DocumentLanguage.UZBEK_LATIN
