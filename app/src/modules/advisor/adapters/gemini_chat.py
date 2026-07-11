"""Chat providers for the dining assistant.

``GeminiChat`` calls the Google Gemini REST API (mirrors ``GeminiMenuParser``'s
httpx call). ``RuleBasedChat`` is the dev/test fallback so the endpoint works
without a key. Secrets are never logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


class ChatProviderError(Exception):
    """The chat provider could not produce an answer."""


class ChatProviderTimeoutError(ChatProviderError):
    """The chat provider timed out."""


class ChatProviderUnavailableError(ChatProviderError):
    """The chat provider is unavailable (quota, 5xx, no key)."""


class ChatProvider(Protocol):
    def complete(self, *, system: str, messages: list[tuple[str, str]]) -> str:
        """Return the assistant reply. ``messages`` is a list of
        ``(role, text)`` where role is ``"user"`` or ``"model"``."""
        ...


@dataclass
class RuleBasedChat:
    """Deterministic fallback when no LLM is configured (dev/test)."""

    def complete(self, *, system: str, messages: list[tuple[str, str]]) -> str:  # noqa: ARG002
        return (
            "Trợ lý AI chưa được bật ở môi trường này. Bạn xem nhãn gợi ý/cảnh báo "
            "trên từng món, hoặc hỏi trực tiếp quán để chắc chắn nhé."
        )


@dataclass
class GeminiChat:
    """Google Gemini ``generateContent`` chat client."""

    api_key: str
    api_base_url: str
    model: str
    timeout_seconds: float
    client: httpx.Client | None = None

    def complete(self, *, system: str, messages: list[tuple[str, str]]) -> str:
        if not self.api_key:
            raise ChatProviderUnavailableError("gemini chat has no api key")

        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": role, "parts": [{"text": text}]} for role, text in messages
            ],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
        }
        url = f"{self.api_base_url}/models/{self.model}:generateContent"
        try:
            response = client.post(url, params={"key": self.api_key}, json=body)
        except httpx.TimeoutException as error:
            raise ChatProviderTimeoutError("gemini chat timed out") from error
        except httpx.HTTPError as error:
            raise ChatProviderUnavailableError("gemini chat request failed") from error
        finally:
            if owns_client:
                client.close()

        if response.status_code in {408, 504}:
            raise ChatProviderTimeoutError("gemini chat timed out")
        if response.status_code == 429 or response.status_code >= 500:
            raise ChatProviderUnavailableError("gemini chat unavailable")
        if response.status_code >= 400:
            raise ChatProviderError("gemini chat rejected the request")

        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ChatProviderError("gemini chat returned invalid response") from error
        return text.strip()
