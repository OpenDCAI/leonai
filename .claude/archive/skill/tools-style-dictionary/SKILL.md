---
name: style-dictionary
description: Transforms design tokens into platform-specific formats (CSS, SCSS, iOS Swift, Android XML). Use when setting up multi-platform token pipelines, creating build processes, or managing cross-platform design systems.
---

# Style Dictionary

## Overview

Set up Style Dictionary to transform design tokens into platform-specific formats. The industry standard for design systems that need to output to web, iOS, Android, and other platforms from a single token source.

## When to Use

- Setting up a new design system with multi-platform needs
- Converting Figma tokens to code
- Generating CSS, SCSS, iOS Swift, Android XML from one source
- Adding custom token transforms or formats
- Integrating tokens into a build pipeline

## Quick Reference: Core Concepts

| Concept | Purpose | Example |
|---------|---------|---------|
| Token | Design value with metadata | `{ "value": "#3b82f6", "type": "color" }` |
| Transform | Converts token values | `color/hex` → `color/rgb` |
| Format | Outputs to file type | CSS variables, Swift, XML |
| Platform | Target environment | web, ios, android |

## The Process

1. **Assess token sources**: Where are tokens defined? (Figma, JSON, YAML)
2. **Identify platforms**: Which platforms need tokens?
3. **Set up config**: Create `style-dictionary.config.js`
4. **Define transforms**: Add any custom value transformations
5. **Build**: Run `style-dictionary build`

### Implementation Checklist

Copy this checklist when setting up Style Dictionary:

```
Style Dictionary Setup:
- [ ] Install: `npm install style-dictionary`
- [ ] Create tokens/ directory with source JSON files
- [ ] Create style-dictionary.config.js with source paths and platform outputs
- [ ] Add build script to package.json: `"tokens:build": "style-dictionary build"`
- [ ] Run build and verify output files are generated correctly
```

---

## Project Setup

### Installation

```bash
npm install style-dictionary
# or
yarn add style-dictionary
```

### Directory Structure

```
tokens/
├── base/
│   ├── colors.json
│   ├── spacing.json
│   └── typography.json
├── semantic/
│   ├── colors.json
│   └── components.json
└── themes/
    ├── light.json
    └── dark.json

build/                    # Generated output
├── css/
│   └── variables.css
├── ios/
│   └── StyleDictionary.swift
└── android/
    └── colors.xml

style-dictionary.config.js
```

---

## Configuration

### Basic Config

```js
// style-dictionary.config.js
module.exports = {
  source: ['tokens/**/*.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: 'build/css/',
      files: [
        {
          destination: 'variables.css',
          format: 'css/variables',
        },
      ],
    },
  },
};
```

### Multi-Platform Config

```js
// style-dictionary.config.js
module.exports = {
  source: ['tokens/**/*.json'],

  platforms: {
    // Web - CSS Custom Properties
    css: {
      transformGroup: 'css',
      buildPath: 'build/css/',
      files: [
        {
          destination: 'variables.css',
          format: 'css/variables',
          options: {
            outputReferences: true, // Keep token references
          },
        },
      ],
    },

    // Web - SCSS Variables
    scss: {
      transformGroup: 'scss',
      buildPath: 'build/scss/',
      files: [
        {
          destination: '_variables.scss',
          format: 'scss/variables',
        },
      ],
    },

    // Web - JavaScript/TypeScript
    js: {
      transformGroup: 'js',
      buildPath: 'build/js/',
      files: [
        {
          destination: 'tokens.js',
          format: 'javascript/es6',
        },
        {
          destination: 'tokens.d.ts',
          format: 'typescript/es6-declarations',
        },
      ],
    },

    // iOS - Swift
    ios: {
      transformGroup: 'ios-swift',
      buildPath: 'build/ios/',
      files: [
        {
          destination: 'StyleDictionary.swift',
          format: 'ios-swift/class.swift',
          className: 'StyleDictionary',
        },
      ],
    },

    // Android - XML Resources
    android: {
      transformGroup: 'android',
      buildPath: 'build/android/',
      files: [
        {
          destination: 'colors.xml',
          format: 'android/colors',
          filter: { type: 'color' },
        },
        {
          destination: 'dimens.xml',
          format: 'android/dimens',
          filter: { type: 'dimension' },
        },
      ],
    },
  },
};
```

---

## Token Format

### Design Tokens Community Group (DTCG) Format

```json
{
  "color": {
    "primary": {
      "$value": "#3b82f6",
      "$type": "color",
      "$description": "Primary brand color"
    },
    "secondary": {
      "$value": "#64748b",
      "$type": "color"
    }
  },
  "spacing": {
    "sm": {
      "$value": "8px",
      "$type": "dimension"
    },
    "md": {
      "$value": "16px",
      "$type": "dimension"
    }
  }
}
```

### Style Dictionary Classic Format

```json
{
  "color": {
    "primary": {
      "value": "#3b82f6",
      "type": "color",
      "comment": "Primary brand color"
    }
  },
  "spacing": {
    "sm": { "value": "8px" },
    "md": { "value": "16px" }
  }
}
```

### Token References (Aliases)

```json
{
  "color": {
    "base": {
      "blue": {
        "500": { "value": "#3b82f6" }
      }
    },
    "primary": {
      "value": "{color.base.blue.500}"
    },
    "button": {
      "background": {
        "value": "{color.primary}"
      }
    }
  }
}
```

---

## Custom Transforms

### Register Custom Transform

```js
// style-dictionary.config.js
const StyleDictionary = require('style-dictionary');

// Transform px to rem
StyleDictionary.registerTransform({
  name: 'size/pxToRem',
  type: 'value',
  matcher: (token) => token.type === 'dimension',
  transformer: (token) => {
    const px = parseFloat(token.value);
    return `${px / 16}rem`;
  },
});

// Transform color to OKLCH
StyleDictionary.registerTransform({
  name: 'color/oklch',
  type: 'value',
  matcher: (token) => token.type === 'color',
  transformer: (token) => {
    // Use a color library like culori
    const { formatCss, oklch, parse } = require('culori');
    return formatCss(oklch(parse(token.value)));
  },
});

module.exports = {
  source: ['tokens/**/*.json'],
  platforms: {
    css: {
      transforms: [
        'attribute/cti',
        'name/cti/kebab',
        'size/pxToRem',      // Custom
        'color/oklch',        // Custom
      ],
      buildPath: 'build/css/',
      files: [
        {
          destination: 'variables.css',
          format: 'css/variables',
        },
      ],
    },
  },
};
```

### Common Custom Transforms

```js
// Clamp font sizes for fluid typography
StyleDictionary.registerTransform({
  name: 'size/fluidType',
  type: 'value',
  matcher: (token) => token.attributes?.category === 'font' && token.attributes?.type === 'size',
  transformer: (token) => {
    const min = parseFloat(token.value) * 0.875;
    const max = parseFloat(token.value);
    return `clamp(${min}rem, 2vw + 1rem, ${max}rem)`;
  },
});

// Shadow to CSS format
StyleDictionary.registerTransform({
  name: 'shadow/css',
  type: 'value',
  matcher: (token) => token.type === 'shadow',
  transformer: (token) => {
    const { x, y, blur, spread, color } = token.value;
    return `${x}px ${y}px ${blur}px ${spread}px ${color}`;
  },
});
```

---

## Custom Formats

### CSS with Dark Mode

```js
StyleDictionary.registerFormat({
  name: 'css/variables-themed',
  formatter: ({ dictionary, options }) => {
    const lightTokens = dictionary.allTokens
      .filter(t => !t.path.includes('dark'))
      .map(t => `  --${t.name}: ${t.value};`)
      .join('\n');

    const darkTokens = dictionary.allTokens
      .filter(t => t.path.includes('dark'))
      .map(t => {
        const name = t.name.replace('dark-', '');
        return `  --${name}: ${t.value};`;
      })
      .join('\n');

    return `:root {\n${lightTokens}\n}\n\n[data-theme="dark"] {\n${darkTokens}\n}`;
  },
});
```

### Tailwind Config Format

```js
StyleDictionary.registerFormat({
  name: 'tailwind/config',
  formatter: ({ dictionary }) => {
    const colors = {};
    const spacing = {};

    dictionary.allTokens.forEach(token => {
      if (token.type === 'color') {
        const path = token.path.slice(1).join('-');
        colors[path] = token.value;
      }
      if (token.type === 'dimension' && token.path[0] === 'spacing') {
        spacing[token.path[1]] = token.value;
      }
    });

    return `module.exports = {
  theme: {
    extend: {
      colors: ${JSON.stringify(colors, null, 2)},
      spacing: ${JSON.stringify(spacing, null, 2)},
    },
  },
};`;
  },
});
```

---

## Multi-Theme Setup

### Token Structure

```
tokens/
├── core/
│   ├── colors.json      # Primitives (blue-500, gray-100)
│   └── spacing.json
├── semantic/
│   ├── light.json       # Semantic mappings for light
│   └── dark.json        # Semantic mappings for dark
└── brand/
    ├── default.json     # Default brand
    └── partner.json     # White-label brand
```

### Theme-Specific Config

```js
// style-dictionary.config.js
const themes = ['light', 'dark'];
const brands = ['default', 'partner'];

module.exports = {
  source: ['tokens/core/**/*.json'],

  platforms: brands.flatMap(brand =>
    themes.map(theme => ({
      [`css-${brand}-${theme}`]: {
        transformGroup: 'css',
        buildPath: `build/${brand}/`,
        files: [
          {
            destination: `${theme}.css`,
            format: 'css/variables',
            filter: (token) =>
              token.filePath.includes('core') ||
              token.filePath.includes(theme),
          },
        ],
        source: [
          `tokens/semantic/${theme}.json`,
          `tokens/brand/${brand}.json`,
        ],
      },
    }))
  ),
};
```

---

## Build Pipeline Integration

### package.json Scripts

```json
{
  "scripts": {
    "tokens:build": "style-dictionary build",
    "tokens:watch": "style-dictionary build --watch",
    "tokens:clean": "rm -rf build/",
    "prebuild": "npm run tokens:build"
  }
}
```

### With Figma Tokens Plugin

```bash
# 1. Export from Figma Tokens plugin to tokens/figma.json
# 2. Transform with Style Dictionary

npx token-transformer tokens/figma.json tokens/transformed.json
style-dictionary build
```

### GitHub Action

```yaml
# .github/workflows/tokens.yml
name: Build Tokens

on:
  push:
    paths:
      - 'tokens/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run tokens:build
      - uses: actions/upload-artifact@v4
        with:
          name: tokens
          path: build/
```

---

## Output Examples

### Input Token

```json
{
  "color": {
    "primary": {
      "value": "#3b82f6",
      "type": "color"
    }
  }
}
```

### CSS Output

```css
:root {
  --color-primary: #3b82f6;
}
```

### SCSS Output

```scss
$color-primary: #3b82f6;
```

### JavaScript Output

```js
export const ColorPrimary = '#3b82f6';
```

### iOS Swift Output

```swift
public class StyleDictionary {
    public static let colorPrimary = UIColor(red: 0.231, green: 0.510, blue: 0.965, alpha: 1.0)
}
```

### Android XML Output

```xml
<?xml version="1.0" encoding="UTF-8"?>
<resources>
  <color name="color_primary">#3b82f6</color>
</resources>
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Circular references | Check token aliases don't loop |
| Token not found | Verify path in reference matches exactly |
| Wrong output format | Check transform group matches platform |
| Missing tokens | Check `filter` isn't excluding them |
| Stale builds | Run `tokens:clean` before build |

## Style Dictionary v4 (Latest)

```js
// style-dictionary.config.js (v4 syntax)
import StyleDictionary from 'style-dictionary';

export default {
  source: ['tokens/**/*.json'],
  preprocessors: ['tokens-studio'], // For Figma Tokens
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: 'build/',
      files: [{
        destination: 'variables.css',
        format: 'css/variables',
      }],
    },
  },
};
```

```bash
# Run with ESM
node --experimental-json-modules ./node_modules/.bin/style-dictionary build
```
