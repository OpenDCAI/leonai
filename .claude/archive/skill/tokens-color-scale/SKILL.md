---
name: color-scale
description: Generates perceptually uniform OKLCH color palettes from brand colors. Use when creating color systems, theme palettes, or converting hex values to 11-step scales. Outputs CSS custom properties, Tailwind config, or JSON tokens.
---

# Color Scale Generator

## Overview

Generate perceptually uniform 11-step color scales (50-950) from any base color. Includes auto-generated neutral and semantic colors harmonized with the brand.

## When to Use

- Starting a new project needing a color system
- Adding brand colors to an existing palette
- Building light/dark theme tokens
- Converting a single hex to a full scale

## Quick Reference

| Step | Lightness | Typical Use |
|------|-----------|-------------|
| 50   | 97%       | Subtle backgrounds |
| 100  | 93%       | Hover states on light |
| 200  | 87%       | Borders, dividers |
| 300  | 78%       | Disabled states |
| 400  | 65%       | Placeholder text |
| 500  | 55%       | Primary brand color |
| 600  | 45%       | Hover on dark |
| 700  | 37%       | Active states |
| 800  | 27%       | Headings |
| 900  | 20%       | Body text |
| 950  | 14%       | High contrast text |

## The Process

1. **Get input**: Ask for base color (hex preferred) and color name (e.g., "primary")
2. **Ask format**: CSS custom properties, Tailwind config, or JSON tokens?
3. **Ask color system** (default OKLCH):
   - OKLCH - Perceptually uniform, modern standard (recommended)
   - HSL - Hue, Saturation, Lightness (wide browser support)
   - RGB - Red, Green, Blue (universal compatibility)
   - LCH - Lightness, Chroma, Hue (perceptual, CSS Color 4)
   - HEX - Hexadecimal notation (maximum compatibility)
4. **Generate scale**: Create 11 steps with consistent chroma/saturation
5. **Add neutrals**: Generate neutral scale using same hue, minimal saturation
6. **Add semantics**: Generate success, warning, error, info harmonized with brand
7. **Output**: Provide complete token set in requested format

## Color Systems

| System | Format Example | Best For |
|--------|----------------|----------|
| OKLCH  | `oklch(55% 0.15 250)` | Modern browsers, perceptual accuracy |
| HSL    | `hsl(220 80% 55%)` | Wide support, intuitive adjustments |
| RGB    | `rgb(59 130 246)` | Universal, legacy systems |
| LCH    | `lch(55% 60 250)` | Perceptual, CSS Color Level 4 |
| HEX    | `#3b82f6` | Maximum compatibility |

**Recommend OKLCH** for new projects - it produces more visually consistent scales because lightness and chroma are perceptually uniform.

## Output Formats

**CSS Custom Properties:**
```css
:root {
  --primary-50: oklch(97% 0.01 250);
  --primary-500: oklch(55% 0.15 250);
  --primary-950: oklch(14% 0.10 250);
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: 'oklch(97% 0.01 250)',
          500: 'oklch(55% 0.15 250)',
        }
      }
    }
  }
}
```

**JSON Tokens:**
```json
{
  "color": {
    "primary": {
      "50": { "value": "oklch(97% 0.01 250)" },
      "500": { "value": "oklch(55% 0.15 250)" }
    }
  }
}
```

## Algorithm Details

**Lightness stops** (L values):
- 50: 0.97, 100: 0.93, 200: 0.87, 300: 0.78, 400: 0.65
- 500: 0.55, 600: 0.45, 700: 0.37, 800: 0.27, 900: 0.20, 950: 0.14

**Chroma/saturation adjustment** at extremes:
- L > 0.9: reduce to 30% (prevents washed-out pastels)
- L < 0.2: reduce to 70% (prevents muddy darks)
- Otherwise: full chroma

**Semantic color hues** (harmonized 10-15% toward brand):
- Success: base 145 (green)
- Warning: base 70 (amber)
- Error: base 25 (red)
- Info: base 250 (blue)
