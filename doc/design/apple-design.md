# Apple (Inspired) Design System

## 1. Core Philosophy
- **Clarity & Contrast:** Content is the interface. Generous negative space, high contrast, and crisp typography.
- **Subtle Depth:** Flat UI by default, utilizing subtle shadows and blur (backdrop-filter) for hierarchy, not harsh borders.

## 2. Color Tokens
- `color-primary`: #0066CC (Apple Blue - Core interaction color for links, primary buttons, and active states)
- `color-secondary`: #1D1D1F (Deep Gray/Black - Primary text color, avoids the harshness of pure #000000)
- `color-tertiary`: #AF4900 (Warm Accent/Orange-brown - Used sparingly for warnings or specific status badges)
- `color-neutral`: #74777F (Muted Gray - For secondary text, disabled states, and subtle borders)
- `color-background`: #FFFFFF (Light mode) / #000000 (Dark mode)

## 3. Typography (Font: Inter / Fallback: San Francisco)
- `text-headline`: 32px to 48px, Weight 600/700, Tracking tight (-0.5px to -1px)
- `text-body`: 17px (Standard iOS body size), Weight 400, Line-height 1.5
- `text-label`: 13px to 15px, Weight 500, Color #74777F

## 4. Radii & Shape (Squircle aesthetic)
- `radius-sm`: 8px (Small inputs, nested cards)
- `radius-md`: 12px (Standard buttons, dropdowns)
- `radius-lg`: 18px to 24px (Main container cards, modals)

## 5. Component Specs
- **Primary Button:** Background `#0066CC`, Text `#FFFFFF`, Radius `12px`, Font Weight `500`. No borders.
- **Secondary Button:** Background transparent, Text `#0066CC`, Border none or subtle `#74777F` 1px outline.
- **Iconography:** Solid or Outline SF Symbols style, stroke width consistent at 1.5px to 2px.