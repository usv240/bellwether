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

## Tracks and mini challenges

**Bee (primary) and Alexa+.** AWS Builder and Open Source mini challenges.

The rules cap winnings rather than entries: "each project can only win one track prize and one mini challenge prize."

**Bee** is the primary track. The repository calls the Bee developer tooling in code, not in a README: `apps/ingest/bellwether_ingest/bee.py` invokes `bee conversations list/get/transcript`, `bee now`, `bee changed` with persisted cursors for exactly-once ingestion, parses `bee stream --json` events, and parses `bee sync` markdown. Thirty tests pin the exact argv of every invocation through an injected runner.

**Alexa+** is not a stretch. The track asks for a self-hosted MCP server implementing spec 2025-11-25 over Streamable HTTP, and `apps/server/bellwether_server/mcp.py` is exactly that, deployed and live, with seven tools and eighteen conformance and behaviour tests. The question a person actually asks about this product is spoken and casual ("how have I been sounding lately, and is it worth mentioning to the doctor?"), and answering it needs dependent reads and a judgement about whether to say anything, which is an agent's job. A Strands agent on Bedrock consumes the same server as an independent outside client with no data access of its own.

## Live

- Site, dashboard, printable doctor report: https://d1xfuyog8wiuvf.cloudfront.net
- API: https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws ([docs](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/v1/docs), [resilience](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/api/resilience))
- MCP server: `https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp`
- Repository (MIT): https://github.com/usv240/bellwether
- Demo video (under 3 minutes): YouTube link, add when published. Shot list with pre-flight commands, and what to do if the device does not arrive in time: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)

The person shown live is simulated and labelled as such on every surface that touches them. The extractor, engine, store, tiers, report and MCP server are the product.

## Tech implementation

**86 tests**, passing from a clean clone with the documented install.

- **`speech-vitals` (MIT, the open-source deliverable).** Nine features, each carrying its literature citation and the direction the dementia-speech literature associates with decline, in code rather than in a paper. Deterministic: same text, same numbers, so any figure in a doctor report is reproducible from the day's transcript. The base package is dependency-free and imports anywhere, including a Lambda that only ever sees feature rows; extraction lives behind an `nlp` extra. A test asserts that a stored record holds no string but the date.
- **The engine.** Warmup, EWMA baseline, concern-signed z-scores, a standardised composite, one-sided CUSUM (k 0.5, h 5.0, expected false-alarm interval on the order of nine hundred days), per-feature CUSUMs for attribution only, low-exposure exclusion, and a **freeze** so the baseline cannot learn its way out of a signal. Nothing that decides a tier calls a model.
- **The Bee adapter.** Four ingestion paths, tolerant normalisation because the Bee docs name the fields but publish no full JSON example, owner isolation, and cursors saved only after features persist so processing is exactly-once.
- **The service.** FastAPI on Lambda behind a function URL. The public API accepts feature rows and **drops any field the schema does not know at the door**; a test posts a row containing a transcript and proves it never lands. Tiers, trends and reports are derived from stored rows on every read, never stored, so a summary cannot drift from the days that produced it.
- **Nothing fails into silence.** A three-model Bedrock ladder falls to a deterministic template that is the engine's own summary, so the weekly note degrades in warmth and never in accuracy, and every note reports which model wrote it. `/api/resilience` reports every degradation path.

## Design

100 on Lighthouse accessibility, best practices and SEO across all three pages. Light and dark themes applied before first paint, 22 info buttons, keyboard operable throughout, and the entire landing page prerendered so the case survives a failed fetch.

The design is grounded in the risk-communication literature, because this product shows health-adjacent numbers to people who may be frightened by them. Spiegelhalter's distinction governs it: **"we need to be clear about whether we are seeking to persuade, or fulfilling a duty to inform."** Bellwether informs, which rules out streak pressure, nudges, gamification and urgency language, and which produced the panel that matters most, `What else could explain this`, placed above the chart and giving the ordinary causes of a change the same visual weight as the change itself. Full reasoning in [DESIGN.md](DESIGN.md).

## Potential impact

The gap is measured in years, the treatment window sits inside it, and the appointment that decides everything is twelve minutes long and mostly forgotten. Bellwether does not close that gap; it puts evidence in the patient's hand at the start of it.

The addressable population is not niche. Dementia prevalence rises with an ageing population, and the second use is broader still: medication fog, sleep, illness and recovery all show in speech, which means a healthy person has a reason to build a baseline long before anyone needs it. Every figure is sourced in [EVIDENCE.md](EVIDENCE.md), including the ones that did not survive checking.

## Quality of the idea

It reframes a fifty dollar note-taking gadget as a health instrument, using a signal the commercial products cannot reach. Every existing speech-based tool (Canary Speech, Winterlight) is a short scripted assessment administered in a clinic, because until wearables like Bee, nobody could collect natural, everyday, longitudinal speech at all. The n-of-1 design is what makes that data usable: it needs no population norms, no diagnosis, and no comparison with anyone.

## Open source

- Repository: https://github.com/usv240/bellwether (MIT, visible in About)
- GitHub username: usv240
- New open-source package: **`speech-vitals`**, a standalone MIT library with no dependency on this repository. Nine language features per day from everyday speech transcripts, each documented with its literature basis, a dependency-free core, a CLI, and 25 tests. It is what the benchmark harness and the service both consume, which is what proves the library is real rather than extracted for show.

## AWS Builder

Amazon Bedrock (weekly note through a three-model ladder with a deterministic floor), the Strands Agents SDK (an agent consuming our own MCP server), DynamoDB (feature rows only, derived reads), Lambda with a function URL, S3, CloudFront and CDK. Each with its reason, and the two services we deliberately did **not** use with the reasons for that, in [AWS.md](AWS.md).

## Friction log

Six entries with task, steps, expected against actual, severity, workaround and an actionable suggestion. The ones we would most want read: Bee publishes no full JSON example for any command, so the ingestion normaliser had to guess shapes (entry 1); speakers are labelled but not identified, with no `is_user` flag, so isolating the wearer's own speech is a heuristic (entry 2); and a Lambda function URL with CORS plus FastAPI CORS middleware emits two `Access-Control-Allow-Origin` headers, which no command-line check can see and which broke every browser call on the deployed site (entry 6). There is also a deliberately positive entry for the Bee CLI running on Windows unannounced.

## Feature requests (optional)

Eight, each from something we actually hit, each cross-referenced to the friction entry that produced it, and each rated critical, important or nice-to-have. The three we would most want read: Bee should expose an `is_user` flag on every utterance, because without it any analysis *of the wearer* rests on a heuristic (critical); AWS should warn when a Lambda function URL's CORS collides with the handler's own, because the resulting duplicate header is invisible to every non-browser check and breaks live demos (critical); and the MCP spec should state that real clients send `DELETE` with a JSON content-type and an empty body, which cost two of our three projects a 500 each. Full list with reasoning in [FEATURE_REQUESTS.md](FEATURE_REQUESTS.md).

## Honest limits

- **The Bee device is on order.** Everything here runs and is tested without it, and the two synthetic personas exercise the production extractor and engine end to end. Real operation on the operator's own Bee data, and the demo video that shows it, wait on the hardware. The week-one gate questions are written and ready.
- **ADReSS validation is not published.** The benchmark harness is written and runnable, but the data is restricted to verified academic researchers by application. Numbers will be published only if that access is obtained. Saying so is better than a table nobody can reproduce.
- **No user testing.** Every design decision is reasoned from literature, not observed in a room with an older adult or a clinician.
- **English only**, stated in the FAQ rather than hidden.
