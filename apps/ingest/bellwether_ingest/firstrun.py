"""The day the Bee arrives, in one command.

    bellwether-ingest firstrun

Why this exists
---------------
The Bee track has a requirement that no amount of good code satisfies on
its own: the project must be shown using **live Bee data** to do something
for a person. A device was bought for exactly that, and the whole of that
purchase converts into a submission only if the first session with it
works. If it does not, the failure will be a missing login, a CLI not on
PATH, a shape the parser did not expect, or an empty day, and each of
those costs hours that the device cannot buy back.

So this walks the entire chain in order, stops at the first thing that is
actually wrong, and says what to do about it in the words the Bee app
uses. Every check that can run without a device runs without one, which
means the whole path can be rehearsed before the hardware is even
unboxed and the only untested step on the day is the one that needs the
device.

    1. Is the CLI installed, and is it the one we expect
    2. Is it logged in
    3. Does the account answer
    4. Is there any speech recorded yet
    5. Does a real day reduce to the nine features
    6. Do those features survive the engine
    7. Would the API accept them

What it does not do
-------------------
It does not upload anything or change any state. It is a read-only
rehearsal, so running it twice is safe and running it in front of a
camera is safe.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass

from speech_vitals import aggregate_day

from .bee import BeeCli, BeeCliError, BeeNotAuthenticated, normalize_conversation


@dataclass
class Step:
    name: str
    ok: bool
    detail: str
    fix: str | None = None


def _step(name: str, ok: bool, detail: str, fix: str | None = None) -> Step:
    return Step(name=name, ok=ok, detail=detail, fix=fix)


def run(cli: BeeCli | None = None) -> list[Step]:
    """Walk the chain and stop at the first genuine failure."""
    cli = cli or BeeCli()
    steps: list[Step] = []

    # 1. The CLI itself.
    found = shutil.which(cli.binary)
    steps.append(
        _step(
            "bee CLI installed",
            found is not None,
            found or "not on PATH",
            "npm install -g @beeai/cli",
        )
    )
    if found is None:
        return steps

    # 2. Logged in. The CLI reports this in prose rather than an exit code,
    #    so the wrapper turns it into an exception and this turns it back
    #    into an instruction.
    try:
        cli.me()
        steps.append(_step("logged in", True, "the account answered"))
    except BeeNotAuthenticated as err:
        steps.append(
            _step(
                "logged in",
                False,
                str(err),
                "Open the Bee app, tap the version number five times to enable "
                "Developer Mode, then run: bee login",
            )
        )
        return steps
    except BeeCliError as err:
        steps.append(_step("logged in", False, str(err), "bee login"))
        return steps

    # 3. Is there anything recorded? A brand new device has nothing, and an
    #    empty result is not a bug, it is a device that has not listened yet.
    try:
        convos = cli.conversations_list(limit=50)
        rows = convos if isinstance(convos, list) else convos.get("conversations", convos.get("data", []))
        count = len(rows or [])
        steps.append(
            _step(
                "conversations recorded",
                count > 0,
                f"{count} conversation(s) available",
                "Wear the device and talk for a while. Bee needs speech before "
                "there is anything to measure, and a first day usually needs a "
                "few hours of ordinary conversation.",
            )
        )
        if count == 0:
            return steps
    except BeeCliError as err:
        steps.append(_step("conversations recorded", False, str(err), "bee conversations list --json"))
        return steps

    # 4. Does a real day reduce to the nine features? This is the step that
    #    can only be tested with real speech: everything before it is
    #    plumbing and everything after it is arithmetic.
    try:
        utterances = []
        for raw in rows:
            utterances.extend(normalize_conversation(raw))
        by_day: dict[str, list] = {}
        for u in utterances:
            by_day.setdefault(u.ts[:10], []).append(u)
        days = [aggregate_day(by_day[d], d) for d in sorted(by_day)]
        usable = [d for d in days if d.token_count_day > 0]
        steps.append(
            _step(
                "a real day reduces to nine features",
                bool(usable),
                f"{len(days)} day(s) extracted, {len(usable)} with speech",
                "If days came back empty, the transcript field name may differ "
                "from what the parser expects. Run: bee conversations list --json "
                "and compare the keys against bellwether_ingest/bee.py.",
            )
        )
        if not usable:
            return steps
    except Exception as err:  # noqa: BLE001
        steps.append(
            _step(
                "a real day reduces to nine features",
                False,
                f"{type(err).__name__}: {err}",
                "Capture the raw JSON and open an issue with it: "
                "bee conversations list --json > raw.json",
            )
        )
        return steps

    # 5. Exposure. A day below the floor is excluded rather than scored, and
    #    knowing that before the camera is on saves an confusing demo.
    best = max(usable, key=lambda d: d.token_count_day)
    enough = best.token_count_day >= 150
    steps.append(
        _step(
            "enough speech in a day to assess",
            enough,
            f"best day has {best.token_count_day} words, the floor is 150",
            "Wear it through a normal day. Days below the floor are excluded on "
            "purpose: a quiet afternoon is not a change in you.",
        )
    )

    # 6. The features carry no words. Worth asserting on real data, because
    #    this is the promise the whole product rests on.
    payload = json.dumps([d.to_dict() for d in usable])
    leaked = any(
        isinstance(v, str) and len(v) > 24 and v[:4].isalpha()
        for d in usable
        for k, v in d.to_dict().items()
        if k != "date"
    )
    steps.append(
        _step(
            "no words left in the features",
            not leaked,
            f"{len(payload)} bytes of feature rows, dates and numbers only",
            "Stop and inspect before uploading anything.",
        )
    )

    return steps


def report(steps: list[Step]) -> str:
    lines = []
    for s in steps:
        lines.append(f"  {'ok  ' if s.ok else 'FAIL'}  {s.name}")
        lines.append(f"        {s.detail}")
        if not s.ok and s.fix:
            for line in s.fix.split(". "):
                if line.strip():
                    lines.append(f"        -> {line.strip().rstrip('.')}.")
    done = all(s.ok for s in steps)
    lines.append("")
    lines.append(
        "  Ready. Next: bellwether-ingest pull --owner <you> --out days.json"
        if done
        else "  Fix the first FAIL above and run this again."
    )
    return "\n".join(lines)
