# Demo video script

Under three minutes, public, English. Judges are not required to watch
past 3:00, so the strongest material is first.

This file is written by `python video/beats.py --script` from the same
data the recorders and the assembler read. Edit `video/beats.py`, not
this file.

---

## Shot list

**0:00, hook, the website, in a real browser**

The front page: the claim, and a simulated person's own range with the days that left it.

> Your watch tracks your heart. Nothing tracks the way you speak. More pauses, simpler sentences, words that are harder to find. They can be the first sign that something is changing.

**0:13, gap, the website, in a real browser**

The three and a half years card, then what people say they want: 79 percent.

> Most of us would never notice. And if we did, how would we explain it to a doctor months later? On average, dementia takes three and a half years to diagnose, and nearly four in five of us say we would want to know early.

**0:32, what, the website, in a real browser**

How it works: wear, measure, learn, show.

> Bellwether uses the Bee on your wrist to learn how you normally speak. Everyone speaks differently, so it compares you only with your own past. It keeps nine numbers a day, never your words, and it is not a diagnosis.

**0:48, term-host, a terminal, a real run rendered**

A terminal: the assistant speaking tonight's three questions while the Bee on the wrist listens; the day read from the Bee and counted; the note read back.

> Every evening, an assistant asks me three short questions out loud. My Bee records my answers. Bellwether removes the assistant's own voice, turns my speech into those nine numbers, and tells me where I stand.

**1:02, checkins, the website, in a real browser**

The dashboard on the builder's own check-ins: the real-data badge, the first week filling.

> This is my own Bee data, live. Seven days teach it what normal sounds like for me. Three days counted. Four more and it starts comparing.

**1:13, change, the website, in a real browser**

The switcher to the simulated person, labelled; the eight-week chart leaving its band; what moved and since when; then what else could explain it.

> Imagine your speech changing so gradually that you don't notice. This simulated example shows how Bellwether makes that change visible. Bellwether shows when it started, which measures moved, and how far from that person's own normal. Then it lists the everyday explanations first. Poor sleep, illness, a new medication. It never names a condition.

**1:39, proof, the website, in a real browser**

The same page, with what the software was checked against on screen.

> We tested Bellwether on speech we didn't write: three hundred forty-nine Supreme Court arguments with no alerts, and six hundred fifty-two presidential press conferences with fewer than three percent flagged. These tests measure software behaviour, not medical accuracy.

**1:55, mcp, the website, in a real browser**

A session held against the MCP server from the page: protocol agreed, nine tools listed, the answer returned.

> It also works with AI assistants like Alexa+. They can ask how you have been sounding, but they can never retrieve your conversations, because none are stored.

**2:07, term-agent, a terminal, a real run rendered**

A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.

> Here a Strands agent on Amazon Bedrock asks for a monthly summary, and says the data is simulated before anything else.

**2:15, report, the website, in a real browser**

The doctor report: the timeline, then the questions to bring, then the links.

> And if something changes, Bellwether gives you a simple timeline to bring to your doctor. What changed, when it started, and what questions to ask. No diagnosis, just a clearer conversation. Open source, and working today. Bellwether. Your own normal, in your own numbers.

Estimated 2:34 of a 3:00 ceiling. The real narration decides the
final cut.

## The terminal beats

Two beats show real commands: `bellwether-ingest mine` against the
builder's own Bee, and the Strands agent against the deployed MCP
server. `record_term.py capture` runs them for real and keeps their
output and how long they took; `render` types them at a human pace in
a terminal frame the same 4K recorder captures, prints the saved
output, and says how long each run really took. The frame says it is
a rendering of a real run.

## What not to say

Any sentence in which Bellwether detects, screens for, predicts or
indicates a condition. "Early detection." "Accurate" or a percentage
about Bellwether itself. Any number not in docs/EVIDENCE.md. Anything
implying the simulated person is real, or that the conversation stream
is the builder's own speech.
