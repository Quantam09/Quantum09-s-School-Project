"""Authentication dependencies (placeholder core module, Developer C scope)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.enums import UserRole
from app.core.security import decode_access_token
from app.shared.errors import AppError, ErrorCode

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: UUID
    email: str
    role: UserRole
    display_name: str = ""


def _credentials_or_error(
    credentials: HTTPAuthorizationCredentials | None,
) -> HTTPAuthorizationCredentials:
    if credentials is None:
        raise AppError(
            ErrorCode.UNAUTHORIZED,
            "Missing bearer token.",
            status_code=401,
        )
    return credentials


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthUser:
    token = _credentials_or_error(credentials).credentials
    payload = decode_access_token(token)
    try:
        user_id = UUID(payload["sub"])
        role = UserRole(payload.get("role", UserRole.LEARNER.value))
    except (KeyError, ValueError) as exc:
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid access token.", status_code=401) from exc
    return AuthUser(
        id=user_id, email=payload.get("email", ""), role=role, display_name=payload.get("name", "")
    )


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthUser | None:
    """Public endpoints that personalise when a token is present (and ignore bad ones)."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials)
    except AppError:
        return None
