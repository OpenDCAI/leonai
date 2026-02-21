---
name: color-contrast
description: Validates WCAG 2.1 contrast ratios and generates accessible color pairings. Use when checking accessibility compliance, fixing contrast issues, or selecting text/background combinations for AA or AAA levels.
---

# Color Contrast Checker

## Overview

Validate and generate accessible color combinations that meet WCAG 2.1 contrast requirements. Check existing palettes or find compliant alternatives for any color pair.

## When to Use

- Validating a color palette for accessibility
- Finding accessible text colors for a background
- Checking if brand colors meet WCAG standards
- Generating accessible color pairings from tokens

## Quick Reference: WCAG Requirements

| Level | Normal Text | Large Text | UI Components |
|-------|-------------|------------|---------------|
| AA | 4.5:1 | 3:1 | 3:1 |
| AAA | 7:1 | 4.5:1 | 4.5:1 |

**Large text**: 18pt (24px) regular or 14pt (18.5px) bold

## The Process

1. **Get colors**: Ask for foreground and background colors (hex, rgb, oklch, hsl)
2. **Calculate ratio**: Compute relative luminance and contrast ratio
3. **Report compliance**: Show AA/AAA pass/fail for text sizes
4. **If failing**: Suggest closest compliant alternatives
5. **Batch mode**: If given a palette, check all combinations

## Contrast Ratio Scale

| Ratio | Rating | Suitable For |
|-------|--------|--------------|
| 21:1 | Maximum | Black on white |
| 7:1+ | Excellent | AAA all text |
| 4.5:1+ | Good | AA normal text, AAA large |
| 3:1+ | Minimum | AA large text, UI components |
| < 3:1 | Failing | Decorative only |

## Output Formats

**Single Pair Check:**
```
Contrast Check: #1a1a1a on #ffffff

Ratio: 16.1:1

✓ AA Normal Text (4.5:1)
✓ AA Large Text (3:1)
✓ AAA Normal Text (7:1)
✓ AAA Large Text (4.5:1)
✓ UI Components (3:1)

Verdict: Passes all WCAG 2.1 criteria
```

**Failing Pair with Suggestions:**
```
Contrast Check: #6b7280 on #ffffff

Ratio: 4.0:1

✓ AA Large Text (3:1)
✗ AA Normal Text (4.5:1) - needs 4.5:1
✗ AAA Normal Text (7:1)
✓ UI Components (3:1)

Suggested fixes:
- Darken foreground to #5b6370 for AA (4.5:1)
- Darken foreground to #3d4351 for AAA (7:1)
```

**Palette Matrix:**
```
Color Contrast Matrix (AA Normal Text = 4.5:1)

             white    gray-100  gray-900  primary
white          -        1.1       16.1      5.2
gray-100      1.1        -        14.5      4.7
gray-900     16.1      14.5        -        3.1
primary       5.2       4.7       3.1        -

Legend: ✓ = 4.5:1+ | ⚠ = 3:1-4.5:1 | ✗ = <3:1
```

**CSS with Accessible Pairs:**
```css
:root {
  /* Accessible text on light backgrounds */
  --text-on-light: #1f2937;      /* 14.5:1 on white */
  --text-muted-on-light: #4b5563; /* 7.2:1 on white */

  /* Accessible text on dark backgrounds */
  --text-on-dark: #f9fafb;        /* 18.1:1 on gray-900 */
  --text-muted-on-dark: #d1d5db;  /* 11.3:1 on gray-900 */

  /* Accessible text on brand color */
  --text-on-primary: #ffffff;     /* 5.2:1 on primary-500 */
}
```

## Algorithm

**Relative Luminance (L):**
```
For each RGB channel (0-255):
1. Normalize: value / 255
2. If ≤ 0.03928: channel / 12.92
3. Else: ((channel + 0.055) / 1.055) ^ 2.4

L = 0.2126 * R + 0.7152 * G + 0.0722 * B
```

**Contrast Ratio:**
```
ratio = (L1 + 0.05) / (L2 + 0.05)
where L1 is lighter, L2 is darker
```

## Common Patterns

**Accessible grays on white:**
| Gray | Hex | Ratio | Use |
|------|-----|-------|-----|
| 600 | #4b5563 | 7.2:1 | Body text (AAA) |
| 500 | #6b7280 | 4.6:1 | Body text (AA) |
| 400 | #9ca3af | 2.9:1 | Large text only |

**Accessible brand colors:**
- Light backgrounds: Darken brand to 500-700 range
- Dark backgrounds: Lighten brand to 300-400 range
- On brand: Use white (dark brands) or gray-900 (light brands)

## Integration with Color Scale

When using with the color-scale skill:

```
1. Generate palette with color-scale
2. Run contrast check on key combinations:
   - Text colors (900, 800) on backgrounds (50, 100)
   - Background (500) with white/dark text
   - Adjacent scale steps for borders
3. Adjust chroma/lightness if needed
4. Document accessible pairings
```

## Testing Checklist

- [ ] Primary text on all background colors
- [ ] Secondary/muted text on backgrounds
- [ ] Interactive elements (buttons, links)
- [ ] Focus indicators against backgrounds
- [ ] Error, warning, success states
- [ ] Disabled states (3:1 minimum for discernible)
- [ ] Placeholder text in inputs
