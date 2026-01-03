"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import User
from ibis_backend.schemas import AuthResponse, LoginRequest, RegisterRequest, UserRead
from ibis_backend.services.auth import create_access_token, hash_password, verify_password

router = APIRouter()


def normalize_email(email: str) -> str:
    """Normalize email casing.

    Args:
        email: Raw email.

    Returns:
        str: Normalized email.
    """

    return email.strip().lower()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register a new user.

    Args:
        payload: Registration payload.
        db: Database session.

    Returns:
        AuthResponse: Auth payload with token.
    """

    email = normalize_email(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Log in an existing user.

    Args:
        payload: Login payload.
        db: Database session.

    Returns:
        AuthResponse: Auth payload with token.
    """

    email = normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.id)
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the current authenticated user.

    Args:
        current_user: Authenticated user.

    Returns:
        UserRead: User profile.
    """

    return UserRead.model_validate(current_user)
