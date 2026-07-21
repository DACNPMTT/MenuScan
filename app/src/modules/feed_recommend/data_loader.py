"""Load the restaurant dataset from ``data/restaurants.json`` into a module-level
in-memory cache.

The file is the source of truth — no database table mirrors it. Update =
edit JSON + restart the process. The cache is a singleton built lazily on the
first read and never invalidated at runtime; tests use ``_reset_cache_for_tests``
to inject synthetic fixtures without touching disk.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Resolve ``<repo_root>/data/restaurants.json`` regardless of CWD.
_DATASET_PATH = Path(__file__).resolve().parents[4] / "data" / "restaurants.json"

@dataclass(frozen=True)
class RestaurantData:
    """One restaurant row, parsed defensively from the JSON file."""

    source_id: int
    name: str
    address: str
    lat: float
    lng: float
    avg_price: int | None = None
    star: float | None = None
    semantic_text: str | None = None
    image_url: str | None = None
    phone_num: str | None = None
    type: list[str] = field(default_factory=list)
    meals: list[dict[str, Any]] = field(default_factory=list)


_CACHE: list[RestaurantData] | None = None
_INDEX: dict[int, RestaurantData] | None = None


def load_restaurants() -> list[RestaurantData]:
    """Return the cached dataset, building it on first call.

    Missing file ⇒ empty cache + warning (lets the app boot before the dataset
    is dropped in). Malformed file ⇒ raises (loud deployment error). Per-row
    parse errors are logged and skipped.
    """
    global _CACHE, _INDEX
    if _CACHE is not None:
        return _CACHE
    parsed: list[RestaurantData] = []
    try:
        raw_text = _DATASET_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "Feed dataset missing at %s — feed will be empty until the file "
            "is added and the process is restarted.",
            _DATASET_PATH,
        )
        _CACHE = []
        _INDEX = {}
        return _CACHE

    raw = json.loads(raw_text)
    items = raw.get("root", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        logger.warning(
            "Feed dataset at %s is not a list (got %s) — feed will be empty.",
            _DATASET_PATH,
            type(raw).__name__,
        )
        _CACHE = []
        _INDEX = {}
        return _CACHE

    for index, item in enumerate(items):
        try:
            parsed.append(_parse_item(item))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Skipping invalid restaurant row #%d in %s: %s",
                index,
                _DATASET_PATH,
                exc,
            )

    _CACHE = parsed
    _INDEX = {r.source_id: r for r in parsed}
    return _CACHE


def get_restaurant_by_source_id(source_id: int) -> RestaurantData | None:
    """Return one restaurant by its ``source_id`` or ``None`` if not present."""
    if _INDEX is None:
        load_restaurants()
    assert _INDEX is not None
    return _INDEX.get(source_id)


def _reset_cache_for_tests(
    restaurants: list[RestaurantData] | None = None,
) -> None:
    """Test-only hook: inject a fixture list (or clear the singleton).

    Production code never calls this — the cache is built once from disk and
    reused. Tests inject synthetic rows so they don't depend on the JSON file.
    """
    global _CACHE, _INDEX
    _CACHE = restaurants
    _INDEX = {r.source_id: r for r in restaurants} if restaurants else {}


def _parse_item(item: Any) -> RestaurantData:
    """Coerce one raw JSON object into a ``RestaurantData``.

    Required: ``id``, ``name``, ``address``, ``lat``, ``lng``. The rest fall
    back to None / empty when absent or malformed. ``star`` is rounded to one
    decimal; out-of-range stars are clamped to ``[0, 5]``.
    """
    if not isinstance(item, dict):
        raise TypeError(f"expected object, got {type(item).__name__}")

    source_id = _require_int(item, "id")
    name = _require_str(item, "name")
    address = _require_str(item, "address")
    lat = _require_float(item, "lat")
    lng = _require_float(item, "lng")

    avg_price = _optional_int(item, "avg_price")
    star = _optional_float(item, "star")
    if star is not None:
        star = round(max(0.0, min(5.0, star)), 1)

    type_field = item.get("type")
    if isinstance(type_field, list):
        type_cleaned = [str(t).strip().lower() for t in type_field if str(t).strip()]
    else:
        type_cleaned = []

    meals_field = item.get("meals")
    meals = [m for m in meals_field if isinstance(m, dict)] if isinstance(meals_field, list) else []

    return RestaurantData(
        source_id=source_id,
        name=name,
        address=address,
        lat=lat,
        lng=lng,
        avg_price=avg_price,
        star=star,
        semantic_text=_optional_str(item, "semantic_text"),
        image_url=_optional_str(item, "image_url"),
        phone_num=_optional_str(item, "phone_num"),
        type=type_cleaned,
        meals=meals,
    )


def _require_int(item: dict[str, Any], key: str) -> int:
    value = item.get(key)
    if value is None:
        raise KeyError(key)
    return int(value)


def _require_float(item: dict[str, Any], key: str) -> float:
    value = item.get(key)
    if value is None:
        raise KeyError(key)
    return float(value)


def _require_str(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KeyError(key)
    return value.strip()


def _optional_int(item: dict[str, Any], key: str) -> int | None:
    value = item.get(key)
    return int(value) if isinstance(value, (int, float)) else None


def _optional_float(item: dict[str, Any], key: str) -> float | None:
    value = item.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _optional_str(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
