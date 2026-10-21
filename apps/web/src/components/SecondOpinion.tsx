/**
 * A second opinion on a flagged change: both sides, then the note.
 *
 * The evidence is live: weigh_the_change on the same server Alexa+ uses
 * lists numbered items for a real change (C) and for an ordinary week (O),
 * computed from the engine's numbers with no model. Below it is one real
 * run of the second-opinion agents, captured and committed: an Advocate
 * and a Sceptic argue from those items, and a Referee writes the note,
 * which passes a gate (both sides cited, no number outside the evidence,
 * no condition named) before anyone sees it.
 *
 * The debate is a recording, labelled with its date and model, because a
 * model run on every page view would make the page slow and different on
 * every visit. The command that produces it is shown.
 */

"use client";

import { useEffect, useState } from "react";
import debate from "../data/second-opinion.json";
import { API, PROFILE, fmtDate } from "../lib/api";

interface Item {
  id: string;
  claim: string;
}

interface Weigh {
  tier: string;
  since: string | null;
  change: Item[];
  ordinary: Item[];
  note: string;
}

function Side({ title, items, tone }: { title: string; items: Item[]; tone: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-line bg-bg p-4">
      <p className={`text-xs font-semibold uppercase tracking-wider ${tone}`}>{title}</p>
      <ul className="mt-2 space-y-2 text-base leading-relaxed text-ink">
        {items.map((e) => (
          <li key={e.id}>
            <span className="mr-2 font-mono text-xs text-muted">{e.id}</span>
            {e.claim}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SecondOpinion() {
  const [w, setW] = useState<Weigh | null>(null);

  useEffect(() => {
    fetch(`${API}/v1/profiles/${PROFILE}/weigh`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setW(d))
      .catch(() => setW(null));
  }, []);

  if (!w || w.change.length === 0) return null;

  return (
    <section id="second-opinion" className="mt-4 rounded-[var(--radius-lg)] border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">A second opinion</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">Real change, or an ordinary week? Both sides first.</h2>
        </div>
        <span className="shrink-0 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
          Evidence, not a verdict
        </span>
      </div>
      <p className="mt-3 max-w-[720px] text-base leading-relaxed text-muted">
        Every item below is computed from this person&apos;s own numbers by the same MCP server Alexa+ uses, with no model
        involved. Two agents then argue it, one for each side, and a third writes the note. The note may cite only these
        items and use only these numbers, or it is refused.
      </p>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Side title="For a real change" items={w.change} tone="text-[var(--watch)]" />
        <Side title="For an ordinary week" items={w.ordinary} tone="text-[var(--success)]" />
      </div>

      {debate.profile_id === PROFILE && (
        <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--primary)] p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">
            The agents&apos; note, from a real run on {fmtDate(debate.captured)}
          </p>
          <p className="mt-2 text-base leading-relaxed text-ink">{debate.note}</p>
          <details className="mt-2 text-base text-muted">
            <summary className="disclose font-medium text-ink">Read the two arguments it weighed</summary>
            <p className="mt-2 leading-relaxed">
              <span className="font-semibold text-ink">The Advocate, for a real change: </span>
              {debate.advocate}
            </p>
            <p className="mt-2 leading-relaxed">
              <span className="font-semibold text-ink">The Sceptic, for an ordinary week: </span>
              {debate.sceptic}
            </p>
          </details>
        </div>
      )}
    </section>
  );
}
