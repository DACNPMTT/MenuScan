from __future__ import annotations

import base64
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from src.modules.menu_scan.menu_table import build_menu_table, rows_to_csv
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
    # Optional key pool. When set, a 429 (rate/quota limit) on one key rotates to
    # the next key for the same model/request before giving up. Falls back to the
    # single ``api_key`` when empty.
    api_keys: tuple[str, ...] = ()
    # When True, a deterministic geometry pass (menu_table) pre-pairs each dish
    # with its price and size, and that CSV is embedded in the prompt as a strong
    # name↔price anchor. Off falls back to the plain OCR text / coordinate dump.
    prealign_csv: bool = True

    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
        images: Sequence[bytes] | None = None,
        preferences_data: list[dict[str, Any]] | None = None,
        is_group: bool = False,
    ) -> ParsedMenuDraft:
        body = self._generate(
            document=document,
            target_language=target_language,
            images=images,
            preferences_data=preferences_data,
            is_group=is_group,
        )
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
                "translation_complete": True,
            }
        )

    def _effective_keys(self) -> list[str]:
        """The key pool to try, in order. Falls back to the single api_key."""
        if self.api_keys:
            keys = [key for key in self.api_keys if key]
            if keys:
                return keys
        return [self.api_key] if self.api_key else []

    def _generate(
        self,
        *,
        document: OcrDocument,
        target_language: str,
        images: Sequence[bytes] | None = None,
        preferences_data: list[dict[str, Any]] | None = None,
        is_group: bool = False,
    ) -> dict[str, Any]:
        keys = self._effective_keys()
        if not keys:
            raise LlmMenuParserError("gemini parser has no api key")

        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        request_body = _build_request(
            document=document,
            target_language=target_language,
            images=images,
            prealign_csv=self.prealign_csv,
            preferences_data=preferences_data,
            is_group=is_group,
        )
        try:
            response = None
            for index, key in enumerate(keys):
                response = self._request_with_retries(client, key, request_body)
                # Rotate to the next key only when this key is rate/quota limited
                # (429). Other outcomes (success, 5xx, 4xx) are handled below.
                if response.status_code == 429 and index < len(keys) - 1:
                    _sleep_before_retry(self.retry_backoff_seconds)
                    continue
                break
        finally:
            if owns_client:
                client.close()

        assert response is not None  # noqa: S101 — loop runs at least once
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

    def _request_with_retries(
        self,
        client: httpx.Client,
        key: str,
        request_body: dict[str, Any],
    ) -> httpx.Response:
        """POST with the given key, retrying transient 5xx/timeouts in place.

        Returns the final response (which the caller inspects for 429 to decide
        whether to rotate keys). Raises on exhausted timeouts/transport errors.
        """
        attempts = max(1, self.max_attempts)
        url = f"{self.api_base_url}/{_model_path(self.model)}:generateContent"
        for attempt in range(1, attempts + 1):
            try:
                response = client.post(url, params={"key": key}, json=request_body)
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
            return response

        raise LlmMenuParserUnavailableError("gemini parser unavailable")


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
    images: Sequence[bytes] | None = None,
    prealign_csv: bool = True,
    preferences_data: list[dict[str, Any]] | None = None,
    is_group: bool = False,
) -> dict[str, Any]:
    image_list = [image for image in (images or []) if image]
    has_images = bool(image_list)
    parts: list[dict[str, Any]] = [
        {
            "text": _build_prompt(
                document=document,
                target_language=target_language,
                has_images=has_images,
                prealign_csv=prealign_csv,
                preferences_data=preferences_data,
                is_group=is_group,
            )
        }
    ]
    # Attach page images after the text so the model reads the instructions
    # first. inlineData carries base64 PNG bytes (the preprocessor emits PNG).
    parts.extend(
        {
            "inlineData": {
                "mimeType": "image/png",
                "data": base64.b64encode(image).decode("ascii"),
            }
        }
        for image in image_list
    )
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _parsed_menu_schema(),
            # Disable model "thinking" — this is a structured extraction with a
            # response schema, not a reasoning task. Thinking multiplies latency
            # on flash/flash-lite for no accuracy gain here. Keeps scans fast.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }


_VARIANT_RULES = (
    "- Some menus print a GROUP HEADER (e.g. a sauce or a base dish) with a "
    "shared description and/or surcharge, then a NUMBERED list of protein or "
    "size variants below it (e.g. header 'Chop Suey' followed by '50. chicken "
    "8.00', '51. beef 9.00'). In that case the real dish is 'HEADER + variant': "
    "put the header in base_name and variant_group, the protein/size in "
    "variant_name, a readable full name in original_name, and attach the "
    "shared description/surcharge to every variant.\n"
    "- The same base dish printed with several prices (e.g. 'regular / cup') is "
    "one item per price; use variant_name for the size and share base_name.\n"
)


_CSV_ANCHOR_INTRO = (
    "Pre-aligned candidate rows (CSV) — a deterministic geometry pass paired each "
    "dish with its price and any detected size variant. Treat this name↔price "
    "pairing as a STRONG PRIOR: keep each price with its dish unless the image or "
    "OCR text clearly contradicts it. Do not drop rows and do not invent prices "
    "that are not present here. Columns: sort_order,name,base_name,variant_name,"
    "variant_group,price,currency,price_text.\n"
)


def _build_csv_anchor(document: OcrDocument, *, prealign_csv: bool) -> str:
    if not prealign_csv:
        return ""
    rows = build_menu_table(document)
    if not rows:
        return ""
    return f"{_CSV_ANCHOR_INTRO}{rows_to_csv(rows)}\n"


def _build_prompt(
    *,
    document: OcrDocument,
    target_language: str,
    has_images: bool = False,
    prealign_csv: bool = True,
    preferences_data: list[dict[str, Any]] | None = None,
    is_group: bool = False,
) -> str:
    detected = document.detected_language or "unknown"
    csv_anchor = _build_csv_anchor(document, prealign_csv=prealign_csv)

    preferences_prompt = ""
    if preferences_data:
        if is_group:
            preferences_prompt = (
                "You are acting as a Group AI Dining Assistant. Below are the dietary preferences and restrictions "
                "of all the diners in this group session. You MUST evaluate each menu item against their combined preferences:\n"
            )
        else:
            preferences_prompt = (
                "You are acting as a Personal AI Dining Assistant. Below are the user's personal dietary preferences "
                "and restrictions. You MUST evaluate each menu item against their personal preferences:\n"
            )
        for diner in preferences_data:
            d_name = diner.get("display_name") or "Diner"
            preferences_prompt += f"- Diner '{d_name}':\n"
            prefs = diner.get("preferences") or []
            if not prefs:
                preferences_prompt += "  No specific preferences/allergies.\n"
            for p in prefs:
                code = p.get("code")
                p_type = p.get("preference_type")
                preferences_prompt += f"  * type={p_type}, code={code}\n"
        preferences_prompt += "\n"

    common_rules = (
        "- Preserve unusual dish names verbatim in original_name.\n"
        "- Do not invent items that are not present in the menu.\n"
        "- Set price to null when the price is missing or confidence is low.\n"
        "- When price is known, use a decimal string such as 60000.00.\n"
        "- Use ISO currency codes such as VND or USD when currency is clear.\n"
        + _VARIANT_RULES
        + f"- ALWAYS fill translated_name in the target language "
        f"({target_language}) for every item; never leave it empty. Determine "
        "each dish's actual language from its own text — do NOT rely on the "
        "detected-source hint below, which is often wrong. If the name is "
        f"already in {target_language}, copy it verbatim.\n"
        "- translated_description is for a foreign diner who has NEVER seen this "
        "dish and does not know the cuisine, so it MUST let them picture it. "
        f"Write it in {target_language}, covering three things IN THIS ORDER: "
        "(1) the main INGREDIENTS; (2) how it is cooked, in simple words (grilled, "
        "stir-fried, steamed, simmered, deep-fried, fresh/raw, …); (3) what it "
        "tastes and feels like (savory, sweet, sour, spicy, rich, crunchy, chewy, "
        "…). Keep it to ONE or two short sentences (about 15-30 words): short but "
        "complete. If the menu printed its own description, use it as a base but "
        "ENRICH it to cover all three — never just echo the bare dish name. Naming "
        "ingredients is required (it also powers allergy matching). This describes "
        "an existing dish; it is NOT inventing a new item. Leave "
        "original_description empty when the menu printed none (never fabricate "
        "source-language text).\n"
        f"- category: a short label in the target language ({target_language}); "
        f"if the menu prints it bilingually, keep only the {target_language} "
        "side.\n"
        "- allergens: from THIS fixed set only, list every one the dish likely "
        "contains — seafood, shellfish, fish, peanut, tree_nut, egg, dairy, "
        "gluten, soy, sesame. Use [] if none or unknown.\n"
        "- dietary_tags: from THIS fixed set only, list every one that applies — "
        "contains_pork, contains_beef, contains_seafood, contains_alcohol, "
        "vegetarian, vegan. Use [] if none apply.\n"
        + (
            (
                "- Since this is a GROUP dining session, you MUST evaluate each dish for the group and for each diner individually:\n"
                "  - For each diner (in participant_breakdowns):\n"
                "    - display_name: Must match the diner's exact display_name.\n"
                "    - verdict: RECOMMENDED, OK, CAUTION, or AVOID.\n"
                "    - score: A number from 0 to 100.\n"
                "    - explanation: A short sentence in the target language explaining the evaluation (e.g. 'Dị ứng với đậu phộng' or 'Thích thịt bò').\n"
                "    - fit_reasons: Array of matching like tags.\n"
                "    - risk_reasons: Array of allergen, dietary constraint, avoid, or dislike matches.\n"
                "  - For the group (in recommendation):\n"
                "    - verdict: RECOMMENDED, OK, CAUTION, or AVOID. If ANY diner has a verdict of AVOID, the group verdict MUST be AVOID to ensure group safety.\n"
                "    - score: The average score of all diners.\n"
                "    - explanation: Summary of suitability for the group (e.g. who can eat it, who cannot).\n"
                "    - why_suitable: Join of all fit_reasons.\n"
                "    - why_not_suitable: Join of all risk_reasons.\n"
                "    - suggested_for: List of diner display_names who have verdict RECOMMENDED.\n"
                "    - warning_for: List of diner display_names who have verdict AVOID.\n"
                "    - fit_reasons: List of unique positive matching tags.\n"
                "    - risk_reasons: List of unique risk matching tags.\n"
                "    - warning_reasons: List of unique warning tags.\n"
                if is_group else
                "- Since this is a PERSONAL dining assistant, you MUST evaluate each dish for the user based on their default Food Profile:\n"
                "  - In recommendation:\n"
                "    - verdict: RECOMMENDED, OK, CAUTION, or AVOID.\n"
                "    - score: A score from 0 to 100 based on their preferences.\n"
                "    - explanation: A short sentence in the target language explaining why this dish fits or does not fit them (e.g., 'Phù hợp với chế độ ăn chay của bạn' or 'Có chứa hải sản mà bạn bị dị ứng').\n"
                "    - why_suitable: Join of fit reasons.\n"
                "    - why_not_suitable: Join of risk reasons.\n"
                "    - suggested_for: Leave empty (not applicable for personal scan).\n"
                "    - warning_for: Leave empty (not applicable for personal scan).\n"
                "    - fit_reasons: Unique positive matching tags.\n"
                "    - risk_reasons: Unique risk matching tags.\n"
                "    - warning_reasons: Unique warning tags.\n"
                "  - In participant_breakdowns: Leave this array empty (not applicable for personal scan).\n"
            )
            if preferences_data else
            "- Do not populate recommendation or participant_breakdowns fields (leave them null or empty) as no dietary preferences are provided.\n"
        )
        + "- Do not output any values in the root level warnings array (leave it empty).\n"
        + "- Omit other optional fields when unknown.\n"
    )

    if has_images:
        # The image is present, so let the model see the real 2-D layout. The
        # OCR text becomes a character/price anchor rather than the structure
        # source, and we drop the (potentially misleading on skewed photos)
        # coordinate dump.
        return (
            "You convert a restaurant menu into structured JSON.\n\n"
            "You are given the menu IMAGE(S) plus an OCR transcription. Rules:\n"
            "- The IMAGE is authoritative for layout: reading order, columns, "
            "which price belongs to which dish, and how items are grouped. "
            "Trust the image over the transcription for structure.\n"
            "- The OCR TRANSCRIPTION is authoritative for exact spelling and "
            "price digits. Trust it for characters (especially Vietnamese "
            "diacritics) and numbers; fix obvious OCR misreads using the image.\n"
            "- Ignore watermarks, background art, logos and photos of dishes.\n"
            + common_rules
            + "\n"
            f"Detected source language (UNRELIABLE hint, may be wrong): {detected}\n"
            f"Target language: {target_language}\n"
            f"{preferences_prompt}"
            f"{csv_anchor}"
            "OCR transcription:\n"
            f"{document.text}"
        )

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
        + common_rules
        + "\n"
        f"Detected source language (UNRELIABLE hint, may be wrong): {detected}\n"
        f"Target language: {target_language}\n"
        f"{preferences_prompt}"
        f"{csv_anchor}"
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
    breakdown_schema = {
        "type": "OBJECT",
        "properties": {
            "display_name": {"type": "STRING"},
            "verdict": {"type": "STRING"},
            "score": {"type": "NUMBER"},
            "explanation": {"type": "STRING"},
            "fit_reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "risk_reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["display_name", "verdict"],
    }
    recommendation_schema = {
        "type": "OBJECT",
        "properties": {
            "verdict": {"type": "STRING"},
            "score": {"type": "NUMBER"},
            "explanation": {"type": "STRING"},
            "why_suitable": {"type": "STRING"},
            "why_not_suitable": {"type": "STRING"},
            "suggested_for": {"type": "ARRAY", "items": {"type": "STRING"}},
            "warning_for": {"type": "ARRAY", "items": {"type": "STRING"}},
            "fit_reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "risk_reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "warning_reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["verdict"],
    }
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
            "allergens": {"type": "ARRAY", "items": {"type": "STRING"}},
            "dietary_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "confidence": {"type": "NUMBER"},
            "sort_order": {"type": "INTEGER"},
            "recommendation": recommendation_schema,
            "participant_breakdowns": {"type": "ARRAY", "items": breakdown_schema},
        },
        "required": [
            "original_name",
            "translated_name",
            "translated_description",
            "allergens",
            "dietary_tags",
            "sort_order",
        ],
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
                "items": {
                    "type": "STRING",
                    "enum": [
                        "UNSUPPORTED_INPUT",
                        "INPUT_TOO_LARGE",
                        "INVALID_DOCUMENT",
                        "PROVIDER_UNAVAILABLE",
                        "PROVIDER_TIMEOUT",
                        "PROVIDER_RATE_LIMITED",
                        "LOW_CONFIDENCE",
                        "NO_TEXT_FOUND",
                        "UNSAFE_PROVIDER_METADATA",
                    ],
                },
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
