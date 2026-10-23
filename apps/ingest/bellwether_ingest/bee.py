"""The Bee integration.

Bee's developer surface is a CLI (``bee``), a real-time event stream, a
markdown export, and a local HTTP proxy. This module speaks to all of them
and reduces whatever they return to ``speech_vitals.Utterance``.

The shapes are deliberately tolerant. The Bee docs name the fields
(``text``, ``speaker``, ``start_time``, ``end_time``, ``created_at``) but
publish no full JSON example, so a normaliser that insisted on one exact
nesting would break on the first real device. Each accessor tries the
documented key first and sensible alternates after, and a test pins every
shape it accepts. The first real transcript from the device becomes a
fixture the day it arrives.

Privacy: functions here return utterances in memory. Nothing writes text.
The only file this module touches is the sync cursor, which holds an opaque
token and no content.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Callable, Iterable

from speech_vitals import Utterance

from .days import day_of_ms, remember_timezone

TEXT_KEYS = ("text", "content", "transcript", "utterance")
# spoken_at first: on the real device (bee-cli 0.7.3) each utterance
# carries spoken_at and created_at as epoch milliseconds, and start and
# end as seconds into the conversation. The relative pair must never be
# read as a time of day; see _looks_absolute.
TIME_KEYS = ("spoken_at", "start_time", "created_at", "timestamp", "ts", "start", "time")
# Below this an integer is a duration or an offset, not an instant.
_EPOCH_FLOOR = 10_000_000_000  # ms in 1970-04; seconds in 2286
CONVERSATION_ID_KEYS = ("id", "uuid", "conversation_uuid", "conversation_id")
UTTERANCE_LIST_KEYS = ("utterances", "transcript", "segments")

Runner = Callable[[list[str]], tuple[int, str, str]]


class BeeCliError(RuntimeError):
    """The bee binary returned an error or unparseable output."""


class BeeNotAuthenticated(BeeCliError):
    """``bee`` is installed but not logged in. Pair the app and run ``bee login``."""


# ---- normalisation ---------------------------------------------------------


def to_iso(value) -> str | None:
    """ISO 8601 UTC from an ISO string, an epoch in seconds or milliseconds,
    or a digit string of either."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return to_iso(int(s))
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, (int, float)):
        seconds = value / 1000.0 if value > 1e11 else float(value)
        return (
            datetime.fromtimestamp(seconds, tz=timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
    return None


def speaker_label(raw) -> str | None:
    """A stable, comparable speaker label: ``"Speaker 1"`` and ``"speaker_1"``
    and ``{"id": "speaker_1"}`` all become ``speaker_1``."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        for key in ("id", "name", "label", "speaker"):
            if raw.get(key) not in (None, ""):
                return speaker_label(raw[key])
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _looks_absolute(value) -> bool:
    """True for ISO strings and epoch numbers; false for the small integers
    the device uses as offsets into a conversation, which would otherwise
    parse as the first seconds of 1970 and put every utterance on one day."""
    if isinstance(value, str):
        return not value.strip().isdigit() or int(value) >= _EPOCH_FLOOR / 1000
    if isinstance(value, (int, float)):
        return value >= _EPOCH_FLOOR / 1000
    return False


def unwrap_conversation(raw) -> dict | None:
    """``bee conversations get`` answers ``{"conversation": {...}, "timezone": ...}``;
    ``now`` and ``changed`` list bare conversations. Both become the bare record."""
    if isinstance(raw, dict) and isinstance(raw.get("conversation"), dict):
        remember_timezone(raw.get("timezone"))
        return raw["conversation"]
    if isinstance(raw, dict):
        remember_timezone(raw.get("timezone"))
    return raw if isinstance(raw, dict) else None


def has_utterances(raw: dict) -> bool:
    """Whether a conversation record carries its utterances at all. The
    ``list`` command carries only ``utterances_count``; the words come from
    ``get``, ``now`` or ``changed``."""
    raw = unwrap_conversation(raw) or {}
    return any(True for _ in _find_utterance_lists(raw))


def normalize_utterance(
    raw: dict, conversation_id: str | None = None, fallback_ts: str | None = None
) -> Utterance | None:
    """One utterance record from any of Bee's shapes, or None if it has no
    text or no usable time."""
    if not isinstance(raw, dict):
        return None
    text = next((str(raw[k]).strip() for k in TEXT_KEYS if raw.get(k)), "")
    if not text:
        return None
    ts = next(
        (to_iso(raw[k]) for k in TIME_KEYS if raw.get(k) not in (None, "") and _looks_absolute(raw[k])),
        None,
    )
    ts = ts or fallback_ts
    if not ts:
        return None
    speaker = speaker_label(raw.get("speaker") or raw.get("speaker_id") or raw.get("speaker_name"))
    cid = conversation_id or next(
        (str(raw[k]) for k in ("conversation_id", "conversation_uuid") if raw.get(k)), None
    )
    return Utterance(ts=ts, text=text, speaker=speaker, conversation_id=cid)


def _find_utterance_lists(raw: dict) -> Iterable[list]:
    for key in UTTERANCE_LIST_KEYS:
        if isinstance(raw.get(key), list):
            yield raw[key]
    # bee sync and some get responses nest under transcriptions[*].utterances
    for t in raw.get("transcriptions") or []:
        if isinstance(t, dict):
            for key in UTTERANCE_LIST_KEYS:
                if isinstance(t.get(key), list):
                    yield t[key]


def normalize_conversation(raw: dict) -> list[Utterance]:
    """Every utterance in a conversation record, in time order."""
    raw = unwrap_conversation(raw)
    if not isinstance(raw, dict):
        return []
    cid = next((str(raw[k]) for k in CONVERSATION_ID_KEYS if raw.get(k) not in (None, "")), None)
    fallback = next((to_iso(raw[k]) for k in ("start_time", "created_at") if raw.get(k)), None)
    out: list[Utterance] = []
    for lst in _find_utterance_lists(raw):
        for item in lst:
            u = normalize_utterance(item, cid, fallback)
            if u:
                out.append(u)
    out.sort(key=lambda u: u.ts)
    return out


_MD_LINE = re.compile(r"^\s*-\s*(?P<speaker>[^:]{1,40}):\s*(?P<text>.+?)\s*$")
_MD_TRANSCRIPT = re.compile(r"^###\s+Transcription", re.IGNORECASE)


def parse_sync_markdown(md: str, conversation_id: str, day: str) -> list[Utterance]:
    """Utterances from a ``bee sync`` conversation file. The export carries
    no per-utterance time, so every line is stamped with the conversation's
    day; that is enough for day-level features and is stated here rather
    than invented."""
    out: list[Utterance] = []
    in_transcript = False
    ts = f"{day}T00:00:00Z"
    for line in md.splitlines():
        if _MD_TRANSCRIPT.match(line):
            in_transcript = True
            continue
        if line.startswith("#"):
            in_transcript = False
            continue
        if not in_transcript:
            continue
        m = _MD_LINE.match(line)
        if m:
            out.append(
                Utterance(
                    ts=ts,
                    text=m.group("text"),
                    speaker=speaker_label(m.group("speaker")),
                    conversation_id=conversation_id,
                )
            )
    return out


def parse_stream_line(line: str) -> Utterance | None:
    """One line of ``bee stream --json``. Only ``new-utterance`` events carry
    speech; everything else is ignored."""
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict):
        return None
    etype = event.get("type") or event.get("event")
    if etype not in ("new-utterance", "new_utterance", "utterance"):
        return None
    payload = event.get("utterance") if isinstance(event.get("utterance"), dict) else event
    cid = event.get("conversation_uuid") or event.get("conversation_id")
    return normalize_utterance(payload, str(cid) if cid else None)


# ---- the CLI ---------------------------------------------------------------


def _default_runner(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


class BeeCli:
    """Calls the ``bee`` binary and parses ``--json`` output.

    ``runner`` is injectable so tests can pin the exact argv each method
    produces without a device. Those argv lists are the code-level Bee
    integration the track requires.
    """

    def __init__(self, binary: str = "bee", runner: Runner | None = None) -> None:
        self.binary = binary
        self._runner = runner or _default_runner

    def _argv(self, *parts: str) -> list[str]:
        exe = shutil.which(self.binary) or self.binary
        argv = [exe, *parts]
        # npm installs a .cmd shim on Windows; CreateProcess needs cmd for it.
        if sys.platform.startswith("win") and exe.lower().endswith((".cmd", ".bat")):
            argv = ["cmd", "/c", *argv]
        return argv

    def _run(self, *parts: str):
        code, out, err = self._runner(self._argv(*parts))
        combined = f"{out}\n{err}"
        if "not logged in" in combined.lower():
            raise BeeNotAuthenticated(
                "bee is not logged in. Enable Developer Mode in the Bee app and run: bee login"
            )
        if code != 0:
            raise BeeCliError(f"bee {' '.join(parts)} failed ({code}): {err.strip() or out.strip()}")
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            raise BeeCliError(f"bee {' '.join(parts)} returned non-JSON output: {out[:200]!r}") from e

    def installed(self) -> bool:
        return shutil.which(self.binary) is not None

    def status_text(self) -> str:
        code, out, err = self._runner(self._argv("status"))
        return (out or err).strip()

    def me(self):
        return self._run("me", "--json")

    def now(self):
        return self._run("now", "--json")

    def changed(self, cursor: str | None = None):
        parts = ["changed"]
        if cursor:
            parts += ["--cursor", cursor]
        return self._run(*parts, "--json")

    def conversations_list(self, limit: int = 50, cursor: str | None = None):
        parts = ["conversations", "list", "--limit", str(limit)]
        if cursor:
            parts += ["--cursor", cursor]
        return self._run(*parts, "--json")

    def todos_list(self, limit: int = 50):
        return self._run("todos", "list", "--limit", str(limit), "--json")

    def todos_create(self, text: str, alarm_at: str | None = None):
        parts = ["todos", "create", "--text", text]
        if alarm_at:
            parts += ["--alarm-at", alarm_at]
        return self._run(*parts, "--json")

    def journals_list(self, limit: int = 50, cursor: str | None = None):
        parts = ["journals", "list", "--limit", str(limit)]
        if cursor:
            parts += ["--cursor", cursor]
        return self._run(*parts, "--json")

    def conversation_get(self, conversation_id: str):
        return self._run("conversations", "get", str(conversation_id), "--json")

    def conversation_transcript(self, conversation_id: str, since_ms: int | None = None):
        parts = ["conversations", "transcript", str(conversation_id)]
        if since_ms is not None:
            parts += ["--since", str(int(since_ms))]
        return self._run(*parts, "--json")


# ---- owner isolation -------------------------------------------------------


class OwnerFilter:
    """Keep only the wearer's own speech.

    Bee labels speakers generically (``speaker_1``). If the owner's label is
    known it is used directly. Otherwise the label with the most utterances
    across the corpus is taken to be the wearer, which is the person the
    device is on. That heuristic is stated in the friction log as a gap in
    the Bee surface; the day the device arrives, the real label becomes
    configuration.
    """

    def __init__(self, owner: str | None = None) -> None:
        self.owner = speaker_label(owner) if owner else None

    def resolve(self, utterances: list[Utterance]) -> str | None:
        if self.owner:
            return self.owner
        counts = Counter(u.speaker for u in utterances if u.speaker)
        if not counts:
            return None
        return counts.most_common(1)[0][0]

    def apply(self, utterances: list[Utterance]) -> list[Utterance]:
        owner = self.resolve(utterances)
        if owner is None:
            return list(utterances)
        return [u for u in utterances if u.speaker == owner]


# ---- incremental sync ------------------------------------------------------


class CursorStore:
    """The ``bee changed`` cursor, persisted so ingestion is incremental and
    exactly-once across runs. Holds an opaque token and nothing else."""

    def __init__(self, path: str = ".bee-cursor") -> None:
        self.path = path

    def load(self) -> str | None:
        if not os.path.exists(self.path):
            return None
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("cursor") or None

    def save(self, cursor: str | None) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"cursor": cursor}, fh)


def _conversation_ids_from_changed(payload) -> list[str]:
    ids: list[str] = []
    items = payload
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("changes") or payload.get("entities") or []
        for key in ("conversations",):
            for c in payload.get(key) or []:
                cid = c.get("id") if isinstance(c, dict) else c
                if cid:
                    ids.append(str(cid))
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        kind = str(it.get("type") or it.get("entity") or it.get("kind") or "").lower()
        if "conversation" in kind:
            cid = it.get("id") or it.get("entity_id") or it.get("conversation_id")
            if cid:
                ids.append(str(cid))
    seen: set[str] = set()
    return [i for i in ids if not (i in seen or seen.add(i))]


def _next_cursor(payload) -> str | None:
    if isinstance(payload, dict):
        for key in ("next_cursor", "cursor", "nextCursor"):
            if payload.get(key):
                return str(payload[key])
    return None


def ingest_changed(
    cli: BeeCli, cursors: CursorStore, owner: OwnerFilter
) -> tuple[list[Utterance], str | None]:
    """Pull everything that changed since the last run, as the owner's
    utterances. Returns the utterances and the new cursor; the caller
    persists the cursor only after it has reduced and stored the features,
    which is what makes processing exactly-once."""
    payload = cli.changed(cursors.load())
    utterances: list[Utterance] = []
    for cid in _conversation_ids_from_changed(payload):
        transcript = cli.conversation_transcript(cid)
        if isinstance(transcript, dict):
            utterances.extend(normalize_conversation({**transcript, "id": cid}))
        elif isinstance(transcript, list):
            utterances.extend(normalize_conversation({"id": cid, "utterances": transcript}))
    return owner.apply(utterances), _next_cursor(payload)


def with_utterances(cli: "BeeCli", rows: list, limit: int = 30) -> list[dict]:
    """Conversation records that carry their words.

    On the real device ``bee conversations list`` answers with summaries
    and an ``utterances_count`` and nothing anybody said; the first run
    against the hardware reduced two recorded conversations to zero
    utterances this way. Rows that lack utterances are fetched one by one
    with ``conversations get``, bounded, and unwrapped. Rows that already
    carry them (``now``, ``changed``) pass through untouched.
    """
    out: list[dict] = []
    fetched = 0
    for raw in rows or []:
        record = unwrap_conversation(raw)
        if record is None:
            continue
        if has_utterances(record):
            out.append(record)
            continue
        cid = next((record[k] for k in CONVERSATION_ID_KEYS if record.get(k) not in (None, "")), None)
        if cid is None or fetched >= limit:
            out.append(record)
            continue
        fetched += 1
        got = unwrap_conversation(cli.conversation_get(str(cid)))
        out.append(got if got is not None else record)
    return out


MEDIA_WORDS = re.compile(
    r"\b(movie|film|video|show|episode|podcast|tv|television|trailer|lecture|webinar|livestream)\b",
    re.IGNORECASE,
)


def keep_conversation(row: dict, max_minutes: float | None) -> bool:
    """Whether a conversation is likely to be the wearer talking.

    Bee labels every speaker "Unknown" on this account, so speech cannot be
    split by voice. What can be removed is what is plainly not the wearer:
    sessions longer than ``max_minutes`` (trainings, films and group events,
    where the wearer is a small share of the talking; on 2026-10-08 the two
    largest were five- and six-hour trainings), and anything Bee's own
    summary names as media. The summary is read on this machine to decide,
    and never stored or published.
    """
    if max_minutes is not None:
        start, end = row.get("start_time"), row.get("end_time")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            if (end - start) / 60000.0 > max_minutes:
                return False
    summary = f"{row.get('short_summary') or ''}"
    return not MEDIA_WORDS.search(summary)


def ingest_backfill(
    cli: BeeCli,
    owner: OwnerFilter,
    page: int = 100,
    max_pages: int = 100,
    max_minutes: float | None = None,
    keep_records: list | None = None,
    since_ms: int | None = None,
) -> list[Utterance]:
    """Every conversation the account holds, as the owner's utterances.
    ``keep_records``, if given, receives the fetched records so a caller
    can derive a second stream without reading the device twice.
    ``since_ms``, if given, stops at the first conversation older than it:
    the list comes newest first, so a daily run reads a day, not a month.

    ``bee changed`` with no cursor answers with recent changes only, so the
    first pull after ten days on the wrist came back with two days. The
    baseline needs the whole history, which only ``conversations list``
    pages through; each row is then fetched for its words.
    """
    rows: list = []
    cursor: str | None = None
    for _ in range(max_pages):
        payload = cli.conversations_list(limit=page, cursor=cursor)
        items = payload
        if isinstance(payload, dict):
            items = payload.get("conversations") or payload.get("items") or payload.get("data") or []
        rows.extend(items or [])
        cursor = _next_cursor(payload)
        if since_ms is not None and items and isinstance(items[-1], dict):
            oldest = _ms(items[-1].get("start_time"))
            if oldest is not None and oldest < since_ms:
                break
        if not cursor or not items:
            break
    if since_ms is not None:
        rows = [r for r in rows if not isinstance(r, dict) or (_ms(r.get("start_time")) or 0) >= since_ms]
    if max_minutes is not None:
        rows = [r for r in rows if not isinstance(r, dict) or keep_conversation(r, max_minutes)]
    records = with_utterances(cli, rows, limit=len(rows))
    if keep_records is not None:
        keep_records.extend(records)
    utterances: list[Utterance] = []
    for record in records:
        utterances.extend(normalize_conversation(record))
    return owner.apply(utterances)


WEARER = "wearer"


def ingest_journals(cli: BeeCli, max_pages: int = 100) -> list[Utterance]:
    """Every Bee voice note on the account, as the wearer's own speech.

    A voice note is recorded by the person wearing the band, on purpose, so
    there is no question of whose words they are. That is what ambient
    conversation cannot offer on an account where every speaker reads
    "Unknown" (friction log entry 12). It is also the stronger measurement:
    a short daily spoken check-in is the same shape as the elicited speech
    tasks the research uses, rather than whatever the room happened to say.

    Each note becomes one utterance stamped with when it was made and
    labelled ``wearer``. Notes still being processed, or with no text,
    are skipped rather than guessed at.
    """
    out: list[Utterance] = []
    cursor: str | None = None
    for _ in range(max_pages):
        payload = cli.journals_list(limit=50, cursor=cursor)
        items = payload.get("journals") if isinstance(payload, dict) else payload
        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("text") or "").strip()
            ts = to_iso(raw.get("created_at"))
            if not text or not ts:
                continue
            out.append(Utterance(ts=ts, text=text, speaker=WEARER,
                                 conversation_id=f"journal-{raw.get('id')}"))
        cursor = _next_cursor(payload)
        if not cursor or not items:
            break
    out.sort(key=lambda u: u.ts)
    return out


# ---- check-ins -------------------------------------------------------------
#
# On the device, a Bee voice note ends after a sentence: five notes on this
# account ran 1 to 15 words, each marked READY three seconds after it was
# made, while the band captured the same minute as a conversation of 100 to
# 150 words. A note alone cannot carry a day. But the wearer can declare a
# session theirs, two ways, and either makes it a check-in:
#
#   1. A voice note in the app, and the band's session that begins within a
#      couple of minutes of it and opens with the note's own words.
#   2. A spoken opener: the session's first words declare it, "Bellwether
#      check-in", "voice note for October 17", "today's vlog".
#
# Both are the wearer talking to the band on purpose, alone. Anyone else
# speaking in those minutes would be counted too; the wearer keeps it to
# themselves, and the site says so.

CHECKIN_BEFORE_S = 60          # the band may have opened the session just before the note
CHECKIN_START_WINDOW_S = 180   # or a little after; beyond that it is a different session
CHECKIN_KEEP_MIN = 10          # how much of the session after the anchor is the check-in
CHECKIN_MIN_NOTE_WORDS = 3     # fewer words cannot anchor anything
CHECKIN_OPENER_WORDS = 6       # the opener must be said at the start, not mentioned later

_WORD = re.compile(r"[a-z']+")
OPENER = re.compile(
    r"\b(bellwether|check[ -]?in|voice note|voice memo|vlog|daily log|journal|note to self|log for)\b"
)


def _words(text) -> list[str]:
    return _WORD.findall(str(text or "").lower())


def note_anchors(note_words: list[str], session_words: list[str]) -> bool:
    """Does the session open with the note? Either half of the note's word
    pairs appear in order in the session's first hundred words, or seven
    in ten of its distinct words do. The second rule is for the device's
    habit of transcribing the same minute twice with small differences:
    on 2026-10-15 a nine-word note shared 7 of 9 words with the session
    that followed it and only 3 of 8 pairs."""
    if len(note_words) < CHECKIN_MIN_NOTE_WORDS:
        return False
    head_words = session_words[:100]
    head = " ".join(head_words)
    pairs = [f"{a} {b}" for a, b in zip(note_words, note_words[1:])]
    hits = sum(1 for p in pairs if p in head)
    if hits * 2 >= len(pairs):
        return True
    distinct = set(note_words)
    return sum(1 for w in distinct if w in set(head_words)) * 10 >= len(distinct) * 7


def opener_declares(session_words: list[str]) -> bool:
    """Do the session's first words declare it a check-in?"""
    return bool(OPENER.search(" ".join(session_words[:CHECKIN_OPENER_WORDS])))


def _ms(value) -> int | None:
    iso = to_iso(value)
    if not iso:
        return None
    from datetime import datetime

    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def _page_all(fetch, key: str, limit: int = 100, max_pages: int = 100) -> list[dict]:
    rows: list[dict] = []
    cursor: str | None = None
    for _ in range(max_pages):
        payload = fetch(limit=limit, cursor=cursor)
        items = payload.get(key) if isinstance(payload, dict) else payload
        if isinstance(payload, dict) and not items:
            items = payload.get("items") or payload.get("data") or []
        rows.extend(r for r in items or [] if isinstance(r, dict))
        cursor = _next_cursor(payload)
        if not cursor or not items:
            break
    return rows


HOST_FILE = ".bellwether-host.json"


def load_host_lines(path: str = HOST_FILE) -> list[str]:
    """Lines a host actually spoke on this computer, as the host agent
    recorded them: ``{date: [line, ...]}``. Empty when no host has run.
    The day's standard script is known without this file; the file is for
    anything a host said beyond it."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    out: list[str] = []
    for lines in (data or {}).values():
        if isinstance(lines, list):
            for x in lines:
                if isinstance(x, str):
                    out.append(x)
                elif isinstance(x, dict) and isinstance(x.get("text"), str):
                    out.append(x["text"])
    return out


def load_host_spans(path: str = HOST_FILE) -> list[tuple[int, int, str]]:
    """When the host on this computer spoke each line: (start_ms, end_ms,
    text), from the laptop's clock. Lines recorded before timing existed
    carry no span and are skipped here."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    spans: list[tuple[int, int, str]] = []
    for lines in (data or {}).values():
        for x in lines if isinstance(lines, list) else []:
            if isinstance(x, dict) and isinstance(x.get("start"), (int, float)) and isinstance(x.get("end"), (int, float)):
                spans.append((int(x["start"] * 1000), int(x["end"] * 1000), str(x.get("text") or "")))
    return sorted(spans)


# The device's clock ran about two seconds behind the host's on 2026-10-19,
# and the wearer began answering at least three seconds after each prompt
# ended. An utterance that begins inside a host line, give or take these, is
# the host.
HOST_SPAN_BEFORE_S = 1.5
HOST_SPAN_AFTER_S = 3.0
HOSTED_GAP_S = 300            # spans further apart than this are separate check-ins
CLOSING_S = 6                 # how long the closing line takes to say


def _span_groups(spans: list[tuple[int, int, str]]) -> list[list[tuple[int, int, str]]]:
    groups: list[list[tuple[int, int, str]]] = []
    for sp in spans:
        if groups and sp[0] - groups[-1][-1][1] <= HOSTED_GAP_S * 1000:
            groups[-1].append(sp)
        else:
            groups.append([sp])
    return groups


def _host_lines_near(anchor_ms: int, extra: list[str]) -> list[str]:
    """The host's possible sentences around that moment: the standard
    script for the day before, the day, and the day after (the host and the
    device may sit on different sides of midnight), plus anything the host
    on this computer recorded saying."""
    from datetime import date, timedelta

    from speech_vitals.elicitation import host_lines_for

    d = date.fromisoformat(day_of_ms(anchor_ms))
    lines: list[str] = []
    for k in (-1, 0, 1):
        lines.extend(host_lines_for(d + timedelta(days=k)))
    lines.extend(extra)
    return lines


def checkins_from(notes: list[dict], records: list[dict], keep_minutes: float = CHECKIN_KEEP_MIN,
                  host_lines: list[str] | None = None,
                  host_spans: list[tuple[int, int, str]] | None = None) -> list[Utterance]:
    """The check-ins among ``records`` (conversation records that carry
    their utterances), anchored by ``notes`` or by a spoken opener. Pure,
    so the rule is tested without a device. No session is used twice;
    nothing before the anchor or after the window is kept.

    A hosted check-in is one a voice assistant opened: the host speaks the
    opener, so the session declares itself, and then the host's questions
    are in the transcript beside the wearer's answers. Every utterance that
    is one of the host's lines is dropped before anything is measured, so a
    sixteen-word question is never counted as the wearer's speech."""
    from speech_vitals.elicitation import host_runs, is_host_line

    extra = list(host_lines or [])
    sessions = []
    for raw in records:
        rec = unwrap_conversation(raw)
        if not isinstance(rec, dict):
            continue
        utts = normalize_conversation(rec)
        if not utts:
            continue
        cid = next((str(rec[k]) for k in CONVERSATION_ID_KEYS if rec.get(k) not in (None, "")), None)
        start = _ms(rec.get("start_time")) or _ms(utts[0].ts)
        sessions.append((cid or utts[0].conversation_id or "", start, utts, _words(" ".join(u.text for u in utts))))

    out: list[Utterance] = []
    used: set[str] = set()

    def keep(cid: str, utts: list[Utterance], anchor_ms: int, label: str) -> None:
        used.add(cid)
        until = anchor_ms + int(keep_minutes * 60000)
        host = _host_lines_near(anchor_ms, extra)
        for u in utts:
            t = _ms(u.ts)
            if t is not None and anchor_ms - CHECKIN_BEFORE_S * 1000 <= t <= until:
                if is_host_line(u.text, host):
                    continue
                out.append(Utterance(ts=u.ts, text=u.text, speaker=WEARER, conversation_id=f"{label}-{cid}"))

    # Hosted, by timing. The host recorded when it spoke; the device was
    # often already recording, so the session's own start means nothing.
    # The check-in is from the first host line to the end of the last, and
    # anything that began while the host was speaking is the host, however
    # the device heard it ("phone number checked in" for "Bellwether
    # check-in", on 2026-10-19).
    for group in _span_groups(list(host_spans or [])):
        g_start, g_end = group[0][0], group[-1][1]
        windows = [(s - int(HOST_SPAN_BEFORE_S * 1000), e + int(HOST_SPAN_AFTER_S * 1000)) for s, e, _ in group]
        texts = [t for _, _, t in group] + _host_lines_near(g_start, extra)
        for cid, start, utts, words in sessions:
            if cid in used:
                continue
            times = [t for t in (_ms(u.ts) for u in utts) if t is not None]
            if not times or max(times) < g_start or min(times) > g_end + 60000:
                continue
            used.add(cid)
            for u in utts:
                t = _ms(u.ts)
                if t is None or not (g_start - int(HOST_SPAN_BEFORE_S * 1000) <= t <= g_end + int(HOST_SPAN_AFTER_S * 1000)):
                    continue
                if any(a <= t <= b for a, b in windows) or is_host_line(u.text, texts):
                    continue
                out.append(Utterance(ts=u.ts, text=u.text, speaker=WEARER, conversation_id=f"hosted-{cid}"))
            break

    # Hosted, by text, for a host that recorded no timing (an Echo, say).
    # The opener and the first question are found anywhere in a session; the
    # check-in runs to the closing line, or the usual window; an utterance
    # mostly made of host words is the host.
    for cid, start, utts, words in sessions:
        if cid in used:
            continue
        anchor_i = None
        for i, u in enumerate(utts):
            t = _ms(u.ts)
            if t is None:
                continue
            near = _host_lines_near(t, [])
            head = [ln for ln in near if ln.startswith("Bellwether check-in") or ln.startswith("Question 1") or ln.startswith("Question one")]
            first_prompts = [ln for k, ln in enumerate(near) if k % 8 == 2]
            if host_runs(u.text, head + first_prompts, min_run=4) >= 4:
                anchor_i = i
                break
        if anchor_i is None:
            continue
        anchor_ms = _ms(utts[anchor_i].ts)
        lines = _host_lines_near(anchor_ms, extra)
        closing = [ln for ln in lines if ln.startswith("Thank you. That is today's check-in")]
        until = anchor_ms + int(keep_minutes * 60000)
        used.add(cid)
        for u in utts[anchor_i:]:
            t = _ms(u.ts)
            if t is None or t > until:
                break
            if host_runs(u.text, closing) >= 3:
                # The closing takes about six seconds to say, and the device
                # may have heard its first words as separate, garbled
                # utterances ("thank you" and a mangled "that is today's
                # check-in" on 2026-10-19). Nothing the wearer said in those
                # seconds is an answer.
                while out and out[-1].conversation_id == f"hosted-{cid}" and (_ms(out[-1].ts) or 0) >= t - CLOSING_S * 1000:
                    out.pop()
                break
            n = len(u.text.split())
            if is_host_line(u.text, lines) or (n and host_runs(u.text, lines) * 2 >= n):
                continue
            out.append(Utterance(ts=u.ts, text=u.text, speaker=WEARER, conversation_id=f"hosted-{cid}"))

    for note in sorted(notes, key=lambda n: _ms(n.get("created_at")) or 0):
        at = _ms(note.get("created_at"))
        text = str(note.get("text") or "").strip()
        if at is None or not text:
            continue
        out.append(Utterance(ts=to_iso(at), text=text, speaker=WEARER, conversation_id=f"journal-{note.get('id')}"))
        nw = _words(text)
        for cid, start, utts, words in sessions:
            if cid in used or start is None:
                continue
            if not (at - CHECKIN_BEFORE_S * 1000 <= start <= at + CHECKIN_START_WINDOW_S * 1000):
                continue
            if note_anchors(nw, words):
                keep(cid, utts, at, "checkin")
                break

    for cid, start, utts, words in sessions:
        if cid in used or start is None:
            continue
        if opener_declares(words):
            keep(cid, utts, start, "checkin")

    out.sort(key=lambda u: u.ts)
    return out


def ingest_checkins(cli: BeeCli, max_pages: int = 100, keep_minutes: float = CHECKIN_KEEP_MIN,
                    records: list[dict] | None = None, host_file: str = HOST_FILE) -> list[Utterance]:
    """Every check-in on the account. ``records`` may be passed in by a
    caller that has already fetched the history (``mine`` does), so the
    device is read once. Lines a host on this computer spoke are read from
    ``host_file`` and never counted as the wearer's."""
    notes = [r for r in _page_all(cli.journals_list, "journals", limit=50, max_pages=max_pages)
             if str(r.get("text") or "").strip()]
    if records is None:
        rows = _page_all(cli.conversations_list, "conversations", limit=100, max_pages=max_pages)
        records = with_utterances(cli, rows, limit=len(rows))
    return checkins_from(notes, records, keep_minutes, host_lines=load_host_lines(host_file),
                         host_spans=load_host_spans(host_file))


def ingest_now(cli: BeeCli, owner: OwnerFilter) -> list[Utterance]:
    """The last several hours, for a live today view."""
    payload = cli.now()
    convs = payload.get("conversations") if isinstance(payload, dict) else payload
    utterances: list[Utterance] = []
    for c in convs or []:
        utterances.extend(normalize_conversation(c))
    return owner.apply(utterances)
