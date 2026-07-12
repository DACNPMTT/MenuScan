"""Extraction and enrichment are split into two LLM calls.

The point of the split is blast radius: enrichment may fail, be truncated, or
come back junk, and the dishes must survive it. These tests pin that contract.
"""

from __future__ import annotations

import json
from typing import Any

from src.modules.menu_scan.food_enricher import GeminiFoodEnricher, NullFoodEnricher
from src.modules.menu_scan.ocr_contract import ParsedMenuDraft, ParsedMenuItemDraft


class FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict[str, Any]:
        return self._body


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = responses

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        return self._responses[index]


def _draft(count: int) -> ParsedMenuDraft:
    return ParsedMenuDraft(
        target_language="en",
        items=[
            ParsedMenuItemDraft(
                original_name=f"Dish {index}",
                translated_name=f"Dish {index}",
                sort_order=index,
            )
            for index in range(count)
        ],
    )


def _enrichment_body(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"items": entries})}]}}
        ]
    }


def _enricher(client: FakeClient, *, batch_size: int = 25) -> GeminiFoodEnricher:
    return GeminiFoodEnricher(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
        batch_size=batch_size,
        retry_backoff_seconds=0,
    )


def test_enricher_fills_food_intelligence_fields() -> None:
    client = FakeClient(
        [
            FakeResponse(
                200,
                _enrichment_body(
                    [
                        {
                            "index": 0,
                            "assistant_summary": "A hearty beef noodle soup.",
                            "main_ingredients": ["beef", "rice noodle"],
                            "ingredient_tags": ["beef", "noodle"],
                            "flavor_tags": ["savory"],
                            "texture_tags": ["tender"],
                            "cooking_methods": ["simmered"],
                            "spice_level": 1,
                            "sweetness_level": 0,
                            "saltiness_level": 3,
                            "sourness_level": 0,
                            "richness_level": 4,
                            "oiliness_level": 2,
                            "risk_notes": "Contains beef.",
                        }
                    ]
                ),
            )
        ]
    )

    enriched = _enricher(client).enrich(_draft(1), target_language="en")

    item = enriched.items[0]
    assert item.assistant_summary == "A hearty beef noodle soup."
    assert item.main_ingredients == ["beef", "rice noodle"]
    assert item.cooking_methods == ["simmered"]
    assert item.richness_level == 4
    assert item.risk_notes == "Contains beef."
    # Extraction fields must survive untouched.
    assert item.original_name == "Dish 0"
    assert item.sort_order == 0


def test_enricher_batches_long_menus() -> None:
    body = _enrichment_body([])
    client = FakeClient([FakeResponse(200, body)])

    _enricher(client, batch_size=2).enrich(_draft(5), target_language="en")

    # 5 dishes at 2 per call: three calls, so no single request can grow
    # unbounded and truncate.
    assert len(client.calls) == 3


def test_failed_batch_keeps_its_dishes_untagged() -> None:
    good = _enrichment_body(
        [
            {
                "index": 0,
                "assistant_summary": "Tagged.",
                "flavor_tags": ["savory"],
            }
        ]
    )
    # First batch succeeds, second returns a server error that survives retries.
    client = FakeClient([FakeResponse(200, good), FakeResponse(500)])

    enriched = _enricher(client, batch_size=1).enrich(_draft(2), target_language="en")

    assert enriched.items[0].assistant_summary == "Tagged."
    # The dish from the dead batch is still here — just without tags.
    assert enriched.items[1].original_name == "Dish 1"
    assert enriched.items[1].assistant_summary is None
    assert enriched.items[1].flavor_tags == []


def test_enricher_ignores_junk_and_out_of_range_values() -> None:
    client = FakeClient(
        [
            FakeResponse(
                200,
                _enrichment_body(
                    [
                        {
                            "index": 0,
                            "assistant_summary": "   ",
                            "flavor_tags": "savory",
                            "spice_level": 9,
                            "sweetness_level": 2,
                        },
                        {"index": 99, "assistant_summary": "Not my dish."},
                    ]
                ),
            )
        ]
    )

    enriched = _enricher(client).enrich(_draft(1), target_language="en")

    item = enriched.items[0]
    assert item.assistant_summary is None  # blank string rejected
    assert item.flavor_tags == []  # wrong type rejected
    assert item.spice_level is None  # out of the 0-5 range rejected
    assert item.sweetness_level == 2  # the one good value lands
    assert len(enriched.items) == 1  # unknown index cannot add a dish


def test_null_enricher_returns_the_draft_unchanged() -> None:
    draft = _draft(2)
    assert NullFoodEnricher().enrich(draft, target_language="en") is draft
