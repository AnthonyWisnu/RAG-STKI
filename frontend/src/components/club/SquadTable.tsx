"use client";

import { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";

import { PositionBadge } from "@/components/player/PositionBadge";
import { formatEuro, formatNumber } from "@/lib/utils";
import type { ClubSquadPlayer } from "@/types";

type SquadTableProps = {
  squad: ClubSquadPlayer[];
};

type SortKey = "name" | "position" | "market_value_eur" | "minutes" | "goals" | "assists";

export function SquadTable({ squad }: SquadTableProps) {
  const [position, setPosition] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("market_value_eur");

  const rows = useMemo(() => {
    return [...squad]
      .filter((player) => !position || player.position === position)
      .sort((a, b) => {
        if (sortKey === "name" || sortKey === "position") {
          return String(a[sortKey] ?? "").localeCompare(String(b[sortKey] ?? ""));
        }
        return Number(b[sortKey] ?? 0) - Number(a[sortKey] ?? 0);
      });
  }, [position, sortKey, squad]);

  const positions = Array.from(new Set(squad.map((player) => player.position).filter(Boolean))) as string[];

  return (
    <section className="overflow-hidden rounded-panel border border-border bg-background-secondary">
      <div className="flex flex-col gap-3 border-b border-border p-4 md:flex-row md:items-center md:justify-between">
        <select value={position} onChange={(event) => setPosition(event.target.value)} className="h-10 rounded-panel border border-border bg-background-primary px-3 text-sm text-text-primary" aria-label="Filter posisi squad">
          <option value="">Semua Posisi</option>
          {positions.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-text-secondary">
          <ArrowUpDown className="h-4 w-4" aria-hidden="true" />
          Urutkan
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)} className="h-10 rounded-panel border border-border bg-background-primary px-3 text-sm text-text-primary" aria-label="Urutkan squad">
            <option value="market_value_eur">Nilai Pasar</option>
            <option value="minutes">Menit</option>
            <option value="goals">Gol</option>
            <option value="assists">Assist</option>
            <option value="name">Nama</option>
            <option value="position">Posisi</option>
          </select>
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[780px] text-sm">
          <thead className="bg-background-primary text-left text-xs uppercase tracking-widest text-text-muted">
            <tr>
              <th className="px-4 py-3">Nama</th>
              <th className="px-4 py-3">Posisi</th>
              <th className="px-4 py-3">Nilai Pasar</th>
              <th className="px-4 py-3">Menit</th>
              <th className="px-4 py-3">Gol</th>
              <th className="px-4 py-3">Assist</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((player) => (
              <tr key={player.player_id} className="border-t border-border transition-colors hover:bg-background-tertiary">
                <td className="px-4 py-3 font-display text-lg font-bold text-text-primary">{player.name}</td>
                <td className="px-4 py-3"><PositionBadge position={player.position} /></td>
                <td className="px-4 py-3 font-mono text-accent">{formatEuro(player.market_value_eur)}</td>
                <td className="px-4 py-3 font-mono text-text-primary">{formatNumber(player.minutes)}</td>
                <td className="px-4 py-3 font-mono text-text-primary">{formatNumber(player.goals)}</td>
                <td className="px-4 py-3 font-mono text-text-primary">{formatNumber(player.assists)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
