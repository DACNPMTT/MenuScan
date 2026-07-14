"""Chat providers for the dining assistant.

``GeminiChat`` runs on the same transport as the menu parser (``call_gemini``):
retries on transient 5xx/timeouts, backs off between key rotations, and normalises
the model path. It used to reimplement all of that, worse — no retry at all, so a
single network hiccup became a 503 in the diner's face.

``RuleBasedChat`` is the dev/test fallback so the endpoint works without a key.
Secrets are never logged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

import httpx

from src.modules.menu_scan.llm_menu_parser import (
    LlmMenuParserError,
    LlmMenuParserTimeoutError,
    LlmMenuParserUnavailableError,
    call_gemini,
)

logger = logging.getLogger(__name__)

# Room for a real answer without letting the model ramble at the diner.
_MAX_OUTPUT_TOKENS = 800


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


@lru_cache(maxsize=1)
def _shared_client(timeout_seconds: float) -> httpx.Client:
    """One pooled client for the whole process.

    A chat turn is short and interactive; opening a fresh TCP + TLS connection to
    Google for every single message is pure added latency the diner feels.
    """
    return httpx.Client(timeout=timeout_seconds)


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
    # Failover models tried in order. A model that is unavailable or quota-spent
    # falls through to the next. A TIMEOUT does not — see complete().
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

        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": role, "parts": [{"text": text}]} for role, text in messages
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": _MAX_OUTPUT_TOKENS,
                # The scan path disables thinking for latency; an interactive chat
                # needs it even more. Someone is watching a spinner.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        client = self.client or _shared_client(self.timeout_seconds)

        last_error: ChatProviderError | None = None
        for index, model in enumerate(models):
            try:
                return self._call(client, model, keys, body)
            except ChatProviderTimeoutError:
                # Do NOT fail over on a timeout. The next model would start a fresh
                # full-length attempt, so a 20s timeout becomes 40s+ of the diner
                # staring at a spinner before they get an error anyway.
                raise
            except ChatProviderError as error:
                last_error = error
                if index < len(models) - 1:
                    logger.warning(
                        "chat_model_failover model=%s reason=%s", model, error
                    )
                    continue
                raise

        # Unreachable: models is non-empty, so the loop returns or raises.
        raise last_error or ChatProviderUnavailableError("gemini chat unavailable")

    def _call(
        self,
        client: httpx.Client,
        model: str,
        keys: list[str],
        body: dict[str, Any],
    ) -> str:
        try:
            data = call_gemini(
                keys=keys,
                api_base_url=self.api_base_url,
                model=model,
                timeout_seconds=self.timeout_seconds,
                request_body=body,
                client=client,
            )
        except LlmMenuParserTimeoutError as error:
            raise ChatProviderTimeoutError("gemini chat timed out") from error
        except LlmMenuParserUnavailableError as error:
            raise ChatProviderUnavailableError("gemini chat unavailable") from error
        except LlmMenuParserError as error:
            raise ChatProviderError(f"gemini chat failed: {error}") from error

        return _extract_reply(data)


def _extract_reply(body: dict[str, Any]) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        raise ChatProviderError("gemini chat returned no candidates")

    candidate = candidates[0]
    # A reply cut off at the token ceiling still arrives as HTTP 200. Showing the
    # diner half a sentence and calling it an answer is worse than saying we failed.
    if candidate.get("finishReason") == "MAX_TOKENS":
        raise ChatProviderError("gemini chat hit the output ceiling")

    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise ChatProviderError("gemini chat returned empty content")
    return text
