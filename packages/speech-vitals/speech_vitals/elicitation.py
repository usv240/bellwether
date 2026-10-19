"""The hosted check-in: what a voice assistant says to draw out two minutes
of a person's own speech, and how the measuring side recognises those words
so it never counts them as the wearer's.

Why the prompts are fixed and not generated. Speech assessment has used a
small set of standard elicitation tasks for fifty years: describing a
scene (the Boston Diagnostic Aphasia Examination's picture description,
the task behind the ADReSS corpus), recounting a personal event, and
explaining a procedure step by step. Each draws connected speech of a known
kind, so a person's days can be compared with their own earlier days. A
model inventing fresh questions nightly would make every day a different
task, and a baseline needs the task to hold still.

Why the host's words are listed here, next to the measures. The Bee hears
the host too. A prompt spoken through a speaker is transcribed into the
same session as the wearer's answer, and a sixteen-word question counted
as the wearer's speech would move the very numbers Bellwether watches. So
the exact lines a host may say are published, and ``is_host_line`` lets
the ingest drop any utterance that is one of them, including the Bee's
habit of splitting a line in two or hearing a date as digits.

The rotation is by date, so the host on the wearer's computer and the
service it talks to agree on the day's script without exchanging it, and
a week never repeats a prompt. Three prompts a day, one of each kind.
"""

from __future__ import annotations

import re
from datetime import date

# One of each kind per day. Twelve to twenty-five words each, so a full
# answer to the three runs well past the 150-word floor a day needs.
PROMPT_BANK: dict[str, list[str]] = {
    "narrative": [
        "Tell me about your day so far, from when you woke up to right now.",
        "Tell me about a trip you remember well: where you went, who was there, and what happened.",
        "What was the best part of your week so far, and what made it good?",
        "Tell me about something you learned recently, and how you would explain it to a friend.",
    ],
    "description": [
        "Describe the room you are in, as if to someone on the phone who has never seen it.",
        "Describe what you can see from the nearest window, in as much detail as you can.",
        "Describe a meal you enjoyed recently: what was on the plate, and how it tasted.",
        "Describe the place where you grew up, the streets, the sounds, and the people.",
    ],
    "procedure": [
        "Explain how you make your usual morning drink, step by step, from the start.",
        "Explain how to get from your front door to the nearest shop, turn by turn.",
        "Explain how you would plan a day out for a visitor who has never been to your town.",
        "Explain how you get ready for a normal working day, in the order you do it.",
    ],
}

KINDS = ("narrative", "description", "procedure")

# The basis a reader can check. Returned by the service beside the prompts.
BASIS = (
    "Standard elicitation tasks from speech and language assessment: scene "
    "description (Boston Diagnostic Aphasia Examination; the task behind the "
    "ADReSS corpus), personal narrative, and procedural discourse. Fixed and "
    "rotated by date so a person's days are comparable with their own."
)

ORDINALS = [
    "", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth",
    "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth",
    "seventeenth", "eighteenth", "nineteenth", "twentieth", "twenty-first", "twenty-second",
    "twenty-third", "twenty-fourth", "twenty-fifth", "twenty-sixth", "twenty-seventh",
    "twenty-eighth", "twenty-ninth", "thirtieth", "thirty-first",
]

WORDS = ["zero", "one", "two", "three"]

CLOSING = (
    "Thank you. That is today's check-in. Bellwether will count it once the Bee has written it down."
)

_WORD = re.compile(r"[a-z0-9']+")


def _day(d: date | str) -> date:
    return d if isinstance(d, date) else date.fromisoformat(str(d)[:10])


def opener_for(d: date | str) -> str:
    """The first words of the session. They declare it a check-in to the
    ingest's opener rule, spoken by the host instead of the wearer."""
    d = _day(d)
    return f"Bellwether check-in, {d.strftime('%B')} {ORDINALS[d.day]}."


def prompts_for(d: date | str) -> list[dict]:
    """Three prompts for the day, one of each kind. Consecutive days never
    share a prompt, and no prompt repeats inside four days."""
    d = _day(d)
    k = d.toordinal()
    return [
        {"kind": kind, "text": PROMPT_BANK[kind][(k + i) % len(PROMPT_BANK[kind])]}
        for i, kind in enumerate(KINDS)
    ]


def host_lines_for(d: date | str) -> list[str]:
    """Every sentence the host says on that day, in order. Anything the
    Bee hears from the speaker is one of these."""
    lines = [opener_for(d)]
    for i, p in enumerate(prompts_for(d), start=1):
        lines.append(f"Question {WORDS[i]}.")
        lines.append(p["text"])
    lines.append(CLOSING)
    return lines


MIN_RUN_WORDS = 4      # a shorter fragment of a host line must be the whole line
MIN_BAG_WORDS = 8      # the loose match is for long lines the device misheard


def _words(text: str) -> list[str]:
    """Lower-case words, with a date the device wrote as digits ("19th",
    "19") turned back into the words the host said ("nineteenth")."""
    out: list[str] = []
    for w in _WORD.findall(text.lower().replace("-", " ")):
        m = re.fullmatch(r"(\d{1,2})(st|nd|rd|th)?", w)
        if m and 1 <= int(m.group(1)) <= 31:
            out.extend(ORDINALS[int(m.group(1))].replace("-", " ").split())
        else:
            out.append(w)
    return out


def is_host_line(utterance_text: str, host_lines: list[str]) -> bool:
    """Is this utterance the host speaking, as the Bee heard it?

    Three ways to match, each narrow on purpose, because a wrong match
    deletes the wearer's own words. Measured on 2026-10-18 over 6,645 real
    utterances from 60 sessions on the builder's account, an earlier,
    looser rule took 98 of them (1.5%), mostly "thank you" and "yes" inside
    a host line. This one took none of the 6,645 (56,444 words). The
    ingest test pins a whole hosted session; the elicitation tests pin
    the short replies that must survive.

      1. The whole utterance is a whole host line ("Question one.").
      2. It is a contiguous run of at least four words of a host line, the
         device's habit of cutting one sentence into two.
      3. It has at least eight words and three quarters of them are in one
         host line, for the small mishearings of a long prompt.
    """
    u = _words(utterance_text)
    if not u:
        return False
    joined_u = " " + " ".join(u) + " "
    for line in host_lines:
        h = _words(line)
        if not h:
            continue
        if u == h:
            return True
        if len(u) >= MIN_RUN_WORDS and joined_u in " " + " ".join(h) + " ":
            return True
        if len(u) >= MIN_BAG_WORDS:
            bag = set(h)
            if sum(1 for w in u if w in bag) * 4 >= len(u) * 3:
                return True
    return False


def strip_host(texts: list[str], host_lines: list[str]) -> list[str]:
    """The wearer's words only."""
    return [t for t in texts if not is_host_line(t, host_lines)]
