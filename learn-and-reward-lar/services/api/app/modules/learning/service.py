"""Learning module business logic (Developer B).

Coin flows go exclusively through the shared CoinClient adapter (Developer C's
ledger owns balances); AI feedback goes through the ai_chat engine protocol.
"""

from __future__ import annotations

import re
import secrets
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import AuthUser
from app.modules.learning.models import (
    ChatMessage,
    Course,
    CourseLevel,
    Enrollment,
    EnrollmentStatus,
    Exercise,
    ExerciseType,
    Lesson,
    MessageRole,
    PracticeKind,
    PracticeSession,
    SessionStatus,
    utcnow,
)
from app.modules.learning.schemas import (
    CertificateResponse,
    CertificateVerifyResponse,
    CourseDetail,
    CourseSummary,
    EnrollmentSummary,
    ExerciseFeedback,
    ExercisePublic,
    LessonDetail,
    LessonSummary,
    PracticeSessionDetail,
    PracticeSessionSummary,
    SubmitResponse,
    VocabularyItem,
)
from app.shared.coin_client import (
    course_unlock_transfer,
    get_coin_client,
    practice_reward_transfer,
)
from app.shared.errors import AppError, ErrorCode
from app.shared.pagination import page_payload
from app.shared.rewards import REWARD_PRACTICE_COINS

_COMMUNITY_FALLBACK_ID = "community-pool"

_LEVEL_LABELS = {
    CourseLevel.BEGINNER: "Beginner",
    CourseLevel.INTERMEDIATE: "Intermediate",
    CourseLevel.ADVANCED: "Advanced",
}


# --- Courses ---------------------------------------------------------------------


def list_courses(db: Session, *, limit: int, offset: int) -> dict:
    query = select(Course).where(Course.is_published.is_(True)).order_by(Course.created_at)
    total = db.scalar(
        select(func.count()).select_from(Course).where(Course.is_published.is_(True))
    ) or 0
    courses = db.scalars(query.limit(limit).offset(offset)).all()
    items = [_course_summary(db, course) for course in courses]
    return page_payload(items, total, limit=limit, offset=offset)


def get_course_detail(db: Session, user: AuthUser | None, course_id: UUID) -> CourseDetail:
    course = _get_published_course(db, course_id)
    lessons = db.scalars(
        select(Lesson).where(Lesson.course_id == course.id).order_by(Lesson.order_index)
    ).all()
    completed_ids: set[str] = set()
    enrollment_summary = None
    if user is not None:
        enrollment = _get_enrollment(db, course.id, user.id)
        if enrollment is not None:
            completed_ids = set(enrollment.completed_lesson_ids or [])
            enrollment_summary = _enrollment_summary(enrollment, total_lessons=len(lessons))
    return CourseDetail(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        language=course.language,
        level=course.level,
        price_coins=course.price_coins,
        is_published=course.is_published,
        lesson_count=len(lessons),
        lessons=[
            LessonSummary(
                id=lesson.id,
                order_index=lesson.order_index,
                title=lesson.title,
                completed=str(lesson.id) in completed_ids,
            )
            for lesson in lessons
        ],
        enrollment=enrollment_summary,
    )


def enroll(db: Session, user: AuthUser, course_id: UUID) -> dict:
    course = _get_published_course(db, course_id)
    existing = _get_enrollment(db, course.id, user.id)
    if existing is not None:
        raise AppError(
            ErrorCode.ALREADY_ENROLLED, "Already enrolled in this course.", status_code=409
        )

    lessons = db.scalars(select(Lesson).where(Lesson.course_id == course.id)).all()
    community_id = str(course.community_id) if course.community_id else _COMMUNITY_FALLBACK_ID
    transfer = course_unlock_transfer(
        user_id=str(user.id),
        community_id=community_id,
        price_coins=course.price_coins,
        idempotency_key=f"course_unlock:{user.id}:{course.id}",
    )
    result = get_coin_client().transfer(transfer)
    if not result.accepted:
        raise AppError(ErrorCode.COIN_TRANSFER_FAILED, "Course unlock payment failed.", status_code=402)

    enrollment = Enrollment(course_id=course.id, user_id=user.id)
    db.add(enrollment)
    db.flush()
    return {
        "enrollment": _enrollment_summary(enrollment, total_lessons=len(lessons)),
        "coins_spent": course.price_coins,
    }


# --- Lessons ----------------------------------------------------------------------


def get_lesson(db: Session, user: AuthUser, lesson_id: UUID) -> LessonDetail:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise AppError(ErrorCode.LESSON_NOT_FOUND, "Lesson not found.", status_code=404)
    course = db.get(Course, lesson.course_id)
    assert course is not None
    enrollment = _get_enrollment(db, course.id, user.id)
    if enrollment is None:
        raise AppError(
            ErrorCode.ENROLLMENT_REQUIRED,
            "Enroll in the course before accessing its lessons.",
            status_code=403,
        )
    return LessonDetail(
        id=lesson.id,
        course_id=course.id,
        course_title=course.title,
        order_index=lesson.order_index,
        title=lesson.title,
        content=lesson.content,
        vocabulary=[VocabularyItem(**item) for item in (lesson.vocabulary or [])],
        exercises=[
            ExercisePublic(
                id=exercise.id,
                order_index=exercise.order_index,
                type=exercise.type,
                prompt=exercise.prompt,
                options=exercise.options,
                points=exercise.points,
            )
            for exercise in sorted(lesson.exercises, key=lambda e: e.order_index)
        ],
    )


# --- Practice sessions --------------------------------------------------------------


def create_practice_session(
    db: Session, user: AuthUser, *, kind: PracticeKind, lesson_id: UUID | None
) -> PracticeSessionDetail:
    lesson = None
    total_exercises = 0
    exercises_public: list[ExercisePublic] = []

    if kind is PracticeKind.LESSON_EXERCISES:
        if lesson_id is None:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "lesson_id is required for lesson_exercises sessions.",
                status_code=422,
            )
        lesson_detail = get_lesson(db, user, lesson_id)  # enforces enrollment
        exercises_public = lesson_detail.exercises
        total_exercises = len(exercises_public)
        lesson = db.get(Lesson, lesson_id)
        assert lesson is not None

    session = PracticeSession(
        user_id=user.id, lesson_id=lesson.id if lesson else None, kind=kind, total_exercises=total_exercises
    )
    db.add(session)
    db.flush()
    return PracticeSessionDetail(
        id=session.id,
        kind=session.kind,
        status=session.status,
        lesson_id=session.lesson_id,
        total_exercises=session.total_exercises,
        correct_exercises=session.correct_exercises,
        coins_awarded=session.coins_awarded,
        created_at=session.created_at,
        completed_at=session.completed_at,
        exercises=exercises_public,
        messages=[],
    )


def get_practice_session(db: Session, user: AuthUser, session_id: UUID) -> PracticeSessionDetail:
    session = _get_session(db, user, session_id)
    exercises_public: list[ExercisePublic] = []
    if session.lesson_id is not None:
        lesson_detail = get_lesson(db, user, session.lesson_id)
        exercises_public = lesson_detail.exercises
    return PracticeSessionDetail(
        id=session.id,
        kind=session.kind,
        status=session.status,
        lesson_id=session.lesson_id,
        total_exercises=session.total_exercises,
        correct_exercises=session.correct_exercises,
        coins_awarded=session.coins_awarded,
        created_at=session.created_at,
        completed_at=session.completed_at,
        exercises=exercises_public,
        messages=[_message_response(message) for message in session.messages],
    )


def submit_exercise(
    db: Session, user: AuthUser, session_id: UUID, submission_exercise_id: UUID, answer: str | int
) -> SubmitResponse:
    session = _get_session(db, user, session_id)
    if session.kind is not PracticeKind.LESSON_EXERCISES:
        raise AppError(
            ErrorCode.EXERCISE_INVALID, "This session does not accept exercise submissions.", status_code=422
        )
    if session.status is SessionStatus.COMPLETED:
        raise AppError(ErrorCode.SESSION_COMPLETED, "This session is already completed.", status_code=409)
    assert session.lesson_id is not None

    exercise = db.get(Exercise, submission_exercise_id)
    if exercise is None or exercise.lesson_id != session.lesson_id:
        raise AppError(ErrorCode.EXERCISE_INVALID, "Exercise does not belong to this session.", status_code=422)

    feedback = _score_exercise(exercise, answer)
    prior_contents = db.scalars(
        select(ChatMessage.content).where(
            ChatMessage.session_id == session.id,
            ChatMessage.role == MessageRole.USER,
            ChatMessage.content.like(f"exercise:{exercise.id}%"),
        )
    ).all()
    already_correct = any(content.endswith(":correct") for content in prior_contents)

    if feedback.correct and not already_correct:
        session.correct_exercises += 1

    user_message = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role=MessageRole.USER,
        content=f"exercise:{exercise.id}:{'correct' if feedback.correct else 'incorrect'}",
    )
    assistant_message = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role=MessageRole.ASSISTANT,
        content=_exercise_feedback_text(exercise, feedback),
    )
    db.add(user_message)
    db.add(assistant_message)
    db.flush()  # make the new messages visible to the completion check (autoflush is off)

    coins_awarded = 0
    session_completed = _maybe_complete_session(db, session)
    if session_completed:
        coins_awarded = _award_practice_coins(db, session)
        _record_lesson_progress(db, user.id, session.lesson_id)

    db.flush()
    return SubmitResponse(
        message_id=assistant_message.id,
        feedback=feedback,
        reply=assistant_message.content,
        citations=[],
        session=_session_summary(session),
        coins_awarded=coins_awarded,
    )


def _score_exercise(exercise: Exercise, answer: str | int) -> ExerciseFeedback:
    expected_raw = exercise.answer or {}
    explanation = exercise.explanation or ""

    if exercise.type is ExerciseType.MULTIPLE_CHOICE:
        try:
            given_index = int(answer)
        except (TypeError, ValueError):
            return ExerciseFeedback(correct=False, expected=None, explanation=explanation)
        expected_index = expected_raw.get("value")
        options = exercise.options or []
        expected_text = (
            str(options[expected_index]) if isinstance(expected_index, int) and expected_index < len(options) else None
        )
        return ExerciseFeedback(
            correct=given_index == expected_index,
            expected=expected_text,
            explanation=explanation,
        )

    # fill_in_blank and translation compare normalized text with optional alternatives.
    expected_value = str(expected_raw.get("value", ""))
    alternatives = [str(a) for a in expected_raw.get("alternatives", [])]
    accepted = [_normalize(expected_value)] + [_normalize(a) for a in alternatives]
    correct = _normalize(str(answer)) in accepted
    return ExerciseFeedback(correct=correct, expected=expected_value, explanation=explanation)


def _exercise_feedback_text(exercise: Exercise, feedback: ExerciseFeedback) -> str:
    verdict = "Correct!" if feedback.correct else "Not quite."
    parts = [verdict]
    if not feedback.correct and feedback.expected:
        parts.append(f"Expected answer: {feedback.expected}.")
    if feedback.explanation:
        parts.append(feedback.explanation)
    return " ".join(parts)


def _maybe_complete_session(db: Session, session: PracticeSession) -> bool:
    if session.status is SessionStatus.COMPLETED:
        return False
    submitted_exercise_ids = set(
        db.scalars(
            select(ChatMessage.content).where(
                ChatMessage.session_id == session.id, ChatMessage.role == MessageRole.USER
            )
        ).all()
    )
    distinct = {
        content.split(":")[1] for content in submitted_exercise_ids if content.startswith("exercise:")
    }
    if len(distinct) >= session.total_exercises and session.total_exercises > 0:
        session.status = SessionStatus.COMPLETED
        session.completed_at = utcnow()
        return True
    return False


def _award_practice_coins(db: Session, session: PracticeSession) -> int:
    if session.coins_awarded:
        return 0
    transfer = practice_reward_transfer(
        user_id=str(session.user_id), idempotency_key=f"practice:{session.id}"
    )
    result = get_coin_client().transfer(transfer)
    if result.accepted:
        session.coins_awarded = REWARD_PRACTICE_COINS
    return session.coins_awarded


def _record_lesson_progress(db: Session, user_id: UUID, lesson_id: UUID) -> None:
    lesson = db.get(Lesson, lesson_id)
    assert lesson is not None
    enrollment = _get_enrollment(db, lesson.course_id, user_id)
    if enrollment is None:
        return
    completed = set(enrollment.completed_lesson_ids or [])
    completed.add(str(lesson_id))
    enrollment.completed_lesson_ids = sorted(completed)

    total_lessons = db.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.course_id == lesson.course_id)
    ) or 0
    if len(completed) >= total_lessons and enrollment.status is EnrollmentStatus.ACTIVE:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = utcnow()


# --- Certificates -------------------------------------------------------------------


def claim_certificate(db: Session, user: AuthUser, course_id: UUID) -> CertificateResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise AppError(ErrorCode.COURSE_NOT_FOUND, "Course not found.", status_code=404)
    enrollment = _get_enrollment(db, course.id, user.id)
    if enrollment is None or enrollment.status is not EnrollmentStatus.COMPLETED:
        raise AppError(
            ErrorCode.CERTIFICATE_NOT_READY,
            "Complete all lessons before claiming the certificate.",
            status_code=409,
        )

    from app.modules.learning.models import Certificate

    existing = db.scalars(
        select(Certificate).where(
            Certificate.user_id == user.id, Certificate.course_id == course.id
        )
    ).first()
    if existing is not None:
        raise AppError(
            ErrorCode.CERTIFICATE_ALREADY_CLAIMED,
            "Certificate already claimed for this course.",
            status_code=409,
        )

    title = f"Micro-Certificate: Luxembourgish {_LEVEL_LABELS[course.level]} — {course.title}"
    certificate = Certificate(
        code=_new_certificate_code(db), user_id=user.id, course_id=course.id, title=title
    )
    db.add(certificate)
    db.flush()
    return CertificateResponse(
        id=certificate.id,
        code=certificate.code,
        course_id=certificate.course_id,
        title=certificate.title,
        issued_at=certificate.issued_at,
        revoked=certificate.revoked,
    )


def list_certificates(db: Session, user: AuthUser) -> list[CertificateResponse]:
    from app.modules.learning.models import Certificate

    certificates = db.scalars(
        select(Certificate).where(Certificate.user_id == user.id).order_by(Certificate.issued_at)
    ).all()
    return [
        CertificateResponse(
            id=c.id, code=c.code, course_id=c.course_id, title=c.title, issued_at=c.issued_at, revoked=c.revoked
        )
        for c in certificates
    ]


def verify_certificate(db: Session, code: str) -> CertificateVerifyResponse:
    from app.modules.learning.models import Certificate

    certificate = db.scalar(select(Certificate).where(Certificate.code == code.strip().upper()))
    if certificate is None:
        raise AppError(ErrorCode.CERTIFICATE_NOT_FOUND, "Certificate code not found.", status_code=404)
    return CertificateVerifyResponse(
        valid=not certificate.revoked,
        code=certificate.code,
        title=certificate.title,
        issued_at=certificate.issued_at,
        revoked=certificate.revoked,
    )


def _new_certificate_code(db: Session) -> str:
    from app.modules.learning.models import Certificate

    while True:
        code = f"LAR-{secrets.token_hex(5).upper()}"
        if db.scalar(select(Certificate).where(Certificate.code == code)) is None:
            return code


# --- Helpers ------------------------------------------------------------------------


def _get_published_course(db: Session, course_id: UUID) -> Course:
    course = db.get(Course, course_id)
    if course is None or not course.is_published:
        raise AppError(ErrorCode.COURSE_NOT_FOUND, "Course not found.", status_code=404)
    return course


def _get_enrollment(db: Session, course_id: UUID, user_id: UUID) -> Enrollment | None:
    return db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == course_id, Enrollment.user_id == user_id
        )
    ).first()


def _get_session(db: Session, user: AuthUser, session_id: UUID) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if session is None or session.user_id != user.id:
        raise AppError(ErrorCode.SESSION_NOT_FOUND, "Practice session not found.", status_code=404)
    return session


def _course_summary(db: Session, course: Course) -> CourseSummary:
    lesson_count = db.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.course_id == course.id)
    ) or 0
    return CourseSummary(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        language=course.language,
        level=course.level,
        price_coins=course.price_coins,
        is_published=course.is_published,
        lesson_count=lesson_count,
    )


def _enrollment_summary(enrollment: Enrollment, *, total_lessons: int) -> EnrollmentSummary:
    return EnrollmentSummary(
        id=enrollment.id,
        course_id=enrollment.course_id,
        status=enrollment.status,
        lessons_completed=len(enrollment.completed_lesson_ids or []),
        total_lessons=total_lessons,
        created_at=enrollment.created_at,
        completed_at=enrollment.completed_at,
    )


def _session_summary(session: PracticeSession) -> PracticeSessionSummary:
    return PracticeSessionSummary(
        id=session.id,
        kind=session.kind,
        status=session.status,
        lesson_id=session.lesson_id,
        total_exercises=session.total_exercises,
        correct_exercises=session.correct_exercises,
        coins_awarded=session.coins_awarded,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


def _message_response(message: ChatMessage):
    from app.modules.learning.schemas import ChatMessageResponse

    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        citations=message.citations,
        created_at=message.created_at,
    )


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[.!?,;:'\"()]+", "", text)
    return re.sub(r"\s+", " ", text)
