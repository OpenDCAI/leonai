---
name: compound-components
description: Builds accessible composable components using Radix/Headless UI patterns. Use when creating Select, Dialog, Tabs, Accordion, Menu, or Dropdown components with proper ARIA, keyboard navigation, and focus management.
---

# Compound Components

## Overview

Build accessible, composable components using the compound component pattern. This is how modern component libraries (Radix UI, Headless UI, React Aria) create flexible, accessible primitives that handle complex interactions.

## When to Use

- Building a component library from scratch
- Creating accessible interactive components (Select, Dialog, Tabs, Accordion)
- Need flexibility in how components render
- Want to separate behavior from styling
- Components with complex state (open/closed, selected, focused)

### Implementation Checklist

Copy this checklist when building a compound component:

```
Compound Component Build:
- [ ] Define component parts and responsibilities (Root, Trigger, Content, Item, etc.)
- [ ] Create Root with context provider (state, refs, generated IDs)
- [ ] Implement child components with ARIA roles and data-state attributes
- [ ] Add keyboard navigation (Arrow keys, Enter/Space, Escape, Tab)
- [ ] Handle focus management (initial focus, focus trap for modals, focus restoration)
- [ ] Test with keyboard-only navigation and screen reader
```

## Quick Reference: Pattern Comparison

| Pattern | Example | Flexibility | Complexity |
|---------|---------|-------------|------------|
| Monolithic | `<Select options={[...]} />` | Low | Low |
| Compound | `<Select.Root><Select.Trigger /><Select.Content /></Select.Root>` | High | Medium |
| Headless | `useSelect()` hook | Highest | High |

## The Compound Pattern

```tsx
// Usage example - caller controls structure
<Dialog.Root>
  <Dialog.Trigger>Open</Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay />
    <Dialog.Content>
      <Dialog.Title>Settings</Dialog.Title>
      <Dialog.Description>Manage preferences</Dialog.Description>
      {/* Custom content */}
      <Dialog.Close>Done</Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

---

## Architecture

### Component Parts

| Part | Purpose | Required |
|------|---------|----------|
| Root | Provides context, manages state | Yes |
| Trigger | Opens/activates the component | Usually |
| Content | Main content area | Yes |
| Portal | Renders outside DOM hierarchy | For overlays |
| Overlay | Backdrop behind content | For modals |
| Title | Accessible heading | For dialogs |
| Description | Accessible description | Optional |
| Close | Closes the component | Usually |
| Item | Individual selectable items | For lists |

### Context Flow

```
┌─────────────────────────────────────────────────┐
│  Root (Context Provider)                         │
│  ┌───────────────────────────────────────────┐  │
│  │  • open/setOpen state                      │  │
│  │  • triggerRef                              │  │
│  │  • contentRef                              │  │
│  │  • generated IDs                           │  │
│  └───────────────────────────────────────────┘  │
│                      │                           │
│           ┌─────────┴─────────┐                 │
│           ▼                   ▼                 │
│       Trigger              Content              │
│    (reads context)     (reads context)          │
│                              │                  │
│                     ┌────────┴────────┐         │
│                     ▼        ▼        ▼         │
│                  Title   Items    Close         │
└─────────────────────────────────────────────────┘
```

---

## Implementation: React

### Select Component

```tsx
// select.tsx
import * as React from 'react';
import { createContext, useContext, useId, useRef, useState } from 'react';

// Types
interface SelectContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  value: string | undefined;
  setValue: (value: string) => void;
  triggerId: string;
  contentId: string;
  triggerRef: React.RefObject<HTMLButtonElement>;
}

interface SelectRootProps {
  children: React.ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
  defaultValue?: string;
}

// Context
const SelectContext = createContext<SelectContextValue | null>(null);

function useSelectContext() {
  const context = useContext(SelectContext);
  if (!context) {
    throw new Error('Select components must be used within Select.Root');
  }
  return context;
}

// Root - manages all state
function SelectRoot({
  children,
  value: controlledValue,
  onValueChange,
  defaultValue
}: SelectRootProps) {
  const [open, setOpen] = useState(false);
  const [internalValue, setInternalValue] = useState(defaultValue);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const id = useId();
  const triggerId = `select-trigger-${id}`;
  const contentId = `select-content-${id}`;

  // Controlled vs uncontrolled
  const value = controlledValue ?? internalValue;
  const setValue = (newValue: string) => {
    setInternalValue(newValue);
    onValueChange?.(newValue);
    setOpen(false);
  };

  return (
    <SelectContext.Provider value={{
      open,
      setOpen,
      value,
      setValue,
      triggerId,
      contentId,
      triggerRef,
    }}>
      {children}
    </SelectContext.Provider>
  );
}

// Trigger - opens the select
interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

function SelectTrigger({ children, className, ...props }: SelectTriggerProps) {
  const { open, setOpen, triggerId, contentId, triggerRef } = useSelectContext();

  return (
    <button
      ref={triggerRef}
      id={triggerId}
      type="button"
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      aria-controls={contentId}
      onClick={() => setOpen(!open)}
      className={className}
      {...props}
    >
      {children}
    </button>
  );
}

// Value - displays current selection
function SelectValue({ placeholder }: { placeholder?: string }) {
  const { value } = useSelectContext();
  return <span>{value || placeholder}</span>;
}

// Content - dropdown container
interface SelectContentProps {
  children: React.ReactNode;
  className?: string;
}

function SelectContent({ children, className }: SelectContentProps) {
  const { open, contentId, triggerId, triggerRef } = useSelectContext();
  const contentRef = useRef<HTMLDivElement>(null);

  // Handle keyboard navigation
  React.useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        triggerRef.current?.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, triggerRef]);

  // Handle click outside
  React.useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (
        contentRef.current &&
        !contentRef.current.contains(e.target as Node) &&
        !triggerRef.current?.contains(e.target as Node)
      ) {
        // Close handled by Root
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open, triggerRef]);

  if (!open) return null;

  return (
    <div
      ref={contentRef}
      id={contentId}
      role="listbox"
      aria-labelledby={triggerId}
      className={className}
    >
      {children}
    </div>
  );
}

// Item - individual option
interface SelectItemProps {
  value: string;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

function SelectItem({ value, children, className, disabled }: SelectItemProps) {
  const { value: selectedValue, setValue } = useSelectContext();
  const isSelected = value === selectedValue;

  return (
    <div
      role="option"
      aria-selected={isSelected}
      aria-disabled={disabled}
      data-selected={isSelected ? '' : undefined}
      data-disabled={disabled ? '' : undefined}
      onClick={() => !disabled && setValue(value)}
      className={className}
    >
      {children}
    </div>
  );
}

// Export compound component
export const Select = {
  Root: SelectRoot,
  Trigger: SelectTrigger,
  Value: SelectValue,
  Content: SelectContent,
  Item: SelectItem,
};
```

### Usage

```tsx
import { Select } from './select';

function Example() {
  const [value, setValue] = useState('');

  return (
    <Select.Root value={value} onValueChange={setValue}>
      <Select.Trigger className="btn">
        <Select.Value placeholder="Select a fruit" />
        <ChevronDownIcon />
      </Select.Trigger>
      <Select.Content className="dropdown">
        <Select.Item value="apple">Apple</Select.Item>
        <Select.Item value="banana">Banana</Select.Item>
        <Select.Item value="cherry" disabled>Cherry (sold out)</Select.Item>
      </Select.Content>
    </Select.Root>
  );
}
```

---

## Implementation: Dialog/Modal

```tsx
// dialog.tsx
import * as React from 'react';
import { createPortal } from 'react-dom';

interface DialogContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  titleId: string;
  descriptionId: string;
}

const DialogContext = React.createContext<DialogContextValue | null>(null);

function useDialogContext() {
  const context = React.useContext(DialogContext);
  if (!context) throw new Error('Dialog components must be within Dialog.Root');
  return context;
}

// Root
function DialogRoot({
  children,
  open: controlledOpen,
  onOpenChange,
  defaultOpen = false
}: {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  defaultOpen?: boolean;
}) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
  const open = controlledOpen ?? internalOpen;

  const setOpen = (value: boolean) => {
    setInternalOpen(value);
    onOpenChange?.(value);
  };

  const id = React.useId();

  return (
    <DialogContext.Provider value={{
      open,
      setOpen,
      titleId: `dialog-title-${id}`,
      descriptionId: `dialog-desc-${id}`,
    }}>
      {children}
    </DialogContext.Provider>
  );
}

// Trigger
function DialogTrigger({
  children,
  asChild,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean }) {
  const { setOpen } = useDialogContext();

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<any>, {
      onClick: () => setOpen(true),
      ...props,
    });
  }

  return (
    <button type="button" onClick={() => setOpen(true)} {...props}>
      {children}
    </button>
  );
}

// Portal
function DialogPortal({ children }: { children: React.ReactNode }) {
  const { open } = useDialogContext();
  if (!open) return null;
  return createPortal(children, document.body);
}

// Overlay
function DialogOverlay({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const { setOpen } = useDialogContext();

  return (
    <div
      className={className}
      onClick={() => setOpen(false)}
      aria-hidden="true"
      {...props}
    />
  );
}

// Content
function DialogContent({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  const { setOpen, titleId, descriptionId } = useDialogContext();
  const contentRef = React.useRef<HTMLDivElement>(null);

  // Trap focus
  React.useEffect(() => {
    const focusableElements = contentRef.current?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements?.[0] as HTMLElement;
    firstElement?.focus();
  }, []);

  // Handle escape
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [setOpen]);

  // Lock body scroll
  React.useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <div
      ref={contentRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      className={className}
      onClick={(e) => e.stopPropagation()}
      {...props}
    >
      {children}
    </div>
  );
}

// Title
function DialogTitle({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  const { titleId } = useDialogContext();
  return <h2 id={titleId} className={className} {...props}>{children}</h2>;
}

// Description
function DialogDescription({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  const { descriptionId } = useDialogContext();
  return <p id={descriptionId} className={className} {...props}>{children}</p>;
}

// Close
function DialogClose({
  children,
  asChild,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean }) {
  const { setOpen } = useDialogContext();

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<any>, {
      onClick: () => setOpen(false),
    });
  }

  return (
    <button type="button" onClick={() => setOpen(false)} {...props}>
      {children}
    </button>
  );
}

export const Dialog = {
  Root: DialogRoot,
  Trigger: DialogTrigger,
  Portal: DialogPortal,
  Overlay: DialogOverlay,
  Content: DialogContent,
  Title: DialogTitle,
  Description: DialogDescription,
  Close: DialogClose,
};
```

---

## Common Components

### Tabs

```tsx
// Tab compound structure
<Tabs.Root defaultValue="tab1">
  <Tabs.List>
    <Tabs.Trigger value="tab1">Account</Tabs.Trigger>
    <Tabs.Trigger value="tab2">Settings</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="tab1">Account settings...</Tabs.Content>
  <Tabs.Content value="tab2">General settings...</Tabs.Content>
</Tabs.Root>

// Context needs: activeTab, setActiveTab, orientation
// ARIA: tablist, tab, tabpanel, aria-selected, aria-controls
```

### Accordion

```tsx
// Accordion compound structure
<Accordion.Root type="single" collapsible>
  <Accordion.Item value="item1">
    <Accordion.Trigger>Section 1</Accordion.Trigger>
    <Accordion.Content>Content 1...</Accordion.Content>
  </Accordion.Item>
  <Accordion.Item value="item2">
    <Accordion.Trigger>Section 2</Accordion.Trigger>
    <Accordion.Content>Content 2...</Accordion.Content>
  </Accordion.Item>
</Accordion.Root>

// Context needs: openItems, setOpenItems, type (single/multiple)
// ARIA: region, button, aria-expanded, aria-controls
```

### Dropdown Menu

```tsx
// Menu compound structure
<Menu.Root>
  <Menu.Trigger>Options</Menu.Trigger>
  <Menu.Content>
    <Menu.Item onSelect={() => {}}>Edit</Menu.Item>
    <Menu.Item onSelect={() => {}}>Duplicate</Menu.Item>
    <Menu.Separator />
    <Menu.Item onSelect={() => {}} variant="destructive">Delete</Menu.Item>
  </Menu.Content>
</Menu.Root>

// Context needs: open, setOpen, highlightedIndex
// ARIA: menu, menuitem, aria-haspopup
```

---

## Styling Patterns

### Data Attributes for State

```tsx
// Component outputs data attributes
<div
  data-state={open ? 'open' : 'closed'}
  data-selected={isSelected ? '' : undefined}
  data-disabled={disabled ? '' : undefined}
/>
```

```css
/* Style with data attributes */
[data-state="open"] {
  opacity: 1;
}

[data-state="closed"] {
  opacity: 0;
}

[data-selected] {
  background: var(--color-bg-selected);
}

[data-disabled] {
  opacity: 0.5;
  pointer-events: none;
}
```

### With Tailwind

```tsx
<Select.Content className="
  absolute mt-1 w-full rounded-md bg-white shadow-lg
  data-[state=open]:animate-in data-[state=closed]:animate-out
  data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0
">
```

### CSS Variables for Customization

```tsx
// Component defines CSS variable contract
<Dialog.Content style={{
  '--dialog-width': '400px',
  '--dialog-padding': 'var(--spacing-lg)',
}}>
```

```css
.dialog-content {
  width: var(--dialog-width, 500px);
  padding: var(--dialog-padding, 1.5rem);
}
```

---

## The `asChild` Pattern

Allows rendering as a different element while keeping behavior:

```tsx
interface AsChildProps {
  asChild?: boolean;
  children: React.ReactNode;
}

function SlotButton({ asChild, children, ...props }: AsChildProps & ButtonProps) {
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...props,
      ...children.props,
    });
  }

  return <button {...props}>{children}</button>;
}

// Usage
<Dialog.Trigger asChild>
  <a href="#">Open as link</a>
</Dialog.Trigger>
```

---

## Accessibility Checklist

| Component | ARIA Roles | Keyboard |
|-----------|------------|----------|
| Dialog | dialog, aria-modal, aria-labelledby | Escape closes, focus trap |
| Select | combobox, listbox, option | Arrow keys, Enter, Escape |
| Tabs | tablist, tab, tabpanel | Arrow keys, Home/End |
| Accordion | region, button, aria-expanded | Enter/Space toggles |
| Menu | menu, menuitem | Arrow keys, Enter, Escape |

---

## Testing

```tsx
// testing-library example
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('Select opens on click and selects item', async () => {
  const onValueChange = jest.fn();

  render(
    <Select.Root onValueChange={onValueChange}>
      <Select.Trigger>Select fruit</Select.Trigger>
      <Select.Content>
        <Select.Item value="apple">Apple</Select.Item>
        <Select.Item value="banana">Banana</Select.Item>
      </Select.Content>
    </Select.Root>
  );

  // Open
  await userEvent.click(screen.getByRole('combobox'));
  expect(screen.getByRole('listbox')).toBeVisible();

  // Select
  await userEvent.click(screen.getByRole('option', { name: 'Apple' }));
  expect(onValueChange).toHaveBeenCalledWith('apple');
});
```

---

## When NOT to Use Compound Components

| Situation | Better Alternative |
|-----------|-------------------|
| Simple button | Single component |
| Static content | Plain HTML |
| One-off component | Monolithic with props |
| No composition needed | Props-based API |

Compound components add complexity. Use them when you need the flexibility they provide.
