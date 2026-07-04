from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from src.modules.menu_scan.layout_classifier import LineRole, classify_line_role
from src.modules.menu_scan.line_item_extractor import split_name_description_price
from src.modules.menu_scan.ocr_contract import (
    OcrDocument,
    OcrErrorCode,
    OcrSourceReference,
    ParsedMenuDraft,
    ParsedMenuItemDraft,
)
from src.modules.menu_scan.price_normalizer import find_price_at_end, parse_price

_GENERIC_SECTIONS = {
    "appetizers",
    "beverages",
    "breakfast",
    "desserts",
    "drinks",
    "food",
    "main",
    "mains",
    "menu",
    "mon an",
    "mon chinh",
    "nuoc",
    "nuoc uong",
    "specials",
}
_PRICELESS_DISH_KEYWORDS = {
    "banh",
    "bun",
    "ca phe",
    "cha",
    "che",
    "com",
    "cuon",
    "goi",
    "mi",
    "nem",
    "pho",
}
_PRICELESS_ITEM_BLACKLIST = {
    "bun bo",
    "do ngon",
    "do them",
    "dongon",
    "delivery",
    "menu",
    "nhan don khach doan",
    "pho bien",
    "popular",
    "sot",
    "tour theo yeu cau",
}
_PRICELESS_ITEM_CONTAINS_BLACKLIST = {
    "co ba",
    "nha hang",
    "quan",
}


class MenuParser(Protocol):
    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
    ) -> ParsedMenuDraft:
        """Convert provider-neutral OCR output into a parsed menu draft."""
        ...


@dataclass(frozen=True, slots=True)
class RuleBasedMenuParser:
    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
    ) -> ParsedMenuDraft:
        return parse_menu(document, target_language=target_language)


def parse_menu(
    document: OcrDocument, *, target_language: str = "en"
) -> ParsedMenuDraft:
    title = _detect_title(document)
    default_currency = _infer_default_currency(document)
    warnings = _collect_warnings(document)

    current_section: str | None = None
    current_base_name: str | None = None
    items: list[ParsedMenuItemDraft] = []

    for page in document.pages:
        for block in sorted(page.blocks, key=_block_sort_key):
            for line in sorted(block.lines, key=_line_sort_key):
                role = classify_line_role(line.text, block, page)
                if role in {LineRole.NOISE, LineRole.UNKNOWN}:
                    continue
                if role == LineRole.TITLE:
                    if _looks_like_price_less_menu_item(line.text):
                        items.append(
                            _draft_item_from_line(
                                line_text=line.text,
                                price_text=None,
                                price=None,
                                currency=None,
                                category=current_section,
                                confidence=_merge_confidence(
                                    block.confidence, line.confidence
                                ),
                                page_index=page.page_index,
                                block_id=block.id,
                                line_id=line.id,
                                bounding_box=line.bounding_box,
                                sort_order=len(items),
                            )
                        )
                    continue

                if role == LineRole.SECTION_HEADER:
                    if _looks_like_price_less_menu_item(line.text):
                        items.append(
                            _draft_item_from_line(
                                line_text=line.text,
                                price_text=None,
                                price=None,
                                currency=None,
                                category=current_section,
                                confidence=_merge_confidence(
                                    block.confidence, line.confidence
                                ),
                                page_index=page.page_index,
                                block_id=block.id,
                                line_id=line.id,
                                bounding_box=line.bounding_box,
                                sort_order=len(items),
                            )
                        )
                        current_base_name = None
                        continue

                    section = _normalize_header(line.text)
                    current_section = section
                    current_base_name = (
                        section if _looks_like_variant_base(section) else None
                    )
                    continue

                if role == LineRole.PRICE_ONLY:
                    continue

                split = split_name_description_price(line.text)
                if not split.name or not split.price_text:
                    continue

                price_result = parse_price(split.price_text)
                if price_result is None:
                    continue

                price, currency = price_result
                original_name = split.name
                base_name: str | None = None
                variant_name: str | None = None

                if current_base_name and _looks_like_variant_name(
                    split.name, current_base_name
                ):
                    variant_name = _lower_first(split.name)
                    base_name = current_base_name
                    original_name = f"{base_name} {variant_name}"

                items.append(
                    _draft_item_from_line(
                        line_text=original_name,
                        description=split.description,
                        price_text=split.price_text,
                        price=price,
                        currency=currency,
                        category=current_section,
                        confidence=_merge_confidence(block.confidence, line.confidence),
                        page_index=page.page_index,
                        block_id=block.id,
                        line_id=line.id,
                        bounding_box=line.bounding_box,
                        sort_order=len(items),
                        base_name=base_name,
                        variant_name=variant_name,
                    )
                )

    return ParsedMenuDraft(
        parsing_provider="rule-based-python",
        title=title,
        source_language=document.detected_language,
        target_language=target_language,
        default_currency=default_currency,
        confidence=document.confidence,
        items=items,
        warnings=warnings,
    )


def _detect_title(document: OcrDocument) -> str | None:
    if not document.pages:
        return None
    page = document.pages[0]
    if not page.blocks:
        return None
    block = sorted(page.blocks, key=_block_sort_key)[0]
    for line in sorted(block.lines, key=_line_sort_key):
        if classify_line_role(line.text, block, page) == LineRole.TITLE:
            return line.text.strip()
    return None


def _infer_default_currency(document: OcrDocument) -> str | None:
    currencies: list[str | None] = []
    for page in document.pages:
        for block in page.blocks:
            for line in block.lines:
                if price_match := find_price_at_end(line.text):
                    price_result = parse_price(price_match[0])
                    if price_result is not None:
                        currencies.append(price_result[1])

    if not currencies:
        return None
    known = [currency for currency in currencies if currency is not None]
    if not known:
        return None
    currency, count = Counter(known).most_common(1)[0]
    if count / len(currencies) >= 0.7:
        return currency
    return None


def _collect_warnings(document: OcrDocument) -> list[OcrErrorCode]:
    for page in document.pages:
        for block in page.blocks:
            if block.confidence is not None and block.confidence < 0.6:
                return [OcrErrorCode.LOW_CONFIDENCE]
    return []


def _block_sort_key(block: object) -> tuple[float, float]:
    bounding_box = block.bounding_box  # type: ignore[attr-defined]
    return (bounding_box.top, bounding_box.left)


def _line_sort_key(line: object) -> tuple[float, float]:
    bounding_box = line.bounding_box  # type: ignore[attr-defined]
    return (bounding_box.top, bounding_box.left)


def _normalize_header(text: str) -> str:
    words = text.strip().split()
    if not words:
        return ""
    return " ".join([_capitalize_word(words[0]), *[word.lower() for word in words[1:]]])


def _capitalize_word(word: str) -> str:
    if not word:
        return word
    return word[:1].upper() + word[1:].lower()


def _looks_like_variant_base(section: str) -> bool:
    normalized = _ascii_fold(section).lower()
    if normalized in _GENERIC_SECTIONS:
        return False
    words = normalized.split()
    return 1 <= len(words) <= 3 and any(word in {"bun", "pho"} for word in words)


def _looks_like_variant_name(name: str, base_name: str) -> bool:
    normalized_name = _ascii_fold(name).lower()
    normalized_base = _ascii_fold(base_name).lower()
    if normalized_name.startswith(normalized_base):
        return False
    return len(normalized_name.split()) <= 4


def _looks_like_price_less_menu_item(text: str) -> bool:
    normalized = _ascii_fold(text)
    words = normalized.split()
    if not words or len(words) > 4:
        return False
    if any(character.isdigit() for character in normalized):
        return False
    if normalized in _GENERIC_SECTIONS or normalized in _PRICELESS_ITEM_BLACKLIST:
        return False
    if any(label in normalized for label in _PRICELESS_ITEM_CONTAINS_BLACKLIST):
        return False
    return any(keyword in normalized for keyword in _PRICELESS_DISH_KEYWORDS)


def _draft_item_from_line(
    *,
    line_text: str,
    price_text: str | None,
    price: str | None,
    currency: str | None,
    category: str | None,
    confidence: float | None,
    page_index: int,
    block_id: str | None,
    line_id: str | None,
    bounding_box: object,
    sort_order: int,
    description: str | None = None,
    base_name: str | None = None,
    variant_name: str | None = None,
) -> ParsedMenuItemDraft:
    return ParsedMenuItemDraft(
        original_name=line_text.strip(),
        original_description=description,
        base_name=base_name,
        variant_name=variant_name,
        variant_group=None,
        price_text=price_text,
        price=price,
        currency=currency,
        category=category,
        confidence=confidence,
        source_references=[
            OcrSourceReference(
                page_index=page_index,
                block_id=block_id,
                line_id=line_id,
                bounding_box=bounding_box,  # type: ignore[arg-type]
            )
        ],
        sort_order=sort_order,
    )


def _lower_first(text: str) -> str:
    if not text:
        return text
    return text[:1].lower() + text[1:]


def _ascii_fold(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    folded = unicodedata.normalize("NFKD", text)
    folded = folded.encode("ascii", "ignore").decode("ascii")
    if folded:
        return " ".join(folded.lower().split())

    replacements = {
        "à": "a",
        "á": "a",
        "ạ": "a",
        "ả": "a",
        "ã": "a",
        "â": "a",
        "ầ": "a",
        "ấ": "a",
        "ậ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ă": "a",
        "ằ": "a",
        "ắ": "a",
        "ặ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "è": "e",
        "é": "e",
        "ẹ": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ê": "e",
        "ề": "e",
        "ế": "e",
        "ệ": "e",
        "ể": "e",
        "ễ": "e",
        "ì": "i",
        "í": "i",
        "ị": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ò": "o",
        "ó": "o",
        "ọ": "o",
        "ỏ": "o",
        "õ": "o",
        "ô": "o",
        "ồ": "o",
        "ố": "o",
        "ộ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ơ": "o",
        "ờ": "o",
        "ớ": "o",
        "ợ": "o",
        "ở": "o",
        "ỡ": "o",
        "ù": "u",
        "ú": "u",
        "ụ": "u",
        "ủ": "u",
        "ũ": "u",
        "ư": "u",
        "ừ": "u",
        "ứ": "u",
        "ự": "u",
        "ử": "u",
        "ữ": "u",
        "ỳ": "y",
        "ý": "y",
        "ỵ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "đ": "d",
    }
    return " ".join(
        "".join(
        replacements.get(character.lower(), character.lower()) for character in text
        ).split()
    )


def _merge_confidence(*values: float | None) -> float | None:
    known = [value for value in values if value is not None]
    if not known:
        return None
    return sum(known) / len(known)
