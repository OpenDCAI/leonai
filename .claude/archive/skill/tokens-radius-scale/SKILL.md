---
name: radius-scale
description: Generates border-radius tokens from sharp to pill shapes. Use when creating corner rounding systems, button radius, card corners, or input styling. Outputs CSS, Tailwind, or JSON.
---

# Radius Scale Generator

## Overview

Generate consistent border-radius scales from sharp to pill-shaped. Creates harmonious rounding that scales appropriately with element size for visual consistency.

## When to Use

- Setting up radius tokens for a new project
- Standardizing corner rounding across components
- Creating button/card/input styling consistency
- Building component-size-aware radius systems

## Quick Reference

| Level | Typical Value | Use Case |
|-------|---------------|----------|
| none | 0 | Sharp corners, tables |
| sm | 2-4px | Subtle rounding, inputs |
| md | 6-8px | Buttons, cards |
| lg | 12-16px | Modals, large cards |
| xl | 20-24px | Panels, containers |
| 2xl | 32px+ | Feature sections |
| full | 9999px | Pills, avatars, badges |

## The Process

1. **Get base radius**: Default 8px (balanced starting point)
2. **Get ratio**: How much each step grows (1.5-2 typical)
3. **Ask steps**: How many radius values (5-7 typical)
4. **Ask unit**: px or rem?
5. **Ask format**: CSS, Tailwind, or JSON?
6. **Include full?**: Add "full" (9999px) for pills? (default: yes)
7. **Generate**: Create scale centered on base

## Common Scales

| Character | Base | Ratio | Result |
|-----------|------|-------|--------|
| Subtle | 4px | 1.5 | 2, 3, 4, 6, 9, 13 |
| Balanced | 8px | 2 | 2, 4, 8, 16, 32 |
| Rounded | 12px | 1.5 | 5, 8, 12, 18, 27, 40 |
| Soft | 16px | 1.5 | 7, 11, 16, 24, 36, 54 |

## Output Formats

**CSS Custom Properties:**
```css
:root {
  --radius-none: 0;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-2xl: 32px;
  --radius-full: 9999px;
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    borderRadius: {
      'none': '0',
      'sm': '4px',
      'md': '8px',
      'lg': '16px',
      'xl': '24px',
      '2xl': '32px',
      'full': '9999px',
    }
  }
}
```

**JSON Tokens:**
```json
{
  "radius": {
    "none": { "value": "0" },
    "sm": { "value": "4px" },
    "md": { "value": "8px" },
    "lg": { "value": "16px" },
    "xl": { "value": "24px" },
    "2xl": { "value": "32px" },
    "full": { "value": "9999px" }
  }
}
```

## Contextual Radius

Larger elements often need proportionally larger radius. Consider semantic tokens:

**CSS with contextual tokens:**
```css
:root {
  /* Base scale */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;

  /* Semantic/contextual */
  --radius-button: var(--radius-md);
  --radius-input: var(--radius-sm);
  --radius-card: var(--radius-lg);
  --radius-modal: var(--radius-xl);
  --radius-badge: var(--radius-full);
  --radius-avatar: var(--radius-full);
}
```

## Algorithm

The scale uses exponential growth from a base:

```
value = baseValue * (ratio ^ (step - midpoint))
```

For a 7-step scale with base 8px and ratio 2:
- Step 0 (3 below): 8 * 2^-3 = 1px
- Step 3 (mid): 8 * 2^0 = 8px
- Step 6 (3 above): 8 * 2^3 = 64px

Values are typically rounded to clean numbers.

## Design Considerations

**Consistency rule**: Inner radius = outer radius - border/padding

```css
/* Card with nested element */
.card {
  border-radius: var(--radius-lg); /* 16px */
  padding: 8px;
}
.card-inner {
  border-radius: calc(var(--radius-lg) - 8px); /* 8px */
}
```

**Squircle alternative**: For iOS-style continuous curves, consider `mask-image` with SVG or libraries like `squircle.js`.

## Common Patterns

| Component | Recommended Radius |
|-----------|-------------------|
| Icon buttons | sm or md |
| Text buttons | md |
| Input fields | sm or md |
| Cards | lg |
| Modals/dialogs | lg or xl |
| Tooltips | md |
| Badges/tags | full (pill) |
| Avatars | full (circle) |
| Containers | xl or 2xl |
