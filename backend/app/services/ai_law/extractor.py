"""Regex-based extraction of structured legal objects from text.

Mirrors the standalone SudAI implementation. Pulls out claimant /
respondent / claim subject / demand summary / contract number / debt
amount / dates / attachments using simple labels (da'vogar, javobgar,
shartnoma raqami, so'm, …).
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.api.schemas.ai_analysis import AIExtractedLegalObjects


def extract_legal_objects(text: str) -> AIExtractedLegalObjects:
    return AIExtractedLegalObjects(
        claimant=_find_after_label(text, ["da'vogar", "davo qiluvchi"]),
        respondent=_find_after_label(text, ["javobgar"]),
        claim_subject=_find_subject(text),
        demand_summary=_find_demand(text),
        contract_number=_first_match(
            text,
            r"(?:shartnoma|kontrakt)\s*(?:raqami|N|№)?\s*[:#№-]?\s*([A-Za-z0-9/-]+)",
        ),
        debt_amount=_first_match(text, r"(\d[\d\s.,]*\s*(?:so'm|sum|uzs))"),
        dates=re.findall(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text),
        attachments=_find_attachments(text),
    )


def _find_after_label(text: str, labels: List[str]) -> Optional[str]:
    for label in labels:
        match = re.search(rf"{label}\s*[:\-]\s*([^\n,.;]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _first_match(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _find_subject(text: str) -> Optional[str]:
    match = re.search(r"(?:da'vo predmeti|talab)\s*[:\-]\s*([^\n.]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _find_demand(text: str) -> Optional[str]:
    match = re.search(
        r"(?:so'rayman|suddan so'rayman)\s*[:\-]?\s*(.{20,300})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return " ".join(match.group(1).split())[:300]


def _find_attachments(text: str) -> List[str]:
    match = re.search(r"(?:ilova|ilovalar)\s*[:\-]\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    raw_items = re.split(r"[\n;]+", match.group(1))
    return [
        item.strip(" -0123456789.)")
        for item in raw_items
        if item.strip()
    ][:10]
