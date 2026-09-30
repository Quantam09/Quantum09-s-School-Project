"""Lesson access control and content delivery."""

from __future__ import annotations

from tests.conftest import auth_headers, seed_course_id


def _enrolled_lesson(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    lesson_id = detail["lessons"][0]["id"]
    return headers, lesson_id


def test_lesson_requires_enrollment(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    lesson_id = detail["lessons"][0]["id"]

    response = client.get(f"/api/v1/lessons/{lesson_id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ENROLLMENT_REQUIRED"


def test_lesson_detail_after_enrollment(client):
    headers, lesson_id = _enrolled_lesson(client)
    response = client.get(f"/api/v1/lessons/{lesson_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["course_title"] == "Luxembourgish for Beginners"
    assert len(body["exercises"]) == 2
    assert body["vocabulary"][0]["term"] == "Moien"
    # Answers must never leak through the public lesson payload.
    assert all("answer" not in exercise for exercise in body["exercises"])


def test_unknown_lesson_404(client):
    headers = auth_headers(client)
    response = client.get(
        "/api/v1/lessons/00000000-0000-0000-0000-00000000000f", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LESSON_NOT_FOUND"
