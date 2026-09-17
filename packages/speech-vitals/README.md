# speech-vitals

Language features from everyday speech transcripts, for personal n-of-1 baselines. **Features only, never words.**

A transcript goes in. Nine numbers per day come out. None of them can reconstruct a sentence. That is the privacy architecture of anything built on this package, expressed as a type rather than a promise.

## Install

Not yet on PyPI. Install from the repository:

```
pip install "git+https://github.com/usv240/bellwether.git#subdirectory=packages/speech-vitals&egg=speech-vitals[nlp]"
python -m spacy download en_core_web_sm
```

Or from a clone:

```
pip install -e "packages/speech-vitals[nlp]"
python -m spacy download en_core_web_sm
```

The core (schema, MATTR, the feature registry) has no dependencies and imports anywhere. The `nlp` extra adds spaCy and wordfreq, which extraction needs.

## Use

```python
from speech_vitals import Utterance, aggregate_day

day = aggregate_day([
    Utterance(ts="2026-09-16T08:12:03Z", text="Well, um, the garden looked lovely this evening.", speaker="speaker_1"),
    Utterance(ts="2026-09-16T19:40:11Z", text="I think we should, uh, call them tomorrow.", speaker="speaker_1"),
])

day.mattr               # lexical diversity, length-stable
day.idea_density        # propositions per 10 words
day.pronoun_noun_ratio  # 'it' and 'they' standing in for the word
day.token_count_day     # exposure: how much was said at all
```

Or from the shell, on a JSON Lines file of `{ts, text, speaker}`:

```
speech-vitals analyze transcript.jsonl --speaker speaker_1 --out days.json
speech-vitals schema
```

## The features

Each carries the direction the dementia-speech literature associates with decline, and its basis. `speech-vitals schema` prints the same table.

| Feature | Unit | Concerning direction | Basis |
|---|---|---|---|
| `mattr` | ratio | lower | Covington and McFall 2010; Fraser, Meltzer and Rudzicz 2016 |
| `mean_utt_len` | words per utterance | lower | Brown 1973; Ahmed et al. 2013 |
| `dep_depth_mean` | parse depth | lower | Fraser et al. 2016 |
| `pronoun_noun_ratio` | ratio | higher | Ahmed et al. 2013; Fraser et al. 2016 |
| `filler_rate` | per 100 words | higher | Fraser et al. 2016; Konig et al. 2015 |
| `disfluency_rate` | per 100 words | higher | Konig et al. 2015 |
| `low_freq_word_rate` | per 100 words | lower | Fraser et al. 2016; wordfreq Zipf scale |
| `idea_density` | per 10 words | lower | Snowdon et al. 1996; Brown et al. 2008 |
| `vocab_size_day` | distinct lemmas | lower | read with `token_count_day` |

`token_count_day` is the exposure denominator, not a feature: a quiet day is not a change in the person.

## Design constraints

- **Deterministic.** Same text, same numbers. A reviewer can reproduce any figure from the day's transcript.
- **No model in the loop.** spaCy's small English pipeline is a tagger and parser, not a language model. A feature a model could hallucinate is not a feature.
- **Nothing retained.** Word streams exist only inside `aggregate_day`, for MATTR and vocabulary size, and are dropped at the day boundary. A test asserts that `DayFeatures` holds no string but the date.
- **Length-stable.** MATTR is used instead of type-token ratio precisely so a long day and a short day are comparable.

## What this is not

Not a diagnostic instrument. Speech varies with sleep, stress, mood, medication, illness, and who you are talking to. These features describe change over time in one person against their own baseline; they do not classify anyone against anyone else, and this package makes no claim about any condition.

## License

MIT.
