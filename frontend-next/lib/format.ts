import type { MetricSet } from "./types";

export function formatNumber(value?: number | null, fractionDigits = 0): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(value);
}

export function percent(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${formatNumber(value * 100, 1)}%`;
}

export function metricLine(metrics?: MetricSet | null) {
  if (!metrics) return "MAE - / RMSE - / MAPE -";
  return `MAE ${formatNumber(metrics.mae, 2)} / RMSE ${formatNumber(metrics.rmse, 2)} / MAPE ${formatNumber(metrics.mape, 2)}%`;
}

export function compactText(value?: string | number | null, fallback = "-"): string {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}
