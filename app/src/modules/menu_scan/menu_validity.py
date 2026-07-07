"""Cheap pre-LLM check: does the OCR text plausibly come from a menu?

Runs on ``OcrDocument.text`` right after OCR and before the (expensive) LLM
parse, so an obviously-wrong photo (a random page of prose, a sign, a receipt of
paragraphs) fails fast with ``INVALID_DOCUMENT`` instead of burning an LLM call.

Deliberately **conservative**: it only rejects content that clearly is not a
menu. A valid menu with no printed prices still passes (many short, list-like
lines), so real menus are never blocked. This mirrors the "Text hợp lệ? là menu?"
node in the scan flow — the strict/semantic judgement is left to the parser.
"""

from __future__ import annotations

from src.modules.menu_scan.ocr_contract import OcrDocument
from src.modules.menu_scan.price_normalizer import find_price_at_end

# A line with at most this many words reads like a dish/price entry rather than a
# prose sentence.
_SHORT_LINE_MAX_WORDS = 6
# Menus are lists: this many short lines is enough to call it menu-like.
_MIN_SHORT_LINES = 3
# Below this much text we never reject — too little to be confidently "prose".
_PROSE_CHAR_THRESHOLD = 200


def looks_like_menu(document: OcrDocument) -> bool:
    """Return False only when the OCR text clearly is not a menu."""
    text = document.text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    # Any real price is a strong menu signal.
    if any(find_price_at_end(line) is not None for line in lines):
        return True

    # No prices: a menu is still a list of short entries.
    short_lines = sum(1 for line in lines if len(line.split()) <= _SHORT_LINE_MAX_WORDS)
    if short_lines >= _MIN_SHORT_LINES:
        return True

    # No prices and little list structure. A lot of text here means prose, not a
    # menu; a little text is ambiguous, so give it the benefit of the doubt.
    return len(text) < _PROSE_CHAR_THRESHOLD
