from __future__ import annotations

from typing import Any

from src.modules.menu_scan.ocr.adapters.google_vision import GoogleVisionOcrProvider
from src.modules.menu_scan.ocr.document_preprocessor import PreparedOcrPage


class FakeResponse:
    status_code = 200

    def json(self) -> dict[str, Any]:
        return {
            "responses": [
                {
                    "fullTextAnnotation": {
                        "text": "Phở bò 60.000đ",
                        "pages": [
                            {
                                "property": {
                                    "detectedLanguages": [
                                        {"languageCode": "vi"}
                                    ]
                                },
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


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse()


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


def test_google_vision_adapter_normalizes_fake_client_response() -> None:
    client = FakeClient()
    provider = GoogleVisionOcrProvider(
        api_key="test-key",
        api_base_url="https://vision.example.test/v1",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
    )

    document = provider.extract_document(
        pages=[
            PreparedOcrPage(
                page_index=0,
                image_bytes=b"png bytes",
                mime_type="image/png",
                width=1000,
                height=500,
            )
        ],
        source_object_key="users/u/scans/s/source",
    )

    assert client.calls[0]["url"] == "https://vision.example.test/v1/images:annotate"
    assert client.calls[0]["params"] == {"key": "test-key"}
    assert document.provider == "google_vision"
    assert document.detected_language == "vi"
    assert document.text == "Phở bò 60.000đ"
    assert document.pages[0].blocks[0].bounding_box.left == 0.01
    assert document.pages[0].blocks[0].lines[0].words[0].text == "Phở"
