"""ID generators — keep format simple, predictable, and grep-friendly."""
import secrets
import time
import uuid


def gen_session_id() -> str:
    """Format: sess-{epoch_seconds}-{4 hex chars}"""
    return f"sess-{int(time.time())}-{secrets.token_hex(2)}"


def gen_entry_id(speaker_id: str, at_ms: int) -> str:
    """Format: e-{at_ms}-{speaker_id}-{3 hex chars}"""
    return f"e-{at_ms}-{speaker_id}-{secrets.token_hex(2)}"


def gen_document_id() -> str:
    """Format: doc-{uuid4-hex}. Stable UUIDs (vs time-based session IDs)
    make on-disk paths predictable and avoid collisions when two uploads
    happen in the same millisecond.
    """
    return f"doc-{uuid.uuid4().hex}"
