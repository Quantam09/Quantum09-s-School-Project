"""ai_chat internal service.

Conversations are persisted in ``learning.chat_messages`` — the table belongs to the
learning schema per the spec (README section 8.4); both modules are Developer B's, so
the ai_chat module writes through the same ORM models (documented internal-service
call, not a cross-schema write by another developer).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import AuthUser
from app.modules.ai_chat.engine import CULTURAL_DISCLAIMER, ChatEngine
from app.modules.learning.models import ChatMessage, MessageRole, PracticeSession
from app.modules.learning.schemas import AiChatResponse


def chat_turn(
    db: Session, user: AuthUser, *, session_id: UUID, message: str, engine: ChatEngine
) -> AiChatResponse:
    session = db.get(PracticeSession, session_id)
    if session is None or session.user_id != user.id:
        from app.shared.errors import AppError, ErrorCode

        raise AppError(ErrorCode.SESSION_NOT_FOUND, "Practice session not found.", status_code=404)

    history_rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    ).all()
    history = [{"role": row.role.value, "content": row.content} for row in history_rows]

    db.add(ChatMessage(session_id=session.id, user_id=user.id, role=MessageRole.USER, content=message))
    db.flush()

    result = engine.chat(message, history=history)

    db.add(
        ChatMessage(
            session_id=session.id,
            user_id=user.id,
            role=MessageRole.ASSISTANT,
            content=result.reply,
            citations=[citation.model_dump() for citation in result.citations],
        )
    )
    db.flush()

    return AiChatResponse(
        session_id=session.id,
        reply=result.reply,
        citations=result.citations,
        disclaimer=CULTURAL_DISCLAIMER,
    )
