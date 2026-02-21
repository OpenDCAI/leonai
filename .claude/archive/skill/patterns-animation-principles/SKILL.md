---
name: animation-principles
description: Applies Disney's 12 animation principles to UI motion design. Use when improving animation quality, designing micro-interactions, creating easing curves, or making transitions feel natural and purposeful.
---

# Animation Principles for UI

## Overview

Apply Disney's 12 principles of animation to create UI motion that feels natural, purposeful, and delightful. These principles, developed in the 1930s for character animation, translate directly to modern interface design.

## When to Use

- Designing micro-interactions and transitions
- Making animations feel more natural and polished
- Reviewing animation quality in a design system
- Training team members on motion design fundamentals
- Creating animation guidelines for a design system

## Quick Reference: The 12 Principles

| Principle | UI Application | Priority |
|-----------|----------------|----------|
| Easing (Slow in/out) | All transitions | Essential |
| Anticipation | Button press, drag start | High |
| Follow-through | Modals, dropdowns, toasts | High |
| Secondary Action | Loading states, notifications | Medium |
| Timing | Duration based on distance/importance | Essential |
| Squash & Stretch | Buttons, toggles, playful UI | Medium |
| Staging | Focus attention, reduce distraction | High |
| Arc | Natural movement paths | Medium |
| Exaggeration | Emphasis, delight moments | Low |
| Solid Drawing | Consistent 3D perspective | Low |
| Appeal | Brand personality | Medium |
| Straight Ahead / Pose to Pose | Complex sequences | Low |

---

## 1. Easing (Slow In and Slow Out)

**Principle:** Objects don't start or stop instantly - they accelerate and decelerate.

**In UI:** Never use `linear` timing for UI animations. Use easing curves.

### CSS Implementation

```css
:root {
  /* Standard easing - use for most transitions */
  --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);      /* Decelerate */
  --ease-in: cubic-bezier(0.4, 0.0, 1, 1);         /* Accelerate */
  --ease-in-out: cubic-bezier(0.4, 0.0, 0.2, 1);   /* Both */

  /* Expressive easing - more personality */
  --ease-expressive: cubic-bezier(0.4, 0.14, 0.3, 1);

  /* Spring-like - for playful UI */
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-overshoot: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

/* ❌ Bad - robotic, unnatural */
.modal {
  transition: opacity 200ms linear;
}

/* ✅ Good - natural deceleration */
.modal {
  transition: opacity 200ms var(--ease-out);
}
```

### When to Use Each

| Easing | Use Case |
|--------|----------|
| ease-out | Elements entering (modals, dropdowns, toasts) |
| ease-in | Elements exiting, leaving viewport |
| ease-in-out | Elements that stay on screen (position changes, morphing) |
| bounce/overshoot | Playful interactions, success states, toggle switches |

---

## 2. Anticipation

**Principle:** Prepare the audience for an action before it happens.

**In UI:** Give users a hint that something is about to happen.

### Examples

```css
/* Button press - slight scale down before action */
.button:active {
  transform: scale(0.97);
  transition: transform 50ms var(--ease-in);
}

.button:not(:active) {
  transition: transform 150ms var(--ease-out);
}

/* Drag anticipation - lift before moving */
.draggable.is-lifting {
  transform: scale(1.02);
  box-shadow: var(--shadow-lg);
  transition: all 100ms var(--ease-out);
}

/* Pull-to-refresh - resistance before release */
.pull-indicator {
  transform: translateY(calc(var(--pull-distance) * 0.4));
  /* Rubber band effect - moves slower than finger */
}
```

### Swipe Action Anticipation

```css
/* Card swipe - tilt in direction of swipe */
.card.swiping-right {
  transform: translateX(var(--swipe-x)) rotate(calc(var(--swipe-x) * 0.05deg));
}
```

---

## 3. Follow-Through and Overlapping Action

**Principle:** Different parts of an object move at different rates; motion continues after the main action stops.

**In UI:** Elements don't stop all at once. Parts settle at different times.

### Modal with Follow-Through

```css
/* Backdrop and content animate separately */
.modal-backdrop {
  animation: fadeIn 200ms var(--ease-out);
}

.modal-content {
  animation: slideUp 300ms var(--ease-out);
  animation-delay: 50ms; /* Slightly after backdrop */
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

### Staggered List Items

```css
/* Items enter one after another */
.list-item {
  animation: fadeSlideIn 300ms var(--ease-out) both;
}

.list-item:nth-child(1) { animation-delay: 0ms; }
.list-item:nth-child(2) { animation-delay: 50ms; }
.list-item:nth-child(3) { animation-delay: 100ms; }
.list-item:nth-child(4) { animation-delay: 150ms; }

/* Or dynamically with CSS custom properties */
.list-item {
  animation-delay: calc(var(--index) * 50ms);
}
```

### React Implementation

```tsx
// Staggered children
function StaggeredList({ children }) {
  return (
    <div>
      {React.Children.map(children, (child, index) => (
        <div
          style={{ '--index': index } as React.CSSProperties}
          className="stagger-item"
        >
          {child}
        </div>
      ))}
    </div>
  );
}
```

---

## 4. Secondary Action

**Principle:** Additional animations that support the main action without distracting from it.

**In UI:** Subtle supporting animations that enhance the primary interaction.

### Examples

```css
/* Primary: checkbox fills. Secondary: subtle bounce */
.checkbox.checked .checkmark {
  animation: checkDraw 200ms var(--ease-out),
             checkBounce 300ms var(--ease-bounce) 150ms;
}

@keyframes checkDraw {
  from { stroke-dashoffset: 24; }
  to { stroke-dashoffset: 0; }
}

@keyframes checkBounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

/* Primary: notification appears. Secondary: icon pulses */
.notification {
  animation: slideIn 300ms var(--ease-out);
}

.notification .icon {
  animation: pulse 600ms var(--ease-in-out) 200ms;
}

/* Primary: button loading. Secondary: shimmer effect */
.button.loading::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255,255,255,0.2),
    transparent
  );
  animation: shimmer 1.5s infinite;
}
```

---

## 5. Timing

**Principle:** The speed of an action gives it meaning and weight.

**In UI:** Duration should match the perceived importance and physical distance.

### Duration Scale

```css
:root {
  /* Based on distance and importance */
  --duration-instant: 50ms;    /* Micro-feedback (hover color) */
  --duration-fast: 100ms;      /* Small movements (button press) */
  --duration-normal: 200ms;    /* Standard transitions */
  --duration-slow: 300ms;      /* Larger movements (modal enter) */
  --duration-slower: 500ms;    /* Complex animations */
}
```

### Guidelines

| Animation Type | Duration | Example |
|---------------|----------|---------|
| Hover states | 100-150ms | Button background change |
| Small reveals | 150-200ms | Dropdown, tooltip |
| Medium reveals | 200-300ms | Modal, sidebar |
| Large reveals | 300-500ms | Page transitions |
| Looping | 1000-2000ms | Loading spinners |

### Distance-Based Timing

```css
/* Shorter distance = shorter duration */
.toast {
  /* Slides 100px */
  transition: transform 200ms var(--ease-out);
}

.modal {
  /* Slides 200px + scales */
  transition: all 300ms var(--ease-out);
}

.page-transition {
  /* Full viewport */
  transition: transform 400ms var(--ease-in-out);
}
```

---

## 6. Squash and Stretch

**Principle:** Objects deform when force is applied, showing weight and flexibility.

**In UI:** Use sparingly for playful, elastic feeling. Great for toggles, buttons, icons.

### Toggle Switch

```css
.toggle-thumb {
  transition: transform 200ms var(--ease-bounce);
}

.toggle.checked .toggle-thumb {
  transform: translateX(20px) scaleX(1.1);
}

/* Or with keyframes for more control */
@keyframes toggleOn {
  0% { transform: translateX(0) scaleX(1); }
  30% { transform: translateX(5px) scaleX(1.2); }
  60% { transform: translateX(22px) scaleX(0.9); }
  100% { transform: translateX(20px) scaleX(1); }
}
```

### Button Press

```css
.button:active {
  transform: scaleY(0.95) scaleX(1.02);
  transition: transform 50ms var(--ease-in);
}
```

### Bouncy Icon

```css
@keyframes bounce {
  0%, 100% { transform: scaleY(1) scaleX(1); }
  25% { transform: scaleY(0.9) scaleX(1.1); }
  50% { transform: scaleY(1.1) scaleX(0.9); }
  75% { transform: scaleY(0.95) scaleX(1.05); }
}

.icon-bounce {
  animation: bounce 500ms var(--ease-out);
}
```

---

## 7. Staging

**Principle:** Direct the audience's attention to what matters.

**In UI:** Use animation to focus attention and reduce cognitive load.

### Focus Attention

```css
/* Dim everything except the focused element */
.tour-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  animation: fadeIn 300ms var(--ease-out);
}

.tour-highlight {
  position: relative;
  z-index: 1000;
  box-shadow: 0 0 0 4px var(--color-primary);
  animation: pulse-ring 2s infinite;
}

/* Reduce motion elsewhere during important action */
.modal-open .background-content {
  filter: blur(2px);
  transform: scale(0.98);
}
```

### Sequential Reveals

```css
/* Reveal content in order of importance */
.hero-title {
  animation: fadeSlideUp 400ms var(--ease-out);
}

.hero-subtitle {
  animation: fadeSlideUp 400ms var(--ease-out) 100ms both;
}

.hero-cta {
  animation: fadeSlideUp 400ms var(--ease-out) 200ms both;
}
```

---

## 8. Arc

**Principle:** Natural movements follow curved paths, not straight lines.

**In UI:** Use arcs for movements that should feel organic.

### Curved Motion Path

```css
/* Element follows arc using offset-path */
.notification-badge {
  offset-path: path('M 0 0 Q 50 -30 100 0');
  animation: followArc 300ms var(--ease-out);
}

@keyframes followArc {
  from { offset-distance: 0%; }
  to { offset-distance: 100%; }
}

/* Or simulate with transform */
@keyframes arcMove {
  0% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(50px, -20px); /* Peak of arc */
  }
  100% {
    transform: translate(100px, 0);
  }
}
```

### Floating Elements

```css
/* Gentle floating with curved motion */
@keyframes float {
  0%, 100% {
    transform: translateY(0) translateX(0);
  }
  25% {
    transform: translateY(-10px) translateX(5px);
  }
  75% {
    transform: translateY(-10px) translateX(-5px);
  }
}

.floating-element {
  animation: float 4s ease-in-out infinite;
}
```

---

## 9. Exaggeration

**Principle:** Push animations beyond realism to make them clearer and more impactful.

**In UI:** Use for moments of delight, celebration, or emphasis. Use sparingly.

### Success Celebration

```css
@keyframes celebrate {
  0% { transform: scale(1); }
  25% { transform: scale(1.3) rotate(-5deg); }
  50% { transform: scale(1.2) rotate(5deg); }
  75% { transform: scale(1.1) rotate(-2deg); }
  100% { transform: scale(1) rotate(0); }
}

.success-icon {
  animation: celebrate 500ms var(--ease-out);
}

/* Confetti burst */
.confetti-particle {
  animation:
    confettiFall 1s var(--ease-in) forwards,
    confettiSpin 1s linear infinite;
}
```

### Error Shake

```css
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-10px); }
  40% { transform: translateX(10px); }
  60% { transform: translateX(-5px); }
  80% { transform: translateX(5px); }
}

.input.error {
  animation: shake 400ms var(--ease-out);
}
```

---

## 10. Solid Drawing (3D Consistency)

**Principle:** Maintain consistent volume and perspective.

**In UI:** Keep transforms consistent. If something has depth, maintain it throughout animation.

```css
/* Consistent perspective origin */
.card-flip {
  perspective: 1000px;
}

.card-flip .card {
  transform-style: preserve-3d;
  transition: transform 600ms var(--ease-in-out);
}

.card-flip:hover .card {
  transform: rotateY(180deg);
}

/* Maintain shadow consistency with elevation */
.card {
  transition: transform 200ms, box-shadow 200ms;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg); /* Shadow grows with elevation */
}
```

---

## 11. Appeal

**Principle:** Create animations that are pleasing and match the personality.

**In UI:** Animation should reflect brand personality.

| Brand Personality | Animation Style |
|-------------------|-----------------|
| Professional | Subtle, quick, minimal easing |
| Playful | Bouncy, squash/stretch, overshoot |
| Elegant | Slow, smooth, gentle easing |
| Energetic | Fast, snappy, exaggerated |

```css
/* Professional - subtle and quick */
.pro-button:hover {
  background: var(--color-primary-hover);
  transition: background 150ms ease-out;
}

/* Playful - bouncy and fun */
.playful-button:hover {
  transform: scale(1.05);
  transition: transform 300ms var(--ease-bounce);
}

/* Elegant - slow and smooth */
.elegant-button:hover {
  opacity: 0.9;
  transition: opacity 400ms ease-in-out;
}
```

---

## 12. Straight Ahead vs Pose to Pose

**Principle:** Two approaches to creating animation sequences.

**In UI:**
- **Pose to pose (keyframes):** Define key states, let CSS interpolate
- **Straight ahead (JS):** Calculate each frame, good for physics

### Pose to Pose (CSS Keyframes)

```css
/* Define key poses, browser interpolates between */
@keyframes modalEnter {
  0% {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
```

### Straight Ahead (JavaScript/Physics)

```tsx
// Physics-based - calculate each frame
import { useSpring, animated } from '@react-spring/web';

function BouncyCard() {
  const [props, api] = useSpring(() => ({
    scale: 1,
    config: { tension: 300, friction: 10 },
  }));

  return (
    <animated.div
      style={{ transform: props.scale.to(s => `scale(${s})`) }}
      onMouseEnter={() => api.start({ scale: 1.05 })}
      onMouseLeave={() => api.start({ scale: 1 })}
    />
  );
}
```

---

## Accessibility: Reduced Motion

Always respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Or selectively keep essential motion */
@media (prefers-reduced-motion: reduce) {
  .decorative-animation {
    animation: none;
  }

  /* Keep functional feedback but make instant */
  .button {
    transition-duration: 0ms;
  }
}
```

---

## Animation Audit Checklist

- [ ] Does the animation use appropriate easing (not linear)?
- [ ] Is the timing appropriate for the action's importance?
- [ ] Does it guide attention effectively (staging)?
- [ ] Are complex animations broken into follow-through parts?
- [ ] Does it match the brand's personality?
- [ ] Is reduced-motion respected?
- [ ] Is it adding value or just decoration?
