# Live Bee data: what actually came back

Evidence that this project reads a real Bee device, captured by
`bellwether-ingest evidence`.

Captured: 2026-10-08T05:07:37+00:00. Commands answering: 3 of 3.

Counts, shapes and the nine features only. No transcript text, no conversation titles, no names, no locations. The input is a real person's day and the output is designed to be publishable.

## Commands

| Call | Command | Result |
|---|---|---|
| account | `bee me --json` | answered |
| recent hours | `bee now --json` | answered |
| conversations | `bee conversations list --json` | answered |

## What the device returned

- Conversations: 133
- Utterances: 15578
- Days with speech: 9
- Words read on this machine: 130229
- Words written to this file: 0

That last pair is the product in one line. The words were read, counted
and thrown away, and only the numbers left the machine.

## The nine features, from a real day

```json
[
 {
  "date": "2026-09-29",
  "utterances": 454,
  "token_count_day": 3276,
  "mattr": 0.7723,
  "mean_utt_len": 7.216,
  "dep_depth_mean": 2.604,
  "pronoun_noun_ratio": 0.5182,
  "filler_rate": 0.336,
  "disfluency_rate": 0.366,
  "low_freq_word_rate": 4.335,
  "idea_density": 3.816,
  "vocab_size_day": 681
 },
 {
  "date": "2026-09-30",
  "utterances": 1164,
  "token_count_day": 8090,
  "mattr": 0.7411,
  "mean_utt_len": 6.95,
  "dep_depth_mean": 2.546,
  "pronoun_noun_ratio": 0.4871,
  "filler_rate": 0.099,
  "disfluency_rate": 0.729,
  "low_freq_word_rate": 4.648,
  "idea_density": 3.888,
  "vocab_size_day": 1287
 },
 {
  "date": "2026-10-01",
  "utterances": 939,
  "token_count_day": 6902,
  "mattr": 0.7617,
  "mean_utt_len": 7.35,
  "dep_depth_mean": 2.655,
  "pronoun_noun_ratio": 0.5219,
  "filler_rate": 0.101,
  "disfluency_rate": 0.478,
  "low_freq_word_rate": 3.231,
  "idea_density": 4.068,
  "vocab_size_day": 1117
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
  "timezone": "<string, 15 chars>"
 },
 {
  "since": 1791400059048,
  "until": 1791436059048,
  "timezone": "<string, 15 chars>",
  "conversations": [
   "list of 13"
  ]
 },
 {
  "conversations": [
   "list of 50"
  ],
  "next_cursor": "<string, 25 chars>",
  "timezone": "<string, 15 chars>"
 }
]
```
