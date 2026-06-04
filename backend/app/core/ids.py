"""ID generators — keep format simple, predictable, and grep-friendly."""
import secrets
import time


def gen_session_id() -> str:
    """Format: sess-{epoch_seconds}-{4 hex chars}"""
    return f"sess-{int(time.time())}-{secrets.token_hex(2)}"


def gen_entry_id(speaker_id: str, at_ms: int) -> str:
    """Format: e-{at_ms}-{speaker_id}-{3 hex chars}"""
    return f"e-{at_ms}-{speaker_id}-{secrets.token_hex(2)}"
