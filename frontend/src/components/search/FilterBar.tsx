"use client";

import { Search, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/Button";
import type { SearchFilterState } from "@/types";

type FilterBarProps = {
  filters: SearchFilterState;
  advancedOpen: boolean;
  onChange: (filters: SearchFilterState) => void;
  onToggleAdvanced: () => void;
};

const positions = ["", "Goalkeeper", "Defender", "Midfielder", "Forward"];
const leagues = ["", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"];
const seasons = ["2025-2026", "2024-2025", "2023-2024"];

export function FilterBar({ filters, advancedOpen, onChange, onToggleAdvanced }: FilterBarProps) {
  function update(key: keyof SearchFilterState, value: string) {
    onChange({ ...filters, [key]: value, page: 1 });
  }

  return (
    <div className="sticky top-14 z-10 border-b border-border bg-background-primary py-3">
      <div className="flex flex-col gap-3 xl:flex-row">
        <label className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            value={filters.q}
            onChange={(event) => update("q", event.target.value)}
            placeholder="Cari nama pemain..."
            className="h-11 w-full rounded-panel border border-border bg-background-secondary pl-10 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
        </label>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:w-[640px]">
          <select
            value={filters.position}
            onChange={(event) => update("position", event.target.value)}
            className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary"
            aria-label="Filter posisi"
          >
            {positions.map((position) => (
              <option key={position || "all"} value={position}>
                {position || "Semua Posisi"}
              </option>
            ))}
          </select>
          <select
            value={filters.league}
            onChange={(event) => update("league", event.target.value)}
            className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary"
            aria-label="Filter liga"
          >
            {leagues.map((league) => (
              <option key={league || "all"} value={league}>
                {league || "Semua Liga"}
              </option>
            ))}
          </select>
          <select
            value={filters.season}
            onChange={(event) => update("season", event.target.value)}
            className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary"
            aria-label="Filter musim"
          >
            {seasons.map((season) => (
              <option key={season} value={season}>
                {season}
              </option>
            ))}
          </select>
          <Button
            variant={advancedOpen ? "primary" : "secondary"}
            onClick={onToggleAdvanced}
            aria-label="Toggle filter lanjutan"
          >
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            Filter
          </Button>
        </div>
      </div>
    </div>
  );
}
