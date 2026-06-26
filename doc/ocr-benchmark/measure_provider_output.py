"""Measure normalized OCR provider output against MenuScan ground truth.

Usage from repository root:

    python doc/ocr-benchmark/measure_provider_output.py \
      --ground-truth doc/ocr-benchmark/dataset/ground_truth.json \
      --provider-output path/to/provider-output.json

Provider output format:

[
  {
    "sample_id": "ocr-001-vi-single-column",
    "provider": "google_vision",
    "text": "...",
    "lines": ["..."],
    "prices": ["60.000d"],
    "column_count": 1,
    "processing_time_ms": 1234
  }
]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "app"))

from src.modules.menu_scan.ocr_metrics import measure_text_metrics  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--provider-output", required=True, type=Path)
    parser.add_argument("--csv-output", type=Path)
    args = parser.parse_args()

    ground_truth = _load_ground_truth(args.ground_truth)
    provider_outputs = json.loads(
        args.provider_output.read_text(encoding="utf-8-sig")
    )
    rows = []

    for output in provider_outputs:
        sample = ground_truth[output["sample_id"]]
        metrics = measure_text_metrics(
            expected_text=sample["expected_text"],
            actual_text=output["text"],
            expected_prices=sample["expected_prices"],
            actual_prices=output.get("prices"),
            expected_lines=sample["expected_lines"],
            actual_lines=output.get("lines"),
            expected_column_count=sample["expected_column_count"],
            actual_column_count=output.get("column_count"),
            processing_time_ms=output["processing_time_ms"],
        )
        rows.append(
            {
                "provider": output["provider"],
                "sample_id": output["sample_id"],
                "cer": metrics.character_error_rate,
                "wer": metrics.word_error_rate,
                "price_accuracy": metrics.price_accuracy,
                "line_recall": metrics.line_recall,
                "column_accuracy": metrics.column_accuracy,
                "processing_time_ms": metrics.processing_time_ms,
            }
        )

    if args.csv_output:
        _write_csv(args.csv_output, rows)
    else:
        print(json.dumps(rows, indent=2))
    return 0


def _load_ground_truth(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return {sample["id"]: sample for sample in payload["samples"]}


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
