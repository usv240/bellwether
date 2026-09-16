"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtDate, type Tier } from "../lib/api";

export interface TrendRow {
  date: string;
  composite: number | null;
  tier: Tier;
  annotation?: string | null;
}

const TIER_COLOR: Record<Tier, string> = {
  learning: "var(--chart-3)",
  stable: "var(--chart-1)",
  watch: "var(--chart-2)",
  discuss: "var(--discuss)",
  excluded: "var(--chart-4)",
};

/**
 * The composite change score, day by day. Zero is "exactly your baseline";
 * higher is further from it in the direction the literature associates
 * with decline. Dots are colored by tier and always paired with a word in
 * the tooltip, so color is never the only carrier of meaning. Quiet days
 * are hollow and break the line rather than being read as a value.
 */
export function TrendChart({ rows, height = 220 }: { rows: TrendRow[]; height?: number }) {
  const data = rows.map((r) => ({
    ...r,
    label: fmtDate(r.date),
    value: r.tier === "excluded" || r.tier === "learning" ? null : r.composite,
  }));

  return (
    <div style={{ width: "100%", height }} role="img" aria-label="Composite change score by day, colored by tier">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval="preserveStartEnd" minTickGap={28} />
          <YAxis tick={{ fill: "var(--text-muted)", fontSize: 11 }} tickLine={false} axisLine={false} domain={[-3, 8]} />
          <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="3 3" />
          <ReferenceLine y={5} stroke="var(--discuss)" strokeDasharray="3 3" label={{ value: "sharp", fill: "var(--discuss)", fontSize: 10, position: "insideTopRight" }} />
          <Tooltip
            cursor={{ stroke: "var(--border)" }}
            contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontSize: 12 }}
            labelStyle={{ color: "var(--text-muted)" }}
            formatter={(v: unknown, _n, item) => {
              const row = item?.payload as TrendRow | undefined;
              const tier = row?.tier ?? "stable";
              const val = typeof v === "number" ? v.toFixed(2) : "no value";
              return [`${val} (${tier})`, "change score"];
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--chart-1)"
            strokeWidth={2}
            connectNulls={false}
            isAnimationActive={false}
            dot={(props) => {
              const { cx, cy, payload } = props as { cx: number; cy: number; payload: TrendRow & { value: number | null } };
              const tier = payload.tier;
              if (payload.value === null || cx == null || cy == null) {
                if (tier === "excluded" && cx != null) {
                  return <circle key={payload.date} cx={cx} cy={height - 34} r={3} fill="none" stroke="var(--chart-4)" strokeWidth={1.5} />;
                }
                return <g key={payload.date} />;
              }
              return <circle key={payload.date} cx={cx} cy={cy} r={payload.annotation ? 4.5 : 3.5} fill={TIER_COLOR[tier]} stroke={payload.annotation ? "var(--text)" : "none"} strokeWidth={1.5} />;
            }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
