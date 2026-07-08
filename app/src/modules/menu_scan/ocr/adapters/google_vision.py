from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx

from src.modules.menu_scan.ocr.document_preprocessor import PreparedOcrPage
from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
    OcrWord,
)
from src.modules.menu_scan.ocr.provider import (
    ProviderProcessingError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _sleep_before_retry(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


@dataclass(frozen=True, slots=True)
class GoogleVisionOcrProvider:
    api_key: str
    api_base_url: str
    timeout_seconds: float
    feature_type: str = "DOCUMENT_TEXT_DETECTION"
    client: httpx.Client | None = None
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.5

    def extract_document(
        self,
        *,
        pages: list[PreparedOcrPage],
        source_object_key: str,
    ) -> OcrDocument:
        started_at = monotonic()
        responses = [self._annotate_page(page) for page in pages]
        ocr_pages = [
            _page_from_response(
                response=response,
                prepared_page=page,
            )
            for page, response in zip(pages, responses, strict=True)
        ]
        text = "\n\n".join(page.text for page in ocr_pages if page.text)

        return OcrDocument(
            provider="google_vision",
            provider_model=self.feature_type,
            source_object_key=source_object_key,
            detected_language=_first_detected_language(responses),
            text=text,
            confidence=_mean_optional(page.confidence for page in ocr_pages),
            pages=ocr_pages,
            processing_time_ms=int((monotonic() - started_at) * 1000),
            metadata={
                "page_count": len(ocr_pages),
            },
        )

    def _annotate_page(self, page: PreparedOcrPage) -> dict[str, Any]:
        payload = {
            "requests": [
                {
                    "image": {
                        "content": base64.b64encode(page.image_bytes).decode("ascii")
                    },
                    "features": [{"type": self.feature_type}],
                    "imageContext": {"languageHints": ["vi", "en"]},
                }
            ]
        }
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        attempts = max(1, self.max_attempts)
        try:
            for attempt in range(1, attempts + 1):
                try:
                    response = client.post(
                        f"{self.api_base_url}/images:annotate",
                        params={"key": self.api_key},
                        json=payload,
                    )
                except httpx.TimeoutException as error:
                    if attempt < attempts:
                        _sleep_before_retry(self.retry_backoff_seconds)
                        continue
                    raise ProviderTimeoutError() from error
                except httpx.HTTPError as error:
                    if attempt < attempts:
                        _sleep_before_retry(self.retry_backoff_seconds)
                        continue
                    raise ProviderUnavailableError() from error

                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < attempts:
                    _sleep_before_retry(self.retry_backoff_seconds)
                    continue
                break
        finally:
            if owns_client:
                client.close()

        if response.status_code in {408, 504}:
            raise ProviderTimeoutError()
        if response.status_code >= 500 or response.status_code == 429:
            raise ProviderUnavailableError()
        if response.status_code >= 400:
            raise ProviderProcessingError()

        body = response.json()
        result = (body.get("responses") or [{}])[0]
        if "error" in result:
            raise ProviderProcessingError()
        return result


def _page_from_response(
    *,
    response: dict[str, Any],
    prepared_page: PreparedOcrPage,
) -> OcrPage:
    annotation = response.get("fullTextAnnotation") or {}
    text = annotation.get("text") or ""
    provider_page = ((annotation.get("pages") or [{}]) or [{}])[0]
    blocks = [
        _block_from_response(
            block=block,
            page_index=prepared_page.page_index,
            block_index=block_index,
            page_width=prepared_page.width,
            page_height=prepared_page.height,
        )
        for block_index, block in enumerate(provider_page.get("blocks") or [])
    ]
    return OcrPage(
        page_index=prepared_page.page_index,
        width=prepared_page.width,
        height=prepared_page.height,
        text=text,
        confidence=_mean_optional(block.confidence for block in blocks),
        blocks=blocks,
    )


def _block_from_response(
    *,
    block: dict[str, Any],
    page_index: int,
    block_index: int,
    page_width: int,
    page_height: int,
) -> OcrBlock:
    lines: list[OcrLine] = []
    for paragraph_index, paragraph in enumerate(block.get("paragraphs") or []):
        line = _line_from_paragraph(
            paragraph=paragraph,
            page_index=page_index,
            block_index=block_index,
            line_index=paragraph_index,
            page_width=page_width,
            page_height=page_height,
        )
        if line.text:
            lines.append(line)

    text = "\n".join(line.text for line in lines)
    return OcrBlock(
        id=f"p{page_index}-b{block_index}",
        text=text,
        confidence=block.get("confidence"),
        bounding_box=_bounding_box(
            block.get("boundingBox"),
            page_width=page_width,
            page_height=page_height,
        ),
        lines=lines,
        column_index=None,
    )


def _line_from_paragraph(
    *,
    paragraph: dict[str, Any],
    page_index: int,
    block_index: int,
    line_index: int,
    page_width: int,
    page_height: int,
) -> OcrLine:
    words = [
        _word_from_response(
            word=word,
            page_index=page_index,
            block_index=block_index,
            line_index=line_index,
            word_index=word_index,
            page_width=page_width,
            page_height=page_height,
        )
        for word_index, word in enumerate(paragraph.get("words") or [])
    ]
    text = " ".join(word.text for word in words).strip()
    return OcrLine(
        id=f"p{page_index}-b{block_index}-l{line_index}",
        text=text,
        confidence=paragraph.get("confidence"),
        bounding_box=_bounding_box(
            paragraph.get("boundingBox"),
            page_width=page_width,
            page_height=page_height,
        ),
        words=words,
    )


def _word_from_response(
    *,
    word: dict[str, Any],
    page_index: int,
    block_index: int,
    line_index: int,
    word_index: int,
    page_width: int,
    page_height: int,
) -> OcrWord:
    text = "".join(((symbol.get("text") or "") for symbol in word.get("symbols") or []))
    return OcrWord(
        id=f"p{page_index}-b{block_index}-l{line_index}-w{word_index}",
        text=text,
        confidence=word.get("confidence"),
        bounding_box=_bounding_box(
            word.get("boundingBox"),
            page_width=page_width,
            page_height=page_height,
        ),
    )


def _bounding_box(
    bounding_poly: dict[str, Any] | None,
    *,
    page_width: int,
    page_height: int,
) -> OcrBoundingBox:
    vertices = (bounding_poly or {}).get("normalizedVertices")
    if vertices:
        xs = [float(vertex.get("x", 0)) for vertex in vertices]
        ys = [float(vertex.get("y", 0)) for vertex in vertices]
    else:
        vertices = (bounding_poly or {}).get("vertices") or []
        xs = [float(vertex.get("x", 0)) / page_width for vertex in vertices]
        ys = [float(vertex.get("y", 0)) / page_height for vertex in vertices]

    if not xs or not ys:
        return OcrBoundingBox(left=0, top=0, width=1, height=1)

    left = _clamp(min(xs))
    top = _clamp(min(ys))
    right = _clamp(max(xs))
    bottom = _clamp(max(ys))
    return OcrBoundingBox(
        left=left,
        top=top,
        width=_clamp(right - left),
        height=_clamp(bottom - top),
    )


def _clamp(value: float) -> float:
    return max(0, min(1, value))


def _mean_optional(values: object) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def _first_detected_language(responses: list[dict[str, Any]]) -> str | None:
    for response in responses:
        for page in (response.get("fullTextAnnotation") or {}).get("pages") or []:
            for property_name in ("property",):
                detected = page.get(property_name, {}).get("detectedLanguages") or []
                if detected:
                    return detected[0].get("languageCode")
    return None
