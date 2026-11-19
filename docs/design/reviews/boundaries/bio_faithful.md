# Bio-faithful integration: review of `docs/design/boundaries.md` (47add00)

- **Lens:** Bio-faithful integration (`docs/code_review.md`), which is always on for design reviews. It also asks
  whether the game's evidence should push back on Maxim (CLAUDE.md, "Push back on Maxim").
- **Design commit:** 47add00 (`phase1/design-v2`).
- **Date:** 2026-11-16.
- **Counts:** 3 BLOCKER, 8 SHOULD-FIX, 4 NIT.
- **Read:** the design under review, and `realtime_lanes_coop.md` §4 and §6, `world_v2.md` §7 (P1 to P7),
  `world_model.md` §6, `research/states_of_matter/sem.md` §3b, `docs/maxim_upstream/exp64_cradle_conduct_prereg_DRAFT.md`,
  `lessons_maxim_in_games.md` (standards worktree), and the roadmap's Phase 3 (act-validation worktree, items 1 to 11).
- **Code read:** the membrane on `phase1/act-validation` at 2f200b5 (`sem_env/bridge.py`, `_compat.py`), and the
  installed pymaxim 1.3.3: `embodiment/tool_bridge.py`, `embodiment/cerebellum.py`, `embodiment/sem.py`,
  `embodiment/audio_localization.py`, `runtime/tool_dispatch.py`, `runtime/bootstrap.py`,
  `hardware/reachy/motor_backend.py` and `simulation/tools.py`. Nothing in Maxim was modified.
- **Correction to an input:** lesson 11 says `time.time()` appears in 178 pymaxim files. In the installed 1.3.3 it
  is 173 (`grep -rl "time\.time()"`). The conclusion holds either way.

## Verdict

The boundaries are mostly the right ones, and B-2, B-3 and B-9 are the ones that matter most to NPCs. But three of
them are worded in a way that either breaks what Maxim learns from an action or can't be satisfied by the design's
own allocation of work:

- **B-9** fuses "one door" with "`execute` returns intents". With today's Maxim, the second half makes every action
  look as if it did nothing, and books it as a success. That makes lesson 6 universal: today only `ignite` and
  phase changes are affected; after B-9, every action is.
- **B-3** seals a core that, according to `realtime_lanes_coop.md`, steps the agents. It doesn't say where the NPC
  substrate runs. Against today's Maxim, the tripwire it keeps would crash the tick, not merely flag it.
- **B-2** says only `sem_env` imports `maxim`, while B-1 gives cradle arcs and NPC authoring to the game and B-7
  gives experiments to a harness. Both need Maxim.

The membrane also has two properties no boundary addresses. It is omniscient (a region's sensors read global truth
from anywhere), and it is shape-checked only (the drift test compares three dataclasses, not what Maxim does with
them).

---

## BLOCKER

### BF-1. B-9's "`execute` returns intents" blinds Maxim's credit to every action, and books each one as a success

**Location:** `boundaries.md::B-9` ("The SEM modulator's `execute` becomes a producer of intents") and its
enforcement row ("`execute` returns intents"). Today's code is
`sem_env/bridge.py::StructureModulator.execute` / `apply`.

**What Maxim does with the return value** (pymaxim 1.3.3, `embodiment/tool_bridge.py::ModulatorAffordanceTool.execute`):
1. It calls `self._modulator.execute(...)` (line 576). If `success` is False, it returns a failure, which
   `runtime/tool_dispatch.py` (line 355) books as NEGATIVE.
2. On success, it reads every sensor of the acted-on entity **in the same call** (lines 580 to 590) into
   `entity_state`.
3. It measures Break-2 relief for world-owned interoceptive drives as (before, after) pairs, where "after" is read
   from `vital_metrics` right after `execute` returns.
4. If `entity_state` is non-empty, it trains the cerebellum on it: `observe_from_action(..., actual=entity_state)`
   (lines 860 to 890). The forward model's Rescorla-Wagner update learns absolute post-action values per
   (entity, modulator, affordance, parameter bucket), whatever the outcome valence.
5. With no `outcome_valence` in the metadata, mechanical success means POSITIVE (`tool_dispatch.py` lines 355 to
   361). The causal link starts at 0.50 confidence, which is above the 0.3 `min_confidence` gate from the first
   observation (Maxim's own comment at that site).

**Failure scenario (Phase 4, once B-9 has landed at sim-clock):**
- An NPC calls `crate_strike(energy_j=400)`. The membrane enqueues an intent and returns `success=True`.
- `entity_state` reads the crate's integrity unchanged, because the intent applies at the next tick.
- The cerebellum learns "after a strike, integrity = what it was". NAc books a POSITIVE causal link for a strike
  nobody has seen land.
- Two ticks later the player's own intent destroys the crate first, and the NPC's intent is refused at application
  as stale. The membrane has already returned, so there is no channel for that refusal: the POSITIVE stands.
- The same holds for `eat`. The measured pair is (0.4, 0.4), so the measured total is 0. `_measured_credit_total`
  stays unset and the flat +1 floor applies. The relief is never learned, which defeats Maxim's own R2 "Break 2"
  survival loop for every world-owned drive.

Today, `strike` is the one affordance whose effect lands inside the call (`damage.strike` runs in `_strike`). B-9
as worded removes it. Lesson 6 ("an action's effect may arrive after the call") becomes "every action's effect
arrives after the call". The design doesn't mention this.

**The fix.** B-9's real goals are one door, one log and no trust bypass. None of them requires `execute` to be
non-blocking. Separate the two, and say which `execute` contract ships:
- **(a) Blocking receipt (recommended until P3 lands).** `execute` submits the intent through the one door, then
  waits **in world time** until the simulation lane has applied it and published the frame after the next physics
  step. It returns a `ModulatorResult` built from the application:
  - `success` and `error` from the application, not from acceptance;
  - `metadata` from the application (`destroyed_volume_m3`, `absorbed_j`, `tick_applied`);
  - `measured_drive_transitions` from the before and after frames.

  This is Maxim's own precedent. `hardware/reachy/motor_backend.py::ReachyOrientMotorBackend.execute` blocks until
  the motion settles, then reports a measured transition (`sem_motor_binding.md` Phase 2). The wait is the body's
  reafference latency (one tick), not a wait for a thought, so it doesn't contradict `realtime_lanes_coop.md` §4.3
  ("nothing waits for a thought"). Say so explicitly. The wait needs a world-time bound and a rule for a paused
  world (a paused world is held, not timed out).
- **(b) Non-blocking intents.** If B-9 keeps this, it must not reach an NPC path until P3 and a tool-level item 16
  (BF-1's pushback below) are in Maxim. Until then, the membrane must return `outcome_valence: "neutral"` (D53: an
  unverified motion isn't a success), so that NAc books no POSITIVE. Record the cerebellum training on stale state
  as an OPEN divergence with a strict red gate. Without that marker, the cerebellum still learns zero deltas,
  because neutral valence doesn't gate `observe_from_action`.

The enforcement row then becomes: "every NPC act reaches cells only through the intent gate. `execute` returns
after application, with the application's outcome (a), or returns `neutral` and is gated on P3 (b)."

**Pushback to Maxim (new, merging P3 with item 16 at the tool level):**
- **What it argues against:** `ModulatorAffordanceTool.execute`'s single-call contract (act, read back, credit and
  train in one call: `tool_bridge.py` lines 576 to 916), and the "mechanical success means POSITIVE" default
  (`tool_dispatch.py` lines 355 to 361).
- **Why item 16 isn't enough:** "Generate vs apply" (`realtime_lanes_coop.md` §6, item 16) splits the agent turn but
  is silent on the tool bridge, where credit is computed.
- **The proposal:** split the tool into `propose(params) -> intent` and `settle(intent, outcome, before, after)`, and
  move cerebellum training, self_effect, measured relief and the valence into `settle`.
- **The precedent's wall clock:** the Reachy backend's measurement window is wall clock (`time.monotonic`,
  `time.sleep(0.1)`, `_MEASURE_TIMEOUT_S = 4.5`, lines 238 to 242). Under a dial, the credit window would then
  depend on wall time, so the generalised version must take an injected clock (it joins P5 and item 10).
- **A second point:** the cerebellum trains even when the tool reports `neutral`. Training a forward model on a
  state the tool itself says it couldn't verify is the "fabricated sign" that `sem_motor_binding.md` forbids for
  NAc. `observe_from_action` should honour it.

### BF-2. B-3 seals a core that the lanes design says steps the agents, and doesn't say where the NPC substrate runs

**Location:** `boundaries.md::B-3`. The forbidden list includes `maxim`, and the core is "later the `Simulation`".
The tripwire "remains for... an unseeded `random.Random` built inside Maxim". See also `boundaries.md::B-8`, where
`sem_env` is layer 6 and above `Simulation` (layer 5).

**The contradiction.** `realtime_lanes_coop.md` §4.1 says the simulation lane "owns Simulation (and through it World
and agents)" and that "agents step inside the simulation lane's tick". Its §4.4 says the tripwire "makes `time`,
`uuid` and the global `random` *raise* inside `Simulation.step`". B-3 and B-8 together say that `Simulation` can't
import `maxim` or call upward into `sem_env`. So one of three things is true:
- the agents don't step inside the tick;
- the core calls Maxim through an interface the design doesn't name;
- B-3 and B-8 are violated.

B-3's phrase "an unseeded `random.Random` built inside Maxim" assumes that Maxim code runs inside the seal.

**Failure scenario.** The first time a real Maxim agent steps inside the sealed tick, it crashes the host.
`ForwardModel.update` calls `time.time()` (`cerebellum.py` line 155), and `SpecSensor.read` and `body.py` stamp
`time.time()`. That is 173 files in pymaxim 1.3.3. Under the tripwire these raise in `Simulation.step`, which is
"a bug, and the host fails loudly" (§4.1). If the tripwire is test-only instead, the live run silently reads the
wall clock inside the "sealed" core. Paused NPCs then get hungry and forget (lesson 11), and the seal is a
fiction in exactly the place Maxim is.

**The fix.** Decide where the substrate (drives, DN, reflexes, `Embodiment.advance`) runs, and write it into B-3:
- **(a) Inside the tick, through a port the core defines.** The core defines a port (for example `AgentPort`:
  `step(world_dt, frame) -> intents`, `settle(outcomes)`), and an adapter outside the core implements it with
  Maxim. Then B-3's static contract holds, and B-8's layering holds by dependency inversion. Say plainly that
  **real Maxim agents can't run in the sealed tick** until #1361 and items 10, 11, 12 and 15 land: until then only
  stubs run there, and a real-Maxim run isn't tier 1 or 2.
- **(b) Outside the core, in the membrane's own lane.** The substrate runs at tick boundaries on frozen frames, and
  its outputs enter as logged intents. Replays stay bit-identical, because the log is the truth. But reflex latency
  becomes at least one tick plus lane hand-off, and the substrate keeps its wall-clock drives (an OPEN divergence
  until #1361 and item 12).

Either way, the static import contract is not the seal for agents; the tripwire is. Also say which side owns the
agent state that Phase 4's save v1 persists ("the world plus each NPC's agent home"). This decides whether that
state is part of the sealed `Simulation`.

**Pushback to Maxim:** this is the strongest evidence yet for putting items 15 (deterministic agents) and 12 (an
externally stepped live tick) ahead of the content items. Without them, Maxim can't be embedded in any
deterministic host: a crash under a tripwire, or a silent wall clock without one. Add this finding to their
"why the game needs it" column.

### BF-3. B-2 ("only `sem_env` imports `maxim`") can't hold under B-1 and B-7, and its promise covers only three dataclasses

**Location:** `boundaries.md::B-2` and its rationale ("Maxim's releases, its frozen types and the Phase 3 proposals
land in one place"; "a newer Maxim is a swap of one package"), against `B-1` (cradle arcs and NPC authoring belong
to the game) and `B-7` (a harness for Maxim's experiments).

**What needs Maxim outside the SEM membrane:**
- **Cradle writing (game, under B-1):** `AgentFactory` (item 5), the seed-memory API (item 3) and the arc YAML
  loader (item 8).
- **The experiment harness (B-7):** Maxim's experiment and ledger tooling.
- **Save v1:** each NPC's agent home.
- **Agent stepping:** clock and RNG injection, and the experience-clock driver (#1361, items 10, 11, 12, 15 and 16).

None of these is the SEM membrane (bodies, percepts, acts).

**Failure scenario.** The first cradle-writer commit in `maxim_overdrive` imports `maxim.agents`, and the
`import-linter` contract goes red. The only ways to turn it green are both wrong:
- move cradle authoring into the engine's `sem_env`, which puts game content in the engine against B-1 and turns
  the membrane into a god-adapter; or
- route Maxim calls through a re-export in `sem_env`, a pass-through that satisfies the letter of the contract and
  defeats it.

**On the promise that a Maxim change lands in one place:** that is true only for the three dataclasses
`_compat.py` mirrors. Phase 3 items 10 to 16 change the agent runtime's surface (`step(world_dt)`, injected clocks
and RNG, generate vs apply, cancellable deliberation), not SEM's types.

**The fix.** Replace "one package imports `maxim`" with "**Maxim is imported only by named adapters, each declaring
the Maxim surface it uses**":
- the engine's `sem_env` (body, percepts, acts);
- an engine agent-runtime adapter (stepping, clocks, RNG, agent-state save);
- a game-side NPC authoring adapter (cradles, rosters);
- the harness.

`import-linter` checks the allowed importers, and a lint checks each adapter's imported symbols against its
declared list. A Maxim release then changes a known, listed surface, and B-2's "swap one package" becomes "swap the
adapters, whose surface is listed". BF-10 covers the behavioural half.

---

## SHOULD-FIX

### BF-4. B-10's read-only views are the wrong guard for percepts: a percept is a sample, not a view

**Location:** `boundaries.md::B-10` ("sensors, snapshots and SEM readings receive read-only views. NumPy arrays
passed outward have `writeable=False`"). Today's code is `sem_env/bridge.py::RegionSensor`, which holds `World`
itself.

**Failure scenarios:**
- **A memory that rewrites itself.** A sensor returns a `SensorReading` whose `value` is a `writeable=False` view
  of the temperature channel (`SensorReading.value` is `Any`, and ndarrays are explicitly allowed). The agent stores
  the reading in an episode ("the crate was hot"). The simulation lane keeps writing the base array, so the episode
  now says whatever the crate is now. A read-only view stops the agent changing the world, but not the world changing
  the agent's memory.
- **A torn percept.** Under the lanes, Maxim reads sensors on the thinking lane:
  - `SensorReadTool.execute`, `EntitySenseTool`, and the readback at `tool_bridge.py` line 580;
  - `RegionSensor.value` computes `temperature_max` and `temperature_mean` from the live grid;
  - `timestamp=grid.time_s` is read afterwards.

  A mid-read `advance` gives a reading that mixes two ticks, with the later tick's time on it.
- **A view guards the wrong object.** `RegionSensor` holds `self._world`, so `writeable=False` on arrays does
  nothing to stop code reaching `self._world.sources` (which `StructureModulator` mutates today).

**The fix.** Write B-10 as "**percepts are immutable samples of one published frame**":
- sensors bind to a frame source, never to `World`;
- a reading's value is a copy (or a frozen scalar) from the frame of tick T, stamped with that frame's world time;
- `writeable=False` stays for snapshots handed to the encoder.

Tests:
- a reading taken at T is unchanged after `advance`;
- a sensor object holds no reference to `World` (check `gc.get_referents`, or simply the constructor's type).

### BF-5. B-10 omits the push path, which is how Maxim's bodies actually perceive the world

**Location:** `boundaries.md::B-10` ("Mutation is reserved to `World.advance` and to applying intents"), and `B-9`'s
fairness claim. The Maxim side is `audio_localization.py::world_set_axis`, `Embodiment.live_world_set_sensors` and
`bootstrap.py` lines 520 to 541.

**How Maxim perceives.** Maxim's faithful path for a body is push, not pull:
- the world writes measured values into the body's `vital_metrics` through `world_set_axis(owner=...)`;
- `live_world_set_sensors` declares the world the single writer;
- `ModulatorAffordanceTool` then filters its *modeled* `self_effect` deltas on those sensors, so a declared delta
  can't fabricate a reading the next measurement reverts.

`world_v2.md` N6 already plans this ("written through `world_set_axis(owner="overdrive_world")` after each
advance"). It is a mutation of agent state, which `realtime_lanes_coop.md` puts inside `Simulation`. B-10 doesn't
name it.

**Failure scenario.** An NPC body declares `touch_fire` with `self_effect: {arms.thermal: +0.6}`, Maxim's shipped
`fire_pit_touch` pattern. The world also computes skin temperature from the contact. If the membrane doesn't
register the sensor as world-owned, the NPC is burned twice: once by the modeled delta, once by physics. The modeled
delta also changes with the YAML, not the fire, so a cooler fire hurts as much.

A player's body (Phase 5: "the same body grammar as the NPCs") is changed only by the world. So the NPC and the
player now differ in exactly the way B-9's fairness argument rules out.

**The fix:**
- B-10 names a second sanctioned mutation: percept delivery into agent bodies, in the simulation lane after
  `advance`, as a pure function of the frame (so it needs no log entry).
- B-9 extends to bodies. Every body sensor the world simulates is world-owned (`live_world_set_sensors`). A modeled
  `self_effect` is allowed only on sensors the world doesn't simulate, and each such sensor is listed as an ANALOG
  divergence.
- Note the dependency: per-part sensors (`arms.thermal`) need P4, because `world_set_axis` is root-only today.

### BF-6. B-9 can't attribute an NPC's intent to its actor: SEM's `Modulator.execute` has no actor

**Location:** `boundaries.md::B-9` ("the same intent log records both"; actor ids per `realtime_lanes_coop.md`
§4.2). The Maxim side is `sem.py`, `Modulator.execute(affordance, params)` (line 809), and `bridge.py::to_maxim_entity`
(one `StructureModulator` per region, shared).

**Failure scenario.** Two NPCs hold tools generated from the same crate `Entity`. Both call `crate_strike`. The
modulator receives `(affordance, params)` with no caller. The intent it produces has no actor, or the wrong one if
the membrane guesses from a thread or the last caller. The log then can't replay who struck. Per-actor limits,
reach and fatigue can't be checked. The player-and-NPC parity B-9 promises fails for NPCs alone.

**The fix.** Bind entities per actor: `to_maxim_entity(world, region, actor=...)`, each NPC with its own `Entity` and
modulator, and its intents stamped with that actor. Keep the entity's `name` and `full_path` identical across
actors, because the cerebellum and NAc key on them (lesson 10).

**Pushback candidate (low):** Maxim's single-agent assumption shows in the modulator contract (and in
`OrchestratorActorTool`'s `target="player"` resolving to the one AUT body). An appended, defaulted acting-entity
context on `execute` would be a SEM minor version (P6). Raise it only if per-actor binding proves costly in memory
or tool-generation time, measured.

### BF-7. The membrane is omniscient: region sensors report global truth to any NPC anywhere

**Location:** `boundaries.md::B-2` and `B-10` (neither constrains what a percept may be computed from). In code:
`bridge.py::RegionSensor` (`integrity` as the mean over every cell, `temperature_max` over every cell including the
interior, `breached`), all read with no reference to the perceiver.

**Failure scenario.** An NPC in another room, with no line of sight, calls `crate_sense` and learns the crate's
interior maximum temperature. No receptor could report that (lessons 4 and 5). The NPC then "avoids" a fire it
couldn't perceive, and Exp 64 or any later experiment attributes that to its cradle. This is the designer-number
failure the lens exists to catch, placed at the boundary that every percept crosses.

**The fix.** Add a boundary candidate, **B-13: percepts are reductions of registered physical channels at the
perceiver.**
- `sem_env` reads the world only through the frame and field-registry API, never through world internals.
- It is forbidden from the encoding layer (NIT BF-12).
- A percept takes the perceiver's position and receptor, and a line-of-sight gate when light lands.

Today's region sensors stay, but are labelled what they are: **instruments** (lesson 5's alternative), an ANALOG
divergence, usable by tests and the lab's instruments, not as an NPC's senses. Lands: `phase1/boundaries` for the
import half; the perceiver half with the first NPC body (Phase 4).

### BF-8. Whether a stale refusal is credit or context is contradictory across the docs, and B-9 is where it gets decided

**Location:** `boundaries.md::B-9`, against `realtime_lanes_coop.md` §4.3 ("an action the world has overtaken is
refused as stale, and the refusal goes back to the NPC as an outcome, which is something it can learn from") and
lesson 9 ("a late thought is context, never credit... stale refusals go to the next thought's context").

**Failure scenario.** The NPC decides to strike the crate. While it deliberates, the player destroys the crate. At
application the intent is refused as stale:
- Under §4.3 the refusal is booked through Maxim's failure path: `success=False`, so NEGATIVE on
  `tool:crate_strike`. The NPC learns that striking crates fails, scaled by how slow its model is and how fast the
  dial runs.
- Under lesson 9 it isn't booked.

Whichever receipt BF-1 picks, the membrane has to choose one, and Maxim has no refusal kind for "the world overtook
you": every `success=False` is NEGATIVE.

**The fix and the pushback:**
- Make lesson 9 the rule in B-9's receipt (stale refusals are context).
- Fix `realtime_lanes_coop.md` §4.3.
- Add "stale" to P2's executor-made refusal kinds, alongside the call error and P1's wrong target: booked to
  context, never to NAc.
- **What this argues against:** TF2's "reached `tool.run`, therefore ran", which is the same decision P2 contests.

### BF-9. B-7's harness must depend on the engine only: Exp 64 as drafted would put rights-reserved content on Maxim's ledger

**Location:** `boundaries.md::B-7` (it forbids only game → harness), against `exp64_cradle_conduct_prereg_DRAFT.md`:
- the body is "`npcs/street_fixer`-derived", which is content under B-5;
- the arms come from the cradle writer, which is game under B-1;
- material calibrations become content under B-5.

**Failure scenario.** Exp 64a is frozen and run, and its result goes on Maxim's ledger. A Maxim reviewer can't
reproduce it from Maxim or from Apache-licensed code: the body, the cradle event pool and the calibrations are
rights-reserved and live in the game.

Later, a gameplay retune of `degrade_*` (content) changes the world under a frozen pre-registration with no version
bump. The direction B-7 forbids (game imports harness) is harmless for faithfulness. The direction it allows
(harness imports game and content) is the one that corrupts experiments.

**The fix:**
- B-7 adds "the harness imports only the engine and its own Apache-2.0 fixtures (body, event pool, scene)".
- The ledger record pins the engine SHA, the pymaxim version, the membrane contract version (BF-1's choice and any
  interim `neutral` behaviour, which is part of the treatment) and the Phase 3 items present.
- Decide this now, not "when the first experiment is built". The Exp 64 draft freezes at the Phase 3 exit and will
  name these paths.

### BF-10. The membrane's drift check covers shape, not behaviour, yet Maxim's behaviour is what NPCs learn from

**Location:** `boundaries.md::B-2` ("a newer Maxim is a swap of one package"), and `tests/test_sem_compat.py`, which
compares three dataclasses field for field.

**Evidence that behaviour drifts between pymaxim releases with no type change:**
- Exp 37 reversed the order of self_effect and failure evaluation (`tool_bridge.py` comment, 2026-06-01).
- D53 made `metadata["outcome_valence"]` and `measured_drive_transitions` learning channels, keyed by strings in an
  untyped dict.
- The cerebellum call used the wrong keyword names from 2026-04-07 to 2026-09-01, and a swallow hid it: "the
  forward model never trained in production for about 5 months".

Any of these changes what an Overdrive NPC learns, with the compat test green.

**Failure scenario.** A pymaxim minor release renames `outcome_valence` or changes the POSITIVE default. BF-1's
interim `neutral` silently stops working, and every queued intent books POSITIVE again. The gate is green.

**The fix.** Add a behavioural contract test to the membrane's guard. It runs a real `ModulatorAffordanceTool` (and
the actor tool) against the membrane, and asserts what Maxim does with the result:
- the valence booked for a success, a refusal and a pending result;
- what the cerebellum is trained on;
- which side_effects keys are promoted.

Also reserve the metadata keys the membrane writes. `**result.metadata` is spread after `success`, `entity_state`
and `active_failures` (`tool_bridge.py` line 916), so a membrane metadata key named `success` would overwrite the
LLM-facing outcome. That is a Maxim NIT worth raising with P6.

### BF-11. Two clocks reach one agent through the membrane

**Location:** `boundaries.md::B-3` (it seals time out of the core but says nothing about which clock crosses into
Maxim). In code:
- `bridge.py::RegionSensor.read` stamps `timestamp=grid.time_s`, seconds since the scene started;
- Maxim's own sensors stamp `time.time()`, Unix epoch seconds (`embodiment/spec.py` line 830, `body.py` lines 502
  and 599).

**Failure scenario.** One NPC's body readings say 1.79e9 and its world readings say 12.0. Any consumer that orders,
ages or renders timestamps mixes them:
- `datetime.fromtimestamp` renders the world reading as 1970;
- `TemporalSignature.from_timestamp` would put a world percept at a 1970 circadian phase;
- an age gate like the Reachy backend's `time.monotonic() - ts` would call every world reading decades stale.

**The fix.** Make the membrane the clock translator. Every timestamp that crosses into Maxim is on one declared
clock, which is the world clock once item 10 and P5 land. Until then, document which clock each field carries, and
treat the mismatch as an OPEN divergence. This is evidence for item 10 and P5: name `SensorReading.timestamp` in
them.

---

## NIT

### BF-12. B-8 lets `sem_env` import the encoding layer

**Location:** `boundaries.md::B-8` puts `sem_env` in layer 6 with "the protocol and encoding".

**Failure scenario.** A percept built from the uint8 `glow` or `crack` display channels is a renderer number, not
physics, and its quantization step becomes something the NPC learns.

**The fix.** Add a forbidden contract from `sem_env` to the encoding layer. It is the percept-side twin of B-6.

### BF-13. B-4's list of gates omits thought results

**Location:** `boundaries.md::B-4` ("Later: the protocol decoder, and the save, scene-v1 and intent-log loaders").

**The gap.** B-9 says LLM output is untrusted, and `realtime_lanes_coop.md` §4.3 has the simulation lane apply a
thought's intents **and memory writes**. The thought-result decoder is a gate and belongs on the list. Memory writes
are Maxim state, so name who validates them: Maxim, through item 16's apply step, not the game.

### BF-14. The numbering of the Phase 3 proposals collides across documents

**Location:** `boundaries.md::B-2` ("the Phase 3 proposals land in one place"), against three schemes:
- the roadmap's items 10 and 11 are validation and done-to;
- `realtime_lanes_coop.md` §6 items 10 to 18 are the clock, the DN and the rest;
- `world_v2.md`'s P1 to P7 include P1 = item 11 and P2 = item 10.

Lessons 7 and 8 cite "item 10" and "item 11" in the roadmap's sense, and lesson 6 cites "P3".

**Failure scenario.** A reader of B-2 can't tell which "item 10" lands in the membrane. Lesson 10 ("names are
identities") applies to proposal ids too.

**The fix.** Give the proposals one id space in `docs/roadmap.md`, and cite those ids.

### BF-15. B-1 doesn't say where body grammar and receptor models live

**Location:** `boundaries.md::B-1` ("What belongs where" lists NPC rosters as game, and says nothing on bodies).

**The fix.** Receptor models and the body grammar are physiology, a mechanism, so they belong in the engine under
Apache-2.0. Each NPC's body instance is game. Otherwise the receptor-first evidence that the Maxim proposals cite
(`maxim_senses.md`, P4, `NociceptorSpec`) sits in rights-reserved content Maxim can't read. This also supports
BF-9's Apache fixture body.

---

## What I checked and found faithful

- **B-2's direction is right.** A single, checked entry point for Maxim is what makes the Phase 3 evidence
  traceable. The objection is to its scope (BF-3), not its existence.
- **B-3 is right to forbid `maxim` in the core.** Maxim's wall clock and global RNG must never decide world state.
  The objection is that the design must say how agents are then stepped (BF-2).
- **B-9's trust argument is right.** LLM output is untrusted input, and NPCs and players should share one validator
  and one log. The objection is only to fusing that with a non-blocking `execute` (BF-1).
- **B-6 helps perception.** Removing display quantization from physics keeps percepts on physical channels; BF-12
  closes the reverse path.
- **B-7's ledger rule** (game runs stay off Maxim's ledger unless pre-registered) matches CLAUDE.md. BF-9 adds the
  dependency direction that actually protects experiments.
- **The current membrane's refusal discipline** (refusals carry no echoed parameters, namesake detection under
  Maxim's name rule, and a target accepted only when it names the region) is faithful to items 10 and 11 as written,
  and nothing in the boundaries undoes it.
