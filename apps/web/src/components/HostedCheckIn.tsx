/**
 * The hosted check-in: a voice assistant asks, the Bee listens.
 *
 * Until now the wearer ran the check-in alone: say "Bellwether check-in"
 * and the date, then talk for two minutes. That works and stays. This
 * card is the other way to do it, the one the judges' brief asks for by
 * name, a wearable beside an Echo: the assistant speaks tonight's three
 * questions through the speaker, the band on the wrist records the
 * answers, and the host's own words are removed before anything is
 * measured.
 *
 * The questions are standard elicitation tasks from speech assessment,
 * fixed and rotated by date, so a person's days stay comparable with
 * their own. The card shows tonight's three so the wearer knows what is
 * coming and a reader can see they are ordinary questions, not a test.
 *
 * The read here is a peek: it does not record a start. Only a host that
 * actually speaks the opener does that, and the card says if one did.
 */

"use client";

import { useEffect, useState } from "react";
import { API, PROFILE, fmtDate } from "../lib/api";

interface Prompt {
  kind: "narrative" | "description" | "procedure";
  text: string;
}

interface Start {
  date: string;
  opener: string;
  prompts: Prompt[];
  closing: string;
  basis: string;
  answer_seconds: number;
  word_floor: number;
  eligible_days: number;
  warmup_days: number;
  today_counted: boolean;
  already_started_today: { at: string; host: string } | null;
}

const KIND: Record<Prompt["kind"], string> = {
  narrative: "Tell",
  description: "Describe",
  procedure: "Explain",
};

export function HostedCheckIn() {
  const [start, setStart] = useState<Start | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const day = new Date();
    const local = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
    fetch(`${API}/v1/profiles/${PROFILE}/check-in?peek=1&date=${local}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: Start) => setStart(d))
      .catch(() => setFailed(true));
  }, []);

  return (
    <section className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">Tonight&apos;s check-in, hosted</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">Let the assistant ask the questions</h2>
        </div>
        <span className="shrink-0 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
          Bee on the wrist, a speaker in the room
        </span>
      </div>

      <p className="mt-3 max-w-[720px] text-base leading-relaxed text-muted">
        The assistant speaks the opener and three questions through the speaker. The band records the answers.
        On your computer, the host&apos;s own words are removed before anything is measured, so a sixteen-word
        question is never counted as your speech. Two minutes of answers is about 250 words; a day counts from
        {start ? ` ${start.word_floor}` : " 150"}.
      </p>

      {failed && (
        <p className="mt-4 text-base text-muted">Tonight&apos;s script could not be fetched from the service just now.</p>
      )}

      {start && (
        <>
          <ol className="mt-4 space-y-2">
            <li className="rounded-[var(--radius-md)] border border-line bg-bg p-3 text-base">
              <span className="mr-2 font-mono text-xs text-muted">opens</span>
              <span className="text-ink">{start.opener}</span>
            </li>
            {start.prompts.map((p, i) => (
              <li key={p.kind} className="rounded-[var(--radius-md)] border border-line bg-bg p-3 text-base">
                <span className="mr-2 font-mono text-xs text-muted">{i + 1}</span>
                <span className="mr-2 rounded-full bg-[var(--success-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--success)]">{KIND[p.kind]}</span>
                <span className="text-ink">{p.text}</span>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            {start.basis} Tonight is {fmtDate(start.date)}. {start.answer_seconds} seconds to answer each.
          </p>
          <p className="mt-2 text-base text-ink">
            {start.today_counted
              ? "Today has already counted."
              : start.already_started_today
                ? `A host started tonight's check-in at ${new Date(start.already_started_today.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}. The Bee is still writing it down, or the day was short.`
                : `Not yet tonight. ${start.eligible_days} of ${start.warmup_days} days counted so far.`}
          </p>
        </>
      )}

    </section>
  );
}
