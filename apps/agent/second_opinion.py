"""A second opinion: two agents argue a flagged change, a third writes the note.

    python apps/agent/second_opinion.py --profile alex-drift
    python apps/agent/second_opinion.py --profile alex-drift --json

When Bellwether flags a change, the useful question is not "is something
wrong?" but "is this real, or is it an ordinary week?". Three Strands
agents on Amazon Bedrock take the two sides of that question, from
evidence they did not write:

  1. The evidence comes from Bellwether's MCP server, the same one Alexa+
     uses: ``weigh_the_change`` lists numbered items for each side (C1...
     for a real change, O1... for an ordinary explanation), computed from
     the engine's numbers with no model involved.
  2. The Advocate argues the change is real and worth raising; the Sceptic
     argues the ordinary explanations; each must cite items by id.
  3. The Referee reads both and writes three sentences for the person:
     what the stronger case is, what would settle it, and one thing to do.

The Referee's note passes a gate before anyone sees it. It must cite at
least one item from each side; every number in it must appear in the
evidence; and it may not name a condition, predict, or diagnose. If it
fails, a note built only from the evidence is used instead, and the output
says which. The debate never sees a word anyone said: there are no
transcripts, only the numbers the tools return.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Callable

DEFAULT_MCP_URL = os.environ.get("BELLWETHER_MCP", "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp")
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

FORBIDDEN = re.compile(
    r"\b(dementia|alzheimer\w*|diagnos\w*|parkinson\w*|aphasia|disease|disorder|predict\w*|will (get|develop)|"
    r"cognitive (decline|impairment)|symptom\w*)\b", re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")
_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
          "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20", "thirty": "30"}
_NUM_WORD = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.I)
_ID = re.compile(r"\b([CO]\d)\b")

RULES = """Rules for everything you write:
- Use only the evidence items given. Cite each item you use by its id in brackets, like [C2] or [O1].
- Use no number that is not in the evidence, and never round one ("18 days", not "nearly twenty"). Write dates as the evidence does.
- Never name a condition, never diagnose, never predict what will happen, never give medical advice.
- If the data is labelled simulated, it is simulated; do not speak of it as a real person.
- Plain prose only: no headings, no bold, no lists, no markdown. No dashes as punctuation. No emojis.
- At most three sentences and 80 words.
- Address the person as "you"; never use a name.
- Do not invent any step, duration or tool that is not in the evidence or in the list of things a person can do."""

ADVOCATE = "You argue that the flagged change in this person's speech is real and worth raising with a clinician. " \
           "Make the strongest honest case in three sentences, from the C items, and answer the strongest O item.\n" + RULES
SCEPTIC = "You argue that an ordinary week, not a real change, explains what Bellwether flagged. " \
          "Make the strongest honest case in three sentences, from the O items, and answer the strongest C item.\n" + RULES
REFEREE = "You read both arguments and write the note the person sees, in exactly three sentences: which case is " \
          "stronger on this evidence and why, citing at least one C item and one O item; what would settle it; and one " \
          "thing the person can do this week (add a note about sleep, travel or illness, run the spoken check, or bring " \
          "the report to a clinician they trust).\n" + RULES


def evidence_text(w: dict) -> str:
    lines = [f"Profile {w['profile_id']}{' (SIMULATED)' if w.get('simulated') else ''}: tier {w['tier']} since {w['since']}."]
    lines += ["Evidence for a real change:"] + [f"[{e['id']}] {e['claim']}" for e in w["change"]]
    lines += ["Evidence for an ordinary explanation:"] + [f"[{e['id']}] {e['claim']}" for e in w["ordinary"]]
    return "\n".join(lines)


def clean(text: str) -> str:
    """The house style, enforced rather than requested: no markdown, no
    dashes as punctuation, one paragraph."""
    t = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"\s*[—–]\s*", ", ", t)
    t = re.sub(r"^\s*[-*]\s+", "", t, flags=re.M)
    return " ".join(t.split())


def gate(note: str, w: dict) -> tuple[bool, str]:
    """Accept the referee's note only if it stays inside the evidence."""
    if FORBIDDEN.search(note):
        return False, f"names or predicts a condition: {FORBIDDEN.search(note).group(0)!r}"
    ids = set(_ID.findall(note))
    known_c = {e["id"] for e in w["change"]}
    known_o = {e["id"] for e in w["ordinary"]}
    if not ids & known_c or not ids & known_o:
        return False, "does not cite both sides"
    if ids - known_c - known_o:
        return False, f"cites items that do not exist: {sorted(ids - known_c - known_o)}"
    # The ids are labels, not numbers: "[O5]" must not let a "5" through.
    raw = set(_NUM.findall(_ID.sub("", evidence_text(w))))
    # "2026-09-03" allows "3" as well as "03": September 3rd is the same date.
    allowed = raw | {n.lstrip("0") or "0" for n in raw} | {"0", "1", "2"}
    body = _ID.sub("", note)
    found = _NUM.findall(body) + [_WORDS[m.lower()] for m in _NUM_WORD.findall(body)]
    stray = [n for n in found if n not in allowed]
    if stray:
        return False, f"uses numbers not in the evidence: {stray}"
    return True, "ok"


def fallback(w: dict) -> str:
    """The floor: a note from the evidence alone, always inside the gate."""
    c, o = w["change"], w["ordinary"]
    return (f"For a real change: {c[0]['claim']} [{c[0]['id']}] "
            f"For an ordinary week: {o[0]['claim']} [{o[0]['id']}] "
            "What would settle it is a few more weeks of days and a note on anything that changed your sleep, health or routine. "
            "This week, add those notes and run the spoken check, and if the change holds, bring the report to a clinician you trust.")


def debate(w: dict, ask: Callable[[str, str], str]) -> dict:
    """Run the three agents. ``ask(system, prompt)`` is one model turn; the
    command line passes Strands agents on Bedrock, the tests pass a script."""
    ev = evidence_text(w)
    advocate = clean(ask(ADVOCATE, ev))
    sceptic = clean(ask(SCEPTIC, ev))
    briefing = f"{ev}\n\nThe Advocate:\n{advocate}\n\nThe Sceptic:\n{sceptic}"
    note = clean(ask(REFEREE, briefing))
    ok, why = gate(note, w)
    rejected = []
    if not ok:
        # One retry, told exactly why. The gate does not bend; the
        # referee rewrites.
        rejected.append({"note": note, "why": why})
        note = clean(ask(REFEREE, f"{briefing}\n\nYour note was rejected: {why}. Rewrite it within the rules, "
                                  "citing at least one C item and one O item in brackets."))
        ok, why = gate(note, w)
        if not ok:
            rejected.append({"note": note, "why": why})
    # The two arguments are shown too, so they meet the same bar on what
    # they may say about health.
    if FORBIDDEN.search(advocate):
        advocate = f"(withheld: it named or predicted a condition, {FORBIDDEN.search(advocate).group(0)!r})"
    if FORBIDDEN.search(sceptic):
        sceptic = f"(withheld: it named or predicted a condition, {FORBIDDEN.search(sceptic).group(0)!r})"
    return {
        "profile_id": w["profile_id"], "simulated": w.get("simulated", False), "tier": w["tier"], "since": w["since"],
        "advocate": advocate, "sceptic": sceptic,
        "note": note if ok else fallback(w), "note_source": "referee" if ok else "evidence (the referee's note failed the gate)",
        "gate": why, "rejected": rejected, "evidence": {"change": w["change"], "ordinary": w["ordinary"]},
    }


def strands_ask(model_id: str = MODEL_ID) -> Callable[[str, str], str]:
    from strands import Agent
    from strands.models import BedrockModel

    model = BedrockModel(model_id=model_id, region_name="us-east-1")

    def ask(system: str, prompt: str) -> str:
        agent = Agent(model=model, system_prompt=system, callback_handler=None)
        return str(agent(prompt)).strip()

    return ask


def fetch_evidence(url: str, profile: str) -> dict:
    from mcp.client.streamable_http import streamablehttp_client
    from strands.tools.mcp import MCPClient

    client = MCPClient(lambda: streamablehttp_client(url))
    with client:
        res = client.call_tool_sync("weigh-1", "weigh_the_change", {"profile_id": profile})
    content = res["content"] if isinstance(res, dict) else res.content
    first = content[0]
    text = first["text"] if isinstance(first, dict) else first.text
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Two agents argue a flagged change; a third writes the note")
    ap.add_argument("--url", default=DEFAULT_MCP_URL)
    ap.add_argument("--profile", default="alex-drift")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    w = fetch_evidence(args.url, args.profile)
    if not w["change"]:
        print(w["note"])
        return 0
    out = debate(w, strands_ask())
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    bar = "=" * 62
    print(f"Evidence from {args.url} (weigh_the_change)\n")
    print(evidence_text(w))
    print(f"\n{bar}\nTHE ADVOCATE: the change is real\n{bar}\n{out['advocate']}")
    print(f"\n{bar}\nTHE SCEPTIC: an ordinary week explains it\n{bar}\n{out['sceptic']}")
    for r in out["rejected"]:
        print(f"\n{bar}\nTHE GATE REFUSED A NOTE: {r['why']}\n{bar}\n{r['note']}")
    print(f"\n{bar}\nTHE REFEREE: the note you see ({out['note_source']})\n{bar}\n{out['note']}")
    print(f"\nGate: {out['gate']}. Three Strands agents on Amazon Bedrock, from Bellwether's MCP tools only. Not a diagnosis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
