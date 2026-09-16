# The Speech Check-in agent

A Strands agent that answers the question a person or a family member actually asks, out loud and casually: "how have I been sounding lately, and is it worth mentioning to the doctor?" It answers by talking to Bellwether's own MCP server.

## The closed loop

The agent does not reach into Bellwether's data. It calls the **same MCP server** Alexa+ would use (`apps/server/bellwether_server/mcp.py`, Model Context Protocol spec 2025-11-25 over Streamable HTTP). Seven tools: `get_speech_vitals`, `get_trend`, `list_days`, `add_annotation`, `run_check_instructions`, `log_check_result`, `generate_doctor_report`. There are no transcripts to give it, because none exist.

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
