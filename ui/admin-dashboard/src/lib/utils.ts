import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function sleep(ms: number = 1000) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Generates page numbers for pagination with ellipsis
 * @param currentPage - Current page number (1-based)
 * @param totalPages - Total number of pages
 * @returns Array of page numbers and ellipsis strings
 *
 * Examples:
 * - Small dataset (≤5 pages): [1, 2, 3, 4, 5]
 * - Near beginning: [1, 2, 3, 4, '...', 10]
 * - In middle: [1, '...', 4, 5, 6, '...', 10]
 * - Near end: [1, '...', 7, 8, 9, 10]
 */
export function getPageNumbers(currentPage: number, totalPages: number) {
  const maxVisiblePages = 5 // Maximum number of page buttons to show
  const rangeWithDots = []

  if (totalPages <= maxVisiblePages) {
    // If total pages is 5 or less, show all pages
    for (let i = 1; i <= totalPages; i++) {
      rangeWithDots.push(i)
    }
  } else {
    // Always show first page
    rangeWithDots.push(1)

    if (currentPage <= 3) {
      // Near the beginning: [1] [2] [3] [4] ... [10]
      for (let i = 2; i <= 4; i++) {
        rangeWithDots.push(i)
      }
      rangeWithDots.push('...', totalPages)
    } else if (currentPage >= totalPages - 2) {
      // Near the end: [1] ... [7] [8] [9] [10]
      rangeWithDots.push('...')
      for (let i = totalPages - 3; i <= totalPages; i++) {
        rangeWithDots.push(i)
      }
    } else {
      // In the middle: [1] ... [4] [5] [6] ... [10]
      rangeWithDots.push('...')
      for (let i = currentPage - 1; i <= currentPage + 1; i++) {
        rangeWithDots.push(i)
      }
      rangeWithDots.push('...', totalPages)
    }
  }

  return rangeWithDots
}




/////////////////////////////////////////

export function toStr(v: unknown): string {
    return v == null ? "" : String(v);
}

export function safeBool(v: unknown, def = false): boolean {
    if (typeof v === "boolean") return v;
    if (v === null || v === undefined || v === "" || v === "None") return def;
    if (typeof v === "number") return !!v;
    if (typeof v === "string") {
        const t = v.trim().toLowerCase();
        return ["1", "true", "t", "yes", "y", "on"].includes(t);
    }
    return def;
}

export function statusLevelFromText(text: string | undefined | null): "ok" | "warn" | "error" | "unknown" {
    if (!text) return "unknown";
    const t = String(text).trim().toLowerCase();
    const ok = ["ok", "healthy", "ready", "running", "active", "online", "up", "success"];
    const warn = ["pending", "starting", "initializing", "init", "degraded", "slow", "busy"];
    const err = ["error", "failed", "down", "crash", "unhealthy", "timeout", "offline"];
    if (ok.some(k => t.includes(k))) return "ok";
    if (warn.some(k => t.includes(k))) return "warn";
    if (err.some(k => t.includes(k))) return "error";
    return "unknown";
}

export function effectiveStatusForItem(raw: string | undefined, enabled: boolean): { level: "ok" | "warn" | "error" | "unknown" | "disabled"; label: string } {
    if (!enabled) return { level: "disabled", label: "Disabled" };
    const level = statusLevelFromText(raw);
    const labelMap = { ok: "OK", warn: "Warning", error: "Error", unknown: "Unknown" } as const;
    const text = toStr(raw) || "Unknown";
    return { level, label: `${labelMap[level]} (${text})` };
}
export function debounce<F extends (...args: any[]) => any>(func: F, waitFor: number) {
    let timeout: ReturnType<typeof setTimeout> | null = null;

    return (...args: Parameters<F>): void => {
        if (timeout) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(() => func(...args), waitFor);
    };
}

