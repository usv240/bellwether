"""The Speech Check-in agent.

A Strands agent that answers the question a person or a family member
actually asks, out loud and casually: "how have I been sounding lately, and
is it worth mentioning to the doctor?" It answers by talking to Bellwether's
own MCP server.

The point of building it this way: the agent is a second, independent
client of the same Model Context Protocol server Alexa+ would use
(apps/server/bellwether_server/mcp.py, spec 2025-11-25 over Streamable
HTTP). It has no database access and no privileged path. It gets seven
tools and nothing else: no transcripts, because none exist to give. If the
MCP surface were wrong, this agent would be wrong too, which is the
cheapest possible proof that the surface is real.

The safety boundary does not move because the output is a sentence. The
agent may report only numbers the tools returned. It never diagnoses,
never names a condition, never predicts, and never gives medical advice.

Usage:
    python speech_check_in.py [--url http://127.0.0.1:8789/mcp] [--profile alex-drift] [--ask "..."]
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

DEFAULT_MCP_URL = "http://127.0.0.1:8789/mcp"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You help one person, or a family member, understand a
tool called Bellwether. Bellwether keeps a personal baseline of how that one
person normally speaks, from language features only (never the words), and
reports when that changes. It compares them only with their own past.

How to work:
1. Call get_speech_vitals first to learn the current tier and since when.
2. If the tier is watch or discuss, call get_trend to see how the days ran,
   and generate_doctor_report if they are asking what to bring to an
   appointment.
3. If they ask to do the spoken check, call run_check_instructions and
   read its lines aloud one at a time, then log the result.
4. Only then answer.

Hard rules:
- Report only numbers and facts the tools returned. Never estimate, never
  extrapolate, never invent a trend the data does not show.
- Never diagnose, never name a condition, never predict what will happen,
  never give medical advice. Suggest only what the person can do
  themselves: add a note about sleep, travel or illness, run the spoken
  check, or bring the report to their clinician.
- Say plainly that data labelled simulated is simulated.
- If the tier is stable, say so briefly. A short answer is a good week.
- Four sentences or fewer, warm and plain, second person. No emojis. No
  dashes of any kind as punctuation.

Output format: the answer itself and nothing else. No preamble, no heading,
no commentary about the tools or your process.
"""


def build_client(url: str) -> MCPClient:
    return MCPClient(lambda: streamablehttp_client(url))


def main() -> int:
    parser = argparse.ArgumentParser(description="Bellwether speech check-in agent")
    parser.add_argument("--url", default=DEFAULT_MCP_URL, help="Bellwether MCP endpoint")
    parser.add_argument("--profile", default="alex-drift", help="Which profile to ask about")
    parser.add_argument("--ask", default=None, help="What to ask; defaults to a monthly check-in")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    question = args.ask or (
        f"How has {args.profile} been sounding this month, and is there anything "
        f"worth mentioning at the next appointment?"
    )

    client = build_client(args.url)
    with client:
        tools = client.list_tools_sync()
        tool_names = sorted(getattr(t, "tool_name", str(t)) for t in tools)
        if not args.json:
            print(f"Connected to {args.url}")
            print(f"Tools discovered: {', '.join(tool_names)}\n")

        agent = Agent(
            model=BedrockModel(model_id=MODEL_ID, region_name="us-east-1"),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            name="bellwether-speech-check-in",
            description="Answers a person's question from Bellwether's MCP tools only.",
            callback_handler=None,
        )
        result = agent(f"The profile is {args.profile}. {question}")
        text = str(result).strip()

    if args.json:
        print(json.dumps({"answer": text, "tools": tool_names, "model": MODEL_ID}, indent=1))
    else:
        print("=" * 62)
        print("SPEECH CHECK-IN")
        print("=" * 62)
        print(text)
        print("=" * 62)
        print("Written by a Strands agent from Bellwether's MCP tools only.")
        print("Not a diagnosis. Bellwether is a general wellness tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
