"""Authentication helpers for password hashing and tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
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


def decode_access_token(token: str) -> str:
    """Decode a JWT access token and return the subject.

    Args:
        token: JWT token string.

    Returns:
        str: Subject identifier.

    Raises:
        ValueError: If the token is invalid or missing a subject.
    """

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    subject = payload.get("sub")
    if not subject:
        raise ValueError("Missing subject")
    return subject
