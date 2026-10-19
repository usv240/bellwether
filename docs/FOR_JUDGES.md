# Bellwether, for judges

Every requirement in the hackathon rules and every judging criterion,
with the file, command or link that proves it. Written to be checked,
not believed. Every published number is re-derived by a test.

**In one line:** Bellwether uses the Bee on your wrist to learn how you
normally speak, compares you only with your own past, keeps nine numbers
a day and never the words, and gives you a clear page for your doctor
when something changes. It is not a diagnosis.

**Live:** site https://d1xfuyog8wiuvf.cloudfront.net · the builder's own
check-ins https://d1xfuyog8wiuvf.cloudfront.net/app/?profile=me-voice ·
API docs https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/v1/docs
· MCP https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp

## Submission requirements

| Requirement | Met by | Check it |
|---|---|---|
| Text description of what it does and how | Devpost text; [SUBMISSION.md](SUBMISSION.md) | Read |
| Public repository with all source, assets and run instructions | This repository; [README.md](../README.md), "Run it" | Clone, then `pytest packages/speech-vitals apps/engine apps/ingest apps/server apps/agent` |
| Open-source licence visible at the top | MIT, [LICENSE](../LICENSE) | The About panel |
| **Bee: the repo calls Bee's CLI, MCP or Skill in code** | `apps/ingest/bellwether_ingest/bee.py` runs `bee conversations list` and `get`, `now`, `changed`, `journals list` and `todos create`, and reads `bee stream --json` and `bee sync` output; every argv pinned in tests. `apps/agent/context_check_in.py` holds Bee's own MCP server behind an audited allow-list | `pytest apps/ingest apps/agent` |
| **Bee: live Bee data doing something for a user** | The builder's own check-ins since 2026-10-15, counted from the Bee: three days so far, the latest 298 words (2026-10-19). The hosted check-in ran live on 2026-10-19: an assistant asked three questions out loud, the Bee recorded the answers, the assistant's own words were removed by timing, the day was counted and the coaching note read back | The live dashboard above; [FRICTION_LOG.md](../FRICTION_LOG.md) entry 19 |
| **Alexa+: MCP server, spec 2025-11-25, Streamable HTTP, in action** | Self-hosted MCP server with ten tools, two of which host the check-in; an Agent Skill at [skills/bellwether/SKILL.md](../skills/bellwether/SKILL.md); a live session from the site; a conformance probe over real HTTP | `node scripts/mcp-conform.mjs` (12 of 12 MUST, 7 of 7 SHOULD) |
| Demo video under three minutes | To be recorded last; the script is [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md), generated from the beats the recorder reads | |
| Product feedback on every tool used | [PRODUCT_FEEDBACK.md](../PRODUCT_FEEDBACK.md) and the Devpost feedback answers, Bee CLI to Amazon Polly | Read |
| Tracks and mini challenges | Bee (primary), Alexa+; AWS Builder; Open Source | [SUBMISSION.md](SUBMISSION.md) |
| Open Source fields | `speech-vitals` on PyPI (MIT) and a pull request to Bee's own CLI (bee-computer/bee-cli#20) | https://pypi.org/project/speech-vitals/ |
| AWS Builder: documented integrations | [AWS.md](AWS.md): Bedrock, Strands Agents, Polly, DynamoDB, Lambda, S3, CloudFront, CDK | Read |
| Pre-existing project | None; first commit 2026-09-16, inside the window | `git log --reverse` |
| Feature requests, rated | [FEATURE_REQUESTS.md](FEATURE_REQUESTS.md), each critical, important or nice-to-have | Read |
| Friction log (up to 10 percent bonus) | [FRICTION_LOG.md](../FRICTION_LOG.md), nineteen entries in the required form | Read |

## Judging criteria

### Technical implementation

- **A personal baseline engine with no model in the decision.** Nine
  language features per day, an exponentially weighted baseline, a
  concern-signed composite, CUSUM drift detection, and a freeze so the
  baseline cannot learn its way out of a real change. Explainable tiers;
  quiet days excluded, not misread.
- **Measured against the rules a reasonable engineer writes instead:**
  none of eighteen settings of two simpler rules beats it on both speed
  and false alarms ([fixtures/detector-comparison.json](../fixtures/detector-comparison.json)).
- **Run on real speech nobody here wrote:** 349 Supreme Court oral
  arguments, no alerts; every press conference of five presidents, with
  18 of 652 flagged on the four with no known dementia, clustered on one
  overseas trip and one final year ([EVIDENCE.md](EVIDENCE.md) 4c and 4d,
  including the parser bug that first hid six of those flags).
- **Two devices in one room, done properly.** The Bee hears the host too,
  so the host's questions are removed by when it spoke; on the first live
  session this kept exactly the wearer's 17 answers, and across 6,645 real
  utterances it removes none of the wearer's own words.
- **A second opinion, argued and gated.** Three Strands agents argue a flagged change from evidence the engine computes (`weigh_the_change`): an Advocate, a Sceptic and a Referee. The Referee's note must cite both sides and use only the evidence's numbers, or it is refused and retried; a real run is committed in `apps/agent/runs/`. `python apps/agent/second_opinion.py --profile alex-drift`.
- **Privacy by construction.** The server drops any field it does not
  know; a test sends a transcript full of names and finds none stored.
- **287 tests**, including guards that fail when a published number
  drifts from the code.

### Design

- One continuous experience: speak to the Bee, Bellwether learns your
  normal, a change becomes visible, and you have a page for your doctor.
- The check-in can be hosted by voice, so a person who will not use a
  screen still takes part; the coaching note says what to do, not just
  what moved.
- A first-week card and a day-by-day replay make the seven-day warmup a
  product rather than a blank; everything simulated is labelled on every
  screen.
- The doctor page has a section written for Medicare's Annual Wellness
  Visit, with three questions to bring. Light and dark, phone and desktop.

### Potential impact

- **The need, in real people's words.** 79 percent of US adults 45 and
  over would want to know they had Alzheimer's before symptoms (survey of
  1,702); 66 percent want brain health guidance from their doctor first,
  and only 14 percent have ever discussed it (survey of 3,829).
- **The gap.** Dementia takes 3.5 years from first symptoms to diagnosis
  on average; in Medicare about 92 percent of expected mild cognitive
  impairment cases went undiagnosed; the newest treatments are approved
  only for the early stage.
- **The signal is there, early.** Language from cognitively normal people
  predicted later Alzheimer's onset 7.6 years ahead in Framingham (written
  picture descriptions, compared across people: timing, not Bellwether's
  accuracy).
- **Somewhere to go that already exists:** the Annual Wellness Visit
  requires a cognitive assessment and names no tool.
- Every source, with what it showed and did not: [EVIDENCE.md](EVIDENCE.md).
  Limits, said plainly: one wearer, no cohort, no claim of clinical
  accuracy; the study to run is written with its endpoints fixed first
  ([PILOT.md](PILOT.md)).

### Quality of the idea

- Speech as a vital sign, measured against your own past rather than a
  population, from a device people already wear, with the words never
  leaving their computer.
- Bee alongside a speaker, which is the cross-device shape the
  organisers' brief asks for, and an assistant that hosts the check-in
  rather than only reading results.
- Nothing like it among the other public Bee projects in this hackathon.
