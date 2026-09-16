"""bellwether-ingest: Bee data in, utterances out, features before anything
is written.

Four ways Bee data reaches this package, all real call sites against the
Bee developer tooling (the track rule requires the technology be called in
code, not mentioned in a README):

    BeeCli            bee conversations list / transcript, bee now, bee changed
    parse_stream_line bee stream --json --types new-utterance
    parse_sync_markdown   bee sync output
    (proxy)           bee proxy --port N, same JSON shapes over local HTTP

Every path ends in ``speech_vitals.Utterance`` records held in memory. The
caller reduces them with ``speech_vitals.aggregate_day`` and persists the
numbers. Nothing in this package writes a transcript anywhere.
"""

from .bee import (
    BeeCli,
    BeeCliError,
    BeeNotAuthenticated,
    CursorStore,
    OwnerFilter,
    ingest_changed,
    ingest_now,
    normalize_conversation,
    normalize_utterance,
    parse_stream_line,
    parse_sync_markdown,
    speaker_label,
    to_iso,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "BeeCli",
    "BeeCliError",
    "BeeNotAuthenticated",
    "CursorStore",
    "OwnerFilter",
    "ingest_changed",
    "ingest_now",
    "normalize_conversation",
    "normalize_utterance",
    "parse_stream_line",
    "parse_sync_markdown",
    "speaker_label",
    "to_iso",
]
