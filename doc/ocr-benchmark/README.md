# MenuScan OCR Benchmark

This directory defines the repeatable OCR research package for MenuScan. It is
intentionally provider-neutral: provider adapters must map their proprietary
responses into `OcrDocument` before parser work starts.

## Dataset

The benchmark dataset is synthetic and generated in-repo, so it contains no
private or copyrighted menu data.

- Ground truth: `dataset/ground_truth.json`
- Assets: `dataset/assets/`
- Generator: `generate_fixtures.ps1`
- Fixture source: `fixture_samples.json`
- Product context: foreign visitors reading menus while eating in Vietnam.
- OCR source priority: Vietnamese restaurant menus. English is not a primary
  source language; it only appears as a translation target or occasional
  bilingual gloss on tourist-area menus.
- Coverage: 22 Vietnamese-source samples with Vietnamese diacritics, including
  single-column menus, multi-column menus, multi-page PDFs, skewed photos,
  low-quality images, dense text, tourist-area price boards, bilingual glosses,
  multiple price formats, three realistic long menus with 20+ priced items, and
  variant menus where one base dish has many priced types such as `Bún bò tái`,
  `Bún bò nạm gân`, and `Bún bò đặc biệt`. The dataset also covers unusual,
  figurative, and regional dish names such as `Vũ nữ chân dài`, `Sỏi mầm`,
  `Cơm Âm Phủ`, and `Bò leo núi`.

Regenerate fixtures on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File doc\ocr-benchmark\generate_fixtures.ps1
```

## Metrics

Every provider must be evaluated on the same ground truth:

- Character Error Rate (CER)
- Word Error Rate (WER)
- price accuracy
- line recall
- column-count accuracy
- processing time in milliseconds

Implementation lives in `app/src/modules/menu_scan/ocr_metrics.py`.

Measure a normalized provider output file:

```powershell
python doc\ocr-benchmark\measure_provider_output.py `
  --ground-truth doc\ocr-benchmark\dataset\ground_truth.json `
  --provider-output path\to\provider-output.json `
  --csv-output doc\ocr-benchmark\results\google_vision.csv
```

## Minimum MVP Gates

The team should not integrate a provider into production scan orchestration
until a live benchmark run on Vietnamese-source menus meets these thresholds:

| Metric | Minimum gate |
| --- | --- |
| Vietnamese-source CER | `<= 0.08` |
| Vietnamese-source WER | `<= 0.18` |
| Price accuracy | `>= 0.95` |
| Line recall | `>= 0.90` |
| Column-count accuracy | `>= 0.85` |
| p95 processing time per page | `<= 5000 ms` |

Low-quality/skewed samples may fail the global CER/WER gate, but they must not
invent prices. Parser must set uncertain fields to `null`.

## Candidate Providers

| Provider | Status for MVP | Why |
| --- | --- | --- |
| Google Cloud Vision `DOCUMENT_TEXT_DETECTION` | Primary candidate | Supports Vietnamese OCR language hints, returns page/block/word geometry, supports image/PDF async flows, and has simple managed deployment. English support is useful only for bilingual glosses, not as the source-language reason. |
| Azure AI Vision Read | Secondary managed fallback | Supports mixed-language Read OCR and printed Vietnamese; useful if Azure deployment/container strategy becomes preferred. |
| PaddleOCR | Offline fallback / later self-hosted candidate | Strong open-source deployability and multilingual support, but requires model packaging, runtime sizing, and local benchmark before MVP. |
| Amazon Textract DetectDocumentText | Rejected for MVP Vietnamese OCR | Strong document layout API, but official language support does not include Vietnamese. |

## Current Evidence State

This task prepares the contract, dataset, fixtures, and benchmark harness.
Provider credentials are not present in the repo, and no provider SDK has been
integrated yet, so live provider CER/WER numbers are intentionally not checked
in. The ADR records Google Cloud Vision as the MVP primary candidate pending a
credentialed live run against this Vietnamese-source dataset. The generator
reads fixture text from UTF-8 JSON so Vietnamese diacritics are preserved even
when run with Windows PowerShell 5.1.

Sources reviewed:

- Google Cloud Vision OCR language support and pricing.
- Azure AI Vision Read language support and pricing.
- Amazon Textract quotas/language support and pricing.
- PaddleOCR official repository and release documentation.
