"""Command line: ``speech-vitals analyze transcript.jsonl --out days.json``.

Input is JSON Lines, one utterance per line::

    {"ts": "2026-09-16T08:12:03Z", "text": "...", "speaker": "speaker_1"}

Output is a JSON array of ``DayFeatures``, one per calendar date, ordered.
Pass ``--speaker`` to keep only one speaker label, which is how the owner's
own speech is isolated from everyone else's. The transcript is read, reduced
and discarded; nothing but numbers is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from .features import aggregate_day
from .types import Utterance, features_schema


def _read_jsonl(path: str) -> list[Utterance]:
    out: list[Utterance] = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as err:
                raise SystemExit(f"{path}:{n}: not valid JSON ({err.msg})") from err
            if "ts" not in row or "text" not in row:
                raise SystemExit(f"{path}:{n}: each line needs 'ts' and 'text'")
            out.append(
                Utterance(
                    ts=str(row["ts"]),
                    text=str(row["text"]),
                    speaker=row.get("speaker"),
                    conversation_id=row.get("conversation_id"),
                )
            )
    return out


def analyze(path: str, speaker: str | None) -> list[dict]:
    utterances = _read_jsonl(path)
    if speaker is not None:
        utterances = [u for u in utterances if u.speaker == speaker]
    by_day: dict[str, list[Utterance]] = defaultdict(list)
    for u in utterances:
        by_day[u.ts[:10]].append(u)
    return [aggregate_day(by_day[d], d).to_dict() for d in sorted(by_day)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speech-vitals",
        description="Language features from everyday speech. Features only, never words.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="reduce a JSONL transcript to daily features")
    a.add_argument("path", help="JSON Lines file of {ts, text, speaker?}")
    a.add_argument("--speaker", help="keep only this speaker label")
    a.add_argument("--out", help="write JSON here instead of stdout")

    sub.add_parser("schema", help="print the feature registry with its literature basis")

    args = parser.parse_args(argv)

    if args.command == "schema":
        json.dump(features_schema(), sys.stdout, indent=1)
        sys.stdout.write("\n")
        return 0

    days = analyze(args.path, args.speaker)
    payload = json.dumps(days, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"{len(days)} day(s) written to {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
