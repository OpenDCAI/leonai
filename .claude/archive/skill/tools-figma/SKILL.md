---
name: figma
description: Syncs design tokens between code and Figma using Variables API or Tokens Studio plugin. Use when establishing Figma-to-code workflows, exporting Figma tokens, or setting up design-development handoff.
---

# Figma Token Integration

## Overview

Sync design tokens between code and Figma using Figma Variables, the Tokens Studio plugin, or Style Dictionary. Establish a single source of truth workflow for design-to-code handoff.

## When to Use

- Setting up Figma Variables from code tokens
- Exporting Figma styles to code tokens
- Establishing a design token workflow
- Syncing colors, typography, and spacing with Figma

## Quick Reference: Figma Token Types

| Figma Type | Maps To | Example |
|------------|---------|---------|
| Color Variable | `--color-*` | `--color-primary-500` |
| Number Variable | `--spacing-*`, `--radius-*` | `--spacing-md` |
| String Variable | Font family, mode names | `--font-sans` |
| Boolean Variable | Feature flags | Theme mode toggles |

## The Process

1. **Choose workflow direction**:
   - Code → Figma (tokens are source of truth in code)
   - Figma → Code (designers own tokens in Figma)
   - Bidirectional (sync both ways)
2. **Select tooling**: Native Variables, Tokens Studio, or custom
3. **Define token structure**: Categories, naming, modes
4. **Set up sync mechanism**: Plugin, API, or manual
5. **Document workflow**: Who updates what, when to sync

## Workflow Options

| Approach | Best For | Tools |
|----------|----------|-------|
| Figma Variables (native) | Simple setups, color/number tokens | Figma UI, REST API |
| Tokens Studio | Complex tokens, multi-file | Tokens Studio plugin + GitHub |
| Style Dictionary | Enterprise, CI/CD integration | Style Dictionary + Figma API |
| Manual sync | Small teams, infrequent changes | Copy/paste with conventions |

---

## Figma Variables (Native)

### Creating Variables from Code Tokens

**Token structure for Figma:**
```json
{
  "color": {
    "primary": {
      "50": { "value": "#eff6ff", "type": "color" },
      "100": { "value": "#dbeafe", "type": "color" },
      "500": { "value": "#3b82f6", "type": "color" },
      "900": { "value": "#1e3a8a", "type": "color" }
    },
    "gray": {
      "50": { "value": "#f9fafb", "type": "color" },
      "900": { "value": "#111827", "type": "color" }
    }
  },
  "spacing": {
    "xs": { "value": 4, "type": "number" },
    "sm": { "value": 8, "type": "number" },
    "md": { "value": 16, "type": "number" },
    "lg": { "value": 24, "type": "number" }
  },
  "radius": {
    "sm": { "value": 4, "type": "number" },
    "md": { "value": 8, "type": "number" },
    "lg": { "value": 16, "type": "number" },
    "full": { "value": 9999, "type": "number" }
  }
}
```

### Figma REST API Example

**Create variables via API:**
```typescript
import Anthropic from '@anthropic-ai/sdk'; // Example using Figma API

interface FigmaVariable {
  name: string;
  resolvedType: 'COLOR' | 'FLOAT' | 'STRING' | 'BOOLEAN';
  valuesByMode: Record<string, any>;
}

async function createFigmaVariables(
  fileKey: string,
  collectionName: string,
  tokens: Record<string, any>
): Promise<void> {
  const accessToken = process.env.FIGMA_ACCESS_TOKEN;

  // Step 1: Create variable collection
  const collectionResponse = await fetch(
    `https://api.figma.com/v1/files/${fileKey}/variables`,
    {
      method: 'POST',
      headers: {
        'X-Figma-Token': accessToken,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        variableCollections: [
          {
            action: 'CREATE',
            name: collectionName,
            initialModeId: 'light',
          },
        ],
      }),
    }
  );

  const { variableCollections } = await collectionResponse.json();
  const collectionId = variableCollections[0].id;

  // Step 2: Create variables
  const variables: FigmaVariable[] = [];

  for (const [category, values] of Object.entries(tokens)) {
    for (const [name, token] of Object.entries(values as Record<string, any>)) {
      variables.push({
        name: `${category}/${name}`,
        resolvedType: token.type === 'color' ? 'COLOR' : 'FLOAT',
        valuesByMode: {
          light: parseValue(token.value, token.type),
        },
      });
    }
  }

  await fetch(`https://api.figma.com/v1/files/${fileKey}/variables`, {
    method: 'POST',
    headers: {
      'X-Figma-Token': accessToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      variables: variables.map((v) => ({
        action: 'CREATE',
        variableCollectionId: collectionId,
        ...v,
      })),
    }),
  });
}

function parseValue(value: string | number, type: string): any {
  if (type === 'color') {
    // Convert hex to Figma RGBA
    const hex = value as string;
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    return { r, g, b, a: 1 };
  }
  return value;
}
```

### Variable Modes (Theming)

**Light/dark mode setup:**
```json
{
  "variableCollections": [
    {
      "name": "Semantic Colors",
      "modes": [
        { "name": "Light", "modeId": "light" },
        { "name": "Dark", "modeId": "dark" }
      ]
    }
  ],
  "variables": [
    {
      "name": "background/default",
      "valuesByMode": {
        "light": { "type": "VARIABLE_ALIAS", "id": "color/gray/50" },
        "dark": { "type": "VARIABLE_ALIAS", "id": "color/gray/900" }
      }
    },
    {
      "name": "text/primary",
      "valuesByMode": {
        "light": { "type": "VARIABLE_ALIAS", "id": "color/gray/900" },
        "dark": { "type": "VARIABLE_ALIAS", "id": "color/gray/50" }
      }
    }
  ]
}
```

---

## Tokens Studio Integration

### Token File Structure

**tokens.json (Tokens Studio format):**
```json
{
  "global": {
    "colors": {
      "primary": {
        "50": { "value": "#eff6ff", "type": "color" },
        "500": { "value": "#3b82f6", "type": "color" },
        "900": { "value": "#1e3a8a", "type": "color" }
      },
      "gray": {
        "50": { "value": "#f9fafb", "type": "color" },
        "900": { "value": "#111827", "type": "color" }
      }
    },
    "spacing": {
      "xs": { "value": "4", "type": "spacing" },
      "sm": { "value": "8", "type": "spacing" },
      "md": { "value": "16", "type": "spacing" },
      "lg": { "value": "24", "type": "spacing" }
    },
    "borderRadius": {
      "sm": { "value": "4", "type": "borderRadius" },
      "md": { "value": "8", "type": "borderRadius" },
      "lg": { "value": "16", "type": "borderRadius" }
    },
    "fontFamilies": {
      "sans": { "value": "Inter", "type": "fontFamilies" },
      "mono": { "value": "JetBrains Mono", "type": "fontFamilies" }
    },
    "fontSizes": {
      "xs": { "value": "12", "type": "fontSizes" },
      "sm": { "value": "14", "type": "fontSizes" },
      "base": { "value": "16", "type": "fontSizes" },
      "lg": { "value": "18", "type": "fontSizes" }
    },
    "lineHeights": {
      "tight": { "value": "1.25", "type": "lineHeights" },
      "normal": { "value": "1.5", "type": "lineHeights" },
      "relaxed": { "value": "1.75", "type": "lineHeights" }
    }
  },
  "light": {
    "bg": {
      "default": { "value": "{global.colors.gray.50}", "type": "color" },
      "subtle": { "value": "{global.colors.gray.100}", "type": "color" }
    },
    "text": {
      "primary": { "value": "{global.colors.gray.900}", "type": "color" },
      "secondary": { "value": "{global.colors.gray.600}", "type": "color" }
    }
  },
  "dark": {
    "bg": {
      "default": { "value": "{global.colors.gray.900}", "type": "color" },
      "subtle": { "value": "{global.colors.gray.800}", "type": "color" }
    },
    "text": {
      "primary": { "value": "{global.colors.gray.50}", "type": "color" },
      "secondary": { "value": "{global.colors.gray.400}", "type": "color" }
    }
  }
}
```

### Tokens Studio → Code Transform

**Style Dictionary config (sd.config.js):**
```javascript
module.exports = {
  source: ['tokens/**/*.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: 'dist/css/',
      files: [
        {
          destination: 'variables.css',
          format: 'css/variables',
          filter: (token) => token.filePath.includes('global'),
        },
        {
          destination: 'light.css',
          format: 'css/variables',
          filter: (token) => token.filePath.includes('light'),
          options: {
            selector: ':root, [data-theme="light"]',
          },
        },
        {
          destination: 'dark.css',
          format: 'css/variables',
          filter: (token) => token.filePath.includes('dark'),
          options: {
            selector: '[data-theme="dark"]',
          },
        },
      ],
    },
    tailwind: {
      transformGroup: 'js',
      buildPath: 'dist/',
      files: [
        {
          destination: 'tailwind.tokens.js',
          format: 'javascript/module',
        },
      ],
    },
  },
};
```

---

## Figma Plugin Development

### Plugin for Token Sync

**manifest.json:**
```json
{
  "name": "Token Sync",
  "id": "token-sync-plugin",
  "api": "1.0.0",
  "main": "code.js",
  "ui": "ui.html",
  "editorType": ["figma"],
  "networkAccess": {
    "allowedDomains": ["api.github.com"]
  }
}
```

**code.ts (plugin logic):**
```typescript
figma.showUI(__html__, { width: 400, height: 500 });

figma.ui.onmessage = async (msg) => {
  if (msg.type === 'import-tokens') {
    await importTokens(msg.tokens);
  } else if (msg.type === 'export-tokens') {
    const tokens = await exportTokens();
    figma.ui.postMessage({ type: 'tokens-exported', tokens });
  }
};

async function importTokens(tokens: Record<string, any>): Promise<void> {
  // Get or create collection
  const collections = await figma.variables.getLocalVariableCollectionsAsync();
  let collection = collections.find((c) => c.name === 'Design Tokens');

  if (!collection) {
    collection = figma.variables.createVariableCollection('Design Tokens');
  }

  const modeId = collection.modes[0].modeId;

  // Import each token
  for (const [path, token] of flattenTokens(tokens)) {
    const existing = await figma.variables.getVariableByIdAsync(
      `VariableID:${path.replace(/\//g, ':')}`
    );

    if (existing) {
      existing.setValueForMode(modeId, parseTokenValue(token));
    } else {
      const variable = figma.variables.createVariable(
        path,
        collection,
        getVariableType(token.type)
      );
      variable.setValueForMode(modeId, parseTokenValue(token));
    }
  }

  figma.notify(`Imported ${Object.keys(tokens).length} tokens`);
}

async function exportTokens(): Promise<Record<string, any>> {
  const tokens: Record<string, any> = {};
  const collections = await figma.variables.getLocalVariableCollectionsAsync();

  for (const collection of collections) {
    for (const variableId of collection.variableIds) {
      const variable = await figma.variables.getVariableByIdAsync(variableId);
      if (!variable) continue;

      const path = variable.name.split('/');
      let current = tokens;

      for (let i = 0; i < path.length - 1; i++) {
        current[path[i]] = current[path[i]] || {};
        current = current[path[i]];
      }

      const modeId = collection.modes[0].modeId;
      current[path[path.length - 1]] = {
        value: formatValue(variable.valuesByMode[modeId], variable.resolvedType),
        type: mapVariableType(variable.resolvedType),
      };
    }
  }

  return tokens;
}

function* flattenTokens(
  obj: Record<string, any>,
  path: string[] = []
): Generator<[string, any]> {
  for (const [key, value] of Object.entries(obj)) {
    if (value.value !== undefined) {
      yield [path.concat(key).join('/'), value];
    } else {
      yield* flattenTokens(value, path.concat(key));
    }
  }
}

function getVariableType(type: string): VariableResolvedDataType {
  switch (type) {
    case 'color':
      return 'COLOR';
    case 'spacing':
    case 'borderRadius':
    case 'fontSizes':
      return 'FLOAT';
    default:
      return 'STRING';
  }
}

function parseTokenValue(token: { value: string; type: string }): VariableValue {
  if (token.type === 'color') {
    return hexToRgba(token.value);
  }
  if (['spacing', 'borderRadius', 'fontSizes'].includes(token.type)) {
    return parseFloat(token.value);
  }
  return token.value;
}

function hexToRgba(hex: string): RGBA {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return { r, g, b, a: 1 };
}
```

---

## Naming Conventions

| Category | Figma Convention | Code Convention |
|----------|------------------|-----------------|
| Colors | `color/primary/500` | `--color-primary-500` |
| Spacing | `spacing/md` | `--spacing-md` |
| Radius | `radius/lg` | `--radius-lg` |
| Typography | `text/body/regular` | `--text-body` |
| Shadows | `shadow/md` | `--shadow-md` |
| Semantic | `bg/default` | `--color-bg-default` |

---

## Workflow Best Practices

1. **Single source of truth**: Decide if code or Figma owns tokens
2. **Version control**: Store token files in Git
3. **CI/CD integration**: Auto-sync on merge to main
4. **Semantic tokens**: Use aliases for theme-aware values
5. **Documentation**: Keep a mapping document for designers
6. **Validation**: Lint tokens before sync

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Color format mismatch | Normalize to hex or RGB before sync |
| Spacing units | Use unitless in Figma, add px/rem in code |
| Missing tokens | Validate token coverage before sync |
| Mode drift | Sync all modes together, not separately |
| Name collisions | Establish naming convention upfront |
