# Feature requests

What we would want built, why it matters, and how urgent it is. Each one comes from something we actually hit while building Bellwether, and each is cross-referenced to the friction log entry that produced it.

Urgency uses the hackathon's scale: **critical**, **important**, **nice-to-have**.

---

## Bee

### 1. An `is_user` flag on every utterance

**Critical.**

Bee labels speakers generically (`Speaker 1`, `Speaker 2`) with no documented way to know which one is the person wearing the device. For any analysis *of the wearer* rather than of the room, that is the whole ballgame: it is the difference between measuring a person and measuring their kitchen.

We work around it by assuming the most frequent speaker across the corpus is the wearer, which is a reasonable guess and still a guess. One boolean, resolved by the app from the voice training it already performs during onboarding, removes an entire class of silent error from every project built on Bee data.

Friction log entry 2.

### 2. One verbatim JSON example per data command

**Important.**

The CLI reference documents the field names (`text`, `speaker`, `start_time`, `end_time`, `created_at`, `next_cursor`) but shows no complete response for any command. So the nesting has to be guessed: is `utterances` top-level or under `transcriptions[]`? Is `speaker` a string or an object? Our normaliser accepts the documented key first and sensible alternates after, with a test per guessed shape, which is a tolerant parser written in place of a five-line one.

One real payload per command, and ideally a shared JSON Schema for `Conversation` and `Utterance`, would let every integrator write the correct parser the first time. This is the cheapest high-value change on this list.

Friction log entry 1.

### 3. A `--json` mode for `bee sync`

**Nice-to-have.**

The offline export writes markdown with `- Speaker 1: text` lines and no per-utterance timestamp, so anything about pacing, turn-taking, or time of day is closed to that path. Day-level work survives, which is why Bellwether can use it, but the JSON commands already return the times; emitting the same records alongside the markdown would make the offline path a first-class one.

Friction log entry 3.

### 4. Android parity, or a stated timeline

**Important.**

The Android app is early access, "includes only some core features", and is "not actively being supported right now". Combined with United States-only shipping, an Android developer outside the US cannot enter the Bee track at all. For a hackathon inviting newcomers to the platform, the constraint deserves stating on the track page rather than in an FAQ, and a timeline would let people plan.

Friction log entry 5.

---

## Model Context Protocol

### 5. Say in the transport section that a real client sends `DELETE` with a JSON content-type and an empty body

**Important.**

The spec is precise about the things that are easy to get wrong, which is why our conformance tests came almost directly from reading it. This one is not in the text, and it cost two of our three projects a 500 error each. A naive body parser treats an empty body with `Content-Type: application/json` as a parse failure; a test suite built on an injection helper never produces that shape, so it passes while real clients fail.

One sentence in the session-termination section would have prevented both bugs. We now handle it by never reading a body on `DELETE`, and we would rather the spec said so than that every implementer discovered it.

---

### 5b. Ship a transport conformance suite, or at least a status-code table

**Important, and it is the highest-leverage thing the project could publish.**

Every server author writes the same tests, guesses at the same ambiguities, and learns which guesses were wrong only when a real client arrives.

Two asks, in order of value.

First, publish the HTTP status mapping. The transport section is precise about sessions and about `Accept`, and silent about what status accompanies a JSON-RPC error. We reasoned it out: a request needing a session and carrying none is 400, an unknown or expired session is 404 so the client starts a new one rather than fixing its request, an unparseable body is -32700 at 400 rather than a 500, and a tool that rejects its arguments is a 200 carrying a JSON-RPC error because the transport succeeded. All defensible, none written down, so implementations will differ and clients will paper over it.

Second, ship the suite. A runner any author can point at a URL would make the specification executable. We built a small one (`scripts/mcp-conform.mjs`, nineteen graded checks, no dependencies) and ran it against three deployed servers on two frameworks. This one passed all nineteen; the two Fastify servers each failed the parse-error rule while their own test suites were green. Grading matters: it separates MUST from SHOULD and accepts either legal answer where the spec permits two, because a conformance tool that grades its own preferences as violations gets ignored.

Friction log entry 9.

## AWS

### 6. Warn when a Lambda function URL's CORS configuration collides with the handler's own

**Critical.**

A function URL configured with CORS reflects the origin. A FastAPI, Express or Flask app configured with CORS middleware, which is what every tutorial for those frameworks tells you to add, sets it too. The response then carries two `Access-Control-Allow-Origin` values and every browser rejects it outright.

What makes this expensive is that nothing on the command line can see it. `curl` does not enforce CORS, so every manual check returns 200 with plausible headers; `TestClient` does not enforce it either, so the test suite passes. The only signal was Lighthouse's console audit on the deployed site, which is not where anyone looks for a CORS bug. For a live demo, this is the difference between a working dashboard and an empty one.

Either strip a conflicting header emitted by the handler, log a warning when both are configured, or at minimum add a line to the function URL CORS documentation: *do not also set CORS headers in your handler*.

Friction log entry 6.

### 7. A first-class Docker-free bundling path for Python Lambda functions

**Important.**

CDK's Python Lambda construct wants Docker for bundling. For a service that is pure Python plus a few compiled wheels, that is a heavy requirement, and on Windows it is a real obstacle. We build the asset by resolving manylinux x86_64 wheels for CPython 3.12 with pip's `--platform` and `--only-binary` flags, which works reliably and produces a 21.8 MB asset, but we had to work it out rather than follow it.

Documenting that pattern, or offering it as a construct option, would help every Python team that does not want Docker in their build.

### 8. Make Bedrock model availability discoverable before invocation

**Important.**

Current-generation Claude models return an access error on this account tier even after marketplace agreements are accepted, and the availability APIs do not surface that gate, so the only way to learn which models an account can actually invoke is to call each one and see. Our three-model ladder exists partly because of this: it degrades rather than failing, but it is degrading around an unknown that should be knowable.

An endpoint that answers "which models can this account invoke right now" would turn a runtime discovery into a build-time one.

This one is inherited from a sibling project in this hackathon (Nightlight, friction log entry 5) and applies identically here.

---

## What we are not asking for

Worth stating, because a list of requests reads better with a boundary.

We are not asking Bee to expose raw audio. Bellwether is built on the principle that words are reduced to numbers where the transcript lives and never travel, and audio access would invite a design that violates that. If it existed we would use it only for pause and articulation timing, behind the same local-first boundary, and we would rather the platform stayed conservative here than opened it by default.
