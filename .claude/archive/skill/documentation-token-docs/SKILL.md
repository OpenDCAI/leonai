---
name: token-docs
description: Generates design token documentation with visual swatches and code examples. Use when documenting token values, creating token reference guides, or building searchable design system documentation.
---

# Design Token Documentation Generator

## Overview

Generate comprehensive documentation for design tokens including visual swatches, usage guidelines, code examples, and cross-reference tables. Create living documentation that stays in sync with token values.

## When to Use

- Documenting a new token system
- Creating a design system style guide
- Generating token reference for developers
- Building visual documentation pages

## Quick Reference: Documentation Sections

| Section | Content | Audience |
|---------|---------|----------|
| Overview | System philosophy, naming conventions | All |
| Color Tokens | Swatches, contrast info, usage | Designers, Devs |
| Typography | Font stacks, scale, line heights | Designers, Devs |
| Spacing | Scale visualization, use cases | Devs |
| Shadows | Visual examples, elevation guide | Designers, Devs |
| Radius | Corner examples, component mapping | Devs |
| Breakpoints | Device targets, media queries | Devs |

## The Process

1. **Gather token data**: Import from CSS, JSON, or JS files
2. **Structure sections**: Organize by category
3. **Add visuals**: Swatches, scales, examples
4. **Write guidelines**: When and how to use each token
5. **Include code**: Copy-paste examples for each format
6. **Cross-reference**: Link related tokens and components

---

## Documentation Templates

### Color Token Documentation

```markdown
# Color Tokens

Our color system uses OKLCH for perceptual uniformity, ensuring consistent
visual steps across the entire scale.

## Naming Convention

`--color-{name}-{step}`

- **name**: Color category (primary, gray, success, etc.)
- **step**: Lightness value (50-950, lower = lighter)

## Primary

Our brand color, used for primary actions and key UI elements.

| Token | Value | Preview | Use Case |
|-------|-------|---------|----------|
| `--color-primary-50` | oklch(97% 0.01 250) | ![#eff6ff](swatch) | Subtle backgrounds |
| `--color-primary-100` | oklch(93% 0.02 250) | ![#dbeafe](swatch) | Hover states (light) |
| `--color-primary-500` | oklch(55% 0.15 250) | ![#3b82f6](swatch) | **Primary brand color** |
| `--color-primary-600` | oklch(45% 0.15 250) | ![#2563eb](swatch) | Hover states (dark) |
| `--color-primary-900` | oklch(20% 0.10 250) | ![#1e3a8a](swatch) | Text on light backgrounds |

### Accessibility

| Combination | Ratio | WCAG |
|-------------|-------|------|
| primary-900 on white | 9.4:1 | AAA |
| primary-500 on white | 4.5:1 | AA |
| white on primary-500 | 4.5:1 | AA |
| white on primary-600 | 5.8:1 | AA |

### Usage

```css
/* Primary actions */
.btn-primary {
  background-color: var(--color-primary-500);
  color: white;
}

.btn-primary:hover {
  background-color: var(--color-primary-600);
}

/* Accent text */
.link {
  color: var(--color-primary-600);
}
```

### Do / Don't

✅ **Do:**
- Use primary-500 for main CTAs
- Use primary-600 for hover states
- Use primary-50/100 for selected backgrounds

❌ **Don't:**
- Use primary-500 for large text blocks
- Mix primary colors from different scales
- Use low-contrast combinations (primary-300 on white)

---

## Gray (Neutral)

Neutral colors for text, backgrounds, borders, and UI elements.

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-gray-50` | #f9fafb | Page backgrounds |
| `--color-gray-100` | #f3f4f6 | Card backgrounds, hover states |
| `--color-gray-200` | #e5e7eb | Borders, dividers |
| `--color-gray-300` | #d1d5db | Input borders, disabled |
| `--color-gray-400` | #9ca3af | Placeholder text |
| `--color-gray-500` | #6b7280 | Muted text, icons |
| `--color-gray-600` | #4b5563 | Secondary text |
| `--color-gray-700` | #374151 | Body text |
| `--color-gray-800` | #1f2937 | Headings |
| `--color-gray-900` | #111827 | Primary text |
| `--color-gray-950` | #030712 | Darkest, rarely used |

---

## Semantic Colors

| Category | Token | Value | Use |
|----------|-------|-------|-----|
| Success | `--color-success-500` | #22c55e | Success messages, confirmations |
| Warning | `--color-warning-500` | #f59e0b | Warnings, caution states |
| Error | `--color-error-500` | #ef4444 | Errors, destructive actions |
| Info | `--color-info-500` | #3b82f6 | Informational messages |

Each semantic color has a full scale (50-900) for backgrounds, text, and borders.
```

---

### Typography Token Documentation

```markdown
# Typography Tokens

Our type scale uses a 1.2 (Minor Third) ratio for harmonious sizing.
Line heights are calculated based on font size for optimal readability.

## Font Families

| Token | Value | Use |
|-------|-------|-----|
| `--font-sans` | 'Inter', system-ui, sans-serif | Body text, UI |
| `--font-mono` | 'JetBrains Mono', monospace | Code, technical |
| `--font-serif` | 'Merriweather', Georgia, serif | Editorial (optional) |

## Font Sizes

| Token | Size | Line Height | Use |
|-------|------|-------------|-----|
| `--text-xs` | 12px | 1.7 | Captions, labels |
| `--text-sm` | 14px | 1.7 | Helper text, meta |
| `--text-base` | 16px | 1.6 | Body text |
| `--text-lg` | 18px | 1.55 | Lead paragraphs |
| `--text-xl` | 20px | 1.5 | H4, card titles |
| `--text-2xl` | 24px | 1.4 | H3 |
| `--text-3xl` | 30px | 1.35 | H2 |
| `--text-4xl` | 36px | 1.3 | H1 |
| `--text-5xl` | 48px | 1.2 | Display |
| `--text-6xl` | 60px | 1.1 | Hero |

## Font Weights

| Token | Value | Use |
|-------|-------|-----|
| `--font-normal` | 400 | Body text |
| `--font-medium` | 500 | UI labels, buttons |
| `--font-semibold` | 600 | Subheadings |
| `--font-bold` | 700 | Headings, emphasis |

## Usage Examples

```css
/* Heading */
h1 {
  font-family: var(--font-sans);
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  line-height: var(--leading-tight);
  color: var(--color-gray-900);
}

/* Body */
p {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-normal);
  line-height: var(--leading-normal);
  color: var(--color-gray-700);
}

/* Code */
code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--color-gray-100);
  padding: 0.125em 0.25em;
  border-radius: var(--radius-sm);
}
```

## Type Scale Visualization

```
--text-6xl  60px  ████████████████████████████████████
--text-5xl  48px  ████████████████████████████
--text-4xl  36px  █████████████████████
--text-3xl  30px  ██████████████████
--text-2xl  24px  ██████████████
--text-xl   20px  ████████████
--text-lg   18px  ███████████
--text-base 16px  ██████████ (base)
--text-sm   14px  ████████
--text-xs   12px  ███████
```
```

---

### Spacing Token Documentation

```markdown
# Spacing Tokens

Our spacing scale uses a base of 4px with a 2x ratio for predictable increments.

## Scale

| Token | Value | Pixels | Use |
|-------|-------|--------|-----|
| `--spacing-px` | 1px | 1 | Borders, fine adjustments |
| `--spacing-0.5` | 0.125rem | 2 | Tight inline spacing |
| `--spacing-1` | 0.25rem | 4 | Icon gaps, compact UI |
| `--spacing-2` | 0.5rem | 8 | Button padding, list gaps |
| `--spacing-3` | 0.75rem | 12 | Card padding (sm) |
| `--spacing-4` | 1rem | 16 | Standard padding |
| `--spacing-5` | 1.25rem | 20 | Section gaps |
| `--spacing-6` | 1.5rem | 24 | Card padding (md) |
| `--spacing-8` | 2rem | 32 | Section padding |
| `--spacing-10` | 2.5rem | 40 | Large gaps |
| `--spacing-12` | 3rem | 48 | Section margins |
| `--spacing-16` | 4rem | 64 | Page sections |
| `--spacing-20` | 5rem | 80 | Hero spacing |
| `--spacing-24` | 6rem | 96 | Major sections |

## Named Aliases

For semantic usage, we provide named aliases:

| Alias | Maps To | Use |
|-------|---------|-----|
| `--spacing-xs` | --spacing-1 | Tight gaps |
| `--spacing-sm` | --spacing-2 | Small padding |
| `--spacing-md` | --spacing-4 | Default padding |
| `--spacing-lg` | --spacing-6 | Generous padding |
| `--spacing-xl` | --spacing-8 | Section spacing |
| `--spacing-2xl` | --spacing-12 | Large sections |

## Visualization

```
--spacing-1   ████ 4px
--spacing-2   ████████ 8px
--spacing-3   ████████████ 12px
--spacing-4   ████████████████ 16px (base)
--spacing-6   ████████████████████████ 24px
--spacing-8   ████████████████████████████████ 32px
--spacing-12  ████████████████████████████████████████████████ 48px
```

## Common Patterns

```css
/* Card */
.card {
  padding: var(--spacing-6);      /* 24px */
  gap: var(--spacing-4);          /* 16px between items */
}

/* Button */
.btn {
  padding: var(--spacing-2) var(--spacing-4);  /* 8px 16px */
  gap: var(--spacing-2);                        /* 8px icon gap */
}

/* Stack */
.stack {
  gap: var(--spacing-4);  /* 16px between items */
}

/* Section */
.section {
  padding: var(--spacing-16) 0;  /* 64px vertical */
  margin-bottom: var(--spacing-12);  /* 48px between sections */
}
```
```

---

### Shadow Token Documentation

```markdown
# Shadow Tokens

Our elevation system uses layered shadows for realistic depth.

## Scale

| Token | Value | Use |
|-------|-------|-----|
| `--shadow-none` | none | Flat elements |
| `--shadow-xs` | 0 1px 2px 0 rgb(0 0 0 / 0.05) | Subtle lift |
| `--shadow-sm` | 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1) | Cards, buttons |
| `--shadow-md` | 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) | Dropdowns |
| `--shadow-lg` | 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1) | Modals |
| `--shadow-xl` | 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1) | Popovers |
| `--shadow-2xl` | 0 25px 50px -12px rgb(0 0 0 / 0.25) | Dialogs |

## Visual Reference

```
┌─────────────────┐
│  shadow-none    │  Flat
└─────────────────┘

┌─────────────────┐
│  shadow-xs      │  ░ Barely raised
└─────────────────┘

┌─────────────────┐
│  shadow-sm      │  ▒ Slight depth
└─────────────────┘

┌─────────────────┐
│  shadow-md      │  ▓ Clear separation
└─────────────────┘

┌─────────────────┐
│  shadow-lg      │  █ Floating
└─────────────────┘
```

## Component Mapping

| Component | Default Shadow | Hover Shadow |
|-----------|----------------|--------------|
| Card | sm | md |
| Button | none or xs | sm |
| Dropdown menu | md | - |
| Modal | lg | - |
| Tooltip | md | - |
| Toast | lg | - |
```

---

## Auto-Generation Script

**generate-docs.ts:**
```typescript
import fs from 'fs';
import path from 'path';

interface Token {
  value: string;
  type: string;
  description?: string;
}

interface TokenGroup {
  [key: string]: Token | TokenGroup;
}

function generateColorDocs(colors: TokenGroup): string {
  let md = '# Color Tokens\n\n';

  for (const [name, scale] of Object.entries(colors)) {
    md += `## ${capitalize(name)}\n\n`;
    md += '| Token | Value | Preview |\n';
    md += '|-------|-------|--------|\n';

    for (const [step, token] of Object.entries(scale as TokenGroup)) {
      if (typeof token === 'object' && 'value' in token) {
        md += `| \`--color-${name}-${step}\` | ${token.value} | ![](swatch:${token.value}) |\n`;
      }
    }
    md += '\n';
  }

  return md;
}

function generateSpacingDocs(spacing: TokenGroup): string {
  let md = '# Spacing Tokens\n\n';
  md += '| Token | Value | Pixels |\n';
  md += '|-------|-------|--------|\n';

  for (const [name, token] of Object.entries(spacing)) {
    if (typeof token === 'object' && 'value' in token) {
      const px = parseFloat(token.value) * 16;
      md += `| \`--spacing-${name}\` | ${token.value} | ${px}px |\n`;
    }
  }

  return md;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Main
const tokens = JSON.parse(fs.readFileSync('./tokens.json', 'utf-8'));

const colorDocs = generateColorDocs(tokens.color);
const spacingDocs = generateSpacingDocs(tokens.spacing);

fs.writeFileSync('./docs/colors.md', colorDocs);
fs.writeFileSync('./docs/spacing.md', spacingDocs);

console.log('Documentation generated!');
```

---

## Best Practices

1. **Keep docs near code**: Store docs alongside token files
2. **Auto-generate when possible**: Reduce manual updates
3. **Include visuals**: Swatches, scales, examples
4. **Show do/don't**: Guide correct usage
5. **Add code examples**: Copy-paste ready snippets
6. **Cross-reference**: Link to components that use tokens
7. **Version control**: Track changes with token updates
