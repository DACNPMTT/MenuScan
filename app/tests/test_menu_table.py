from __future__ import annotations

import csv
import io
import json

from src.modules.menu_scan.menu_table import (
    MenuTableRow,
    build_menu_table,
    rows_to_csv,
    rows_to_json,
)

from fixtures.menu_parser_fixtures import (
    make_multi_column_document,
    make_single_column_document,
)


def _by_name(rows: list[MenuTableRow]) -> dict[str, MenuTableRow]:
    return {row.name: row for row in rows}


def test_plain_single_column_pairs_name_and_price() -> None:
    document = make_single_column_document(
        [
            "Phở bò đặc biệt 60.000đ",
            "Bún bò Huế 55.000đ",
            "Cà phê sữa đá 25.000đ",
        ],
        title="Menu Quán Phở Sen",
    )

    rows = build_menu_table(document)

    assert [row.name for row in rows] == [
        "Phở bò đặc biệt",
        "Bún bò Huế",
        "Cà phê sữa đá",
    ]
    assert [row.price for row in rows] == ["60000.00", "55000.00", "25000.00"]
    # No base/variant composition on a plain menu.
    assert all(row.base_name is None and row.variant_name is None for row in rows)


def test_multi_column_pairs_both_columns() -> None:
    document = make_multi_column_document(
        ["Phở bò 60.000đ", "Bún bò 55.000đ"],
        ["Cà phê đá 20.000đ", "Trà đào 30.000đ"],
    )

    rows = build_menu_table(document)

    assert {row.name for row in rows} == {"Phở bò", "Bún bò", "Cà phê đá", "Trà đào"}
    assert all(row.price is not None for row in rows)


def test_base_header_composes_variants() -> None:
    document = make_single_column_document(
        [
            "PHỞ BÒ",
            "Tái 55.000đ",
            "Chín 55.000đ",
            "Tái nạm 62.000đ",
        ],
        title="Phở Bò Gia Truyền",
    )

    rows = build_menu_table(document)
    by_name = _by_name(rows)

    assert set(by_name) == {"Phở bò tái", "Phở bò chín", "Phở bò tái nạm"}
    tai = by_name["Phở bò tái"]
    assert tai.base_name == "Phở bò"
    assert tai.variant_name == "Tái"
    assert tai.price == "55000.00"
    # The title (Title-Cased) must NOT be treated as the base header.
    assert all(row.base_name == "Phở bò" for row in rows)


def test_size_variant_tagged_as_size() -> None:
    document = make_single_column_document(
        [
            "BÚN BÒ",
            "Tái 55.000đ",
            "Nạm 58.000đ",
            "Tô nhỏ 45.000đ",
            "Tô lớn 90.000đ",
        ],
    )

    by_name = _by_name(build_menu_table(document))

    assert by_name["Bún bò tái"].variant_group is None
    assert by_name["Bún bò tô nhỏ"].variant_group == "size"
    assert by_name["Bún bò tô lớn"].variant_group == "size"


def test_addon_lines_stay_standalone_under_base() -> None:
    document = make_single_column_document(
        [
            "PHỞ BÒ",
            "Tái 55.000đ",
            "Chín 55.000đ",
            "Thêm trứng chần 10.000đ",
        ],
    )

    by_name = _by_name(build_menu_table(document))

    assert "Thêm trứng chần" in by_name
    addon = by_name["Thêm trứng chần"]
    assert addon.base_name is None
    assert addon.variant_name is None
    assert addon.price == "10000.00"


def test_title_case_header_is_not_a_base() -> None:
    # A Title-Cased line above short priced items (dot-leader style menu) must not
    # be composed as a base dish — the items are standalone.
    document = make_single_column_document(
        [
            "Bánh mì thịt 28.000đ",
            "Mì Quảng 52.000đ",
            "Sữa đậu nành 15.000đ",
        ],
        title="Menu Dấu Chấm",
    )

    rows = build_menu_table(document)

    assert [row.name for row in rows] == ["Bánh mì thịt", "Mì Quảng", "Sữa đậu nành"]
    assert all(row.base_name is None for row in rows)


def test_no_price_document_yields_no_rows() -> None:
    document = make_single_column_document(
        ["Phở bò", "Bún bò", "Cà phê"],
        title="Quán không giá",
    )

    assert build_menu_table(document) == []


def test_price_on_its_own_line_pairs_with_name_above() -> None:
    # Name and price on separate stacked lines (OCR split them).
    document = make_single_column_document(
        ["Phở bò", "60.000đ", "Bún bò Huế", "55.000đ"],
    )

    rows = build_menu_table(document)
    by_name = _by_name(rows)

    assert set(by_name) == {"Phở bò", "Bún bò Huế"}
    assert by_name["Phở bò"].price == "60000.00"
    assert by_name["Bún bò Huế"].price == "55000.00"
    # The bare price lines must not survive as nameless rows.
    assert all(row.name not in {"60.000đ", "55.000đ"} for row in rows)


def test_right_hand_price_column_pairs_across_columns() -> None:
    # Names in the left column, prices in a separate right column, same rows.
    document = make_multi_column_document(
        ["Phở bò", "Bún bò Huế"],
        ["60.000đ", "55.000đ"],
    )

    rows = build_menu_table(document)
    by_name = _by_name(rows)

    assert set(by_name) == {"Phở bò", "Bún bò Huế"}
    assert by_name["Phở bò"].price == "60000.00"
    assert by_name["Bún bò Huế"].price == "55000.00"


def test_rows_to_json_round_trips() -> None:
    document = make_single_column_document(["Phở bò đặc biệt 60.000đ"])

    payload = json.loads(rows_to_json(build_menu_table(document)))

    assert payload[0]["name"] == "Phở bò đặc biệt"
    assert payload[0]["price"] == "60000.00"
    assert payload[0]["currency"] == "VND"


def test_rows_to_csv_has_header_and_quotes_values() -> None:
    document = make_single_column_document(["Phở bò đặc biệt 60.000đ"])

    text = rows_to_csv(build_menu_table(document))
    parsed = list(csv.reader(io.StringIO(text)))

    assert parsed[0] == [
        "sort_order",
        "name",
        "base_name",
        "variant_name",
        "variant_group",
        "price",
        "currency",
        "price_text",
    ]
    assert parsed[1][1] == "Phở bò đặc biệt"
    assert parsed[1][5] == "60000.00"
