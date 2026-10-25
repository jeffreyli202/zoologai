"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatBehavior } from "@/components/analytics/chartTheme";
import type { DayCompare } from "@/lib/types";

type DayCompareChartProps = {
  compare: DayCompare;
};

export function DayCompareChart({ compare }: DayCompareChartProps) {
  const behaviors = Array.from(
    new Set([
      ...compare.day_a.by_behavior.map((b) => b.behavior),
      ...compare.day_b.by_behavior.map((b) => b.behavior),
    ]),
  ).sort();

  const countA = Object.fromEntries(
    compare.day_a.by_behavior.map((b) => [b.behavior, b.count]),
  );
  const countB = Object.fromEntries(
    compare.day_b.by_behavior.map((b) => [b.behavior, b.count]),
  );

  const rows = behaviors.map((behavior) => ({
    behavior: formatBehavior(behavior),
    [compare.day_a.date]: countA[behavior] ?? 0,
    [compare.day_b.date]: countB[behavior] ?? 0,
  }));

  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted">
        Neither day has recorded samples. Missing data is not inactivity.
      </p>
    );
  }

  return (
    <div className="h-72 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dde8d9" />
          <XAxis
            dataKey="behavior"
            tick={{ fill: "#6d8f72", fontSize: 11 }}
            interval={0}
            angle={-15}
            textAnchor="end"
            height={52}
          />
          <YAxis allowDecimals={false} tick={{ fill: "#6d8f72", fontSize: 12 }} />
          <Tooltip
            formatter={(value: number) => [`${value} samples`, "Count"]}
            contentStyle={{
              borderRadius: 12,
              borderColor: "#dde8d9",
              fontSize: 12,
            }}
          />
          <Legend />
          <Bar
            dataKey={compare.day_a.date}
            fill="#4a6a50"
            radius={[6, 6, 0, 0]}
          />
          <Bar
            dataKey={compare.day_b.date}
            fill="#a3bda6"
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
