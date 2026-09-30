"""RAG retrieval adapter.

Developer A owns the ``ai_voice`` module (RAG index over approved resources in
pgvector) and exposes ``POST /api/v1/rag/search``. The ai_chat module only consumes
retrieval results through this seam:

* ``StubRagClient`` — searches a small set of license-tagged seed chunks (JSON fixture)
  with naive keyword scoring. Includes a revoked chunk so the compliance filtering
  (license tags + ``revoked_at``) is real and demonstrable.
* ``HttpRagClient`` — calls Developer A's endpoint once merged.

Every chunk carries its license tags; the chat engine filters unusable chunks before
building the model context (README sections 3.2, 10.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.shared.config import Settings, get_settings
from app.shared.errors import AppError, ErrorCode

RAG_SEED_FILE = Path(__file__).resolve().parents[2] / "app" / "modules" / "ai_chat" / "rag_seed.json"


@dataclass
class RagChunk:
    chunk_id: str
    resource_id: str
    chunk_text: str
    language: str = "lb"
    license: dict[str, Any] = field(default_factory=dict)
    revoked_at: datetime | None = None


class RagClient(Protocol):
    def search(self, query: str, *, language: str = "lb", top_k: int = 4) -> list[RagChunk]: ...


def is_chunk_usable_for_learning(chunk: RagChunk) -> bool:
    """License gate enforced before any AI retrieval use (README sections 9.2, 10.3)."""
    if chunk.revoked_at is not None:
        return False
    license_tags = chunk.license or {}
    # Learning use is allowed when the resource permits learning and/or research.
    # commercial_ai=false does not block practice chat, only commercial outputs.
    return bool(license_tags.get("learning_only") or license_tags.get("research"))


class StubRagClient:
    def __init__(self, seed_file: Path = RAG_SEED_FILE) -> None:
        self._chunks: list[RagChunk] = []
        if seed_file.exists():
            raw = json.loads(seed_file.read_text(encoding="utf-8"))
            for item in raw["chunks"]:
                revoked = item.get("revoked_at")
                self._chunks.append(
                    RagChunk(
                        chunk_id=item["chunk_id"],
                        resource_id=item["resource_id"],
                        chunk_text=item["chunk_text"],
                        language=item.get("language", "lb"),
                        license=item.get("license", {}),
                        revoked_at=datetime.fromisoformat(revoked) if revoked else None,
                    )
                )

    def search(self, query: str, *, language: str = "lb", top_k: int = 4) -> list[RagChunk]:
        query_terms = _terms(query)
        if not query_terms:
            return []
        scored: list[tuple[float, RagChunk]] = []
        for chunk in self._chunks:
            chunk_terms = _terms(chunk.chunk_text)
            overlap = len(query_terms & chunk_terms)
            if overlap > 0:
                scored.append((overlap / (len(query_terms) + len(chunk_terms)), chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]


class HttpRagClient:
    def __init__(self, search_url: str) -> None:
        self._search_url = search_url.rstrip("/")

    def search(self, query: str, *, language: str = "lb", top_k: int = 4) -> list[RagChunk]:
        try:
            response = httpx.post(
                self._search_url,
                json={"query": query, "language": language, "top_k": top_k},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(
                ErrorCode.CHAT_UNAVAILABLE,
                "RAG search service is unavailable.",
                details={"reason": str(exc)},
            ) from exc
        chunks = []
        for item in response.json().get("chunks", []):
            revoked = item.get("revoked_at")
            chunks.append(
                RagChunk(
                    chunk_id=item["chunk_id"],
                    resource_id=item["resource_id"],
                    chunk_text=item["chunk_text"],
                    language=item.get("language", "lb"),
                    license=item.get("license", {}),
                    revoked_at=datetime.fromisoformat(revoked) if revoked else None,
                )
            )
        return chunks


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-zäëéèóöàè']+", text.lower()) if len(term) > 1}


_client: RagClient | None = None


def get_rag_client(settings: Settings | None = None) -> RagClient:
    global _client
    if _client is None:
        settings = settings or get_settings()
        if settings.rag_mode == "internal" and settings.rag_search_url:
            _client = HttpRagClient(settings.rag_search_url)
        else:
            _client = StubRagClient()
    return _client


def reset_rag_client() -> None:
    """Test helper."""
    global _client
    _client = None
