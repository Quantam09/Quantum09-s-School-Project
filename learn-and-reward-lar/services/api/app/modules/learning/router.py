"""Learning module API endpoints (Developer B scope — README section 7.2)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import AuthUser, get_current_user, get_optional_user
from app.modules.ai_chat.deps import ChatEngineDep
from app.modules.ai_chat.service import chat_turn
from app.modules.learning import service
from app.modules.learning.models import PracticeKind
from app.modules.learning.schemas import (
    AiChatRequest,
    AiChatResponse,
    CertificateClaimRequest,
    CertificateResponse,
    CertificateVerifyResponse,
    CourseDetail,
    EnrollResponse,
    ExerciseSubmission,
    FreeChatMessage,
    LessonDetail,
    PracticeSessionCreate,
    PracticeSessionDetail,
    SubmitResponse,
)
from app.shared.db import get_db
from app.shared.errors import AppError, ErrorCode
from app.shared.pagination import PageParams, page_payload

router = APIRouter(tags=["learning"])

DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[AuthUser, Depends(get_current_user)]


@router.get("/courses")
def list_courses(db: DbDep, page: Annotated[PageParams, Depends()]) -> dict:
    payload = service.list_courses(db, limit=page.limit, offset=page.offset)
    return page_payload(payload["items"], payload["total"], limit=page.limit, offset=page.offset)


@router.get("/courses/{course_id}", response_model=CourseDetail)
def get_course(
    course_id: UUID,
    db: DbDep,
    user: Annotated[AuthUser | None, Depends(get_optional_user)],
) -> CourseDetail:
    return service.get_course_detail(db, user, course_id)


@router.post("/courses/{course_id}/enroll", response_model=EnrollResponse)
def enroll_course(course_id: UUID, db: DbDep, user: UserDep) -> EnrollResponse:
    result = service.enroll(db, user, course_id)
    return EnrollResponse(**result)


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(lesson_id: UUID, db: DbDep, user: UserDep) -> LessonDetail:
    return service.get_lesson(db, user, lesson_id)


@router.post("/practice/sessions", response_model=PracticeSessionDetail, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    payload: PracticeSessionCreate, db: DbDep, user: UserDep
) -> PracticeSessionDetail:
    return service.create_practice_session(db, user, kind=payload.kind, lesson_id=payload.lesson_id)


@router.get("/practice/sessions/{session_id}", response_model=PracticeSessionDetail)
def get_practice_session(session_id: UUID, db: DbDep, user: UserDep) -> PracticeSessionDetail:
    return service.get_practice_session(db, user, session_id)


@router.post(
    "/practice/sessions/{session_id}/messages",
    response_model=SubmitResponse | AiChatResponse,
)
def submit_session_message(
    session_id: UUID,
    payload: ExerciseSubmission | FreeChatMessage,
    db: DbDep,
    user: UserDep,
    engine: ChatEngineDep,
) -> SubmitResponse | AiChatResponse:
    """Unified session message endpoint.

    * ``lesson_exercises`` sessions take an :class:`ExerciseSubmission`.
    * ``free_conversation`` sessions take a :class:`FreeChatMessage` and get an
      AI reply (RAG context + DeepSeek) through the ai_chat module.
    """
    if isinstance(payload, ExerciseSubmission):
        return service.submit_exercise(db, user, session_id, payload.exercise_id, payload.answer)
    from app.modules.learning import service as learning_service

    session = learning_service.get_practice_session(db, user, session_id)
    if session.kind is not PracticeKind.FREE_CONVERSATION:
        raise AppError(
            ErrorCode.EXERCISE_INVALID, "This session expects an exercise submission.", status_code=422
        )
    return chat_turn(db, user, session_id=session_id, message=payload.content, engine=engine)


@router.post("/ai/chat", response_model=AiChatResponse)
def ai_chat(payload: AiChatRequest, db: DbDep, user: UserDep, engine: ChatEngineDep) -> AiChatResponse:
    session_id = payload.session_id
    if session_id is None:
        created = service.create_practice_session(
            db, user, kind=PracticeKind.FREE_CONVERSATION, lesson_id=None
        )
        session_id = created.id
    else:
        # Verify ownership (raises 404 otherwise).
        service.get_practice_session(db, user, session_id)
    return chat_turn(db, user, session_id=session_id, message=payload.message, engine=engine)


@router.post("/certificates/claim", response_model=CertificateResponse)
def claim_certificate(payload: CertificateClaimRequest, db: DbDep, user: UserDep) -> CertificateResponse:
    return service.claim_certificate(db, user, payload.course_id)


@router.get("/certificates", response_model=list[CertificateResponse])
def list_my_certificates(db: DbDep, user: UserDep) -> list[CertificateResponse]:
    return service.list_certificates(db, user)


@router.get("/certificates/{code}/verify", response_model=CertificateVerifyResponse)
def verify_certificate(code: str, db: DbDep) -> CertificateVerifyResponse:
    return service.verify_certificate(db, code)
