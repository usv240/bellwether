import Link from "next/link";
import { DemoStrip } from "../components/DemoStrip";
import { InfoButton } from "../components/InfoButton";
import { Nav } from "../components/Nav";
import { API } from "../lib/api";

const STATS = [
  { value: "3.5 years", label: "from first symptoms to a dementia diagnosis, on average", info: "diagnostic-delay" },
  { value: "Early stage only", label: "where the newest Alzheimer's treatments are approved to work", info: "treatment-window" },
  { value: "40 to 80%", label: "of what a doctor says is forgotten immediately", info: "forgotten-information" },
  { value: "85 to 89.6%", label: "accuracy of speech-based detection on the field's public benchmark", info: "adress" },
];

const STEPS = [
  { n: 1, title: "Wear", info: "bee", text: "The Bee wristband transcribes your day. You already have it on." },
  { n: 2, title: "Measure", info: "features-not-words", text: "On your own computer, each day of speech becomes nine numbers. The words are discarded." },
  { n: 3, title: "Learn", info: "n-of-1", text: "A week of your normal. Not anyone else's. Your accent, your pace, your habits are the baseline." },
  { n: 4, title: "Show", info: "tiers", text: "Stable, watch, or discuss, with the reasons and the dates, and a one-page report for the appointment." },
];

const EVIDENCE = [
  { title: "Time to diagnosis in dementia: systematic review with meta-analysis", source: "Orgeta et al., Int J Geriatr Psychiatry, 2025", finding: "3.5 years on average from symptom onset to diagnosis across 13 studies and 30,257 participants; 4.1 years for young-onset.", url: "https://onlinelibrary.wiley.com/doi/10.1002/gps.70129" },
  { title: "Lecanemab and donanemab indications", source: "U.S. FDA, 2023 and 2024", finding: "Both approved only for mild cognitive impairment or mild dementia due to Alzheimer's disease, with no data on starting later.", url: "https://www.fda.gov/news-events/press-announcements/fda-converts-novel-alzheimers-disease-treatment-traditional-approval" },
  { title: "Patients' memory for medical information", source: "Kessels, J R Soc Med, 2003", finding: "40 to 80 percent of medical information is forgotten immediately; almost half of what is remembered is incorrect.", url: "https://journals.sagepub.com/doi/abs/10.1177/014107680309600504" },
  { title: "The ADReSS challenge", source: "Luz et al., Interspeech, 2020", finding: "Best systems separate Alzheimer's from control speech at 85 to 89.6 percent on a benchmark balanced for age and gender.", url: "https://arxiv.org/abs/2004.06833" },
  { title: "Linguistic ability in early life and Alzheimer's disease in late life", source: "Snowdon et al., JAMA, 1996", finding: "Low idea density in writing at age 22 predicted Alzheimer's disease at autopsy some 58 years later. The Nun Study.", url: "https://pubmed.ncbi.nlm.nih.gov/8606473/" },
  { title: "Linguistic features identify Alzheimer's disease in narrative speech", source: "Fraser, Meltzer and Rudzicz, J Alzheimers Dis, 2016", finding: "The linguistic profile this product measures: reduced diversity and syntactic complexity, more pronouns and filled pauses.", url: "https://pubmed.ncbi.nlm.nih.gov/26484921/" },
];

const FAQ = [
  { q: "Is this a diagnosis?", a: "No. Bellwether describes change over time in one person against their own baseline and lists its reasons. It does not diagnose, screen for, treat or prevent any condition, and it is not a medical device. It gives you a record to share with a clinician you trust." },
  { q: "Who can see my data?", a: "You. Nothing that could reconstruct a sentence is stored anywhere: transcripts are turned into nine numbers a day on your own machine and discarded. The service receives only the numbers, and a test proves that any field carrying text is dropped at the door." },
  { q: "What if I have an accent, or speak two languages?", a: "Your baseline is you. Bellwether never compares you with a population, so an accent or a quiet manner is simply what normal looks like for you. Cross-language support is on the roadmap; the feature extractor is English-only today." },
  { q: "Why should a healthy thirty-year-old care?", a: "Medication fog, poor sleep, illness and recovery all show in speech, and a long baseline is the most valuable thing this can give you. The earlier the baseline starts, the more a change later in life has to be compared with." },
  { q: "What does Bee record?", a: "Bee transcribes conversations near the wearer. Bellwether analyses only the wearer's own utterances and drops everyone else's at ingest. No audio reaches Bellwether at all." },
  { q: "Can it detect a stroke?", a: "No. It is not an emergency product and reacts on the scale of days, not minutes. If speech changes suddenly, call emergency services." },
  { q: "Why does it say the person is simulated?", a: "Because they are. The live baseline on this page is generated speech for one invented person, run through the real extractor and the real engine, so you can see eight weeks including a change from week six. Everything after the words is the product." },
  { q: "Can an assistant ask it for me?", a: "Yes. Bellwether is a Model Context Protocol server, so a voice assistant or AI agent can ask how you have been sounding, read the report, or run the spoken check with you by voice. The assistant gets the same seven numbers-only tools and nothing else." },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />
      <main id="main">
        {/* Hero */}
        <section className="mx-auto max-w-[1120px] px-4 pb-16 pt-16 sm:px-6 sm:pt-24">
          <div className="max-w-[720px]">
            <p className="mb-4 inline-block rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-muted">
              Built on Bee. Not a diagnosis.
            </p>
            <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
              Speech is a vital sign.{" "}
              <span className="text-[var(--primary)]">Start measuring yours.</span>
            </h1>
            <p className="mt-6 max-w-[640px] text-lg leading-relaxed text-muted">
              Bellwether uses the Bee wristband you already wear to learn how you normally speak, and shows you, in numbers you own, when that changes. Evidence for a better conversation with your doctor.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#demo" className="rounded-[var(--radius-sm)] bg-[var(--primary)] px-5 py-3 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90">
                See a live baseline
              </a>
              <a href="#evidence" className="rounded-[var(--radius-sm)] border border-line bg-surface px-5 py-3 text-sm font-medium text-ink hover:bg-surface-raised">
                Read the evidence
              </a>
            </div>
            <p className="mt-8 text-xs text-muted">
              Bee, Amazon Bedrock, AWS, and the Model Context Protocol. Open source under MIT.
            </p>
          </div>
        </section>

        {/* The problem */}
        <section id="problem" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Your watch knows when your heart skips. Nothing knows when your brain does.</h2>
            <p className="mt-4 max-w-[720px] leading-relaxed text-muted">
              Speech is the brain&apos;s only continuous, observable output. When something changes, speech is usually where it shows first: more pauses, simpler sentences, lost words. Doctors know this. They also hear a patient for a few minutes a year, so the change hides in plain sound, for years.
              <InfoButton id="speech-as-signal" />
            </p>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {STATS.map((s) => (
                <div key={s.info} className="rounded-[var(--radius-lg)] border border-line bg-bg p-5">
                  <p className="text-3xl font-semibold tracking-tight text-[var(--primary)]">{s.value}</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    {s.label}
                    <InfoButton id={s.info} />
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="border-t border-line">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h2>
            <p className="mt-3 max-w-[640px] text-muted">Four steps. The words never leave your machine.</p>
            <svg viewBox="0 0 880 90" className="mt-8 w-full max-w-[880px]" role="img" aria-label="Wear, measure, learn, show: a four-step flow">
              {["Wear", "Measure", "Learn", "Show"].map((t, i) => (
                <g key={t} transform={`translate(${i * 220}, 10)`}>
                  <rect width="180" height="60" rx="10" fill="var(--surface)" stroke="var(--border)" />
                  <text x="90" y="37" textAnchor="middle" fontSize="16" fontWeight="600" fill="var(--text)">{t}</text>
                  {i < 3 && <path d="M186 40 L212 40 M204 33 L212 40 L204 47" stroke="var(--primary)" strokeWidth="2" fill="none" />}
                </g>
              ))}
              <text x="90" y="86" textAnchor="middle" fontSize="11" fill="var(--text-muted)">words</text>
              <text x="310" y="86" textAnchor="middle" fontSize="11" fill="var(--text-muted)">numbers only from here</text>
            </svg>
            <ol className="mt-8 grid gap-4 md:grid-cols-4">
              {STEPS.map((s) => (
                <li key={s.n} className="rounded-[var(--radius-lg)] border border-line bg-surface p-5">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">Step {s.n}</p>
                  <h3 className="mt-1 text-lg font-semibold">
                    {s.title}
                    <InfoButton id={s.info} />
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Live baseline */}
        <section id="demo" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">A live baseline, on the real engine</h2>
            <p className="mt-3 max-w-[640px] text-muted">
              This is the deployed service. The person is simulated; the extractor, the baseline engine and the tiers are the product.
            </p>
            <div className="mt-8">
              <DemoStrip />
            </div>
          </div>
        </section>

        {/* Evidence */}
        <section id="evidence" className="border-t border-line">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">The evidence</h2>
            <p className="mt-3 max-w-[640px] text-muted">Every number on this page, with its source. Each was checked at the source during the build.</p>
            <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {EVIDENCE.map((e) => (
                <a key={e.url} href={e.url} target="_blank" rel="noopener noreferrer" className="block rounded-[var(--radius-lg)] border border-line bg-surface p-5 transition-colors hover:border-[var(--primary)]">
                  <p className="text-sm font-semibold leading-snug">{e.title}</p>
                  <p className="mt-1 text-xs text-[var(--primary)]">{e.source}</p>
                  <p className="mt-3 text-sm leading-relaxed text-muted">{e.finding}</p>
                </a>
              ))}
              <a href="https://github.com/usv240/bellwether/blob/main/docs/EVIDENCE.md" target="_blank" rel="noopener noreferrer" className="block rounded-[var(--radius-lg)] border border-dashed border-line bg-bg p-5 transition-colors hover:border-[var(--primary)]">
                <p className="text-sm font-semibold">We publish our own validation</p>
                <p className="mt-1 text-xs text-[var(--primary)]">docs/EVIDENCE.md, section 6</p>
                <p className="mt-3 text-sm leading-relaxed text-muted">Two synthetic personas through the production extractor and engine: 47 quiet days with no false alarms, and a gradual change caught two days in. Plus what it does not show, stated plainly.</p>
              </a>
            </div>
          </div>
        </section>

        {/* Privacy */}
        <section id="privacy" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What we store, and what we never do
              <InfoButton id="features-not-words" />
            </h2>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-5">
                <p className="text-sm font-semibold text-[var(--success)]">Stored</p>
                <ul className="mt-3 space-y-2 text-sm text-muted">
                  <li>Nine numbers per day, such as vocabulary variety and idea density</li>
                  <li>How many words were spoken that day</li>
                  <li>Notes you add, such as travel or poor sleep</li>
                  <li>Spoken check scores</li>
                </ul>
              </div>
              <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-5">
                <p className="text-sm font-semibold text-[var(--discuss)]">Never stored</p>
                <ul className="mt-3 space-y-2 text-sm text-muted">
                  <li>Transcripts, sentences, or any words</li>
                  <li>Audio of any kind</li>
                  <li>Other people&apos;s speech</li>
                  <li>Anything that could reconstruct a conversation</li>
                </ul>
              </div>
            </div>
            <p className="mt-8 max-w-[720px] text-sm leading-relaxed text-muted">
              Bellwether is a general wellness tool. It does not diagnose, treat, cure, or prevent any disease, and it is not a medical device. Changes in speech have many everyday causes, including sleep, stress, medication, and mood. Share the report with a clinician you trust.
              <InfoButton id="general-wellness" />
            </p>
          </div>
        </section>

        {/* For developers */}
        <section id="api" className="border-t border-line">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">For developers</h2>
            <p className="mt-3 max-w-[720px] text-muted">
              The API accepts feature rows, not text. Run the open-source <code className="font-mono text-sm">speech-vitals</code> package where the transcript is, and post the numbers. That is a stance, not a limit.
            </p>
            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <pre className="overflow-x-auto rounded-[var(--radius-lg)] border border-line bg-surface p-4 font-mono text-xs leading-relaxed text-ink"><code>{`pip install "speech-vitals[nlp]"
python -m spacy download en_core_web_sm
speech-vitals analyze transcript.jsonl --speaker speaker_1 --out days.json

curl -X POST ${API}/v1/profiles/me/days \\
  -H "content-type: application/json" \\
  -d @days.json`}</code></pre>
              <div className="rounded-[var(--radius-lg)] border border-line bg-surface p-5 text-sm leading-relaxed text-muted">
                <p><span className="font-semibold text-ink">Endpoints.</span> <code className="font-mono text-xs">GET /v1/profiles/{"{id}"}/summary</code>, <code className="font-mono text-xs">/assessments</code>, <code className="font-mono text-xs">/report</code>, <code className="font-mono text-xs">/weekly-note</code>; <code className="font-mono text-xs">POST /days</code>, <code className="font-mono text-xs">/annotations</code>, <code className="font-mono text-xs">/checks</code>. Interactive docs at <a className="text-[var(--primary)] underline underline-offset-2" href={`${API}/v1/docs`} target="_blank" rel="noopener noreferrer">/v1/docs</a>.</p>
                <p className="mt-3"><span className="font-semibold text-ink">MCP.</span> <code className="font-mono text-xs">{API}/mcp</code>, spec 2025-11-25 over Streamable HTTP, seven tools. <InfoButton id="mcp" /></p>
                <p className="mt-3"><span className="font-semibold text-ink">Resilience.</span> <a className="text-[var(--primary)] underline underline-offset-2" href={`${API}/api/resilience`} target="_blank" rel="noopener noreferrer">/api/resilience</a> reports every degradation path.</p>
                <p className="mt-3"><span className="font-semibold text-ink">Bee.</span> Ingestion calls <code className="font-mono text-xs">bee conversations</code>, <code className="font-mono text-xs">bee now</code>, <code className="font-mono text-xs">bee changed</code>, <code className="font-mono text-xs">bee stream --json</code> and <code className="font-mono text-xs">bee sync</code> in code. <InfoButton id="bee" /></p>
              </div>
            </div>
          </div>
        </section>

        {/* About the build */}
        <section id="build" className="border-t border-line bg-surface">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">About the build</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-5 text-sm leading-relaxed text-muted">
                <p className="font-semibold text-ink">Tracks</p>
                <p className="mt-2">Bee (Wearable AI), with the MCP server as a genuine Alexa+ surface. Mini challenges: AWS Builder and Open Source.</p>
              </div>
              <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-5 text-sm leading-relaxed text-muted">
                <p className="font-semibold text-ink">AWS, and why</p>
                <p className="mt-2">Bedrock phrases the weekly note through a three-model ladder that falls to a deterministic template. DynamoDB holds feature rows only. Lambda runs the API and MCP server without spaCy. CDK, S3 and CloudFront for the rest. <InfoButton id="bedrock-ladder" /></p>
              </div>
              <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-5 text-sm leading-relaxed text-muted">
                <p className="font-semibold text-ink">Open source</p>
                <p className="mt-2"><code className="font-mono text-xs">speech-vitals</code> (MIT): nine language features per day with their literature basis, features only, never words. The engine, the Bee adapter and the service are MIT too.</p>
              </div>
            </div>
            <p className="mt-6 text-sm text-muted">
              <a className="text-[var(--primary)] underline underline-offset-2" href="https://github.com/usv240/bellwether" target="_blank" rel="noopener noreferrer">Repository</a>
              {" · "}
              <a className="text-[var(--primary)] underline underline-offset-2" href="https://github.com/usv240/bellwether/blob/main/FRICTION_LOG.md" target="_blank" rel="noopener noreferrer">Friction log</a>
              {" · "}
              <a className="text-[var(--primary)] underline underline-offset-2" href="https://github.com/usv240/bellwether/blob/main/docs/EVIDENCE.md" target="_blank" rel="noopener noreferrer">Evidence</a>
              {" · "}
              <Link className="text-[var(--primary)] underline underline-offset-2" href="/report">Doctor report</Link>
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="border-t border-line">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">The questions a careful person asks</h2>
            <div className="mt-8 max-w-[760px] divide-y divide-line rounded-[var(--radius-lg)] border border-line bg-surface">
              {FAQ.map((f) => (
                <details key={f.q} className="group px-5 py-4">
                  <summary className="cursor-pointer list-none text-sm font-semibold text-ink marker:hidden">{f.q}</summary>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-[1120px] px-4 py-10 text-xs leading-relaxed text-muted sm:px-6">
          <p>Bellwether is a general wellness tool and not a medical device. It does not diagnose, treat, cure, or prevent any disease. MIT licensed. Built for the Build, Ship, Shape: Amazon Developer Hackathon.</p>
          <p className="mt-2">Design principles: progressive disclosure, one idea per screen, evidence beside every claim, WCAG 2.2 AA, honest labelling of simulated data.</p>
        </div>
      </footer>
    </div>
  );
}
