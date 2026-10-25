/**
 * Deterministic formatting helpers.
 *
 * `Number.prototype.toLocaleString()` / `Date.prototype.toLocale*()` with no
 * explicit locale use the RUNTIME's default locale. The Next.js server (Node)
 * and the browser can resolve different defaults, so their formatted output
 * differs — causing React hydration mismatches. Pinning the locale (and, for
 * dates, the time zone) makes server- and client-rendered markup identical.
 */

const LOCALE = "en-US";

/** Group-separated integer/number string, stable across server and client. */
export function formatNumber(value: number): string {
  return value.toLocaleString(LOCALE);
}

/** Short date (e.g. "6/1/2025"), stable across server and client. */
export function formatDate(value: string | number | Date): string {
  return new Date(value).toLocaleDateString(LOCALE, { timeZone: "UTC" });
}

/** Date + time, stable across server and client. */
export function formatDateTime(value: string | number | Date): string {
  return new Date(value).toLocaleString(LOCALE, { timeZone: "UTC" });
}
