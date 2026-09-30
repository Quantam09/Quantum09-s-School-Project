"""Auth endpoints (placeholder core module, Developer C scope).

Provides the minimum of Developer C's documented API surface (README section 7.3)
needed by Mission B: register, login, and current user. Replace wholesale when the
real core module (users, communities, roles, community_members) is merged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import AuthUser, get_current_user
from app.core.models import User
from app.core.security import create_access_token, hash_password, verify_password
from app.shared.db import get_db
from app.shared.errors import AppError, ErrorCode

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "Email is already registered.", status_code=409)
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.flush()
    return _user_response(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(ErrorCode.UNAUTHORIZED, "Incorrect email or password.", status_code=401)
    token = create_access_token(
        user_id=user.id, email=user.email, role=user.role.value, display_name=user.display_name
    )
    return TokenResponse(access_token=token, user=_user_response(user))


@router.get("/users/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[AuthUser, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role.value,
        created_at=datetime.now(UTC),
    )
