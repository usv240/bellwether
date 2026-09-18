/**
 * Info button dictionary. Every statistic, technical term, and non-obvious
 * feature shown in the UI has an entry here, so any visitor, technical or
 * not, can understand any part of the page without leaving it. Sources are
 * the ones verified in docs/EVIDENCE.md.
 */

export interface InfoEntry {
  id: string;
  term: string;
  plain: string;
  technical?: string;
  sourceUrl?: string;
  sourceLabel?: string;
}

export const INFO: Record<string, InfoEntry> = {
  "baseline-band": {
    id: "baseline-band",
    term: "What this chart shows",
    plain:
      "Each dot is one day of one person's speech. The shaded band is that same person's ordinary range, learned from their own earlier days. A dot outside the band is only unusual compared with the band it left, never compared with anybody else.",
    technical:
      "The dots are real composite scores from the committed demonstration person, the same file the engine tests assert against. The band is the range their own quiet days occupied before any change was injected. Everything is greyscale except days outside the band, so the one colour on the chart carries exactly one meaning.",
  },
  "real-speech": {
    id: "real-speech",
    term: "349 real recorded conversations",
    plain:
      "To check the engine does not cry wolf on real people, it was run over 349 Supreme Court oral arguments by 8 justices, speech nobody here wrote. It flagged nothing. It also found that two different people sit closer together than one person's own day-to-day range, which is the reason this compares you only with yourself.",
    technical:
      "ConvoKit's Supreme Court corpus, from the Oyez Project. Paired with a sensitivity sweep so the zero means something: a sustained shift of 1.5 of a person's own standard deviations, injected into their real sessions, was caught in 5 of 5 subjects at a median of 2 sessions, and a do-nothing control at 0.0 caught nobody. There is no labelled cognitive change in that corpus, so none of this is evidence about dementia.",
    sourceUrl:
      "https://github.com/usv240/bellwether/blob/main/harness/scotus/results.json",
    sourceLabel: "The full result, including its four limits",
  },
  "speech-as-signal": {
    id: "speech-as-signal",
    term: "Speech as a vital sign",
    plain:
      "Your heart rate is measured all day by a watch. Speech is the only thing the brain produces continuously that anyone can observe, and when something changes in the brain, speech is usually where it shows first: more pauses, simpler sentences, lost words.",
    technical:
      "Language features from spontaneous speech (lexical diversity, syntactic complexity, pronoun reliance, filled pauses, idea density) are among the most replicated markers in the dementia-speech literature. Bellwether measures them against one person's own baseline rather than against a population.",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/26484921/",
    sourceLabel: "Fraser, Meltzer and Rudzicz, J Alzheimers Dis, 2016",
  },
  "diagnostic-delay": {
    id: "diagnostic-delay",
    term: "3.5 years to a diagnosis",
    plain:
      "Across all types of dementia, the average time from the first symptoms to a diagnosis is three and a half years. For people whose symptoms start young it is over four.",
    technical:
      "Systematic review with meta-analysis of 13 studies and 30,257 participants. Mean time to diagnosis 3.5 years (95 percent CI 2.7 to 4.3); young-onset 4.1 years (3.4 to 4.9). Moderate-quality evidence.",
    sourceUrl: "https://onlinelibrary.wiley.com/doi/10.1002/gps.70129",
    sourceLabel: "Orgeta et al., Int J Geriatr Psychiatry, 2025",
  },
  "treatment-window": {
    id: "treatment-window",
    term: "Treatments for the early stage only",
    plain:
      "The newest Alzheimer's treatments are approved only for people at the earliest stage. That is the stage a three-year delay skips past.",
    technical:
      "Lecanemab (traditional FDA approval July 2023) and donanemab (July 2024) are indicated for mild cognitive impairment or mild dementia due to Alzheimer's disease with confirmed amyloid. The lecanemab label states there are no data on initiating treatment at earlier or later stages than were studied. Bellwether makes no claim about treatment.",
    sourceUrl:
      "https://www.fda.gov/news-events/press-announcements/fda-converts-novel-alzheimers-disease-treatment-traditional-approval",
    sourceLabel: "U.S. FDA, 2023",
  },
  "forgotten-information": {
    id: "forgotten-information",
    term: "40 to 80 percent forgotten",
    plain:
      "Patients forget between 40 and 80 percent of what a doctor tells them straight away, and nearly half of what they do remember is wrong. That is why Bellwether produces a page you can take out of the room.",
    technical:
      "Quoted from the review: 40 to 80 percent of medical information provided by healthcare practitioners is forgotten immediately; almost half of the information that is remembered is incorrect.",
    sourceUrl: "https://journals.sagepub.com/doi/abs/10.1177/014107680309600504",
    sourceLabel: "Kessels, J R Soc Med, 2003",
  },
  adress: {
    id: "adress",
    term: "85 to 89.6 percent on the field's benchmark",
    plain:
      "On the standard public test the field uses, the best systems tell Alzheimer's speech from healthy speech about nine times out of ten. Bellwether does not classify anyone; it uses the same kinds of features to track one person over time.",
    technical:
      "ADReSS (Interspeech 2020): baselines of 62.5 percent from acoustic features and 76.85 percent from linguistic features of manual transcripts; best submitted systems 85 to 89.6 percent. Balanced for age and gender, drawn from the Pitt corpus in DementiaBank. Access to the data is restricted to verified academic researchers.",
    sourceUrl: "https://arxiv.org/abs/2004.06833",
    sourceLabel: "Luz et al., Interspeech 2020",
  },
  "n-of-1": {
    id: "n-of-1",
    term: "Your own baseline",
    plain:
      "Bellwether never compares you with other people. It learns how you normally speak, then watches for change from that. An accent, a second language, a quiet personality: none of it matters, because the baseline is you.",
    technical:
      "n-of-1 design. Per-feature EWMA mean and variance after a seven-day warmup; each day standardised as a z-score against the baseline as it stood before that day, so no day is compared with itself.",
  },
  warmup: {
    id: "warmup",
    term: "Learning",
    plain:
      "For the first seven days with enough speech, Bellwether only listens. It needs a week to learn what normal looks like for you before it can say anything about change.",
    technical:
      "The first seven eligible days set the initial mean and variance per feature by ordinary sample statistics. No tier is shown. Days with fewer than 150 words do not count toward warmup.",
  },
  cusum: {
    id: "cusum",
    term: "How change is detected",
    plain:
      "One running score adds up small, persistent shifts in the same direction and ignores one-off noisy days. It is designed to be slow to alarm, because a false alarm costs a family real worry.",
    technical:
      "One-sided CUSUM on a standardised composite of concern-signed z-scores (k 0.5, h 5.0). Under no change, the expected time to a false alarm is on the order of nine hundred days. Per-feature CUSUMs run for attribution only and never set the tier.",
  },
  freeze: {
    id: "freeze",
    term: "The baseline cannot learn its way out of a signal",
    plain:
      "While Bellwether is flagging a change, it stops updating what counts as normal. Otherwise a slow real change would quietly become the new normal and the signal would vanish.",
    technical:
      "EWMA updates are suspended while the composite CUSUM is above threshold. Without this, a persistent drift is absorbed into the baseline within a few weeks and the detector loses it.",
  },
  tiers: {
    id: "tiers",
    term: "Stable, watch, discuss",
    plain:
      "Stable means your speech is within your own normal range. Watch means several measures have moved together and Bellwether is keeping an eye on it. Discuss means the change has persisted for a week, or one day was sharply different, and it is worth raising with your clinician. None of these is a diagnosis.",
    technical:
      "watch: composite CUSUM tripped. discuss: tripped for seven consecutive eligible days, or a single day's composite above 5. excluded: fewer than 150 words that day. Every tier change lists the contributing features and their direction.",
  },
  exposure: {
    id: "exposure",
    term: "Quiet days",
    plain:
      "A day when you barely spoke is not a change in you. Bellwether leaves those days out and draws them hollow on the chart rather than reading anything into them.",
    technical:
      "Days with token_count_day below 150 are excluded from warmup, baseline updates and tier logic, and reported as excluded with the reason.",
  },
  "features-not-words": {
    id: "features-not-words",
    term: "Features, never words",
    plain:
      "Bellwether turns each day of speech into nine numbers and throws the words away. Nothing it stores can be turned back into a sentence. This is built into the code, not promised in a policy.",
    technical:
      "The public API accepts feature rows, not text; any field the schema does not know is dropped at the door, and a test posts a row with a transcript field and proves it never lands. A stored DayFeatures record holds no string but the date, and a test asserts that too.",
  },
  mattr: {
    id: "mattr",
    term: "Vocabulary variety",
    plain: "How varied your vocabulary is, measured in a way that is fair to long days and short days alike.",
    technical:
      "Moving-Average Type-Token Ratio over a 50-token window (Covington and McFall, 2010). Reduced lexical diversity is a replicated marker in Alzheimer's speech.",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/26484921/",
    sourceLabel: "Fraser et al., 2016",
  },
  "idea-density": {
    id: "idea-density",
    term: "Idea density",
    plain: "How much is actually said per ten words. In a famous long-term study, it predicted Alzheimer's disease decades in advance.",
    technical:
      "Propositions per ten words, approximated from part-of-speech tags after CPIDR (Brown et al., 2008). In the Nun Study, low idea density in autobiographies written at age 22 was associated with Alzheimer's disease at autopsy some 58 years later.",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/8606473/",
    sourceLabel: "Snowdon et al., JAMA, 1996",
  },
  "pronoun-noun": {
    id: "pronoun-noun",
    term: "Pronoun reliance",
    plain: "How often 'it' and 'they' stand in for the actual word. It rises when finding the right word gets harder.",
    technical: "Pronouns over pronouns plus nouns. Elevated in dementia discourse (Ahmed et al., Brain, 2013).",
  },
  "filler-rate": {
    id: "filler-rate",
    term: "Ums and uhs",
    plain: "Filled pauses per hundred words. Everyone has some; what matters is change from your own usual rate.",
    technical: "Lexically matched filled pauses per 100 words. A marker of lexical retrieval effort (Konig et al., 2015).",
  },
  "low-freq": {
    id: "low-freq",
    term: "Specific words",
    plain: "How often you reach for a rarer, more precise word instead of a common one. A fall can mean the precise word is harder to find.",
    technical:
      "Content words with a wordfreq Zipf frequency below 4.0, per 100 words. Proper nouns excluded so a friend's name does not count as sophisticated vocabulary.",
  },
  "dep-depth": {
    id: "dep-depth",
    term: "Sentence structure",
    plain: "How layered your sentences are, with clauses inside clauses.",
    technical: "Mean maximum dependency-parse depth per utterance. Reduced syntactic complexity is among the most replicated linguistic markers (Fraser et al., 2016).",
  },
  "spoken-check": {
    id: "spoken-check",
    term: "The spoken check",
    plain:
      "A ninety-second check you can do out loud when Bellwether flags a change, or whenever you like: name as many animals as you can in a minute, then repeat three sentences. An assistant can run it with you by voice.",
    technical:
      "Category fluency (animals, 60 seconds) and sentence repetition, scored locally and added to the timeline. The literature reports a cutoff below 15 animals as a high-sensitivity screen in older adults; Bellwether shows the score and never a judgement beyond the tier language.",
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/14981170/",
    sourceLabel: "Canning et al., Neurology, 2004",
  },
  simulated: {
    id: "simulated",
    term: "Simulated",
    plain:
      "The person on this page is not real. Their speech was generated to show what eight weeks looks like, including a gradual change from week six. Everything downstream of the words is the real product.",
    technical:
      "Synthetic personas from fixtures/personas, run through the production extractor and engine. The stable persona is quiet for 47 days with no false alarms; the drift persona reaches watch two days into a two-week ramp and discuss once the deviation is sharp.",
  },
  bee: {
    id: "bee",
    term: "The Bee wristband",
    plain:
      "Bee is a small wearable that transcribes your day. Bellwether reads those transcripts on your own computer, keeps the numbers and discards the words.",
    technical:
      "Ingestion calls the Bee CLI in code: bee conversations, bee now, bee changed with exactly-once cursors, bee stream --json in real time, and bee sync markdown offline. Only the wearer's own speech is analysed.",
    sourceUrl: "https://docs.bee.computer/",
    sourceLabel: "Bee developer documentation",
  },
  mcp: {
    id: "mcp",
    term: "Ask it out loud",
    plain:
      "Bellwether is also available to voice assistants and AI agents, so you can ask how you have been sounding without opening anything. The assistant gets the same seven numbers-only tools and nothing else.",
    technical:
      "A self-hosted Model Context Protocol server, spec 2025-11-25 over Streamable HTTP, with seven tools. A Strands agent on Amazon Bedrock consumes it as an independent client and has no other data access.",
  },
  "bedrock-ladder": {
    id: "bedrock-ladder",
    term: "The weekly note",
    plain:
      "Once a week Bellwether writes you three plain sentences about how your speech has been. The facts are computed first; an AI model is only allowed to phrase them, never to add to them or diagnose.",
    technical:
      "Claude on Amazon Bedrock through a three-model ladder; if every model fails, a deterministic template ships, so the note degrades in warmth and never in accuracy. Every note reports which model wrote it.",
  },
  confounders: {
    id: "confounders",
    term: "What else could explain this",
    plain:
      "Speech moves for ordinary reasons all the time: a bad night, a cold, a new medication, a stressful week, or simply talking to fewer people. Those explain far more changes than anything worrying does, so they are shown first, at the same size as the result.",
    technical:
      "Guidance on communicating uncertainty is explicit that a tool like this should admit what it does not know rather than present a single confident number. Bellwether shows the ordinary explanations beside every flag, and lets you annotate days so a change can be read in context later.",
    sourceUrl: "https://www.annualreviews.org/content/journals/10.1146/annurev-statistics-010814-020148",
    sourceLabel: "Spiegelhalter, Annual Review of Statistics and Its Application, 2017",
  },
  "duty-to-inform": {
    id: "duty-to-inform",
    term: "Informing, not persuading",
    plain:
      "Bellwether is not trying to get you to do anything. It shows you what changed, what might explain it, and what it cannot tell you, and then it stops. What you do with that is yours.",
    technical:
      "The risk-communication literature draws a sharp line between persuading an audience and fulfilling a duty to inform. Bellwether takes the second: no nudges, no streak pressure, no gamification, no urgency language, and the ordinary explanations for a change are given the same prominence as the change itself.",
    sourceUrl: "https://www.annualreviews.org/content/journals/10.1146/annurev-statistics-010814-020148",
    sourceLabel: "Spiegelhalter, 2017",
  },
  "general-wellness": {
    id: "general-wellness",
    term: "Not a diagnosis",
    plain:
      "Bellwether does not diagnose, treat, cure or prevent any disease, and it is not a medical device. Speech changes with sleep, stress, mood, medication and illness. It gives you a record of change over time to share with a clinician you trust.",
    technical:
      "Positioned as a general wellness tool. No output names a condition; the agent and the weekly note are forbidden from doing so by prompt and by test.",
  },
};

export function info(id: string): InfoEntry {
  const entry = INFO[id];
  if (!entry) {
    return { id, term: id, plain: "No explanation is available for this item yet." };
  }
  return entry;
}
