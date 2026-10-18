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

> Your watch knows when your heart skips a beat. But what about changes in the way you speak? More pauses, simpler sentences, words that suddenly become harder to find. Small changes that are easy to overlook.

**0:15, gap, the website, in a real browser**

The four figures under the problem; the three and a half years card first.

> Across all dementias, the average time from first symptoms to a diagnosis is three and a half years. That's years of uncertainty for people and their families.

**0:26, what, the website, in a real browser**

How it works: wear, measure, learn, show.

> Bellwether is not a diagnosis and not a medical device. It learns how one person normally speaks, and tells them when that changes. Only against your own past, never against anyone else.

**0:39, term-mine, a terminal, a real run rendered**

A terminal: bellwether-ingest mine against the builder's own Bee, the days it read, the days that count, the page to open.

> This runs on my own Bee. I talk to it for two minutes each day. Bellwether turns that speech into nine measurements and discards the words. Anyone can do the same with their own Bee, or with the meeting transcripts they already have.

**0:57, checkins, the website, in a real browser**

The dashboard on the builder's own check-ins: the real-data badge, the first week filling.

> Here's the result, from my real data. Seven days teach it what normal sounds like for me; every day after is compared with them. Two days in. Five more and it compares. Until then it says so, instead of hunting for something to report.

**1:15, room, the website, in a real browser**

The switcher to the band's conversations, the note under the badge saying what that stream is.

> The band also hears everyone around me, and Bee does not yet say who was talking. So that stream is kept separate and labelled for what it is: the room, not just me.

**1:29, change, the website, in a real browser**

The switcher to the simulated person, labelled; what moved and since when; then what else could explain it.

> Now imagine someone's speech gradually changes over several weeks. This is a simulated example. Bellwether shows when the change started, which measurements moved, and how far they've shifted from that person's usual range. Poor sleep, illness or medication could also explain it. That's why it shows the possible explanations, not a diagnosis.

**1:51, mcp, the website, in a real browser**

A session held against the MCP server from the page, every request answered by the deployed server.

> All of this is also a Model Context Protocol server over Streamable HTTP, the way Alexa+ talks to tools. Seven tools, and none can return a transcript, because none exists.

**2:04, term-agent, a terminal, a real run rendered**

A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.

> A Strands agent on Amazon Bedrock asks how things have been going. It says the data is simulated before anything else, and it may never name a condition.

**2:15, report, the website, in a real browser**

The doctor report, then the links.

> Imagine noticing something different, but not knowing how to explain it to your doctor. Bellwether gives you a simple timeline of what changed and when. Not a diagnosis, but a clearer starting point for that conversation. Open source, and built around privacy. Bellwether. Your own normal, in your own numbers.

Estimated 2:36 of a 3:00 ceiling. The real narration decides the
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
