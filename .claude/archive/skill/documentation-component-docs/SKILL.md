---
name: component-docs
description: Generates component API documentation with props tables, usage examples, and guidelines. Use when documenting component libraries, creating API references, or building component documentation for designers and developers.
---

# Component Documentation Generator

## Overview

Generate comprehensive component documentation including API references, usage examples, accessibility guidelines, and design specifications. Create documentation that serves both designers and developers.

## When to Use

- Documenting new components
- Creating component API references
- Writing usage guidelines
- Building a design system documentation site

## Quick Reference: Documentation Sections

| Section | Purpose | Audience |
|---------|---------|----------|
| Overview | What the component does | All |
| When to Use | Decision guidance | Designers |
| Props/API | Technical reference | Developers |
| Examples | Code snippets | Developers |
| Variants | Visual options | All |
| States | Interactive states | Designers |
| Accessibility | A11y guidelines | All |
| Design Specs | Spacing, tokens used | Designers |
| Do/Don't | Usage guidance | All |

## The Process

1. **Identify component scope**: What does it do, what doesn't it do?
2. **Define props interface**: All configurable options
3. **Create examples**: Basic, advanced, edge cases
4. **Document variants**: Visual variations
5. **Add accessibility**: ARIA, keyboard, screen reader
6. **Include design specs**: Spacing, colors, typography tokens
7. **Write guidelines**: When to use, when not to

---

## Component Documentation Template

```markdown
# Button

Buttons allow users to take actions and make choices with a single tap.

## Overview

The Button component is used for triggering actions. Use buttons to submit forms,
navigate between pages, or trigger in-page functionality.

## When to Use

| Scenario | Recommendation |
|----------|----------------|
| Primary action | Use `variant="primary"` |
| Secondary action | Use `variant="secondary"` |
| Destructive action | Use `variant="danger"` |
| Navigation | Consider using a Link instead |
| In forms | Use `type="submit"` |

## Import

```tsx
import { Button } from '@acme/design-system';
```

## Basic Usage

```tsx
<Button onClick={handleClick}>Click me</Button>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'danger'` | `'primary'` | Visual style variant |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Button size |
| `disabled` | `boolean` | `false` | Disables the button |
| `loading` | `boolean` | `false` | Shows loading spinner |
| `fullWidth` | `boolean` | `false` | Makes button 100% width |
| `leftIcon` | `ReactNode` | - | Icon before text |
| `rightIcon` | `ReactNode` | - | Icon after text |
| `type` | `'button' \| 'submit' \| 'reset'` | `'button'` | HTML button type |
| `onClick` | `(event: MouseEvent) => void` | - | Click handler |
| `children` | `ReactNode` | - | Button label |

## Variants

### Primary
Use for the main action on a page or in a form.

```tsx
<Button variant="primary">Save changes</Button>
```

### Secondary
Use for secondary actions that support the primary action.

```tsx
<Button variant="secondary">Cancel</Button>
```

### Ghost
Use for tertiary actions or in dense UIs.

```tsx
<Button variant="ghost">Learn more</Button>
```

### Danger
Use for destructive actions like delete.

```tsx
<Button variant="danger">Delete account</Button>
```

## Sizes

```tsx
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>
```

| Size | Height | Font Size | Use Case |
|------|--------|-----------|----------|
| `sm` | 32px | 14px | Compact UIs, tables |
| `md` | 40px | 16px | Default, most uses |
| `lg` | 48px | 18px | Hero sections, emphasis |

## States

### Default
```tsx
<Button>Default</Button>
```

### Hover
Slightly darkened background. Applied automatically on mouse hover.

### Active
Pressed state with slight scale reduction.

### Focus
Focus ring appears on keyboard focus (focus-visible).

### Disabled
```tsx
<Button disabled>Disabled</Button>
```
- 50% opacity
- Cursor changes to not-allowed
- Click events are ignored

### Loading
```tsx
<Button loading>Saving...</Button>
```
- Shows spinner icon
- Button is disabled
- Label remains for width consistency
- `aria-busy="true"` for screen readers

## With Icons

```tsx
// Icon before text
<Button leftIcon={<PlusIcon />}>Add item</Button>

// Icon after text
<Button rightIcon={<ArrowRightIcon />}>Continue</Button>

// Icon only (use aria-label)
<Button aria-label="Settings">
  <SettingsIcon />
</Button>
```

## Full Width

```tsx
<Button fullWidth>Sign up</Button>
```

## Button Groups

```tsx
<div className="button-group">
  <Button variant="secondary">Cancel</Button>
  <Button variant="primary">Save</Button>
</div>
```

## Accessibility

### Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Move focus to button |
| `Enter` | Activate button |
| `Space` | Activate button |

### ARIA

- Uses native `<button>` element
- `aria-disabled` when disabled (maintains focusability)
- `aria-busy` when loading
- `aria-pressed` for toggle buttons

### Screen Readers

- Ensure button has accessible name (text content or aria-label)
- Loading state announced via aria-busy
- Icon-only buttons require aria-label

### Focus Management

- Focus ring visible on keyboard focus (not mouse)
- 2px outline with 2px offset
- Meets WCAG 2.4.7 Focus Visible

## Design Specifications

### Spacing

| Element | Token | Value |
|---------|-------|-------|
| Horizontal padding (sm) | `--spacing-sm` | 8px |
| Horizontal padding (md) | `--spacing-md` | 16px |
| Horizontal padding (lg) | `--spacing-lg` | 24px |
| Icon gap | `--spacing-xs` | 4px |
| Button group gap | `--spacing-sm` | 8px |

### Colors

| Variant | Background | Text | Border |
|---------|------------|------|--------|
| Primary | `--color-primary-500` | white | - |
| Primary:hover | `--color-primary-600` | white | - |
| Secondary | transparent | `--color-gray-700` | `--color-gray-300` |
| Ghost | transparent | `--color-gray-700` | - |
| Danger | `--color-error-500` | white | - |

### Typography

| Size | Token | Weight |
|------|-------|--------|
| sm | `--text-sm` (14px) | 500 |
| md | `--text-base` (16px) | 500 |
| lg | `--text-lg` (18px) | 500 |

### Other

| Property | Token | Value |
|----------|-------|-------|
| Border radius | `--radius-md` | 8px |
| Focus ring | `--color-primary-500` | 2px solid |
| Transition | - | 150ms ease |

## Do's and Don'ts

### Do ✅

- Use clear, action-oriented labels ("Save", "Delete", "Continue")
- Place primary action on the right in button groups
- Use loading state for async actions
- Provide aria-label for icon-only buttons

### Don't ❌

- Don't use vague labels ("Click here", "Submit")
- Don't use more than one primary button per view
- Don't disable buttons without explanation
- Don't use buttons for navigation (use Links)

## Related Components

- [Link](/components/link) - For navigation
- [IconButton](/components/icon-button) - Icon-only variant
- [ButtonGroup](/components/button-group) - Multiple buttons together
- [ToggleButton](/components/toggle-button) - Stateful toggle

## Changelog

| Version | Changes |
|---------|---------|
| 1.2.0 | Added `loading` prop |
| 1.1.0 | Added `ghost` variant |
| 1.0.0 | Initial release |
```

---

## API Documentation Template

**For TypeScript components:**

```markdown
## API Reference

### ButtonProps

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Visual style variant
   * @default 'primary'
   */
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';

  /**
   * Button size
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Shows loading spinner and disables button
   * @default false
   */
  loading?: boolean;

  /**
   * Makes button full width of container
   * @default false
   */
  fullWidth?: boolean;

  /**
   * Icon element to display before text
   */
  leftIcon?: React.ReactNode;

  /**
   * Icon element to display after text
   */
  rightIcon?: React.ReactNode;

  /**
   * Button content (label)
   */
  children: React.ReactNode;
}
```

### Ref

The Button component forwards its ref to the underlying `<button>` element.

```tsx
const buttonRef = useRef<HTMLButtonElement>(null);
<Button ref={buttonRef}>Click me</Button>
```

### CSS Classes

| Class | Description |
|-------|-------------|
| `.btn` | Base button styles |
| `.btn--primary` | Primary variant |
| `.btn--secondary` | Secondary variant |
| `.btn--ghost` | Ghost variant |
| `.btn--danger` | Danger variant |
| `.btn--sm` | Small size |
| `.btn--md` | Medium size |
| `.btn--lg` | Large size |
| `.btn--loading` | Loading state |
| `.btn--full-width` | Full width modifier |
```

---

## Auto-Generation from TypeScript

**generate-component-docs.ts:**
```typescript
import ts from 'typescript';
import fs from 'fs';

interface PropDoc {
  name: string;
  type: string;
  description: string;
  defaultValue?: string;
  required: boolean;
}

function extractPropsFromInterface(
  sourceFile: ts.SourceFile,
  interfaceName: string
): PropDoc[] {
  const props: PropDoc[] = [];

  function visit(node: ts.Node) {
    if (ts.isInterfaceDeclaration(node) && node.name.text === interfaceName) {
      node.members.forEach((member) => {
        if (ts.isPropertySignature(member) && member.name) {
          const name = member.name.getText(sourceFile);
          const type = member.type?.getText(sourceFile) || 'unknown';
          const required = !member.questionToken;

          // Extract JSDoc
          const jsDoc = ts.getJSDocTags(member);
          const description = ts.getJSDocCommentsAndTags(member)
            .map((c) => c.getText())
            .join(' ')
            .replace(/\/\*\*|\*\/|\*/g, '')
            .trim();

          const defaultTag = jsDoc.find((t) => t.tagName.text === 'default');
          const defaultValue = defaultTag?.comment?.toString();

          props.push({ name, type, description, defaultValue, required });
        }
      });
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return props;
}

function generatePropsTable(props: PropDoc[]): string {
  let md = '| Prop | Type | Default | Required | Description |\n';
  md += '|------|------|---------|----------|-------------|\n';

  for (const prop of props) {
    const required = prop.required ? 'Yes' : 'No';
    const defaultVal = prop.defaultValue || '-';
    md += `| \`${prop.name}\` | \`${prop.type}\` | ${defaultVal} | ${required} | ${prop.description} |\n`;
  }

  return md;
}

// Usage
const sourceCode = fs.readFileSync('./components/Button.tsx', 'utf-8');
const sourceFile = ts.createSourceFile(
  'Button.tsx',
  sourceCode,
  ts.ScriptTarget.Latest,
  true
);

const props = extractPropsFromInterface(sourceFile, 'ButtonProps');
const table = generatePropsTable(props);

console.log(table);
```

---

## Documentation Site Structure

```
docs/
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   └── theming.md
├── foundations/
│   ├── colors.md
│   ├── typography.md
│   ├── spacing.md
│   └── icons.md
├── components/
│   ├── primitives/
│   │   ├── button.md
│   │   ├── input.md
│   │   └── text.md
│   ├── composite/
│   │   ├── card.md
│   │   ├── modal.md
│   │   └── dropdown.md
│   └── layout/
│       ├── stack.md
│       ├── grid.md
│       └── container.md
├── patterns/
│   ├── forms.md
│   ├── navigation.md
│   └── data-display.md
└── resources/
    ├── changelog.md
    ├── migration.md
    └── contributing.md
```

---

## Best Practices

1. **Lead with examples**: Show code before explaining
2. **Be consistent**: Use same structure for all components
3. **Include visuals**: Screenshots, diagrams, live demos
4. **Document edge cases**: Empty states, long text, RTL
5. **Keep it updated**: Automate where possible
6. **Cross-reference**: Link related components
7. **Show context**: Include realistic usage scenarios
8. **Test your examples**: Ensure code snippets work
