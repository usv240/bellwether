"""Which day an utterance belongs to: the wearer's day, not UTC's.

Utterance timestamps are kept in UTC so they compare across devices. A
day, though, is the wearer's: a check-in at half past eleven at night in
New York is that evening's check-in, not the next morning's. The Bee
reports the wearer's timezone with every conversation it returns
(``{"conversation": {...}, "timezone": "America/New_York"}``); the first
one seen in a run is remembered here, and ``BELLWETHER_TZ`` overrides
it. With neither, the day is the UTC day, as before.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_reported: str | None = None


def remember_timezone(name) -> None:
    """Keep the timezone the device reported, once per run."""
    global _reported
    if isinstance(name, str) and name.strip() and _reported is None:
        _reported = name.strip()


def wearer_timezone() -> str | None:
    return os.environ.get("BELLWETHER_TZ") or _reported


def day_of(ts: str) -> str:
    """``YYYY-MM-DD`` of an ISO UTC timestamp in the wearer's timezone."""
    name = wearer_timezone()
    if not name:
        return ts[:10]
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ts[:10]
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts[:10]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(zone).date().isoformat()


def day_of_ms(ms: int) -> str:
    return day_of(datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
