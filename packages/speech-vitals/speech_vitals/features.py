"""Feature extraction: a transcript goes in, numbers come out, the words do
not come back.

Two levels. ``extract_utterance`` produces raw counts for one utterance.
``aggregate_day`` reduces a day's utterances to rates whose denominators are
meaningful, and computes the one feature (MATTR) that only makes sense over
a token stream rather than a sentence.

Design constraints, stated because they are load-bearing:

- Deterministic. Same text, same numbers, every time. The baseline engine
  and the benchmark harness both rely on it, and a reviewer must be able to
  reproduce any figure in a doctor report from the day's transcript.
- No model in the loop. spaCy's small English pipeline is a statistical
  tagger and parser, not a language model, and nothing here calls one. A
  feature that a language model could hallucinate is not a feature.
- Nothing retained. ``UtteranceFeatures`` carries the lemma and word streams
  only so the day aggregate can compute MATTR and vocabulary size; they are
  dropped at the day boundary and never persisted. ``DayFeatures`` cannot
  reconstruct a sentence.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from statistics import mean

import spacy
from wordfreq import zipf_frequency

from .types import DayFeatures, Utterance, UtteranceFeatures

# Filled pauses. Matched lexically after lowercasing, so the tagger's
# treatment of interjections does not matter.
FILLERS: frozenset[str] = frozenset(
    {"um", "uh", "er", "erm", "ah", "hmm", "mm", "mhm", "uhm", "hm"}
)

# Content words for vocabulary and word-frequency measures. Proper nouns are
# deliberately excluded from the frequency measure: a person's friends' names
# are rare in the wordfreq corpus and would count as sophisticated vocabulary.
CONTENT_POS: frozenset[str] = frozenset({"NOUN", "PROPN", "VERB", "ADJ", "ADV"})
LOW_FREQ_POS: frozenset[str] = frozenset({"NOUN", "VERB", "ADJ", "ADV"})

# Proposition-bearing parts of speech, after the CPIDR heuristic
# (Brown et al., 2008): verbs, adjectives, adverbs, prepositions and
# conjunctions each carry roughly one proposition; nouns and pronouns are
# the arguments, not the propositions.
PROPOSITION_POS: frozenset[str] = frozenset(
    {"VERB", "ADJ", "ADV", "ADP", "CCONJ", "SCONJ"}
)

# wordfreq Zipf scale: 7 is "the", 4 is roughly once per 10,000 words,
# 1 is once per hundred million. Below 4 is "rare enough to notice".
LOW_FREQ_ZIPF: float = 4.0

# Covington and McFall (2010) recommend windows between 50 and 100 tokens;
# 50 keeps short talking days measurable.
MATTR_WINDOW: int = 50


@lru_cache(maxsize=1)
def _nlp():
    # NER is not needed and is the slowest component.
    return spacy.load("en_core_web_sm", disable=["ner"])


def _depth(token) -> int:
    """Distance from a token to the root of its sentence.

    Compared by index, never by identity: spaCy hands back a new Python
    wrapper on every ``.head`` access, so ``head is token`` is false even at
    the root and an identity loop never ends. The bound is belt and braces.
    """
    depth = 0
    current = token
    limit = len(token.doc)
    while current.head.i != current.i and depth < limit:
        current = current.head
        depth += 1
    return depth


def extract_utterance(text: str) -> UtteranceFeatures:
    """Raw counts and measures for one utterance. Pure and deterministic."""
    doc = _nlp()(text or "")
    words = [t for t in doc if t.is_alpha]
    lowered = [t.text.lower() for t in words]

    fillers = sum(1 for w in lowered if w in FILLERS)

    # Disfluency: an immediately repeated word ("the the"), plus a token that
    # was broken off with a trailing hyphen ("I wan- I want"). Repeated
    # fillers are already counted as fillers, not as repetitions.
    repeats = sum(
        1
        for a, b in zip(lowered, lowered[1:])
        if a == b and a not in FILLERS
    )
    fragments = sum(
        1 for t in doc if len(t.text) > 1 and t.text.endswith("-") and t.text[:-1].isalpha()
    )

    content = [
        t for t in words if t.pos_ in CONTENT_POS and t.text.lower() not in FILLERS
    ]
    pronouns = sum(1 for t in words if t.pos_ == "PRON")
    nouns = sum(1 for t in words if t.pos_ in ("NOUN", "PROPN"))
    low_freq = sum(
        1
        for t in content
        if t.pos_ in LOW_FREQ_POS
        and zipf_frequency(t.text.lower(), "en") < LOW_FREQ_ZIPF
    )
    propositions = sum(1 for t in words if t.pos_ in PROPOSITION_POS)
    depth = max((_depth(t) for t in doc if not t.is_space), default=0)

    return UtteranceFeatures(
        tokens=sum(1 for t in doc if not t.is_space),
        words=len(words),
        content_words=len(content),
        pronouns=pronouns,
        nouns=nouns,
        fillers=fillers,
        disfluencies=repeats + fragments,
        low_freq_words=low_freq,
        propositions=propositions,
        dep_depth_max=depth,
        lemmas=tuple(t.lemma_.lower() for t in content),
        word_stream=tuple(lowered),
    )


def mattr(stream: list[str] | tuple[str, ...], window: int = MATTR_WINDOW) -> float:
    """Moving-Average Type-Token Ratio (Covington and McFall, 2010).

    The mean type-token ratio over every window of ``window`` tokens. Unlike
    plain TTR it does not fall as a day gets longer, which is the whole
    reason to use it on days of very different length. A stream shorter than
    one window falls back to plain TTR, which is the only honest value.
    """
    n = len(stream)
    if n == 0:
        return 0.0
    if n <= window:
        return len(set(stream)) / n

    counts: Counter[str] = Counter(stream[:window])
    distinct = len(counts)
    total = distinct / window
    windows = 1
    for i in range(window, n):
        leaving = stream[i - window]
        counts[leaving] -= 1
        if counts[leaving] == 0:
            del counts[leaving]
            distinct -= 1
        entering = stream[i]
        if counts[entering] == 0:
            distinct += 1
        counts[entering] += 1
        total += distinct / window
        windows += 1
    return total / windows


def _empty_day(date: str, utterances: int) -> DayFeatures:
    return DayFeatures(
        date=date,
        utterances=utterances,
        token_count_day=0,
        vocab_size_day=0,
        mattr=0.0,
        mean_utt_len=0.0,
        dep_depth_mean=0.0,
        pronoun_noun_ratio=0.0,
        filler_rate=0.0,
        disfluency_rate=0.0,
        low_freq_word_rate=0.0,
        idea_density=0.0,
    )


def aggregate_day(utterances: list[Utterance], date: str | None = None) -> DayFeatures:
    """Reduce one day's utterances to ``DayFeatures``.

    Rates are per 100 words, idea density per 10 words, both following the
    conventions of the literature they cite. ``token_count_day`` counts
    alphabetic words: punctuation is not exposure to language.
    """
    ordered = sorted(utterances, key=lambda u: u.ts)
    day = date or (ordered[0].ts[:10] if ordered else "")
    feats = [extract_utterance(u.text) for u in ordered]
    spoken = [f for f in feats if f.words > 0]
    total_words = sum(f.words for f in spoken)
    if not spoken or total_words == 0:
        return _empty_day(day, len(feats))

    stream = [w for f in spoken for w in f.word_stream]
    lemmas = {lemma for f in spoken for lemma in f.lemmas}
    pronouns = sum(f.pronouns for f in spoken)
    nouns = sum(f.nouns for f in spoken)
    per_100 = 100.0 / total_words

    return DayFeatures(
        date=day,
        utterances=len(spoken),
        token_count_day=total_words,
        vocab_size_day=len(lemmas),
        mattr=round(mattr(stream), 4),
        mean_utt_len=round(total_words / len(spoken), 3),
        dep_depth_mean=round(mean(f.dep_depth_max for f in spoken), 3),
        pronoun_noun_ratio=round(pronouns / (pronouns + nouns), 4) if (pronouns + nouns) else 0.0,
        filler_rate=round(sum(f.fillers for f in spoken) * per_100, 3),
        disfluency_rate=round(sum(f.disfluencies for f in spoken) * per_100, 3),
        low_freq_word_rate=round(sum(f.low_freq_words for f in spoken) * per_100, 3),
        idea_density=round(sum(f.propositions for f in spoken) * 10.0 / total_words, 3),
    )
