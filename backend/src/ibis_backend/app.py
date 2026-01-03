"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ibis_backend.api.auth import router as auth_router
from ibis_backend.api.health import router as health_router
from ibis_backend.api.notes import router as notes_router
from ibis_backend.api.tasks import router as tasks_router
from ibis_backend.config import get_settings
from ibis_backend.db import init_db


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI instance.
    """

    settings = get_settings()
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        yield

    app = FastAPI(title="Ibis API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(notes_router, prefix="/notes", tags=["notes"])
    app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

    return app


app = create_app()
