# Processing speed as a per-person trait: what the individual-differences literature supports

Status: literature review, 2026-11-16. Purpose: ground the NPC "processing speed" trait (a multiplier on the
modelled onset of replies and decisions, median 1, drawn once, stable for life) in human data instead of a guess.
Fatigue and other within-person variation are out of scope except where they bound how "stable" a trait can be.

## How to read the tags

- **verified**: I read the number in the primary source (full text or abstract) during this review; the location is
  given.
- **verified (cited)**: I read it in a primary paper by the same authors that cites their own earlier paper for it; the
  earlier paper itself was not read.
- **secondary**: from a review or a later paper citing it.
- **derived**: my arithmetic on verified numbers (the formula is given). Not a published figure.
- **unverified**: remembered or not located; do not rely on it.

Lognormal conversions use sigma = sqrt(ln(1 + CV^2)); for CV under 0.3, sigma is about equal to CV. The skew of a
lognormal with that CV is (e^(sigma^2) + 2) * sqrt(e^(sigma^2) - 1); a gamma with the same CV has skew 2 * CV.

## Correction to the design note first

The note cites "Deary, Der & Ford 2001, *to verify*". The citation is real and correct: Deary, I. J., Der, G., & Ford,
G. (2001). Reaction times and intelligence differences: A population-based cohort study. *Intelligence*, 29(5),
389-399. doi:10.1016/S0160-2896(01)00062-9. But it cannot carry the age part of the design: it is a single
narrow-age cohort (mean age 56.3, SD 0.6). It gives the spread among people **of one age**, which is what a per-person
trait should model once age is handled separately. The age data come from Der & Deary (2006) and (2017), below.

## 1. Between-person distribution of mean RT in healthy adults

### Numbers

| Source | Sample | Task | Mean of person means | Between-person SD | CV | Skew of person means | Tag, location |
|---|---|---|---|---|---|---|---|
| Deary, Der & Ford 2001 | N = 900, West of Scotland Twenty-07 cohort, age 56 (SD 0.6), population-representative, tested at home by nurses | Simple RT, 20 test trials | 358.2 ms | 119.7 ms | 0.33 (derived) | not reported | verified, Table 1, p. 393 |
| same | same | 4-choice RT, 40 test trials | 727.8 ms | 107.5 ms | 0.15 (derived) | not reported | verified, Table 1, p. 393 |
| Der & Deary 2017 | Twenty-07 wave 4 (2000/01), N = 714 aged 30, 813 aged 50, 669 aged 69; same device and protocol | Simple RT | 290 / 318 / 354 ms | 74 / 97 / 112 ms | 0.26 / 0.31 / 0.32 (derived) | 2.0 / 2.0 / 1.6 | verified, Table 1, p. 91 |
| same | same | 4-choice RT | 539 / 623 / 729 ms | 72 / 93 / 105 ms | 0.13 / 0.15 / 0.14 (derived) | 0.7 / 1.1 / 0.8 | verified, Table 1, p. 91 |
| Hagger-Johnson et al. 2014 (NHANES III) | N = 5,134 US adults aged 20-59 (mean 36.7), representative | Simple RT, 50 trials, no practice | 242.7 ms | 58.0 ms | 0.24 (derived) | not reported | verified, Table 1 |
| Woods et al. 2015a | N = 1,469 community volunteers, 18-65, lab | Simple RT, 120 trials | 230.8 ms | 26.8 ms | 0.12 (derived) | not reported; 8 people above 350 ms not plotted | verified, Table 2 |
| Woods et al. 2015b | N = 1,466 (same pool), 18-65, lab | Visual feature-conjunction choice RT, 140 trials | 550 ms | 72 ms | 0.13 (derived) | not reported | verified, Tables 1-2 |
| Hintz et al. 2020 (IDLaS-NL) | N = 112 Dutch adults aged 18-29, lab, outliers trimmed | Auditory simple RT | 235 ms | 48 ms | 0.20 | log10 values: -1.36 | verified, Online-only Table 2 |
| same | same | Visual simple RT | 244 ms | 33 ms | 0.14 | log10 values: -0.54 | verified, Online-only Table 2 |
| same | same | Auditory choice RT | 417 ms | 100 ms | 0.24 | log10 values: -0.60 | verified, Online-only Table 2 |
| same | same | Visual choice RT | 439 ms | 90 ms | 0.21 | log10 values: 0.88 | verified, Online-only Table 2 |

Hintz et al. also give the SD of log10 person means: 0.08 (auditory simple), 0.05 (visual simple), 0.09 (auditory
choice), 0.07 (visual choice). In natural-log units that is a lognormal sigma of 0.18, 0.12, 0.21, 0.16 (derived,
times ln 10).

Correlation with ability (Deary, Der & Ford 2001, verified, Results p. 393 and Table 2): AH4 Part I total correlates
-0.31 with simple RT mean, -0.49 with 4-choice RT mean, -0.26 with each intra-individual SD, and -0.15 with the
choice minus simple difference. Simple and choice RT means correlate 0.59 with each other (p. 397). No sex difference
in either mean (p = .68 and .97); women had higher choice-RT variability (effect size 0.38 SD). Der & Deary 2017
(verified, Table 3) replicate this by age: CRT-AH4 -0.44, -0.47, -0.53 at ages 30, 50, 69; SRT-AH4 -0.27, -0.30,
-0.32. Pooling ages inflates them (-0.58 and -0.36) because age drives both.

### What shape fits person-level means

- **Ex-Gaussian is the wrong level.** It is the standard fit for one person's trial distribution (Shao et al. 2012
  use it that way), not for the distribution of person means. No source I found fits ex-Gaussian, gamma or
  lognormal to person means and compares them formally. **I found no direct model comparison; say so in the design.**
- **Raw person means are right-skewed** in every population sample that reports skew: SRT 1.6-2.0, CRT 0.7-1.1 (Der &
  Deary 2017, verified). Der and Deary use a Box-Cox transform to normalise them and note "a floor effect just above
  200 milliseconds" for SRT and variance that grows at lower ability (verified, p. 90-91). UK Biobank RT was "positively
  [skewed]" and natural-log transformed for analysis (Lyall et al. 2016, verified, Analysis section).
- **That skew is larger than a lognormal with the same CV predicts.** A lognormal with CV 0.26-0.32 has skew 0.8-1.0,
  against 1.6-2.0 observed for SRT; for CRT CV 0.13-0.15 it predicts 0.4-0.45 against 0.7-1.1 observed (derived). A
  gamma is lighter still (0.5-0.6 and 0.3). So the population tail is heavier than lognormal. The likely reason, from
  the same papers: a minority of slow, inconsistent responders (lower ability, older, lapses on a 20-trial home test).
- **In trimmed lab data the log of person means is roughly symmetric**: Hintz et al. report log10 skews of -1.36 to
  +0.88, mostly near or below zero, so after trimming a lognormal is if anything slightly too right-tailed for healthy
  young adults (verified table; interpretation mine).
- **The CV depends heavily on protocol.** For simple RT it ranges from 0.12 (120 lab trials, Woods) to 0.33 (20 home
  trials, Deary 2001); choice RT is steadier at 0.13-0.24. Few trials, no practice and home testing inflate the spread
  with lapses and measurement error. For a game trait that models a person's true typical speed, the lower,
  many-trial figures are the better guide, but the population tail is real.

## 2. Stable trait versus noise

| Quantity | Value | Sample, interval | Tag, location |
|---|---|---|---|
| Test-retest of SRT mean | 0.67 (Spearman) | Twenty-07, "period free" | verified (cited): Der & Deary 2017, p. 90, citing Deary & Der 2005 |
| Test-retest of 4-choice RT mean | 0.92 | same | verified (cited), same |
| Test-retest of SRT / CRT intra-individual SD | 0.20 / 0.73 | same | verified (cited), same |
| Test-retest of RT means, 3 weeks | 0.35-0.80, mostly 0.6-0.8 (e.g. flanker congruent 0.74 and 0.69, Stroop neutral 0.74 and 0.73, Posner valid 0.80) | Undergraduates, N = 40-57 per task | verified, Hedge et al. 2018, Tables 1-2 |
| Test-retest of RT means, ~1 month | auditory SRT 0.59, visual SRT 0.58, auditory CRT 0.76, visual CRT 0.78, letter comparison 0.83, picture naming 0.69 | IDLaS-NL, N = 112, ages 18-29, mean 33 days | verified, Hintz et al. 2020, Online-only Table 2 |
| Internal consistency of the same | 0.86-0.96 (picture naming 0.88) | same, single session | verified, same |
| Stability over ~4.3 years, UK Biobank "snap" RT | ICC(2,1) = 0.57 (95% CI 0.56-0.58) | N = 19,327; mean interval 4.33 y (range 2-7) | verified, Lyall et al. 2016, Table 4 |

What this says: one session's mean RT is internally reliable (0.86-0.96), but day to day it is less so (0.6-0.8, and
about 0.6 for simple RT). The gap between internal consistency and retest is state variation across days: fatigue,
arousal, practice. Over four years, with a test of only a handful of trials, about 57% of the variance is stable.
Choice RT is the more trait-like measure (0.76-0.92); simple RT is noisier (0.58-0.67). Hedge et al. note that low
reliability in their tasks "emerged from low variance between individuals rather than high measurement variance"
(verified, abstract).

Share of trial-level variance that is between-person (derived from Deary, Der & Ford 2001, Table 1: between-person
variance over between-person plus mean within-person variance, using the root mean square of the intra-individual
SD): about 0.54 for simple RT and 0.39 for choice RT. From Woods et al. 2015b (between SD 72 ms, intrasubject SD 162
ms): 0.16. So on any single trial, most of the variance is within-person; the person's mean is stable but individual
responses scatter widely around it. **[engineering]** This argues for keeping a per-response noise term in the model
that is larger than the between-person spread, not for widening the trait.

## 3. Age

| Source | Sample | Task | Result | Tag, location |
|---|---|---|---|---|
| Der & Deary 2017 | Twenty-07 cohorts aged 30, 50, 69 | Simple RT | 290 -> 318 -> 354 ms: +10% from 30 to 50, +11% from 50 to 69 (derived) | verified, Table 1 |
| same | same | 4-choice RT | 539 -> 623 -> 729 ms: +16% from 30 to 50, +17% from 50 to 69; about +0.8% per year in log terms (derived) | verified, Table 1 |
| Der & Deary 2006 | UK Health and Lifestyle Survey, N = 7,130 adults | Simple and 4-choice RT | "Simple RT shows little slowing until around 50, whereas choice RT slows throughout the adult age range"; sex differences mainly in choice-RT variability | verified, abstract only (full text not reachable); no slopes taken from it |
| Woods et al. 2015a | N = 1,469, 18-65 | Simple RT | +0.55 ms/year (0.45 in a second sample of 189 aged 18-82); r(age) = 0.24, so about 6% of variance (derived) | verified, Results, Exp. 1-2 |
| Woods et al. 2015b | N = 1,466, 18-65 | Choice RT | +2.80 ms/year (1.91 in a second sample of 178 aged 18-82); r(age) = 0.46, so about 21% of variance (derived); about 0.5% per year of the mean (derived) | verified, Results, Exp. 1-2 |

Within a single age, the spread does not shrink. If anything it grows with age: SRT CV is 0.26 at 30 and 0.32 at 69,
and CRT CV stays at 0.13-0.15 (derived from Der & Deary 2017). So age is a shift in the median, not a source of
most of the spread. In a mixed-age adult population age explains about 6% of simple-RT variance and about 21% of
choice-RT variance (Woods). Woods et al. attribute most simple-RT ageing to slower motor output and most choice-RT
ageing (over 80%) to central processing (verified, abstracts).

The 2006 abstract and the 2017 table disagree a little for simple RT: the abstract says SRT is flat until about 50,
while the 2017 cohorts slow by 10% from 30 to 50. Different waves and samples; I did not resolve it.

## 4. Conversation timing

| Source | Sample | Result | Tag, location |
|---|---|---|---|
| Stivers et al. 2009 (PNAS 106:10587) | 10 languages, 350 polar questions per language from 5-17 interactions each | Overall mode 0 ms; language modes 0 to +200 ms; cross-language median +100 ms and mean +208 ms; language means from +7 ms (Japanese) to +469 ms (Danish), all within about 250 ms of the cross-language mean; distributions unimodal and slightly right-skewed | verified, Results, Fig. 1-2 |
| same | same | Speaker-level analysis: **none**. The design capped any one interaction at 3% of the data and few people appeared in more than one conversation | verified, Data section |
| same | same | Answers faster than non-answers (+132 ms for non-answer), confirmations faster (-207 ms), visible responses faster (-87 ms), questioner gaze faster (-69 ms), information requests slower (+129 ms) | verified, Table 1 |
| Levinson & Torreira 2015 (Front. Psychol. 6:731) | Switchboard, 348 English telephone conversations | Overlaps are 30.1% of floor transfers; between-overlaps have mode 96 ms, median 205 ms, mean 275 ms (duration). No individual-speaker analysis; they note that people accommodate to their partner's gap length (ten Bosch et al. 2004, 2005) | verified, section 5.2 and 5.1 |
| Cavalcanti & Skantze 2025 (Interspeech; arXiv 2505.24736) | Fisher corpus, 10,950 US English telephone calls, 11,684 speakers, each in up to 4 calls; 21,900 speaker-by-call means | Mean of per-speaker-per-call TFO 300 ms, SD 228 ms | verified, section 3.1 |
| same | same | Variance attributable to the dyad: 41.5%; to the speaker: 12.8% (change in conditional R^2) | verified, Table 2 |
| same | same | Sex explains 3.2%, age 1.3%, education ~0 (ANOVA); older and female speakers have slightly shorter TFOs | verified, Table 1 and section 3.2 |

Answer to "is a person's typical gap stable": weakly. The best evidence (Fisher, the only large multi-conversation
speaker dataset I found) says a speaker's gap habit explains about 13% of the variance in their per-call mean gap,
while the pairing explains about 42%. People resemble their current partner more than themselves in another call.
As a rough spread, sqrt(0.128) * 228 ms is about 80 ms of speaker-level SD around a 300 ms mean (derived; this
treats the R^2 share as a variance share, which is approximate). Note that Cavalcanti and Skantze quote the
Danish mean as 489 ms; Stivers et al. give +469 ms. 469 is the primary figure.

The gap is not a reaction time. Speakers plan the reply during the other's turn; Levinson & Torreira cite about 600
ms from picture to naming onset (Indefrey & Levelt 2004) and about 1,500 ms for a simple sentence (Griffin & Bock
2000), both far longer than the ~200 ms gap (secondary, section 6.3). So gap timing is mostly prediction and
coordination, not raw speed.

I found no study correlating a person's lab RT with their conversational gap. Bögels, Casillas & Levinson (2018,
"fast responders show reduced anticipatory processing of the question") study fast and slow responders, but I read
only its title in search results, so its numbers are **unverified**.

## 5. Speech production onset (naming)

| Source | Sample | Task | Mean | Between-person SD | CV | Tag, location |
|---|---|---|---|---|---|---|
| Shao, Roelofs & Meyer 2012, Exp. 1 | 28 undergraduates (24 analysed), British English, 18-22 | Object naming / action naming | 794 / 844 ms | 69 / 90 ms | 0.087 / 0.107 (derived) | verified, Table 1 |
| same, Exp. 2 | 24 undergraduates (20 analysed), 18-38 | Object / action naming | 705 / 782 ms | 69 / 70 ms | 0.098 / 0.090 (derived) | verified, Table 2 |
| Hintz et al. 2020 | 111 Dutch adults, 18-29 | Picture naming onset | 923 ms | 120 ms (log10 SD 0.06, sigma 0.14 derived) | 0.13 | verified, Online-only Table 2 |

Naming-latency spread across young adults is CV 0.09-0.13, a little narrower than choice RT in the same kind of
sample. Retest over a month is 0.69 (Hintz). Picture-naming norms such as MultiPic are item norms, not person norms,
and do not give the spread of participant means; I did not use them. I found no large age-spanning sample for naming
onset; the age effect on naming is **unverified** here.

## 6. Do speed traits generalise across tasks?

| Pair | Correlation of person means | Sample | Tag, location |
|---|---|---|---|
| Simple RT vs 4-choice RT | 0.59 | N = 900, age 56 | verified, Deary, Der & Ford 2001, p. 397 |
| same, corrected for retest reliability (0.67, 0.92) | 0.75 | | derived: 0.59 / sqrt(0.67 * 0.92) |
| Simple RT vs choice RT | 0.49 (second sample 0.48) | N = 1,466, 18-65 | verified, Woods et al. 2015b, Results |
| Object naming vs action naming | 0.744 (Exp. 1), 0.76 (Exp. 2) | N = 24, 20 | verified, Shao et al. 2012, Results and Table 3 |
| Naming vs stop-signal RT | 0.45 (object and action) | N = 20 | verified, Shao et al. 2012, Table 3 |
| Naming vs nonverbal processing speed | visual processing speed correlates with naming onset; auditory processing speed does not; coefficients shown only as a heatmap | N = 112 and N = 169 | verified (direction only), Hintz et al. 2022 CogSci, Fig. 1; Hintz & Momenian 2026, Fig. 1A |
| Lab RT vs conversational gap | **not found** | | |

A shared speed factor clearly exists: choice RT, simple RT and naming all load on it, and the speeded comprehension
tasks cluster with the processing-speed tests (Hintz et al. 2022, verified). But the shared part is partial. Raw
correlations between task means run 0.45-0.76; even corrected for unreliability, simple vs choice RT is about 0.75,
so roughly 40-45% of each task's true between-person variance is task-specific (derived, 1 - 0.75^2). Picture naming
correlated "less strongly" with the other word-production tests and only with visual, not auditory, processing speed
(Hintz et al. 2022 and 2026, verified). For conversational gaps the speaker share is small (13%) and no link to lab
speed has been measured.

## Recommendation

| Item | Recommendation | Basis |
|---|---|---|
| Shape | Lognormal, median 1. A lognormal handles the right skew and the multiplicative effect (a slow person is slow by a ratio, not a fixed number of ms). It slightly underpredicts the population's slow tail. If the game wants that tail, mix in a small slow component, e.g. 5% of NPCs with sigma doubled | Shape: sourced (log-transform practice, near-symmetric log means in Hintz). Tail mixture and its 5%: [engineering] |
| Spread for decision and reply onset | sigma = 0.15 within an age, plausible range 0.10-0.25 | Sourced: choice RT CV 0.13-0.15 within age cohorts (Der & Deary 2017), 0.13 (Woods), sigma 0.16-0.21 (Hintz). Choosing the choice-RT figure over the noisier simple-RT figure (0.12-0.33) is [engineering] |
| Spread for speech onset | Same trait; naming spread (sigma 0.09-0.14) is a bit narrower | Sourced (Shao, Hintz); small samples |
| Age | Shift the median with age; leave sigma unchanged. About +0.5 to +0.8% per year of adulthood for decision onset (median about 1.17 at 50 and 1.37 at 69, relative to 30), and less for simple, motor-dominated responses (about +0.25 to +0.5% per year, with little change before about 50 per Der & Deary 2006). Normalise so the median of the whole adult population, not of 30-year-olds, is 1, or define 1 at a reference age; pick one and write it down | Slopes sourced (Der & Deary 2017, Woods 2015a/b). Normalisation choice: [engineering] |
| Stability | Drawn once and fixed is defensible for the trait; the human data say only about 60-90% of a measured mean is stable across days and about 57% over four years on a short test. Put the rest in fatigue and per-response noise, not in the trait | Sourced (Hedge, Hintz, Lyall). Allocation: [engineering] |
| One multiplier or several | One general factor plus per-domain residuals, not a single multiplier and not fully independent ones. For example m_domain = exp(sigma_domain * (lambda * z_general + sqrt(1 - lambda^2) * z_domain)) with lambda about 0.75 for decision and speech onset, z drawn once per NPC. Domains: manual/decision onset, speech onset | lambda from the disattenuated simple-choice correlation and the 0.74-0.76 naming correlations: sourced estimate; the functional form: [engineering] |
| Turn-transition gaps | Do not drive them mainly from the speed trait. Model the gap as a function of the dialogue (question type, answer versus non-answer, confirmation, gaze) and of the pair (accommodation to the partner), with a small speaker term (about 13% of per-call variance, roughly 80 ms SD around a 300 ms mean). If the speed trait feeds in at all, give it a weak loading | Sourced (Stivers 2009, Cavalcanti & Skantze 2025, Levinson & Torreira 2015). Weak loading: [engineering], no direct evidence |

### What remains uncertain

- No paper formally compares lognormal, gamma and other shapes for person-level means. The shape choice rests on
  skew values and transform practice, not a fit.
- The spread depends on protocol (trials, practice, setting, trimming) by a factor of almost three for simple RT.
  Which protocol best represents "true" everyday speed is a judgment.
- Der & Deary 2006 (the largest age-spanning RT sample, N = 7,130) was read only as an abstract; its slopes are not
  used here. Its full text would firm up the age curve and the shape of age slowing after 50.
- No measured correlation between lab RT or naming latency and a person's conversational gap. The weak-loading
  recommendation for gaps is a judgment.
- Naming spread comes from small student samples (N 20-111, all under 40). Age effects on naming were not found.
- UK Biobank RT means and SDs (very large sample) were not retrieved; only its stability (ICC 0.57) was.

## Sources

- Deary, I. J., Der, G., & Ford, G. (2001). Reaction times and intelligence differences: A population-based cohort
  study. *Intelligence*, 29, 389-399. Full text: https://www.gwern.net/doc/iq/2001-deary.pdf
- Der, G., & Deary, I. J. (2017). The relationship between intelligence and reaction time varies with age: Results
  from three representative narrow-age age cohorts at 30, 50 and 69 years. *Intelligence*, 64, 89-97.
  https://eprints.gla.ac.uk/145462/
- Der, G., & Deary, I. J. (2006). Age and sex differences in reaction time in adulthood: Results from the United
  Kingdom Health and Lifestyle Survey. *Psychology and Aging*, 21, 62-73. Abstract:
  https://www.research.ed.ac.uk/en/publications/age-and-sex-differences-in-reaction-time-in-adulthood-results-fro/
- Hagger-Johnson, G., Deary, I. J., Davies, C. A., Weiss, A., & Batty, G. D. (2014). Reaction time and mortality from
  the major causes of death: The NHANES-III study. *PLoS ONE*, 9(1), e82959. https://eprints.gla.ac.uk/102423/
- Woods, D. L., Wyma, J. M., Yund, E. W., Herron, T. J., & Reed, B. (2015a). Factors influencing the latency of simple
  reaction time. *Frontiers in Human Neuroscience*, 9, 131. https://pmc.ncbi.nlm.nih.gov/articles/PMC4374455
- Woods, D. L., Wyma, J. M., Yund, E. W., Herron, T. J., & Reed, B. (2015b). Age-related slowing of response
  selection and production in a visual choice reaction time task. *Frontiers in Human Neuroscience*, 9, 193.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4407573/
- Hedge, C., Powell, G., & Sumner, P. (2018). The reliability paradox. *Behavior Research Methods*, 50, 1166-1186.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5990556/
- Lyall, D. M., et al. (2016). Cognitive test scores in UK Biobank: Data reduction in 480,416 participants and
  longitudinal stability in 20,346 participants. *PLoS ONE*, 11(4), e0154222.
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0154222
- Hintz, F., Dijkhuis, M., van 't Hoff, V., McQueen, J. M., & Meyer, A. S. (2020). A behavioural dataset for studying
  individual differences in language skills. *Scientific Data*, 7, 429.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7722889/fullTextXML
- Hintz, F., Voeten, C., McQueen, J., et al. (2022). Quantifying the relationships between linguistic experience,
  general cognitive skills and linguistic processing skills. *Proceedings of CogSci* 44.
  https://escholarship.org/uc/item/1dc0w4cn
- Hintz, F., & Momenian, M. (2026). *Memory & Cognition*, 54(6), 2165-2186.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC13461654/
- Shao, Z., Roelofs, A., & Meyer, A. S. (2012). Sources of individual differences in the speed of naming objects and
  actions: The contribution of executive control. *Quarterly Journal of Experimental Psychology*, 65, 1927-1944.
  https://www.mpi.nl/publications/item_1100608
- Stivers, T., et al. (2009). Universals and cultural variation in turn-taking in conversation. *PNAS*, 106,
  10587-10592. https://pmc.ncbi.nlm.nih.gov/articles/PMC2705608/
- Levinson, S. C., & Torreira, F. (2015). Timing in turn-taking and its implications for processing models of
  language. *Frontiers in Psychology*, 6, 731. https://pmc.ncbi.nlm.nih.gov/articles/PMC4464110/
- Cavalcanti, J. C., & Skantze, G. (2025). "Dyadosyncrasy", idiosyncrasy and demographic factors in turn-taking.
  *Interspeech 2025*. https://arxiv.org/abs/2505.24736
