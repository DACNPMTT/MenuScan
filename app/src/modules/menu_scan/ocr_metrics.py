"""Benchmark metrics for provider-neutral OCR output."""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

PRICE_PATTERN = re.compile(
    r"(?:(?:VND|USD|EUR)\s*)?\d[\d.,]*(?:\s*(?:đ|d|VND|USD|EUR))?",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class TextMetrics:
    character_error_rate: float
    word_error_rate: float
    price_accuracy: float
    line_recall: float
    column_accuracy: float
    processing_time_ms: int


def measure_text_metrics(
    *,
    expected_text: str,
    actual_text: str,
    expected_prices: list[str],
    actual_prices: list[str] | None = None,
    expected_lines: list[str] | None = None,
    actual_lines: list[str] | None = None,
    expected_column_count: int | None = None,
    actual_column_count: int | None = None,
    processing_time_ms: int,
) -> TextMetrics:
    normalized_expected_text = _normalize_text(expected_text)
    normalized_actual_text = _normalize_text(actual_text)
    expected_words = _words(normalized_expected_text)
    actual_words = _words(normalized_actual_text)
    prices = actual_prices or extract_prices(actual_text)

    return TextMetrics(
        character_error_rate=_ratio(
            _edit_distance(normalized_expected_text, normalized_actual_text),
            len(normalized_expected_text),
        ),
        word_error_rate=_ratio(
            _edit_distance(expected_words, actual_words),
            len(expected_words),
        ),
        price_accuracy=_set_recall(
            {_normalize_price(price) for price in expected_prices},
            {_normalize_price(price) for price in prices},
        ),
        line_recall=_line_recall(expected_lines or [], actual_lines or []),
        column_accuracy=(
            1.0
            if expected_column_count is None
            or expected_column_count == actual_column_count
            else 0.0
        ),
        processing_time_ms=processing_time_ms,
    )


def timed_call(callback: Callable[[], str]) -> tuple[str, int]:
    started_at = time.perf_counter()
    result = callback()
    elapsed_ms = round((time.perf_counter() - started_at) * 1000)
    return result, elapsed_ms


def extract_prices(text: str) -> list[str]:
    return [match.group(0) for match in PRICE_PATTERN.finditer(text)]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n")
    return "\n".join(line.strip() for line in normalized.strip().splitlines())


def _normalize_price(price: str) -> str:
    normalized = price.upper().replace(" ", "").replace("Đ", "VND")
    return normalized.replace(".", "").replace(",", "")


def _words(text: str) -> list[str]:
    return WORD_PATTERN.findall(text.lower())


def _ratio(distance: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0 if distance == 0 else 1.0
    return distance / denominator


def _set_recall(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 1.0
    return len(expected & actual) / len(expected)


def _line_recall(expected_lines: list[str], actual_lines: list[str]) -> float:
    if not expected_lines:
        return 1.0
    normalized_actual = {_normalize_text(line).lower() for line in actual_lines}
    matched = sum(
        1
        for line in expected_lines
        if _normalize_text(line).lower() in normalized_actual
    )
    return matched / len(expected_lines)


def _edit_distance(left: str | list[str], right: str | list[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            cost = 0 if left_item == right_item else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + cost,
                )
            )
        previous = current
    return previous[-1]
