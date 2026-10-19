"""The simulated first week: what the warmup looks like day by day.

    python fixtures/personas/make_first_week.py

A new wearer's real profile takes seven counted days to say anything, and
in a hackathon's last week no real profile can show day eight. This one
can, and it says what it is on every screen: SIMULATED.

It is the first ten days of the stable simulated person (alex-stable, the
production extractor and engine over generated speech), re-dated to end on
2026-10-18, with each day's word count set to the size of a two-minute
check-in. Day three is set under the 150-word floor, as happens in real
use (the builder's own 2026-10-16 came to 93 words), so the replay shows a
short day not counting and the first comparison arriving a day later
because of it. The nine features are alex-stable's own, unchanged.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "alex-stable" / "days.json"
OUT = HERE / "sam-first-week"
END = date(2026, 10, 18)
WORDS = [262, 241, 118, 288, 255, 230, 274, 266, 251, 280]


def main() -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))[: len(WORDS)]
    start = END - timedelta(days=len(WORDS) - 1)
    days = []
    for i, (row, words) in enumerate(zip(src, WORDS)):
        days.append({**row, "date": (start + timedelta(days=i)).isoformat(), "token_count_day": words})
    OUT.mkdir(exist_ok=True)
    (OUT / "days.json").write_text(json.dumps(days, indent=1) + "\n", encoding="utf-8")
    meta = {
        "label": "SIMULATED",
        "persona": "sam-first-week",
        "description": (
            "A simulated first week of check-ins. The first ten days of alex-stable (generated speech, "
            "production extractor and engine), re-dated, with word counts set to check-in sizes; day three "
            "is under the 150-word floor on purpose."
        ),
        "source": "alex-stable",
        "days": len(days),
        "start": days[0]["date"],
        "end": days[-1]["date"],
        "short_day": days[2]["date"],
        "annotations": {},
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'days.json'}: {len(days)} days, {days[0]['date']} to {days[-1]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
