from __future__ import annotations

import json
from typing import Any

import pytest

from src.modules.menu_scan.adapters.gemini_translation import GeminiTranslationProvider
from src.modules.menu_scan.translation_provider import (
    TranslationTimeoutError,
    TranslationUnavailableError,
)


class FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict[str, Any]:
        return self._body


class FakeClient:
    def __init__(self, response: FakeResponse | list[FakeResponse] | Exception) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = response if isinstance(response, list) else [response]

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        response = self._responses[index]
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        pass


def test_gemini_translation_posts_correct_batch_request() -> None:
    provider_body = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(["Beef pho", "Spring rolls"])}]}}
        ]
    }
    client = FakeClient(FakeResponse(200, provider_body))
    provider = GeminiTranslationProvider(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
    )

    result = provider.translate_batch(
        texts=["Phở bò", "Gỏi cuốn"],
        source_language="vi",
        target_language="en",
    )

    call = client.calls[0]
    assert call["url"] == (
        "https://gemini.example.test/v1beta/models/gemini-2.5-flash:generateContent"
    )
    assert call["params"] == {"key": "test-key"}
    assert call["json"]["generationConfig"]["responseMimeType"] == "application/json"

    prompt = call["json"]["contents"][0]["parts"][0]["text"]
    assert "Phở bò" in prompt
    assert "Gỏi cuốn" in prompt

    assert result == ["Beef pho", "Spring rolls"]


def test_gemini_translation_maps_429_to_unavailable() -> None:
    provider = GeminiTranslationProvider(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="models/gemini-2.5-flash",
        timeout_seconds=5,
        client=FakeClient(FakeResponse(429)),  # type: ignore[arg-type]
    )

    with pytest.raises(TranslationUnavailableError):
        provider.translate_batch(
            texts=["Phở bò"],
            source_language="vi",
            target_language="en",
        )


def test_gemini_translation_rotates_key_on_429() -> None:
    provider_body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(["Beef pho"])}]}}]
    }
    client = FakeClient([FakeResponse(429), FakeResponse(200, provider_body)])
    provider = GeminiTranslationProvider(
        api_key="unused",
        api_keys=("key-1", "key-2"),
        api_base_url="https://gemini.example.test/v1beta",
        model="models/gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
        retry_backoff_seconds=0,
    )

    result = provider.translate_batch(
        texts=["Phá»Ÿ bÃ²"],
        source_language="vi",
        target_language="en",
    )

    assert result == ["Beef pho"]
    assert len(client.calls) == 2
    assert client.calls[0]["params"] == {"key": "key-1"}
    assert client.calls[1]["params"] == {"key": "key-2"}


def test_gemini_translation_maps_timeout() -> None:
    import httpx

    provider = GeminiTranslationProvider(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="models/gemini-2.5-flash",
        timeout_seconds=5,
        client=FakeClient(httpx.TimeoutException("timeout")),  # type: ignore[arg-type]
    )

    with pytest.raises(TranslationTimeoutError):
        provider.translate_batch(
            texts=["Phở bò"],
            source_language="vi",
            target_language="en",
        )


def test_gemini_translation_partial_result_pads_none() -> None:
    provider_body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(["Beef pho"])}]}}]
    }
    client = FakeClient(FakeResponse(200, provider_body))
    provider = GeminiTranslationProvider(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
    )

    result = provider.translate_batch(
        texts=["Phở bò", "Gỏi cuốn"],
        source_language="vi",
        target_language="en",
    )

    assert result == ["Beef pho", None]
