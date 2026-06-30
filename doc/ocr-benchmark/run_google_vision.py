from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from time import monotonic

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "app"))

from src.modules.menu_scan.ocr.adapters.google_vision import GoogleVisionOcrProvider
from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.ocr.service import OcrService, OcrSource

def main():
    import dotenv
    dotenv.load_dotenv(REPO_ROOT / "env" / ".env.local")
    
    api_key = os.getenv("GOOGLE_VISION_API_KEY")
    if not api_key:
        print("Missing GOOGLE_VISION_API_KEY in .env.local")
        return 1

    provider = GoogleVisionOcrProvider(
        api_key=api_key,
        api_base_url="https://vision.googleapis.com/v1",
        timeout_seconds=30.0,
    )
    preprocessor = DocumentPreprocessor(max_image_dimension=2048, contrast_factor=1.0)
    service = OcrService(preprocessor=preprocessor, provider=provider)

    dataset_dir = REPO_ROOT / "doc" / "ocr-benchmark" / "dataset"
    gt_path = dataset_dir / "ground_truth.json"
    gt_data = json.loads(gt_path.read_text(encoding="utf-8-sig"))
    
    output_path = REPO_ROOT / "doc" / "ocr-benchmark" / "results" / "provider-output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    print(f"Running Google Vision OCR on {len(gt_data['samples'])} samples...")
    
    for sample in gt_data["samples"]:
        sample_id = sample["id"]
        img_path = dataset_dir / sample["file"]
        mime_type = sample.get("mime_type", "image/png")
        
        print(f"Processing {sample_id}...", end="", flush=True)
        
        img_bytes = img_path.read_bytes()
        source = OcrSource(
            object_key=sample["file"],
            data=img_bytes,
            mime_type=mime_type
        )
        
        t0 = monotonic()
        try:
            doc = service.process(source)
            t1 = monotonic()
            
            lines = []
            for page in doc.pages:
                for block in page.blocks:
                    for line in block.lines:
                        if line.text.strip():
                            lines.append(line.text.strip())
                            
            # Determine column count by checking max column_index (Google Vision doesn't provide this yet, so it might be None)
            column_count = 1
            
            results.append({
                "sample_id": sample_id,
                "provider": "google_vision",
                "text": doc.text,
                "lines": lines,
                "prices": None, # let metric script extract
                "column_count": None,
                "processing_time_ms": doc.processing_time_ms
            })
            print(f" OK ({(t1-t0)*1000:.0f}ms)")
        except Exception as e:
            print(f" FAILED: {e}")
            
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. Wrote {len(results)} results to {output_path}")

if __name__ == "__main__":
    sys.exit(main())
