from __future__ import annotations

from typing import Any

import httpx
import pytest

from src.modules.menu_scan.ocr.adapters.google_vision import GoogleVisionOcrProvider
from src.modules.menu_scan.ocr.document_preprocessor import PreparedOcrPage
from src.modules.menu_scan.ocr.provider import (
    ProviderProcessingError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def _ok_body() -> dict[str, Any]:
    return {
        "responses": [
            {
                "fullTextAnnotation": {
                    "text": "Phở bò 60.000đ",
                    "pages": [
                        {
                            "property": {"detectedLanguages": [{"languageCode": "vi"}]},
                            "blocks": [
                                {
                                    "confidence": 0.96,
                                    "boundingBox": {
                                        "vertices": [
                                            {"x": 10, "y": 20},
                                            {"x": 210, "y": 20},
                                            {"x": 210, "y": 80},
                                            {"x": 10, "y": 80},
                                        ]
                                    },
                                    "paragraphs": [
                                        {
                                            "confidence": 0.97,
                                            "boundingBox": {
                                                "vertices": [
                                                    {"x": 10, "y": 20},
                                                    {"x": 210, "y": 20},
                                                    {"x": 210, "y": 80},
                                                    {"x": 10, "y": 80},
                                                ]
                                            },
                                            "words": [
                                                _word("Phở", 0.98),
                                                _word("bò", 0.97),
                                                _word("60.000đ", 0.95),
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        ]
    }


class FakeResponse:
    def __init__(
        self, status_code: int = 200, body: dict[str, Any] | None = None
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else _ok_body()

    def json(self) -> dict[str, Any]:
        return self._body


class FakeClient:
    """Queue of actions: a FakeResponse is returned, an Exception is raised."""

    def __init__(self, actions: FakeResponse | Exception | list[Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._actions = actions if isinstance(actions, list) else [actions]

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        index = min(len(self.calls) - 1, len(self._actions) - 1)
        action = self._actions[index]
        if isinstance(action, Exception):
            raise action
        return action


def _word(text: str, confidence: float) -> dict[str, Any]:
    return {
        "confidence": confidence,
        "boundingBox": {
            "vertices": [
                {"x": 10, "y": 20},
                {"x": 210, "y": 20},
                {"x": 210, "y": 80},
                {"x": 10, "y": 80},
            ]
        },
        "symbols": [{"text": character} for character in text],
    }


def _page() -> PreparedOcrPage:
    return PreparedOcrPage(
        page_index=0,
        image_bytes=b"png bytes",
        mime_type="image/png",
        width=1000,
        height=500,
    )


def _provider(client: FakeClient, **overrides: Any) -> GoogleVisionOcrProvider:
    return GoogleVisionOcrProvider(
        api_key="test-key",
        api_base_url="https://vision.example.test/v1",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
        retry_backoff_seconds=0,
        **overrides,
    )


def test_google_vision_adapter_normalizes_fake_client_response() -> None:
    client = FakeClient(FakeResponse())
    provider = _provider(client)

    document = provider.extract_document(
        pages=[_page()],
        source_object_key="users/u/scans/s/source",
    )

    assert client.calls[0]["url"] == "https://vision.example.test/v1/images:annotate"
    assert client.calls[0]["params"] == {"key": "test-key"}
    assert document.provider == "google_vision"
    assert document.detected_language == "vi"
    assert document.text == "Phở bò 60.000đ"
    assert document.pages[0].blocks[0].bounding_box.left == 0.01
    assert document.pages[0].blocks[0].lines[0].words[0].text == "Phở"


def test_google_vision_adapter_retries_timeout_then_succeeds() -> None:
    client = FakeClient([httpx.TimeoutException("timed out"), FakeResponse()])
    provider = _provider(client)

    document = provider.extract_document(pages=[_page()], source_object_key="key")

    assert len(client.calls) == 2
    assert document.text == "Phở bò 60.000đ"


def test_google_vision_adapter_raises_timeout_after_exhausting_retries() -> None:
    client = FakeClient(
        [
            httpx.TimeoutException("timed out"),
            httpx.TimeoutException("timed out"),
        ]
    )
    provider = _provider(client, max_attempts=2)

    with pytest.raises(ProviderTimeoutError):
        provider.extract_document(pages=[_page()], source_object_key="key")
    assert len(client.calls) == 2


def test_google_vision_adapter_retries_429_then_succeeds() -> None:
    client = FakeClient([FakeResponse(429), FakeResponse()])
    provider = _provider(client)

    document = provider.extract_document(pages=[_page()], source_object_key="key")

    assert len(client.calls) == 2
    assert document.text == "Phở bò 60.000đ"


def test_google_vision_adapter_raises_unavailable_after_exhausting_429_retries() -> (
    None
):
    client = FakeClient([FakeResponse(429), FakeResponse(429)])
    provider = _provider(client, max_attempts=2)

    with pytest.raises(ProviderUnavailableError):
        provider.extract_document(pages=[_page()], source_object_key="key")
    assert len(client.calls) == 2


def test_google_vision_adapter_retries_5xx_then_succeeds() -> None:
    client = FakeClient([FakeResponse(503), FakeResponse()])
    provider = _provider(client)

    document = provider.extract_document(pages=[_page()], source_object_key="key")

    assert len(client.calls) == 2
    assert document.text == "Phở bò 60.000đ"


def test_google_vision_adapter_raises_unavailable_after_exhausting_5xx_retries() -> (
    None
):
    client = FakeClient([FakeResponse(503), FakeResponse(503)])
    provider = _provider(client, max_attempts=2)

    with pytest.raises(ProviderUnavailableError):
        provider.extract_document(pages=[_page()], source_object_key="key")
    assert len(client.calls) == 2


def test_google_vision_adapter_maps_non_retryable_4xx_without_retry() -> None:
    client = FakeClient(FakeResponse(400))
    provider = _provider(client, max_attempts=3)

    with pytest.raises(ProviderProcessingError):
        provider.extract_document(pages=[_page()], source_object_key="key")
    assert len(client.calls) == 1


def test_google_vision_adapter_handles_missing_full_text_annotation_gracefully() -> (
    None
):
    client = FakeClient(FakeResponse(200, {"responses": [{}]}))
    provider = _provider(client)

    document = provider.extract_document(pages=[_page()], source_object_key="key")

    assert document.text == ""
    assert document.pages[0].confidence is None


def test_google_vision_adapter_maps_api_level_error_field_to_processing_error() -> None:
    client = FakeClient(
        FakeResponse(
            200, {"responses": [{"error": {"code": 3, "message": "Bad image"}}]}
        )
    )
    provider = _provider(client, max_attempts=3)

    with pytest.raises(ProviderProcessingError):
        provider.extract_document(pages=[_page()], source_object_key="key")
    assert len(client.calls) == 1
