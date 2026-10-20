# The study to run

Bellwether makes no claim to shorten anyone's diagnostic delay, because nobody has measured whether it does. This is the study that would, written so its endpoints are fixed before any data exists. It involves no one yet. It is a protocol, not a result.

## Question

Can a daily, own-baseline record of everyday speech, kept on a wearable the person already owns, be sustained for a year by adults attending a memory clinic, and does change in that record line up with change the clinic measures?

## Design

Single-arm feasibility study, twelve months, one memory clinic.

- **Participants:** 40 adults aged 60 or over attending the clinic for a routine annual review, with a clinic-assessed status at entry (any status; the study is about change, not about a group). English speakers, since the feature set is English only today. Each receives a Bee wristband.
- **What they do:** wear the band and record one voice note of about two minutes a day in the Bee app, any topic. Run `bellwether-ingest mine` once a day on their own computer, or a family member does it for them. Nothing else.
- **What leaves the home:** nine numbers a day and a date. The stack is deployed into the clinic's own AWS account from one CDK command, so the clinic holds the numbers and nobody else does.
- **What the clinic does:** its usual assessment at entry, six months and twelve months (whatever instrument the clinic already uses, for example MoCA or CDR), recorded blind to the Bellwether record.
- **What Bellwether does:** nothing different from today. Tiers are derived by the same engine, with the same thresholds, and are frozen before the first participant enrols.

## Endpoints, fixed in advance

**Primary (feasibility):**

1. Adherence: the proportion of study days with at least 150 words of the participant's own speech recorded. The product is designed around two minutes a day; if people will not do that, the design fails, whatever the engine can do.
2. Retention: the proportion of participants still recording at twelve months.

**Secondary (signal):**

3. Agreement: among participants whose clinic assessment changed between entry and twelve months, the proportion whose Bellwether record entered the watch or discuss tier before the clinic visit that recorded the change, and by how many days.
4. Restraint: among participants whose clinic assessment did not change, the number of days spent in watch or discuss per hundred assessed days. This is the false-alarm rate on real people, which no synthetic persona can give.
5. Usefulness: each clinician rates the doctor report at the twelve-month visit on whether it changed what they asked, on a fixed three-point scale.

**Pre-specified kill criteria:** if adherence is below 60 percent of days, or retention below 50 percent, the product as designed does not work, and the report says so first.

## Sample size

Forty is a feasibility number, not a powered one. It is enough to estimate adherence to within about 15 percentage points and to see whether endpoint 3 is worth a controlled study; it is not enough to claim sensitivity or specificity, and the write-up will not.

## What this study cannot show

- That Bellwether shortens the diagnostic delay. That needs a controlled study with time-to-diagnosis as the outcome, which this one is designed to justify or rule out.
- Anything about a population. Every comparison is within one person.
- Anything about audio features. Bee gives transcripts; pauses and articulation are not measured.

## Safety and consent

Participants are told in writing, and the dashboard says on every page, that Bellwether is not a diagnosis, not a screening test and not a medical device. A watch or discuss tier is a reason to add a note or to bring the report to the next visit, never a reason to act alone. Any participant can stop at any time and have their rows deleted; the rows contain no speech to begin with. Ethics approval from the clinic's board before enrolment.

## Cost

Forty wristbands at $49.99, about $2,000. The service costs about 20 cents per participant per month inside the clinic's account with a nightly spoken check-in, at list prices (`scripts/cost.py`). The real cost is staff time at three visits the clinic was holding anyway, plus one person to answer the phone when the command does not run. This is the whole reason the study can exist: every previous speech-cognition instrument needed a trained administrator in a room, so none could be run daily for a year.

## Why a payer would care

The savings from a shorter delay land with families, who carry about 70 percent of the lifetime cost, and with the treatment window itself, since the newest treatments are approved only for the earliest stage. A record that moves a conversation with a clinician earlier changes what can even be offered. That is the case for funding this study. It is not a case for believing the product works yet.

Sources for every figure: [EVIDENCE.md](EVIDENCE.md).
