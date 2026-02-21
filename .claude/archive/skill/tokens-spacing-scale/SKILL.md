---
name: spacing-scale
description: Generates consistent spacing tokens using base values and ratios. Use when creating margin/padding systems, gap tokens, or layout spacing. Outputs CSS custom properties, Tailwind config, or JSON tokens.
---

# Spacing Scale Generator

## Overview

Generate consistent spacing scales using a base value and ratio. Creates exponentially distributed values centered around a base unit for harmonious layouts.

## When to Use

- Setting up spacing tokens for a new project
- Standardizing padding and margin values
- Creating a gap/grid system
- Migrating from arbitrary spacing to tokens

## Quick Reference

| Naming Style | Example Names | Best For |
|--------------|---------------|----------|
| T-shirt | xs, sm, md, lg, xl | Semantic, readable |
| Numeric | 100, 200, 300... | Precise, extensible |

| Unit | When to Use |
|------|-------------|
| px | Fixed layouts, pixel-perfect designs |
| rem | Scalable, respects user font settings |
| em | Component-relative spacing |

## The Process

1. **Get base value**: Default 4px or 0.25rem (common base unit)
2. **Get ratio**: How much each step grows (1.5 is balanced, 2 is dramatic)
3. **Ask steps**: How many spacing values (8-12 is typical)
4. **Ask naming**: T-shirt sizes (xs, sm, md, lg) or numeric (100, 200, 300)?
5. **Ask unit**: px, rem, or em?
6. **Ask format**: CSS, Tailwind, or JSON?
7. **Generate**: Create scale centered on base, expanding in both directions

## Common Ratios

| Ratio | Character | Example (base 4px) |
|-------|-----------|-------------------|
| 1.25 | Tight | 2, 2.5, 3, 4, 5, 6, 8 |
| 1.5 | Balanced | 1.8, 2.7, 4, 6, 9, 13.5 |
| 1.618 | Golden | 1.5, 2.5, 4, 6.5, 10.5, 17 |
| 2 | Dramatic | 1, 2, 4, 8, 16, 32 |

## Output Formats

**CSS Custom Properties:**
```css
:root {
  --spacing-xs: 2px;
  --spacing-sm: 4px;
  --spacing-md: 8px;
  --spacing-lg: 16px;
  --spacing-xl: 32px;
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    spacing: {
      'xs': '2px',
      'sm': '4px',
      'md': '8px',
      'lg': '16px',
      'xl': '32px',
    }
  }
}
```

**JSON Tokens:**
```json
{
  "spacing": {
    "xs": "2px",
    "sm": "4px",
    "md": "8px",
    "lg": "16px",
    "xl": "32px"
  }
}
```

## Algorithm

The scale is centered on the base value at the midpoint:

```
value = baseValue * (ratio ^ (step - midpoint))
```

For a 10-step scale with base 4 and ratio 1.5:
- Step 0 (5 below mid): 4 * 1.5^-5 = 0.53
- Step 5 (midpoint): 4 * 1.5^0 = 4
- Step 9 (4 above mid): 4 * 1.5^4 = 20.25

## T-shirt Size Mapping

Full range: 3xs, 2xs, xs, sm, md, lg, xl, 2xl, 3xl, 4xl, 5xl, 6xl

The midpoint of your scale maps to "md" and expands outward.
