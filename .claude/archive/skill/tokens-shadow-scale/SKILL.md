---
name: shadow-scale
description: Generates layered box-shadow elevation tokens for depth hierarchy. Use when creating elevation systems, card shadows, modal depth, or dark mode shadow variants. Outputs CSS, Tailwind, or JSON.
---

# Shadow Scale Generator

## Overview

Generate consistent elevation scales using layered box-shadows. Creates depth hierarchy from subtle lifts to dramatic floats with proper blur, spread, and opacity progressions.

## When to Use

- Setting up elevation tokens for a new project
- Creating card/modal depth hierarchy
- Standardizing shadow styles across components
- Building dark mode shadow variants

## Quick Reference

| Level | Typical Use | Character |
|-------|-------------|-----------|
| none | Flat elements | No elevation |
| xs | Subtle lift | Barely raised |
| sm | Cards, buttons | Slight depth |
| md | Dropdowns, tooltips | Clear separation |
| lg | Modals, popovers | Floating |
| xl | Dialogs, drawers | High elevation |
| 2xl | Full overlays | Maximum depth |

## The Process

1. **Get base color**: Shadow color (default: black with opacity)
2. **Ask style**:
   - Soft - Large blur, low opacity (modern, subtle)
   - Sharp - Small blur, higher opacity (defined edges)
   - Layered - Multiple shadows per level (most realistic)
3. **Ask levels**: How many elevation steps (5-7 typical)
4. **Ask dark mode**: Generate inverted/adjusted dark mode variants?
5. **Ask format**: CSS, Tailwind, or JSON?
6. **Generate**: Create scale with progressive blur/spread/opacity

## Shadow Styles

| Style | Character | Best For |
|-------|-----------|----------|
| Soft | Diffuse, gentle | Modern UI, cards, light themes |
| Sharp | Defined, crisp | Buttons, data-dense UI |
| Layered | Realistic, nuanced | Premium feel, modals |

**Layered shadows** use 2-3 shadow layers per level:
- Ambient layer: Large blur, low opacity (environmental light)
- Key layer: Medium blur, medium opacity (directional light)
- Edge layer: Minimal blur, subtle (contact shadow)

## Output Formats

**CSS Custom Properties (Layered):**
```css
:root {
  --shadow-none: none;
  --shadow-xs:
    0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-sm:
    0 1px 3px 0 rgb(0 0 0 / 0.1),
    0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-md:
    0 4px 6px -1px rgb(0 0 0 / 0.1),
    0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg:
    0 10px 15px -3px rgb(0 0 0 / 0.1),
    0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl:
    0 20px 25px -5px rgb(0 0 0 / 0.1),
    0 8px 10px -6px rgb(0 0 0 / 0.1);
  --shadow-2xl:
    0 25px 50px -12px rgb(0 0 0 / 0.25);
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    boxShadow: {
      'none': 'none',
      'xs': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      'sm': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
      'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
      'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
      'xl': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
      '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    }
  }
}
```

**JSON Tokens:**
```json
{
  "shadow": {
    "none": { "value": "none" },
    "xs": { "value": "0 1px 2px 0 rgb(0 0 0 / 0.05)" },
    "sm": { "value": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)" },
    "md": { "value": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)" },
    "lg": { "value": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)" }
  }
}
```

## Algorithm Details

**Progression factors** (each level multiplies previous):
- Y-offset: ~2x per level
- Blur radius: ~1.5-2x per level
- Spread: Slightly negative (prevents harsh edges)
- Opacity: Increases slightly at higher levels

**Layered shadow formula:**
```
Level N:
  Ambient: 0 (N*4)px (N*6)px 0 rgb(0 0 0 / 0.04)
  Key:     0 (N*2)px (N*3)px -(N)px rgb(0 0 0 / 0.08)
```

## Dark Mode Considerations

Shadows are less visible on dark backgrounds. Options:

| Approach | How | When |
|----------|-----|------|
| Reduce opacity | Cut opacity 30-50% | Subtle dark UI |
| Add glow | Light color, outward spread | Neon/modern aesthetic |
| Ring highlight | Subtle light border + shadow | Card separation |
| Invert direction | Top-lit shadows | Unique style |

**Dark mode CSS example:**
```css
:root.dark {
  --shadow-md:
    0 4px 6px -1px rgb(0 0 0 / 0.3),
    0 0 0 1px rgb(255 255 255 / 0.05);
}
```

## Inset Shadows

For pressed states or inner depth:

```css
:root {
  --shadow-inner-sm: inset 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-inner-md: inset 0 2px 4px 0 rgb(0 0 0 / 0.1);
}
```
