# Live Bee data: what actually came back

Evidence that this project reads a real Bee device, captured by
`bellwether-ingest evidence`.

Captured: 2026-09-29T21:02:33+00:00. Commands answering: 3 of 3.

Counts, shapes and the nine features only. No transcript text, no conversation titles, no names, no locations. The input is a real person's day and the output is designed to be publishable.

## Commands

| Call | Command | Result |
|---|---|---|
| account | `bee me --json` | answered |
| recent hours | `bee now --json` | answered |
| conversations | `bee conversations list --json` | answered |

## What the device returned

- Conversations: 2
- Utterances: 45
- Days with speech: 1
- Words read on this machine: 446
- Words written to this file: 0

That last pair is the product in one line. The words were read, counted
and thrown away, and only the numbers left the machine.

## The nine features, from a real day

```json
[
 {
  "date": "2026-09-29",
  "utterances": 45,
  "token_count_day": 446,
  "mattr": 0.8262,
  "mean_utt_len": 9.911,
  "dep_depth_mean": 3.467,
  "pronoun_noun_ratio": 0.4637,
  "filler_rate": 0.673,
  "disfluency_rate": 0.224,
  "low_freq_word_rate": 4.036,
  "idea_density": 4.283,
  "vocab_size_day": 157
 }
]
```

## Response shapes

Field names and value types, so the integration can be checked without
publishing any content.

```json
[
 {
  "id": 53269,
  "first_name": "<string, 5 chars>",
  "last_name": "<string, 7 chars>",
  "timezone": "<string, 16 chars>"
 },
 {
  "since": 1790679754238,
  "until": 1790715754238,
  "timezone": "<string, 16 chars>",
  "conversations": [
   "list of 2"
  ]
 },
 {
  "conversations": [
   "list of 2"
  ],
  "next_cursor": null,
  "timezone": "<string, 16 chars>"
 }
]
```
