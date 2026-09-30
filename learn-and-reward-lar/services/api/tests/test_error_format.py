"""API-wide conventions: unified error body and free-conversation practice chat."""

from __future__ import annotations

import pytest

from app.modules.ai_chat import deps as chat_deps
from tests.conftest import auth_headers, seed_course_id
from tests.test_chat import StubEngine


@pytest.fixture()
def stub_engine(client):
    engine = StubEngine()
    client.app.dependency_overrides[chat_deps.get_chat_engine] = lambda: engine
    yield engine
    client.app.dependency_overrides.pop(chat_deps.get_chat_engine, None)


def test_error_shape_is_uniform(client):
    response = client.get("/api/v1/lessons/00000000-0000-0000-0000-0000000000e0")
    assert response.status_code in (401, 403, 404)
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}


def test_validation_errors_use_uniform_shape(client):
    response = client.get("/api/v1/courses/not-a-uuid")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_course_404(client):
    headers = auth_headers(client)
    response = client.post(
        "/api/v1/courses/00000000-0000-0000-0000-0000000000d0/enroll", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COURSE_NOT_FOUND"


def test_free_conversation_session_gets_ai_reply(client, stub_engine):
    headers = auth_headers(client)
    session = client.post(
        "/api/v1/practice/sessions", headers=headers, json={"kind": "free_conversation"}
    )
    assert session.status_code == 201
    body = session.json()
    assert body["kind"] == "free_conversation"
    assert body["total_exercises"] == 0

    reply = client.post(
        f"/api/v1/practice/sessions/{body['id']}/messages",
        headers=headers,
        json={"content": "Moien! Ech wëlle Lëtzebuergesch léieren."},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["reply"].startswith("Mock reply")

    # Exercise submissions are rejected on free_conversation sessions.
    wrong_kind = client.post(
        f"/api/v1/practice/sessions/{body['id']}/messages",
        headers=headers,
        json={"exercise_id": "00000000-0000-0000-0000-000000000001", "answer": 1},
    )
    assert wrong_kind.status_code == 422


def test_lesson_session_rejects_plain_text(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    session = client.post(
        "/api/v1/practice/sessions",
        headers=headers,
        json={"kind": "lesson_exercises", "lesson_id": detail["lessons"][0]["id"]},
    ).json()

    response = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"content": "just text"},
    )
    assert response.status_code == 422
