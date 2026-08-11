"""Thin async OpenRouter client for live-transcript post-processing.

We only need ONE thing from OpenRouter: clean up obviously mangled ASR
output (punctuation, split numbers like "1 1 7" -> "117", double spaces).
We DO NOT rewrite wording. If anything fails (no key, HTTP error, timeout,
malformed response), we return the original text untouched.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

log = logging.getLogger("openrouter")

SYSTEM_PROMPT = (
    "You are a post-processor for Russian-language live court transcription. "
    "Your job is NORMALIZATION ONLY — do not change wording, do not add or remove facts. "
    "Allowed operations: "
    "(1) add or fix punctuation; "
    "(2) fix obvious ASR word-splitting (e.g. 'статьей 1 1 7' -> 'статьей 117'); "
    "(3) normalize capitalization at sentence starts; "
    "(4) collapse accidental double spaces. "
    "Output the corrected sentence and nothing else. "
    "If the input is already clean, return it verbatim."
)


class OpenRouterService:
    def __init__(
        self, api_key: str, base_url: str, model: str, timeout_s: float
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(self._timeout_s, connect=2.0)
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://faysal-ai.local",
                    "X-Title": "Faysal AI STT Post-Processor",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            finally:
                self._client = None

    async def normalize(self, text: str) -> str:
        """Return normalized text. Falls back to the input on any error / missing key."""
        if not self.enabled:
            return text
        if not text or not text.strip():
            return text
        try:
            client = await self._get_client()
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.0,
                "max_tokens": 256,
                "stream": False,
            }
            r = await client.post("/chat/completions", json=payload)
            if r.status_code != 200:
                log.warning(
                    "openrouter_http_%s body=%s",
                    r.status_code,
                    r.text[:200].replace("\n", " "),
                )
                return text
            data = r.json()
            choices = data.get("choices") or []
            if not choices:
                return text
            out = (choices[0].get("message") or {}).get("content") or ""
            out = out.strip()
            return out or text
        except httpx.TimeoutException as e:
            log.warning("openrouter_timeout: %s", e)
            return text
        except httpx.HTTPError as e:
            log.warning("openrouter_http_error: %s", e)
            return text
        except Exception as e:  # noqa: BLE001
            log.exception("openrouter_unexpected: %s", e)
            return text
