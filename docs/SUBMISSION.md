# Bellwether: submission

## What it does

Your watch tracks your heart. What about the way you speak?

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

**On live data.** A Bee was bought for this and arrived on 2026-09-29.
`bellwether-ingest firstrun` walked the entire chain against it the same
day and stopped, honestly, at the first thing wrong: the CLI's shapes
differed from every fixture in three ways nobody had guessed (the list
carries counts and no words, `get` wraps its record, and utterance times
come as `spoken_at` beside offsets that parse as 1970). The parser was
fixed against the device, the shapes are pinned in
`apps/ingest/tests/test_device_shapes.py`, and the rehearsal then passed
every step: two conversations, one day, 393 words, nine numbers, no
words. [BEE_LIVE.md](BEE_LIVE.md) is the record, written by
`bellwether-ingest evidence`: counts, shapes and the nine features from a
real day of the operator's own speech, and not one word of it.

**Two streams of real data, labelled.** Fourteen days in, the device
had given 143 conversations and not one utterance with a speaker other
than "Unknown", even after the app enrolled the wearer's voice (friction
log entry 12, [bee-cli issue #19](https://github.com/bee-computer/bee-cli/issues/19)).
A personal baseline built on everyone within earshot is not a personal
baseline, so the live site now shows the wearer's Bee as two profiles
and says which is which. *My check-ins* starts from `bee journals`: a
note the wearer records on purpose, so the speaker is certain by
construction. On the device a note ends after a sentence (friction log
entry 16), so the check-in is the band's session the wearer declares
theirs: either by a note it opens with, or by opening it out loud,
"Bellwether check-in" or "vlog for October 17" (entry 17). The next ten
minutes at most, the wearer talking to the band alone. `bellwether-ingest pull --checkins` reads it and posts to a
profile of its own. *My conversations* is the band's everyday ambient speech with
sessions over an hour and anything Bee calls media left out, which is a
filter and is described as one. The simulated person stays, labelled,
because a baseline that has never moved cannot show what moving looks
like. The dashboard switches between the three in one row. The external validation in `harness/scotus` is real
human speech, but it is Supreme Court audio rather than Bee audio, and it
is offered as evidence about the engine rather than about the device.

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

**A second opinion, argued.** When a change is flagged, `apps/agent/second_opinion.py` runs three Strands agents on Amazon Bedrock over the evidence from the `weigh_the_change` MCP tool, which lists numbered items for a real change (C1...) and for an ordinary week (O1...), computed from the engine's numbers with no model. An Advocate argues the change is real, a Sceptic argues the everyday explanations, and a Referee writes the note. The note passes a gate before anyone sees it: it must cite both sides, use no number outside the evidence (numbers written as words included, and none rounded), and name no condition. A refused note gets one retry with the reason; if that fails too, a note built from the evidence alone is shown. A real run is committed at `apps/agent/runs/second-opinion-alex-drift.json` and shown on the simulated person's dashboard, and the same agents are deployed on Amazon Bedrock AgentCore Runtime as an endpoint anything can invoke (`apps/agentcore`).

**Alexa+** is not a stretch. The track asks for a self-hosted MCP server implementing spec 2025-11-25 over Streamable HTTP, and `apps/server/bellwether_server/mcp.py` is exactly that, deployed and live, with ten tools and thirty-one conformance and behaviour tests. Two of the ten make the assistant a participant rather than a reader: `start_check_in` returns tonight's exact lines for a voice assistant to speak (an opener that declares the session a check-in, three standard elicitation prompts rotated by date, a closing), and `coaching_note` returns what to tell the person after, built only from the engine's numbers. `apps/agent/check_in_host.py` runs that loop end to end: it speaks through Amazon Polly while the Bee on the wrist records, waits for the Bee to write the session down, counts the day on the wearer's computer with the host's own lines removed, and reads the note back. Bee alongside a speaker, which is the shape the organisers' brief asks for. The rule asks for it **in action**, so the **Ask Alexa+ how you have been sounding** section of the live site holds a complete session from the visitor's own browser against the deployed server: protocol 2025-11-25 agreed, the handshake finished, ten tools listed, `get_speech_vitals` called, and the session closed with a 204. Every row is the server's own answer, and the tier it returns is the same one the dashboard above it shows, because the assistant reads the same profile rather than a copy made for the panel. The question a person actually asks about this product is spoken and casual ("how have I been sounding lately, and is it worth mentioning to the doctor?"), and answering it needs dependent reads and a judgement about whether to say anything, which is an agent's job. A Strands agent on Bedrock consumes the same server as an independent outside client with no data access of its own.

## Live

- Site, dashboard, printable doctor report: https://d1xfuyog8wiuvf.cloudfront.net
- API: https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws ([docs](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/v1/docs), [resilience](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/api/resilience))
- MCP server: `https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp`
- Repository (MIT): https://github.com/usv240/bellwether
- Demo video (under 3 minutes): YouTube link, add when published. Shot list with pre-flight commands, and what to do if the device does not arrive in time: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md)

The dashboard opens on a simulated person, labelled as such on every surface that touches them, and switches in one row to two profiles of real Bee data from the builder's own band: voice notes, whose speaker is certain, and everyday conversations, whose speaker is not. The extractor, engine, store, tiers, report and MCP server are the product.

## Shown on the site, not only claimed

Two things a visitor can press, both new, both mirroring a pattern proven in the sibling Nightlight project.

**The privacy claim, checked live.** Bellwether's premise is that it never holds what a person said. The privacy section now sends one day to the real intake route with an ordinary morning's transcript attached, full of a name, a doctor, a family member, an address, an account number and a medication, then reads back what the store kept and searches it for each one. Three text fields are dropped at the door, twelve fields are kept, the only string left is the date, and none of the six survive. It runs against a fresh in-memory store per press, so no visitor can write into the deployed table, and the page says so. `apps/server/tests/test_privacy_check.py` includes a test that deliberately makes the intake leak and asserts the check notices, because a check that always reports "absent" would prove nothing.

**Without a Bee.** `bellwether-ingest file` reads the transcripts people already have, Zoom or Teams WebVTT, Otter text exports, or plain `Name: text` lines, lists the speakers by words spoken, and keeps only the named person's turns before reducing each day to the same nine numbers. Meeting transcripts name who said what, which the Bee does not yet do, so this path has the wearer's own speech by construction. Six tests, one of which asserts no word of anyone's speech reaches the output.

**Using it with your own Bee.** One command, `bellwether-ingest mine --profile <your-name>`, with the five steps it performs listed beneath it and each badged by where the person's words are at that point: on their own computer until the last, which carries nine numbers a day. On the first run it claims the two profiles with a key made on the wearer's machine; only the key's hash is stored, so from then on nobody else can post a day as them, add a note to their record, or log a check, and the demo profile stays open on purpose. The dashboard asks for the key once, keeps it in that browser only, and sends it as a header, never in a URL. The section says plainly that Bee does not yet tell speakers apart, and that the wearer's stream is the check-ins they declare theirs.

## Tech implementation

**290 tests**, passing from a clean clone with the documented install.

- **`speech-vitals` (MIT, the open-source deliverable).** Nine features, each carrying its literature citation and the direction the dementia-speech literature associates with decline, in code rather than in a paper. Deterministic: same text, same numbers, so any figure in a doctor report is reproducible from the day's transcript. The base package is dependency-free and imports anywhere, including a Lambda that only ever sees feature rows; extraction lives behind an `nlp` extra. A test asserts that a stored record holds no string but the date.
- **The engine.** Warmup, EWMA baseline, concern-signed z-scores, a standardised composite, one-sided CUSUM (k 0.5, h 5.0, expected false-alarm interval on the order of nine hundred days), per-feature CUSUMs for attribution only, low-exposure exclusion, and a **freeze** so the baseline cannot learn its way out of a signal. Nothing that decides a tier calls a model.
- **The Bee adapter.** Four ingestion paths, tolerant normalisation because the Bee docs name the fields but publish no full JSON example, owner isolation when Bee labels the wearer (on our band every speaker reads Unknown, so long sessions and media are filtered instead; friction log entry 12), a full-history backfill, and cursors saved only after features persist so processing is exactly-once. Since 2026-10-13 the wearer's check-ins are a stream of their own, the one whose speaker is as certain as the device allows: the voice note that anchors them is the wearer by construction, and the band's session that opens with the note's words is the rest. Posted straight from `pull --checkins --post`.
- **The service.** FastAPI on Lambda behind a function URL. Reads are open; writes to a claimed profile need its key (`POST /v1/profiles/{id}/claim` once, `X-Bellwether-Key` thereafter, sha256 at rest, constant-time compare; first claim wins; the demo profile cannot be claimed). The public API accepts feature rows and **drops any field the schema does not know at the door**; a test posts a row containing a transcript and proves it never lands. Tiers, trends and reports are derived from stored rows on every read, never stored, so a summary cannot drift from the days that produced it.
- **Nothing fails into silence.** A three-model Bedrock ladder falls to a deterministic template that is the engine's own summary, so the weekly note degrades in warmth and never in accuracy, and every note reports which model wrote it. `/api/resilience` reports every degradation path.

## Design

100 on Lighthouse accessibility, best practices and SEO across all three pages. Light and dark themes applied before first paint, 22 info buttons, keyboard operable throughout, and the entire landing page prerendered so the case survives a failed fetch.

**The interaction model is the device's.** A band on a wrist and an app with a record button, so the wearer's whole job is two minutes of talking a day. Day one is one command, `bellwether-ingest mine`, which reads the Bee, keeps nine numbers a day on the wearer's machine, sends only those and opens their page, in the Bee app's own words if something is missing. If a day is short, `--remind` puts the ask where the wearer will see it: a todo on their own Bee. The dashboard's first week is a product rather than an absence: seven slots, today's words against the 150-word floor, how many more minutes of talking would make the day count, what happens on day eight, and a link to the simulated person for what done looks like. The landing page walks the week (day one, every day, day eight, any day, appointment day) so a judge can see the whole loop before pressing anything.

The design is grounded in the risk-communication literature, because this product shows health-adjacent numbers to people who may be frightened by them. Spiegelhalter's distinction governs it: **"we need to be clear about whether we are seeking to persuade, or fulfilling a duty to inform."** Bellwether informs, which rules out streak pressure, nudges, gamification and urgency language, and which produced the panel that matters most, `What else could explain this`, placed above the chart and giving the ordinary causes of a change the same visual weight as the change itself. Full reasoning in [DESIGN.md](DESIGN.md).

## Potential impact (the economics)

**The interval itself is the largest modifiable cost in this disease's early course.** A health-economic cohort model found that **net benefit falls by around 17 percent for every year intervention is delayed** (Barnett et al., *BMC Neurology*, 2014). The mean delay from first symptoms to diagnosis is **3.5 years**. Not the treatment, not the scan: the years before anyone looked.

The denominator: US dementia care costs $409 billion in 2026 before the 6.8 billion hours of unpaid family care worth $237 billion, with a lifetime cost of $405,262 per person, about 70 percent borne by families (Alzheimer's Association, 2026). The treatment window sits precisely inside the delay, since lecanemab and donanemab are approved **only** for mild cognitive impairment or mild dementia.

Bellwether costs **pennies per person per month** to run, on a $49.99 wristband people are buying anyway. The live site now says who it is for in their own situations (the person who has started to wonder, the family member who notices first on the phone, the clinician with twelve minutes), gives the economics in four sourced numbers, and names the three ways it leaves the hackathon: a family at home with one command, a memory clinic deploying the stack into its own account between annual visits with only nine numbers a day reaching it, and any transcript source at all, since `speech-vitals` reads any speaker-labelled transcript. Every existing speech-cognition tool is a scripted assessment delivered by a professional in a room, which is why none of them can run daily for two years. That is the whole reason this can exist.

Three things are true and separable, and we keep them separate: the delay costs about 17 percent a year (measured, by others); language features separate Alzheimer's from control speech at 85 to 89.6 percent on the field's benchmark (measured, by others); those features come out of ordinary wearable transcripts at pennies with no clinic (measured, by us, on synthetic personas through the production pipeline). **What connects them into a shortened delay is a trial nobody has run**, and saying so is more useful than a number we invented. So the trial is written: [PILOT.md](PILOT.md) is a twelve-month, single-clinic, forty-person feasibility protocol with its endpoints fixed before any data (adherence and retention first, then agreement with the clinic's own assessment, the false-alarm rate on real people, and whether the report changed what a clinician asked), pre-specified kill criteria, a sample-size statement that refuses to claim sensitivity, and a cost of about two thousand dollars in hardware. It involves no one yet. [EVIDENCE.md](EVIDENCE.md) section 7.

## Quality of the idea

It reframes a fifty dollar note-taking gadget as a health instrument, using a signal the commercial products cannot reach. Every existing speech-based tool (Canary Speech, Winterlight) is a short scripted assessment administered in a clinic, because until wearables like Bee, nobody could collect natural, everyday, longitudinal speech at all. The n-of-1 design is what makes that data usable: it needs no population norms, no diagnosis, and no comparison with anyone.

## Open source

- Repository: https://github.com/usv240/bellwether (MIT, visible in About)
- GitHub username: usv240
- New open-source package: **`speech-vitals`**, a standalone MIT library with no dependency on this repository, [published on PyPI](https://pypi.org/project/speech-vitals/) (`pip install speech-vitals`). Nine language features per day from everyday speech transcripts, each documented with its literature basis, a dependency-free core, a CLI, and 35 tests. It is what the benchmark harness and the service both consume, which is what proves the library is real rather than extracted for show.
- Contribution to Bee's own CLI: [bee-computer/bee-cli PR #20](https://github.com/bee-computer/bee-cli/pull/20) adds `bee conversations list --all`, which follows `next_cursor` to the end and returns a whole history in one command, with four tests and the existing suite passing (315 pass), and one round of review feedback addressed. Written after a first pull of nine days returned two. The companion [issue #19](https://github.com/bee-computer/bee-cli/issues/19) reports that every speaker comes back `Unknown` and proposes a backwards-compatible fix.

## AWS Builder

Amazon Bedrock (weekly note through a three-model ladder with a deterministic floor), the Strands Agents SDK (an agent consuming our own MCP server), DynamoDB (feature rows only, derived reads), Lambda with a function URL, S3, CloudFront and CDK. Each with its reason, and the two services we deliberately did **not** use with the reasons for that, in [AWS.md](AWS.md).

## Product feedback

Full version, tool by tool, in [PRODUCT_FEEDBACK.md](../PRODUCT_FEEDBACK.md): what each was used for, what worked, what needs work, how onboarding felt, and whether we would build with it again.

Summary. The **Bee CLI** surface is unusually clean and we would build on it again: every data command takes `--json`, list commands paginate with cursors, `bee changed` is exactly the primitive an incremental ingester wants, and `bee mcp serve-http` means an agent can read Bee context with no adapter at all. It installed and ran on Windows through npm without the docs promising it would. Three things need work, in order: no full JSON example for any command, so nesting and types are guessed until a device arrives; every speaker comes back `Unknown`, even after the app enrols the wearer's voice, so the wearer's own speech cannot be isolated (reported as [issue #19](https://github.com/bee-computer/bee-cli/issues/19), with a proposed fix); and `bee sync` markdown carries no per-utterance timestamps. The single most useful change would be that one boolean.

**MCP** (spec 2025-11-25, Streamable HTTP) is precise about what is easy to get wrong, which is why thirty-one conformance and behaviour tests came almost directly from reading it. One of them exists because we got it wrong: the DNS-rebinding guidance to validate `Origin` produced a loopback-only check here, and the deployed server answered its own website with a 403 the first time a browser held a session with it. The one thing that bit both sibling projects is not in the spec text: a real client sends `DELETE` with a JSON content-type and an empty body, and a naive body parser answers 500. **Strands** handed the agent every tool over Streamable HTTP with no adapter code, though tool-call failures surface as Python tracebacks rather than structured results.

On AWS we used **Bedrock** (the weekly note through a three-model Claude ladder with a deterministic floor, forbidden from adding, altering, diagnosing or predicting), **DynamoDB** (feature rows only, every tier and trend derived on read), **Lambda** behind a function URL, **S3** and **CloudFront**, and **CDK**. Our strongest AWS feedback is that a function URL's own CORS configuration silently collides with the handler's, producing two `Access-Control-Allow-Origin` headers that no command-line check can see and that break every browser call. The services we deliberately did not use, and why, are in [AWS.md](AWS.md).

## Friction log

Nineteen entries in [FRICTION_LOG.md](../FRICTION_LOG.md), each with task, steps, expected against actual, severity, workaround and an actionable suggestion. The one we would most want read is entry 12, written after nine days on the wrist: every one of 15,578 utterances is labelled "Unknown", so a product about the wearer's own speech cannot find the wearer, even after the app confirmed the wearer's voice was enrolled, and the fix Bee could ship is carrying that enrolment through to the developer data as a wearer flag. Entry 13 is its quieter companion: `bee changed` without a cursor returns recent changes only, so the first pull of a nine-day history came back with two days. Entry 16 found that a Bee voice note ends after a sentence, and answers it with the check-in: the note proves who started the session, the band's session that opens with the note's words is the rest. Entry 18 is ours and the spec's: MCP sessions kept in one Lambda instance's memory failed the moment Lambda scaled, found mid-recording and fixed in all four servers with signed ids. Entry 17 adds the anchor the wearer actually uses, a spoken opener, after two declared days were dropped for lack of a note. Entry 19 is what a second device in the room costs: the Bee hears the host too, nothing marks its words as not the wearer's, so the host's script is published and removed before measuring. Entry 15 is ours: a static prerender cannot see the URL, so every real-data page hydrated with a mismatch only Lighthouse's console audit caught. Entry 14 is the answer we found ourselves: a Bee voice note is the wearer's own speech by construction, which the docs never say, and it now carries the wearer's profile at the price of two minutes of deliberate talking a day. Before the device: Bee publishes no full JSON example for any command, so the ingestion normaliser had to guess shapes (entry 1); speakers are labelled but not identified, with no `is_user` flag, so isolating the wearer's own speech is a heuristic (entry 2); and a Lambda function URL with CORS plus FastAPI CORS middleware emits two `Access-Control-Allow-Origin` headers, which no command-line check can see and which broke every browser call on the deployed site (entry 6). There is also a deliberately positive entry for the Bee CLI running on Windows unannounced. Three of the earlier entries are about us, not anyone else's product: entry 7 is our own dashboard hiding its most important panel behind a fetch, entry 8 is spaCy failing to import from a deep Windows path with an error that names the wrong cause, and entry 9 records that this server was already correct on the transport shape that broke the other two, which we only know because we probed all three. Entry 10 is the newest and also ours: the spec's DNS-rebinding guidance says to validate `Origin` and does not say that a server which serves its own browser client must allow that client in, so ours answered its own front page with a 403 the first time anyone opened it in a browser.

## Feature requests (optional)

Ten, each from something we actually hit, each cross-referenced to the friction entry that produced it, and each rated critical, important or nice-to-have. The three we would most want read: Bee should expose an `is_user` flag on every utterance, because without it any analysis *of the wearer* rests on a heuristic (critical); AWS should warn when a Lambda function URL's CORS collides with the handler's own, because the resulting duplicate header is invisible to every non-browser check and breaks live demos (critical); and the MCP spec should state that real clients send `DELETE` with a JSON content-type and an empty body, which cost two of our three projects a 500 each. Full list with reasoning in [FEATURE_REQUESTS.md](FEATURE_REQUESTS.md).

## Real speech, not ours

**Five real people over years, run unchanged.** Every press conference of five presidents from the public record, only each president's own words. On the four with no known dementia diagnosis, 18 of 652 conferences were flagged (2.8 percent): five of George H. W. Bush's six in one week of an overseas trip in July 1991, all twelve of Clinton's in his last eighteen months, and none at all for George W. Bush or Obama across eight years each. Reagan, the famous case the field now disputes, was not flagged. Rare, clustered on a change of setting, and called "watch": the behaviour the product claims, measured on real people. The first run had a parser bug that hid six of those flags; EVIDENCE.md section 4d records it.

Across **349 oral-argument sessions of 8 Supreme Court justices** (ConvoKit, from the Oyez Project), speech nobody here wrote, Bellwether flagged **zero**. Paired with sensitivity so the zero means something: a sustained shift of 1.5 of a person's own standard deviations, injected into their real sessions, was caught in 5 of 5 subjects at a median of 2 sessions, and the do-nothing control at 0.0 caught nobody.

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

- **Bee does not yet say who was speaking.** Every utterance from fourteen days on the wrist is labelled "Unknown" (friction log entry 12, reported upstream). The conversation profile is therefore the band's surroundings with long sessions and media filtered out, not the wearer alone, and the site says so beside it. The wearer's own speech comes from check-ins: a voice note proves who started the session, and the session is the wearer talking alone to the band. Anyone else speaking in those minutes would be counted too; the wearer keeps it to themselves. It costs about two minutes a day, so that profile has fewer days than the band has been worn.
- **The simulated person still carries the demonstration of change.** The real profiles are stable, which is the expected and honest result for a healthy wearer over three weeks, and a baseline that has not moved cannot show what the watch and discuss tiers look like.
- **No ADReSS validation, and no harness for it.** The benchmark's data is restricted to verified academic researchers by application, we do not have that access, and nothing here is validated against it. ADReSS is cited as the field's evidence that language features carry the signal, and for nothing else.
- **No user testing.** Every design decision is reasoned from literature, not observed in a room with an older adult or a clinician.
- **English only**, stated in the FAQ rather than hidden.

## Built with

Bee CLI; Bee's own MCP server; MCP server, spec 2025-11-25, Streamable HTTP; Agent Skill; Amazon Bedrock (Claude); Strands Agents SDK; Amazon Bedrock AgentCore Runtime; Amazon Polly; Amazon DynamoDB, AWS Lambda, Amazon S3, Amazon CloudFront, AWS CDK; PyPI. Each, with the file that uses it, is in the README's Built with table.
