"""Both sides of a change, from the engine's numbers, before anyone argues.

When the tier is watch or discuss, a person's first question is whether
something real is happening or whether an ordinary week explains it. This
lays out the evidence for each side, every item computed from the stored
day rows and nothing else, each with an id an agent must cite:

  C1..  for a real change: how long it has held, how many measures moved
        together, how far the composite is from the baseline, whether it
        returned to the baseline at any point since it began.
  O1..  for an ordinary explanation: notes the person added near the
        change, days too quiet to read, everyday causes whose known effects
        match the measures that moved, and a change too young to call.

No model writes any of it. The second-opinion agents argue from this list,
and a referee's note may cite only these ids and use only these numbers.
The list never names a condition and never says which side is right.
"""

from __future__ import annotations

from datetime import date

# Everyday causes and the measures they are known to move, matching the
# list the dashboard shows under "What else could explain this".
EVERYDAY = [
    ("not sleeping well", {"mean_utt_len", "filler_rate", "low_freq_word_rate"}),
    ("a cold, flu or any illness", None),  # moves everything at once
    ("a new or changed medication", {"mean_utt_len", "dep_depth_mean", "idea_density"}),
    ("a stressful or busy week", {"mattr", "filler_rate", "disfluency_rate"}),
    ("talking mostly to one person, or on the phone", {"mattr", "vocab_size_day", "low_freq_word_rate"}),
    ("alcohol or a late night", {"filler_rate", "disfluency_rate"}),
]

PLAIN = {
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

NEAR_DAYS = 7


def _days_between(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def weigh(view: dict) -> dict:
    s = view["summary"]
    a_all = view["assessments"]
    tier, since = s.tier, s.since
    out = {"profile_id": view["profile_id"], "simulated": view["simulated"], "tier": tier, "since": since,
           "change": [], "ordinary": [], "note": "Evidence only. Neither side is a diagnosis, and this list does not say which is right."}
    if tier not in ("watch", "discuss") or not since:
        out["note"] = "Nothing to weigh: the tier is " + tier + ". Evidence is listed only once a change is flagged."
        return out

    after = [a for a in a_all if a.date >= since and a.eligible]
    flagged = [a for a in after if a.tier in ("watch", "discuss")]
    moved = list(s.contributors)
    peak = max((a.composite for a in after if a.composite is not None), default=None)
    back = [a.date for a in after if a.tier == "stable"]

    c = out["change"]
    c.append({"id": "C1", "claim": f"Flagged on {len(flagged)} of {len(after)} readable days since {since}."})
    c.append({"id": "C2", "claim": f"{len(moved)} of 9 measures moved together: " + ", ".join(PLAIN.get(m, m) for m in moved) + "."})
    if peak is not None:
        c.append({"id": "C3", "claim": f"The change score peaked at {peak:.1f}, where 0 is this person's own baseline."})
    c.append({"id": "C4", "claim": "It has not returned to the baseline on any readable day since it began." if not back
              else f"It returned to the baseline on {len(back)} readable day(s) since it began, most recently {back[-1]}."})

    o = out["ordinary"]
    notes = {d: n for d, n in (view.get("annotations") or {}).items()}
    near = sorted((d, n) for d, n in notes.items() if _days_between(d, since) <= NEAR_DAYS)
    far = sorted((d, n) for d, n in notes.items() if d not in dict(near))
    if near:
        o.append({"id": "O1", "claim": "Notes the person added within a week of the change: " + "; ".join(f"{d}: {n}" for d, n in near) + "."})
    elif far:
        o.append({"id": "O1", "claim": f"The person's notes are not near the change: the closest is {far[-1][0]} ({far[-1][1]}), "
                  f"{_days_between(far[-1][0], since)} days before it began."})
    else:
        o.append({"id": "O1", "claim": "The person has added no notes, so sleep, travel or illness has not been ruled in or out."})
    quiet = sum(1 for a in a_all if a.date >= since and not a.eligible)
    o.append({"id": "O2", "claim": f"{quiet} day(s) since the change were too quiet to read and are left out." if quiet
              else "No days since the change were too quiet to read."})
    moved_set = set(moved)
    matches = []
    for cause, feats in EVERYDAY:
        if feats is None:
            if len(moved_set) >= 6:
                matches.append(f"{cause} (it moves many measures at once, and {len(moved_set)} moved)")
        else:
            hit = sorted(PLAIN[f] for f in feats & moved_set)
            if hit:
                matches.append(f"{cause} ({', '.join(hit)})")
    if matches:
        o.append({"id": "O3", "claim": "Everyday causes known to move the measures that moved: " + "; ".join(matches) + "."})
    young = len(after) < 14
    o.append({"id": "O4", "claim": f"The change is {len(after)} readable days old; under two weeks, an ordinary stretch is easy to mistake for a trend."
              if young else f"The change is {len(after)} readable days old, past the two weeks in which an ordinary stretch is easily mistaken for a trend."})
    checks = view.get("checks") or []
    o.append({"id": "O5", "claim": f"{len(checks)} spoken check(s) logged; a spoken check adds an active measure beside the passive one."
              if checks else "No spoken check has been logged, so there is no active measure beside the passive one yet."})
    return out
