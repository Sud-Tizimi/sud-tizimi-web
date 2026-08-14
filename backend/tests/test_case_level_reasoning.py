"""Regression coverage for factual-first, two-pass case-level reasoning."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from docx import Document as DocxDocument

from app.api.schemas.ai_analysis import (
    AICaseDocumentInput,
    AIMatchedSource,
)
from app.core.enums import CaseLegalCategory
from app.services.ai_law import case_pipeline, rag
from app.services.ai_law.case_pipeline import CaseDocumentSource
from app.services.ai_law.case_synthesis import synthesize_case_locally
from app.services.ai_law.classifier import classify
from app.services.ai_law.providers import (
    AIProviderResult,
    LocalAIProvider,
    ProviderResponseError,
)


CASE_DOCUMENTS = [
    (
        "doc-inventory",
        "01_inventory.docx",
        "Inventar dalolatnomasi. Tashkilotga tegishli portativ kompyuterning "
        "seriya raqami ZX-84Q2-PL. Uning balans qiymati 17 800 000 so'm. "
        "Xodimga ushbu mulkni olib chiqish uchun ruxsat berilmagan.",
    ),
    (
        "doc-access-video",
        "02_access_video.docx",
        "Kirish kartasi xodimning ish vaqtidan keyin xonaga kirganini qayd etdi. "
        "Kamera videoyozuvida xodimning qurilma bilan chiqishi ko'rinadi. "
        "Bu vaqtda xonada boshqa shaxs bo'lmagan.",
    ),
    (
        "doc-buyer-payment",
        "03_buyer_payment.docx",
        "Покупатель сообщил, что сотрудник продал ему устройство за 9 000 000 сум. "
        "Оплата поступила на банковскую карту сотрудника. Серийный номер "
        "ZX-84Q2-PL совпадает с номером переданного устройства.",
    ),
    (
        "doc-admission",
        "04_admission.docx",
        "Xodim qurilmani ruxsatsiz olib chiqqanini va uchinchi shaxsga sotganini "
        "tan oldi. Sotuvdan olingan pulning bir qismi shaxsiy qarzlarini "
        "to'lashga sarflanganini tasdiqladi.",
    ),
]


def _case_inputs() -> list[AICaseDocumentInput]:
    return [
        AICaseDocumentInput(document_id=document_id, filename=filename, text=text)
        for document_id, filename, text in CASE_DOCUMENTS
    ]


def _synthetic_criminal_source() -> AIMatchedSource:
    return AIMatchedSource(
        law="Synthetic criminal property test corpus",
        article="test-article",
        title="Test-only trusted property source",
        excerpt="Test fixture: property evidence must be assessed as one evidentiary chain.",
        relevance=0.94,
        source_id="test-criminal-source",
        category_path="criminal/property/test-only",
    )


class _FakeRemoteCaseProvider:
    def __init__(self, *, inject_unknown_citation: bool = False) -> None:
        self.inject_unknown_citation = inject_unknown_citation
        self.synthesis_requests = []
        self.reasoning_requests = []

    async def analyze(self, _request):  # pragma: no cover - must never be used by case flow
        raise AssertionError("document provider pass must not run in case pipeline")

    async def synthesize_case(self, request):
        self.synthesis_requests.append(request)
        synthesis = synthesize_case_locally(request.documents)
        return AIProviderResult(
            payload=synthesis.model_dump(mode="json"),
            provider="fake_openai_compatible",
            model="fake-case-model",
            latency_ms=11,
            token_usage={"total_tokens": 101},
        )

    async def analyze_case(self, request):
        self.reasoning_requests.append(request)
        source_ids = [source.source_id for source in request.legal_context]
        cited = ["rag:unknown:injected"] if self.inject_unknown_citation else source_ids[:1]
        findings = [
            {
                "kind": "document_fact",
                "statement": "Barcha hujjatlardagi faktlar yagona dalillar zanjiriga birlashtirildi.",
                "source_ids": [],
            }
        ]
        if cited:
            findings.append(
                {
                    "kind": "legal_assessment",
                    "statement": "Huquqiy baho faqat test uchun berilgan trusted source bilan cheklangan.",
                    "source_ids": cited,
                }
            )
        else:
            findings.append(
                {
                    "kind": "insufficient_context",
                    "statement": "Candidate domain uchun trusted source topilmadi.",
                    "source_ids": [],
                }
            )
        return AIProviderResult(
            payload={
                "primary_conclusion": (
                    "Mulkka egalik, kirish, video, olib chiqish, sotuv, to'lov, "
                    "seriya raqami va tan olish dalillari o'zaro bog'langan."
                ),
                "explanation": "Yagona case synthesis asosida ikki bosqichli tahlil bajarildi.",
                "evidence_summary": [fact.statement for fact in request.synthesis.facts],
                "confidence_percent": 82 if source_ids else 60,
                "human_review": {
                    "status": "xodim tasdiqlashi kerak" if source_ids else "qo'lda tekshirish kerak",
                    "recommendation": "Dalillar va trusted sources tekshirilsin.",
                    "risk": "Yakuniy huquqiy kvalifikatsiya inson nazoratini talab qiladi.",
                },
                "findings": findings,
                "context_sufficient": bool(source_ids),
            },
            provider="fake_openai_compatible",
            model="fake-case-model",
            latency_ms=13,
            token_usage={"total_tokens": 202},
        )


def _write_docx(path: Path, text: str) -> None:
    document = DocxDocument()
    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)
    document.save(path)


class DeterministicCaseSynthesisTests(unittest.TestCase):
    def test_four_documents_are_linked_without_turning_asset_value_into_debt(self):
        synthesis = synthesize_case_locally(_case_inputs())

        self.assertEqual(set(synthesis.document_ids), {item[0] for item in CASE_DOCUMENTS})
        self.assertEqual(
            {document_id for fact in synthesis.facts for document_id in fact.document_ids},
            set(synthesis.document_ids),
        )
        typed = {(amount.amount, amount.amount_type) for amount in synthesis.amounts}
        self.assertIn(("17 800 000 so'm", "asset_value"), typed)
        self.assertIn(("9 000 000 сум", "sale_price"), typed)
        self.assertNotIn("debt", {amount.amount_type for amount in synthesis.amounts})
        self.assertEqual(synthesis.candidate_legal_domains[0].domain, "criminal_property")
        self.assertNotIn(
            "civil_debt", {candidate.domain for candidate in synthesis.candidate_legal_domains}
        )

        serial_links = [link for link in synthesis.evidence_links if "ZX-84Q2-PL" in link.identifiers]
        self.assertEqual(len(serial_links), 1)
        self.assertEqual(
            set(serial_links[0].document_ids),
            {"doc-inventory", "doc-buyer-payment"},
        )
        chain = next(
            link for link in synthesis.evidence_links if "admission" in link.identifiers
        )
        self.assertTrue(
            {"access", "video", "taking", "sale", "payment", "admission"}.issubset(
                set(chain.identifiers)
            )
        )

    def test_plain_concatenation_with_legacy_classifier_is_explicitly_not_the_fix(self):
        combined = "\n".join(text for _, _, text in CASE_DOCUMENTS)
        legacy = classify(combined)

        self.assertEqual(legacy.main_category, CaseLegalCategory.FUQAROLIK_ISHI)
        self.assertEqual(legacy.sub_category, "qarz undirish")
        synthesis = synthesize_case_locally(_case_inputs())
        self.assertEqual(synthesis.candidate_legal_domains[0].domain, "criminal_property")

    def test_case_retrieval_filters_family_tax_and_discloses_missing_domain_corpus(self):
        synthesis = synthesize_case_locally(_case_inputs())
        unrelated = [
            AIMatchedSource(
                law="Oila kodeksi",
                article="96-modda",
                title="Ta'minot",
                excerpt="Oila huquqi.",
                relevance=0.95,
            ),
            AIMatchedSource(
                law="Soliq kodeksi",
                article="220-modda",
                title="Soliq qarzdorligi",
                excerpt="Soliq huquqi.",
                relevance=0.95,
            ),
            _synthetic_criminal_source(),
        ]
        with patch.object(rag, "_retrieve_from_lexuz", return_value=unrelated):
            matched = rag.retrieve_case_sources(synthesis)
        self.assertEqual([source.law for source in matched], ["Synthetic criminal property test corpus"])

        with patch.object(rag, "_retrieve_from_lexuz", return_value=[]):
            self.assertEqual(rag.retrieve_case_sources(synthesis), [])
        self.assertEqual(
            rag._preferred_law_terms("shaxsiy qarzlarini to'lash", "criminal_property"),
            ["Jinoyat kodeksi", "Жиноят кодекси", "Уголовный кодекс"],
        )


class TwoPassCasePipelineTests(unittest.IsolatedAsyncioTestCase):
    async def _sources(self, temp_dir: str) -> list[CaseDocumentSource]:
        sources = []
        for document_id, filename, text in CASE_DOCUMENTS:
            path = Path(temp_dir) / filename
            _write_docx(path, text)
            sources.append(CaseDocumentSource(document_id, filename, path))
        return sources

    async def test_fake_remote_receives_all_documents_before_retrieval_and_reasons_second(self):
        provider = _FakeRemoteCaseProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            sources = await self._sources(temp_dir)
            with (
                patch.object(case_pipeline, "build_ai_provider", return_value=provider),
                patch.object(
                    case_pipeline,
                    "retrieve_case_sources",
                    return_value=[_synthetic_criminal_source()],
                ) as retrieval,
            ):
                result = await case_pipeline.analyze_case_documents(sources)

        self.assertEqual(len(provider.synthesis_requests), 1)
        first_request = provider.synthesis_requests[0]
        self.assertFalse(hasattr(first_request, "legal_context"))
        self.assertEqual(
            {document.document_id for document in first_request.documents},
            {item[0] for item in CASE_DOCUMENTS},
        )
        retrieval.assert_called_once()
        self.assertEqual(len(provider.reasoning_requests), 1)
        second_request = provider.reasoning_requests[0]
        self.assertEqual(set(second_request.synthesis.document_ids), {item[0] for item in CASE_DOCUMENTS})
        self.assertEqual(len(second_request.legal_context), 1)
        self.assertTrue(second_request.legal_context[0].source_id.startswith("rag:0:"))

        response = result.response
        self.assertEqual(response.candidate_legal_domains[0].domain, "criminal_property")
        self.assertIsNone(response.extracted_objects.debt_amount)
        self.assertTrue(response.primary_conclusion)
        self.assertEqual(response.technical_metadata.analysis_mode, "llm")
        self.assertEqual(response.technical_metadata.token_usage, {"total_tokens": 303})
        self.assertEqual(
            {amount.amount_type for amount in response.typed_amounts},
            {"asset_value", "sale_price"},
        )
        self.assertTrue(response.findings[-1].source_ids[0].startswith("rag:0:"))

    async def test_local_mode_returns_insufficient_context_not_fake_civil_conclusion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sources = await self._sources(temp_dir)
            with (
                patch.object(case_pipeline, "build_ai_provider", return_value=LocalAIProvider()),
                patch.object(case_pipeline, "retrieve_case_sources", return_value=[]),
            ):
                result = await case_pipeline.analyze_case_documents(sources)

        response = result.response
        self.assertEqual(response.technical_metadata.analysis_mode, "local")
        self.assertEqual(response.candidate_legal_domains[0].domain, "criminal_property")
        self.assertEqual(response.classification.main_category, CaseLegalCategory.UMUMIY_HUQUQIY_MUROJAAT)
        self.assertEqual(response.classification.sub_category, "criminal_property")
        self.assertIsNone(response.extracted_objects.debt_amount)
        self.assertEqual(response.matched_sources, [])
        self.assertEqual(response.human_review.status, "qo'lda tekshirish kerak")
        self.assertTrue(any(finding.kind == "insufficient_context" for finding in response.findings))
        self.assertNotIn("fuqarolik-huquqiy", response.explanation)

    async def test_fake_remote_without_domain_sources_must_disclose_insufficient_context(self):
        provider = _FakeRemoteCaseProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            sources = await self._sources(temp_dir)
            with (
                patch.object(case_pipeline, "build_ai_provider", return_value=provider),
                patch.object(case_pipeline, "retrieve_case_sources", return_value=[]),
            ):
                result = await case_pipeline.analyze_case_documents(sources)

        response = result.response
        self.assertEqual(response.matched_sources, [])
        self.assertEqual(response.human_review.status, "qo'lda tekshirish kerak")
        self.assertTrue(any(finding.kind == "insufficient_context" for finding in response.findings))
        self.assertFalse(provider.reasoning_requests[0].legal_context)

    async def test_invalid_case_synthesis_is_a_controlled_schema_error(self):
        provider = _FakeRemoteCaseProvider()
        provider.synthesize_case = AsyncMock(
            return_value=AIProviderResult(
                payload={"unexpected": True},
                provider="fake_openai_compatible",
                model="fake-case-model",
                latency_ms=1,
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            sources = await self._sources(temp_dir)
            with patch.object(case_pipeline, "build_ai_provider", return_value=provider):
                with self.assertRaisesRegex(ProviderResponseError, "case_synthesis_schema_error"):
                    await case_pipeline.analyze_case_documents(sources)

    async def test_case_reasoning_unknown_citation_is_rejected(self):
        provider = _FakeRemoteCaseProvider(inject_unknown_citation=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            sources = await self._sources(temp_dir)
            with (
                patch.object(case_pipeline, "build_ai_provider", return_value=provider),
                patch.object(
                    case_pipeline,
                    "retrieve_case_sources",
                    return_value=[_synthetic_criminal_source()],
                ),
            ):
                with self.assertRaisesRegex(ProviderResponseError, "untrusted_citation"):
                    await case_pipeline.analyze_case_documents(sources)


if __name__ == "__main__":
    unittest.main()
