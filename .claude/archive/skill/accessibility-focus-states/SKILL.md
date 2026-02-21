---
name: focus-states
description: Generates accessible focus indicators meeting WCAG 2.4.7 and 2.4.11 requirements. Use when styling :focus-visible, keyboard navigation indicators, or fixing focus ring visibility issues.
---

# Focus States Generator

## Overview

Generate accessible, visible focus indicators for interactive elements. Creates focus styles that meet WCAG 2.4.7 (Focus Visible) and 2.4.11 (Focus Appearance) requirements while maintaining visual design consistency.

## When to Use

- Setting up focus styles for a design system
- Ensuring keyboard navigation is visible
- Creating custom focus rings that match brand
- Fixing "invisible" focus states in existing UI

## Quick Reference: WCAG Requirements

| Criterion | Requirement | Level |
|-----------|-------------|-------|
| 2.4.7 Focus Visible | Focus indicator must be visible | AA |
| 2.4.11 Focus Appearance | 2px+ perimeter, 3:1 contrast | AAA |
| 2.4.12 Focus Not Obscured | Focus not hidden by other content | AA |

## The Process

1. **Get brand colors**: Primary color and background colors
2. **Ask style preference**:
   - Ring (outline around element)
   - Glow (soft shadow-based)
   - Underline (for text links)
   - Hybrid (ring + offset)
3. **Ask visibility approach**: Always visible or focus-visible only?
4. **Generate**: Create focus tokens and utility classes
5. **Test guidance**: Provide keyboard testing checklist

## Focus Style Options

| Style | Character | Best For |
|-------|-----------|----------|
| Ring | Clean, defined | Buttons, inputs, cards |
| Glow | Soft, modern | Dark themes, premium UI |
| Underline | Minimal | Text links, nav items |
| Offset | High contrast | When ring blends with element |
| Inset | Subtle | Contained elements |

## Output Formats

**CSS Custom Properties + Utilities:**
```css
:root {
  /* Focus tokens */
  --focus-ring-color: #2563eb;
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
  --focus-ring-style: solid;

  /* Computed focus ring */
  --focus-ring: var(--focus-ring-width) var(--focus-ring-style) var(--focus-ring-color);
  --focus-ring-offset-shadow: 0 0 0 var(--focus-ring-offset) var(--color-background);
  --focus-ring-shadow: 0 0 0 calc(var(--focus-ring-offset) + var(--focus-ring-width)) var(--focus-ring-color);
}

/* Base focus reset */
*:focus {
  outline: none;
}

/* Focus-visible for keyboard only */
*:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

/* Alternative: box-shadow approach (more styling control) */
.focus-ring:focus-visible {
  outline: none;
  box-shadow:
    var(--focus-ring-offset-shadow),
    var(--focus-ring-shadow);
}
```

**Component-Specific Focus:**
```css
/* Buttons */
.btn:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

/* Inputs - inset focus */
.input:focus-visible {
  outline: none;
  border-color: var(--focus-ring-color);
  box-shadow: 0 0 0 3px rgb(37 99 235 / 0.2);
}

/* Cards - offset ring */
.card:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 4px;
}

/* Links - underline enhancement */
a:focus-visible {
  outline: none;
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
  background-color: rgb(37 99 235 / 0.1);
  border-radius: 2px;
}

/* Skip link */
.skip-link:focus {
  position: fixed;
  top: 1rem;
  left: 1rem;
  z-index: 9999;
  padding: 1rem;
  background: var(--color-background);
  outline: 2px solid var(--focus-ring-color);
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    extend: {
      ringColor: {
        DEFAULT: '#2563eb',
      },
      ringWidth: {
        DEFAULT: '2px',
      },
      ringOffsetWidth: {
        DEFAULT: '2px',
      },
    }
  },
  plugins: [
    // Custom focus-visible variant
    plugin(function({ addVariant }) {
      addVariant('focus-visible-within', '&:has(:focus-visible)')
    })
  ]
}
```

**Tailwind Utilities:**
```html
<!-- Standard focus ring -->
<button class="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
  Button
</button>

<!-- Glow style -->
<button class="focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-500/30">
  Glow Button
</button>
```

**JSON Tokens:**
```json
{
  "focus": {
    "ring": {
      "color": { "value": "{color.primary.500}" },
      "width": { "value": "2px" },
      "offset": { "value": "2px" },
      "style": { "value": "solid" }
    },
    "glow": {
      "color": { "value": "{color.primary.500}" },
      "blur": { "value": "4px" },
      "spread": { "value": "2px" },
      "opacity": { "value": "0.3" }
    }
  }
}
```

## Dark Mode Focus

```css
/* Light mode */
:root {
  --focus-ring-color: #2563eb;
  --focus-ring-offset-color: #ffffff;
}

/* Dark mode - increase visibility */
:root.dark {
  --focus-ring-color: #60a5fa;
  --focus-ring-offset-color: #1f2937;
}
```

## Focus Indicator Contrast

WCAG 2.4.11 requires 3:1 contrast between:
1. Focus indicator and adjacent background
2. Focus indicator and the element itself

**Safe combinations:**
| Background | Focus Ring | Ratio |
|------------|------------|-------|
| White | #2563eb (blue-600) | 4.7:1 ✓ |
| Gray-100 | #1d4ed8 (blue-700) | 6.5:1 ✓ |
| Gray-900 | #60a5fa (blue-400) | 6.2:1 ✓ |
| Black | #93c5fd (blue-300) | 9.4:1 ✓ |

## Interactive States Order

Apply states in this specificity order:
```css
.element { }
.element:hover { }
.element:focus { }
.element:focus-visible { }  /* Keyboard only */
.element:active { }
.element:disabled { }
```

## Testing Checklist

- [ ] Tab through entire page - focus always visible
- [ ] Focus ring visible against all backgrounds
- [ ] Focus visible on buttons, links, inputs, selects
- [ ] Custom components (dropdowns, modals) receive focus
- [ ] Focus trapped in modals when open
- [ ] Skip link appears on first Tab press
- [ ] Focus returns to trigger when modal closes
- [ ] No focus on non-interactive elements
- [ ] Focus order matches visual order

## Common Fixes

**Focus disappears on click:**
```css
/* Use focus-visible, not focus */
button:focus-visible { outline: ... }
```

**Focus hidden behind sticky header:**
```css
:target { scroll-margin-top: 80px; }
*:focus { scroll-margin-top: 80px; }
```

**Focus invisible on element with background:**
```css
/* Add offset to create separation */
outline-offset: 2px;
/* Or use contrasting ring color */
```
