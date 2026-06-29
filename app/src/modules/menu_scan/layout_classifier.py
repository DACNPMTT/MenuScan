from __future__ import annotations

import re
from enum import StrEnum

from src.modules.menu_scan.ocr_contract import OcrBlock, OcrPage
from src.modules.menu_scan.price_normalizer import find_price_at_end, parse_price


class LineRole(StrEnum):
    TITLE = "TITLE"
    SECTION_HEADER = "SECTION_HEADER"
    MENU_ITEM = "MENU_ITEM"
    PRICE_ONLY = "PRICE_ONLY"
    NOISE = "NOISE"
    UNKNOWN = "UNKNOWN"


_URL_RE = re.compile(r"(https?://|www\.|\S+\.(?:com|vn|net|org)\b)", re.IGNORECASE)
_FOOTER_RE = re.compile(
    r"\b(page|trang|hotline|wifi|wi-fi|thank you|thanks|cam on|cảm ơn)\b",
    re.IGNORECASE,
)


def classify_line_role(line_text: str, block: OcrBlock, page: OcrPage) -> LineRole:
    text = " ".join(line_text.split())
    if not text:
        return LineRole.UNKNOWN

    if _is_noise(text):
        return LineRole.NOISE

    if parse_price(text) is not None:
        return LineRole.PRICE_ONLY

    if find_price_at_end(text) is not None:
        return LineRole.MENU_ITEM

    if _is_title_candidate(text, block, page):
        return LineRole.TITLE

    if _is_section_header(text, block):
        return LineRole.SECTION_HEADER

    return LineRole.MENU_ITEM


def _is_noise(text: str) -> bool:
    return bool(re.fullmatch(r"\d+", text) or _URL_RE.search(text) or _FOOTER_RE.search(text))


def _is_title_candidate(text: str, block: OcrBlock, page: OcrPage) -> bool:
    if page.page_index != 0:
        return False
    if page.blocks and page.blocks[0].id != block.id:
        return False
    return block.bounding_box.top < 0.2 and len(text) < 60


def _is_section_header(text: str, block: OcrBlock) -> bool:
    if len(text) >= 40 or block.bounding_box.width >= 0.7:
        return False
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    if "".join(letters).isupper():
        return True
    words = [word for word in re.split(r"\s+", text) if any(char.isalpha() for char in word)]
    return bool(words) and all(_is_title_word(word) for word in words)


def _is_title_word(word: str) -> bool:
    letters = [character for character in word if character.isalpha()]
    return bool(letters) and letters[0].isupper()
