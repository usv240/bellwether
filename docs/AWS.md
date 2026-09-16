# AWS Integrations

This file is the documented-integrations record for the AWS Builder mini challenge. Every service below is called from code in this repository, every design choice is stated with its reason, and every live claim was verified against the deployed stack.

Live: `https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/` (API), `/mcp` (Model Context Protocol), `/api/resilience` (every degradation path, reported).

## Amazon Bedrock (Anthropic Claude)

- Where: `apps/server/bellwether_server/bedrock.py`, exposed as `GET /v1/profiles/{id}/weekly-note`
- What for: phrasing the weekly note. The engine computes WHAT happened deterministically (tested in `apps/engine`); Claude on Bedrock decides only HOW TO SAY IT, warmly and in three sentences. The prompt forbids adding, removing or altering a fact, forbids diagnosis and prediction, and allows only suggestions the person can act on themselves.
- A ladder, not a model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, then Claude 3.5 Sonnet v2, then Claude 3.5 Haiku. If every rung fails, the deterministic template ships. It is the engine's own summary, so the note degrades in warmth and never in accuracy. Every response carries `model` and `attempts`. `BELLWETHER_MODEL_IDS` sets an explicit ladder; `BELLWETHER_MODEL_ID` names a preference and is prepended rather than replacing the ladder, so configuration cannot remove a safety net by accident.
- Verified live: the first rung answered on the deployed stack with full provenance, and the text honoured every rule (facts only, no diagnosis, second person, no dashes).
- The detection path never touches a model. Feature extraction is a tagger and parser; the baseline engine is arithmetic. A reviewer can reproduce any tier from the day's features.

## Strands Agents SDK

- Where: `apps/agent/speech_check_in.py`
- What for: the Speech Check-in agent, which answers the question a person actually asks ("how have I been sounding, and is it worth mentioning to the doctor?"). That needs dependent reads (status, then trend, then the report) and a judgement about whether to say anything, which is an agent's job.
- The design choice that matters: the agent has no data access. It is a second, independent client of the **same MCP server** Alexa+ would use. It gets seven tools and nothing else; there are no transcripts to give it. Verified against the deployed endpoint: it chained status, trend and report, opened with the simulated label, and suggested nothing beyond bringing the report to an appointment.
- Model: Claude on Amazon Bedrock. The safety boundary does not move because the output is a sentence.

## Amazon DynamoDB

- Where: `apps/server/bellwether_server/store.py` (`DynamoStore`), table in `infra/bin/app.ts`
- What for: raw day feature rows, annotations, spoken-check results and small metadata. Never text: the API drops any field the schema does not know at the door, and a test posts a row with a `transcript` field and proves it never lands.
- Layout: one on-demand table, partition key `PROFILE#{id}`, sort-key prefixes `DAY#`, `ANN#`, `CHECK#`, `META#`. A whole profile is one partition query.
- The design that matters: tiers, trends and reports are derived from the stored rows on every read by the pure engine, never stored, so nothing can drift from the days that produced it and a config change re-derives the whole history. Same principle as Nightlight's event log.
- Verified live: the simulated persona seeded itself into the table on the first request to the deployed API.

## AWS Lambda + function URL

- Where: `apps/server/bellwether_server/lambda.py` (Mangum), deployed by `infra/bin/app.ts`
- What for: the same FastAPI app that runs locally, behind a function URL with CORS that exposes `MCP-Session-Id` so a browser MCP client can read the session off the initialize response. Python 3.12, 512 MB, 30 s.
- Built without Docker: `infra/build-lambda.mjs` resolves manylinux x86_64 wheels for CPython 3.12 with pip's `--platform` and `--only-binary` flags for the compiled dependencies anthropic and fastapi pull in, adds our three pure-Python packages, and bundles the simulated persona. 21.8 MB. spaCy is deliberately absent: extraction runs where the transcript is, and only feature rows cross into this stack.

## Amazon S3 + CloudFront

- Where: `infra/bin/app.ts`, conditional on `apps/web/out` existing
- What for: the statically exported Next.js site (landing page, dashboard, doctor report). Private bucket with Origin Access Control; a CloudFront function rewrites extensionless paths to their directory index.

## AWS CDK

- Where: `infra/`
- What for: the whole stack as reviewable TypeScript. `npm run deploy` builds the Lambda asset and deploys.

## Deploy

```
cd infra && npm install
npm run deploy                                    # builds build/lambda, deploys API + table
# once the site is built (cd apps/web && NEXT_PUBLIC_API_URL=<ApiUrl> npm run build):
npm run deploy                                    # second pass publishes the site
```

## Cost posture

On-demand DynamoDB, one small Lambda, one CloudFront distribution, and Bedrock usage of a fraction of a cent per weekly note. Inside the free tier plus the hackathon's credits. A $10 monthly budget alert guards the account.

## What was deliberately not used

- SageMaker: nothing here trains a model. The benchmark harness is a scripted evaluation of a deterministic feature set, not a training job, and calling it SageMaker would be a checkbox rather than an integration.
- Amazon Transcribe and Polly: Bee already transcribes; Bellwether consumes features, not audio. If the week-one gate finds audio access, Transcribe's word-level timestamps would enable a pause and articulation module, and that is documented in TECHNICAL_DESIGN.md as the branch it is.
