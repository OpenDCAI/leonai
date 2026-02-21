---
name: layout-primitives
description: Builds composable layout components (Stack, Cluster, Grid, Sidebar, Center, Cover). Use when creating layout systems, spacing compositions, or Every Layout-style intrinsic design patterns that adapt without breakpoints.
---

# Layout Primitives

## Overview

Build reusable layout primitives (Stack, Cluster, Sidebar, Grid) that compose to create any layout. Based on Every Layout patterns - intrinsic design that adapts without breakpoints.

## When to Use

- Setting up layout components for a design system
- Creating composable layout building blocks
- Replacing repetitive flexbox/grid patterns
- Building layouts that adapt without media queries
- Implementing consistent spacing throughout an app

## Quick Reference: Core Primitives

| Primitive | Purpose | Primary CSS |
|-----------|---------|-------------|
| Stack | Vertical spacing | `flex-direction: column` + gap |
| Cluster | Horizontal wrapping groups | `flex-wrap: wrap` + gap |
| Sidebar | Two-column with minmax | `flex-wrap: wrap` + basis |
| Switcher | Stack/row based on width | `flex-wrap` + container query |
| Center | Centered max-width | `max-width` + `margin-inline: auto` |
| Cover | Vertically centered hero | `min-height` + flex |
| Grid | Auto-fill responsive grid | `grid-template-columns: repeat(auto-fill)` |
| Frame | Aspect ratio container | `aspect-ratio` |
| Reel | Horizontal scroll | `overflow-x: auto` + `flex-wrap: nowrap` |
| Box | Spacing/padding container | `padding` |

---

## Stack

Vertical rhythm with consistent spacing.

### CSS

```css
.stack {
  display: flex;
  flex-direction: column;
}

.stack > * + * {
  margin-block-start: var(--stack-space, 1.5rem);
}

/* Or with gap (modern, simpler) */
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--stack-space, 1.5rem);
}

/* Variants */
.stack[data-space="sm"] { --stack-space: 0.5rem; }
.stack[data-space="md"] { --stack-space: 1rem; }
.stack[data-space="lg"] { --stack-space: 2rem; }
.stack[data-space="xl"] { --stack-space: 4rem; }
```

### React Component

```tsx
interface StackProps {
  space?: 'sm' | 'md' | 'lg' | 'xl';
  as?: React.ElementType;
  children: React.ReactNode;
  className?: string;
}

export function Stack({
  space = 'md',
  as: Component = 'div',
  children,
  className,
}: StackProps) {
  return (
    <Component
      className={clsx('stack', className)}
      data-space={space}
    >
      {children}
    </Component>
  );
}

// Usage
<Stack space="lg">
  <h1>Title</h1>
  <p>Paragraph</p>
  <p>Another paragraph</p>
</Stack>
```

### Tailwind Utility

```tsx
// Tailwind approach
<div className="flex flex-col gap-4">
  {/* children */}
</div>

// With custom component
function Stack({ space = 4, children }) {
  return (
    <div className={`flex flex-col gap-${space}`}>
      {children}
    </div>
  );
}
```

---

## Cluster

Horizontal grouping that wraps naturally.

### CSS

```css
.cluster {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cluster-space, 1rem);
  align-items: var(--cluster-align, center);
  justify-content: var(--cluster-justify, flex-start);
}

/* Variants */
.cluster[data-justify="center"] { justify-content: center; }
.cluster[data-justify="space-between"] { justify-content: space-between; }
.cluster[data-justify="end"] { justify-content: flex-end; }

.cluster[data-align="start"] { align-items: flex-start; }
.cluster[data-align="end"] { align-items: flex-end; }
.cluster[data-align="stretch"] { align-items: stretch; }
```

### React Component

```tsx
interface ClusterProps {
  space?: 'xs' | 'sm' | 'md' | 'lg';
  justify?: 'start' | 'center' | 'end' | 'space-between';
  align?: 'start' | 'center' | 'end' | 'stretch';
  children: React.ReactNode;
  className?: string;
}

export function Cluster({
  space = 'md',
  justify = 'start',
  align = 'center',
  children,
  className,
}: ClusterProps) {
  return (
    <div
      className={clsx('cluster', className)}
      data-space={space}
      data-justify={justify}
      data-align={align}
    >
      {children}
    </div>
  );
}

// Usage
<Cluster space="sm" justify="space-between">
  <Tag>React</Tag>
  <Tag>TypeScript</Tag>
  <Tag>CSS</Tag>
</Cluster>
```

---

## Sidebar

Two-column layout with a sidebar that stacks below breakpoint.

### CSS

```css
.with-sidebar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sidebar-gap, 1rem);
}

.with-sidebar > :first-child {
  flex-basis: var(--sidebar-width, 20rem);
  flex-grow: 1;
}

.with-sidebar > :last-child {
  flex-basis: 0;
  flex-grow: 999;
  min-inline-size: var(--sidebar-content-min, 50%);
}

/* Sidebar on right */
.with-sidebar[data-side="right"] {
  flex-direction: row-reverse;
}
```

### React Component

```tsx
interface SidebarProps {
  sideWidth?: string;
  contentMin?: string;
  gap?: string;
  side?: 'left' | 'right';
  children: React.ReactNode;
}

export function Sidebar({
  sideWidth = '20rem',
  contentMin = '50%',
  gap = '1rem',
  side = 'left',
  children,
}: SidebarProps) {
  return (
    <div
      className="with-sidebar"
      style={{
        '--sidebar-width': sideWidth,
        '--sidebar-content-min': contentMin,
        '--sidebar-gap': gap,
      } as React.CSSProperties}
      data-side={side}
    >
      {children}
    </div>
  );
}

// Usage
<Sidebar sideWidth="250px" contentMin="60%">
  <nav>Sidebar content</nav>
  <main>Main content</main>
</Sidebar>
```

---

## Switcher

Switches between horizontal and vertical based on available width.

### CSS

```css
.switcher {
  display: flex;
  flex-wrap: wrap;
  gap: var(--switcher-gap, 1rem);
}

.switcher > * {
  flex-grow: 1;
  flex-basis: calc((var(--switcher-threshold, 30rem) - 100%) * 999);
}

/* Limit number of items per row */
.switcher > :nth-last-child(n+4),
.switcher > :nth-last-child(n+4) ~ * {
  flex-basis: 100%;
}
```

### React Component

```tsx
interface SwitcherProps {
  threshold?: string;
  gap?: string;
  limit?: number;
  children: React.ReactNode;
}

export function Switcher({
  threshold = '30rem',
  gap = '1rem',
  limit = 4,
  children,
}: SwitcherProps) {
  return (
    <div
      className="switcher"
      style={{
        '--switcher-threshold': threshold,
        '--switcher-gap': gap,
      } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

// Usage - items stay horizontal until container < 30rem
<Switcher threshold="500px">
  <Card>First</Card>
  <Card>Second</Card>
  <Card>Third</Card>
</Switcher>
```

---

## Center

Horizontally center with max-width.

### CSS

```css
.center {
  box-sizing: content-box;
  max-inline-size: var(--center-max, 60ch);
  margin-inline: auto;
  padding-inline: var(--center-gutter, 1rem);
}

/* Text centering variant */
.center[data-text] {
  text-align: center;
}

/* Intrinsic centering (shrink-wrap) */
.center[data-intrinsic] {
  display: flex;
  flex-direction: column;
  align-items: center;
}
```

### React Component

```tsx
interface CenterProps {
  max?: string;
  gutter?: string;
  text?: boolean;
  intrinsic?: boolean;
  children: React.ReactNode;
}

export function Center({
  max = '60ch',
  gutter = '1rem',
  text = false,
  intrinsic = false,
  children,
}: CenterProps) {
  return (
    <div
      className="center"
      style={{
        '--center-max': max,
        '--center-gutter': gutter,
      } as React.CSSProperties}
      data-text={text || undefined}
      data-intrinsic={intrinsic || undefined}
    >
      {children}
    </div>
  );
}

// Usage
<Center max="800px">
  <article>Centered content with max width</article>
</Center>
```

---

## Cover

Full-height section with vertically centered content.

### CSS

```css
.cover {
  display: flex;
  flex-direction: column;
  min-block-size: var(--cover-min-height, 100vh);
  padding: var(--cover-padding, 1rem);
}

.cover > * {
  margin-block: var(--cover-space, 1rem);
}

.cover > :first-child:not([data-centered]) {
  margin-block-start: 0;
}

.cover > :last-child:not([data-centered]) {
  margin-block-end: 0;
}

.cover > [data-centered] {
  margin-block: auto;
}
```

### React Component

```tsx
interface CoverProps {
  minHeight?: string;
  padding?: string;
  children: React.ReactNode;
}

export function Cover({ minHeight = '100vh', padding = '1rem', children }: CoverProps) {
  return (
    <div
      className="cover"
      style={{
        '--cover-min-height': minHeight,
        '--cover-padding': padding,
      } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

export function CoverCenter({ children }: { children: React.ReactNode }) {
  return <div data-centered>{children}</div>;
}

// Usage - header at top, content centered, footer at bottom
<Cover>
  <header>Logo</header>
  <CoverCenter>
    <h1>Hero Content</h1>
  </CoverCenter>
  <footer>Footer</footer>
</Cover>
```

---

## Grid

Responsive grid without media queries.

### CSS

```css
.grid {
  display: grid;
  gap: var(--grid-gap, 1rem);
  grid-template-columns: repeat(
    auto-fill,
    minmax(min(var(--grid-min, 250px), 100%), 1fr)
  );
}

/* Fixed columns variant */
.grid[data-columns="2"] {
  grid-template-columns: repeat(2, 1fr);
}
.grid[data-columns="3"] {
  grid-template-columns: repeat(3, 1fr);
}
.grid[data-columns="4"] {
  grid-template-columns: repeat(4, 1fr);
}
```

### React Component

```tsx
interface GridProps {
  min?: string;
  gap?: string;
  children: React.ReactNode;
}

export function Grid({ min = '250px', gap = '1rem', children }: GridProps) {
  return (
    <div
      className="grid"
      style={{
        '--grid-min': min,
        '--grid-gap': gap,
      } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

// Usage
<Grid min="300px" gap="1.5rem">
  <Card>1</Card>
  <Card>2</Card>
  <Card>3</Card>
  <Card>4</Card>
</Grid>
```

---

## Frame

Aspect ratio container for media.

### CSS

```css
.frame {
  aspect-ratio: var(--frame-ratio, 16 / 9);
  overflow: hidden;
}

.frame > img,
.frame > video,
.frame > iframe {
  inline-size: 100%;
  block-size: 100%;
  object-fit: cover;
}

/* Common ratios */
.frame[data-ratio="1:1"] { --frame-ratio: 1; }
.frame[data-ratio="4:3"] { --frame-ratio: 4 / 3; }
.frame[data-ratio="16:9"] { --frame-ratio: 16 / 9; }
.frame[data-ratio="21:9"] { --frame-ratio: 21 / 9; }
```

### React Component

```tsx
type FrameRatio = '1:1' | '4:3' | '16:9' | '21:9' | string;

interface FrameProps {
  ratio?: FrameRatio;
  children: React.ReactNode;
}

const ratioMap: Record<string, string> = {
  '1:1': '1',
  '4:3': '4 / 3',
  '16:9': '16 / 9',
  '21:9': '21 / 9',
};

export function Frame({ ratio = '16:9', children }: FrameProps) {
  return (
    <div
      className="frame"
      style={{
        '--frame-ratio': ratioMap[ratio] || ratio,
      } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

// Usage
<Frame ratio="16:9">
  <img src="/hero.jpg" alt="Hero" />
</Frame>
```

---

## Reel

Horizontal scrolling container.

### CSS

```css
.reel {
  display: flex;
  gap: var(--reel-gap, 1rem);
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-color: var(--color-border-primary) transparent;
}

.reel > * {
  flex: 0 0 var(--reel-item-width, auto);
}

/* Hide scrollbar (optional) */
.reel[data-hide-scrollbar] {
  scrollbar-width: none;
}

.reel[data-hide-scrollbar]::-webkit-scrollbar {
  display: none;
}

/* Snap scrolling */
.reel[data-snap] {
  scroll-snap-type: x mandatory;
  scroll-padding-inline: var(--reel-gap, 1rem);
}

.reel[data-snap] > * {
  scroll-snap-align: start;
}
```

### React Component

```tsx
interface ReelProps {
  gap?: string;
  itemWidth?: string;
  snap?: boolean;
  hideScrollbar?: boolean;
  children: React.ReactNode;
}

export function Reel({
  gap = '1rem',
  itemWidth,
  snap = false,
  hideScrollbar = false,
  children,
}: ReelProps) {
  return (
    <div
      className="reel"
      style={{
        '--reel-gap': gap,
        '--reel-item-width': itemWidth,
      } as React.CSSProperties}
      data-snap={snap || undefined}
      data-hide-scrollbar={hideScrollbar || undefined}
    >
      {children}
    </div>
  );
}

// Usage
<Reel itemWidth="300px" snap>
  <Card>1</Card>
  <Card>2</Card>
  <Card>3</Card>
  <Card>4</Card>
</Reel>
```

---

## Box

Padding and background container.

### CSS

```css
.box {
  padding: var(--box-padding, 1rem);
  border: var(--box-border, 0);
  background-color: var(--box-bg, transparent);
  border-radius: var(--box-radius, 0);
}

/* Invert colors */
.box[data-invert] {
  background-color: var(--color-bg-inverse);
  color: var(--color-text-inverse);
}
```

### React Component

```tsx
interface BoxProps {
  padding?: string;
  bg?: string;
  invert?: boolean;
  children: React.ReactNode;
}

export function Box({ padding = '1rem', bg, invert, children }: BoxProps) {
  return (
    <div
      className="box"
      style={{
        '--box-padding': padding,
        '--box-bg': bg,
      } as React.CSSProperties}
      data-invert={invert || undefined}
    >
      {children}
    </div>
  );
}
```

---

## Composition Examples

### Page Layout

```tsx
<Stack space="xl">
  <Center max="1200px">
    <header>
      <Cluster justify="space-between">
        <Logo />
        <nav>
          <Cluster space="md">
            <a href="#">Home</a>
            <a href="#">About</a>
            <a href="#">Contact</a>
          </Cluster>
        </nav>
      </Cluster>
    </header>
  </Center>

  <Cover minHeight="80vh">
    <CoverCenter>
      <Center text>
        <Stack space="lg">
          <h1>Welcome</h1>
          <p>Hero content here</p>
        </Stack>
      </Center>
    </CoverCenter>
  </Cover>

  <Center max="1200px">
    <Sidebar sideWidth="300px">
      <aside>
        <Stack space="md">
          <h2>Sidebar</h2>
          {/* sidebar content */}
        </Stack>
      </aside>
      <main>
        <Stack space="lg">
          <Grid min="300px">
            <Card>1</Card>
            <Card>2</Card>
            <Card>3</Card>
          </Grid>
        </Stack>
      </main>
    </Sidebar>
  </Center>
</Stack>
```

### Card Grid

```tsx
<Grid min="280px" gap="1.5rem">
  {items.map(item => (
    <Box key={item.id} padding="1.5rem">
      <Stack space="md">
        <Frame ratio="16:9">
          <img src={item.image} alt="" />
        </Frame>
        <h3>{item.title}</h3>
        <p>{item.description}</p>
        <Cluster justify="space-between">
          <span>{item.date}</span>
          <a href={item.url}>Read more</a>
        </Cluster>
      </Stack>
    </Box>
  ))}
</Grid>
```

---

## Tailwind Implementation

```js
// tailwind.config.js - custom utilities
module.exports = {
  theme: {
    extend: {
      // Custom layout utilities can use @apply or plugins
    },
  },
  plugins: [
    function({ addComponents }) {
      addComponents({
        '.stack': {
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--stack-space, 1rem)',
        },
        '.cluster': {
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--cluster-space, 1rem)',
          alignItems: 'center',
        },
        // ... etc
      });
    },
  ],
};
```

Or use utility classes directly:

```html
<!-- Stack -->
<div class="flex flex-col gap-4">

<!-- Cluster -->
<div class="flex flex-wrap gap-2 items-center">

<!-- Center -->
<div class="max-w-prose mx-auto px-4">

<!-- Grid -->
<div class="grid gap-4 grid-cols-[repeat(auto-fill,minmax(250px,1fr))]">
```

---

## Resources

- Every Layout: https://every-layout.dev
- Intrinsic Web Design: https://www.youtube.com/watch?v=AMPKmh98XLY
- Layout Land: https://www.youtube.com/c/LayoutLand
