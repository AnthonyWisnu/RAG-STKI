"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip
} from "recharts";

import type { PlayerSummary, RadarMetricRow } from "@/types";
import { getPositionCode } from "@/lib/utils";

type RadarComparisonProps = {
  rows: RadarMetricRow[];
  selectedPlayers: PlayerSummary[];
};

type Dimension = {
  key: keyof RadarMetricRow;
  label: string;
};

type RadarPoint = {
  metric: string;
  [player: string]: string | number;
};

const mixedDimensions: Dimension[] = [
  { key: "goals", label: "Gol" },
  { key: "assists", label: "Assist" },
  { key: "shots_total", label: "Shots" },
  { key: "minutes", label: "Menit" }
];

const goalkeeperDimensions: Dimension[] = [
  { key: "saves", label: "Saves" },
  { key: "clean_sheets", label: "Clean Sheet" },
  { key: "minutes", label: "Menit" }
];

const chartColors = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)"
];

function getDimensions(selectedPlayers: PlayerSummary[]): Dimension[] {
  const positionCodes = selectedPlayers.map((player) => getPositionCode(player.position));
  const sameGoalkeeper =
    positionCodes.length > 0 && positionCodes.every((position) => position === "GK");
  return sameGoalkeeper ? goalkeeperDimensions : mixedDimensions;
}

function normalize(value: number | null | undefined, max: number): number {
  if (!value || max <= 0) {
    return 0;
  }
  return Math.round((value / max) * 100);
}

export function RadarComparison({ rows, selectedPlayers }: RadarComparisonProps) {
  const dimensions = getDimensions(selectedPlayers);
  const data: RadarPoint[] = dimensions.map((dimension) => {
    const max = Math.max(
      ...rows.map((row) => Number(row[dimension.key] ?? 0)),
      0
    );
    return rows.reduce<RadarPoint>(
      (point, row) => ({
        ...point,
        [row.player]: normalize(Number(row[dimension.key] ?? 0), max)
      }),
      { metric: dimension.label }
    );
  });

  return (
    <div className="h-[360px] w-full rounded-panel border border-border bg-background-secondary p-4">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid stroke="var(--color-border)" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-secondary)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              color: "var(--color-text-primary)"
            }}
          />
          {rows.map((row, index) => (
            <Radar
              key={row.player_id}
              name={row.player}
              dataKey={row.player}
              stroke={chartColors[index % chartColors.length]}
              fill={chartColors[index % chartColors.length]}
              fillOpacity={0.16}
              isAnimationActive
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
