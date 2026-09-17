"""The Context Check-in agent: one agent, two MCP servers.

This is the agent that answers the question the dashboard cannot:

    "Your speech was flagged starting the 3rd. That week you were at the
     hospital twice and had four late nights logged. That is the most
     likely explanation, and it is worth noting on those days."

Bellwether's own MCP server knows *that* something changed and which
measures moved. It has no idea *why*, because it holds nine numbers a day
and nothing else. Bee's MCP server knows the shape of the day: where the
person was, what they had to do, what the day was summarised as. Neither
server can answer the question alone. An agent holding both can.

Why this matters more than it looks
-----------------------------------
The most important panel in the product is "What else could explain this",
which lists the ordinary causes of a change (poor sleep, illness, a new
medication, a stressful week) so that a worried person reaches the mundane
explanation before the frightening one. Today it asks the person to
remember their own week and annotate it. That is work, and it is work at
exactly the moment someone is least able to do it.

This agent does that work instead, from data the person already has.

The privacy boundary, enforced here rather than promised
--------------------------------------------------------
Bee's MCP server exposes both derived context and **verbatim speech**:
``bee_get_conversation_transcript``, ``bee_get_conversation``,
``bee_search`` and the voice-note tools all return what was actually said.

Bellwether's entire architecture rests on the opposite: words are reduced
to numbers where the transcript lives, and nothing that can reconstruct a
sentence ever travels. An agent that could read transcripts would break
that guarantee at the one seam where nobody was looking.

So this agent takes an **allowlist**, not a denylist. Only the tools below
are ever handed to the model. A new Bee tool, or a renamed one, is excluded
by default rather than included by accident, which is the safe direction
for a list like this to fail in.

Run it
------
    # terminal 1: Bellwether
    uvicorn bellwether_server.main:app --port 8789

    # terminal 2: Bee's own MCP server, localhost-bound, bearer token
    export BEE_MCP_HTTP_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
    bee mcp serve-http --port 9779

    # terminal 3
    python apps/agent/context_check_in.py --profile alex-drift

Without a paired Bee device the second server will not serve data. The
agent degrades to Bellwether's tools alone and says so, rather than
pretending to have context it does not have.
"""

from __future__ import annotations

import argparse
import contextlib
import io as _io
import json
import os
import sys
import warnings

# An MCP client that never connected leaves an un-awaited cleanup coroutine
# behind, which Python reports at interpreter shutdown, after our output has
# already printed. Bee's server simply not running is an ordinary state, and
# a warning trailing a correct answer reads as a failure to anyone watching.
warnings.filterwarnings(
    "ignore",
    message=r"coroutine 'MCPClient\.stop.*' was never awaited",
    category=RuntimeWarning,
)

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

BELLWETHER_MCP_URL = "http://127.0.0.1:8789/mcp"
BEE_MCP_URL = "http://127.0.0.1:9779/mcp"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Derived context only. Every one of these describes the shape of a day.
# None of them returns a sentence the person said.
BEE_CONTEXT_TOOLS: frozenset[str] = frozenset(
    {
        "bee_get_daily_summary",
        "bee_list_daily_summaries",
        "bee_list_todos",
        "bee_get_insights",
        "bee_get_location_clusters",
        "bee_get_recent_visits",
        "bee_get_current_location",
        "bee_get_recent_activity",
        "bee_status",
    }
)

# Named explicitly so the exclusion is auditable, and so anyone reading this
# file can see exactly what was kept out and why.
BEE_SPEECH_TOOLS: frozenset[str] = frozenset(
    {
        "bee_get_conversation_transcript",
        "bee_get_conversation",
        "bee_list_conversations",
        "bee_get_related_conversations",
        "bee_search",
        "bee_list_voice_notes",
        "bee_search_voice_notes",
        "bee_get_voice_note",
    }
)

SYSTEM_PROMPT = """You help one person understand a tool called Bellwether,
which keeps a personal baseline of how they normally speak (from language
features only, never the words) and reports when that changes.

You have two sets of tools.

From Bellwether: the speech baseline. get_speech_vitals for the current
tier, get_trend for how the days ran, list_days for the underlying numbers,
generate_doctor_report, add_annotation, and the spoken check.

From Bee: the shape of the person's days. Daily summaries, todos, places
visited, recent activity. You do NOT have access to anything they said, and
you must never ask for it or imply you have it.

How to work:
1. Call get_speech_vitals first. If the tier is stable, say so briefly and
   stop. A short answer is a good week.
2. If the tier is watch or discuss, call get_trend to find the dates the
   change began and persisted.
3. Then, and only then, look at those specific dates in Bee: the daily
   summaries, the todos, the places. You are looking for ordinary
   explanations, in this order of likelihood: disrupted sleep, illness or a
   medical appointment, a new or changed medication, travel, an unusually
   heavy or stressful stretch, or a period spent talking to far fewer
   people than usual.
4. If you find a plausible ordinary explanation, say it plainly and offer
   to annotate those days. If you do not find one, say that too. Do not
   invent one, and do not stretch a weak one to be reassuring.

Hard rules:
- Report only what the tools returned. Never estimate or extrapolate.
- Never diagnose, never name a condition, never predict, never give medical
  advice. Suggest only what the person can do themselves: annotate a day,
  run the spoken check, or bring the report to their clinician.
- Never quote or paraphrase anything the person said. You do not have it.
- Say plainly when data is simulated.
- An ordinary explanation makes a change easier to read. It does not make
  the change untrue, and you must not present it as an all-clear.
- Five sentences or fewer, warm and plain, second person. No emojis. No
  dashes of any kind as punctuation.

Output format: the answer itself and nothing else.
"""


@contextlib.contextmanager
def _quiet_stderr():
    """Swallow the transport's own traceback when a local server is absent.

    A refused connection to an optional local process is an expected state,
    and printing an httpx stack trace for it makes a working degradation
    look like a crash to anyone watching.
    """
    saved = sys.stderr
    sys.stderr = _io.StringIO()
    try:
        yield
    finally:
        sys.stderr = saved


def build_client(url: str, token: str | None = None) -> MCPClient:
    if token:
        return MCPClient(
            lambda: streamablehttp_client(url, headers={"Authorization": f"Bearer {token}"})
        )
    return MCPClient(lambda: streamablehttp_client(url))


def tool_name(tool) -> str:
    return getattr(tool, "tool_name", str(tool))


def main() -> int:
    parser = argparse.ArgumentParser(description="Bellwether context check-in (two MCP servers)")
    parser.add_argument("--url", default=BELLWETHER_MCP_URL, help="Bellwether MCP endpoint")
    parser.add_argument("--bee-url", default=BEE_MCP_URL, help="Bee MCP endpoint (bee mcp serve-http)")
    parser.add_argument("--bee-token", default=os.environ.get("BEE_MCP_HTTP_TOKEN"), help="Bee MCP bearer token")
    parser.add_argument("--profile", default="alex-drift")
    parser.add_argument("--ask", default=None)
    parser.add_argument("--no-bee", action="store_true", help="skip Bee and use Bellwether alone")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    question = args.ask or (
        f"Has {args.profile} had any change in how they are speaking, and if so, "
        f"is there an ordinary explanation for it in their week?"
    )

    bellwether = build_client(args.url)
    tools: list = []
    bee_tools: list = []
    excluded: list[str] = []
    bee_status = "not attempted"

    with bellwether:
        tools.extend(bellwether.list_tools_sync())

        bee_client = None
        if not args.no_bee:
            started = False
            try:
                # Bee's MCP server is a separate local process that may simply
                # not be running. That is an ordinary state, not an error, so
                # the noise from a refused connection is suppressed and the
                # agent is told plainly that it has no context this session.
                with warnings.catch_warnings(), _quiet_stderr():
                    warnings.simplefilter("ignore")
                    candidate = build_client(args.bee_url, args.bee_token)
                    candidate.start()
                    started = True
                    offered = candidate.list_tools_sync()
                bee_client = candidate
                for t in offered:
                    name = tool_name(t)
                    (bee_tools if name in BEE_CONTEXT_TOOLS else excluded).append(
                        t if name in BEE_CONTEXT_TOOLS else name
                    )
                tools.extend(bee_tools)
                bee_status = f"connected, {len(bee_tools)} context tools, {len(excluded)} withheld"
            except Exception as err:  # noqa: BLE001
                first = str(err).splitlines()[0][:70] if str(err).strip() else type(err).__name__
                bee_status = f"not running ({first})"
                if started:
                    try:
                        with _quiet_stderr():
                            candidate.stop(None, None, None)
                    except Exception:  # noqa: BLE001
                        pass
                bee_client = None

        if not args.json:
            print(f"Bellwether MCP: {args.url}")
            print(f"  tools: {', '.join(sorted(tool_name(t) for t in tools if tool_name(t) not in BEE_CONTEXT_TOOLS))}")
            print(f"Bee MCP: {bee_status}")
            if bee_tools:
                print(f"  context tools in use: {', '.join(sorted(tool_name(t) for t in bee_tools))}")
            if excluded:
                speech = [n for n in excluded if n in BEE_SPEECH_TOOLS]
                print(f"  withheld: {len(excluded)} tools, including {len(speech)} that return verbatim speech")
            print()

        prompt = f"The profile is {args.profile}. {question}"
        if not bee_tools:
            prompt += (
                "\n\nNote: the Bee context tools are not available in this session, so you "
                "cannot look for an explanation in their week. Say so plainly rather than guessing."
            )

        agent = Agent(
            model=BedrockModel(model_id=MODEL_ID, region_name="us-east-1"),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            name="bellwether-context-check-in",
            description="Correlates a speech change with the shape of the person's week, from two MCP servers.",
            callback_handler=None,
        )
        result = agent(prompt)
        text = str(result).strip()

        if bee_client is not None:
            try:
                with _quiet_stderr():
                    bee_client.stop(None, None, None)
            except Exception:  # noqa: BLE001
                pass

    if args.json:
        print(
            json.dumps(
                {
                    "answer": text,
                    "bellwether_mcp": args.url,
                    "bee_mcp": bee_status,
                    "bee_context_tools": sorted(tool_name(t) for t in bee_tools),
                    "withheld_tools": sorted(excluded),
                    "model": MODEL_ID,
                },
                indent=1,
            )
        )
    else:
        print("=" * 62)
        print("CONTEXT CHECK-IN")
        print("=" * 62)
        print(text)
        print("=" * 62)
        print("Two MCP servers: Bellwether for the speech baseline, Bee for the")
        print("shape of the days. No tool in this session can return anything")
        print("the person said. Not a diagnosis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
