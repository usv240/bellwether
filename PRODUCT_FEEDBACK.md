# Product feedback

Draft of the submission's product-feedback answer, maintained as we build so it reflects real experience. Format per the rules: what we used it for, what worked well, what needs work, how onboarding felt, whether we would build with it again.

## Bee CLI (`@beeai/cli`) and the Bee developer surface

- Used for: every path Bee data takes into Bellwether. `bee conversations list`, `get` and `transcript` for history, `bee now` for the live view, `bee changed` with cursors for incremental exactly-once ingestion, `bee stream --json --types new-utterance` for real time, `bee sync` markdown as an offline path, and `bee stream --webhook-endpoint` as a way to push events into the deployed API. Every one of these is a real call site in `apps/ingest`, and a fake runner pins the exact argv of each in tests.
- Worked well: the command surface is unusually clean. Every data command takes `--json`, list commands paginate with `next_cursor` and `--cursor`, `bee changed` is exactly the primitive an incremental ingester wants, and the CLI doubling as an MCP server (`bee mcp serve-http`) means an agent can read Bee context with no adapter at all. It installed and ran on Windows via npm without the docs promising it would (FRICTION_LOG entry 4).
- Needs work, in order: no full JSON example for any command, so nesting and types are guessed until a device arrives (entry 1); speakers are labelled generically with no `is_user` flag, so isolating the wearer's own speech is a heuristic (entry 2); `bee sync` markdown has no per-utterance time (entry 3).
- Onboarding: `npm install -g @beeai/cli` and `bee status` is a two-minute start. Developer Mode is a five-tap on the app version number, which is fine once you know and invisible until you do; the docs say it, the app does not.
- Build again: yes. The surface is right; it needs examples and one boolean.

## Model Context Protocol (spec 2025-11-25, Streamable HTTP)

- Used for: the Alexa+ surface (`apps/server/bellwether_server/mcp.py`), a faithful port of the transport already proven in our two sibling projects.
- Worked well: the spec is precise about the things that are easy to get wrong (session issuance, 400 versus 404, the 405 allowance for GET, origin validation), so eighteen conformance and tool tests came almost directly from reading it.
- Needs work: the one thing that bit both sibling projects is not in the spec text: a real client sends DELETE with a JSON content-type and an empty body, and a naive body parser answers 500. Ported here as "DELETE never reads a body". A sentence in the transport section would have saved two bugs.
- Build again: yes, three times now.

## Strands Agents SDK

- Used for: the Speech Check-in agent (`apps/agent`), an outside client of our own MCP server, verified against the deployed endpoint.
- Worked well: `MCPClient` over Streamable HTTP plus `list_tools_sync` handed the agent all seven tools with no adapter code. The agent chained status, trend and report on its own and honoured a system prompt that forbids diagnosis, which is the constraint that matters most in this product.
- Needs work: tool-call failures surface as long Python tracebacks rather than structured results, which is hard to reason about mid-loop.
- Onboarding: `pip install strands-agents` and a `BedrockModel` was the whole setup.
- Build again: yes.

## Amazon Bedrock (Anthropic Claude)

- Used for: phrasing the weekly note from facts the engine computed, through a three-model ladder that falls to the deterministic template. The engine decides what happened; the model decides only how to say it, and may not add, alter, diagnose or predict.
- Worked well: verified live on the deployed stack. The first rung (Sonnet 4.5 via inference profile) answered cleanly, respected every rule in the prompt including the no-dashes and no-diagnosis constraints, and the response carried provenance (`model`, `attempts`) so a degraded note is explainable.
- Needs work: current-generation Claude models remain allowlist-gated on this account tier (see the Nightlight friction log, entry 5), which is why the ladder starts at Sonnet 4.5 rather than a current model.
- Build again: yes.

## Amazon DynamoDB, AWS Lambda, AWS CDK

- Used for: the feature-row store (raw rows only, tiers derived on read), the FastAPI service behind a function URL, and the stack as TypeScript.
- Worked well: the persona seeded itself into DynamoDB on the first live request; a single partition query serves a whole profile.
- Needs work: CDK's Python Lambda construct wants Docker for bundling. We built the asset without it by resolving manylinux wheels for CPython 3.12 with pip's `--platform` and `--only-binary` flags (`infra/build-lambda.mjs`), which works well and is under-documented. A first-class Docker-free option for pure-Python-plus-wheels services would remove a real obstacle on Windows.
- Build again: yes.

## spaCy and wordfreq (third-party, the feature extractor)

- Used for: part-of-speech tags, dependency parses and lemmas; Zipf word-frequency norms for the word-finding proxy.
- Worked well: the small English pipeline is fast enough to process 56 days of speech in seconds, and wordfreq's Zipf scale separates "the" (7.7) from "perambulate" (1.3) exactly as the feature needs.
- Needs work: a spaCy gotcha cost a hang and a killed process: `token.head` returns a fresh wrapper on every access, so an identity comparison at the root never terminates. Compare indices. Recorded here because it will bite the next person too.
- Build again: yes, in an isolated environment; installing spaCy into an Anaconda base environment on Windows disturbed an unrelated compiled package there.

## Still to record

- The Bee device itself: pairing, Developer Mode, first real `bee now --json` payload (which becomes a test fixture), speaker-label behaviour, sync latency, and rate limits. The week-one gate in TECHNICAL_DESIGN.md lists the questions.
