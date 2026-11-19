# Real time, lanes and co-op (design v1, 2026-11-15)

> **Superseded 2026-11-16 by `world_v2.md`,** which folds this design, its delta review (`reviews/realtime_lanes_coop/delta1_*.md`)
> and the states-of-matter deep dive. Kept as the record of how the decisions were reached.

**Status:** DRAFT v1, the design-review fold. v0 (52e64f0) was reviewed by seven lenses: Executor, Architecture,
Wire integrity, Bio-faithful integration, Determinism and replay, Concurrency and performance, and Trust boundary.
Their findings, 22 BLOCKER, 61 SHOULD-FIX and 24 NIT, are kept verbatim in `docs/design/reviews/realtime_lanes_coop/`,
and `README.md` there records how each was folded. Finding ids below (A3, TB-1, X1 …) point into those files.

This design replaces Phase 1 step 2 as first briefed (a client that sends `advance` and `act` to a turn-based
server) with four PRs (§8). Nothing here is built until the owner accepts it.

## Decisions

**Owner, 2026-11-15:**
1. **Real time with pause, on a fixed tick.** Not turn-based. Maxim's SCN learns daily and weekly rhythms, and
   Maxim's hybrid runtime puts a fast substrate loop under slow LLM deliberation. A world that only moves when the
   player acts gives neither anything to work with. Every lens found this sound.
2. **The time scale is a dial from the start.** Slow motion, normal speed and fast-forward are values of one
   number. Pause is a separate state, not a dial value (W-F9).
3. **Day length is a knob, held at 24 hours for now.** Varying it later is an experiment in time dynamics (§3.4).
4. **Time control is host-only, behind a policy** that a vote can replace.
5. **Step 2 is split into several PRs.**
6. **Bio-faithful integration is a standing lens** for design reviews and for every change an NPC senses, acts
   through or keeps time by (`docs/code_review.md`).

**Owner, on the v1 fold (2026-11-15):**
7. **Neither the world nor the NPC waits for a thought.** Waiting isn't bio-faithful. Needing to wait is a sign the
   hybrid mode isn't working as intended, so it's something to find out through experiments, not to build around
   (§4.3). Building and tuning the hybrid mode, through experiments in the game and on real robots, is proposed to
   Maxim as a 1.5 line (§6).
8. **The dial stays free,** with fast-forward presets for waiting and sleeping (§3.4).
9. **The hybrid plan's revive trigger covers simulated bodies,** as a re-keying proposed to Maxim. The Microduck,
   due in about a month, will meet the physical trigger anyway.
10. **Push back on Maxim's plans where the game shows they're wrong,** through Maxim's own process. Guiding Maxim
    through a real application is a pillar goal of this project, and it's now a standing rule in CLAUDE.md
    ("Working").

## 1. What the review changed, in brief

- **The deterministic core is a `Simulation`, not the host** (A1, W-F3, X3). The `Simulation` owns `World`, the
  integer tick, the world config, the RNG and, later, the agents. The host only collects inputs and paces calls to
  `Simulation.step`. Replays, cradles and tests drive the `Simulation` directly, with no sessions.
- **One clock, in integers** (A5, D7, W-F8, X-N3). The world's time is `tick × tick_us` microseconds. `grid.time_s`,
  `World.turn` and `World.turn_seconds` go: anything that needs world time derives it from the tick.
- **The cost table was wrong**, found by four lenses (X1, CP-1, A4, W-F7). `World.advance` recomputes the fire's
  sphere overlap (64 passes over the whole grid per source) and the stability limit on every call. Calling it 12
  times per 6 s instead of once makes physics about 4 to 14 times dearer per world second. The root fix (§2.3) comes
  before any real-time loop.
- **Maxim's agents are far less ready for a deterministic world than v0 said** (D1, Bio-1 to Bio-4, X4 to X6, A3,
  CP-2). More of Maxim's substrate reads the wall clock than the three systems v0 listed: drives, DN timers, NAc
  decay, sleep forgetting, hippocampus de-duplication, percept timestamps. Agent state is written during LLM calls,
  and ids come from `uuid4`. Phase 3 grows from 4 items to 8 (§6), and until they land the determinism promise
  covers the world and stub agents only (§4.4).
- **Input validation had a live hole in code that's already committed** (TB-1, X7). The SEM `structure` modulator
  accepts NaN, infinite and negative values; a NaN `ignite` turns every cell's temperature to NaN after one advance.
  It's fixed first, on its own PR (§8), because NPCs already use this path.
- **The intent log is a versioned format** (A2, D2, W-F2), and **every client message gets exactly one final
  reply**, including every intent (W-F1).
- **Co-op roles are bound to tokens** (TB-4, A8, W-F13). Separate host and guest tokens, no promotion, and the world
  pauses when the host leaves.
- **Backpressure everywhere** (TB-8, CP-5): bounded inbound queues, latest-wins outbound slots.

## 2. The simulation and its clock

### 2.1 Ownership

```
Simulation (deterministic, in a scanned package, imports nothing from server/)
  ├── World (cells, physics; no clock of its own)
  ├── tick: int, the only clock
  ├── WorldConfig (frozen, integers): tick_us, physics_every_ticks, day_length_ticks, epoch_us
  ├── rng: numpy.random.Generator, seeded from the log header
  ├── actors: an allocator of integer ids, in the order joins are applied
  └── step(inputs: StepInputs) -> StepOutputs        (inputs are the validated, ordered records for this tick)
```

- `Simulation.step` is the only thing that moves time. CLAUDE.md's "only `World.advance` moves time" becomes "only
  `Simulation.step` moves time"; `World.advance(seconds)` stays as the physics call that `step` makes on physics
  ticks (W-F3, A11).
- **Within a tick, the order is fixed** (D10): (1) apply this tick's records in log order (joins, leaves, time
  decisions, intents, thought results); (2) step agents (Phase 4; a no-op until then); (3) on ticks where
  `tick % physics_every_ticks == 0`, run physics for the interval that ends at this tick; (4) emit outputs (tick
  status, and a snapshot when cells' version changed).
- **A save is a `Simulation` checkpoint plus the log header** (A12): the tick, the RNG state, the world, queued
  records and the thoughts in flight with their deadlines. Save v0 itself stays a Phase 1 item.

### 2.2 World config (integers, frozen per run)

| Field | Proposed | Meaning |
|---|---|---|
| `tick_us` | 100,000 | world time per tick (0.1 s) |
| `physics_every_ticks` | 5 | physics runs every 5 ticks (0.5 s) |
| `day_length_ticks` | 864,000 | 24 hours at 0.1 s per tick |
| `epoch_us` | an integer, UTC, with no time zone | the world's date and time at tick 0 |

- Time of day is `(epoch_us + tick × tick_us) mod (day_length_ticks × tick_us)`, in integers (D7).
- World config lives in `data/world/` and is hashed into the log header. Server config (`snapshot_hz`, queue
  limits, rate limits, caps) is separate, in `data/server/`, because it doesn't change the world (A14).

### 2.3 Physics on a period, at no extra cost: the root fix comes first

- **The rig field changes from `min_substeps_per_turn` to `substeps_per_physics_step`, an integer** (X2, W-F7,
  CP-1). With a 0.5 s physics step: laptop 1 (0.5 s substeps, finer than today's 1.5 s), rig 2 (0.25 s, finer than
  0.375 s), max 6 (0.083 s, finer than 0.094 s). Precision is never coarser than today at any rig. The heat
  solver's stability limit still applies on top. An old rig YAML is refused with a message naming the new field.
- **Stop recomputing what hasn't changed** (X1, CP-1). Compute each source's sphere overlap only over its bounding
  box, and once per source, since it depends only on geometry. Cache the power field and `stable_dt` behind a
  version counter that adding a source, removing one and `destroy` all bump. This is the root fix for the cost, not
  a tuning: today's code does O(cells × 64) work per call regardless of whether anything changed.
- **Tests that come with it:** a period-split cross-tier test (one 6 s run against twelve 0.5 s steps, same outcome
  class at every rig); a closed-form check that the cached power field equals a fresh one after each kind of
  change; and the existing heat tests on the new rig field, whose two `test_heat.py` calls are rewritten to the new
  meaning (X2), not reinterpreted.

**Cost, measured by the review on a full 16×10×4 m tile (CP-1); to be re-measured on a committed tile by B5:**

| Profile | Fastest sustainable dial, v0 as designed | With the caching fix (estimated) |
|---|---|---|
| laptop, 0.2 m | about 44× | about 300× |
| rig, 0.1 m | about 5× | about 20× |
| max, 0.05 m | about 0.4× | about 0.75×, slower than real time |

The max profile can't keep real time on a full tile until Phase 2's "Scale" item lands. That's allowed: the world
stays correct, and the dial reports dilation. Every physics tick is lumpy (CP-9: about 100 ms at rig and up to
1.2 s at max as v0 was designed), so the meters report p99 tick time and the delay before a control request
takes effect.

## 3. Time, the dial and the day

### 3.1 The dial

`time_scale` is world seconds per wall second, a finite number in `[min_scale, max_scale]` from server config.
Pause is a separate flag, not scale 0 (W-F9). The dial changes only **how often the host calls `step`**, never what
a step does, so the dial never changes the bits of a replay or the outcome class of a run.

- **Dilation is reported, never hidden.** When the host can't step as fast as the dial asks, it steps as fast as it
  can, and the tick status carries the effective scale, measured over at least one physics period (A15).
- **Unpaced is a host mode, not a dial value** (W-F9: `inf` isn't valid JSON). Headless runs, cradles and tests
  call `step` directly.
- **The dial, dilation and thought deadlines never reach a percept** (Bio-11). An NPC can't sense how fast the
  player's machine is running the world.

### 3.2 The day knob and Maxim's calendar

Maxim's `TemporalSignature` computes circadian, weekly, monthly and annual phase from a Unix timestamp with
`datetime.fromtimestamp`. That's host-local time, with daylight saving, and 86,400 s is hard-coded (X5, Bio-2,
W-F10). Two machines would give the same world moment different phases. The fix is Maxim's (§6 item 10): one world
clock for every `TemporalSignature` producer, phase from world time and the world's day length, no local time. Until
then, NPCs must not run against the world clock with their SCN on host time.

### 3.3 The experience clock

The world declares itself to Maxim's `ExperienceClockDriver` as a turn-based world: `experience_turns()` returns the
tick, and `experience_us_per_turn` is `tick_us` (W-F11, Bio-9). A paused world then produces no experience,
so NPCs don't forget while paused. Two caveats from the review: the driver only runs inside Maxim's full agent loop,
not under `AgentPool.run_turn` (X4), and most decay in Maxim still runs on the wall clock until Maxim's #1361 lands
(§6).

### 3.4 Play against a 24-hour day (owner decision 8)

At 1× with a 24-hour day, a play session sees little of one day, NPCs never sleep in it, and drive rates tuned for
Maxim's two-minute experiments run far too fast or slow (Bio-8). A day in an hour (24×) isn't reachable on a rig
tile even with the caching fix (CP-10).

- **The dial stays free** for the host, within the server's `[min_scale, max_scale]`.
- **Fast-forward presets** for waiting and sleeping are named dial values in `data/server/` (for example "wait" and
  "sleep"). They're host requests like any other, and they're capped by what the rig can sustain, with dilation
  reported.
- **NPCs live most of their days in headless cradles,** unpaced, so they arrive with whole days and nights behind
  them.

A different day length gives the SCN perfect entrainment to any period, because Maxim's SCN has no intrinsic period
apart from the clock it's given. A real day-length experiment needs one, and Maxim's own pre-registration (Bio-7).

## 4. Lanes

> **Superseded in part (2026-11-16).** Agent ownership in §4.1 ("owns Simulation (and through it World and
> agents)", "agents step inside the simulation lane's tick"), arrival-order `host_seq` and request-id assignment in
> §4.2, and several §4.3 rules are replaced by `npcs_and_sem.md` §11.1 and `boundaries.md` §6.2 and §7.1. Read those
> first; the rest of this section stands.

### 4.1 One owner, explicit channels

```
             ┌──────────── simulation lane: owns Simulation (and through it World and agents) ───────────┐
 records ──▶ │ waits on ONE inbox: intents, controls, thought results, stop                             │ ──▶ outputs
             │ assigns each record its tick and a host sequence number, writes it to the log, then      │   (latest-wins
             │ applies it in Simulation.step                                                            │    slot per
             └──────────────────────────────────────────────────────────────────────────────────────────┘    session)
       ▲                                ▲                                                   │
 network lane: ONE asyncio         thinking lane: a worker pool                  record lane: the log is written
 loop thread, a task per           with a frozen request in and a                synchronously by the simulation
 session; decodes and              pure result value out                         lane each tick (CP-6); this lane
 schema-checks, never                                                            only flushes and rotates
 touches World
```

- **The network lane is one asyncio loop thread** with a task per session (A13, CP-7). Inbound: `put_nowait` onto a
  bounded per-session queue; full means a `busy` error reply. Outbound: the simulation lane writes the latest tick
  status and snapshot into per-session slots and wakes the loop with `call_soon_threadsafe`. `websockets` gets
  `compression=None`, a small `max_size` (about 64 KiB, because snapshots go out, not in; TB-7), and a bounded
  `max_queue`.
- **Moving a lane to a process is possible, not free** (A10, CP-N1). Agents step inside the simulation lane's tick,
  so moving them out means a lockstep barrier every tick and messages that pickle.
- **Lifecycle and crashes** (TB-2, CP-6): an exception in the simulation lane is a bug, and the host fails loudly:
  it flushes the log (including the record that caused it), stops every lane and joins every thread. It never
  swallows the exception and carries on. A network task's failure ends only its session. `WorldHost` is a context
  manager. A test injects a crash into each lane and checks that every thread is joined. TB-1's validation is what
  keeps valid input from ever raising.
- **Meters, each a B5 row** (CP-12): physics-step breakdown, p99 tick time, control-request delay, fastest
  sustainable dial, peak memory, CPU against wall time for the simulation lane (CP-11, GIL), queue depths, slot
  overwrites and overflows, and for thinking: requests in flight, late and failed results. Budgets use best-of-N or
  operation counts, not one wall-time sample.

### 4.2 Ordering and ids (D3, D4, D6, A6, TB-12, W-F5)

- **The host assigns the order.** Each record gets `(tick, host_seq)` when the simulation lane takes it off its
  inbox, and the log stores it. A replay applies records in log order. The client's `seq` is only echoed in replies.
- **Which tick an intent gets depends on when it arrives,** in a live run (X8). That's input, like a keypress, and
  the log records it. Only replays are independent of timing.
- **Actor ids are integers from the simulation lane's allocator**, issued when a join is applied, never reused,
  for players and NPCs alike. NPCs are allocated in roster order at load.
- **Thoughts due on the same tick apply in request-id order**, where the request id is `(tick, actor, n)` assigned
  by the simulation lane.

### 4.3 The thinking lane

- **A thought request is a frozen context, built from the state at tick T, and its result is a pure value** (A3,
  CP-2): the intents the NPC will try, plus the memory writes it wants. The simulation lane applies both at the
  deadline, through the same validators as client intents (TB-15, A7), and logs them. The model never touches
  `World` or agent state from the thinking lane. Maxim's turn today writes the hippocampus and NAc during the LLM
  call, so this needs Maxim's "generate vs apply" split (§6 item 16); the 2b stub has this shape now.
- **Nothing waits for a thought: not the world, and not the NPC** (owner decision 7). A living animal can't stop the
  world while it thinks, and it doesn't freeze either. While a thought is in flight, the NPC's substrate keeps
  acting: its reflexes, habits and the action it's already doing. **If an NPC would need to wait, the hybrid isn't
  working as intended.** That's a finding for the hybrid experiments (§6), never a mechanism to build here.
- **A thought applies on the first tick after it arrives.** The simulation lane takes it off its inbox at a tick
  boundary, and the log records the tick it applied at, so replays are bit-identical (A9, D5). At that tick the
  result passes the same validation as any intent, against the world as it is then (Bio-5). An action the world has
  overtaken is refused as stale, and the refusal goes back to the NPC as an outcome, which is something it can learn
  from.
- **Abandoning a thought is decided in world time** by the simulation lane. A thought older than `max_age_ticks`
  (in `data/`) is abandoned, logged as `thought_failed`, and a later arrival is dropped. Pain or salience can cancel
  a thought in flight (§6 item 13). The model call's own wall-time timeout only frees its worker (CP-4), and its
  failure arrives as a message, applied and logged like any result.
- **With live models, thinking speed in world time depends on the dial.** In slow motion an NPC gets more thought
  per world second, and at fast-forward less. That's a real property of a mind in a faster or slower world, so it is
  measured rather than hidden. Decision 2 still holds for replays and scripted runs (§4.4 tiers 1 and 2). Live
  models are tier 3, which was never reproducible.
- **The signs that the hybrid isn't working are meters, per NPC:**
  - thought latency in world ticks;
  - the stale-refusal rate;
  - the fraction of ticks the NPC acts on its substrate alone while a thought is in flight, and what it does then;
  - reflex-against-deliberation conflicts;
  - abandoned thoughts;
  - LLM calls per NPC-hour.
  
  These are what the hybrid experiments tune against.
- **The queue orders by priority, then age, with one outstanding thought per NPC** (CP-4). The NPC the player is
  talking to comes first.
- **The test stub has a fixed latency in ticks**, so scripted runs with stub agents stay bit-identical at any dial
  (tier 2).

### 4.4 What determinism promises, in three tiers (D9, D1)

1. **Replays are bit-identical** on one machine: same scene, rig, world config and log.
2. **Scripted runs are bit-identical at any dial and any pacing**, with stub agents, because a stub thought is a
   pure function of its request.
3. **Live models or live players aren't reproducible.** The log is the only reproduction, and it is complete.

Real Maxim agents join tier 1 only when §6's deterministic-agent items land (D1). A tripwire test makes `time`,
`uuid` and the global `random` raise inside `Simulation.step`, so any agent code that reaches them fails loudly. The
host code lives in a package the AST scan covers; `server/` holds only the transport (D8). The hash-seed test grows to
a multi-session replay.

## 5. Sessions, tokens and co-op (TB-4 to TB-6, TB-14, TB-16, A8, W-F13)

- **Two kinds of token, fresh each launch:** one host token and up to N guest tokens. The role is bound to the
  token, compared with `hmac.compare_digest`. One live session per token, and no promotion. Tokens reach the client
  by environment variable or a 0600 file, never argv, and never appear in a log or an error echo.
- **The handshake:** `hello` comes first and only once, within a deadline; anything else closes the session. There's
  a session cap. Client binary frames are refused. Any request carrying an `Origin` header is refused, including an
  empty one or `null`. Plain HTTP to the port gets a 400. The server binds the literal `127.0.0.1`.
- **Joins and leaves are records** at a tick, in the log. When a guest leaves, its intents that already have a tick
  apply and the rest are discarded. **When the host leaves, the world pauses** (a logged time decision) until the
  host token reconnects.
- **`TimeAuthority`** sees a frozen view of the sessions. `HostOnly` grants the host and refuses guests, with a
  reason; it never returns `pending`. A `vote` message is refused in v0 (TB-17). A future vote needs a timeout and
  a quorum rule, and the "pending" reply is reserved for it.
- **Same-tick conflicts favour whoever applies first** in host order (TB-18), which is arrival order, not actor id.

## 6. Maxim upstream: Phase 3, revised

Each goes to the Maxim repo through Maxim's own issue, plan and four-lens review. None is patched here.

| # | Item | Why the game needs it |
|---|---|---|
| prerequisite | **#1361, experience-clock decay** (`docs/plans/experience_clock_decay.md`: NAc decay, eligibility and windows, `Embodiment.advance`, `decay_all`), already proposed with owner decisions taken | paused NPCs otherwise get hungry and forget on the wall clock (Bio-1) |
| 10 | **One world clock for every `TemporalSignature` producer and percept timestamp**: phase from world time and the world's day length, no local time; the SCN oscillator integrates elapsed time, not one hour per event. It argues against #1361's §(g), which keeps SCN phases on the host calendar by design (decision 10). | X5, Bio-2, Bio-6, W-F10 |
| 11 | **An externally stepped Default Network**: `step(world_now)`, every DN timer on the injected clock, an injected RNG, a non-visual input channel, per-behaviour suppression and efference copy (the hybrid plan's BL-2, A3, A4, SF-1, SF-2) | X6, Bio-3, Bio-10 |
| 12 | **An externally stepped agent live tick** (not `AgentPool`, which has no body, drives or DN): `step(world_dt)` driving the experience driver, `Embodiment.advance` and the proposer, proposing on action completion, not every tick | Bio-3, X4 |
| 13 | **Cancellable deliberation with a world-time deadline**, cancellable by bottom-up escalation (joins item 7) | Bio-5 |
| 14 | **Consolidation without ending the session**, on experience time, with idle replay | Bio-4 |
| 15 | **Deterministic agents**: an injected clock, RNG and id source across agent code (hippocampus de-duplication on `time.time()`, `uuid4` ids, the global `random` in DN); a world-seeded RNG | D1, A10 |
| 16 | **Generate vs apply**: an agent turn that returns its intents and memory writes as values, with no side effects during the LLM call | A3, CP-2 |
| 17 | **Re-key the hybrid plan's revive trigger** (today a second physical robot body, `outstanding.md` M76) to include a simulated body in the game, and decide the Phase 4 movement-on-substrate, speech-on-LLM split in a Maxim plan. The Microduck's arrival meets the physical trigger too. | owner decision 9; Bio-3, X6 |
| 18 | **A Maxim 1.5 line: build the hybrid runtime and tune it by experiment**, in the game and on real robots (Reachy, the Microduck). Its pre-registered experiments ask whether the substrate carries an NPC while deliberation is in flight. Draft: `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`. | owner decision 7 |

The Exp 64 pre-registration draft (`docs/maxim_upstream/`) needs updating for real time before it freezes (Bio-12):
host-clock temporal credit, the shipped NPC path (Maxim's turn path or the game's tick), a failed thought as the
outage abort, encounter spacing pre-registered in ticks, and frozen drift through #1361's `Embodiment.advance`.

## 7. Protocol v0

The transport is as decided (`docs/architecture.md`, "Transport"). **Closed schemas everywhere** (TB-3, W-N4):
unknown message types, fields and params are refused, including any client-sent `actor`, `tick`, `role` or
`session`. JSON is parsed with NaN, Infinity and out-of-range numbers refused (TB-1). **Every client message gets
exactly one final reply** (W-F1).

**Client to server** (amended at the merge, DC-B2): the messages are `tile_and_client.md` §3.3's, which replaces
this table. `act` and `act_result` are retired: one message per kind (`move`, `move_to`, `kindle`, `time`,
`snapshot`), `intent_result` as the one reply to an intent, and no client message carries a region or an actor.
`seq` is an integer in `[0, 2^31)` and must increase within a session (W-F5).

**Validation runs in two stages** (TB-13). The network lane checks the schema: types, finiteness, ranges, caps from
`data/server/`. The simulation lane checks what depends on the world at the record's tick: the target exists, the
intent is allowed, the per-tick limits. Both refusals are `error` or `intent_result` replies with a code from a
listed vocabulary (W-N3), and the world is unchanged. The intent validator is the same one PR 1 (§8) adds to the
SEM bridge, so NPCs, LLM results and clients pass one gate. Per-session rate limits and a cap on heat sources bound what valid
intents can cost (TB-10).

**Server to client.**

| Message | When | Carries |
|---|---|---|
| `welcome` | after a valid `hello` | `session`, `actor`, `role`, the world config, the rig, `dx`, `shape` with its axis order, the region list with each region's affordances, the material table, and the current time state (W-F12) |
| `tick` | each tick, throttled per session | `tick`, `world_time_us`, `time_of_day_us`, requested and effective scale, paused |
| snapshot (binary) | when cells' version changed, at most `snapshot_hz` per session (2 Hz is the normal rate during any fire, CP-8), and on request | `[u32 header length][JSON header][array bytes]`, little-endian; the header has `kind: "full"`, `protocol`, `tick`, `shape: [nz, ny, nx]`, `axis_order: "zyx"`, `frame: "z-up"`, and for each array its name, dtype from a listed vocabulary (`u8`, `<f2`), offset from the start of the array section, stored and uncompressed size, and compression (`none`) |
| `error` | a refused message | `code`, `message`, `in_reply_to`; the world is unchanged |

- **Readers refuse** an unknown protocol version, `kind`, dtype or compression, loudly (W-F6).
- **Axis order is Godot's** (W-F4, X-N2): arrays are sent z, y, x with x varying fastest, one `Image` per z-slice for
  `ImageTexture3D`. The server is z-up and Godot y-up, so the client maps axes in one place, the shader. An
  **asymmetric golden fixture** (a different value at each corner) holds both conventions.
- **Snapshots are encoded once per published tick and shared** across sessions (CP-8), and their arrays are
  read-only (D11, W-N2).
- **Compression is off in v0**, with the field reserved. A roadmap item tries zstd at several levels once real
  scenes exist.

**The intent log v0** (A2, D2, W-F2) is a versioned file:
- **Header:** format version, protocol version, code SHA, pymaxim, numpy and Python versions, platform; content
  hashes of the scene, rig, material table, world config and agent roster; the RNG seed; each agent's initial state
  hash.
- **Records:** `tick`, `host_seq`, `kind` (join, leave, time decision, intent, thought result, thought failed),
  `actor` and the validated payload.
- **Every N ticks a state digest, and an end marker** with the final tick (ticks with no records still run).
- **Only the simulation lane writes records.** The reader is itself an untrusted loader (TB-15): it validates
  every record and refuses a header it doesn't match.
- **Golden fixtures**, like every other format (B3).

## 8. The PRs

1. **`phase1/act-validation`: fix the input hole in committed code** (TB-1, X7). Typed, frozen parameters for
   `strike`, `ignite` and `extinguish`, built with `finite_vector`; NaN, infinite, negative and out-of-range values
   refused, with caps from `data/`; a second check inside `damage.strike` and `HeatSource`. It starts with a test
   per probe the review ran, each red first, plus a Hypothesis property: no input crashes the modulator or leaves a
   non-finite value in the grid.
2. **`phase1/sim-clock`: the `Simulation`, the integer clock and the physics cost fix** (§2). This includes the
   rig-field change, caching, the period-split cross-tier test, the cost table re-measured on a committed tile
   (B5's first rows), and the "Supersedes" doc updates (below).
3. **`phase1/protocol`: protocol v0, sessions and tokens, `TimeAuthority` with `HostOnly`, the host with stepped and
   constant-scale wall pacing, the intent log v0 with a replay test, golden fixtures (B3), and the B14 refusals.**
   Its test list is the 41 rejection paths in `reviews/realtime_lanes_coop/trust_boundary.md`, plus one end-to-end
   test over a real localhost WebSocket.
4. **`phase1/lanes`: the lanes, backpressure, the thinking lane with its stub and late-thought semantics, the meters, and the
   crash-injection tests.**

Each PR runs the standard review round plus the lenses it triggers, Bio-faithful included where it applies.

### Supersedes (A11, W-F14, X-N4)

When PR 2 lands, these change in the same PR:
- CLAUDE.md: "only `World.advance` moves time".
- `docs/architecture.md`: "The game is turn-based"; head-of-line blocking "harmless for a turn-based game"; the
  buffer-cap advice (TB-7: only the client raises its cap); known gaps counted in turns.
- `docs/roadmap.md`: Phase 4's "dialogue screen and turn order", the "Turn length" open question, and the new
  Phase 3 items.
- `docs/standards_backlog.md`: B2's "turn", B5's rows, and B7's fixed turn.
- Code: `World.turn` and `turn_seconds`, `min_substeps_per_turn`, docstrings and the rig YAML comments.

## 9. Questions the v1 fold raised, and their answers

1. **Hold the world for a late thought?** No: neither the world nor the NPC waits (decision 7, §4.3). The
   bio-faithful reviewer's case for holding was that deliberation is lived time. Under decision 7 that stays true,
   because the NPC lives through its deliberation by acting on its substrate. The world doesn't stop for it.
2. **Play against a 24-hour day?** A free dial with "wait" and "sleep" presets, plus headless cradles (decision 8,
   §3.4).
3. **The hybrid plan's revive trigger?** Re-key it to cover simulated bodies (decision 9, §6 item 17).
4. **#1361's §(g)** (SCN phases on the host calendar by design)? Argue against it in Maxim (decision 10, §6 item 10).

A delta review of v1 runs on §3.4, §4.3, §6 and the new draft in `docs/maxim_upstream/` before PR 2 is built.
