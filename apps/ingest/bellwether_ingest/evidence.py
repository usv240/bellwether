"""Capture proof that live Bee data really flowed, without publishing a life.

    bellwether-ingest evidence --out docs/BEE_LIVE.md

The Bee track asks for live data in the video and the code. A video is a
claim a reviewer has to take on trust for three minutes; a committed,
dated record of what the device actually returned is a claim they can
read at their own pace. The sibling Ring project did the same thing with
`docs/RING_LIVE.md` and it was the single most useful artefact in that
repository, so the pattern is repeated here.

The hard part is that Bee data is somebody's day. A transcript of a real
person's conversations is the most sensitive thing this project will ever
touch, and the whole premise is that it never leaves the machine. So this
writes counts, shapes and the nine numbers, and never a word of speech.

That is not a policy stated in a comment. `redact` drops any value that
could be text, and a test feeds it a conversation full of sentences and
asserts none of them survive. The output is designed so that publishing
it is safe even though the input never could be.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from speech_vitals import FEATURE_NAMES, aggregate_day

from .bee import BeeCli, BeeCliError, normalize_conversation

# Anything that could carry speech. The rule is an allowlist of shapes we
# understand rather than a blocklist of fields we happen to have seen,
# because the next CLI version may add a field nobody here anticipated.
_SAFE_NUMERIC = (int, float, bool)


def redact(value, depth: int = 0):
    """Keep structure and counts. Drop anything that could be words.

    A string is only ever reported as its type and length, never its
    content, including keys we believe are identifiers: a conversation
    title is a string, and a conversation title is often a sentence
    somebody said.
    """
    if depth > 5:
        return "..."
    if isinstance(value, dict):
        return {k: redact(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [f"list of {len(value)}"] if value else []
    if isinstance(value, _SAFE_NUMERIC) or value is None:
        return value
    if isinstance(value, str):
        return f"<string, {len(value)} chars>"
    return f"<{type(value).__name__}>"


def capture(cli: BeeCli | None = None) -> dict:
    """Ask the device the questions this project actually asks it."""
    cli = cli or BeeCli()
    out: dict = {
        "capturedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "calls": [],
        "days": [],
        "note": (
            "Counts, shapes and the nine features only. No transcript text, no "
            "conversation titles, no names, no locations. The input is a real "
            "person's day and the output is designed to be publishable."
        ),
    }

    def attempt(label: str, argv_hint: str, fn):
        try:
            data = fn()
            out["calls"].append(
                {
                    "call": label,
                    "command": argv_hint,
                    "ok": True,
                    "shape": redact(data),
                }
            )
            return data
        except BeeCliError as err:
            out["calls"].append(
                {"call": label, "command": argv_hint, "ok": False, "error": str(err)[:160]}
            )
            return None

    attempt("account", "bee me --json", cli.me)
    attempt("recent hours", "bee now --json", cli.now)
    convos = attempt(
        "conversations", "bee conversations list --json", lambda: cli.conversations_list(limit=50)
    )

    rows = []
    if isinstance(convos, list):
        rows = convos
    elif isinstance(convos, dict):
        rows = convos.get("conversations") or convos.get("data") or []

    utterances = []
    for raw in rows:
        utterances.extend(normalize_conversation(raw))

    by_day: dict[str, list] = {}
    for u in utterances:
        by_day.setdefault(u.ts[:10], []).append(u)

    for day in sorted(by_day):
        features = aggregate_day(by_day[day], day)
        row = features.to_dict()
        # Explicitly reconstruct rather than pass the row through, so a new
        # field in DayFeatures cannot silently appear in a published file.
        out["days"].append(
            {
                "date": row["date"],
                "utterances": row["utterances"],
                "token_count_day": row["token_count_day"],
                **{name: row[name] for name in FEATURE_NAMES if name in row},
            }
        )

    out["totals"] = {
        "conversations": len(rows),
        "utterances": len(utterances),
        "days": len(out["days"]),
        "wordsSeen": sum(d["token_count_day"] for d in out["days"]),
        "wordsPublished": 0,
    }
    return out


def to_markdown(data: dict) -> str:
    calls = data["calls"]
    answered = sum(1 for c in calls if c["ok"])
    totals = data.get("totals", {})

    lines = [
        "# Live Bee data: what actually came back",
        "",
        "Evidence that this project reads a real Bee device, captured by",
        "`bellwether-ingest evidence`.",
        "",
        f"Captured: {data['capturedAt']}. Commands answering: {answered} of {len(calls)}.",
        "",
        data["note"],
        "",
        "## Commands",
        "",
        "| Call | Command | Result |",
        "|---|---|---|",
    ]
    for c in calls:
        lines.append(
            f"| {c['call']} | `{c['command']}` | "
            f"{'answered' if c['ok'] else 'failed: ' + c.get('error', '')} |"
        )

    lines += [
        "",
        "## What the device returned",
        "",
        f"- Conversations: {totals.get('conversations', 0)}",
        f"- Utterances: {totals.get('utterances', 0)}",
        f"- Days with speech: {totals.get('days', 0)}",
        f"- Words read on this machine: {totals.get('wordsSeen', 0)}",
        f"- Words written to this file: {totals.get('wordsPublished', 0)}",
        "",
        "That last pair is the product in one line. The words were read, counted",
        "and thrown away, and only the numbers left the machine.",
        "",
        "## The nine features, from a real day",
        "",
        "```json",
        json.dumps(data["days"][:3], indent=1),
        "```",
        "",
        "## Response shapes",
        "",
        "Field names and value types, so the integration can be checked without",
        "publishing any content.",
        "",
        "```json",
        json.dumps([c.get("shape") for c in calls if c["ok"]], indent=1)[:2400],
        "```",
        "",
    ]
    return "\n".join(lines)
