"""Dependency providers for the ai_chat module. Tests override get_chat_engine."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.ai_chat.deepseek import DeepSeekClient
from app.modules.ai_chat.engine import ChatEngine
from app.shared.rag_client import get_rag_client


def get_deepseek_client() -> DeepSeekClient:
    return DeepSeekClient()


def get_chat_engine(
    deepseek: Annotated[DeepSeekClient, Depends(get_deepseek_client)],
) -> ChatEngine:
    return ChatEngine(deepseek=deepseek, rag=get_rag_client())


ChatEngineDep = Annotated[ChatEngine, Depends(get_chat_engine)]
