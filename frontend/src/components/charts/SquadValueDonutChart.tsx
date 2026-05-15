"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { formatEuro, getPositionCode } from "@/lib/utils";
import type { ClubSquadPlayer } from "@/types";

type SquadValueDonutChartProps = {
  squad: ClubSquadPlayer[];
};

const positionColors: Record<string, string> = {
  GK: "var(--color-pos-gk)",
  DEF: "var(--color-pos-def)",
  MID: "var(--color-pos-mid)",
  FWD: "var(--color-pos-fwd)"
};

export function SquadValueDonutChart({ squad }: SquadValueDonutChartProps) {
  const grouped = squad.reduce<Record<string, number>>((acc, player) => {
    const key = getPositionCode(player.position);
    acc[key] = (acc[key] ?? 0) + Number(player.market_value_eur ?? 0);
    return acc;
  }, {});
  const data = Object.entries(grouped).map(([position, value]) => ({ position, value }));
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="grid gap-4 rounded-panel border border-border bg-background-secondary p-4 lg:grid-cols-[360px_minmax(0,1fr)]">
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="position"
              innerRadius={78}
              outerRadius={122}
              paddingAngle={3}
              isAnimationActive
            >
              {data.map((entry) => (
                <Cell key={entry.position} fill={positionColors[entry.position]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [formatEuro(value), "Nilai"]}
              contentStyle={{
                background: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                color: "var(--color-text-primary)"
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-col justify-center space-y-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-text-secondary">Total Nilai Squad</div>
          <div className="mt-2 font-display text-4xl font-bold text-text-primary">{formatEuro(total)}</div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {data.map((item) => (
            <div key={item.position} className="rounded-panel border border-border bg-background-primary p-3">
              <div className="font-mono text-xs text-text-secondary">{item.position}</div>
              <div className="mt-1 font-mono text-sm text-text-primary">{formatEuro(item.value)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
