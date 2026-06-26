---
name: Voltage Minimalist
colors:
  surface: '#f7fbed'
  surface-dim: '#d7dcce'
  surface-bright: '#f7fbed'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f5e7'
  surface-container: '#ebf0e2'
  surface-container-high: '#e6eadc'
  surface-container-highest: '#e0e4d6'
  on-surface: '#181d15'
  on-surface-variant: '#41493a'
  inverse-surface: '#2d3229'
  inverse-on-surface: '#eef2e4'
  outline: '#717a68'
  outline-variant: '#c1cab5'
  surface-tint: '#2e6c00'
  primary: '#2e6b00'
  on-primary: '#ffffff'
  primary-container: '#418613'
  on-primary-container: '#ffffff'
  inverse-primary: '#8fda60'
  secondary: '#5e5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e2e2e2'
  on-secondary-container: '#646464'
  tertiary: '#5d5e5f'
  on-tertiary: '#ffffff'
  tertiary-container: '#757777'
  on-tertiary-container: '#ffffff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a9f779'
  primary-fixed-dim: '#8fda60'
  on-primary-fixed: '#092100'
  on-primary-fixed-variant: '#215100'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c6'
  on-secondary-fixed: '#1b1b1b'
  on-secondary-fixed-variant: '#474747'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#f7fbed'
  on-background: '#181d15'
  surface-variant: '#e0e4d6'
  ink-muted: '#707070'
  hairline: '#E6E6E6'
typography:
  display-xl:
    fontFamily: Jost
    fontSize: 60px
    fontWeight: '700'
    lineHeight: 72px
  display-xl-mobile:
    fontFamily: Jost
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
  display-md:
    fontFamily: Jost
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 34px
  heading-md:
    fontFamily: Jost
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 30px
  heading-sm:
    fontFamily: Jost
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
  body-md:
    fontFamily: Jost
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 22.4px
  body-sm:
    fontFamily: Jost
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 21px
  label-md:
    fontFamily: Jost
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 14px
  button-md:
    fontFamily: Jost
    fontSize: 17px
    fontWeight: '700'
    lineHeight: 24px
  nav-link:
    fontFamily: Jost
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 14px
spacing:
  xs: 5px
  sm: 8px
  md: 20px
  base: 25px
  lg: 30px
  xl: 50px
  2xl: 75px
---

## Brand & Style

This design system is built on a philosophy of **Modern Cinematic Minimalism**. It leverages high-contrast color blocks and photography-led layouts to create a premium, "modern burger stand" atmosphere. The aesthetic is intentionally disciplined, eschewing the visual clutter of traditional fast-food marketing in favor of a sophisticated, mid-market feel.

The design style is **High-Contrast / Bold**, defined by:
- **Binary Surface Logic:** A striking transition between saturated brand color, pure white, and deep black.
- **Organic Professionalism:** The use of a deep forest green provides a more organic, premium feel than standard primary colors.
- **Disciplined Precision:** Strict adherence to a single typeface and a specific signature corner radius creates an unmistakable brand signature.

## Colors

The color palette utilizes a "Voltage" strategy: the primary brand green is reserved for high-impact brand moments and conversion points, making its appearance feel significant rather than decorative. 

- **Primary (#418613):** Used for the hero background and primary "Order" calls to action.
- **Ink (#000000):** The structural foundation. Used for footers, text cards, and primary body text.
- **Canvas (#FFFFFF):** The clean space for content-heavy mid-sections and button fills.
- **Muted & Hairline:** These low-chroma tones are used exclusively for secondary support (helper text, subtle dividers, and input underlines).

## Typography

This design system uses **Jost** as its universal typeface. The system is highly disciplined, utilizing only weight 400 (Regular) and 700 (Bold) to maintain a sharp, graphic quality. 

Hierarchy is established through extreme scale shifts rather than weight variations. Large display headlines are used for editorial impact, while navigation links utilize uppercase styling for a structural, architectural feel. On mobile, the `display-xl` scale reduces to ensure legibility and visual balance without losing brand impact.

## Layout & Spacing

The layout philosophy relies on **Panel Layering**. Content is organized into full-bleed horizontal strips that jump between the primary colors of the palette. 

- **Grid Strategy:** A responsive 4-column grid is used for the footer and content cards, while hero sections remain full-bleed.
- **Rhythm:** An 8px base unit drives vertical rhythm, with significant horizontal margins (75px) on desktop to create a centered, focused content well.
- **Reflow:** On mobile devices, 75px horizontal margins compress to 20px, and 4-column grids collapse into a single stacked column.

## Elevation & Depth

This system is **entirely flat**. Visual hierarchy is achieved through contrast and color-blocking rather than shadows or depth effects.

- **Stacking:** Depth is implied by overlapping sharp-edged cards (often black or white) onto saturated or photographic backgrounds.
- **No Shadows:** Do not use box-shadows or drop-shadows on any element.
- **Clarity:** Use 1px hairline borders in the `hairline` color (#E6E6E6) only when necessary to separate elements of the same color; otherwise, rely on the binary surface jumps for separation.

## Shapes

The shape language is a study in contrast: **Hard containers and pill-shaped interactive elements.**

- **Structural Surfaces:** All major containers, including navigation bars, hero sections, and text cards, use sharp (0px) corners.
- **Interactive Elements:** All buttons and specific call-to-action pills must use a **30px border radius**. This signature curve is the primary differentiator for interactive vs. static content.
- **Inputs:** Form fields remain sharp (0px) to align with the structural containers, utilizing a bottom-border only for a minimal "underline" style.

## Components

### Buttons
- **Primary:** Forest green background, white Jost 700 text, 30px border radius. Height: 48px.
- **Secondary:** White background, 1px black border, black Jost 700 text, 30px border radius.
- **Nav Pill:** Forest green background, white Jost 700 text, 30px border radius.

### Input Fields
- **Style:** Transparent background with a 1px `hairline` (#E6E6E6) bottom border.
- **Typography:** Labels use `label-md` (Jost 400).

### Hero Text Card
- **Style:** Pure black (#000000) background with sharp 0px corners.
- **Typography:** White Jost text. Positioned to overlap the hero image or background to create depth through panel layering.

### Footer
- **Style:** Pure black (#000000) background. 
- **Structure:** 4-column layout on desktop. High-contrast white text for links and brand identifiers.

### Content Cards
- **Style:** Sharp 0px corners. Typically white or black depending on the section's background. No border or shadow.