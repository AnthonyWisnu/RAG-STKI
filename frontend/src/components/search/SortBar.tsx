"use client";

import { ArrowUpDown } from "lucide-react";

import type { SearchFilterState } from "@/types";

type SortBarProps = {
  total: number;
  shown: number;
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
};

const sortOptions: Array<{ value: NonNullable<SearchFilterState["sort"]>; label: string }> = [
  { value: "name", label: "Nama" },
  { value: "market_value", label: "Nilai Pasar" },
  { value: "minutes", label: "Menit" },
  { value: "goals", label: "Gol" },
  { value: "assists", label: "Assist" }
];

export function SortBar({ total, shown, filters, onChange }: SortBarProps) {
  return (
    <div className="flex flex-col gap-3 border-y border-border py-3 md:flex-row md:items-center md:justify-between">
      <span className="text-sm text-text-secondary">
        Menampilkan {shown} dari {total} pemain
      </span>
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        <ArrowUpDown className="h-4 w-4" aria-hidden="true" />
        Urutkan
        <select
          value={filters.sort}
          onChange={(event) =>
            onChange({
              ...filters,
              sort: event.target.value as SearchFilterState["sort"],
              page: 1
            })
          }
          className="h-9 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary"
          aria-label="Urutkan hasil"
        >
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
