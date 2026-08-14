"""Deterministic factual synthesis used by the local case-analysis mode.

This module deliberately reasons about evidence and event relationships only.
It does not select statutes and never creates legal citations.  Remote mode may
produce a richer synthesis through the provider, but both modes share the same
strict DTO and case pipeline.
"""
from __future__ import annotations

from collections import defaultdict
import re
from typing import TYPE_CHECKING, Iterable, Sequence

from app.api.schemas.ai_analysis import (
    AICandidateLegalDomain,
    AICaseDocumentInput,
    AICaseEntity,
    AICaseEvidenceLink,
    AICaseFact,
    AICaseFactualSynthesis,
    AICaseReasoningOutput,
    AICaseTimelineEvent,
    AICaseTypedAmount,
    AILegalFinding,
    AIRecommendation,
)

if TYPE_CHECKING:
    from app.services.ai_law.providers import LegalContextSource


_MONEY_PATTERN = re.compile(
    r"\b(?:\d{1,3}(?:[\s\u00a0.,]\d{3})+|\d+)"
    r"(?:\s*(?:million|millionta|mln|миллион(?:а|ов)?))?"
    r"\s*(?:so['’`ʻ]?m|sum|uzs|сум)\b",
    re.IGNORECASE,
)
_SERIAL_PATTERN = re.compile(
    r"(?:seriya(?:viy)?\s*(?:raqami)?|serial(?:\s*(?:number|no|raqami))?|"
    r"серийн(?:ый|ого)?\s*(?:номер)?)\s*[:№#-]?\s*"
    r"([A-ZА-Я0-9][A-ZА-Я0-9-]{4,})",
    re.IGNORECASE,
)

_EVENT_MARKERS: dict[str, tuple[str, ...]] = {
    "ownership": (
        "tashkilotga tegishli",
        "korxonaga tegishli",
        "mulk hisoblanadi",
        "balans qiymati",
        "принадлежит организации",
        "собственность организации",
        "балансовая стоимость",
    ),
    "access": (
        "ish vaqtidan keyin",
        "ish vaqti tugagach",
        "kirish kartasi",
        "xonaga kir",
        "после рабочего времени",
        "карта доступа",
        "вошел в помещение",
        "вошёл в помещение",
    ),
    "video": (
        "kamera",
        "videoyozuv",
        "video yozuv",
        "видеозапись",
        "камера",
    ),
    "taking": (
        "ruxsatsiz olib chiq",
        "ruxsatsiz olib ket",
        "qurilma bilan chiq",
        "noutbuk bilan chiq",
        "без разрешения вынес",
        "вынес устройство",
        "вышел с устройством",
        "вышел с ноутбуком",
    ),
    "sale": (
        "sotgan",
        "sotdi",
        "sotilgan",
        "xaridorga",
        "продал",
        "продано",
        "покупателю",
    ),
    "payment": (
        "bank kartasiga",
        "kartasiga tush",
        "pul o'tkaz",
        "to'lov",
        "банковскую карту",
        "поступили на карту",
        "банковский перевод",
        "оплата поступила",
    ),
    "serial": (
        "seriya raqami",
        "serial number",
        "серийный номер",
        "серийного номера",
    ),
    "admission": (
        "tan oldi",
        "tan olgan",
        "tasdiqladi",
        "o'zi tasdiq",
        "признал",
        "подтвердил, что вынес",
        "подтверждает, что вынес",
    ),
}

_FACT_MARKERS = tuple(marker for values in _EVENT_MARKERS.values() for marker in values)
_STOP_SENTENCE_PREFIXES = ("ilova:", "ilovalar:", "приложение:")


def synthesize_case_locally(documents: Sequence[AICaseDocumentInput]) -> AICaseFactualSynthesis:
    """Build conservative cross-document facts without legal-source input."""
    if not documents:
        raise ValueError("case_synthesis_requires_documents")

    document_ids = [document.document_id for document in documents]
    grouped_events: dict[str, list[tuple[str, str]]] = defaultdict(list)
    facts: list[AICaseFact] = []

    for document in documents:
        sentences = _sentences(document.text)
        selected = _select_fact_sentences(sentences)
        if not selected and sentences:
            selected = sentences[:1]
        for index, sentence in enumerate(selected[:4], start=1):
            facts.append(
                AICaseFact(
                    fact_id=f"fact:{document.document_id}:{index}",
                    statement=sentence,
                    document_ids=[document.document_id],
                )
            )
        for event_type, markers in _EVENT_MARKERS.items():
            matching = next(
                (sentence for sentence in sentences if _contains_marker(sentence, markers)),
                None,
            )
            if matching:
                grouped_events[event_type].append((document.document_id, matching))

    timeline = _build_timeline(grouped_events)
    amounts = _extract_typed_amounts(documents)
    evidence_links = _build_evidence_links(documents, grouped_events)
    entities = _build_entities(documents)
    candidates = _candidate_domains(documents, grouped_events, amounts)
    primary_domain = candidates[0].domain

    return AICaseFactualSynthesis(
        document_ids=document_ids,
        facts=facts,
        timeline=timeline,
        evidence_links=evidence_links,
        entities=entities,
        amounts=amounts,
        candidate_legal_domains=candidates,
        legal_issues=_legal_issues(primary_domain, grouped_events),
        retrieval_terms=_retrieval_terms(primary_domain, grouped_events),
        uncertainties=_uncertainties(grouped_events),
    )


def reason_case_locally(
    synthesis: AICaseFactualSynthesis,
    legal_context: Sequence[LegalContextSource],
) -> AICaseReasoningOutput:
    """Produce a conservative local result and disclose missing legal context."""
    primary = synthesis.candidate_legal_domains[0]
    evidence_summary = [fact.statement for fact in synthesis.facts[:8]]
    if primary.domain == "criminal_property":
        factual_conclusion = (
            "Hujjatlar majmuasi mulkka egalik, ruxsatsiz olib chiqish, keyingi sotuv, "
            "to'lov, ashyoviy identifikatorlar va tan olishga oid o'zaro bog'liq "
            "dalillar mavjudligini ko'rsatadi."
        )
    elif primary.domain == "civil_debt":
        factual_conclusion = (
            "Hujjatlar majmuasida qarz yoki shartnomaviy majburiyatni qaytarish "
            "masalasi markaziy huquqiy muammo sifatida ko'rinadi."
        )
    else:
        factual_conclusion = (
            "Hujjatlar bo'yicha faktlar birlashtirildi, biroq huquqiy domainni "
            "ishonchli aniqlash uchun qo'shimcha tekshiruv kerak."
        )

    findings = [
        AILegalFinding(kind="document_fact", statement=fact.statement, source_ids=[])
        for fact in synthesis.facts[:8]
    ]
    context_sufficient = bool(legal_context)
    if context_sufficient:
        for source in legal_context:
            findings.append(
                AILegalFinding(
                    kind="legal_assessment",
                    statement=source.excerpt,
                    source_ids=[source.source_id],
                )
            )
        explanation = (
            f"{factual_conclusion} Huquqiy baholash faqat backend retrieval orqali "
            "taqdim etilgan ishonchli manbalar bilan cheklangan."
        )
        recommendation = AIRecommendation(
            status="xodim tasdiqlashi kerak",
            recommendation="Faktlar va ko'rsatilgan huquqiy manbalarni sud xodimi tasdiqlashi kerak.",
            risk="Yakuniy kvalifikatsiya va dalillarning maqbulligi inson tomonidan tekshiriladi.",
        )
        confidence = min(round(primary.confidence * 100), 85)
    else:
        findings.append(
            AILegalFinding(
                kind="insufficient_context",
                statement=(
                    f"{primary.domain} domaini bo'yicha ishonchli retrieval manbalari "
                    "topilmadi; huquqiy kvalifikatsiya avtomatik berilmadi."
                ),
                source_ids=[],
            )
        )
        explanation = (
            f"{factual_conclusion} Biroq asosiy candidate domain uchun trusted legal "
            "sources mavjud emas, shu sabab fuqarolik yoki boshqa tasodifiy xulosa berilmadi."
        )
        recommendation = AIRecommendation(
            status="qo'lda tekshirish kerak",
            recommendation="Tegishli ishonchli huquqiy manbalarni topib, kvalifikatsiyani qo'lda tekshirish kerak.",
            risk="Huquqiy manbasiz avtomatik yakuniy kvalifikatsiya ishonchsiz bo'ladi.",
        )
        confidence = min(round(primary.confidence * 100), 65)

    return AICaseReasoningOutput(
        primary_conclusion=factual_conclusion,
        explanation=explanation,
        evidence_summary=evidence_summary,
        confidence_percent=confidence,
        human_review=recommendation,
        findings=findings,
        context_sufficient=context_sufficient,
    )


def _sentences(text: str) -> list[str]:
    normalized = text.replace("\r", "\n")
    parts = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    return [" ".join(part.split()) for part in parts if len(" ".join(part.split())) >= 12]


def _select_fact_sentences(sentences: Iterable[str]) -> list[str]:
    selected = []
    for sentence in sentences:
        lowered = _normalize(sentence)
        if lowered.startswith(_STOP_SENTENCE_PREFIXES):
            continue
        if any(marker in lowered for marker in _FACT_MARKERS):
            selected.append(sentence)
    return selected


def _normalize(value: str) -> str:
    return (
        value.lower()
        .replace("’", "'")
        .replace("ʻ", "'")
        .replace("`", "'")
        .replace("ё", "е")
    )


def _contains_marker(text: str, markers: Iterable[str]) -> bool:
    normalized = _normalize(text)
    return any(_normalize(marker) in normalized for marker in markers)


def _build_timeline(
    grouped_events: dict[str, list[tuple[str, str]]],
) -> list[AICaseTimelineEvent]:
    order = ("ownership", "access", "video", "taking", "sale", "payment", "admission")
    result = []
    for event_type in order:
        events = grouped_events.get(event_type, [])
        if not events:
            continue
        document_ids = list(dict.fromkeys(document_id for document_id, _ in events))
        result.append(
            AICaseTimelineEvent(
                sequence=len(result) + 1,
                event=events[0][1],
                document_ids=document_ids,
            )
        )
    return result


def _extract_typed_amounts(
    documents: Sequence[AICaseDocumentInput],
) -> list[AICaseTypedAmount]:
    amounts: list[AICaseTypedAmount] = []
    seen: set[tuple[str, str, str]] = set()
    for document in documents:
        for sentence in _sentences(document.text):
            for match in _MONEY_PATTERN.finditer(sentence):
                amount = " ".join(match.group(0).split())
                amount_type = _amount_type(sentence)
                key = (_normalize(amount), amount_type, document.document_id)
                if key in seen:
                    continue
                seen.add(key)
                amounts.append(
                    AICaseTypedAmount(
                        amount=amount,
                        currency="UZS",
                        amount_type=amount_type,
                        context=sentence,
                        document_ids=[document.document_id],
                    )
                )
    return amounts


def _amount_type(context: str) -> str:
    normalized = _normalize(context)
    contextual_markers = (
        ("asset_value", ("balans qiym", "mulk qiym", "qurilma qiym", "стоимост", "балансов")),
        ("sale_price", ("sotgan", "sotdi", "sotilgan", "xaridor", "продал", "продаж", "покупател")),
        ("payment", ("bank karta", "kartasiga tush", "pul o'tkaz", "to'lov", "поступ", "перевод", "оплат")),
        ("damage", ("zarar", "ziyon", "ущерб")),
        ("salary", ("ish haqi", "maosh", "зарплат")),
        ("debt", ("qarz", "qarzdor", "kredit", "долг", "задолж", "займ")),
    )
    for amount_type, markers in contextual_markers:
        if any(marker in normalized for marker in markers):
            return amount_type
    return "unknown"


def _build_evidence_links(
    documents: Sequence[AICaseDocumentInput],
    grouped_events: dict[str, list[tuple[str, str]]],
) -> list[AICaseEvidenceLink]:
    links: list[AICaseEvidenceLink] = []
    serial_documents: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        for match in _SERIAL_PATTERN.finditer(document.text):
            serial = match.group(1).upper()
            if document.document_id not in serial_documents[serial]:
                serial_documents[serial].append(document.document_id)
    for serial, document_ids in serial_documents.items():
        if len(document_ids) >= 2:
            links.append(
                AICaseEvidenceLink(
                    relationship="Bir xil ashyoviy identifikator turli hujjatlarda mos keladi.",
                    document_ids=document_ids,
                    identifiers=[serial],
                )
            )

    chain_types = ("access", "video", "taking", "sale", "payment", "admission")
    present = [event_type for event_type in chain_types if grouped_events.get(event_type)]
    chain_document_ids = list(
        dict.fromkeys(
            document_id
            for event_type in present
            for document_id, _ in grouped_events[event_type]
        )
    )
    if len(present) >= 4 and len(chain_document_ids) >= 2:
        links.append(
            AICaseEvidenceLink(
                relationship=(
                    "Kirish/video, mulkni olib chiqish, sotish, to'lov va tan olishga "
                    "oid dalillar yagona hodisalar zanjirini tashkil etadi."
                ),
                document_ids=chain_document_ids,
                identifiers=present,
            )
        )
    return links


def _build_entities(documents: Sequence[AICaseDocumentInput]) -> list[AICaseEntity]:
    roles = {
        "organization": ("tashkilot", "korxona", "организац"),
        "employee": ("xodim", "сотрудник", "работник"),
        "buyer": ("xaridor", "покупател", "третьему лицу"),
    }
    result = []
    for role, markers in roles.items():
        document_ids = [
            document.document_id
            for document in documents
            if any(marker in _normalize(document.text) for marker in markers)
        ]
        if document_ids:
            result.append(
                AICaseEntity(
                    label=role,
                    entity_type="case_role",
                    document_ids=document_ids,
                )
            )
    return result


def _candidate_domains(
    documents: Sequence[AICaseDocumentInput],
    grouped_events: dict[str, list[tuple[str, str]]],
    amounts: Sequence[AICaseTypedAmount],
) -> list[AICandidateLegalDomain]:
    event_count = sum(bool(grouped_events.get(name)) for name in _EVENT_MARKERS)
    candidates: list[AICandidateLegalDomain] = []
    if grouped_events.get("ownership") and event_count >= 4 and any(
        grouped_events.get(name) for name in ("taking", "sale", "admission")
    ):
        confidence = min(0.64 + event_count * 0.04, 0.94)
        candidates.append(
            AICandidateLegalDomain(
                domain="criminal_property",
                confidence=round(confidence, 2),
                rationale=(
                    "Mulkka egalik va uni ruxsatsiz olib chiqish/sotish bilan bog'liq "
                    "bir nechta mustaqil dalil turlari o'zaro bog'langan."
                ),
            )
        )

    combined = _normalize("\n".join(document.text for document in documents))
    central_debt = bool(
        re.search(
            r"(?:qarz\s+shartnoma|qarzni\s+(?:undirish|qaytar)|qarzdorlikni\s+undirish|"
            r"договор\s+займа|взыскан\w*\s+задолж|возврат\w*\s+долг)",
            combined,
        )
    )
    if central_debt:
        candidates.append(
            AICandidateLegalDomain(
                domain="civil_debt",
                confidence=0.82,
                rationale="Qarz majburiyatini undirish yoki qaytarish hujjatlarning markaziy talabidir.",
            )
        )

    marker_domains = (
        ("family", ("aliment", "nikoh", "ajrash", "алимет", "брак")),
        ("labor", ("mehnat shartnoma", "ish haqi", "ishga tiklash", "трудов", "зарплат")),
        ("tax", ("soliq nizosi", "soliq qarzdor", "налогов", "налоговая задолж")),
    )
    for domain, markers in marker_domains:
        if any(marker in combined for marker in markers):
            candidates.append(
                AICandidateLegalDomain(
                    domain=domain,
                    confidence=0.72,
                    rationale=f"Hujjatlar majmuasida {domain} domainiga oid markaziy belgilar mavjud.",
                )
            )

    if not candidates:
        candidates.append(
            AICandidateLegalDomain(
                domain="unknown",
                confidence=0.45,
                rationale="Faktlar mavjud, ammo domainni ishonchli ajratish uchun signal yetarli emas.",
            )
        )
    return sorted(candidates, key=lambda item: item.confidence, reverse=True)


def _legal_issues(
    primary_domain: str,
    grouped_events: dict[str, list[tuple[str, str]]],
) -> list[str]:
    if primary_domain == "criminal_property":
        issues = ["mulkni ruxsatsiz olib chiqish va tasarruf etish"]
        if grouped_events.get("sale"):
            issues.append("mulkni uchinchi shaxsga sotish")
        if grouped_events.get("payment"):
            issues.append("sotuvdan tushgan mablag' harakati")
        if grouped_events.get("serial"):
            issues.append("ashyoviy identifikatorlarning mosligi")
        return issues
    if primary_domain == "civil_debt":
        return ["qarz yoki shartnomaviy majburiyatni qaytarish"]
    return ["huquqiy domainni aniqlash"]


def _retrieval_terms(
    primary_domain: str,
    grouped_events: dict[str, list[tuple[str, str]]],
) -> list[str]:
    if primary_domain == "criminal_property":
        terms = ["jinoyat mulkka qarshi", "o'zganing mol-mulki", "mulkni ruxsatsiz egallash"]
        if grouped_events.get("sale"):
            terms.append("mulkni sotish")
        if grouped_events.get("admission"):
            terms.append("aybni tan olish dalili")
        return terms
    if primary_domain == "civil_debt":
        return ["qarz shartnomasi", "qarzdorlikni undirish", "majburiyatni bajarish"]
    return []


def _uncertainties(grouped_events: dict[str, list[tuple[str, str]]]) -> list[str]:
    uncertainties = []
    if not grouped_events.get("ownership"):
        uncertainties.append("Mulk huquqini tasdiqlovchi dalil aniqlanmadi.")
    if not grouped_events.get("serial"):
        uncertainties.append("Ashyoviy identifikatorlar bo'yicha bog'lanish aniqlanmadi.")
    if not grouped_events.get("admission"):
        uncertainties.append("Tan olish yoki bevosita tushuntirish aniqlanmadi.")
    return uncertainties
