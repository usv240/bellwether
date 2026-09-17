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

<!-- Add new entries above this line as they happen. -->
