import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("IBIS_DATABASE_URL", "sqlite://")

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
