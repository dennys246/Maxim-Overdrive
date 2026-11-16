# NPCs and SEM: time, thought, action and perception (design part 2, 2026-11-16)

**Status:** DRAFT, for a design review before any code. Part 2 of three: part 1 is `world_model.md` (the world),
part 3 will be `lab_and_core_loop.md` (the lab tile and the loop the player lives in). This part carries the detail
that `boundaries.md` v2 defers: what an NPC's time, thought, action and perception are, and what Maxim's SEM needs
to support them.

**It builds on `boundaries.md` v2 and does not reopen it.** That design fixed the interfaces:
- `AgentPort` in integer ticks (§7.1);
- propose and settle, with receipts (§7.2);
- published immutable frames (§4.2);
- the log record (§6);
- named Maxim adapters (§8.1);
- B-13: percepts only through physical channels (§4.4).

Where this part finds a factual error in v2, it says so in §12.3 instead of quietly diverging.

**Sources:**
- `research/time/` (neuroscience, the Maxim time audit, the engine mapping, the skeptic);
- `research/signals/`;
- `docs/maxim_upstream/world_clock_release_DRAFT.md` and `sem_breaking_change_plan_DRAFT.md`;
- roadmap Phase 3 (tiers A, B, C);
- the boundaries and real-time reviews;
- the lessons doc (`docs/lessons_maxim_in_games.md` on `phase1/standards`).

**Numbers:** each number names its source. *To verify* marks a number recalled from memory that must be checked
against a primary source before it enters `data/`.

**Every mechanism is tagged with when it lands:**
- **[now]:** a foundation, built in Overdrive's Phase 1 PRs;
- **[after A]:** needs Maxim's tier A world-clock release;
- **[earned]:** built only if a pre-registered experiment earns it (§10);
- **[Phase 4]:** lands with the first NPC bodies.

## 0. Decisions this part rests on

| # | Decision (owner, 2026-11-16) | Where |
|---|---|---|
| O2 | Action results: (a) a world-time wait for the receipt now, (b) `neutral` plus late credit later; propose/settle laid now | §6 |
| O3 | The substrate runs outside the sealed core behind `AgentPort`, with real Maxim; it moves inline after tier A | §1, §2 |
| O4 | Three clocks; no time field reaches cognition; thought cost is modelled and phased in world time; late thoughts dilate the world; it couples to fatigue and sleep pressure, not hunger | §1–§5 |
| O5 | Refining SEM is in scope and a priority, through Maxim's process; additive first, one breaking batch at most | §8 |
| — | The thought-cost unit is as fine as is realistic and useful, so that conversation can be dynamic in hybrid mode | §4, §5 |
| — | Lay the foundations now, and test against Maxim as each tier lands | throughout |

## 1. Three clocks, and who owns them

| Clock | What it is | Owner | Exact? | Reaches cognition? |
|---|---|---|---|---|
| **World time** | the integer tick × `tick_us` | `Simulation` | exact | never |
| **Body time** | the physics of the body: drive drift, depletion pools, reflex latency, sleep pressure | the agent substrate, fed the true world `dt` by `AgentPort.step` | exact | never as a number; only through what the body feels |
| **Perceived time** | durations, order and time of day as the NPC believes them | modelled time senses (§3) | coarse, biased, noisy | yes, as estimates |

**Why three, and not two.** The owner's analogy ("the wall clock is universal time") is right in spirit. Inside the
game, though, the universal time is the world tick. The wall clock belongs to the machine running the universe, and
no NPC may be able to sense it, or how fast the dial is set (research/time/skeptic.md §1, engine_mapping.md §1).
Body time must be exact, because physics doesn't estimate: a body cools by the true elapsed time. Only perception is
coarse.

**Where wall time legitimately remains (host only):**
- the pacing loop that converts the dial into ticks per wall second;
- measuring and reporting dilation;
- LLM and network timeouts, which only free a worker (a late thought is handled in world time, §4.4);
- meters, and log flushing.

None of these values crosses `AgentPort`. **[now]**

**Today's violation, for the record** (research/time/maxim_time_audit.md):
- Maxim reads the host clock about 880 times, in about 215 files.
- Its substrate cadences run on the wall clock: `llm_submit_interval` 0.5 s, the Default Network at 30 Hz,
  `ReactionBus` refractory 0.5 s. So at 20× an NPC's reflexes slow down in world time.
- The prompt carries the exact host date and time (`prompt_builder.py`).

Tier A (A2–A9) fixes the clock reads; until it lands, every real-Maxim run is an OPEN divergence (§12.2).

## 2. The body: substrate in world time

### 2.1 Every process is Δt-invariant **[now for Overdrive's side; after A for Maxim's]**

- **Rule:** every body process advances by closed-form updates in world `dt`, so its state after a world interval
  is the same whether it was stepped once or a hundred times. Decay is `x *= exp(-k·dt)`, never `x -= k·x·dt`.
  Linear drift is `x += r·dt`, clamped.
- **Why:** the dial is to an NPC what a varying frame rate is to a game. Games learned to express every rate per
  second and integrate it exactly; anything non-linear stepped naively changes with the step size. This is the agent's
  version of the resolution rule ("a rig may change precision, never the outcome class"), and the neuroscience report
  reaches the same rule from the biology (research/time/neuroscience.md §8.2).
- **Threshold crossings are reconstructed, not sampled.** A drive that crosses `deprivation_threshold` partway
  through a step fires its pain at the crossing time, computed in closed form, stamped at sub-tick resolution, and
  delivered at the next tick. This is part 1's "reconstruct, decide at the point, integrate" applied to the body:
  checking the threshold only at step ends would move the pain onset by up to one step, and by more at coarse rates.
- **The test (the step-size invariance test):** run each process over the same world interval at step sizes of 1,
  2, 5, 10 and 50 ticks.
  - Continuous state agrees within a closed-form tolerance.
  - Discrete events (threshold crossings, refractory ends) land on the same tick, which is the outcome class.

  Prove it by planting an Euler update and watching the test go red.
- **Multi-rate is allowed; thinning is not.** A process may run at an integer divisor of the tick with a per-actor
  phase (`boundaries.md` §7.3); for example, reflexes at the tick and drive drift at 1 Hz. When the host can't keep up,
  the world dilates. **The host never lowers an NPC's substrate rate to keep pace**, because that changes its reflexes
  (engine_mapping.md §2.4).

### 2.2 Drives: homeostatic and entropic

Maxim already has the split, in `embodiment/sem.py`, both types frozen in shape since 1.0 (CC3):

| Spec | Behaviour | Examples | Relief |
|---|---|---|---|
| `HomeostaticDriveSpec` | pulled back toward `set_point` at `drift_rate` | temperature, pressure | the body itself, once the force is removed |
| `EntropicDriveSpec` | drifts away at `drift_rate`; only an action resets it | hunger, thirst, fatigue | eating, drinking, resting |

- **The time base of `drift_rate` is "per second", with no clock named.** Today it is read as the host's elapsed
  time, with no reset across a pause and no cap (`body.py:293-298`, per the audit). So a paused NPC gets hungry.
- **Decision:** `drift_rate` means per world second.
  - The additive path is SEM plan S1: #1361 S4 already makes drift happen only through
    `Embodiment.advance(dt)` on the experience clock, plus a docstring and a test that state the unit.
  - Renaming the field to carry its unit belongs to the breaking batch, and is opened only on evidence.
  - **[after A]**, through A1 (#1361) and A2.
- **Overdrive never models the same drive twice.** A drive the world simulates, such as body temperature from part
  1's heat field, is world-owned and pushed through `world_set_axis` (§7.2). A Maxim `self_effect` delta is allowed
  only on drives the world doesn't simulate, and each is listed as an ANALOG divergence (`boundaries.md` §4.3).

### 2.3 Fatigue, sleep pressure and the cognitive reserve

- **Fatigue** is an entropic drive (Maxim's own example). **Sleep pressure** follows the two-process model's Process
  S: it rises with time awake (τ ≈ 18.2 h) and clears in sleep (τ ≈ 4.2 h) (neuroscience.md §6.4, checked against the
  Process S literature). Caffeine's half-life is about 5 h (same source).
- **A cognitive reserve** is a new body sensor that falls while the NPC deliberates (§4.6) and recovers with rest.
  Fatigue's existing `EntropicDriveSpec.coupled_to: CouplingSpec` (`sem.py:244`) makes it drift faster while the
  reserve is low.
  - `coupled_to` is parsed from YAML today but never applied ("implementation deferred post-cradle").
  - The additive path is to implement its evaluator: SEM plan S7, roadmap C5. **[after A; behaviour earned by T2]**
  - **The hook is `coupled_to`, not `modulated_by`.** `modulated_by` exists only on `HomeostaticDriveSpec`
    (`sem.py:209`), and fatigue is entropic (§12.3).
- **Sleep and the substrate rate.** A sleeping NPC runs its substrate at low rates and doesn't deliberate. That is
  biology, and it is also why the "sleep" fast-forward preset is the one that reaches 20× with many NPCs
  (engine_mapping.md §2.4).

## 3. Perceived time: coarse, by scale

### 3.1 The rule **[now]**

**No time field reaches cognition.** The adapter strips every one before anything reaches an agent's percepts,
memory text or prompt:
- `observed_tick`, `issued_tick`, `apply_tick`, receipt and deliver ticks;
- deadlines;
- the dial, and dilation;
- wall time.

The NPC matches a receipt to its action by an opaque id, and feels a delay only by when the receipt arrives
(`boundaries.md` §7.3).

- **`SensorReading.timestamp` is body machinery.** It is stamped from the injected clock (SEM plan S2; tier A), and
  it never reaches a prompt verbatim.
- **In-world clocks are percepts, not oracles.** A wall clock, a phone, a newsfeed or the sky through a window is an
  object in the world. The NPC learns the time by perceiving it, through B-13's channels (§7), as people do
  (neuroscience.md §7–§8.4).
- **Tests:**
  - a schema test: no agent-facing type has a time field;
  - a prompt test: a rendered prompt contains no tick, no clock string and no date from the host;
  - **the dial-invisibility test:** a scripted run at 1× and at 20× gives bit-identical percepts and prompts, NPC by
    NPC, tick by tick.

### 3.2 The senses, scale by scale

Numbers are from neuroscience.md §3 and §8.4. That report checked them against primary sources where it says so, and
each "approx." there is *to verify* here.

| Scale | What the NPC perceives | Mechanism | Lands |
|---|---|---|---|
| under ~10 ms | nothing as time; fine timing arrives as a feature (sound direction) | the world converts it before the percept | [Phase 4], with sound |
| ~10–40 ms | events within ~30 ms are simultaneous, order unknown (central order threshold ~20–40 ms) | an order-threshold window on event percepts | [earned] |
| ~40–100 ms | one perceptual moment: events within ~100 ms bind as one | the integration window | [earned] |
| 0.1–3 s | a "now"; reaction 150–250 ms simple, 300–600 ms choice | reaction latency (§4.2) | [now] as data, [earned] as state-dependent |
| seconds to minutes | prospective interval estimates with scalar noise, CV ~0.1–0.2 (Weber's law for time), biased by arousal | an interval sense; Maxim's number-sense Weber machinery (`math/ips.py`, 0.15) could be reused | [earned], T2 |
| minutes to hours | retrospective duration from the density of salient events, tens of % off and biased by content; awake-hours roughly from sleep pressure | counting salient changes (Roseboom et al. 2019) | [earned] |
| time of day | to minutes with light or a clock; without them the SCN phase drifts ~11 min/day (period 24.18 ± 0.15 h, Czeisler 1999), and its readout is uncertain to an hour or more (weak evidence) | an SCN oscillator entrained by world light (§3.3) | [earned], T1 |
| days | a count of sleeps; in isolation off by days to weeks (Siffre: 58 days felt like 33) | a sleep counter feeding the date belief | [earned] |

**Two biases are tunables, not facts:**
- **Arousal's effect on felt intervals.** Its sign is contested: Soares et al. 2016 found that dopamine-neuron
  stimulation made mice judge intervals shorter, the opposite of the classic drug studies (neuroscience.md §4.4).
  `data/` holds the sign as a parameter.
- **"Fear slows time."** Stetson et al. 2007 found that it is denser memory, not finer perception: falls were
  remembered 36% longer, with no better resolution in the moment, from 7 duration judgments. The retrospective sense
  models it as memory.

**Not built:** a literal perceptual frame rate, since alpha/theta sampling is contested (Buergers & Noppeney 2022,
Brookshire 2022); a waking 90-minute cycle; felt time speeding up with age.

### 3.3 The SCN **[earned, T1; after B8]**

- **Today:** Maxim's SCN is a calendar index.
  - Its phase comes from `datetime.fromtimestamp`, which is host local time, with daylight saving and 86,400 s
    hard-coded (`temporal_signature.py:62`).
  - It has no light input, and `zeitgeber_strength` is declared but never set.
  - Its oscillator advances one hour per observed event (`oscillator.py:193-194`).
  - Maxim records this as "host calendar by design" (#1361 §(g)).
- **Target:**
  - an oscillator with a free-running period a little over 24 h, held in `data/`;
  - entrained by a world light percept (melanopsin-like: peak ~480 nm, half-maximal ~100 lux), shifting by up to
    2–3 h a day along a phase-response curve (neuroscience.md §6.2);
  - its phase exposed to cognition only as an estimate.
- **Why it matters here:** an arcology is mostly windowless. Underground NPCs drift, night-shift NPCs are
  phase-shifted, and a captive loses track of days. That is bio-faithful, and it is also story material.
- **Path:**
  - Tier A's A7 makes the phase come from world time, not the host calendar.
  - Tier B's B8 adds the entrained oscillator and its estimate.
  - A7 alone is still an oracle: exact phase, from the world (skeptic.md §2b). B8 removes the oracle.

### 3.4 Where the noise comes from **[now]**

- **A per-NPC counter-based stream,** keyed by `(run seed, actor, stream, counter)`. An example is Philox, spawned
  through `SeedSequence` from the log header's seed (`boundaries.md` §7.3).
- **Never the World's generator.** Otherwise adding a noisy sense to an NPC would change a fire's outcome (D-S5).
  The skeptic's brief says "from the world RNG" (skeptic.md §5, item 3); that is superseded here.
- **Each sense owns a named stream,** so adding a sense doesn't shift another sense's draws.

## 4. Thought cost

### 4.1 The problem, and the decision

LLM latency is a property of the machine, in wall seconds. If thoughts cost no modelled time, a 3 s thought costs
0.75 world seconds at 0.25× and 60 at 20× (engine_mapping.md §3.1). An NPC's competence would then depend on the dial
and the GPU, which is the same class of bug as rig-dependent physics (lesson 1).

**Decision (O4):** a thought costs **modelled world time, by phase**.
- An early result is held until its time.
- A late result dilates the world in wall time, with the dilation reported by cause ("deliberation", beside
  "physics" and "substrate").
- This keeps "nobody waits" in world time: the NPC lives through exactly the modelled time, acting on its substrate
  throughout.
- It reverses `realtime_lanes_coop.md` §9 Q1 as measured in wall time (§11).

### 4.2 The phases

A thought is not one number. It is a sequence of segments, each landing at a modelled world time. The unit is the
world microsecond, stamped below the tick and applied at tick boundaries in sub-tick order (§9).

| Phase | Who produces it | World-time cost | Bio basis (all *to verify* unless marked) |
|---|---|---|---|
| **P0 reaction** | the substrate, no LLM | a reaction latency from `data/`: ~150–250 ms simple, ~300–600 ms choice (Hick's law) | reaction-time norms (neuroscience.md §3.1); conversational backchannels ("mm-hm", a nod, a glance) and fillers ("um") come here |
| **P1 onset** | the LLM, modelled | `D_onset(kind, state)`: the time to a first word or a first action | planning a spoken reply begins after ~0.6–1.5 s (Levinson & Torreira 2015); a deliberate choice among a few options takes ~0.5–2 s (engine_mapping.md §3.1) |
| **P2 speech** | the LLM's stream, timed by the body | each word stamped at speech rate, ~2–3 words/s (~150 wpm), with durations by syllables | speech-rate norms |
| **P3 act** | an action the thought chose | the action's own world time, through the pipeline (§6) | — |
| **Pn next segment** | the LLM, after a tool result or a percept | another modelled onset | a think → act → perceive loop |

- **Speech length is not part of the deadline.** A reply's length is known only when it arrives, so a deadline that
  depended on it would depend on wall time. Speaking is an action that takes world time in proportion to its length,
  like walking (engine_mapping.md §3.5 item 6).
- **A segment boundary is any model output the world must act on:** a tool call, a speech act, or a final intent
  list. Each lands at its modelled time. This is how Maxim's current tool-using turns (mode (a), §6.1) stay
  deterministic: the tool call's world time comes from the model, not from when the GPU emitted it.
- **`D_onset` by kind** comes from `data/agents/timing.yaml`, in microseconds. Example kinds: `backchannel` (none:
  it's P0), `reply`, `choice`, `plan`.
  - **[now]:** fixed per kind.
  - **[earned, T2]:** modulated by fatigue, arousal and circadian phase. Until T2 earns state dependence, a fixed
    value per kind is the honest model.
- **Calibration:** the hybrid draft's H2 sweeps stub latency over world time (0, 1, 3, 10, 30 s). That becomes the
  calibration for `D_onset`: where competence collapses, and where people actually take that long
  (engine_mapping.md §3.5 item 8; roadmap C11).

### 4.3 Interruption and barge-in **[now as interfaces; after C9 in Maxim]**

- **`cancel_on`** is set on a thought request (`boundaries.md` §7.4). It lists the world events that end a thought
  in flight: pain above a threshold, a salient percept, being spoken to, being addressed by name. Cancellation is
  decided at a tick, in world time, and logged.
- **Speech is interruptible mid-stream.** When an NPC is cut off:
  - the words it has not yet spoken are dropped;
  - **its memory records what it actually said**, not what it planned. Receipts for speech acts carry the spoken
    prefix.

  That is faithful, since people remember being interrupted, and it means a player can talk over an NPC and the NPC
  knows it.
- **A cancelled thought's late result** is dropped and logged as `cancelled`.
- Maxim needs cancellable deliberation with a world-time deadline (roadmap C9, joining items 7 and 13).

### 4.4 Late thoughts **[now]**

- **The default host policy is to dilate.** The host does not step past a segment's modelled time until that segment
  has arrived. In world time nobody waits; in wall time the world slows, with the slowdown reported as deliberation.
- **`latency_policy: abandon`** is the explicit, logged alternative, for runs that value wall pace over faithfulness
  (a long unattended fast-forward). At the deadline the thought fails as `thought_failed`, and its failure rate is a
  meter. These runs are tier 3, since the machine decides which thoughts fail.
- **Not built: fillers on a stall.** Emitting "um" when the model runs late would be lifelike, but then the machine
  decides the NPC's speech, which is dial- and hardware-dependent. Fillers belong to P0 (the substrate), decided by
  modelled time, never by a stalled stream.
- **This supersedes** `realtime_lanes_coop.md` §4.3's `max_age_ticks` abandonment as the default (§11).

### 4.5 Throughput, honestly

**Sustainable dial ≈ W / (N × m)** (engine_mapping.md §3.4; derived, an upper bound because it ignores bursts):
- W is thoughts per wall second (workers ÷ wall latency);
- N is the number of awake, deliberating NPCs;
- m is the number of thoughts each starts per world second.

For streamed speech, the token rate needed is **dial × speakers × ~3–4 tokens/s**: about 2.5 words/s × ~1.3 tokens
per word (*to verify*).

| Scene | What holds |
|---|---|
| One local model, 3 s, ten NPCs each thinking twice a world minute | 1× |
| The same NPCs idle, thinking once in 5 world minutes | ~10× |
| Everyone asleep | physics-bound, ~20× |
| One NPC speaking at 20× | ~70 tokens/s from the model, which many local models can't sustain |

So the world slows toward 1× during conversation, and fast-forward survives for its stated purposes ("wait",
"sleep"). Twenty times while ten NPCs argue isn't achievable: either the world slows, or the NPCs get stupider. This
design chooses the first, and says so on screen.

### 4.6 Coupling to the body: fatigue and sleep pressure, not hunger **[after A; earned by T2]**

- **The biology** (*to verify* where marked):
  - The brain uses ~20 W at rest, and effortful thought adds only a few percent.
  - "Ego depletion" (willpower as blood glucose) failed a large multi-lab replication (Hagger et al. 2016).
  - Sustained cognitive control does build fatigue: glutamate accumulated in lateral prefrontal cortex after hours of
    hard work (Wiehler et al. 2022).
- **The loop:** time spent in P1 and Pn draws down the cognitive reserve (§2.3) in world time, scaled by kind. The low
  reserve makes fatigue drift faster through `coupled_to`. Fatigue then lengthens `D_onset` and degrades later
  thoughts (once T2 earns state dependence). Rest and sleep recover both. Sleep pressure follows time awake.
  Deliberation adds to sleep pressure only if an experiment earns it.
- **Not hunger.** Charging thoughts to calories would contradict the biology.
- **Never from `LLMEnergyTracker`** (`energy/llm_tracker.py`). It counts tokens and wall latency, which are the
  machine's costs: an NPC would tire faster on a slower GPU (SEM plan S7).
- **Ties to the owner's Phase 5 energy and homeostasis plan.** Body energy and the heat budget are what the Overdrive
  mechanic spends (world_v2.md §10). The cognitive reserve is a third, slower budget, on the same drive machinery.

### 4.7 Reproducing runs with real thoughts **[now]**

- **A recorded response cache,** keyed by SHA-256 of the canonical request (`boundaries.md` §7.4). With modelled
  landing times, both when a thought lands and what it says are pure functions of the run. So a session with real LLM
  thoughts reproduces at any dial: the first run records the answers, and a rerun reads them.
- **Replays still never call anything live.** The log is the truth. The cache is for reruns, debugging and
  calibration.

## 5. Conversation in hybrid mode

**The split** (roadmap C11, the hybrid line; Phase 4's "movement on the substrate, speech on the LLM"):

| Behaviour | Produced by | Why |
|---|---|---|
| Turn-taking signals: gaze, nods, backchannels, fillers, starting to answer | the substrate, P0 | humans take turns with gaps of ~200 ms (Stivers et al. 2009, *to verify*), far faster than they can plan content (~600 ms or more), so they plan in overlap and signal with fast routines |
| Content: what to say and what to do | the LLM, P1 onward | deliberation |
| Speaking it | the body, at speech rate, interruptible | speech is an action (§4.2) |
| Reacting to being interrupted | the substrate first (stop, look), then the LLM | barge-in (§4.3) |

**What the client renders** (the server is authoritative, CLAUDE.md):
- Speech arrives as tokens stamped with world-microsecond times. The client shows or voices each token at its time,
  and may animate a mouth to match.
- The client never decides when speech happens. Timing comes from the server, as with every other channel.
- This is how voiced games do lip sync: the line carries phoneme timestamps, and the renderer places mouth shapes on
  them whatever its frame rate.

**What the substrate needs from Maxim:** a P0 repertoire of fast conversational acts, and a way to hand off to the
LLM. That is the hybrid line's work (C11), tuned by its experiments. Until then, P0 in conversation is a stub with
fixed latencies from `data/` **[now]**.

## 6. The action contract in detail

### 6.1 Mode (a), now **[now; tested against real Maxim]**

1. Maxim's tool loop calls the membrane's `execute` during an LLM turn.
2. The adapter submits an intent through the one pipeline, stamped with the actor (from the channel),
   `observed_tick`, and the segment's modelled time (§4.2).
3. The adapter **waits in world time** for the receipt and the next published frame. It's a body's reafference
   latency, not a wait for a thought. The wait is bounded in world ticks, and a paused world holds the call. This is
   Maxim's own Reachy precedent (`ReachyOrientMotorBackend.execute`).
4. It returns a `ModulatorResult` built from the application:
   - `success` and `error` from the receipt;
   - metadata from the measured effect (`destroyed_volume_m3`, `absorbed_j`);
   - drive transitions from the frames before and after.
5. Maxim's cerebellum trains on the sensors read during the call (`tool_bridge.py:864-892`). Because those reads now
   come after the wait, it sees the effect. NAc books valence as it does today.

### 6.2 Mode (b), later **[after C1]**

- `execute` returns at once, with `outcome_valence: "neutral"`, and the receipt reaches Maxim later through settle.
- **The corrected ask** (SEM plan S3; §12.3): valence is not an input to the cerebellum, and NAc already honours
  `neutral` (`tool_dispatch.py:356-375`). What has to change is **when the cerebellum observes: at settle time**, from
  the receipt's frames, not during the call.
- This needs Maxim's tool-level propose and settle: an additive `ModulatorReceipt`, a deferred cerebellum
  observation, and generate vs apply (roadmap C1). Until then mode (b) would train the cerebellum on the state before
  the effect, so it isn't used.
- Switching from (a) to (b) changes the adapter only (O2).
- **With generate vs apply (item 16),** a turn returns its intents as values with no side effects, which is mode (b)'s
  natural shape. The lanes design's "a thought result is a pure value" (§4.3) holds only from then on (§11).

### 6.3 Refusals and stale results **[now; OPEN until C2]**

- **Receipt kinds:** `applied`, `refused`, `stale`, `cancelled`.
- **Stale is context, never credit** (lesson 9). Maxim books every `success=False` as NEGATIVE, so a stale refusal
  under mode (a) would teach the NPC that a good tool is bad, in proportion to how late its thoughts run.
  - Until Maxim has a refusal-kind key (SEM plan S4, roadmap C2: `call_error`, `stale`, `refused_by_world`), stale
    refusals are an **OPEN divergence behind a strict red gate**.
  - Meanwhile the receipt also goes into the next thought's context.
  - This supersedes `realtime_lanes_coop.md` §4.3's "something it can learn from" (§11).
- **A malformed call is a cognitive error, not a tool failure** (lesson 7; roadmap C2).

### 6.4 Per-actor binding **[now]**

- `to_maxim_entity(world, region, actor=...)` gives each NPC its own entity and modulator, so its intents are
  stamped with that actor (`boundaries.md` §7.2; BF-6).
- `name` and `full_path` stay identical across actors, since the cerebellum and NAc key on them (lesson 10).
- The longer-term version is an `actor` key that Maxim injects into `params`, as it injects `target` today (SEM plan
  S6, roadmap C4, additive).

## 7. Perception

### 7.1 B-13: percepts through physical channels **[import half now; perceiver half Phase 4]**

- **A percept** is a reduction of registered physical channels, evaluated at the perceiver's position and receptor,
  with a line-of-sight gate once light exists (`boundaries.md` §4.4).
- **An instrument** is anything else: a region sensor that reports a crate's interior maximum temperature to anyone,
  anywhere. Today's region sensors are relabelled as instruments, an ANALOG divergence. An NPC reads an instrument
  only by using one (a thermometer, a terminal, a clock face).
- **In Maxim** (SEM plan S8, roadmap C6, additive): a declared `percept` or `instrument` kind on Maxim's existing
  `modality:` sensor declarations, carried in `SensorReading.extra`. Prompts render instruments only while the agent
  is using one. Whether `modality:` can carry this without a schema change is unverified.

### 7.2 The push path **[Phase 4; per-part sensors after C8]**

- Maxim bodies perceive by push: the world writes values through `world_set_axis`, and `live_world_set_sensors`
  declares the world the single writer. The membrane does this in the agent lane, as a pure function of a published
  frame, so it needs no log record (`boundaries.md` §4.3).
- **Every body sensor the world simulates is world-owned**, so an NPC is never burned twice: once by a YAML delta and
  once by physics.
- Per-part sensors (`arms.thermal`) need `world_set_axis` for sub-sensors (P4, roadmap C8).

### 7.3 The receptor-first rule **[now, as a review rule]**

- Every sense names its human receptor or drive, or it is an instrument (lesson 5; research/signals/maxim_senses.md).
  For example, an NPC feels rising CO₂ as air hunger, never "low O₂".
- Every hazard has a cue before harm, and an action that relieves it; otherwise the NPC learns helplessness, not
  avoidance.
- In Phase 1's well-mixed rooms, nothing changes as an NPC approaches a fire until it touches it (lesson 4). So the
  senses each phase adds are physical sources of cues (sound, light, smoke layers, radiant heat), not designer events.

## 8. SEM refinement items

Additive first, one breaking batch at most (O5). The breaking batch opens only on evidence, and its four entries
each have an additive version used first (SEM plan §3).

| SEM plan | Roadmap | What | This part | Path |
|---|---|---|---|---|
| — | A1–A10 | the world-clock release: injected clock, RNG and ids; stepped DN and live tick; prompt time; refractory split; salience 0.0 bug | §1, §2.1 | additive (defaults keep robots unchanged) |
| S1 | A1, A2 | `drift_rate` per world second | §2.2 | additive; renaming is batched |
| S2 | A2, C8 | `SensorReading.timestamp` is the body clock, never a percept | §3.1 | additive |
| S3 | C1 | propose and settle; the cerebellum observes at settle | §6.2 | additive (`ModulatorReceipt`); `pending` on `ModulatorResult` is batched |
| S4 | C2 | refusal kinds: stale is context | §6.3 | additive (a metadata key) |
| S5 | C3 | a declared direction per affordance (done to / done by) | §6 | additive first (a modulator attribute); `acts_on` is batched |
| S6 | C4 | the acting entity reaches `execute` | §6.4 | additive (an injected key); a signature change is batched |
| S7 | C5 | deliberation couples to fatigue through `coupled_to` | §2.3, §4.6 | additive |
| S8 | C6 | percepts vs instruments | §7.1 | additive, if `modality:` can carry it (unverified) |
| S9 | C7 | a versioned SEM vocabulary; a CC3 declaration on `ModulatorResult` | §6 | additive |
| S10 | C8 | `world_set_axis` per part; `FailureMode.last_fired` on world time | §7.2 | additive (unverified against `main`) |
| — | B8 | an SCN entrained by world light, phase exposed as an estimate | §3.3 | additive, earned by T1 |
| — | B9, B10 | the prompt's time of day from the agent's own time sense; an interval sense | §3.2 | additive, earned by T1 and T2 |
| — | C9 | cancellable deliberation with a world-time deadline | §4.3 | additive |

## 9. The tick and sub-tick time (for `phase1/sim-clock`)

- **The question:** at `tick_us` = 100,000 (0.1 s), the fastest possible response is one tick, two to four times a
  spinal reflex (25–50 ms, *to verify*). A 200 ± 50 ms reaction rounds to about the size of its own spread
  (engine_mapping.md §2.3, skeptic.md §3). Conversation gaps of ~200 ms are only two ticks.
- **The proposal** (decided in sim-clock, measured first):
  1. **Keep the tick for physics.** Physics keeps its 0.5 s period regardless of the tick.
  2. **Stamp agent events in world microseconds below the tick:** percepts, crossings, intents and speech tokens.
     The applier applies intents at tick boundaries, in canonical order: tick, then sub-tick time, then actor, then
     sequence. That extends `boundaries.md` §6's ordering with the sub-tick key.
  3. **If reflex arcs need to act below one tick,** the substrate steps k times inside a tick on the same frame, for
     reflexes only (engine_mapping.md §2.3). The alternative is a smaller tick, which costs agent and host overhead
     per world second but not physics.
- **If neither lands,** a reflex latency below one tick is recorded as a Known gap, with numbers.
- **Lane hand-off counts inside the modelled latency.** Intents are scheduled at `observed_tick + L_bio`, and a
  configuration where `L_bio` is shorter than the lane's minimum is refused. So moving the substrate inline later
  changes nothing an NPC experiences (`boundaries.md` §7.1).
- **Timing data** lives in `data/agents/timing.yaml`, in microseconds, versioned and strictly loaded, and is
  converted to ticks at load, with a check that rounding stays within tolerance. Changing `tick_us` is then a reload,
  not a refactor.

## 10. Experiments (Maxim cradles, off the game ledger)

These are pre-registered in Maxim's process, and run as cradles with an engine-only fixture body. Game runs never go
on Maxim's ledger (`boundaries.md` §8.4). From skeptic.md §5, with the arms, predictions and kill criteria there.

| Exp | Question | Arms | Kill criterion |
|---|---|---|---|
| **T1** | Does perceived time of day carry behavioural weight? | exact SCN phase; the entrained oscillator with light; the same with light removed for N days | if the oscillator arm can't learn food anticipation within the margin of the exact arm, the exact phase stays a marked ANALOG and the gap is filed as a Maxim finding |
| **T2** | Does state-dependent timing change what is learned, not only how fast? | fixed latency; latency modulated by fatigue and circadian phase; a shuffled control with the same latencies but no link to state | if the modulated arm doesn't beat the shuffled control on the scheduling metric by a pre-registered effect size, state dependence is game feel only (`[engineering]`) |
| **H2** (hybrid draft) | At what deliberation latency in world time does competence collapse? | stub latency 0, 1, 3, 10, 30 world s | calibration, not a claim: it sets `D_onset` (§4.2) |

The refractory window and habituation curves are manipulation checks in T1 and T2, not results: they hold by
construction.

## 11. What this supersedes in `realtime_lanes_coop.md`

| There | Here |
|---|---|
| §4.3 "A thought applies on the first tick after it arrives" | Each segment lands at its modelled world time; early results are held (§4.2) |
| §4.3 "With live models, thinking speed in world time depends on the dial… measured rather than hidden" | Thinking speed is modelled and dial-independent; late thoughts dilate the world (§4.1, §4.4) |
| §4.3 abandonment by `max_age_ticks` as the default | Dilation is the default; abandonment is an explicit, logged host policy (§4.4) |
| §4.3 a stale refusal is "something it can learn from" | Stale is context, never credit, OPEN until C2 (§6.3) |
| §4.3 "a thought result is a pure value" | Holds once generate vs apply lands (C1); mode (a) runs Maxim's tool loop until then (§6.2) |
| §9 Q1 "don't hold the world for a late thought" | Held in wall time, never in world time (§4.1) |
| §4.4 tier 3 "live models aren't reproducible" | With modelled landing times and the response cache, reruns with real thoughts reproduce (§4.7); replays were always exact |

Everything else in §4.3 stands: one thought in flight per NPC, the priority queue, the hybrid meters, and the
fixed-latency test stub.

## 12. Open questions and divergences

### 12.1 For the owner

1. **Who decides a thought's kind?** The agent's policy at request time (proposed), or the host from context. It
   sets `D_onset`, so it decides how long an NPC takes.
2. **The dilation banner.** When deliberation slows the world, does the player see the cause ("the ripperdoc is
   thinking"), or only a slower clock? The proposal is that they see it.
3. **How much of P0's conversational repertoire to stub in Phase 1,** before the hybrid line exists: none, fixed
   backchannels, or fillers too.
4. **Whether speech's world-time stamps are per word or per syllable.** Per syllable is finer, and costs more data in
   frames.
5. **The cognitive reserve's name and shape:** one reserve, or one per kind of effort.

### 12.2 Known OPEN divergences (each with a red gate when there is code)

- Real Maxim reads the host clock on the live path: about 880 reads. Closes with tier A.
- Two clocks reach one agent: the membrane stamps world seconds, Maxim's own sensors stamp epoch seconds (BF-11).
  Closes with A2 and S2.
- Stale refusals book NEGATIVE under mode (a). Closes with C2.
- The SCN phase is an oracle: the host calendar today, exact world phase after A7. Closes with B8, if T1 earns it.
- Region sensors are omniscient instruments that NPCs can read. Closes with the Phase 4 perceiver half of B-13, and
  with C6.

### 12.3 Inconsistencies found across the sources

- **`boundaries.md` v2 §9.3** lists "the cerebellum honours `outcome_valence: neutral`" and "finish `modulated_by` for
  the fatigue coupling". Both are wrong, per the SEM plan's verification against Maxim's code:
  - Valence isn't a cerebellum input, and the ask is to move its observation to settle (§6.2).
  - Fatigue's hook is `EntropicDriveSpec.coupled_to` (§2.3).

  Fold this into boundaries at its next revision.
- **Count mismatches:** roadmap A5 says about 38 `uuid4` calls, 39 global `random` uses and 36 timestamp defaults;
  the time audit says 36, 28 and 35, and boundaries' summary of it repeats the audit. Both are greps, and the
  world-clock release PRs should replace them with a call-graph walk.
- **The noise source:** skeptic.md §5 draws perceived-time noise from "the world RNG"; `boundaries.md` §7.3 and
  engine_mapping.md §5.2 use a per-NPC stream. The per-NPC stream wins (§3.4).
- **`realtime_lanes_coop.md` §4.3** contradicts lesson 9 on stale refusals, and §9 Q1 contradicts O4 in wall time.
  Both are superseded in §11.
