"use client";

import { InfoButton } from "./InfoButton";
import { TIER_LABEL, type Summary, type Tier } from "../lib/api";

/**
 * "What else could explain this."
 *
 * The single most important panel in the product, and the one a tool like
 * this is most tempted to leave out.
 *
 * Spiegelhalter's review of risk communication ends with "have the humility
 * to admit uncertainty" and, earlier, with the distinction that decides the
 * whole design: "we need to be clear about whether we are seeking to
 * persuade, or fulfilling a duty to inform." Bellwether is informing. A
 * person who opens this and sees "discuss" will not read a methods page;
 * they will feel something. The honest response is to put the ordinary
 * explanations directly next to the tier, at the same size, before they go
 * looking for the frightening one.
 *
 * The confounders are not hedging. Every one of them genuinely moves these
 * features, and a person who recognises their own week in this list has
 * learned something true that the number alone would have hidden.
 *
 * Spiegelhalter D. Risk and Uncertainty Communication. Annual Review of
 * Statistics and Its Application. 2017;4:31-60.
 */

const COMMON = [
  { cause: "Not sleeping well", effect: "shorter sentences, more ums, harder to find words" },
  { cause: "A cold, flu, or any illness", effect: "everything moves at once, then returns" },
  { cause: "A new or changed medication", effect: "slower pace, simpler sentences, sometimes for weeks" },
  { cause: "A stressful or busy week", effect: "less varied vocabulary, more filler" },
  { cause: "Talking mostly to one person, or mostly on the phone", effect: "vocabulary narrows without anything changing in you" },
  { cause: "Alcohol, or a late night", effect: "clear effects on the following day" },
];

export function Confounders({ summary }: { summary: Summary | null }) {
  // Renders with or without the API. The ordinary explanations for a change
  // are the last thing that should depend on a network call succeeding: a
  // reader who sees a tier and no context is worse off than one who sees
  // neither. Only the tier word adapts once the summary arrives.
  const flagged = summary?.tier === "watch" || summary?.tier === "discuss";
  const tierWord = summary ? TIER_LABEL[summary.tier as Tier].toLowerCase() : "a flag";

  return (
    <section className="rounded-[var(--radius-lg)] border border-line bg-surface p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">
        What else could explain this
        <InfoButton id="confounders" />
      </h2>

      <p className="mt-2 max-w-[720px] text-sm leading-relaxed">
        {flagged ? (
          <>
            Bellwether has flagged a change, and the most likely reasons are ordinary ones. Speech moves with sleep, health, mood and who you spend the week talking to. Before reading anything else into it, look down this list and see whether you recognise your own weeks.
          </>
        ) : (
          <>
            {summary ? "Nothing is flagged right now. It is still worth knowing what moves these numbers, because when something does change, the explanation is usually on this list." : "Speech moves for ordinary reasons all the time. These explain far more changes than anything worrying does, which is why they are shown here rather than in a footnote."}
          </>
        )}
      </p>

      <ul className="mt-4 grid gap-x-8 gap-y-2 sm:grid-cols-2">
        {COMMON.map((c) => (
          <li key={c.cause} className="text-sm leading-relaxed">
            <span className="font-medium text-ink">{c.cause}</span>
            <span className="text-muted">: {c.effect}</span>
          </li>
        ))}
      </ul>

      <div className="mt-5 rounded-[var(--radius-md)] border border-line bg-bg p-4">
        <p className="text-sm font-semibold">What {tierWord} does not mean</p>
        <ul className="mt-2 space-y-1 text-sm leading-relaxed text-muted">
          <li>It is not a diagnosis, a screening result, or a probability of any condition.</li>
          <li>It does not predict what will happen next. Bellwether has no opinion about the future.</li>
          <li>It compares you only with your own past, never with other people, so it says nothing about how you compare with anyone.</li>
          {flagged && <li>It is a reason to add a note about your week, or to bring the report to a clinician. It is not a reason to act on your own.</li>}
        </ul>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-muted">
        The most useful thing you can do is add a note to the days you remember. A week marked{" "}
        <span className="text-ink">slept badly, travelling</span> is a week you can read honestly a month later, and notes never change the numbers.
      </p>
    </section>
  );
}
