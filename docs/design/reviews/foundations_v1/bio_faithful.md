# Bio-faithful integration: review of `docs/design/npcs_and_sem.md` (part 2) and the two Maxim drafts (4f7a754)

- **Lens:** Bio-faithful integration (`docs/code_review.md`), always on for design reviews. It also asks whether the
  game's evidence should push back on Maxim, and whether the drafts' arguments against Maxim decisions are fair.
- **Design commit:** 4f7a754 (`phase1/design-v2`).
- **Date:** 2026-11-16.
- **Counts:** 2 BLOCKER, 7 SHOULD-FIX, 6 NIT.
- **Read:** `npcs_and_sem.md` (all), `boundaries.md` v2 §4.3, §4.4, §7, `maxim_upstream/world_clock_release_DRAFT.md`,
  `maxim_upstream/sem_breaking_change_plan_DRAFT.md`, roadmap Phase 3, `research/time/` (neuroscience §3, §5, §6;
  engine_mapping §2.3, §3; skeptic §2–§5), the lessons doc (standards worktree), and the v1 review
  `reviews/boundaries/bio_faithful.md`.
- **Maxim read (read-only), `main` at 4b773ef8:** `embodiment/sem.py` (drive specs, `CouplingSpec`),
  `embodiment/tool_bridge.py::ModulatorAffordanceTool.execute`, `runtime/tool_dispatch.py` (the D53 valence block),
  `hardware/reachy/motor_backend.py::ReachyOrientMotorBackend.execute`, `_data/components/bodies/base_humanoid.yaml`,
  `time/oscillator.py`, `docs/time.md`, `docs/plans/experience_clock_decay.md` §(g), `docs/agents/embodiment.md`,
  `docs/energy.md`, and Maxim's `CLAUDE.md` two-tier rule. Nothing in Maxim was modified.
- **Citations checked on the web** where marked "verified" below; the rest are marked "from memory" and need the
  same treatment before they enter `data/`.

## Verdict

The architecture of time is right, and at the right Marr level: three clocks, no time field reaching cognition,
Δt-invariant body processes, modelled thought cost in world time with dilation, and estimators rather than a second
clock. It answers the owner's tenets on dial-independence and coarse perception better than any earlier document,
and the corrections to v2 (§12.3: `coupled_to`, not `modulated_by`; the cerebellum observes at settle) hold against
Maxim's code.

Two mechanisms are wrong in substance, not in detail, and both are the ones the owner's tenets lean on most:

1. **The "cognitive reserve"** (§2.3, §4.6, SEM plan S7) is a depleting-resource model, the shape of the ego-depletion
   account the document itself cites as failed. Its name is an established and unrelated construct, and its cited
   evidence (Wiehler 2022) describes an accumulation with a different behavioural consequence. As written it would go
   to Maxim with a "Bio basis" line it hasn't earned.
2. **Conversational onset** (§4.2, §5) reads Levinson & Torreira's production latency (≥600 ms) as the time before a
   reply starts. People hide that latency by planning during the other's turn, and answer after a gap of about
   200 ms. Modelled from the end of the turn, the NPC's replies would come 3–7 times late, in the band listeners read
   as reluctance. That breaks the "dynamic conversation in hybrid mode" tenet at its foundation.

The rest are fixable in place: mode (a) doesn't emit Maxim's D53 valence, sleep is modelled as a slower substrate
instead of a raised arousal threshold, "instrument" means two different things, the [now] interim gives NPCs no time
sense at all rather than a coarse one, and the model's capability (set by the player's hardware) is an unnamed way the
machine decides NPC competence.

---

## BLOCKER

### BF2-1. The cognitive reserve is a resource-depletion model under a borrowed name, and its evidence says otherwise

**Location:** `npcs_and_sem.md` §2.3 ("A cognitive reserve is a new body sensor that falls while the NPC deliberates"),
§4.6 ("The loop"), §12.1 Q5; `sem_breaking_change_plan_DRAFT.md` S7 ("expose a body sensor that falls while the agent
deliberates (a cognitive reserve)", "Bio basis"); roadmap C5.

**Four problems, each enough on its own:**

1. **The name is taken.** "Cognitive reserve" is an established construct (Stern 2002, *J Int Neuropsychol Soc*,
   from memory): a long-term trait (education, occupation, IQ) that buffers clinical decline against brain pathology.
   It doesn't deplete in an afternoon. Maxim's `CLAUDE.md` says "Bio-inspired naming … does NOT count as behavioral
   validation", and a name that already means something else in the literature does worse: it imports an authority
   it doesn't have.
2. **The shape is the model the document rejects.** §4.6 cites Hagger 2016 against "willpower as a resource", then
   builds a reserve that thinking drains and rest refills. That is the strength (resource) model of self-control,
   which is what Hagger 2016 and Vohs et al. 2021 (*Psychol Sci*, 36 sites, N ≈ 3,500, d ≈ 0.06; from memory) failed
   to replicate. The live accounts of cognitive fatigue are accumulation (a cost signal or a metabolite rises with
   control demand; Wiehler 2022) and opportunity cost (Kurzban et al. 2013, *Behav Brain Sci*, from memory). Both rise
   with work. Neither is a tank that empties.
3. **The cited evidence predicts a different behaviour.** Wiehler et al. 2022 (*Curr Biol* 32:3564, verified):
   about 40 participants split between high- and low-demand groups, 6.25 h of work, MRS glutamate up in lateral PFC
   (about 8% in press summaries) and not in V1. The behavioural marker was **choice**: the high-demand group shifted
   toward immediate, low-effort options, with smaller pupil dilation (the same group's Blain et al. 2016 *PNAS*, from
   memory). §4.6's loop has fatigue "lengthen `D_onset`", which is slower thought. The evidence says *less* thought:
   a fatigued NPC should deliberate less often and pick cheaper options, handing more to the substrate. Slower
   responses with time on task are also real (vigilance decrement, Mackworth; Boksem et al. 2005, from memory), so both
   can be modulators, but the one the cited paper supports is missing.
4. **Maxim's machinery can't express it as described, and the target drive doesn't exist.**
   - `CouplingSpec` is `{sensor, below, multiplier}` (`sem.py::CouplingSpec`): a step function that multiplies drift
     while the source is under a threshold. Wiehler's effect is graded with demand. A reserve with one threshold gives
     a binary "tired at 2×" switch, and the deliberation load itself never enters fatigue, only a second variable
     downstream of it. The S7 claim "No field changes" holds only for the binary version.
   - A step coupling makes the coupled drive piecewise in time. §2.1's step-size invariance test passes only if the
     source's threshold crossing is reconstructed in closed form before the coupled drive is integrated. The doc
     doesn't say so, and a naive evaluator applying the multiplier per step fails the test at 50-tick steps.
   - `base_humanoid.yaml` has `stamina` (physical, relieved by `rest`), and no `fatigue` drive. "Fatigue's existing
     `coupled_to`" (§2.3) refers to a docstring example, not a declared drive. Coupling deliberation into `stamina`
     would make a marathon slow thinking and a chess game slow running at the same rate. Mental and physical fatigue
     are distinct but interact (Marcora et al. 2009, *J Appl Physiol*: mental fatigue cut time to exhaustion; from
     memory), so this is a modelling decision to make explicitly, not to inherit.

**Failure scenario:** S7 goes to Maxim's plan review with "Bio basis: … Wiehler 2022". Maxim's bio-faithful lens
finds the depletion shape, the borrowed name and the mismatch with the cited behaviour, and either refuses it or,
worse, accepts it; then T2 tests "latency modulated by fatigue" and earns a mechanism whose state variable has no
biological referent.

**Fix:**
- Rename and reshape: a **mental-fatigue drive** that rises (entropic, `drift_direction: up`) in proportion to
  deliberation load in world time (time in P1/Pn × a per-kind control-demand weight from `data/`), recovered by rest
  and sleep. Drop the reserve as a separate variable. Mark it `[engineering]` explicitly in §2.3 and S7, and put the
  bio basis as "consistent with" accumulation accounts, not "is".
- Its consequences, both T2 arms candidates: (a) a raised cost of starting a thought, so the NPC deliberates less and
  leans on the substrate (the Wiehler/Kurzban effect); (b) longer, more variable onset with time on task (vigilance).
- Decide stamina vs mental fatigue (§12.1 Q5 already gestures at it: "one reserve, or one per kind of effort").
  Recommend two drives, with an optional, marked cross-coupling.
- Tell Maxim the truth about `CouplingSpec`: graded, load-driven accumulation isn't expressible additively. The
  additive path is a drive that the thought gate advances by load (an internal writer, like `world_set_axis` for
  the world), not `coupled_to`. If that doesn't fit, it's a breaking-batch candidate with this evidence. (This is a
  new pushback; see "Pushbacks to Maxim".)

### BF2-2. Reply onset models production latency as the gap, which makes every NPC answer late and sound reluctant

**Location:** §4.2 P1 row ("planning a spoken reply begins after ~0.6–1.5 s (Levinson & Torreira 2015)"), §5 split
table, §4.2 "Speech length is not part of the deadline", engine_mapping.md §3.1.

**What the literature says (verified):**
- Levinson & Torreira 2015 (*Front Psychol* 6:731): gaps between turns are about 200 ms, while production latencies
  are over 600 ms (single word, Indefrey & Levelt) and longer for clauses. So responders **plan content in overlap
  with the incoming turn** and launch articulation on turn-final cues (their two-stage model). The 0.6–1.5 s is not
  "when planning begins"; it is how long planning takes, and most of it is hidden. (The 1.5 s upper figure didn't
  turn up in my search; treat it as unverified.)
- Stivers et al. 2009 (*PNAS* 106:10587, verified): ten languages, mode between 0 and 200 ms, language means from
  about 7 ms (Japanese) to about 470 ms (Danish), all within about 250 ms of the cross-language mean. Measured on
  answers to polar questions, so "~200 ms" is the mode for that turn type, not every reply.
- Kendrick & Torreira 2015 (*Discourse Processes* 52:255, verified): at gaps of about 700 ms and over, dispreferred
  responses (refusals, disagreements) outnumber preferred ones. A long gap is itself a signal.
- Torreira, Bögels & Levinson 2015 (verified): answers preceded by an audible in-breath have a modal latency of about
  576 ms against about 100 ms without one.

**Failure scenario:** `timing.yaml` ships `reply: 600_000..1_500_000 µs` [now], counted from the end of the player's
turn. Every NPC reply arrives in or near the dispreferred band. Players read every NPC as hesitant or evasive, and the
"dynamic conversation" goal fails in exactly the mode the owner asked to get right, with the tick, the sub-tick
stamping and the token timing all correct.

**Fix:**
- Model the **gap**, not the production latency: `D_gap(kind)` from the end of the interlocutor's turn, mode about
  200 ms with a right-skewed tail, per turn type (polar answer, open reply, dispreferred). The LLM's real latency is
  absorbed by dilation, which is what dilation is for.
- **Content-dependent landing is possible, and §4.2 says it isn't.** Under the dilate policy the host already holds
  the world at the segment's earliest landing until the result exists. So it can hold at `T + D_min`, read the
  content, and then set the landing from it: a refusal or a hard answer lands later, with an "um" or an in-breath in
  the gap. That is still a pure function of the run, and independent of the dial. "A deadline that depended on
  [content] would depend on wall time" is true only for the abandon policy.
- Rewrite the bio-basis cell to say what Levinson & Torreira say, and make the gap literature the source of `D_gap`.
- Keep 0.6–2 s for non-conversational choices and plans, where nothing hides the latency (still *to verify*).

---

## SHOULD-FIX

### BF2-3. Mode (a) doesn't emit Maxim's D53 valence, so an applied action that changed nothing books POSITIVE

**Location:** §6.1 step 4 ("`success` and `error` from the receipt; metadata from the measured effect"), step 3
("the wait is bounded in world ticks").

**What Maxim does** (`runtime/tool_dispatch.py`, D53 block): `success=False` → NEGATIVE; else the tool's own
`outcome_valence` if present; else **POSITIVE** ("the historical contract every existing tool relies on"). D53 exists
because "a refused motion booked a full POSITIVE causal link". The Reachy precedent the design cites
(`ReachyOrientMotorBackend.execute`) emits `outcome_valence: "neutral"` when the readback is unknown or nothing moved,
and puts drive deltas in `measured_drive_transitions`, which is the key Maxim's credit reads ("metadata alone is
structurally invisible to the learning chain").

**Failure scenario:** an NPC strikes a steel door; the receipt is `applied`, the door takes no damage. §6.1 returns
`success=True` with `destroyed_volume_m3: 0` and no valence, so NAc books POSITIVE and the NPC learns striking steel
doors works. And at the wait bound, the design doesn't say what is returned; `success=False` would book NEGATIVE for a
world that was merely slow.

**Fix:** state in §6.1 that the adapter always self-reports, as Reachy does: `neutral` when the measured effect is nil
or unverifiable (including wait-bound expiry), `None` (positive) only on a measured effect, and drive deltas through
`measured_drive_transitions`. Also say what the cerebellum is meant to learn in mode (a). Biologically it predicts
immediate reafference (hundreds of ms), and NAc's temporal window carries consequences that take seconds. So one
settle frame is the right horizon for the cerebellum, but entity sensors dominated by an ongoing process (a crate in
a fire) will train it on the world's drift, not the action's effect (v1 BF-1's absolute-value point). Restrict the
in-call sensors to those the affordance declares it affects, as Maxim already does for interoceptive drives.

### BF2-4. Citation corrections (the checks the brief asked for)

| Claim in the docs | Status | Correction |
|---|---|---|
| Stivers et al. 2009, gaps ~200 ms | **verified, narrow it** | Mode 0–200 ms; language means ~7 ms (Japanese) to ~470 ms (Danish); within ±250 ms of the cross-language mean; polar question–answer pairs only |
| Levinson & Torreira 2015, "planning a spoken reply begins after ~0.6–1.5 s" | **misread** | Production latency >600 ms is planned in overlap; the gap is ~200 ms (BF2-2). 1.5 s not found |
| Clark & Fox Tree 2002, fillers | **verified, supports the design** | *uh* and *um* are planned words announcing an anticipated minor or major delay (*Cognition* 84:73). Disputed by later corpus work (O'Connell & Kowal 2005, from memory) |
| Hagger et al. 2016, "ego depletion (willpower as blood glucose) failed" | **conflated** | The RRR tested the depletion effect (sequential-task paradigm), not glucose: 23 labs, N = 2,141, d = 0.04 [−0.07, 0.15] (verified). The glucose account was challenged separately (Kurzban 2010; Vadillo et al. 2016, from memory). Add Vohs et al. 2021 |
| Wiehler et al. 2022 | **verified, mis-applied** | ~40 people between groups, 6.25 h, lPFC glutamate up; the behaviour is a shift to low-effort, immediate choices (BF2-1) |
| Brain ~20 W, thought adds a few percent | **right** (from memory) | Raichle & Gusnard 2002 (*PNAS*): task-evoked increases are under ~5% of baseline. Cite it |
| Speech rate ~2–3 words/s, ~150 wpm | **right** (from memory) | Conversational English ~150–190 wpm, ~4–6 syllables/s; ~1.3 tokens/word is a tokenizer property, check it against the model actually used |
| Spinal reflex 25–50 ms (§9) | **right number, wrong reflex** | That is the monosynaptic stretch reflex (posture). The hazard reflex is the nociceptive withdrawal reflex: RIII above ~90 ms by convention, RII 50–90 ms (Thorell et al. 2023, verified). Heat pain via Aδ/C fibres is slower again (from memory: hundreds of ms to over 1 s). So withdrawal from a burn fits one 100 ms tick; acoustic startle (~30–50 ms EMG onset, from memory) is the one below a tick. §9's argument for sub-tick reflexes should use startle, not the stretch reflex |
| Roseboom et al. 2019 under "minutes to hours: retrospective duration" (§3.2) | **wrong scale** | Clips were 1–64 s (verified), and reports were made right after each clip. The minutes-to-hours retrospective row belongs to Ornstein 1969 and Block & Zakay 1997; Roseboom is a candidate mechanism extrapolated upward, and §3.2 should say so |
| Czeisler 1999, 24.18 ± 0.15 h | right (neuroscience.md) | Write it as SD, not ±. 0.18 h/day ≈ 11 min/day checks out |
| Zeitzer 2000, half-max ~100 lux | right, add the condition | Half-max for a ~6.5 h exposure; individual sensitivity varies over an order of magnitude (Phillips et al. 2019 *PNAS*, from memory). See BF2-13 |
| Process S τ 18.2 h / 4.2 h | right | Daan, Beersma & Borbély 1984 |

### BF2-5. Sleep is modelled as a slower substrate, but biology sleeps by raising arousal thresholds

**Location:** §2.3 "Sleep and the substrate rate" ("runs its substrate at low rates … That is biology"), §4.5.

The sleeping brain isn't running slowly. It gates sensory input and raises arousal thresholds, while salient stimuli
still get through: one's own name, a baby's cry (Oswald et al. 1960; Portas et al. 2000, from memory). Whether a
sleeper wakes to a smoke alarm depends on the stimulus, the sleep stage and the person (children often don't wake;
Bruck 1999, from memory), not on a sampling rate. Lowering the step rate also violates §2.1's own rule ("the host
never lowers an NPC's substrate rate … because that changes its reflexes"); here it's the state that lowers it, but
the reaction latency it produces is still set by a performance choice.

**Failure scenario:** a fire starts in a dormitory. The time an NPC takes to wake and flee is set by the sleep-mode
step rate, which was picked so the "sleep" preset reaches 20×, and it changes whenever that rate is retuned for
performance.

**Fix:** model sleep as gating: per-channel arousal thresholds by sleep stage in `data/`, with a salient-stimulus
bypass, and keep the wake path's detection at the full rate. Infrequent drive drift during sleep is fine, since it's
closed-form. The fast-forward benefit survives, because a sleeping NPC still doesn't deliberate. Label "low rates" as
`[engineering]`, and say that the 20× sleep preset is a performance property, not biology.

### BF2-6. "Instrument" means two things, and S8 would bake omniscience-with-a-flag into Maxim

**Location:** §7.1, `boundaries.md` §4.4, SEM plan S8.

§7.1 uses "instrument" both for today's relabelled region sensors (a crate's interior maximum, to anyone, anywhere)
and for in-world devices ("a thermometer, a terminal, a clock face"). They are different under receptor-first. A
thermometer reads its own temperature at its own position, with its own time constant, and the NPC reads its display
through vision (§3.1 says exactly this of clocks). A region sensor rendered "while the agent is using one" is still
global truth, behind a usage flag.

**Failure scenario:** an NPC picks up a "thermometer" and reads the crate's interior maximum without the probe being
inside the crate, instantly. The receptor-first rule is satisfied on paper (a declared `instrument` kind) and violated
in fact.

**Fix:** define an instrument as an in-world object with a position, its own physical reduction (a probe, a lag), and
a display that is perceived like any other percept. Keep the omniscient region sensors as test and lab instruments,
which are never an NPC's input. Then re-check S8: if instruments are world objects, Maxim may need nothing beyond the
existing `modality:` on a visual percept, and the "prompts render instruments only while using one" rule moves to the
world, where "using one" is a fact (in hand, in sight). Shrinking our own ask is the honest outcome.

### BF2-7. The [now] interim gives NPCs no sense of time, not a coarse one, and the oscillator's calendar scales are unlisted oracles

**Location:** §3.1 (strip every time field [now]), §3.2 (every sense [earned]), §12.2, world-clock draft §3.4.

- Between Phase 1 and T1/T2, an NPC has no time-of-day belief, no recency, and no duration sense: not coarse,
  absent. An LLM asked "what time is it?" or "how long ago was that?" with nothing in context will make up a precise
  answer. Fabricated precision is further from the owner's tenet than an honest coarse bin.
- The world-clock draft's §3.4 puts the injected clock's **calendar** into the prompt "or omitted when the embedder
  declares no calendar". §3.1's prompt test ("no clock string") passes only if Overdrive declares no calendar. The
  design doesn't say which it will do.
- Maxim's oscillator network has four scales: circadian, weekly, monthly, annual (`docs/time.md`, "Coupled
  Oscillator Network"). After A7 all four take their phase from the world calendar. Weekly and monthly have no
  biological clock behind them in humans; they are social calendars, learned from cues. §12.2 lists only the SCN
  phase as an oracle.

**Fix:** (a) a [now] `[engineering]` ANALOG divergence: a deterministic coarse readout (time of day in four or six
bins only when a light or clock percept is present; recency in log bins: just now, minutes, hours, days), listed in
§12.2 and replaced by the B9/B10 estimators when earned; (b) state that Overdrive declares no calendar to Maxim; (c)
add the weekly, monthly and annual oscillator phases to §12.2 as calendar oracles, closed by perceived calendar cues
(a newsfeed, a shift roster), not by B8.

### BF2-8. Hardware still decides NPC competence, through the model and through wall timeouts

**Location:** §1 (LLM timeouts "only free a worker"), §4.4, §4.5, §12.1 Q1.

The modelled thought cost removes latency as a channel. Two others remain, and neither is named:
- **Model capability.** The player's VRAM decides which model and context length runs. A bigger GPU gives cleverer
  NPCs at every dial. This can't be modelled away, but it is the agent analogue of the resolution rule, and it should
  be stated as such: the model, its quantization and context length go in the log header, like a rig profile, and
  §12.2 or the Known gaps records that outcome class is not promised across model profiles.
- **Wall timeouts under dilate.** §4.4 says dilate is the default, but §1 lets an LLM timeout free a worker. If a
  timed-out thought is then failed, the machine decided. If it is retried, say so: under dilate, a wall timeout must
  retry, or escalate to a host-visible stall, never become `thought_failed`.
- **Kind chosen by the host** (§12.1 Q1): if the host ever picks a cheaper kind under load, the dial decides
  competence again. Add the rule "kind may depend on the NPC's state and context, never on host load or the dial",
  with a test (same scene at 1× and 20× with a stub at varied wall latencies gives the same kinds).

### BF2-9. O4 couples thought cost to sleep pressure; §4.6 doesn't

**Location:** §0 O4 ("it couples to fatigue and sleep pressure, not hunger") against §4.6 ("Deliberation adds to
sleep pressure only if an experiment earns it").

The owner's decision and the mechanism disagree. There is real evidence on both sides. Process S in the two-process
model is driven by time awake, but sleep need is also use-dependent and local: a learning task raised slow-wave
activity in the cortex it used (Huber et al. 2004, *Nature*, from memory), and extracellular adenosine rises with
neural activity during wakefulness (Porkka-Heiskanen et al. 1997, from memory). So §4.6's "earned by experiment" is
defensible, but it is not what O4 records.

**Fix:** either amend O4's text to "fatigue now, sleep pressure only if earned", with the owner's agreement, or add a
small, marked `[engineering]` load term to Process S with the Huber evidence. Don't leave the decision table and the
mechanism disagreeing. "Not hunger" stands: it is right (Raichle & Gusnard 2002). The small studies claiming mental
work raises later food intake (Chaput & Tremblay 2007, from memory) aren't strong enough to change it.

---

## NIT

### BF2-10. Fillers: the rule is right; derive them from the modelled delay

§4.4's "fillers belong to P0, decided by modelled time, never by a stalled stream" is correct, and Clark & Fox Tree
supply the mechanism: a filler announces an anticipated delay, *uh* minor and *um* major. Since the onset (BF2-2) is
known in world time before it elapses, P0 can choose *uh*, *um* or an in-breath (Torreira et al. 2015) from the
pending gap. Answer §12.1 Q3 with that, rather than fixed fillers. Note the contested status.

### BF2-11. An interrupted speaker keeps the unsaid part as an intention

§4.3 records only the spoken prefix and drops the rest. Recording what was actually said is right, but people also
keep what they meant to say ("as I was saying…"). Keep the unsaid remainder as an interrupted intention in the next
thought's context, never as speech. Separately, overlaps are usually resolved within a syllable or two (Schegloff
2000, from memory), so the stop is a P0 reaction, not an instant drop.

### BF2-12. The world-clock draft calls PainBus's refractory "perceptual refractoriness"; it isn't

World-clock draft §4, row 2, and roadmap A8. The split (motor and IO limits on the wall, the rest on the injected
clock) is right and fair to Maxim's recorded "hardware safety" rationale. But Maxim's own brief says the PainBus gate
is a per-`(entity, failure_mode)` dispatch de-duplication ("without it two entities firing embodiment pain in one tick
collapse into one dispatch", `docs/agents/embodiment.md`). And biologically, repeated noxious input sensitises rather
than refracts (temporal summation, wind-up; Price 1977, from memory). Call it an `[engineering]` dispatch gate on world
time, and don't claim a perceptual basis for it.

### BF2-13. Windowless doesn't mean drifting

§3.3 says underground NPCs drift. Ordinary room light is around the half-maximum for phase shifting (~100 lux, for
long exposures), so NPCs under an arcology's lighting schedule entrain to that schedule. Free-running drift needs dim
light or darkness (forced-desynchrony protocols use under ~15 lux, from memory). The faithful and better story: NPCs
entrain to whatever lighting the arcology runs, which may not match the outer day. Shift workers on bright night
lighting shift partly. Captives in the dark drift. T1 arm C already tests the dark case.

### BF2-14. "Every hazard has a cue before harm" is a design rule, not biology

§7.3. Humans have no receptor for carbon monoxide, nitrogen asphyxia or ionising radiation; that is why they kill.
Label the rule as game design, and allow cueless hazards only together with an in-world instrument (a CO alarm), which
also fits BF2-6. CO₂ felt as air hunger, with hypoxia mostly unfelt, is correctly stated.

### BF2-15. §3.4 contradicts CLAUDE.md's determinism rule

CLAUDE.md: "Randomness … comes from one seeded `numpy.random.Generator` owned by `World`." §3.4 (rightly) keeps per-NPC
counter-based streams off the World's generator. Amend the standing rule when this lands, or a reviewer applying
CLAUDE.md literally will refuse the right design.

---

## Pushbacks to Maxim this reveals (for Phase 3)

1. **`CouplingSpec` can't express load-driven accumulation** (BF2-1). It is a threshold step on drift; cognitive
   fatigue is graded with demand. Arguing against: the SHAPE-FROZEN rationale ("an `extra` dict would invite YAML
   authors to stash unstructured logic"). That rationale is fair about `extra`, but the shape itself fixes coupling as
   binary. Ask Maxim to decide, when it implements the deferred evaluator, whether graded coupling is in scope. If it
   isn't, the additive path is a drive advanced by an internal writer. Evidence: Wiehler 2022's graded effect, and the
   Δt-invariance failure of a naively stepped coupling.
2. **D53's default "absent a report, mechanical success means POSITIVE"** (BF2-3). Maxim's comment calls it the
   historical contract. For embedded world modulators, whose effects are measured from frames, a silent default of
   POSITIVE is the bug class D53 was written to fix. Propose a declared per-modulator default (additive), with
   Overdrive's adapter always self-reporting meanwhile.
3. **The oscillator's weekly, monthly and annual scales** (BF2-7). After A7 they are exact calendar oracles with no
   biological clock behind them. Propose that an embedder can declare them cue-driven, and list them beside B8.
4. **S8 should probably shrink** (BF2-6). Not a pushback on Maxim but a correction of our own ask, which the "push
   back" rule requires us to make as loudly.

## Are the drafts fair to Maxim's recorded rationales?

Mostly yes, and in places generously so.
- **"Host calendar by design"** (#1361 §(g)): Maxim records no reason beyond "by design". The draft keeps it as the
  default and changes only the source. Fair.
- **"`llm_submit_interval` … loop scheduling; no longer pace decay"**: the draft concedes it's true once S3a lands,
  and argues only that it still paces proposals. Fair.
- **"PainBus refractory, reflex cooldowns | hardware safety"**: the split is fair. The label "perceptual
  refractoriness" is not (BF2-12).
- **G17 and M76**: fair, and they cite Maxim's own G3.
- **S3 and S7 corrections**: they hold against the code (`tool_bridge.py` trains the cerebellum on in-call reads;
  `modulated_by` is homeostatic-only). S7's "no field changes" is optimistic (BF2-1).
- **One omission:** S3 should say that the D53 valence contract already exists and that a deferred result must use
  it, so Maxim's reviewers don't read S3 as asking for a new valence mechanism.

## What I checked and found faithful

- The three clocks, and "perceived time is estimators fed by world time, never a second clock" (skeptic §1).
- Δt-invariance with closed-form updates and reconstructed threshold crossings (§2.1): the right rule at Marr's
  algorithmic level, and the step-size test with a planted Euler update is a real guard.
- The dial-invisibility test (§3.1): the right test for the owner's "time perceived coarsely" tenet.
- Modelled thought cost with dilation as the default (§4.1, §4.4): it removes latency as a hardware channel, and
  "abandon" is correctly marked tier 3.
- Not charging thought to hunger or to `LLMEnergyTracker` (§4.6): correct.
- The P0/LLM split for conversation (§5): matches the two-stage turn-taking model, once the onset is fixed (BF2-2).
- Per-NPC noise streams (§3.4), the arousal-sign tunable (Soares 2016), and Stetson 2007 modelled as memory density:
  correct and honestly caveated.
- Mode (a)'s world-time wait as reafference latency, with a paused world holding the call (§6.1): faithful, once it
  self-reports valence (BF2-3).
- Stale as context, never credit (§6.3): right, and correctly kept behind a red gate until C2.
- T1 and T2 with shuffled controls and kill criteria (§10), and the manipulation checks named as such.
