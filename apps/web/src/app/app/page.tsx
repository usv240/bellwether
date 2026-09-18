"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { InfoButton } from "../../components/InfoButton";
import { Confounders } from "../../components/Confounders";
import { Nav } from "../../components/Nav";
import { TrendChart, type TrendRow } from "../../components/TrendChart";
import {
  FEATURE_INFO,
  FEATURE_LABEL,
  humaniseExplanation,
  PROFILE,
  TIER_CLASS,
  TIER_LABEL,
  fmtDate,
  getJSON,
  postJSON,
  type Assessment,
  type Note,
  type Summary,
} from "../../lib/api";

interface DayRow {
  date: string;
  utterances?: number;
  token_count_day: number;
  [k: string]: number | string | undefined;
}

const SENTENCES = [
  "The quiet river ran behind the old stone mill.",
  "She bought fresh bread and two green apples on Tuesday.",
  "If it rains tomorrow, we will visit the museum instead.",
];

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [days, setDays] = useState<DayRow[]>([]);
  const [note, setNote] = useState<Note | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [annDate, setAnnDate] = useState("");
  const [annText, setAnnText] = useState("");
  const [saving, setSaving] = useState(false);

  const [fluencyRunning, setFluencyRunning] = useState(false);
  const [fluencyLeft, setFluencyLeft] = useState(60);
  const [fluencyCount, setFluencyCount] = useState("");
  const [repScores, setRepScores] = useState<number[]>([2, 2, 2]);
  const [checkMsg, setCheckMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, a, d] = await Promise.all([
        getJSON<Summary>(`/v1/profiles/${PROFILE}/summary`),
        getJSON<{ days: Assessment[] }>(`/v1/profiles/${PROFILE}/assessments?weeks=8`),
        getJSON<{ days: DayRow[] }>(`/v1/profiles/${PROFILE}/days`),
      ]);
      setSummary(s);
      setAssessments(a.days);
      setDays(d.days);
      if (!annDate && s.latest_date) setAnnDate(s.latest_date);
      getJSON<Note>(`/v1/profiles/${PROFILE}/weekly-note`).then(setNote).catch(() => setNote(null));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [annDate]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!fluencyRunning) return;
    if (fluencyLeft <= 0) {
      setFluencyRunning(false);
      return;
    }
    const t = setTimeout(() => setFluencyLeft((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [fluencyRunning, fluencyLeft]);

  const rows: TrendRow[] = assessments.map((d) => ({ date: d.date, composite: d.composite, tier: d.tier, annotation: d.annotation }));
  const latest = assessments[assessments.length - 1];
  const recent = [...assessments].reverse().slice(0, 14);
  const sampleRow = days[days.length - 1];

  async function saveAnnotation(e: React.FormEvent) {
    e.preventDefault();
    if (!annDate || !annText.trim()) return;
    setSaving(true);
    try {
      await postJSON(`/v1/profiles/${PROFILE}/annotations`, { date: annDate, note: annText.trim() });
      setAnnText("");
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function logCheck(kind: "animal_fluency" | "sentence_repetition", score: number, detail: string) {
    await postJSON(`/v1/profiles/${PROFILE}/checks`, { kind, score, detail });
    setCheckMsg(`Logged ${kind === "animal_fluency" ? "animal naming" : "sentence repetition"}: ${score}. It now appears on the report timeline.`);
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />
      <main id="main" className="mx-auto max-w-[1120px] px-4 py-10 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full border border-line bg-accent-soft px-2.5 py-0.5 text-xs font-medium text-[var(--accent)]">Simulated person</span>
          <InfoButton id="simulated" />
          <span className="text-xs text-muted">Alex, eight weeks. Real engine, generated speech.</span>
        </div>

        {error && <p className="mt-6 rounded-[var(--radius-md)] border border-line bg-surface p-4 text-sm text-muted">The service did not answer: {error}</p>}

        {!summary && !error && (
          <section
            className="mt-6 rounded-[var(--radius-lg)] border border-line bg-surface p-5"
            aria-busy="true"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Right now
            </p>
            <p className="mt-2 text-sm text-muted">Reading the baseline...</p>
          </section>
        )}

        {summary && (
          <>
            {/* Status */}
            <section className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-[var(--radius-lg)] border border-line bg-surface p-5 md:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Right now
                  <InfoButton id="tiers" />
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <span className={`rounded-full px-3 py-1 text-base font-semibold ${TIER_CLASS[summary.tier]}`}>{TIER_LABEL[summary.tier]}</span>
                  {summary.since && <span className="text-sm text-muted">since {fmtDate(summary.since)}</span>}
                </div>
                <ul className="mt-3 space-y-1 text-sm leading-relaxed text-muted">
                  {summary.explanation.map((line) => (
                    <li key={line}>{humaniseExplanation(line)}</li>
                  ))}
                </ul>
                {summary.contributors.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {summary.contributors.map((c) => (
                      <span key={c} className="rounded-full border border-line bg-bg px-2.5 py-1 text-xs text-ink">
                        {FEATURE_LABEL[c] ?? c}
                        <InfoButton id={FEATURE_INFO[c] ?? "features-not-words"} />
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="rounded-[var(--radius-lg)] border border-line bg-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Baseline
                  <InfoButton id="n-of-1" />
                </p>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between"><dt className="text-muted">Days assessed</dt><dd className="font-medium">{summary.eligible_days}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Quiet days excluded <InfoButton id="exposure" /></dt><dd className="font-medium">{summary.excluded_days}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Stable streak</dt><dd className="font-medium">{summary.stable_streak_days} days</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Latest day</dt><dd className="font-medium">{fmtDate(summary.latest_date)}</dd></div>
                </dl>
                <Link prefetch={false} href="/report" className="mt-4 inline-block rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90">
                  Open the doctor report
                </Link>
              </div>
            </section>

            {/* Weekly note */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                This week
                <InfoButton id="bedrock-ladder" />
              </p>
              {note ? (
                <>
                  <p className="mt-2 max-w-[720px] text-base leading-relaxed">{note.text}</p>
                  <p className="mt-2 text-xs text-muted">
                    {note.source === "bedrock" ? `Phrased by ${note.model} on Amazon Bedrock from facts the engine computed.` : "The deterministic template: every model in the ladder was unavailable, so this is the engine's own summary."}
                    {note.attempts.length > 1 && ` ${note.attempts.length - 1} model(s) were tried first.`}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted">Writing the note...</p>
              )}
            </section>

            {/* Trend */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                Eight weeks
                <InfoButton id="cusum" />
              </p>
              <div className="mt-3">
                <TrendChart rows={rows} height={240} />
              </div>
              <p className="mt-2 text-xs text-muted">Zero is your baseline. Higher is further from it in the direction the literature associates with decline. Hollow marks are quiet days, excluded. A ringed dot has a note. <InfoButton id="freeze" /></p>
            </section>

            {/*
              What, then why, then so what.

              This panel used to sit at the top of the page, above any data,
              which put a wall of caveats in front of a reader who did not
              yet know what they were being cautioned about. It reads as the
              answer to "should I worry" only once the tier and the trend
              have been seen, so it lives here now.

              It still takes a nullable summary and renders whatever the API
              does, because the ordinary explanations for a change are the
              last thing that should depend on a network call.
            */}
            <section className="mt-4">
              <Confounders summary={summary} />
            </section>

            {/* Recent days + annotate */}
            <section className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-line bg-surface p-5 md:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">Recent days</p>
                <table className="mt-3 w-full text-sm">
                  <thead className="text-left text-xs text-muted">
                    <tr><th className="py-1 pr-3 font-medium">Day</th><th className="py-1 pr-3 font-medium">Tier</th><th className="py-1 pr-3 font-medium">Change score</th><th className="py-1 pr-3 font-medium">Note</th></tr>
                  </thead>
                  <tbody>
                    {recent.map((a) => (
                      <tr key={a.date} className="border-t border-line">
                        <td className="py-2 pr-3">{fmtDate(a.date)}</td>
                        <td className="py-2 pr-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_CLASS[a.tier]}`}>{TIER_LABEL[a.tier]}</span></td>
                        <td className="py-2 pr-3 font-mono text-xs">{a.composite === null ? (a.reason ? "excluded" : "learning") : a.composite.toFixed(2)}</td>
                        <td className="py-2 pr-3 text-muted">{a.annotation ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <form onSubmit={saveAnnotation} className="rounded-[var(--radius-lg)] border border-line bg-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">Add a note to a day</p>
                <p className="mt-2 text-sm text-muted">Travel, illness, poor sleep, a new medication. Notes never change the numbers; they help you read them.</p>
                <label className="mt-3 block text-xs text-muted">
                  Day
                  <input type="date" value={annDate} onChange={(e) => setAnnDate(e.target.value)} className="mt-1 w-full rounded-[var(--radius-sm)] border border-line bg-bg px-3 py-2 text-sm text-ink" required />
                </label>
                <label className="mt-3 block text-xs text-muted">
                  Note
                  <input type="text" value={annText} onChange={(e) => setAnnText(e.target.value)} maxLength={200} placeholder="slept badly, travelling" className="mt-1 w-full rounded-[var(--radius-sm)] border border-line bg-bg px-3 py-2 text-sm text-ink" required />
                </label>
                <button type="submit" disabled={saving} className="mt-4 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90 disabled:opacity-60">
                  {saving ? "Saving..." : "Save note"}
                </button>
              </form>
            </section>

            {/* Spoken check */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                The spoken check
                <InfoButton id="spoken-check" />
              </p>
              <p className="mt-2 max-w-[720px] text-sm text-muted">Ninety seconds, out loud. Useful when the tier is watch or discuss, and any time you like. An assistant can run it with you by voice through the MCP server.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div className="rounded-[var(--radius-md)] border border-line bg-bg p-4">
                  <p className="text-sm font-semibold">1. Name as many animals as you can in sixty seconds</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <button type="button" onClick={() => { setFluencyLeft(60); setFluencyRunning(true); }} disabled={fluencyRunning} className="rounded-[var(--radius-sm)] border border-line px-3 py-2 text-sm hover:bg-surface-raised disabled:opacity-60">
                      {fluencyRunning ? "Running" : "Start the timer"}
                    </button>
                    <span className="font-mono text-2xl tabular-nums" aria-live="polite">{fluencyLeft}s</span>
                  </div>
                  <label className="mt-3 block text-xs text-muted">
                    Distinct animals named
                    <input type="number" min={0} max={100} value={fluencyCount} onChange={(e) => setFluencyCount(e.target.value)} className="mt-1 w-32 rounded-[var(--radius-sm)] border border-line bg-surface px-3 py-2 text-sm text-ink" />
                  </label>
                  <button type="button" onClick={() => logCheck("animal_fluency", Number(fluencyCount || 0), "web dashboard")} disabled={fluencyCount === ""} className="mt-3 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90 disabled:opacity-60">
                    Log the score
                  </button>
                </div>
                <div className="rounded-[var(--radius-md)] border border-line bg-bg p-4">
                  <p className="text-sm font-semibold">2. Repeat each sentence exactly</p>
                  <ol className="mt-3 space-y-3 text-sm">
                    {SENTENCES.map((s, i) => (
                      <li key={s}>
                        <p className="text-muted">{s}</p>
                        <div className="mt-1 flex gap-2 text-xs">
                          {[2, 1, 0].map((v) => (
                            <label key={v} className="flex items-center gap-1">
                              <input type="radio" name={`rep-${i}`} checked={repScores[i] === v} onChange={() => setRepScores((r) => r.map((x, j) => (j === i ? v : x)))} />
                              {v === 2 ? "exact" : v === 1 ? "one change" : "different"}
                            </label>
                          ))}
                        </div>
                      </li>
                    ))}
                  </ol>
                  <button type="button" onClick={() => logCheck("sentence_repetition", repScores.reduce((a, b) => a + b, 0), "web dashboard")} className="mt-3 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90">
                    Log {repScores.reduce((a, b) => a + b, 0)} of 6
                  </button>
                </div>
              </div>
              {checkMsg && <p className="mt-3 text-sm text-[var(--success)]" role="status">{checkMsg}</p>}
              <p className="mt-3 text-xs text-muted">Scores are displayed on the timeline and never turned into a judgement beyond the tier language.</p>
            </section>

            {/* What we store */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                What we store
                <InfoButton id="features-not-words" />
              </p>
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted">An actual stored row for {latest ? fmtDate(latest.date) : "the latest day"}. This is everything there is.</p>
                  <pre className="mt-2 overflow-x-auto rounded-[var(--radius-md)] border border-line bg-bg p-3 font-mono text-xs leading-relaxed">{sampleRow ? JSON.stringify(sampleRow, null, 1) : "..."}</pre>
                </div>
                <div>
                  <p className="text-sm text-muted">Never stored, by construction:</p>
                  <ul className="mt-2 space-y-1 text-sm text-muted">
                    <li>The words that produced those numbers</li>
                    <li>Any audio</li>
                    <li>Anyone else&apos;s speech</li>
                  </ul>
                  <p className="mt-3 text-xs text-muted">A test posts a row with a transcript field and proves it never lands. Extraction runs on your own machine; the service only ever receives numbers.</p>
                </div>
              </div>
            </section>

            <p className="mt-8 text-xs leading-relaxed text-muted">{summary.disclaimer}</p>
          </>
        )}
      </main>
    </div>
  );
}
