/**
 * DateTime & Currency formatting helpers.
 */

/**
 * Format ISO datetime string into human-readable format:
 * e.g. "25 Aug 2026, 02:49:06 PM UTC"
 */
export function formatTimestamp(isoStr: string | null | undefined): string {
  if (!isoStr) return "—";

  // Ensure UTC parse when timezone offset is absent
  const hasTimezone =
    isoStr.endsWith("Z") ||
    isoStr.includes("+") ||
    (isoStr.includes("-") && isoStr.indexOf("-", 10) !== -1);

  const normalized = hasTimezone ? isoStr : `${isoStr}Z`;
  const d = new Date(normalized);
  if (isNaN(d.getTime())) return isoStr;

  const formatted = new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZone: "UTC",
  }).format(d);

  return `${formatted} UTC`;
}

/**
 * Format date string (YYYY-MM-DD) into "25 Aug 2026".
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/**
 * Format INR currency: e.g. ₹1,23,456
 */
export function formatINR(val: number | string | null | undefined): string {
  if (val === null || val === undefined) return "₹0";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "₹0";
  return `₹${num.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
