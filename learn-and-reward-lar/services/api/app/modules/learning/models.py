"""Learning module ORM models (Developer B, ``learning`` schema — README section 8.4).

Tables: courses, lessons, exercises, enrollments, practice_sessions, chat_messages,
certificates. ``chat_messages`` lives in the learning schema per the spec; the
``ai_chat`` module writes through the learning service (cross-module calls use
internal services, never cross-schema writes).

user_id / community_id are plain UUIDs without FK constraints: cross-module
references must not JOIN across schemas (README section 5).
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import Base
from app.shared.schema_names import LEARNING_SCHEMA

# JSON columns render as JSONB on PostgreSQL and JSON on SQLite (test/dev fallbacks).
JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class CourseLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ExerciseType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    TRANSLATION = "translation"


class PracticeKind(str, enum.Enum):
    LESSON_EXERCISES = "lesson_exercises"
    FREE_CONVERSATION = "free_conversation"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(12), default="lb")  # BCP-47
    level: Mapped[CourseLevel] = mapped_column(
        Enum(CourseLevel, native_enum=False, length=32), default=CourseLevel.BEGINNER
    )
    price_coins: Mapped[int] = mapped_column(Integer, default=10)
    is_published: Mapped[bool] = mapped_column(default=False)
    # Developer C's core.communities reference (no cross-schema FK).
    community_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="course", order_by="Lesson.order_index", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.courses.id"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    # [{"term": "Moien", "translation": "Hello", "pronunciation": "MOY-en"}]
    vocabulary: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    course: Mapped[Course] = relationship(back_populates="lessons")
    exercises: Mapped[list[Exercise]] = relationship(
        back_populates="lesson", order_by="Exercise.order_index", cascade="all, delete-orphan"
    )


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.lessons.id"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, native_enum=False, length=32), default=ExerciseType.MULTIPLE_CHOICE
    )
    prompt: Mapped[str] = mapped_column(Text)
    # multiple_choice: ["option A", "option B", ...]; otherwise null
    options: Mapped[list | None] = mapped_column(JsonType, nullable=True)
    # {"value": 2} for multiple_choice, {"value": "moien", "alternations": [...]} otherwise
    answer: Mapped[dict] = mapped_column(JsonType)
    explanation: Mapped[str] = mapped_column(Text, default="")
    points: Mapped[int] = mapped_column(Integer, default=1)

    lesson: Mapped[Lesson] = relationship(back_populates="exercises")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.courses.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, native_enum=False, length=32), default=EnrollmentStatus.ACTIVE
    )
    # Completed lesson ids, tracked as JSON until a dedicated progress table is needed.
    completed_lesson_ids: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.lessons.id"), nullable=True, index=True
    )
    kind: Mapped[PracticeKind] = mapped_column(
        Enum(PracticeKind, native_enum=False, length=32), default=PracticeKind.LESSON_EXERCISES
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, length=32), default=SessionStatus.IN_PROGRESS
    )
    total_exercises: Mapped[int] = mapped_column(Integer, default=0)
    correct_exercises: Mapped[int] = mapped_column(Integer, default=0)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.practice_sessions.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False, length=16), default=MessageRole.USER
    )
    content: Mapped[str] = mapped_column(Text)
    # Assistant messages: [{"index": 1, "chunk_id": ..., "resource_id": ..., "snippet": ...}]
    citations: Mapped[list | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[PracticeSession | None] = relationship(back_populates="messages")


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = {"schema": LEARNING_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{LEARNING_SCHEMA}.courses.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))  # English certificate content
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked: Mapped[bool] = mapped_column(default=False)
