"""The speech-vitals schema.

Everything downstream (the baseline engine, the dashboard, the doctor
report, the MCP server) consumes these records and nothing else. A
transcript enters ``extract_utterance`` and only numbers leave. That is the
privacy architecture of the whole product, stated as a type: nothing in
``DayFeatures`` can reconstruct a sentence.

Every feature carries its literature basis and the direction that the
dementia-speech literature associates with decline. The direction is used by
the baseline engine to build a signed composite, and it is stated here rather
than hidden in engine weights so it can be argued with.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Direction = Literal["lower_is_concerning", "higher_is_concerning"]


@dataclass(frozen=True)
class Utterance:
    """One thing one person said. ``ts`` is ISO 8601; ``speaker`` is whatever
    label the source gave (Bee emits labels such as ``speaker_1``)."""

    ts: str
    text: str
    speaker: str | None = None
    conversation_id: str | None = None


@dataclass(frozen=True)
class UtteranceFeatures:
    """Raw counts and measures for a single utterance. Rates are computed at
    the day level, where the denominators are meaningful."""

    tokens: int
    words: int
    content_words: int
    pronouns: int
    nouns: int
    fillers: int
    disfluencies: int
    low_freq_words: int
    propositions: int
    dep_depth_max: int
    lemmas: tuple[str, ...] = field(default_factory=tuple)
    word_stream: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DayFeatures:
    """One day of a person's speech, reduced to numbers.

    ``token_count_day`` is the exposure denominator, not a feature: a day
    with too few tokens is excluded from baseline logic rather than treated
    as a change in the person.
    """

    date: str
    utterances: int
    token_count_day: int
    vocab_size_day: int
    mattr: float
    mean_utt_len: float
    dep_depth_mean: float
    pronoun_noun_ratio: float
    filler_rate: float
    disfluency_rate: float
    low_freq_word_rate: float
    idea_density: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    unit: str
    direction: Direction
    plain: str
    basis: str


FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="mattr",
        unit="ratio 0 to 1",
        direction="lower_is_concerning",
        plain="How varied the vocabulary is, measured in a sliding window so long days and short days are comparable.",
        basis="Moving-Average Type-Token Ratio, Covington and McFall (2010), J Quant Linguist 17(2). Reduced lexical diversity in Alzheimer's speech: Fraser, Meltzer and Rudzicz (2016), J Alzheimers Dis 49(2).",
    ),
    FeatureSpec(
        name="mean_utt_len",
        unit="words per utterance",
        direction="lower_is_concerning",
        plain="How long the average thing said is.",
        basis="Mean length of utterance as a language-complexity index, after Brown (1973). Shorter utterances in dementia discourse: Ahmed et al. (2013), Brain 136(12).",
    ),
    FeatureSpec(
        name="dep_depth_mean",
        unit="mean maximum parse depth",
        direction="lower_is_concerning",
        plain="How grammatically layered sentences are.",
        basis="Syntactic complexity via parse-tree depth; reduced syntactic complexity is among the most replicated linguistic markers of Alzheimer's speech: Fraser et al. (2016).",
    ),
    FeatureSpec(
        name="pronoun_noun_ratio",
        unit="pronouns over pronouns plus nouns",
        direction="higher_is_concerning",
        plain="How often 'it' and 'they' stand in for the actual word.",
        basis="Elevated pronoun-to-noun ratio reflects word-retrieval difficulty: Ahmed et al. (2013); Fraser et al. (2016).",
    ),
    FeatureSpec(
        name="filler_rate",
        unit="per 100 tokens",
        direction="higher_is_concerning",
        plain="Ums and uhs.",
        basis="Filled pauses as a marker of lexical retrieval effort in cognitive decline: Fraser et al. (2016); Konig et al. (2015), Alzheimers Dement (Amst) 1(1).",
    ),
    FeatureSpec(
        name="disfluency_rate",
        unit="per 100 tokens",
        direction="higher_is_concerning",
        plain="Repeated words and broken-off words.",
        basis="Repetitions and restarts in spontaneous speech of people with dementia: Konig et al. (2015).",
    ),
    FeatureSpec(
        name="low_freq_word_rate",
        unit="per 100 tokens",
        direction="lower_is_concerning",
        plain="How often rarer, more specific words are used instead of common ones.",
        basis="Word-finding difficulty shows as a shift toward high-frequency vocabulary: Fraser et al. (2016). Frequency norms from the wordfreq Zipf scale (Speer, 2022).",
    ),
    FeatureSpec(
        name="idea_density",
        unit="propositions per 10 words",
        direction="lower_is_concerning",
        plain="How much is actually said per ten words.",
        basis="Idea density in early life predicted later Alzheimer's disease in the Nun Study: Snowdon et al. (1996), JAMA 275(7). Automated approximation after CPIDR: Brown et al. (2008), Behav Res Methods 40(2).",
    ),
    FeatureSpec(
        name="vocab_size_day",
        unit="distinct content lemmas",
        direction="lower_is_concerning",
        plain="How many different words were used that day.",
        basis="Vocabulary richness alongside MATTR; sensitive to exposure, so read together with token_count_day.",
    ),
)

FEATURE_NAMES: tuple[str, ...] = tuple(f.name for f in FEATURES)


def features_schema() -> list[dict]:
    """The feature registry as plain dicts, for consumers and for the
    dashboard's info buttons."""
    return [asdict(f) for f in FEATURES]
