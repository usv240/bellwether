/**
 * How a person connects their own Bee.
 *
 * The page showed what Bellwether does with a year of speech and never
 * said how somebody gets their own speech into it. For the Bee track the
 * answer is the whole point: the project exists to use a person's real
 * Bee data, and the steps to do that lived only in the README.
 *
 * The order is the privacy argument made physical. Steps one to four
 * happen on the person's own computer, where the words are. Only step
 * five crosses the network, and by then there are no words left, only
 * nine numbers a day. The badge on each step says which side of that line
 * it is on.
 *
 * The status note is the honest part. The pipeline is built and every
 * failure of the first run is rehearsed in tests with an injected runner,
 * but the device is on order, so no real Bee day has been through it yet.
 * The page says that rather than letting the steps imply otherwise.
 */

import { API } from "../lib/api";

const REPO = "https://github.com/usv240/bellwether";

const STEPS: { title: string; body: string; code: string; where: "device" | "yours" | "network" }[] = [
  {
    title: "Let your computer read your Bee",
    body: "Install Bee's own command line tool, then in the Bee app turn on Developer Mode by selecting the version number five times in Settings.",
    code: "npm install -g @beeai/cli\nbee login",
    where: "device",
  },
  {
    title: "Install Bellwether's reader",
    body: "It runs on your machine, not ours. The feature extractor is the open source speech-vitals package from PyPI.",
    code: `git clone ${REPO}\ncd bellwether\npip install -e "packages/speech-vitals[nlp]" -e apps/ingest\npython -m spacy download en_core_web_sm`,
    where: "yours",
  },
  {
    title: "Rehearse the first run",
    body: "Read only and safe to repeat. It checks the tool, the login, whether anything has been recorded, whether a real day reduces to nine numbers, and whether that day has enough speech to judge. It stops at the first thing that is actually wrong and says what.",
    code: "bellwether-ingest firstrun",
    where: "yours",
  },
  {
    title: "Turn your days into numbers",
    body: "Each day of your speech becomes nine numbers. The words are read, measured and discarded here. Only your own voice is kept, not the people you talked to.",
    code: "bellwether-ingest pull --owner speaker_1 --out days.json",
    where: "yours",
  },
  {
    title: "Send the numbers",
    body: "This is the only step that leaves your computer, and by now there is nothing in it that could reconstruct a sentence. Open the file first if you want to see for yourself.",
    // The real URL, not a placeholder. "$API" read fine to anyone who had
    // seen this repository and meant nothing to anyone who had not.
    code: `curl -X POST ${API}/v1/profiles/me/days \\\n  -H "content-type: application/json" -d @days.json`,
    where: "network",
  },
];

const WHERE: Record<(typeof STEPS)[number]["where"], { label: string; cls: string }> = {
  device: { label: "Your Bee", cls: "bg-[var(--accent-soft)] text-[var(--accent)]" },
  yours: { label: "Your computer, words stay here", cls: "bg-[var(--success-soft)] text-[var(--success)]" },
  network: { label: "Leaves your computer, numbers only", cls: "bg-[var(--watch-soft)] text-[var(--watch)]" },
};

export function BeeConnect() {
  return (
    <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-6 sm:p-8">
      <h3 className="text-lg font-semibold tracking-tight">
        Connecting your own Bee
      </h3>
      <p className="mt-3 max-w-[720px] text-sm leading-relaxed text-muted">
        Five steps. The first four happen on your own computer, which is
        where your words are and where they stay. Only the last one uses
        the network, and it carries nine numbers a day.
      </p>

      <ol className="mt-6 space-y-3">
        {STEPS.map((s, i) => (
          <li
            key={s.title}
            className="rounded-[var(--radius-md)] border border-line bg-surface p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <p className="max-w-[560px] font-medium text-ink">
                <span className="mr-2 font-mono text-sm text-muted">{i + 1}</span>
                {s.title}
              </p>
              <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${WHERE[s.where].cls}`}>
                {WHERE[s.where].label}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
            <pre className="mt-3 overflow-x-auto rounded-[var(--radius-sm)] border border-line bg-bg p-3 font-mono text-[12px] leading-relaxed text-ink">
              <code>{s.code}</code>
            </pre>
          </li>
        ))}
      </ol>

      {/*
        Said plainly. A reader who works out for themselves that no real
        Bee day has been through this yet is right to distrust every step
        above it.
      */}
      <p className="mt-6 max-w-[720px] text-sm leading-relaxed text-muted">
        <span className="font-medium text-ink">Where this actually stands: </span>
        every step is built, and every way the first run can fail is
        rehearsed in tests before the hardware exists. The device is on
        order, so no real Bee day has been through the pipeline yet. The day
        one does, <code className="font-mono text-[12px]">bellwether-ingest evidence</code>{" "}
        writes a public record that it happened, containing counts and the
        nine numbers and not one word of speech.
      </p>
    </div>
  );
}
