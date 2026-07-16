"""Deterministic OCR → menu table (name + price + size/variant) exporter.

A geometry-first pass that pairs each dish name with its price straight from the
OCR ``OcrDocument`` — no LLM. It also recognises the common Vietnamese
"base dish header + variant list" layout (e.g. a ``PHỞ BÒ`` header followed by
``Tái 55.000đ`` / ``Chín 55.000đ`` …) and composes ``base + variant`` rows,
tagging size variants (``Tô nhỏ`` / ``Tô lớn``) as ``variant_group="size"``.

Output serialises to JSON or CSV. The table is meant to be:
  * an accurate deterministic result on its own, and
  * a compact **anchor** handed to the LLM parser so name↔price pairing is
    grounded (see the OCR→CSV→LLM plan) instead of the verbose coordinate dump.

No hardcoded dish names: a base header is detected generically as an ALL-CAPS
line immediately followed by ≥2 short "name + price" variant lines (lookahead).

Reuses ``price_normalizer`` and ``line_item_extractor`` so behaviour matches the
rest of the pipeline.
"""

from __future__ import annotations

import csv
import io
import json
import unicodedata
from dataclasses import asdict, dataclass

from src.modules.menu_scan.line_item_extractor import split_name_description_price
from src.modules.menu_scan.ocr_contract import OcrDocument
from src.modules.menu_scan.price_normalizer import parse_price

# Size-denoting tokens (ascii-folded). A variant whose leading words hit one of
# these is tagged variant_group="size".
_SIZE_TOKENS = frozenset(
    {
        "to",
        "size",
        "nho",
        "vua",
        "lon",
        "phan",
        "suat",
        "dia",
        "ly",
        "chai",
        "small",
        "medium",
        "large",
        "reg",
        "regular",
        "s",
        "m",
        "l",
    }
)
# A line whose leading word is one of these is an add-on / topping ("Thêm ..."),
# kept as its own row rather than composed under the current base dish.
_ADDON_PREFIXES = frozenset({"them"})

_MAX_VARIANT_WORDS = 3
_MIN_VARIANTS_FOR_BASE = 2


@dataclass(frozen=True, slots=True)
class MenuTableRow:
    """One (dish, price) pair. A dish with N sizes yields N rows."""

    sort_order: int
    name: str
    base_name: str | None
    variant_name: str | None
    variant_group: str | None
    price: str | None
    currency: str | None
    price_text: str | None


@dataclass(frozen=True, slots=True)
class _Line:
    text: str
    top: float
    left: float
    height: float
    column: int
    priced: bool
    name_part: str | None
    price: str | None
    currency: str | None
    price_text: str | None


def build_menu_table(document: OcrDocument) -> list[MenuTableRow]:
    """Extract an ordered (name, price, size) table from an OCR document."""
    lines = _collect_lines(document)
    rows: list[MenuTableRow] = []
    order = 0
    index = 0
    total = len(lines)

    while index < total:
        line = lines[index]

        if line.priced:
            rows.append(
                MenuTableRow(
                    sort_order=order,
                    name=line.name_part or line.text.strip(),
                    base_name=None,
                    variant_name=None,
                    variant_group=None,
                    price=line.price,
                    currency=line.currency,
                    price_text=line.price_text,
                )
            )
            order += 1
            index += 1
            continue

        # A no-price line may be a base dish header. Look ahead over the run of
        # priced lines that follow it in the same column.
        run_end = index + 1
        while (
            run_end < total
            and lines[run_end].priced
            and lines[run_end].column == line.column
        ):
            run_end += 1
        run = lines[index + 1 : run_end]

        short_variants = [
            item
            for item in run
            if _word_count(item.name_part) <= _MAX_VARIANT_WORDS
            and not _is_addon(item.name_part)
        ]
        is_base = (
            len(run) >= _MIN_VARIANTS_FOR_BASE
            and len(short_variants) >= _MIN_VARIANTS_FOR_BASE
            and _is_all_caps(line.text)
        )

        if not is_base:
            # A plain header/title/category line — emit nothing, keep walking.
            index += 1
            continue

        base = _header_case(line.text)
        for item in run:
            if _is_addon(item.name_part):
                rows.append(
                    MenuTableRow(
                        sort_order=order,
                        name=item.name_part or item.text.strip(),
                        base_name=None,
                        variant_name=None,
                        variant_group=None,
                        price=item.price,
                        currency=item.currency,
                        price_text=item.price_text,
                    )
                )
            else:
                variant = (item.name_part or "").strip()
                rows.append(
                    MenuTableRow(
                        sort_order=order,
                        name=f"{base} {_lower_first(variant)}",
                        base_name=base,
                        variant_name=variant,
                        variant_group="size" if _is_size(variant) else None,
                        price=item.price,
                        currency=item.currency,
                        price_text=item.price_text,
                    )
                )
            order += 1
        index = run_end

    return rows


def rows_to_json(rows: list[MenuTableRow]) -> str:
    return json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2)


def rows_to_csv(rows: list[MenuTableRow]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "sort_order",
            "name",
            "base_name",
            "variant_name",
            "variant_group",
            "price",
            "currency",
            "price_text",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.sort_order,
                row.name,
                row.base_name or "",
                row.variant_name or "",
                row.variant_group or "",
                row.price or "",
                row.currency or "",
                row.price_text or "",
            ]
        )
    return buffer.getvalue()


# ── internals ───────────────────────────────────────────────────────


def _collect_lines(document: OcrDocument) -> list[_Line]:
    raw = [
        (block.column_index, line)
        for page in document.pages
        for block in page.blocks
        for line in block.lines
        if line.text.strip()
    ]

    columns_known = any(column is not None for column, _ in raw)
    split = None
    if not columns_known:
        centers = [
            line.bounding_box.left + line.bounding_box.width / 2 for _, line in raw
        ]
        split = _column_split(centers)

    lines: list[_Line] = []
    for column_index, line in raw:
        box = line.bounding_box
        center = box.left + box.width / 2
        column = column_index if column_index is not None else _column_of(center, split)

        split_result = split_name_description_price(line.text)
        price = currency = price_text = name_part = None
        priced = False
        if split_result.price_text:
            parsed = parse_price(split_result.price_text)
            if parsed is not None:
                price, currency = parsed
                price_text = split_result.price_text
                name_part = split_result.name
                priced = True

        lines.append(
            _Line(
                text=line.text,
                top=box.top,
                left=box.left,
                height=box.height,
                column=column,
                priced=priced,
                name_part=name_part,
                price=price,
                currency=currency,
                price_text=price_text,
            )
        )

    lines = _pair_detached_prices(lines)
    lines.sort(key=lambda item: (item.column, item.top, item.left))
    return lines


def _pair_detached_prices(lines: list[_Line]) -> list[_Line]:
    """Attach a name to each detached price token.

    Handles the two layouts ``split_name_description_price`` alone misses: a price
    printed on its **own line** below the dish name, and a price in a separate
    **right-hand column** at the same row. Each such price borrows the nearest
    name — same row band to its left (cross-column), else the closest name-like
    line directly above in its column (own-line) — and that name is consumed so
    it is not also emitted as a nameless row. No-op when every price is inline.
    """
    tolerance = _row_tolerance(lines)
    adjacent_gap = tolerance * 3.2
    consumed: set[int] = set()
    result = list(lines)

    for price_index, price in enumerate(lines):
        if not _is_price_only(price):
            continue
        name_index = _find_name_for_price(
            price, lines, consumed, tolerance, adjacent_gap
        )
        if name_index is None:
            continue
        consumed.add(name_index)
        result[price_index] = _paired_line(lines[name_index], price)

    return [line for index, line in enumerate(result) if index not in consumed]


def _find_name_for_price(
    price: _Line,
    lines: list[_Line],
    consumed: set[int],
    tolerance: float,
    adjacent_gap: float,
) -> int | None:
    price_center_y = _center_y(price)

    # 1) Same row band, to the left → a right-hand price column.
    best_index: int | None = None
    best_left = -1.0
    for index, candidate in enumerate(lines):
        if index in consumed or candidate.priced or not _is_name_like(candidate):
            continue
        if (
            candidate.left < price.left
            and abs(_center_y(candidate) - price_center_y) <= tolerance
            and candidate.left > best_left
        ):
            best_left = candidate.left
            best_index = index
    if best_index is not None:
        return best_index

    # 2) Nearest name-like line directly above in the same column → own-line price.
    best_gap = adjacent_gap
    for index, candidate in enumerate(lines):
        if index in consumed or candidate.priced or not _is_name_like(candidate):
            continue
        if candidate.column != price.column:
            continue
        gap = price.top - candidate.top
        if 0 < gap <= best_gap:
            best_gap = gap
            best_index = index
    return best_index


def _paired_line(name: _Line, price: _Line) -> _Line:
    return _Line(
        text=name.text,
        top=min(name.top, price.top),
        left=name.left,
        height=name.height,
        column=name.column,
        priced=True,
        name_part=name.text,
        price=price.price,
        currency=price.currency,
        price_text=price.price_text,
    )


def _is_price_only(line: _Line) -> bool:
    return line.priced and not (line.name_part or "").strip()


def _is_name_like(line: _Line) -> bool:
    text = line.text.strip()
    if not any(char.isalpha() for char in text):
        return False
    return 1 <= len(text.split()) <= 8


def _center_y(line: _Line) -> float:
    return line.top + line.height / 2


def _row_tolerance(lines: list[_Line]) -> float:
    heights = sorted(line.height for line in lines if line.height > 0)
    if not heights:
        return 0.02
    median = heights[len(heights) // 2]
    return max(median * 0.7, 0.012)


def _column_split(centers: list[float]) -> float | None:
    """Return an x split point when the line centers form two clear columns."""
    if len(centers) < 4:
        return None
    ordered = sorted(centers)
    best_gap = 0.0
    best_at: float | None = None
    for low, high in zip(ordered, ordered[1:]):
        if high - low > best_gap:
            best_gap = high - low
            best_at = (low + high) / 2
    if best_gap >= 0.18 and best_at is not None:
        left = [center for center in centers if center < best_at]
        right = [center for center in centers if center >= best_at]
        if len(left) >= 2 and len(right) >= 2:
            return best_at
    return None


def _column_of(center: float, split: float | None) -> int:
    if split is None:
        return 0
    return 0 if center < split else 1


def _fold(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().split())


def _word_count(text: str | None) -> int:
    return len(_fold(text or "").split())


def _is_size(variant: str) -> bool:
    return any(word in _SIZE_TOKENS for word in _fold(variant).split())


def _is_addon(name_part: str | None) -> bool:
    words = _fold(name_part or "").split()
    return bool(words) and words[0] in _ADDON_PREFIXES


def _is_all_caps(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and "".join(letters).isupper()


def _header_case(text: str) -> str:
    words = text.split()
    if not words:
        return text
    return " ".join([words[0].capitalize(), *[word.lower() for word in words[1:]]])


def _lower_first(text: str) -> str:
    if not text:
        return text
    return text[:1].lower() + text[1:]
