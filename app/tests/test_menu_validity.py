from __future__ import annotations

from src.modules.menu_scan.menu_validity import looks_like_menu

from fixtures.menu_parser_fixtures import make_single_column_document


def _doc(text: str):
    return make_single_column_document(text.splitlines())


def test_menu_with_prices_passes() -> None:
    assert looks_like_menu(_doc("Phở bò 60.000đ\nBún bò Huế 55.000đ")) is True


def test_no_price_menu_still_passes_on_short_lines() -> None:
    # A valid menu with no printed prices — many short, list-like lines.
    assert looks_like_menu(_doc("Phở bò\nBún bò Huế\nCà phê\nTrà đá")) is True


def test_empty_text_is_rejected() -> None:
    assert looks_like_menu(_doc("")) is False


def test_prose_without_prices_is_rejected() -> None:
    prose = (
        "This is a long paragraph of ordinary prose that goes on and on about "
        "something entirely unrelated to food while never once naming a dish or "
        "quoting a price, the kind of text a photo of a book page would produce "
        "when run through optical character recognition on a phone."
    )
    assert looks_like_menu(_doc(prose)) is False


def test_short_ambiguous_text_gets_benefit_of_the_doubt() -> None:
    # Little text, no prices, not clearly prose — do not block.
    assert looks_like_menu(_doc("Fixture OCR text")) is True
