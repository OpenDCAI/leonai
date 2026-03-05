/**
 * Shared formatting utilities for resource metrics
 */

export function formatNumber(value: number | null | undefined, nullText: string = "--"): string {
  if (value == null) {
    return nullText;
  }
  if (Number.isInteger(value)) {
    return String(value);
  }
  return value.toFixed(1).replace(/\.0$/, "");
}

export function formatMetric(value: number | null | undefined, unit: string): string {
  if (value == null) return "--";
  return `${formatNumber(value)}${unit}`;
}

export function formatLimit(limit: number | null | undefined, unit: string, nullText: string = "--"): string {
  if (limit == null) {
    return `limit: ${nullText} ${unit}`;
  }
  return `limit: ${formatNumber(limit)} ${unit}`;
}
