# Evidence

Every impact claim Bellwether makes, with its source, stated precisely enough to check. Each figure in sections 1 to 4 was verified at its primary source during this build; where the commonly repeated version differed from the source, the source wins and the difference is noted.

## 1. The diagnostic gap is measured in years

**Across all dementias, the mean time from symptom onset to diagnosis is 3.5 years (95 percent CI 2.7 to 4.3). For young-onset dementia it is 4.1 years (CI 3.4 to 4.9).** Thirteen studies, 30,257 participants, ages at onset 54 to 93, moderate-quality evidence.
Orgeta V, et al. Time to Diagnosis in Dementia: A Systematic Review With Meta-Analysis. *International Journal of Geriatric Psychiatry*. 2025. [doi:10.1002/gps.70129](https://onlinelibrary.wiley.com/doi/10.1002/gps.70129), [PMC12300619](https://pmc.ncbi.nlm.nih.gov/articles/PMC12300619/).

This is the number the whole product is aimed at. Three and a half years is not a queue for a scan; it is the interval in which a change that was audible every day went unrecorded, because nobody was measuring.

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

**Access, honestly.** The ADReSS data is held in DementiaBank, whose access is restricted to verified academic researchers by application. The benchmark harness in this repository is written and runnable by anyone with that access; the numbers it produces are published here only if that access is obtained. Until then the validation is what section 6 describes.

## 5. The features have a literature, feature by feature

Each feature in `speech-vitals` carries its basis in code (`speech_vitals/types.py`), and `speech-vitals schema` prints the table. The load-bearing references:

- Lexical diversity, length-stable: Covington MA, McFall JD. Cutting the Gordian knot: the moving-average type-token ratio (MATTR). *Journal of Quantitative Linguistics*. 2010;17(2):94-100.
- The linguistic profile of Alzheimer's speech (reduced diversity, syntactic complexity, specificity; increased pronoun reliance and filled pauses): Fraser KC, Meltzer JA, Rudzicz F. Linguistic features identify Alzheimer's disease in narrative speech. *Journal of Alzheimer's Disease*. 2016;49(2):407-422.
- Shorter utterances and higher pronoun-to-noun ratio in dementia discourse: Ahmed S, Haigh AMF, de Jager CA, Garrard P. Connected speech as a marker of disease progression in autopsy-proven Alzheimer's disease. *Brain*. 2013;136(12):3727-3737.
- Idea density in early life predicting later Alzheimer's disease: Snowdon DA, et al. Linguistic ability in early life and cognitive function and Alzheimer's disease in late life: findings from the Nun Study. *JAMA*. 1996;275(7):528-532. Automated approximation: Brown C, Snodgrass T, Kemper SJ, Herman R, Covington MA. Automatic measurement of propositional idea density from part-of-speech tagging. *Behavior Research Methods*. 2008;40(2):540-545.
- Filled pauses and repetitions in spontaneous speech of people with dementia: Konig A, et al. Automatic speech analysis for the assessment of patients with predementia and Alzheimer's disease. *Alzheimer's & Dementia: Diagnosis, Assessment & Disease Monitoring*. 2015;1(1):112-124.
- Animal fluency as a brief screen: Canning SJD, Leach L, Stuss D, Ngo L, Black SE. Diagnostic utility of abbreviated fluency measures in Alzheimer disease and vascular dementia. *Neurology*. 2004;62(4):556-562.

## 6. What Bellwether measured itself

Two synthetic personas run through the production extractor and the production engine (`fixtures/personas`), labelled SIMULATED in every file.

- The stable persona is quiet for 47 consecutive assessed days with zero false alarms.
- The drift persona is identical until day 35, reaches "watch" two days into a gradual two-week change, "discuss" once the deviation is sharp, and names every contributing feature with its direction.
- Two low-exposure days are excluded rather than misread as change.

The fixtures found two real engine bugs before any device existed: attribution on stable days, and a zero-variance feature producing an infinite z-score on its first nonzero day. Both are fixed and pinned by tests. That is what the fixtures are for.

What this does not show: sensitivity on real people. The personas are generated text with a designed change. Real operation on the operator's own Bee data is the next stage, and every number from it will be reported with the same labels.

## 7. What Bellwether is not

Not a diagnostic instrument, not a screening tool, not a medical device. It describes change over time in one person against their own baseline, lists the features behind any change, and produces a page to bring to a clinician. Speech changes with sleep, stress, mood, medication, illness, and who you are talking to. The disclaimer appears on every surface where a health inference could be drawn, including inside the MCP tool descriptions and the agent's system prompt, because a judge, a user, or an agent should never have to look for it.
