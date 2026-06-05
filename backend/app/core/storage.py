"""Async file storage helpers.

``storage_root`` is interpreted relative to the backend CWD unless it is
absolute. The directory is created lazily by ``ensure_storage_root`` so a
fresh `uvicorn` boot does not 500 on a missing ``uploads/`` folder.

The path scheme is ``<root>/<user_id>/<document_id>.<ext>`` so per-user
isolation is preserved even if the row-level ``uploader_id`` check is
bypassed in a future code path.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..config import get_settings


_INVALID_SEGMENT = re.compile(r"[^A-Za-z0-9._-]")


def _safe_segment(value: str) -> str:
    """Sanitise a path segment (defence in depth — UUIDs are already safe)."""
    return _INVALID_SEGMENT.sub("_", value)[:128] or "anon"


def storage_root() -> Path:
    settings = get_settings()
    root = Path(settings.storage_root)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root


def ensure_storage_root() -> Path:
    root = storage_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_storage_path(user_id: str, document_id: str, ext: str) -> Path:
    """``<root>/<user_id>/<document_id>.<ext>``."""
    root = ensure_storage_root()
    user_dir = root / _safe_segment(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    ext_clean = ext.lstrip(".").lower()
    return user_dir / f"{_safe_segment(document_id)}.{_safe_segment(ext_clean)}"


def resolve_storage_path(storage_path: str) -> Path:
    """Resolve a relative ``storage_path`` (as stored in the DB) to an
    absolute ``Path`` on disk.

    The DB stores paths relative to ``storage_root``. The seed migration
    uses literal ``seed/...`` paths, which we resolve as-is (they almost
    certainly don't exist; downloading a seeded document is best-effort).
    """
    if not storage_path:
        raise FileNotFoundError("empty_storage_path")
    p = Path(storage_path)
    if p.is_absolute():
        return p
    return storage_root() / p


def relative_to_root(absolute: Path) -> str:
    """Store a path relative to ``storage_root`` so the DB stays portable."""
    try:
        return str(absolute.relative_to(storage_root()))
    except ValueError:
        return str(absolute)


def delete_file_silently(path: Path) -> None:
    """Best-effort delete. Never raise — we don't want a cleanup failure to
    abort a successful DELETE /api/documents/{id}.
    """
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
