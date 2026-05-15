"use client";

import { useEffect, useState } from "react";
import { AlertCircle, MessageSquare, Users } from "lucide-react";

import { PlayerCard } from "@/components/player/PlayerCard";
import { PlayerSelector } from "@/components/compare/PlayerSelector";
import { RadarComparison } from "@/components/compare/RadarComparison";
import { StatsAccordion } from "@/components/compare/StatsAccordion";
import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { comparePlayers } from "@/lib/api";
import { formatEuro, formatNumber } from "@/lib/utils";
import type { CompareResponse, PlayerSummary } from "@/types";

const STORAGE_KEY = "football-rag-compare-players";

function readStoredPlayers(): PlayerSummary[] {
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

function writeStoredPlayers(players: PlayerSummary[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(players));
}

export default function ComparePage() {
  const [selectedPlayers, setSelectedPlayers] = useState<PlayerSummary[]>([]);
  const [response, setResponse] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedPlayers(readStoredPlayers());
  }, []);

  function handleSelection(players: PlayerSummary[]) {
    setSelectedPlayers(players);
    writeStoredPlayers(players);
    if (players.length < 2) {
      setResponse(null);
    }
  }

  async function runCompare() {
    if (selectedPlayers.length < 2) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await comparePlayers({
        player_ids: selectedPlayers.map((player) => player.player_id),
        player_names: selectedPlayers.map((player) => player.name)
      });
      setResponse(result);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Perbandingan gagal dimuat.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <SectionHeading title="Pilih Pemain" />
        <PlayerSelector selectedPlayers={selectedPlayers} onChange={handleSelection} />
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            disabled={selectedPlayers.length < 2 || loading}
            onClick={() => void runCompare()}
          >
            <Users className="h-4 w-4" aria-hidden="true" />
            {loading ? "Membandingkan..." : "Bandingkan Pemain"}
          </Button>
          <span className="text-sm text-text-secondary">
            Minimal 2 pemain, maksimal 4 pemain.
          </span>
        </div>
        {error ? (
          <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
            <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
            {error}
          </div>
        ) : null}
      </section>

      {selectedPlayers.length > 0 ? (
        <section className="space-y-4">
          <SectionHeading title="Header Statistik" />
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {selectedPlayers.map((player) => (
              <PlayerCard
                key={player.player_id}
                player={player}
                action={
                  <div className="hidden text-right md:block">
                    <div className="font-mono text-sm text-accent">
                      {formatEuro(player.market_value_eur)}
                    </div>
                    <div className="text-xs text-text-secondary">
                      {formatNumber(player.minutes)} menit
                    </div>
                  </div>
                }
              />
            ))}
          </div>
        </section>
      ) : null}

      {response ? (
        <>
          <section className="space-y-4">
            <SectionHeading title="Radar Normalisasi" />
            <p className="max-w-3xl text-sm leading-relaxed text-text-secondary">
              Nilai radar dinormalisasi ke skala 0 sampai 100 berdasarkan pemain yang dipilih.
              Untuk perbandingan lintas posisi, sistem memakai metrik campuran yang tersedia dari data publik.
            </p>
            <RadarComparison rows={response.radar_data} selectedPlayers={selectedPlayers} />
          </section>

          <section className="space-y-4">
            <SectionHeading title="Detail Statistik" />
            <StatsAccordion rows={response.radar_data} />
          </section>

          <section className="rounded-panel border border-border bg-background-secondary p-5">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-accent" aria-hidden="true" />
              <h2 className="font-display text-xl font-bold text-text-primary">
                Narasi Komparatif
              </h2>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              {response.narrative}
            </p>
            <div className="mt-4 font-mono text-xs text-text-muted">
              Citation: {response.citations.length}
            </div>
          </section>
        </>
      ) : (
        <section className="rounded-panel border border-border bg-background-secondary p-8 text-center">
          <Users className="mx-auto h-8 w-8 text-text-muted" aria-hidden="true" />
          <p className="mt-3 text-sm text-text-secondary">
            Pilih minimal dua pemain untuk melihat radar, tabel statistik, dan narasi komparatif.
          </p>
        </section>
      )}
    </div>
  );
}
