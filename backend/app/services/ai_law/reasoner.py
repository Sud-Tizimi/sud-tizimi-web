"""Build human-readable explanations and human-review recommendations.

The 0.85 confidence threshold that decides between "tasdiqlash kerak"
(awaiting staff review) and "qo'lda tekshirish kerak" (manual review
required) is pulled from :class:`app.config.Settings` so it can be
tuned per deployment.
"""
from __future__ import annotations

from typing import List

from app.api.schemas.ai_analysis import (
    AIClassificationResult,
    AIMatchedSource,
    AIRecommendation,
)
from app.config import get_settings


def build_explanation(
    classification: AIClassificationResult,
    matched_sources: List[AIMatchedSource],
) -> str:
    if classification.sub_category == "qarz undirish":
        return (
            "Arizada qarz yoki shartnomaviy majburiyatni undirish belgilariga o'xshash holatlar mavjud. "
            "Da'vogar va javobgar o'rtasidagi munosabat fuqarolik-huquqiy majburiyatdan kelib chiqqani sababli "
            "hujjat fuqarolik sud ish yurituvi doirasida ko'rib chiqilishi mumkin. "
            f"RAG qidiruvi {', '.join(source.law + ' ' + source.article for source in matched_sources)} manbalarini mos deb topdi."
        )

    if classification.main_category.value == "oilaviy_nizo":
        return "Hujjatda oilaviy-huquqiy munosabatlar, aliment yoki farzand ta'minoti bilan bog'liq belgilar bor."

    if classification.main_category.value == "mehnat_nizosi":
        return "Hujjatda mehnat shartnomasasi, ishga tiklash yoki ish haqi bilan bog'liq nizo belgilariga o'xshash ma'lumotlar mavjud."

    return "Hujjat mazmunida huquqiy murojaat belgilari mavjud, biroq aniq toifa uchun sud xodimi tekshiruvi talab qilinadi."


def build_recommendation(classification: AIClassificationResult) -> AIRecommendation:
    threshold = get_settings().sudai_recommendation_threshold
    if classification.confidence >= threshold:
        return AIRecommendation(
            status="xodim tasdiqlashi kerak",
            recommendation=f"{classification.main_category.value} sifatida ro'yxatga olish tavsiya etiladi.",
            risk="Sudlovlilik, davlat boji va ilova hujjatlar alohida tekshirilishi lozim.",
        )

    return AIRecommendation(
        status="qo'lda tekshirish kerak",
        recommendation="Avtomatik tavsiya past ishonchlilik bilan shakllandi; hujjatni mas'ul xodim ko'rib chiqishi kerak.",
        risk="Toifa, sudlovlilik yoki ish yurituvi turi noto'g'ri aniqlangan bo'lishi mumkin.",
    )
