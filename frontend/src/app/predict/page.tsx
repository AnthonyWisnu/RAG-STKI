"use client";

import { useState } from "react";
import { AlertCircle, ChevronDown, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { PlayerSelector } from "@/components/player/PlayerSelector";
import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { predictValuation } from "@/lib/api";
import { cn, formatEuro } from "@/lib/utils";
import type { PlayerSummary, PredictResponse, SupportingFactor } from "@/types";

const seasons = ["2025-2026", "2024-2025", "2023-2024"];

function impactLabel(impact?: string): string {
  if (impact === "positive") {
    return "mendorong naik";
  }
  if (impact === "negative") {
    return "menahan naik";
  }
  return "netral";
}

function impactClass(impact?: string): string {
  if (impact === "positive") {
    return "border-status-fresh text-status-fresh";
  }
  if (impact === "negative") {
    return "border-status-old text-status-old";
  }
  return "border-status-stale text-status-stale";
}

function FactorItem({ factor }: { factor: SupportingFactor }) {
  return (
    <li className="rounded-panel border border-border bg-background-secondary p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("rounded-panel border px-2 py-1 text-[11px]", impactClass(factor.impact))}>
          {impactLabel(factor.impact)}
        </span>
        {factor.citation_ids?.length ? (
          <span className="font-mono text-[11px] text-text-muted">
            {factor.citation_ids.length} citation
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-sm leading-relaxed text-text-secondary">{factor.factor}</p>
    </li>
  );
}

export default function PredictPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerSummary | null>(null);
  const [season, setSeason] = useState("2025-2026");
  const [response, setResponse] = useState<PredictResponse | null>(null);
  const [contextOpen, setContextOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runPrediction() {
    if (!selectedPlayer) {
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const result = await predictValuation({
        player_name: selectedPlayer.name,
        language: "id",
        use_llm: false
      });
      setResponse(result);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Estimasi nilai gagal dimuat.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  const trendDown = response?.trend_direction === "down";
  const TrendIcon = trendDown ? TrendingDown : TrendingUp;

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <SectionHeading title="Pilih Pemain" />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px]">
          <PlayerSelector
            selectedPlayer={selectedPlayer}
            onSelect={(player) => {
              setSelectedPlayer(player);
              setResponse(null);
            }}
            placeholder="Cari pemain untuk estimasi nilai..."
          />
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-widest text-text-secondary">Musim</span>
            <select
              value={season}
              onChange={(event) => setSeason(event.target.value)}
              className="h-12 w-full rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary"
              aria-label="Pilih musim"
            >
              {seasons.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Button
          variant="primary"
          disabled={!selectedPlayer || loading}
          onClick={() => void runPrediction()}
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {loading ? "Menghitung reasoning..." : "Jalankan Estimasi"}
        </Button>
        <p className="text-sm text-text-secondary">
          Estimasi memakai LLM reasoning berbasis KG/RAG dan ditampilkan sebagai range, bukan angka pasti.
        </p>
      </section>

      {error ? (
        <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
          <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="h-36 animate-pulse rounded-panel border border-border bg-background-secondary" />
            <div className="h-36 animate-pulse rounded-panel border border-border bg-background-secondary" />
          </div>
          <div className="h-48 animate-pulse rounded-panel border border-border bg-background-secondary" />
        </div>
      ) : response ? (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-panel border border-accent bg-accent-dim p-5">
              <div className="text-xs uppercase tracking-widest text-accent">Estimasi Wajar</div>
              <div className="mt-3 font-display text-4xl font-bold leading-none text-text-primary">
                {response.estimated_range?.label ?? "Tidak tersedia"}
              </div>
              <div className="mt-2 font-mono text-xs text-text-secondary">
                LLM + KG/RAG, musim dipilih {season}
              </div>
            </div>
            <div className="rounded-panel border border-border bg-background-secondary p-5">
              <div className="text-xs uppercase tracking-widest text-text-secondary">Nilai Saat Ini</div>
              <div className="mt-3 font-display text-4xl font-bold leading-none text-text-primary">
                {response.current_value?.label ?? formatEuro(null)}
              </div>
              <div className="mt-2 font-mono text-xs text-text-muted">
                {response.current_value?.date ?? "Tanggal tidak tersedia"}
              </div>
            </div>
          </section>

          <section className="rounded-panel border border-border bg-background-secondary p-5">
            <div className="flex items-center gap-2">
              <TrendIcon className="h-4 w-4 text-accent" aria-hidden="true" />
              <h2 className="font-display text-xl font-bold text-text-primary">
                Arah Tren: {response.trend_direction}
              </h2>
            </div>
            <p className="mt-3 text-sm text-text-secondary">
              Sistem menilai range estimasi dari histori market value, konteks pemain, dan statistik publik yang tersedia.
            </p>
          </section>

          <section className="space-y-4">
            <SectionHeading title="Faktor Pendukung" />
            <ul className="grid gap-3 lg:grid-cols-3">
              {response.supporting_factors.map((factor, index) => (
                <FactorItem key={`${factor.factor}-${index}`} factor={factor} />
              ))}
            </ul>
          </section>

          <section className="rounded-panel border border-border bg-background-secondary p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" aria-hidden="true" />
              <h2 className="font-display text-xl font-bold text-text-primary">
                Eksplanasi LLM
              </h2>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              {response.explanation}
            </p>
            <div className="mt-4 font-mono text-xs text-text-muted">
              Citation: {response.citations.length}
            </div>
          </section>

          <section className="overflow-hidden rounded-panel border border-border bg-background-secondary">
            <button
              type="button"
              onClick={() => setContextOpen((value) => !value)}
              className="flex w-full items-center justify-between px-5 py-4 text-left font-display text-xl font-bold text-text-primary"
            >
              Data yang Dipakai
              <ChevronDown
                className={cn("h-4 w-4 text-text-secondary transition-transform", contextOpen ? "rotate-180" : "")}
                aria-hidden="true"
              />
            </button>
            {contextOpen ? (
              <pre className="max-h-96 overflow-auto border-t border-border bg-background-primary p-4 font-mono text-xs leading-relaxed text-text-secondary">
                {JSON.stringify(response.raw, null, 2)}
              </pre>
            ) : null}
          </section>
        </>
      ) : (
        <section className="rounded-panel border border-border bg-background-secondary p-10 text-center">
          <Sparkles className="mx-auto h-9 w-9 text-text-muted" aria-hidden="true" />
          <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
            Belum ada estimasi
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Pilih pemain, lalu jalankan estimasi untuk melihat range nilai dan faktor pendukungnya.
          </p>
        </section>
      )}
    </div>
  );
}
