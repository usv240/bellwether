# Design

Why Bellwether looks and reads the way it does. Every principle here is either from the shared design system used across all three projects in this hackathon, or from the risk-communication literature, which matters more for this product than for the other two: Bellwether shows health-adjacent numbers to people who may be frightened by them.

## The governing distinction

> "Crucially, we need to be clear about whether we are seeking to persuade, or fulfilling a duty to inform."
>
> Spiegelhalter D. Risk and Uncertainty Communication. *Annual Review of Statistics and Its Application*. 2017;4:31-60. [DOI](https://www.annualreviews.org/content/journals/10.1146/annurev-statistics-010814-020148)

Bellwether informs. That single choice rules out a large amount of ordinary product design, and the exclusions are deliberate:

- **No streaks used as pressure.** A stable streak is displayed because it is information, never celebrated, and never framed as something to protect.
- **No nudges, badges, or gamification.** Nothing encourages you to talk more so the numbers look better. That would corrupt the measurement and the person.
- **No urgency language.** No "act now", no red banners, no exclamation marks. The most serious tier is called `Discuss`, which is a verb describing what to do, not an alarm.
- **No engagement optimisation.** There is nothing to come back for daily. A weekly note and a report are the whole surface.

## The seven recommendations, and what each one changed

Spiegelhalter's review closes with concrete recommendations. These are the ones that shaped the interface, quoted and then applied.

**"Allow for different levels of interest, knowledge, and numeracy, for example, a top gist level, then numerical information, and then evidence and uncertainty."**

This is the exact structure of every screen. The gist is a word: `Stable`, `Watch`, `Discuss`. Under it, sentences with dates and feature names. Under that, the numbers. Behind a 22-entry info-button dictionary, the technical layer and the citation. A visitor can stop at any depth and have something true and complete.

**"Have the humility to admit uncertainty."**

This produced the panel that matters most, `What else could explain this`, placed above the chart on the dashboard rather than in a footnote. It lists the ordinary causes (poor sleep, illness, new medication, a stressful week, talking to fewer people) at the same visual weight as the result, followed by an explicit list of what the tier does **not** mean. A worried person reaches the mundane explanations before they reach the frightening one, because that is the honest ordering.

**"Use plain language and limit information to only what is necessary."**

Nine features exist; the dashboard names at most three as contributors and the rest stay in the report. Feature names are translated everywhere: `mattr` is shown as "vocabulary variety", `pronoun_noun_ratio` as "pronoun reliance". The raw names appear only in the developer surfaces.

**"Be explicit about the time interval."**

Every tier carries a date: "Discuss since September 3." Every report carries its range in the heading. No figure is shown without the window it covers.

**"Be aware that comparators can create an emotional response."**

Bellwether has no comparator at all, and this is the deepest design decision in the product. It never compares you with a population, an age band, or a norm, so there is no "you are below average" to feel. The only comparator is your own past, which is stated in the interface every time it matters.

**"Illuminate graphics with words and numbers."** and **"Helpful narrative labels are important."**

The trend chart is never alone. It carries a zero reference line labelled as your baseline, a threshold line labelled `sharp`, a legend naming every state in words, and a `Recent days` table beneath it with the same values as text. The report restates every notable change in a sentence with a date.

**"Consider a good summary table as a visualization."** and **"Use multiple formats, because no single representation suits all members of an audience."**

The same eight weeks appear three ways: as a line chart, as a proportional tier bar in the report, and as a table. Someone who cannot read one can read another.

## Colour is never the only carrier of meaning

Every tier is a word as well as a colour, in the badge, the chart tooltip, the legend and the report's tier bar. The four tier colours are chosen to pass AA contrast against both light and dark backgrounds, and the chart palette never exceeds four series. A person with any form of colour vision deficiency loses nothing.

Quiet days are drawn as hollow circles on the axis and break the line, rather than being plotted as zero. A gap in the data is shown as a gap, which is both more honest and less alarming than a value that dropped to the floor.

## Progressive disclosure, and never mixing audiences

From the shared design system: the default reading path is entirely non-technical, and technical depth appears in exactly three sanctioned places, which are the "In technical terms" field of an info popover, the developer section, and the documentation. No paragraph addresses both audiences at once. This is why the landing page can be read start to finish by someone with no technical background and still be useful to a judge reading for architecture.

## The report is designed for twelve minutes

An appointment is short, and 40 to 80 percent of what is said in it is forgotten immediately, with almost half of what is remembered being wrong ([Kessels, 2003](https://journals.sagepub.com/doi/abs/10.1177/014107680309600504)). So the deliverable is a single page that leaves the room with the patient:

- One heading with the date range and how many days it covers.
- The current state in one badge and one sentence.
- A proportional bar of the whole period, so the shape is visible in a glance.
- Notable changes as a table: date, tier, and what moved in plain words.
- Spoken checks and the person's own notes.
- The non-diagnostic statement in full, inside the page rather than in a footer.
- Numbered sources.

A print stylesheet removes navigation and interface chrome, so what comes out of the printer is the page, not a screenshot of a website.

## Accessibility is a floor, not a goal

WCAG 2.2 AA minimum, verified: 100 on Lighthouse accessibility across all three pages, keyboard operable throughout, visible focus rings, reduced motion respected, 44px touch targets. The full audit and its honest limits are in [ACCESSIBILITY.md](ACCESSIBILITY.md). What Lighthouse cannot check is whether the tier language is clear to a worried person, and no user testing has been done, which is stated there rather than glossed.

## What we would change with more time

- **User testing with older adults and with clinicians.** Every claim above is reasoned from literature, not observed in a room. That is the largest gap in this design and no amount of internal review closes it.
- **A confidence indicator on the tier itself.** The engine knows how many days of baseline underlie a judgement; the interface reports the count but does not yet turn it into a stated confidence, which Spiegelhalter's "quantitative epistemic uncertainty about the numbers" would suggest for a more knowledgeable audience.
- **A second language.** The feature extractor is English-only, which is a real limit on who this can serve and is stated in the FAQ rather than hidden.
