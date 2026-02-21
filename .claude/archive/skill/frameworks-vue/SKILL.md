---
name: vue
description: Builds token-driven Vue 3 components with Composition API and TypeScript. Use when creating Vue component libraries, integrating design tokens, or building Nuxt design system components with composables.
---

# Vue Component Patterns

## Overview

Build accessible, token-driven Vue 3 components using Composition API and modern patterns. Covers SFC structure, TypeScript integration, composables, and consuming design tokens.

## When to Use

- Creating a Vue 3 component library
- Building components that use design tokens
- Setting up a design system in Vue/Nuxt
- Converting designs to Vue components

## The Process

1. **Identify component type**: Primitive, composite, or layout?
2. **Choose styling approach**: Scoped CSS, CSS Modules, Tailwind, or UnoCSS?
3. **Define props with TypeScript**: Use `defineProps` with interfaces
4. **Implement with tokens**: CSS custom properties or provide/inject
5. **Add accessibility**: ARIA, keyboard handling, focus management
6. **Create composables**: Extract reusable logic

## Project Structure

```
src/
├── components/
│   ├── primitives/
│   │   ├── VButton/
│   │   │   ├── VButton.vue
│   │   │   ├── VButton.test.ts
│   │   │   └── index.ts
│   │   ├── VInput/
│   │   └── VText/
│   ├── composite/
│   │   ├── VCard/
│   │   ├── VModal/
│   │   └── VDropdown/
│   └── layout/
│       ├── VStack/
│       ├── VGrid/
│       └── VContainer/
├── composables/
│   ├── useTheme.ts
│   ├── useBreakpoint.ts
│   └── useId.ts
├── tokens/
│   └── index.css
└── index.ts
```

## Component Patterns

### Button Component

**VButton.vue:**
```vue
<script setup lang="ts">
import { computed, useSlots } from 'vue';

export interface ButtonProps {
  /** Visual style variant */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  /** Size of the button */
  size?: 'sm' | 'md' | 'lg';
  /** Full width button */
  fullWidth?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** HTML button type */
  type?: 'button' | 'submit' | 'reset';
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'primary',
  size: 'md',
  fullWidth: false,
  loading: false,
  disabled: false,
  type: 'button',
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const slots = useSlots();

const isDisabled = computed(() => props.disabled || props.loading);

const classes = computed(() => [
  'btn',
  `btn--${props.variant}`,
  `btn--${props.size}`,
  {
    'btn--full-width': props.fullWidth,
    'btn--loading': props.loading,
  },
]);

function handleClick(event: MouseEvent) {
  if (!isDisabled.value) {
    emit('click', event);
  }
}
</script>

<template>
  <button
    :type="type"
    :class="classes"
    :disabled="isDisabled"
    :aria-busy="loading"
    @click="handleClick"
  >
    <span v-if="loading" class="btn__spinner" aria-hidden="true" />
    <span v-if="slots.leftIcon" class="btn__icon">
      <slot name="leftIcon" />
    </span>
    <span class="btn__label">
      <slot />
    </span>
    <span v-if="slots.rightIcon" class="btn__icon">
      <slot name="rightIcon" />
    </span>
  </button>
</template>

<style scoped>
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

**VInput.vue:**
```vue
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useId } from '@/composables/useId';

export interface InputProps {
  /** v-model value */
  modelValue?: string;
  /** Label text */
  label?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Helper text */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Input type */
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Disabled state */
  disabled?: boolean;
  /** Required field */
  required?: boolean;
  /** Full width */
  fullWidth?: boolean;
}

const props = withDefaults(defineProps<InputProps>(), {
  modelValue: '',
  type: 'text',
  size: 'md',
  disabled: false,
  required: false,
  fullWidth: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  blur: [event: FocusEvent];
  focus: [event: FocusEvent];
}>();

const slots = defineSlots<{
  startAdornment?: () => any;
  endAdornment?: () => any;
}>();

const inputId = useId();
const helperId = computed(() => `${inputId}-helper`);
const errorId = computed(() => `${inputId}-error`);

const inputRef = ref<HTMLInputElement>();

const classes = computed(() => [
  'input-wrapper',
  `input-wrapper--${props.size}`,
  {
    'input-wrapper--error': props.error,
    'input-wrapper--disabled': props.disabled,
    'input-wrapper--full-width': props.fullWidth,
  },
]);

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
}

function focus() {
  inputRef.value?.focus();
}

defineExpose({ focus, inputRef });
</script>

<template>
  <div :class="['input-container', { 'input-container--full-width': fullWidth }]">
    <label v-if="label" :for="inputId" class="input-label">
      {{ label }}
      <span v-if="required" class="input-required" aria-hidden="true">*</span>
    </label>

    <div :class="classes">
      <span v-if="slots.startAdornment" class="input-adornment">
        <slot name="startAdornment" />
      </span>

      <input
        :id="inputId"
        ref="inputRef"
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="error ? errorId : helperText ? helperId : undefined"
        class="input"
        @input="handleInput"
        @blur="emit('blur', $event)"
        @focus="emit('focus', $event)"
      />

      <span v-if="slots.endAdornment" class="input-adornment">
        <slot name="endAdornment" />
      </span>
    </div>

    <span v-if="error" :id="errorId" class="input-error" role="alert">
      {{ error }}
    </span>
    <span v-else-if="helperText" :id="helperId" class="input-helper">
      {{ helperText }}
    </span>
  </div>
</template>

<style scoped>
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

/* Sizes */
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

**VStack.vue:**
```vue
<script setup lang="ts">
import { computed, type Component } from 'vue';

type SpacingToken = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface StackProps {
  /** HTML element or component to render */
  as?: string | Component;
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
}

const props = withDefaults(defineProps<StackProps>(), {
  as: 'div',
  direction: 'column',
  gap: 'md',
  align: 'stretch',
  justify: 'start',
  wrap: false,
  fullWidth: false,
});

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

const styles = computed(() => ({
  '--stack-gap': `var(--spacing-${props.gap})`,
  '--stack-align': alignMap[props.align],
  '--stack-justify': justifyMap[props.justify],
}));

const classes = computed(() => [
  'stack',
  `stack--${props.direction}`,
  {
    'stack--wrap': props.wrap,
    'stack--full-width': props.fullWidth,
  },
]);
</script>

<template>
  <component :is="as" :class="classes" :style="styles">
    <slot />
  </component>
</template>

<style scoped>
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

## Composables

### useTheme

**useTheme.ts:**
```ts
import { ref, watch, onMounted, readonly } from 'vue';

type Theme = 'light' | 'dark' | 'system';

const theme = ref<Theme>('system');
const resolvedTheme = ref<'light' | 'dark'>('light');

export function useTheme() {
  function setTheme(newTheme: Theme) {
    theme.value = newTheme;
    localStorage.setItem('theme', newTheme);
  }

  function updateResolvedTheme() {
    if (theme.value === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      resolvedTheme.value = prefersDark ? 'dark' : 'light';
    } else {
      resolvedTheme.value = theme.value;
    }
    document.documentElement.dataset.theme = resolvedTheme.value;
  }

  onMounted(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored) theme.value = stored;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', updateResolvedTheme);

    updateResolvedTheme();
  });

  watch(theme, updateResolvedTheme);

  return {
    theme: readonly(theme),
    resolvedTheme: readonly(resolvedTheme),
    setTheme,
  };
}
```

### useId

**useId.ts:**
```ts
import { getCurrentInstance } from 'vue';

let idCounter = 0;

export function useId(prefix = 'v'): string {
  const instance = getCurrentInstance();
  const uid = instance?.uid ?? ++idCounter;
  return `${prefix}-${uid}`;
}
```

### useBreakpoint

**useBreakpoint.ts:**
```ts
import { ref, onMounted, onUnmounted } from 'vue';

const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

type Breakpoint = keyof typeof breakpoints;

export function useBreakpoint() {
  const width = ref(0);
  const current = ref<Breakpoint | 'xs'>('xs');

  function update() {
    width.value = window.innerWidth;

    if (width.value >= breakpoints['2xl']) current.value = '2xl';
    else if (width.value >= breakpoints.xl) current.value = 'xl';
    else if (width.value >= breakpoints.lg) current.value = 'lg';
    else if (width.value >= breakpoints.md) current.value = 'md';
    else if (width.value >= breakpoints.sm) current.value = 'sm';
    else current.value = 'xs';
  }

  onMounted(() => {
    update();
    window.addEventListener('resize', update);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', update);
  });

  const isAbove = (bp: Breakpoint) => width.value >= breakpoints[bp];
  const isBelow = (bp: Breakpoint) => width.value < breakpoints[bp];

  return {
    width,
    current,
    isAbove,
    isBelow,
    isMobile: () => isBelow('md'),
    isDesktop: () => isAbove('lg'),
  };
}
```

---

## Provide/Inject Pattern

**ThemeProvider.vue:**
```vue
<script setup lang="ts">
import { provide, readonly } from 'vue';
import { useTheme } from '@/composables/useTheme';

const { theme, resolvedTheme, setTheme } = useTheme();

provide('theme', {
  theme: readonly(theme),
  resolvedTheme: readonly(resolvedTheme),
  setTheme,
});
</script>

<template>
  <slot />
</template>
```

**Consuming in child:**
```vue
<script setup lang="ts">
import { inject } from 'vue';

const themeContext = inject('theme');
</script>
```

---

## v-model Patterns

**Multiple v-models:**
```vue
<script setup lang="ts">
const props = defineProps<{
  modelValue: string;
  open: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'update:open': [value: boolean];
}>();
</script>

<!-- Usage -->
<MyComponent v-model="value" v-model:open="isOpen" />
```

---

## Plugin Registration

**index.ts:**
```ts
import type { App, Plugin } from 'vue';
import VButton from './components/primitives/VButton/VButton.vue';
import VInput from './components/primitives/VInput/VInput.vue';
import VStack from './components/layout/VStack/VStack.vue';
import './tokens/index.css';

export { VButton, VInput, VStack };

export const DesignSystem: Plugin = {
  install(app: App) {
    app.component('VButton', VButton);
    app.component('VInput', VInput);
    app.component('VStack', VStack);
  },
};

export default DesignSystem;
```

**Usage:**
```ts
import { createApp } from 'vue';
import { DesignSystem } from '@my-org/design-system';
import App from './App.vue';

createApp(App).use(DesignSystem).mount('#app');
```

---

## Testing

**VButton.test.ts:**
```ts
import { mount } from '@vue/test-utils';
import { describe, it, expect, vi } from 'vitest';
import VButton from './VButton.vue';

describe('VButton', () => {
  it('renders slot content', () => {
    const wrapper = mount(VButton, {
      slots: { default: 'Click me' },
    });
    expect(wrapper.text()).toContain('Click me');
  });

  it('emits click event', async () => {
    const wrapper = mount(VButton);
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('does not emit when disabled', async () => {
    const wrapper = mount(VButton, {
      props: { disabled: true },
    });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });

  it('applies variant class', () => {
    const wrapper = mount(VButton, {
      props: { variant: 'danger' },
    });
    expect(wrapper.classes()).toContain('btn--danger');
  });

  it('shows loading state', () => {
    const wrapper = mount(VButton, {
      props: { loading: true },
    });
    expect(wrapper.attributes('aria-busy')).toBe('true');
    expect(wrapper.find('.btn__spinner').exists()).toBe(true);
  });
});
```
