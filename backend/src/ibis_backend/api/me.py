"""User self-service endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ibis_backend.config import get_settings
from ibis_backend.db import get_db
from ibis_backend.dependencies import get_current_user
from ibis_backend.models import User, Video
from ibis_backend.schemas import MeRead, MeUpdate, UserRead

router = APIRouter()


@router.get("", response_model=MeRead)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeRead:
    """Return the current user along with storage usage."""

    total_bytes = (
        db.query(func.coalesce(func.sum(Video.file_size_bytes), 0))
        .filter(Video.user_id == current_user.id)
        .scalar()
        or 0
    )
    settings = get_settings()
    return MeRead(
        user=UserRead.model_validate(current_user),
        storage_used_bytes=int(total_bytes),
        storage_limit_bytes=settings.storage_limit_bytes,
    )


@router.patch("", response_model=MeRead)
def update_me(
    payload: MeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeRead:
    """Update current user settings."""

    if payload.lesson_autogroup_hours is not None:
        current_user.lesson_autogroup_hours = payload.lesson_autogroup_hours
    db.commit()
    db.refresh(current_user)
    total_bytes = (
        db.query(func.coalesce(func.sum(Video.file_size_bytes), 0))
        .filter(Video.user_id == current_user.id)
        .scalar()
        or 0
    )
    settings = get_settings()
    return MeRead(
        user=UserRead.model_validate(current_user),
        storage_used_bytes=int(total_bytes),
        storage_limit_bytes=settings.storage_limit_bytes,
    )
