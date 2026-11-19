# Executor lens: real time, lanes and co-op (design v0)

Reviewed `docs/design/realtime_lanes_coop.md` at 52e64f0 against the code in this repo and Maxim at 4b773ef8.
Timings were re-run on the 3x3x2 m crate scene from `tests/test_cross_tier.py`, best of 3-5 runs, on the owner's
laptop with `.venv/bin/python`. The script is not committed. To simulate `max_substep_s`, it set
`min_substeps_per_turn = ceil(period / max_substep_s)` and called `World.advance(period)` 6/period times.

## BLOCKER

### X1. The cost table is wrong on the shipped path. A 0.5 s physics period costs 2.6x to 10x more per world second than one 6 s turn.

- **Location:** design section 1, "What it costs", and the sentence "per world second the cost doesn't depend on
  `tick_s` or `physics_period_s`". The cause is in `world/world.py::World._power_field`, `world/world.py::World.advance`
  and `world/heat.py::step`.
- **What happens:** every call to `World.advance` runs `heat.step`, which calls `power()` once at its start (and
  again after any substep that destroyed cells). `_power_field` calls `sphere_overlap` once per source. That is a
  4^3 = 64-pass loop over the whole grid, so it costs the same per call however short the call's `seconds` is.
  `heat.step` also computes `stable_dt` over the whole grid on every call. On top of that, a period that isn't a
  multiple of the proposed `max_substep_s` rounds the substep count up: ceil(0.5/1.5) = 1, ceil(0.5/0.375) = 2,
  ceil(0.5/0.094) = 6. That gives 12, 24 and 72 substeps per 6 s, not 4, 16 and 64.

  Measured: ms of wall time per 6 s of world time, crate scene, with two 60 kW fires (as in `_burn`):

  | Profile | 1 x 6 s (today) | 12 x 0.5 s (design) | 60 x 0.1 s | Design's claim | `_power_field` per call |
  |---|---|---|---|---|---|
  | laptop 0.2 m | 1.38 (4 substeps) | **13.7** (12) | 68.9 (60) | 0.9 | 1.0 ms |
  | rig 0.1 m | 10.9 (16) | **61.6** (24) | 283 (60) | 9 | 4.0 ms |
  | max 0.05 m | 214 (64) | **554** (72) | 2254 (120) | 201 | 26.8 ms |

  With no fires the design period costs 1.68 / 13.2 / 244 ms, against 0.37 / 6.5 / 179 ms for one 6 s turn. So
  even without the power field, the rounding and the per-call overhead cost 1.4x to 4.5x.

  Scaled by the design's own 36x, the full-tile estimates become about **12x real time (laptop), 2.7x (rig) and
  0.3x (max)**, not 190x, 18x and 0.8x. The rig profile, which is the target machine, keeps less than 3x headroom
  before NPC substrates, the thinking lane or a tile's real number of fires are added. `_power_field` cost scales
  with sources x cells, and a tile will have more than two.
- **Failure:** 2a ships with a B5 budget and a dial built on the wrong numbers. The first measured tile in step 3
  shows dilation on the rig profile once a few fires and NPCs are running, and the design's claim that "only the
  max profile dilates" turns out false.
- **Fix:** make the design's numbers measure the design's own loop (12 x 0.5 s), not today's one 6 s turn. Then
  fix the root cause in 2a, alongside the `max_substep_s` change:
  - `sphere_overlap` depends only on geometry (`shape`, `dx`), not on materials. Compute it once per source when the
    source is placed, and redo only the `frac * solid` weighting when cells are destroyed.
  - Cache the power field and `stable_dt` across `advance` calls until sources or materials change.
  - Choose substep values that divide `physics_period_s` (see X2).

  Then re-measure the table and put the measurement method next to it.

## SHOULD-FIX

### X2. "1.5, 0.375 and 0.094 s, the same precision as today" holds only for a 6 s advance. At the proposed 0.5 s period the substeps come out different and more numerous.

- **Location:** design section 1, the third bullet. Also `config.py::RigProfile`, `world/heat.py::step` and
  `tests/test_heat.py::_error`.
- **What happens:** the values are right as 6/4, 6/16 and 6/64 (6/0.094 rounds up to 64). Also checked: stability
  never binds today, with `stable_dt` at 240, 60 and 15 s on the crate scene. But at a 0.5 s period the solver takes
  substeps of 0.5, 0.25 and 0.083 s. That is finer than today, so results differ from today's turns, and it costs
  more (X1).

  The rename also ripples further than the design says. `heat.step` takes `min_substeps` as an argument.
  `tests/test_heat.py` passes `rig.min_substeps_per_turn` to a 3600 s step, so the closed-form test (and the
  "1% / 0.1% / 0.01%" claim in `docs/architecture.md`) was calibrated at 4, 16 and 64 substeps per hour. With
  `max_substep_s` the same test takes 2,400, 9,600 and 38,298 substeps.
- **Failure:** the closed-form and conservation tests change meaning and runtime silently, and the "same precision"
  claim can't be checked, because precision per world second was never the old contract.
- **Fix:**
  - State the rig field as substeps per physics period (`physics_substeps`: 1, 2 or 4 at 0.5 s, say), or require
    `physics_period_s / max_substep_s` to be an integer and validate that on load.
  - Say how `heat.step`'s signature and `tests/test_heat.py` change, and re-derive the closed-form error figures.

### X3. `World` already carries a second clock and a 6 s turn. The design says "Nothing else is the world's time."

- **Location:** design section 1. In code: `world/grid.py::MaterialGrid.time_s`, `world/heat.py::step`
  (`grid.time_s += seconds`), `world/world.py::World.turn`, `World.turn_seconds`, `World.advance`,
  `world/world.py::snapshot` (`"time_s"`) and `sem_env/bridge.py::RegionSensor.read` (`timestamp=grid.time_s`).
- **What happens:**
  - `grid.time_s` advances only on physics steps, as a float sum. It trails `tick x tick_s` by up to
    `physics_period_s`, and it would drift for a period that isn't exact in binary.
  - Every SEM `SensorReading.timestamp` and the snapshot's `time_s` report `grid.time_s`, not world time.
  - `World.turn` increments once per `advance`, so it would count physics steps. `tests/test_determinism.py`
    hashes it, and `tests/test_validation.py` asserts `w.turn == 1`.
  - `World.advance()` with no argument still advances 6 s (`turn_seconds = 6.0`). A host that calls it bare jumps
    the world twelve physics periods.

  Rates are fine: degradation is per second, strikes are instantaneous, and sources have no lifetime. No physics
  assumes 6 s.
- **Failure:** an NPC's percept timestamp disagrees with the tick status's `world_time_s`. A snapshot sent after a
  strike on a non-physics tick carries a stale `time_s` next to a newer header `world_time_s`.
- **Fix:** the design should name these.
  - Make `World` take the tick (or world time) from the host, or have the snapshot and sensors read the host's
    world time.
  - Remove or rename `turn` and `turn_seconds`, and make `advance` require `seconds` (keyword-only, per the
    standards).
  - Keep world time as integer ticks (or integer microseconds, as Maxim's `ExperienceClock` does), not a float sum.

### X4. The `ExperienceClock` row works only on Maxim's full agent loop, not on the `AgentPool` path NPCs use today.

- **Location:** design section 3, table row 1. In Maxim: `runtime/experience_time.py::ExperienceClockDriver`,
  `runtime/loop_setup.py:194`, `runtime/agent_pool.py::AgentPool.run_turn`.
- **What happens:**
  - The claim about what it reads is correct: elapsed monotonic time minus the controller's pauses, or the
    duck-typed `experience_turns()` / `experience_us_per_turn`. The game could declare `experience_turns() = tick`
    and `experience_us_per_turn = 100_000` without any Maxim change.
  - But the driver is built only in `loop_setup.py` and advances "once per live loop pass". `AgentPool.run_turn`
    says it "does NOT run the full agent loop", so nothing advances an `AgentPool` NPC's clock.
  - The realtime kind subtracts the autonomy controller's pause, not a world pause. A paused game would make a
    real-time-kind NPC forget.
- **Failure:** NPCs built through `AgentPool` never forget, or they raise `ExperienceClockStalled` once a strength
  strategy is on.
- **Fix:** say which path the game uses and that the turns protocol is the mechanism. Add "drive the experience
  clock from the per-tick substrate step" to Phase 3 item 12.

### X5. Phase 3 item 10 (an injectable clock for `TemporalSignature` and the SCN) is larger than one injection point, and it has a determinism trap.

- **Location:** design section 3, table row 2, and item 10. In Maxim: `time/temporal_signature.py`, `time/scn.py`,
  and the call sites below.
- **What happens:**
  - `TemporalSignature.now()` is called at about 15 sites: `similarity/encoder.py` (x3), `decisions/nac.py`,
    `decisions/temporal_credit.py` (x2), `embodiment/body.py`, `bridges/tool_pain_bridge.py` (x2),
    `bridges/escalation_bridge.py` (x2), `agents/exec_agent.py`, `agents/statistician_agent.py` and
    `simulation/introspection.py`.
  - The SCN bins from `memory.timestamp`, which is set elsewhere, and `BoundedBin.add` stamps `_time.time()`.
  - `from_timestamp` uses `datetime.fromtimestamp(ts)`, which is **local time**. Even a world timestamp passed in
    gives different circadian and weekly phases on machines in different timezones.
  - The class is documented SHAPE-FROZEN at 1.0, so a "day-length-aware `TemporalSignature`" can add only defaulted
    trailing fields.
  - 86,400 is hard-coded.
- **Failure:** NPCs whose SCN reads a world clock but whose memories are stamped in wall time, or who bin
  differently on two machines. The design's own "outcome class across machines" promise would break.
- **Fix:** list the call-site count, the `memory.timestamp` source and the timezone issue in item 10. The world
  clock should hand Maxim phases (or a UTC-naive world datetime), not a Unix timestamp read in local time.

### X6. Maxim's "hybrid runtime" and its Default Network are not what section 2 describes.

- **Location:** design section 2, "Substrate and the hybrid runtime", and Phase 3 item 11. In Maxim:
  `docs/plans/deferred/hybrid_substrate_reflex_runtime.md`, `default_network/network.py::_run_loop`,
  `default_network/background_tasks.py::OperationThrottler`.
- **What happens:**
  - The plan is **DEFERRED** (2026-09-19). Its revive trigger is a second physical robot body.
  - One-way voluntary suppression is net-new there (SF-1: only `turn_around` self-inhibits today). The design
    calls it "Maxim's hybrid runtime" in the present tense and says suppression works "as in Maxim's design".
  - The DN is a vision loop: `_process_tick` consumes detections with `track_id`, `class_id` and pixel gaze. Its
    sub-rates (novelty and salience at 10 Hz, spatial at 5 Hz) are `OperationThrottler`s that read `time.time()`
    on their own.

  The 30 Hz default (`update_hz: float = 30.0`), the thread and `time.sleep` are as claimed.
- **Failure:** item 11's `step(now)` with no thread is not enough. The throttlers still read wall time, and the
  world has to produce DN-format detections. Phase 3 is under-scoped, and reviving a deferred plan needs its
  trigger re-read by the Maxim owner.
- **Fix:**
  - Cite the deferred status and its trigger.
  - Add "throttlers on the injected clock" and "a percept adapter from SEM sensors to DN detections, or a non-visual
    DN input" to item 11.
  - State that suppression is to be built, not existing.

### X7. "Validated before anything is applied" has no validator to stand on: the existing modulator accepts bad input and can crash.

- **Location:** design section 5, the `act` row. In code: `sem_env/bridge.py::StructureModulator.execute`,
  `world/damage.py::strike`.
- **What happens:** I probed it on the laptop profile.
  - `strike` with `point_m: [1.5, 1.5]` raises an **IndexError**, which escapes the bridge's
    `(KeyError, ValueError, TypeError)` handler.
  - `strike` with `energy_j: NaN` returns `success=True` and writes NaN into `grid.integrity`. The check
    `energy_j < 0` is false for NaN.
  - `ignite` accepts `power_w` of -1e9 or inf, and `radius_m: -1`. A negative radius squares to a 1 m fire.
- **Failure:** a client message crashes the simulation lane, or poisons the world with NaN while the reply says
  success. That breaks the "error reply, world unchanged" rule.
- **Fix:** 2a's list should name a protocol-layer validator for `act`: finite, ranged floats, a 3-element `point_m`
  inside the grid, and a known region and action. It should have a rejection-path test per field (B14). Fixing
  `damage.strike`'s NaN check at the root belongs in the same PR.

### X8. "Nothing depends on thread scheduling" is true only of replays.

- **Location:** design section 2, "Ordering is part of the contract".
- **What happens:** the host assigns the tick when it takes an intent off the channel. In a live run, which tick an
  intent lands on depends on when the network thread enqueued it relative to the simulation lane's dequeue. That is
  scheduling. Ordering within a tick is deterministic, and the log makes replays exact.
- **Failure:** a reviewer or a test assumes two live runs with the same client input agree bit for bit. They don't.
- **Fix:** say "a live run's tick assignment depends on arrival; the logged assignment makes every replay
  bit-identical".

## NIT

- **N1, volume and timing figures (sections 1 and 5).** 5 bytes per cell is right (material, crack and glow at 1
  byte each, temperature at 2). The rig tile is 640,000 cells x 5 B x 2 Hz = 6.4 MB/s, which is correct. The max
  tile is 5.12 M cells x 5 x 2 = **51.2** MB/s, not 52. The 36x factor is right (640/18 = 35.6). The design doesn't
  say which scenario was timed. I got 1.4 / 10.9 / 214 ms with the two fires and 0.37 / 6.5 / 179 ms without; the
  design's 0.9 / 9 / 201 sits between. Name the scenario and the method.
- **N2, axis order (section 5).** `grid` arrays are C-order (x, y, z), so z (up) varies fastest. Sending (z, y, x)
  with x fastest needs a server-side `np.ascontiguousarray(a.transpose(2, 1, 0))` per array. Godot is Y-up, so
  texture depth (world z) still maps to Godot's Y in the shader. `ImageTexture3D.create` takes an `Array[Image]` of
  depth slices, so the client splits the buffer anyway. Also say whether `shape` in `welcome` and the header is
  listed as (x, y, z) or (z, y, x).
- **N3, integer time (section 1).** Specify the physics cadence as integer ticks (`physics_every_n_ticks = 5`), not
  "a multiple of `tick_s`": 0.3/0.1 = 2.9999999999999996. Compute time of day from integer ticks or microseconds.
- **N4, stale documents.** The roadmap's Phase 4 still says "a dialogue screen and turn order". `docs/architecture.md`
  "Transport" calls head-of-line blocking "harmless for a turn-based game", which no longer applies at 6 to
  52 MB/s of snapshots. Both need updating with the decision record.

## Checked and found correct

- `heat.step`: n = max(min_substeps, ceil(seconds / stable_dt)), with the stability limit on top. The runs take
  exactly 4 / 16 / 64 substeps per 6 s turn. `stable_dt` is 240 / 60 / 15 s on the crate scene, so stability
  never binds.
- Calling `advance(0.1)` with today's rig field gives 60 x 4 = 240 substeps per 6 s, against 4: the "60 times"
  claim is right.
- 6/4, 6/16 and 6/64 give 1.5, 0.375 and 0.094 s, and the speed-up ratios follow from the claimed timings
  (6,700x, 670x and 30x, then /36).
- The 6 s timings reproduce to within about 20% (fires on), see N1.
- Snapshot contents (`shape`, `cell_size_m`, `time_s`, `material`, `crack`, `glow`, `temperature_c` float16): 5
  bytes per cell, and the tile sizes in `docs/architecture.md` (0.4 / 3.2 / 26 MB) agree. `snapshot()` takes
  0.8 ms on the max crate, so about 30 ms per tile per session.
- The SEM `structure` vocabulary is exactly `strike(energy_j, sigma_m, point_m)`, `ignite(power_w, radius_m)` and
  `extinguish()`.
- No physics rate is per turn: `thermal_degrade` is per second times `dt`, strikes are instantaneous and sources
  have no lifetime. Physics can be run at any period.
- The dial claim holds: `World` takes no wall time, so the same intents on the same ticks give the same state at
  any dial setting, given that `tick()` takes no duration.
- In Maxim: `TemporalSignature.now()` is `from_timestamp(time.time())`. The DN has a 30 Hz default, its own thread,
  `time.time()` and `sleep`. `AgentPool` has `run_turn` and `run_round` and nothing per tick. The
  `ExperienceClockDriver` kinds are as described (but see X4).
- Phase 3 numbering continues the roadmap's list (1 to 9). Item 7 is cancellable SEM actions.
- B14 already requires that no wall-clock duration reaches `World.advance`.
