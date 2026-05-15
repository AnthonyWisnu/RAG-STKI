"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, TrendingDown, TrendingUp } from "lucide-react";

import { ValuationLineChart } from "@/components/charts/ValuationLineChart";
import { PlayerSelector } from "@/components/player/PlayerSelector";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { getValuationHistory } from "@/lib/api";
import { formatEuro } from "@/lib/utils";
import type { PlayerSummary, ValuationHistoryResponse, ValuationRow } from "@/types";

type MetricCardProps = {
  label: string;
  value?: number | null;
  date?: string;
};

function MetricCard({ label, value, date }: MetricCardProps) {
  return (
    <div className="rounded-panel border border-border bg-background-secondary p-5">
      <div className="text-xs uppercase tracking-widest text-text-secondary">{label}</div>
      <div className="mt-3 font-display text-4xl font-bold leading-none text-text-primary">
        {formatEuro(value)}
      </div>
      <div className="mt-2 font-mono text-xs text-text-muted">{date ?? "Tanggal tidak tersedia"}</div>
    </div>
  );
}

function getHighest(valuations: ValuationRow[]): ValuationRow | null {
  return valuations.reduce<ValuationRow | null>((highest, row) => {
    if (!highest || row.market_value_eur > highest.market_value_eur) {
      return row;
    }
    return highest;
  }, null);
}

function getLowest(valuations: ValuationRow[]): ValuationRow | null {
  return valuations.reduce<ValuationRow | null>((lowest, row) => {
    if (!lowest || row.market_value_eur < lowest.market_value_eur) {
      return row;
    }
    return lowest;
  }, null);
}

export default function ValuationPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerSummary | null>(null);
  const [history, setHistory] = useState<ValuationHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlayer) {
      setHistory(null);
      return;
    }

    let mounted = true;
    setLoading(true);
    setError(null);
    getValuationHistory(selectedPlayer.player_id)
      .then((response) => {
        if (mounted) {
          setHistory(response);
        }
      })
      .catch((caught) => {
        if (mounted) {
          const message = caught instanceof Error ? caught.message : "Histori valuasi gagal dimuat.";
          setError(message);
          setHistory(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [selectedPlayer]);

  const current = history?.valuations[0] ?? null;
  const highest = useMemo(() => getHighest(history?.valuations ?? []), [history]);
  const lowest = useMemo(() => getLowest(history?.valuations ?? []), [history]);
  const trendDown =
    history && history.valuations.length >= 2
      ? history.valuations[0].market_value_eur < history.valuations[1].market_value_eur
      : false;
  const TrendIcon = trendDown ? TrendingDown : TrendingUp;

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <SectionHeading title="Pilih Pemain" />
        <PlayerSelector
          selectedPlayer={selectedPlayer}
          onSelect={setSelectedPlayer}
          placeholder="Cari pemain untuk analisis valuasi..."
        />
      </section>

      {error ? (
        <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
          <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-32 animate-pulse rounded-panel border border-border bg-background-secondary" />
            ))}
          </div>
          <div className="h-[360px] animate-pulse rounded-panel border border-border bg-background-secondary" />
        </div>
      ) : history ? (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <MetricCard label="Nilai Saat Ini" value={current?.market_value_eur} date={current?.valuation_date} />
            <MetricCard label="Nilai Tertinggi" value={highest?.market_value_eur} date={highest?.valuation_date} />
            <MetricCard label="Nilai Terendah" value={lowest?.market_value_eur} date={lowest?.valuation_date} />
          </section>

          <section className="space-y-4">
            <SectionHeading title="Tren Valuasi" />
            <ValuationLineChart valuations={history.valuations} />
          </section>

          <section className="rounded-panel border border-border bg-background-secondary p-5">
            <div className="flex items-center gap-2">
              <TrendIcon className="h-4 w-4 text-accent" aria-hidden="true" />
              <h2 className="font-display text-xl font-bold text-text-primary">
                Insight Naratif
              </h2>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              {history.trend_narrative}
            </p>
            <div className="mt-4 font-mono text-xs text-text-muted">
              Sumber: Transfermarkt Kaggle, {history.valuations.length} titik valuasi.
            </div>
          </section>
        </>
      ) : (
        <section className="rounded-panel border border-border bg-background-secondary p-10 text-center">
          <TrendingUp className="mx-auto h-9 w-9 text-text-muted" aria-hidden="true" />
          <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
            Belum ada pemain yang dipilih
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Cari pemain untuk melihat histori valuasi, nilai saat ini, dan tren pasar.
          </p>
        </section>
      )}
    </div>
  );
}
