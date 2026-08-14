"""Two-pass case-level analysis over the complete document set.

The document pipeline remains intentionally separate.  A case first extracts
and anonymizes every available document, then performs factual synthesis before
any legal retrieval.  Only the second provider pass receives backend-owned
legal sources.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Sequence

import aiofiles
from pydantic import ValidationError

from app.api.schemas.ai_analysis import (
    AIAnalysisResponse,
    AIAnalysisTechnicalMetadata,
    AIAnonymizationEntity,
    AICaseDocumentInput,
    AICaseFactualSynthesis,
    AICaseReasoningOutput,
    AIClassificationResult,
    AIDocumentMetadata,
    AIExtractedLegalObjects,
)
from app.config import get_settings
from app.core.enums import CaseLegalCategory, ProcedureType
from app.services.ai_law.anonymizer import anonymize
from app.services.ai_law.document_loader import (
    DocumentExtractionError,
    extract_text_for_analysis,
)
from app.services.ai_law.pipeline import (
    _assert_trusted_citations,
    _detect_language,
    _legal_context_source,
)
from app.services.ai_law.providers import (
    AICaseReasoningProviderRequest,
    AICaseSynthesisProviderRequest,
    ProviderResponseError,
    build_ai_provider,
)
from app.services.ai_law.rag import retrieve_case_sources


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaseDocumentSource:
    document_id: str
    filename: str
    file_path: Path


@dataclass(frozen=True)
class CasePipelineResult:
    response: AIAnalysisResponse
    sub_failures: list[dict[str, str]]


@dataclass(frozen=True)
class _PreparedDocument:
    provider_input: AICaseDocumentInput
    pages: int
    extraction_method: str
    ocr_used: bool
    entities: list[AIAnonymizationEntity]


async def analyze_case_documents(
    documents: Sequence[CaseDocumentSource],
) -> CasePipelineResult:
    """Run factual synthesis and legal reasoning over all usable documents."""
    prepared: list[_PreparedDocument] = []
    failures: list[dict[str, str]] = []
    for document in documents:
        try:
            prepared.append(await _prepare_document(document))
        except DocumentExtractionError as exc:
            failures.append(
                {"documentId": document.document_id, "error": _safe_extraction_error(exc)}
            )
        except Exception as exc:  # noqa: BLE001 — one unreadable file stays isolated
            _log.warning(
                "sudai_case_extraction_failed document_id=%s error_type=%s",
                document.document_id,
                type(exc).__name__,
            )
            failures.append({"documentId": document.document_id, "error": "file_read_failed"})

    if not prepared:
        raise DocumentExtractionError("all_documents_failed")

    provider = build_ai_provider(get_settings())
    synthesis_result = await provider.synthesize_case(
        AICaseSynthesisProviderRequest(
            documents=[item.provider_input for item in prepared]
        )
    )
    try:
        synthesis = AICaseFactualSynthesis.model_validate(synthesis_result.payload)
    except ValidationError as exc:
        raise ProviderResponseError("case_synthesis_schema_error") from exc
    _validate_synthesis_document_references(synthesis, prepared)

    matched_sources = retrieve_case_sources(synthesis)
    legal_context = [
        _legal_context_source(index, source)
        for index, source in enumerate(matched_sources)
    ]
    reasoning_result = await provider.analyze_case(
        AICaseReasoningProviderRequest(
            synthesis=synthesis,
            legal_context=legal_context,
        )
    )
    try:
        reasoning = AICaseReasoningOutput.model_validate(reasoning_result.payload)
    except ValidationError as exc:
        raise ProviderResponseError("case_reasoning_schema_error") from exc
    _assert_trusted_citations(reasoning, legal_context)

    response = _build_case_response(
        prepared=prepared,
        synthesis=synthesis,
        reasoning=reasoning,
        matched_sources=matched_sources,
        synthesis_provider_result=synthesis_result,
        reasoning_provider_result=reasoning_result,
    )
    return CasePipelineResult(response=response, sub_failures=failures)


async def _prepare_document(document: CaseDocumentSource) -> _PreparedDocument:
    async with aiofiles.open(document.file_path, "rb") as file_handle:
        content = await file_handle.read()
    extracted = await extract_text_for_analysis(
        content,
        document.file_path,
        document.filename,
    )
    anonymized_text, entities = anonymize(extracted.text)
    return _PreparedDocument(
        provider_input=AICaseDocumentInput(
            document_id=document.document_id,
            filename=document.filename,
            text=anonymized_text,
        ),
        pages=extracted.pages,
        extraction_method=extracted.extraction_method,
        ocr_used=extracted.ocr_used,
        entities=entities,
    )


def _validate_synthesis_document_references(
    synthesis: AICaseFactualSynthesis,
    prepared: Sequence[_PreparedDocument],
) -> None:
    expected = {item.provider_input.document_id for item in prepared}
    if set(synthesis.document_ids) != expected or len(synthesis.document_ids) != len(expected):
        raise ProviderResponseError("case_synthesis_document_set_mismatch")

    referenced_in_facts = {
        document_id
        for fact in synthesis.facts
        for document_id in fact.document_ids
    }
    if referenced_in_facts != expected:
        raise ProviderResponseError("case_synthesis_incomplete_evidence")

    reference_groups = [
        *(item.document_ids for item in synthesis.facts),
        *(item.document_ids for item in synthesis.timeline),
        *(item.document_ids for item in synthesis.evidence_links),
        *(item.document_ids for item in synthesis.entities),
        *(item.document_ids for item in synthesis.amounts),
    ]
    if any(not set(document_ids).issubset(expected) for document_ids in reference_groups):
        raise ProviderResponseError("case_synthesis_unknown_document")


def _build_case_response(
    *,
    prepared: Sequence[_PreparedDocument],
    synthesis: AICaseFactualSynthesis,
    reasoning: AICaseReasoningOutput,
    matched_sources,
    synthesis_provider_result,
    reasoning_provider_result,
) -> AIAnalysisResponse:
    candidate = synthesis.candidate_legal_domains[0]
    classification = _classification_from_candidate(candidate.domain, candidate.confidence)
    combined_text = "\n\n".join(
        (
            f"[documentId={item.provider_input.document_id}; "
            f"filename={item.provider_input.filename}]\n{item.provider_input.text}"
        )
        for item in prepared
    )
    all_entities = [entity for item in prepared for entity in item.entities]
    debt_amount = next(
        (amount.amount for amount in synthesis.amounts if amount.amount_type == "debt"),
        None,
    )
    total_latency = synthesis_provider_result.latency_ms + reasoning_provider_result.latency_ms
    token_usage = _merge_token_usage(
        synthesis_provider_result.token_usage,
        reasoning_provider_result.token_usage,
    )
    provider_name = reasoning_provider_result.provider

    return AIAnalysisResponse(
        metadata=AIDocumentMetadata(
            document_type="case_file",
            language=_detect_language(combined_text),
            pages=sum(item.pages for item in prepared),
            ocr_required=any(item.ocr_used for item in prepared),
            extraction_method=(
                "ocr" if any(item.extraction_method == "ocr" for item in prepared) else "text"
            ),
            ocr_used=any(item.ocr_used for item in prepared),
        ),
        anonymized_text=combined_text,
        anonymized_entities=all_entities,
        extracted_objects=AIExtractedLegalObjects(
            debt_amount=debt_amount,
            dates=[],
            attachments=[],
        ),
        classification=classification,
        matched_sources=matched_sources,
        explanation=reasoning.explanation,
        confidence_percent=reasoning.confidence_percent,
        human_review=reasoning.human_review,
        findings=reasoning.findings,
        technical_metadata=AIAnalysisTechnicalMetadata(
            analysis_mode="local" if provider_name == "local" else "llm",
            provider=provider_name,
            model=reasoning_provider_result.model,
            latency_ms=total_latency,
            token_usage=token_usage,
        ),
        factual_synthesis=synthesis,
        primary_conclusion=reasoning.primary_conclusion,
        evidence_summary=reasoning.evidence_summary,
        timeline=synthesis.timeline,
        evidence_links=synthesis.evidence_links,
        typed_amounts=synthesis.amounts,
        candidate_legal_domains=synthesis.candidate_legal_domains,
        uncertainties=synthesis.uncertainties,
    )


def _classification_from_candidate(domain: str, confidence: float) -> AIClassificationResult:
    if domain == "civil_debt":
        return AIClassificationResult(
            main_category=CaseLegalCategory.FUQAROLIK_ISHI,
            sub_category="qarz undirish",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=confidence,
        )
    if domain == "family":
        return AIClassificationResult(
            main_category=CaseLegalCategory.OILAVIY_NIZO,
            sub_category="oila munosabatlari",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=confidence,
        )
    if domain == "labor":
        return AIClassificationResult(
            main_category=CaseLegalCategory.MEHNAT_NIZOSI,
            sub_category="mehnat huquqi",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=confidence,
        )
    if domain in {"tax", "administrative"}:
        return AIClassificationResult(
            main_category=CaseLegalCategory.MAMURIY_YOKI_IQTISODIY_NIZO,
            sub_category=domain,
            procedure_type=ProcedureType.MAMURIY_YOKI_IQTISODIY_SUD,
            confidence=confidence,
        )
    # The legacy enum has no criminal procedure value. Keep the wire contract
    # stable and expose the actual candidate through `candidateLegalDomains`.
    return AIClassificationResult(
        main_category=CaseLegalCategory.UMUMIY_HUQUQIY_MUROJAAT,
        sub_category=domain,
        procedure_type=ProcedureType.SUD_XODIMI_ANIQLAYDI,
        confidence=confidence,
    )


def _merge_token_usage(
    first: dict[str, int] | None,
    second: dict[str, int] | None,
) -> dict[str, int] | None:
    if not first and not second:
        return None
    merged: dict[str, int] = {}
    for source in (first or {}, second or {}):
        for key, value in source.items():
            merged[key] = merged.get(key, 0) + value
    return merged


def _safe_extraction_error(exc: DocumentExtractionError) -> str:
    message = str(exc)
    allowed = {
        "document_text_is_empty",
        "ocr_text_is_empty",
        "all_documents_failed",
    }
    if message in allowed or message.startswith("unsupported_document_type:"):
        return message
    return "document_extraction_failed"
