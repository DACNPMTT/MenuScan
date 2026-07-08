# ADR 0004: Deterministic OCR→CSV anchor + parse guardrails + latency budget

Date: 2026-07-08

Status: Accepted. Amends ADR 0002 and ADR 0003.

## Context

ADR 0002 chose **OCR → text → LLM**; ADR 0003 made the LLM parse **hybrid
image + OCR text**. In practice three problems remained on real Vietnamese
menus:

1. **Price↔dish mis-association.** The LLM still had to reconstruct which price
   belongs to which dish from either a verbose coordinate dump
   (`_build_layout_text`) or the image. On two-column and variant menus it
   sometimes paired the wrong price, or mis-grouped size/variant blocks.
2. **Wasted LLM calls and hallucinations.** A non-menu photo (a page of prose, a
   sign) still ran the full — expensive — parse, and the multimodal model
   occasionally invented dishes not present on the menu.
3. **Latency.** With model "thinking" left on and a 240s timeout, a scan could
   take minutes. Target: scan → menu in ~100s.

## Decision

Add a deterministic pass and two guardrails around the existing parse, and tune
the parse call for latency.

### 1. Deterministic OCR → menu-table (name, price, size) CSV anchor

`menu_table.build_menu_table(document)` pairs each dish with its price straight
from OCR geometry and recognises the `HEADER + variant list` layout (an ALL-CAPS
base header followed by short priced variants, detected by lookahead — **no
hardcoded dish names**), tagging size variants. It serialises to JSON/CSV.

The CSV is embedded in the parse prompt as a **strong name↔price anchor**
(`LLM_PREALIGN_CSV`, default on). The model is told to keep each price with its
dish unless the image/OCR clearly contradicts. In multimodal mode the image is
used for layout and the coordinate dump is dropped; in text-only mode the
structured OCR block dump is still included.

### 2. Pre-LLM menu-validity gate

`menu_validity.looks_like_menu(document)` runs before the parse. It is
deliberately conservative — it rejects only content that clearly is not a menu
(prose, no prices, no list structure) with `INVALID_DOCUMENT`, so a valid
no-price menu still passes. This is the "Text hợp lệ? là menu?" node; it saves an
LLM call on obviously-wrong photos.

### 3. Post-LLM output verification

`output_verifier.verify_draft(draft, document)` drops items with no name- or
price-grounding in the OCR text. Matching is **ascii-folded**, so the parser's
diacritic corrections (`GÃ`→`GÀ`, an explicit goal of ADR 0003) still match
their OCR source and are never dropped. It **never empties a non-empty draft** —
total removal is treated as a faulty check, not a faulty parse.

### 4. Latency budget

- Default model → `gemini-3.1-flash-lite` (`gemini-2.5-flash` as fallback).
- Disable model thinking (`thinkingConfig.thinkingBudget = 0`) — this is a
  schema-constrained extraction, not a reasoning task.
- Lower the default parse timeout to **100s**; a call that exceeds it is stuck,
  so fail fast to the fallback model.

## Consequences

- New modules: `menu_table.py`, `menu_validity.py`, `output_verifier.py`. The
  CSV table is both a standalone deliverable (exportable JSON/CSV) and the parse
  anchor.
- `GeminiMenuParser` gains `prealign_csv`; `LlmConfig` gains `prealign_csv` and a
  100s default timeout. `INVALID_DOCUMENT` is now an emitted scan error code.
- The rule-based fallback path is unaffected: its items are OCR-derived, so the
  verifier keeps them, and it ignores the CSV/thinking settings.
- Row counts from `build_menu_table` match the OCR-benchmark ground truth on
  every labelled sample; a follow-up should measure the CSV-anchor parse
  accuracy and latency live and, if favourable, drop `_build_layout_text`.
- **Unverified live:** actual latency and the API's acceptance of `thinkingConfig`
  for `gemini-3.1-flash-lite` must be confirmed with a real scan; the validity /
  quality thresholds need calibration on real photos.

## Sources

- ADR 0002: OCR-to-Parser Pipeline Architecture.
- ADR 0003: Multimodal Menu Parser (image + OCR text).
- Google Gemini `generateContent` `thinkingConfig` / structured-output docs.
- OCR benchmark ground truth (`doc/ocr-benchmark/dataset/ground_truth.json`).
