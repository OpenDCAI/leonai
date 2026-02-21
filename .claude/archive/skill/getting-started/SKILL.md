---
name: getting-started
description: Introduction to the design system skills plugin. Use when first installing the plugin, exploring available skills, or planning a design system implementation.
---

# Getting Started with Design System Skills

## Overview

This plugin provides 28 skills for building design systems: token generators, component patterns, accessibility guidance, framework integrations, and tool workflows. Each skill is a focused guide Claude uses to help you implement specific parts of a design system.

## Quick Start

**Building a new design system?** Start here:

1. **Token foundation**: Use `design-tokens-structure` to plan your architecture
2. **Colors**: Use `color-scale` to generate your palette
3. **Spacing/Typography**: Use `spacing-scale` and `type-scale`
4. **Components**: Use your framework skill (`react`, `vue`, `svelte`, `angular`)

**Adding to an existing project?** Jump to the skill you need:

| Task | Skill |
|------|-------|
| Add dark mode | `dark-mode` |
| Fix contrast issues | `color-contrast` |
| Improve animations | `animation-principles` + `motion-scale` |
| Set up Storybook | `storybook` |
| Multi-platform tokens | `style-dictionary` |

## Available Skills

### Tokens (10 skills)
Generate design tokens in CSS, Tailwind, or JSON:

| Skill | Purpose |
|-------|---------|
| `color-scale` | OKLCH color palettes from brand colors |
| `spacing-scale` | Margin/padding/gap token scales |
| `type-scale` | Typography with modular ratios |
| `shadow-scale` | Elevation and depth tokens |
| `radius-scale` | Border radius tokens |
| `breakpoints` | Responsive breakpoint tokens |
| `motion-scale` | Animation duration and easing |
| `z-index-scale` | Layering/stacking tokens |
| `design-tokens-structure` | Token architecture (primitive → semantic → component) |
| `responsive-typography` | Fluid type with clamp() |

### Patterns (6 skills)
Implementation patterns for common challenges:

| Skill | Purpose |
|-------|---------|
| `dark-mode` | Theme switching with semantic tokens |
| `compound-components` | Radix/Headless UI patterns |
| `icon-system` | SVG sprites and icon components |
| `layout-primitives` | Stack, Cluster, Grid, Sidebar |
| `animation-principles` | Disney's 12 principles for UI |

### Frameworks (4 skills)
Framework-specific component patterns:

| Skill | Purpose |
|-------|---------|
| `react` | React + TypeScript components |
| `vue` | Vue 3 + Composition API |
| `svelte` | Svelte 5 + runes |
| `angular` | Angular + signals |

### Tools (4 skills)
Design tool and build integrations:

| Skill | Purpose |
|-------|---------|
| `figma` | Figma Variables and Tokens Studio |
| `storybook` | Component documentation |
| `framer` | Framer token integration |
| `style-dictionary` | Multi-platform token transformation |

### Accessibility (3 skills)
WCAG compliance and a11y patterns:

| Skill | Purpose |
|-------|---------|
| `color-contrast` | WCAG contrast validation |
| `focus-states` | Keyboard focus indicators |
| `aria-patterns` | ARIA for interactive components |

### Documentation (2 skills)
Generate documentation:

| Skill | Purpose |
|-------|---------|
| `token-docs` | Design token documentation |
| `component-docs` | Component API documentation |

---

## Recommended Paths

### Path A: New Design System

```
1. design-tokens-structure  → Plan your token architecture
2. color-scale              → Generate color palette
3. spacing-scale            → Generate spacing tokens
4. type-scale               → Generate typography tokens
5. shadow-scale             → Generate elevation tokens
6. dark-mode                → Add theme support
7. [framework skill]        → Build components
8. storybook                → Document components
```

### Path B: Add Design Tokens to Existing Project

```
1. design-tokens-structure  → Understand token layers
2. color-scale              → Convert existing colors to tokens
3. spacing-scale            → Standardize spacing
4. style-dictionary         → Set up build process
```

### Path C: Improve Accessibility

```
1. color-contrast           → Audit and fix contrast
2. focus-states             → Add visible focus indicators
3. aria-patterns            → Fix interactive components
```

### Path D: Cross-Platform Design System

```
1. design-tokens-structure  → Plan architecture
2. style-dictionary         → Multi-platform output
3. figma                    → Sync with design tool
```

---

## How Skills Work

Each skill provides:

1. **When to use**: Scenarios that trigger the skill
2. **Quick reference**: Tables and cheat sheets
3. **The process**: Step-by-step workflow
4. **Implementation checklist**: Trackable progress (for complex skills)
5. **Code examples**: CSS, Tailwind, JSON, framework-specific

Skills output in multiple formats:
- **CSS custom properties**: `--color-primary: #3b82f6`
- **Tailwind config**: `theme.extend.colors.primary`
- **JSON tokens**: Design token format for tools

---

## Tips for Best Results

1. **Be specific**: "Generate a blue color scale" → uses `color-scale`
2. **Mention format**: "in Tailwind format" → gets Tailwind config output
3. **Chain skills**: "Create spacing tokens then document them" → uses `spacing-scale` + `token-docs`
4. **Reference existing**: "Match my existing token structure" → adapts to your patterns

---

## Getting Help

- **Find a skill**: Describe what you're trying to do
- **Learn a concept**: Ask about tokens, theming, accessibility
- **Debug issues**: "Why isn't my dark mode working?"
- **Best practices**: "What's the best way to structure tokens?"

This plugin is maintained by [buoy.design](https://buoy.design).
