"""The baseline engine: one person, compared only with themselves.

Statistics, stated plainly so they can be argued with:

1. Warmup. The first ``warmup_days`` eligible days are used to learn a mean
   and standard deviation per feature by ordinary sample statistics. No tier
   is shown; the product says "Learning". A baseline built on fewer days
   would be built on noise.

2. Baseline. After warmup, each feature's mean and variance follow an
   exponentially weighted moving average (``ewma_lambda`` 0.05, a half-life
   of about two weeks), so the baseline follows a person as they slowly and
   benignly change.

3. Standardisation. Each day, each feature is expressed as a z-score against
   the baseline *before* that day is folded in, so no day is compared with
   itself. The sign is flipped for features whose concerning direction is
   downward, giving a "concern z" that is positive when the feature moved
   the way the literature associates with decline.

4. The composite. The weighted mean of concern z across features, scaled by
   the square root of the feature count so that, under no change, it behaves
   roughly like a standard normal. One number, one test, one false-alarm
   rate, instead of nine independent alarms that would trip on noise.

5. Drift detection. A one-sided CUSUM on the composite (``cusum_k`` 0.5,
   ``cusum_h`` 5.0). With those parameters the expected time to a false
   alarm on pure noise is on the order of nine hundred days, which is the
   right side of the trade for a product whose false alarms cost a family
   sleep. Per-feature CUSUMs run alongside for attribution only: they say
   which features are driving the composite, they never set the tier.

6. The freeze. While the composite CUSUM is tripped, the baseline stops
   updating. Otherwise a slow, real drift would be absorbed into "normal"
   over a few weeks and the signal would disappear into the baseline that
   was supposed to detect it. The baseline may not learn its way out of a
   signal.

7. Exposure. A day with fewer than ``min_tokens`` words is excluded from
   every step above. A quiet day is not a change in the person.

Tiers:
  excluded   too little speech that day to say anything
  learning   inside the warmup
  stable     composite CUSUM below its threshold
  watch      composite CUSUM tripped
  discuss    tripped for ``discuss_consecutive`` eligible days in a row, or a
             single day whose composite exceeds ``acute_composite``

None of this diagnoses anything. It describes change over time in one
person against that person's own past, and it lists its reasons.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from speech_vitals.types import FEATURE_NAMES, FEATURES

DIRECTION: dict[str, str] = {f.name: f.direction for f in FEATURES}

_DIRECTION_WORD = {
    "lower_is_concerning": "lower",
    "higher_is_concerning": "higher",
}


@dataclass(frozen=True)
class EngineConfig:
    warmup_days: int = 7
    ewma_lambda: float = 0.05
    cusum_k: float = 0.5
    cusum_h: float = 5.0
    feature_cusum_h: float = 4.0
    min_tokens: int = 150
    discuss_consecutive: int = 7
    acute_composite: float = 5.0
    # Relative floor on the standard deviation, so a feature that barely
    # varied during warmup cannot produce absurd z-scores later.
    sd_floor_fraction: float = 0.05
    # Absolute floors, per feature, in the feature's own units. A relative
    # floor is no floor at all when the mean is zero: someone who did not
    # say "um" for seven days has a filler rate of exactly zero with zero
    # variance, and without this the first "um" is an infinite z-score and
    # an acute alarm. Found by the persona fixture. These state a belief:
    # nobody's day-to-day variability is ever smaller than this.
    sd_floor_abs: dict[str, float] = field(
        default_factory=lambda: {
            "mattr": 0.01,
            "mean_utt_len": 0.5,
            "dep_depth_mean": 0.15,
            "pronoun_noun_ratio": 0.02,
            "filler_rate": 0.5,
            "disfluency_rate": 0.3,
            "low_freq_word_rate": 0.5,
            "idea_density": 0.15,
            "vocab_size_day": 10.0,
        }
    )
    weights: dict[str, float] = field(
        default_factory=lambda: {name: 1.0 for name in FEATURE_NAMES}
    )


DEFAULT_CONFIG = EngineConfig()


@dataclass(frozen=True)
class FeatureAssessment:
    name: str
    value: float
    baseline_mean: float | None
    baseline_sd: float | None
    z: float | None
    concern_z: float | None
    cusum: float
    tripped: bool
    direction: str


@dataclass(frozen=True)
class DayAssessment:
    date: str
    eligible: bool
    reason: str | None
    tier: str
    composite: float | None
    composite_cusum: float | None
    features: tuple[FeatureAssessment, ...]
    contributors: tuple[str, ...]
    explanation: tuple[str, ...]
    annotation: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Summary:
    tier: str
    since: str | None
    latest_date: str | None
    eligible_days: int
    excluded_days: int
    in_warmup: bool
    warmup_days_remaining: int
    stable_streak_days: int
    contributors: tuple[str, ...]
    explanation: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class _FeatureState:
    __slots__ = ("warm", "mean", "var", "cusum", "trip_since")

    def __init__(self) -> None:
        self.warm: list[float] = []
        self.mean: float | None = None
        self.var: float = 0.0
        self.cusum: float = 0.0
        self.trip_since: str | None = None


def _as_dict(day) -> dict:
    return day if isinstance(day, dict) else day.to_dict()


def _finish_warmup(state: _FeatureState) -> None:
    n = len(state.warm)
    mean = sum(state.warm) / n
    var = sum((v - mean) ** 2 for v in state.warm) / n
    state.mean = mean
    state.var = var


def assess(
    days,
    config: EngineConfig = DEFAULT_CONFIG,
    annotations: dict[str, str] | None = None,
) -> list[DayAssessment]:
    """One ``DayAssessment`` per input day, in date order. Pure: the same
    days and config always produce the same assessments."""
    annotations = annotations or {}
    ordered = sorted((_as_dict(d) for d in days), key=lambda d: d["date"])
    weights = config.weights
    weight_total = sum(weights.get(n, 0.0) for n in FEATURE_NAMES) or 1.0
    scale = math.sqrt(len(FEATURE_NAMES))

    states: dict[str, _FeatureState] = {n: _FeatureState() for n in FEATURE_NAMES}
    eligible_seen = 0
    composite_cusum = 0.0
    tripped_since: str | None = None
    tripped_days = 0
    out: list[DayAssessment] = []

    for d in ordered:
        date = d["date"]
        note = annotations.get(date)
        tokens = int(d.get("token_count_day", 0))

        if tokens < config.min_tokens:
            out.append(
                DayAssessment(
                    date=date,
                    eligible=False,
                    reason=f"low exposure: {tokens} words recorded, below {config.min_tokens}",
                    tier="excluded",
                    composite=None,
                    composite_cusum=None,
                    features=(),
                    contributors=(),
                    explanation=("Not enough speech was recorded to assess this day.",)
                    + ((f"You noted: {note}",) if note else ()),
                    annotation=note,
                )
            )
            continue

        eligible_seen += 1
        in_warmup = eligible_seen <= config.warmup_days

        if in_warmup:
            for name in FEATURE_NAMES:
                states[name].warm.append(float(d[name]))
            if eligible_seen == config.warmup_days:
                for st in states.values():
                    _finish_warmup(st)
            remaining = config.warmup_days - eligible_seen
            out.append(
                DayAssessment(
                    date=date,
                    eligible=True,
                    reason=None,
                    tier="learning",
                    composite=None,
                    composite_cusum=None,
                    features=tuple(
                        FeatureAssessment(
                            name=n, value=float(d[n]), baseline_mean=None, baseline_sd=None,
                            z=None, concern_z=None, cusum=0.0, tripped=False, direction=DIRECTION[n],
                        )
                        for n in FEATURE_NAMES
                    ),
                    contributors=(),
                    explanation=(
                        (
                            f"Learning your baseline: {remaining} more day(s) of speech needed."
                            if remaining > 0
                            else "Baseline learned. From tomorrow, days are compared with it."
                        ),
                    )
                    + ((f"You noted: {note}",) if note else ()),
                    annotation=note,
                )
            )
            continue

        # ---- post-warmup: standardise against the baseline as it stood ----
        feats: list[FeatureAssessment] = []
        weighted_concern = 0.0
        for name in FEATURE_NAMES:
            st = states[name]
            x = float(d[name])
            mean = st.mean if st.mean is not None else x
            sd = math.sqrt(max(st.var, 0.0))
            sd = max(
                sd,
                config.sd_floor_fraction * abs(mean),
                config.sd_floor_abs.get(name, 0.0),
                1e-9,
            )
            z = (x - mean) / sd
            cz = -z if DIRECTION[name] == "lower_is_concerning" else z
            st.cusum = max(0.0, st.cusum + cz - config.cusum_k)
            f_trip = st.cusum > config.feature_cusum_h
            if f_trip and st.trip_since is None:
                st.trip_since = date
            if not f_trip:
                st.trip_since = None
            weighted_concern += weights.get(name, 0.0) * cz
            feats.append(
                FeatureAssessment(
                    name=name, value=x, baseline_mean=round(mean, 6), baseline_sd=round(sd, 6),
                    z=round(z, 4), concern_z=round(cz, 4), cusum=round(st.cusum, 4),
                    tripped=f_trip, direction=DIRECTION[name],
                )
            )

        composite = (weighted_concern / weight_total) * scale
        composite_cusum = max(0.0, composite_cusum + composite - config.cusum_k)
        tripped = composite_cusum > config.cusum_h
        acute = composite > config.acute_composite

        if tripped:
            tripped_days += 1
            if tripped_since is None:
                tripped_since = date
        else:
            tripped_days = 0
            tripped_since = None

        if acute or (tripped and tripped_days >= config.discuss_consecutive):
            tier = "discuss"
        elif tripped:
            tier = "watch"
        else:
            tier = "stable"

        # The freeze: while signalling, the baseline does not learn.
        if not tripped:
            lam = config.ewma_lambda
            for name in FEATURE_NAMES:
                st = states[name]
                x = float(d[name])
                prev = st.mean if st.mean is not None else x
                st.mean = (1 - lam) * prev + lam * x
                st.var = (1 - lam) * st.var + lam * (x - prev) ** 2

        # Attribution only when there is something to attribute. A single
        # feature's CUSUM will trip on noise somewhere in a couple of months
        # even while the composite, which alone sets the tier, stays quiet.
        # Naming a "contributor" on a stable day would be telling a family
        # that something moved when nothing did.
        contributors = (
            tuple(
                f.name
                for f in sorted(feats, key=lambda f: -(f.concern_z or 0.0))
                if f.tripped
            )
            if (tripped or acute)
            else ()
        )
        explanation: list[str] = []
        if tier == "stable":
            explanation.append("All measures are within your normal range.")
        else:
            if acute:
                explanation.append(
                    f"Today's speech differs sharply from your baseline (composite {composite:.1f})."
                )
            elif tripped:
                explanation.append(
                    f"Several measures have moved together since {tripped_since}"
                    + (f" ({tripped_days} days)." if tripped_days > 1 else ".")
                )
            for f in feats:
                if f.tripped:
                    since = states[f.name].trip_since or date
                    explanation.append(
                        f"{f.name} has been {_DIRECTION_WORD[f.direction]} than your baseline since {since}."
                    )
        if note:
            explanation.append(f"You noted: {note}")

        out.append(
            DayAssessment(
                date=date,
                eligible=True,
                reason=None,
                tier=tier,
                composite=round(composite, 4),
                composite_cusum=round(composite_cusum, 4),
                features=tuple(feats),
                contributors=contributors,
                explanation=tuple(explanation),
                annotation=note,
            )
        )

    return out


def summarize(assessments: list[DayAssessment], config: EngineConfig = DEFAULT_CONFIG) -> Summary:
    """The current state, for a dashboard header or an agent's first call."""
    eligible = [a for a in assessments if a.eligible]
    excluded = len(assessments) - len(eligible)
    if not eligible:
        return Summary(
            tier="learning", since=None, latest_date=assessments[-1].date if assessments else None,
            eligible_days=0, excluded_days=excluded, in_warmup=True,
            warmup_days_remaining=config.warmup_days, stable_streak_days=0,
            contributors=(), explanation=("No eligible days yet.",),
        )
    latest = eligible[-1]
    in_warmup = latest.tier == "learning"
    remaining = max(0, config.warmup_days - len(eligible)) if in_warmup else 0

    since = latest.date
    for a in reversed(eligible):
        if a.tier != latest.tier:
            break
        since = a.date

    streak = 0
    for a in reversed(eligible):
        if a.tier == "stable":
            streak += 1
        else:
            break

    return Summary(
        tier=latest.tier,
        since=since,
        latest_date=latest.date,
        eligible_days=len(eligible),
        excluded_days=excluded,
        in_warmup=in_warmup,
        warmup_days_remaining=remaining,
        stable_streak_days=streak,
        contributors=latest.contributors,
        explanation=latest.explanation,
    )
