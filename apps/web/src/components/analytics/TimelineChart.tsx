"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import {
  colorForBehavior,
  formatBehavior,
} from "@/components/analytics/chartTheme";
import type { TimelinePoint } from "@/lib/types";

type TimelineChartProps = {
  points: TimelinePoint[];
};

const BEHAVIOR_BAND: Record<string, number> = {
  eating: 7,
  resting: 6,
  walking: 5,
  swimming: 4,
  climbing: 3,
  playing: 2,
  not_visible: 1,
  unknown: 0,
};

type ScatterRow = {
  t: number;
  band: number;
  behavior: string;
  label: string;
  id: number;
  when: string;
  fill: string;
};

function ColoredDot(props: {
  cx?: number;
  cy?: number;
  payload?: ScatterRow;
}) {
  const { cx = 0, cy = 0, payload } = props;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5}
      fill={payload?.fill ?? "#4a6a50"}
      stroke="#2d3d32"
      strokeWidth={0.5}
    />
  );
}

export function TimelineChart({ points }: TimelineChartProps) {
  if (points.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted">
        No timeline points — no observations in this range.
      </p>
    );
  }

  const rows: ScatterRow[] = points.map((p) => ({
    t: new Date(p.observed_at).getTime(),
    band: BEHAVIOR_BAND[p.behavior] ?? 0,
    behavior: p.behavior,
    label: formatBehavior(p.behavior),
    id: p.observation_id,
    when: p.observed_at,
    fill: colorForBehavior(p.behavior),
  }));

  const behaviors = Object.keys(BEHAVIOR_BAND);

  return (
    <div className="w-full min-w-0">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#dde8d9" />
            <XAxis
              type="number"
              dataKey="t"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(value: number) =>
                new Date(value).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              }
              tick={{ fill: "#6d8f72", fontSize: 10 }}
            />
            <YAxis
              type="number"
              dataKey="band"
              domain={[-0.5, 7.5]}
              ticks={behaviors.map((b) => BEHAVIOR_BAND[b])}
              tickFormatter={(value: number) => {
                const entry = Object.entries(BEHAVIOR_BAND).find(
                  ([, band]) => band === value,
                );
                return entry ? formatBehavior(entry[0]) : "";
              }}
              tick={{ fill: "#6d8f72", fontSize: 10 }}
              width={78}
            />
            <ZAxis range={[60, 60]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null;
                const row = payload[0].payload as ScatterRow;
                return (
                  <div className="rounded-xl border border-border bg-surface px-3 py-2 text-xs shadow-sm">
                    <p className="font-medium text-ink">{row.label}</p>
                    <p className="mt-1 text-muted">
                      {new Date(row.when).toLocaleString()} · obs #{row.id}
                    </p>
                  </div>
                );
              }}
            />
            <Scatter data={rows} shape={<ColoredDot />} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
        {behaviors.map((behavior) => (
          <span key={behavior} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: colorForBehavior(behavior) }}
            />
            {formatBehavior(behavior)}
          </span>
        ))}
      </div>
    </div>
  );
}
