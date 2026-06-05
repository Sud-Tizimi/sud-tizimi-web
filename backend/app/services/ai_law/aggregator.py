"""Aggregate per-document SudAI results into a single case-level response.

The case-level view is what the "AI Analyze all" button shows to the
judge: one combined picture of every document attached to the case,
rather than N independent result cards.

Aggregation rules (kept simple and explainable):

* **classification** — pick the modal ``main_category`` (the most common
  legal category across the analysed docs). When there's a tie, prefer
  the category with the highest single-document confidence. ``confidence``
  is averaged.
* **matched_sources** — top 5 by combined score
  (``frequency × mean(relevance)``). This surfaces laws/articles that
  recur across documents, which is the most useful signal for a judge.
* **extracted_objects** — first non-null claimant / respondent / claim
  subject / demand summary / contract number / debt amount. ``dates`` and
  ``attachments`` are flattened and de-duplicated.
* **human_review** — the case requires manual review if *any* sub-result
  requires manual review (worst-case-wins policy).
* **explanation** — pass through the highest-confidence sub-result's
  explanation; that sub-result was the most representative document.
"""
from __future__ import annotations

from collections import Counter
from typing import List, Optional

from app.api.schemas.ai_analysis import (
    AIAnalysisResponse,
    AIExtractedLegalObjects,
    AIMatchedSource,
    AIRecommendation,
)


def _first_str(*candidates: Optional[str]) -> Optional[str]:
    for value in candidates:
        if value:
            return value
    return None


def _modal_category(items: List[AIAnalysisResponse]):
    """Return ``(category, total_confidence, count)`` of the modal category."""
    counts: Counter = Counter()
    conf_sums: dict = {}
    for item in items:
        cat = item.classification.main_category
        counts[cat] += 1
        conf_sums[cat] = conf_sums.get(cat, 0.0) + item.classification.confidence

    if not counts:
        return None

    # Ties broken by total confidence, then by alphabetical enum value.
    top_count = max(counts.values())
    candidates = [c for c, n in counts.items() if n == top_count]
    best = max(candidates, key=lambda c: (conf_sums[c], c.value))
    return best, conf_sums[best], counts[best]


def _aggregate_matched_sources(items: List[AIAnalysisResponse], limit: int = 5) -> List[AIMatchedSource]:
    """Group matches by ``(law, article)`` and rank by frequency × relevance."""
    bucket: dict[tuple[str, str], dict] = {}

    for item in items:
        for source in item.matched_sources:
            key = (source.law, source.article)
            slot = bucket.setdefault(
                key,
                {
                    "law": source.law,
                    "article": source.article,
                    "title": source.title,
                    "excerpt": source.excerpt,
                    "source_id": source.source_id,
                    "source_url": source.source_url,
                    "category_path": source.category_path,
                    "frequency": 0,
                    "relevance_sum": 0.0,
                },
            )
            slot["frequency"] += 1
            slot["relevance_sum"] += source.relevance

    ranked = sorted(
        bucket.values(),
        key=lambda s: s["frequency"] * (s["relevance_sum"] / s["frequency"]),
        reverse=True,
    )

    results: List[AIMatchedSource] = []
    for slot in ranked[:limit]:
        results.append(
            AIMatchedSource(
                law=slot["law"],
                article=slot["article"],
                title=slot["title"],
                excerpt=slot["excerpt"],
                relevance=round(slot["relevance_sum"] / slot["frequency"], 2),
                source_id=slot["source_id"],
                source_url=slot["source_url"],
                category_path=slot["category_path"],
            )
        )
    return results


def _aggregate_extracted_objects(items: List[AIAnalysisResponse]) -> AIExtractedLegalObjects:
    claimant: Optional[str] = None
    respondent: Optional[str] = None
    claim_subject: Optional[str] = None
    demand_summary: Optional[str] = None
    contract_number: Optional[str] = None
    debt_amount: Optional[str] = None
    dates: list[str] = []
    attachments: list[str] = []

    for item in items:
        objs = item.extracted_objects
        claimant = claimant or objs.claimant
        respondent = respondent or objs.respondent
        claim_subject = claim_subject or objs.claim_subject
        demand_summary = demand_summary or objs.demand_summary
        contract_number = contract_number or objs.contract_number
        debt_amount = debt_amount or objs.debt_amount
        for d in objs.dates:
            if d not in dates:
                dates.append(d)
        for a in objs.attachments:
            if a and a not in attachments:
                attachments.append(a)

    return AIExtractedLegalObjects(
        claimant=claimant,
        respondent=respondent,
        claim_subject=claim_subject,
        demand_summary=demand_summary,
        contract_number=contract_number,
        debt_amount=debt_amount,
        dates=dates,
        attachments=attachments,
    )


def _aggregated_recommendation(items: List[AIAnalysisResponse]) -> AIRecommendation:
    """Worst-case-wins: if any sub-result needs manual review, so does the case."""
    for item in items:
        if item.human_review.status == "qo'lda tekshirish kerak":
            return item.human_review
    return items[0].human_review


def aggregate_case_results(items: List[AIAnalysisResponse]) -> AIAnalysisResponse:
    """Combine ``items`` (per-document responses) into a single response.

    Returns the input unchanged when only one document was analysed.
    """
    if not items:
        raise ValueError("aggregate_case_results requires at least one item")
    if len(items) == 1:
        return items[0]

    modal = _modal_category(items)
    if modal is None:
        return items[0]
    category, total_conf, count = modal
    mean_confidence = round(total_conf / count, 2)

    # Take the first item as the template for metadata, anonymized text, entities.
    base = items[0]

    # Reuse the explanation from the most confident sub-result.
    best_by_confidence = max(items, key=lambda i: i.classification.confidence)

    return AIAnalysisResponse(
        metadata=base.metadata,  # metadata is per-document; not aggregated.
        anonymized_text=base.anonymized_text,
        anonymized_entities=base.anonymized_entities,
        extracted_objects=_aggregate_extracted_objects(items),
        classification=base.classification.model_copy(
            update={
                "main_category": category,
                "confidence": mean_confidence,
            }
        ),
        matched_sources=_aggregate_matched_sources(items),
        explanation=best_by_confidence.explanation,
        confidence_percent=round(mean_confidence * 100),
        human_review=_aggregated_recommendation(items),
    )
