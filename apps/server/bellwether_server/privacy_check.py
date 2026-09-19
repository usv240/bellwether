"""The privacy claim, shown working rather than asserted.

Why this exists
---------------
Bellwether's whole premise is that it never holds what a person said.
Nine numbers a day cross the line; the words stay on the machine that
heard them. The page said so, a test proved it, and a visitor had no way
to see either. For a product that listens to somebody's speech, "trust
us" is the one argument that cannot be allowed to carry the weight.

So this makes it pressable. One request sends a day to the real intake
route with a transcript attached that is full of exactly what must never
be stored: a name, a doctor, a family member, an address, an account
number. It then reads back what the store kept and searches the stored
row for every one of those strings.

The mirror of the Ring proof in the sibling Nightlight project, where the
interesting rows are the refusals. Here the interesting result is an
absence, so the check reports what it looked for and did not find, not
only that the request succeeded.

What is real here, and what is not
----------------------------------
Real: `build_app`, the production `POST /v1/profiles/{id}/days` route, its
`validate_day`, the store's `put_day`, and the `GET` that reads it back.
Driven through FastAPI's TestClient, which exercises the full request
path including JSON parsing and validation.

Not real: the store. It is a fresh MemoryStore built for this request,
so a visitor pressing a button cannot write rows into the deployed
table, and the transcript sent here is never anywhere but this process.
The page says so.
"""

from __future__ import annotations

import time
from typing import Any

# What a real Bee transcript of an ordinary day contains, and what a
# system like this must never keep. Every one is searched for afterwards.
SENSITIVE = {
    "a name": "Margaret",
    "a doctor": "Dr. Okafor",
    "a family member": "my son Daniel",
    "an address": "14 Larkspur Lane",
    "an account number": "4472 9910",
    "a medication": "donepezil",
}

TRANSCRIPT = (
    "Morning. It's Margaret. I saw Dr. Okafor on Tuesday about the "
    "donepezil, and my son Daniel is driving over from 14 Larkspur Lane "
    "later. The bank rang about account 4472 9910, I told them I'd call back."
)

# The nine numbers one real day reduces to, taken from the demo profile's
# shape so the row is one the engine would accept on its own merits.
FEATURES = {
    "vocab_size_day": 112,
    "mattr": 0.749,
    "mean_utt_len": 15.452,
    "dep_depth_mean": 4.381,
    "pronoun_noun_ratio": 0.3947,
    "filler_rate": 1.233,
    "disfluency_rate": 0.924,
    "low_freq_word_rate": 6.78,
    "idea_density": 4.314,
}


def run_privacy_check() -> dict[str, Any]:
    # Imported here so the module imports cleanly in environments that
    # never serve the check, and so build_app's own import of this module
    # cannot become circular.
    from fastapi.testclient import TestClient

    from .app import build_app
    from .store import MemoryStore

    started = time.perf_counter()
    profile = "privacy-check"
    app = build_app(store=MemoryStore(), default_profile=profile, seed=False)
    client = TestClient(app)

    sent = {
        "date": "2026-09-19",
        "utterances": 42,
        "token_count_day": 649,
        **FEATURES,
        # Three places a careless integration puts words. Every one must go.
        "transcript": TRANSCRIPT,
        "speaker_name": "Margaret",
        "notes": "follow up with Dr. Okafor re donepezil",
    }

    post = client.post(f"/v1/profiles/{profile}/days", json=[sent])
    got = client.get(f"/v1/profiles/{profile}/days")
    body = got.json()
    rows = body if isinstance(body, list) else body.get("days", [])
    stored = rows[0] if rows else {}

    # Search the whole stored row, keys and values, for every sensitive
    # string. Stringifying the row means a value nested anywhere, or a key
    # that happened to carry text, is found too.
    haystack = repr(stored).lower()
    findings = [
        {"what": what, "looked_for": needle, "found": needle.lower() in haystack}
        for what, needle in SENSITIVE.items()
    ]

    dropped = sorted(k for k in sent if k not in stored)
    kept = sorted(stored)
    strings_kept = sorted(k for k, v in stored.items() if isinstance(v, str))

    return {
        "sent": {
            "fields": sorted(sent),
            "transcript": TRANSCRIPT,
        },
        "response": {"status": post.status_code, "body": post.json()},
        "stored": stored,
        "kept": kept,
        "dropped": dropped,
        # The page's claim is that a stored row holds no string but the
        # date. This is that claim, measured on the row just written.
        "strings_kept": strings_kept,
        "findings": findings,
        "any_found": any(f["found"] for f in findings),
        "sandbox": True,
        "ms": round((time.perf_counter() - started) * 1000),
    }
