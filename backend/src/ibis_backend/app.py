"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ibis_backend.api.auth import router as auth_router
from ibis_backend.api.config import router as config_router
from ibis_backend.api.health import router as health_router
from ibis_backend.api.jobs import router as jobs_router
from ibis_backend.api.lessons import router as lessons_router
from ibis_backend.api.me import router as me_router
from ibis_backend.api.notes import router as notes_router
from ibis_backend.api.search import router as search_router
from ibis_backend.api.tasks import router as tasks_router
from ibis_backend.api.videos import router as videos_router
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
    app.include_router(config_router, tags=["config"])
    app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
    app.include_router(me_router, prefix="/me", tags=["me"])
    app.include_router(lessons_router, prefix="/lessons", tags=["lessons"])
    app.include_router(notes_router, prefix="/notes", tags=["notes"])
    app.include_router(search_router, prefix="/search", tags=["search"])
    app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
    app.include_router(videos_router, prefix="/videos", tags=["videos"])

    return app


app = create_app()
