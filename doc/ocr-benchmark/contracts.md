# OCR and Parser Contracts

## Boundary

```text
Scan Orchestrator
  -> OCR adapter: source object key, MIME, page limit
  <- OcrDocument: raw text, pages, blocks, lines, boxes, confidence, safe metadata

Parser (LLM or rule-based)
  -> OcrDocument
  <- ParsedMenuDraft: menu title, item drafts with translation,
     price text/value, source references, parsing_provider

Translation
  -> ParsedMenuDraft items that parser already identified
  <- translated names/descriptions (may be populated by LLM parser in a single call)
```

OCR never creates `Menu` or `FoodItem`. Parser owns menu/item extraction.
Translation never reads raw provider output.

Product assumption for MVP: users are foreign visitors in Vietnam. OCR should
optimize for Vietnamese source menus first; English belongs mainly to the
translation target or rare bilingual menu glosses.

## `OcrDocument`

Defined in `app/src/modules/menu_scan/ocr_contract.py`.

Required behavior:

- Use normalized bounding boxes where `left`, `top`, `width`, and `height` are
  floats from `0..1`.
- Preserve page/block/line IDs so parser output can cite `OcrSourceReference`.
- `OcrLine` maps to a Vision 'paragraph' or an Azure 'line'. Adapters may split
  long Vision paragraphs at detected line breaks. One `OcrLine` represents the
  smallest logical text unit the parser receives.
- Keep provider metadata safe: no API keys, access tokens, full provider raw
  payloads, signed URLs, or customer data beyond OCR text already stored in
  `raw_text`.
- `provider` is an internal short code such as `google_vision`, `azure_read`,
  `paddle_ocr`, or `fixture`.

## `ParsedMenuDraft`

Defined in `app/src/modules/menu_scan/ocr_contract.py`.

Required behavior:

- `price_text` is the exact text seen by parser.
- `price` is a decimal string only when parser is confident; otherwise `null`.
- `currency` is ISO 4217 (`VND`, `USD`, `EUR`) when known; otherwise `null`.
- For one-dish-many-type layouts, parser should emit one priced item draft per
  variant while preserving `base_name`, `variant_name`, and `variant_group`.
  Example: OCR line `Đặc biệt 85.000đ` under heading `BÚN BÒ` becomes
  `original_name = "Bún bò đặc biệt"`, `base_name = "Bún bò"`,
  `variant_name = "đặc biệt"`.
- Preserve unusual, figurative, and regional dish names exactly in
  `original_name`. Do not replace `Vũ nữ chân dài`, `Sỏi mầm`, or
  `Cơm Âm Phủ` with inferred ingredient-only names. If the menu includes an
  explanation after a dash or colon, keep it in `original_description`.
- Each item should include at least one `source_reference` when OCR geometry is
  available.
- `source_language` is the detected source menu language. MVP fixtures should be
  Vietnamese-first (`vi`), even when a line contains an English gloss.
- `target_language` is the user's display language after parser output is
  known; OCR adapters do not translate.
- `translated_name` and `translated_description` carry the translation output.
  When the parser is an LLM that translates in the same call, these are
  populated directly. When translation is a separate step, they start as `null`
  and are filled later.
- `parsing_provider` identifies who produced the draft (e.g. `gemini-2.5-flash`,
  `rule-based`, `fixture`) for debug and benchmark traceability.
- Fixture and benchmark data should preserve Vietnamese diacritics and include
  long menus with at least 20 priced items, because that is the expected
  production shape for many restaurants in Vietnam.
- Draft data is not persisted directly as final menu data until scan completion
  validates at least one item.

## Standard OCR Error Codes

| Code | Meaning |
| --- | --- |
| `UNSUPPORTED_INPUT` | MIME, page count, or image/PDF shape cannot be processed. |
| `INPUT_TOO_LARGE` | Provider or MenuScan size/page limit exceeded. |
| `INVALID_DOCUMENT` | Corrupt image/PDF or password-protected PDF. |
| `PROVIDER_UNAVAILABLE` | Provider dependency is unavailable. |
| `PROVIDER_TIMEOUT` | Provider did not finish inside timeout budget. |
| `PROVIDER_RATE_LIMITED` | Provider throttled the request. |
| `LOW_CONFIDENCE` | OCR completed but confidence is below MVP threshold. |
| `NO_TEXT_FOUND` | Provider returned no usable text. |
| `UNSAFE_PROVIDER_METADATA` | Adapter attempted to persist unsafe metadata. |
