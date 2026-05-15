"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Shield } from "lucide-react";

import { SquadValueDonutChart } from "@/components/charts/SquadValueDonutChart";
import { TopScorerBarChart } from "@/components/charts/TopScorerBarChart";
import { ClubHeader } from "@/components/club/ClubHeader";
import { ClubSelector } from "@/components/club/ClubSelector";
import { SquadTable } from "@/components/club/SquadTable";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { getClubDetail } from "@/lib/api";
import { formatEuro } from "@/lib/utils";
import type { ClubDetailResponse, ClubSearchItem } from "@/types";

const seasons = ["2025-2026", "2024-2025", "2023-2024"];
const tabs = ["Squad", "Top Scorer Musim Ini", "Nilai Squad"] as const;
type ClubTab = (typeof tabs)[number];

export default function ClubPage() {
  const [selectedClub, setSelectedClub] = useState<ClubSearchItem | null>(null);
  const [season, setSeason] = useState("2025-2026");
  const [detail, setDetail] = useState<ClubDetailResponse | null>(null);
  const [activeTab, setActiveTab] = useState<ClubTab>("Squad");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedClub) {
      setDetail(null);
      return;
    }

    let mounted = true;
    setLoading(true);
    setError(null);
    getClubDetail(selectedClub.club_id, season)
      .then((response) => {
        if (mounted) {
          setDetail(response);
        }
      })
      .catch((caught) => {
        if (mounted) {
          const message = caught instanceof Error ? caught.message : "Profil klub gagal dimuat.";
          setError(message);
          setDetail(null);
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
  }, [season, selectedClub]);

  const topScorer = useMemo(() => {
    return detail?.squad.reduce((best, player) => {
      if (!best || Number(player.goals ?? 0) > Number(best.goals ?? 0)) {
        return player;
      }
      return best;
    }, detail.squad[0]);
  }, [detail]);

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <SectionHeading title="Pilih Klub" />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px]">
          <ClubSelector selectedClub={selectedClub} season={season} onSelect={setSelectedClub} />
          <label className="space-y-2">
            <span className="text-xs uppercase tracking-widest text-text-secondary">Musim</span>
            <select value={season} onChange={(event) => setSeason(event.target.value)} className="h-12 w-full rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary" aria-label="Pilih musim klub">
              {seasons.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </section>

      {error ? (
        <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
          <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <div className="h-32 animate-pulse rounded-panel border border-border bg-background-secondary" />
          <div className="h-96 animate-pulse rounded-panel border border-border bg-background-secondary" />
        </div>
      ) : detail ? (
        <>
          <ClubHeader detail={detail} />
          <section className="grid gap-3 md:grid-cols-3">
            <div className="rounded-panel border border-border bg-background-secondary p-4">
              <div className="text-xs uppercase tracking-widest text-text-secondary">Top Scorer</div>
              <div className="mt-2 font-display text-2xl font-bold text-text-primary">{topScorer?.name ?? "-"}</div>
              <div className="mt-1 font-mono text-sm text-accent">{topScorer?.goals ?? 0} gol</div>
            </div>
            <div className="rounded-panel border border-border bg-background-secondary p-4">
              <div className="text-xs uppercase tracking-widest text-text-secondary">Total Squad</div>
              <div className="mt-2 font-display text-2xl font-bold text-text-primary">{detail.squad.length} pemain</div>
            </div>
            <div className="rounded-panel border border-border bg-background-secondary p-4">
              <div className="text-xs uppercase tracking-widest text-text-secondary">Nilai Squad</div>
              <div className="mt-2 font-display text-2xl font-bold text-accent">{formatEuro(detail.total_squad_value)}</div>
            </div>
          </section>

          <div className="flex flex-wrap gap-2 border-b border-border pb-3">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-panel border px-3 py-2 text-sm transition-colors ${
                  activeTab === tab
                    ? "border-accent bg-accent-dim text-accent"
                    : "border-border bg-background-secondary text-text-secondary hover:bg-background-tertiary"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === "Squad" ? <SquadTable squad={detail.squad} /> : null}
          {activeTab === "Top Scorer Musim Ini" ? <TopScorerBarChart players={detail.squad} /> : null}
          {activeTab === "Nilai Squad" ? <SquadValueDonutChart squad={detail.squad} /> : null}
        </>
      ) : (
        <section className="rounded-panel border border-border bg-background-secondary p-10 text-center">
          <Shield className="mx-auto h-9 w-9 text-text-muted" aria-hidden="true" />
          <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
            Belum ada klub yang dipilih
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Pilih klub untuk melihat squad, top scorer, dan distribusi nilai pasar.
          </p>
        </section>
      )}
    </div>
  );
}
