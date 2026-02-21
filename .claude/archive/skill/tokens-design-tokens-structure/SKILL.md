---
name: design-tokens-structure
description: Architects token systems with primitive, semantic, and component layers. Use when structuring tokens from scratch, adding multi-theme support, setting up token aliasing, or organizing token hierarchies.
---

# Design Tokens Structure

## Overview

Establish the architectural foundation for a scalable design token system. Defines the three-layer token hierarchy (primitive → semantic → component) that enables theming, multi-brand support, and maintainable design systems.

## When to Use

- Starting a new design system from scratch
- Restructuring an existing token system
- Adding multi-theme or multi-brand support
- Converting hardcoded values to tokens
- Creating a token governance strategy

### Implementation Checklist

Copy this checklist when architecting a token system:

```
Token Architecture Setup:
- [ ] Audit existing values and establish naming conventions
- [ ] Define primitive tokens (raw values, context-free)
- [ ] Define semantic tokens (purpose-based, reference primitives)
- [ ] Create theme overrides (dark.json, brand variants)
- [ ] Add component tokens for complex stateful components
- [ ] Configure build output (CSS variables, Tailwind, JSON)
```

## Quick Reference: Token Layers

| Layer | Also Called | Purpose | Example |
|-------|-------------|---------|---------|
| Primitive | Core, Base, Global | Raw values, context-free | `blue-500: #3b82f6` |
| Semantic | Alias, Purpose, Role | Meaning-based references | `color-primary: {blue-500}` |
| Component | Specific, Local | Component-scoped tokens | `button-bg: {color-primary}` |

## The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    COMPONENT TOKENS                      │
│        button-bg, card-border, input-focus-ring          │
│                         ↓ references                     │
├─────────────────────────────────────────────────────────┤
│                    SEMANTIC TOKENS                       │
│       color-primary, color-bg-surface, spacing-page      │
│                         ↓ references                     │
├─────────────────────────────────────────────────────────┤
│                    PRIMITIVE TOKENS                      │
│         blue-500, gray-100, spacing-16, radius-8         │
│                    (raw values only)                     │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: Primitive Tokens

Raw design values with no semantic meaning. These are the building blocks.

### Characteristics
- Context-free (no "primary", "background", etc.)
- Named by their intrinsic property (color: hue, spacing: size)
- Never change between themes
- Comprehensive palette of options

### Structure

```json
{
  "primitive": {
    "color": {
      "gray": {
        "50": { "value": "#f9fafb" },
        "100": { "value": "#f3f4f6" },
        "200": { "value": "#e5e7eb" },
        "300": { "value": "#d1d5db" },
        "400": { "value": "#9ca3af" },
        "500": { "value": "#6b7280" },
        "600": { "value": "#4b5563" },
        "700": { "value": "#374151" },
        "800": { "value": "#1f2937" },
        "900": { "value": "#111827" },
        "950": { "value": "#030712" }
      },
      "blue": {
        "50": { "value": "#eff6ff" },
        "100": { "value": "#dbeafe" },
        "200": { "value": "#bfdbfe" },
        "300": { "value": "#93c5fd" },
        "400": { "value": "#60a5fa" },
        "500": { "value": "#3b82f6" },
        "600": { "value": "#2563eb" },
        "700": { "value": "#1d4ed8" },
        "800": { "value": "#1e40af" },
        "900": { "value": "#1e3a8a" }
      },
      "green": { /* success colors */ },
      "red": { /* error colors */ },
      "amber": { /* warning colors */ }
    },
    "spacing": {
      "0": { "value": "0" },
      "1": { "value": "0.25rem" },
      "2": { "value": "0.5rem" },
      "3": { "value": "0.75rem" },
      "4": { "value": "1rem" },
      "5": { "value": "1.25rem" },
      "6": { "value": "1.5rem" },
      "8": { "value": "2rem" },
      "10": { "value": "2.5rem" },
      "12": { "value": "3rem" },
      "16": { "value": "4rem" },
      "20": { "value": "5rem" },
      "24": { "value": "6rem" }
    },
    "radius": {
      "none": { "value": "0" },
      "sm": { "value": "0.125rem" },
      "md": { "value": "0.375rem" },
      "lg": { "value": "0.5rem" },
      "xl": { "value": "0.75rem" },
      "2xl": { "value": "1rem" },
      "full": { "value": "9999px" }
    },
    "font": {
      "family": {
        "sans": { "value": "Inter, system-ui, sans-serif" },
        "mono": { "value": "JetBrains Mono, monospace" }
      },
      "size": {
        "xs": { "value": "0.75rem" },
        "sm": { "value": "0.875rem" },
        "md": { "value": "1rem" },
        "lg": { "value": "1.125rem" },
        "xl": { "value": "1.25rem" },
        "2xl": { "value": "1.5rem" },
        "3xl": { "value": "1.875rem" },
        "4xl": { "value": "2.25rem" }
      },
      "weight": {
        "normal": { "value": "400" },
        "medium": { "value": "500" },
        "semibold": { "value": "600" },
        "bold": { "value": "700" }
      }
    }
  }
}
```

---

## Layer 2: Semantic Tokens

Purpose-based tokens that reference primitives. These tokens change between themes.

### Characteristics
- Named by purpose/role, not appearance
- Reference primitive tokens only
- The only layer that changes per theme
- Describe "what for", not "what it looks like"

### Structure

```json
{
  "semantic": {
    "color": {
      "bg": {
        "primary": { "value": "{primitive.color.gray.50}" },
        "secondary": { "value": "{primitive.color.gray.100}" },
        "tertiary": { "value": "{primitive.color.gray.200}" },
        "inverse": { "value": "{primitive.color.gray.900}" },
        "brand": { "value": "{primitive.color.blue.500}" }
      },
      "text": {
        "primary": { "value": "{primitive.color.gray.900}" },
        "secondary": { "value": "{primitive.color.gray.600}" },
        "tertiary": { "value": "{primitive.color.gray.500}" },
        "inverse": { "value": "{primitive.color.gray.50}" },
        "brand": { "value": "{primitive.color.blue.600}" },
        "link": { "value": "{primitive.color.blue.600}" }
      },
      "border": {
        "primary": { "value": "{primitive.color.gray.200}" },
        "secondary": { "value": "{primitive.color.gray.300}" },
        "focus": { "value": "{primitive.color.blue.500}" }
      },
      "status": {
        "success": { "value": "{primitive.color.green.500}" },
        "warning": { "value": "{primitive.color.amber.500}" },
        "error": { "value": "{primitive.color.red.500}" },
        "info": { "value": "{primitive.color.blue.500}" }
      },
      "interactive": {
        "primary": { "value": "{primitive.color.blue.500}" },
        "primary-hover": { "value": "{primitive.color.blue.600}" },
        "primary-active": { "value": "{primitive.color.blue.700}" },
        "secondary": { "value": "{primitive.color.gray.100}" },
        "secondary-hover": { "value": "{primitive.color.gray.200}" }
      }
    },
    "spacing": {
      "page": { "value": "{primitive.spacing.6}" },
      "section": { "value": "{primitive.spacing.12}" },
      "element": { "value": "{primitive.spacing.4}" },
      "inline": { "value": "{primitive.spacing.2}" }
    },
    "radius": {
      "interactive": { "value": "{primitive.radius.md}" },
      "container": { "value": "{primitive.radius.lg}" },
      "pill": { "value": "{primitive.radius.full}" }
    }
  }
}
```

### Dark Theme Override

```json
{
  "semantic": {
    "color": {
      "bg": {
        "primary": { "value": "{primitive.color.gray.950}" },
        "secondary": { "value": "{primitive.color.gray.900}" },
        "tertiary": { "value": "{primitive.color.gray.800}" },
        "inverse": { "value": "{primitive.color.gray.50}" }
      },
      "text": {
        "primary": { "value": "{primitive.color.gray.50}" },
        "secondary": { "value": "{primitive.color.gray.400}" },
        "tertiary": { "value": "{primitive.color.gray.500}" },
        "inverse": { "value": "{primitive.color.gray.900}" }
      },
      "border": {
        "primary": { "value": "{primitive.color.gray.800}" },
        "secondary": { "value": "{primitive.color.gray.700}" }
      }
    }
  }
}
```

---

## Layer 3: Component Tokens

Component-specific tokens that reference semantic tokens. Optional but powerful for complex components.

### Characteristics
- Scoped to a specific component
- Reference semantic tokens (rarely primitives)
- Enable component-level customization
- Used for complex, stateful components

### Structure

```json
{
  "component": {
    "button": {
      "primary": {
        "bg": { "value": "{semantic.color.interactive.primary}" },
        "bg-hover": { "value": "{semantic.color.interactive.primary-hover}" },
        "text": { "value": "{semantic.color.text.inverse}" },
        "border": { "value": "transparent" },
        "radius": { "value": "{semantic.radius.interactive}" },
        "padding-x": { "value": "{primitive.spacing.4}" },
        "padding-y": { "value": "{primitive.spacing.2}" }
      },
      "secondary": {
        "bg": { "value": "{semantic.color.interactive.secondary}" },
        "bg-hover": { "value": "{semantic.color.interactive.secondary-hover}" },
        "text": { "value": "{semantic.color.text.primary}" },
        "border": { "value": "{semantic.color.border.primary}" }
      },
      "disabled": {
        "bg": { "value": "{primitive.color.gray.100}" },
        "text": { "value": "{primitive.color.gray.400}" }
      }
    },
    "input": {
      "bg": { "value": "{semantic.color.bg.primary}" },
      "text": { "value": "{semantic.color.text.primary}" },
      "placeholder": { "value": "{semantic.color.text.tertiary}" },
      "border": { "value": "{semantic.color.border.primary}" },
      "border-focus": { "value": "{semantic.color.border.focus}" },
      "radius": { "value": "{semantic.radius.interactive}" },
      "padding-x": { "value": "{primitive.spacing.3}" },
      "padding-y": { "value": "{primitive.spacing.2}" }
    },
    "card": {
      "bg": { "value": "{semantic.color.bg.primary}" },
      "border": { "value": "{semantic.color.border.primary}" },
      "radius": { "value": "{semantic.radius.container}" },
      "padding": { "value": "{semantic.spacing.element}" },
      "shadow": { "value": "{primitive.shadow.md}" }
    }
  }
}
```

---

## CSS Output

### Generated Variables

```css
/* Primitives - available but rarely used directly */
:root {
  --primitive-color-gray-50: #f9fafb;
  --primitive-color-gray-900: #111827;
  --primitive-color-blue-500: #3b82f6;
  --primitive-spacing-4: 1rem;
  /* ... */
}

/* Semantic - the main tokens you use */
:root {
  --color-bg-primary: var(--primitive-color-gray-50);
  --color-text-primary: var(--primitive-color-gray-900);
  --color-interactive-primary: var(--primitive-color-blue-500);
  --spacing-element: var(--primitive-spacing-4);
  /* ... */
}

/* Dark theme overrides semantic only */
[data-theme="dark"] {
  --color-bg-primary: var(--primitive-color-gray-950);
  --color-text-primary: var(--primitive-color-gray-50);
  /* primitives stay the same */
}

/* Component tokens (optional) */
:root {
  --button-primary-bg: var(--color-interactive-primary);
  --button-primary-text: var(--color-text-inverse);
  --card-bg: var(--color-bg-primary);
  --card-padding: var(--spacing-element);
}
```

### Usage in Components

```css
/* Use semantic tokens */
.card {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-primary);
  padding: var(--spacing-element);
}

/* Or use component tokens if defined */
.card {
  background: var(--card-bg);
  padding: var(--card-padding);
}

/* Never use primitives directly in components */
/* ❌ Bad */
.card {
  background: var(--primitive-color-gray-50);
}
```

---

## File Organization

### Recommended Structure

```
tokens/
├── primitive/
│   ├── colors.json
│   ├── spacing.json
│   ├── typography.json
│   ├── radius.json
│   └── shadows.json
├── semantic/
│   ├── light.json       # Light theme semantic mappings
│   └── dark.json        # Dark theme overrides
├── component/
│   ├── button.json
│   ├── input.json
│   └── card.json
└── index.json           # Combines all for build
```

### Flat vs Nested

**Nested (Recommended for large systems):**
```json
{
  "color": {
    "bg": {
      "primary": { "value": "..." }
    }
  }
}
```
Output: `--color-bg-primary`

**Flat (Simpler for small systems):**
```json
{
  "color-bg-primary": { "value": "..." }
}
```
Output: `--color-bg-primary`

---

## Naming Conventions

### Pattern: `{category}-{property}-{variant}-{state}`

| Category | Examples |
|----------|----------|
| color | `color-bg-primary`, `color-text-secondary` |
| spacing | `spacing-page`, `spacing-inline` |
| radius | `radius-interactive`, `radius-container` |
| font | `font-size-lg`, `font-weight-bold` |
| shadow | `shadow-md`, `shadow-lg` |

### Semantic Naming Guidelines

| Use | Avoid |
|-----|-------|
| `color-text-primary` | `color-dark-gray` |
| `color-bg-surface` | `color-white` |
| `color-interactive-primary` | `color-blue` |
| `spacing-page` | `spacing-24px` |
| `color-status-error` | `color-red` |

---

## When to Add Each Layer

| Situation | Layers Needed |
|-----------|---------------|
| Simple app, single theme | Primitive + Semantic |
| Multi-theme (light/dark) | Primitive + Semantic (per theme) |
| Complex components | All three layers |
| Multi-brand (white-label) | All three + brand-specific overrides |
| Design tool sync | Primitive only to start |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Semantic references semantic | Circular/complex chains | Semantic → Primitive only |
| Using primitives in components | Breaks theming | Use semantic tokens |
| Color names in semantic | Leaks visual info | Use purpose names |
| Too many component tokens | Maintenance burden | Only for complex states |
| Skipping semantic layer | Can't theme | Always have semantic layer |

---

## Migrating Existing Tokens

### Step 1: Audit Current Usage
Find all hardcoded values and existing variables.

### Step 2: Create Primitive Layer
Extract unique values into primitives.

### Step 3: Create Semantic Layer
Map primitives to purposes.

### Step 4: Update Components
Replace hardcoded values with semantic tokens.

### Step 5: Add Themes
Create theme-specific semantic overrides.

```css
/* Before */
.button {
  background: #3b82f6;
  color: white;
}

/* After */
.button {
  background: var(--color-interactive-primary);
  color: var(--color-text-inverse);
}
```
