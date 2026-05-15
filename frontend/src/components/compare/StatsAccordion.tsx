"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { cn, formatNumber } from "@/lib/utils";
import type { RadarMetricRow } from "@/types";

type StatsAccordionProps = {
  rows: RadarMetricRow[];
};

type StatDefinition = {
  key: keyof RadarMetricRow;
  label: string;
};

const sections: Array<{ title: string; stats: StatDefinition[] }> = [
  {
    title: "Volume",
    stats: [{ key: "minutes", label: "Menit" }]
  },
  {
    title: "Attacking",
    stats: [
      { key: "goals", label: "Gol" },
      { key: "assists", label: "Assist" }
    ]
  },
  {
    title: "Shooting",
    stats: [{ key: "shots_total", label: "Shots" }]
  },
  {
    title: "Goalkeeping",
    stats: [
      { key: "saves", label: "Saves" },
      { key: "clean_sheets", label: "Clean Sheet" }
    ]
  }
];

export function StatsAccordion({ rows }: StatsAccordionProps) {
  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set(["Volume", "Attacking"])
  );

  function toggle(section: string) {
    setOpenSections((current) => {
      const next = new Set(current);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }

  return (
    <div className="overflow-hidden rounded-panel border border-border bg-background-secondary">
      {sections.map((section) => {
        const open = openSections.has(section.title);
        return (
          <div key={section.title} className="border-b border-border last:border-b-0">
            <button
              type="button"
              onClick={() => toggle(section.title)}
              className="flex w-full items-center justify-between px-4 py-3 text-left font-display text-lg font-bold text-text-primary"
            >
              {section.title}
              <ChevronDown
                className={cn("h-4 w-4 text-text-secondary transition-transform", open ? "rotate-180" : "")}
                aria-hidden="true"
              />
            </button>
            {open ? (
              <div className="overflow-x-auto border-t border-border">
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="bg-background-primary text-left text-xs uppercase tracking-widest text-text-muted">
                      <th className="px-4 py-3">Stat</th>
                      {rows.map((row) => (
                        <th key={row.player_id} className="px-4 py-3">
                          {row.player}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {section.stats.map((stat) => {
                      const max = Math.max(...rows.map((row) => Number(row[stat.key] ?? 0)), 0);
                      return (
                        <tr key={stat.key} className="border-t border-border">
                          <td className="px-4 py-3 text-text-secondary">{stat.label}</td>
                          {rows.map((row) => {
                            const value = Number(row[stat.key] ?? 0);
                            return (
                              <td
                                key={`${row.player_id}-${String(stat.key)}`}
                                className={cn(
                                  "px-4 py-3 font-mono",
                                  max > 0 && value === max ? "font-bold text-accent" : "text-text-primary"
                                )}
                              >
                                {formatNumber(value)}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
