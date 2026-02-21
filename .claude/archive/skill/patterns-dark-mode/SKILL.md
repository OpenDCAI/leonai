---
name: dark-mode
description: Implements theme switching with semantic tokens and prefers-color-scheme detection. Use when adding dark mode, light/dark themes, color scheme toggles, or converting hardcoded colors to theme-aware tokens.
---

# Dark Mode Implementation

## Overview

Implement robust dark mode using semantic color tokens, CSS custom properties, and system preference detection. Creates a theme system that's maintainable, accessible, and works across frameworks.

## When to Use

- Adding dark mode to an existing project
- Setting up a theme system from scratch
- Converting hardcoded colors to semantic tokens
- Implementing system preference detection
- Building a theme toggle component

## Quick Reference: Theme Architecture

| Layer | Purpose | Example |
|-------|---------|---------|
| Primitive tokens | Raw color values | `--color-blue-500: #3b82f6` |
| Semantic tokens | Purpose-based aliases | `--color-primary: var(--color-blue-500)` |
| Theme tokens | Mode-specific values | `--color-bg: var(--color-gray-50)` in light |
| Component tokens | Component-specific | `--button-bg: var(--color-primary)` |

## The Process

1. **Audit existing colors**: Find all color usage in codebase
2. **Define primitive palette**: Use color-scale skill if needed
3. **Create semantic tokens**: Map primitives to purposes
4. **Define theme tokens**: Light and dark values
5. **Choose switching mechanism**: CSS classes, data attributes, or media query
6. **Add system detection**: `prefers-color-scheme`
7. **Implement persistence**: localStorage or cookies
8. **Handle edge cases**: Images, shadows, third-party components

### Implementation Checklist

Copy this checklist and track progress:

```
Dark Mode Implementation:
- [ ] Audit colors in codebase (grep for hex, rgb, hsl, color names)
- [ ] Create semantic token layer (bg, text, border, surface, interactive, status)
- [ ] Define light and dark theme values for all semantic tokens
- [ ] Implement switching mechanism (data-theme attribute recommended)
- [ ] Add system preference detection (prefers-color-scheme)
- [ ] Add inline script in <head> to prevent flash of wrong theme
- [ ] Build toggle component with localStorage persistence
- [ ] Handle edge cases (images, shadows, third-party components, form inputs)
- [ ] Test contrast ratios meet WCAG AA in both themes
```

## Theme Token Architecture

### Layer 1: Primitive Tokens (Theme-Independent)

```css
:root {
  /* Gray scale */
  --color-gray-50: #f9fafb;
  --color-gray-100: #f3f4f6;
  --color-gray-200: #e5e7eb;
  --color-gray-300: #d1d5db;
  --color-gray-400: #9ca3af;
  --color-gray-500: #6b7280;
  --color-gray-600: #4b5563;
  --color-gray-700: #374151;
  --color-gray-800: #1f2937;
  --color-gray-900: #111827;
  --color-gray-950: #030712;

  /* Brand colors */
  --color-blue-500: #3b82f6;
  --color-blue-600: #2563eb;
  --color-blue-400: #60a5fa;

  /* Semantic colors */
  --color-green-500: #22c55e;
  --color-red-500: #ef4444;
  --color-amber-500: #f59e0b;
}
```

### Layer 2: Semantic Theme Tokens

```css
/* Light theme (default) */
:root,
[data-theme="light"] {
  /* Backgrounds */
  --color-bg-primary: var(--color-gray-50);
  --color-bg-secondary: var(--color-gray-100);
  --color-bg-tertiary: var(--color-gray-200);
  --color-bg-inverse: var(--color-gray-900);

  /* Surfaces (cards, modals, dropdowns) */
  --color-surface-primary: #ffffff;
  --color-surface-secondary: var(--color-gray-50);
  --color-surface-elevated: #ffffff;

  /* Text */
  --color-text-primary: var(--color-gray-900);
  --color-text-secondary: var(--color-gray-600);
  --color-text-tertiary: var(--color-gray-500);
  --color-text-inverse: var(--color-gray-50);
  --color-text-disabled: var(--color-gray-400);

  /* Borders */
  --color-border-primary: var(--color-gray-200);
  --color-border-secondary: var(--color-gray-300);
  --color-border-focus: var(--color-blue-500);

  /* Interactive */
  --color-interactive-primary: var(--color-blue-500);
  --color-interactive-primary-hover: var(--color-blue-600);
  --color-interactive-secondary: var(--color-gray-100);
  --color-interactive-secondary-hover: var(--color-gray-200);

  /* Status */
  --color-status-success: var(--color-green-500);
  --color-status-warning: var(--color-amber-500);
  --color-status-error: var(--color-red-500);
  --color-status-info: var(--color-blue-500);

  /* Shadows - more visible in light mode */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);

  /* Overlay */
  --color-overlay: rgb(0 0 0 / 0.5);
}

/* Dark theme */
[data-theme="dark"] {
  /* Backgrounds */
  --color-bg-primary: var(--color-gray-950);
  --color-bg-secondary: var(--color-gray-900);
  --color-bg-tertiary: var(--color-gray-800);
  --color-bg-inverse: var(--color-gray-50);

  /* Surfaces - slightly elevated from background */
  --color-surface-primary: var(--color-gray-900);
  --color-surface-secondary: var(--color-gray-800);
  --color-surface-elevated: var(--color-gray-800);

  /* Text */
  --color-text-primary: var(--color-gray-50);
  --color-text-secondary: var(--color-gray-400);
  --color-text-tertiary: var(--color-gray-500);
  --color-text-inverse: var(--color-gray-900);
  --color-text-disabled: var(--color-gray-600);

  /* Borders - less contrast in dark mode */
  --color-border-primary: var(--color-gray-800);
  --color-border-secondary: var(--color-gray-700);
  --color-border-focus: var(--color-blue-400);

  /* Interactive - lighter shades for dark bg */
  --color-interactive-primary: var(--color-blue-500);
  --color-interactive-primary-hover: var(--color-blue-400);
  --color-interactive-secondary: var(--color-gray-800);
  --color-interactive-secondary-hover: var(--color-gray-700);

  /* Status - same or slightly adjusted */
  --color-status-success: var(--color-green-500);
  --color-status-warning: var(--color-amber-500);
  --color-status-error: var(--color-red-500);
  --color-status-info: var(--color-blue-400);

  /* Shadows - less visible, add subtle glow */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4);

  /* Overlay */
  --color-overlay: rgb(0 0 0 / 0.7);
}
```

---

## Switching Mechanisms

### Option 1: Data Attribute (Recommended)

```html
<html data-theme="light">
```

```css
[data-theme="light"] { /* light tokens */ }
[data-theme="dark"] { /* dark tokens */ }
```

**Pros:** Explicit, debuggable, works with SSR
**Cons:** Requires JavaScript to toggle

### Option 2: CSS Class

```html
<html class="dark">
```

```css
:root { /* light tokens */ }
.dark { /* dark tokens */ }
```

**Pros:** Simple, Tailwind-compatible
**Cons:** Can conflict with other classes

### Option 3: Media Query Only (No Toggle)

```css
:root { /* light tokens */ }

@media (prefers-color-scheme: dark) {
  :root { /* dark tokens */ }
}
```

**Pros:** Zero JavaScript, respects system
**Cons:** No user override

### Option 4: Hybrid (Best UX)

```css
/* Default: follow system */
:root { /* light tokens */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark tokens */ }
}

/* Manual overrides */
[data-theme="light"] { /* light tokens */ }
[data-theme="dark"] { /* dark tokens */ }
```

---

## JavaScript Implementation

### Vanilla JavaScript

```js
// theme.js
const STORAGE_KEY = 'theme';

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEY);
}

function setTheme(theme) {
  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;
  document.documentElement.dataset.theme = resolvedTheme;
  localStorage.setItem(STORAGE_KEY, theme);
}

function initTheme() {
  const stored = getStoredTheme();
  const theme = stored || 'system';
  setTheme(theme);

  // Listen for system changes
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', (e) => {
      if (getStoredTheme() === 'system' || !getStoredTheme()) {
        document.documentElement.dataset.theme = e.matches ? 'dark' : 'light';
      }
    });
}

// Initialize on load
initTheme();

// Export for toggle button
window.toggleTheme = () => {
  const current = document.documentElement.dataset.theme;
  setTheme(current === 'dark' ? 'light' : 'dark');
};
```

### Prevent Flash of Wrong Theme (FOWT)

Add inline script in `<head>` before CSS:

```html
<head>
  <script>
    (function() {
      const stored = localStorage.getItem('theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = stored || (prefersDark ? 'dark' : 'light');
      document.documentElement.dataset.theme = theme;
    })();
  </script>
  <link rel="stylesheet" href="styles.css">
</head>
```

---

## Framework Integration

### React

```tsx
// ThemeProvider.tsx
import { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored) setThemeState(stored);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)');

    const updateTheme = () => {
      const resolved = theme === 'system'
        ? (systemDark.matches ? 'dark' : 'light')
        : theme;
      setResolvedTheme(resolved);
      root.dataset.theme = resolved;
    };

    updateTheme();
    systemDark.addEventListener('change', updateTheme);
    return () => systemDark.removeEventListener('change', updateTheme);
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
```

```tsx
// ThemeToggle.tsx
import { useTheme } from './ThemeProvider';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );
}
```

### Tailwind CSS

**tailwind.config.js:**
```js
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  // or: darkMode: 'class', // uses .dark class
  theme: {
    extend: {
      colors: {
        // Map to CSS variables
        bg: {
          primary: 'var(--color-bg-primary)',
          secondary: 'var(--color-bg-secondary)',
        },
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
        },
      },
    },
  },
};
```

**Usage:**
```html
<!-- Using CSS variable colors -->
<div class="bg-bg-primary text-text-primary">
  Content
</div>

<!-- Or using Tailwind's dark: variant -->
<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-50">
  Content
</div>
```

---

## Edge Cases

### Images

```css
/* Dim images in dark mode */
[data-theme="dark"] img:not([data-theme-safe]) {
  filter: brightness(0.9);
}

/* Invert diagrams/illustrations */
[data-theme="dark"] img[data-invert] {
  filter: invert(1) hue-rotate(180deg);
}

/* Provide alternate images */
<picture>
  <source srcset="dark-logo.svg" media="(prefers-color-scheme: dark)">
  <img src="light-logo.svg" alt="Logo">
</picture>
```

### SVG Icons

```css
/* Icons that use currentColor work automatically */
.icon {
  color: var(--color-text-primary);
}

/* Filled icons may need explicit colors */
[data-theme="dark"] .icon-filled {
  fill: var(--color-text-primary);
}
```

### Third-Party Components

```css
/* Override third-party styles */
[data-theme="dark"] .third-party-component {
  --third-party-bg: var(--color-surface-primary);
  --third-party-text: var(--color-text-primary);
}
```

### Code Blocks / Syntax Highlighting

```css
/* Light theme syntax */
:root {
  --code-bg: var(--color-gray-100);
  --code-text: var(--color-gray-800);
  --code-keyword: #d73a49;
  --code-string: #22863a;
}

/* Dark theme syntax */
[data-theme="dark"] {
  --code-bg: var(--color-gray-900);
  --code-text: var(--color-gray-100);
  --code-keyword: #ff7b72;
  --code-string: #a5d6ff;
}
```

### Form Inputs

```css
/* Ensure form elements follow theme */
input, textarea, select {
  background-color: var(--color-surface-primary);
  color: var(--color-text-primary);
  border-color: var(--color-border-primary);
}

/* Autofill override */
input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 1000px var(--color-surface-primary) inset;
  -webkit-text-fill-color: var(--color-text-primary);
}
```

---

## Accessibility Considerations

1. **Sufficient contrast**: Test both themes with color-contrast skill
2. **Focus visibility**: Ensure focus rings visible in both themes
3. **Motion preferences**: Consider reduced-motion for transitions
4. **Persist preference**: Remember user's choice
5. **System preference**: Respect `prefers-color-scheme` by default

```css
/* Smooth theme transition (respect motion preferences) */
@media (prefers-reduced-motion: no-preference) {
  :root {
    transition: background-color 200ms ease, color 200ms ease;
  }
}
```

---

## Testing Checklist

- [ ] Light mode renders correctly
- [ ] Dark mode renders correctly
- [ ] Toggle switches between modes
- [ ] System preference detected on first visit
- [ ] User preference persists across sessions
- [ ] System preference change updates theme (if set to "system")
- [ ] No flash of wrong theme on page load
- [ ] All text has sufficient contrast
- [ ] Focus indicators visible in both modes
- [ ] Images/icons display appropriately
- [ ] Third-party components styled correctly
- [ ] Forms and inputs themed properly

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Hardcoding colors | Use CSS variables everywhere |
| Only theming backgrounds | Theme text, borders, shadows too |
| Forgetting scrollbars | Add `color-scheme: light dark` |
| Ignoring system preference | Use `prefers-color-scheme` as default |
| Flash on load | Inline script in `<head>` |
| Not testing contrast | Run accessibility audit on both themes |
| Over-transitioning | Only transition color properties |
