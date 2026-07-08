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

### Parse-accuracy (text-only vs multimodal B2)

`measure_parse_accuracy.py` scores item name-recall and price-accuracy of the
`GeminiMenuParser` against samples that have item-level ground truth, running it
both text-only and with the page image attached (ADR 0003). It makes live
Vision + Gemini calls (quota, rate-limited) — run manually, not in CI:

```powershell
python doc\ocr-benchmark\measure_parse_accuracy.py            # all item-truth samples
python doc\ocr-benchmark\measure_parse_accuracy.py ocr-019 ocr-020  # subset
```

Note: the synthetic dataset is clean, so text-only and B2 often tie here; the
gap widens on genuine skewed/multi-column photos.

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
| Google Cloud Vision `DOCUMENT_TEXT_DETECTION` | Implemented candidate, below current quality gates | Supports Vietnamese OCR language hints, returns page/block/word geometry, and has simple managed deployment. MenuScan preprocesses images/PDF pages to PNG before calling it. Current checked-in benchmark is fast but below CER/WER, price, and line-recall gates. |
| Azure AI Vision Read | Secondary managed fallback | Supports mixed-language Read OCR and printed Vietnamese; useful if Azure deployment/container strategy becomes preferred. |
| PaddleOCR | Offline fallback / later self-hosted candidate | Strong open-source deployability and multilingual support, but requires model packaging, runtime sizing, and local benchmark before MVP. |
| Amazon Textract DetectDocumentText | Rejected for MVP Vietnamese OCR | Strong document layout API, but official language support does not include Vietnamese. |

## Current Evidence State

The repository now includes the provider-neutral contract, synthetic dataset,
fixtures, benchmark harness, Google Vision adapter, and a checked-in normalized
Google Vision benchmark run:

- Provider output: `results/provider-output.json`
- Aggregate CSV: `results/google_vision.csv`
- Summary report: `../content/ocr-baseline-report.md`

Google Vision is wired in code behind `OCR_PROVIDER=google_vision`, while local
development still defaults to `OCR_PROVIDER=fake`. The checked-in benchmark is
evidence for tracking quality, not a guarantee that Google Vision currently
passes the MVP gates: the latest recorded CER/WER, price accuracy, and line
recall are below the gates, although p95 processing time passes. The generator
reads fixture text from UTF-8 JSON so Vietnamese diacritics are preserved even
when run with Windows PowerShell 5.1.

Sources reviewed:

- Google Cloud Vision OCR language support and pricing.
- Azure AI Vision Read language support and pricing.
- Amazon Textract quotas/language support and pricing.
- PaddleOCR official repository and release documentation.
