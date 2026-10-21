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
import { fmtDate, TIER_LABEL, type Tier } from "../lib/api";

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
 * A y-axis that fits the data. The old fixed [-3, 8] domain clipped a
 * sharp change (the simulated person reaches the twenties) and let the
 * charting library pick fractional ticks such as 5.0929. The domain always
 * holds zero (the baseline) and the "sharp" line at 5, and the ticks are
 * whole numbers on a 1, 2, 5 or 10 step.
 */
function axis(values: number[]): { domain: [number, number]; ticks: number[] } {
  const lo0 = Math.min(-2, ...values.map((v) => Math.floor(v)));
  const hi0 = Math.max(6, ...values.map((v) => Math.ceil(v)));
  const step = [1, 2, 5, 10, 20].find((s) => (hi0 - lo0) / s <= 6) ?? 50;
  const lo = Math.floor(lo0 / step) * step;
  const hi = Math.ceil(hi0 / step) * step;
  const ticks: number[] = [];
  for (let t = lo; t <= hi; t += step) ticks.push(t);
  return { domain: [lo, hi], ticks };
}

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

  const values = data.map((d) => d.value).filter((v): v is number => typeof v === "number");
  const { domain, ticks } = axis(values);
  const first = rows[0];
  const last = rows[rows.length - 1];
  const label = last
    ? `Change score by day, ${fmtDate(first!.date)} to ${fmtDate(last.date)}. Latest day: ${TIER_LABEL[last.tier].toLowerCase()}. Zero is the person's own baseline.`
    : "Change score by day. No days yet.";

  return (
    <div style={{ width: "100%", height }} role="img" aria-label={label}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--border)" }} interval="preserveStartEnd" minTickGap={28} />
          <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} domain={domain} ticks={ticks} interval={0} allowDecimals={false} width={44} />
          <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="3 3" />
          <ReferenceLine y={5} stroke="var(--discuss)" strokeDasharray="3 3" label={{ value: "sharp", fill: "var(--discuss)", fontSize: 12, position: "insideTopRight" }} />
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
