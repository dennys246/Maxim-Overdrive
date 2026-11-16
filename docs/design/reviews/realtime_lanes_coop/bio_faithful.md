# Bio-faithful integration: design review of `docs/design/realtime_lanes_coop.md` (v0, 2026-11-15)

Reader: Bio-faithful integration lens (`docs/code_review.md`). Overdrive at 52e64f0; Maxim read at 4b773ef8
(read only). Every claim below about Maxim cites the file it comes from.

**Verdict.** The real-time-with-pause decision is right for Maxim's mechanisms, and so is the core rule that a
tick never changes size. Holding for a thought is also the bio-faithful choice (finding 5). But §3 counts three
Maxim clocks, and Maxim has at least six that matter. Every one it leaves out runs on `time.time()`, so decision
2's promise, that NPC behaviour doesn't depend on the dial, is false for hunger, fatigue, reflexes, NAc credit and
sleep. The per-tick "substrate step" in §2 is the `aut_mode="hybrid"` design that Maxim's hybrid plan rejects.
Sleep and consolidation are missing entirely, and in a persistent world they never fire. Phase 3 items 10 to 13 are
the right direction but incomplete. Item 10 contradicts a recorded Maxim owner decision without saying so.

Counts: 4 BLOCKER, 8 SHOULD-FIX, 4 NIT.

---

## BLOCKER

### 1. §3 misses half of Maxim's clocks, so NPCs still live on the host's wall clock under the dial

**Location:** design §3 table and the Phase 3 list; decision 2; §1 "The dial".

**What Maxim actually reads** (all wall clock, none named in §3):

| Mechanism | Wall-clock read | Under pause / 0.25× / 30× / a held tick |
|---|---|---|
| Drive drift (hunger, fatigue, cold) | `embodiment/body.py::Embodiment.evaluate_failures` computes `drift_dt = time.time() - self._last_poll` and calls `tick_vital_drift(drift_dt)` | NPCs get hungry while the world is **paused**. At 30× they starve 30 times slower per world day. A held tick (waiting on a thought) adds hunger with no world time passing. |
| DN reflex timing | `default_network/background_tasks.py::OperationThrottler.should_run` (novelty and salience at 10 Hz, spatial map at 5 Hz, behaviours at 15 Hz, all on `time.time()`); `inhibition.py` auto-release at 5 s; `attention/gaze_history.py` IOR recovery at 2 s; `arbiter.py` `min_switch_interval` 0.3 s; `inference/segment_vision.py::NoveltyTracker` focus decay at 10 s and recovery at 20 s; idle exploration at 3 to 8 s | At 30× (300 ticks per wall second) novelty updates every 30th tick and voluntary suppression lasts 150 world seconds. At 0.25× every throttle fires every tick and suppression lasts 1.25 world seconds. During a hold or a pause, IOR recovers, novelty habituates and inhibition releases while the world is frozen, so the reflex fires against the deliberation on the first tick after it resumes. |
| NAc decay and credit windows | per-tick decay (`NACConfig.reward_bias_decay_tau` = 50 "ticks", `cluster_reward_bias_decay_tau` = 300); `temporal_window_seconds`; `nac.py` decision provenance `tick = int(time.time() - _sim_start)` | A "tick" is whatever calls it (`docs/plans/experience_clock_decay.md`, "What a tick is today"). Called at the world's 10 Hz, tau = 300 becomes 30 world seconds of fear and reward memory. |
| Sleep forgetting | Hippocampus `sleep()` and ATL forget by `time.time()` against `accessed_at` (`experience_clock_decay.md` §(f), "Stated inconsistency (kept by Q5)") | A game left paused overnight makes NPCs forget at their next sleep. |
| Percept and memory timestamps | `agents/percept_factory.py` stamps `time.time()`; `integration/memory_hub.py::_on_memory_captured_scn` bins by it | SCN bins hold the player's hours, not the NPC's (finding 2). |

**The concrete failure:** a player pauses for lunch. The world shows no time passing, but every NPC comes back
hungrier, with habituated novelty and recovered IOR, and on the next sleep forgets as if an hour had passed.

**Fix:**
- Rewrite §3 as a complete clock inventory.
- Add Maxim **#1361 (`docs/plans/experience_clock_decay.md`, PROPOSED, owner decisions Q1 to Q9 taken
  2026-10-17)** to Phase 3 as a hard prerequisite. It already moves NAc decay, eligibility and temporal windows
  (S3a, S3b), body drift (`Embodiment.advance(dt)`, S4, whose gate G4 is "a 30 s pause adds zero drift") and
  `decay_all` (S5) onto the experience clock. The game should not reinvent it.
- Add the items #1361 leaves out:
  - DN timing on an injected world clock (fold into item 11; finding 3).
  - Sleep forgetting on experience time. #1361's Q5 deliberately left it alone, so this asks Maxim to revisit Q5.
  - Percept timestamps from the world clock (fold into item 10).
- Add a Maxim-side lint: no `time.time()`, `time.monotonic()` or `TemporalSignature.now()` in the substrate path
  outside named clock seams. #1361 §Enforcement already proposes one, so extend its allowlist rather than add a
  second.

Until these land, decision 2 must be worded as "world physics doesn't depend on the dial; NPC substrates do,
until Phase 3 items 10 to 14 and #1361 land".

### 2. Item 10 (an injectable SCN clock) contradicts a recorded Maxim decision, is incomplete, and would mix clocks if done halfway

**Location:** design §3 and Phase 3 item 10; Maxim `time/temporal_signature.py::TemporalSignature.now` and
`from_timestamp`; `docs/plans/experience_clock_decay.md` §(g).

- **What the SCN computes.** It is not an entrained oscillator driven by elapsed time. `SCN` bins memories by the
  calendar phase of their timestamp (Bio-mapping: FUNCTIONAL). `OscillatorNetwork.observe` soft-resets four phases
  toward the phase of the observed timestamp, then takes one fixed Euler step (`dt` = 1/24 day). The zeitgeber is
  the timestamp itself (`docs/time.md`, "Zeitgebers (time cues) → TemporalSignature"). "~20k oscillators /
  entrainment inputs" is an ANALOG row in `bio_faithful_roadmap.md`.
- **So injecting the world's clock is consistent with Maxim's own model**, and light entrainment is not something
  Maxim has (finding 7). The design's proposal is the right shape.
- **The Maxim decision it contradicts.** `experience_clock_decay.md` §(g), "What stays wall-clock on purpose",
  lists "SCN phases, `TemporalSignature` similarity: host calendar by design". Item 10 reverses that. Maxim's
  process requires the item to say so and argue it: the agent's world is not the host, as with experience time.
  Otherwise it is refused, or worse, patched around here.
- **Incomplete.** There are at least 12 `TemporalSignature.now()` call sites on the substrate path:
  - `similarity/encoder.py` (×3, the NAc eligibility temporal anchors)
  - `decisions/nac.py:3629` (anchor fallback credit)
  - `decisions/temporal_credit.py` (×2)
  - `embodiment/body.py:559` (drive temporal events)
  - `bridges/tool_pain_bridge.py` (×2)
  - `bridges/escalation_bridge.py` (×2)
  - `agents/exec_agent.py` and `agents/statistician_agent.py`
  - `retrieval/temporal_signal.py`, where "last night" is resolved by `dateparser` against host now
  - `percept_factory.py` timestamps, which feed SCN registration

  `from_timestamp` uses `datetime.fromtimestamp`, which is **host-local time zone with DST**. The same world epoch
  then gives different circadian phases on two machines, and the phase jumps an hour twice a year.
- **The failure if only "the SCN" is injected:** memories bin on world time, but NAc temporal anchors are stamped
  and compared on host time (`nac.py` anchor fallback: `anchor_sig.similarity(now_sig)`). Temporal-fallback credit
  then goes to whatever happened at the same *host* hour, a credit signal built from the player's schedule.

**Fix:** frame item 10 as "one clock source for every `TemporalSignature` producer and for percept timestamps;
phase computed from world seconds and the world's day, never `datetime` local time". Name the decision it revisits
(§(g)), the brief invariant it touches (`docs/agents/bio-memory.md`, SCN temporal credit), and the lint that guards
it. Tag: **ANALOG**, kept on purpose (the calendar is still the zeitgeber; only whose calendar changes).

### 3. The per-tick "substrate step" is the hybrid mode Maxim rejected; items 11 and 12 aim at the wrong targets, and the DN reflexes would have nothing to react to

**Location:** design §2, "Substrate and the hybrid runtime" (step 3 of the simulation lane: "drives, reflexes,
`NAc.recommend_action` over its affordances", every tick, with deliberation alongside); Phase 3 items 11 and 12;
`docs/roadmap.md` Phase 4 ("Movement runs in substrate-primary mode (no LLM); speech goes to the LLM").

- **Two layers in one step.** `NAc.recommend_action` is substrate-primary's *agent-level action selector*
  (`docs/substrate_primary.md`; `runtime/substrate_proposal.py::propose_via_substrate`), not a reflex. Maxim's
  hybrid plan (`docs/plans/deferred/hybrid_substrate_reflex_runtime.md`, front-gate) rejects interleaving it with
  the LLM: "Hybrid is not 'sometimes substrate, sometimes LLM cognition'; it's 'a reflex runs *underneath*
  continuous LLM cognition'". There the reflex is a DN `Behavior` that calls `recommend_action` on its *own*
  isolated NAc (A3/BL-4), so its learning can't leak into the LLM's prompt. The design runs the agent-level
  selector and the LLM over the same NAc. Roadmap Phase 4's movement/speech split is a third architecture that
  neither Maxim mode supports.
- **Selecting every tick is dithering.** Calling `recommend_action` at 10 Hz re-selects ten times a second.
  - Each call increments `visit_count`, the explore term's driver, so exploration collapses.
  - Per-tick decay at 10 Hz rescales every tau (finding 1).
  - There is no action duration or hysteresis at the NAc level. DN's arbiter has hysteresis; NAc doesn't.

  In biology, action selection is gated by action completion or interruption. The NPC would start an action
  every 100 ms and never finish one.
- **Item 12 targets the wrong class.** `AgentPool` (`runtime/agent_pool.py::run_turn`) is a text turn: store an
  observation, make one LLM call, write one NAc `observe`. It has no body, no drives and no DN. A "per-tick
  substrate step on `AgentPool`" means building a new runtime. The thing to step is the agent loop's live tick:
  `runtime/loop_gates.py::_loop_live_tick`, the experience driver, `Embodiment.advance` (after #1361), §8.5 bio
  maintenance, and the proposer.
- **The DN reflexes would be starved.** `DefaultNetwork._process_tick` returns early `if not detections`
  (detections are YOLO-style pixel boxes). Its behaviours are visual orienting, startle, social attention and idle
  gaze. The world produces no detection stream until Phase 2's light and visibility work, and even then it needs
  the hybrid plan's BL-2 non-visual cue channel. A world-stepped DN in Phase 4 would run pain (`PainCircuitBridge`)
  and entity novelty (`on_percept`) and nothing else.
- **The hybrid plan is DEFERRED.** Its revive trigger is "a second robot body physically exists", and the
  2026-10-07 note says that trigger is not re-keyed. Using it needs a Maxim owner decision to re-key it, or a new
  plan for simulated bodies.

**Fix:**
- Rewrite step 3 as the hybrid plan's two layers:
  - (a) world-stepped DN behaviours: the reflexes, on an isolated reflex NAc;
  - (b) agent-level selection, either substrate-primary (`recommend_action`) **or** LLM deliberation per NPC mode,
    run when the current action completes or is interrupted, not every tick.
- Retarget item 12 to "an externally stepped agent live tick: `step(world_dt)` with no thread, no sleep and no
  wall clock".
- Extend item 11 with:
  - every DN wall-clock read (the throttlers, inhibition, IOR, arbiter, `NoveltyTracker`, idle timers, the
    head-sync timer) on the injected clock;
  - BL-2 (a non-visual cue channel, so `_process_tick` runs without detections);
  - A3 (an isolated reflex NAc);
  - A4 (IOR for target-less proposals);
  - SF-1 (per-behaviour live suppression);
  - an injected RNG. DN draws from the global `random` (`movement_utils.py`, `gaze_manager.py`), which breaks
    replay.
- Add item 15: re-key the hybrid plan's revive trigger, or write a simulated-body reflex plan, through Maxim's
  four-lens process.
- Phase 4's movement/speech split needs its own Maxim plan.

Tag the split as **OPEN** until that plan decides it.

### 4. Sleep and consolidation are missing, and in a persistent real-time world they never happen

**Location:** design (absent); Maxim `integration/memory_hub.py::sleep` (it *is* `on_session_end`);
`memory/hippocampus_consolidation.py::sleep_with_clustering`; `bio_faithful_roadmap.md`, "Sleep replay":
"Session-end only today… consolidation happens during rest, not only at 'death of session'".

- **Sleep only at session end.** In Maxim, consolidation runs only at session end. A world that runs
  continuously, and is saved and resumed, never ends an NPC's session, so the NPCs never consolidate: no replay, no
  promotion, no ATL/AG consolidation. Exp 64 already notes it relies on "the one `sleep()` in the cradle".
- **Clustering runs on host hours.** `sleep_with_clustering` keeps the best representatives per SCN `(hour, day)`
  cluster. With host-clock bins at 30×, a world day takes 48 wall minutes. All of it lands in one or two host-hour
  clusters, and consolidation prunes a whole lived day down to a handful of memories.
- **Wall cost.** Sleep can block for seconds (`on_session_end_lightweight` docstring). Run in the simulation lane,
  it stalls every NPC's world.

**Fix:**
- Make NPC sleep a world behaviour: a fatigue drive, plus the SCN phase, plus a bed or rest affordance on the tile
  (the two-process shape, homeostatic S plus circadian C; **OPEN**: Maxim has both parts but no coupling, and
  `CircadianContext.phase` "wake/rest/sleep" has no producer).
- While the body is asleep in the world (no actions, sensors gated), consolidation runs as a thinking-lane job
  whose result applies at wake time, under the same deadline semantics as a thought.
- Add a Phase 3 item: a consolidation entry point that doesn't end the agent's session (or a session-per-wake
  protocol), on experience time (finding 1). It joins Maxim's Stage B idle-time coordinator
  (`bio_faithful_roadmap.md`, DN initiative), which is the **EARN** path there.

---

## SHOULD-FIX

### 5. Open question 1: hold the world. It is the bio-faithful answer, with four conditions

**Location:** §2 "The thinking lane and determinism"; §8 Q1.

- **Why hold.** Maxim has already decided this principle twice:
  - `runtime/experience_time.py`: in turn-based worlds "a slow model must not make the agent forget faster";
  - `experience_clock_decay.md`: decay must not be "bound to thinking speed", whose rate varies about 10× across
    hardware.

  With apply-on-arrival, an NPC's world-time reaction speed is a property of the host's GPU, its load and the dial.
  That is the caricature. With a hold, deliberation time `d` is experienced world time, the same on every machine,
  which is what a mind's thinking latency should be. A fixed `d` per request type, independent of content, is an
  **ANALOG**; name it.
- **Condition (a): the substrate runs during `d`.** In Maxim, voluntary action suppresses the reflex while it is
  *executing* (hybrid plan, "Motor arbitration"), not while it is being deliberated. So reflexes must keep running
  for ticks T to T+d.
- **Condition (b): bottom-up interruption.** Pain or salience escalation through the thalamic gate (`gate.py`)
  must be able to cancel an in-flight thought, as pain interrupts thought. Item 13 says "cancellable" but not by
  whom. A cancelled thought must release the hold, and the log must record it.
- **Condition (c): validate against the current world.** A thought formed on the percepts of tick T is validated
  at T+d through SEM `requires` against the world as it is at T+d. If it no longer applies, it is a logged tool
  failure, credited as Maxim credits failures (`docs/plans/tool_failure_credit.md`), never silently dropped.
- **Condition (d): headless never times out.** A wall timeout makes the outcome depend on the host again.
  Headless (cradles, experiments) must hold with no timeout, and fail with a typed abort instead
  (`thought_failed` is Exp 64's G0 abort; finding 12).

### 6. The oscillator advances one hour per observation, not per hour of elapsed time

**Location:** Maxim `time/oscillator.py::OscillatorNetwork.observe` (step 5: `integration_steps` × `step()` with
the fixed `dt` = 1/24 day). Item 10.

**Failure:** the game produces tool events far more densely than Maxim's sessions do, and every NPC tool use
records one (`tool_pain_bridge.py` is the only live producer; `scn_event_producer_gap.md`). Free-running, the
oscillator moves an hour per event and is pulled back 10% (`blend` floor 0.1). Its phase is then a function of
how often the NPC acts, not of the world's time. `prediction_error_ema`, `temporal_anomaly_score` and
`predict_next_occurrence` stop meaning anything, and anticipatory credit (dormant today) would be wrong when
revived.

**Fix:** item 10 should include "the oscillator integrates the elapsed world time since its last observation".
**EARN**, as a Maxim bug fix. It also lands under the SCN event-producer gap's front-gate question.

### 7. The day-length knob: the design's options model perfect entrainment, and light is not a Maxim entrainment input

**Location:** decision 3; §3 ("a day-length-aware `TemporalSignature` or a world clock that reports phase"; "A
circadian clock is entrained by light… until then… no cue to entrain to"); §8 Q5.

- **Perfect entrainment.** Both options redefine the agent's day as the world's day. The NPC's SCN then entrains
  perfectly to any day length. A biological SCN has an intrinsic period (about 24.2 h in humans) and a limited
  range of entrainment. Outside that range it free-runs, which is forced desynchrony. "An experiment in time
  dynamics" is only meaningful with two separate quantities: the world's day (the cue) and the agent's intrinsic
  period (the oscillator's ω, `_NATURAL_FREQUENCIES`).
- **No light entrainment in Maxim.** Phase 2 light would not entrain Maxim's SCN. The entrainment inputs row is
  ANALOG, and making it EARN needs a new argument in Maxim.
- **No week or month.** Weekly, monthly and annual phases have no definition in a 30 h world (`/7`, `/31`,
  `/365.25` of what?).

**Fix:**
- Q5's answer: v0 uses a world clock that reports phase, with the intrinsic period equal to the world day. State
  it as **ANALOG: perfect entrainment**.
- Varying the day is a Maxim experiment with its own pre-registration (the standing rule keeps game runs off the
  ledger), and it needs (i) ω separate from the world day and (ii) an entrainment input: light as a percept, flipped
  to EARN in Maxim. Until then, say the knob has no bio meaning beyond rescaling.
- Define the week and year of a non-24 h world in the world's config.

### 8. Open question 3: at 1× the rhythms decision 1 cites can't be learned, and drive rates are tuned for 2-minute experiments

**Location:** decision 1; §8 Q3; drive `drift_rate` in Maxim bodies (`bodies/infant_humanoid.yaml`: "reaches 0.7 in
~120s (tuned for 15-turn PoC)").

- **Failure at 1×.** A player who plays two hours each evening on a 24 h day at 1× gives NPCs a life of 7 to
  9 pm. They never see night, never sleep (finding 4), never fill more than two or three SCN hour bins, and never
  see a week. Decision 1's reason for real time ("SCN learns daily and weekly rhythms") isn't met.
- **Failure of the rates.** Drive rates tuned in seconds make an NPC cross hunger threshold every two minutes of
  world time, hundreds of times a day.

**Fix:**
- Q3, from this lens: the world must deliver whole days at a rate the NPC lives through. Either the default dial
  is well above 1× (24× gives a day an hour), or night passes in fast-forward or sleep-skip. Either way, every NPC
  sees full cycles.
- Calibrate drive rates in world-day terms in `data/` (meals per day, sleep per day). Never inherit a Maxim
  fixture's per-second rate.

### 9. The experience clock: say which declaration, because the default one is wrong under the dial

**Location:** §3 row 1 ("a percept source declares the world's time"); Maxim
`runtime/experience_time.py::ExperienceClockDriver`.

- **The default is wrong.** The driver has two kinds. `realtime`, the default (and #1361's Q6 choice for the
  survival world), uses monotonic wall time minus pause. Under the dial that is wrong: at 30× an NPC forgets 30
  times slower per world day.
- **The right kind already exists.** The `turns` kind is right and needs no Maxim change: `experience_turns()`
  returns the tick count and `experience_us_per_turn` = `tick_s` × 10⁶ (100,000). Pause, slow motion,
  fast-forward and a held tick are then all correct automatically.
- **Who calls it.** The driver advances "once per live loop pass". The world-stepped live tick (item 12, as
  retargeted in finding 3) has to call `on_live_pass`. Otherwise `ExperienceClockStalled` fires at session end, if
  there ever is one (finding 4).

**Fix:** state the tick-as-turn declaration in §3, and note the driver is "chosen once per loop run, so a world
cannot switch kinds" (the module's docstring). Ask Maxim for a docstring note that a "turn" may be a fixed world
tick. That is a doc change, not a fork.

### 10. Efference copy and one-way suppression: the design names suppression but not efference copy, and Maxim has neither wired

**Location:** §2 "Substrate and the hybrid runtime"; Maxim hybrid plan SF-1 and SF-2;
`default_network/network.py::_run_loop` (`if not self._inhibited: self._process_tick()`).

- **Suppression is all or nothing.** Maxim's suppression is global. Inhibiting DN skips the whole tick, and
  `inhibited_behaviors` comes from mode config. "Suppresses the conflicting reflexes, one way only" needs the
  SF-1 per-behaviour live hook, which the hybrid plan calls "net-new wiring". As things stand, a voluntary
  `ignite` would also suppress the pain reflex.
- **No efference copy.** The hybrid plan calls efference copy "mandatory, not optional" (SF-2). When the reflex
  moves an NPC's avatar, the deliberation that is in flight or comes next must get the self-motion signal.
  Otherwise the LLM sees the world shift and takes its own movement for the world's. With a hold, the thought at
  T+d was formed before a reflex at T+k moved the body.

**Fix:** add both to Phase 3 (in item 11), and state in §2 that reafference reaches deliberation through
`body_state`, not through a new channel.

### 11. D1: drives with no world relief, and host state that must never reach a percept

**Location:** design §2, last bullet (good as far as it goes); Maxim `docs/experiments/DESIGN_REVIEW.md`
environment lens D1.

- **Drives with no relief.** The design never says the world must afford the actions that relieve a drive. The
  Phase 1 tile (clinic and alley) has no food, water or bed as SEM affordances. With drives drifting and nothing
  to relieve them, entropic drives cross their deprivation thresholds. That emits drive pain without end, and
  fear learning attaches to whatever is present.
- **Host state the NPC must never sense.** The time of day an NPC uses is a calendar it is handed. Maxim accepts
  that as its zeitgeber analog (finding 2), so name it ANALOG. The dial, the effective scale, dilation, thought
  deadlines and `d` must never reach an NPC's percepts.

**Fix:**
- Either the Phase 4 tile authors relief affordances for every drive the bodies carry, or those drives get
  `drift_rate: 0` as world-owned, the way Maxim's `minecraft_player.yaml` does (**ANALOG**, named).
- Add a test row (B14 style) that the percept builder reads only `World` state, never host or session state.

### 12. Exp 64 and Phase 4: the real-time decision changes the pre-registration draft

**Location:** `docs/maxim_upstream/exp64_cradle_conduct_prereg_DRAFT.md` (Claim: "on the shipped NPC path"; G0;
"drive drift is frozen during the probe"; Probe; Aborts); roadmap Phase 4.

- **(a) The host clock confounds the arms.** While `TemporalSignature` reads the host clock (finding 2), arms run
  one after another at different host hours get different temporal-anchor credit and different SCN `(hour, day)`
  clusters at the cradle's `sleep()`. That is a confound unrelated to the betrayal. Pin the world clock in the
  harness, or list item 10 as a prerequisite.
- **(b) "The shipped NPC path" is now ambiguous.** The draft's mechanism is `AgentPool.run_turn`, a turn. Under
  this design the game's path becomes the stepped live tick plus the thinking lane. Either 64a tests Maxim's turn
  path, said explicitly, with the game path a later replication, or items 10 to 13 and #1361 become
  prerequisites.
- **(c) A failed thought is an outage.** `thought_failed` is exactly an LLM-outage fallback, which is G0 and a
  typed abort. Headless must never time out (finding 5d).
- **(d) Time between encounters becomes a parameter.** In a ticking world, the world seconds between probe
  encounters set recency, experience-clock decay and novelty habituation toward the player. Pre-register them in
  ticks, identical across arms.
- **(e) Freezing drift needs a mechanism.** "Drift frozen" means not calling `Embodiment.advance` during the
  probe, which exists only after #1361 S4. Name that mechanism, so freezing is not a harness patch to
  `evaluate_failures`.

---

## NIT

### 13. Open question 4: 10 Hz is enough for DN, provided its subsystems run on world time

**Location:** §2, the line "whether a reflex loop at the world's tick keeps its job"; §8 Q4.

- **The 30 Hz throttles at 10 Hz.** On world time, novelty (10 Hz), salience (10 Hz) and the spatial map (5 Hz)
  are unaffected by a 10 Hz tick. Behaviour evaluation drops from 15 to 10 Hz. The arbiter's 0.3 s minimum switch
  is 3 ticks, IOR's 2 s is 20 ticks, and inhibition's 5 s is 50 ticks.
- **Reflex latency.** Quantized to 100 ms, inside the range of human withdrawal and orienting reflexes (tens of ms
  to about 200 ms).
- **The exception.** `salience/movement_detector.py` scores in pixels *per frame* (`velocity_normalization` = 50,
  `frames_stationary`), which is rate-dependent: at 10 Hz the per-frame velocity triples. That needs per-second
  normalization in item 11.
- **The real limit is the percept rate.** Temperature changes only on physics steps (2 Hz). That is physically
  fine for heat, provided SEM sensors sample cells **every tick**, so contact pain arrives at tick latency. Say so
  in §1.

### 14. Phase 2 visibility shaped as YOLO detections would be a synthetic camera

**Location:** §2 ("SEM sensors over cells, sound and light from Phase 2"); DN's pixel-space detection schema.

Feeding DN means producing pixel boxes in a 640×480 frame. If Phase 2 renders visibility into that schema, the world
is fabricating a sensor's output format rather than affording a signal. **OPEN.** The cleaner path is the hybrid
plan's BL-2 non-visual cue channel carrying bearing and range from the light and visibility field.

### 15. Determinism items that also starve the substrate

**Location:** Maxim `embodiment/body.py::_emit_drive_temporal_event` (`uuid.uuid4()`); DN's global `random`; SCN
`BoundedBin.add` (`registered_at = time.time()`).

"Replays read results from the log and never call a model" doesn't make replay bit-identical if the substrate
itself reads the clock or the global RNG. Cross-lens with Determinism. Fold into item 11's injected clock and RNG,
and the lint in finding 1.

### 16. §3's description of the Default Network is out of date

**Location:** §3 table row 3 ("its own 30 Hz thread with `time.time()` and `sleep`").

The row is true, but DN's Bio-mapping tag is NAME-ONLY: it is a salience and orienting layer, not the default mode
network. That matters for Phase 4: the "idle cognition" an NPC needs (replay, prospection) is Maxim's Stage B
coordinator, not DN.

---

## Proposed Phase 3 list (folding 1 to 4 and 10)

| # | Item | Status in Maxim |
|---|---|---|
| — | #1361 experience-clock decay, S1 to S5 (NAc decay, eligibility and windows, `Embodiment.advance`, `decay_all`) | PROPOSED, decisions taken: a prerequisite, not new |
| 10 | One world clock for every `TemporalSignature` producer and for percept timestamps; phase from world seconds and the world's day, with no `datetime` local time; the oscillator integrates elapsed time; revisits `experience_clock_decay.md` §(g) | new; ANALOG kept |
| 11 | Externally stepped DN: `step(world_now)`; every DN timer on the injected clock; injected RNG; BL-2, A3, A4, SF-1, SF-2; movement scored per second | new, plus parts of the hybrid plan |
| 12 | An externally stepped agent live tick (not `AgentPool`): `step(world_dt)` driving the experience driver, `Embodiment.advance` and the proposer, on action completion | new |
| 13 | Cancellable deliberation with a world-time deadline, cancellable by bottom-up escalation (joins item 7) | new |
| 14 | Consolidation without ending the session, on experience time (revisits #1361 Q5); with Stage B idle replay | new; EARN |
| 15 | Re-key the hybrid plan's revive trigger, or write a simulated-body reflex plan; decide the Phase 4 movement/speech split | an owner decision in Maxim |

Each goes through Maxim's own issue, plan and four-lens review. None is patched here.

---

## What I checked and found faithful

- **A fixed `tick_s` that the dial never changes.** This is exactly what Maxim's experience clock and #1361 want:
  time quanta independent of host speed. It makes the `turns` declaration (finding 9) a clean fit with no Maxim
  change.
- **The wall clock never reaches `World`, and headless is the dial at "unpaced".** Correct, and it is the same
  rule Maxim applied to decay ("not bound to thinking speed").
- **Thoughts scheduled in world time.** This is the bio-faithful choice (finding 5). The log-every-result rule
  keeps the NPC's lived history replayable.
- **NPCs act through the same SEM modulators and intents as the player, and get percepts only from the world.**
  This is D1 as written, apart from the gaps in finding 11.
- **One-way suppression.** Correctly named as Maxim's design (hybrid plan SF-1). Only the wiring is missing
  (finding 10).
- **§3's characterization of `ExperienceClock`.** Accurate: the clock reads no clock, and its driver offers the
  turn-quantum mode.
- **§3's statement that the SCN and `TemporalSignature` read the wall clock.** Accurate (`TemporalSignature.now`,
  `from_timestamp`). Incomplete in scope (finding 2).
- **§3's statement that DN runs its own 30 Hz thread on `time.time()` and `sleep`.** Accurate
  (`DefaultNetworkConfig.update_hz` = 30, `_run_loop`).
- **Listing the Maxim changes under Phase 3 rather than shimming them here.** Correct, and in line with "keep
  Maxim untouched". The changes are only incomplete and need framing (findings 1, 2, 3).
- **The physics period (0.5 s) against NPC thermal percepts.** Heat fields change slowly enough that 2 Hz updates
  don't caricature thermal sensing, provided cells are sampled every tick (finding 13).
