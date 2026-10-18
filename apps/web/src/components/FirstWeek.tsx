/**
 * The first week, as a product rather than an absence.
 *
 * A new wearer's dashboard used to say "Learning. No eligible days yet."
 * and nothing else, which is a dead end: it does not say what is being
 * learned, how far along it is, what the wearer should do today, or what
 * the page will look like once it is done. A judge who opened the real
 * profile saw an empty product; a family member would have closed it.
 *
 * So the warmup gets its own card: seven slots, one per counted day,
 * today's words against the 150-word floor, the days that fell short and
 * by how much, what happens on day eight, and a link to the simulated
 * person for what "done" looks like. Everything here is derived from the
 * same rows the engine reads, so it cannot disagree with the tier.
 */

import Link from "next/link";
import { InfoButton } from "./InfoButton";
import { PROFILE, fmtDate, type Assessment } from "../lib/api";

const WARMUP_DAYS = 7;
const MIN_WORDS = 150;

interface DayRow {
  date: string;
  token_count_day: number;
}

export function FirstWeek({ days, assessments, eligibleDays }: { days: DayRow[]; assessments: Assessment[]; eligibleDays: number }) {
  const eligible = new Set(assessments.filter((a) => a.eligible).map((a) => a.date));
  const counted = days.filter((d) => eligible.has(d.date)).map((d) => d.date);
  const latest = days.length ? days[days.length - 1] : null;
  const latestCounted = latest ? eligible.has(latest.date) : false;
  const short = days.filter((d) => !eligible.has(d.date) && d.date !== latest?.date).slice(-5).reverse();
  const slots = Array.from({ length: WARMUP_DAYS }, (_, i) => counted[i] ?? null);
  const voice = PROFILE === "me-voice";

  return (
    <section className="mt-4 rounded-[var(--radius-lg)] border border-[var(--primary)] bg-surface p-5" aria-labelledby="first-week">
      <p id="first-week" className="text-xs font-semibold uppercase tracking-wider text-muted">
        Your first week
        <InfoButton id="n-of-1" />
      </p>
      <p className="mt-2 text-sm leading-relaxed text-ink">
        Seven counted days teach Bellwether what normal sounds like for you. Nothing is compared until they are in.{" "}
        <span className="font-medium">{Math.min(eligibleDays, WARMUP_DAYS)} of {WARMUP_DAYS} days counted.</span>
      </p>

      <ol className="mt-4 grid grid-cols-7 gap-1.5" aria-label="Counted days">
        {slots.map((date, i) => (
          <li
            key={i}
            className={`rounded-[var(--radius-sm)] border px-1 py-2 text-center text-xs ${date ? "border-[var(--success)] bg-success-soft text-[var(--success)]" : "border-dashed border-line text-muted"}`}
            title={date ? `${fmtDate(date)} counted` : `Day ${i + 1}, not yet`}
          >
            <span className="block font-semibold">{i + 1}</span>
            <span className="block truncate">{date ? fmtDate(date) : " "}</span>
          </li>
        ))}
      </ol>

      {latest && !latestCounted && (
        <div className="mt-4">
          <div className="flex items-baseline justify-between text-sm">
            <span className="text-muted">{fmtDate(latest.date)}, so far</span>
            <span className="font-medium">
              {latest.token_count_day} of {MIN_WORDS} words
            </span>
          </div>
          <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-bg" role="progressbar" aria-valuemin={0} aria-valuemax={MIN_WORDS} aria-valuenow={Math.min(latest.token_count_day, MIN_WORDS)} aria-label="Words toward today counting">
            <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.min(100, (latest.token_count_day / MIN_WORDS) * 100)}%` }} />
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            {voice
              ? `About ${Math.max(1, Math.ceil((MIN_WORDS - latest.token_count_day) / 130))} more minute${MIN_WORDS - latest.token_count_day > 130 ? "s" : ""} of talking today and this day counts. Check in: say "Bellwether check-in" and the date, then keep talking to the band on your own. Any topic: what you did, what is on your mind, plans for tomorrow.`
              : "A day needs 150 words of speech to count. Quiet days are left out rather than misread as change."}
          </p>
        </div>
      )}

      {short.length > 0 && (
        <ul className="mt-4 divide-y divide-line rounded-[var(--radius-sm)] border border-line text-sm">
          {short.map((d) => (
            <li key={d.date} className="flex justify-between px-3 py-1.5">
              <span className="text-muted">{fmtDate(d.date)}</span>
              <span className="text-muted">{d.token_count_day} words, short by {MIN_WORDS - d.token_count_day}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 grid gap-3 text-sm leading-relaxed text-muted sm:grid-cols-2">
        <p>
          <span className="font-medium text-ink">From day eight:</span> each new day is compared with these seven. The chart fills, the weekly note starts, and the report becomes something to bring to an appointment.
        </p>
        <p>
          <span className="font-medium text-ink">What that looks like:</span>{" "}
          <Link href="/app" className="text-[var(--primary)] underline underline-offset-2">the simulated person</Link>, eight weeks in, labelled as simulated on every screen.
        </p>
      </div>
    </section>
  );
}
