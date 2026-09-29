# Bellwether: what is left, and when

Written 2026-09-29, the day the Bee arrived and the chain first ran on
live data. Deadline 2026-10-23, 3:00pm EDT. Everything a judge can read
is finished; what remains is gated by days on the wristband, and the
rest is parked here so nothing waits on memory.

## The band, every day

Wear it through ordinary conversation, not only work. A day with under
150 words of the wearer's own speech is excluded rather than counted,
so quiet days give the baseline nothing to learn from. The engine
needs seven days of warmup before it compares anything; the video's
two live shots need at least ten days worn.

- 2026-10-06: first pull. `./.venv/Scripts/bellwether-ingest pull
  --owner <label> --out days.json` from the repository root, then
  `bellwether-ingest evidence` to refresh `docs/BEE_LIVE.md` with a
  week of days and no words. Look at the baseline forming on `/app`.
  Speaker labels were "Unknown" on day one; the pull takes whatever
  label Bee has settled on by then.
- 2026-10-13: fourteen days. Record the two live shots (below), cut,
  upload, done with a week to spare.

## The video (not started; the script is written)

`docs/VIDEO_SCRIPT.md`: nine shots, 2:55, the two live shots are 4 and
5. Build the pipeline the way Earshot's was built
(`earshot/video/`: `beats.py` as the single source, `narrate.py` for
Polly, `record.py` for the browser at 4K with the clapperboard,
`assemble.py`, `subtitle.py`), on the stand-in persona first so the
only thing left on the 13th is the two live shots.

- A second camera for the terminal shots: real commands, real output,
  rendered in a terminal frame the same recorder captures, and the
  script says that is what it is. Do not fake output; do not speed
  anything up.
- From the wearer: two seconds of phone video of the band on the wrist.
- Every line keeps the site's line: no condition named, the disclaimer
  spoken aloud, "not a diagnosis" on screen where the tiers are.
- Under 3:00, public on YouTube, English, no music, no third-party
  footage. Upload the captioned mp4 only, not the .srt as well.
- Then the URL into `docs/SUBMISSION.md` under Live, and the friction
  log's "Still to record" section in `PRODUCT_FEEDBACK.md` closed.

## The wearer's first day (to build while the band accumulates)

Day one for a real wearer is a command line. A judge who asks "what
does my mother do with this" should get one command that pairs, pulls,
and opens the dashboard on the wearer's own profile, with the same
words the Bee app uses when something is missing. This is the missing
point on Design and it does not need the device to build; it needs
the device to prove, which the 13th provides.

## Still yours

- `bee login` is done on this machine; if the token expires, `bee login`
  again and approve in the Bee app.
- The Nightlight video URL into every submission doc.

## Known and accepted

- Profile timezone is America/New_York; days are grouped by UTC date,
  which for India puts the day boundary at 05:30 local. Nothing to do.
- The Bee track's stated priorities are education, developer experience
  and personal productivity; this is a wellness tool, entered on the
  strength of the work.
- No ADReSS validation, no user testing, English only: all stated in
  `docs/SUBMISSION.md` under Honest limits.
