"""Regression tests for hybrid deterministic retrieval + LLM reasoning."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.schemas.ai_analysis import (
    AIAnalysisResponse,
    AIAnalysisTechnicalMetadata,
    AIClassificationResult,
    AIDocumentMetadata,
    AIExtractedLegalObjects,
    AIMatchedSource,
    AIRecommendation,
    analysis_result_to_api,
)
from app.core.enums import CaseLegalCategory, DocumentLanguage, ProcedureType, UserRole
from app.services import ai_analyze_service
from app.services.ai_law import pipeline
from app.services.ai_law.providers import (
    AIProviderResult,
    ProviderResponseError,
    ProviderTimeoutError,
)


class _FakeProvider:
    def __init__(self, payload_factory):
        self.payload_factory = payload_factory
        self.requests = []

    async def analyze(self, request):
        self.requests.append(request)
        return AIProviderResult(
            payload=self.payload_factory(request),
            provider="fake_openai_compatible",
            model="fake-model",
            latency_ms=7,
            token_usage={"total_tokens": 12},
        )


class _RecordingSession:
    def __init__(self, document):
        self.document = document
        self.added = []
        self.flushed = 0
        self.committed = 0

    async def get(self, _model, _id):
        return self.document

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        self.flushed += 1

    async def commit(self):
        self.committed += 1


def _reasoning_payload(request):
    source_id = request.legal_context[0].source_id
    return {
        "explanation": "Retrieval context bilan cheklangan tekshiruv bajarildi.",
        "confidence_percent": 72,
        "human_review": {
            "status": "qo'lda tekshirish kerak",
            "recommendation": "Sud xodimi hujjat va manbalarni tekshirishi kerak.",
            "risk": "Kontekst cheklangan bo'lishi mumkin.",
        },
        "findings": [
            {
                "kind": "legal_assessment",
                "statement": "Majburiyatga oid retrieval manbasi mavjud.",
                "source_ids": [source_id],
            }
        ],
        "context_sufficient": True,
    }


def _analysis_response() -> AIAnalysisResponse:
    return AIAnalysisResponse(
        metadata=AIDocumentMetadata(
            document_type="da'vo arizasi",
            language=DocumentLanguage.UZBEK_LATIN,
            pages=1,
            ocr_required=False,
        ),
        anonymized_text="Qarz va shartnoma bo'yicha da'vo arizasi.",
        anonymized_entities=[],
        extracted_objects=AIExtractedLegalObjects(),
        classification=AIClassificationResult(
            main_category=CaseLegalCategory.FUQAROLIK_ISHI,
            sub_category="qarz undirish",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=0.72,
        ),
        matched_sources=[
            AIMatchedSource(
                law="Fuqarolik kodeksi",
                article="234-modda",
                title="Majburiyat",
                excerpt="Majburiyat shartnoma asosida kelib chiqadi.",
                relevance=0.9,
                source_id="trusted-source",
            )
        ],
        explanation="Tekshiruv bajarildi.",
        confidence_percent=72,
        human_review=AIRecommendation(
            status="qo'lda tekshirish kerak", recommendation="Tekshirish", risk="Xavf"
        ),
        technical_metadata=AIAnalysisTechnicalMetadata(
            analysis_mode="llm", provider="fake_openai_compatible", model="fake-model"
        ),
    )


class HybridProviderPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_structured_reasoning_receives_retrieval_and_keeps_sources_trusted(self):
        provider = _FakeProvider(_reasoning_payload)
        with patch.object(pipeline, "build_ai_provider", return_value=provider):
            result = await pipeline.analyze_text(
                "Da'vo arizasida qarzdorlik va shartnoma bo'yicha qarzni undirish so'ralgan."
            )

        self.assertEqual(len(provider.requests), 1)
        self.assertTrue(provider.requests[0].legal_context)
        self.assertEqual(result.technical_metadata.analysis_mode, "llm")
        self.assertEqual(result.technical_metadata.provider, "fake_openai_compatible")
        self.assertEqual(result.matched_sources[0].law, "Fuqarolik kodeksi")
        self.assertTrue(result.findings[0].source_ids[0].startswith("rag:0:"))

    async def test_citation_injection_is_rejected_and_never_becomes_a_trusted_source(self):
        def injected(_request):
            payload = _reasoning_payload(_request)
            payload["findings"][0]["source_ids"] = ["Article-123-not-retrieved"]
            return payload

        with patch.object(pipeline, "build_ai_provider", return_value=_FakeProvider(injected)):
            with self.assertRaisesRegex(ProviderResponseError, "untrusted_citation"):
                await pipeline.analyze_text("Qarz shartnomasi bo'yicha qarzdorlik undiriladi.")

    async def test_invalid_structured_response_is_a_controlled_provider_error(self):
        with patch.object(
            pipeline, "build_ai_provider", return_value=_FakeProvider(lambda _request: {"bad": True})
        ):
            with self.assertRaisesRegex(ProviderResponseError, "schema_error"):
                await pipeline.analyze_text("Qarz shartnomasi bo'yicha qarzdorlik undiriladi.")

    async def test_empty_retrieval_context_requires_explicit_insufficiency_disclosure(self):
        def unsupported_context(request):
            self.assertEqual(request.legal_context, [])
            return {
                "explanation": "Aniq xulosa berildi.",
                "confidence_percent": 90,
                "human_review": {"status": "ok", "recommendation": "ok", "risk": "ok"},
                "findings": [{"kind": "document_fact", "statement": "Fakt", "source_ids": []}],
                "context_sufficient": True,
            }

        with (
            patch.object(pipeline, "retrieve_sources", return_value=[]),
            patch.object(
                pipeline,
                "build_ai_provider",
                return_value=_FakeProvider(unsupported_context),
            ),
        ):
            with self.assertRaisesRegex(ProviderResponseError, "missing_context_disclosure"):
                await pipeline.analyze_text("Mazmuni aniq bo'lmagan murojaat.")

    async def test_local_mode_requires_no_remote_credentials(self):
        # The local provider is the existing rules/RAG implementation behind
        # the same provider interface, so no API key participates here.
        from app.services.ai_law.providers import LocalAIProvider

        with patch.object(pipeline, "build_ai_provider", return_value=LocalAIProvider()):
            result = await pipeline.analyze_text("Qarz shartnomasi bo'yicha qarzdorlik undiriladi.")

        self.assertEqual(result.technical_metadata.analysis_mode, "local")
        self.assertEqual(result.technical_metadata.provider, "local")
        self.assertTrue(result.matched_sources)


class AnalysisPersistenceAndContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_analysis_is_done_and_serializes_camelcase_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claim.pdf"
            path.write_bytes(b"pdf bytes")
            document = SimpleNamespace(
                id="doc-1",
                case_id="case-1",
                uploader_id="assistant-1",
                storage_path="claim.pdf",
                file_name="claim.pdf",
            )
            actor = SimpleNamespace(id="assistant-1", role=UserRole.ASSISTANT)
            case = SimpleNamespace(id="case-1", assistant_id="assistant-1")
            session = _RecordingSession(document)

            with (
                patch.object(ai_analyze_service.case_service, "get_case_in_scope", new=AsyncMock(return_value=case)),
                patch.object(ai_analyze_service.activity_service, "record_event", new=AsyncMock()),
                patch.object(ai_analyze_service, "resolve_storage_path", return_value=path),
                patch.object(ai_analyze_service, "pipeline_analyze_document", new=AsyncMock(return_value=_analysis_response())),
            ):
                analysis = await ai_analyze_service.analyze_document(
                    session, actor=actor, document_id=document.id
                )

        self.assertEqual(analysis.status.value, "done")
        self.assertTrue(analysis.result_json)
        public = analysis_result_to_api(analysis.result_json)
        assert public is not None
        self.assertIn("confidencePercent", public)
        self.assertIn("humanReview", public)
        self.assertIn("matchedSources", public)
        self.assertIn("technicalMetadata", public)
        self.assertNotIn("confidence_percent", public)

    async def test_timeout_provider_error_marks_analysis_failed_without_raw_client_detail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claim.pdf"
            path.write_bytes(b"pdf bytes")
            document = SimpleNamespace(
                id="doc-2",
                case_id="case-2",
                uploader_id="assistant-2",
                storage_path="claim.pdf",
                file_name="claim.pdf",
            )
            actor = SimpleNamespace(id="assistant-2", role=UserRole.ASSISTANT)
            case = SimpleNamespace(id="case-2", assistant_id="assistant-2")
            session = _RecordingSession(document)
            with (
                patch.object(ai_analyze_service.case_service, "get_case_in_scope", new=AsyncMock(return_value=case)),
                patch.object(ai_analyze_service.activity_service, "record_event", new=AsyncMock()),
                patch.object(ai_analyze_service, "resolve_storage_path", return_value=path),
                patch.object(
                    ai_analyze_service,
                    "pipeline_analyze_document",
                    new=AsyncMock(side_effect=ProviderTimeoutError("socket secret detail")),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await ai_analyze_service.analyze_document(
                        session, actor=actor, document_id=document.id
                    )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "ai_analysis_failed")
        self.assertEqual(session.added[0].status.value, "failed")
        self.assertEqual(session.added[0].error_message, "analysis_failed")
        self.assertIsNone(session.added[0].result_json)
