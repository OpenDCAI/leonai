---
name: breakpoints
description: Generates responsive breakpoint tokens for media queries and container queries. Use when setting up responsive design, mobile-first layouts, or viewport-based styling. Outputs CSS, Tailwind, or JSON.
---

# Breakpoints Generator

## Overview

Generate consistent responsive breakpoint tokens for mobile-first or desktop-first design. Includes common device-based presets and custom configuration options.

## When to Use

- Setting up responsive design tokens
- Standardizing media queries across a project
- Creating container query breakpoints
- Migrating from arbitrary breakpoints to tokens

## Quick Reference: Common Breakpoints

| Name | Min Width | Target Devices |
|------|-----------|----------------|
| xs | 0 | Small phones |
| sm | 640px | Large phones, small tablets |
| md | 768px | Tablets portrait |
| lg | 1024px | Tablets landscape, laptops |
| xl | 1280px | Desktops |
| 2xl | 1536px | Large desktops |

## The Process

1. **Ask approach**: Mobile-first (min-width) or desktop-first (max-width)?
2. **Ask preset or custom**:
   - Preset: Tailwind, Bootstrap, Material, or Custom
   - Custom: Define your own values
3. **Ask steps**: How many breakpoints (4-6 typical)
4. **Ask container queries**: Include container query tokens?
5. **Ask format**: CSS, Tailwind, JSON, or SCSS?
6. **Generate**: Create breakpoint scale with media query helpers

## Breakpoint Presets

| Preset | Values | Character |
|--------|--------|-----------|
| Tailwind | 640, 768, 1024, 1280, 1536 | Content-focused |
| Bootstrap | 576, 768, 992, 1200, 1400 | Traditional |
| Material | 600, 905, 1240, 1440 | Google spec |
| Minimal | 640, 1024, 1440 | Simple 3-tier |

## Output Formats

**CSS Custom Properties + Media Queries:**
```css
:root {
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
}

/* Mobile-first media queries (use with @media) */
/* @media (min-width: 640px) - sm and up */
/* @media (min-width: 768px) - md and up */
/* @media (min-width: 1024px) - lg and up */
/* @media (min-width: 1280px) - xl and up */
/* @media (min-width: 1536px) - 2xl and up */
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    }
  }
}
```

**JSON Tokens:**
```json
{
  "breakpoint": {
    "sm": { "value": "640px", "type": "dimension" },
    "md": { "value": "768px", "type": "dimension" },
    "lg": { "value": "1024px", "type": "dimension" },
    "xl": { "value": "1280px", "type": "dimension" },
    "2xl": { "value": "1536px", "type": "dimension" }
  }
}
```

**SCSS Variables + Mixins:**
```scss
$breakpoint-sm: 640px;
$breakpoint-md: 768px;
$breakpoint-lg: 1024px;
$breakpoint-xl: 1280px;
$breakpoint-2xl: 1536px;

@mixin sm-up {
  @media (min-width: $breakpoint-sm) { @content; }
}
@mixin md-up {
  @media (min-width: $breakpoint-md) { @content; }
}
@mixin lg-up {
  @media (min-width: $breakpoint-lg) { @content; }
}
@mixin xl-up {
  @media (min-width: $breakpoint-xl) { @content; }
}
@mixin 2xl-up {
  @media (min-width: $breakpoint-2xl) { @content; }
}

// Usage: @include md-up { .element { width: 50%; } }
```

## Container Queries

Modern CSS container queries for component-level responsiveness:

```css
/* Container query breakpoints */
:root {
  --container-sm: 320px;
  --container-md: 480px;
  --container-lg: 640px;
  --container-xl: 800px;
}

/* Define container */
.card-container {
  container-type: inline-size;
  container-name: card;
}

/* Query container */
@container card (min-width: 480px) {
  .card-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
```

## Mobile-First vs Desktop-First

| Approach | Media Query | Write Styles For |
|----------|-------------|------------------|
| Mobile-first | `min-width` | Small screens first, enhance up |
| Desktop-first | `max-width` | Large screens first, reduce down |

**Mobile-first** (recommended):
```css
.element { width: 100%; }
@media (min-width: 768px) { .element { width: 50%; } }
@media (min-width: 1024px) { .element { width: 33%; } }
```

**Desktop-first**:
```css
.element { width: 33%; }
@media (max-width: 1023px) { .element { width: 50%; } }
@media (max-width: 767px) { .element { width: 100%; } }
```

## Best Practices

1. **Content-driven breakpoints**: Let content determine where layout breaks, not device sizes
2. **Fewer is better**: 4-6 breakpoints handles most cases
3. **Test in-between**: Don't just test at exact breakpoints
4. **Use container queries** for component-level responsiveness
5. **Avoid pixel-perfect**: Focus on fluid layouts between breakpoints

## Utility Classes (Tailwind-style)

```css
/* Visibility utilities */
.hidden { display: none; }
.sm\:block { @media (min-width: 640px) { display: block; } }
.md\:hidden { @media (min-width: 768px) { display: none; } }

/* Responsive grid */
.grid-cols-1 { grid-template-columns: 1fr; }
.md\:grid-cols-2 { @media (min-width: 768px) { grid-template-columns: repeat(2, 1fr); } }
.lg\:grid-cols-3 { @media (min-width: 1024px) { grid-template-columns: repeat(3, 1fr); } }
```
