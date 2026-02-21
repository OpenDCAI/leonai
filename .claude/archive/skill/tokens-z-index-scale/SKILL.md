---
name: z-index-scale
description: Generates systematic z-index tokens for layering management. Use when organizing stacking contexts, modal/dropdown z-index, tooltip layers, or fixing z-index conflicts. Outputs CSS, Tailwind, or JSON.
---

# Z-Index Scale

## Overview

Generate a systematic z-index token scale that eliminates arbitrary values and z-index conflicts. Creates predictable layering for dropdowns, modals, tooltips, and overlays.

## When to Use

- Setting up z-index tokens for a new design system
- Fixing z-index conflicts and "wars" in existing code
- Creating consistent layering for overlays, modals, tooltips
- Documenting stacking context expectations

## Quick Reference: Layering Levels

| Level | Purpose | Typical Range |
|-------|---------|---------------|
| Base | Default content flow | 0 |
| Raised | Cards, subtle elevation | 1-10 |
| Dropdown | Menus, selects, popovers | 100-199 |
| Sticky | Sticky headers, sidebars | 200-299 |
| Fixed | Fixed navigation, FABs | 300-399 |
| Overlay | Backdrop, dimmer | 400-499 |
| Modal | Dialogs, sheets | 500-599 |
| Toast | Notifications, snackbars | 600-699 |
| Tooltip | Tooltips, hovers | 700-799 |
| Maximum | Debug overlays, dev tools | 9999 |

## The Process

1. **Understand stacking needs**: Identify all layered components in the system
2. **Ask output format**: CSS custom properties, Tailwind config, or JSON tokens
3. **Generate scale**: Create tokens with semantic naming
4. **Document usage**: Explain which token for which use case

## Output Formats

### CSS Custom Properties

```css
:root {
  /* Base - default document flow */
  --z-index-base: 0;
  --z-index-below: -1;

  /* Raised - subtle elevation within content */
  --z-index-raised: 1;
  --z-index-raised-2: 2;
  --z-index-raised-3: 3;

  /* Dropdown - menus, selects, comboboxes, popovers */
  --z-index-dropdown: 100;

  /* Sticky - sticky positioned elements */
  --z-index-sticky: 200;

  /* Fixed - fixed navigation, floating action buttons */
  --z-index-fixed: 300;
  --z-index-header: 310;
  --z-index-sidebar: 320;

  /* Overlay - backdrop behind modals */
  --z-index-overlay: 400;

  /* Modal - dialogs, sheets, drawers */
  --z-index-modal: 500;
  --z-index-modal-content: 510;

  /* Toast - notifications, snackbars */
  --z-index-toast: 600;

  /* Tooltip - tooltips, title attributes */
  --z-index-tooltip: 700;

  /* Maximum - debug, dev tools (avoid in production) */
  --z-index-max: 9999;
}
```

### Tailwind Config

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      zIndex: {
        'below': '-1',
        'base': '0',
        'raised': '1',
        'raised-2': '2',
        'raised-3': '3',
        'dropdown': '100',
        'sticky': '200',
        'fixed': '300',
        'header': '310',
        'sidebar': '320',
        'overlay': '400',
        'modal': '500',
        'modal-content': '510',
        'toast': '600',
        'tooltip': '700',
        'max': '9999',
      },
    },
  },
};
```

**Usage:**
```html
<div class="z-overlay">Backdrop</div>
<div class="z-modal">Modal content</div>
<div class="z-tooltip">Tooltip</div>
```

### JSON Tokens (Design Tokens Format)

```json
{
  "z-index": {
    "below": { "value": -1, "description": "Below base content" },
    "base": { "value": 0, "description": "Default document flow" },
    "raised": {
      "1": { "value": 1, "description": "Subtle elevation" },
      "2": { "value": 2, "description": "Medium elevation" },
      "3": { "value": 3, "description": "High elevation" }
    },
    "dropdown": { "value": 100, "description": "Menus, selects, popovers" },
    "sticky": { "value": 200, "description": "Sticky positioned elements" },
    "fixed": {
      "base": { "value": 300, "description": "Fixed elements" },
      "header": { "value": 310, "description": "Fixed header" },
      "sidebar": { "value": 320, "description": "Fixed sidebar" }
    },
    "overlay": { "value": 400, "description": "Backdrop behind modals" },
    "modal": {
      "base": { "value": 500, "description": "Modal container" },
      "content": { "value": 510, "description": "Modal inner content" }
    },
    "toast": { "value": 600, "description": "Notifications, snackbars" },
    "tooltip": { "value": 700, "description": "Tooltips" },
    "max": { "value": 9999, "description": "Maximum (debug only)" }
  }
}
```

---

## Stacking Context Concepts

### What Creates a New Stacking Context

Understanding stacking contexts prevents unexpected z-index behavior:

```css
/* These properties create new stacking contexts */
.creates-context {
  /* Any of these: */
  position: relative; z-index: 1; /* positioned + z-index */
  position: fixed;                 /* fixed positioning */
  position: sticky;                /* sticky positioning */
  opacity: 0.99;                   /* opacity < 1 */
  transform: translateZ(0);        /* any transform */
  filter: blur(0);                 /* any filter */
  isolation: isolate;              /* explicit isolation */
  contain: layout;                 /* containment */
  will-change: transform;          /* will-change hint */
}
```

### Isolation Pattern

Use `isolation: isolate` to contain z-index within a component:

```css
/* Component creates its own stacking context */
.card {
  isolation: isolate;
}

/* Internal z-index stays within the card */
.card__overlay {
  z-index: 1; /* Only relative to .card, not page */
}

.card__content {
  z-index: 2;
}
```

---

## Component Patterns

### Modal with Backdrop

```css
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-index-overlay);
  background: rgb(0 0 0 / 0.5);
}

.modal {
  position: fixed;
  z-index: var(--z-index-modal);
  /* centering styles */
}

/* Nested modal (rare but possible) */
.modal--nested {
  z-index: calc(var(--z-index-modal) + 10);
}
```

### Dropdown in Fixed Header

```css
.header {
  position: fixed;
  top: 0;
  z-index: var(--z-index-header);
  isolation: isolate; /* Contain dropdown z-index */
}

.header__dropdown {
  position: absolute;
  z-index: var(--z-index-dropdown);
}
```

### Toast Notifications

```css
.toast-container {
  position: fixed;
  bottom: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: var(--z-index-toast);

  /* Stack toasts */
  display: flex;
  flex-direction: column-reverse;
  gap: var(--spacing-sm);
}
```

### Tooltip

```css
.tooltip {
  position: absolute;
  z-index: var(--z-index-tooltip);
  /* Always on top, even over modals */
}
```

---

## Common Patterns

### Progressive Scale

For simple projects, use powers of 10:

```css
:root {
  --z-dropdown: 10;
  --z-sticky: 20;
  --z-fixed: 30;
  --z-modal: 40;
  --z-toast: 50;
  --z-tooltip: 60;
}
```

### Hundred-Based Scale

For complex apps needing sub-levels:

```css
:root {
  --z-dropdown: 100;
  --z-dropdown-nested: 110;
  --z-sticky: 200;
  --z-modal: 500;
  --z-modal-nested: 510;
}
```

### Named Layers (CSS Cascade Layers)

Modern alternative using `@layer`:

```css
@layer base, components, overlays, modals, notifications;

@layer overlays {
  .dropdown { /* Automatically layered */ }
}

@layer modals {
  .modal { /* Higher than overlays */ }
}
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| `z-index: 99999` | Arms race, unmaintainable | Use semantic tokens |
| Random values | No system, conflicts | Follow scale consistently |
| Inline z-index | Hard to debug | Use CSS custom properties |
| Everything high | Defeats layering purpose | Start low, only elevate as needed |
| No isolation | Components affect each other | Use `isolation: isolate` |

---

## Debugging Z-Index Issues

### Browser DevTools

1. Elements panel → Computed → search "z-index"
2. 3D View (Chrome) → Shows stacking visually
3. Check if parent creates stacking context

### Debug Utility

```css
/* Temporarily visualize z-index layers */
[style*="z-index"] {
  outline: 2px solid red !important;
}

[style*="z-index"]::after {
  content: attr(style);
  position: absolute;
  background: red;
  color: white;
  font-size: 10px;
  padding: 2px;
}
```

### Common Fixes

```css
/* Problem: z-index not working */
.element {
  z-index: 100; /* Won't work without positioning */
}

/* Fix: Add positioning */
.element {
  position: relative; /* or absolute/fixed */
  z-index: 100;
}

/* Problem: Child higher than parent's sibling */
/* Fix: Use isolation on parent */
.parent {
  isolation: isolate;
}
```

---

## Integration with Other Tokens

```css
:root {
  /* Z-index works with shadows for elevation */
  --elevation-1: var(--z-index-raised), var(--shadow-sm);
  --elevation-2: var(--z-index-dropdown), var(--shadow-md);
  --elevation-3: var(--z-index-modal), var(--shadow-lg);
}

/* Usage */
.card {
  z-index: var(--z-index-raised);
  box-shadow: var(--shadow-sm);
}
```
