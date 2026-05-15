"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Trophy } from "lucide-react";

import { TopPerformersTable } from "@/components/top/TopPerformersTable";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { getTopPerformers } from "@/lib/api";
import type { TopCategory, TopPerformersResponse } from "@/types";

const leagues = ["", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"];
const seasons = ["2025-2026", "2024-2025", "2023-2024"];
const positions = ["", "Goalkeeper", "Defender", "Midfielder", "Forward"];

const categoryOptions: Record<string, Array<{ value: TopCategory; label: string }>> = {
  Goalkeeper: [
    { value: "saves", label: "Saves" },
    { value: "clean_sheets", label: "Clean Sheet" },
    { value: "minutes", label: "Menit Bermain" }
  ],
  Defender: [
    { value: "minutes", label: "Menit Bermain" },
    { value: "goals", label: "Gol" },
    { value: "assists", label: "Assist" }
  ],
  Midfielder: [
    { value: "assists", label: "Assist" },
    { value: "goals", label: "Gol" },
    { value: "minutes", label: "Menit Bermain" }
  ],
  Forward: [
    { value: "goals", label: "Gol" },
    { value: "assists", label: "Assist" },
    { value: "minutes", label: "Menit Bermain" }
  ],
  All: [
    { value: "goals", label: "Gol" },
    { value: "assists", label: "Assist" },
    { value: "minutes", label: "Menit Bermain" },
    { value: "saves", label: "Saves" },
    { value: "clean_sheets", label: "Clean Sheet" }
  ]
};

export default function TopPage() {
  const [league, setLeague] = useState("");
  const [season, setSeason] = useState("2025-2026");
  const [position, setPosition] = useState("");
  const [category, setCategory] = useState<TopCategory>("goals");
  const [response, setResponse] = useState<TopPerformersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const availableCategories = useMemo(
    () => categoryOptions[position || "All"],
    [position]
  );

  useEffect(() => {
    if (!availableCategories.some((option) => option.value === category)) {
      setCategory(availableCategories[0].value);
    }
  }, [availableCategories, category]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    getTopPerformers({
      category,
      season,
      league: league || undefined,
      position: position || undefined,
      limit: 25
    })
      .then((data) => {
        if (mounted) {
          setResponse(data);
        }
      })
      .catch((caught) => {
        if (mounted) {
          const message = caught instanceof Error ? caught.message : "Ranking gagal dimuat.";
          setError(message);
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
  }, [category, league, position, season]);

  return (
    <div className="space-y-5">
      <section className="sticky top-14 z-10 rounded-panel border border-border bg-background-primary p-4">
        <SectionHeading title="Filter Ranking" />
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <select value={league} onChange={(event) => setLeague(event.target.value)} className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary" aria-label="Filter liga">
            {leagues.map((item) => <option key={item || "all"} value={item}>{item || "Semua Liga"}</option>)}
          </select>
          <select value={season} onChange={(event) => setSeason(event.target.value)} className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary" aria-label="Filter musim">
            {seasons.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select value={position} onChange={(event) => setPosition(event.target.value)} className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary" aria-label="Filter posisi">
            {positions.map((item) => <option key={item || "all"} value={item}>{item || "Semua Posisi"}</option>)}
          </select>
          <select value={category} onChange={(event) => setCategory(event.target.value as TopCategory)} className="h-11 rounded-panel border border-border bg-background-secondary px-3 text-sm text-text-primary" aria-label="Filter kategori">
            {availableCategories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </div>
      </section>

      {error ? (
        <div className="flex items-center gap-2 rounded-panel border border-status-old bg-background-secondary px-3 py-2 text-sm text-text-primary">
          <AlertCircle className="h-4 w-4 text-status-old" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="h-96 animate-pulse rounded-panel border border-border bg-background-secondary" />
      ) : response && response.items.length > 0 ? (
        <TopPerformersTable rows={response.items} category={response.category} />
      ) : (
        <div className="rounded-panel border border-border bg-background-secondary p-10 text-center">
          <Trophy className="mx-auto h-9 w-9 text-text-muted" aria-hidden="true" />
          <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
            Ranking tidak tersedia
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            Coba ubah liga, musim, atau kategori statistik.
          </p>
        </div>
      )}
    </div>
  );
}
