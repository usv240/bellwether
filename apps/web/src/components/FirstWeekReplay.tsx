/**
 * The first week, replayed one evening at a time.
 *
 * A real wearer's profile needs seven counted days before it says anything,
 * and in a hackathon's last week no real profile can show what day eight
 * looks like. This can, and it is labelled simulated on every line: the
 * first ten days of the stable simulated person, word counts set to the
 * size of a two-minute check-in, day three short on purpose.
 *
 * Each step asks the service for the profile as it stood at the end of
 * that day (as_of), so what shows is what the wearer would have seen that
 * evening, not hindsight: the slots filling, the short day not counting,
 * the first comparison arriving a day later because of it, and the note
 * the assistant would read aloud after the check-in.
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import { API, fmtDate } from "../lib/api";

const SIM = "sam-first-week";
const FLOOR = 150;

interface Day {
  date: string;
  token_count_day: number;
}

interface Summary {
  tier: "learning" | "stable" | "watch" | "discuss" | "excluded";
  eligible_days: number;
}

interface Coaching {
  text: string;
  actions: string[];
}

const TIER: Record<Summary["tier"], { label: string; cls: string }> = {
  learning: { label: "Learning", cls: "bg-[var(--accent-soft)] text-[var(--accent)]" },
  stable: { label: "Stable", cls: "bg-[var(--success-soft)] text-[var(--success)]" },
  watch: { label: "Watch", cls: "bg-[var(--watch-soft)] text-[var(--watch)]" },
  discuss: { label: "Discuss", cls: "bg-[var(--watch-soft)] text-[var(--watch)]" },
  excluded: { label: "Excluded", cls: "bg-surface text-muted" },
};

export function FirstWeekReplay() {
  const [days, setDays] = useState<Day[]>([]);
  const [i, setI] = useState(0);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [note, setNote] = useState<Coaching | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(`${API}/v1/profiles/${SIM}/days`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { days: Day[] }) => {
        const rows = [...d.days].sort((a, b) => a.date.localeCompare(b.date));
        setDays(rows);
        setI(0);
      })
      .catch(() => setFailed(true));
  }, []);

  const day = days[i];
  useEffect(() => {
    if (!day) return;
    let live = true;
    Promise.all([
      fetch(`${API}/v1/profiles/${SIM}/summary?as_of=${day.date}`).then((r) => r.json()),
      fetch(`${API}/v1/profiles/${SIM}/coaching?as_of=${day.date}`).then((r) => r.json()),
    ])
      .then(([s, n]: [Summary, Coaching]) => {
        if (live) {
          setSummary(s);
          setNote(n);
        }
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [day]);

  const counted = useMemo(() => {
    let n = 0;
    return days.map((d, k) => {
      if (k <= i && d.token_count_day >= FLOOR) n += 1;
      return n;
    });
  }, [days, i]);

  return (
    <section id="first-week-replay" className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">Simulated first week, one evening at a time</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">What the first ten days look like</h2>
        </div>
        <span className="shrink-0 rounded-full bg-[var(--watch-soft)] px-3 py-1 text-xs font-semibold text-[var(--watch)]">
          Simulated
        </span>
      </div>
      <p className="mt-3 max-w-[720px] text-base leading-relaxed text-muted">
        Generated speech through the real extractor and engine, word counts set to the size of a two-minute
        check-in, and the third day short on purpose. Each step is the profile as it stood that evening, and the
        note is what the assistant would read aloud after the check-in.
      </p>

      {failed && <p className="mt-4 text-base text-muted">The simulated week could not be fetched from the service just now.</p>}

      {days.length > 0 && (
        <>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => setI((k) => Math.max(0, k - 1))}
              disabled={i === 0}
              className="press min-h-11 shrink-0 rounded-[var(--radius-sm)] border border-line px-4 text-base text-ink disabled:opacity-40"
              aria-label="Back, previous evening"
            >
              Back
            </button>
            <input
              type="range"
              min={0}
              max={days.length - 1}
              value={i}
              onChange={(e) => setI(Number(e.target.value))}
              className="h-11 w-full cursor-pointer accent-[var(--primary)]"
              aria-label="Evening"
              aria-valuetext={`Day ${i + 1}, ${fmtDate(day?.date)}`}
            />
            <button
              type="button"
              onClick={() => setI((k) => Math.min(days.length - 1, k + 1))}
              disabled={i === days.length - 1}
              className="press min-h-11 shrink-0 rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-base font-medium text-[var(--primary-contrast)] disabled:opacity-40"
              aria-label="Next evening"
            >
              Next
            </button>
          </div>

          <ol className="mt-4 grid grid-cols-5 gap-1.5 sm:grid-cols-10" aria-label="Check-ins so far">
            {days.map((d, k) => {
              const future = k > i;
              const short = d.token_count_day < FLOOR;
              const cls = future
                ? "border-dashed border-line text-muted"
                : short
                  ? "border-2 border-dashed border-[var(--watch)] bg-bg text-[var(--watch)]"
                  : counted[k] > 7
                    ? "border-[var(--success)] bg-[var(--success-soft)] text-[var(--success)]"
                    : "border-[var(--primary)] bg-bg text-ink";
              return (
                <li key={d.date} className={`rounded-[var(--radius-sm)] border p-1.5 text-center ${cls}`}>
                  <span className="block text-xs font-semibold">Day {k + 1}</span>
                  <span className="block font-mono text-xs">{future ? "" : short ? `${d.token_count_day}, short` : d.token_count_day}</span>
                </li>
              );
            })}
          </ol>
          <p className="mt-2 text-sm text-muted">
            Words that evening. Outlined days build the baseline, green days are compared with it, and a day under {FLOOR} words is short and does not count.
          </p>

          <div className="mt-4 rounded-[var(--radius-md)] border border-line bg-bg p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-base font-medium text-ink">Evening of {fmtDate(day?.date)}</span>
              {summary && (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${TIER[summary.tier].cls}`}>
                  {TIER[summary.tier].label}
                </span>
              )}
              {summary && <span className="text-sm text-muted">{Math.min(summary.eligible_days, 7)} of 7 baseline days counted</span>}
            </div>
            {note && (
              <>
                <p className="mt-3 text-base leading-relaxed text-ink">
                  <span className="mr-2 font-mono text-xs text-muted">host says</span>
                  {note.text}
                </p>
                {note.actions.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-base text-muted">
                    {note.actions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}
