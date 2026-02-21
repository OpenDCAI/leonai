---
name: type-scale
description: Generates typography scales using modular ratios with auto-calculated line heights. Use when setting up font-size tokens, heading hierarchy (h1-h6), or text sizing systems. Outputs CSS, Tailwind, or JSON.
---

# Type Scale Generator

## Overview

Generate harmonious typography scales using musical interval ratios. Automatically calculates appropriate line heights based on font size for optimal readability.

## When to Use

- Setting up typography for a new project
- Creating heading hierarchy (h1-h6)
- Standardizing font sizes across components
- Building a responsive type system

## Quick Reference: Musical Ratios

| Name | Ratio | Character |
|------|-------|-----------|
| Minor Second | 1.067 | Subtle, tight |
| Major Second | 1.125 | Conservative |
| Minor Third | 1.2 | Versatile (recommended) |
| Major Third | 1.25 | Balanced |
| Perfect Fourth | 1.333 | Bold contrast |
| Augmented Fourth | 1.414 | Dramatic |
| Perfect Fifth | 1.5 | High contrast |
| Golden Ratio | 1.618 | Classical, striking |

## The Process

1. **Get base size**: Default 16px (browser default, good baseline)
2. **Choose ratio**: Recommend Minor Third (1.2) for most projects
3. **Steps up**: How many sizes above base (6-8 typical for headings)
4. **Steps down**: How many sizes below base (2-3 for small/caption text)
5. **Ask unit**: px, rem, or em?
6. **Ask format**: CSS, Tailwind, or JSON?
7. **Generate**: Create scale with auto line heights

## Auto Line Height

Larger fonts need tighter line height for readability:

| Font Size | Line Height | Reasoning |
|-----------|-------------|-----------|
| 14px or less | 1.7 | Small text needs room |
| 15-18px | 1.6 | Body text range |
| 19-24px | 1.5 | Large body/small headings |
| 25-32px | 1.4 | Subheadings |
| 33-48px | 1.3 | Headings |
| 49px+ | 1.2 | Display text |

## Output Formats

**CSS Custom Properties:**
```css
:root {
  /* Font Sizes */
  --text-xs: 13.33px;
  --text-sm: 14.22px;
  --text-base: 16px;
  --text-lg: 19.2px;
  --text-xl: 23.04px;
  --text-2xl: 27.65px;

  /* Line Heights */
  --leading-xs: 1.70;
  --leading-sm: 1.70;
  --leading-base: 1.60;
  --leading-lg: 1.50;
  --leading-xl: 1.50;
  --leading-2xl: 1.40;
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    fontSize: {
      'xs': ['13.33px', { lineHeight: '1.70' }],
      'sm': ['14.22px', { lineHeight: '1.70' }],
      'base': ['16px', { lineHeight: '1.60' }],
      'lg': ['19.2px', { lineHeight: '1.50' }],
      'xl': ['23.04px', { lineHeight: '1.50' }],
      '2xl': ['27.65px', { lineHeight: '1.40' }],
    }
  }
}
```

**JSON Tokens:**
```json
{
  "typography": {
    "xs": { "fontSize": "13.33px", "lineHeight": "1.70" },
    "sm": { "fontSize": "14.22px", "lineHeight": "1.70" },
    "base": { "fontSize": "16px", "lineHeight": "1.60" },
    "lg": { "fontSize": "19.2px", "lineHeight": "1.50" }
  }
}
```

## Naming Convention

| Position | Name |
|----------|------|
| 3 below base | xxs |
| 2 below base | xs |
| 1 below base | sm |
| Base | base |
| 1 above base | lg |
| 2 above base | xl |
| 3+ above base | 2xl, 3xl, 4xl... |

## Common Configurations

**Compact UI** (dashboards, data-dense):
- Ratio: 1.125 (Major Second)
- Base: 14px
- Steps: 2 down, 5 up

**Content Site** (blogs, marketing):
- Ratio: 1.25 (Major Third)
- Base: 18px
- Steps: 2 down, 6 up

**Editorial** (magazines, long-form):
- Ratio: 1.333 (Perfect Fourth)
- Base: 20px
- Steps: 2 down, 8 up
