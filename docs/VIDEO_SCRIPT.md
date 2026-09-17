# Bellwether demo video: shot list

Target length 2:50. Hard limit 3:00; judges are not required to watch past it, so the strongest material is in the first 45 seconds. Everything shown is the live deployment, so nothing in the video can differ from what a judge clicks.

**This video cannot be finished before the Bee device arrives.** The Bee track requires that "your video and code need to show your project actually using live Bee data to do something for a user, mentioning Bee isn't enough." Shots 4 and 5 are the live-data shots, and they need the wristband. Everything else can be recorded now and cut together later.

Rules this video must satisfy, and where it does:

- Bee: live Bee data doing something for a person. Shots 4 and 5.
- Alexa+: "show your MCP server (spec 2025-11-25+, Streamable HTTP) in action." Shots 7 and 8.
- No third-party trademarks, music, or footage. Narration only, no background track.
- English, public on YouTube.
- Nothing that could be read as a medical claim. The disclaimer is spoken aloud, not only shown.

## Before you press record

```
# 1. Terminal, large font (18pt+), dark theme, 1280x720.
export API=https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws
export MCP=$API/mcp

# 2. Warm every endpoint. A Bedrock cold start on camera looks like a bug.
curl -s $API/v1/profiles/alex-drift/summary | python -m json.tool
curl -s $API/v1/profiles/alex-drift/weekly-note | python -m json.tool
curl -s $API/api/resilience | python -m json.tool

# 3. Warm the agent, then run it again on camera.
python apps/agent/speech_check_in.py --url $MCP --profile alex-drift

# 4. With the device paired and worn for at least ten days:
bee status                       # expect: logged in
bellwether-ingest pull --owner <your speaker label> --out days.json
curl -X POST $API/v1/profiles/me/days -H "content-type: application/json" -d @days.json
curl -s $API/v1/profiles/me/summary | python -m json.tool
```

Browser: https://d1xfuyog8wiuvf.cloudfront.net at 125 percent zoom, light theme to start. Open `/app` and `/report` in separate tabs. Close everything else, hide the bookmarks bar.

Record at 1080p, 30fps. Pause half a second before each click.

## Shot list

### Shot 1: the hook (0:00 to 0:18)

Screen: the landing page hero.

Say: "Your watch knows when your heart skips a beat. Nothing knows when your brain does. Speech is the only thing the brain produces continuously that anyone can observe, and when something changes, speech is usually where it shows first."

### Shot 2: the gap (0:18 to 0:40)

Screen: scroll slowly to the four statistics. Let the 3.5 years card rest for two seconds.

Say: "Across all dementias, the average time from first symptoms to a diagnosis is three and a half years. The newest treatments are approved only for the earliest stage, which is exactly what that delay skips past. And when the appointment finally happens, patients forget up to eighty percent of what they are told."

### Shot 3: what it is, and is not (0:40 to 0:55)

Screen: still on the landing page, over the how-it-works steps.

Say: "Bellwether is not a diagnosis and not a medical device. It learns how one person normally speaks, from the wristband they already wear, and shows them when that changes. It compares you only with your own past, never with anyone else."

### Shot 4: real Bee data, on your wrist (0:55 to 1:20) **needs the device**

Screen: show the Bee band on your wrist for two seconds, then the terminal.

Run, on camera:

```
bee status
bellwether-ingest pull --owner <your speaker label> --out days.json
```

Then show `days.json` on screen and scroll it.

Say: "This is my own Bee wristband, and this is my own speech from the last two weeks. The important part is what is in this file. Nine numbers a day, and no words. The transcript was reduced on my machine and discarded. Nothing that leaves here could reconstruct a sentence."

### Shot 5: my own baseline (1:20 to 1:40) **needs the device**

Screen: post the file, then open `/app` pointed at your own profile.

Say: "Fourteen days. Seven of them were spent learning what normal sounds like for me, and the rest are compared with it. Stable, which is what I expected, and the system says so plainly rather than looking for something to report."

### Shot 6: what a change looks like (1:40 to 2:05)

Screen: switch to the simulated persona on `/app`. The simulated badge must be visible.

Say: "This is a simulated person, labelled throughout, so you can see eight weeks including a gradual change from week six."

Screen: scroll to `What else could explain this`. Let it be readable.

Say: "And this is the panel that matters most. Before the chart, before anything frightening, the ordinary explanations: a bad week of sleep, a cold, a new medication, talking to fewer people. Those explain far more changes than anything worrying does, so they get the same space as the result."

Screen: scroll to the trend chart and the contributors.

Say: "When it does flag something, it says which measures moved, in which direction, and since when."

### Shot 7: the MCP server (2:05 to 2:20)

Screen: terminal.

```
curl -s -D- -o /dev/null -X POST $MCP -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}' \
  | grep -i mcp-session-id
```

Say: "All of this is also a Model Context Protocol server, spec 2025-11-25 over Streamable HTTP. Seven tools, and none of them can return a transcript, because none exists."

### Shot 8: asking out loud (2:20 to 2:40)

Screen: run the agent live.

```
python apps/agent/speech_check_in.py --url $MCP --profile alex-drift
```

Say: "A Strands agent on Amazon Bedrock, with no database access of its own. It reads the status, the trend and the report through those tools, says the data is simulated before anything else, and suggests only what a person can act on themselves. It is forbidden from naming a condition or predicting anything."

### Shot 9: the page that leaves the room (2:40 to 2:55)

Screen: `/report`, then click Print so the print preview shows.

Say: "And this is the point of the whole thing. One page, for a twelve-minute appointment: what changed, when, what moved, and in full, the statement that this is not a diagnosis. Open source, MIT, live at the link."

Hold on the URL for two seconds. Cut.

## Do not say

- Any sentence in which Bellwether detects, screens for, predicts, or indicates a condition.
- "Early detection." Say "a record of change over time."
- "Accurate" or "%" about Bellwether itself. The 85 to 89.6 percent figure belongs to the ADReSS literature and must be attributed to it out loud if used at all.
- Any number that is not in `docs/EVIDENCE.md`.
- Anything implying the person on screen in Shot 6 is real.

## If the device does not arrive in time

Do not fake it, and do not imply it. Cut shots 4 and 5, open Shot 1 with the simulated label stated aloud, and say plainly in the closing shot: "The Bee device is on order; everything shown runs on the production pipeline against a labelled simulated person." A judge will respect that far more than footage that quietly implies data we do not have, and the Bee track scoring will reflect the gap either way.

## After recording

- Export 1080p, H.264. No music.
- YouTube: title "Bellwether: speech is a vital sign", visibility Public, not Unlisted. Description: one paragraph, the site URL, the repo URL, the MCP URL, and the non-diagnostic disclaimer verbatim.
- Paste the link into `docs/SUBMISSION.md` under Live, and into the Devpost form.
