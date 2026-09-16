"use client";

import { useEffect, useState } from "react";
import { InfoButton } from "../../components/InfoButton";
import { Nav } from "../../components/Nav";
import { FEATURE_LABEL, PROFILE, TIER_CLASS, TIER_LABEL, fmtDate, getJSON, type Report, type Tier } from "../../lib/api";

/**
 * The doctor report: one page, designed for a twelve-minute appointment.
 * Same data the MCP tool generate_doctor_report returns, rendered for a
 * printer. The disclaimer is part of the page, not a footer.
 */
export default function ReportPage() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJSON<Report>(`/v1/profiles/${PROFILE}/report?weeks=8`).then(setReport).catch((e: Error) => setError(e.message));
  }, []);

  const total = report?.tier_history?.reduce((n, r) => n + r.days, 0) ?? 0;

  return (
    <div className="min-h-screen bg-bg text-ink">
      <style>{`@media print { header, .no-print { display: none !important; } body { background: #fff; color: #000; } .print-page { border: none !important; box-shadow: none !important; } }`}</style>
      <Nav />
      <main id="main" className="mx-auto max-w-[860px] px-4 py-10 sm:px-6">
        <div className="no-print flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-line bg-accent-soft px-2.5 py-0.5 text-xs font-medium text-[var(--accent)]">Simulated person</span>
            <InfoButton id="simulated" />
          </div>
          <button type="button" onClick={() => window.print()} className="rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90">
            Print or save as PDF
          </button>
        </div>

        {error && <p className="mt-6 text-sm text-muted">The service did not answer: {error}</p>}

        {report && report.available && (
          <article className="print-page mt-6 rounded-[var(--radius-lg)] border border-line bg-surface p-6 shadow-[var(--shadow-sm)] sm:p-10">
            <header>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">Bellwether speech report</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                {fmtDate(report.range?.from)} to {fmtDate(report.range?.to)}, {report.range?.weeks} weeks
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                A record of change over time in one person&apos;s everyday speech, compared only with their own baseline. Nine language features per day; no transcript exists. {report.eligible_days} days assessed, {report.excluded_days} quiet days excluded.
              </p>
            </header>

            {/* Current */}
            <section className="mt-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Current status</h2>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                {report.current && (
                  <>
                    <span className={`rounded-full px-3 py-1 text-base font-semibold ${TIER_CLASS[report.current.tier]}`}>{TIER_LABEL[report.current.tier]}</span>
                    {report.current.since && <span className="text-sm text-muted">since {fmtDate(report.current.since)}</span>}
                  </>
                )}
              </div>
              {report.current && report.current.contributors.length > 0 && (
                <p className="mt-2 text-sm text-muted">
                  Measures behind this: {report.current.contributors.map((c) => FEATURE_LABEL[c] ?? c).join(", ")}.
                </p>
              )}
            </section>

            {/* Tier history */}
            <section className="mt-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Tier over the period</h2>
              <div className="mt-2 flex h-6 w-full overflow-hidden rounded-[var(--radius-sm)] border border-line" role="img" aria-label="Tier history as a proportional bar">
                {report.tier_history?.map((r, i) => (
                  <div key={i} title={`${TIER_LABEL[r.tier]}: ${fmtDate(r.from)} to ${fmtDate(r.to)}`} className={`${TIER_CLASS[r.tier as Tier]} h-full`} style={{ width: `${(r.days / Math.max(total, 1)) * 100}%` }} />
                ))}
              </div>
              <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                {report.tier_history?.map((r, i) => (
                  <li key={i}>{TIER_LABEL[r.tier]}: {fmtDate(r.from)}{r.days > 1 ? ` to ${fmtDate(r.to)}` : ""} ({r.days}d)</li>
                ))}
              </ul>
            </section>

            {/* Notable changes */}
            <section className="mt-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Notable changes</h2>
              {report.notable_changes && report.notable_changes.length > 0 ? (
                <table className="mt-2 w-full text-sm">
                  <thead className="text-left text-xs text-muted">
                    <tr><th className="py-1 pr-3 font-medium">From</th><th className="py-1 pr-3 font-medium">Tier</th><th className="py-1 pr-3 font-medium">What moved</th></tr>
                  </thead>
                  <tbody>
                    {report.notable_changes.map((n) => (
                      <tr key={n.date} className="border-t border-line align-top">
                        <td className="py-2 pr-3 whitespace-nowrap">{fmtDate(n.date)}</td>
                        <td className="py-2 pr-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_CLASS[n.tier]}`}>{TIER_LABEL[n.tier]}</span> <span className="text-xs text-muted">{n.days}d</span></td>
                        <td className="py-2 pr-3 text-muted">
                          {n.features.length > 0 ? n.features.map((f) => `${FEATURE_LABEL[f.feature] ?? f.feature} ${f.direction}`).join("; ") : n.explanation[0]}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="mt-2 text-sm text-muted">No change outside the person&apos;s normal range in this period.</p>
              )}
            </section>

            {/* Most moved */}
            {report.most_moved_features && report.most_moved_features.length > 0 && (
              <section className="mt-6">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Features that moved most</h2>
                <ul className="mt-2 space-y-1 text-sm">
                  {report.most_moved_features.map((f) => (
                    <li key={f.feature}><span className="font-medium">{FEATURE_LABEL[f.feature] ?? f.feature}</span> <span className="text-muted">({f.plain}) mean change score {f.mean_concern_z.toFixed(2)}</span></li>
                  ))}
                </ul>
              </section>
            )}

            {/* Checks and notes */}
            <section className="mt-6 grid gap-6 sm:grid-cols-2">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Spoken checks</h2>
                {report.spoken_checks && report.spoken_checks.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm text-muted">
                    {report.spoken_checks.map((c, i) => (
                      <li key={i}>{fmtDate(c.at.slice(0, 10))}: {c.kind === "animal_fluency" ? "animals in 60 s" : "sentence repetition"} {c.score}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-muted">None recorded in this period.</p>
                )}
              </div>
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Notes the person added</h2>
                {report.annotations && Object.keys(report.annotations).length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm text-muted">
                    {Object.entries(report.annotations).map(([d, n]) => (
                      <li key={d}>{fmtDate(d)}: {n}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-muted">None.</p>
                )}
              </div>
            </section>

            {/* Disclaimer and method */}
            <section className="mt-8 rounded-[var(--radius-md)] border border-line bg-bg p-4">
              <p className="text-sm font-semibold">This is not a diagnosis.</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{report.disclaimer}</p>
              <p className="mt-2 text-xs leading-relaxed text-muted">{report.method}</p>
            </section>

            <section className="mt-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Sources</h2>
              <ol className="mt-2 space-y-1 text-xs leading-relaxed text-muted">
                {report.citations?.map((c, i) => (
                  <li key={i}>{i + 1}. {c.claim}. {c.source}</li>
                ))}
              </ol>
            </section>
          </article>
        )}

        {report && !report.available && <p className="mt-6 text-sm text-muted">{report.message}</p>}
      </main>
    </div>
  );
}
