---
version: alpha
name: MenuScan Landing (Duolingo dialect)
description: >-
  MenuScan's marketing landing rendered in Duolingo's visual dialect on a
  pure-white canvas with a single owl-green CTA voltage (#58cc02), Nunito as
  the open-source stand-in for Feather Bold (display) and DIN Round (body),
  uppercase gamepad-button labels, and Pip the pineapple as the decoration
  anchor. Navy display headlines (#042c60) pair with owl-green section titles.
---

## Colors

| Token | Hex | Role |
|---|---|---|
| owl-green | #58cc02 | primary CTA fill, brand voltage, section h2, check icons |
| owl-green-pressed | #58a700 | button shadow-lip, hover emphasis, tip text |
| owl-green-soft | #d7ffb8 | logo badge, icon tiles, avatar fallback, chip tint |
| owl-green-mint | #a5ed6e | sparkle accent, secondary blob |
| navy-display | #042c60 | hero h1, card titles, wordmark |
| body-ink | #3c3c3c | emphasized body, partner names |
| body-muted | #777777 | body paragraphs, nav links |
| body-soft | #afafaf | footer copyright, disabled text |
| canvas | #ffffff | edge-to-edge section background |
| surface-gray | #f7f7f7 | Partners section tint |
| hairline | #e5e5e5 | card/input borders, button lips, dividers |
| macaw-blue | #1cb0f6 | secondary CTA text (duo-outline) |
| bee-gold | #ffc800 | review stars, sparkle accent |
| fox-orange | #ff9600 | step tip pills |

## Typography

Single family — **Nunito** (Google Fonts, weights 400–900). It is the closest
free substitute for both Feather Bold (display) and DIN Round (UI/body).

| Token | Family | Size | Weight | Tracking | Transform |
|---|---|---|---|---|---|
| display-xl | Nunito | 56px | 900 | -0.02em | none |
| section-h2 | Nunito | 48px | 900 | tight | none |
| body-lg | Nunito | 17px | 500 | 0 | none |
| body-md | Nunito | 15px | 700 | 0 | none |
| label-cta | Nunito | 15px | 800 | 0.8px | UPPERCASE |

Weight discipline: 500 for body, 800/900 for headings and CTAs. No 400/600 on
the landing.

## Shapes & Elevation

- Button / card radius: `16px` (`rounded-2xl`). Pill (`9999px`) for badges,
  solves-check circles, tip pills only.
- **Shadow-as-lip**: every primary element carries a flat `box-shadow:
  0 4px 0 <pressed-color>` that collapses to `0 2px 0` + `translateY(2px)` on
  `:active`. No diffuse blur shadows on the landing.
- Hairline borders: `2px solid #e5e5e5`.

## Components

- **button duo** — owl-green fill, white uppercase Nunito 800/0.8px label,
  `0 4px 0 #58a700` lip, 52px height on hero CTAs.
- **button duo-outline** — white fill, macaw-blue uppercase label, `2px #e5e5e5`
  border + matching lip.
- **badge-pill** — white pill, `2px` green-tint border, green uppercase label.
- **step-badge** — green rounded square, white number, green lip.
- **review-card** — white, `2px` hairline border + gray lip, bee-gold stars.
- **cta-panel** — owl-green block with `0 8px 0` lip (giant gamepad button).
- **mascot-cluster** — floating Pip pineapple + green/gold twinkling sparkles.

## Do's and Don'ts

**Do** use #58cc02 for primary CTAs and section h2 only.
**Do** keep CTA labels uppercase with 0.8px letter-spacing.
**Don't** introduce a second saturated fill — secondary actions are white +
macaw-blue text.
**Don't** use gradients — decoration is the mascot + solid blobs only.
**Don't** use Inter / Plus Jakarta on the landing — Nunito carries the rounded
display character the dialect depends on.
