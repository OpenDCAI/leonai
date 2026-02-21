---
name: motion-scale
description: Generates animation duration, easing curves, and delay tokens with prefers-reduced-motion support. Use when creating transition timing, animation speed, or motion systems. Outputs CSS, Tailwind, or JSON.
---

# Motion Scale Generator

## Overview

Generate consistent animation and transition tokens for duration, easing, and delay. Creates a motion system that feels cohesive and respects user preferences for reduced motion.

## When to Use

- Setting up animation tokens for a new project
- Standardizing transition timing across components
- Replacing hardcoded animation values
- Implementing reduced motion support
- Building micro-interaction patterns

## Quick Reference: Duration Scale

| Token | Value | Use Case |
|-------|-------|----------|
| `instant` | 0ms | Immediate, no animation |
| `fastest` | 50ms | Micro-feedback (ripples, highlights) |
| `fast` | 100ms | Hover, focus, small changes |
| `normal` | 200ms | Most transitions, toggles |
| `slow` | 300ms | Modals, drawers, reveals |
| `slower` | 400ms | Page transitions, complex sequences |
| `slowest` | 500ms | Elaborate animations, onboarding |

## Quick Reference: Easing Curves

| Token | Curve | Use Case |
|-------|-------|----------|
| `linear` | `linear` | Progress bars, looping |
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Exit animations |
| `ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Enter animations (most common) |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Move, resize, continuous |
| `ease-bounce` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Playful, attention |
| `ease-elastic` | `cubic-bezier(0.68, -0.55, 0.27, 1.55)` | Springy, overshoot |

## The Process

1. **Choose duration scale**: How many steps? (5-7 typical)
2. **Define base duration**: 200ms is standard baseline
3. **Select ratio**: How durations scale (1.5x or 2x)
4. **Pick easing curves**: Standard set + any special curves
5. **Create semantic aliases**: Map to component behaviors
6. **Add reduced motion**: Respect user preferences
7. **Choose format**: CSS, Tailwind, or JSON

## Output Formats

**CSS Custom Properties:**
```css
:root {
  /* ===== Durations ===== */
  --duration-0: 0ms;
  --duration-50: 50ms;
  --duration-100: 100ms;
  --duration-150: 150ms;
  --duration-200: 200ms;
  --duration-300: 300ms;
  --duration-400: 400ms;
  --duration-500: 500ms;
  --duration-700: 700ms;
  --duration-1000: 1000ms;

  /* Named aliases */
  --duration-instant: var(--duration-0);
  --duration-fastest: var(--duration-50);
  --duration-fast: var(--duration-100);
  --duration-normal: var(--duration-200);
  --duration-slow: var(--duration-300);
  --duration-slower: var(--duration-500);
  --duration-slowest: var(--duration-700);

  /* ===== Easings ===== */
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

  /* Expressive easings */
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-elastic: cubic-bezier(0.68, -0.55, 0.27, 1.55);
  --ease-snap: cubic-bezier(0.2, 0, 0, 1);

  /* Deceleration/Acceleration (Material Design style) */
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);
  --ease-accelerate: cubic-bezier(0.4, 0, 1, 1);
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);

  /* ===== Delays ===== */
  --delay-none: 0ms;
  --delay-short: 50ms;
  --delay-medium: 100ms;
  --delay-long: 200ms;

  /* Stagger delays for sequential animations */
  --delay-stagger-1: 0ms;
  --delay-stagger-2: 50ms;
  --delay-stagger-3: 100ms;
  --delay-stagger-4: 150ms;
  --delay-stagger-5: 200ms;

  /* ===== Semantic Transitions ===== */
  --transition-colors: color, background-color, border-color, fill, stroke;
  --transition-opacity: opacity;
  --transition-transform: transform;
  --transition-shadow: box-shadow;
  --transition-all: all;

  /* Component transitions */
  --transition-hover: var(--duration-fast) var(--ease-out);
  --transition-focus: var(--duration-fast) var(--ease-out);
  --transition-active: var(--duration-fastest) var(--ease-out);
  --transition-enter: var(--duration-normal) var(--ease-out);
  --transition-exit: var(--duration-fast) var(--ease-in);
  --transition-move: var(--duration-normal) var(--ease-in-out);
  --transition-expand: var(--duration-slow) var(--ease-out);
  --transition-collapse: var(--duration-normal) var(--ease-in);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-50: 0ms;
    --duration-100: 0ms;
    --duration-150: 0ms;
    --duration-200: 0ms;
    --duration-300: 0ms;
    --duration-400: 0ms;
    --duration-500: 0ms;
    --duration-700: 0ms;
    --duration-1000: 0ms;
  }
}

/* Alternative: Keep minimal motion */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fastest: 0ms;
    --duration-fast: 0ms;
    --duration-normal: 50ms;  /* Minimal feedback */
    --duration-slow: 50ms;
    --duration-slower: 100ms;
    --duration-slowest: 100ms;

    /* Disable expressive easings */
    --ease-bounce: var(--ease-out);
    --ease-elastic: var(--ease-out);
  }
}
```

**Tailwind Config:**
```js
module.exports = {
  theme: {
    extend: {
      transitionDuration: {
        '0': '0ms',
        '50': '50ms',
        '100': '100ms',
        '150': '150ms',
        '200': '200ms',
        '300': '300ms',
        '400': '400ms',
        '500': '500ms',
        '700': '700ms',
        '1000': '1000ms',
      },
      transitionTimingFunction: {
        'in': 'cubic-bezier(0.4, 0, 1, 1)',
        'out': 'cubic-bezier(0, 0, 0.2, 1)',
        'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'bounce': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'elastic': 'cubic-bezier(0.68, -0.55, 0.27, 1.55)',
        'snap': 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDelay: {
        '0': '0ms',
        '50': '50ms',
        '100': '100ms',
        '150': '150ms',
        '200': '200ms',
      },
      animation: {
        'fade-in': 'fade-in 200ms ease-out',
        'fade-out': 'fade-out 150ms ease-in',
        'slide-up': 'slide-up 200ms ease-out',
        'slide-down': 'slide-down 200ms ease-out',
        'scale-in': 'scale-in 200ms ease-out',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
};
```

**JSON Tokens:**
```json
{
  "motion": {
    "duration": {
      "0": { "value": "0ms", "type": "duration" },
      "50": { "value": "50ms", "type": "duration" },
      "100": { "value": "100ms", "type": "duration" },
      "200": { "value": "200ms", "type": "duration" },
      "300": { "value": "300ms", "type": "duration" },
      "500": { "value": "500ms", "type": "duration" }
    },
    "easing": {
      "linear": { "value": "linear", "type": "cubicBezier" },
      "ease-in": { "value": "cubic-bezier(0.4, 0, 1, 1)", "type": "cubicBezier" },
      "ease-out": { "value": "cubic-bezier(0, 0, 0.2, 1)", "type": "cubicBezier" },
      "ease-in-out": { "value": "cubic-bezier(0.4, 0, 0.2, 1)", "type": "cubicBezier" },
      "bounce": { "value": "cubic-bezier(0.34, 1.56, 0.64, 1)", "type": "cubicBezier" }
    },
    "delay": {
      "none": { "value": "0ms", "type": "duration" },
      "short": { "value": "50ms", "type": "duration" },
      "medium": { "value": "100ms", "type": "duration" }
    }
  }
}
```

---

## Easing Curve Reference

### Standard Curves

```
ease-out (enter/appear):
    ●━━━━━━━━━━━━━━━━━━●
    Fast start, gentle stop
    Best for: Elements entering view

ease-in (exit/leave):
    ●━━━━━━━━━━━━━━━━━━●
    Gentle start, fast end
    Best for: Elements leaving view

ease-in-out (move/resize):
    ●━━━━━━━━━━━━━━━━━━●
    Gentle start and end
    Best for: Elements moving position

linear (progress):
    ●━━━━━━━━━━━━━━━━━━●
    Constant speed
    Best for: Progress bars, spinners
```

### Expressive Curves

```
bounce (playful):
    ●━━━━━━━━╮
            ╰━━━●
    Overshoots then settles
    Best for: Notifications, confirmations

elastic (springy):
    ●━━━╮   ╭━╮
        ╰━━━╯ ╰●
    Oscillates before settling
    Best for: Attention, drag-and-drop

snap (decisive):
    ●━━━━━━━━━━━━━━━━●
    Very fast deceleration
    Best for: Snapping, selections
```

### Custom Curve Creation

```css
/*
  cubic-bezier(x1, y1, x2, y2)

  x1, y1 = First control point (affects start)
  x2, y2 = Second control point (affects end)

  y values > 1 = overshoot
  y values < 0 = anticipation
*/

/* Dramatic entrance */
--ease-dramatic: cubic-bezier(0.2, 0.8, 0.2, 1);

/* Snappy with slight overshoot */
--ease-snappy: cubic-bezier(0.2, 1.2, 0.3, 1);

/* Gentle float */
--ease-float: cubic-bezier(0.4, 0.2, 0.2, 1);
```

---

## Component Patterns

### Button Hover

```css
.button {
  transition:
    background-color var(--transition-hover),
    transform var(--transition-active);
}

.button:hover {
  background-color: var(--color-primary-600);
}

.button:active {
  transform: scale(0.98);
}
```

### Modal Enter/Exit

```css
.modal-backdrop {
  transition: opacity var(--duration-normal) var(--ease-out);
}

.modal-content {
  transition:
    opacity var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out);
}

/* Enter */
.modal-backdrop.entering { opacity: 0; }
.modal-backdrop.entered { opacity: 1; }
.modal-content.entering { opacity: 0; transform: scale(0.95) translateY(10px); }
.modal-content.entered { opacity: 1; transform: scale(1) translateY(0); }

/* Exit (faster) */
.modal-backdrop.exiting {
  opacity: 0;
  transition-duration: var(--duration-fast);
}
.modal-content.exiting {
  opacity: 0;
  transform: scale(0.95);
  transition-duration: var(--duration-fast);
}
```

### Dropdown Menu

```css
.dropdown-menu {
  transform-origin: top;
  transition:
    opacity var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.dropdown-menu[data-state="closed"] {
  opacity: 0;
  transform: scaleY(0.9);
  pointer-events: none;
}

.dropdown-menu[data-state="open"] {
  opacity: 1;
  transform: scaleY(1);
}
```

### Staggered List Animation

```css
.list-item {
  opacity: 0;
  transform: translateY(10px);
  animation: slide-up var(--duration-normal) var(--ease-out) forwards;
}

.list-item:nth-child(1) { animation-delay: var(--delay-stagger-1); }
.list-item:nth-child(2) { animation-delay: var(--delay-stagger-2); }
.list-item:nth-child(3) { animation-delay: var(--delay-stagger-3); }
.list-item:nth-child(4) { animation-delay: var(--delay-stagger-4); }
.list-item:nth-child(5) { animation-delay: var(--delay-stagger-5); }

@keyframes slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### Loading Spinner

```css
.spinner {
  animation: spin var(--duration-1000) var(--ease-linear) infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Pulsing loader */
.pulse {
  animation: pulse var(--duration-700) var(--ease-in-out) infinite alternate;
}

@keyframes pulse {
  0% { opacity: 0.4; transform: scale(0.95); }
  100% { opacity: 1; transform: scale(1); }
}
```

### Skeleton Loading

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-gray-200) 0%,
    var(--color-gray-100) 50%,
    var(--color-gray-200) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s var(--ease-in-out) infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## Reduced Motion

### Strategy 1: Remove All Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Strategy 2: Reduce, Don't Remove

```css
@media (prefers-reduced-motion: reduce) {
  :root {
    /* Keep brief transitions for feedback */
    --duration-fast: 0ms;
    --duration-normal: 50ms;
    --duration-slow: 100ms;

    /* Simplify easings */
    --ease-bounce: var(--ease-out);
    --ease-elastic: var(--ease-out);
  }

  /* Disable parallax, auto-play, infinite loops */
  .parallax { transform: none !important; }
  .auto-animate { animation: none !important; }
}
```

### Strategy 3: Provide Alternatives

```css
/* Full motion */
.card-enter {
  animation: slide-up var(--duration-normal) var(--ease-out);
}

/* Reduced: fade only, no movement */
@media (prefers-reduced-motion: reduce) {
  .card-enter {
    animation: fade-in var(--duration-fast) var(--ease-out);
  }
}
```

---

## Duration Guidelines

| Duration | Feel | Use For |
|----------|------|---------|
| 0-50ms | Instant | Ripples, micro-feedback |
| 50-100ms | Snappy | Hover states, focus, toggles |
| 100-200ms | Quick | Most UI transitions |
| 200-300ms | Smooth | Modals, panels, reveals |
| 300-500ms | Deliberate | Page transitions, onboarding |
| 500ms+ | Slow | Complex sequences, emphasis |

**Rule of thumb:**
- Smaller elements = faster (50-150ms)
- Larger elements = slower (200-400ms)
- User-triggered = fast (100-200ms)
- System-triggered = can be slower (200-400ms)

---

## Testing Checklist

- [ ] Transitions feel smooth, not jarring
- [ ] Hover/focus feedback is immediate (<150ms)
- [ ] Modals/drawers don't feel sluggish
- [ ] Animations enhance, don't block interaction
- [ ] `prefers-reduced-motion` is respected
- [ ] No layout shift during animations
- [ ] Animations work at 60fps
- [ ] Consistent timing across similar interactions
