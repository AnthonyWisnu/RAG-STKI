"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, SearchX } from "lucide-react";

import { ActiveFilterChips } from "@/components/search/ActiveFilterChips";
import { AdvancedFilters } from "@/components/search/AdvancedFilters";
import { FilterBar } from "@/components/search/FilterBar";
import { SortBar } from "@/components/search/SortBar";
import { PlayerCard } from "@/components/player/PlayerCard";
import { Button } from "@/components/ui/Button";
import { searchPlayers } from "@/lib/api";
import type { PlayerSearchResponse, PlayerSummary, SearchFilterState } from "@/types";

const PAGE_SIZE = 20;
const STORAGE_KEY = "football-rag-compare-players";

const defaultFilters: SearchFilterState = {
  q: "",
  position: "",
  league: "",
  season: "2025-2026",
  sort: "name",
  page: 1,
  minMinutes: "",
  minValue: "",
  maxValue: "",
  minGoals: "",
  minAssists: ""
};

function readComparePlayers(): PlayerSummary[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PlayerSummary[]) : [];
  } catch {
    return [];
  }
}

function writeComparePlayers(players: PlayerSummary[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(players));
}

function toNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function applyClientFilters(items: PlayerSummary[], filters: SearchFilterState): PlayerSummary[] {
  const minMinutes = toNumber(filters.minMinutes);
  const minValue = toNumber(filters.minValue);
  const maxValue = toNumber(filters.maxValue);
  const minGoals = toNumber(filters.minGoals);
  const minAssists = toNumber(filters.minAssists);

  return items.filter((player) => {
    if (minMinutes !== null && Number(player.minutes ?? 0) < minMinutes) {
      return false;
    }
    if (minValue !== null && Number(player.market_value_eur ?? 0) < minValue) {
      return false;
    }
    if (maxValue !== null && Number(player.market_value_eur ?? 0) > maxValue) {
      return false;
    }
    if (minGoals !== null && Number(player.goals ?? 0) < minGoals) {
      return false;
    }
    if (minAssists !== null && Number(player.assists ?? 0) < minAssists) {
      return false;
    }
    return true;
  });
}

export default function SearchPage() {
  const [filters, setFilters] = useState<SearchFilterState>(defaultFilters);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [result, setResult] = useState<PlayerSearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparePlayers, setComparePlayers] = useState<PlayerSummary[]>([]);

  useEffect(() => {
    setComparePlayers(readComparePlayers());
  }, []);

  useEffect(() => {
    let mounted = true;
    const timeout = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      searchPlayers({
        q: filters.q,
        position: filters.position || undefined,
        league: filters.league || undefined,
        season: filters.season,
        sort: filters.sort,
        page: filters.page,
        page_size: PAGE_SIZE
      })
        .then((response) => {
          if (mounted) {
            setResult(response);
          }
        })
        .catch((caught) => {
          if (mounted) {
            const message = caught instanceof Error ? caught.message : "Gagal mengambil data pemain.";
            setError(message);
          }
        })
        .finally(() => {
          if (mounted) {
            setLoading(false);
          }
        });
    }, 300);

    return () => {
      mounted = false;
      window.clearTimeout(timeout);
    };
  }, [filters]);

  const filteredItems = useMemo(
    () => applyClientFilters(result?.items ?? [], filters),
    [filters, result]
  );
  const selectedIds = useMemo(
    () => new Set(comparePlayers.map((player) => player.player_id)),
    [comparePlayers]
  );

  function resetFilters() {
    setFilters(defaultFilters);
  }

  function addToCompare(player: PlayerSummary) {
    if (selectedIds.has(player.player_id) || comparePlayers.length >= 4) {
      return;
    }
    const next = [...comparePlayers, player];
    setComparePlayers(next);
    writeComparePlayers(next);
  }

  function removeFromCompare(player: PlayerSummary) {
    const next = comparePlayers.filter((item) => item.player_id !== player.player_id);
    setComparePlayers(next);
    writeComparePlayers(next);
  }

  return (
    <div className="space-y-5">
      <FilterBar
        filters={filters}
        advancedOpen={advancedOpen}
        onChange={setFilters}
        onToggleAdvanced={() => setAdvancedOpen((value) => !value)}
      />

      {advancedOpen ? (
        <AdvancedFilters filters={filters} onChange={setFilters} onReset={resetFilters} />
      ) : null}

      <ActiveFilterChips filters={filters} onChange={setFilters} onReset={resetFilters} />

      <SortBar
        total={result?.total ?? 0}
        shown={filteredItems.length}
        filters={filters}
        onChange={setFilters}
      />

      {comparePlayers.length > 0 ? (
        <div className="rounded-panel border border-border bg-background-secondary px-4 py-3 text-sm text-text-secondary">
          Daftar bandingkan: {comparePlayers.map((player) => player.name).join(", ")}.
          Maksimal 4 pemain.
        </div>
      ) : null}

      {error ? (
        <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
          <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div
              key={index}
              className="h-28 animate-pulse rounded-panel border border-border bg-background-secondary"
            />
          ))}
        </div>
      ) : filteredItems.length > 0 ? (
        <div className="space-y-3">
          {filteredItems.map((player) => {
            const selected = selectedIds.has(player.player_id);
            const disabled = !selected && comparePlayers.length >= 4;
            return (
              <PlayerCard
                key={player.player_id}
                player={player}
                action={
                  <Button
                    variant={selected ? "primary" : "secondary"}
                    disabled={disabled}
                    onClick={() => (selected ? removeFromCompare(player) : addToCompare(player))}
                    className="min-w-36"
                  >
                    {selected ? "Sudah Dipilih" : "Bandingkan"}
                  </Button>
                }
              />
            );
          })}
        </div>
      ) : (
        <div className="rounded-panel border border-border bg-background-secondary p-10 text-center">
          <SearchX className="mx-auto h-9 w-9 text-text-muted" aria-hidden="true" />
          <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
            Tidak ada pemain yang cocok
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Kurangi filter atau cari nama pemain lain.
          </p>
          <Button className="mt-4" variant="secondary" onClick={resetFilters}>
            Reset Semua Filter
          </Button>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border pt-4">
        <Button
          variant="secondary"
          disabled={filters.page <= 1 || loading}
          onClick={() => setFilters((current) => ({ ...current, page: Math.max(1, current.page - 1) }))}
        >
          Sebelumnya
        </Button>
        <span className="font-mono text-sm text-text-secondary">Halaman {filters.page}</span>
        <Button
          variant="secondary"
          disabled={!result?.has_next || loading}
          onClick={() => setFilters((current) => ({ ...current, page: current.page + 1 }))}
        >
          Berikutnya
        </Button>
      </div>
    </div>
  );
}
