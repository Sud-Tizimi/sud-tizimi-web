"""PII/PHI redaction for analysed legal documents.

The patterns are tuned for Uzbek formats (phone, passport, JSHSHIR/PINFL,
STIR, addresses, F.I.Sh. with patronymic suffixes). Behaviour matches
the original ``sudai-research-raw/app/services/anonymizer.py`` — only
the schema import is rewired to live inside Sud-Tizimi.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import List, Tuple

from app.api.schemas.ai_analysis import AIAnonymizationEntity
from app.core.enums import AnonymizationLabel

# Each pattern is paired with its enum value so the rest of the codebase
# can use :class:`AnonymizationLabel` directly instead of free strings.
PATTERNS: List[Tuple[AnonymizationLabel, re.Pattern[str]]] = [
    (
        AnonymizationLabel.PHONE,
        re.compile(r"(?:\+998|998)?\s?\(?\d{2}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}"),
    ),
    (
        AnonymizationLabel.PASSPORT,
        re.compile(r"\b[A-Z]{2}\d{7}\b"),
    ),
    (
        AnonymizationLabel.JSHSHIR,
        re.compile(r"\b\d{14}\b"),
    ),
    (
        AnonymizationLabel.STIR,
        re.compile(r"\b\d{9}\b"),
    ),
    (
        AnonymizationLabel.ADDRESS,
        re.compile(
            r"\b(?:Toshkent|Andijon|Farg'ona|Fargona|Namangan|Samarqand|Buxoro|Navoiy|Xorazm|"
            r"Qashqadaryo|Surxondaryo|Jizzax|Sirdaryo|Qoraqalpog'iston)"
            r"[^.\n]{0,80}(?:ko'chasi|tumani|shahar|viloyati|mahallasi)\b",
            re.IGNORECASE,
        ),
    ),
    (
        AnonymizationLabel.FISH,
        re.compile(
            r"\b[A-Z][a-zA-Z'`-]+(?:ev|ova|yev|yeva|ov|ina)?\s+"
            r"[A-Z][a-zA-Z'`-]+\s+"
            r"[A-Z][a-zA-Z'`-]+(?:ovich|ovna|evich|yevich|qizi|o'g'li)\b"
        ),
    ),
]


def anonymize(text: str) -> Tuple[str, List[AIAnonymizationEntity]]:
    """Return ``(anonymized_text, entities)``.

    Each match is replaced by a stable placeholder of the form
    ``[LABEL_N]`` (e.g. ``[PHONE_1]``) so the same PII appearing twice
    in the same document is consistently redacted and reported once.
    """
    anonymized = text
    counters: defaultdict[AnonymizationLabel, int] = defaultdict(int)
    entities: list[AIAnonymizationEntity] = []
    seen: dict[tuple[AnonymizationLabel, str], str] = {}

    for label, pattern in PATTERNS:
        def replace(match: re.Match[str], _label: AnonymizationLabel = label) -> str:
            original = match.group(0)
            key = (_label, original)
            if key not in seen:
                counters[_label] += 1
                placeholder = f"[{_label.value.upper()}_{counters[_label]}]"
                seen[key] = placeholder
                entities.append(
                    AIAnonymizationEntity(
                        label=_label,
                        original=original,
                        placeholder=placeholder,
                    )
                )
            return seen[key]

        anonymized = pattern.sub(replace, anonymized)

    return anonymized, entities
