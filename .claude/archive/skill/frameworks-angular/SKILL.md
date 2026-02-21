---
name: angular
description: Builds token-driven Angular components with signals and standalone components. Use when creating Angular component libraries, integrating design tokens, or building design system components with new control flow syntax.
---

# Angular Component Patterns

## Overview

Build accessible, token-driven Angular components using modern patterns including signals, standalone components, and the new control flow syntax. Covers component architecture, TypeScript integration, services, and consuming design tokens.

## When to Use

- Creating an Angular component library
- Building components that use design tokens
- Setting up a design system in Angular
- Converting designs to Angular components

## The Process

1. **Identify component type**: Primitive, composite, or layout?
2. **Choose styling approach**: Component styles, CSS Modules, or Tailwind?
3. **Define inputs/outputs**: Use signal-based inputs with transforms
4. **Implement with tokens**: CSS custom properties via styles or host bindings
5. **Add accessibility**: ARIA, keyboard handling, focus management
6. **Create services**: Extract shared state and logic

## Angular 17+ Features Quick Reference

| Feature | Purpose | Example |
|---------|---------|---------|
| `input()` | Signal-based input | `variant = input<'primary'>('primary')` |
| `output()` | Event emitter | `clicked = output<void>()` |
| `model()` | Two-way binding | `value = model<string>('')` |
| `computed()` | Derived signals | `isDisabled = computed(() => ...)` |
| `@if/@for` | Control flow | `@if (loading) { ... }` |
| Standalone | No NgModule needed | `standalone: true` |

## Project Structure

```
src/
├── lib/
│   ├── components/
│   │   ├── primitives/
│   │   │   ├── button/
│   │   │   │   ├── button.component.ts
│   │   │   │   ├── button.component.html
│   │   │   │   ├── button.component.css
│   │   │   │   ├── button.component.spec.ts
│   │   │   │   └── index.ts
│   │   │   ├── input/
│   │   │   └── text/
│   │   ├── composite/
│   │   │   ├── card/
│   │   │   ├── modal/
│   │   │   └── dropdown/
│   │   └── layout/
│   │       ├── stack/
│   │       ├── grid/
│   │       └── container/
│   ├── services/
│   │   └── theme.service.ts
│   ├── directives/
│   │   └── focus-trap.directive.ts
│   ├── tokens/
│   │   └── tokens.css
│   └── index.ts
└── public-api.ts
```

## Component Patterns

### Button Component

**button.component.ts:**
```typescript
import {
  Component,
  computed,
  input,
  output,
  ChangeDetectionStrategy,
} from '@angular/core';
import { NgClass } from '@angular/common';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'ui-button',
  standalone: true,
  imports: [NgClass],
  templateUrl: './button.component.html',
  styleUrl: './button.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.btn--full-width]': 'fullWidth()',
    '[attr.data-loading]': 'loading()',
  },
})
export class ButtonComponent {
  /** Visual style variant */
  variant = input<ButtonVariant>('primary');

  /** Size of the button */
  size = input<ButtonSize>('md');

  /** Full width button */
  fullWidth = input<boolean>(false);

  /** Loading state */
  loading = input<boolean>(false);

  /** Disabled state */
  disabled = input<boolean>(false);

  /** Button type */
  type = input<'button' | 'submit' | 'reset'>('button');

  /** Click event */
  clicked = output<MouseEvent>();

  /** Computed disabled state */
  isDisabled = computed(() => this.disabled() || this.loading());

  /** CSS classes */
  classes = computed(() => ({
    btn: true,
    [`btn--${this.variant()}`]: true,
    [`btn--${this.size()}`]: true,
    'btn--loading': this.loading(),
  }));

  handleClick(event: MouseEvent): void {
    if (!this.isDisabled()) {
      this.clicked.emit(event);
    }
  }
}
```

**button.component.html:**
```html
<button
  [ngClass]="classes()"
  [type]="type()"
  [disabled]="isDisabled()"
  [attr.aria-busy]="loading()"
  (click)="handleClick($event)"
>
  @if (loading()) {
    <span class="btn__spinner" aria-hidden="true"></span>
  }

  <ng-content select="[leftIcon]" />

  <span class="btn__label">
    <ng-content />
  </span>

  <ng-content select="[rightIcon]" />
</button>
```

**button.component.css:**
```css
:host {
  display: inline-block;
}

:host(.btn--full-width) {
  display: block;
  width: 100%;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  width: 100%;
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

/* Loading */
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
```

---

### Input Component

**input.component.ts:**
```typescript
import {
  Component,
  computed,
  input,
  model,
  signal,
  output,
  forwardRef,
  ChangeDetectionStrategy,
  ElementRef,
  ViewChild,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

export type InputSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'ui-input',
  standalone: true,
  templateUrl: './input.component.html',
  styleUrl: './input.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true,
    },
  ],
  host: {
    '[class.input-container--full-width]': 'fullWidth()',
  },
})
export class InputComponent implements ControlValueAccessor {
  @ViewChild('inputRef') inputRef!: ElementRef<HTMLInputElement>;

  /** Bound value */
  value = model<string>('');

  /** Label text */
  label = input<string>('');

  /** Placeholder */
  placeholder = input<string>('');

  /** Helper text */
  helperText = input<string>('');

  /** Error message */
  error = input<string>('');

  /** Input type */
  type = input<'text' | 'email' | 'password' | 'number' | 'tel'>('text');

  /** Size variant */
  size = input<InputSize>('md');

  /** Disabled */
  disabled = input<boolean>(false);

  /** Required */
  required = input<boolean>(false);

  /** Full width */
  fullWidth = input<boolean>(false);

  /** Input ID */
  inputId = input<string>(`input-${crypto.randomUUID().slice(0, 8)}`);

  /** Blur event */
  blurred = output<FocusEvent>();

  /** Focus event */
  focused = output<FocusEvent>();

  /** CVA callbacks */
  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  /** Computed IDs */
  helperId = computed(() => `${this.inputId()}-helper`);
  errorId = computed(() => `${this.inputId()}-error`);

  /** Wrapper classes */
  wrapperClasses = computed(() => ({
    'input-wrapper': true,
    [`input-wrapper--${this.size()}`]: true,
    'input-wrapper--error': !!this.error(),
    'input-wrapper--disabled': this.disabled(),
  }));

  /** Focus the input */
  focus(): void {
    this.inputRef?.nativeElement?.focus();
  }

  /** Handle input changes */
  onInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.value.set(target.value);
    this.onChange(target.value);
  }

  /** Handle blur */
  onBlur(event: FocusEvent): void {
    this.onTouched();
    this.blurred.emit(event);
  }

  /** ControlValueAccessor */
  writeValue(value: string): void {
    this.value.set(value ?? '');
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    // Handle via input signal in template
  }
}
```

**input.component.html:**
```html
<div class="input-container">
  @if (label()) {
    <label [for]="inputId()" class="input-label">
      {{ label() }}
      @if (required()) {
        <span class="input-required" aria-hidden="true">*</span>
      }
    </label>
  }

  <div [ngClass]="wrapperClasses()">
    <span class="input-adornment">
      <ng-content select="[startAdornment]" />
    </span>

    <input
      #inputRef
      [id]="inputId()"
      [type]="type()"
      [value]="value()"
      [placeholder]="placeholder()"
      [disabled]="disabled()"
      [required]="required()"
      [attr.aria-invalid]="!!error()"
      [attr.aria-describedby]="error() ? errorId() : helperText() ? helperId() : null"
      class="input"
      (input)="onInput($event)"
      (blur)="onBlur($event)"
      (focus)="focused.emit($event)"
    />

    <span class="input-adornment">
      <ng-content select="[endAdornment]" />
    </span>
  </div>

  @if (error()) {
    <span [id]="errorId()" class="input-error" role="alert">
      {{ error() }}
    </span>
  } @else if (helperText()) {
    <span [id]="helperId()" class="input-helper">
      {{ helperText() }}
    </span>
  }
</div>
```

---

### Stack Layout Component

**stack.component.ts:**
```typescript
import {
  Component,
  input,
  computed,
  ChangeDetectionStrategy,
} from '@angular/core';
import { NgStyle, NgClass } from '@angular/common';

export type SpacingToken = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
export type AlignOption = 'start' | 'center' | 'end' | 'stretch' | 'baseline';
export type JustifyOption = 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';

@Component({
  selector: 'ui-stack',
  standalone: true,
  imports: [NgStyle, NgClass],
  template: `
    <ng-content />
  `,
  styles: [`
    :host {
      display: flex;
      gap: var(--stack-gap, var(--spacing-md));
      align-items: var(--stack-align, stretch);
      justify-content: var(--stack-justify, flex-start);
    }

    :host(.stack--column) {
      flex-direction: column;
    }

    :host(.stack--row) {
      flex-direction: row;
    }

    :host(.stack--wrap) {
      flex-wrap: wrap;
    }

    :host(.stack--full-width) {
      width: 100%;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.stack--column]': "direction() === 'column'",
    '[class.stack--row]': "direction() === 'row'",
    '[class.stack--wrap]': 'wrap()',
    '[class.stack--full-width]': 'fullWidth()',
    '[style.--stack-gap]': "'var(--spacing-' + gap() + ')'",
    '[style.--stack-align]': 'alignValue()',
    '[style.--stack-justify]': 'justifyValue()',
  },
})
export class StackComponent {
  direction = input<'row' | 'column'>('column');
  gap = input<SpacingToken>('md');
  align = input<AlignOption>('stretch');
  justify = input<JustifyOption>('start');
  wrap = input<boolean>(false);
  fullWidth = input<boolean>(false);

  private alignMap: Record<AlignOption, string> = {
    start: 'flex-start',
    center: 'center',
    end: 'flex-end',
    stretch: 'stretch',
    baseline: 'baseline',
  };

  private justifyMap: Record<JustifyOption, string> = {
    start: 'flex-start',
    center: 'center',
    end: 'flex-end',
    between: 'space-between',
    around: 'space-around',
    evenly: 'space-evenly',
  };

  alignValue = computed(() => this.alignMap[this.align()]);
  justifyValue = computed(() => this.justifyMap[this.justify()]);
}
```

---

## Services

### Theme Service

**theme.service.ts:**
```typescript
import { Injectable, signal, computed, effect } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { inject } from '@angular/core';

export type Theme = 'light' | 'dark' | 'system';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private document = inject(DOCUMENT);

  /** Current theme setting */
  theme = signal<Theme>('system');

  /** Resolved theme (light or dark) */
  resolvedTheme = signal<'light' | 'dark'>('light');

  constructor() {
    // Load stored preference
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored) this.theme.set(stored);

    // Watch for system changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', () => this.updateResolved());

    // React to theme changes
    effect(() => {
      this.updateResolved();
    });
  }

  setTheme(theme: Theme): void {
    this.theme.set(theme);
    localStorage.setItem('theme', theme);
  }

  private updateResolved(): void {
    let resolved: 'light' | 'dark';

    if (this.theme() === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      resolved = prefersDark ? 'dark' : 'light';
    } else {
      resolved = this.theme() as 'light' | 'dark';
    }

    this.resolvedTheme.set(resolved);
    this.document.documentElement.dataset['theme'] = resolved;
  }
}
```

**Usage:**
```typescript
import { Component, inject } from '@angular/core';
import { ThemeService } from './theme.service';

@Component({
  selector: 'app-theme-toggle',
  template: `
    <button (click)="toggleTheme()">
      Current: {{ themeService.resolvedTheme() }}
    </button>
  `,
})
export class ThemeToggleComponent {
  themeService = inject(ThemeService);

  toggleTheme(): void {
    const next = this.themeService.resolvedTheme() === 'light' ? 'dark' : 'light';
    this.themeService.setTheme(next);
  }
}
```

---

## Directives

### Focus Trap Directive

**focus-trap.directive.ts:**
```typescript
import {
  Directive,
  ElementRef,
  OnInit,
  OnDestroy,
  inject,
} from '@angular/core';

@Directive({
  selector: '[uiFocusTrap]',
  standalone: true,
})
export class FocusTrapDirective implements OnInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private focusableSelector =
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

  ngOnInit(): void {
    this.el.nativeElement.addEventListener('keydown', this.handleKeydown);
    this.focusFirst();
  }

  ngOnDestroy(): void {
    this.el.nativeElement.removeEventListener('keydown', this.handleKeydown);
  }

  private handleKeydown = (event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return;

    const focusable = this.el.nativeElement.querySelectorAll<HTMLElement>(
      this.focusableSelector
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  private focusFirst(): void {
    const first = this.el.nativeElement.querySelector<HTMLElement>(
      this.focusableSelector
    );
    first?.focus();
  }
}
```

---

## Component Communication

### Input transforms

```typescript
import { booleanAttribute, numberAttribute } from '@angular/core';

@Component({...})
export class ExampleComponent {
  // Transform string "true"/"false" to boolean
  disabled = input(false, { transform: booleanAttribute });

  // Transform string to number
  count = input(0, { transform: numberAttribute });

  // Custom transform
  items = input<string[]>([], {
    transform: (value: string | string[]) =>
      typeof value === 'string' ? value.split(',') : value,
  });
}
```

### Content projection with selectors

```typescript
@Component({
  selector: 'ui-card',
  template: `
    <div class="card">
      <header class="card__header">
        <ng-content select="[cardHeader]" />
      </header>
      <div class="card__body">
        <ng-content />
      </div>
      <footer class="card__footer">
        <ng-content select="[cardFooter]" />
      </footer>
    </div>
  `,
})
export class CardComponent {}

// Usage:
// <ui-card>
//   <h2 cardHeader>Title</h2>
//   <p>Body content</p>
//   <button cardFooter>Action</button>
// </ui-card>
```

---

## Library Export

**public-api.ts:**
```typescript
// Components
export * from './lib/components/primitives/button';
export * from './lib/components/primitives/input';
export * from './lib/components/layout/stack';
export * from './lib/components/composite/card';

// Services
export * from './lib/services/theme.service';

// Directives
export * from './lib/directives/focus-trap.directive';

// Types
export type { ButtonVariant, ButtonSize } from './lib/components/primitives/button';
export type { InputSize } from './lib/components/primitives/input';
```

---

## Testing

**button.component.spec.ts:**
```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ButtonComponent } from './button.component';
import { By } from '@angular/platform-browser';

describe('ButtonComponent', () => {
  let component: ButtonComponent;
  let fixture: ComponentFixture<ButtonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ButtonComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit clicked event', () => {
    const spy = jest.spyOn(component.clicked, 'emit');
    const button = fixture.debugElement.query(By.css('button'));
    button.triggerEventHandler('click', new MouseEvent('click'));
    expect(spy).toHaveBeenCalled();
  });

  it('should be disabled when loading', () => {
    fixture.componentRef.setInput('loading', true);
    fixture.detectChanges();
    const button = fixture.debugElement.query(By.css('button'));
    expect(button.nativeElement.disabled).toBe(true);
  });

  it('should apply variant class', () => {
    fixture.componentRef.setInput('variant', 'danger');
    fixture.detectChanges();
    const button = fixture.debugElement.query(By.css('button'));
    expect(button.nativeElement.classList).toContain('btn--danger');
  });

  it('should have aria-busy when loading', () => {
    fixture.componentRef.setInput('loading', true);
    fixture.detectChanges();
    const button = fixture.debugElement.query(By.css('button'));
    expect(button.nativeElement.getAttribute('aria-busy')).toBe('true');
  });
});
```
