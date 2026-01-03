"""Authentication helpers for password hashing and tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from ibis_backend.config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: Plaintext password.

    Returns:
        str: Password hash.
    """

    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash.

    Args:
        password: Plaintext password.
        password_hash: Stored password hash.

    Returns:
        bool: True if valid.
    """

    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str) -> str:
    """Create a JWT access token.

    Args:
        subject: Subject identifier (user ID).

    Returns:
        str: Signed JWT token.
    """

    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
