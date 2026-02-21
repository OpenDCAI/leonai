---
name: framer
description: Integrates design tokens with Framer for prototyping and production sites. Use when adding CSS custom properties to Framer projects, creating code components, or building Framer sites with design systems.
---

# Framer Token Integration

## Overview

Integrate design tokens with Framer for consistent prototyping and production sites. Use CSS custom properties, Framer overrides, and code components to bring your design system into Framer.

## When to Use

- Setting up design tokens in Framer
- Creating Framer code components with tokens
- Building interactive prototypes with design system
- Publishing Framer sites with consistent styling

## Quick Reference: Integration Methods

| Method | Use Case | Complexity |
|--------|----------|------------|
| CSS Variables | Global token import | Simple |
| Code Components | Custom React components | Medium |
| Overrides | Dynamic styling | Simple |
| Framer Library | Shared component library | Advanced |

## The Process

1. **Export tokens as CSS**: Generate CSS custom properties file
2. **Import in Framer**: Add to custom code or component
3. **Create code components**: Build with token references
4. **Set up overrides**: Apply dynamic styles
5. **Publish and maintain**: Keep tokens in sync

---

## CSS Variables in Framer

### Global CSS Import

**In Framer Site Settings → Custom Code → Head:**
```html
<style>
  :root {
    /* Colors */
    --color-primary-50: #eff6ff;
    --color-primary-100: #dbeafe;
    --color-primary-500: #3b82f6;
    --color-primary-600: #2563eb;
    --color-primary-900: #1e3a8a;

    --color-gray-50: #f9fafb;
    --color-gray-100: #f3f4f6;
    --color-gray-500: #6b7280;
    --color-gray-900: #111827;

    --color-success-500: #22c55e;
    --color-warning-500: #f59e0b;
    --color-error-500: #ef4444;

    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;

    /* Typography */
    --text-xs: 12px;
    --text-sm: 14px;
    --text-base: 16px;
    --text-lg: 18px;
    --text-xl: 20px;
    --text-2xl: 24px;

    /* Border Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 16px;
    --radius-full: 9999px;

    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  }

  /* Dark mode */
  [data-framer-theme="dark"] {
    --color-background: var(--color-gray-900);
    --color-foreground: var(--color-gray-50);
  }
</style>
```

### External CSS File

**Link your token CSS file:**
```html
<link rel="stylesheet" href="https://your-cdn.com/tokens.css">
```

---

## Code Components

### Button Component

**Button.tsx (Framer Code Component):**
```tsx
import { addPropertyControls, ControlType } from "framer"
import { motion } from "framer-motion"

interface ButtonProps {
  text: string
  variant: "primary" | "secondary" | "ghost" | "danger"
  size: "sm" | "md" | "lg"
  fullWidth: boolean
  disabled: boolean
  onClick?: () => void
}

export function Button({
  text = "Button",
  variant = "primary",
  size = "md",
  fullWidth = false,
  disabled = false,
  onClick,
}: ButtonProps) {
  const sizeStyles = {
    sm: {
      height: 32,
      padding: "0 var(--spacing-sm)",
      fontSize: "var(--text-sm)",
    },
    md: {
      height: 40,
      padding: "0 var(--spacing-md)",
      fontSize: "var(--text-base)",
    },
    lg: {
      height: 48,
      padding: "0 var(--spacing-lg)",
      fontSize: "var(--text-lg)",
    },
  }

  const variantStyles = {
    primary: {
      backgroundColor: "var(--color-primary-500)",
      color: "white",
      border: "none",
    },
    secondary: {
      backgroundColor: "transparent",
      color: "var(--color-gray-700)",
      border: "1px solid var(--color-gray-300)",
    },
    ghost: {
      backgroundColor: "transparent",
      color: "var(--color-gray-700)",
      border: "none",
    },
    danger: {
      backgroundColor: "var(--color-error-500)",
      color: "white",
      border: "none",
    },
  }

  const hoverStyles = {
    primary: { backgroundColor: "var(--color-primary-600)" },
    secondary: { backgroundColor: "var(--color-gray-50)" },
    ghost: { backgroundColor: "var(--color-gray-100)" },
    danger: { backgroundColor: "var(--color-error-600)" },
  }

  return (
    <motion.button
      style={{
        ...sizeStyles[size],
        ...variantStyles[variant],
        width: fullWidth ? "100%" : "auto",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--spacing-xs)",
        borderRadius: "var(--radius-md)",
        fontWeight: 500,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        fontFamily: "inherit",
        outline: "none",
      }}
      whileHover={disabled ? {} : hoverStyles[variant]}
      whileTap={disabled ? {} : { scale: 0.98 }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
    >
      {text}
    </motion.button>
  )
}

addPropertyControls(Button, {
  text: {
    type: ControlType.String,
    title: "Text",
    defaultValue: "Button",
  },
  variant: {
    type: ControlType.Enum,
    title: "Variant",
    options: ["primary", "secondary", "ghost", "danger"],
    optionTitles: ["Primary", "Secondary", "Ghost", "Danger"],
    defaultValue: "primary",
  },
  size: {
    type: ControlType.Enum,
    title: "Size",
    options: ["sm", "md", "lg"],
    optionTitles: ["Small", "Medium", "Large"],
    defaultValue: "md",
  },
  fullWidth: {
    type: ControlType.Boolean,
    title: "Full Width",
    defaultValue: false,
  },
  disabled: {
    type: ControlType.Boolean,
    title: "Disabled",
    defaultValue: false,
  },
})
```

### Card Component

**Card.tsx:**
```tsx
import { addPropertyControls, ControlType } from "framer"
import type { ReactNode } from "react"

interface CardProps {
  children?: ReactNode
  padding: "none" | "sm" | "md" | "lg"
  elevation: "none" | "sm" | "md" | "lg"
  radius: "none" | "sm" | "md" | "lg"
}

export function Card({
  children,
  padding = "md",
  elevation = "sm",
  radius = "md",
}: CardProps) {
  const paddingMap = {
    none: 0,
    sm: "var(--spacing-sm)",
    md: "var(--spacing-md)",
    lg: "var(--spacing-lg)",
  }

  const shadowMap = {
    none: "none",
    sm: "var(--shadow-sm)",
    md: "var(--shadow-md)",
    lg: "var(--shadow-lg)",
  }

  const radiusMap = {
    none: 0,
    sm: "var(--radius-sm)",
    md: "var(--radius-md)",
    lg: "var(--radius-lg)",
  }

  return (
    <div
      style={{
        padding: paddingMap[padding],
        boxShadow: shadowMap[elevation],
        borderRadius: radiusMap[radius],
        backgroundColor: "white",
        width: "100%",
        height: "100%",
      }}
    >
      {children}
    </div>
  )
}

addPropertyControls(Card, {
  children: {
    type: ControlType.ComponentInstance,
    title: "Content",
  },
  padding: {
    type: ControlType.Enum,
    title: "Padding",
    options: ["none", "sm", "md", "lg"],
    optionTitles: ["None", "Small", "Medium", "Large"],
    defaultValue: "md",
  },
  elevation: {
    type: ControlType.Enum,
    title: "Elevation",
    options: ["none", "sm", "md", "lg"],
    optionTitles: ["None", "Small", "Medium", "Large"],
    defaultValue: "sm",
  },
  radius: {
    type: ControlType.Enum,
    title: "Radius",
    options: ["none", "sm", "md", "lg"],
    optionTitles: ["None", "Small", "Medium", "Large"],
    defaultValue: "md",
  },
})
```

### Input Component

**Input.tsx:**
```tsx
import { addPropertyControls, ControlType } from "framer"
import { useState } from "react"

interface InputProps {
  label: string
  placeholder: string
  helperText: string
  error: string
  disabled: boolean
  required: boolean
  type: "text" | "email" | "password" | "number"
  size: "sm" | "md" | "lg"
}

export function Input({
  label = "",
  placeholder = "Enter text...",
  helperText = "",
  error = "",
  disabled = false,
  required = false,
  type = "text",
  size = "md",
}: InputProps) {
  const [value, setValue] = useState("")
  const [focused, setFocused] = useState(false)

  const sizeStyles = {
    sm: { height: 32, fontSize: "var(--text-sm)" },
    md: { height: 40, fontSize: "var(--text-base)" },
    lg: { height: 48, fontSize: "var(--text-lg)" },
  }

  const hasError = !!error

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
      {label && (
        <label
          style={{
            fontSize: "var(--text-sm)",
            fontWeight: 500,
            color: "var(--color-gray-700)",
          }}
        >
          {label}
          {required && <span style={{ color: "var(--color-error-500)" }}> *</span>}
        </label>
      )}

      <input
        type={type}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        disabled={disabled}
        style={{
          ...sizeStyles[size],
          padding: "0 var(--spacing-md)",
          border: `1px solid ${
            hasError
              ? "var(--color-error-500)"
              : focused
              ? "var(--color-primary-500)"
              : "var(--color-gray-300)"
          }`,
          borderRadius: "var(--radius-md)",
          outline: "none",
          boxShadow: focused
            ? `0 0 0 3px ${hasError ? "rgb(239 68 68 / 0.15)" : "rgb(59 130 246 / 0.15)"}`
            : "none",
          backgroundColor: disabled ? "var(--color-gray-100)" : "white",
          color: "var(--color-gray-900)",
          fontFamily: "inherit",
          transition: "border-color 150ms, box-shadow 150ms",
        }}
      />

      {(error || helperText) && (
        <span
          style={{
            fontSize: "var(--text-sm)",
            color: hasError ? "var(--color-error-500)" : "var(--color-gray-500)",
          }}
        >
          {error || helperText}
        </span>
      )}
    </div>
  )
}

addPropertyControls(Input, {
  label: { type: ControlType.String, title: "Label", defaultValue: "Label" },
  placeholder: { type: ControlType.String, title: "Placeholder", defaultValue: "Enter text..." },
  helperText: { type: ControlType.String, title: "Helper Text" },
  error: { type: ControlType.String, title: "Error" },
  type: {
    type: ControlType.Enum,
    title: "Type",
    options: ["text", "email", "password", "number"],
    defaultValue: "text",
  },
  size: {
    type: ControlType.Enum,
    title: "Size",
    options: ["sm", "md", "lg"],
    optionTitles: ["Small", "Medium", "Large"],
    defaultValue: "md",
  },
  disabled: { type: ControlType.Boolean, title: "Disabled", defaultValue: false },
  required: { type: ControlType.Boolean, title: "Required", defaultValue: false },
})
```

---

## Overrides

### Dynamic Styling with Tokens

**tokenOverrides.ts:**
```tsx
import type { ComponentType } from "react"

// Apply primary button styling
export function withPrimaryButton(Component: ComponentType): ComponentType {
  return (props: any) => {
    return (
      <Component
        {...props}
        style={{
          ...props.style,
          backgroundColor: "var(--color-primary-500)",
          color: "white",
          borderRadius: "var(--radius-md)",
          padding: "0 var(--spacing-md)",
          height: 40,
          fontWeight: 500,
        }}
      />
    )
  }
}

// Apply card styling
export function withCard(Component: ComponentType): ComponentType {
  return (props: any) => {
    return (
      <Component
        {...props}
        style={{
          ...props.style,
          backgroundColor: "white",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-md)",
          padding: "var(--spacing-lg)",
        }}
      />
    )
  }
}

// Responsive text sizing
export function withResponsiveText(Component: ComponentType): ComponentType {
  return (props: any) => {
    return (
      <Component
        {...props}
        style={{
          ...props.style,
          fontSize: "clamp(var(--text-base), 2.5vw, var(--text-xl))",
        }}
      />
    )
  }
}
```

### Theme Toggle Override

**themeOverride.ts:**
```tsx
import { useState, useEffect } from "react"
import type { ComponentType } from "react"

export function withThemeToggle(Component: ComponentType): ComponentType {
  return (props: any) => {
    const [theme, setTheme] = useState<"light" | "dark">("light")

    useEffect(() => {
      document.documentElement.dataset.framerTheme = theme
    }, [theme])

    const toggleTheme = () => {
      setTheme(theme === "light" ? "dark" : "light")
    }

    return <Component {...props} onClick={toggleTheme} />
  }
}
```

---

## Framer Library Setup

### Shared Component Package

**package.json:**
```json
{
  "name": "@acme/framer-components",
  "version": "1.0.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "peerDependencies": {
    "framer": "*",
    "framer-motion": "*",
    "react": "^18.0.0"
  },
  "scripts": {
    "build": "tsc",
    "publish:framer": "framer-cli publish"
  }
}
```

**index.ts:**
```tsx
export { Button } from "./components/Button"
export { Input } from "./components/Input"
export { Card } from "./components/Card"
export { Stack } from "./components/Stack"

// Re-export tokens as JS object for code components
export { tokens } from "./tokens"
```

---

## Token Sync Workflow

### Automated Token Updates

**sync-to-framer.ts:**
```typescript
import fs from "fs"

interface Token {
  value: string
  type: string
}

function tokensToCSS(tokens: Record<string, any>, prefix = ""): string {
  let css = ""

  for (const [key, value] of Object.entries(tokens)) {
    const path = prefix ? `${prefix}-${key}` : key

    if (typeof value === "object" && "value" in value) {
      css += `  --${path}: ${value.value};\n`
    } else if (typeof value === "object") {
      css += tokensToCSS(value, path)
    }
  }

  return css
}

function generateFramerCSS(tokensPath: string, outputPath: string): void {
  const tokens = JSON.parse(fs.readFileSync(tokensPath, "utf-8"))

  const css = `:root {\n${tokensToCSS(tokens)}}\n`

  fs.writeFileSync(outputPath, css)
  console.log(`Generated ${outputPath}`)
}

generateFramerCSS("./tokens/tokens.json", "./framer/tokens.css")
```

---

## Best Practices

1. **Use CSS variables**: Framer supports CSS custom properties natively
2. **Centralize tokens**: Import tokens once in site settings
3. **Create code components**: Build reusable components with property controls
4. **Use consistent naming**: Match Framer property names to token names
5. **Document for designers**: Explain which tokens map to which controls
6. **Test dark mode**: Ensure token switching works properly
7. **Version control**: Keep Framer components in sync with design system

## Common Patterns

| Pattern | Implementation |
|---------|----------------|
| Hover states | Use `whileHover` with token color values |
| Focus rings | Apply `boxShadow` with token-based focus color |
| Responsive spacing | Use token values in responsive breakpoints |
| Theme switching | Toggle `data-theme` attribute on root |
| Loading states | Use token colors for spinner/skeleton |
