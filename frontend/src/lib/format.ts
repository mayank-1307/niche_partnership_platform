export function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value.replace(/[$,\s]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

const currencyKeyPattern = /(usd|currency|deal.?size|funding|revenue|valuation|contract|amount|budget|price|pricing|cost|arr|mrr)/i;
const currencyTextPattern = /(\$|usd|dollar|deal size|funding|revenue|valuation|contract value)/i;

export function isCurrencyKey(key: string): boolean {
  return currencyKeyPattern.test(key);
}

function parseCompactCurrency(value: string): number | null {
  const match = value.trim().match(/[-+]?\$?\s*([\d,.]+)\s*([kmb])?/i);
  if (!match) return null;

  const base = Number(match[1].replace(/,/g, ""));
  if (!Number.isFinite(base)) return null;

  const suffix = match[2]?.toLowerCase();
  if (suffix === "k") return base * 1_000;
  if (suffix === "m") return base * 1_000_000;
  if (suffix === "b") return base * 1_000_000_000;
  return base;
}

export function formatUsd(value: unknown): string {
  const amount = typeof value === "string" ? parseCompactCurrency(value) : asNumber(value);
  if (amount === null) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);
}

export function formatCurrencyDisplay(value: unknown, key = ""): string | null {
  if (typeof value === "number") {
    return isCurrencyKey(key) ? formatUsd(value) : null;
  }

  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!isCurrencyKey(key) && !currencyTextPattern.test(trimmed)) return null;

  const parts = trimmed.split(/\s*(?:-|to|–|—)\s*/i).filter(Boolean);
  if (parts.length >= 2) {
    const formattedRange = parts.slice(0, 2).map((part) => formatUsd(part));
    if (formattedRange.every((part) => part !== "-")) {
      return formattedRange.join(" - ");
    }
  }

  const formatted = formatUsd(trimmed);
  return formatted === "-" ? null : formatted;
}
