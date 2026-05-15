"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import type { SearchFilterState } from "@/types";

type ActiveFilterChipsProps = {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  onReset: () => void;
};

const labels: Partial<Record<keyof SearchFilterState, string>> = {
  q: "Nama",
  position: "Posisi",
  league: "Liga",
  minMinutes: "Min Menit",
  minValue: "Min Nilai",
  maxValue: "Max Nilai",
  minGoals: "Min Gol",
  minAssists: "Min Assist"
};

export function ActiveFilterChips({ filters, onChange, onReset }: ActiveFilterChipsProps) {
  const activeEntries = Object.entries(labels)
    .map(([key, label]) => ({
      key: key as keyof SearchFilterState,
      label,
      value: filters[key as keyof SearchFilterState]
    }))
    .filter((entry) => Boolean(entry.value));

  if (activeEntries.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {activeEntries.map((entry) => (
        <button
          key={entry.key}
          type="button"
          onClick={() => onChange({ ...filters, [entry.key]: "", page: 1 })}
          className="inline-flex items-center gap-2 rounded-panel border border-accent bg-accent-dim px-3 py-1.5 text-xs text-accent"
        >
          {entry.label}: {entry.value}
          <X className="h-3 w-3" aria-hidden="true" />
        </button>
      ))}
      <Button variant="ghost" className="min-h-8 px-2 py-1 text-xs" onClick={onReset}>
        Reset Semua
      </Button>
    </div>
  );
}
