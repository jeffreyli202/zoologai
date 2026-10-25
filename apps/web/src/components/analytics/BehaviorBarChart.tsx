"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";

import {
  colorForBehavior,
  formatBehavior,
} from "@/components/analytics/chartTheme";
import type { BehaviorCount } from "@/lib/types";

type BehaviorBarChartProps = {
  data: BehaviorCount[];
};

export function BehaviorBarChart({ data }: BehaviorBarChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted">
        No recorded samples in this range.
      </p>
    );
  }

  const rows = data.map((item, index) => ({
    ...item,
    label: formatBehavior(item.behavior),
    fill: colorForBehavior(item.behavior, index),
  }));

  return (
    <div className="h-72 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dde8d9" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#6d8f72", fontSize: 12 }}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={56}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "#6d8f72", fontSize: 12 }}
            label={{
              value: "Sample count",
              angle: -90,
              position: "insideLeft",
              fill: "#6d8f72",
              fontSize: 11,
            }}
          />
          <Tooltip
            formatter={(value: number) => [`${value} samples`, "Count"]}
            labelFormatter={(label) => String(label)}
            contentStyle={{
              borderRadius: 12,
              borderColor: "#dde8d9",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[8, 8, 0, 0]}>
            {rows.map((row) => (
              <Cell key={row.behavior} fill={row.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
