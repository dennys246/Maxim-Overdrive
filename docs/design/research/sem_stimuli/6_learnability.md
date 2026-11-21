# SEM stimulus interface, lens 6: learnability and bio-faithfulness

Research only; nothing edited. Revisions read: Overdrive `phase1/sem-stimulus` at `5ff1b7c`; **Maxim
`origin/main` at `043eab8f` (2026-11-20 20:23 -0700)**, read through `git show` only (no fetch, no working tree).

Tags: **V** primary source or its abstract, read on its page; **S** secondhand or abstract seen only in search
fragments (most web sources here); **M** memory; **D** my derivation.

## 0. In brief

1. **Learnable means:** a cue precedes harm, varies with dose, responds to the agent's own acts, and is
   contingent, not merely paired (§1).
2. **A leak blocks learning.** A perfect privileged predictor ("flammable") takes the prediction error, so the
   physical cue beside it is never learned (Kamin blocking) (§2).
3. **Leaks have shapes beyond labels:** identity-carrying sensors, readings through walls, a sensor set that
   changes with hazards, outcome text, affordance names, units an LLM reads as meaning. Each gets a test (§2.3).
4. **An LLM-primary NPC's fire behaviour measures its prior** (Maxim Exp 38/40). Claims need substrate-side
   measures, physical counter-priors (no inverted rules) or between-NPC dose–response (§3).
5. **One interface at every developmental stage;** curriculum is scenario order (§4).
6. **Per-NPC receptor gain is Maxim's, real, and a measurement tool** (§5). §6 lists 16 rules.

## 1. What makes a stimulus stream learnable

### 1.1 A cue before harm

- **The agent must be able to act between cue and damage.** Radiant pain precedes a second-degree burn by 3–6×
  (NOAA/FEMA, **V** in `6_biofaithful_sem.md` §1.1); lessons 4 and 5.
- **Learning tracks prediction error** (**S**, Schultz, Dayan & Montague 1997, *Science* 275:1593). With no
  earlier cue, the only predictor is contact itself, too late to avoid (**D**).

### 1.2 Contingency, not pairing

- Rescorla (1968, *J Comp Physiol Psychol* 66:1): when shock was equally likely with or without the tone, the tone
  produced no conditioned suppression, although pairings occurred. Contingency means P(US | CS) against
  P(US | no CS) (**S**).
- **Consequence (D):** a cue that fires everywhere (smoke smell that never fades, warmth pinned at maximum)
  predicts nothing despite pairing. A cue present *only* for the hazard is too perfect: §2.2's identity leak.
- **Adaptation keeps contingency alive** (`6b` MP-6; time research §8.3). It is transduction, so Maxim's
  (lesson 24); the world never pre-adapts, pre-thresholds or pre-normalizes.

### 1.3 Graded, not binary

- Error-driven updates scale with the error; a boolean gives one bit and thresholds an entity mean (D25, N2)
  (**D**). A gradient lets the agent find a comfort band (curriculum stage 1), and behaviour that scales with
  intensity is evidence the stimulus drives it (§3.3).

### 1.4 Contingent on the agent's own acts

- **Self-produced change is what calibrates perception.** Held & Hein (1963, *J Comp Physiol Psychol* 56:872):
  kittens that moved themselves developed visually guided paw placement. Yoked kittens, carried through the
  same visual stream, did not (**S**).
- **Control is what is learned, not helplessness.** "Passivity in response to shock is not learned. It is the
  default, unlearned response to prolonged aversive events." It "can be overcome by learning control", with
  medial prefrontal cortex detecting control (**V**, Maier & Seligman 2016, *Psychol Rev* 123:349, abstract).
- **Consequence (D):** stepping back, turning away or dousing must change the stimulus in the next pull
  (lesson 23); later effects need credit by invocation id (lesson 6, OD-A16). An unrelievable hazard teaches
  the default, passivity. A stimulus that ignores the agent's own motion (no change when the head turns) leaves
  the efference copy nothing to match.

### 1.5 Noise, and where it belongs

- **Noise can help a receptor.** Added noise improved crayfish mechanoreceptors' signal transfer by stochastic
  resonance, the first biological demonstration (**S**, Douglass et al. 1993, *Nature* 365:337).
- **Variability stops memorization.** Standard RL agents overfit, and common stochasticity tricks do not
  reliably prevent or detect it (paraphrase) (**S**, Zhang et al. 2018, arXiv:1804.06893). Domain randomization
  works by making the real world "just another variation" (**S**, Tobin et al. 2017, arXiv:1703.06907).
- **The split (D):** the world's variability is physical (flicker, draughts, material scatter within cited
  ranges), seeded for replay. Transduction noise is Maxim's (leak test 2). The world never delivers a cleaned
  quantity (a mean over cells the receptor doesn't occupy, a smoothing it doesn't integrate): that is an
  omniscient reduction in time. Noise is no leak fix: a jittered "flammable" is still a constant.

## 2. What leaks privileged information

### 2.1 Why leaks matter more than "unearned knowledge"

- **Definition:** "information about the data mining target that should not be legitimately available to mine
  from." The cure is "learn-predict separation" (**S**, Kaufman, Rosset & Perlich 2012, *ACM TKDD* 6(4)).
- **Shortcuts:** decision rules that pass benchmarks but fail under harder conditions, also seen in comparative
  psychology, education and linguistics (**V**, Geirhos et al. 2020, *Nat Mach Intell*
  2:665, abstract).
- **Blocking (the mechanism that makes leaks costly).** After A→US training, a new cue B added to A gets little
  conditioning (**S**, Kamin 1969). Under Rescorla–Wagner the leaked flag is cue A: it predicts burns
  perfectly, the error is used up, and radiant warmth (cue B) stays unlearned (**D**). Maxim's own roadmap has
  compound-cue competition (ΣV) **OPEN** for NAc and the cerebellum (`bio_faithful_roadmap.md`). A faithful learner
  will block, so the interface mustn't rely on the substrate failing to.
- **Privileged information is legitimate only on the teacher's side.** Vapnik's LUPI uses it during training only
  (**S**, Vashist & Vapnik 2009, *Neural Netw* 22:544). In the asymmetric actor–critic, the critic sees full
  state and the actor sees only images (**S**, Pinto et al. 2017, arXiv:1710.06542). **Our analogue (D):** lab
  instruments may feed tests, graders and analysers, never an NPC's input or its reward.

### 2.2 The leak taxonomy, with an Overdrive or Maxim instance of each

| Shape | Instance | Source |
|---|---|---|
| Material constant as a sensor | "flammable", "porous"; flash point, φ | lesson 24; `6_biofaithful_sem.md` §1.3 |
| Boolean over an entity | "soaked: yes" | N2, D25 |
| Omniscient reduction | `RegionInstrument` `temperature_max` from anywhere; 6.0 widening it to see cardboard inside a closed crate | `fire_solid` review B1 |
| Identity-carrying stimulus | `flame_luminance`: fires only for fire, through walls. A lamp should excite it too | `fire_model` review S3; delta1 NS5 |
| Outcome text | an act refused "because it won't burn"; descriptions telegraphing the twist | `6_biofaithful_sem.md` §6; Exp 38 §7 guard 1 |
| Affordance names | `warmth_beta_SAFE` "hand the answer to the LLM" | Maxim Exp 44 apparatus fix 1 |
| Harness text | `respond: NOT AVAILABLE` in every prompt moved Exp 38's turn bins; Sonnet's interaction withdrawn | Exp 38 re-assessment (#1260, #1301) |
| Sensor-set leak | the read-all tool lists every sensor on an Entity, so a sensor that exists only near hazards is a hazard detector | Maxim `tool_bridge.py` via `fire_solid` review B1 (**D** for the generalization) |
| Name/meaning drift | same name, new meaning: before/after replays can't be told apart | `fire_solid` review B1, F1 |
| Timing | LLM wall-time leaking into outcomes; step-count-dependent updates | time research §8.2 |
| Clock | "the NPC should never receive the world clock as such" | time research §8.4, **in tension with lesson 11** ("agents need world time, injected"). Not settled here |
| Units as meaning (LLM only) | "skin 47 °C" is a number to a substrate, but an LLM knows 47 °C hurts | **D**; Maxim's motor-only prompt carries "English-leak sentinels" (`grounded_language_acquisition.md`) |

### 2.3 How to test for leaks

Lesson 24's two tests, as corrected by `fire_model` review S4, decide **ownership**. Tissue counts as world:

- **T1 (instrument).** Could an instrument at that spot measure it without a nervous system? If so, it is the
  world's.
- **T2 (transduction).** Is it a threshold, gain, adaptation or latency? If so, it is the receptor's.

They don't catch identity, occlusion or set leaks. I propose (**D**) adding eight tests that run in CI:

- **T3, source swap.** Replace the source with a different one that has the same physical emission (a lamp of
  equal luminance and flicker band, a hot plate of equal flux). The stimulus at the receptor must be equal
  within tolerance.
- **T4, occlusion.** Put the hazard behind an opaque wall or inside a closed container. Every reading at the
  NPC must be unchanged until something physical crosses: conducted heat, gas, sound.
- **T5, counterfactual material.** Two materials, identical in appearance and in the reduced fields, differing
  only in a combustion constant. Before any thermal event, the two NPC stimulus streams must be byte-identical.
  This generalizes Exp 38's hearth to physics.
- **T6, probe.** Fit a simple decoder from pre-event stimulus frames to quantities no receptor could know:
  material constants beyond appearance, state behind occluders, designer labels. Above-chance decoding is a
  leak (Kaufman's learn-predict separation). Decoding *future heat* from present flux is **not** a leak. It is
  §1.1's signal, and the probe's targets must say so.
- **T7, text denylist.** Run Exp 38's telegraph test over every string an NPC can see: entity names,
  descriptions, affordance names and docstrings, refusal and error text, and harness lines.
- **T8, sensor-set invariance.** The set of sensors on an NPC's entities, their names, units and declared
  ranges must not depend on whether a hazard exists in the scene.
- **T9, Δt and wall-time invariance.** The same world history chopped into different steps, with different LLM
  latencies, must give the same stimulus stream (time research §8.2).
- **T10, name stability.** A changed meaning gets a new name (F1). Pin `QUANTITIES` and the NPC sensor set with
  a test (`fire_solid` review N3).

Each test must first be shown red on a planted leak.

## 3. LLM priors confound claims of learning

### 3.1 The evidence

- **Models recite.** On counterfactual variants of 11 tasks, model performance is "nontrivial but consistently
  and substantially" lower than on the defaults (**V**, Wu et al. 2024, NAACL, arXiv:2307.02477, abstract).
- **Maxim Exp 37/38/40.** With a hearth whose `warm_self` hurts, carried substrate did not override
  `fire→warm` at GPT-4o, DeepSeek-V3, R1 or Qwen2.5-32B (Sonnet's interaction withdrawn, #1301). R1's substrate
  was load-bearing but **amplified the prior** (two valid ablations, per #889).
- **Without the LLM, the substrate learns:** Exp 42 graduated safe-vs-harm discrimination substrate-primary
  (flip +0.96), saturated so blind to moderate regressions (T1-6). Exp 39 stalled on fixation; Exp 41 VOID.
- **The substrate steers an LLM a little:** Exp 44's matched counterfactual flipped 15/100 decisions toward
  safe, exploratory, on colour-twin flames made leak-free by renaming.

### 3.2 What follows for the interface (D)

- The interface can't remove a prior, only avoid feeding it (T7, units-as-meaning) and make every claim
  measurable past it.
- What the LLM sees is a separate channel: real units are right for the substrate (`6b` §3.2), but as prose
  they carry meaning. A design should say per channel what the LLM sees.

### 3.3 Three ways to measure past the prior

1. **Substrate-side measures.** NAc link valence, cluster fear, first contact in a resumed session,
   ablation reversion. Exp 38's verdict tree is the model: a pre-registered tree, frozen, with a matched
   consistent control and an "avoids both" void branch for general caution.
2. **Physical counter-priors (D).** Here a counter-prior must come from physics, not an inverted affordance
   (lesson 22). Cases: near-invisible methanol or hydrogen flames (**M**; check the flux too); metal below
   visible glow (Draper point ~525 °C, **M**) that burns on contact; a lamp or screen showing flame (T3's
   pair); later, a fuel that looks like water (Phase 2 vapour).
3. **Between-NPC dose–response (D, new).** Every NPC shares the prior. If avoidance tracks *that NPC's own*
   receptor gain (§5), the stimulus is doing the work. Pre-register it in a Maxim harness; game runs never go
   on Maxim's ledger.

**Also: pressure must be game-native** (D1, `6_biofaithful_sem.md` §5). There are no instructed fire lessons.

## 4. Developmental ordering

- **The agent's order is not the physics ladder's.** It runs: heat source, contact, process, control,
  starting, anticipation, with observation throughout (`6_biofaithful_sem.md` §5; Pruetz & LaDuke 2010, **V**
  there; Fessler 2006, **S** there).
- **Limited input can help development.** Turkewitz & Kenny (1982, *Dev Psychobiol*) argue that sensory
  limitations aid perceptual organization, and that prenatal senses come online sequentially (**S**).
- **But starting small is not reliably necessary.** Rohde & Plaut (1999, *Cognition* 72:67) failed to
  reproduce Elman's starting-small advantage. Restrictions "hinder acquisition" as the languages become more
  realistic (**S**).
- **Consequence (D):** curriculum is **scenario order**, pre-registered as a factor; never a stage-gated
  interface (a novice danger flag blocks the real cue, §2.1). Senses come online in order only where a body
  lacks them (an infant variant), in Maxim's body YAML.
- **Social learning is later and selective:** snakes, not flowers (Cook & Mineka 1989, **S**); a calm model
  beforehand blocks it (Mineka & Cook 1986, **S**). Phase 5 must deliver *observed behaviour* (a recoil seen and
  heard), never a transmitted label (**D**).

## 5. Individual differences: receptor gain and threshold per NPC

- **Receptors vary between people, by genotype.**
  - OR7D4 genotype changed androstenone thresholds in 391 people. Heterozygotes were less sensitive, and other
    odours were unaffected (**S**, Keller et al. 2007, *Nature* 449:468). About 30% of people can't detect it
    (**S**, Nature news).
  - Twin heritability of pain traits ranges from ~0 to 68% across measures (**S**, review via search).
  - Women's heat-pain thresholds are lower (**S**, Rolke et al. 2006, *Pain* 123:231). I did not retrieve the
    numerical SD.
  - Processing speed is modelled as lognormal, drawn once, with σ ≈ 0.15 and a general factor plus per-domain
    residuals (repo `speed/individual_differences.md`, its tags).
- **Where it lives (D, from T2).** Per-NPC gain, threshold, adaptation and latency are Maxim's receptor
  parameters, drawn once under a recorded seed. Skin thickness, clothing and size are tissue: the world's. A
  world quantity that changes with an NPC's sensitivity means transduction leaked into physics.
- **Why it helps (D):** no lockstep NPCs; §3.3's dose–response measure; no single "correct" threshold for a
  designer to encode.
- **Unknown:** whether the planned `ReceptorSpec.gain` and `NociceptorSpec` threshold (`6b` §2) take a
  per-instance draw. A question for GL2b and GL3.

## 6. Rules and tests the interface design should carry

Each rule names the failure it prevents and the test that holds it.

| # | Rule | Failure prevented | Test |
|---|---|---|---|
| R1 | Every hazard delivers a physical cue at the receptor before damage, with lead time measured per hazard | Unlearnable hazard; the agent learns passivity (lesson 5, Maier & Seligman) | A per-hazard scenario asserting cue onset precedes the damage integral's onset, with the lead in seconds recorded |
| R2 | The world stops at the stimulus at the receptor's location, in physical units. Tissue is world; transduction is Maxim's | A second heat path; the world writing pain or drives | T1, T2; a grep gate showing no drive or pain writes from the world |
| R3 | No material constant, label or designer category is an NPC input | Unearned knowledge that **blocks** learning of the real cue (Kamin) | T5, T6 |
| R4 | Continuous values only. No booleans or entity-mean thresholds | D25; one-bit prediction error | A schema check rejecting bool and enum NPC sensors |
| R5 | Stimuli are generic in their source. Luminance, flux and concentration don't know what emitted them | Identity leak; fear through walls; never fearing a lamp's heat | T3 |
| R6 | Every value respects occlusion and position. No region-wide max or mean reaches an NPC | Omniscient reduction (`fire_solid` B1) | T4; a builder split so lab instruments can't be put on an NPC entity |
| R7 | The NPC sensor set, names, units and ranges are fixed per body, independent of the scene | Sensor existence as a hazard detector | T8, T10 |
| R8 | An act changes the next pull. Delayed effects carry the invocation id | Efference copy with nothing to match; acts look inert (lessons 6, 23) | The existing ownership test, plus a per-act receipt test |
| R9 | Fruitless acts succeed as acts and fail in the world. No reason text | Outcome text teaching the rule | T7 over error and refusal paths |
| R10 | Every NPC-visible string passes the telegraph denylist | The prior and the answer delivered in words (Exp 38, Exp 44) | T7 |
| R11 | Physical variability is seeded and the same everywhere. The world never denoises, pre-adapts or pre-normalizes | Memorized worlds; adaptation done twice | A replay byte-equality test; a check of the reduction kernels against receptor geometry |
| R12 | The stream doesn't depend on step size or LLM wall time | Behaviour changing with the speed dial; latency leaks | T9 |
| R13 | Lab instruments feed tests and graders only (the LUPI or critic side) | A privileged teacher becoming the student's input | A type or builder boundary, with a failing test that hands an instrument to an NPC |
| R14 | Per-NPC receptor parameters are drawn once, seeded and recorded on Maxim's side. Body physics varies on the world side | Lockstep NPCs; transduction leaking into physics | A replay test; a test that world fields don't change with an NPC's gain |
| R15 | No learning claim from an LLM-primary arm alone. Claims need substrate-side measures, a physical counter-prior or between-NPC dose–response, pre-registered under Maxim's process and under game-native pressure | Citing the LLM's prior as learning (`fire_model` review S8) | The design's claim discipline section; review gate |
| R16 | The interface is identical across curriculum stages. Stage lives in scenarios | Beginner sensors that leak and block | T8 across the scenario catalogue |

**Open (not settled here):** the world-clock tension (lesson 11 vs time research §8.4); what the LLM is shown
of numeric stimuli; whether Maxim's substrate blocks while ΣV is OPEN; whether GL2b/GL3 receptor specs take
per-instance draws (questions to Maxim plans, not new asks).
