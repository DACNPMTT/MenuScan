from __future__ import annotations

import re
from dataclasses import dataclass

from src.modules.menu_scan.price_normalizer import find_price_at_end


@dataclass(frozen=True)
class NameDescriptionPrice:
    name: str | None
    description: str | None
    price_text: str | None


_DOT_LEADER_RE = re.compile(r"\s*\.{2,}\s*")
_DASH_RE = re.compile(r"\s+[–-]\s+")


def split_name_description_price(line_text: str) -> NameDescriptionPrice:
    text = _normalize_spaces(_DOT_LEADER_RE.sub(" ", line_text))
    price_text: str | None = None

    if price_match := find_price_at_end(text):
        price_text, start, _end = price_match
        text = _normalize_spaces(text[:start])

    name_text = text
    description: str | None = None
    dash_parts = _DASH_RE.split(text, maxsplit=1)
    if len(dash_parts) == 2:
        name_text = dash_parts[0]
        description = dash_parts[1] or None

    name = name_text.strip(" -–:;,.") or None
    if description is not None:
        description = description.strip(" -–:;,.") or None

    return NameDescriptionPrice(
        name=name, description=description, price_text=price_text
    )


def _normalize_spaces(text: str) -> str:
    return " ".join(text.strip().split())
