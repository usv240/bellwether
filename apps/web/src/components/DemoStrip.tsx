"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { InfoButton } from "./InfoButton";
import { TrendChart, type TrendRow } from "./TrendChart";
import { FEATURE_LABEL, PROFILE, TIER_CLASS, TIER_LABEL, fmtDate, getJSON, type Assessment, type Summary } from "../lib/api";

/**
 * The live baseline on the landing page: the real deployed service, the
 * real engine, a simulated person. Labelled as such the whole time.
 */
export function DemoStrip() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [rows, setRows] = useState<TrendRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      getJSON<Summary>(`/v1/profiles/${PROFILE}/summary`),
      getJSON<{ days: Assessment[] }>(`/v1/profiles/${PROFILE}/assessments?weeks=8`),
    ])
      .then(([s, a]) => {
        if (!alive) return;
        setSummary(s);
        setRows(a.days.map((d) => ({ date: d.date, composite: d.composite, tier: d.tier, annotation: d.annotation })));
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="rounded-[var(--radius-lg)] border border-line bg-surface p-5 shadow-[var(--shadow-sm)] sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-line bg-accent-soft px-2.5 py-0.5 text-xs font-medium text-[var(--accent)]">
            Simulated person
          </span>
          <InfoButton id="simulated" />
        </div>
        {summary && (
          <span className={`rounded-full px-3 py-1 text-sm font-medium ${TIER_CLASS[summary.tier]}`}>
            {TIER_LABEL[summary.tier]}
            {summary.since ? ` since ${fmtDate(summary.since)}` : ""}
          </span>
        )}
      </div>

      {error && (
        <p className="mt-4 text-sm text-muted">
          The live service did not answer ({error}). The dashboard and report still describe what it shows.
        </p>
      )}

      {summary && (
        <>
          <p className="mt-4 max-w-[640px] text-sm leading-relaxed text-muted">
            Eight weeks of one person&apos;s speech, reduced to numbers each day and compared with their own first week.
            {summary.tier === "discuss" || summary.tier === "watch" ? (
              <>
                {" "}From early September, {summary.contributors.slice(0, 3).map((c) => FEATURE_LABEL[c] ?? c).join(", ")} moved together, and the engine says so with dates.
              </>
            ) : (
              " Nothing has moved outside their normal range."
            )}
          </p>
          <div className="mt-4">
            <TrendChart rows={rows} height={200} />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted">
            <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[var(--chart-1)]" />stable</span>
            <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[var(--chart-2)]" />watch</span>
            <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[var(--discuss)]" />discuss</span>
            <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full border border-[var(--chart-4)]" />quiet day, excluded</span>
            <span className="ml-auto">
              {summary.eligible_days} days assessed, {summary.excluded_days} quiet
            </span>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link prefetch={false} href="/app" className="rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90">
              Open the dashboard
            </Link>
            <Link prefetch={false} href="/report" className="rounded-[var(--radius-sm)] border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-surface-raised">
              See the doctor report
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
