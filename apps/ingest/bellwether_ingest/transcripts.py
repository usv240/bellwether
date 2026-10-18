"""Bellwether without a Bee: the transcripts people already have.

    bellwether-ingest file meeting.vtt --speaker "Ujwal"
    bellwether-ingest file ~/Zoom/*.vtt --speaker "Ujwal" --post me-meetings

A Bee is the best input, because it hears a whole day. But most people
already have their own speech written down somewhere: every Zoom or Teams
meeting with transcription on leaves a WebVTT file, and Otter exports
text. Each of those names who said what, which is the one thing the Bee
does not yet do, so a person's own words can be kept and everyone else's
dropped before anything is measured.

Formats read
------------
  WebVTT from Zoom      "Name: what they said" inside each cue
  WebVTT from Teams     "<v Name>what they said</v>"
  Otter text export     a "Name  0:01" line, then what they said
  Plain text            "Name: what they said", one turn per line

The date of each file is taken from a YYYY-MM-DD in its name, else the
date given with --date, else the file's modified date. One file is one
meeting; several files on the same date are one day.

Nothing here keeps a word. The text is reduced to the same nine numbers a
day as every other path, and only those leave the machine.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from pathlib import Path

from speech_vitals import Utterance

_ZOOM = re.compile(r"^\s*([^:<>]{1,60}?):\s+(.+)$")
_TEAMS = re.compile(r"<v\s+([^>]{1,60})>(.*?)(?:</v>|$)", re.S)
_OTTER_HEAD = re.compile(r"^(.{1,60}?)\s{2,}\d{1,2}:\d{2}(?::\d{2})?\s*$")
_TIMING = re.compile(r"-->")
_DATE_IN_NAME = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def turns(text: str) -> list[tuple[str, str]]:
    """(speaker, words) for every turn the transcript attributes."""
    out: list[tuple[str, str]] = []
    if text.lstrip().startswith("WEBVTT") or _TIMING.search(text):
        for block in re.split(r"\n\s*\n", text):
            lines = [l for l in block.splitlines() if l.strip() and not _TIMING.search(l)
                     and not l.strip().isdigit() and not l.startswith(("WEBVTT", "NOTE"))]
            body = " ".join(lines).strip()
            if not body:
                continue
            teams = _TEAMS.findall(body)
            if teams:
                out.extend((s.strip(), re.sub(r"<[^>]+>", "", t).strip()) for s, t in teams)
                continue
            m = _ZOOM.match(body)
            if m:
                out.append((m.group(1).strip(), m.group(2).strip()))
        return [(s, t) for s, t in out if t]

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        head = _OTTER_HEAD.match(lines[i])
        if head:
            speaker = head.group(1).strip()
            said: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() and not _OTTER_HEAD.match(lines[i]):
                said.append(lines[i].strip())
                i += 1
            if said:
                out.append((speaker, " ".join(said)))
            continue
        m = _ZOOM.match(lines[i])
        if m:
            out.append((m.group(1).strip(), m.group(2).strip()))
        i += 1
    return [(s, t) for s, t in out if t]


def speakers(text: str) -> Counter:
    """Words per speaker, so a person can see which name is theirs."""
    c: Counter = Counter()
    for s, t in turns(text):
        c[s] += len(t.split())
    return c


def date_of(path: Path, given: str | None) -> str:
    m = _DATE_IN_NAME.search(path.name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if given:
        return given
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date().isoformat()


def utterances_from(path: Path, speaker: str, given_date: str | None = None) -> list[Utterance]:
    """The named speaker's own turns in one file, everyone else's dropped.
    Names are matched without regard to case or surrounding space."""
    text = path.read_text(encoding="utf-8", errors="replace")
    day = date_of(path, given_date)
    want = speaker.strip().lower()
    return [Utterance(ts=f"{day}T12:00:00Z", text=t, speaker="wearer", conversation_id=f"file-{path.name}")
            for s, t in turns(text) if s.strip().lower() == want]
