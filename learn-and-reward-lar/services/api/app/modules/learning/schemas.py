"""Pydantic request/response schemas for the learning module (English API surface)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.learning.models import (
    CourseLevel,
    EnrollmentStatus,
    ExerciseType,
    MessageRole,
    PracticeKind,
    SessionStatus,
)

# --- Courses -----------------------------------------------------------------


class CourseSummary(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str
    language: str
    level: CourseLevel
    price_coins: int
    is_published: bool
    lesson_count: int


class LessonSummary(BaseModel):
    id: UUID
    order_index: int
    title: str
    completed: bool = False


class CourseDetail(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str
    language: str
    level: CourseLevel
    price_coins: int
    is_published: bool
    lesson_count: int
    lessons: list[LessonSummary] = []
    enrollment: EnrollmentSummary | None = None


class VocabularyItem(BaseModel):
    term: str
    translation: str
    pronunciation: str | None = None


# --- Enrollment ---------------------------------------------------------------


class EnrollmentSummary(BaseModel):
    id: UUID
    course_id: UUID
    status: EnrollmentStatus
    lessons_completed: int
    total_lessons: int
    created_at: datetime
    completed_at: datetime | None = None


class EnrollResponse(BaseModel):
    enrollment: EnrollmentSummary
    coins_spent: int


# --- Lessons / exercises -------------------------------------------------------


class ExercisePublic(BaseModel):
    id: UUID
    order_index: int
    type: ExerciseType
    prompt: str
    options: list | None = None
    points: int


class LessonDetail(BaseModel):
    id: UUID
    course_id: UUID
    course_title: str
    order_index: int
    title: str
    content: str
    vocabulary: list[VocabularyItem] = []
    exercises: list[ExercisePublic] = []


# --- Practice sessions ---------------------------------------------------------


class PracticeSessionCreate(BaseModel):
    kind: PracticeKind = PracticeKind.LESSON_EXERCISES
    lesson_id: UUID | None = None


class PracticeSessionSummary(BaseModel):
    id: UUID
    kind: PracticeKind
    status: SessionStatus
    lesson_id: UUID | None
    total_exercises: int
    correct_exercises: int
    coins_awarded: int
    created_at: datetime
    completed_at: datetime | None = None


class PracticeSessionDetail(PracticeSessionSummary):
    exercises: list[ExercisePublic] = []
    messages: list[ChatMessageResponse] = []


class ExerciseSubmission(BaseModel):
    exercise_id: UUID
    answer: str | int = Field(description="Option index for multiple_choice, text otherwise.")


class FreeChatMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ExerciseFeedback(BaseModel):
    correct: bool
    expected: str | None = None
    explanation: str = ""
    ai_hint: str | None = None


class SubmitResponse(BaseModel):
    message_id: UUID
    feedback: ExerciseFeedback | None
    reply: str | None = None
    citations: list = []
    session: PracticeSessionSummary
    coins_awarded: int = 0


# --- Chat messages --------------------------------------------------------------


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID | None
    role: MessageRole
    content: str
    citations: list | None = None
    created_at: datetime


# --- Certificates ----------------------------------------------------------------


class CertificateClaimRequest(BaseModel):
    course_id: UUID


class CertificateResponse(BaseModel):
    id: UUID
    code: str
    course_id: UUID
    title: str
    issued_at: datetime
    revoked: bool


class CertificateVerifyResponse(BaseModel):
    valid: bool
    code: str
    title: str
    issued_at: datetime
    revoked: bool


# --- AI chat ---------------------------------------------------------------------


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = Field(
        default=None, description="Existing practice session to continue; a new one is created when omitted."
    )


class Citation(BaseModel):
    index: int
    chunk_id: str
    resource_id: str
    snippet: str


class AiChatResponse(BaseModel):
    session_id: UUID
    reply: str
    citations: list[Citation]
    disclaimer: str
