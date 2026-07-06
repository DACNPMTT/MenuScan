"""Parse-accuracy benchmark: text-only vs B2 hybrid (image + OCR text).

For every ground-truth sample that has item-level truth (``items`` non-empty),
run the real OCR service + GeminiMenuParser twice — once text-only, once with
the page image(s) attached — and score item-name recall and price accuracy
against the ground truth. Prints a per-flow summary so the parsing improvement
from ADR 0003 can be measured instead of eyeballed.

This makes live Google Vision + Gemini calls (costs quota, rate-limited). Run
manually, not in CI:

    python doc/ocr-benchmark/measure_parse_accuracy.py
    python doc/ocr-benchmark/measure_parse_accuracy.py ocr-019 ocr-020  # subset
"""

from __future__ import annotations

import json
import os
import sys
import time
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "app"))

import dotenv

dotenv.load_dotenv(REPO_ROOT / "env" / ".env.local")

from src.modules.menu_scan.llm_menu_parser import GeminiMenuParser
from src.modules.menu_scan.ocr.adapters.google_vision import GoogleVisionOcrProvider
from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.ocr.service import OcrService, OcrSource

DATASET = REPO_ROOT / "doc" / "ocr-benchmark" / "dataset"


def _fold(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(folded.lower().split())


def _name_hit(expected: str, parsed_names: list[str]) -> bool:
    exp = _fold(expected)
    return any(exp in _fold(name) or _fold(name) in exp for name in parsed_names if name)


def _score(expected_items: list[dict], parsed) -> tuple[int, int, int]:
    """Return (name_hits, price_hits, total) for one draft against truth."""
    parsed_names = [it.original_name for it in parsed.items]
    price_by_fold = {
        _fold(it.original_name): it.price for it in parsed.items if it.price
    }
    name_hits = price_hits = 0
    for exp in expected_items:
        if _name_hit(exp["name"], parsed_names):
            name_hits += 1
        exp_price = str(exp.get("price") or "")
        if exp_price and any(
            _fold(exp["name"]) in folded and price == exp_price
            for folded, price in price_by_fold.items()
        ):
            price_hits += 1
    return name_hits, price_hits, len(expected_items)


def _build(model: str) -> tuple[OcrService, GeminiMenuParser, DocumentPreprocessor]:
    vision_key = os.environ["GOOGLE_VISION_API_KEY"]
    provider = GoogleVisionOcrProvider(
        api_key=vision_key,
        api_base_url=os.getenv(
            "GOOGLE_VISION_API_BASE_URL", "https://vision.googleapis.com/v1"
        ),
        timeout_seconds=30.0,
        feature_type=os.getenv("GOOGLE_VISION_MODEL", "DOCUMENT_TEXT_DETECTION"),
    )
    prep = DocumentPreprocessor(max_image_dimension=2048, contrast_factor=1.1)
    service = OcrService(preprocessor=prep, provider=provider)
    parser = GeminiMenuParser(
        api_key=os.environ.get("GEMINI_API_KEY") or os.environ["LLM_API_KEY"],
        api_base_url=os.getenv(
            "LLM_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ),
        model=model,
        timeout_seconds=90.0,
    )
    return service, parser, prep


def main() -> int:
    only = set(sys.argv[1:])
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    image_dim = int(os.getenv("LLM_IMAGE_MAX_DIMENSION", "1536"))

    gt = json.loads((DATASET / "ground_truth.json").read_text(encoding="utf-8-sig"))
    samples = [s for s in gt["samples"] if s["items"] and (not only or s["id"] in only)]

    service, parser, _ = _build(model)
    llm_prep = DocumentPreprocessor(max_image_dimension=image_dim, contrast_factor=1.0)

    totals = {"text": [0, 0, 0], "b2": [0, 0, 0]}
    print(f"Model={model}  image_dim={image_dim}  samples={len(samples)}\n")
    print(f"{'sample':<34} {'text name/price':>16} {'b2 name/price':>16}")

    for s in samples:
        source = OcrSource(
            object_key=s["file"],
            data=(DATASET / s["file"]).read_bytes(),
            mime_type=s.get("mime_type", "image/png"),
        )
        doc = service.process(source)
        images = [p.image_bytes for p in llm_prep.prepare(
            data=source.data, mime_type=source.mime_type
        ).pages]

        row = {}
        for flow, imgs in (("text", None), ("b2", images)):
            try:
                draft = parser.parse(doc, target_language="en", images=imgs)
                n, p, t = _score(s["items"], draft)
            except Exception as e:  # noqa: BLE001
                print(f"  {s['id']} {flow} FAILED: {e}")
                n, p, t = 0, 0, len(s["items"])
            row[flow] = (n, p, t)
            for i in range(3):
                totals[flow][i] += (n, p, t)[i]
            time.sleep(8)  # be gentle on free-tier RPM

        tn, tp, tt = row["text"]
        bn, bp, bt = row["b2"]
        print(f"{s['id']:<34} {f'{tn}/{tp} of {tt}':>16} {f'{bn}/{bp} of {bt}':>16}")

    print("\n=== TOTALS ===")
    for flow in ("text", "b2"):
        n, p, t = totals[flow]
        print(
            f"{flow:<5} name-recall={n}/{t} ({n / t:.0%})  "
            f"price-accuracy={p}/{t} ({p / t:.0%})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
