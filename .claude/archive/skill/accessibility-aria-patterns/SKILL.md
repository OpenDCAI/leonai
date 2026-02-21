---
name: aria-patterns
description: Provides ARIA roles, states, and properties for interactive components. Use when building custom widgets, fixing screen reader issues, or implementing modals, tabs, accordions, menus, or dialogs accessibly.
---

# ARIA Patterns Guide

## Overview

Implement accessible interactive components using correct ARIA roles, states, and properties. Provides copy-paste patterns for common widgets that work with screen readers and keyboard navigation.

## When to Use

- Building custom interactive components
- Making dynamic content accessible
- Fixing screen reader issues
- Adding keyboard support to custom widgets

## Quick Reference: First Rules of ARIA

1. **Don't use ARIA if native HTML works** - `<button>` over `<div role="button">`
2. **Don't change native semantics** - Don't put `role="button"` on a heading
3. **All interactive ARIA elements must be keyboard accessible**
4. **Don't use `role="presentation"` or `aria-hidden="true"` on focusable elements**
5. **All interactive elements must have accessible names**

## The Process

1. **Identify component type**: What widget pattern matches?
2. **Check native HTML first**: Can a semantic element do this?
3. **Apply ARIA pattern**: Roles, states, properties
4. **Add keyboard support**: Expected keys for the pattern
5. **Test with screen reader**: Verify announcements

## Component Patterns

### Button

**Native (preferred):**
```html
<button type="button">Click me</button>
```

**Custom (when necessary):**
```html
<div
  role="button"
  tabindex="0"
  aria-pressed="false"
  onkeydown="handleKeyDown(event)"
>
  Toggle
</div>

<script>
function handleKeyDown(e) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    e.target.click();
  }
}
</script>
```

### Toggle Button

```html
<button
  type="button"
  aria-pressed="false"
  onclick="this.setAttribute('aria-pressed', this.getAttribute('aria-pressed') === 'true' ? 'false' : 'true')"
>
  <span class="sr-only">Enable</span> Dark Mode
</button>
```

---

### Modal Dialog

```html
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-desc"
>
  <h2 id="modal-title">Confirm Action</h2>
  <p id="modal-desc">Are you sure you want to proceed?</p>

  <button type="button">Cancel</button>
  <button type="button">Confirm</button>
</div>
```

**Required behavior:**
- Focus moves to dialog on open
- Focus trapped within dialog
- Escape key closes dialog
- Focus returns to trigger on close

```js
// Focus trap example
function trapFocus(dialog) {
  const focusable = dialog.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  dialog.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
}
```

---

### Dropdown Menu

```html
<div class="dropdown">
  <button
    type="button"
    aria-haspopup="menu"
    aria-expanded="false"
    aria-controls="dropdown-menu"
    id="dropdown-trigger"
  >
    Options
  </button>

  <ul
    role="menu"
    id="dropdown-menu"
    aria-labelledby="dropdown-trigger"
    hidden
  >
    <li role="none">
      <button role="menuitem" tabindex="-1">Edit</button>
    </li>
    <li role="none">
      <button role="menuitem" tabindex="-1">Duplicate</button>
    </li>
    <li role="none">
      <button role="menuitem" tabindex="-1">Delete</button>
    </li>
  </ul>
</div>
```

**Keyboard:**
- Enter/Space: Open menu, activate item
- Arrow Down: Next item (or first if closed)
- Arrow Up: Previous item
- Escape: Close menu
- Home: First item
- End: Last item

---

### Tabs

```html
<div class="tabs">
  <div role="tablist" aria-label="Account settings">
    <button
      role="tab"
      aria-selected="true"
      aria-controls="panel-1"
      id="tab-1"
      tabindex="0"
    >
      Profile
    </button>
    <button
      role="tab"
      aria-selected="false"
      aria-controls="panel-2"
      id="tab-2"
      tabindex="-1"
    >
      Security
    </button>
    <button
      role="tab"
      aria-selected="false"
      aria-controls="panel-3"
      id="tab-3"
      tabindex="-1"
    >
      Billing
    </button>
  </div>

  <div role="tabpanel" id="panel-1" aria-labelledby="tab-1" tabindex="0">
    Profile content...
  </div>
  <div role="tabpanel" id="panel-2" aria-labelledby="tab-2" tabindex="0" hidden>
    Security content...
  </div>
  <div role="tabpanel" id="panel-3" aria-labelledby="tab-3" tabindex="0" hidden>
    Billing content...
  </div>
</div>
```

**Keyboard:**
- Arrow Left/Right: Move between tabs
- Home: First tab
- End: Last tab
- Tab: Move into panel content

---

### Accordion

```html
<div class="accordion">
  <h3>
    <button
      type="button"
      aria-expanded="true"
      aria-controls="section-1"
      id="accordion-header-1"
    >
      Section 1
    </button>
  </h3>
  <div
    role="region"
    id="section-1"
    aria-labelledby="accordion-header-1"
  >
    Section 1 content...
  </div>

  <h3>
    <button
      type="button"
      aria-expanded="false"
      aria-controls="section-2"
      id="accordion-header-2"
    >
      Section 2
    </button>
  </h3>
  <div
    role="region"
    id="section-2"
    aria-labelledby="accordion-header-2"
    hidden
  >
    Section 2 content...
  </div>
</div>
```

---

### Tooltip

```html
<button
  type="button"
  aria-describedby="tooltip-1"
>
  Help
</button>

<div
  role="tooltip"
  id="tooltip-1"
  hidden
>
  Click here for more information
</div>
```

**Note:** For interactive content, use a disclosure or dialog instead.

---

### Alert / Status Messages

```html
<!-- Alert (important, interruptive) -->
<div role="alert">
  Error: Please enter a valid email address.
</div>

<!-- Status (polite update) -->
<div role="status" aria-live="polite">
  3 items in cart
</div>

<!-- Live region (for dynamic content) -->
<div aria-live="polite" aria-atomic="true">
  <!-- Content updates announced to screen readers -->
</div>
```

---

### Combobox (Autocomplete)

```html
<div class="combobox">
  <label for="search-input">Search</label>
  <input
    type="text"
    id="search-input"
    role="combobox"
    aria-autocomplete="list"
    aria-expanded="false"
    aria-controls="search-listbox"
    aria-activedescendant=""
  >

  <ul
    role="listbox"
    id="search-listbox"
    hidden
  >
    <li role="option" id="option-1">Option 1</li>
    <li role="option" id="option-2">Option 2</li>
    <li role="option" id="option-3" aria-selected="true">Option 3</li>
  </ul>
</div>
```

**Update `aria-activedescendant` to the ID of the highlighted option.**

---

### Progress / Loading

```html
<!-- Determinate progress -->
<div
  role="progressbar"
  aria-valuenow="75"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-label="Upload progress"
>
  75%
</div>

<!-- Indeterminate loading -->
<div
  role="status"
  aria-label="Loading"
>
  <span class="spinner" aria-hidden="true"></span>
  <span class="sr-only">Loading...</span>
</div>
```

---

## Common ARIA Attributes

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `aria-label` | Accessible name | `aria-label="Close"` |
| `aria-labelledby` | Name from element | `aria-labelledby="heading-1"` |
| `aria-describedby` | Description | `aria-describedby="hint-1"` |
| `aria-expanded` | Open/closed state | `aria-expanded="true"` |
| `aria-controls` | Controlled element | `aria-controls="menu-1"` |
| `aria-hidden` | Hide from AT | `aria-hidden="true"` |
| `aria-live` | Announce updates | `aria-live="polite"` |
| `aria-pressed` | Toggle state | `aria-pressed="false"` |
| `aria-selected` | Selection state | `aria-selected="true"` |
| `aria-current` | Current item | `aria-current="page"` |

## Screen Reader Only Text

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

## Testing

1. **Keyboard only**: Tab through, use arrows, Enter, Escape
2. **Screen reader**: Test with VoiceOver (Mac), NVDA (Windows), or JAWS
3. **Check announcements**: Are labels, states, and changes announced?
4. **axe DevTools**: Run automated accessibility audit
