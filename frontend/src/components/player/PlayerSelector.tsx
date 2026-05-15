"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import { PlayerCard } from "@/components/player/PlayerCard";
import { Button } from "@/components/ui/Button";
import { searchPlayers } from "@/lib/api";
import type { PlayerSummary } from "@/types";

type PlayerSelectorProps = {
  selectedPlayer: PlayerSummary | null;
  onSelect: (player: PlayerSummary | null) => void;
  placeholder?: string;
};

export function PlayerSelector({
  selectedPlayer,
  onSelect,
  placeholder = "Cari pemain..."
}: PlayerSelectorProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(false);

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

  function selectPlayer(player: PlayerSummary) {
    onSelect(player);
    setQuery("");
    setResults([]);
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
          className="h-12 w-full rounded-panel border border-border bg-background-secondary pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        {query.trim().length >= 3 ? (
          <div className="absolute left-0 right-0 top-14 z-30 max-h-96 overflow-auto rounded-panel border border-border bg-background-secondary p-2 shadow-panel">
            {loading ? (
              <div className="p-3 text-sm text-text-secondary">Mencari pemain...</div>
            ) : results.length > 0 ? (
              <div className="space-y-2">
                {results.map((player) => (
                  <button
                    key={player.player_id}
                    type="button"
                    onClick={() => selectPlayer(player)}
                    className="w-full text-left"
                  >
                    <PlayerCard player={player} compact />
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-3 text-sm text-text-secondary">
                Tidak ada pemain yang cocok.
              </div>
            )}
          </div>
        ) : null}
      </div>

      {selectedPlayer ? (
        <div className="space-y-2">
          <PlayerCard
            player={selectedPlayer}
            action={
              <Button
                variant="icon"
                onClick={() => onSelect(null)}
                aria-label={`Hapus ${selectedPlayer.name}`}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            }
          />
        </div>
      ) : null}
    </div>
  );
}
