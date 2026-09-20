# Bellwether: submission

## What it does

Your watch knows when your heart skips a beat. Nothing knows when your brain does.

Speech is the brain's only continuous, externally observable output, and when something changes it is usually where the change shows first: more pauses, simpler sentences, lost words. Clinicians know this, and they hear a patient for a few minutes a year. Across all dementias, the mean time from first symptoms to diagnosis is **3.5 years** ([Orgeta et al., 2025](https://onlinelibrary.wiley.com/doi/10.1002/gps.70129), 13 studies, 30,257 participants), and the newest treatments are approved **only** for the earliest stage, which is precisely what that delay skips past.

The Bee wristband already transcribes its wearer's day. Bellwether reads those transcripts on the wearer's own machine, keeps nine language features and discards the words, learns how that one person normally speaks, and shows them when that changes. It never diagnoses. Its output is the thing patients have never had: a page to put on a doctor's desk, which matters because 40 to 80 percent of what is said in an appointment is forgotten immediately and almost half of what is remembered is wrong ([Kessels, 2003](https://journals.sagepub.com/doi/abs/10.1177/014107680309600504)).

## How it works

Four steps, and the words never leave the wearer's machine.

1. **Wear.** Bee transcribes the day.
2. **Measure.** `speech-vitals` turns each day into nine features, each with its literature basis: vocabulary variety (MATTR), sentence length, syntactic depth, pronoun reliance, filled pauses, disfluencies, rare-word use, idea density, vocabulary size. The transcript is reduced in memory and discarded.
3. **Learn.** Seven days of warmup establish a personal baseline. After that, each day is standardised against the baseline **as it stood before that day**, so no day is compared with itself. A one-sided CUSUM on a signed composite detects persistent drift while ignoring noisy days.
4. **Show.** A tier with its reasons and dates, a weekly note, and a one-page report.

## The Bee track requirement, answered directly

The rule is specific: the video and the code have to show the project
actually using live Bee data to do something for a person, and mentioning
Bee is not enough. Taking each half of that separately.

**In code.** `apps/ingest` is a real client of the Bee CLI, not a wrapper
around a mention of one. It builds and runs the argv for `bee me`,
`bee now`, `bee changed --cursor`, `bee conversations list`,
`bee stream --json` and `bee sync`, handles the npm shim that Windows
needs, turns "not logged in" back into the instruction the Bee app uses,
and reduces what comes back to the nine features while discarding every
word. Thirty tests pin the exact argv through an injected runner, so the
integration is asserted rather than described. A second agent in
`apps/agent` holds Bee's own MCP server alongside ours, behind an
allowlist that withholds every Bee tool returning verbatim speech.

**On live data.** A Bee was bought for this. Everything upstream of the
device is finished and rehearsed: `bellwether-ingest firstrun` walks the
entire chain, stops at the first thing genuinely wrong, and says what to
do about it in the words the Bee app uses. Every failure that first
session can hit is reproduced in tests with an injected runner, including
a device with nothing recorded yet and a day too quiet to assess, so the
only untested step on the day is the one that needs the hardware.

Until that device is in hand there is no live Bee data in this repository,
and none is claimed. The personas are synthetic and say so, in the
fixtures, in the API responses and on every page that shows them. The
external validation in `harness/scotus` is real human speech, but it is
Supreme Court audio rather than Bee audio, and it is offered as evidence
about the engine rather than about the device.

## Built during the hackathon

This project did not exist before the submission window. The first commit
is 2026-09-16 and the whole repository is public history: every file, every
number and every correction was written for this hackathon.

Nothing here was adapted from earlier work, so the rules' question about
what changed during the window has the simplest possible answer, which is
all of it.

## Tracks and mini challenges

**Bee (primary) and Alexa+.** AWS Builder and Open Source mini challenges.

The rules cap winnings rather than entries: "each project can only win one track prize and one mini challenge prize."

**Bee** is the primary track. The repository calls the Bee developer tooling in code, not in a README: `apps/ingest/bellwether_ingest/bee.py` invokes `bee conversations list/get/transcript`, `bee now`, `bee changed` with persisted cursors for exactly-once ingestion, parses `bee stream --json` events, and parses `bee sync` markdown. Thirty tests pin the exact argv of every invocation through an injected runner.

**The Bee integration goes further than the CLI.** Bee ships its own MCP server (`bee mcp serve-http`), and `apps/agent/context_check_in.py` consumes it alongside Bellwether's, so one agent holds both: Bellwether knows *that* speech changed and which measures moved, Bee knows the shape of those days. Neither can answer "is there an ordinary explanation for this?" alone. That agent turns the product's most important panel, the ordinary causes of a change, from something the worried person has to remember into something the system finds for them.

It is also where the privacy guarantee is most at risk, so it is enforced rather than promised. Bee's catalogue exposes verbatim speech (`bee_get_conversation_transcript`, `bee_search`, the voice-note tools) alongside derived context. The agent takes an **allowlist** of nine context tools and withholds everything else, with every speech tool named explicitly so the exclusion is auditable and an unknown tool excluded by default. Nine tests pin that boundary.

**Alexa+** is not a stretch. The track asks for a self-hosted MCP server implementing spec 2025-11-25 over Streamable HTTP, and `apps/server/bellwether_server/mcp.py` is exactly that, deployed and live, with seven tools and eighteen conformance and behaviour tests. The question a person actually asks about this product is spoken and casual ("how have I been sounding lately, and is it worth mentioning to the doctor?"), and answering it needs dependent reads and a judgement about whether to say anything, which is an agent's job. A Strands agent on Bedrock consumes the same server as an independent outside client with no data access of its own.

## Live

- Site, dashboard, printable doctor report: https://d1xfuyog8wiuvf.cloudfront.net
- API: https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws ([docs](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/v1/docs), [resilience](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/api/resilience))
- MCP server: `https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp`
- Repository (MIT): https://github.com/usv240/bellwether
- Demo video (under 3 minutes): YouTube link, add when published. Shot list with pre-flight commands, and what to do if the device does not arrive in time: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)

The person shown live is simulated and labelled as such on every surface that touches them. The extractor, engine, store, tiers, report and MCP server are the product.

## Shown on the site, not only claimed

Two things a visitor can press, both new, both mirroring a pattern proven in the sibling Nightlight project.

**The privacy claim, checked live.** Bellwether's premise is that it never holds what a person said. The privacy section now sends one day to the real intake route with an ordinary morning's transcript attached, full of a name, a doctor, a family member, an address, an account number and a medication, then reads back what the store kept and searches it for each one. Three text fields are dropped at the door, twelve fields are kept, the only string left is the date, and none of the six survive. It runs against a fresh in-memory store per press, so no visitor can write into the deployed table, and the page says so. `apps/server/tests/test_privacy_check.py` includes a test that deliberately makes the intake leak and asserts the check notices, because a check that always reports "absent" would prove nothing.

**Using it with your own Bee.** Five steps, each checked against the real CLI, and each badged by where the person's words are at that point: the first four on their own computer, only the fifth crossing the network, carrying nine numbers a day. The section says plainly that the device is on order and no real Bee day has been through the pipeline yet.

## Tech implementation

**179 tests**, passing from a clean clone with the documented install.

- **`speech-vitals` (MIT, the open-source deliverable).** Nine features, each carrying its literature citation and the direction the dementia-speech literature associates with decline, in code rather than in a paper. Deterministic: same text, same numbers, so any figure in a doctor report is reproducible from the day's transcript. The base package is dependency-free and imports anywhere, including a Lambda that only ever sees feature rows; extraction lives behind an `nlp` extra. A test asserts that a stored record holds no string but the date.
- **The engine.** Warmup, EWMA baseline, concern-signed z-scores, a standardised composite, one-sided CUSUM (k 0.5, h 5.0, expected false-alarm interval on the order of nine hundred days), per-feature CUSUMs for attribution only, low-exposure exclusion, and a **freeze** so the baseline cannot learn its way out of a signal. Nothing that decides a tier calls a model.
- **The Bee adapter.** Four ingestion paths, tolerant normalisation because the Bee docs name the fields but publish no full JSON example, owner isolation, and cursors saved only after features persist so processing is exactly-once.
- **The service.** FastAPI on Lambda behind a function URL. The public API accepts feature rows and **drops any field the schema does not know at the door**; a test posts a row containing a transcript and proves it never lands. Tiers, trends and reports are derived from stored rows on every read, never stored, so a summary cannot drift from the days that produced it.
- **Nothing fails into silence.** A three-model Bedrock ladder falls to a deterministic template that is the engine's own summary, so the weekly note degrades in warmth and never in accuracy, and every note reports which model wrote it. `/api/resilience` reports every degradation path.

## Design

100 on Lighthouse accessibility, best practices and SEO across all three pages. Light and dark themes applied before first paint, 22 info buttons, keyboard operable throughout, and the entire landing page prerendered so the case survives a failed fetch.

The design is grounded in the risk-communication literature, because this product shows health-adjacent numbers to people who may be frightened by them. Spiegelhalter's distinction governs it: **"we need to be clear about whether we are seeking to persuade, or fulfilling a duty to inform."** Bellwether informs, which rules out streak pressure, nudges, gamification and urgency language, and which produced the panel that matters most, `What else could explain this`, placed above the chart and giving the ordinary causes of a change the same visual weight as the change itself. Full reasoning in [DESIGN.md](DESIGN.md).

## Potential impact (the economics)

**The interval itself is the largest modifiable cost in this disease's early course.** A health-economic cohort model found that **net benefit falls by around 17 percent for every year intervention is delayed** (Barnett et al., *BMC Neurology*, 2014). The mean delay from first symptoms to diagnosis is **3.5 years**. Not the treatment, not the scan: the years before anyone looked.

The denominator: US dementia care costs $409 billion in 2026 before the 6.8 billion hours of unpaid family care worth $237 billion, with a lifetime cost of $405,262 per person, about 70 percent borne by families (Alzheimer's Association, 2026). The treatment window sits precisely inside the delay, since lecanemab and donanemab are approved **only** for mild cognitive impairment or mild dementia.

Bellwether costs **pennies per person per month** to run, on a $49.99 wristband people are buying anyway. Every existing speech-cognition tool is a scripted assessment delivered by a professional in a room, which is why none of them can run daily for two years. That is the whole reason this can exist.

Three things are true and separable, and we keep them separate: the delay costs about 17 percent a year (measured, by others); language features separate Alzheimer's from control speech at 85 to 89.6 percent on the field's benchmark (measured, by others); those features come out of ordinary wearable transcripts at pennies with no clinic (measured, by us, on synthetic personas through the production pipeline). **What connects them into a shortened delay is a trial nobody has run**, and saying so is more useful than a number we invented. [EVIDENCE.md](EVIDENCE.md) section 7.

## Quality of the idea

It reframes a fifty dollar note-taking gadget as a health instrument, using a signal the commercial products cannot reach. Every existing speech-based tool (Canary Speech, Winterlight) is a short scripted assessment administered in a clinic, because until wearables like Bee, nobody could collect natural, everyday, longitudinal speech at all. The n-of-1 design is what makes that data usable: it needs no population norms, no diagnosis, and no comparison with anyone.

## Open source

- Repository: https://github.com/usv240/bellwether (MIT, visible in About)
- GitHub username: usv240
- New open-source package: **`speech-vitals`**, a standalone MIT library with no dependency on this repository, [published on PyPI](https://pypi.org/project/speech-vitals/) (`pip install speech-vitals`). Nine language features per day from everyday speech transcripts, each documented with its literature basis, a dependency-free core, a CLI, and 25 tests. It is what the benchmark harness and the service both consume, which is what proves the library is real rather than extracted for show.

## AWS Builder

Amazon Bedrock (weekly note through a three-model ladder with a deterministic floor), the Strands Agents SDK (an agent consuming our own MCP server), DynamoDB (feature rows only, derived reads), Lambda with a function URL, S3, CloudFront and CDK. Each with its reason, and the two services we deliberately did **not** use with the reasons for that, in [AWS.md](AWS.md).

## Product feedback

Full version, tool by tool, in [PRODUCT_FEEDBACK.md](../PRODUCT_FEEDBACK.md): what each was used for, what worked, what needs work, how onboarding felt, and whether we would build with it again.

Summary. The **Bee CLI** surface is unusually clean and we would build on it again: every data command takes `--json`, list commands paginate with cursors, `bee changed` is exactly the primitive an incremental ingester wants, and `bee mcp serve-http` means an agent can read Bee context with no adapter at all. It installed and ran on Windows through npm without the docs promising it would. Three things need work, in order: no full JSON example for any command, so nesting and types are guessed until a device arrives; speakers are labelled but not identified, with no `is_user` flag, so isolating the wearer's own speech is a heuristic; and `bee sync` markdown carries no per-utterance timestamps. The single most useful change would be that one boolean.

**MCP** (spec 2025-11-25, Streamable HTTP) is precise about what is easy to get wrong, which is why eighteen conformance and tool tests came almost directly from reading it. The one thing that bit both sibling projects is not in the spec text: a real client sends `DELETE` with a JSON content-type and an empty body, and a naive body parser answers 500. **Strands** handed the agent every tool over Streamable HTTP with no adapter code, though tool-call failures surface as Python tracebacks rather than structured results.

On AWS we used **Bedrock** (the weekly note through a three-model Claude ladder with a deterministic floor, forbidden from adding, altering, diagnosing or predicting), **DynamoDB** (feature rows only, every tier and trend derived on read), **Lambda** behind a function URL, **S3** and **CloudFront**, and **CDK**. Our strongest AWS feedback is that a function URL's own CORS configuration silently collides with the handler's, producing two `Access-Control-Allow-Origin` headers that no command-line check can see and that break every browser call. The services we deliberately did not use, and why, are in [AWS.md](AWS.md).

## Friction log

Nine entries in [FRICTION_LOG.md](../FRICTION_LOG.md), each with task, steps, expected against actual, severity, workaround and an actionable suggestion. The ones we would most want read: Bee publishes no full JSON example for any command, so the ingestion normaliser had to guess shapes (entry 1); speakers are labelled but not identified, with no `is_user` flag, so isolating the wearer's own speech is a heuristic (entry 2); and a Lambda function URL with CORS plus FastAPI CORS middleware emits two `Access-Control-Allow-Origin` headers, which no command-line check can see and which broke every browser call on the deployed site (entry 6). There is also a deliberately positive entry for the Bee CLI running on Windows unannounced. Three of the nine are not about anyone else's product: entry 7 is our own dashboard hiding its most important panel behind a fetch, entry 8 is spaCy failing to import from a deep Windows path with an error that names the wrong cause, and entry 9 records that this server was already correct on the transport shape that broke the other two, which we only know because we probed all three.

## Feature requests (optional)

Nine, each from something we actually hit, each cross-referenced to the friction entry that produced it, and each rated critical, important or nice-to-have. The three we would most want read: Bee should expose an `is_user` flag on every utterance, because without it any analysis *of the wearer* rests on a heuristic (critical); AWS should warn when a Lambda function URL's CORS collides with the handler's own, because the resulting duplicate header is invisible to every non-browser check and breaks live demos (critical); and the MCP spec should state that real clients send `DELETE` with a JSON content-type and an empty body, which cost two of our three projects a 500 each. Full list with reasoning in [FEATURE_REQUESTS.md](FEATURE_REQUESTS.md).

## Real speech, not ours

Across **349 Supreme Court oral arguments by 8 justices** (ConvoKit, from the Oyez Project), speech nobody here wrote, Bellwether flagged **zero**. Paired with sensitivity so the zero means something: a sustained shift of 1.5 of a person's own standard deviations, injected into their real sessions, was caught in 5 of 5 subjects at a median of 2 sessions, and the do-nothing control at 0.0 caught nobody.

And the measured case for the design: on all nine features the gap between two different justices is smaller than one justice's own session-to-session range. Comparing a person with a population asks a detector to resolve a difference smaller than the noise it has to tolerate anyway.

No labelled cognitive change exists in that corpus, so none of this is evidence about dementia and none of it is offered as any. `harness/scotus/results.json`.

## The alternative, measured

Bellwether accumulates: a one-sided CUSUM on a concern-signed composite fires when deviation persists, not when a single day looks bad. Against the two rules a reasonable engineer writes instead, swept across eighteen settings, with every detector seeing identical features and an identical baseline so only the rule differs:

| Rule | False alarms on the unchanged person | Days into the change before it fires |
|---|---|---|
| **Bellwether** | **0** | **2** |
| Fixed composite threshold, quietest setting | 0 | 4 |
| Fixed composite threshold, fastest setting | 1 | 1 |
| Single-feature z threshold, best setting | 1 | 3 |

None of the eighteen beats it on both axes. Both personas are synthetic and ours, so this shows the decision rule earns its complexity, not that the detector works on a real person. `fixtures/detector-comparison.json`.

## Honest limits

- **The Bee device is on order.** Everything here runs and is tested without it, and the two synthetic personas exercise the production extractor and engine end to end. Real operation on the operator's own Bee data, and the demo video that shows it, wait on the hardware. The week-one gate questions are written and ready.
- **No ADReSS validation, and no harness for it.** The benchmark's data is restricted to verified academic researchers by application, we do not have that access, and nothing here is validated against it. ADReSS is cited as the field's evidence that language features carry the signal, and for nothing else.
- **No user testing.** Every design decision is reasoned from literature, not observed in a room with an older adult or a clinician.
- **English only**, stated in the FAQ rather than hidden.
