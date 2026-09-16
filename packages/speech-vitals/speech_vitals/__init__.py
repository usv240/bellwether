"""speech-vitals: language features from everyday speech, for personal
baselines. Features only, never words.

    from speech_vitals import Utterance, aggregate_day, extract_utterance

    day = aggregate_day([Utterance(ts="2026-09-16T08:00:00Z", text="...")])
    day.mattr, day.idea_density, day.pronoun_noun_ratio

A ``DayFeatures`` record cannot reconstruct a sentence. That is the point.
"""

from .features import (
    FILLERS,
    LOW_FREQ_ZIPF,
    MATTR_WINDOW,
    aggregate_day,
    extract_utterance,
    mattr,
)
from .types import (
    FEATURE_NAMES,
    FEATURES,
    DayFeatures,
    FeatureSpec,
    Utterance,
    UtteranceFeatures,
    features_schema,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "FEATURES",
    "FEATURE_NAMES",
    "FILLERS",
    "LOW_FREQ_ZIPF",
    "MATTR_WINDOW",
    "DayFeatures",
    "FeatureSpec",
    "Utterance",
    "UtteranceFeatures",
    "aggregate_day",
    "extract_utterance",
    "features_schema",
    "mattr",
]
