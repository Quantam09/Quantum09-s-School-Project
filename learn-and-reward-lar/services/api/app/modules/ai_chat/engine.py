"""Chat engine: RAG context + DeepSeek conversation with the mandated dialogue
principles (README sections 10.3 / 10.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.ai_chat.deepseek import DeepSeekClient
from app.modules.learning.schemas import Citation
from app.shared.errors import AppError
from app.shared.rag_client import RagChunk, RagClient, is_chunk_usable_for_learning

SYSTEM_PROMPT = """You are a Luxembourgish (lb) language practice partner on the \
Learn-and-Reward platform.

Dialogue principles:
- Help the learner practise Luxembourgish. Reply in simple Luxembourgish and add a \
short English explanation when that helps the learner.
- You are NOT a cultural authority. When you are unsure, advise the learner to \
consult community teachers or elders.
- Ground factual and cultural answers in the provided context when available and cite \
them as [1], [2] matching the numbered context entries. If the context is not \
relevant, say so instead of inventing sources.
- Never generate unauthorised voice cloning and never produce commercial outputs \
from resources licensed with commercial_ai=false.
- Keep answers short and encouraging; ask one follow-up question to keep the \
conversation going.
"""

CULTURAL_DISCLAIMER = (
    "AI-generated practice content. The AI is not a cultural authority; consult "
    "community teachers or elders for authoritative guidance."
)

_HISTORY_LIMIT = 12


@dataclass
class EngineReply:
    reply: str
    citations: list[Citation] = field(default_factory=list)


class ChatEngine:
    """Retrieval-augmented conversation partner used by both the ai_chat endpoint and
    free-conversation practice sessions."""

    def __init__(self, deepseek: DeepSeekClient, rag: RagClient) -> None:
        self._deepseek = deepseek
        self._rag = rag

    def chat(self, message: str, history: list[dict] | None = None) -> EngineReply:
        chunks = self._retrieve(message)
        citations = [_citation(i, chunk) for i, chunk in enumerate(chunks, start=1)]
        context = _format_context(chunks)

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": f"Reviewed context entries:\n{context}"})
        for item in (history or [])[-_HISTORY_LIMIT:]:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": message})

        reply = self._deepseek.chat(messages)
        return EngineReply(reply=reply, citations=citations)

    def translation_hint(self, *, prompt: str, expected: str, given: str) -> str | None:
        """One-sentence coaching hint for a missed translation exercise (no answer)."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You coach Luxembourgish learners. Given a translation exercise, the "
                    "expected answer and the learner's answer, give ONE short encouraging "
                    "sentence pointing at the kind of mistake (word choice, word order, "
                    "spelling) without revealing the full expected answer. Reply in English."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Exercise: {prompt}\nLearner answered: {given}\n"
                    "(The expected answer is hidden from you.)"
                ),
            },
        ]
        try:
            return self._deepseek.chat(messages, temperature=0.3).strip()
        except AppError:
            return None

    def _retrieve(self, query: str) -> list[RagChunk]:
        retrieved = self._rag.search(query, language="lb", top_k=4)
        # Mandatory compliance filter: license tags and revocation state.
        return [chunk for chunk in retrieved if is_chunk_usable_for_learning(chunk)]


def _citation(index: int, chunk: RagChunk) -> Citation:
    return Citation(
        index=index,
        chunk_id=chunk.chunk_id,
        resource_id=chunk.resource_id,
        snippet=chunk.chunk_text[:160],
    )


def _format_context(chunks: list[RagChunk]) -> str:
    if not chunks:
        return ""
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        attribution = "community-reviewed resource"
        if chunk.license.get("attribution_required"):
            attribution += " (attribution required)"
        lines.append(f"[{i}] {chunk.chunk_text}  — {attribution}")
    return "\n".join(lines)
