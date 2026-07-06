# ADR 0002: OCR-to-Parser Pipeline Architecture

Date: 2026-06-29

Status: Accepted

## Context

MenuScan processes uploaded images and PDFs of Vietnamese restaurant menus.
Raw OCR output from a provider must be converted into structured menu data
(dish names, prices, categories) that a foreign visitor can read in their
language. Two pipeline architectures were considered.

**Option A — OCR then LLM (two-step)**

```text
file bytes → OcrAdapter.run() → OcrDocument
           → LLM parser (Gemini) with OcrDocument.text
           → ParsedMenuDraft (with translated_name/translated_description)
           → persist Menu + FoodItem rows
```

**Option B — Direct multimodal LLM**

```text
file bytes → Gemini multimodal (image + text prompt)
           → ParsedMenuDraft
           → persist Menu + FoodItem rows
```

## Decision

Use **Option A** — OCR then LLM.

For the LLM parsing step, use **Google Gemini** (`gemini-2.5-flash` default)
with `responseMimeType: "application/json"` and an explicit `responseSchema`
matching `ParsedMenuDraft`. The parser call combines extraction and
translation in a single prompt, populating `translated_name` and
`translated_description` alongside the structured item data.

## Rationale

### Why Option A over Option B

| Concern | Option A (OCR → LLM) | Option B (direct multimodal) |
| --- | --- | --- |
| Text accuracy on low-quality photos | OCR provider specialized for document text | Multimodal LLM may hallucinate text from blur |
| Vietnamese diacritics | Vision `languageHints: ["vi"]` improves recognition | No equivalent hint mechanism |
| Benchmark and regression testing | CER/WER measurable on `OcrDocument.text` | No intermediate text to measure |
| Cost | OCR cheap per page; LLM only sees text tokens | LLM pays image tokens for every page |
| Provider swap | Swap OCR adapter; parser unchanged | Entire pipeline tied to one multimodal provider |
| Geometry / layout traceability | `OcrSourceReference` carries bounding boxes | No geometry from pure LLM output |

### Why Gemini for the LLM parser step

- Supports structured JSON output via `responseMimeType` + `responseSchema`,
  eliminating fragile markdown code-block parsing.
- Handles Vietnamese text well and can produce translations in the same call.
- `gemini-2.5-flash` is fast and cost-effective for text-only prompts.
- The model name is configurable via `settings.llm.model`; the parser does
  not hardcode it.

### PDF handling decision

Google Cloud Vision `files:annotate` requires files to be in Google Cloud
Storage — inline base64 PDF is not supported. To keep the upload flow simple
(no GCS dependency at the adapter boundary), adapters **must**:

1. Detect `application/pdf` MIME type.
2. Convert each page to PNG using **`pymupdf`** (import name `fitz`) before
   calling the provider.
3. Call the provider's image endpoint once per page.
4. Merge per-page results into one `OcrDocument` with one `OcrPage` per page.

`pymupdf` is a pure-Python wheel with no system-level Poppler or Ghostscript
dependency, which simplifies Docker build and local development.

The upload validator already enforces a page limit (`max_pages` from
`settings`). Adapters must honour this limit and raise
`OcrAdapterError(OcrErrorCode.INPUT_TOO_LARGE)` if the PDF exceeds it.

## Consequences

- The `OcrAdapter` base class in `ocr_contract.py` is the only interface the
  worker imports; adapters implement `run(file_bytes, mime_type,
  source_object_key) → OcrDocument`.
- Parser and translation code must never import an adapter module.
- `pymupdf` must be added to `app/pyproject.toml` dependencies before any
  adapter handles PDFs.
- LLM parsing prompt must instruct the model to set `price = null` when
  confidence is low, and to preserve unusual dish names verbatim in
  `original_name`.
- `parsing_provider` in `ParsedMenuDraft` must be set to the Gemini model
  string (e.g. `"gemini-2.5-flash"`) for benchmark traceability.
- `source_references` and per-item `confidence` in `ParsedMenuItemDraft` will
  be empty/null when using the LLM parser, because the model receives only
  text and has no access to bounding box geometry. This is an accepted
  trade-off for MVP.
  **Superseded in part by ADR 0003:** the Gemini parser now also receives the
  menu page image(s) (hybrid image + OCR text). OCR is retained as the
  character/price anchor and benchmark intermediate; `source_references` /
  per-item confidence remain empty. See
  [ADR 0003](0003-multimodal-menu-parser.md).
- A live OCR benchmark (CER/WER, price accuracy, line recall) against
  `doc/ocr-benchmark/dataset/ground_truth.json` must pass the quality gates
  in `doc/ocr-benchmark/README.md` before any adapter is wired to production
  scan orchestration.

## Sources

- Google Cloud Vision `DOCUMENT_TEXT_DETECTION` response structure and
  language support documentation.
- Google Cloud Vision `files:annotate` PDF limitation (GCS-only input).
- Google Gemini `generateContent` structured output documentation
  (`responseMimeType`, `responseSchema`).
- `pymupdf` (fitz) official repository and release notes.
- ADR 0001: OCR Provider for MVP.
