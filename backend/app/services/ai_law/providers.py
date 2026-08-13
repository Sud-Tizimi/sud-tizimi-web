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


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.sudai_provider == "local":
        return LocalAIProvider()
    if settings.sudai_provider == "remote":
        return OpenAICompatibleProvider(settings)
    raise ProviderError("unsupported_sudai_provider")
