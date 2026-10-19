"""The hosted check-in, from the service's side.

Two things an assistant needs that the seven original tools did not give.
What to say tonight: the opener that declares the session a check-in, the
three prompts, and the closing, as exact lines, so the host speaks them
verbatim and the ingest can strip them. And what to tell the person after:
where they stand in their first week, or what moved, as something to do
rather than a chart to read.

The coaching note is deterministic. Every sentence is built from numbers
the engine produced: days counted, words on each day, the tier, the
measures behind it. It never names a condition and never predicts. The
Bedrock ladder in bedrock.py may rephrase it; it may not add to it.

Context across sessions is kept in the store's meta rows: when the day's
check-in was started and by which host, so a second start on the same day
is told so rather than run twice.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from speech_vitals.elicitation import BASIS, CLOSING, host_lines_for, opener_for, prompts_for

WORD_FLOOR = 150          # a day below this does not count; apps/engine says so too
WARMUP_DAYS = 7
TWO_MINUTES_WORDS = 250   # about what two minutes of unhurried speech comes to
_NUM = ["zero", "one", "two", "three", "four", "five", "six", "seven"]

# Plain names for speaking aloud. The engine's names are for code.
SPOKEN = {
    "mattr": "vocabulary variety",
    "mean_utt_len": "sentence length",
    "dep_depth_mean": "sentence structure",
    "pronoun_noun_ratio": "pronoun use",
    "filler_rate": "ums and uhs",
    "disfluency_rate": "restarts",
    "low_freq_word_rate": "rarer words",
    "idea_density": "idea density",
    "vocab_size_day": "words used",
}


def _spoken_list(names: list[str], limit: int = 3) -> str:
    plain = [SPOKEN.get(n, n.replace("_", " ")) for n in names]
    if not plain:
        return "several measures"
    head = plain[:limit]
    more = len(plain) - len(head)
    if more:
        n = _NUM[more] if more < len(_NUM) else str(more)
        return ", ".join(head) + f" and {n} other {'measure' if more == 1 else 'measures'}"
    return head[0] if len(head) == 1 else ", ".join(head[:-1]) + " and " + head[-1]


def _today(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def _valid_day(s: str) -> bool:
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def start_payload(store, profile_id: str, view: dict, now: datetime | None = None, host: str = "assistant",
                  day: str | None = None) -> dict:
    """What the host says tonight, and where the person stands before it.
    ``day`` is the host's local date when it sends one; the service's clock
    is UTC and an evening check-in in the Americas is already tomorrow
    there."""
    today = day if day and _valid_day(day) else _today(now)
    summary = view["summary"].to_dict()
    eligible_dates = {a.date for a in view["assessments"] if a.eligible}
    started = store.get_meta(profile_id, f"checkin_started:{today}")
    when = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not started:
        store.put_meta(profile_id, f"checkin_started:{today}", json.dumps({"at": when, "host": host}))
    return {
        "profile_id": profile_id,
        "date": today,
        "opener": opener_for(today),
        "prompts": prompts_for(today),
        "closing": CLOSING,
        "host_lines": host_lines_for(today),
        "basis": BASIS,
        "answer_seconds": 45,
        "word_floor": WORD_FLOOR,
        "eligible_days": summary.get("eligible_days", 0),
        "warmup_days": WARMUP_DAYS,
        "today_counted": today in eligible_dates,
        "already_started_today": json.loads(started) if started else None,
        "how_to_count": (
            "After the Bee has written the session down, run `bellwether-ingest mine --days 1` on the wearer's "
            "computer. The host's lines are removed before anything is measured; only nine numbers leave."
        ),
    }


def coaching_payload(view: dict, now: datetime | None = None) -> dict:
    """The week as something to do. Built only from the engine's numbers."""
    summary = view["summary"].to_dict()
    days = view["days"]
    assessments = view["assessments"]
    tier = summary.get("tier", "learning")
    eligible = summary.get("eligible_days", 0)
    today = _today(now)

    by_date = {d["date"]: d for d in days}
    recent = sorted(by_date)[-7:]
    recent_words = [int(by_date[d].get("token_count_day") or 0) for d in recent]
    short_days = [(d, w) for d, w in zip(recent, recent_words) if 0 < w < WORD_FLOOR]
    counted_words = [w for w in recent_words if w >= WORD_FLOOR]
    avg_counted = round(sum(counted_words) / len(counted_words)) if counted_words else 0

    facts = {
        "tier": tier,
        "eligible_days": eligible,
        "warmup_days": WARMUP_DAYS,
        "recent_days": [{"date": d, "words": w} for d, w in zip(recent, recent_words)],
        "short_days": [{"date": d, "words": w} for d, w in short_days],
        "average_words_on_counted_days": avg_counted,
        "since": summary.get("since"),
        "contributors": summary.get("contributors") or [],
        "stable_streak_days": summary.get("stable_streak_days", 0),
        "simulated": view.get("simulated", False),
    }

    sentences: list[str] = []
    actions: list[str] = []

    if tier == "learning":
        left = max(0, WARMUP_DAYS - eligible)
        sentences.append(f"Day {_NUM[min(eligible, 7)]} of seven counted." if eligible else "No day has counted yet.")
        if left:
            sentences.append(
                f"{_NUM[left].capitalize()} more {'day' if left == 1 else 'days'} of check-ins and Bellwether starts comparing."
            )
            actions.append("Check in tomorrow at about the same time of day. A baseline is most useful when the conditions are alike.")
        else:
            sentences.append("From tomorrow each day is compared with these seven.")
        if short_days:
            d, w = short_days[-1]
            sentences.append(
                f"The check-in on {d} came to {w} words, under the floor of {WORD_FLOOR}, so it did not count."
            )
            actions.append("Answer each of the three questions in full sentences until the host says thank you. Two minutes is about 250 words.")
        elif avg_counted:
            sentences.append(f"Your counted days average {avg_counted} words, well over the floor of {WORD_FLOOR}.")
    elif tier == "stable":
        streak = summary.get("stable_streak_days", 0)
        sentences.append(f"Stable against your own baseline, {streak} {'day' if streak == 1 else 'days'} in a row.")
        actions.append("Keep the check-ins going at the same time of day. Nothing else to do this week.")
    else:
        who = _spoken_list(list(summary.get("contributors") or []))
        sentences.append(f"Since {summary.get('since')}, {who} have been outside your usual range.")
        sentences.append("This is not a diagnosis. Sleep, illness, travel and medication move these measures too.")
        actions.append("Add a note to the days in question if sleep, illness or travel explains them.")
        actions.append("Run the spoken check with the host once this week.")
        if tier == "discuss":
            actions.append("If it holds another week, bring the report to a clinician you trust.")

    if view.get("simulated"):
        sentences.insert(0, "This person is simulated.")

    return {
        "profile_id": view["profile_id"],
        "simulated": view.get("simulated", False),
        "date": today,
        "text": " ".join(sentences),
        "actions": actions,
        "facts": facts,
        "note": "Every sentence is built from the numbers above. Not a diagnosis.",
    }
