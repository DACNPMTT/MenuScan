from __future__ import annotations

import json
from pathlib import Path

from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
    ParsedMenuDraft,
    ParsedMenuItemDraft,
)
from src.modules.menu_scan.ocr_metrics import measure_text_metrics


GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[2]
    / "doc"
    / "ocr-benchmark"
    / "dataset"
    / "ground_truth.json"
)
VIETNAMESE_ACCENT_CHARS = set(
    "àáạảãâầấậẩẫăằắặẳẵ"
    "èéẹẻẽêềếệểễ"
    "ìíịỉĩ"
    "òóọỏõôồốộổỗơờớợởỡ"
    "ùúụủũưừứựửữ"
    "ỳýỵỷỹđ"
    "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ"
    "ÈÉẸẺẼÊỀẾỆỂỄ"
    "ÌÍỊỈĨ"
    "ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ"
    "ÙÚỤỦŨƯỪỨỰỬỮ"
    "ỲÝỴỶỸĐ"
)


def has_vietnamese_accent(text: str) -> bool:
    return any(character in VIETNAMESE_ACCENT_CHARS for character in text)


def test_ground_truth_dataset_has_required_coverage() -> None:
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

    assert payload["product_context"] == "foreign_visitor_in_vietnam"
    assert payload["primary_source_language"] == "vi"
    assert payload["sample_count"] == len(payload["samples"])
    assert len(payload["samples"]) >= 22
    assert {sample["language"] for sample in payload["samples"]} == {"vi"}
    assert all("-en-" not in sample["id"] for sample in payload["samples"])
    assert all(
        has_vietnamese_accent(sample["expected_text"]) for sample in payload["samples"]
    )
    assert (
        sum(1 for sample in payload["samples"] if len(sample["expected_prices"]) >= 20)
        >= 3
    )
    item_names = {
        item["name"]
        for sample in payload["samples"]
        for item in sample["items"]
        if "name" in item
    }
    assert {"Vũ nữ chân dài", "Sỏi mầm", "Cơm Âm Phủ"} <= item_names
    variant_samples = [
        sample for sample in payload["samples"] if "variant_menu" in sample["tags"]
    ]
    assert len(variant_samples) >= 2
    assert all(
        any(
            item.get("base_name") and item.get("variant_name")
            for item in sample["items"]
        )
        for sample in variant_samples
    )
    tags = {tag for sample in payload["samples"] for tag in sample["tags"]}
    assert {
        "single_column",
        "multi_column",
        "multi_page",
        "skewed",
        "low_quality",
        "price_formats",
        "bilingual_gloss",
        "accented_vietnamese",
        "long_menu",
        "variant_menu",
        "unusual_name",
        "figurative_name",
        "regional_specialty",
    } <= tags


def test_ocr_document_contract_accepts_provider_neutral_shape() -> None:
    document = OcrDocument(
        provider="fixture",
        provider_model="fixture-v1",
        source_object_key="users/user-id/scans/scan-id/source",
        detected_language="vi",
        text="Phở bò\n60.000đ",
        confidence=0.95,
        processing_time_ms=120,
        pages=[
            OcrPage(
                page_index=0,
                width=1200,
                height=800,
                text="Phở bò\n60.000đ",
                confidence=0.95,
                blocks=[
                    OcrBlock(
                        id="b1",
                        text="Phở bò 60.000đ",
                        confidence=0.95,
                        column_index=0,
                        bounding_box=OcrBoundingBox(
                            left=0.1,
                            top=0.1,
                            width=0.5,
                            height=0.2,
                        ),
                        lines=[
                            OcrLine(
                                id="l1",
                                text="Phở bò",
                                confidence=0.96,
                                bounding_box=OcrBoundingBox(
                                    left=0.1,
                                    top=0.1,
                                    width=0.3,
                                    height=0.05,
                                ),
                            )
                        ],
                    )
                ],
            )
        ],
        metadata={"page_count": 1},
    )

    assert document.schema_version == "ocr-document.v1"
    assert document.pages[0].blocks[0].lines[0].text == "Phở bò"


def test_parsed_menu_draft_keeps_source_references() -> None:
    draft = ParsedMenuDraft(
        title="Fixture Menu",
        source_language="vi",
        target_language="en",
        default_currency="VND",
        confidence=0.9,
        items=[
            ParsedMenuItemDraft(
                original_name="Phở bò",
                base_name="Phở",
                variant_name="bò",
                variant_group="loại thịt",
                price_text="60.000đ",
                price="60000.00",
                currency="VND",
                confidence=0.91,
                sort_order=1,
            )
        ],
    )

    assert draft.schema_version == "parsed-menu-draft.v1"
    assert draft.items[0].price == "60000.00"
    assert draft.items[0].base_name == "Phở"
    assert draft.items[0].variant_name == "bò"


def test_ocr_metrics_measure_text_price_layout_and_latency() -> None:
    metrics = measure_text_metrics(
        expected_text="Phở bò\n60.000đ",
        actual_text="Phở bò\n60.000đ",
        expected_prices=["60.000đ"],
        expected_lines=["Phở bò", "60.000đ"],
        actual_lines=["Phở bò", "60.000đ"],
        expected_column_count=1,
        actual_column_count=1,
        processing_time_ms=88,
    )

    assert metrics.character_error_rate == 0
    assert metrics.word_error_rate == 0
    assert metrics.price_accuracy == 1
    assert metrics.line_recall == 1
    assert metrics.column_accuracy == 1
    assert metrics.processing_time_ms == 88
