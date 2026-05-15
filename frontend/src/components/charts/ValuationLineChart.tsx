"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { formatEuro } from "@/lib/utils";
import type { ValuationRow } from "@/types";

type ValuationLineChartProps = {
  valuations: ValuationRow[];
};

type ChartPoint = {
  date: string;
  value: number;
  valueLabel: string;
};

const seasonMarkers = [
  { date: "2023-07-01", label: "2023/24" },
  { date: "2024-07-01", label: "2024/25" },
  { date: "2025-07-01", label: "2025/26" }
];

export function ValuationLineChart({ valuations }: ValuationLineChartProps) {
  const data: ChartPoint[] = [...valuations]
    .sort((a, b) => a.valuation_date.localeCompare(b.valuation_date))
    .map((row) => ({
      date: row.valuation_date,
      value: row.market_value_eur / 1_000_000,
      valueLabel: formatEuro(row.market_value_eur)
    }));

  if (data.length === 0) {
    return (
      <div className="flex h-[360px] items-center justify-center rounded-panel border border-border bg-background-secondary text-sm text-text-secondary">
        Histori valuasi belum tersedia untuk pemain ini.
      </div>
    );
  }

  return (
    <div className="h-[360px] rounded-panel border border-border bg-background-secondary p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 24, bottom: 12, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }}
            tickMargin={10}
          />
          <YAxis
            tick={{ fill: "var(--color-text-secondary)", fontSize: 12 }}
            tickFormatter={(value: number) => `${value}M`}
            width={56}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toLocaleString("id-ID")}M EUR`, "Nilai"]}
            labelFormatter={(label) => `Tanggal ${label}`}
            contentStyle={{
              background: "var(--color-bg-secondary)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              color: "var(--color-text-primary)"
            }}
          />
          {seasonMarkers.map((marker) => (
            <ReferenceLine
              key={marker.date}
              x={marker.date}
              stroke="var(--color-border-bright)"
              label={{
                value: marker.label,
                fill: "var(--color-text-secondary)",
                fontSize: 11
              }}
            />
          ))}
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-accent)" }}
            activeDot={{ r: 5 }}
            isAnimationActive
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
