"""bellwether-engine: a personal baseline for how one person speaks, and an
honest account of when that changes.

    from bellwether_engine import assess, summarize

    assessments = assess(day_features)      # one DayAssessment per day
    status = summarize(assessments)         # current tier, since when, why

Nothing here calls a model. Every number is a pure function of the day
features that went in, and every tier change lists the features behind it.
"""

from .baseline import (
    DEFAULT_CONFIG,
    DayAssessment,
    EngineConfig,
    FeatureAssessment,
    Summary,
    assess,
    summarize,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DEFAULT_CONFIG",
    "DayAssessment",
    "EngineConfig",
    "FeatureAssessment",
    "Summary",
    "assess",
    "summarize",
]
