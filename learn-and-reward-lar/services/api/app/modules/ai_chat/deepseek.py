"""DeepSeek API client (Developer B, ai_chat module).

The platform strategy (README section 3.3) is: local small models for ASR/TTS/RAG,
a large-model API for conversation. The client is synchronous and fails fast with
``CHAT_UNAVAILABLE`` when no API key is configured or the API errors out.
"""

from __future__ import annotations

import httpx

from app.shared.config import get_settings
from app.shared.errors import AppError, ErrorCode


class DeepSeekClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.deepseek_api_key
        self._base_url = (base_url or settings.deepseek_base_url).rstrip("/")
        self._model = model or settings.deepseek_model
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def chat(self, messages: list[dict], *, temperature: float = 0.7) -> str:
        if not self.is_configured:
            raise AppError(
                ErrorCode.CHAT_UNAVAILABLE,
                "AI chat is not configured. Set DEEPSEEK_API_KEY to enable conversation practice.",
                status_code=503,
            )
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AppError(
                ErrorCode.CHAT_UNAVAILABLE,
                "DeepSeek API returned an error.",
                status_code=503,
                details={"status_code": exc.response.status_code},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                ErrorCode.CHAT_UNAVAILABLE,
                "Could not reach the DeepSeek API.",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

        body = response.json()
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AppError(
                ErrorCode.CHAT_UNAVAILABLE,
                "Unexpected response from the DeepSeek API.",
                status_code=503,
            ) from exc
