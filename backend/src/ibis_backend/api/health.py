"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Return a basic health status.

    Returns:
        dict: Health status payload.
    """

    return {"status": "ok"}
