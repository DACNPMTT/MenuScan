from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.modules.menu_scan.menu_parser import RuleBasedMenuParser
from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
)
from src.modules.menu_scan.ocr_metrics import measure_text_metrics

GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parents[2]
    / "doc"
    / "ocr-benchmark"
    / "dataset"
    / "ground_truth.json"
)

@pytest.fixture(scope="session")
def ground_truth_samples() -> list[dict]:
    with GROUND_TRUTH_PATH.open(encoding="utf-8") as f:
        return json.load(f)["samples"]


@pytest.fixture(scope="session")
def parser() -> RuleBasedMenuParser:
    return RuleBasedMenuParser()


def _mock_ocr_document(sample: dict) -> OcrDocument:
    """Build a perfect OcrDocument from expected_text for parser testing."""
    text = sample["expected_text"]
    return OcrDocument(
        provider="perfect-mock",
        source_object_key="mock",
        detected_language=sample["language"],
        text=text,
        confidence=1.0,
        processing_time_ms=0,
        pages=[
            OcrPage(
                page_index=0,
                width=1000,
                height=1000,
                text=text,
                confidence=1.0,
                blocks=[
                    OcrBlock(
                        id="b0",
                        text=text,
                        confidence=1.0,
                        bounding_box=OcrBoundingBox(left=0, top=0, width=1, height=1),
                        lines=[
                            OcrLine(
                                id=f"l{i}",
                                text=line,
                                confidence=1.0,
                                bounding_box=OcrBoundingBox(left=0, top=0, width=1, height=1)
                            )
                            for i, line in enumerate(text.splitlines())
                        ]
                    )
                ]
            )
        ]
    )


@pytest.fixture(scope="session")
def parser_results(ground_truth_samples, parser) -> dict[str, dict]:
    results = {}
    for sample in ground_truth_samples:
        doc = _mock_ocr_document(sample)
        draft = parser.parse(doc)
        
        parsed_prices = [item.price_text for item in draft.items if item.price_text]
        metrics = measure_text_metrics(
            expected_text=sample["expected_text"],
            actual_text=sample["expected_text"],  # Perfect OCR
            expected_prices=sample["expected_prices"],
            actual_prices=parsed_prices,
            expected_lines=sample["expected_lines"],
            actual_lines=sample["expected_lines"],  # Perfect OCR
            expected_column_count=sample.get("expected_column_count", 1),
            actual_column_count=sample.get("expected_column_count", 1),
            processing_time_ms=0,
        )
        
        # Calculate name accuracy
        expected_names = {item["name"].lower().strip() for item in sample["items"] if "name" in item}
        parsed_names = {item.original_name.lower().strip() for item in draft.items}
        
        name_accuracy = 1.0
        if expected_names:
            matched = len(expected_names & parsed_names)
            name_accuracy = matched / len(expected_names)
            
        results[sample["id"]] = {
            "metrics": metrics,
            "name_accuracy": name_accuracy,
            "draft": draft,
            "sample": sample
        }
    return results


class TestParserQualityBaseline:
    """Evaluate parser logic independently of OCR provider errors."""

    def test_aggregate_price_accuracy_above_threshold(self, parser_results):
        total_price_acc = sum(r["metrics"].price_accuracy for r in parser_results.values())
        avg_price_acc = total_price_acc / len(parser_results)
        # Parser alone should be very good on perfect text
        assert avg_price_acc >= 0.95

    def test_aggregate_name_accuracy_above_threshold(self, parser_results):
        total_name_acc = sum(r["name_accuracy"] for r in parser_results.values())
        avg_name_acc = total_name_acc / len(parser_results)
        assert avg_name_acc >= 0.85

    def test_single_column_samples_parsed(self, parser_results):
        sc_results = [r for r in parser_results.values() if "single_column" in r["sample"]["tags"]]
        assert len(sc_results) > 0
        avg_acc = sum(r["name_accuracy"] for r in sc_results) / len(sc_results)
        assert avg_acc >= 0.90

    def test_multi_column_samples_parsed(self, parser_results):
        mc_results = [r for r in parser_results.values() if "multi_column" in r["sample"]["tags"]]
        assert len(mc_results) > 0
        avg_acc = sum(r["name_accuracy"] for r in mc_results) / len(mc_results)
        # Current rule-based parser achieves ~79% on multi-column
        assert avg_acc >= 0.75

    @pytest.mark.xfail(reason="RuleBasedMenuParser does not yet extract variant names from variants")
    def test_variant_menu_extracts_base_and_variants(self, parser_results):
        var_results = [r for r in parser_results.values() if "variant_menu" in r["sample"]["tags"]]
        assert len(var_results) > 0
        for r in var_results:
            draft = r["draft"]
            has_variants = any(item.base_name and item.variant_name for item in draft.items)
            assert has_variants, f"Failed to extract variants for {r['sample']['id']}"
