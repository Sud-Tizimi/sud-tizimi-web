"""Retrieve relevant legal sources for an analysed document.

Two-tier retrieval:

1. **lexuz.db** (SQLite, ~400 MB) — set via the ``LEXUZ_DB_PATH`` env
   variable. When the file does not exist, this tier is skipped.
2. **LEGAL_KNOWLEDGE_BASE** — a hardcoded fallback of six high-level
   articles from FK / FPK / Oila / Mehnat / Soliq codexes. Used when
   lexuz.db is absent, empty, or errors out.

The scoring formula weights token overlap, keyword matches, exact
phrases, and topic-bonus hints (e.g. FK 732-modda for "qarz undirish"),
then subtracts penalties for amendments and expired docs.
"""
from __future__ import annotations

import math
import os
import re
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from app.api.schemas.ai_analysis import AIMatchedSource

_log = logging.getLogger(__name__)

# Default to no SQLite corpus. Set ``LEXUZ_DB_PATH`` to enable lexuz retrieval.
DEFAULT_LEXUZ_DB_PATH: Optional[str] = None


@dataclass(frozen=True)
class LegalChunk:
    law: str
    article: str
    title: str
    text: str
    keywords: Tuple[str, ...]


@dataclass(frozen=True)
class ArticleChunk:
    article: str
    text: str


LEGAL_KNOWLEDGE_BASE: List[LegalChunk] = [
    LegalChunk(
        law="Fuqarolik kodeksi",
        article="234-modda",
        title="Majburiyat tushunchasi va vujudga kelish asoslari",
        text="Majburiyat shartnoma, zarar yetkazish yoki qonunda ko'rsatilgan boshqa asoslardan kelib chiqishi mumkin.",
        keywords=("majburiyat", "qarz", "shartnoma", "undirish", "tilxat"),
    ),
    LegalChunk(
        law="Fuqarolik kodeksi",
        article="236-modda",
        title="Majburiyatlarni lozim darajada bajarish",
        text="Majburiyatlar shartnoma shartlari va qonun talablariga muvofiq lozim darajada bajarilishi kerak.",
        keywords=("majburiyat", "bajarish", "shartnoma", "qarzdor"),
    ),
    LegalChunk(
        law="Fuqarolik protsessual kodeksi",
        article="189-modda",
        title="Da'vo arizasining shakli va mazmuni",
        text="Da'vo arizasida sud nomi, taraflar, talab mazmuni, asoslar va ilova hujjatlar ko'rsatiladi.",
        keywords=("da'vo arizasi", "talab", "javobgar", "da'vogar", "ilova"),
    ),
    LegalChunk(
        law="Oila kodeksi",
        article="96-modda",
        title="Ota-onaning voyaga yetmagan bolalariga ta'minot berish majburiyati",
        text="Ota-ona voyaga yetmagan bolalariga ta'minot berishi shart.",
        keywords=("aliment", "farzand", "ta'minot", "ota-ona"),
    ),
    LegalChunk(
        law="Mehnat kodeksi",
        article="161-modda",
        title="Mehnat shartnomasini bekor qilish asoslari",
        text="Mehnat shartnomasini bekor qilish qonunda belgilangan asoslar mavjud bo'lganda amalga oshiriladi.",
        keywords=("mehnat", "ishdan bo'shatish", "ishga tiklash", "shartnoma"),
    ),
    LegalChunk(
        law="Soliq kodeksi",
        article="220-modda",
        title="Soliq qarzdorligi",
        text="Soliq majburiyatlari bajarilmaganda soliq qarzdorligi va tegishli javobgarlik masalalari yuzaga keladi.",
        keywords=("soliq", "qarzdorlik", "penya", "jarima"),
    ),
]


def retrieve_sources(
    query: str,
    limit: int = 3,
    category_hint: Optional[str] = None,
) -> List[AIMatchedSource]:
    """Return up to ``limit`` matched law sources, preferring lexuz.db."""
    lexuz_sources = _retrieve_from_lexuz(query, limit=limit, category_hint=category_hint)
    if lexuz_sources:
        return lexuz_sources
    return _retrieve_from_demo_base(query, limit=limit)


def _retrieve_from_lexuz(
    query: str, limit: int, category_hint: Optional[str]
) -> List[AIMatchedSource]:
    env_path = os.getenv("LEXUZ_DB_PATH", DEFAULT_LEXUZ_DB_PATH)
    if not env_path:
        return []
    db_path = Path(env_path)
    if not db_path.exists():
        _log.warning("LEXUZ_DB_PATH=%s does not exist; skipping lexuz tier", env_path)
        return []
    try:
        _probe = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        _probe.close()
    except sqlite3.DatabaseError as exc:
        _log.warning(
            "LEXUZ_DB_PATH=%s is not a readable SQLite database (%s); skipping lexuz tier",
            env_path, exc,
        )
        return []

    preferred_laws = _preferred_law_terms(query, category_hint)
    search_terms = _build_search_terms(query, preferred_laws)
    content_terms = [term for term in search_terms if term not in preferred_laws] or search_terms
    if not search_terms:
        return []

    where_parts = ["status = 'ok'", "text IS NOT NULL", "length(text) > 100"]
    params: List[str] = []

    if preferred_laws:
        law_clauses = []
        for law in preferred_laws:
            law_clauses.append("(title LIKE ? OR dataset_title LIKE ?)")
            like_law = f"%{law}%"
            params.extend([like_law, like_law])
        where_parts.append("(" + " OR ".join(law_clauses) + ")")

    content_clauses = []
    for term in content_terms[:10]:
        content_clauses.append("(title LIKE ? OR text LIKE ?)")
        like_term = f"%{term}%"
        params.extend([like_term, like_term])
    where_parts.append("(" + " OR ".join(content_clauses) + ")")

    sql = f"""
        SELECT id, url, title, text, category_path, dataset_title, char_count
        FROM documents
        WHERE {" AND ".join(where_parts)}
        LIMIT 120
    """

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()

    scored = []
    query_tokens = _tokens(query)

    for row in rows:
        title = row["title"] or row["dataset_title"] or "Lex.uz hujjati"
        raw_text = row["text"] or ""
        text = _clean_lexuz_text(raw_text)
        category_path = row["category_path"] or ""
        title_score = sum(10 for law in preferred_laws if _normalize(law) in _normalize(title))
        primary_law_score = 45 if _is_primary_law_title(title, preferred_laws) else 0
        secondary_penalty = 30 if _looks_like_secondary_doc(title) else 0
        expired_penalty = 30 if _looks_expired(title + " " + category_path) else 0

        for chunk in _article_chunks(text):
            haystack = _normalize(f"{title} {category_path} {chunk.text}")
            token_score = len(query_tokens.intersection(_tokens(haystack)))
            term_score = sum(4 for term in content_terms if _normalize(term) in haystack)
            exact_phrase_score = _exact_phrase_score(query, chunk.text)
            topic_score = _topic_article_bonus(query, category_hint, title, chunk)

            score = (
                token_score
                + term_score
                + exact_phrase_score
                + topic_score
                + title_score
                + primary_law_score
                - secondary_penalty
                - expired_penalty
            )
            if score <= 0:
                continue

            snippet = _article_snippet(chunk.text, content_terms)
            relevance = min(0.55 + math.log1p(score) / 4, 0.98)
            scored.append((score, row, title, snippet, chunk.article, relevance))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        AIMatchedSource(
            law=_clean_law_title(title),
            article=article,
            title=_clean_title(title),
            excerpt=snippet,
            relevance=round(relevance, 2),
            source_id=str(row["id"]),
            source_url=row["url"],
            category_path=row["category_path"],
        )
        for _, row, title, snippet, article, relevance in scored[:limit]
    ]


def _retrieve_from_demo_base(query: str, limit: int) -> List[AIMatchedSource]:
    query_tokens = _tokens(query)
    scored = []

    for chunk in LEGAL_KNOWLEDGE_BASE:
        keyword_score = sum(2 for keyword in chunk.keywords if _normalize(keyword) in _normalize(query))
        token_score = len(query_tokens.intersection(_tokens(chunk.text + " " + chunk.title)))
        score = keyword_score + token_score
        if score > 0:
            relevance = min(0.55 + math.log1p(score) / 3, 0.97)
            scored.append((score, relevance, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        AIMatchedSource(
            law=chunk.law,
            article=chunk.article,
            title=chunk.title,
            excerpt=chunk.text,
            relevance=round(relevance, 2),
        )
        for _, relevance, chunk in scored[:limit]
    ]


def _build_search_terms(query: str, preferred_laws: List[str]) -> List[str]:
    normalized = _normalize(query)
    terms = list(preferred_laws)

    keyword_map = {
        "qarz": ["qarz shartnomasi", "qarzdorlik", "qarz", "undirish", "majburiyat", "da'vo", "shartnoma"],
        "kredit": ["kredit", "qarzdorlik", "bank", "undirish", "majburiyat"],
        "aliment": ["aliment", "farzand", "ta'minot", "oila"],
        "nikoh": ["nikoh", "ajrashish", "oila"],
        "mehnat": ["mehnat", "ish haqi", "ishga tiklash", "bo'shatish"],
        "soliq": ["soliq", "penya", "jarima", "qarzdorlik"],
    }
    for marker, values in keyword_map.items():
        if marker in normalized:
            terms.extend(values)

    terms.extend(sorted(_tokens(normalized), key=len, reverse=True)[:8])
    return _dedupe_terms(terms)


def _preferred_law_terms(query: str, category_hint: Optional[str]) -> List[str]:
    normalized = _normalize(f"{category_hint or ''} {query}")
    terms: List[str] = []

    if any(word in normalized for word in ["qarz", "shartnoma", "undirish", "fuqarolik", "da'vo"]):
        terms.extend(["Fuqarolik kodeksi", "Fuqarolik protsessual kodeksi"])
    if any(word in normalized for word in ["aliment", "nikoh", "farzand", "oila", "oilaviy"]):
        terms.append("Oila kodeksi")
    if any(word in normalized for word in ["mehnat", "ish haqi", "ishga tiklash", "bo'shatish"]):
        terms.append("Mehnat kodeksi")
    if "soliq" in normalized:
        terms.append("Soliq kodeksi")

    return _dedupe_terms(terms)


def _dedupe_terms(terms: List[str]) -> List[str]:
    result = []
    seen = set()
    for term in terms:
        cleaned = term.strip()
        key = _normalize(cleaned)
        if len(key) < 4 or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _clean_lexuz_text(text: str) -> str:
    text = re.sub(r"\[\s*(OKOZ|TSZ|SPiT):.*?\]", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"Oldingi tahrirga qarang\.?", " ", text, flags=re.IGNORECASE)
    boilerplate = [
        "Hujjatga taklif yuborish",
        "Audioni tinglash",
        "Hujjat elementidan havola olish",
        "LexUZ sharhi",
    ]
    for phrase in boilerplate:
        text = text.replace(phrase, " ")
    return " ".join(text.split())


def _article_chunks(text: str, max_chunks: int = 1600) -> List[ArticleChunk]:
    matches = list(
        re.finditer(
            r"(?P<num>\d{1,4})\s*[-–]?\s*(?:modda|модда)\b\s*[.。]?",
            text,
            flags=re.IGNORECASE,
        )
    )
    if not matches:
        return [ArticleChunk(article="tegishli modda", text=text[:3000])]

    chunks: List[ArticleChunk] = []
    for index, match in enumerate(matches[:max_chunks]):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(text), start + 3500)
        chunk_text = text[start:end].strip()
        if len(chunk_text) < 80:
            continue
        chunks.append(ArticleChunk(article=f"{match.group('num')}-modda", text=chunk_text[:3500]))

    return chunks or [ArticleChunk(article="tegishli modda", text=text[:3000])]


def _article_snippet(text: str, terms: List[str]) -> str:
    first_part = " ".join(text[:900].split())
    normalized_first = _normalize(first_part)
    if any(_normalize(term) in normalized_first for term in terms):
        return _clean_excerpt(first_part[:850])

    snippet = _best_snippet(text, terms, before=60, after=780)
    article_match = re.search(
        r"\b\d{1,4}\s*[-–]?\s*(?:modda|модда)\b", snippet, flags=re.IGNORECASE
    )
    if not article_match:
        return _clean_excerpt(snippet)
    return _clean_excerpt(snippet[article_match.start():])


def _best_snippet(text: str, terms: List[str], before: int = 160, after: int = 650) -> str:
    if not text:
        return ""

    normalized_text = _normalize(text)
    position = 0
    for term in terms:
        position = normalized_text.find(_normalize(term))
        if position >= 0:
            break
    start = max(position - before, 0)
    end = min(position + after, len(text))
    if start > 0:
        next_space = text.find(" ", start)
        if 0 <= next_space < position:
            start = next_space + 1
    snippet = " ".join(text[start:end].split())
    return snippet[:850]


def _clean_excerpt(text: str) -> str:
    text = re.sub(r"Oldingi tahrirga qarang\.?", " ", text, flags=re.IGNORECASE)
    text = text.replace("LexUZ sharhi", " ")
    return " ".join(text.split())


def _exact_phrase_score(query: str, text: str) -> int:
    normalized_query = _normalize(query)
    normalized_text = _normalize(text)
    phrases = [
        "qarz shartnomasi",
        "qarzdorlik",
        "qarz oluvchi",
        "qarz beruvchi",
        "sud buyrug'i",
        "yozma bitim",
        "undirish",
        "aliment",
        "ishga tiklash",
        "ish haqi",
        "soliq qarzdorligi",
    ]
    score = 0
    for phrase in phrases:
        if phrase in normalized_query and phrase in normalized_text:
            score += 10
    return score


def _topic_article_bonus(
    query: str,
    category_hint: Optional[str],
    title: str,
    chunk: ArticleChunk,
) -> int:
    normalized = _normalize(f"{category_hint or ''} {query}")
    normalized_title = _normalize(title)
    normalized_text = _normalize(chunk.text)
    score = 0

    if any(word in normalized for word in ["qarz", "qarzdorlik", "kredit", "undirish"]):
        if "fuqarolik kodeksi" in normalized_title and chunk.article == "732-modda":
            score += 95
        if "fuqarolik kodeksi" in normalized_title and chunk.article in {"733-modda", "734-modda", "735-modda"}:
            score += 55
        if "fuqarolik protsessual kodeksi" in normalized_title and chunk.article in {"171-modda", "172-modda", "189-modda"}:
            score += 35
        if any(phrase in normalized_text for phrase in ["qarz shartnomasi", "qarzdorlik", "yozma bitim", "undirish"]):
            score += 18

    if any(word in normalized for word in ["aliment", "farzand", "oila"]):
        if "oila kodeksi" in normalized_title and any(
            phrase in normalized_text for phrase in ["aliment", "ta'minot", "voyaga yetmagan"]
        ):
            score += 40

    if any(word in normalized for word in ["mehnat", "ish haqi", "ishga tiklash", "bo'shatish"]):
        if "mehnat kodeksi" in normalized_title and any(
            phrase in normalized_text for phrase in ["mehnat shartnomasi", "ish haqi", "ishga tiklash"]
        ):
            score += 40

    if "soliq" in normalized:
        if "soliq kodeksi" in normalized_title and any(
            phrase in normalized_text for phrase in ["soliq qarzdorligi", "penya", "jarima"]
        ):
            score += 40

    return score


def _clean_title(title: str) -> str:
    return title.replace("\xa0", " ").strip()


def _clean_law_title(title: str) -> str:
    title = _clean_title(title)
    title = re.sub(
        r"^[A-ZОЎҚҒҲ'`-]+-\d+[-A-ZОЎҚҒҲ'`]*-son\s+\d{2}\.\d{2}\.\d{4}\.\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"^\d{2}\.\d{2}\.\d{4}\.\s*", "", title)
    title = re.sub(r"^[^ ]+-son\s+\d{2}\.\d{2}\.\d{4}\.\s*", "", title, flags=re.IGNORECASE)
    return title.strip()


def _is_primary_law_title(title: str, preferred_laws: List[str]) -> bool:
    normalized_title = _normalize(title)
    if not any(_normalize(law) in normalized_title for law in preferred_laws):
        return False
    return not _looks_like_secondary_doc(title)


def _looks_like_secondary_doc(title: str) -> bool:
    normalized_title = _normalize(title)
    markers = [
        "o'zgartish",
        "o'zgartirish",
        "qo'shimcha",
        "kiritish",
        "plenum",
        "qarori",
        "loyihasi",
        "shikoyati bo'yicha",
        "amalga oshirish",
        "tasdiqlash to'g'risida",
    ]
    return any(marker in normalized_title for marker in markers)


def _looks_expired(text: str) -> bool:
    normalized_text = _normalize(text)
    return any(
        marker in normalized_text
        for marker in ["kuchini yo'qotgan", "кучини йукотган", "кучини йўқотган"]
    )


def _normalize(text: str) -> str:
    return (
        text.lower()
        .replace("ʻ", "'")
        .replace("‘", "'")
        .replace("’", "'")
        .replace("`", "'")
        .replace("ʼ", "'")
    )


def _tokens(text: str) -> Set[str]:
    return set(re.findall(r"[a-zA-Zа-яА-Яўқғҳʼ'`-]{4,}", _normalize(text)))
