"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { ClubSquadPlayer } from "@/types";

type TopScorerBarChartProps = {
  players: ClubSquadPlayer[];
};

export function TopScorerBarChart({ players }: TopScorerBarChartProps) {
  const data = [...players]
    .sort((a, b) => Number(b.goals ?? 0) - Number(a.goals ?? 0))
    .slice(0, 10)
    .map((player) => ({
      name: player.name,
      goals: player.goals ?? 0
    }));

  return (
    <div className="h-[360px] rounded-panel border border-border bg-background-secondary p-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 24 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis type="number" tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }}
            width={140}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-secondary)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              color: "var(--color-text-primary)"
            }}
          />
          <Bar dataKey="goals" fill="var(--color-accent)" radius={[0, 6, 6, 0]} isAnimationActive />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
