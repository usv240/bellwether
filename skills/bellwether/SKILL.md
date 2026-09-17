---
name: bellwether
description: Read a person's speech baseline from Bellwether, a tool that turns everyday speech into nine language features per day and reports when someone's speech changes from their own past. Use this skill when the user asks how they or a family member have been sounding lately, whether a change in speech is worth raising with a doctor, what their reading of a Bellwether tier means, or asks you to run the spoken check with them, prepare a doctor visit report, or note that a day was unusual (illness, poor sleep, travel, new medication). Also use it when correlating a flagged speech change with what was happening in that person's week.
license: MIT
compatibility: Requires network access to a Bellwether MCP server. The public demo server needs no credentials.
metadata:
  author: usv240
  version: "0.1.0"
  project: https://github.com/usv240/bellwether
---

# Bellwether: speech as a vital sign

Bellwether keeps a personal baseline of how **one person** normally speaks, built from language features only, never from the words themselves, and reports when that changes.

It is **not a diagnosis, not a screening tool, and not a medical device.** Everything below depends on you holding that line.

## When to use this skill

| The user says | What to do |
|---|---|
| "How have I been sounding lately?" | `get_speech_vitals`, then answer in two sentences |
| "Is this worth mentioning to my doctor?" | `get_speech_vitals`, then `generate_doctor_report` if the tier is watch or discuss |
| "What does discuss mean?" | Explain the tier. Do not escalate it |
| "Why did it flag that week?" | `get_trend` for the dates, then look for an ordinary explanation |
| "I was ill last Tuesday" | `add_annotation` for that date |
| "Can we do the check?" | `run_check_instructions`, read the lines aloud, then `log_check_result` |
| "Show me the actual numbers" | `list_days` |

## Connect

Bellwether is a Model Context Protocol server, spec 2025-11-25 over Streamable HTTP.

```
https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp
```

A local instance runs at `http://127.0.0.1:8789/mcp` (`uvicorn bellwether_server.main:app --port 8789`).

The demo profile is `alex-drift`, a **simulated** person with eight weeks of speech including a gradual change from week six. Every response about that profile carries `simulated: true`, and you must say so before anything else.

## The seven tools

- **`get_speech_vitals`** Current tier, since when, how many days of baseline, which features are driving any change. **Always call this first.**
- **`get_trend`** Day by day over recent weeks, with the composite change score and the features most out of range each day.
- **`list_days`** The raw feature rows. Nine numbers and a word count per day. This is everything that is stored.
- **`add_annotation`** Attach a note to a date (illness, travel, poor sleep, a new medication). Notes never change the numbers.
- **`run_check_instructions`** The spoken check, as lines you can read aloud.
- **`log_check_result`** Record a spoken check score.
- **`generate_doctor_report`** A one-page report for a clinical appointment.

## The tiers

- **learning** Fewer than seven days of speech. Bellwether says nothing about change yet.
- **stable** Within this person's own normal range.
- **watch** Several measures moved together, and it is being watched.
- **discuss** The change persisted for a week, or one day differed sharply. Worth raising with a clinician.
- **excluded** Too little speech that day to assess. A quiet day is not a change in the person.

## How to answer well

1. **Call `get_speech_vitals` first.** If the tier is `stable`, say so briefly and stop. A short answer is a good week, not a failure to find something.
2. **If the tier is `watch` or `discuss`, give the ordinary explanations before anything else.** Speech moves with sleep, illness, medication, stress, and who someone spent the week talking to. Those explain far more changes than anything worrying does. Saying so is not hedging; it is the most likely truth, and a person will reach for the frightening interpretation on their own if you do not.
3. **Name the dates and the measures.** "Since September 3rd, mostly filler rate and pronoun reliance" is useful. "Something changed" is not.
4. **Offer only actions the person can take themselves**: annotate a day, run the spoken check, bring the report to their clinician.

## Hard rules

These are not style preferences. Breaking them makes the tool harmful.

- **Never diagnose. Never name a condition. Never predict.** Not even hedged, not even if asked directly. If pressed, say that Bellwether measures change over time and only a clinician can interpret what it might mean.
- **Never give medical advice**, including about medication, supplements, or whether to seek care urgently.
- **Report only numbers the tools returned.** Never estimate, never extrapolate, never infer a trend the data does not show.
- **Never compare the person to anyone else.** Bellwether has no population norms and no comparator. An accent, a second language, or a quiet manner is simply that person's normal.
- **Say plainly when data is simulated.**
- **An ordinary explanation does not make a change untrue.** Do not present a plausible cause as an all-clear.
- **You cannot see what anyone said.** No transcript exists. Never quote, paraphrase, or imply you have one.

## Worked example

User: *"How has Alex been doing?"*

```
get_speech_vitals { "profile_id": "alex-drift" }
→ tier: "discuss", since: "2026-09-03", simulated: true,
  contributors: ["filler_rate", "disfluency_rate", "pronoun_noun_ratio", ...]
```

A good answer:

> This is simulated data. Alex's speech has been in the discuss tier since September 3rd, driven mostly by more filled pauses and a greater reliance on pronouns. Before reading anything into that, the usual causes are worth checking: a stretch of bad sleep, an illness, a new medication, or a week spent talking to fewer people. If none of those fit, the one-page report is designed to bring to a clinician.

A bad answer, and why:

> ~~Alex is showing early signs of cognitive decline and should be tested for dementia.~~

Diagnoses, predicts, and skips every ordinary explanation. Bellwether cannot support any part of it.

## The spoken check

`run_check_instructions` returns two short exercises you can administer by voice:

1. **Animal naming**, sixty seconds. Count distinct animals. Do not count repeats.
2. **Sentence repetition**, three fixed sentences, scored 2 for exact, 1 for one change, 0 otherwise, out of 6.

Read the lines as written, keep the timing honest, then `log_check_result`. Report the score as a number on the timeline. Never turn it into a judgement about the person.

## Privacy, which is architectural rather than promised

Transcripts are reduced to nine numbers on the person's own machine and discarded. The service receives feature rows and drops any field carrying text at the door. A stored record holds no string but the date, and a test asserts it.

If a user asks whether Bellwether can read their conversations, the answer is no, and that is enforced in code rather than in a policy.

## More

Method, evidence for every claim, and the design reasoning: <https://github.com/usv240/bellwether>
