from __future__ import annotations

from src.modules.menu_scan.ocr_contract import (
    OcrDocument,
    ParsedMenuDraft,
    ParsedMenuItemDraft,
)
from src.modules.menu_scan.output_verifier import verify_draft


def _doc(text: str) -> OcrDocument:
    return OcrDocument(
        provider="fake",
        source_object_key="k",
        detected_language="vi",
        text=text,
        pages=[],
        processing_time_ms=1,
    )


def _item(
    name: str,
    *,
    price: str | None = None,
    price_text: str | None = None,
    sort_order: int = 0,
) -> ParsedMenuItemDraft:
    return ParsedMenuItemDraft(
        original_name=name, price=price, price_text=price_text, sort_order=sort_order
    )


def _draft(items: list[ParsedMenuItemDraft]) -> ParsedMenuDraft:
    return ParsedMenuDraft(target_language="en", items=items)


def test_keeps_items_grounded_in_ocr() -> None:
    doc = _doc("Phở bò 60.000đ\nBún bò Huế 55.000đ")
    draft = _draft(
        [
            _item("Phở bò", price="60000.00", sort_order=0),
            _item("Bún bò Huế", price="55000.00", sort_order=1),
        ]
    )

    result, dropped = verify_draft(draft, doc)

    assert dropped == 0
    assert [i.original_name for i in result.items] == ["Phở bò", "Bún bò Huế"]


def test_drops_hallucinated_item_and_reindexes() -> None:
    doc = _doc("Phở bò 60.000đ\nBún bò Huế 55.000đ")
    draft = _draft(
        [
            _item("Phở bò", price="60000.00", sort_order=0),
            _item("Spring rolls", price="99000.00", sort_order=1),
            _item("Bún bò Huế", price="55000.00", sort_order=2),
        ]
    )

    result, dropped = verify_draft(draft, doc)

    assert dropped == 1
    assert [i.original_name for i in result.items] == ["Phở bò", "Bún bò Huế"]
    assert [i.sort_order for i in result.items] == [0, 1]


def test_diacritic_correction_still_matches() -> None:
    # OCR misread the diacritics; the parser corrected them. Folding neutralises
    # the difference, so the corrected item is kept.
    doc = _doc("Ga nuong 50.000d")
    draft = _draft([_item("Gà nướng", price="50000.00")])

    _result, dropped = verify_draft(draft, doc)

    assert dropped == 0


def test_price_only_support_keeps_item() -> None:
    doc = _doc("60.000đ\n55.000đ")
    draft = _draft([_item("Unreadable name", price="60000.00", price_text="60.000đ")])

    _result, dropped = verify_draft(draft, doc)

    assert dropped == 0


def test_never_empties_a_draft() -> None:
    # Nothing is grounded, but total removal is distrusted — draft is unchanged.
    doc = _doc("completely unrelated paragraph of words")
    draft = _draft([_item("Phở bò", price="60000.00")])

    result, dropped = verify_draft(draft, doc)

    assert dropped == 0
    assert len(result.items) == 1


def test_empty_draft_is_noop() -> None:
    result, dropped = verify_draft(_draft([]), _doc("anything"))
    assert dropped == 0
    assert result.items == []
