"""Practice sessions: exercise submission, scoring, completion rewards, progress."""

from __future__ import annotations

import pytest

from app.shared.coin_client import get_coin_client, reset_coin_client
from tests.conftest import auth_headers, seed_course_id


@pytest.fixture(autouse=True)
def fresh_coin_client():
    reset_coin_client()
    yield
    reset_coin_client()


def _start_lesson_session(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    lesson_id = detail["lessons"][0]["id"]
    lesson = client.get(f"/api/v1/lessons/{lesson_id}", headers=headers).json()
    session = client.post(
        "/api/v1/practice/sessions",
        headers=headers,
        json={"kind": "lesson_exercises", "lesson_id": lesson_id},
    )
    assert session.status_code == 201, session.text
    return headers, lesson_id, lesson, session.json()


def _answer_for(exercise):
    if exercise["type"] == "multiple_choice":
        return 0  # seed's correct MCQ answer is index 1; 0 is wrong (except where stated)
    return "definitely-wrong"


def test_session_creation_counts_exercises(client):
    headers, lesson_id, lesson, session = _start_lesson_session(client)
    assert session["kind"] == "lesson_exercises"
    assert session["total_exercises"] == 2
    assert session["status"] == "in_progress"


def test_exercise_submission_scoring_and_completion(client):
    headers, lesson_id, lesson, session = _start_lesson_session(client)
    exercises = lesson["exercises"]

    # Wrong MCQ answer first.
    wrong = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"exercise_id": exercises[0]["id"], "answer": 0},
    )
    assert wrong.status_code == 200, wrong.text
    body = wrong.json()
    assert body["feedback"]["correct"] is False
    assert body["feedback"]["expected"] == "Moien"
    assert body["coins_awarded"] == 0
    assert body["session"]["status"] == "in_progress"

    # Correct MCQ answer (index 1 per seed data).
    correct = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"exercise_id": exercises[0]["id"], "answer": 1},
    )
    body = correct.json()
    assert body["feedback"]["correct"] is True
    assert body["session"]["correct_exercises"] == 1

    # Fill-in-blank with case-insensitive match completes the session.
    fill = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"exercise_id": exercises[1]["id"], "answer": " merci "},
    )
    body = fill.json()
    assert body["feedback"]["correct"] is True
    assert body["session"]["status"] == "completed"
    assert body["coins_awarded"] == 5
    assert body["session"]["coins_awarded"] == 5

    # Enrollment progress recorded one completed lesson.
    course = client.get(f"/api/v1/courses/{lesson['course_id']}", headers=headers).json()
    assert course["enrollment"]["lessons_completed"] == 1


def test_reward_paid_once(client):
    headers, lesson_id, lesson, session = _start_lesson_session(client)
    exercises = lesson["exercises"]
    for exercise, answer in zip(exercises, [1, "merci"]):
        client.post(
            f"/api/v1/practice/sessions/{session['id']}/messages",
            headers=headers,
            json={"exercise_id": exercise["id"], "answer": answer},
        )

    # Session completed: further submissions are rejected (no double rewards).
    again = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"exercise_id": exercises[0]["id"], "answer": 1},
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "SESSION_COMPLETED"

    practice_transfers = [
        t for t in get_coin_client().records if t.transaction_type == "REWARD_PRACTICE"
    ]
    assert len(practice_transfers) == 1


def test_exercise_from_other_lesson_rejected(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    lesson_ids = [lesson["id"] for lesson in detail["lessons"]]

    first_lesson = client.get(f"/api/v1/lessons/{lesson_ids[0]}", headers=headers).json()
    second_lesson = client.get(f"/api/v1/lessons/{lesson_ids[1]}", headers=headers).json()

    session = client.post(
        "/api/v1/practice/sessions",
        headers=headers,
        json={"kind": "lesson_exercises", "lesson_id": lesson_ids[0]},
    ).json()

    foreign = client.post(
        f"/api/v1/practice/sessions/{session['id']}/messages",
        headers=headers,
        json={"exercise_id": second_lesson["exercises"][0]["id"], "answer": 0},
    )
    assert foreign.status_code == 422
    assert foreign.json()["error"]["code"] == "EXERCISE_INVALID"

    assert first_lesson["exercises"], "seed exercises missing"


def test_session_requires_lesson_enrollment(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    lesson_id = detail["lessons"][0]["id"]

    response = client.post(
        "/api/v1/practice/sessions",
        headers=headers,
        json={"kind": "lesson_exercises", "lesson_id": lesson_id},
    )
    assert response.status_code == 403
