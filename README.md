# Bellwether

Your watch knows when your heart skips a beat. Nothing knows when your brain does. Bellwether makes speech a vital sign.

Built for the Build, Ship, Shape: Amazon Developer Hackathon. Track: Bee (Wearable AI). Mini challenges: AWS Builder, Open Source.

**Not a diagnosis.** Bellwether is a general wellness tool. It does not diagnose, treat, cure, or prevent any disease, and it is not a medical device. Changes in speech have many everyday causes, including sleep, stress, medication, and mood. It describes change over time in one person against their own past, lists its reasons, and produces something to put on a doctor's desk. Share it with a clinician you trust.

## What it does

Speech is the brain's only continuous, externally observable output, and when something changes it is usually where the change shows first: more pauses, simpler sentences, lost words. Clinicians know this, and they hear a patient for a few minutes a year. The Bee wristband already transcribes its wearer's day. Bellwether reads those transcripts, keeps the numbers and discards the words, learns how that one person normally speaks, and shows them, in numbers they own, when that changes.

## Status

Under construction, fixtures first, device second. What exists and is tested:

| Piece | What it is | Tests |
|---|---|---|
| `packages/speech-vitals` | The open-source feature package (MIT). Nine language features per day, each with its literature basis. Features only, never words. | 25 |
| `apps/engine` | The personal baseline: warmup, EWMA baseline, standardised composite, CUSUM drift detection, explainable tiers, a freeze so the baseline cannot learn its way out of a signal. No model in the loop. | 12 |
| `apps/ingest` | The Bee integration: `bee conversations`, `bee now`, `bee changed`, `bee stream --json`, `bee sync` markdown, owner isolation, exactly-once cursors. Tests pin the exact CLI argv without a device. | 30 |
| `fixtures/personas` | Two synthetic personas, one stable and one with a gradual change, run through the real extractor and real engine. Labelled SIMULATED in every file. | |

Coming: the dashboard and landing page, the doctor report, the MCP server (Alexa+ surface), the Bedrock-phrased weekly summary with a model ladder, DynamoDB persistence, a resilience endpoint, the evidence file, and live operation on a Bee device.

## Run what exists

```
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -e "packages/speech-vitals[dev]" -e "apps/engine[dev]" -e "apps/ingest[dev]"
python -m spacy download en_core_web_sm
pytest packages/speech-vitals apps/engine apps/ingest
python fixtures/personas/generate.py
```

Bee CLI: `npm install -g @beeai/cli`, enable Developer Mode in the Bee app (tap the version five times in Settings), then `bee login`. Everything above runs without it.

## Privacy, as architecture

Transcripts are reduced to features in memory and never written. A `DayFeatures` record holds no string but the date, and a test asserts it. The only file the ingestion layer writes is an opaque sync cursor.

## License

MIT.
