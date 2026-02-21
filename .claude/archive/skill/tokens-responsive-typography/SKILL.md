---
name: responsive-typography
description: Implements fluid typography using CSS clamp() that scales with viewport. Use when creating responsive font sizes, viewport-aware headings, or type that adapts smoothly without breakpoints.
---

# Responsive Typography

## Overview

Implement fluid typography that scales smoothly between viewport sizes without breakpoints. Uses CSS `clamp()` to create type that's readable on mobile and properly sized on desktop, eliminating abrupt size jumps.

## When to Use

- Creating typography that scales with viewport
- Avoiding multiple breakpoint-based font sizes
- Implementing fluid/responsive headings
- Setting up a fluid type scale for a design system

## Quick Reference: Clamp Syntax

```css
/* clamp(minimum, preferred, maximum) */
font-size: clamp(1rem, 2.5vw + 0.5rem, 2rem);
/*         ↑min    ↑scales with vw    ↑max */
```

| Part | Purpose |
|------|---------|
| Minimum | Smallest the text will ever be |
| Preferred | Scales with viewport (uses vw) |
| Maximum | Largest the text will ever be |

---

## The Math

### Fluid Type Formula

```
preferred = (slope × viewport) + intercept

Where:
- slope = (maxSize - minSize) / (maxViewport - minViewport)
- intercept = minSize - (slope × minViewport)
```

### Example Calculation

For text that's 16px at 320px viewport and 20px at 1200px viewport:

```
slope = (20 - 16) / (1200 - 320) = 4 / 880 = 0.00454545
intercept = 16 - (0.00454545 × 320) = 14.545px

preferred = 0.454545vw + 14.545px
→ Convert to rem: 0.454545vw + 0.909rem

Result: clamp(1rem, 0.45vw + 0.91rem, 1.25rem)
```

---

## Fluid Type Scale

### CSS Custom Properties

```css
:root {
  /* Fluid type scale
   * Min viewport: 320px
   * Max viewport: 1200px
   */

  /* Body text */
  --font-size-sm: clamp(0.8rem, 0.17vw + 0.76rem, 0.875rem);
  --font-size-base: clamp(1rem, 0.34vw + 0.91rem, 1.125rem);
  --font-size-lg: clamp(1.125rem, 0.45vw + 1.01rem, 1.25rem);

  /* Headings */
  --font-size-xl: clamp(1.25rem, 0.91vw + 1.07rem, 1.5rem);
  --font-size-2xl: clamp(1.5rem, 1.36vw + 1.23rem, 1.875rem);
  --font-size-3xl: clamp(1.875rem, 1.82vw + 1.51rem, 2.25rem);
  --font-size-4xl: clamp(2.25rem, 2.73vw + 1.7rem, 3rem);
  --font-size-5xl: clamp(3rem, 4.55vw + 2.09rem, 4rem);

  /* Display */
  --font-size-display: clamp(3rem, 6.82vw + 1.64rem, 5rem);
}
```

### Tailwind Config

```js
// tailwind.config.js
module.exports = {
  theme: {
    fontSize: {
      'sm': 'clamp(0.8rem, 0.17vw + 0.76rem, 0.875rem)',
      'base': 'clamp(1rem, 0.34vw + 0.91rem, 1.125rem)',
      'lg': 'clamp(1.125rem, 0.45vw + 1.01rem, 1.25rem)',
      'xl': 'clamp(1.25rem, 0.91vw + 1.07rem, 1.5rem)',
      '2xl': 'clamp(1.5rem, 1.36vw + 1.23rem, 1.875rem)',
      '3xl': 'clamp(1.875rem, 1.82vw + 1.51rem, 2.25rem)',
      '4xl': 'clamp(2.25rem, 2.73vw + 1.7rem, 3rem)',
      '5xl': 'clamp(3rem, 4.55vw + 2.09rem, 4rem)',
      'display': 'clamp(3rem, 6.82vw + 1.64rem, 5rem)',
    },
  },
};
```

### JSON Tokens

```json
{
  "font": {
    "size": {
      "fluid": {
        "sm": {
          "value": "clamp(0.8rem, 0.17vw + 0.76rem, 0.875rem)",
          "min": "0.8rem",
          "max": "0.875rem"
        },
        "base": {
          "value": "clamp(1rem, 0.34vw + 0.91rem, 1.125rem)",
          "min": "1rem",
          "max": "1.125rem"
        },
        "lg": {
          "value": "clamp(1.125rem, 0.45vw + 1.01rem, 1.25rem)",
          "min": "1.125rem",
          "max": "1.25rem"
        },
        "xl": {
          "value": "clamp(1.25rem, 0.91vw + 1.07rem, 1.5rem)",
          "min": "1.25rem",
          "max": "1.5rem"
        },
        "2xl": {
          "value": "clamp(1.5rem, 1.36vw + 1.23rem, 1.875rem)",
          "min": "1.5rem",
          "max": "1.875rem"
        },
        "3xl": {
          "value": "clamp(1.875rem, 1.82vw + 1.51rem, 2.25rem)",
          "min": "1.875rem",
          "max": "2.25rem"
        },
        "4xl": {
          "value": "clamp(2.25rem, 2.73vw + 1.7rem, 3rem)",
          "min": "2.25rem",
          "max": "3rem"
        },
        "5xl": {
          "value": "clamp(3rem, 4.55vw + 2.09rem, 4rem)",
          "min": "3rem",
          "max": "4rem"
        }
      }
    }
  }
}
```

---

## Fluid Scale Generator

### JavaScript Function

```js
/**
 * Generate a fluid font-size clamp value
 *
 * @param {number} minSize - Minimum size in px
 * @param {number} maxSize - Maximum size in px
 * @param {number} minVw - Minimum viewport in px (default: 320)
 * @param {number} maxVw - Maximum viewport in px (default: 1200)
 * @returns {string} CSS clamp() value
 */
function fluidType(minSize, maxSize, minVw = 320, maxVw = 1200) {
  const minSizeRem = minSize / 16;
  const maxSizeRem = maxSize / 16;

  const slope = (maxSize - minSize) / (maxVw - minVw);
  const slopeVw = (slope * 100).toFixed(2);

  const intercept = minSize - slope * minVw;
  const interceptRem = (intercept / 16).toFixed(2);

  return `clamp(${minSizeRem}rem, ${slopeVw}vw + ${interceptRem}rem, ${maxSizeRem}rem)`;
}

// Usage
fluidType(16, 20);  // "clamp(1rem, 0.45vw + 0.91rem, 1.25rem)"
fluidType(24, 48);  // "clamp(1.5rem, 2.73vw + 0.95rem, 3rem)"
```

### Generate Full Scale

```js
const scale = {
  sm: fluidType(12.8, 14),
  base: fluidType(16, 18),
  lg: fluidType(18, 20),
  xl: fluidType(20, 24),
  '2xl': fluidType(24, 30),
  '3xl': fluidType(30, 36),
  '4xl': fluidType(36, 48),
  '5xl': fluidType(48, 64),
};
```

---

## Predefined Scales

### Conservative Scale (Subtle)

Minimal scaling - good for content-heavy sites.

```css
:root {
  /* Min: 320px, Max: 1200px */
  /* Ratio: 1.125 minor second at mobile, 1.2 minor third at desktop */

  --fs-xs: clamp(0.75rem, 0.11vw + 0.73rem, 0.8rem);
  --fs-sm: clamp(0.875rem, 0.11vw + 0.85rem, 0.9375rem);
  --fs-base: clamp(1rem, 0.23vw + 0.95rem, 1.0625rem);
  --fs-lg: clamp(1.125rem, 0.34vw + 1.06rem, 1.25rem);
  --fs-xl: clamp(1.25rem, 0.57vw + 1.14rem, 1.5rem);
  --fs-2xl: clamp(1.5rem, 0.91vw + 1.32rem, 1.875rem);
  --fs-3xl: clamp(1.875rem, 1.36vw + 1.6rem, 2.25rem);
}
```

### Expressive Scale (Bold)

More dramatic scaling - good for marketing/landing pages.

```css
:root {
  /* Min: 320px, Max: 1200px */
  /* Ratio: 1.2 minor third at mobile, 1.333 perfect fourth at desktop */

  --fs-xs: clamp(0.75rem, 0.23vw + 0.7rem, 0.875rem);
  --fs-sm: clamp(0.875rem, 0.34vw + 0.81rem, 1rem);
  --fs-base: clamp(1rem, 0.45vw + 0.91rem, 1.125rem);
  --fs-lg: clamp(1.2rem, 0.91vw + 1.02rem, 1.5rem);
  --fs-xl: clamp(1.44rem, 1.59vw + 1.12rem, 2rem);
  --fs-2xl: clamp(1.728rem, 2.5vw + 1.23rem, 2.665rem);
  --fs-3xl: clamp(2.074rem, 3.64vw + 1.35rem, 3.553rem);
  --fs-4xl: clamp(2.488rem, 5.11vw + 1.47rem, 4.736rem);
}
```

---

## Usage Patterns

### Headlines

```css
h1 { font-size: var(--font-size-4xl); }
h2 { font-size: var(--font-size-3xl); }
h3 { font-size: var(--font-size-2xl); }
h4 { font-size: var(--font-size-xl); }
h5 { font-size: var(--font-size-lg); }
h6 { font-size: var(--font-size-base); }
```

### Body Text

```css
body {
  font-size: var(--font-size-base);
  line-height: 1.5;
}

.small {
  font-size: var(--font-size-sm);
}

.large {
  font-size: var(--font-size-lg);
}
```

### Hero Sections

```css
.hero-title {
  font-size: var(--font-size-display);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.hero-subtitle {
  font-size: var(--font-size-xl);
  line-height: 1.4;
}
```

---

## Fluid Line Height

Line height can also scale for better readability:

```css
:root {
  /* Tighter line height on larger text */
  --line-height-tight: clamp(1.1, 1.5 - 0.25vw, 1.2);
  --line-height-normal: clamp(1.4, 1.7 - 0.2vw, 1.5);
  --line-height-relaxed: clamp(1.6, 1.9 - 0.2vw, 1.75);
}

h1, h2 {
  line-height: var(--line-height-tight);
}

p {
  line-height: var(--line-height-normal);
}
```

---

## Fluid Spacing (Related)

Apply the same principle to spacing:

```css
:root {
  /* Fluid spacing */
  --space-xs: clamp(0.25rem, 0.5vw, 0.5rem);
  --space-sm: clamp(0.5rem, 1vw, 1rem);
  --space-md: clamp(1rem, 2vw, 2rem);
  --space-lg: clamp(1.5rem, 3vw, 3rem);
  --space-xl: clamp(2rem, 5vw, 5rem);
  --space-2xl: clamp(3rem, 8vw, 8rem);
}

/* Section spacing scales with viewport */
section {
  padding-block: var(--space-xl);
}

/* Container padding */
.container {
  padding-inline: var(--space-md);
}
```

---

## Container Query Typography

For component-based fluid type (modern browsers):

```css
/* Container context */
.card {
  container-type: inline-size;
}

/* Scale based on container, not viewport */
.card-title {
  font-size: clamp(1rem, 3cqi + 0.5rem, 1.5rem);
}

@container (min-width: 400px) {
  .card-title {
    font-size: clamp(1.25rem, 4cqi + 0.5rem, 2rem);
  }
}
```

---

## Accessibility Considerations

### Respect User Preferences

```css
/* Scale from user's preferred size, not fixed 16px */
:root {
  /* Use rem, never px for font sizes */
  font-size: 100%; /* Respects browser default */
}

/* Zoom-friendly: content reflows properly */
@media (min-width: 320px) {
  /* Fluid values handle this automatically */
}
```

### Text Zoom Test

Ensure text remains readable when zoomed to 200%:

```css
/* Avoid cutting off text at max sizes */
.hero-title {
  font-size: clamp(2rem, 5vw + 1rem, 4rem);
  /* At 200% zoom: 4rem × 2 = 8rem - still proportional */
}
```

### Minimum Readable Size

Never go below 16px (1rem) for body text:

```css
/* Body text minimum */
--font-size-base: clamp(1rem, 0.34vw + 0.91rem, 1.125rem);
/*                     ↑ Never smaller than 1rem */

/* Small text minimum */
--font-size-sm: clamp(0.875rem, 0.17vw + 0.83rem, 0.9375rem);
/*                    ↑ 14px minimum for secondary text */
```

---

## Tools & Resources

### Online Calculators

- **Utopia**: https://utopia.fyi/type/calculator
- **Modern Fluid Typography**: https://modern-fluid-typography.vercel.app
- **Fluid Type Scale**: https://www.fluid-type-scale.com

### PostCSS Plugin

```js
// postcss.config.js
module.exports = {
  plugins: [
    require('postcss-utopia')({
      minWidth: 320,
      maxWidth: 1240,
      minFontSize: 16,
      maxFontSize: 18,
      minTypeScale: 1.2,
      maxTypeScale: 1.25,
    }),
  ],
};
```

---

## Common Mistakes

| Mistake | Problem | Solution |
|---------|---------|----------|
| Using px in clamp | Doesn't respect user preferences | Always use rem |
| Min > Max | Invalid, browser ignores | Ensure min < max |
| No max | Text grows infinitely | Always set maximum |
| vw only | Too small on mobile | Add rem offset |
| Too aggressive scaling | Jarring at extremes | Limit slope |

---

## Browser Support

`clamp()` is supported in all modern browsers (Chrome 79+, Firefox 75+, Safari 13.1+, Edge 79+).

For older browsers:

```css
/* Fallback with media queries */
.heading {
  font-size: 2rem; /* Fallback */
  font-size: clamp(1.5rem, 2vw + 1rem, 2.5rem);
}

/* Or use @supports */
@supports not (font-size: clamp(1rem, 1vw, 2rem)) {
  .heading {
    font-size: 2rem;
  }
}
```
