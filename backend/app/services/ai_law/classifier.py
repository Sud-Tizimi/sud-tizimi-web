"""Keyword-based legal-domain classifier for analysed documents.

Behaviour identical to ``sudai-research-raw/app/services/classifier.py``,
but the rule table now references :class:`CaseLegalCategory` and
:class:`ProcedureType` enums instead of free Uzbek strings, so the
results are storable and i18n-friendly downstream.
"""
from __future__ import annotations

from typing import Optional, Tuple

from app.api.schemas.ai_analysis import AIClassificationResult
from app.core.enums import CaseLegalCategory, ProcedureType


# (keyword_tuple, classification). Keywords are matched in lowercase
# against the document text. The rule with the most keyword hits wins.
CATEGORY_RULES: list[Tuple[Tuple[str, ...], AIClassificationResult]] = [
    (
        ("aliment", "nikoh", "farzand", "otalik", "ajrashish"),
        AIClassificationResult(
            main_category=CaseLegalCategory.OILAVIY_NIZO,
            sub_category="oila munosabatlari",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=0.86,
        ),
    ),
    (
        ("ish haqi", "mehnat shartnomasi", "bo'shatish", "ishga tiklash"),
        AIClassificationResult(
            main_category=CaseLegalCategory.MEHNAT_NIZOSI,
            sub_category="mehnat huquqi",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=0.84,
        ),
    ),
    (
        ("soliq", "penya", "jarima", "kameral", "hisobvaraq"),
        AIClassificationResult(
            main_category=CaseLegalCategory.MAMURIY_YOKI_IQTISODIY_NIZO,
            sub_category="soliq nizosi",
            procedure_type=ProcedureType.MAMURIY_YOKI_IQTISODIY_SUD,
            confidence=0.78,
        ),
    ),
    (
        ("qarz", "qarzdorlik", "tilxat", "kredit", "qarz shartnomasi", "shartnoma bo'yicha"),
        AIClassificationResult(
            main_category=CaseLegalCategory.FUQAROLIK_ISHI,
            sub_category="qarz undirish",
            procedure_type=ProcedureType.FUQAROLIK_SUD,
            confidence=0.91,
        ),
    ),
]


def detect_document_type(text: str) -> str:
    """Return a free-text Uzbek label describing the document kind.

    The label is later mapped to our ``DocumentType`` enum by
    :func:`app.api.schemas.document_type_mapper.map_document_type`.
    Returning the raw label here keeps the classifier self-contained.
    """
    lowered = text.lower()
    if "da'vo arizasi" in lowered or "davo arizasi" in lowered:
        return "da'vo arizasi"
    if "iltimosnoma" in lowered:
        return "iltimosnoma"
    if "e'tiroz" in lowered or "etiroz" in lowered:
        return "e'tiroz"
    if "qarshi da'vo" in lowered or "qarshi davo" in lowered:
        return "qarshi da'vo"
    if "shikoyat" in lowered:
        return "shikoyat"
    return "aniqlanmagan hujjat"


def classify(text: str) -> AIClassificationResult:
    """Pick the best matching category and bump confidence by extra hits.

    The bump is +0.03 per keyword above the first match, capped at 0.97.
    When no rule matches, returns a generic "manual review" classification
    at 0.55 confidence.
    """
    lowered = text.lower()
    best_result: Optional[AIClassificationResult] = None
    best_matches = 0

    for keywords, result in CATEGORY_RULES:
        matches = sum(1 for keyword in keywords if keyword in lowered)
        if matches > best_matches:
            best_matches = matches
            best_result = result

    if best_result:
        confidence = min(best_result.confidence + (best_matches - 1) * 0.03, 0.97)
        return best_result.model_copy(update={"confidence": round(confidence, 2)})

    return AIClassificationResult(
        main_category=CaseLegalCategory.UMUMIY_HUQUQIY_MUROJAAT,
        sub_category="qo'lda tekshirish kerak",
        procedure_type=ProcedureType.SUD_XODIMI_ANIQLAYDI,
        confidence=0.55,
    )
