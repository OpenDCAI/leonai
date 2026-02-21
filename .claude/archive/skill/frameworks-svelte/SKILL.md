---
name: svelte
description: Builds token-driven Svelte 5 components with runes ($state, $props) and TypeScript. Use when creating Svelte component libraries, integrating design tokens, or building SvelteKit design system components.
---

# Svelte Component Patterns

## Overview

Build accessible, token-driven Svelte 5 components using runes and modern patterns. Covers component structure, TypeScript integration, stores, and consuming design tokens.

## When to Use

- Creating a Svelte component library
- Building components that use design tokens
- Setting up a design system in SvelteKit
- Converting designs to Svelte components

## The Process

1. **Identify component type**: Primitive, composite, or layout?
2. **Choose styling approach**: Scoped CSS, Tailwind, or global tokens?
3. **Define props with TypeScript**: Use `$props()` rune
4. **Implement with tokens**: CSS custom properties
5. **Add accessibility**: ARIA, keyboard handling, focus management
6. **Extract state logic**: Use `$state`, `$derived`, and `$effect`

## Svelte 5 Runes Quick Reference

| Rune | Purpose | Example |
|------|---------|---------|
| `$state` | Reactive state | `let count = $state(0)` |
| `$derived` | Computed values | `let double = $derived(count * 2)` |
| `$effect` | Side effects | `$effect(() => console.log(count))` |
| `$props` | Component props | `let { variant = 'primary' } = $props()` |
| `$bindable` | Two-way binding | `let { value = $bindable() } = $props()` |

## Project Structure

```
src/
├── lib/
│   ├── components/
│   │   ├── primitives/
│   │   │   ├── Button/
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── Button.test.ts
│   │   │   │   └── index.ts
│   │   │   ├── Input/
│   │   │   └── Text/
│   │   ├── composite/
│   │   │   ├── Card/
│   │   │   ├── Modal/
│   │   │   └── Dropdown/
│   │   └── layout/
│   │       ├── Stack/
│   │       ├── Grid/
│   │       └── Container/
│   ├── stores/
│   │   └── theme.svelte.ts
│   ├── tokens/
│   │   └── index.css
│   └── index.ts
└── routes/
```

## Component Patterns

### Button Component

**Button.svelte:**
```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    /** Visual style variant */
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    /** Size of the button */
    size?: 'sm' | 'md' | 'lg';
    /** Full width button */
    fullWidth?: boolean;
    /** Loading state */
    loading?: boolean;
    /** Icon before text */
    leftIcon?: Snippet;
    /** Icon after text */
    rightIcon?: Snippet;
    /** Button content */
    children: Snippet;
  }

  let {
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    loading = false,
    disabled = false,
    leftIcon,
    rightIcon,
    children,
    class: className = '',
    ...restProps
  }: Props = $props();

  let isDisabled = $derived(disabled || loading);
</script>

<button
  class="btn btn--{variant} btn--{size} {className}"
  class:btn--full-width={fullWidth}
  class:btn--loading={loading}
  disabled={isDisabled}
  aria-busy={loading}
  {...restProps}
>
  {#if loading}
    <span class="btn__spinner" aria-hidden="true"></span>
  {/if}

  {#if leftIcon}
    <span class="btn__icon">
      {@render leftIcon()}
    </span>
  {/if}

  <span class="btn__label">
    {@render children()}
  </span>

  {#if rightIcon}
    <span class="btn__icon">
      {@render rightIcon()}
    </span>
  {/if}
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-xs);
    font-family: inherit;
    font-weight: 500;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    transition:
      background-color 150ms ease,
      border-color 150ms ease,
      transform 100ms ease;
  }

  .btn:focus-visible {
    outline: 2px solid var(--color-primary-500);
    outline-offset: 2px;
  }

  .btn:active:not(:disabled) {
    transform: scale(0.98);
  }

  .btn:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  /* Variants */
  .btn--primary {
    background-color: var(--color-primary-500);
    color: white;
  }

  .btn--primary:hover:not(:disabled) {
    background-color: var(--color-primary-600);
  }

  .btn--secondary {
    background-color: transparent;
    border-color: var(--color-gray-300);
    color: var(--color-gray-700);
  }

  .btn--secondary:hover:not(:disabled) {
    background-color: var(--color-gray-50);
    border-color: var(--color-gray-400);
  }

  .btn--ghost {
    background-color: transparent;
    color: var(--color-gray-700);
  }

  .btn--ghost:hover:not(:disabled) {
    background-color: var(--color-gray-100);
  }

  .btn--danger {
    background-color: var(--color-error-500);
    color: white;
  }

  .btn--danger:hover:not(:disabled) {
    background-color: var(--color-error-600);
  }

  /* Sizes */
  .btn--sm {
    height: 32px;
    padding: 0 var(--spacing-sm);
    font-size: var(--text-sm);
  }

  .btn--md {
    height: 40px;
    padding: 0 var(--spacing-md);
    font-size: var(--text-base);
  }

  .btn--lg {
    height: 48px;
    padding: 0 var(--spacing-lg);
    font-size: var(--text-lg);
  }

  /* Modifiers */
  .btn--full-width {
    width: 100%;
  }

  .btn--loading .btn__label {
    opacity: 0;
  }

  .btn__spinner {
    position: absolute;
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 600ms linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .btn__icon {
    display: flex;
    flex-shrink: 0;
  }
</style>
```

---

### Input Component

**Input.svelte:**
```svelte
<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';

  interface Props extends Omit<HTMLInputAttributes, 'size'> {
    /** Bound value */
    value?: string;
    /** Label text */
    label?: string;
    /** Helper text */
    helperText?: string;
    /** Error message */
    error?: string;
    /** Size variant */
    size?: 'sm' | 'md' | 'lg';
    /** Full width */
    fullWidth?: boolean;
  }

  let {
    value = $bindable(''),
    label,
    helperText,
    error,
    size = 'md',
    fullWidth = false,
    disabled = false,
    required = false,
    id,
    class: className = '',
    ...restProps
  }: Props = $props();

  let inputId = $derived(id || `input-${crypto.randomUUID().slice(0, 8)}`);
  let helperId = $derived(`${inputId}-helper`);
  let errorId = $derived(`${inputId}-error`);

  let inputRef: HTMLInputElement;

  export function focus() {
    inputRef?.focus();
  }
</script>

<div class="input-container" class:input-container--full-width={fullWidth}>
  {#if label}
    <label for={inputId} class="input-label">
      {label}
      {#if required}
        <span class="input-required" aria-hidden="true">*</span>
      {/if}
    </label>
  {/if}

  <div
    class="input-wrapper input-wrapper--{size} {className}"
    class:input-wrapper--error={error}
    class:input-wrapper--disabled={disabled}
  >
    {#if $$slots.startAdornment}
      <span class="input-adornment">
        <slot name="startAdornment" />
      </span>
    {/if}

    <input
      bind:this={inputRef}
      bind:value
      {id}
      {disabled}
      {required}
      aria-invalid={!!error}
      aria-describedby={error ? errorId : helperText ? helperId : undefined}
      class="input"
      {...restProps}
    />

    {#if $$slots.endAdornment}
      <span class="input-adornment">
        <slot name="endAdornment" />
      </span>
    {/if}
  </div>

  {#if error}
    <span id={errorId} class="input-error" role="alert">{error}</span>
  {:else if helperText}
    <span id={helperId} class="input-helper">{helperText}</span>
  {/if}
</div>

<style>
  .input-container {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .input-container--full-width {
    width: 100%;
  }

  .input-label {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--color-gray-700);
  }

  .input-required {
    color: var(--color-error-500);
    margin-left: 2px;
  }

  .input-wrapper {
    display: flex;
    align-items: center;
    border: 1px solid var(--color-gray-300);
    border-radius: var(--radius-md);
    background-color: white;
    transition: border-color 150ms ease, box-shadow 150ms ease;
  }

  .input-wrapper:focus-within {
    border-color: var(--color-primary-500);
    box-shadow: 0 0 0 3px rgb(59 130 246 / 0.15);
  }

  .input-wrapper--error {
    border-color: var(--color-error-500);
  }

  .input-wrapper--error:focus-within {
    box-shadow: 0 0 0 3px rgb(239 68 68 / 0.15);
  }

  .input-wrapper--disabled {
    background-color: var(--color-gray-100);
    cursor: not-allowed;
  }

  .input-wrapper--sm {
    height: 32px;
    padding: 0 var(--spacing-sm);
  }

  .input-wrapper--md {
    height: 40px;
    padding: 0 var(--spacing-md);
  }

  .input-wrapper--lg {
    height: 48px;
    padding: 0 var(--spacing-md);
  }

  .input {
    flex: 1;
    width: 100%;
    border: none;
    background: transparent;
    font: inherit;
    color: var(--color-gray-900);
  }

  .input:focus {
    outline: none;
  }

  .input::placeholder {
    color: var(--color-gray-400);
  }

  .input:disabled {
    cursor: not-allowed;
    color: var(--color-gray-500);
  }

  .input-adornment {
    display: flex;
    align-items: center;
    color: var(--color-gray-500);
  }

  .input-helper {
    font-size: var(--text-sm);
    color: var(--color-gray-500);
  }

  .input-error {
    font-size: var(--text-sm);
    color: var(--color-error-500);
  }
</style>
```

---

### Stack Layout Component

**Stack.svelte:**
```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLAttributes } from 'svelte/elements';

  type SpacingToken = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

  interface Props extends HTMLAttributes<HTMLElement> {
    /** Direction of stacking */
    direction?: 'row' | 'column';
    /** Gap between items */
    gap?: SpacingToken;
    /** Horizontal alignment */
    align?: 'start' | 'center' | 'end' | 'stretch' | 'baseline';
    /** Distribution */
    justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
    /** Wrap items */
    wrap?: boolean;
    /** Full width */
    fullWidth?: boolean;
    /** Content */
    children: Snippet;
  }

  let {
    direction = 'column',
    gap = 'md',
    align = 'stretch',
    justify = 'start',
    wrap = false,
    fullWidth = false,
    children,
    class: className = '',
    ...restProps
  }: Props = $props();

  const alignMap: Record<string, string> = {
    start: 'flex-start',
    center: 'center',
    end: 'flex-end',
    stretch: 'stretch',
    baseline: 'baseline',
  };

  const justifyMap: Record<string, string> = {
    start: 'flex-start',
    center: 'center',
    end: 'flex-end',
    between: 'space-between',
    around: 'space-around',
    evenly: 'space-evenly',
  };

  let styles = $derived(`
    --stack-gap: var(--spacing-${gap});
    --stack-align: ${alignMap[align]};
    --stack-justify: ${justifyMap[justify]};
  `);
</script>

<div
  class="stack stack--{direction} {className}"
  class:stack--wrap={wrap}
  class:stack--full-width={fullWidth}
  style={styles}
  {...restProps}
>
  {@render children()}
</div>

<style>
  .stack {
    display: flex;
    gap: var(--stack-gap, var(--spacing-md));
    align-items: var(--stack-align, stretch);
    justify-content: var(--stack-justify, flex-start);
  }

  .stack--column {
    flex-direction: column;
  }

  .stack--row {
    flex-direction: row;
  }

  .stack--wrap {
    flex-wrap: wrap;
  }

  .stack--full-width {
    width: 100%;
  }
</style>
```

---

## State Management with Runes

### Theme Store

**theme.svelte.ts:**
```ts
type Theme = 'light' | 'dark' | 'system';

class ThemeState {
  theme = $state<Theme>('system');
  resolvedTheme = $state<'light' | 'dark'>('light');

  constructor() {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme') as Theme | null;
      if (stored) this.theme = stored;
      this.updateResolved();

      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', () => this.updateResolved());
    }
  }

  private updateResolved() {
    if (this.theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.resolvedTheme = prefersDark ? 'dark' : 'light';
    } else {
      this.resolvedTheme = this.theme;
    }
    document.documentElement.dataset.theme = this.resolvedTheme;
  }

  setTheme(newTheme: Theme) {
    this.theme = newTheme;
    localStorage.setItem('theme', newTheme);
    this.updateResolved();
  }
}

export const themeState = new ThemeState();
```

**Usage:**
```svelte
<script>
  import { themeState } from '$lib/stores/theme.svelte';
</script>

<p>Current theme: {themeState.resolvedTheme}</p>
<button onclick={() => themeState.setTheme('dark')}>Dark Mode</button>
```

---

## Context Pattern

**ThemeProvider.svelte:**
```svelte
<script lang="ts">
  import { setContext } from 'svelte';
  import { themeState } from '$lib/stores/theme.svelte';

  setContext('theme', themeState);
</script>

<slot />
```

**Consuming context:**
```svelte
<script>
  import { getContext } from 'svelte';
  const theme = getContext('theme');
</script>
```

---

## Actions (Directives)

**clickOutside.ts:**
```ts
export function clickOutside(node: HTMLElement, callback: () => void) {
  function handleClick(event: MouseEvent) {
    if (!node.contains(event.target as Node)) {
      callback();
    }
  }

  document.addEventListener('click', handleClick, true);

  return {
    destroy() {
      document.removeEventListener('click', handleClick, true);
    },
  };
}
```

**Usage:**
```svelte
<script>
  import { clickOutside } from '$lib/actions/clickOutside';
  let open = $state(false);
</script>

<div use:clickOutside={() => open = false}>
  Dropdown content
</div>
```

**focusTrap.ts:**
```ts
export function focusTrap(node: HTMLElement) {
  const focusable = node.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  function handleKeydown(e: KeyboardEvent) {
    if (e.key !== 'Tab') return;

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  first?.focus();
  node.addEventListener('keydown', handleKeydown);

  return {
    destroy() {
      node.removeEventListener('keydown', handleKeydown);
    },
  };
}
```

---

## Transitions

**Custom transition with tokens:**
```svelte
<script>
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  let visible = $state(true);
</script>

{#if visible}
  <div
    transition:fly={{ y: 10, duration: 200, easing: cubicOut }}
    class="modal"
  >
    Modal content
  </div>
{/if}
```

---

## Library Export

**index.ts:**
```ts
// Components
export { default as Button } from './components/primitives/Button/Button.svelte';
export { default as Input } from './components/primitives/Input/Input.svelte';
export { default as Stack } from './components/layout/Stack/Stack.svelte';
export { default as Card } from './components/composite/Card/Card.svelte';

// Stores
export { themeState } from './stores/theme.svelte';

// Actions
export { clickOutside } from './actions/clickOutside';
export { focusTrap } from './actions/focusTrap';

// Types
export type { ButtonProps } from './components/primitives/Button/Button.svelte';
```

---

## Testing

**Button.test.ts:**
```ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Button from './Button.svelte';

describe('Button', () => {
  it('renders children', () => {
    render(Button, {
      props: { children: () => 'Click me' },
    });
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(Button, {
      props: { onclick: onClick, children: () => 'Click' },
    });
    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when loading', () => {
    render(Button, {
      props: { loading: true, children: () => 'Loading' },
    });
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies variant class', () => {
    render(Button, {
      props: { variant: 'danger', children: () => 'Delete' },
    });
    expect(screen.getByRole('button')).toHaveClass('btn--danger');
  });
});
```
