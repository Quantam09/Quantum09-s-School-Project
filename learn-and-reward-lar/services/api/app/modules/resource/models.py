"""Resource module ORM models (Developer A, ``resource`` schema — README section 8.2).

Tables: resources, resource_files, review_tasks, voice_consents. created_by /
community_id / reviewer_id are plain UUIDs without FK constraints — cross-module
references must not JOIN across schemas (README section 5). Voice cloning is never
performed in the MVP: voice_consents only records consent scope, revocation and an
audit trail (README section 10.5).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import Base
from app.shared.schema_names import RESOURCE_SCHEMA

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResourceType(str, enum.Enum):
    RECORDING = "recording"
    STORY = "story"
    SONG = "song"
    DICTIONARY = "dictionary"
    DIALOGUE = "dialogue"
    TEXT = "text"


class ResourceStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


class ReviewDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = {"schema": RESOURCE_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, native_enum=False, length=32), default=ResourceType.TEXT
    )
    language: Mapped[str] = mapped_column(String(12), default="lb")  # BCP-47
    # License tags per README section 8.2 (learning_only, research, commercial_ai,
    # remix, revocable, voice_clone_consent, attribution_required).
    license: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, native_enum=False, length=32), default=ResourceStatus.DRAFT, index=True
    )
    community_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    # Transcript produced by ASR and confirmed by human proofreading (README 10.1).
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    files: Mapped[list["ResourceFile"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    review_tasks: Mapped[list["ReviewTask"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class ResourceFile(Base):
    __tablename__ = "resource_files"
    __table_args__ = {"schema": RESOURCE_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{RESOURCE_SCHEMA}.resources.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="original")
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resource: Mapped[Resource] = relationship(back_populates="files")


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    __table_args__ = {"schema": RESOURCE_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{RESOURCE_SCHEMA}.resources.id"), index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, native_enum=False, length=16), default=ReviewDecision.PENDING
    )
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resource: Mapped[Resource] = relationship(back_populates="review_tasks")


class VoiceConsent(Base):
    __tablename__ = "voice_consents"
    __table_args__ = {"schema": RESOURCE_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{RESOURCE_SCHEMA}.resources.id"), nullable=True, index=True
    )
    speaker_display_name: Mapped[str] = mapped_column(String(200))
    # Consent scope, e.g. {"asr": true, "distribution": true, "voice_clone": false}.
    scope: Mapped[dict] = mapped_column(JsonType, default=dict)
    revoked: Mapped[bool] = mapped_column(default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audit_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
