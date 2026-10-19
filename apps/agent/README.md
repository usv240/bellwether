# The Speech Check-in agent

A Strands agent that answers the question a person or a family member actually asks, out loud and casually: "how have I been sounding lately, and is it worth mentioning to the doctor?" It answers by talking to Bellwether's own MCP server.

## The closed loop

The agent does not reach into Bellwether's data. It calls the **same MCP server** Alexa+ would use (`apps/server/bellwether_server/mcp.py`, Model Context Protocol spec 2025-11-25 over Streamable HTTP). Ten tools: `get_speech_vitals`, `get_trend`, `list_days`, `add_annotation`, `run_check_instructions`, `log_check_result`, `generate_doctor_report`, and the two that host the check-in, `start_check_in` and `coaching_note`. There are no transcripts to give it, because none exist.

## The second opinion: two agents argue, a third decides what you read

`second_opinion.py` asks Bellwether's MCP server for `weigh_the_change`: numbered evidence that a flagged change is real (C1, C2...) and that an ordinary week explains it (O1, O2...), computed from the engine's numbers with no model. Three Strands agents on Bedrock take it from there. The Advocate argues the change is real; the Sceptic argues the everyday explanations; the Referee writes three sentences for the person: which case is stronger on this evidence, what would settle it, and one thing to do this week.

The Referee's note is gated, not trusted: it must cite at least one item from each side, every number in it must appear in the evidence (written as words or not, and never rounded), and it may not name or predict a condition. A refused note is sent back once with the reason; a second refusal falls back to a note built from the evidence alone. The arguments are shown too, and either is withheld if it names a condition. Fourteen tests drive it with a scripted model.

```
python apps/agent/second_opinion.py --profile alex-drift          # the debate, printed
python apps/agent/second_opinion.py --profile alex-drift --json   # the record committed in runs/
```

## The Check-in Host: the assistant asks, the Bee listens

`check_in_host.py` is the two-devices-in-one-room version of the check-in. It calls `start_check_in` for tonight's exact lines (an opener that declares the session a check-in, three standard elicitation prompts rotated by date, a closing), speaks them through Amazon Polly, waits for the wearer to answer each, and the Bee on the wrist records the whole exchange. With `--count` it then waits for the Bee to write the session down, runs `bellwether-ingest mine --days 1` on the wearer's computer, which removes every line the host spoke before measuring, and reads the `coaching_note` back: day three of seven, or the last day fell under the floor and why, or what moved and the one thing to do.

The host stands in for Alexa+ because the Alexa+ MCP connection cannot yet be driven from a script; it uses exactly the tools an Alexa+ agent gets. It never reads a transcript: it polls the conversation list for counts and hears the result come back from `mine`.

The band hears the host, and on the first live run it merged, split and misheard the host's lines. So the host saves when it played each line, by this computer's clock, in `.bellwether-host.json`, and the ingest drops anything that began while the host was speaking and ends the check-in at the closing line. On that real session this kept exactly the wearer's 17 answers, 297 words. A host that saves no timing still works by text, which matched on the same session.

```
python apps/agent/check_in_host.py --dry-run                 # print tonight's script
python apps/agent/check_in_host.py --profile me              # speak it; count later with mine --days 1
python apps/agent/check_in_host.py --profile me --count      # speak, wait for the Bee, count, read the note
```

If the MCP surface were wrong, this agent would be wrong too. That is the cheapest possible proof that the surface is real.

## The safety rule, enforced in the prompt and in the design

The agent may **only** report numbers the tools returned. It never diagnoses, never names a condition, never predicts, and never gives medical advice. It suggests only what the person can do themselves: add a note about sleep, travel or illness, run the spoken check, or bring the report to their clinician. It says plainly when data is simulated.

## The spoken check, administered by voice

`run_check_instructions` returns the check as short lines an agent can read aloud: sixty seconds of animal naming, then three sentences to repeat, with scoring rules and the literature basis. The agent logs the result with `log_check_result`, and it appears on the timeline beside the passive trend. Designed so that a person who cannot or will not use a screen can still do the check.

## Run it

```
pip install strands-agents strands-agents-tools mcp
uvicorn bellwether_server.main:app --port 8789     # from the repo root, in the venv
python apps/agent/speech_check_in.py
# against the deployed server:
python apps/agent/speech_check_in.py --url https://<function-url>/mcp
python apps/agent/speech_check_in.py --ask "Can we do the spoken check now?"
```

Verified output against the deployed endpoint, on the simulated persona:

```
Tools discovered: add_annotation, generate_doctor_report, get_speech_vitals,
                  get_trend, list_days, log_check_result, run_check_instructions

This is simulated data. Your speech has been in the discuss tier since
September 3, and the trend shows sharp changes from your own baseline. The
report shows that filler rate and disfluency rate have been consistently
higher, and several other features including sentence length, vocabulary
diversity, and idea density have been lower since early September. Yes,
bring this report to your next appointment.
```

Every fact there came from a tool call, the simulated label was stated first, and the only suggestion was one the person can act on.

Model: Claude on Amazon Bedrock (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`).

---

# The Context Check-in agent: one agent, two MCP servers

`context_check_in.py` answers the question the dashboard cannot:

> *"Your speech was flagged starting the 3rd. That week you were at the hospital twice and had four late nights logged. That is the most likely explanation, and it is worth noting on those days."*

Bellwether's MCP server knows **that** something changed and which measures moved. It cannot know **why**, because it holds nine numbers a day and nothing else. Bee's own MCP server (`bee mcp serve-http`) knows the shape of the day: daily summaries, todos, places, activity. Neither server can answer the question alone. An agent holding both can.

## Why this is the point, not a demo

The most important panel in the product is `What else could explain this`, which puts the ordinary causes of a change in front of a worried person before the frightening one. Today it asks them to remember and annotate their own week. That is work, at exactly the moment someone is least able to do it. This agent does that work instead, from data the person already has.

## The privacy boundary, enforced rather than promised

Bee's MCP catalogue exposes **verbatim speech** alongside derived context: `bee_get_conversation_transcript`, `bee_get_conversation`, `bee_search` and the voice-note tools all return what was actually said.

Bellwether's whole architecture rests on the opposite. An agent that could read transcripts would break that guarantee at the one seam where nobody was looking.

So the agent takes an **allowlist**, not a denylist. Nine derived-context tools are handed to the model; everything else is withheld, including every speech tool, named explicitly so the exclusion is auditable. A tool Bee adds tomorrow, or renames, is withheld by default rather than admitted by accident.

**Nine tests pin that boundary** (`tests/test_allowlist.py`), including that the two sets never overlap and that an unknown tool is excluded by default. It is a safety claim, so it has a test.

## Run it

```
# terminal 1: Bellwether
uvicorn bellwether_server.main:app --port 8789

# terminal 2: Bee's own MCP server, localhost-bound, bearer token, 32 chars minimum
export BEE_MCP_HTTP_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
bee mcp serve-http --port 9779

# terminal 3
python apps/agent/context_check_in.py --profile alex-drift
```

Without a paired Bee device the second server serves no data. The agent degrades to Bellwether's tools alone and says so:

```
Bellwether MCP: https://.../mcp
  tools: add_annotation, generate_doctor_report, get_speech_vitals, get_trend,
         list_days, log_check_result, run_check_instructions
Bee MCP: not running

Your speech has changed sharply from your baseline beginning September 2nd,
reaching discuss tier on September 3rd and remaining there since. This data is
simulated. I cannot look for an explanation in your daily activities because
the Bee context tools are not available in this session. I recommend bringing
this to your clinician or using the doctor report feature to prepare.
```

It states the simulated label first, reports only tool facts, says plainly what it could not check, and suggests only what the person can act on. That degradation is the behaviour, not a fallback.
