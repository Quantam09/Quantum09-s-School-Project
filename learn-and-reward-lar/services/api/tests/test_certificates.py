"""Micro-certificates: eligibility, claim, public verification."""

from __future__ import annotations

from tests.conftest import auth_headers, seed_course_id


def _complete_course(client):
    """Enroll and complete all three lessons; returns (headers, course_id)."""
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    detail = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()

    answers = {
        0: [1, "merci"],
        1: [2, "fënnef"],
        2: ["Ech sinn aus Lëtzebuerg", "ech"],
    }
    for lesson in detail["lessons"]:
        lesson_detail = client.get(f"/api/v1/lessons/{lesson['id']}", headers=headers).json()
        session = client.post(
            "/api/v1/practice/sessions",
            headers=headers,
            json={"kind": "lesson_exercises", "lesson_id": lesson["id"]},
        ).json()
        for exercise, answer in zip(lesson_detail["exercises"], answers[_lesson_index(lesson, detail)]):
            response = client.post(
                f"/api/v1/practice/sessions/{session['id']}/messages",
                headers=headers,
                json={"exercise_id": exercise["id"], "answer": answer},
            )
            assert response.status_code == 200, response.text
    return headers, course_id


def _lesson_index(lesson, detail):
    ids = [l["id"] for l in detail["lessons"]]
    return ids.index(lesson["id"])


def test_claim_requires_completed_course(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)

    response = client.post("/api/v1/certificates/claim", headers=headers, json={"course_id": course_id})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CERTIFICATE_NOT_READY"


def test_claim_after_completion_and_public_verify(client):
    headers, course_id = _complete_course(client)

    claim = client.post("/api/v1/certificates/claim", headers=headers, json={"course_id": course_id})
    assert claim.status_code == 200, claim.text
    certificate = claim.json()
    assert certificate["code"].startswith("LAR-")
    assert "Luxembourgish" in certificate["title"]

    # Public verification (no auth header).
    verify = client.get(f"/api/v1/certificates/{certificate['code']}/verify")
    assert verify.status_code == 200
    body = verify.json()
    assert body["valid"] is True
    assert body["title"] == certificate["title"]

    # Claiming twice conflicts.
    again = client.post("/api/v1/certificates/claim", headers=headers, json={"course_id": course_id})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CERTIFICATE_ALREADY_CLAIMED"


def test_verify_unknown_code_404(client):
    response = client.get("/api/v1/certificates/LAR-DEADBEEF00/verify")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CERTIFICATE_NOT_FOUND"


def test_list_my_certificates(client):
    headers, course_id = _complete_course(client)
    client.post("/api/v1/certificates/claim", headers=headers, json={"course_id": course_id})
    listing = client.get("/api/v1/certificates", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert client.get("/api/v1/certificates").status_code == 401
