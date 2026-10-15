"""A wearer's first day, in one command.

    bellwether-ingest mine

Why this exists
---------------
Every other command here is a tool: pull this, post that, with a flag for
each thing Bee does and does not give. A person whose mother has just
put the band on does not want tools. They want one command that reads
her Bee, sends the numbers and nothing else, and opens her own page, and
that says what is missing in the words the Bee app uses.

What it does, in order
----------------------
    1. Is the CLI installed and logged in (the words from the Bee app if not)
    2. Read the check-ins: each voice note and the band's session it anchors
    3. Read the everyday conversations, sessions over an hour and media left out
    4. Reduce both to nine numbers a day, here; the words go no further
    5. Send the numbers to the wearer's two profiles
    6. Print the page to open, and how many days count so far
    7. With --remind, and only if today is short: a todo on the wearer's
       own Bee asking for a check-in, which the app shows

Only step 5 uses the network, and only the day rows travel. Nothing is
printed that could carry a word of speech: counts, dates and a URL.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from .bee import BeeCli, BeeCliError, BeeNotAuthenticated, OwnerFilter, ingest_backfill, ingest_checkins

SITE = "https://d1xfuyog8wiuvf.cloudfront.net"
MIN_WORDS = 150  # the engine's floor for a day to count; speech_vitals min_tokens

VOICE_PROFILE = "me-voice"
TALK_PROFILE = "me"


@dataclass
class Stream:
    profile: str
    label: str
    days: list[dict] = field(default_factory=list)
    posted: dict | None = None

    @property
    def counted(self) -> int:
        return sum(1 for d in self.days if d["token_count_day"] >= MIN_WORDS)


REMINDER_PREFIX = "Bellwether:"


def remind_on_the_bee(cli: BeeCli, words_today: int, log) -> bool:
    """Put the day's ask where the wearer will see it: a todo on their
    own Bee, which the app shows and can alarm. Only when the day is
    short, and never twice; an open Bellwether todo is left alone. The
    text carries a number and no words of speech."""
    if words_today >= MIN_WORDS:
        return False
    try:
        payload = cli.todos_list(limit=50)
    except BeeCliError:
        payload = {}
    items = payload.get("todos") if isinstance(payload, dict) else payload
    for raw in items or []:
        if isinstance(raw, dict) and str(raw.get("text", "")).startswith(REMINDER_PREFIX) and not raw.get("completed"):
            return False
    need = MIN_WORDS - words_today
    cli.todos_create(f"{REMINDER_PREFIX} check in: a short voice note, then two minutes of talking ({need} more words for today to count)")
    log("A reminder was added to your Bee's todos.")
    return True


def first_day(
    cli: BeeCli,
    post,
    reduce,
    max_minutes: float = 60,
    log=lambda s: print(s, file=sys.stderr),
    remind: bool = False,
) -> int:
    """Run the whole first day. ``post(days, profile)`` sends rows and
    returns the service's answer; ``reduce(utterances)`` makes day rows.
    Both are injected so the path is testable without a network or a
    device. Returns the exit code."""
    if not cli.installed():
        log("The Bee CLI is not installed. Run: npm install -g @beeai/cli")
        return 2

    voice = Stream(VOICE_PROFILE, "check-ins")
    talk = Stream(TALK_PROFILE, "everyday conversations")

    try:
        log("Reading your check-ins...")
        voice.days = reduce(ingest_checkins(cli))
        log("Reading the band's conversations (this can take a few minutes)...")
        talk.days = reduce(ingest_backfill(cli, OwnerFilter(None), max_minutes=max_minutes))
    except BeeNotAuthenticated:
        log("Bee is not logged in. Open the Bee app, then run: bee login")
        return 3
    except BeeCliError as err:
        log(f"Bee did not answer: {err}")
        return 1

    if not voice.days and not talk.days:
        log("Nothing recorded yet. Wear the band through a day, and check in once (a short voice note in the Bee app, then keep talking to the band), then run this again.")
        return 4

    for s in (voice, talk):
        if s.days:
            s.posted = post(s.days, s.profile)
            log(f"{s.label}: {len(s.days)} day(s) read, {s.counted} count toward your baseline")

    log("")
    log(f"Your page: {SITE}/app/?profile={VOICE_PROFILE}")
    if voice.counted < 7:
        need = 7 - voice.counted
        log(f"Your check-ins need {need} more day(s) of at least {MIN_WORDS} words before Bellwether compares anything. A short voice note, then about two minutes of talking, once a day.")
    else:
        log("Your check-in baseline is set. Every new day is compared with it.")
    if remind:
        today = voice.days[-1]["token_count_day"] if voice.days else 0
        remind_on_the_bee(cli, today, log)
    log("The words were read here and discarded. Only the day rows were sent.")
    return 0
