"""Enrichment is the second LLM pass, and it runs off the scan path.

The point of the split is blast radius: enrichment may fail, be truncated, or come
back junk, and the dishes must survive it untouched. These tests pin that.
"""

from __future__ import annotations

import json
from typing import Any

from src.modules.menu_scan.food_enricher import (
    DishInput,
    GeminiFoodEnricher,
    NullFoodEnricher,
)


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


def _dishes(count: int) -> list[DishInput]:
    return [
        DishInput(key=f"dish-{index}", name=f"Dish {index}") for index in range(count)
    ]


def _body(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"items": entries})}]}}
        ]
    }


def _enricher(
    client: FakeClient,
    *,
    batch_size: int = 20,
    max_workers: int = 1,
) -> GeminiFoodEnricher:
    return GeminiFoodEnricher(
        api_key="test-key",
        api_base_url="https://gemini.example.test/v1beta",
        model="gemini-2.5-flash",
        timeout_seconds=5,
        client=client,  # type: ignore[arg-type]
        batch_size=batch_size,
        max_workers=max_workers,
        retry_backoff_seconds=0,
    )


def test_enricher_returns_food_intelligence_keyed_by_dish() -> None:
    client = FakeClient(
        [
            FakeResponse(
                200,
                _body(
                    [
                        {
                            "key": "dish-0",
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

    result = _enricher(client).enrich_dishes(_dishes(1), target_language="en")

    assert result["dish-0"]["assistant_summary"] == "A hearty beef noodle soup."
    assert result["dish-0"]["main_ingredients"] == ["beef", "rice noodle"]
    assert result["dish-0"]["richness_level"] == 4
    assert result["dish-0"]["risk_notes"] == "Contains beef."


def test_enricher_batches_long_menus() -> None:
    client = FakeClient([FakeResponse(200, _body([]))])

    _enricher(client, batch_size=2).enrich_dishes(_dishes(5), target_language="en")

    # 5 dishes at 2 per call: three calls, so no single request can grow unbounded
    # and truncate the way the old single-call schema did.
    assert len(client.calls) == 3


def test_failed_batch_only_loses_its_own_dishes() -> None:
    good = _body([{"key": "dish-0", "assistant_summary": "Tagged."}])
    # First batch succeeds, second returns a server error that survives retries.
    client = FakeClient([FakeResponse(200, good), FakeResponse(500)])

    result = _enricher(client, batch_size=1).enrich_dishes(
        _dishes(2), target_language="en"
    )

    assert result["dish-0"]["assistant_summary"] == "Tagged."
    assert "dish-1" not in result  # dead batch yields nothing — and raises nothing


def test_enricher_drops_junk_and_unknown_keys() -> None:
    client = FakeClient(
        [
            FakeResponse(
                200,
                _body(
                    [
                        {
                            "key": "dish-0",
                            "assistant_summary": "   ",
                            "flavor_tags": "savory",
                            "spice_level": 9,
                            "sweetness_level": 2,
                        },
                        {"key": "not-a-dish", "assistant_summary": "Not mine."},
                    ]
                ),
            )
        ]
    )

    result = _enricher(client).enrich_dishes(_dishes(1), target_language="en")

    update = result["dish-0"]
    assert "assistant_summary" not in update  # blank string rejected
    assert "flavor_tags" not in update  # wrong type rejected
    assert "spice_level" not in update  # outside the 0-5 range rejected
    assert update["sweetness_level"] == 2  # the one good value lands
    assert "not-a-dish" not in result  # a key we never sent cannot come back


def test_null_enricher_returns_nothing() -> None:
    assert NullFoodEnricher().enrich_dishes(_dishes(2), target_language="en") == {}
