"use client";

import { useState } from "react";
import { API } from "../lib/api";

/**
 * The privacy claim, pressable.
 *
 * The section above says Bellwether never stores words. For a product
 * that listens to somebody's speech every day, that sentence carries more
 * weight than anything else on the page, and a visitor had no way to
 * check it. A test proved it; the test was invisible.
 *
 * One press sends a day to the real intake route with a transcript
 * attached that is full of what must never be kept: a name, a doctor, a
 * family member, an address, an account number, a medication. Then it
 * reads back what the store kept and searches it for each one.
 *
 * The result worth looking at is an absence, so the panel reports what
 * it searched for and did not find, rather than only that a request
 * succeeded. It runs against a fresh in-memory store for each press, so
 * nobody can write rows into the deployed table, and it says so below.
 */

interface Finding {
  what: string;
  looked_for: string;
  found: boolean;
}

interface Result {
  sent: { fields: string[]; transcript: string };
  response: { status: number; body: { stored: number } };
  kept: string[];
  dropped: string[];
  strings_kept: string[];
  findings: Finding[];
  any_found: boolean;
  sandbox: boolean;
  ms: number;
}

export function PrivacyProof() {
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [r, setR] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setState("running");
    setError(null);
    try {
      const res = await fetch(`${API}/v1/privacy-check`, { method: "POST" });
      if (!res.ok) throw new Error(`the service answered ${res.status}`);
      setR((await res.json()) as Result);
      setState("done");
    } catch (err) {
      setError((err as Error).message);
      setState("error");
    }
  };

  return (
    <div className="mt-10 rounded-[var(--radius-lg)] border border-line bg-bg p-6 sm:p-8">
      <h3 className="text-lg font-semibold tracking-tight">
        Check it yourself
      </h3>
      <p className="mt-3 max-w-[720px] text-sm leading-relaxed text-muted">
        This sends one day to the real intake with an ordinary morning&apos;s
        transcript attached, the kind a wearable hears, full of a name, a
        doctor, a family member, an address, an account number and a
        medication. Then it reads back what was kept and searches it for
        every one of them.
      </p>

      <button
        type="button"
        onClick={() => void run()}
        disabled={state === "running"}
        className="mt-6 rounded-[var(--radius-sm)] bg-[var(--primary)] px-5 py-3 text-sm font-medium text-[var(--primary-contrast)] transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {state === "running"
          ? "Sending the day..."
          : state === "idle"
            ? "Send a day with the words attached"
            : "Send it again"}
      </button>

      <div aria-live="polite">
        {state === "error" && (
          <p className="mt-6 rounded-[var(--radius-md)] border border-[var(--discuss)] bg-[var(--discuss-soft)] p-4 text-sm text-[var(--discuss)]">
            The service could not be reached: {error}. Nothing is being shown
            in its place.
          </p>
        )}

        {state === "done" && r && (
          <>
            <div className="mt-6 rounded-[var(--radius-md)] border border-line bg-surface p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                What was sent, alongside the nine numbers
              </p>
              <p className="mt-2 text-sm italic leading-relaxed text-ink">
                &ldquo;{r.sent.transcript}&rdquo;
              </p>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="rounded-[var(--radius-md)] border border-line bg-surface p-4">
                <p className="text-sm font-semibold text-[var(--success)]">
                  Kept: {r.kept.length} fields
                </p>
                <p className="mt-2 font-mono text-[12px] leading-relaxed text-muted">
                  {r.kept.join(", ")}
                </p>
                <p className="mt-3 text-sm text-muted">
                  The only text left is{" "}
                  <span className="font-medium text-ink">
                    {r.strings_kept.join(", ")}
                  </span>
                  .
                </p>
              </div>
              <div className="rounded-[var(--radius-md)] border border-line bg-surface p-4">
                <p className="text-sm font-semibold text-[var(--discuss)]">
                  Dropped at the door: {r.dropped.length} fields
                </p>
                <p className="mt-2 font-mono text-[12px] leading-relaxed text-muted">
                  {r.dropped.join(", ")}
                </p>
              </div>
            </div>

            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {r.findings.map((f) => (
                <li
                  key={f.looked_for}
                  className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-line bg-surface px-4 py-3 text-sm"
                >
                  <span className="text-muted">
                    {f.what}: <span className="font-mono text-[12px] text-ink">{f.looked_for}</span>
                  </span>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      f.found
                        ? "bg-[var(--discuss-soft)] text-[var(--discuss)]"
                        : "bg-[var(--success-soft)] text-[var(--success)]"
                    }`}
                  >
                    {f.found ? "Found" : "Not stored"}
                  </span>
                </li>
              ))}
            </ul>

            <p className="mt-4 text-sm leading-relaxed text-muted">
              {r.any_found
                ? "Something that should never be stored was found. This is a defect, and it is shown rather than hidden."
                : `None of the six survived. The day was accepted and stored, with the words gone, in ${r.ms}ms.`}{" "}
              This ran the real intake route against a fresh store made for
              this press, so nothing you send here is written to the live
              service.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
