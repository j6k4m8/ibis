import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("IBIS_DATABASE_URL", "sqlite://")
os.environ.setdefault("IBIS_FETCH_VIDEO_TITLES", "false")
os.environ.setdefault("IBIS_PROCESSING_ENABLED", "false")

from ibis_backend.app import create_app
from ibis_backend.db import Base, SessionLocal, init_db


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> None:
    """Initialize the database once per test session."""

    init_db()


@pytest.fixture(autouse=True)
def clear_db() -> None:
    """Clear all tables between tests."""

    with SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture()
def client() -> TestClient:
    """Return a FastAPI test client."""

    app = create_app()
    return TestClient(app)


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    """Return auth headers for a registered user."""

    payload = {"email": "user@example.com", "password": "supersecret"}
    response = client.post("/auth/register", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
