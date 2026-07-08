# ADR 0003: Multimodal Menu Parser (image + OCR text)

Date: 2026-07-06

Status: Accepted. Amends ADR 0002.

## Context

ADR 0002 chose **OCR → text → LLM** (Option A) and explicitly rejected direct
multimodal (Option B), recording as a consequence that "the model receives only
text and has no access to bounding box geometry".

In practice, hard menus break this text-only assumption: two-column layouts,
per-item descriptions, right-aligned price columns, grouped variant lists
(a section header + a numbered list of protein/size variants sharing one
description and surcharge), and skewed photos. On such menus the OCR provider's
block grouping is unreliable, and the parser only receives coordinates as text —
a weak channel for reconstructing 2-D layout.

A live A/B/C experiment on a real two-column Vietnamese–English menu (38 items,
faint background watermark) measured:

- **A — text-only (current):** re-associated even the OCR-detached price column
  correctly (bbox coordinates helped), but **propagated OCR character errors**
  verbatim (`GÃ`→`GÀ`, `CHẠY`→`CHAY`).
- **B1 — image-only (drop OCR):** **timed out (>90s)** on the dense menu; the
  model had to both read and reconstruct structure from the image alone. Also
  loses the CER/WER benchmark and the non-LLM fallback.
- **B2 — hybrid image + OCR text:** same price accuracy as A, **fixed the OCR
  character errors**, and recovered the menu title. Best result.

## Decision

Adopt **B2 (Hybrid)** for the Gemini parser: attach the menu page image(s) to the
same `generateContent` call as an `inlineData` part, alongside the OCR text.

- The **image** is authoritative for layout: reading order, columns, price↔dish
  association, and item grouping.
- The **OCR text** is authoritative for exact spelling and price digits (the
  character/price anchor, with Vietnamese `languageHints`).
- When images are present, the coordinate dump (`_build_layout_text`) is dropped
  in favour of the image; the raw OCR text is still sent as the anchor.
- **OCR is retained**, not replaced. B1 (image-only) is rejected: it is slower
  and timeout-prone on dense menus, removes the CER/WER benchmark intermediate,
  and removes the rule-based fallback path.

Gated by `settings.llm.multimodal` (env `LLM_MULTIMODAL`, default **true**) and
bounded by `settings.llm.image_max_dimension` (env `LLM_IMAGE_MAX_DIMENSION`,
default 1536) to cap image-token cost and latency. Only the `gemini` provider
consumes images; the rule-based parser ignores them.

## Consequences

- `MenuParser.parse` gains an optional `images: Sequence[bytes] | None`. The
  pipeline prepares per-page PNGs (one per page; multi-page ready) via the
  `DocumentPreprocessor` and passes them to the parser.
- Image preparation is **best-effort**: any failure logs and falls back to
  text-only — it must never fail a scan.
- OCR (`OcrDocument.text`) is unchanged, so the CER/WER OCR benchmark still
  applies. A separate parse-accuracy (item/price) benchmark is added to measure
  the parsing improvement quantitatively.
- Cost: one (down-scaled) image per page of input token cost per scan; latency
  per parse increases. Image-heavy calls are more rate-limited on the Gemini free
  tier — retry/backoff and the model chain (`gemini-3.1-flash-lite` primary,
  `gemini-2.5-flash` fallback by default) remain important.
- `source_references` and per-item `confidence` from the LLM parser remain
  empty/null (unchanged from ADR 0002) — the model still does not emit geometry.
- The grouped-variant prompt rules map header + numbered variants into
  `base_name` / `variant_group` / `variant_name`.

## Sources

- ADR 0002: OCR-to-Parser Pipeline Architecture.
- Google Gemini `generateContent` multimodal input (`inlineData`) and structured
  output (`responseMimeType`, `responseSchema`) documentation.
- Live A/B/C parse experiment (this repo, 2026-07-06).
