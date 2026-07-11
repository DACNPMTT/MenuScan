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
    # Optional key pool tried in order; a 429 (quota) on one key rotates to the
    # next. Falls back to the single ``api_key`` when empty.
    api_keys: tuple[str, ...] = ()
    # Failover models tried in order (e.g. from LLM_MODELS); a model that a key
    # cannot use (4xx) falls through to the next. Falls back to [model].
    models: tuple[str, ...] = ()

    def _keys(self) -> list[str]:
        pool = [key for key in self.api_keys if key]
        if pool:
            return pool
        return [self.api_key] if self.api_key else []

    def _model_list(self) -> list[str]:
        chain = [model for model in self.models if model]
        if chain:
            return chain
        return [self.model] if self.model else []

    def complete(self, *, system: str, messages: list[tuple[str, str]]) -> str:
        keys = self._keys()
        if not keys:
            raise ChatProviderUnavailableError("gemini chat has no api key")
        models = self._model_list()
        if not models:
            raise ChatProviderUnavailableError("gemini chat has no model")

        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": role, "parts": [{"text": text}]} for role, text in messages
            ],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
        }
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            for index, model in enumerate(models):
                url = f"{self.api_base_url}/models/{model}:generateContent"
                try:
                    return self._call(client, url, keys, body)
                except ChatProviderError:
                    # A bad/unavailable model: fall through to the next one.
                    if index < len(models) - 1:
                        continue
                    raise
        finally:
            if owns_client:
                client.close()
        raise ChatProviderUnavailableError("gemini chat unavailable")

    def _call(
        self,
        client: httpx.Client,
        url: str,
        keys: list[str],
        body: dict[str, object],
    ) -> str:
        response = None
        for index, key in enumerate(keys):
            try:
                response = client.post(url, params={"key": key}, json=body)
            except httpx.TimeoutException as error:
                raise ChatProviderTimeoutError("gemini chat timed out") from error
            except httpx.HTTPError as error:
                raise ChatProviderUnavailableError("gemini chat request failed") from error
            # Rotate to the next key only on a quota/rate limit.
            if response.status_code == 429 and index < len(keys) - 1:
                continue
            break

        assert response is not None  # noqa: S101 — loop runs at least once
        if response.status_code in {408, 504}:
            raise ChatProviderTimeoutError("gemini chat timed out")
        if response.status_code == 429 or response.status_code >= 500:
            raise ChatProviderUnavailableError(
                f"gemini chat unavailable (HTTP {response.status_code})"
            )
        if response.status_code >= 400:
            raise ChatProviderError(
                f"gemini chat rejected the request (HTTP {response.status_code}): "
                f"{response.text[:300]}"
            )
        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ChatProviderError(
                f"gemini chat returned an unexpected response: {response.text[:300]}"
            ) from error
        return text.strip()
