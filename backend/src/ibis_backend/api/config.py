"""Public configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ibis_backend.config import get_settings
from ibis_backend.schemas import AppConfigRead

router = APIRouter()


@router.get("/config", response_model=AppConfigRead, tags=["config"])
def get_app_config() -> AppConfigRead:
    """Expose runtime limits for clients."""

    settings = get_settings()
    return AppConfigRead(
        upload_max_bytes=settings.upload_max_bytes,
        storage_limit_bytes=settings.storage_limit_bytes,
    )
