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

TEXT_KEYS = ("text", "content", "transcript", "utterance")
TIME_KEYS = ("start_time", "created_at", "timestamp", "ts", "start", "time")
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
    ts = next((to_iso(raw[k]) for k in TIME_KEYS if raw.get(k) not in (None, "")), None)
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


def ingest_now(cli: BeeCli, owner: OwnerFilter) -> list[Utterance]:
    """The last several hours, for a live today view."""
    payload = cli.now()
    convs = payload.get("conversations") if isinstance(payload, dict) else payload
    utterances: list[Utterance] = []
    for c in convs or []:
        utterances.extend(normalize_conversation(c))
    return owner.apply(utterances)
