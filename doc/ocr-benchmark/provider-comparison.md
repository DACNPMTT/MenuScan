# OCR Provider Comparison

The table below is desk research from official provider documentation checked on
2026-06-26. Live benchmark metrics must be filled by running the same
`dataset/ground_truth.json` against each provider adapter once credentials are
available.

MenuScan's MVP user is a foreign visitor eating in Vietnam. The OCR source
language is therefore Vietnamese restaurant-menu text first. English support is
useful for bilingual glosses and downstream translation, but it must not drive
provider selection.

| Provider | Vietnamese menu fit | Layout preservation | Images/PDF | Speed/deploy | Cost shape | MVP decision |
| --- | --- | --- | --- | --- | --- | --- |
| Google Cloud Vision `DOCUMENT_TEXT_DETECTION` | Officially lists Vietnamese `vi`; supports language hints. English support is secondary for occasional bilingual text. | Page/block/paragraph/word style OCR geometry via document text detection. | Images and async file/PDF OCR flows. | Managed API, low ops burden. | Per-feature unit pricing, with free monthly quota on many Vision features. | **Primary candidate** pending live benchmark. |
| Azure AI Vision Read | Read supports mixed-language documents and printed Vietnamese. | Read returns lines/words with bounding polygons. | Images and documents; multipage PDF counts per page. | Managed API and container options. | Transaction-based pricing; Read has free tier and paid tiers. | Secondary managed fallback. |
| PaddleOCR | Open-source multilingual OCR; current docs highlight broad language support and self-hosted deployment. | PP-Structure can emit structured coordinates/JSON/Markdown. | Images/PDF workflows supported by toolkit. | Requires packaging, CPU/GPU sizing, model download, and ops ownership. | No per-page API fee, but infra/ops cost. | Offline/self-hosted fallback after live benchmark. |
| Amazon Textract DetectDocumentText | Official Textract language support excludes Vietnamese. | Strong document block geometry. | JPEG, PNG, PDF, TIFF; async supports large multipage files. | Managed AWS API. | Per-page pricing; DetectDocumentText examples list per-page rates. | Rejected for MVP Vietnamese OCR. |

## Live Benchmark Result Template

| Provider | Samples | CER | WER | Price accuracy | Line recall | Column accuracy | p95 ms/page | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| google_vision | 22 Vietnamese-source | pending | pending | pending | pending | pending | pending | Must run before production integration |
| azure_read | 22 | pending | pending | pending | pending | pending | pending | Must run before fallback approval |
| paddle_ocr | 22 | pending | pending | pending | pending | pending | pending | Must run before self-hosted approval |

## Benchmark Run Rules

1. Use exactly the files in `dataset/assets/`.
2. Disable provider-specific parser features; capture OCR text and geometry only.
3. Map each provider response to `OcrDocument`.
4. Compute metrics with `ocr_metrics.py`.
5. Save raw provider responses outside the repo if they contain unsafe metadata.
6. Commit only normalized `OcrDocument` outputs and aggregate metrics.

## Official Sources Checked

- Google Cloud Vision OCR language support: `https://cloud.google.com/vision/docs/languages`
- Google Cloud Vision pricing: `https://cloud.google.com/vision/pricing`
- Azure AI Vision language support: `https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/language-support`
- Azure AI Vision pricing: `https://azure.microsoft.com/en-us/pricing/details/computer-vision/`
- Amazon Textract quotas and language support: `https://docs.aws.amazon.com/textract/latest/dg/limits-document.html`
- Amazon Textract pricing: `https://aws.amazon.com/textract/pricing/`
- PaddleOCR official repository: `https://github.com/PaddlePaddle/PaddleOCR`
