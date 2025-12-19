import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
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
function statusLevelFromText(
  text: string | undefined | null,
): "ok" | "warn" | "error" | "unknown" {
  if (!text) return "unknown";
  const t = String(text).trim().toLowerCase();
  const ok = [
    "ok",
    "healthy",
    "ready",
    "running",
    "active",
    "online",
    "up",
    "success",
  ];
  const warn = [
    "pending",
    "starting",
    "initializing",
    "init",
    "degraded",
    "slow",
    "busy",
  ];
  const err = [
    "error",
    "failed",
    "down",
    "crash",
    "unhealthy",
    "timeout",
    "offline",
  ];
  if (ok.some((k) => t.includes(k))) return "ok";
  if (warn.some((k) => t.includes(k))) return "warn";
  if (err.some((k) => t.includes(k))) return "error";
  return "unknown";
}


export function effectiveStatusForItem(
  raw: string | undefined,
  enabled: boolean,
): { level: "ok" | "warn" | "error" | "unknown" | "disabled"; label: string } {
  if (!enabled) return { level: "disabled", label: "Disabled" };
  const level = statusLevelFromText(raw);
  const labelMap = {
    ok: "OK",
    warn: "Warning",
    error: "Error",
    unknown: "Unknown",
  } as const;
  const text = toStr(raw) || "Unknown";
  return { level, label: `${labelMap[level]} (${text})` };
}
export function getErrorMessage(
  error: unknown,
  defaultMessage = "An unexpected error occurred.",
): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string" && error.length > 0) {
    return error;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as any).message === "string"
  ) {
    return (error as { message: string }).message;
  }

  return defaultMessage;
}
export function toStr(v: unknown): string {
  return v == null ? "" : String(v);
}
