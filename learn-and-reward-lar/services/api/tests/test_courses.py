"""Course catalog and enrollment flows (coin debit via the CoinClient adapter)."""

from __future__ import annotations

import pytest

from app.shared.coin_client import get_coin_client, reset_coin_client
from tests.conftest import auth_headers, seed_course_id


@pytest.fixture(autouse=True)
def fresh_coin_client():
    reset_coin_client()
    yield
    reset_coin_client()


def test_list_courses_returns_seed(client):
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    course = body["items"][0]
    assert course["slug"] == "luxembourgish-for-beginners"
    assert course["lesson_count"] == 3
    assert course["price_coins"] == 10
    assert course["language"] == "lb"


def test_list_courses_pagination(client):
    body = client.get("/api/v1/courses?limit=100").json()
    assert body["limit"] == 100
    body = client.get("/api/v1/courses?limit=0").json()
    assert body.get("error", {}).get("code") == "VALIDATION_ERROR"


def test_course_detail_includes_lessons(client):
    course_id = seed_course_id(client)
    response = client.get(f"/api/v1/courses/{course_id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["lessons"]) == 3
    assert body["enrollment"] is None


def test_enroll_requires_auth(client):
    course_id = seed_course_id(client)
    response = client.post(f"/api/v1/courses/{course_id}/enroll")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_enroll_debits_coins_once(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)

    first = client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["coins_spent"] == 10
    assert body["enrollment"]["status"] == "active"
    assert body["enrollment"]["total_lessons"] == 3

    # Idempotency guard: a second enroll conflicts instead of double-charging.
    second = client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_ENROLLED"

    transfers = get_coin_client().records
    assert len(transfers) == 1
    transfer = transfers[0]
    assert transfer.transaction_type == "COURSE_UNLOCK"
    amounts = sorted(entry.amount for entry in transfer.entries)
    assert amounts == [-10, 3, 7]  # user pays 10; community +7; platform +3


def test_course_detail_shows_enrollment(client):
    course_id = seed_course_id(client)
    headers = auth_headers(client)
    client.post(f"/api/v1/courses/{course_id}/enroll", headers=headers)
    body = client.get(f"/api/v1/courses/{course_id}", headers=headers).json()
    assert body["enrollment"]["status"] == "active"
    assert body["enrollment"]["lessons_completed"] == 0
