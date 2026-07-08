# ADR 0001: OCR Provider for MVP

Date: 2026-06-26

Status: Accepted for MVP planning; production integration remains benchmark-gated

## Context

MenuScan is built for foreign visitors eating in Vietnam. Most source menus are
Vietnamese restaurant menus from images and PDFs; English is mainly a user
target language after parsing, or an occasional bilingual gloss on tourist-area
menus. OCR must not leak provider-specific response shapes into parser,
translation, or scan orchestration. The parser owns menu item extraction; OCR
only returns raw text, layout references, bounding boxes, confidence, and safe
metadata.

## Decision

Use Google Cloud Vision `DOCUMENT_TEXT_DETECTION` as the primary MVP OCR
candidate. Keep Azure AI Vision Read as the managed fallback and PaddleOCR as
the offline/self-hosted fallback. Reject Amazon Textract for MVP Vietnamese OCR.

Current implementation note (2026-07-08): Google Vision is implemented behind
`OCR_PROVIDER=google_vision`, while local development defaults to
`OCR_PROVIDER=fake`. The checked-in benchmark run is fast but below the current
MVP quality gates for CER/WER, price accuracy, and line recall, so production
use should include review/fallback expectations.

This chooses the primary provider for MVP adapter planning. Production
integration still requires a live run against
`doc/ocr-benchmark/dataset/ground_truth.json` that passes the quality gates in
`doc/ocr-benchmark/README.md`. The benchmark set must include Vietnamese
diacritics and realistic long menus with 20+ items, not only short sample menus.
It also must cover Vietnamese variant menus where one base dish has multiple
priced forms, such as `Bún bò` with `tái`, `nạm`, `gân`, `bò viên`, and
`đặc biệt`.
The benchmark must preserve unusual and figurative dish names from Vietnamese
menus, such as `Vũ nữ chân dài`, `Sỏi mầm`, and `Cơm Âm Phủ`, instead of
normalizing them into generic ingredient descriptions.

## Rationale

- Google Cloud Vision officially supports Vietnamese OCR language hints, can
  auto-detect document text, and maps naturally to page/block/line geometry
  needed by `OcrDocument`.
- Azure Read has strong mixed-language OCR and deployment flexibility, but it is
  kept as fallback until the team confirms Azure is preferred operationally.
- PaddleOCR is attractive for cost/privacy and self-hosting, but it introduces
  model/runtime operations that are heavier than the MVP needs.
- Textract has strong document layout features, but official language support
  excludes Vietnamese, which is a core MenuScan requirement.

## Consequences

- Provider adapters must normalize to `OcrDocument`; parser and translation must
  not import provider SDKs or raw response types.
- Provider evaluation must prioritize Vietnamese menu text and VND price
  extraction. English-only menus are not representative of the MVP path.
- The fixture set includes long Vietnamese menus so OCR/provider decisions are
  tested against normal restaurant menu density, not only three-item examples.
- Parser-facing contracts preserve optional `base_name`, `variant_name`, and
  `variant_group` for cases where a menu prints one base dish with many priced
  variants.
- OCR/parser evaluation must check that unusual names and regional specialties
  remain intact as `original_name`; explanations belong in
  `original_description` only when the menu text provides them.
- OCR adapter work can proceed independently from parser work using
  `doc/ocr-benchmark/fixtures/ocr-document.fixture.json`.
- Parser work can proceed independently using
  `doc/ocr-benchmark/fixtures/parsed-menu-draft.fixture.json`.
- The team must run live benchmark metrics before wiring a production scan
  worker to any provider.

## Review Checklist

- Đức can implement parser against `ParsedMenuDraft` fixtures without provider
  SDKs.
- Quang Linh can implement provider adapter against `OcrDocument` fixtures
  without menu persistence.
- QA can regenerate the 15-sample benchmark dataset and compare CER/WER, price,
  layout, and latency metrics.

## Sources

- Google Cloud Vision OCR language support and pricing.
- Azure AI Vision Read language support and pricing.
- Amazon Textract quotas/language support and pricing.
- PaddleOCR official repository and release notes.
