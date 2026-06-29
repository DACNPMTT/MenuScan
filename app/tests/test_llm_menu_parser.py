from __future__ import annotations

import json
from typing import Any

import pytest

from src.modules.menu_scan.llm_menu_parser import (
    GeminiMenuParser,
    LlmMenuParserUnavailableError,
)
from src.modules.menu_scan.ocr_contract import OcrDocument


class FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict[str, Any]:
        return self._body


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self._response


def test_gemini_parser_posts_structured_json_request() -> None:
    provider_body = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "title": "Quan Pho Sen",
                                    "items": [
                                        {
                                            "original_name": "Pho bo",
                                            "translated_name": "Beef pho",
                                            "price_text": "60.000 VND",
                                            "price": "60000.00",
                                            "currency": "VND",
                                            "sort_order": 0,
                                        }
                                    ],
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }
    client = FakeClient(FakeResponse(200, provider_body))
    parser = GeminiMenuParser(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
    )

    draft = parser.parse(
        _document("Pho bo 60.000 VND"),
        target_language="en",
    )

    call = client.calls[0]
    assert call["url"] == (
        "https://gemini.example.test/v1beta/"
        "models/gemini-2.5-flash:generateContent"
    )
    assert call["params"] == {"key": "test-key"}
    assert call["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseSchema" in call["json"]["generationConfig"]
    prompt = call["json"]["contents"][0]["parts"][0]["text"]
    assert "Pho bo 60.000 VND" in prompt
    assert draft.parsing_provider == "gemini-2.5-flash"
    assert draft.source_language == "vi"
    assert draft.target_language == "en"
    assert draft.items[0].translated_name == "Beef pho"
    assert draft.items[0].price == "60000.00"


def test_gemini_parser_maps_429_to_unavailable() -> None:
    parser = GeminiMenuParser(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="models/gemini-2.5-flash",
        timeout_seconds=5,
        client=FakeClient(FakeResponse(429)),  # type: ignore[arg-type]
    )

    with pytest.raises(LlmMenuParserUnavailableError):
        parser.parse(_document("Pho bo 60.000 VND"), target_language="en")


def _document(text: str) -> OcrDocument:
    return OcrDocument(
        provider="fixture",
        provider_model="fixture-v1",
        source_object_key="users/u/scans/s/source",
        detected_language="vi",
        text=text,
        pages=[],
        processing_time_ms=1,
    )
