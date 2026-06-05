"""Map free-text Uzbek document type strings (from SudAI's
:classifier.detect_document_type`) onto the canonical
:class:`DocumentType` enum.

When the classifier returns ``"aniqlanmagan hujjat"`` (unrecognised),
``map_document_type`` returns ``None`` — the caller should leave
``detected_type`` unset rather than forcing an inaccurate classification.
"""
from __future__ import annotations

from typing import Optional

from app.core.enums import DocumentType

# Uzbek label produced by SudAI  →  our canonical DocumentType
_UZBEK_TO_DOC_TYPE: dict[str, DocumentType] = {
    "da'vo arizasi": DocumentType.CLAIM,
    "davo arizasi": DocumentType.CLAIM,  # ascii-only variant that may appear
    "qarshi da'vo": DocumentType.COUNTERCLAIM,
    "qarshi davo": DocumentType.COUNTERCLAIM,
    "shikoyat": DocumentType.APPEAL,
    "iltimosnoma": DocumentType.STATEMENT,
    "e'tiroz": DocumentType.OBJECTION,
    "etiroz": DocumentType.OBJECTION,
}


def map_document_type(uzbek_label: str) -> Optional[DocumentType]:
    """Resolve a SudAI Uzbek label to a :class:`DocumentType` value.

    Returns ``None`` for the "aniqlanmagan hujjat" sentinel and any other
    label the mapper does not know about — callers should treat that as
    "no classification available" rather than guessing.
    """
    if not uzbek_label:
        return None
    return _UZBEK_TO_DOC_TYPE.get(uzbek_label.strip().lower())
