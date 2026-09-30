"""PLACEHOLDER core.user model (Developer C scope).

Mission B needs working authentication to function, and the repository is empty, so
this file provides the minimum user storage required by the JWT shim. When Developer
C's real ``core`` module lands (users, communities, roles, community_members), replace
this model and the rest of the ``app/core`` package.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import UserRole
from app.shared.db import Base
from app.shared.schema_names import CORE_SCHEMA


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": CORE_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32), default=UserRole.LEARNER
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
