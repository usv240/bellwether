"""The demo video as data, not prose.

One record per beat: the pause before it, what the recorder should do,
what is on screen, and the exact line Polly will say. Nothing else in
the pipeline may invent a timecode; every downstream step derives its
timing from here, and after recording, from where each beat actually
landed.

The human-readable script is docs/VIDEO_SCRIPT.md, and it is written by
this file: `python beats.py --script` regenerates it.

Two cameras
-----------
Most beats are the deployed website driven by a real browser at 4K. Two
beats are a terminal: real commands run against the builder's own Bee
and the deployed server, their real output rendered in a terminal frame
the same recorder captures. `action` starting with `term_` means terminal
footage, and the frame says on screen that it is a rendering of a real
run.

The day count
-------------
Beat five says how many days of check-ins the baseline holds. That is a
fact about the live service on the day of the take, so it is a constant
here, CHECKIN_DAYS, and `record.py` refuses to record if the service says
anything else. The narration cannot drift from the screen it is spoken
over.

The hard constraint
-------------------
Three minutes, and judges are not required to watch past it. `python
beats.py` prints the estimate and exits non-zero if the plan is over.

What the order is for
---------------------
A judge who watches only the first fifteen seconds should leave with one
sentence: speech is where a change in the brain shows first, and nothing
measures it. Then the gap it costs, what Bellwether is and is not, the
builder's own Bee doing it, honestly labelled, what change looks like on
a simulated person, the assistant, and the page for the doctor.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Patrick, long-form, at the rate narrate.py asks for, measured on the
# sibling videos: 146 words a minute. A gate before recording only.
WORDS_PER_MINUTE = 146
CEILING_SECONDS = 180

# Days of check-ins the live baseline holds on the day of the take. Set it
# before narrating; record.py checks it against the service.
CHECKIN_DAYS = 2

_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven"]


def _days_line(n: int) -> str:
    if n >= 7:
        return "Seven days in, and every new day is compared with them. Stable, and it says so plainly instead of hunting for something to report."
    more = 7 - n
    return (
        f"{_WORDS[n].capitalize()} day{'s' if n != 1 else ''} in. "
        f"{_WORDS[more].capitalize()} more and it compares. "
        "Until then it says so, instead of hunting for something to report."
    )


@dataclass
class Beat:
    key: str
    say: str
    action: str
    shows: str = ""
    pause_before: float = 0.0
    min_hold: float = 0.0

    @property
    def is_terminal(self) -> bool:
        return self.action.startswith("term_")

    # The assembler and recorder were written for a second camera called
    # "tv"; the terminal is that camera here.
    @property
    def is_tv(self) -> bool:
        return self.is_terminal

    @property
    def speak_seconds(self) -> float:
        return len(self.say.split()) / WORDS_PER_MINUTE * 60

    @property
    def seconds(self) -> float:
        return max(self.pause_before + self.speak_seconds, self.min_hold)


BEATS: list[Beat] = [
    Beat(
        key="hook",
        action="hero",
        shows="The front page: the claim, and a simulated person's own range with the days that left it.",
        pause_before=0.8,
        say=(
            "Your watch knows when your heart skips a beat. Nothing knows when your brain does. "
            "When something changes there, speech usually shows it first: "
            "more pauses, simpler sentences, words that will not come."
        ),
    ),
    Beat(
        key="gap",
        action="stats",
        shows="The four figures under the problem; the three and a half years card first.",
        say=(
            "Across all dementias, the average wait from first symptoms to a diagnosis is three and a half years. "
            "The newest treatments only work at the earliest stage. That wait skips straight past it."
        ),
    ),
    Beat(
        key="what",
        action="how",
        shows="How it works: wear, measure, learn, show.",
        say=(
            "Bellwether is not a diagnosis and not a medical device. "
            "It learns how one person normally speaks, and tells them when that changes. "
            "Only against your own past, never against anyone else."
        ),
    ),
    Beat(
        key="term-mine",
        action="term_mine",
        shows="A terminal: bellwether-ingest mine against the builder's own Bee, the days it read, the days that count, the page to open.",
        min_hold=12,
        say=(
            "This is my Bee. Each day I check in: two minutes of talking to the band on my own. "
            "One command turns each day into nine numbers on my computer and throws the words away. "
            "Anyone can do the same with their own Bee, and a free key keeps the profile theirs."
        ),
    ),
    Beat(
        key="checkins",
        action="checkins",
        shows="The dashboard on the builder's own check-ins: the real-data badge, the first week filling.",
        pause_before=0.4,
        say=(
            "My own baseline, from real Bee data. "
            "Seven days teach it what normal sounds like for me; every day after is compared with them. "
            + _days_line(CHECKIN_DAYS)
        ),
    ),
    Beat(
        key="room",
        action="conversations",
        shows="The switcher to the band's conversations, the note under the badge saying what that stream is.",
        pause_before=0.3,
        say=(
            "The band also hears everyone around me, and Bee does not yet say who was talking. "
            "So that stream is kept separate and labelled for what it is: "
            "three weeks of everyday conversation, also stable."
        ),
    ),
    Beat(
        key="change",
        action="simulated",
        shows="The switcher to the simulated person, labelled; then what else could explain a change.",
        pause_before=0.3,
        say=(
            "To show what change looks like: a simulated person, labelled on every screen. "
            "Before the chart, the ordinary explanations: a bad week of sleep, a cold, a new medication. "
            "They explain far more changes than anything worrying, so they get the same space as the result."
        ),
    ),
    Beat(
        key="moved",
        action="chart",
        shows="The eight-week chart, then the measures that moved.",
        say="When it does flag something, it says which measures moved, in which direction, and since when.",
    ),
    Beat(
        key="mcp",
        action="alexa",
        shows="A session held against the MCP server from the page, every request answered by the deployed server.",
        pause_before=0.3,
        min_hold=9,
        say=(
            "All of this is also a Model Context Protocol server over Streamable HTTP, the way Alexa+ talks to tools. "
            "Seven tools, and none can return a transcript, because none exists."
        ),
    ),
    Beat(
        key="term-agent",
        action="term_agent",
        shows="A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.",
        min_hold=10,
        say=(
            "A Strands agent on Amazon Bedrock asks how the week went. "
            "It says the data is simulated before anything else, and it may never name a condition."
        ),
    ),
    Beat(
        key="report",
        action="report",
        shows="The doctor report, then the links.",
        pause_before=0.3,
        min_hold=12,
        say=(
            "This is the point. One page for a twelve-minute appointment: what changed, when, what moved, "
            "and in full, that this is not a diagnosis. Open source, live at the link. "
            "Bellwether. Your own normal, in your own numbers."
        ),
    ),
]


def sentences(line: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]


def sentence_spans(line: str, total: float) -> list[tuple[float, float]]:
    """Where each sentence starts and ends, proportionally by word count."""
    parts = sentences(line)
    words = [len(s.split()) for s in parts]
    all_words = sum(words) or 1
    spans, at = [], 0.0
    for w in words:
        dur = total * w / all_words
        spans.append((at, at + dur))
        at += dur
    return spans


def script() -> str:
    """docs/VIDEO_SCRIPT.md, from the beats, so it cannot be stale."""
    out = [
        "# Demo video script",
        "",
        "Under three minutes, public, English. Judges are not required to watch",
        "past 3:00, so the strongest material is first.",
        "",
        "This file is written by `python video/beats.py --script` from the same",
        "data the recorders and the assembler read. Edit `video/beats.py`, not",
        "this file.",
        "",
        "---",
        "",
        "## Shot list",
        "",
    ]
    at = 0.0
    for b in BEATS:
        cam = "a terminal, a real run rendered" if b.is_terminal else "the website, in a real browser"
        m, sec = divmod(int(at), 60)
        out += [f"**{m}:{sec:02d}, {b.key}, {cam}**", "", b.shows, "", "> " + b.say, ""]
        at += b.seconds
    m, sec = divmod(int(at), 60)
    out += [
        f"Estimated {m}:{sec:02d} of a 3:00 ceiling. The real narration decides the",
        "final cut.",
        "",
        "## The terminal beats",
        "",
        "Two beats show real commands: `bellwether-ingest mine` against the",
        "builder's own Bee, and the Strands agent against the deployed MCP",
        "server. `record_term.py capture` runs them for real and keeps their",
        "output and how long they took; `render` types them at a human pace in",
        "a terminal frame the same 4K recorder captures, prints the saved",
        "output, and says how long each run really took. The frame says it is",
        "a rendering of a real run.",
        "",
        "## What not to say",
        "",
        "Any sentence in which Bellwether detects, screens for, predicts or",
        "indicates a condition. \"Early detection.\" \"Accurate\" or a percentage",
        "about Bellwether itself. Any number not in docs/EVIDENCE.md. Anything",
        "implying the simulated person is real, or that the conversation stream",
        "is the builder's own speech.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    if "--script" in sys.argv:
        dest = Path(__file__).parent.parent / "docs" / "VIDEO_SCRIPT.md"
        dest.write_text(script(), encoding="utf8")
        print(f"wrote {dest}")
        return 0
    total = 0.0
    for b in BEATS:
        cam = "term" if b.is_terminal else "web "
        print(f"  {b.key:12} {cam}  {b.seconds:5.1f}s  {b.say[:58]}...")
        total += b.seconds
    print(f"\nestimated {total:.0f}s of {CEILING_SECONDS}s, {CEILING_SECONDS - total:.0f}s headroom")
    return 0 if total <= CEILING_SECONDS else 1


if __name__ == "__main__":
    raise SystemExit(main())
