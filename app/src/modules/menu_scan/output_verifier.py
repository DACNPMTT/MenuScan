"""Verify an LLM-parsed draft against the OCR text to drop hallucinated items.

The multimodal parser can invent dishes that never appeared on the menu. This
pass keeps an item only when its name or its price is actually grounded in the
OCR text, so obvious hallucinations are removed before persistence.

Two design constraints, both deliberate:

* **Diacritic-safe.** The parser is *supposed* to fix OCR misreads (``GÃ`` →
  ``GÀ``). Matching is done on ascii-folded text, so a corrected item still
  matches its OCR source and is never dropped for the correction.
* **Never empties a menu.** If every item would be dropped, the draft is returned
  unchanged. Total removal almost always means the check — not the parse — is
  wrong (e.g. an image-only layout), and nuking the whole menu is worse than
  keeping a few unverified rows.
"""

from __future__ import annotations

import re
import unicodedata

from src.modules.menu_scan.ocr_contract import (
    ParsedMenuDraft,
    ParsedMenuItemDraft,
    OcrDocument,
)

# Fraction of a dish name's words that must appear in the OCR text for the name
# to count as "grounded".
_NAME_SUPPORT_RATIO = 0.6
_DIGIT_RUN_RE = re.compile(r"\d[\d.,]*")


def verify_draft(
    draft: ParsedMenuDraft, document: OcrDocument
) -> tuple[ParsedMenuDraft, int]:
    """Return (filtered draft, dropped_count). Never empties a non-empty draft."""
    if not draft.items:
        return draft, 0

    text_fold = _fold(document.text)
    haystack_words = set(text_fold.split())
    digit_runs = _digit_set(document.text)

    kept: list[ParsedMenuItemDraft] = []
    for item in draft.items:
        if _is_supported(item, text_fold, haystack_words, digit_runs):
            kept.append(item)

    dropped = len(draft.items) - len(kept)
    if dropped == 0:
        return draft, 0
    if not kept:
        # Total removal → distrust the verifier, keep the parse as-is.
        return draft, 0

    reindexed = [
        item.model_copy(update={"sort_order": index}) for index, item in enumerate(kept)
    ]
    return draft.model_copy(update={"items": reindexed}), dropped


def _is_supported(
    item: ParsedMenuItemDraft,
    text_fold: str,
    haystack_words: set[str],
    digit_runs: set[str],
) -> bool:
    return _name_supported(item.original_name, haystack_words) or _price_supported(
        item, text_fold, digit_runs
    )


def _name_supported(name: str, haystack_words: set[str]) -> bool:
    words = _fold(name).split()
    if not words:
        return False
    hits = sum(1 for word in words if word in haystack_words)
    return hits / len(words) >= _NAME_SUPPORT_RATIO


def _price_supported(
    item: ParsedMenuItemDraft, text_fold: str, digit_runs: set[str]
) -> bool:
    if item.price_text and _fold(item.price_text) in text_fold:
        return True
    if item.price:
        integer_part = re.sub(r"\D", "", item.price.split(".")[0]).lstrip("0")
        if integer_part and integer_part in digit_runs:
            return True
    return False


def _digit_set(text: str) -> set[str]:
    runs: set[str] = set()
    for match in _DIGIT_RUN_RE.findall(text):
        digits = re.sub(r"\D", "", match)
        if digits:
            runs.add(digits.lstrip("0") or "0")
    return runs


def _fold(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().split())
