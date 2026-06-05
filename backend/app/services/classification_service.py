"""Filename-keyword classifier.

Ported from the original frontend's ``pickClassification`` (which lived in
``caseStore.ts`` before Phase A). It's deterministic, runs in <1ms, and
gives a confidence score that lines up with the seeded mock data — so the
demo experience post-Phase-B matches the pre-MySQL CP1 demo.

A real AI engine is a CP2 / future concern. This module returns a
``ClassifyResult`` so the rest of the code can stay engine-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import DocumentCategory, DocumentFileType, DocumentType


@dataclass(frozen=True)
class ClassifyResult:
    category: DocumentCategory
    detected_type: DocumentType
    detected_type_label: str
    ai_confidence: int  # 0..100


# Keyword → (category, type, label, confidence)
_RULES: list[tuple[tuple[str, ...], DocumentCategory, DocumentType, str, int]] = [
    (("claim",), DocumentCategory.PROCEDURAL, DocumentType.CLAIM, "Claim", 96),
    (("counterclaim",), DocumentCategory.PROCEDURAL, DocumentType.COUNTERCLAIM, "Counterclaim", 86),
    (("appeal",), DocumentCategory.PROCEDURAL, DocumentType.APPEAL, "Appeal", 93),
    (("cassation",), DocumentCategory.PROCEDURAL, DocumentType.CASSATION_APPEAL, "Cassation Appeal", 91),
    (("statement",), DocumentCategory.PROCEDURAL, DocumentType.STATEMENT, "Statement", 90),
    (("explanation",), DocumentCategory.PARTICIPANT, DocumentType.EXPLANATION, "Explanation", 84),
    (("objection",), DocumentCategory.PARTICIPANT, DocumentType.OBJECTION, "Objection", 87),
    (("additional",), DocumentCategory.PARTICIPANT, DocumentType.ADDITIONAL_STATEMENT, "Additional Statement", 81),
    (("contract", "agreement"), DocumentCategory.EVIDENCE, DocumentType.CONTRACT, "Contract", 91),
    (("financial", "invoice", "receipt", "bank"), DocumentCategory.EVIDENCE, DocumentType.FINANCIAL_DOCUMENT, "Financial Document", 89),
    (("id", "passport", "license"), DocumentCategory.EVIDENCE, DocumentType.PERSONAL_DOCUMENT, "Personal Document", 88),
    (("court_decision", "decision"), DocumentCategory.COURT, DocumentType.COURT_DECISION, "Court Decision", 95),
    (("court_resolution", "resolution", "order"), DocumentCategory.COURT, DocumentType.COURT_RESOLUTION, "Court Resolution", 95),
    (("transcript", "hearing", "protocol"), DocumentCategory.COURT, DocumentType.HEARING_TRANSCRIPT, "Hearing Transcript", 92),
]


def classify(file_name: str, file_type: DocumentFileType) -> ClassifyResult:
    """Return a deterministic classification for the file.

    Falls back to ``(procedural, statement, "Statement", 70)`` for any
    filename that doesn't match a known keyword. The 70 baseline keeps the
    confidence bar amber rather than red, signalling "we don't really know".
    """
    name = (file_name or "").lower()
    for keywords, cat, dtype, label, conf in _RULES:
        if any(kw in name for kw in keywords):
            return ClassifyResult(cat, dtype, label, conf)
    # Image default: most likely a personal document
    if file_type in (DocumentFileType.JPG, DocumentFileType.PNG):
        return ClassifyResult(
            DocumentCategory.EVIDENCE,
            DocumentType.PERSONAL_DOCUMENT,
            "Personal Document",
            80,
        )
    return ClassifyResult(
        DocumentCategory.PROCEDURAL,
        DocumentType.STATEMENT,
        "Statement",
        70,
    )
