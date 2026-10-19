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

The figures under the problem; the three and a half years card first, then the case in three verified steps.

> Across all dementias, the average time from first symptoms to a diagnosis is three and a half years. And in Medicare, nine in ten early cases are never diagnosed at all.

**0:28, what, the website, in a real browser**

How it works: wear, measure, learn, show.

> Bellwether is not a diagnosis and not a medical device. Everyone speaks differently. So it learns what's normal for you, rather than comparing you with anyone else, and tells you when that changes.

**0:41, term-mine, a terminal, a real run rendered**

A terminal: bellwether-ingest mine against the builder's own Bee, the days it read, the days that count, the page to open.

> This runs on my own Bee. I talk to it for two minutes each day. Bellwether turns that speech into nine measurements and discards the words. Anyone can do the same with their own Bee, or with the meeting transcripts they already have.

**0:59, term-host, a terminal, a real run rendered**

A terminal: the Check-in Host speaking tonight's three questions through the speaker while the Bee on the wrist listens; the day counted; the coaching note read back.

> Or the assistant hosts it, with the same MCP tools Alexa+ gets. It asks three questions out loud, my Bee records the answers, and the host's words are removed before anything is measured. Then it tells me where I stand.

**1:16, checkins, the website, in a real browser**

The dashboard on the builder's own check-ins: the real-data badge, the first week filling.

> Here's the result, from my real data. Seven days teach it what normal sounds like for me; every day after is compared with them. Two days in. Five more and it compares. Until then it says so, instead of hunting for something to report.

**1:34, replay, the website, in a real browser**

The simulated first week, labelled: the slider stepping through the evenings, the short third day marked, day nine turning green with the first comparison, and the note the assistant reads aloud.

> Here is the whole first week, simulated. A short day doesn't count. On day nine the first comparison arrives, and the assistant reads the note aloud.

**1:45, change, the website, in a real browser**

The switcher to the simulated person, labelled; the eight-week chart leaving its band; what moved and since when; then what else could explain it.

> Now imagine someone's speech gradually changes over several weeks. This is a simulated example. Bellwether shows when the change started, which measurements moved, and how far they've shifted from that person's usual range. Poor sleep, illness or medication could also explain it. That's why it shows the possible explanations, not a diagnosis.

**2:13, mcp, the website, in a real browser**

A session held against the MCP server from the page, every request answered by the deployed server.

> Bellwether also connects to AI assistants through nine MCP tools, using the same protocol Alexa+ supports. And because it never stores conversations, those tools can't retrieve them.

**2:24, term-agent, a terminal, a real run rendered**

A terminal: the Strands agent on Amazon Bedrock asking the deployed server how the simulated person's month went.

> A Strands agent on Amazon Bedrock asks how things have been going. It says the data is simulated before anything else, and it may never name a condition.

**2:36, report, the website, in a real browser**

The doctor report, then the links.

> Imagine noticing something different, but not knowing how to explain it to your doctor. Bellwether gives you a simple timeline of what changed and when, written for the yearly wellness visit Medicare already offers. Not a diagnosis, a clearer starting point. Open source, and built around privacy. Bellwether. Your own normal, in your own numbers.

Estimated 2:59 of a 3:00 ceiling. The real narration decides the
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
