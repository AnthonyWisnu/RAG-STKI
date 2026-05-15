"use client";

import { Download, Info } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { formatNumber } from "@/lib/utils";
import type { TopCategory, TopPerformerRow } from "@/types";

type TopPerformersTableProps = {
  rows: TopPerformerRow[];
  category: TopCategory;
};

const categoryLabels: Record<TopCategory, string> = {
  goals: "Gol",
  assists: "Assist",
  saves: "Saves",
  clean_sheets: "Clean Sheet",
  minutes: "Menit"
};

function rankClass(index: number): string {
  if (index === 0) {
    return "text-status-stale";
  }
  if (index === 1) {
    return "text-text-primary";
  }
  if (index === 2) {
    return "text-chart-3";
  }
  return "text-text-secondary";
}

function exportCsv(rows: TopPerformerRow[], category: TopCategory) {
  const header = ["rank", "player", "club", "league", "season", "position", category, "minutes"];
  const body = rows.map((row, index) =>
    [
      index + 1,
      row.player,
      row.club,
      row.league,
      row.season,
      row.position ?? "",
      row.value,
      row.minutes ?? ""
    ]
      .map((value) => `"${String(value).replaceAll('"', '""')}"`)
      .join(",")
  );
  const blob = new Blob([[header.join(","), ...body].join("\n")], {
    type: "text/csv;charset=utf-8"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `top-performers-${category}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function TopPerformersTable({ rows, category }: TopPerformersTableProps) {
  return (
    <section className="overflow-hidden rounded-panel border border-border bg-background-secondary">
      <div className="flex flex-col gap-3 border-b border-border p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Info className="h-4 w-4 text-accent" aria-hidden="true" />
          Statistik lanjutan yang tidak tersedia dari FBref publik tidak ditampilkan.
        </div>
        <Button variant="secondary" onClick={() => exportCsv(rows, category)}>
          <Download className="h-4 w-4" aria-hidden="true" />
          Export CSV
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="sticky top-0 bg-background-primary text-left text-xs uppercase tracking-widest text-text-muted">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Nama</th>
              <th className="px-4 py-3">Klub</th>
              <th className="px-4 py-3">Liga</th>
              <th className="px-4 py-3">Posisi</th>
              <th className="px-4 py-3">{categoryLabels[category]}</th>
              <th className="px-4 py-3">Menit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.player}-${row.club}-${index}`} className="border-t border-border transition-colors hover:bg-background-tertiary">
                <td className={`px-4 py-3 font-display text-xl font-bold ${rankClass(index)}`}>
                  {index + 1}
                </td>
                <td className="px-4 py-3 font-display text-lg font-bold text-text-primary">
                  {row.player}
                </td>
                <td className="px-4 py-3 text-text-secondary">{row.club}</td>
                <td className="px-4 py-3 text-text-secondary">{row.league}</td>
                <td className="px-4 py-3 text-text-secondary">{row.position ?? "-"}</td>
                <td className="px-4 py-3 font-mono text-accent">{formatNumber(row.value)}</td>
                <td className="px-4 py-3 font-mono text-text-primary">{formatNumber(row.minutes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
