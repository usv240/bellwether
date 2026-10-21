"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { InfoButton } from "../../components/InfoButton";
import { Confounders } from "../../components/Confounders";
import { FirstWeek } from "../../components/FirstWeek";
import { HostedCheckIn } from "../../components/HostedCheckIn";
import { SecondOpinion } from "../../components/SecondOpinion";
import { FirstWeekReplay } from "../../components/FirstWeekReplay";
import { Nav } from "../../components/Nav";
import { TrendChart, type TrendRow } from "../../components/TrendChart";
import debate from "../../data/second-opinion.json";
import {
  FEATURE_INFO,
  FEATURE_LABEL,
  humaniseExplanation,
  isMeasureLine,
  PROFILE,
  PROFILES,
  PROFILE_TABS,
  withProfile,
  TIER_CLASS,
  TIER_LABEL,
  fmtDate,
  getJSON,
  ownerKey,
  postJSON,
  setOwnerKey,
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

const cap = (s: string) => (s ? s[0]!.toUpperCase() + s.slice(1) : s);

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
  // The profile is read from the URL, which the static prerender cannot
  // see, so anything that names it waits for the client. Otherwise the
  // server's "Simulated person" and the client's "Real Bee" disagree and
  // React reports a hydration mismatch on every real-data page.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [annDate, setAnnDate] = useState("");
  const [annText, setAnnText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [claimed, setClaimed] = useState(false);
  const [keyDraft, setKeyDraft] = useState("");
  useEffect(() => {
    getJSON<{ claimed: boolean }>(`/v1/profiles/${PROFILE}/claimed`).then((r) => setClaimed(r.claimed)).catch(() => setClaimed(false));
    setKeyDraft(ownerKey());
  }, []);

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

  // The flag moment's parts: one whole-day sentence leads, the rest folds.
  const flagged = summary?.tier === "watch" || summary?.tier === "discuss";
  const general = (summary?.explanation ?? []).filter((l) => !isMeasureLine(l)).map(humaniseExplanation);
  const measureLines = (summary?.explanation ?? []).filter(isMeasureLine).map((l) => ({
    text: cap(humaniseExplanation(l)),
    key: Object.keys(FEATURE_LABEL).find((k) => l.startsWith(`${k} `)),
  }));
  const lead = general[0] ?? "";
  const detail: { text: string; key?: string }[] = [...general.slice(1).map((text) => ({ text })), ...measureLines];
  const measureCount = measureLines.length;

  async function saveAnnotation(e: React.FormEvent) {
    e.preventDefault();
    if (!annDate || !annText.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      await postJSON(`/v1/profiles/${PROFILE}/annotations`, { date: annDate, note: annText.trim() });
      setAnnText("");
      await load();
    } catch (e) {
      setSaveError((e as Error).message);
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
        <h1 className="text-2xl font-semibold tracking-tight">Speech baseline</h1>
        {mounted && (<>
        {/*
          Whose data. Four choices, so two rows of two on a phone and one
          row from sm up; the old three-column grid stranded the fourth on
          a row of its own. Plain links, not next/link: PROFILE is read once
          when the page loads.
        */}
        <nav aria-label="Whose data" className="mt-4 grid grid-cols-2 gap-0.5 rounded-[var(--radius-sm)] border border-line bg-surface p-0.5 text-[13px] sm:inline-flex sm:text-sm">
          {PROFILE_TABS.map((t) => (
            <a
              key={t.id}
              href={withProfile("/app", t.id)}
              aria-current={t.id === PROFILE ? "page" : undefined}
              className={`press flex min-h-11 items-center justify-center rounded-[calc(var(--radius-sm)-2px)] px-2 text-center sm:px-3 font-medium leading-tight sm:whitespace-nowrap ${t.id === PROFILE ? "bg-[var(--primary)] text-[var(--primary-contrast)]" : "text-muted hover:bg-bg hover:text-ink"}`}
            >
              {t.short}
            </a>
          ))}
        </nav>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className={`rounded-full border border-line px-2.5 py-0.5 text-xs font-medium ${PROFILES[PROFILE].simulated ? "bg-accent-soft text-[var(--accent)]" : "bg-success-soft text-[var(--success)]"}`}>{PROFILES[PROFILE].label}</span>
          {PROFILES[PROFILE].simulated && <InfoButton id="simulated" />}
          <span className="max-w-[760px] text-sm text-muted">{PROFILES[PROFILE].note}</span>
        </div>
        </>)}

        {error && <p className="mt-6 rounded-[var(--radius-md)] border border-line bg-surface p-4 text-base text-muted">The service did not answer: {error}</p>}

        {!summary && !error && (
          <section
            className="mt-6 rounded-[var(--radius-lg)] border border-line bg-surface p-5"
            aria-busy="true"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Right now
            </p>
            <p className="mt-2 text-base text-muted">Reading the baseline...</p>
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
                  {summary.since && <span className="text-base text-muted">since {fmtDate(summary.since)}</span>}
                </div>
                {flagged ? (
                  <>
                    {/*
                      The flag moment. A red pill followed by ten mechanical
                      lines reads as a verdict. So: one plain sentence, then
                      what the tier does and does not mean, right under it,
                      and the measure-by-measure detail one tap away.
                    */}
                    {lead && <p className="mt-3 text-lg leading-snug text-ink">{lead}</p>}
                    <ul className="mt-3 space-y-1 text-base leading-relaxed text-muted">
                      <li>It is not a diagnosis, a screening result, or a probability of any condition.</li>
                      <li>It is a reason to add a note about your week, or to bring the report to a clinician. It is not a reason to act on your own.</li>
                    </ul>
                    {(detail.length > 0 || summary.contributors.length > 0) && (
                      <details className="mt-4 rounded-[var(--radius-md)] border border-line bg-bg px-4">
                        <summary className="disclose text-base font-medium text-ink">
                          What moved{measureCount > 0 ? ` (${measureCount} ${measureCount === 1 ? "measure" : "measures"})` : ""}
                        </summary>
                        <ul className="space-y-2 pb-3 text-base leading-relaxed text-muted">
                          {detail.map((d) => (
                            <li key={d.text}>
                              {d.text}
                              {d.key && <InfoButton id={FEATURE_INFO[d.key] ?? "features-not-words"} />}
                            </li>
                          ))}
                        </ul>
                        {measureCount === 0 && summary.contributors.length > 0 && (
                          <div className="flex flex-wrap gap-2 border-t border-line py-3">
                            {summary.contributors.map((c) => (
                              <span key={c} className="rounded-full border border-line bg-surface px-2.5 py-1 text-sm text-ink">
                                {FEATURE_LABEL[c] ?? c}
                                <InfoButton id={FEATURE_INFO[c] ?? "features-not-words"} />
                              </span>
                            ))}
                          </div>
                        )}
                      </details>
                    )}
                  </>
                ) : (
                  <ul className="mt-3 space-y-1 text-base leading-relaxed text-muted">
                    {summary.explanation.map((line) => (
                      <li key={line}>{humaniseExplanation(line)}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="rounded-[var(--radius-lg)] border border-line bg-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Baseline
                  <InfoButton id="n-of-1" />
                </p>
                <dl className="mt-3 space-y-2 text-base">
                  <div className="flex justify-between"><dt className="text-muted">Days assessed</dt><dd className="font-medium">{summary.eligible_days}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Quiet days excluded <InfoButton id="exposure" /></dt><dd className="font-medium">{summary.excluded_days}</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Stable streak</dt><dd className="font-medium">{summary.stable_streak_days} days</dd></div>
                  <div className="flex justify-between"><dt className="text-muted">Latest day</dt><dd className="font-medium">{fmtDate(summary.latest_date)}</dd></div>
                </dl>
                <Link prefetch={false} href={withProfile("/report")} className="press mt-4 inline-flex min-h-11 items-center rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-base font-medium text-[var(--primary-contrast)] hover:opacity-90">
                  Open the doctor report
                </Link>
              </div>
            </section>

            {summary.in_warmup && <FirstWeek days={days} assessments={assessments} eligibleDays={summary.eligible_days} />}

            {!PROFILES[PROFILE].simulated && <HostedCheckIn />}

            {(PROFILE === "sam-first-week" || PROFILE === "me-voice") && <FirstWeekReplay />}

            {/* Weekly note */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                This week
                <InfoButton id="bedrock-ladder" />
              </p>
              {note ? (
                <>
                  <p className="mt-2 max-w-[720px] text-base leading-relaxed">{note.text}</p>
                  <p className="mt-2 text-sm text-muted">
                    {note.source === "bedrock" ? "Phrased on Amazon Bedrock from facts the engine computed." : "The engine's own summary, from a fixed template."}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-base text-muted">Writing the note...</p>
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
              <p className="mt-2 text-sm leading-relaxed text-muted">Zero is your baseline. Higher is further from it in the direction the literature associates with decline. Hollow marks are quiet days, excluded. A ringed dot has a note. <InfoButton id="freeze" /></p>
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

            <SecondOpinion />

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
                <p className="mt-2 text-base text-muted">Travel, illness, poor sleep, a new medication. Notes never change the numbers; they help you read them.</p>
                <label className="mt-3 block text-sm text-muted">
                  Day
                  <input type="date" value={annDate} onChange={(e) => setAnnDate(e.target.value)} className="mt-1 min-h-11 w-full rounded-[var(--radius-sm)] border border-line bg-bg px-3 py-2 text-base text-ink" required />
                </label>
                <label className="mt-3 block text-sm text-muted">
                  Note
                  <input type="text" value={annText} onChange={(e) => setAnnText(e.target.value)} maxLength={200} placeholder="slept badly, travelling" className="mt-1 min-h-11 w-full rounded-[var(--radius-sm)] border border-line bg-bg px-3 py-2 text-base text-ink" required />
                </label>
                <button type="submit" disabled={saving} className="press mt-4 min-h-11 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-base font-medium text-[var(--primary-contrast)] hover:opacity-90 disabled:opacity-60">
                  {saving ? "Saving..." : "Save note"}
                </button>
                {saveError && <p className="mt-3 text-base text-[var(--discuss)]">{saveError}</p>}
                {claimed && (
                  <label className="mt-4 block text-sm text-muted">
                    This profile is claimed by its wearer. Their key, to write here (kept in this browser only)
                    <input
                      type="password"
                      autoComplete="off"
                      value={keyDraft}
                      onChange={(e) => { setKeyDraft(e.target.value); setOwnerKey(PROFILE, e.target.value.trim()); }}
                      placeholder="from .bellwether-key on the wearer's computer"
                      className="mt-1 min-h-11 w-full rounded-[var(--radius-sm)] border border-line bg-bg px-3 py-2 text-base text-ink"
                    />
                  </label>
                )}
              </form>
            </section>

            {/* Spoken check */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                The spoken check
                <InfoButton id="spoken-check" />
              </p>
              <p className="mt-2 max-w-[720px] text-base text-muted">Ninety seconds, out loud. Useful when the tier is watch or discuss, and any time you like. An assistant can run it with you by voice through the MCP server.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div className="rounded-[var(--radius-md)] border border-line bg-bg p-4">
                  <p className="text-base font-semibold">1. Name as many animals as you can in sixty seconds</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <button type="button" onClick={() => { setFluencyLeft(60); setFluencyRunning(true); }} disabled={fluencyRunning} className="press min-h-11 rounded-[var(--radius-sm)] border border-line px-4 text-base hover:bg-surface-raised disabled:opacity-60">
                      {fluencyRunning ? "Running" : "Start the timer"}
                    </button>
                    <span className="font-mono text-2xl tabular-nums" aria-live="polite">{fluencyLeft}s</span>
                  </div>
                  <label className="mt-3 block text-sm text-muted">
                    Distinct animals named
                    <input type="number" min={0} max={100} value={fluencyCount} onChange={(e) => setFluencyCount(e.target.value)} className="mt-1 block min-h-11 w-32 rounded-[var(--radius-sm)] border border-line bg-surface px-3 py-2 text-base text-ink" />
                  </label>
                  <button type="button" onClick={() => logCheck("animal_fluency", Number(fluencyCount || 0), "web dashboard")} disabled={fluencyCount === ""} className="press mt-3 min-h-11 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-base font-medium text-[var(--primary-contrast)] hover:opacity-90 disabled:opacity-60">
                    Log the score
                  </button>
                </div>
                <div className="rounded-[var(--radius-md)] border border-line bg-bg p-4">
                  <p className="text-base font-semibold">2. Repeat each sentence exactly</p>
                  <ol className="mt-3 space-y-3 text-base">
                    {SENTENCES.map((s, i) => (
                      <li key={s}>
                        <p className="text-muted">{s}</p>
                        <div className="choice-row mt-1.5 grid grid-cols-3 gap-1.5 text-sm" role="radiogroup" aria-label={`Sentence ${i + 1}`}>
                          {[2, 1, 0].map((v) => (
                            <label key={v} className={`press relative flex min-h-11 cursor-pointer items-center justify-center rounded-[var(--radius-sm)] border px-2 text-center leading-tight ${repScores[i] === v ? "border-[var(--primary)] bg-primary-soft font-semibold text-[var(--primary)]" : "border-line text-muted hover:text-ink"}`}>
                              <input type="radio" className="sr-only" name={`rep-${i}`} checked={repScores[i] === v} onChange={() => setRepScores((r) => r.map((x, j) => (j === i ? v : x)))} />
                              {v === 2 ? "exact" : v === 1 ? "one change" : "different"}
                            </label>
                          ))}
                        </div>
                      </li>
                    ))}
                  </ol>
                  <button type="button" onClick={() => logCheck("sentence_repetition", repScores.reduce((a, b) => a + b, 0), "web dashboard")} className="press mt-3 min-h-11 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-base font-medium text-[var(--primary-contrast)] hover:opacity-90">
                    Log {repScores.reduce((a, b) => a + b, 0)} of 6
                  </button>
                </div>
              </div>
              {checkMsg && <p className="mt-3 text-base text-[var(--success)]" role="status">{checkMsg}</p>}
              <p className="mt-3 text-sm text-muted">Scores are displayed on the timeline and never turned into a judgement beyond the tier language.</p>
            </section>

            {/* What we store */}
            <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                What we store
                <InfoButton id="features-not-words" />
              </p>
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-base text-muted">An actual stored row for {latest ? fmtDate(latest.date) : "the latest day"} is under How this works, below. This is everything there is.</p>
                </div>
                <div>
                  <p className="text-base text-muted">Never stored, by construction:</p>
                  <ul className="mt-2 space-y-1 text-base text-muted">
                    <li>The words that produced those numbers</li>
                    <li>Any audio</li>
                    <li>Anyone else&apos;s speech</li>
                  </ul>
                  <p className="mt-3 text-sm text-muted">A test posts a row with a transcript field and proves it never lands. Extraction runs on your own machine; the service only ever receives numbers.</p>
                </div>
              </div>
            </section>

            {/*
              How this works. The model ids, the commands and the raw row
              are real and worth keeping, for a developer or a judge. They
              are not for the person whose speech this is, so they sit
              behind one disclosure at the end rather than beside the tier.
            */}
            <details className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface px-5">
              <summary className="disclose text-base font-semibold text-ink">How this works</summary>
              <div className="space-y-5 border-t border-line py-5 text-sm leading-relaxed text-muted">
                {note && (
                  <div>
                    <p className="font-semibold text-ink">The weekly note</p>
                    <p className="mt-1">
                      {note.source === "bedrock" ? `Phrased by ${note.model} on Amazon Bedrock from facts the engine computed.` : "The deterministic template: every model in the ladder was unavailable, so this is the engine's own summary."}
                      {note.attempts.length > 1 && ` ${note.attempts.length - 1} ${note.attempts.length - 1 === 1 ? "model was" : "models were"} tried first.`}
                    </p>
                  </div>
                )}
                {debate.profile_id === PROFILE && (
                  <div>
                    <p className="font-semibold text-ink">The second opinion</p>
                    <p className="mt-1">
                      {debate.model}. Gate: {debate.gate}. Run it yourself:
                    </p>
                    <pre tabIndex={0} className="mt-2 overflow-x-auto rounded-[var(--radius-md)] border border-line bg-bg p-3 font-mono text-xs leading-relaxed text-ink"><code>{`python apps/agent/second_opinion.py --profile ${debate.profile_id}`}</code></pre>
                  </div>
                )}
                {!PROFILES[PROFILE].simulated && (
                  <div>
                    <p className="font-semibold text-ink">The hosted check-in</p>
                    <pre tabIndex={0} className="mt-2 overflow-x-auto rounded-[var(--radius-md)] border border-line bg-bg p-3 font-mono text-xs leading-relaxed text-ink"><code>{"python apps/agent/check_in_host.py --profile <your-name> --count"}</code></pre>
                    <p className="mt-2">
                      The host is a client of the same MCP server an Alexa+ agent gets: <code className="font-mono text-xs">start_check_in</code> for
                      tonight&apos;s lines, <code className="font-mono text-xs">coaching_note</code> for what to say after. It speaks through Amazon
                      Polly because the Alexa+ connection is not yet open to scripts. It never reads a transcript; it waits for the
                      Bee, runs <code className="font-mono text-xs">bellwether-ingest mine --days 1</code>, and hears the count come back.
                    </p>
                  </div>
                )}
                <div>
                  <p className="font-semibold text-ink">An actual stored row for {latest ? fmtDate(latest.date) : "the latest day"}</p>
                  <pre tabIndex={0} className="mt-2 overflow-x-auto rounded-[var(--radius-md)] border border-line bg-bg p-3 font-mono text-xs leading-relaxed text-ink">{sampleRow ? JSON.stringify(sampleRow, null, 1) : "..."}</pre>
                </div>
              </div>
            </details>

            <p className="mt-8 max-w-[760px] text-sm leading-relaxed text-muted">{summary.disclaimer}</p>
          </>
        )}
      </main>
    </div>
  );
}
