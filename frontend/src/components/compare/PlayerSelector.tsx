"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { PlayerCard } from "@/components/player/PlayerCard";
import { searchPlayers } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { PlayerSummary } from "@/types";

type PlayerSelectorProps = {
  selectedPlayers: PlayerSummary[];
  onChange: (players: PlayerSummary[]) => void;
  maxPlayers?: number;
};

export function PlayerSelector({
  selectedPlayers,
  onChange,
  maxPlayers = 4
}: PlayerSelectorProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const selectedIds = useMemo(
    () => new Set(selectedPlayers.map((player) => player.player_id)),
    [selectedPlayers]
  );

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setResults([]);
      return;
    }

    let mounted = true;
    const timeout = window.setTimeout(() => {
      setLoading(true);
      searchPlayers({ q: trimmed, page_size: 8 })
        .then((response) => {
          if (mounted) {
            setResults(response.items);
          }
        })
        .catch(() => {
          if (mounted) {
            setResults([]);
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
  }, [query]);

  function addPlayer(player: PlayerSummary) {
    if (selectedIds.has(player.player_id) || selectedPlayers.length >= maxPlayers) {
      return;
    }
    onChange([...selectedPlayers, player]);
    setQuery("");
    setResults([]);
  }

  function removePlayer(playerId: number) {
    onChange(selectedPlayers.filter((player) => player.player_id !== playerId));
  }

  return (
    <section className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Cari pemain untuk dibandingkan..."
          className="h-12 w-full rounded-panel border border-border bg-background-secondary pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        {query.trim().length >= 3 ? (
          <div className="absolute left-0 right-0 top-14 z-30 max-h-96 overflow-auto rounded-panel border border-border bg-background-secondary p-2 shadow-panel">
            {loading ? (
              <div className="p-3 text-sm text-text-secondary">Mencari pemain...</div>
            ) : results.length > 0 ? (
              <div className="space-y-2">
                {results.map((player) => {
                  const disabled = selectedIds.has(player.player_id) || selectedPlayers.length >= maxPlayers;
                  return (
                    <button
                      key={player.player_id}
                      type="button"
                      disabled={disabled}
                      onClick={() => addPlayer(player)}
                      className="w-full text-left disabled:opacity-45"
                    >
                      <PlayerCard player={player} compact />
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="p-3 text-sm text-text-secondary">
                Tidak ada pemain yang cocok.
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {selectedPlayers.map((player) => (
          <span
            key={player.player_id}
            className="inline-flex max-w-full items-center gap-2 rounded-panel border border-border bg-background-secondary px-3 py-2 text-sm text-text-primary"
          >
            <span className="truncate">{player.name}</span>
            <button
              type="button"
              onClick={() => removePlayer(player.player_id)}
              className="text-text-secondary transition-colors hover:text-text-primary"
              aria-label={`Hapus ${player.name}`}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </span>
        ))}
        <span
          className={cn(
            "inline-flex items-center rounded-panel border border-border px-3 py-2 font-mono text-xs",
            selectedPlayers.length >= maxPlayers ? "text-status-stale" : "text-text-secondary"
          )}
        >
          {selectedPlayers.length}/{maxPlayers} pemain
        </span>
      </div>

      {selectedPlayers.length > 0 ? (
        <Button variant="ghost" onClick={() => onChange([])}>
          Reset pilihan
        </Button>
      ) : null}
    </section>
  );
}
