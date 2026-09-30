"""AI chat: RAG license filtering, DeepSeek wiring, message persistence."""

from __future__ import annotations

import pytest

from app.modules.ai_chat import deps as chat_deps
from app.modules.ai_chat.engine import CULTURAL_DISCLAIMER, ChatEngine, EngineReply
from app.modules.learning.schemas import Citation
from tests.conftest import auth_headers


class StubEngine:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def chat(self, message: str, history=None) -> EngineReply:
        self.calls.append(message)
        return EngineReply(
            reply="Mock reply: Moien! Wéi geet et?",
            citations=[
                Citation(index=1, chunk_id="seed-chunk-001", resource_id="seed-resource-001", snippet="Moien!")
            ],
        )

    def translation_hint(self, *, prompt: str, expected: str, given: str) -> str | None:
        return "Watch the verb order."


@pytest.fixture()
def stub_engine(client):
    engine = StubEngine()
    client.app.dependency_overrides[chat_deps.get_chat_engine] = lambda: engine
    yield engine
    client.app.dependency_overrides.pop(chat_deps.get_chat_engine, None)


def test_ai_chat_returns_reply_and_citations(client, stub_engine):
    headers = auth_headers(client)
    response = client.post("/api/v1/ai/chat", headers=headers, json={"message": "Moien! Wéi geet et?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"].startswith("Mock reply")
    assert body["citations"][0]["chunk_id"] == "seed-chunk-001"
    assert body["disclaimer"] == CULTURAL_DISCLAIMER
    assert stub_engine.calls == ["Moien! Wéi geet et?"]

    # Conversation persisted and resumable via the session id.
    followup = client.post(
        "/api/v1/ai/chat",
        headers=headers,
        json={"message": "Merci!", "session_id": body["session_id"]},
    )
    assert followup.status_code == 200

    session = client.get(f"/api/v1/practice/sessions/{body['session_id']}", headers=headers)
    assert session.status_code == 200
    roles = [message["role"] for message in session.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_ai_chat_requires_auth(client):
    assert client.post("/api/v1/ai/chat", json={"message": "Moien"}).status_code == 401


def test_ai_chat_fails_cleanly_without_deepseek_key(client):
    headers = auth_headers(client)
    # No dependency override: the real engine with an unconfigured DeepSeekClient.
    response = client.post("/api/v1/ai/chat", headers=headers, json={"message": "Moien"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHAT_UNAVAILABLE"


def test_engine_filters_revoked_chunks(db_engine, fake_chat_engine):
    """The compliance gate must exclude revoked / non-licensed chunks from context."""
    engine: ChatEngine = fake_chat_engine
    result = engine.chat("Moien! Gudde Moien, wéi geet et?")

    cited_chunk_ids = {c.chunk_id for c in result.citations}
    assert "seed-chunk-006" not in cited_chunk_ids  # revoked in the seed fixture
    assert "seed-chunk-001" in cited_chunk_ids

    # The DeepSeek call carries the system prompt and numbered context.
    deepseek_messages = engine._deepseek.calls[-1]  # noqa: SLF001 - intentional white-box check
    assert any(m["role"] == "system" and "practice partner" in m["content"] for m in deepseek_messages)
    assert any("Reviewed context entries" in m["content"] for m in deepseek_messages)


def test_engine_skips_context_when_no_license_allows_it(db_engine):
    from app.modules.ai_chat.engine import ChatEngine

    class NoLicenseRag:
        def search(self, query: str, *, language: str = "lb", top_k: int = 4):
            from app.shared.rag_client import RagChunk

            return [
                RagChunk(
                    chunk_id="c1",
                    resource_id="r1",
                    chunk_text="Ech sinn aus Lëtzebuerg",
                    license={"learning_only": False, "research": False},
                )
            ]

    class SilentDeepSeek:
        def chat(self, messages, *, temperature=0.7):
            return "ok"

    engine = ChatEngine(deepseek=SilentDeepSeek(), rag=NoLicenseRag())
    result = engine.chat("Ech sinn aus Lëtzebuerg?")
    assert result.citations == []  # licensed-only filtering removed everything
