"""Second-pass food intelligence for an already-extracted menu.

Extraction and enrichment are two different jobs. Extraction must not miss a dish
or mispair a price; enrichment invents nothing that matters if it is missing — a
dish without flavour tags is still a dish.

They used to share one Gemini call, which made the model write ~13 extra fields
per item while it was supposed to be reading prices off a photo. On a 99-dish
menu that pushed the response past the output ceiling and Gemini returned a
valid-but-truncated array: 3 dishes out of 99, no error raised.

Enrichment now runs on its own, off the scan path, when the diner opens the menu.
Dishes are enriched in parallel batches so a long menu stays fast, and a failed
batch degrades to "no tags for those dishes" instead of taking anything down.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from src.modules.menu_scan.llm_menu_parser import LlmMenuParserError, call_gemini

logger = logging.getLogger(__name__)

# The six 0-5 taste axes the model scores per dish.
LEVEL_FIELDS = (
    "spice_level",
    "sweetness_level",
    "saltiness_level",
    "sourness_level",
    "richness_level",
    "oiliness_level",
)

LIST_FIELDS = (
    "main_ingredients",
    "ingredient_tags",
    "flavor_tags",
    "texture_tags",
    "cooking_methods",
)

TEXT_FIELDS = ("assistant_summary", "risk_notes")


@dataclass(frozen=True, slots=True)
class DishInput:
    """One dish to analyse. ``key`` is echoed back so the caller can match rows."""

    key: str
    name: str
    description: str = ""
    category: str = ""


class FoodEnricher(Protocol):
    def enrich_dishes(
        self,
        dishes: Sequence[DishInput],
        *,
        target_language: str,
    ) -> dict[str, dict[str, Any]]:
        """Map each dish key to the food-intelligence fields inferred for it."""
        ...


class NullFoodEnricher:
    """No-op enricher for the rule-based / no-API-key path."""

    def enrich_dishes(
        self,
        dishes: Sequence[DishInput],
        *,
        target_language: str,
    ) -> dict[str, dict[str, Any]]:
        return {}


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
    # The model failover chain, primary first — the same one the parser uses. Each
    # model has its own quota, so a 429 on one is not a 429 on the next. Running a
    # single model (and, worse, pinning it to the *fallback* one) meant a spent
    # quota killed enrichment outright: 49 dishes, 0 tagged, every single time.
    models: tuple[str, ...] = ()
    # Dishes per Gemini call. Bounds the output size of any single request so a
    # long menu cannot truncate, and caps the blast radius of one bad batch.
    batch_size: int = 20
    # Batches run concurrently, but gently. Free-tier keys are rate-limited per
    # minute, so firing every batch at once on a single key is a 429 we inflict on
    # ourselves — which is exactly what was happening.
    max_workers: int = 2

    def enrich_dishes(
        self,
        dishes: Sequence[DishInput],
        *,
        target_language: str,
    ) -> dict[str, dict[str, Any]]:
        if not dishes:
            return {}

        batches = _batched(list(dishes), self.batch_size)
        results: dict[str, dict[str, Any]] = {}

        workers = min(self.max_workers, len(batches))
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            for batch_result in pool.map(
                lambda batch: self._enrich_batch(batch, target_language),
                batches,
            ):
                results.update(batch_result)

        logger.info(
            "food_enrich_complete models=%s enriched=%d total=%d batches=%d",
            ",".join(self._model_chain()),
            len(results),
            len(dishes),
            len(batches),
        )
        return results

    def _effective_keys(self) -> list[str]:
        if self.api_keys:
            keys = [key for key in self.api_keys if key]
            if keys:
                return keys
        return [self.api_key] if self.api_key else []

    def _model_chain(self) -> list[str]:
        chain = [model for model in self.models if model]
        if chain:
            return chain
        return [self.model] if self.model else []

    def _enrich_batch(
        self,
        batch: Sequence[DishInput],
        target_language: str,
    ) -> dict[str, dict[str, Any]]:
        request_body = _build_request(dishes=batch, target_language=target_language)
        models = self._model_chain()
        payload: dict[str, Any] | None = None

        for index, model in enumerate(models):
            try:
                payload = _extract_payload(
                    call_gemini(
                        keys=self._effective_keys(),
                        api_base_url=self.api_base_url,
                        model=model,
                        timeout_seconds=self.timeout_seconds,
                        request_body=request_body,
                        client=self.client,
                        max_attempts=self.max_attempts,
                        retry_backoff_seconds=self.retry_backoff_seconds,
                    )
                )
                break
            except Exception:
                last = index == len(models) - 1
                logger.warning(
                    "food_enrich_batch_failed model=%s dishes=%d%s",
                    model,
                    len(batch),
                    "" if last else " — trying the next model",
                    exc_info=last,
                )

        if payload is None:
            # Every model refused. The dishes are already saved and stay on the
            # menu; they just have no tags.
            return {}

        valid_keys = {dish.key for dish in batch}
        result: dict[str, dict[str, Any]] = {}
        for entry in payload.get("items") or []:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key")
            if not isinstance(key, str) or key not in valid_keys:
                continue
            update = clean_entry(entry)
            if update:
                result[key] = update
        return result


def _batched(dishes: list[DishInput], size: int) -> list[list[DishInput]]:
    step = max(1, size)
    return [dishes[start : start + step] for start in range(0, len(dishes), step)]


def clean_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Keep only well-formed fields; a junk value must not overwrite a good one."""
    update: dict[str, Any] = {}

    for field in TEXT_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, str) and raw.strip():
            update[field] = raw.strip()

    for field in LIST_FIELDS:
        raw = entry.get(field)
        if not isinstance(raw, list):
            continue
        cleaned = [
            value.strip() for value in raw if isinstance(value, str) and value.strip()
        ]
        if cleaned:
            update[field] = cleaned

    for field in LEVEL_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if 0 <= raw <= 5:
            update[field] = raw

    return update


def _build_request(
    *,
    dishes: Sequence[DishInput],
    target_language: str,
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": _build_prompt(
                            dishes=dishes,
                            target_language=target_language,
                        )
                    }
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
    dishes: Sequence[DishInput],
    target_language: str,
) -> str:
    dish_block = "\n".join(
        json.dumps(
            {
                "key": dish.key,
                "name": dish.name,
                "description": dish.description,
                "category": dish.category,
            },
            ensure_ascii=False,
        )
        for dish in dishes
    )

    return (
        "You are a food analyst. For each dish below, infer its food profile from "
        "its name and description. The dishes were already extracted from a menu — "
        "do NOT add, drop, merge or rename any dish. Return exactly one entry per "
        "input dish, echoing its key verbatim.\n"
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
            "key": {"type": "STRING"},
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
            "key",
            "assistant_summary",
            "main_ingredients",
            "ingredient_tags",
            "flavor_tags",
            "texture_tags",
            "cooking_methods",
            *LEVEL_FIELDS,
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
