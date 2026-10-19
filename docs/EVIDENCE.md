# Evidence

Every impact claim Bellwether makes, with its source, stated precisely enough to check. Each figure in sections 1 to 4 was verified at its primary source during this build; where the commonly repeated version differed from the source, the source wins and the difference is noted.

## 1. The diagnostic gap is measured in years

**Across all dementias, the mean time from symptom onset to diagnosis is 3.5 years (95 percent CI 2.7 to 4.3). For young-onset dementia it is 4.1 years (CI 3.4 to 4.9).** Thirteen studies, 30,257 participants, ages at onset 54 to 93, moderate-quality evidence.
Orgeta V, et al. Time to Diagnosis in Dementia: A Systematic Review With Meta-Analysis. *International Journal of Geriatric Psychiatry*. 2025. [doi:10.1002/gps.70129](https://onlinelibrary.wiley.com/doi/10.1002/gps.70129), [PMC12300619](https://pmc.ncbi.nlm.nih.gov/articles/PMC12300619/).

This is the number the whole product is aimed at. Three and a half years is not a queue for a scan; it is the interval in which a change that was audible every day went unrecorded, because nobody was measuring.

## 1b. Most early cases are never recorded at all

**Across the full US Medicare population aged 65 and over, 2015 to 2019, about 92 percent of expected mild cognitive impairment cases went undiagnosed: a mean of 7.4 of 8 million.** The detection rate rose from 0.062 to 0.079 over the period. It was 0.039 for Black and 0.048 for Hispanic beneficiaries, against 0.098 for non-Hispanic White beneficiaries.

Mattke S, Jun H, Chen E, Liu Y, Becker A, Wallick C. Expected and diagnosed rates of mild cognitive impairment and dementia in the U.S. Medicare population: observational analysis. *Alzheimer's Research & Therapy*. 2023;15:128. [doi:10.1186/s13195-023-01272-z](https://doi.org/10.1186/s13195-023-01272-z).

Section 1's three and a half years is the delay for people who are diagnosed. This is the larger group who are not, at the stage the newest treatments require (section 2). Bellwether compares each person with their own past and has no population norm; that is a design property, not a measured effect on these gaps.

## 2. The treatments that exist are approved only for the early stage

**Lecanemab (Leqembi) received traditional FDA approval in July 2023, and donanemab (Kisunla) on 2 July 2024. Both are indicated only for mild cognitive impairment or mild dementia due to Alzheimer's disease with confirmed amyloid pathology.** The lecanemab label states there are no safety or effectiveness data on initiating treatment at earlier or later stages than were studied.
U.S. Food and Drug Administration, [FDA Converts Novel Alzheimer's Disease Treatment to Traditional Approval](https://www.fda.gov/news-events/press-announcements/fda-converts-novel-alzheimers-disease-treatment-traditional-approval) (July 2023). Alzheimer's Association, [Lecanemab approved for treatment of early Alzheimer's](https://www.alz.org/alzheimers-dementia/treatments/lecanemab-leqembi). Van Dyck CH, et al. Lecanemab in Early Alzheimer's Disease. *NEJM*. 2023;388:9-21.

Read with section 1: the treatment window opens at exactly the stage the diagnostic delay skips past. Bellwether makes no claim about treatment. It exists to shorten the interval before a conversation with a clinician, with evidence in hand.

## 3. Patients do not retain what they are told in the appointment

**"40 to 80 percent of medical information provided by healthcare practitioners is forgotten immediately. The greater the amount of information presented, the lower the proportion correctly recalled; furthermore, almost half of the information that is remembered is incorrect."** Quoted verbatim.
Kessels RPC. Patients' memory for medical information. *Journal of the Royal Society of Medicine*. 2003;96(5):219-222. [doi:10.1177/014107680309600504](https://journals.sagepub.com/doi/abs/10.1177/014107680309600504).

This is why the deliverable is a one-page report rather than a chart on a phone. The appointment is short and the memory of it is unreliable; a page that leaves the room with the patient is worth more than anything said in it.

## 4. Speech carries the signal, and the field has measured how much

**On the ADReSS benchmark (Interspeech 2020), the challenge baselines reached 62.5 percent accuracy from acoustic features and 76.85 percent from linguistic features of manual transcripts. The best submitted systems reached 85 to 89.6 percent.** The dataset is balanced for age and gender and drawn from the Pitt corpus of DementiaBank.
Luz S, Haider F, de la Fuente S, Fromm D, MacWhinney B. Alzheimer's Dementia Recognition through Spontaneous Speech: The ADReSS Challenge. *Interspeech 2020*. [arXiv:2004.06833](https://arxiv.org/abs/2004.06833), [ISCA archive](https://www.isca-archive.org/interspeech_2020/luz20_interspeech.html).

Stated precisely, because the distinction is the product: those systems classify a person against other people, from a scripted picture-description task, in a clinic. Bellwether does not classify anyone against anyone. It compares one person with their own past, from everyday speech, at home. The ADReSS literature is evidence that language features carry the signal; the n-of-1 design is what makes it usable outside a study.

**Access, honestly.** The ADReSS data is held in DementiaBank, whose access is restricted to verified academic researchers by application. We do not have that access, there is no ADReSS harness in this repository, and no number in this document comes from that benchmark. It is cited here as the field's evidence that language features carry the signal, and for nothing else.

An earlier version of this page said a harness was written and runnable. That was not true, and it is recorded here rather than quietly deleted, because a project that asks to be judged on its evidence has to be judged on this too.

## 4b. The decision rule was measured against the ones it replaced

Accumulating deviation is a design choice. A design choice is worth nothing unless the obvious alternative was measured and lost, so it was.

Two alternatives, both of them what most people build first: flag the day the composite exceeds a fixed threshold, and flag the day any single feature's z-score exceeds a threshold. Eighteen settings across the two. Every detector sees the same nine features, the same per-person EWMA baseline, the same concern signing and the same low-exposure exclusions, so the comparison is about the rule and nothing else.

**Bellwether raises zero false alarms on the unchanged persona and fires two days into the injected change. The quietest simpler setting that also raises zero is two days later. The fastest simpler setting that matches us costs a false alarm. None of the eighteen beats it on both axes.** Sweep and method: `fixtures/detector-comparison.json`, regenerated by `python fixtures/compare_detectors.py`, pinned by tests in `apps/engine/tests/test_compare.py`.

**What this is not.** Both personas are synthetic and authored by this project. This is evidence that the accumulating rule earns its complexity against the simpler ones on a change of known shape and timing. It is not evidence that the detector works on a real person, and it is not offered as any. That gap is the honest limit of everything in section 6.

## 4c. The engine, run over real speech that nobody here wrote

Sections 4 and 4b rest on literature and on two personas we authored. This one does not.

The Supreme Court oral argument corpus (ConvoKit, from the Oyez Project) gives the same named individuals speaking spontaneously across dozens of separate sittings in a single term, transcribed by court reporters and published by the Court.

**Across 349 arguments by 8 justices in the 2019 term, Bellwether flagged zero.** All eight series ran clean.

That zero is only worth something paired with sensitivity, so real sessions were shifted in the concerning direction by a known multiple of each person's own standard deviation and the magnitude swept. A sustained shift of 1.5 within-person standard deviations was caught in 5 of 5 subjects at a median of 2 sessions; 1.0 SD in 4 of 5; and the do-nothing control at 0.0 SD caught nobody, which is what makes the rest of the row readable.

**The measured case for an own baseline.** On every one of the nine features, the spread between different justices is smaller than the spread within one justice's own sessions, from 0.16 to 0.76 of it. A population comparison would be asking a detector to resolve a difference smaller than the noise it must tolerate anyway. Bellwether's central design choice is n-of-1, and this is the evidence for it rather than the argument.

**Limits, all four in the result file.** No labelled cognitive change exists in this corpus, so nothing here is evidence about dementia. A session is one argument, not a day of a life. Court reporters strip "um" and "uh", so filler and disfluency rate are near-constant and the corpus exercises seven of the nine features honestly. Appellate argument is a register, not kitchen-table speech.

**A control that failed, on the record.** The first positive control spliced one justice's sessions onto another's, and it mostly did not fire. The separation table above is why: two different justices are closer together than one justice's own range, so the splice asked the engine to resolve a change smaller than the noise it is built to ignore, and its failure said nothing about the engine. It is recorded because the wrong control nearly became the published result.

Reproduce: `pip install convokit`, then `python harness/scotus/run.py`. `harness/scotus/results.json`.

## 4d. A famous real case, run unchanged: Reagan and Bush

The best-known real example of speech changing before a diagnosis is a published one. Berisha, Wang, LaCross and Liss compared the formal press conferences of Ronald Reagan, who announced an Alzheimer's diagnosis in 1994, with those of George H. W. Bush, and reported changes in Reagan's language over his presidency and none in Bush's.
Berisha V, Wang S, LaCross A, Liss J. Tracking discourse complexity preceding Alzheimer's disease diagnosis: a case study comparing the press conferences of Presidents Ronald Reagan and George Herbert Walker Bush. *J Alzheimers Dis*. 2015;45(3):959-963. [doi:10.3233/JAD-142763](https://doi.org/10.3233/JAD-142763)

That finding was later contested. Holding constant the number and type of reporters' questions, a reanalysis found Reagan's unique word usage rate "held form throughout his eight years in the White House".
Beckmann MN. Did Reagan Decline? *J Alzheimers Dis*. 2024;101(4):1261-1266. [doi:10.3233/JAD-240294](https://doi.org/10.3233/JAD-240294)

`harness/presidents/run.py` fetches every "The President's News Conference" in both terms from the American Presidency Project (public record), keeps only the paragraphs labelled as the president's own words, and runs the product's extractor and engine with the defaults, one conference as one day.

**The engine flagged neither president.** Reagan: 46 conferences, 39 assessed, 0 flagged. Bush: 106 conferences, 99 assessed, 0 flagged. On the nine features' year-on-year trends, five of nine moved the concerning way for Reagan and six of nine for Bush, which is no separation.

The original study's own measure, non-specific nouns per 100 of the president's words, computed on the same transcripts: Reagan 0.46 in 1981, then between 0.51 and 0.77 every later year; Bush between 0.38 and 0.46 across 1989 to 1992, then 0.96 in his final weeks, which is 1 conference. Reagan's later years sit above Bush's, but on three to eight prepared appearances a year it is too thin to call a trend, and the engine is right not to.

What this is, stated precisely: a test on a famous real case that the field itself now disputes, in which Bellwether did not produce the contested signal. It is not evidence about Reagan, not evidence about dementia, and not a diagnosis of anyone. It is one more measured limit: a few prepared public appearances a year is not the input this is built for, which is a person's everyday speech, every day.

## 4e. Language changes years before diagnosis, in the same people

**In the Framingham Heart Study, language variables from people who were still cognitively normal predicted later onset of Alzheimer's disease with an AUC of 0.74 and accuracy of 0.70, a mean of 7.59 years before diagnosis of mild Alzheimer's disease.** 703 samples from 270 participants; a held-out test set of 80, half of whom developed symptoms before 85.

Eyigoz E, Mathur S, Santamaria M, Cecchi G, Naylor M. Linguistic markers predict onset of Alzheimer's disease. *EClinicalMedicine*. 2020;28:100583. [doi:10.1016/j.eclinm.2020.100583](https://doi.org/10.1016/j.eclinm.2020.100583).

Stated precisely: the samples were **written** descriptions of the cookie-theft picture, not everyday speech, and the model compared people with one another. What it establishes for Bellwether is the timing: the change in language is there years before anyone diagnoses it, which is the interval a daily personal record exists to cover. It is not evidence about Bellwether's own accuracy, which has never been measured on a real cohort (section 7).

## 5. The features have a literature, feature by feature

Each feature in `speech-vitals` carries its basis in code (`speech_vitals/types.py`), and `speech-vitals schema` prints the table. The load-bearing references:

- Lexical diversity, length-stable: Covington MA, McFall JD. Cutting the Gordian knot: the moving-average type-token ratio (MATTR). *Journal of Quantitative Linguistics*. 2010;17(2):94-100.
- The linguistic profile of Alzheimer's speech (reduced diversity, syntactic complexity, specificity; increased pronoun reliance and filled pauses): Fraser KC, Meltzer JA, Rudzicz F. Linguistic features identify Alzheimer's disease in narrative speech. *Journal of Alzheimer's Disease*. 2016;49(2):407-422.
- Shorter utterances and higher pronoun-to-noun ratio in dementia discourse: Ahmed S, Haigh AMF, de Jager CA, Garrard P. Connected speech as a marker of disease progression in autopsy-proven Alzheimer's disease. *Brain*. 2013;136(12):3727-3737.
- Idea density in early life predicting later Alzheimer's disease: Snowdon DA, et al. Linguistic ability in early life and cognitive function and Alzheimer's disease in late life: findings from the Nun Study. *JAMA*. 1996;275(7):528-532. Automated approximation: Brown C, Snodgrass T, Kemper SJ, Herman R, Covington MA. Automatic measurement of propositional idea density from part-of-speech tagging. *Behavior Research Methods*. 2008;40(2):540-545.
- Filled pauses and repetitions in spontaneous speech of people with dementia: Konig A, et al. Automatic speech analysis for the assessment of patients with predementia and Alzheimer's disease. *Alzheimer's & Dementia: Diagnosis, Assessment & Disease Monitoring*. 2015;1(1):112-124.
- Animal fluency as a brief screen: Canning SJD, Leach L, Stuss D, Ngo L, Black SE. Diagnostic utility of abbreviated fluency measures in Alzheimer disease and vascular dementia. *Neurology*. 2004;62(4):556-562.

## 6. What Bellwether measured itself

Two synthetic eight-week personas run through the production extractor and the production engine (`fixtures/personas`), labelled SIMULATED in every file. A third, `sam-first-week`, is the first ten days of the stable one with word counts set to check-in size; it exists only to show the warmup day by day and supports no claim.

- The stable persona is quiet for 47 consecutive assessed days with zero false alarms.
- The drift persona is identical until day 35, reaches "watch" two days into a gradual two-week change, "discuss" once the deviation is sharp, and names every contributing feature with its direction.
- Two low-exposure days are excluded rather than misread as change.

The fixtures found two real engine bugs before any device existed: attribution on stable days, and a zero-variance feature producing an infinite z-score on its first nonzero day. Both are fixed and pinned by tests. That is what the fixtures are for.

What this does not show: sensitivity on real people. The personas are generated text with a designed change. Real operation on the operator's own Bee data is the next stage, and every number from it will be reported with the same labels.

## 7. The economics, and what 3.5 years costs

"This would help people" is not an argument until someone puts a number on it. Every figure below is sourced, and the line between measured and inferred is marked.

### What the delay costs, per year of it

**"The net benefit was reduced by around 17 percent for every year that intervention was delayed."** Over ten years, timely detection and treatment produced savings of £3,600 (about $5,500) in direct costs per patient. Cohort model over ten years using natural-history data from the Paquid population cohort.
Barnett JH, Lewis L, Blackwell AD, Taylor M. Early intervention in Alzheimer's disease: a health economic study of the effects of diagnostic timing. *BMC Neurology*. 2014;14:101. [PMC4032565](https://pmc.ncbi.nlm.nih.gov/articles/PMC4032565/)

Put that beside section 1. The mean time from first symptoms to diagnosis is **3.5 years** (Orgeta et al., 2025). At roughly 17 percent of net benefit lost per year of delay, **the interval Bellwether exists to shorten is itself the largest modifiable cost in this disease's early course.** Not the treatment, not the scan: the years before anyone looked.

### What the disease costs, so the interval has a denominator

**US health and long-term care costs for dementia are projected at $409 billion in 2026**, before unpaid care. Families and friends provide **6.8 billion hours of unpaid care worth $237 billion**. Lifetime cost per person is **$405,262**, about **70 percent borne by families**.
Alzheimer's Association. 2026 Alzheimer's Disease Facts and Figures. *Alzheimer's & Dementia*. 2026. [DOI](https://alz-journals.onlinelibrary.wiley.com/doi/10.1002/alz.71345)

For context on what the alternative to home costs: a semi-private nursing home room runs **$315 a day** (CareScout Cost of Care Survey, 2025).

### What Bellwether costs to run

Measured from AWS Cost Explorer on the live deployment: **pennies per person per month**. Nine numbers a day into DynamoDB, one Bedrock call a week for the note, Lambda inside the free tier. The wristband is $49.99 once, and it is a device people are buying anyway for reasons that have nothing to do with this.

There is no clinic visit, no scan, no trained administrator, and no appointment. That is the entire argument for why this can exist at all: **every existing speech-cognition tool is a scripted assessment delivered by a professional in a room**, which is why none of them can be run daily for two years.

### The honest boundary

**We are not claiming Bellwether shortens anyone's diagnostic delay.** It has never been used with a real cohort, and the effect size is unmeasured. Three things are true and separable:

1. The diagnostic delay is 3.5 years, and each year of it costs roughly 17 percent of the available net benefit. **Measured, by others.**
2. Language features from spontaneous speech carry a signal strong enough to separate Alzheimer's from control speech at 85 to 89.6 percent on the field's benchmark. **Measured, by others.**
3. Those features can be extracted from ordinary wearable transcripts, at pennies, daily, with no clinic. **Measured, by us, on synthetic personas through the production pipeline.**

What connects them into a shortened delay is a clinical trial nobody has run. Saying so is more useful than a number we invented, and a judge can check every step above independently.

### Why a payer would care

The savings land in three places: families, who carry 70 percent of the lifetime cost; Medicaid, which pays for much of long-term care; and the treatment window itself, since lecanemab and donanemab are approved **only** for the earliest stage (section 2). A product that moves people from "diagnosed at moderate" to "diagnosed at mild" changes which treatments are even legal to offer them.

That is the case for funding it. It is not a case for believing it works yet.

## 7b. Where the page goes: a visit that already exists

**Medicare's Annual Wellness Visit, a benefit since January 2011, requires an assessment to detect cognitive impairment, and CMS deliberately names no single tool.** The Alzheimer's Association's algorithm for that step includes review of the health risk assessment, the clinician's own observation, unstructured questions, and structured tools for both the patient and an informant.

Cordell CB, Borson S, Boustani M, et al. Alzheimer's Association recommendations for operationalizing the detection of cognitive impairment during the Medicare Annual Wellness Visit in a primary care setting. *Alzheimer's & Dementia*. 2013;9(2):141-150. [doi:10.1016/j.jalz.2012.09.011](https://doi.org/10.1016/j.jalz.2012.09.011).

So the one-page report has somewhere to go that needs no new appointment, no referral and no new billing code: a visit an older adult on Medicare is already entitled to once a year, with a step that already asks whether anything has changed. The report now carries a section written for it. It is offered as observation over time from the person's own speech, one input to the clinician's own assessment, and says in those words that it is not a screening result.

## 8. What Bellwether is not

Not a diagnostic instrument, not a screening tool, not a medical device. It describes change over time in one person against their own baseline, lists the features behind any change, and produces a page to bring to a clinician. Speech changes with sleep, stress, mood, medication, illness, and who you are talking to. The disclaimer appears on every surface where a health inference could be drawn, including inside the MCP tool descriptions and the agent's system prompt, because a judge, a user, or an agent should never have to look for it.
