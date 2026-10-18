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

> Your watch knows when your heart skips a beat. Nothing knows when your brain does. When something changes there, speech usually shows it first: more pauses, simpler sentences, words that will not come.

**0:14, gap, the website, in a real browser**

The four figures under the problem; the three and a half years card first.

> Across all dementias, the average wait from first symptoms to a diagnosis is three and a half years. The newest treatments only work at the earliest stage. That wait skips straight past it.

**0:27, what, the website, in a real browser**

How it works: wear, measure, learn, show.

> Bellwether is not a diagnosis and not a medical device. It learns how one person normally speaks, and tells them when that changes. Only against your own past, never against anyone else.

**0:41, term-mine, a terminal, a real run rendered**

A terminal: bellwether-ingest mine against the builder's own Bee, the days it read, the days that count, the page to open.

> This is my Bee. Each day I check in: two minutes of talking to the band on my own. One command turns each day into nine numbers on my computer and throws the words away. Anyone can do the same with their own Bee, and a free key keeps the profile theirs.

**1:02, checkins, the website, in a real browser**

The dashboard on the builder's own check-ins: the real-data badge, the first week filling.

> My own baseline, from real Bee data. Seven days teach it what normal sounds like for me; every day after is compared with them. Two days in. Five more and it compares. Until then it says so, instead of hunting for something to report.

**1:20, room, the website, in a real browser**

The switcher to the band's conversations, the note under the badge saying what that stream is.

> The band also hears everyone around me, and Bee does not yet say who was talking. So that stream is kept separate and labelled for what it is: three weeks of everyday conversation, also stable.

**1:35, change, the website, in a real browser**

The switcher to the simulated person, labelled; then what else could explain a change.

> To show what change looks like: a simulated person, labelled on every screen. Before the chart, the ordinary explanations: a bad week of sleep, a cold, a new medication. They explain far more changes than anything worrying, so they get the same space as the result.

**1:54, moved, the website, in a real browser**

The eight-week chart, then the measures that moved.

> When it does flag something, it says which measures moved, in which direction, and since when.

**2:01, mcp, the website, in a real browser**

A session held against the MCP server from the page, every request answered by the deployed server.

> All of this is also a Model Context Protocol server over Streamable HTTP, the way Alexa+ talks to tools. Seven tools, and none can return a transcript, because none exists.

**2:14, term-agent, a terminal, a real run rendered**

A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.

> A Strands agent on Amazon Bedrock asks how the week went. It says the data is simulated before anything else, and it may never name a condition.

**2:25, report, the website, in a real browser**

The doctor report, then the links.

> This is the point. One page for a twelve-minute appointment: what changed, when, what moved, and in full, that this is not a diagnosis. Open source, live at the link. Bellwether. Your own normal, in your own numbers.

Estimated 2:41 of a 3:00 ceiling. The real narration decides the
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
