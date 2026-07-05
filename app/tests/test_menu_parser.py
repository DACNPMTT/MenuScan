from __future__ import annotations

import json
from pathlib import Path

from src.modules.menu_scan.menu_parser import parse_menu
from src.modules.menu_scan.ocr_contract import OcrDocument
from src.modules.menu_scan.price_normalizer import parse_price

from fixtures.menu_parser_fixtures import (
    make_multi_column_document,
    make_multi_page_document,
    make_single_column_document,
)

FIXTURE_SAMPLES_PATH = (
    Path(__file__).resolve().parents[2]
    / "doc"
    / "ocr-benchmark"
    / "fixture_samples.json"
)


def test_single_column_vi_items_extracted() -> None:
    document = make_single_column_document(
        [
            "Phở bò đặc biệt 60.000đ",
            "Bún bò Huế 55.000đ",
            "Cà phê sữa đá 25.000đ",
        ],
        title="Menu Quán Phở Sen",
    )

    draft = parse_menu(document)

    assert draft.title == "Menu Quán Phở Sen"
    assert [item.original_name for item in draft.items] == [
        "Phở bò đặc biệt",
        "Bún bò Huế",
        "Cà phê sữa đá",
    ]
    assert [item.price for item in draft.items] == ["60000.00", "55000.00", "25000.00"]
    assert draft.default_currency == "VND"


def test_multi_column_items_from_both_columns() -> None:
    document = make_multi_column_document(
        ["Phở bò 60.000đ", "Bún bò 55.000đ"],
        ["Cà phê đá 20.000đ", "Trà đào 30.000đ"],
    )

    draft = parse_menu(document)

    assert len(draft.items) == 4
    assert {item.source_references[0].block_id for item in draft.items}
    assert {item.original_name for item in draft.items} == {
        "Phở bò",
        "Bún bò",
        "Cà phê đá",
        "Trà đào",
    }


def test_multi_page_items_preserve_page_index() -> None:
    document = make_multi_page_document(
        [["Phở bò 60.000đ"], ["Bún bò 55.000đ", "Cà phê đá 20.000đ"]]
    )

    draft = parse_menu(document)

    assert [item.source_references[0].page_index for item in draft.items] == [0, 1, 1]


def test_price_vnd_dot_thousands() -> None:
    assert parse_price("60.000đ") == ("60000.00", "VND")


def test_price_vnd_comma_thousands() -> None:
    assert parse_price("45,000 VND") == ("45000.00", "VND")


def test_price_vnd_k_suffix() -> None:
    assert parse_price("45k") == ("45000.00", "VND")


def test_price_usd_dollar_prefix() -> None:
    assert parse_price("$12.50") == ("12.50", "USD")


def test_price_usd_decimal_comma() -> None:
    assert parse_price("4,5 USD") == ("4.50", "USD")


def test_price_bare_int_no_currency() -> None:
    assert parse_price("60000") == ("60000.00", None)


def test_dot_leader_stripped() -> None:
    document = make_single_column_document(["Bánh mì ........ 28.000đ"])

    draft = parse_menu(document)

    assert draft.items[0].original_name == "Bánh mì"
    assert "..." not in draft.items[0].original_name


def test_description_after_dash() -> None:
    document = make_single_column_document(
        ["Vũ nữ chân dài - khô nhái chiên mắm 95.000đ"]
    )

    draft = parse_menu(document)

    assert draft.items[0].original_name == "Vũ nữ chân dài"
    assert draft.items[0].original_description == "khô nhái chiên mắm"


def test_unusual_names_preserved() -> None:
    document = make_single_column_document(
        [
            "Vũ nữ chân dài - khô nhái chiên mắm 95.000đ",
            "Sỏi mầm - heo rừng nướng sỏi nóng 180.000đ",
            "Cơm Âm Phủ - cơm trộn Huế nhiều màu 75.000đ",
        ]
    )

    draft = parse_menu(document)

    assert [item.original_name for item in draft.items] == [
        "Vũ nữ chân dài",
        "Sỏi mầm",
        "Cơm Âm Phủ",
    ]


def test_variant_menu_base_name_set() -> None:
    sample = _fixture_sample("ocr-019-vi-bun-bo-variants")
    document = make_single_column_document(sample["lines"], title=sample["title"])

    draft = parse_menu(document)

    assert len(draft.items) == len(sample["items"])
    assert {item.base_name for item in draft.items} == {"Bún bò"}
    assert draft.items[0].original_name == "Bún bò tái"
    assert draft.items[0].variant_name == "tái"
    assert all(item.variant_group is None for item in draft.items)


def test_section_header_becomes_category() -> None:
    document = make_single_column_document(
        ["DRINKS", "Coca cola 20.000đ", "Trà đào 30.000đ"],
        title="Menu",
    )

    draft = parse_menu(document)

    assert [item.category for item in draft.items] == ["Drinks", "Drinks"]
    assert [item.base_name for item in draft.items] == [None, None]


def test_source_reference_has_block_and_page() -> None:
    document = make_single_column_document(["Phở bò 60.000đ"], title="Menu")

    draft = parse_menu(document)
    reference = draft.items[0].source_references[0]

    assert reference.page_index == 0
    assert reference.block_id is not None
    assert reference.line_id is not None


def test_no_items_from_noise_lines() -> None:
    document = make_single_column_document(
        ["1", "www.example.com", "Hotline 0900000000", "Phở bò 60.000đ"]
    )

    draft = parse_menu(document)

    assert [item.original_name for item in draft.items] == ["Phở bò"]


def test_empty_document_returns_empty_draft() -> None:
    document = OcrDocument(
        provider="fixture",
        source_object_key="empty",
        detected_language="vi",
        text="",
        pages=[],
        processing_time_ms=0,
    )

    draft = parse_menu(document)

    assert draft.items == []


def test_rule_based_parser_marks_translation_incomplete() -> None:
    """Rule-based parsing never translates — pipeline must still run translation."""
    document = make_single_column_document(["Phở bò 60.000đ"])

    draft = parse_menu(document)

    assert draft.translation_complete is False


def test_line_without_name_not_added() -> None:
    document = make_single_column_document(["60.000đ"])

    draft = parse_menu(document)

    assert draft.items == []


def test_price_less_vietnamese_dish_names_are_extracted() -> None:
    document = make_single_column_document(
        [
            "BÚN BÒ HUẾ",
            "PHỞ",
            "BÁNH MÌ",
            "GỎI CUỐN",
            "PHỔ BIẾN",
            "ĐỘ NGON",
        ]
    )

    draft = parse_menu(document)

    assert [item.original_name for item in draft.items] == [
        "BÚN BÒ HUẾ",
        "PHỞ",
        "BÁNH MÌ",
        "GỎI CUỐN",
    ]
    assert [item.price for item in draft.items] == [None, None, None, None]


def test_parse_failure_returns_empty_not_fake_items() -> None:
    document = make_single_column_document(["hello world", "not a menu item"])

    draft = parse_menu(document)

    assert draft.items == []


def test_default_currency_inferred_when_majority_vnd() -> None:
    document = make_single_column_document(
        ["Phở bò 60.000đ", "Bún bò 55.000đ", "Cơm gà 65.000đ", "Coffee $3.50"]
    )

    draft = parse_menu(document)

    assert draft.default_currency == "VND"


def test_name_accuracy_on_fixture_sample() -> None:
    sample = _fixture_sample("ocr-021-vi-unusual-dish-names")
    document = make_single_column_document(sample["lines"], title=sample["title"])

    draft = parse_menu(document)
    expected_names = {item["name"] for item in sample["items"]}
    actual_names = {item.original_name for item in draft.items}
    accuracy = len(expected_names & actual_names) / len(expected_names)
    print(f"ocr-021 name accuracy: {accuracy:.2%}")

    assert accuracy >= 0.8


def test_price_accuracy_on_fixture_sample() -> None:
    sample = _fixture_sample("ocr-021-vi-unusual-dish-names")
    document = make_single_column_document(sample["lines"], title=sample["title"])

    draft = parse_menu(document)
    expected_prices = {item["price"] for item in sample["items"]}
    actual_prices = {item.price for item in draft.items}
    accuracy = len(expected_prices & actual_prices) / len(expected_prices)
    print(f"ocr-021 price accuracy: {accuracy:.2%}")

    assert accuracy >= 0.95


def test_description_continuation_line_after_item() -> None:
    document = make_single_column_document(
        [
            "Grilled chicken 120.000 VND",
            "lemongrass, chili, fish sauce",
            "Beef noodle soup 80.000 VND",
        ]
    )

    draft = parse_menu(document)

    assert [item.original_name for item in draft.items] == [
        "Grilled chicken",
        "Beef noodle soup",
    ]
    assert draft.items[0].original_description == "lemongrass, chili, fish sauce"
    assert draft.items[1].original_description is None


def _fixture_sample(sample_id: str) -> dict[str, object]:
    payload = json.loads(FIXTURE_SAMPLES_PATH.read_text(encoding="utf-8"))
    for sample in payload["image_samples"]:
        if sample["id"] == sample_id:
            return sample
    raise AssertionError(f"missing fixture sample {sample_id}")
