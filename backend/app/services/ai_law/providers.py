"""Provider boundary for the SudAI legal-reasoning layer.

Retrieval, classification and source selection never live in a provider.  A
remote provider receives only the already selected legal context and returns a
small JSON object which the pipeline validates before incorporating it into an
analysis result.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.ai_analysis import (
    AIClassificationResult,
    AICaseDocumentInput,
    AICaseFactualSynthesis,
    AICaseReasoningOutput,
    AIDocumentMetadata,
    AIExtractedLegalObjects,
    AIMatchedSource,
    AIRecommendation,
)
from app.config import Settings
from app.services.ai_law.reasoner import build_explanation, build_recommendation

_log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Faysal AI's legal-document reasoning component.
Return only a JSON object matching the requested schema; no markdown.

Rules:
1. Analyse only the supplied document text and metadata.
2. Treat the supplied retrieval context as the complete set of legal sources.
3. Never invent a law, article, court decision, URL, fact, or source ID.
4. Every `legal_assessment` finding must cite one or more supplied source IDs.
5. Use `document_fact` for facts found in the document and do not attach legal
   source IDs to those facts.
6. If the supplied legal context is insufficient, say so explicitly with an
   `insufficient_context` finding, set context_sufficient=false, and require
   human review.
7. Separate document facts from legal interpretation.  Be conservative with
   confidence and require human review when uncertainty remains.
"""

CASE_SYNTHESIS_SYSTEM_PROMPT = """You are Faysal AI's factual case-synthesis component.
Return only a JSON object matching the requested schema; no markdown.

Rules:
1. Treat every supplied document as part of one case while preserving document boundaries.
2. Extract facts, timeline, entities, typed amounts, cross-document evidence links,
   candidate legal domains/issues, retrieval terms, and uncertainties.
3. Every fact, event, amount, entity, and evidence link must reference supplied document IDs.
4. Do not cite, name, invent, or reason from statutes, articles, decisions, URLs, or legal sources.
5. Type money by its local factual context. Asset value, sale price, payment, debt,
   damage, and salary are different concepts; incidental personal debt is not a debt claim.
6. Candidate domains are retrieval hypotheses, not final legal conclusions.
7. Do not omit a document merely because its facts are corroborative rather than conclusive.
"""

CASE_REASONING_SYSTEM_PROMPT = """You are Faysal AI's case-level legal reasoning component.
Return only a JSON object matching the requested schema; no markdown.

Rules:
1. Reason over the complete supplied factual synthesis, not isolated documents.
2. Treat the supplied retrieval context as the complete set of trusted legal sources.
3. Never invent a law, article, decision, URL, fact, or source ID.
4. Every legal_assessment must cite one or more supplied source IDs.
5. document_fact findings must not cite legal source IDs.
6. If sources do not support the primary candidate domain, return an
   insufficient_context finding, context_sufficient=false, and require human review.
7. Do not replace an unsupported domain with an unrelated domain merely because its
   sources are available. Separate factual conclusion from legal qualification.
"""


class ProviderError(RuntimeError):
    """Safe provider-layer failure; callers must not expose its detail to clients."""


class ProviderTimeoutError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class LegalContextSource(BaseModel):
    """Trusted retrieval source sent to a provider, identified internally."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    law: str
    article: str
    title: str
    excerpt: str
    relevance: float


class AIProviderRequest(BaseModel):
    """Business-layer request shared by local and remote providers."""

    model_config = ConfigDict(extra="forbid")

    document_text: str = Field(min_length=1)
    metadata: AIDocumentMetadata
    classification: AIClassificationResult
    extracted_objects: AIExtractedLegalObjects
    legal_context: list[LegalContextSource]


class AICaseSynthesisProviderRequest(BaseModel):
    """First case pass: bounded documents only, with no legal source context."""

    model_config = ConfigDict(extra="forbid")

    documents: list[AICaseDocumentInput] = Field(min_length=1)


class AICaseReasoningProviderRequest(BaseModel):
    """Second case pass: validated synthesis plus backend-owned legal sources."""

    model_config = ConfigDict(extra="forbid")

    synthesis: AICaseFactualSynthesis
    legal_context: list[LegalContextSource]


@dataclass(frozen=True)
class AIProviderResult:
    """Raw JSON payload plus safe execution metadata from a provider."""

    payload: Any
    provider: str
    model: str | None
    latency_ms: int
    token_usage: dict[str, int] | None = None


class AIProvider(Protocol):
    async def analyze(self, request: AIProviderRequest) -> AIProviderResult: ...

    async def synthesize_case(
        self, request: AICaseSynthesisProviderRequest
    ) -> AIProviderResult: ...

    async def analyze_case(
        self, request: AICaseReasoningProviderRequest
    ) -> AIProviderResult: ...


class LocalAIProvider:
    """Preserves the existing deterministic explanation/recommendation path."""

    async def analyze(self, request: AIProviderRequest) -> AIProviderResult:
        started = time.perf_counter()
        matched_sources = [
            AIMatchedSource(
                law=source.law,
                article=source.article,
                title=source.title,
                excerpt=source.excerpt,
                relevance=source.relevance,
                source_id=source.source_id,
            )
            for source in request.legal_context
        ]
        findings: list[dict[str, Any]] = []
        for source in request.legal_context:
            findings.append(
                {
                    "kind": "legal_assessment",
                    "statement": source.excerpt,
                    "source_ids": [source.source_id],
                }
            )
        if not findings:
            findings.append(
                {
                    "kind": "insufficient_context",
                    "statement": "Aniq huquqiy xulosa uchun retrieval manbalari yetarli emas.",
                    "source_ids": [],
                }
            )
        payload = {
            "explanation": build_explanation(request.classification, matched_sources),
            "confidence_percent": round(request.classification.confidence * 100),
            "human_review": build_recommendation(request.classification).model_dump(),
            "findings": findings,
            "context_sufficient": bool(request.legal_context),
        }
        return AIProviderResult(
            payload=payload,
            provider="local",
            model=None,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    async def synthesize_case(
        self, request: AICaseSynthesisProviderRequest
    ) -> AIProviderResult:
        from app.services.ai_law.case_synthesis import synthesize_case_locally

        started = time.perf_counter()
        synthesis = synthesize_case_locally(request.documents)
        return AIProviderResult(
            payload=synthesis.model_dump(mode="json"),
            provider="local",
            model=None,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    async def analyze_case(
        self, request: AICaseReasoningProviderRequest
    ) -> AIProviderResult:
        from app.services.ai_law.case_synthesis import reason_case_locally

        started = time.perf_counter()
        reasoning = reason_case_locally(request.synthesis, request.legal_context)
        return AIProviderResult(
            payload=reasoning.model_dump(mode="json"),
            provider="local",
            model=None,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible `/chat/completions` JSON provider."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.sudai_base_url.rstrip("/")
        self._api_key = settings.sudai_api_key
        self._model = settings.sudai_model
        self._timeout_s = settings.sudai_timeout_s
        self._max_context_chars = settings.sudai_max_context_chars

    def _assert_configured(self) -> None:
        if not self._base_url or not self._api_key or not self._model:
            raise ProviderError("remote_provider_not_configured")

    async def analyze(self, request: AIProviderRequest) -> AIProviderResult:
        self._assert_configured()
        if len(request.document_text) > self._max_context_chars:
            raise ProviderResponseError("document_context_too_large")

        started = time.perf_counter()
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "document_text": request.document_text,
                            "metadata": request.metadata.model_dump(mode="json"),
                            "classification": request.classification.model_dump(mode="json"),
                            "extracted_objects": request.extracted_objects.model_dump(mode="json"),
                            "legal_context": [
                                source.model_dump(mode="json") for source in request.legal_context
                            ],
                            "required_json_schema": {
                                "explanation": "string",
                                "confidence_percent": "integer 0..100",
                                "human_review": {
                                    "status": "string",
                                    "recommendation": "string",
                                    "risk": "string",
                                },
                                "findings": [
                                    {
                                        "kind": "document_fact|legal_assessment|insufficient_context",
                                        "statement": "string",
                                        "source_ids": "array of supplied source_id values",
                                    }
                                ],
                                "context_sufficient": "boolean",
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        try:
            timeout = httpx.Timeout(self._timeout_s)
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self._api_key}"},
            ) as client:
                response = await asyncio.wait_for(
                    client.post("/chat/completions", json=payload), timeout=self._timeout_s
                )
        except asyncio.TimeoutError as exc:
            raise ProviderTimeoutError("remote_provider_timeout") from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("remote_provider_timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("remote_provider_connection_error") from exc

        if response.status_code >= 400:
            _log.warning("sudai_remote_http_error status=%s", response.status_code)
            raise ProviderError("remote_provider_http_error")
        try:
            body = response.json()
            content = ((body.get("choices") or [])[0].get("message") or {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty_content")
            parsed = json.loads(content)
        except (ValueError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("remote_provider_invalid_json") from exc

        usage = body.get("usage") if isinstance(body, dict) else None
        token_usage = (
            {key: int(value) for key, value in usage.items() if isinstance(value, int)}
            if isinstance(usage, dict)
            else None
        )
        return AIProviderResult(
            payload=parsed,
            provider="openai_compatible",
            model=self._model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            token_usage=token_usage,
        )

    async def synthesize_case(
        self, request: AICaseSynthesisProviderRequest
    ) -> AIProviderResult:
        user_payload = {
            "documents": [
                document.model_dump(mode="json", by_alias=True)
                for document in request.documents
            ],
            "requiredJsonSchema": AICaseFactualSynthesis.model_json_schema(by_alias=True),
        }
        return await self._complete_case_json(CASE_SYNTHESIS_SYSTEM_PROMPT, user_payload)

    async def analyze_case(
        self, request: AICaseReasoningProviderRequest
    ) -> AIProviderResult:
        user_payload = {
            "factualSynthesis": request.synthesis.model_dump(mode="json", by_alias=True),
            "legalContext": [
                source.model_dump(mode="json") for source in request.legal_context
            ],
            "requiredJsonSchema": AICaseReasoningOutput.model_json_schema(by_alias=True),
        }
        return await self._complete_case_json(CASE_REASONING_SYSTEM_PROMPT, user_payload)

    async def _complete_case_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> AIProviderResult:
        """Make one structured case call without exposing credentials or raw errors."""
        self._assert_configured()
        serialized = json.dumps(user_payload, ensure_ascii=False)
        if len(serialized) > self._max_context_chars:
            raise ProviderResponseError("case_context_too_large")

        started = time.perf_counter()
        payload = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": serialized},
            ],
        }
        try:
            timeout = httpx.Timeout(self._timeout_s)
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self._api_key}"},
            ) as client:
                response = await asyncio.wait_for(
                    client.post("/chat/completions", json=payload), timeout=self._timeout_s
                )
        except asyncio.TimeoutError as exc:
            raise ProviderTimeoutError("remote_provider_timeout") from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("remote_provider_timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("remote_provider_connection_error") from exc

        if response.status_code >= 400:
            _log.warning("sudai_remote_http_error status=%s", response.status_code)
            raise ProviderError("remote_provider_http_error")
        try:
            body = response.json()
            content = ((body.get("choices") or [])[0].get("message") or {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty_content")
            parsed = json.loads(content)
        except (ValueError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("remote_provider_invalid_json") from exc

        usage = body.get("usage") if isinstance(body, dict) else None
        token_usage = (
            {key: int(value) for key, value in usage.items() if isinstance(value, int)}
            if isinstance(usage, dict)
            else None
        )
        return AIProviderResult(
            payload=parsed,
            provider="openai_compatible",
            model=self._model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            token_usage=token_usage,
        )


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.sudai_provider == "local":
        return LocalAIProvider()
    if settings.sudai_provider == "remote":
        return OpenAICompatibleProvider(settings)
    raise ProviderError("unsupported_sudai_provider")
