"""Second-pass food intelligence for an already-extracted menu.

Extraction (llm_menu_parser) and enrichment are two different jobs. Extraction
must not miss a dish or mispair a price; enrichment invents nothing that matters
if it is missing — a dish without flavour tags is still a dish.

They used to share one Gemini call, which made the model write ~13 extra fields
per item while it was supposed to be reading prices off a photo. That cost
accuracy on the part we cannot get wrong, and on long menus it pushed the
response past the output ceiling, so the JSON came back cut and the whole scan
failed. Splitting them means a bad enrichment costs tags, not the menu.

Items are enriched in batches so one oversized menu cannot blow the ceiling
again, and a failed batch degrades to "no tags for those items" instead of
taking the scan down.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from src.modules.menu_scan.llm_menu_parser import (
    LlmMenuParserError,
    call_gemini,
)
from src.modules.menu_scan.ocr_contract import ParsedMenuDraft, ParsedMenuItemDraft

logger = logging.getLogger(__name__)

# The six 0-5 taste axes the model scores per dish.
_LEVEL_FIELDS = (
    "spice_level",
    "sweetness_level",
    "saltiness_level",
    "sourness_level",
    "richness_level",
    "oiliness_level",
)

_LIST_FIELDS = (
    "main_ingredients",
    "ingredient_tags",
    "flavor_tags",
    "texture_tags",
    "cooking_methods",
)


class FoodEnricher(Protocol):
    def enrich(
        self,
        draft: ParsedMenuDraft,
        *,
        target_language: str,
    ) -> ParsedMenuDraft:
        """Return the draft with food-intelligence fields filled in."""
        ...


class NullFoodEnricher:
    """No-op enricher for the rule-based / no-API-key path."""

    def enrich(
        self,
        draft: ParsedMenuDraft,
        *,
        target_language: str,
    ) -> ParsedMenuDraft:
        return draft


@dataclass(frozen=True, slots=True)
class GeminiFoodEnricher:
    api_key: str
    api_base_url: str
    model: str
    timeout_seconds: float
    client: httpx.Client | None = None
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.5
    api_keys: tuple[str, ...] = ()
    # Dishes per Gemini call. Bounds the output size of any single request so a
    # 120-item menu cannot truncate, and caps the blast radius of one bad batch.
    batch_size: int = 25

    def enrich(
        self,
        draft: ParsedMenuDraft,
        *,
        target_language: str,
    ) -> ParsedMenuDraft:
        if not draft.items:
            return draft

        enriched_by_index: dict[int, dict[str, Any]] = {}
        batches = list(_batched(range(len(draft.items)), self.batch_size))

        for batch in batches:
            try:
                enriched_by_index.update(
                    self._enrich_batch(draft.items, batch, target_language)
                )
            except Exception:
                # One failed batch loses tags for those dishes only. The dishes
                # themselves are already extracted and will still be saved.
                logger.warning(
                    "food_enrich_batch_failed model=%s items=%d — keeping dishes untagged",
                    self.model,
                    len(batch),
                    exc_info=True,
                )

        if not enriched_by_index:
            return draft

        items = [
            item.model_copy(update=enriched_by_index[index])
            if index in enriched_by_index
            else item
            for index, item in enumerate(draft.items)
        ]
        logger.info(
            "food_enrich_complete model=%s enriched=%d total=%d",
            self.model,
            len(enriched_by_index),
            len(items),
        )
        return draft.model_copy(update={"items": items})

    def _effective_keys(self) -> list[str]:
        if self.api_keys:
            keys = [key for key in self.api_keys if key]
            if keys:
                return keys
        return [self.api_key] if self.api_key else []

    def _enrich_batch(
        self,
        items: Sequence[ParsedMenuItemDraft],
        batch: Sequence[int],
        target_language: str,
    ) -> dict[int, dict[str, Any]]:
        body = call_gemini(
            keys=self._effective_keys(),
            api_base_url=self.api_base_url,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
            request_body=_build_request(
                dishes=[(index, items[index]) for index in batch],
                target_language=target_language,
            ),
            client=self.client,
            max_attempts=self.max_attempts,
            retry_backoff_seconds=self.retry_backoff_seconds,
        )
        payload = _extract_payload(body)
        valid_indices = set(batch)
        result: dict[int, dict[str, Any]] = {}

        for entry in payload.get("items") or []:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or index not in valid_indices:
                continue
            update = _clean_entry(entry)
            if update:
                result[index] = update

        return result


def _batched(values: Sequence[int] | range, size: int) -> list[list[int]]:
    step = max(1, size)
    sequence = list(values)
    return [sequence[start : start + step] for start in range(0, len(sequence), step)]


def _clean_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Keep only well-formed fields; a junk value must not overwrite a good one."""
    update: dict[str, Any] = {}

    summary = entry.get("assistant_summary")
    if isinstance(summary, str) and summary.strip():
        update["assistant_summary"] = summary.strip()

    notes = entry.get("risk_notes")
    if isinstance(notes, str) and notes.strip():
        update["risk_notes"] = notes.strip()

    for field in _LIST_FIELDS:
        raw = entry.get(field)
        if not isinstance(raw, list):
            continue
        cleaned = [
            value.strip()
            for value in raw
            if isinstance(value, str) and value.strip()
        ]
        if cleaned:
            update[field] = cleaned

    for field in _LEVEL_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if 0 <= raw <= 5:
            update[field] = raw

    return update


def _build_request(
    *,
    dishes: Sequence[tuple[int, ParsedMenuItemDraft]],
    target_language: str,
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _build_prompt(dishes=dishes, target_language=target_language)}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _enrichment_schema(),
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }


def _build_prompt(
    *,
    dishes: Sequence[tuple[int, ParsedMenuItemDraft]],
    target_language: str,
) -> str:
    lines = []
    for index, item in dishes:
        name = item.translated_name or item.original_name
        description = item.translated_description or item.original_description or ""
        category = item.category or ""
        lines.append(
            json.dumps(
                {
                    "index": index,
                    "name": name,
                    "description": description,
                    "category": category,
                },
                ensure_ascii=False,
            )
        )
    dish_block = "\n".join(lines)

    return (
        "You are a food analyst. For each dish below, infer its food profile "
        "from its name and description. The dishes were already extracted from a "
        "menu — do NOT add, drop, merge or rename any dish, and do not correct "
        "prices. Return exactly one entry per input dish, echoing its index.\n"
        "\n"
        f"Write all human-readable text in the target language ({target_language}).\n"
        "\n"
        "- assistant_summary: ONE short practical sentence helping a diner decide "
        "whether to order this. Do not just repeat the description.\n"
        "- main_ingredients: 2-8 human-readable ingredients. Infer from the name "
        "and description only; use [] when nothing can reasonably be inferred.\n"
        "- ingredient_tags: lowercase ASCII tags for ingredients or protein "
        "families, e.g. beef, pork, chicken, shrimp, tofu, rice, noodle, herbs, "
        "vegetable, egg, dairy, peanut, soy.\n"
        "- flavor_tags: e.g. savory, sweet, sour, spicy, rich, umami.\n"
        "- texture_tags: e.g. crunchy, tender, chewy, creamy, crispy, fresh.\n"
        "- cooking_methods: e.g. grilled, steamed, fried, deep_fried, stir_fried, "
        "simmered, raw, baked, boiled.\n"
        "- The six level fields are integers 0-5: 0 clearly absent, 1-2 mild, "
        "3 medium, 4-5 strong. Score every dish on all six.\n"
        "- risk_notes: ONLY real cautions — visible allergens, meat/seafood/alcohol "
        "conflicts, raw or undercooked items, or genuine ingredient uncertainty. "
        "Omit it when no risk is visible. Never write reassuring notes here.\n"
        "\n"
        "Dishes (one JSON object per line):\n"
        f"{dish_block}"
    )


def _enrichment_schema() -> dict[str, Any]:
    item_schema = {
        "type": "OBJECT",
        "properties": {
            "index": {"type": "INTEGER"},
            "assistant_summary": {"type": "STRING"},
            "main_ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
            "ingredient_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "flavor_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "texture_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "cooking_methods": {"type": "ARRAY", "items": {"type": "STRING"}},
            "spice_level": {"type": "INTEGER"},
            "sweetness_level": {"type": "INTEGER"},
            "saltiness_level": {"type": "INTEGER"},
            "sourness_level": {"type": "INTEGER"},
            "richness_level": {"type": "INTEGER"},
            "oiliness_level": {"type": "INTEGER"},
            "risk_notes": {"type": "STRING"},
        },
        "required": [
            "index",
            "assistant_summary",
            "main_ingredients",
            "ingredient_tags",
            "flavor_tags",
            "texture_tags",
            "cooking_methods",
            *_LEVEL_FIELDS,
        ],
    }
    return {
        "type": "OBJECT",
        "properties": {"items": {"type": "ARRAY", "items": item_schema}},
        "required": ["items"],
    }


def _extract_payload(body: dict[str, Any]) -> dict[str, Any]:
    candidates = body.get("candidates") or []
    if not candidates:
        raise LlmMenuParserError("gemini enricher returned no candidates")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise LlmMenuParserError("gemini enricher returned empty content")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise LlmMenuParserError("gemini enricher returned invalid content") from error
    if not isinstance(payload, dict):
        raise LlmMenuParserError("gemini enricher returned a non-object payload")
    return payload
