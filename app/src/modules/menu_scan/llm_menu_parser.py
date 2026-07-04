from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from src.modules.menu_scan.ocr_contract import OcrDocument, ParsedMenuDraft


class LlmMenuParserError(Exception):
    """Raised when the LLM parser cannot produce a valid parsed menu."""


class LlmMenuParserTimeoutError(LlmMenuParserError):
    """Raised when the LLM parser exceeds the configured timeout."""


class LlmMenuParserUnavailableError(LlmMenuParserError):
    """Raised when the LLM provider is temporarily unavailable or exhausted."""


@dataclass(frozen=True, slots=True)
class GeminiMenuParser:
    api_key: str
    api_base_url: str
    model: str
    timeout_seconds: float
    client: httpx.Client | None = None
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.5

    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
    ) -> ParsedMenuDraft:
        body = self._generate(document=document, target_language=target_language)
        payload = _extract_json_payload(body)
        payload.setdefault("items", [])
        payload.setdefault("target_language", target_language)
        if document.detected_language is not None:
            payload.setdefault("source_language", document.detected_language)

        draft = ParsedMenuDraft.model_validate(payload)
        return draft.model_copy(
            update={
                "parsing_provider": draft.parsing_provider or self.model,
                "target_language": target_language,
            }
        )

    def _generate(
        self,
        *,
        document: OcrDocument,
        target_language: str,
    ) -> dict[str, Any]:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        attempts = max(1, self.max_attempts)
        try:
            for attempt in range(1, attempts + 1):
                try:
                    response = client.post(
                        f"{self.api_base_url}/{_model_path(self.model)}:generateContent",
                        params={"key": self.api_key},
                        json=_build_request(
                            document=document,
                            target_language=target_language,
                        ),
                    )
                except httpx.TimeoutException as error:
                    if attempt < attempts:
                        _sleep_before_retry(self.retry_backoff_seconds)
                        continue
                    raise LlmMenuParserTimeoutError("gemini parser timed out") from error
                except httpx.HTTPError as error:
                    if attempt < attempts:
                        _sleep_before_retry(self.retry_backoff_seconds)
                        continue
                    raise LlmMenuParserUnavailableError(
                        "gemini parser request failed"
                    ) from error

                if response.status_code in {408, 500, 502, 503, 504} and attempt < attempts:
                    _sleep_before_retry(self.retry_backoff_seconds)
                    continue
                break
        finally:
            if owns_client:
                client.close()

        if response.status_code in {408, 504}:
            raise LlmMenuParserTimeoutError("gemini parser timed out")
        if response.status_code == 429 or response.status_code >= 500:
            raise LlmMenuParserUnavailableError("gemini parser unavailable")
        if response.status_code >= 400:
            raise LlmMenuParserError("gemini parser rejected the request")

        try:
            return response.json()
        except ValueError as error:
            raise LlmMenuParserError("gemini parser returned invalid json") from error


def _model_path(model: str) -> str:
    normalized = model.strip("/")
    if normalized.startswith("models/"):
        return normalized
    return f"models/{normalized}"


def _sleep_before_retry(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _build_request(
    *,
    document: OcrDocument,
    target_language: str,
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": _build_prompt(
                            document=document,
                            target_language=target_language,
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _parsed_menu_schema(),
        },
    }


def _build_prompt(
    *,
    document: OcrDocument,
    target_language: str,
) -> str:
    detected = document.detected_language or "unknown"
    layout_text = _build_layout_text(document)
    return (
        "You convert OCR text from restaurant menus into structured JSON.\n"
        "\n"
        "Menu text is extracted from an image and may lose original column/layout "
        "structure. Apply these rules when reconstructing items:\n"
        "- A line that looks like a dish name starts a new item.\n"
        "- The line(s) immediately following a dish name line, that do NOT "
        "themselves look like a new dish name or a new price line, are almost "
        "always the description or ingredient list for that dish. Attach them "
        "to original_description; do not discard them and do not treat them as "
        "a separate item.\n"
        "- A line consisting mostly of comma-separated nouns or ingredients "
        "directly below a dish name is a description, not a new dish.\n"
        "- Only start a new item when you see a new price, a new number/bullet, "
        "or a line that clearly reads as a dish title rather than a sentence "
        "fragment.\n"
        "- If in doubt whether a line is a new dish or a continuation, prefer "
        "treating it as a description of the previous dish rather than "
        "inventing a new item.\n"
        "- The structured OCR text below is grouped by OCR block. Lines within "
        "the same BLOCK are spatially close together and very likely belong to "
        "the same dish entry (name + description + price), even when they read "
        "like separate sentences.\n"
        "- Do not split one BLOCK into multiple dish items unless it clearly "
        "contains more than one price or more than one distinct dish name.\n"
        "- Preserve unusual dish names verbatim in original_name.\n"
        "- Do not invent items that are not present in the OCR text.\n"
        "- Set price to null when the price is missing or confidence is low.\n"
        "- When price is known, use a decimal string such as 60000.00.\n"
        "- Use ISO currency codes such as VND or USD when currency is clear.\n"
        "- Translate names and descriptions into the requested target language.\n"
        "- Omit optional fields when unknown.\n\n"
        f"Detected source language: {detected}\n"
        f"Target language: {target_language}\n"
        "Structured OCR blocks:\n"
        f"{layout_text}\n\n"
        "Raw OCR text fallback:\n"
        f"{document.text}"
    )


def _build_layout_text(document: OcrDocument) -> str:
    if not document.pages:
        return document.text

    pages_out: list[str] = []
    for page in sorted(document.pages, key=lambda item: item.page_index):
        block_parts: list[str] = []
        for block in sorted(page.blocks, key=_block_sort_key):
            box = block.bounding_box
            lines = sorted(block.lines, key=_line_sort_key)
            line_parts = [
                (
                    f"  LINE id={line.id} "
                    f"x={line.bounding_box.left:.3f} y={line.bounding_box.top:.3f} "
                    f"w={line.bounding_box.width:.3f} h={line.bounding_box.height:.3f}: "
                    f"{line.text}"
                )
                for line in lines
                if line.text.strip()
            ]
            if not line_parts and block.text.strip():
                line_parts = [f"  TEXT: {block.text.strip()}"]
            if line_parts:
                block_parts.append(
                    (
                        f"BLOCK id={block.id} "
                        f"x={box.left:.3f} y={box.top:.3f} "
                        f"w={box.width:.3f} h={box.height:.3f}\n"
                        + "\n".join(line_parts)
                    )
                )
        if block_parts:
            pages_out.append(
                f"PAGE {page.page_index} width={page.width} height={page.height}\n"
                + "\n\n".join(block_parts)
            )

    return "\n\n".join(pages_out) or document.text


def _block_sort_key(block: object) -> tuple[float, float]:
    bounding_box = block.bounding_box  # type: ignore[attr-defined]
    return (bounding_box.top, bounding_box.left)


def _line_sort_key(line: object) -> tuple[float, float]:
    bounding_box = line.bounding_box  # type: ignore[attr-defined]
    return (bounding_box.top, bounding_box.left)


def _parsed_menu_schema() -> dict[str, Any]:
    item_schema = {
        "type": "OBJECT",
        "properties": {
            "original_name": {"type": "STRING"},
            "original_description": {"type": "STRING"},
            "translated_name": {"type": "STRING"},
            "translated_description": {"type": "STRING"},
            "base_name": {"type": "STRING"},
            "variant_name": {"type": "STRING"},
            "variant_group": {"type": "STRING"},
            "price_text": {"type": "STRING"},
            "price": {"type": "STRING"},
            "currency": {"type": "STRING"},
            "category": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "sort_order": {"type": "INTEGER"},
        },
        "required": ["original_name", "sort_order"],
    }
    return {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "source_language": {"type": "STRING"},
            "target_language": {"type": "STRING"},
            "default_currency": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "items": {"type": "ARRAY", "items": item_schema},
            "warnings": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
        },
        "required": ["items"],
    }


def _extract_json_payload(body: dict[str, Any]) -> dict[str, Any]:
    candidates = body.get("candidates") or []
    if not candidates:
        raise LlmMenuParserError("gemini parser returned no candidates")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise LlmMenuParserError("gemini parser returned empty content")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise LlmMenuParserError("gemini parser returned invalid content") from error
    if not isinstance(payload, dict):
        raise LlmMenuParserError("gemini parser returned a non-object payload")
    return payload
