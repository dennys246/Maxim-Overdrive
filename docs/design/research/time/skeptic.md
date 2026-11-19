# Bio-faithful NPC time: the skeptic's brief (2026-11-16)

**Role:** designated skeptic. The job is to argue against, stress-test and sharpen the owner's idea, then steelman
what survives. This is not a design and decides nothing.

**The idea, in two versions.**
- **v1 (first brief):** the wall clock is like universal physical time. Humans perceive time their own way. The
  brain has intrinsic "ticks" set by its physics: a neuron can only fire so fast, limited by transmitter reuptake,
  vesicle formation and the SNARE machinery reloading. Make NPC time more bio-faithful along those lines.
- **v2 (owner's refinement, relayed by the coordinator):** this isn't about neurons as a literal clock. Humans can't
  perceive time at its true fine resolution. Perception of time is coarse at every scale (the SCN included), coarser
  than the time that is really there. An NPC should perceive world time only coarsely and noisily, at each timescale.

**Read:** `realtime_lanes_coop.md` (§3, §4.3, §6), `world_v2.md` (§6, the thinking lane and the world-time latency
mode), `boundaries.md`, `reviews/boundaries/bio_faithful.md` (BF-11, two clocks), `lessons_maxim_in_games.md`
(lessons 11 and 12), and from Maxim: `docs/time.md` (SCN, `TemporalSignature`, the oscillator), `ARCHITECTURE.md`
("Bio-mapping is FUNCTIONAL only"), `CLAUDE.md` (the two-tier invariant rule), `docs/substrate_primary.md`,
`docs/default_network.md`, `src/maxim/reactions/bus.py` and `default_network/behaviors/social.py`.

**On the evidence:** the neuroscience and psychophysics numbers below are textbook values quoted from memory, with
their usual sources named. I ran no web searches for this brief. Treat each number as an order of magnitude to check
before it goes into `data/`, not as a citation.

**Verdict, up front.**
- **v1 is the wrong level of abstraction for Maxim,** and on the shipped path it can't even be seen. Maxim has no
  neurons, so there is nothing for a vesicle to deplete. The sub-millisecond dynamics v1 names all happen far inside
  one 100 ms world tick.
- **v2 is mostly right, it is the right level, and it is cheap, deterministic and testable against human
  psychophysics.** Two things are wrong with it as stated: "coarse sampling of a finer reality" is the wrong model of
  how brains get time, and "noisy" undersells the errors, which are mostly systematic.
- **The biggest timing infidelity in the system today is neither of these.** It is that the NPC's cortex (the LLM)
  and much of its substrate (the Default Network's 30 Hz thread, the `ReactionBus` refractory, the drive decay) run
  on the host's wall clock. Fix that first: it is §6 items 10 to 12 and 15, and Maxim #1361.

---

## 1. Is "the wall clock is universal time" the right analogy?

**No. It runs backwards, and the way it runs backwards is the thing to design around.**

- **There are three times here, not two:**
  - **Host time** (the wall clock) is the time of the universe that *runs* the simulation. In simulation-hypothesis
    terms it is the substrate, not physics. A simulated being can't sense it: if the host stalls for an hour between
    two ticks, nothing inside can tell.
  - **World time** (`tick × tick_us`) is the physics of the NPC's universe. It is the only clock that is "universal"
    for an NPC. The designs already treat it so ("one clock, in integers", Bio-11: the dial never reaches a percept).
  - **Agent time** is what an NPC *believes* about elapsed time and time of day. It is an estimate built from world
    events, and it is wrong in lawful ways (§2b).
- **Where the analogy misleads the design:**
  - **It makes the wall clock sound privileged, as if NPC time should approximate it.** The opposite is the goal:
    host time must be *invisible* to the NPC. Every place it leaks is a bug, not a fidelity question.
  - **It hides the real leak: part of the NPC's mind lives in the host universe.** The physics is simulated, but the
    LLM is not. It runs in host time on the host's GPU. That is why `realtime_lanes_coop.md` §4.3 had to concede
    "with live models, thinking speed in world time depends on the dial", and why `world_v2.md` added `d_min` and the
    world-time latency mode ("without it, cradles at about 300× would abandon almost every thought, at a rate set by
    the host's GPU"). In the analogy's own terms, the NPC's cortex sits outside its universe. No model of perceived
    time fixes that. Declaring deliberation latency in world time (`d_min`, the ANALOG-tagged constant) is the
    partial fix the design already has.
  - **Physics has no universal time anyway.** The world clock is Newtonian absolute time. That's fine for a game, but
    it means "bio-faithful" can't borrow any authority from "physical time is X". The world clock is a design choice
    with one job: to order every event exactly, so replays are bit-identical.
  - **"Humans perceive time their own way" suggests a second clock running inside the NPC.** There isn't one, in
    people or in a good design. Perceived time is not an independent clock. It is a set of estimators read off world
    events (light, routine, memory density, interval timing). Build estimators fed by world time, never a parallel
    clock, or the NPC's time can drift away from the world's for no physical reason.
- **The right analogy:** world time is physics, agent time is perception, and host time is the machine the universe
  runs on. Its rule: *nothing in an NPC may depend on host time*. That is already the boundaries design's B-3, and
  BF-11 shows the membrane still mixes clocks (`grid.time_s` against `time.time()`).

## 2a. v1: do neurons have "ticks", and is SNARE physics worth modelling?

**Neurons have rate limits and depletable resources, not ticks, and the brain has no global clock.**

- **Rate limits, not a clock.** The absolute refractory period is about 1 ms and the relative one a few ms, so
  sustained rates top out at a few hundred Hz. Neurons don't fire on a beat. Their spikes are asynchronous, timed by
  their inputs. Oscillations (theta, alpha, gamma) coordinate populations, but none is a system clock. Many areas run
  at once, with no shared beat.
- **Vesicle dynamics are resource depletion on a range of timescales.** Depleting and re-priming the readily
  releasable pool (SNARE assembly, Munc13 and Munc18 priming) gives short-term synaptic depression over tens of ms to
  seconds. Full endocytic recycling takes seconds to tens of seconds. Behaviourally, this shows up as
  *adaptation*: a repeated input drives a pathway less.
- **Single-neuron limits barely set behavioural timing.** Ultra-rapid visual categorisation (Thorpe et al., 1996) is
  about 150 ms across roughly ten stages, so most neurons fire at most one spike per stage. Behavioural latency comes
  from conduction and synaptic delays across stages, and from evidence accumulation, not from the refractory
  ceiling. A population of asynchronous neurons reacts faster than any one neuron's inter-spike interval.

**Marr's levels decide this.** Marr's three levels are the computation, the algorithm and the implementation. SNARE
physics is implementation. Maxim's own stated level is functional: `ARCHITECTURE.md` says the "Bio-mapping is
FUNCTIONAL only … not a claimed isomorphism". The NAc is a causal-link table, and the EC an O(Nd) centroid scan.
Adding vesicle pools under a causal-link table is a category error: **there are no synapses to deplete.** You would
have to invent a synapse just to give the vesicles a home, and the parameters would have no anatomy to anchor them.

**On the shipped path it can't be seen anyway.** `tick_us` is 100,000 (0.1 s). A 1 ms refractory period and a
sub-second vesicle re-priming happen inside one tick, and physics steps only every 0.5 s. The world can't tell a
modelled synapse from an unmodelled one.

**The behaviour that might justify v1, and the simpler models that already give it:**

| Observable (people) | Rough scale | Simpler model at Maxim's level | In Maxim already? |
|---|---|---|---|
| Reaction-time distributions: right-skewed, slower and more variable with fatigue | simple RT about 150 to 250 ms; ex-Gaussian shape | a world-time latency distribution (ex-Gaussian, or drift diffusion per Ratcliff), with state modulators | no: the substrate reacts in a fixed one tick plus hand-off, and thought latency is a constant `d` or `d_min` |
| Habituation and dishabituation | seconds to minutes | short-term depression on a channel's gain (Tsodyks-Markram, 1997: U, τ_rec, optionally τ_facil) | partly: `social.py` gaze habituation; `memory_hub.py` sensitisation that resists habituation |
| Not re-triggering a response straight away | hundreds of ms | a refractory window per reaction | yes: `ReactionBus.DEFAULT_REFRACTORY_S = 0.5`, but on the wall clock |
| The psychological refractory period (a second decision soon after the first is delayed) | stimulus onset asynchrony under about 300 ms | one central response-selection bottleneck with a busy window | no |
| The attentional blink | 200 to 500 ms | the same bottleneck on encoding | no |
| Vigilance decrement (Mackworth's clock test) | tens of minutes | a fatigue drive raising latency and miss rate | the drive exists; nothing couples it to latency |
| Behaviour-switch inertia | about 0.3 s | a minimum switch interval | yes: the Default Network's `min_switch_interval = 0.3`, on the wall clock |

Every observable on that list is captured at the functional level, with one to three parameters each. None of them
needs vesicles. **The useful kernel of v1 is "processing takes time and capacity runs out", and Maxim's own level
expresses that.**

## 2b. v2: "a coarse sampling of a finer reality"

**Where it's right:**
- **Order and simultaneity are coarse.** Two events need to be about 20 to 60 ms apart before people can say which
  came first (Hirsh and Sherrick, 1961, about 20 ms). Audiovisual events up to about 100 ms or more apart fuse into
  one. Flicker fuses at about 50 to 90 Hz.
- **Durations are coarse, and the error scales with the duration.** Interval timing follows Weber's law: the error is
  about 10 to 20% of the interval (scalar timing; Gibbon, 1977).
- **Time of day is coarse.** Without cues, people misjudge clock time by hours. The human circadian clock free-runs
  at about 24.2 h (Czeisler et al., 1999) and stays on time only by daily resetting to cues (zeitgebers), light
  above all.
- **Long spans are reconstructed, and badly.** "How long ago" for days and months comes from memory, not from any
  timer.

**Where it's wrong, or misleading as a design model:**
1. **The brain does compute time finely. It just doesn't present fine time as time.** Interaural time differences of
   about 10 to 20 µs are resolved, and become a *direction*, not a felt interval. Gaps of a few ms are detected in
   sound and felt as texture or pitch. Fine timing is folded into other percepts. "Coarse sampling" would throw it
   away, and the brain doesn't.
2. **Perception is reconstructed after the fact, not sampled at a moment.** The flash-lag effect, the cutaneous
   rabbit and colour phi show that what you perceived "at" t depends on what happened up to about 100 ms *after* t.
   The brain integrates over a window, then labels the result. A model that samples instants gets the structure
   wrong: a percept is an inference over a window, labelled after the fact.
3. **There's no single resolution, so no grid.** Resolution varies by modality (hearing is far finer than sight) and
   by scale (scalar timing: the error is proportional to the interval). It also shifts with state. A fixed coarse
   sampling grid is the wrong shape.
4. **The errors are mostly systematic, not just noise.**
   - Arousal and dopamine speed up the internal clock (Meck).
   - Filled intervals feel longer than empty ones.
   - Estimates regress towards the mean of recent intervals (Vierordt's law).
   - "Time slowing down" in danger is denser memory, not finer perception: people in free fall didn't gain temporal
     resolution (Stetson, Fiesta and Eagleman, 2007).
   - Timing recalibrates to a constant lag (Fujisaki et al., 2004, audiovisual lag adaptation).

   "Noisy" hides all of this. Noise alone gives unbiased estimates. These biases are the parts that change
   behaviour.
5. **The SCN isn't a coarse perception of time.** It is an oscillator that *anticipates* (it gates hormones,
   temperature and alertness before dawn), and its phase is largely not consciously accessible. It doesn't sample
   world time. It is pulled into phase by cues and drifts without them. Maxim's SCN is two things: an exact
   timestamp index (`TemporalSignature.from_timestamp`) and a Kuramoto oscillator that is enabled but integrates one
   hour per event (`realtime_lanes_coop.md` §6 item 10). The bio-faithful part is the entrained oscillator, not the
   exact phase.

**The right design consequence for an NPC: no clock reading crosses the membrane into cognition. Each timescale
gets its own estimator, fed by world events and written in world time.**

| Timescale | What the NPC gets | Built from |
|---|---|---|
| under 1 tick (< 100 ms) | **Not time.** Fine timing reaches the NPC as other features: direction from sound geometry, the texture of an impact | world physics (a cue's direction, with noise from the world RNG); never simulate the µs mechanism |
| about 0.1 to 1 s | event *order* and *simultaneity*, with a binding window: events inside it fuse, and their order may be wrong. Percepts are labelled after a short integration window | the membrane assembling percepts from the frames of a window |
| seconds to minutes | interval estimates ("it's been a while"), with scalar noise (CV about 0.15) and the biases above: arousal speeds them up, and they regress to recent intervals | an interval timer per tracked interval, read from world ticks, with noise from the world RNG |
| hours | a time-of-day *belief*: the SCN oscillator's phase, entrained by world light and routine; it drifts indoors or underground | the oscillator stepped on world time (item 10), with zeitgebers from the world (light from the rendering-independent light channel, meals, social cues) |
| days and longer | a reconstructed "how long ago", from memory density and landmarks | the hippocampus's episodes; no counter |

Three rules go with the table:
- **The exact world timestamp stays as machinery.** It orders the log, keys the hippocampus and drives the
  oscillator's integration. It just never appears in a percept or in an LLM prompt as "the time is 14:32:07". This
  is the bio-faithful version of BF-11: the membrane translates clocks, and the agent receives *estimates*.
- **Every stochastic estimate draws from the world-owned seeded generator,** so tier-1 replays stay bit-identical.
- **The parameters have human norms** (TOJ thresholds, Weber fractions, the free-running period, phase-response
  curves). That makes this model *validatable*, which v1 is not.

**A tension to raise, not hide.** §6 item 10 asks Maxim to take SCN phase "from world time and the world's day
length". That fixes the wall-clock bug, and it remains the prerequisite. But exact phase from world time is still an
oracle the NPC couldn't have. The v2 step after item 10 is to feed the entrained oscillator from world time and to
give cognition the oscillator's phase, not the computed one. It is a separate Maxim proposal, and it argues against
treating `TemporalSignature`'s exact phases as perception.

## 3. Cost

| | v1 (vesicles or spiking) | v2 (estimators at each timescale) plus a latency and capacity model |
|---|---|---|
| Compute | there are no neurons. If you added any, a population per pathway per NPC at sub-ms steps is thousands of times the tick budget; or the result is invisible at a 100 ms tick | O(channels + timers) per NPC per tick: a few multiplies and RNG draws |
| Determinism | fine if it's integer or fixed-step, but it multiplies agent state that must be saved and hashed | fine: world RNG, world ticks, small checkpointable state |
| Testability | no behavioural readout at the tick's resolution, and no anatomy to fit; it can't be validated | closed-form tests (the mean and CV of an estimator, the free-run drift per day, a PRP curve) and human norms to compare with |
| Design complexity | a new layer under a functional architecture, against Maxim's level | moderate: one membrane rule (no clock percepts) and one estimator per row, each [engineering] until earned |
| Tick resolution | sub-tick, so invisible | **a real cost:** at `tick_us` = 100 ms, a 200 ± 50 ms reaction time is quantised to about ±50 ms, the same size as the effect. Either sample latencies in µs and apply them at the next tick (state the quantisation as a known gap, with numbers), or argue that the agent step needs a finer tick. Decide this before building latency distributions |

**The benefit side.**
- **Gameplay:**
  - Reactions that vary and degrade, and so read as alive, not robotic.
  - Exploitable but fair windows: feints and distractions via the psychological refractory period.
  - Alarms that habituate, which the player can manipulate.
  - NPCs whose sense of time drifts in a windowless arcology: shift workers, the jet-lagged, and people
    "underground for days" who are wrong about the hour. That last one is strong cyberpunk material.
- **Research:** whether a mind that knows time only through estimates still learns time-structured behaviour. The
  SCN, temporal credit and anticipation all depend on that, and Maxim has never tested it, because its agents have
  always held a perfect clock (`time.time()`).

## 4. Risks

1. **Fidelity theatre while the gross infidelity stands.** The LLM is a fluent adult on an infant's body (the
   owner's "PhD English major" point), and its latency is seconds of host time scaled by the dial. Tuning millisecond
   reaction-time distributions under that is polishing the wrong part. **Order of work:** the host time leak (items
   10 to 12 and 15, #1361), then deliberation latency in world time (done as `d_min` and ANALOG), then v2.
2. **Competence that depends on the dial or the hardware.** Any timing tied to host steps or GPU speed makes NPCs
   smarter on a faster machine or at a slower dial. Rule: every latency, refractory and estimator is defined in world
   ticks. Today three Maxim mechanisms break this: `ReactionBus` refractory (`time` based), Default Network
   `update_hz` (a daemon thread on the wall clock), and `min_switch_interval`. They join item 11's list.
3. **Making NPCs worse, not more alive.** Slower and noisier isn't more interesting by itself. Players need *legible*
   tells (a visible flinch, a delay) to use a window. Every mechanism should have a visible consequence, or it's cost
   with no gameplay.
4. **A model that can't be validated.** v1 has no anatomy and no behaviour to fit, so its parameters can only be
   tuned. v2 has human norms, but no human run in this world to compare against. Validate each estimator against its
   closed form and its human norm, and accept nothing on "looks right".
5. **Bio naming as validation.** Maxim's `CLAUDE.md` says bio-inspired naming "does NOT count as behavioral
   validation", and new mechanisms enter as `[engineering]` until an experiment earns them. A "vesicle pool" name
   would look earned without being earned.
6. **Interfering with learning.** Latency jitter and noisy time make temporal credit assignment harder (NAc
   eligibility windows, lesson 6, lesson 9). That may be the point, but it can't be allowed to silently break
   learning that works today. Every experiment needs a no-noise arm.
7. **Ledger rules.** Game runs never go on Maxim's results ledger. The experiment below has to run as a Maxim cradle
   under Maxim's process, with the game as the motivating evidence.

## 5. Steelman

**The strongest version that survives:** *an NPC is a bounded system living in world time. It knows that time only
through lawful, state-dependent estimates at each timescale. Its responses take world time and use up a finite
central capacity that recovers.* That's v2, plus v1's real kernel (rate limits and depletion), stated at Maxim's
functional level.

**The minimum worth building, in this order:**
0. **Prerequisite, not optional:** nothing in an NPC reads host time (items 10, 11, 12, 15, #1361; this adds
   `ReactionBus` and the Default Network's rate and switch timers to item 11's list).
1. **No clock percepts.** The membrane never gives cognition a timestamp or a clock string. It gives estimates. This
   is one rule with a test, and the cheapest part.
2. **The SCN phase perceived from the entrained oscillator, not from the exact phase,** with zeitgebers from world
   light and routine and a free-running period a little off 24 h, in `data/`.
3. **Interval estimators with scalar noise and the arousal bias,** from the world RNG.
4. **A world-time latency distribution for substrate responses and for deliberation,** with fatigue, arousal and
   circadian phase as modulators. It replaces the fixed one tick and the constant `d`, after the tick-resolution
   question is decided.
5. **One central bottleneck with a refractory window (the PRP),** and short-term depression per channel
   (Tsodyks-Markram), reusing and moving to world time the refractory and habituation code Maxim already has.

Not worth building: spiking neurons, vesicle pools, SNARE kinetics, a global brain tick, or anything below one world
tick that would be presented as time.

**Experiments to pre-register in Maxim's process** (cradle runs, not game runs):

- **T1: does perceived time carry behavioural weight?** This tests items 2 and 3.
  - *Arms:*
    - (A) the exact SCN phase given to the agent, as today;
    - (B) the entrained-oscillator phase, with light zeitgebers;
    - (C) the same as B, with the light removed for N days (a windowless room).
  - *Task:* food is available only in a fixed daily window, and the agent learns to anticipate it (food-anticipatory
    activity, which Maxim's oscillator was built to learn).
  - *Pre-registered predictions:*
    - B anticipates as well as A, within a stated margin;
    - in C, the time of anticipation drifts by about (τ − 24 h) per day, then re-entrains within a stated number of
      days once light returns;
    - A shows no drift in C, which is the oracle signature.
  - *Kill criterion:* if B can't learn anticipation within the margin of A, the oscillator isn't ready to be
    perception. File it as a Maxim finding, and keep the exact phase as a marked ANALOG.
- **T2: does state-dependent timing change what is learned, not just how fast?** This tests item 4.
  - *Arms:*
    - (A) a fixed latency;
    - (B) latency modulated by fatigue and circadian phase;
    - (C) a shuffled control with B's marginal latency distribution, independent of state.
  - *Task:* a timed hazard that punishes slow responses, with rest available.
  - *Pre-registered prediction:* only B learns to schedule hazardous actions when alert, after rest or at a high
    circadian phase. C has the same mean latency but no state to learn from.
  - *Kill criterion:* if B and C don't differ on the scheduling metric by a pre-registered effect size, the state
    dependence stays a game-feel parameter, `[engineering]` only, and makes no claim about Maxim.
  - The PRP and the habituation curves are manipulation checks in both experiments, not results. They hold by
    construction.

**For the owner, in one line:** the instinct that a mind is bounded in time is right, and v2 is the version to
build. Build it as estimators at each timescale in world time, not as neuron mechanics, and only after the host
clock stops leaking into the NPC.
