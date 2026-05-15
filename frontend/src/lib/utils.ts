import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatEuro(value?: number | null): string {
  if (value === null || value === undefined) {
    return "Tidak tersedia";
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("id-ID", {
      maximumFractionDigits: 1
    })}M EUR`;
  }

  return `${value.toLocaleString("id-ID")} EUR`;
}

export function formatNumber(value?: number | null): string {
  if (value === null || value === undefined) {
    return "-";
  }

  return value.toLocaleString("id-ID");
}

export function getPositionCode(position?: string | null): "GK" | "DEF" | "MID" | "FWD" {
  const normalized = (position ?? "").toLowerCase();
  if (normalized.includes("goalkeeper")) {
    return "GK";
  }
  if (normalized.includes("defender")) {
    return "DEF";
  }
  if (normalized.includes("midfielder")) {
    return "MID";
  }
  return "FWD";
}

export function getPositionAccentClass(position?: string | null): string {
  const code = getPositionCode(position);
  if (code === "GK") {
    return "border-position-gk";
  }
  if (code === "DEF") {
    return "border-position-def";
  }
  if (code === "MID") {
    return "border-position-mid";
  }
  return "border-position-fwd";
}

export function getPositionTextClass(position?: string | null): string {
  const code = getPositionCode(position);
  if (code === "GK") {
    return "text-position-gk";
  }
  if (code === "DEF") {
    return "text-position-def";
  }
  if (code === "MID") {
    return "text-position-mid";
  }
  return "text-position-fwd";
}
