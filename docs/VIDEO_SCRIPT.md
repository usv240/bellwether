# Demo video script

Under three minutes, public, English. Judges are not required to watch
past 3:00, so the strongest material is first.

This file is written by `python video/beats.py --script` from the same
data the recorders and the assembler read. Edit `video/beats.py`, not
this file.

---

## Shot list

**0:00, hook, the website, in a real browser**

Three tiles over the front page: Bee captures speech, Bellwether finds changes, a doctor report supports the conversation; then the page under them.

> Your Bee already captures your conversations. Bellwether looks for changes in how you speak over time, and turns them into something useful for your doctor. Nine numbers a day, never your words, and not a diagnosis.

**0:16, gap, the website, in a real browser**

The three and a half years card, then what people say they want: 79 percent.

> Most of us would never notice, and could not describe it to a doctor months later. Dementia takes three and a half years to diagnose on average, and nearly four in five of us would want to know early.

**0:32, term-host, a terminal, a real run rendered**

A terminal: the assistant speaking tonight's three questions while the Bee on the wrist listens; the day read from the Bee and counted; the note read back. Tonight's real run.

> Every evening, an assistant asks me three short questions out loud. My Bee records my answers. On my own computer, Bellwether removes the assistant's voice, keeps nine numbers, and throws the words away.

**0:46, checkins, the website, in a real browser**

The dashboard on the builder's own check-ins: the real-data badge, seven of seven days, then the one command that gives anyone their own profile.

> This is my own Bee data, live. Seven days counted, and every new day is compared with them. Anyone with a Bee can do the same, with one command and a key of their own.

**1:00, compare, the website, in a real browser**

Two simulated people side by side, labelled: the stable one with nothing flagged, the changing one with a persistent change since September; then the changing person's chart with the late days ringed; then what else could explain it.

> Two simulated people, labelled as such. One speaks the same way week after week: nothing is flagged. The other changes so gradually they would never notice, and Bellwether shows when it started, which measures moved, and how far. It offers everyday explanations first, like poor sleep, illness or medication. It never names a condition.

**1:24, report, the website, in a real browser**

The doctor report: the timeline, then the questions to bring.

> And when something changes, Bellwether gives you a simple timeline to bring to your doctor: what changed, when it started, and which questions to ask.

**1:35, mcp, the website, in a real browser**

A session held against the MCP server from the page: protocol agreed, the tools listed, the answer returned.

> Bellwether also connects to assistants through an MCP server, on the standard Alexa+ uses. An assistant can ask about your trends, never your conversations, which were never stored.

**1:47, term-agent, a terminal, a real run rendered**

A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.

> Here a Strands agent on Amazon Bedrock asks for a month's summary, and says the data is simulated before anything else.

**1:56, aws, the website, in a real browser**

One line of four boxes: Bee, local analysis on the wearer's computer, AWS (Lambda, DynamoDB, Bedrock, AgentCore), the dashboard and report.

> Speech is analysed on my own computer. AWS Lambda and Amazon DynamoDB hold the nine numbers a day, and Claude on Amazon Bedrock phrases the weekly note from those numbers alone.

**2:09, proof, the website, in a real browser**

Three checked facts beside the chart: real Bee data from the wearer's own band; words that never leave the computer; three hundred tests and the Supreme Court run with zero false alarms.

> Checked, not claimed: real Bee data from my own band; words that never leave my computer; and three hundred automated tests, with three hundred forty-nine Supreme Court sessions, zero false alarms. Software behaviour, not medical accuracy.

**2:24, close, the website, in a real browser**

The changing person's chart, then the doctor report, then the final card with the product name and the last line.

> Imagine noticing small changes in how someone you love speaks, with no way to tell whether it is a pattern. For someone noticing changes in themselves or a loved one, Bellwether offers a clearer record to bring into a conversation with a clinician, instead of memory alone. It does not diagnose. It helps you notice a change, understand it, and start a better conversation with a clinician. Because sometimes the first step is simply noticing.

Estimated 2:55 of a 3:00 ceiling. The real narration decides the
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
