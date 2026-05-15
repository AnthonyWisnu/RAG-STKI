"use client";

import { useEffect, useState } from "react";
import { Search, Shield } from "lucide-react";

import { searchClubs } from "@/lib/api";
import type { ClubSearchItem } from "@/types";

type ClubSelectorProps = {
  selectedClub: ClubSearchItem | null;
  season: string;
  onSelect: (club: ClubSearchItem) => void;
  label?: string;
};

export function ClubSelector({ selectedClub, season, onSelect, label = "Klub" }: ClubSelectorProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ClubSearchItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const timeout = window.setTimeout(() => {
      setLoading(true);
      searchClubs(query, season)
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
    }, 250);

    return () => {
      mounted = false;
      window.clearTimeout(timeout);
    };
  }, [query, season]);

  return (
    <div className="space-y-2">
      <span className="block text-xs uppercase tracking-widest text-text-secondary">{label}</span>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          placeholder={selectedClub?.name ?? "Cari klub..."}
          className="h-12 w-full rounded-panel border border-border bg-background-secondary pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
      {open ? (
      <div className="absolute left-0 right-0 top-14 z-30 max-h-96 overflow-auto rounded-panel border border-border bg-background-secondary p-2 shadow-panel">
        {loading ? (
          <div className="p-3 text-sm text-text-secondary">Mencari klub...</div>
        ) : results.length > 0 ? (
          <div className="space-y-2">
            {results.map((club) => (
              <button
                key={club.club_id}
                type="button"
                onClick={() => {
                  onSelect(club);
                  setQuery("");
                  setResults([]);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 rounded-panel border border-border bg-background-primary px-3 py-3 text-left transition-colors hover:bg-background-tertiary"
              >
                <Shield className="h-4 w-4 text-accent" aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-text-primary">{club.name}</span>
                  <span className="block text-xs text-text-secondary">
                    {club.league ?? "Liga tidak tersedia"} - {club.squad_count} pemain
                  </span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-3 text-sm text-text-secondary">Tidak ada klub yang cocok.</div>
        )}
      </div>
      ) : null}
      </div>
    </div>
  );
}
