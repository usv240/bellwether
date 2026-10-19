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
CHECKIN_DAYS = 3

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
        shows="The front page: the claim, and a simulated person's own range with the days that left it.",
        pause_before=0.8,
        say=(
            "Your watch tracks your heart. But what about changes in the way you speak? "
            "More pauses, simpler sentences, words that become harder to find. "
            "Small changes that are easy to overlook."
        ),
    ),
    Beat(
        key="gap",
        action="stats",
        shows="The three and a half years card, then what people say they want: 79 percent.",
        say=(
            "Most of us would never notice. And if we did, how would we explain it to a doctor months later? "
            "On average, dementia takes three and a half years to diagnose, "
            "and nearly four in five of us say we would want to know early."
        ),
    ),
    Beat(
        key="what",
        action="how",
        shows="How it works: wear, measure, learn, show.",
        say=(
            "Bellwether uses the Bee on your wrist to learn how you normally speak. "
            "Everyone speaks differently, so it compares you only with your own past. "
            "It keeps nine numbers a day, never your words, and it is not a diagnosis."
        ),
    ),
    Beat(
        key="term-host",
        action="term_host",
        shows="A terminal: the assistant speaking tonight's three questions while the Bee on the wrist listens; the day read from the Bee and counted; the note read back.",
        min_hold=14,
        say=(
            "Every evening, an assistant asks me three short questions out loud. "
            "My Bee records my answers. Bellwether removes the assistant's own voice, "
            "turns my speech into those nine numbers, and tells me where I stand."
        ),
    ),
    Beat(
        key="checkins",
        action="checkins",
        shows="The dashboard on the builder's own check-ins: the real-data badge, the first week filling.",
        pause_before=0.4,
        say=(
            "This is my own Bee data, live. Seven days teach it what normal sounds like for me. "
            + _days_line(CHECKIN_DAYS)
        ),
    ),
    Beat(
        key="change",
        action="simulated",
        shows="The switcher to the simulated person, labelled; the eight-week chart leaving its band; what moved and since when; then what else could explain it.",
        pause_before=0.3,
        min_hold=26,
        say=(
            "Imagine your speech changing so gradually that you don't notice. "
            "In this simulated example, Bellwether shows when the change started, which measurements shifted, "
            "and how far they've moved from that person's usual range. "
            "It also offers everyday explanations, like poor sleep, illness, or medication. "
            "It never names a condition."
        ),
    ),
    Beat(
        key="proof",
        action="proof",
        shows="The same page, with what the software was checked against on screen.",
        pause_before=0.3,
        min_hold=11,
        say=(
            "We tested Bellwether on speech we didn't write: "
            "three hundred forty-nine Supreme Court arguments with no alerts, "
            "and six hundred fifty-two presidential press conferences with fewer than three percent flagged. "
            "These tests measure software behaviour, not medical accuracy."
        ),
    ),
    Beat(
        key="mcp",
        action="alexa",
        shows="A session held against the MCP server from the page: protocol agreed, nine tools listed, the answer returned.",
        pause_before=0.3,
        min_hold=8,
        say=(
            "Bellwether also connects to AI assistants through an MCP server, built using the same standard Alexa+ supports. "
            "Assistants can ask about your speech trends, but they cannot retrieve your conversations, because Bellwether doesn't store them."
        ),
    ),
    Beat(
        key="term-agent",
        action="term_agent",
        shows="A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.",
        min_hold=8,
        say=(
            "Here a Strands agent on Amazon Bedrock asks for a monthly summary, "
            "and says the data is simulated before anything else."
        ),
    ),
    Beat(
        key="report",
        action="report",
        shows="The doctor report: the timeline, then the questions to bring, then the links.",
        pause_before=0.3,
        min_hold=12,
        say=(
            "And if something changes, Bellwether gives you a simple timeline to bring to your doctor. "
            "What changed, when it started, and what questions to ask. "
            "No diagnosis, just a clearer conversation. "
            "Open source, and working today. "
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
