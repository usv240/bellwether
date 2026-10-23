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
CHECKIN_DAYS = 7

_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven"]


def _days_line(n: int) -> str:
    if n >= 7:
        return "Seven days counted, and every new day is compared with them."
    more = 7 - n
    return (
        f"{_WORDS[n].capitalize()} day{'s' if n != 1 else ''} counted. "
        f"{_WORDS[more].capitalize()} more and it starts comparing."
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
        shows="Three tiles over the front page: Bee captures speech, Bellwether finds changes, a doctor report supports the conversation; then the page under them.",
        pause_before=0.8,
        min_hold=16,
        say=(
            "Your Bee already captures your conversations. "
            "Bellwether looks for changes in how you speak over time, "
            "and turns them into something useful for a conversation with your doctor. "
            "Nine numbers a day, never your words, and not a diagnosis."
        ),
    ),
    Beat(
        key="gap",
        action="stats",
        shows="The three and a half years card, then what people say they want: 79 percent.",
        say=(
            "Most of us would never notice, and months later could not describe it to a doctor. "
            "Dementia takes three and a half years to diagnose on average, "
            "and nearly four in five of us would want to know early."
        ),
    ),
    Beat(
        key="term-host",
        action="term_host",
        shows="A terminal: the assistant speaking tonight's three questions while the Bee on the wrist listens; the day read from the Bee and counted; the note read back. Tonight's real run.",
        min_hold=14,
        say=(
            "Every evening, an assistant asks me three short questions out loud. "
            "My Bee records my answers. On my own computer, Bellwether removes the assistant's voice, "
            "keeps nine numbers, and throws the words away."
        ),
    ),
    Beat(
        key="checkins",
        action="checkins",
        shows="The dashboard on the builder's own check-ins: the real-data badge, seven of seven days, then the one command that gives anyone their own profile.",
        pause_before=0.4,
        say=(
            "This is my own Bee data, live. "
            + _days_line(CHECKIN_DAYS)
            + " Anyone with a Bee can do the same, with one command and a key of their own."
        ),
    ),
    Beat(
        key="compare",
        action="compare",
        shows="Two simulated people side by side, labelled: the stable one with nothing flagged, the changing one with a persistent change since September; then the changing person's chart with the late days ringed; then what else could explain it.",
        pause_before=0.3,
        min_hold=24,
        say=(
            "Two simulated people, labelled as such. One speaks the same way week after week: nothing is flagged. "
            "The other changes so gradually they would never notice, and Bellwether shows when it started, "
            "which measures moved, and how far. "
            "It offers everyday explanations first, like poor sleep, illness or medication. It never names a condition."
        ),
    ),
    Beat(
        key="report",
        action="report",
        shows="The doctor report: the timeline, then the questions to bring.",
        pause_before=0.3,
        min_hold=11,
        say=(
            "And when something changes, Bellwether gives you a simple timeline to bring to your doctor: "
            "what changed, when it started, and which questions to ask."
        ),
    ),
    Beat(
        key="mcp",
        action="alexa",
        shows="A session held against the MCP server from the page: protocol agreed, the tools listed, the answer returned.",
        pause_before=0.3,
        min_hold=8,
        say=(
            "Bellwether also connects to assistants through an MCP server, on the standard Alexa+ uses. "
            "An assistant can ask about your trends, never your conversations, because Bellwether never stored them."
        ),
    ),
    Beat(
        key="term-agent",
        action="term_agent",
        shows="A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.",
        min_hold=8,
        say=(
            "Here a Strands agent on Amazon Bedrock asks for a month's summary, "
            "and says the data is simulated before anything else."
        ),
    ),
    Beat(
        key="aws",
        action="aws",
        shows="One line of four boxes: Bee, local analysis on the wearer's computer, AWS (Lambda, DynamoDB, Bedrock, AgentCore), the dashboard and report.",
        pause_before=0.3,
        min_hold=12,
        say=(
            "Speech is analysed on my own computer. AWS Lambda and Amazon DynamoDB hold the nine numbers a day, "
            "and Claude on Amazon Bedrock phrases the weekly note from those numbers alone."
        ),
    ),
    Beat(
        key="proof",
        action="proof",
        shows="Three checked facts beside the chart: real Bee data from the wearer's own band; words that never leave the computer; three hundred tests and the Supreme Court run with zero false alarms.",
        pause_before=0.3,
        min_hold=14,
        say=(
            "Checked, not claimed: real Bee data from my own band; words that never leave my computer; "
            "and three hundred automated tests, with three hundred forty-nine Supreme Court sessions and zero false alarms. "
            "Software behaviour, not medical accuracy."
        ),
    ),
    Beat(
        key="close",
        action="close",
        shows="The changing person's chart, then the doctor report, then the final card with the product name and the last line.",
        pause_before=0.3,
        min_hold=26,
        say=(
            "Imagine noticing small changes in how someone you love speaks, with no way to tell whether they are becoming a pattern. "
            "Bellwether turns those moments into a clearer picture to bring to the doctor, instead of memory alone. "
            "It does not diagnose. It helps you notice a change, understand it, and start a better conversation with a clinician. "
            "Because sometimes the first step is simply noticing."
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
