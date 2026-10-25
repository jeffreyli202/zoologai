"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DayCount, HourCount } from "@/lib/types";

type DaySamplesChartProps = {
  data: DayCount[];
};

export function DaySamplesChart({ data }: DaySamplesChartProps) {
  const rows = data.map((d) => ({
    date: d.date.slice(5),
    fullDate: d.date,
    count: d.count,
  }));

  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dde8d9" />
          <XAxis dataKey="date" tick={{ fill: "#6d8f72", fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fill: "#6d8f72", fontSize: 12 }} />
          <Tooltip
            formatter={(value: number) => [`${value} samples`, "Recorded"]}
            labelFormatter={(_, payload) => {
              const full = payload?.[0]?.payload?.fullDate;
              return full
                ? `${full} (UTC) — zero means no samples, not inactivity`
                : "";
            }}
            contentStyle={{
              borderRadius: 12,
              borderColor: "#dde8d9",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" fill="#4a6a50" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

type HourSamplesChartProps = {
  data: HourCount[];
};

export function HourSamplesChart({ data }: HourSamplesChartProps) {
  const rows = data.map((h) => ({
    hour: `${String(h.hour).padStart(2, "0")}:00`,
    count: h.count,
  }));

  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dde8d9" />
          <XAxis
            dataKey="hour"
            tick={{ fill: "#6d8f72", fontSize: 10 }}
            interval={2}
          />
          <YAxis allowDecimals={false} tick={{ fill: "#6d8f72", fontSize: 12 }} />
          <Tooltip
            formatter={(value: number) => [`${value} samples`, "UTC hour"]}
            contentStyle={{
              borderRadius: 12,
              borderColor: "#dde8d9",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#6d8f72"
            strokeWidth={2}
            dot={{ r: 3, fill: "#4a6a50" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
