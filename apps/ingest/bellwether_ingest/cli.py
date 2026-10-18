"""Command line for ingestion.

    bellwether-ingest status
    bellwether-ingest mine                                  # a wearer's first day, in one command
    bellwether-ingest pull  --out days.json [--owner speaker_1] [--cursor-file .bee-cursor] [--now | --backfill | --journals]
    bellwether-ingest pull  --checkins --post me-voice      # the wearer's check-ins, straight to the service
    bee stream --json --types new-utterance | bellwether-ingest stream --out days.json

Every command ends the same way: utterances are reduced with
``speech_vitals.aggregate_day`` and only the resulting day features are
written. The cursor is saved after the features are, so a crash between the
two re-fetches rather than skips.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict

from speech_vitals import Utterance, aggregate_day

from .bee import (
    BeeCli,
    BeeCliError,
    BeeNotAuthenticated,
    CursorStore,
    OwnerFilter,
    ingest_backfill,
    ingest_changed,
    ingest_checkins,
    ingest_journals,
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


DEFAULT_API = "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws"


def post_days(days: list[dict], profile: str, api: str, key: str | None = None) -> dict:
    """Send day feature rows to the service. Only the rows travel: the
    same nine numbers, count and date that --out writes, never text. A
    claimed profile needs its key, sent as a header and never in the URL."""
    headers = {"content-type": "application/json"}
    if key:
        headers["x-bellwether-key"] = key
    req = urllib.request.Request(
        f"{api.rstrip('/')}/v1/profiles/{profile}/days",
        data=json.dumps(days).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read())


def claim_profile(profile: str, api: str, key: str) -> str:
    """Make a profile the wearer's. Returns "claimed", "already" (by this
    key or another; the first post will tell) or raises."""
    req = urllib.request.Request(
        f"{api.rstrip('/')}/v1/profiles/{profile}/claim",
        data=json.dumps({"key": key}).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            return "claimed"
    except urllib.error.HTTPError as err:
        if err.code == 409:
            return "already"
        raise


KEY_FILE = ".bellwether-key"


def load_or_make_key(path: str = KEY_FILE) -> str:
    """The wearer's key lives on the wearer's machine, in a file next to
    their day features, and is made once. Only its hash ever leaves."""
    import secrets

    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            key = fh.read().strip()
        if len(key) >= 16:
            return key
    key = secrets.token_urlsafe(24)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(key + "\n")
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bellwether-ingest", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="is bee installed and logged in?")

    mine = sub.add_parser("mine", help="your first day: read your Bee, send the numbers, open your page")
    mine.add_argument("--max-minutes", type=float, default=60)
    mine.add_argument("--days", type=int, default=None,
                      help="read only the last N days (a daily run); earlier days stay on the service as they were")
    mine.add_argument("--api", default=os.environ.get("BELLWETHER_API", DEFAULT_API))
    mine.add_argument("--remind", action="store_true",
                      help="if today's voice notes are short, add a todo on your Bee asking for the note")
    mine.add_argument("--profile", default=os.environ.get("BELLWETHER_PROFILE", "me"),
                      help="your profile name on the service; your check-ins go to <name>-voice")
    mine.add_argument("--key-file", default=KEY_FILE,
                      help="where your profile key lives; made on first run, only its hash leaves")

    sub.add_parser(
        "firstrun",
        help="rehearse the whole chain the day the device arrives, read only",
    )

    ev = sub.add_parser(
        "evidence",
        help="write a publishable record that live Bee data flowed, no speech in it",
    )
    ev.add_argument("--out", default="docs/BEE_LIVE.md")

    pull = sub.add_parser("pull", help="fetch what changed since last run and reduce it to day features")
    pull.add_argument("--owner", help="the wearer's speaker label; defaults to the most frequent speaker")
    pull.add_argument("--cursor-file", default=".bee-cursor")
    pull.add_argument("--now", action="store_true", help="use bee now (recent hours) instead of bee changed")
    pull.add_argument("--backfill", action="store_true",
                      help="every conversation on the account, not just recent changes")
    pull.add_argument("--journals", action="store_true",
                      help="the wearer's Bee voice notes only: certain to be their own speech")
    pull.add_argument("--checkins", action="store_true",
                      help="each voice note plus the band's session it anchors: the wearer talking to the band on purpose")
    pull.add_argument("--max-minutes", type=float, default=None,
                      help="with --backfill, skip conversations longer than this and any Bee "
                           "summarises as media; for accounts whose speakers are all Unknown")
    pull.add_argument("--out", help="write day features JSON here")
    pull.add_argument("--post", metavar="PROFILE", help="also send the day features to this profile on the service")
    pull.add_argument("--api", default=os.environ.get("BELLWETHER_API", DEFAULT_API))
    pull.add_argument("--key", default=os.environ.get("BELLWETHER_KEY"),
                      help="the profile's key, if it is claimed; or set BELLWETHER_KEY")

    stream = sub.add_parser("stream", help="reduce bee stream --json events from stdin")
    stream.add_argument("--owner")
    stream.add_argument("--out")

    tf = sub.add_parser("file", help="no Bee needed: your own words from Zoom or Teams .vtt, Otter .txt, or 'Name: text' files")
    tf.add_argument("paths", nargs="+", help="one or more transcript files; one file is one meeting")
    tf.add_argument("--speaker", help="your name as the transcript prints it; omit to list the names in the files")
    tf.add_argument("--date", help="YYYY-MM-DD for files with no date in their name; default is the file's modified date")
    tf.add_argument("--out", help="write day features JSON here")
    tf.add_argument("--post", metavar="PROFILE", help="also send the day features to this profile on the service")
    tf.add_argument("--api", default=os.environ.get("BELLWETHER_API", DEFAULT_API))
    tf.add_argument("--key", default=os.environ.get("BELLWETHER_KEY"))

    args = parser.parse_args(argv)

    if args.command == "file":
        from pathlib import Path

        from .transcripts import speakers, utterances_from

        files = [Path(p) for p in args.paths]
        missing = [str(f) for f in files if not f.is_file()]
        if missing:
            print(f"not found: {', '.join(missing)}", file=sys.stderr)
            return 2
        if not args.speaker:
            # Names and word counts only; never a word of what was said.
            from collections import Counter

            total: Counter = Counter()
            for f in files:
                total.update(speakers(f.read_text(encoding="utf-8", errors="replace")))
            if not total:
                print("no speaker-labelled turns found in these files", file=sys.stderr)
                return 4
            print("Speakers in these files, by words spoken. Run again with --speaker \"<your name>\":", file=sys.stderr)
            for name, words in total.most_common():
                print(f"  {name}: {words} words", file=sys.stderr)
            return 0
        utts = [u for f in files for u in utterances_from(f, args.speaker, args.date)]
        if not utts:
            print(f"no turns by {args.speaker!r} in these files; run without --speaker to see the names", file=sys.stderr)
            return 4
        days = reduce_to_days(utts)
        _write_days(days, args.out)
        if args.post and days:
            res = post_days(days, args.post, args.api, args.key)
            print(f"posted {res['stored']} day(s) to {args.post}: {res['tier']}, "
                  f"{res['eligible_days']} day(s) count", file=sys.stderr)
        return 0

    cli = BeeCli()

    if args.command == "mine":
        from .mine import first_day

        key = load_or_make_key(args.key_file)
        return first_day(cli, post=lambda days, profile: post_days(days, profile, args.api, key), reduce=reduce_to_days,
                         max_minutes=args.max_minutes, remind=args.remind, profile=args.profile,
                         claim=lambda profile: claim_profile(profile, args.api, key), days=args.days)

    if args.command == "evidence":
        from .evidence import capture, to_markdown

        data = capture(cli)
        text = to_markdown(data)
        with open(args.out, "w", encoding="utf8", newline="\n") as fh:
            fh.write(text)
        print(f"Wrote {args.out}: {data['totals']['wordsSeen']} words read, "
              f"{data['totals']['wordsPublished']} published.")
        return 0 if any(c["ok"] for c in data["calls"]) else 1

    if args.command == "firstrun":
        # Read only, so it is safe to run twice and safe to run on camera.
        from .firstrun import report, run

        steps = run(cli)
        print(report(steps))
        return 0 if all(step.ok for step in steps) else 1

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
            elif args.journals:
                utterances, new_cursor = ingest_journals(cli), None
            elif args.checkins:
                utterances, new_cursor = ingest_checkins(cli), None
            elif args.backfill:
                utterances, new_cursor = ingest_backfill(cli, owner, max_minutes=args.max_minutes), None
            else:
                utterances, new_cursor = ingest_changed(cli, cursors, owner)
            days = reduce_to_days(utterances)
            _write_days(days, args.out)
            if args.post and days:
                res = post_days(days, args.post, args.api, args.key)
                print(f"posted {res['stored']} day(s) to {args.post}: {res['tier']}, "
                      f"{res['eligible_days']} day(s) count", file=sys.stderr)
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
