"""Authentication endpoints (placeholder core module)."""

from __future__ import annotations

from tests.conftest import auth_headers


def test_register_and_login(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123", "display_name": "Alice"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "learner"

    login = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["user"]["display_name"] == "Alice"


def test_duplicate_register_conflicts(client):
    payload = {"email": "bob@example.com", "password": "password123", "display_name": "Bob"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "password123", "display_name": "Carol"},
    )
    response = client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_me_returns_profile(client):
    headers = auth_headers(client, email="dave@example.com")
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "dave@example.com"
