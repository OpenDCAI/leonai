---
name: icon-system
description: Implements scalable icon systems with SVG sprites or React/Vue components. Use when setting up icon libraries, creating icon sizing tokens, optimizing SVGs, or building accessible icon buttons.
---

# Icon System

## Overview

Implement a scalable icon system with SVG sprites or icon components, proper sizing tokens, consistent stroke widths, and accessibility. Covers both sprite-based and component-based approaches.

## When to Use

- Setting up icons for a new design system
- Converting icon fonts to SVG
- Creating an icon component library
- Establishing icon sizing standards
- Making icons accessible

## Quick Reference: Approaches

| Approach | Best For | Bundle Size | Styling |
|----------|----------|-------------|---------|
| SVG Sprite | Large icon sets, caching | One request | CSS limited |
| Inline SVG Components | Tree-shaking, full control | Per-icon | Full CSS |
| Icon Font | Legacy support | One request | Limited |
| External SVG | Simple sites | Per-icon | Limited |

## The Process

1. **Choose approach**: Sprite vs components based on project needs
2. **Define size scale**: Icon size tokens (xs, sm, md, lg, xl)
3. **Establish stroke width**: Consistent line weights
4. **Create component**: Wrapper with accessibility
5. **Build tooling**: Optimization, sprite generation

---

## Size Tokens

### Icon Size Scale

```css
:root {
  /* Icon sizes - match common UI patterns */
  --icon-size-xs: 0.75rem;   /* 12px - inline text */
  --icon-size-sm: 1rem;      /* 16px - small buttons */
  --icon-size-md: 1.25rem;   /* 20px - default */
  --icon-size-lg: 1.5rem;    /* 24px - large buttons */
  --icon-size-xl: 2rem;      /* 32px - feature icons */
  --icon-size-2xl: 2.5rem;   /* 40px - hero icons */
  --icon-size-3xl: 3rem;     /* 48px - illustrations */
}
```

### Tailwind Config

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      width: {
        'icon-xs': '0.75rem',
        'icon-sm': '1rem',
        'icon-md': '1.25rem',
        'icon-lg': '1.5rem',
        'icon-xl': '2rem',
      },
      height: {
        'icon-xs': '0.75rem',
        'icon-sm': '1rem',
        'icon-md': '1.25rem',
        'icon-lg': '1.5rem',
        'icon-xl': '2rem',
      },
    },
  },
};
```

### JSON Tokens

```json
{
  "icon": {
    "size": {
      "xs": { "value": "0.75rem", "description": "12px - inline" },
      "sm": { "value": "1rem", "description": "16px - small buttons" },
      "md": { "value": "1.25rem", "description": "20px - default" },
      "lg": { "value": "1.5rem", "description": "24px - large buttons" },
      "xl": { "value": "2rem", "description": "32px - feature icons" }
    },
    "stroke": {
      "thin": { "value": "1" },
      "regular": { "value": "1.5" },
      "medium": { "value": "2" },
      "bold": { "value": "2.5" }
    }
  }
}
```

---

## Approach 1: Inline SVG Components (Recommended)

Best for React, Vue, Svelte. Tree-shakeable, full styling control.

### React Icon Component

```tsx
// components/Icon.tsx
import { forwardRef, SVGProps } from 'react';
import clsx from 'clsx';

type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: IconSize;
  label?: string; // Accessible label
}

const sizeMap: Record<IconSize, string> = {
  xs: 'w-3 h-3',      // 12px
  sm: 'w-4 h-4',      // 16px
  md: 'w-5 h-5',      // 20px
  lg: 'w-6 h-6',      // 24px
  xl: 'w-8 h-8',      // 32px
};

export const Icon = forwardRef<SVGSVGElement, IconProps>(
  ({ size = 'md', label, className, children, ...props }, ref) => {
    return (
      <svg
        ref={ref}
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={clsx(sizeMap[size], className)}
        aria-hidden={!label}
        aria-label={label}
        role={label ? 'img' : 'presentation'}
        {...props}
      >
        {children}
      </svg>
    );
  }
);
```

### Individual Icon Components

```tsx
// icons/ChevronDown.tsx
import { Icon, IconProps } from '../Icon';

export function ChevronDown(props: IconProps) {
  return (
    <Icon {...props}>
      <polyline points="6 9 12 15 18 9" />
    </Icon>
  );
}

// icons/Check.tsx
export function Check(props: IconProps) {
  return (
    <Icon {...props}>
      <polyline points="20 6 9 17 4 12" />
    </Icon>
  );
}

// icons/X.tsx
export function X(props: IconProps) {
  return (
    <Icon {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </Icon>
  );
}
```

### Icon Index with Tree-Shaking

```tsx
// icons/index.ts
export { ChevronDown } from './ChevronDown';
export { Check } from './Check';
export { X } from './X';
export { Search } from './Search';
// ... etc

// Usage - only imports what's used
import { ChevronDown, Check } from '@/icons';
```

### Usage Examples

```tsx
// Basic usage
<ChevronDown />

// With size
<Check size="lg" />

// With accessible label (for meaningful icons)
<X label="Close dialog" />

// Custom styling
<Search className="text-gray-400" size="sm" />

// In a button
<button className="flex items-center gap-2">
  <PlusIcon size="sm" />
  Add item
</button>
```

---

## Approach 2: SVG Sprite

Best for large icon sets where caching matters.

### Sprite File Structure

```
icons/
├── sprite.svg         # Combined sprite
├── build-sprite.js    # Build script
└── src/               # Source SVGs
    ├── arrow-up.svg
    ├── arrow-down.svg
    └── check.svg
```

### Sprite Format

```xml
<!-- icons/sprite.svg -->
<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
  <symbol id="icon-arrow-up" viewBox="0 0 24 24">
    <polyline points="18 15 12 9 6 15"/>
  </symbol>
  <symbol id="icon-arrow-down" viewBox="0 0 24 24">
    <polyline points="6 9 12 15 18 9"/>
  </symbol>
  <symbol id="icon-check" viewBox="0 0 24 24">
    <polyline points="20 6 9 17 4 12"/>
  </symbol>
</svg>
```

### Usage with Sprite

```html
<!-- Inline sprite in HTML (for same-page access) -->
<body>
  <!-- Embed sprite at top of body -->
  <svg style="display: none;">
    <!-- ... symbols ... -->
  </svg>

  <!-- Use icons anywhere -->
  <svg class="icon icon--md" aria-hidden="true">
    <use href="#icon-check"/>
  </svg>
</body>
```

```html
<!-- External sprite file -->
<svg class="icon" aria-hidden="true">
  <use href="/icons/sprite.svg#icon-check"/>
</svg>
```

### Sprite Component (React)

```tsx
// components/SpriteIcon.tsx
interface SpriteIconProps {
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  label?: string;
  className?: string;
}

export function SpriteIcon({ name, size = 'md', label, className }: SpriteIconProps) {
  return (
    <svg
      className={clsx('icon', `icon--${size}`, className)}
      aria-hidden={!label}
      aria-label={label}
      role={label ? 'img' : 'presentation'}
    >
      <use href={`/icons/sprite.svg#icon-${name}`} />
    </svg>
  );
}

// Usage
<SpriteIcon name="check" size="lg" />
```

### Build Script (Node.js)

```js
// build-sprite.js
const fs = require('fs');
const path = require('path');
const { optimize } = require('svgo');

const iconsDir = './icons/src';
const outputFile = './icons/sprite.svg';

const files = fs.readdirSync(iconsDir).filter(f => f.endsWith('.svg'));

let symbols = '';

files.forEach(file => {
  const name = path.basename(file, '.svg');
  const content = fs.readFileSync(path.join(iconsDir, file), 'utf8');

  // Optimize SVG
  const result = optimize(content, {
    plugins: [
      'removeDoctype',
      'removeXMLProcInst',
      'removeComments',
      'removeMetadata',
      'removeTitle',
      'removeDesc',
      'removeUselessDefs',
      'removeEditorsNSData',
      'removeEmptyAttrs',
      'removeHiddenElems',
      'removeEmptyText',
      'removeEmptyContainers',
      { name: 'removeAttrs', params: { attrs: ['class', 'style', 'fill', 'stroke'] } },
    ],
  });

  // Extract viewBox and inner content
  const viewBoxMatch = result.data.match(/viewBox="([^"]+)"/);
  const viewBox = viewBoxMatch ? viewBoxMatch[1] : '0 0 24 24';
  const innerContent = result.data.replace(/<svg[^>]*>/, '').replace(/<\/svg>/, '');

  symbols += `  <symbol id="icon-${name}" viewBox="${viewBox}">\n    ${innerContent}\n  </symbol>\n`;
});

const sprite = `<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n${symbols}</svg>`;

fs.writeFileSync(outputFile, sprite);
console.log(`Generated sprite with ${files.length} icons`);
```

---

## CSS for Icons

### Base Styles

```css
/* Icon base */
.icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
  width: var(--icon-size-md);
  height: var(--icon-size-md);
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

/* Sizes */
.icon--xs { width: var(--icon-size-xs); height: var(--icon-size-xs); }
.icon--sm { width: var(--icon-size-sm); height: var(--icon-size-sm); }
.icon--md { width: var(--icon-size-md); height: var(--icon-size-md); }
.icon--lg { width: var(--icon-size-lg); height: var(--icon-size-lg); }
.icon--xl { width: var(--icon-size-xl); height: var(--icon-size-xl); }

/* Filled variant */
.icon--filled {
  fill: currentColor;
  stroke: none;
}

/* Adjust stroke for different sizes */
.icon--xs,
.icon--sm {
  stroke-width: 2.5; /* Thicker at small sizes */
}

.icon--xl {
  stroke-width: 1.5; /* Thinner at large sizes */
}
```

### Dark Mode

```css
/* Icons generally inherit color, but you can override */
[data-theme="dark"] .icon--subdued {
  opacity: 0.8;
}
```

---

## Accessibility

### Decorative Icons (Most Common)

```tsx
// Icon next to text - purely decorative
<button>
  <Icon name="plus" aria-hidden="true" />
  Add item
</button>

// Decorative enhancement
<span>
  <Icon name="check" aria-hidden="true" />
  Success
</span>
```

### Meaningful Icons

```tsx
// Icon-only button - needs label
<button aria-label="Close dialog">
  <Icon name="x" aria-hidden="true" />
</button>

// Or use icon's label prop
<Icon name="warning" label="Warning" />

// Status indicator
<Icon name="error" label="Error occurred" role="img" />
```

### Icon Buttons Pattern

```tsx
// IconButton component
interface IconButtonProps {
  icon: React.ComponentType<IconProps>;
  label: string;
  onClick: () => void;
}

function IconButton({ icon: IconComponent, label, onClick }: IconButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="p-2 rounded hover:bg-gray-100"
    >
      <IconComponent aria-hidden="true" />
    </button>
  );
}

// Usage
<IconButton icon={TrashIcon} label="Delete item" onClick={handleDelete} />
```

---

## Animation

```css
/* Spin animation for loading */
.icon--spin {
  animation: icon-spin 1s linear infinite;
}

@keyframes icon-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Pulse animation */
.icon--pulse {
  animation: icon-pulse 2s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .icon--spin,
  .icon--pulse {
    animation: none;
  }
}
```

---

## Optimization

### SVGO Config

```js
// svgo.config.js
module.exports = {
  plugins: [
    'preset-default',
    'removeDimensions',
    {
      name: 'removeAttrs',
      params: {
        attrs: ['class', 'data-name', 'fill', 'stroke'],
      },
    },
    {
      name: 'addAttributesToSVGElement',
      params: {
        attributes: [
          { fill: 'none' },
          { stroke: 'currentColor' },
          { 'stroke-width': '2' },
          { 'stroke-linecap': 'round' },
          { 'stroke-linejoin': 'round' },
        ],
      },
    },
  ],
};
```

### Vite/Webpack SVG Import

```js
// vite.config.js
import svgr from 'vite-plugin-svgr';

export default {
  plugins: [
    svgr({
      svgrOptions: {
        icon: true,
        svgProps: {
          fill: 'none',
          stroke: 'currentColor',
        },
      },
    }),
  ],
};
```

```tsx
// Usage with SVGR
import { ReactComponent as HomeIcon } from './icons/home.svg';

<HomeIcon className="w-5 h-5" />
```

---

## Icon Libraries Integration

### Lucide React

```tsx
// Already well-structured icons
import { Home, Settings, User } from 'lucide-react';

// Wrap with your size system
function Icon({ icon: IconComponent, size = 'md' }) {
  const sizeMap = { sm: 16, md: 20, lg: 24, xl: 32 };
  return <IconComponent size={sizeMap[size]} />;
}
```

### Heroicons

```tsx
import { HomeIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { HomeIcon as HomeIconSolid } from '@heroicons/react/24/solid';
```

### Phosphor Icons

```tsx
import { House, Gear, User } from '@phosphor-icons/react';

<House size={24} weight="regular" />
<Gear size={24} weight="bold" />
```

---

## File Organization

```
src/
├── components/
│   └── Icon/
│       ├── Icon.tsx           # Base component
│       ├── Icon.css           # Styles
│       └── index.ts
├── icons/
│   ├── arrows/
│   │   ├── ChevronDown.tsx
│   │   ├── ChevronUp.tsx
│   │   └── index.ts
│   ├── actions/
│   │   ├── Plus.tsx
│   │   ├── Minus.tsx
│   │   └── index.ts
│   ├── status/
│   │   ├── Check.tsx
│   │   ├── X.tsx
│   │   └── index.ts
│   └── index.ts               # Re-exports all
└── tokens/
    └── icons.json             # Size tokens
```

---

## Common Patterns

### Icon + Text Alignment

```css
/* Inline with text */
.inline-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
}

/* Icon matches text line-height */
.inline-icon svg {
  height: 1em;
  width: 1em;
}
```

### Button Icon Positions

```tsx
// Icon left
<button className="flex items-center gap-2">
  <PlusIcon size="sm" />
  Add item
</button>

// Icon right
<button className="flex items-center gap-2">
  Continue
  <ArrowRightIcon size="sm" />
</button>

// Icon only
<button aria-label="Settings" className="p-2">
  <SettingsIcon />
</button>
```
