"""Password hashing and JWT helpers — see Phase A plan §Auth flow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from .enums import UserRole

# Bcrypt with default 12 rounds. Constant cost acceptable for the MVP demo.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of plaintext to a bcrypt hash."""
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(
    *,
    sub: str,
    role: UserRole,
    email: str,
    expires_minutes: int,
    secret: str,
    algorithm: str = "HS256",
) -> str:
    """Encode a JWT for the given user.

    ``sub`` carries the user UUID. ``role`` and ``email`` are denormalised
    onto the token so the client / `get_current_user` dep can read them
    without hitting the DB on every request.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role.value,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str = "HS256") -> Optional[dict]:
    """Decode and verify a JWT. Returns None on any failure (expired / bad sig / malformed).

    Callers should treat None as "unauthorized".
    """
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError:
        return None
