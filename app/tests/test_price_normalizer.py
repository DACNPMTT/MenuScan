"""Regression tests for the rule-based price parser.

Guards the grouped-thousands VND bug where prices of one million or more
(``1.250.000đ``) were either rejected outright or, worse, silently truncated
to their last three-digit group (``250.000đ``) by ``find_price_at_end``.
"""

from __future__ import annotations

import pytest

from src.modules.menu_scan.price_normalizer import find_price_at_end, parse_price


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Sub-million, single separator (already worked; kept as a guard).
        ("45.000đ", ("45000.00", "VND")),
        ("250.000đ", ("250000.00", "VND")),
        # Million-plus with grouped separators — the regression.
        ("1.250.000đ", ("1250000.00", "VND")),
        ("2.500.000đ", ("2500000.00", "VND")),
        ("1.000.000đ", ("1000000.00", "VND")),
        ("1.250.000 VND", ("1250000.00", "VND")),
        # Other currencies and compact forms remain intact.
        ("$12.50", ("12.50", "USD")),
        ("20 USD", ("20.00", "USD")),
        ("12.500k", ("12500.00", "VND")),
        ("12k", ("12000.00", "VND")),
        ("45000", ("45000.00", None)),
    ],
)
def test_parse_price_grouped_thousands(text: str, expected: tuple[str, str | None]) -> None:
    assert parse_price(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "45.50 VND",  # 2-digit trailing group is not a confident VND amount
        "not a price",
    ],
)
def test_parse_price_rejects_non_confident(text: str) -> None:
    assert parse_price(text) is None


def test_find_price_at_end_keeps_full_million_amount() -> None:
    """The trailing-price extractor must not truncate a million-plus VND price."""
    result = find_price_at_end("Lẩu hải sản đặc biệt 1.250.000đ")
    assert result is not None
    price_text, _start, _end = result
    assert price_text == "1.250.000đ"
    assert parse_price(price_text) == ("1250000.00", "VND")


def test_find_price_at_end_sub_million_unchanged() -> None:
    result = find_price_at_end("Phở bò 45.000đ")
    assert result is not None
    assert result[0] == "45.000đ"
