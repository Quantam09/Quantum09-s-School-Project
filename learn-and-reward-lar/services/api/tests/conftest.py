"""Pytest fixtures.

Runs against in-memory SQLite (schema names dropped) so the suite needs no external
services; DeepSeek is replaced by a fake engine where relevant. The production
configuration (PostgreSQL + pgvector via docker-compose) is exercised through
Alembic migrations, not this suite.
"""

from __future__ import annotations

import os

# Configure before importing the app: schema resolution happens at import time.
# Plain assignment (not setdefault) so a machine-wide DEEPSEEK_API_KEY can never
# leak into the suite and hit the real API.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "test"
os.environ["DEEPSEEK_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.main import app  # noqa: E402
from app.modules.learning.seed import seed_if_empty  # noqa: E402
from app.shared.db import Base, get_engine, init_engine, strip_schemas_for_sqlite  # noqa: E402


@pytest.fixture()
def db_engine():
    """Fresh in-memory database per test (function scope for isolation)."""
    init_engine("sqlite://", force=True)
    engine = get_engine()
    # SQLite has no schema support: drop module schema names for the test DDL.
    strip_schemas_for_sqlite()
    Base.metadata.create_all(engine)
    with Session(bind=engine) as session:
        seed_if_empty(session)
        session.commit()
    yield engine


@pytest.fixture()
def client(db_engine):
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient, email: str = "learner@example.com", password: str = "password123") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Test Learner"},
    )
    if response.status_code == 409:  # already registered in this database
        pass
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_course_id(client: TestClient) -> str:
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items, "seed course missing"
    return items[0]["id"]


@pytest.fixture()
def fake_chat_engine():
    """Standalone fake engine for direct engine-level tests."""
    from app.modules.ai_chat.engine import ChatEngine

    class FakeDeepSeek:
        def __init__(self) -> None:
            self.calls: list[list[dict]] = []

        def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
            self.calls.append(messages)
            return "Mock DeepSeek reply."

    class FakeRag:
        def search(self, query: str, *, language: str = "lb", top_k: int = 4):
            from app.shared.rag_client import RagClient, StubRagClient  # noqa: F401

            return StubRagClient().search(query, language=language, top_k=top_k)

    return ChatEngine(deepseek=FakeDeepSeek(), rag=FakeRag())
