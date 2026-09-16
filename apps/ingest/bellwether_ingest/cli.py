"""Command line for ingestion.

    bellwether-ingest status
    bellwether-ingest pull  --out days.json [--owner speaker_1] [--cursor-file .bee-cursor] [--now]
    bee stream --json --types new-utterance | bellwether-ingest stream --out days.json

Every command ends the same way: utterances are reduced with
``speech_vitals.aggregate_day`` and only the resulting day features are
written. The cursor is saved after the features are, so a crash between the
two re-fetches rather than skips.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from speech_vitals import Utterance, aggregate_day

from .bee import (
    BeeCli,
    BeeCliError,
    BeeNotAuthenticated,
    CursorStore,
    OwnerFilter,
    ingest_changed,
    ingest_now,
    parse_stream_line,
)


def reduce_to_days(utterances: list[Utterance]) -> list[dict]:
    by_day: dict[str, list[Utterance]] = defaultdict(list)
    for u in utterances:
        by_day[u.ts[:10]].append(u)
    return [aggregate_day(by_day[d], d).to_dict() for d in sorted(by_day)]


def _write_days(days: list[dict], out: str | None) -> None:
    payload = json.dumps(days, indent=1)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(f"{len(days)} day(s) of features written to {out}", file=sys.stderr)
    else:
        print(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bellwether-ingest", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="is bee installed and logged in?")

    pull = sub.add_parser("pull", help="fetch what changed since last run and reduce it to day features")
    pull.add_argument("--owner", help="the wearer's speaker label; defaults to the most frequent speaker")
    pull.add_argument("--cursor-file", default=".bee-cursor")
    pull.add_argument("--now", action="store_true", help="use bee now (recent hours) instead of bee changed")
    pull.add_argument("--out", help="write day features JSON here")

    stream = sub.add_parser("stream", help="reduce bee stream --json events from stdin")
    stream.add_argument("--owner")
    stream.add_argument("--out")

    args = parser.parse_args(argv)
    cli = BeeCli()

    if args.command == "status":
        if not cli.installed():
            print("bee is not installed: npm install -g @beeai/cli", file=sys.stderr)
            return 2
        print(cli.status_text())
        return 0

    owner = OwnerFilter(getattr(args, "owner", None))

    try:
        if args.command == "pull":
            cursors = CursorStore(args.cursor_file)
            if args.now:
                utterances, new_cursor = ingest_now(cli, owner), None
            else:
                utterances, new_cursor = ingest_changed(cli, cursors, owner)
            days = reduce_to_days(utterances)
            _write_days(days, args.out)
            if new_cursor:
                cursors.save(new_cursor)
            return 0

        if args.command == "stream":
            utterances = [u for u in (parse_stream_line(l) for l in sys.stdin) if u]
            days = reduce_to_days(owner.apply(utterances))
            _write_days(days, args.out)
            return 0
    except BeeNotAuthenticated as err:
        print(str(err), file=sys.stderr)
        return 3
    except BeeCliError as err:
        print(str(err), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
