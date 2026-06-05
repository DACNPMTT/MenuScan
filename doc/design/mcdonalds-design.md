# McDonald's Design System

## 1. Core Philosophy
- **Photography as Voltage:** The marketing chrome has receded to charcoal on white. Every chromatic moment lives inside campaign photography.
- **Single Golden Pill:** The Arches yellow appears exclusively on CTA pill fills, fenced by a 1px gold-stroke border.
- **Editorial Typography:** Speedee runs across every tier without heavier display weights. The loudest moment is the 36px / 700 hero text.

## 2. Color Tokens
- `color-primary`: #FFBC0D (Arches Yellow - Use ONLY for primary CTA pill backgrounds)
- `color-primary-stroke`: #C08B00 (1px border specifically for the primary CTA pill)
- `color-text-main`: #292929 (Charcoal Ink - Used for 839+ text and border occurrences instead of pure black)
- `color-background`: #FFFFFF (Pure White canvas)
- `color-civic-blue`: #006BAE (Used exclusively for community programs, accessibility, and footer links. NEVER on commercial CTAs)

## 3. Typography (Font: Speedee / Fallback: Inter)
- `text-hero`: 36px, Weight 700, Letter-spacing -0.15px, Color #292929
- `text-body`: 16px, Weight 400, Color #292929
- `text-caption`: 10px, Weight 400, Color #292929 (Disclaimer text)
*Note: No display ladder, no serif companion, no italic emphasis.*

## 4. Radii & Shape (Strictly Binary)
- `radius-button`: 48px (Full Pill shape, applied to all CTAs)
- `radius-tile`: 12px (Applied to image tiles/cards)
*Note: Do not use 4px, 8px, or 16px middle tiers.*

## 5. Spacing System
- Core rhythm is dominated by `18px` and `6px` increments. 

## 6. Component Specs
- **Primary CTA:** Background `#FFBC0D`, Border `1px solid #C08B00`, Radius `48px`, Text Color `#292929` or `#FFFFFF` (depending on contrast).
- **Photo Card Stack:** Radius `12px`, zero outer margin bleed (full-bleed stacked).