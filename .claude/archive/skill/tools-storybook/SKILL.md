---
name: storybook
description: Documents components with Storybook using CSF 3.0, controls, and MDX. Use when creating component catalogs, interactive examples, visual testing setups, or design system documentation sites.
---

# Storybook Component Documentation

## Overview

Document and showcase design system components using Storybook. Create interactive examples, visual tests, and comprehensive documentation with controls, args, and MDX.

## When to Use

- Setting up component documentation
- Creating interactive component playground
- Visual regression testing
- Building a component library catalog
- Onboarding developers to the design system

## Quick Reference: Story Formats

| Format | Use Case | File Extension |
|--------|----------|----------------|
| CSF 3.0 | Standard stories with args | `.stories.tsx` |
| MDX | Documentation + stories | `.mdx` |
| Autodocs | Auto-generated docs | Enabled in config |

## The Process

1. **Install Storybook**: `npx storybook@latest init`
2. **Configure for framework**: React, Vue, Svelte, Angular
3. **Set up design tokens**: Import CSS tokens globally
4. **Write stories**: One story per component variant
5. **Add controls**: Enable props manipulation
6. **Write docs**: MDX documentation pages
7. **Add addons**: A11y, viewport, themes

## Project Structure

```
.storybook/
├── main.ts           # Storybook config
├── preview.ts        # Global decorators, parameters
├── preview-head.html # Global CSS imports
└── theme.ts          # Custom Storybook theme

src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.stories.tsx
│   │   └── Button.mdx       # Optional MDX docs
│   └── Input/
├── tokens/
│   └── index.css
└── docs/
    ├── Introduction.mdx
    ├── Colors.mdx
    └── Typography.mdx
```

---

## Configuration

**.storybook/main.ts:**
```typescript
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../src/**/*.mdx',
    '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)',
  ],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-links',
    '@storybook/addon-interactions',
    '@chromatic-com/storybook',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag', // Enable autodocs for tagged components
  },
  staticDirs: ['../public'],
};

export default config;
```

**.storybook/preview.ts:**
```typescript
import type { Preview } from '@storybook/react';
import '../src/tokens/index.css';
import './storybook.css';

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#ffffff' },
        { name: 'dark', value: '#1f2937' },
        { name: 'gray', value: '#f3f4f6' },
      ],
    },
    viewport: {
      viewports: {
        mobile: { name: 'Mobile', styles: { width: '375px', height: '667px' } },
        tablet: { name: 'Tablet', styles: { width: '768px', height: '1024px' } },
        desktop: { name: 'Desktop', styles: { width: '1280px', height: '800px' } },
      },
    },
  },
  globalTypes: {
    theme: {
      description: 'Global theme',
      defaultValue: 'light',
      toolbar: {
        title: 'Theme',
        icon: 'paintbrush',
        items: ['light', 'dark'],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme;
      document.documentElement.dataset.theme = theme;
      return <Story />;
    },
  ],
};

export default preview;
```

---

## Story Patterns

### Basic Story (CSF 3.0)

**Button.stories.tsx:**
```tsx
import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'Components/Button',
  component: Button,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Primary UI button component with multiple variants and sizes.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost', 'danger'],
      description: 'Visual style variant',
      table: {
        type: { summary: 'primary | secondary | ghost | danger' },
        defaultValue: { summary: 'primary' },
      },
    },
    size: {
      control: 'radio',
      options: ['sm', 'md', 'lg'],
      description: 'Button size',
      table: {
        type: { summary: 'sm | md | lg' },
        defaultValue: { summary: 'md' },
      },
    },
    loading: {
      control: 'boolean',
      description: 'Shows loading spinner and disables button',
    },
    disabled: {
      control: 'boolean',
      description: 'Disables the button',
    },
    fullWidth: {
      control: 'boolean',
      description: 'Makes button full width',
    },
    children: {
      control: 'text',
      description: 'Button label',
    },
    onClick: {
      action: 'clicked',
      description: 'Click handler',
    },
  },
  args: {
    children: 'Button',
    onClick: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Default story
export const Default: Story = {
  args: {
    variant: 'primary',
  },
};

// Variant stories
export const Primary: Story = {
  args: {
    variant: 'primary',
    children: 'Primary Button',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Secondary Button',
  },
};

export const Ghost: Story = {
  args: {
    variant: 'ghost',
    children: 'Ghost Button',
  },
};

export const Danger: Story = {
  args: {
    variant: 'danger',
    children: 'Delete',
  },
};

// Size stories
export const Small: Story = {
  args: {
    size: 'sm',
    children: 'Small',
  },
};

export const Large: Story = {
  args: {
    size: 'lg',
    children: 'Large Button',
  },
};

// State stories
export const Loading: Story = {
  args: {
    loading: true,
    children: 'Saving...',
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
    children: 'Disabled',
  },
};

// With icons
export const WithLeftIcon: Story = {
  args: {
    children: 'Download',
    leftIcon: <DownloadIcon />,
  },
};

// Full width
export const FullWidth: Story = {
  args: {
    fullWidth: true,
    children: 'Full Width Button',
  },
  parameters: {
    layout: 'padded',
  },
};

// All variants showcase
export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Danger</Button>
    </div>
  ),
};

// All sizes showcase
export const AllSizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
};
```

---

### Input Component Story

**Input.stories.tsx:**
```tsx
import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { Input } from './Input';
import { SearchIcon, EyeIcon, EyeOffIcon } from '../icons';

const meta: Meta<typeof Input> = {
  title: 'Components/Input',
  component: Input,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    label: { control: 'text' },
    placeholder: { control: 'text' },
    helperText: { control: 'text' },
    error: { control: 'text' },
    size: { control: 'radio', options: ['sm', 'md', 'lg'] },
    type: { control: 'select', options: ['text', 'email', 'password', 'number'] },
    disabled: { control: 'boolean' },
    required: { control: 'boolean' },
    fullWidth: { control: 'boolean' },
  },
  args: {
    label: 'Label',
    placeholder: 'Enter text...',
  },
  decorators: [
    (Story) => (
      <div style={{ width: '320px' }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithHelperText: Story = {
  args: {
    label: 'Email',
    placeholder: 'you@example.com',
    helperText: 'We will never share your email.',
  },
};

export const WithError: Story = {
  args: {
    label: 'Email',
    placeholder: 'you@example.com',
    error: 'Please enter a valid email address.',
    defaultValue: 'invalid-email',
  },
};

export const Required: Story = {
  args: {
    label: 'Username',
    placeholder: 'Enter username',
    required: true,
  },
};

export const Disabled: Story = {
  args: {
    label: 'Email',
    disabled: true,
    value: 'disabled@example.com',
  },
};

export const WithStartIcon: Story = {
  args: {
    label: 'Search',
    placeholder: 'Search...',
    startAdornment: <SearchIcon />,
  },
};

// Interactive password toggle
export const PasswordWithToggle: Story = {
  render: function PasswordInput() {
    const [show, setShow] = useState(false);
    return (
      <Input
        label="Password"
        type={show ? 'text' : 'password'}
        placeholder="Enter password"
        endAdornment={
          <button
            type="button"
            onClick={() => setShow(!show)}
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          >
            {show ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        }
      />
    );
  },
};

// Form example
export const InForm: Story = {
  render: () => (
    <form
      style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
      onSubmit={(e) => e.preventDefault()}
    >
      <Input label="First Name" placeholder="John" required />
      <Input label="Last Name" placeholder="Doe" required />
      <Input label="Email" type="email" placeholder="john@example.com" required />
      <button type="submit">Submit</button>
    </form>
  ),
  decorators: [
    (Story) => (
      <div style={{ width: '400px', padding: '2rem' }}>
        <Story />
      </div>
    ),
  ],
};
```

---

### MDX Documentation

**Button.mdx:**
```mdx
import { Meta, Story, Canvas, Controls, Source } from '@storybook/blocks';
import * as ButtonStories from './Button.stories';

<Meta of={ButtonStories} />

# Button

Buttons allow users to take actions and make choices with a single tap.

## Usage

```tsx
import { Button } from '@acme/design-system';

<Button variant="primary" onClick={handleClick}>
  Click me
</Button>
```

## Variants

Use different variants to indicate hierarchy and importance:

<Canvas of={ButtonStories.AllVariants} />

| Variant | Use Case |
|---------|----------|
| `primary` | Primary actions, CTAs |
| `secondary` | Secondary actions |
| `ghost` | Tertiary actions, less emphasis |
| `danger` | Destructive actions |

## Sizes

<Canvas of={ButtonStories.AllSizes} />

## States

### Loading

Show a loading spinner during async operations:

<Canvas of={ButtonStories.Loading} />

### Disabled

Prevent interaction when button should not be clickable:

<Canvas of={ButtonStories.Disabled} />

## With Icons

Buttons can include icons for visual context:

<Canvas of={ButtonStories.WithLeftIcon} />

## Props

<Controls />

## Accessibility

- Uses native `<button>` element
- Includes `aria-busy` when loading
- Focus-visible ring for keyboard navigation
- Disabled state prevents interaction and shows visually

## Design Tokens Used

| Token | Property |
|-------|----------|
| `--color-primary-500` | Primary background |
| `--color-primary-600` | Primary hover |
| `--spacing-sm/md/lg` | Horizontal padding |
| `--radius-md` | Border radius |
| `--text-sm/base/lg` | Font size by size variant |
```

---

### Token Documentation Page

**docs/Colors.mdx:**
```mdx
import { Meta, ColorPalette, ColorItem } from '@storybook/blocks';

<Meta title="Tokens/Colors" />

# Colors

Our color system uses OKLCH for perceptual uniformity.

## Primary

<ColorPalette>
  <ColorItem
    title="Primary"
    subtitle="Brand color scale"
    colors={{
      50: 'var(--color-primary-50)',
      100: 'var(--color-primary-100)',
      200: 'var(--color-primary-200)',
      300: 'var(--color-primary-300)',
      400: 'var(--color-primary-400)',
      500: 'var(--color-primary-500)',
      600: 'var(--color-primary-600)',
      700: 'var(--color-primary-700)',
      800: 'var(--color-primary-800)',
      900: 'var(--color-primary-900)',
      950: 'var(--color-primary-950)',
    }}
  />
</ColorPalette>

## Gray

<ColorPalette>
  <ColorItem
    title="Gray"
    subtitle="Neutral scale"
    colors={{
      50: 'var(--color-gray-50)',
      100: 'var(--color-gray-100)',
      500: 'var(--color-gray-500)',
      900: 'var(--color-gray-900)',
    }}
  />
</ColorPalette>

## Semantic

<ColorPalette>
  <ColorItem title="Success" colors={{ 500: 'var(--color-success-500)' }} />
  <ColorItem title="Warning" colors={{ 500: 'var(--color-warning-500)' }} />
  <ColorItem title="Error" colors={{ 500: 'var(--color-error-500)' }} />
  <ColorItem title="Info" colors={{ 500: 'var(--color-info-500)' }} />
</ColorPalette>

## Usage

```css
.element {
  background-color: var(--color-primary-500);
  color: var(--color-gray-50);
}
```
```

---

## Addons

### Accessibility Testing

**Install:**
```bash
npm install @storybook/addon-a11y --save-dev
```

**Usage in story:**
```tsx
export const AccessibleButton: Story = {
  args: {
    children: 'Accessible Button',
  },
  parameters: {
    a11y: {
      config: {
        rules: [
          { id: 'color-contrast', enabled: true },
          { id: 'button-name', enabled: true },
        ],
      },
    },
  },
};
```

### Interaction Testing

**Button.stories.tsx:**
```tsx
import { expect, userEvent, within } from '@storybook/test';

export const ClickInteraction: Story = {
  args: {
    children: 'Click me',
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button');

    await userEvent.click(button);
    await expect(args.onClick).toHaveBeenCalled();
  },
};

export const HoverState: Story = {
  args: {
    children: 'Hover me',
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button');

    await userEvent.hover(button);
    // Add visual assertions if needed
  },
};
```

---

## Custom Theme

**.storybook/theme.ts:**
```typescript
import { create } from '@storybook/theming/create';

export default create({
  base: 'light',
  brandTitle: 'Acme Design System',
  brandUrl: 'https://acme.com',
  brandImage: '/logo.svg',
  brandTarget: '_self',

  // Colors
  colorPrimary: '#3b82f6',
  colorSecondary: '#6366f1',

  // UI
  appBg: '#f8fafc',
  appContentBg: '#ffffff',
  appBorderColor: '#e2e8f0',
  appBorderRadius: 8,

  // Typography
  fontBase: '"Inter", sans-serif',
  fontCode: '"JetBrains Mono", monospace',

  // Text colors
  textColor: '#1e293b',
  textInverseColor: '#ffffff',

  // Toolbar
  barTextColor: '#64748b',
  barSelectedColor: '#3b82f6',
  barBg: '#ffffff',

  // Form colors
  inputBg: '#ffffff',
  inputBorder: '#cbd5e1',
  inputTextColor: '#1e293b',
  inputBorderRadius: 6,
});
```

**.storybook/manager.ts:**
```typescript
import { addons } from '@storybook/manager-api';
import theme from './theme';

addons.setConfig({
  theme,
});
```

---

## Best Practices

1. **One story per variant**: Make each state explicit and testable
2. **Use args over props**: Enable controls panel manipulation
3. **Include play functions**: Add interaction tests for complex behaviors
4. **Document with MDX**: Combine stories with usage guidelines
5. **Show realistic data**: Use meaningful content, not "Lorem ipsum"
6. **Test responsive**: Use viewport addon for different screen sizes
7. **Check accessibility**: Run a11y addon on all stories
