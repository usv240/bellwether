# Bellwether

Your watch knows when your heart skips a beat. Nothing knows when your brain does. Bellwether makes speech a vital sign.

Built for the Build, Ship, Shape: Amazon Developer Hackathon. Track: Bee (Wearable AI), with the MCP server as a genuine Alexa+ surface. Mini challenges: AWS Builder, Open Source.

**Not a diagnosis.** Bellwether is a general wellness tool. It does not diagnose, treat, cure, or prevent any disease, and it is not a medical device. Changes in speech have many everyday causes, including sleep, stress, medication, and mood. It describes change over time in one person against their own past, lists its reasons, and produces something to put on a doctor's desk. Share it with a clinician you trust.

## Live

- Site, dashboard and doctor report: https://d1xfuyog8wiuvf.cloudfront.net
- API: https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws ([interactive docs](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/v1/docs), [resilience report](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/api/resilience))
- MCP server (the Alexa+ surface): `https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp`, spec 2025-11-25 over Streamable HTTP, seven tools

The person on the live site is simulated and labelled as such everywhere. The extractor, the engine, the store, the tiers and the report are the product.

## What it does

Speech is the brain's only continuous, externally observable output, and when something changes it is usually where the change shows first: more pauses, simpler sentences, lost words. Clinicians know this, and they hear a patient for a few minutes a year. Across all dementias, the average time from first symptoms to diagnosis is **3.5 years** ([Orgeta et al., 2025](https://onlinelibrary.wiley.com/doi/10.1002/gps.70129)), and the newest treatments are approved only for the earliest stage.

The Bee wristband already transcribes its wearer's day. Bellwether reads those transcripts **on the wearer's own machine**, keeps nine numbers and discards the words, learns how that one person normally speaks, and shows them, in numbers they own, when that changes. Every claim on the site is sourced in [docs/EVIDENCE.md](docs/EVIDENCE.md).

## What is here

| Piece | What it is | Tests |
|---|---|---|
| [`packages/speech-vitals`](packages/speech-vitals) | The open-source feature package (MIT, dependency-free core). Nine language features per day, each with its literature basis and concerning direction. Features only, never words. | 25 |
| [`apps/engine`](apps/engine) | The personal baseline: warmup, EWMA baseline, concern-signed composite, CUSUM drift detection, explainable tiers, low-exposure exclusion, and a freeze so the baseline cannot learn its way out of a signal. No model in the loop. Includes the claims suite: every figure this repository states in public, re-derived from the committed personas. | 30 |
| [`apps/ingest`](apps/ingest) | The Bee integration, called in code: `bee conversations`, `bee now`, `bee changed` with exactly-once cursors, `bee stream --json`, `bee sync` markdown, owner isolation. | 30 |
| [`apps/server`](apps/server) | FastAPI: dashboard API, public features API, the MCP server, the Bedrock weekly note, the doctor report. Receives feature rows, never text. | 18 |
| [`apps/web`](apps/web) | Landing page, dashboard, printable doctor report. Light and dark, 22 info buttons, 100 on accessibility. | |
| [`apps/agent`](apps/agent) | Two Strands agents on Bedrock. One consumes Bellwether's MCP server as an outside client. The other holds **two** MCP servers at once, Bellwether's and Bee's own, to find the ordinary explanation for a change, behind an audited allowlist that withholds every Bee tool returning verbatim speech. | 9 |
| [`fixtures/personas`](fixtures/personas) | Two synthetic personas through the real extractor and engine, labelled SIMULATED. They share a seed and differ only in whether a change is injected from day 35, which is asserted, so the comparison is controlled. | |

**112 tests.** Run them: `pytest packages/speech-vitals apps/engine apps/ingest apps/server apps/agent`

## The properties worth arguing with

- **Features, never words.** The API accepts feature rows and drops any field the schema does not know at the door. A stored record holds no string but the date. Both are tests, not promises.
- **Your own baseline.** Bellwether never compares you with a population. An accent or a quiet manner is simply your normal.
- **Nothing that decides a tier calls a model.** Extraction is a tagger and parser; the engine is arithmetic. A reviewer can reproduce any tier from the day's features. A language model is allowed to phrase the weekly note and explain nothing else.
- **The baseline cannot learn its way out of a signal.** While drift is flagged, the baseline stops updating. Otherwise a slow real change becomes the new normal within weeks.
- **A quiet day is not a change in you.** Days below 150 words are excluded and drawn hollow.
- **Nothing fails into silence.** Three-model Bedrock ladder to a deterministic template; the catalogue and the store report their own degradation at [`/api/resilience`](https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/api/resilience).

## Run it

```
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -e "packages/speech-vitals[nlp,dev]" -e "apps/engine[dev]" -e "apps/ingest[dev]" -e "apps/server[dev]"
python -m spacy download en_core_web_sm
pytest packages/speech-vitals apps/engine apps/ingest apps/server apps/agent

python fixtures/personas/generate.py                # regenerate the personas
uvicorn bellwether_server.main:app --port 8789      # API + MCP on :8789
cd apps/web && npm install && npm run dev           # the site on :3000
```

On Windows, clone to a short path such as `C:/dev/bellwether`. spaCy's compiled parser fails to load from a deep directory and reports it as `DLL load failed ... The filename or extension is too long`, which names the wrong cause. FRICTION_LOG.md entry 8.

Bee: `npm install -g @beeai/cli`, enable Developer Mode in the Bee app (tap the version five times in Settings), then `bee login`. Everything above runs without it.

```
bellwether-ingest status
bellwether-ingest pull --owner speaker_1 --out days.json
curl -X POST $API/v1/profiles/me/days -H "content-type: application/json" -d @days.json
```

## Every number here is a test

[`apps/engine/tests/test_claims.py`](apps/engine/tests/test_claims.py) re-derives every published figure from the committed personas and checks it against the documents that state it. Two of its seventeen assertions do more than bookkeeping.

The personas share a seed, and the test asserts their feature values are identical up to the exact day the change is injected. Without that, the drift persona would not be evidence that the engine detects drift; it would be evidence that the engine can tell two people apart.

And the freeze is asserted against twenty days of real output: from the first non-stable day, every feature's baseline stops moving and never moves again. An adaptive baseline that keeps learning while it is signalling will absorb the change it was built to report and return to "stable" with nothing resolved. That failure is invisible in ordinary operation, which is exactly why it needs a test.

## Verify the live MCP server yourself

Opening an MCP URL in a browser shows an error, because the protocol is a POST with a session handshake. So there is a probe:

```
node scripts/mcp-conform.mjs            # this project's deployed server
node scripts/mcp-conform.mjs --all      # all three servers built for this hackathon
```

No install and no MCP client library: one dependency-free Node script against the deployed Lambda. It checks nineteen rules from spec revision 2025-11-25 over real HTTP, including the two shapes that in-process tests never produce: a DELETE carrying a JSON content-type and an empty body, and a body the server cannot parse.

The same file runs in all three repositories, which is the point of `--all`: this server is FastAPI on Python and the other two are Fastify on Node, and a conformance claim that has only ever met one implementation is a claim about that implementation. This one passes all nineteen on every run, including both shapes that the Node servers failed.

It grades what it checks. A MUST failure is a spec violation and exits non-zero; a SHOULD failure is reported and does not. Where the spec allows more than one answer, such as GET opening a stream or declining with 405, the probe accepts either and says which it saw. A conformance tool that grades its own preferences as violations teaches people to ignore it.

It has already paid for itself. Its first run across the three deployed Lambdas found that a malformed request body came back as an HTTP 500 carrying the framework's own error envelope, where JSON-RPC calls for a -32700 Parse error. Bellwether was already correct; the two Node servers were not, and every in-process test in both passed while the live servers were wrong. That is the whole argument for probing over real HTTP.

## Documentation

[SUBMISSION.md](docs/SUBMISSION.md) · [EVIDENCE.md](docs/EVIDENCE.md) (every claim with its source) · [DESIGN.md](docs/DESIGN.md) · [AWS.md](docs/AWS.md) · [ACCESSIBILITY.md](docs/ACCESSIBILITY.md) · [FEATURE_REQUESTS.md](docs/FEATURE_REQUESTS.md) · [FRICTION_LOG.md](FRICTION_LOG.md) · [PRODUCT_FEEDBACK.md](PRODUCT_FEEDBACK.md)

## Status

The device is on order. Everything above runs and is tested without it; the wristband gates the live footage and the week-one gate questions in the plan, not the build.

## License

MIT.
