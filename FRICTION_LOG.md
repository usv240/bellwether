# Friction log

Each entry: the task attempted, the steps taken, what was expected against what happened, a severity, the workaround, and an actionable suggestion. Entries are written the day they happen. Bee-device entries will follow the day the device arrives; everything below was hit before it did.

## Entry 1: Bee's docs name the fields but publish no JSON example (2026-09-17)

- Task: write the ingestion normaliser for `bee conversations transcript --json`, `bee now --json` and `bee stream --json` before the device arrived.
- Steps: read docs.bee.computer (CLI reference, Full Sync), the bee-cli README, and the bee-skill SKILL.md, looking for one complete JSON payload of a conversation or an utterance.
- Expected: a sample response per command, as most API references carry.
- Actual: the field names are documented (`text`, `speaker`, `start_time`, `end_time`, `created_at`, `next_cursor`), and the README describes payloads with placeholder fragments such as `"speaker": "speaker_1"`, but no command shows a full response, so the nesting (is `utterances` top-level or under `transcriptions[]`? is `speaker` a string or an object?) has to be guessed.
- Severity: medium. It does not block a build, but it turns a one-hour adapter into a tolerant parser with alternates for every key, plus a test fixture per guessed shape, and the first real device will still be the first real test.
- Workaround: `normalize_utterance` and `normalize_conversation` accept the documented key first and sensible alternates after (string or object speakers, ISO or epoch times, flat or nested utterance lists), and a fake runner pins every accepted shape in tests.
- Suggestion: one verbatim `--json` example per data command in the CLI reference, and a JSON Schema for `Conversation` and `Utterance` that the stream, the transcript command and the proxy all share.

## Entry 2: speakers are labelled, not identified, so the wearer's own speech cannot be isolated without a guess (2026-09-17)

- Task: analyse only the wearer's speech, which is the whole premise of a personal baseline, and drop everyone else's at ingest.
- Steps: read the Full Sync output format and the CLI reference for any owner or user flag on an utterance.
- Expected: something like `is_user`, `is_owner`, or a stable speaker id that the app already resolves to the wearer, given that the app knows whose device it is.
- Actual: transcripts carry generic labels (`Speaker 1`, `Speaker 2`), and the JSON `speaker` carries `name` and `id` with no documented meaning for "the wearer". Nothing in the docs says which label is the person wearing the band.
- Severity: high for this use, and for any analysis of the wearer specifically. It is the difference between measuring a person and measuring a room.
- Workaround: `OwnerFilter` takes a configured owner label, and otherwise assumes the label with the most utterances across the corpus is the wearer, which is the person the device is on. Stated in code, in the README, and here.
- Suggestion: a boolean `is_user` on every utterance, resolved by the app from voice enrolment, and a documented statement of how stable speaker ids are across conversations and days.

## Entry 3: bee sync markdown carries no per-utterance timestamps (2026-09-17)

- Task: use the offline `bee sync` export as an ingestion path for a full history.
- Steps: read the sync output format: conversation files with `### Transcription <id>` headers and `- Speaker 1: text` lines.
- Expected: a time per utterance, since the JSON commands carry `start_time` and `end_time`.
- Actual: the markdown lines carry speaker and text only; the conversation's day is the only time available, and the format notes `realtime: false`.
- Severity: medium. Day-level features do not need finer time, so this path still works for Bellwether, but any analysis of pacing, turn-taking or time of day is closed to the offline export.
- Workaround: `parse_sync_markdown` stamps every line with the conversation's day and says so in its docstring rather than inventing times.
- Suggestion: a `--json` option on `bee sync` that writes the same records the transcript command returns, alongside the markdown.

## Entry 4: the CLI is npm on Windows and works, though the docs do not say so (2026-09-17, positive)

- Task: install and exercise the Bee CLI on Windows 11 before the device arrived, to make the ingestion call sites real rather than hypothetical.
- Steps: `npm install -g @beeai/cli`, `bee --version`, `bee status`, then `bee <command> --help` for every command the adapter would call.
- Expected: uncertainty. The README discusses Unix socket paths and lists iOS and Android apps, and never mentions Windows.
- Actual: it installed and ran first time, printed the developer API endpoint and a clear "Not logged in." rather than crashing, and every `--help` was accurate to the command. The only Windows-specific wrinkle is that npm installs a `.cmd` shim, so a subprocess call needs `cmd /c` in front of it, which the adapter handles.
- Severity: none. Recorded because it is the opposite of the experience the sibling projects had with other toolchains on Windows, and it deserves saying.
- Suggestion: one line in the README: "Windows: supported via npm; use `--port` rather than `--socket` for the proxy."

## Entry 5: Android is early access and unsupported, which narrows who can enter the Bee track (2026-09-17)

- Task: decide whether the operator's Pixel phone could pair the device.
- Steps: read the Bee FAQ and product page on platform support.
- Expected: parity, or a stated timeline.
- Actual: iOS is the supported platform. The Android build is early access, "includes only some core features", and "is not actively being supported right now". Bee ships to United States addresses only.
- Severity: medium for this project (the operator also has an iPhone), high for the track's reach: an Android-only developer outside the United States has no way to enter at all.
- Workaround: pair with the iPhone.
- Suggestion: state the platform and shipping constraints on the hackathon's Bee track page, not only in the FAQ, so entrants know before they plan.

## Entry 6: Lambda function URL CORS plus app CORS equals two headers and a broken browser (2026-09-18)

- Task: load the deployed dashboard, which fetches the deployed API from a different origin (CloudFront to a Lambda function URL).
- Steps: configure CORS on the function URL in CDK (`allowedOrigins: ["*"]`, `exposedHeaders: ["MCP-Session-Id"]`, which the MCP transport needs), and separately add FastAPI's `CORSMiddleware` because that is what every FastAPI tutorial does.
- Expected: one of them wins, or they agree.
- Actual: both emit `Access-Control-Allow-Origin`, so the response carried two values, `*` and the reflected origin. Chrome refuses that: "contains multiple values, but only one is allowed". Every API call from the browser failed.
- What made it expensive: nothing on the command line could see it. `curl` does not enforce CORS, so every manual check returned 200 with plausible headers, and eighteen server tests passed because `TestClient` does not enforce it either. The only signal was Lighthouse's console audit on the deployed site, which is not where anyone looks for a CORS bug.
- Severity: high. On a project whose live demo is the thing judges click, this is the difference between a working dashboard and an empty one, and it is invisible to every non-browser check.
- Workaround: CORS is handled by exactly one layer. The app adds its middleware only when `AWS_LAMBDA_FUNCTION_NAME` is absent, so the function URL owns it in Lambda and the middleware owns it locally.
- Suggestion, for AWS: the function URL CORS configuration should either strip a conflicting `Access-Control-Allow-Origin` emitted by the handler or log a warning, because the combination is silent, common (every FastAPI and Express example adds middleware), and only reproducible in a browser. A line in the Lambda function URL CORS documentation saying "do not also set CORS headers in your handler" would have prevented it outright.

## Entry 7: our own dashboard hid its most important panel behind a fetch (2026-09-18, ours not theirs)

- Task: check that the "What else could explain this" panel, which gives the ordinary explanations for a flagged change, actually reaches a reader.
- Steps: curl the deployed dashboard and grep the prerendered HTML for the panel's text.
- Expected: present. It is static content; nothing in it depends on the API.
- Actual: absent. The whole dashboard body sat inside a `{summary && (...)}` branch, so every word of it, including the panel whose entire purpose is to reach a worried person before the frightening interpretation does, existed only after a successful API call. A judge on a slow connection, or anyone hitting a failed fetch, would have seen a nav bar and a simulated-data badge.
- Severity: high, and higher for this panel than for any other. The risk-communication literature is explicit that the ordinary explanations must accompany the result; making them conditional on a network call inverts the design.
- Workaround: the panel renders unconditionally and takes a nullable summary, adapting only the tier word once data arrives. Verified in the deployed HTML.
- Why it is in this log: it is our bug, not a platform's, and it is the second time in this hackathon that client-gated content silently removed the case for a project from the page. Recorded so the pattern is named: anything that explains, reassures or qualifies should render before anything that fetches.

## Entry 8: spaCy fails to import from a deep Windows path, and the error names the wrong thing (2026-09-17)

- Task: verify the README's own setup from a clean clone, on the theory that a reviewer will do exactly that and nothing else.
- Steps: clone into a nested working directory, `python -m venv .venv`, install the four packages, `python -m spacy download en_core_web_sm`, run the suite.
- Expected: the 112 tests that pass in development.
- Actual: sixteen failures, every one of them a spaCy import, with `ImportError: DLL load failed while importing transition_system: The filename or extension is too long.` The model download reported the same error and still printed a success line.
- What made it expensive: the message points at spaCy's compiled parser, so the obvious readings are a broken wheel, a Python version mismatch, or a corrupt model. The actual cause is Windows MAX_PATH: the venv's `site-packages` path plus spaCy's own nesting crosses 260 characters and the loader gives up. The same clone at `C:/tmp/bwx` installs and passes all 112. Nothing about the failure suggests the parent directory is the variable.
- Severity: medium for us, high for anyone judging on Windows. A reviewer who clones into a deep folder sees a sixth of the suite fail and reasonably concludes the project does not run.
- Workaround: clone to a short path. Documented in the README next to the setup block rather than buried here, because the person who needs it is reading the README.
- Suggestion: spaCy could name the real cause on Windows when an extension import fails and the resolved path is near the limit, and `spacy download` should not print a success line after an import error. This is the second MAX_PATH failure across our three projects this hackathon; the other took most of a day in a React Native TV build.

## Entry 9: this server was already right, and we only know because we probed all three (2026-09-17, positive, and a method note)

- Task: prove the claim "the MCP server is live and spec correct" in a way a reviewer can check. An MCP URL opened in a browser shows an error, because the protocol is a POST with a session handshake, so there is nothing to click.
- Steps: run `node scripts/mcp-conform.mjs --all`, a dependency-free probe that speaks the Streamable HTTP transport over real HTTP and grades each check as MUST or SHOULD against spec revision 2025-11-25, against this server and the two sibling projects.
- Expected: three passes, since all three have conformance suites that pass.
- Actual: this server, nineteen of nineteen. The two Node servers, eighteen of nineteen each: both answered an unparseable body with an HTTP 500 carrying the framework's error envelope, where JSON-RPC calls for -32700. FastAPI's request parsing raises where the app can catch it and turn it into a protocol error; Fastify's content-type parser callback defaults to a 500 unless the error carries a status code.
- Severity: none here, and it is logged as a positive for that reason. The note worth keeping is about method rather than about this bug.
- Why it is in this log: we would not have trusted a green result from a probe that had only ever met one implementation. Running the same file against two frameworks is what made the pass meaningful, and it is also what found the other two servers' defect. A conformance check against your own server tells you your server agrees with itself.

## Entry 10: the spec says to validate Origin and does not say to allow your own site (2026-09-20, ours, and a spec-docs gap)

- Task: let a visitor press a button on the Bellwether website and watch a complete MCP session run against the deployed server, because the Alexa+ track asks for the server to be shown in action rather than described.
- Steps: build the panel, deploy it, open the live site in a real browser and press the button.
- Expected: the same five steps that `scripts/mcp-conform.mjs` had already passed nineteen of nineteen against this exact server.
- Actual: HTTP 403 on `initialize`, from our own front page. The transport section of spec revision 2025-11-25 tells implementers to validate the `Origin` header to defend against DNS rebinding. The natural reading of that, and the one we took, is an allowlist of loopback addresses, which is correct for a server whose only clients are local. It silently makes the product's own website a forbidden caller.
- Severity: medium. It cost no data and broke nothing that existed, but it would have been high had we shipped the panel without opening it in a browser, since the track requirement it answers is the one that would have failed on camera.
- Workaround: allow loopback plus the site's own origin plus anything named in an environment variable, and test that a correct caller is admitted rather than only that an incorrect one is refused.
- Suggestion: the transport section could add one sentence, that a server which also serves a browser client must include that client's origin in the allowlist, and ideally a two-line example. The guidance as written describes what to keep out and leaves what to let in to be inferred. Worth noting how it hid: every conformance test passed, every `curl` succeeded, and the nineteen-check live probe was green, because none of them sends an `Origin` header the way a browser always does. A rule only wrong callers can trip is indistinguishable from a correct rule until a right caller turns up.

## Entry 11: the Bee CLI's real shapes differ from its readme in three ways, and the first one silently returns nothing (2026-09-29, the day the device arrived)

- Task: run the rehearsed first session against the real wristband: list conversations, reduce a day to nine features, prove no words leave the machine.
- Steps: `bee login`, then `bellwether-ingest firstrun` against bee-cli 0.7.3 with two conversations recorded that afternoon.
- Expected: the fixtures had been written from the readme, which says `conversations list` lists conversations and `get` returns one, and the parser accepted every utterance shape the readme describes.
- Actual: three surprises. `bee conversations list --json` returns summaries and an `utterances_count` and not one utterance, so a parser fed the list reduces a full afternoon to zero days with no error. `bee conversations get <id> --json` wraps the record as `{"conversation": {...}, "timezone": ...}`, where `now` and `changed` return bare records, so the same parser sees words in one and nothing in the other. And each utterance carries `spoken_at` and `created_at` as epoch milliseconds beside `start` and `end` as seconds into the conversation; a parser that prefers `start` as a time puts every word on 1970-01-01 and a personal baseline on one impossible day. None of the three is in the readme.
- Severity: high for anyone building on the CLI, because the first two fail silently: an empty result looks like a quiet device, not a wrong call. Low for us on the day, because the rehearsal was built to stop at the first wrong step and say so, and it did.
- Workaround: rows without utterances are fetched one by one with `get`, bounded, and unwrapped; `spoken_at` is read first; integers too small to be an instant are never read as one. Pinned in `apps/ingest/tests/test_device_shapes.py` with the device's field names and placeholder words.
- Suggestion: say in the readme which commands return utterances and which return counts, give one example response per command with its wrapper, and name the unit of every time field. Or make `list` accept `--with-utterances`, which is what everybody who lists conversations wants next.

## Entry 12: every speaker is "Unknown", so a product about the wearer's own speech cannot find the wearer (2026-10-08, nine days worn)

- Task: reduce nine days on the wrist to the wearer's own daily speech features, which is the whole premise of a personal baseline.
- Steps: paired the band 2026-09-29, wore it daily, pulled 133 conversations and 15,578 utterances on 2026-10-08, counted the `speaker` values; tried the Bee app's voice setup, which reports that the wearer's voice is already enrolled; checked the five newest conversations again afterwards.
- Expected: either a label that identifies the wearer, an `is_user` flag on each utterance (entry 2 asked for this before the device arrived), or a way to tell the app which voice is yours.
- Actual: all 15,578 utterances say "Unknown", and so does every utterance recorded after the app confirmed the voice was enrolled (five conversations on 2026-10-08, 590 utterances). The app knows the voice; the developer data never uses it. The CLI has no flag, and the readme does not say whether labels ever split. The band picks up everyone nearby, so a day's text is the wearer, the people they talk to and any training or film playing, with nothing to tell them apart: two days on this account had about 44,000 words each because the band sat through five- and six-hour group trainings.
- Severity: high, and the most important entry here. A Bee product for a person, which is the track's own framing, needs to know which speech is that person's.
- Workaround: `bellwether-ingest pull --backfill --max-minutes 60` leaves out sessions longer than an hour and any Bee's own summary names as media (read locally, never stored). The days fall to between 1,500 and 12,000 words, which looks like everyday conversation, and the site and video say plainly that speakers are not told apart. It is a filter, not an identification.
- Suggestion: carry the app's existing voice enrolment through to the developer API, as a wearer flag on each utterance. That one field would make every personal product on Bee possible. Reported to Bee: [bee-cli issue #19](https://github.com/bee-computer/bee-cli/issues/19), with a backwards-compatible proposal (an `is_wearer` field, a `diarized` flag and a `--wearer-only` filter) in [the comment that follows it](https://github.com/bee-computer/bee-cli/issues/19#issuecomment-6069168908), and by email to hi@bee.computer. Short of that, a documented field saying whether diarization ran and how many distinct speakers it found per conversation.

## Entry 13: `bee changed` with no cursor answers with recent changes only, so the first pull of a history returns two days of nine (2026-10-08)

- Task: the first full pull after nine days worn.
- Steps: `bellwether-ingest pull --out days.json`, which starts from `bee changed` with no cursor and keeps the returned cursor for next time.
- Expected: no cursor means from the beginning, as for most change feeds.
- Actual: two days of features from 133 conversations across nine. Nothing errored; it looked like a quiet week.
- Severity: medium. Silent, and it lands on the first run, which is the one a new developer judges the platform by.
- Workaround: `pull --backfill` pages `bee conversations list` to the end and fetches every row with `get` (about three minutes for 133 conversations). The evidence capture does the same.
- Suggestion: document the window `changed` covers without a cursor, or accept `--since <date>`; and add `--all` to `conversations list` so paging is not every client's job. We wrote the second one: [bee-cli PR #20](https://github.com/bee-computer/bee-cli/pull/20) adds `bee conversations list --all`, with four tests and one round of review feedback addressed; on this account it returns all 143 conversations where `list` alone returns 20.

## Entry 14: the one Bee stream whose speaker is certain is the voice note, and nothing in the docs says so (2026-10-13, fourteen days worn, partly positive)

- Task: with every conversation utterance labelled "Unknown" (entry 12), find any Bee data that is the wearer's own speech by construction rather than by filter.
- Steps: read the CLI's resource list, tried `bee journals list --json`, `get` and `search`; recorded two voice notes in the Bee app and pulled them; built `bellwether-ingest pull --journals`, which reads only that resource and labels every utterance as the wearer.
- Expected: nothing. The readme describes journals as notes, with no mention that they are recorded on purpose by the person wearing the band.
- Actual: they are exactly that. A voice note is the wearer pressing record and speaking, so its `text` is the wearer's speech with nobody else in it, and the CLI returns it with an `id`, `state` and `created_at` in epoch milliseconds, the same conventions as conversations. Two notes recorded at 17:37 UTC came back processed within the minute. Bellwether now runs two streams of real data side by side: the wearer's voice notes, whose speaker is certain, and the band's everyday conversations, whose speaker is not; the site labels which is which.
- Severity: low as a defect, high as a finding. It costs the wearer about two minutes of talking a day (the engine excludes any day under 150 words), which is a real price, and the docs could have saved a week of waiting for labels by saying this is the stream for the wearer's own voice.
- Workaround: `bellwether-ingest pull --journals --out voice.json`, then post to a profile of its own, so neither stream is mistaken for the other.
- Suggestion: say in the journals reference that notes are the wearer's own speech, and give the resource a word count or duration field so a client can tell a ten-second note from a two-minute one without reading the text.

## Entry 15: a static prerender cannot see the URL, so every real-data page hydrated with a mismatch nobody noticed (2026-10-13, ours)

- Task: show the wearer's two real profiles on the same dashboard as the simulated person, chosen by `?profile=` on a statically exported Next.js site.
- Steps: read the profile from `window.location.search` at module load; render the badge, note and switcher from it; export the site; open `/app?profile=me-voice`; later, re-run Lighthouse on the deployed page after adding the first-week card.
- Expected: the page shows the real profile, which it did, and every audit stays at 100, which the landing page and report did.
- Actual: the dashboard's best-practices score fell to 96 on one audit, errors in console, carrying React error #418: the prerendered HTML said "Simulated person" and the client's first render said "Real Bee". React patched the text and the page looked right, so no screenshot, test or human saw it. Only the console did.
- Severity: low for a visitor, medium for the project: a hydration mismatch on every real-data page is the kind of thing a reviewer opens DevTools and finds, and the dashboard is where the Bee track's live data is shown.
- Workaround: anything that names the profile waits for the client (`mounted` state set in an effect) and the prerender carries a neutral header. All three pages are back to 100 on accessibility, best practices and SEO.
- Suggestion: for ourselves, run Lighthouse on the pages that take parameters and not only on the landing page; a static export with URL-driven state is a hydration mismatch waiting to happen, and the framework's error page says so only after it has happened.

## Entry 16: a Bee voice note ends after a sentence, so the one certain stream cannot carry a day on its own (2026-10-15)

- Task: build the wearer's own baseline from voice notes, two minutes a day (entry 14).
- Steps: recorded notes in the Bee app on 2026-10-13 and 2026-10-15 while speaking for about a minute each time; read them back with `bee journals list --json`; compared with `bee conversations list` for the same minutes.
- Expected: a note the length of the speech, or a documented maximum.
- Actual: five notes of 1, 6, 9, 12 and 15 words, each marked READY three seconds after it was created, two of them ten seconds apart. In the same minutes the band captured the same speech as conversations of 101 and 151 words. The note records a sentence and stops; nothing in the app or the docs says so, and `text` is the whole record.
- Severity: medium. The one stream whose speaker is certain holds about ten seconds a day, which is below any floor a language measure can use.
- Workaround: a check-in. The note proves who started it; the band's session that begins within a minute before or three minutes after the note and opens with the note's words is the wearer talking to the band on purpose, and `bellwether-ingest pull --checkins` keeps the next ten minutes of it. On 2026-10-15 that turned 16 words of notes into 265 words of check-in, and the day counted. The rule is pinned by five tests, including the session that started fourteen minutes before a note (a meeting, not a check-in) and a session in the same minute with different words.
- Suggestion: let a note run until the wearer stops it, or document the limit; and the `is_wearer` flag of entry 12 would make all of this unnecessary.

## Entry 17: the wearer's natural opener is a better anchor than the note, and nothing in Bee marks either (2026-10-17)

- Task: count the wearer's two-minute check-ins on 2026-10-16 and 2026-10-17 toward their baseline.
- Steps: the wearer talked to the band alone on both days, opening with "today's vlog, it's October 16th" and "vlog for October 17th", and did not make a voice note first; pulled check-ins with the note-anchor rule from entry 16.
- Expected: the sessions to count, since they are plainly declared.
- Actual: zero, because the rule needed a voice note within three minutes of the session, and there was none. Three sessions of 98, 126 and 152 words, each the wearer alone, each opening by saying what it was, dropped on the floor.
- Severity: medium, and ours as much as Bee's. The wearer did the natural thing; the rule asked for a ceremony.
- Workaround: a second anchor. A session whose first six words declare it ("Bellwether check-in", "voice note for", "vlog for", "today's vlog", "journal", "note to self") is a check-in, with the same ten-minute window; the note anchor stays for people who prefer it. Pinned by a test in which "as I was saying in my vlog yesterday" at word ten does not count. On this account it turned 0 counted days into the two expected.
- Suggestion: a way for the wearer to mark a session as theirs on the band or in the app, carried through to the developer data. Until the `is_wearer` flag of entry 12 exists, a declared session is the honest substitute, and it is the wearer's own voice saying so.

## Entry 18: an MCP session remembered in memory breaks the moment Lambda scales (2026-10-18, ours, and a spec-docs gap)

- Task: record the Strands agent asking the deployed MCP server how a month went, for the demo video.
- Steps: ran `apps/agent/speech_check_in.py` against the function URL; it made four tool calls in one session.
- Expected: four answers, as on every earlier run.
- Actual: the fourth call failed with "Session terminated". Sessions were a set in one instance's memory; the agent's calls had made Lambda start a second instance, which had never issued the id and answered 404. Every earlier run had happened to stay on one warm instance, and every test runs one process, so nothing had ever seen it. The same pattern was in all four servers built for this hackathon, so Alexa+ or any judge's MCP client could hit it whenever traffic spread.
- Severity: high for the Alexa+ surface, and invisible until load.
- Workaround: a session id is now a nonce and an HMAC of it, keyed by the function's own name and version, so every instance verifies it with no table and no state (the pattern the Volley server already used). A test opens a session on one app instance and uses it on another. Live, 24 sessions opened at once on each of the four servers were all fully usable afterwards.
- Suggestion: the transport section should say plainly that a session id must be verifiable by any replica, and show the stateless way to do it. Every serverless MCP server meets this, and the natural reading of "the server assigns a session id" is a set in memory.

## Entry 19: The Bee hears the host too, and nothing marks a session or a speaker as "not the wearer" (2026-10-18)
- Task: let a voice assistant host the check-in (the judges' brief asks for Bee alongside Echo): the assistant speaks three standard questions through a speaker, the wearer answers, the band records.
- Steps: ran `apps/agent/check_in_host.py --dry-run` against the service, then read the shape of a real session (`bee conversations get <id> --json`) to see how a spoken prompt and an answer would arrive.
- Expected: some way to tell the device or the data that the next minutes contain a second voice that is not the wearer, or at least a speaker label that would separate them.
- Actual: every utterance still carries `speaker: "Unknown"` (entries 1, 12, 17), there is no session tag, no "exclude this text" hint, and a sixteen-word question spoken by a synthetic voice would be transcribed into the same session as the wearer's answer and counted as the wearer's speech, moving the very numbers being watched. Transcription also lands minutes after the session ends, with no event or field that says a conversation is finished, so a host has to poll `conversations list` until the utterance count stops growing.
- Severity: medium for this product, high for any "two devices in one room" Bee project, which is the shape the brief recommends.
- Workaround: the host's possible sentences are published. The three prompts are standard elicitation tasks fixed in `speech_vitals.elicitation` and rotated by date, so the host on the wearer's computer and the service derive the same script without exchanging it; the ingest removes any utterance that is one of those lines, including a line the device cut in two and a date heard as digits; and the host appends every line it actually spoke to `.bellwether-host.json` so an unscripted sentence is removed too. Tests pin the rule, one of them a whole hosted session with the wearer's three answers surviving and nothing else. Measured on the builder's real account the same day: the first version of the rule would have deleted 98 of 6,645 real utterances (1.5%), mostly "thank you" and "yes" because they occur inside a host line; the rule now needs a whole line, a run of four words, or a long near-match, and deletes none of them (0 of 56,444 words). A live run of the host through a laptop speaker the same evening produced no Bee session in twenty minutes. That is not evidence about synthetic speech: the account received nothing at all from the band between 19:42 and past midnight local, so the band was not uploading. Nothing in the CLI says a band has stopped syncing; `bee ping` answers and `conversations list` simply stops growing. The host now says when no session began instead of only timing out. The "finished" problem is handled by watching `utterances_count` across two polls a minute apart.
- Suggestion: a per-session tag a developer can set ("hosted", "check-in", or free text) that comes back on `conversations get`; a `state` value that distinguishes "recording" from "transcribed"; and the `is_wearer` flag of entry 12, which would have made all of this one line.
<!-- Add new entries above this line as they happen. -->
