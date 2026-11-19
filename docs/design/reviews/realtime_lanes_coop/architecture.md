# Architecture lens: realtime_lanes_coop.md (design v0, reviewed at 52e64f0)

Reader: Architecture. Inputs: CLAUDE.md, `docs/code_review.md`, `docs/architecture.md`, `docs/roadmap.md`,
`docs/standards_backlog.md`, the design, and the code it changes (`world/world.py`, `world/heat.py`, `config.py`,
`data/rigs/*.yaml`, `sem_env/bridge.py`), plus Maxim's `runtime/agent_pool.py` and `embodiment/tool_bridge.py` for the
Phase 4 shape. Measurements below come from a scratch script on the 3×3×2 m crate scene (`tests/test_cross_tier.py::SCENE`).

Counts: 3 BLOCKER, 9 SHOULD-FIX, 4 NIT.

## BLOCKER

### A1. The deterministic step lives inside `WorldHost`, mixed with sessions and pacing
**Where:** §2 (the simulation lane box), §4 ("A `WorldHost` owns the simulation lane"), §6 2a (`WorldHost` with `tick()`).
**Scenario:** 2a builds `WorldHost.tick()` as the per-tick pipeline: take intents, apply thoughts, step substrates,
advance physics, publish. `WorldHost` also holds sessions, the `TimeAuthority`, the pacers and the publish fan-out.
A replay, a cradle and an Exp 64 run then all have to build a `WorldHost`, with fake sessions, to reach the state
transition. The tick counter and the world clock (`tick × tick_s`) live on the host, not in `World`. So a save of `World`
leaves out the world's time. Meanwhile `grid.time_s` (added to by `heat.step`) keeps running as a second clock that
lags the tick clock by up to `physics_period_s`. SEM sensor timestamps (`RegionSensor.read` uses `grid.time_s`) and
the snapshot's `time_s` then disagree with the protocol's `world_time_s`. That breaks "nothing else is the world's
time" on the shipped path. In 2b the same `tick()` has to be pulled out of the host into the simulation lane's thread,
which is a tear-out.
**Fix:** Split the state transition from the host. A pure `Simulation` (or `World.step_tick(inputs: TickInputs)`)
owns `World`, the integer tick, the world config, the seeded RNG and (in Phase 4) the agents. It takes one tick's
already-ordered, already-validated inputs and returns the tick's outputs (status, the snapshot when cells changed,
and any requests to the thinking lane). `WorldHost` only collects inputs, runs the `TimeAuthority` and paces calls.
Replay and cradles drive `Simulation` directly from the log. Derive `grid.time_s` from the tick, or remove it, so
there's one clock. 2b then moves `Simulation` into a thread unchanged.

### A2. The intent log is a new persisted format with no version, header or schema
**Where:** §2 ("Every result ... goes into the intent log"), §4 ("The log records the decision"), §6 2a ("the intent log,
with a replay test").
**Scenario:** CLAUDE.md says every format is versioned, readers refuse versions they don't know, and the log is
"the save format's backbone". The design names what goes into the log but not its format, its version, or what pins
the run. Suppose a log is replayed against an edited `data/materials/core.yaml`, a different `physics_period_s`, or
`max_substep_s` before and after the A-series change. The replay runs, comes out different, and gives no error, so
the replay test passes only because nothing changed between the record and the replay. Thought results
(LLM text) going into the log also make it a store of untrusted content with no size bound.
**Fix:** Specify log v0 in the design, so 2a doesn't invent it. It needs:
- A header with the format version, protocol version, scene (or its hash), rig name and fields, a hash of the
  material table, the deterministic world config (`tick_s`, the physics period, `day_length_s`, `epoch`, the RNG
  seed) and the code version.
- One record per tick input: `tick`, the kind, the actor, a host-assigned sequence number and the payload.
- Golden fixtures under B2/B4.

The reader refuses a header that doesn't match the world it's asked to replay into. State that a save is a
checkpoint plus the log tail, and decide now whether save v0 (Phase 1) embeds the log header.

### A3. The SEM bridge mutates `World` directly, so "the simulation lane alone holds `World`" fails once an NPC acts
**Where:** §2 ("One owner of the world"), §2 "Substrate and the hybrid runtime", `sem_env/bridge.py::StructureModulator.execute`,
`sem_env/bridge.py::RegionSensor.value`.
**Scenario:**
- `StructureModulator` and `RegionSensor` hold a live `World` and read or mutate it on call. `ignite` writes
  `world.sources`, and `strike` writes cells.
- Maxim runs modulators synchronously from LLM tool calls (`embodiment/tool_bridge.py`, the `execute` methods).
- `AgentPool.run_turn` writes the hippocampus and NAc during the LLM call itself (`runtime/agent_pool.py::run_turn`).

If deliberation runs in the thinking lane, as the design says, then two things happen off the simulation thread, at
wall-clock arrival time, with nothing logged: an NPC's tool call mutates `World`, and its turn writes the agent's
memory. The first is a data race on `World`. The second breaks replays, because a replay never calls the model, so
it never stores those observations, and the agent state diverges.

The design reserves this shape ("the risk is building the lanes around the wrong shape") but builds the thinking-lane
interface in 2b anyway.

**Fix:** Decide the boundary in this design, before 2b fixes the interface:
- (a) In the thinking lane, a modulator emits an intent message instead of mutating anything. Its
  `ModulatorResult` becomes "queued" (Maxim's synchronous SEM contract can't return `destroyed_volume_m3` yet: list
  that under Phase 3 next to item 13).
- (b) Sensors in the thinking lane read the published immutable snapshot, not `World`.
- (c) Extend "one owner" to agent state. The simulation lane owns the agents. A thinking request carries an
  immutable context. A result carries validated intents plus memory-write messages, which the simulation lane
  applies at the deadline tick, and the log records them.

Add a Phase 3 item: run a turn with no side effects, returning its memory and NAc writes instead of applying them.

## SHOULD-FIX

### A4. `max_substep_s` doesn't keep today's precision or cost at the proposed period
**Where:** §1 ("the same precision as today", and "per world second the cost doesn't depend on `tick_s` or
`physics_period_s`"), `world/heat.py::step`.
**Scenario:** `heat.step` sets `n = ceil(seconds / min(max_substep_s, stable_dt))`. For a 0.5 s period that gives:

| Profile | `max_substep_s` | Substeps per 0.5 s step | Substeps per 6 s, today → proposed |
|---|---|---|---|
| laptop | 1.5 s | 1, of 0.5 s | 4 → 12 |
| rig | 0.375 s | ⌈1.33⌉ = 2, of 0.25 s | 16 → 24 |
| max | 0.094 s | ⌈5.33⌉ = 6 | 64 → 72 |

I measured these with the current `stable_dt` (240, 60 and 15 s), so stability never binds. The effective precision
is now set by the world's period as well as the rig, and the laptop does 3× the work.

Each `advance` also has fixed costs. `sphere_overlap` (64 sub-samples over the *whole* grid, once per source per
`advance`) costs 0.5 / 2.1 / 13.7 ms, and `stable_dt` costs 0.1 / 0.5 / 3.2 ms. Twelve advances per 6 s with two
fires at max adds about 370 ms to the measured 201 ms, so the max tile's "about 0.8×" is closer to 0.3×.

The resolution rule isn't broken, but the design's cost table and its precision claim are wrong. The known-gap numbers
in `docs/architecture.md` were measured at 4, 16 and 64 substeps per turn, so they will move too.

**Fix:** State the substep count as `ceil(period / min(max_substep_s, stable_dt))`, and either pick `max_substep_s`
values that divide the period or accept and record the new counts. Cache the power field. It only changes when
`sources` changes or a cell is destroyed, which `heat.step` already detects. Compute the overlap over the sphere's
bounding box instead of the whole grid. Redo the cost table after both changes, and re-measure the known gaps.

### A5. The world clock is in floats; make it integer ticks
**Where:** §1 (`physics_period_s` "a multiple of `tick_s`", time of day `(epoch + tick × tick_s) mod day_length_s`).
**Scenario:** A config of `tick_s: 0.1` and `physics_period_s: 0.3` fails a check of the form
`period / tick_s == int(...)`, because `0.3/0.1 = 2.9999999999999996`. A day of 86,400 s isn't an exact number of
0.1 s ticks in binary either. Time of day computed in floats drifts away from tick boundaries over long runs, and
the SCN's phase reads that drift.
**Fix:** Keep the config in integers: `tick_us` (or `ticks_per_s`), `physics_every_ticks`, `day_length_ticks` and
`epoch` as a tick offset. Derive seconds only for display and for `World.advance(physics_every_ticks × tick_s)`.

### A6. Intent ordering uses the client's `seq`, which the client controls
**Where:** §2 ("ordered by ... then by sequence number"), §5 ("Every message carries `seq`").
**Scenario:** A client sends two `act` messages with the same `seq` in one tick, or numbers them in reverse. The
order is then a tie, broken by arrival or sort stability, or the client picks the order. The rule that "nothing
depends on ... arrival order" holds only by luck. Actor ids are also unspecified (string or int, how they're issued),
and lexical against numeric ordering changes who acts first.
**Fix:** The host stamps its own per-tick arrival counter and orders by `(tick, actor, host_seq)`. Keep the client's
`seq` only for echoing in replies. Make actor ids host-issued integers, issued deterministically and logged. State how
NPC-originated intents (from steps 2 and 3) enter the same order. Today players always apply before NPCs in a tick,
which contradicts "the world doesn't distinguish players from NPCs". Better: every actor's intents produced at tick T
apply at T+1, through one queue.

### A7. Thought results bypass the validation that client intents get
**Where:** §2 step 2 ("apply thoughts whose deadline is this tick").
**Scenario:** A thought's result comes from an LLM. CLAUDE.md says to never write cells from LLM output without
validation, and that intents are validated at one layer. The design validates client intents in the network lane,
but says only that thoughts "apply". A hallucinated `ignite` with `power_w: 1e12`, or with a region that doesn't
exist, could take a different path from a client's.
**Fix:** One intent validator, shared by the network lane and the thinking lane. A thought result is a list of
proposed intents (and imagination specs, through `imagination.spec.place`). Each is validated when it's applied. A
refusal is logged like a client error.

### A8. The design is silent on avatars, joining and leaving, and the host leaving
**Where:** §4.
**Scenario:** If joining creates an avatar in the world, joining changes world state at a tick that comes from
wall-clock arrival. If the log doesn't record it, a replay diverges. If the host session disconnects, `HostOnly` has
nobody to grant `resume`, and the world stays paused or running for good. If "host" means the first session to
connect, then which client is host is a race. With per-session tokens, the design doesn't say who issues a guest's
token when the listener is loopback-only.
**Fix:** Join and leave become logged inputs at a tick. Bind the role to the credential (the per-launch token is the
host's, and the host issues guest tokens through a host-only request). Define the host-leave policy (pause, and refuse
guest time requests) and give it a test.

### A9. "Hold the world" is argued as necessary for replay, but replay doesn't need it
**Where:** §2 "The thinking lane and determinism", §8 Q1.
**Scenario:** The log already records every result. If it also records the tick at which each result was *applied*,
a replay is bit-identical whether the world holds or applies on arrival. All the hold buys is dial-independence of
NPC timing in *fresh* runs, which the design already says match only in outcome class with live models. The cost is
real. In co-op, one NPC's slow API call freezes every player's world. At 30× a deliberation time of 5 world seconds
is 0.17 wall seconds, so almost every thought holds, and fast-forward runs at LLM throughput.
**Fix:** Restate the trade honestly: the hold gives fresh-run fidelity, not replay determinism. Consider applying at
`max(T + d, arrival tick)` with the applied tick logged, plus a hold budget that the dial can turn up (headless
experiments hold fully; interactive play holds for 0 to a few hundred ms). Decide whether dialogue pauses the world
(see A11), because that answers most of Q1 for the case players notice.

### A10. Substrate stepping is a step of the simulation lane, so it can't "move to a process" as a lane
**Where:** §2 ("A lane that turns out to be CPU-bound ... substrate stepping for many NPCs, say ... moves to a process"),
§2 step 3.
**Scenario:** Step 3 runs inside the simulation lane's tick, in actor order, and reads cells. Moving it to a process
needs a lockstep barrier every tick: send percepts, wait, then apply. At 10 Hz that's an IPC round trip on the
simulation's critical path. It isn't the "same message types, no code change" move the design claims. Maxim's
substrate also uses unseeded randomness (`decisions/significance.py` imports `random`, and the
`default_network/behaviors/*` modules use it), and the rule is one seeded generator owned by `World`.
**Fix:** Say plainly that substrates are part of the deterministic step, and that parallelising them means a
per-tick barrier with outputs ordered by actor. Add a Phase 3 item: an injectable RNG (a `numpy.random.Generator`
per agent, derived from the world seed) for every substrate component the simulation lane steps.

### A11. The docs and contracts this makes stale aren't listed
**Where:** "Decisions" (only `docs/architecture.md`'s "turn-based" line is named).
**Scenario:** After 2a ships, the docs still say:
- CLAUDE.md: "Actions change cells; only `World.advance` moves time". Under the design, the tick moves time and
  `advance` runs only on physics ticks.
- `docs/architecture.md`:
  - the diagram says "fixed turn";
  - "LLM latency lands in a dialogue screen, not in a combat loop" (the original rationale, now reversed);
  - head-of-line blocking is "harmless for a turn-based game" (it isn't, at 6.4 MB/s of snapshots with tick
    messages queued behind them);
  - "interpolation between turns";
  - the known gaps are counted in turns ("after 150 turns", "turn 50"), which now have no unit.
- `docs/roadmap.md`:
  - Phase 0's "a turn loop";
  - Phase 4's "a dialogue screen and turn order";
  - the open question "Turn length: 6 s".
- `docs/standards_backlog.md`:
  - B2 "with its turn";
  - B5 "turn time";
  - B7 "fixed camera and turn".
- `docs/code_review.md`: the Performance lens says "per turn", and the Lifecycle row says "turn start and end".
- Code:
  - `world/world.py`: `World.turn`, `World.turn_seconds` and the module docstring;
  - `world/__init__.py` ("the turn loop");
  - the `heat.py` module docstring;
  - the rig YAML comments.

`World.turn` would quietly come to mean "physics steps taken", with no reader.

**Fix:** Add a "Supersedes" section that lists each of these and what it becomes. Delete `World.turn` and
`turn_seconds`, or rename them to the physics-step meaning, in 2a. Decide the Phase 4 dialogue model (does talking
pause the world, as with a tactical pause, or run on with the hold?), because it reverses the roadmap's line.

### A12. Save v0 (Phase 1) and in-flight state aren't designed together
**Where:** §6 (no save), roadmap Phase 1 "Save format v0: the world grid plus the scene spec".
**Scenario:** A save taken mid-run under this design has to carry:
- the tick;
- the heat sources;
- intents queued for future ticks;
- thoughts in flight, with their deadlines;
- the RNG state and the world config.

"The grid plus the scene spec" has none of these. If a thought is pending at save, then on load either its result
never arrives, so the world holds until the timeout and then logs `thought_failed`, or it's re-requested with a new
deadline. That changes the outcome, depending on when you saved.
**Fix:** Define save v0 as a checkpoint of `Simulation` (A1) plus the log header, and a rule that in-flight thoughts
are cancelled and logged as `thought_cancelled_by_save`, or re-issued at their original deadline. Make the save
format a 2a dependency, or note that save v0 has to follow 2a.

## NIT

### A13. Network lanes "one per client" don't fit the transport
Python `websockets` is asyncio: one event-loop thread serves every connection. A thread per client is overbuilt and
would fight the library. Fix: one network lane (the event loop) with per-session state and per-session outbound
queues with bounded depth.

### A14. `snapshot_hz` and the deliberation times aren't deterministic world config
`snapshot_hz` affects only the network. If it sits with `tick_s` in "world config", changing it looks as though it
invalidates replays. Fix: split `data/world/<name>.yaml` (deterministic, pinned in the log header) from
`data/server.yaml` (cadence, timeouts). Deliberation `d` *is* deterministic, so it belongs in the pinned file. Name
the paths and add them to B12.

### A15. Physics ticks make tick time bursty
Every fifth tick carries a whole period's physics. At max on a tile, that's hundreds of ms on one tick and next to
nothing on the other four, so a per-tick dilation meter oscillates. Fix: meter dilation over a window of at least
one physics period, and say so in the B5 row.

### A16. The `time` message's `scale` is required by the table even for pause and resume
Fix: specify `scale` as required for `set_scale` only, and refused if present otherwise, so the validator has one
unambiguous shape per request.

## What I checked and found sound

- One owner of `World` with frozen messages is the right invariant. Making it the simulation lane's job is sound,
  given A1 (split the pure step from the host) and A3 (extend it to agents and the SEM bridge).
- The dial changes only how often `tick()` runs, never `tick_s`. Reporting dilation instead of stretching ticks keeps
  determinism and the resolution rule independent of the dial. `tick()` takes no duration, which B14 can test.
- Making the physics period world config rather than rig config keeps the latency from intent to heat the same at
  every rig, so the outcome class can't depend on the rig through timing. The split test (one 6 s advance against
  twelve 0.5 s advances) is the right extra test. Replacing a per-turn minimum with a per-second maximum fixes the
  root cause, not a band-aid (subject to A4's numbers).
- `TimeAuthority` as a policy, with "pending" reserved and the decision logged, is the right size: cheap now, with
  no protocol change for a vote. Assigning the actor from the session, never from the message, is correct.
- Leaving out LAN play, prediction, rollback and accounts is the right scope. Interest management and deltas fit
  later as per-session views over one immutable published snapshot, without changing the simulation lane, provided
  sessions keep their own baseline state (A13's per-session queue).
- The order 2a then 2b is buildable if A1 holds. If the pure `Simulation` step and the message types land in 2a,
  2b adds only threads, the thinking stub and meters, and tears nothing out. Without A1, 2a's `WorldHost.tick()` is
  rewritten in 2b.
- The protocol table: `advance` out of the client's vocabulary, the token in `hello` rather than the URL, the
  axis order fixed with a golden fixture, and compression fields reserved. All are consistent with
  `docs/architecture.md`'s transport decision.
- The Maxim changes (items 10 to 13) are correctly routed to Phase 3 rather than patched here. A3 and A10 add two
  more (a turn with no side effects, an injectable RNG).
