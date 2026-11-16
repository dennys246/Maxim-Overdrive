# Real time, lanes and co-op (design v0, 2026-11-15)

**Status:** DRAFT, for a design review before any code. It replaces Phase 1 step 2 as first briefed (a client that
sends `advance` and `act` to a turn-based server) and splits it into steps 2a and 2b. The review's findings and
how they were folded go in `docs/design/reviews/realtime_lanes_coop/`.

## Decisions (owner, 2026-11-15)

1. **Real time with pause, on a fixed tick.** Not turn-based. The reason: Maxim's SCN learns daily and weekly
   rhythms, and Maxim's hybrid runtime puts a fast substrate loop under slow LLM deliberation. A world that only moves
   when the player acts gives neither anything to work with.
2. **The time scale is a dial from the start.** Slow motion, normal speed and fast-forward are values of one
   number, not separate modes. Pause is the dial at zero.
3. **Day length is a knob, held at 24 hours for now.** Varying it later is an experiment in time dynamics.
4. **Time control is host-only, behind a policy** that a vote can replace without protocol or host changes.
5. **Step 2 is two PRs:** 2a (protocol, sessions, the host and its tick loop) and 2b (lanes, the thinking lane,
   metering, real-time pacing under load).
6. **A design review before code,** with new lenses for this design, including bio-faithful integration.

`docs/architecture.md` ("The game is turn-based") gets a dated decision record pointing here when this design is
accepted.

## 1. The world clock

The world's time is `tick × tick_s`. Nothing else is the world's time.

- **`tick_s` is fixed for a world**, a world-config value in `data/` (proposed: 0.1 s). The rig never changes it,
  so the tick count for a given scenario is the same at every profile.
- **Physics runs at its own period**, `physics_period_s` (proposed 0.5 s of world time, a multiple of `tick_s`).
  Each physics step is `World.advance(physics_period_s)`. Intents that change cells land at the next tick, and their
  effect on temperature shows at the next physics step, at most `physics_period_s` later.
- **The rig profile's `min_substeps_per_turn` becomes `max_substep_s`.** Today the rig sets a minimum number of heat
  substeps *per turn*. The measured runs take exactly that minimum (4, 16 and 64 per 6 s turn at 0.2, 0.1 and
  0.05 m), so stability is not what limits them. Calling `World.advance` with a shorter period would keep the
  count and multiply the work: 60 times the substeps for the same simulated time at 0.1 s. The rig field becomes
  the longest substep it allows, in seconds (1.5, 0.375 and 0.094 s, the same precision as today). The heat
  solver's stability limit still applies on top of it. This is a rig-profile contract change, so it gets its own
  cross-tier test: the same scenario run as one 6 s advance and as twelve 0.5 s advances lands in the same outcome
  class, at every profile.
- **The day.** `day_length_s` (default 86,400) and `epoch` (the world's date and time at tick 0) are world config.
  Time of day is `(epoch + tick × tick_s) mod day_length_s`. v0 fixes both for a run. Changing either mid-run is a
  later intent, which the log would record.

### The dial

`time_scale` is world seconds per wall second: 0 is paused, 0.25 is slow motion, 1 is real time, 30 is
fast-forward. The dial changes only **how often the host runs a tick**, never what a tick does. Every tick advances
the world by the same `tick_s` at every speed. So:

- Determinism and the resolution rule don't depend on the dial. A run at 0.25× and a run at 30× with the same
  intents on the same ticks are bit-identical.
- Slow motion costs nothing extra, and it's not a separate mode. A tactical slow-motion view is a client choice of
  dial value.
- **Time dilation is reported, not hidden.** When the host can't run ticks as fast as the dial asks (the max profile
  is slower than real time on a full tile, below), it runs them as fast as it can, and the tick status carries the
  effective scale. The world is never stepped with a longer `tick_s` to catch up.
- **Headless mode is the dial at "unpaced".** Cradles, experiments and tests run the same host with no wall pacing
  at all: a test steps ticks directly, and an experiment runs as fast as the machine allows. It's one code path, not
  a separate one. The wall clock never reaches `World`: the pacer only decides *when* to call `tick()`, and
  `tick()` takes no duration argument (backlog B14 tests this).

### What it costs (measured 2026-11-15 on the 3×3×2 m crate scene; the tile figures are scaled up, not measured)

| Profile | Physics time per 6 s of world time | Faster than real time by | A 16×10×4 m tile (36× the cells), estimated |
|---|---|---|---|
| laptop, 0.2 m | 0.9 ms | 6,700× | about 190× |
| rig, 0.1 m | 9 ms | 670× | about 18× |
| max, 0.05 m | 201 ms | 30× | **about 0.8×: slower than real time** |

These assume `max_substep_s` as above, so per world second the cost doesn't depend on `tick_s` or
`physics_period_s`. The max profile on a full tile runs slower than the world clock at a dial setting of 1×. That's
allowed: the world stays correct, the dial reports dilation, and Phase 2's "Scale" item (coarser cells beyond
`full_res_radius_m`, then numba or C) is what fixes it. B5 sets the budgets from measured tiles in step 3.

## 2. Lanes

**One owner of the world.** The simulation lane alone holds `World`. Every other lane talks to it through messages.
So determinism and replay hold however much else runs in parallel, and a lane can move from a thread to a process
without its code changing.

```
              ┌──────────── simulation lane: owns World, runs one tick at a time ───────────────┐
 intents ───▶ │ 1. take the intents for this tick, ordered by (tick, actor, seq)                │ ──▶ published
              │ 2. apply thoughts whose deadline is this tick (from the thinking lane)          │     snapshot
              │ 3. step each NPC's substrate, in actor order (Phase 4; a no-op until then)      │     (immutable)
              │ 4. on physics ticks, World.advance(physics_period_s)                            │
              │ 5. publish the tick status, and a snapshot when cells changed                   │
              └─────────────────────────────────────────────────────────────────────────────────┘
       ▲                        ▲                                         │
 network lanes             thinking lane (LLM)                       record lane
 one per client:           a worker pool; requests and               intent log, metrics,
 decode, validate,         results are messages; results             autosave (later)
 stamp the actor, queue    apply at a world-time deadline
```

- **The interface is a channel of frozen messages** (a dataclass per message type). In 2b lanes are threads with
  `queue.Queue` channels. A lane that turns out to be CPU-bound in Python (substrate stepping for many NPCs, say)
  moves to a process with the same message types. Python 3.14's free-threaded build is the other option, but it
  isn't relied on.
- **Ordering is part of the contract.** Intents are ordered by the tick the host assigns them, then by actor id,
  then by sequence number. The host assigns the tick when it takes the intent off the channel, never from a client
  clock. Nothing depends on thread scheduling, dict order or `hash()`.
- **Each lane is metered separately**, and each budget is its own B5 row:
  - Simulation: tick time, and dilation (effective vs requested scale).
  - Thinking: requests in flight, tokens, wall latency and late results, per NPC and per tile. The queue has
    priorities, so an NPC the player is talking to thinks first.
  - Network: bytes per second, snapshot size and queue depth per client.
  - Record: log bytes per second.

### The thinking lane and determinism

LLM output isn't deterministic, and its wall latency changes with load and with the dial. If a thought were applied
whenever it arrived, slow motion would make NPCs think faster *in world time* (more wall time per tick), and
fast-forward would make them slower. NPC behaviour would then depend on the dial, which decision 2 rules out.

So **a thought is scheduled in world time.** When a request is made at tick T, its result applies at tick
T + d, where d is the deliberation time in world seconds (set per request type in `data/`, for example a reply in
dialogue against a plan for the day). If the result arrives early, it waits. If it hasn't arrived by T + d, the
simulation lane **holds at that tick** until it does, up to a wall-time timeout (that's dilation, and it's reported).
At the timeout the thought resolves as `thought_failed`, and the NPC goes on with its substrate alone.

- **Every result, including `thought_failed`, goes into the intent log.** A replay reads results from the log and
  never calls a model, so replays stay bit-identical. A fresh run with live models is reproducible only in outcome
  class, as across machines.
- At fast-forward the host can only run as fast as thoughts complete. Thinking throughput then caps the effective
  scale, and the meter shows it.
- Holding the world for a thought is a choice to review. The alternative, applying late thoughts whenever they
  arrive, keeps the world moving but makes NPC timing depend on load.

### Substrate and the hybrid runtime (Phase 4, with Maxim changes)

Maxim's hybrid runtime puts a fast Default Network reflex loop, about 30 Hz, under slow LLM deliberation, which
suppresses reflexes one way only (`docs/plans/deferred/hybrid_substrate_reflex_runtime.md` in Maxim). The game's
version is step 3 of the simulation lane, the substrate, plus the thinking lane:

- Every tick each NPC's substrate runs: drives, reflexes, `NAc.recommend_action` over its affordances. It acts
  through the same SEM modulators and intents as the player.
- Deliberation runs in the thinking lane. While a voluntary action is in progress, its result suppresses the
  conflicting reflexes, one way only, as in Maxim's design.
- Each NPC gets its percepts from the world: SEM sensors over cells, sound and light from Phase 2. It never gets a
  synthetic signal that the world doesn't produce.

At 10 Hz this is slower than the Default Network's 30 Hz default. Whether a reflex loop at the world's tick keeps
its job is a question for the bio-faithful lens.

## 3. The world clock and Maxim's time systems

Three Maxim clocks meet the world clock:

| Maxim system | Reads today | In the game |
|---|---|---|
| `ExperienceClock` (memory strength, forgetting) | its world: elapsed monotonic time, or a fixed amount per turn (`runtime/experience_time.py`) | world time: a percept source declares the world's time, so a paused world doesn't make NPCs forget |
| SCN and `TemporalSignature` (circadian, weekly, monthly and annual phase) | the wall clock: `TemporalSignature.now()` and `from_timestamp(time.time())` | **needs an injected world clock** (Maxim change), or NPCs live on the player's machine time |
| Default Network (reflex loop) | its own 30 Hz thread with `time.time()` and `sleep` | **needs an externally stepped tick** (Maxim change), so the simulation lane drives it deterministically |

The SCN's day comes from `day_length_s`. With a knob instead of a constant, Maxim's 24-hour bins need either a
day-length-aware `TemporalSignature` or a world clock that reports phase. Which one is a Maxim design question. A
circadian clock is entrained by light in biology. The world produces light only from Phase 2, so until then the
world gives NPCs the time of day but no cue to entrain to.

**Phase 3 additions** (in Maxim, through its own process; numbers continue the roadmap's list):

10. An injectable clock for `TemporalSignature` and the SCN, with day length taken from it.
11. An externally stepped Default Network: `step(now)` with no thread and no wall clock.
12. A per-tick substrate step on `AgentPool` (today it has `run_turn` and `run_round`).
13. Deliberation requests with a deadline that can be cancelled, which joins item 7 (cancellable SEM actions).

## 4. Sessions, actors and co-op

The server-authoritative, intent-driven design is already the right model for co-op. These are cheap now and
expensive to add later:

- **Many sessions, one world, from v0.** A `WorldHost` owns the simulation lane. Each connection is a `Session`
  with its own token, actor and role (`host` or `guest`). Nothing assumes a single client.
- **The host assigns the actor.** An intent's actor comes from its session, never from the message. The world
  doesn't distinguish players from NPCs: both act through avatars, the same way.
- **Time control goes through a policy.** `pause`, `resume` and `set_time_scale` are *requests*. A `TimeAuthority`
  turns a request plus the sessions into a decision, or "pending". v0 ships `HostOnly`: the host's request is
  granted, and a guest's is refused with a reason. A vote is another `TimeAuthority`, with no protocol change
  beyond a "pending" reply, which v0 already reserves. The log records the *decision*, so a replay never re-runs
  the policy.
- **Each session gets its own snapshot.** Each has its own cadence and, later, its own view (interest management:
  only what's near its actor). In v0 the view is the whole tile.
- **Deliberately not now:** listening beyond 127.0.0.1 (LAN play), NAT traversal, client prediction or rollback,
  accounts. Each would be a deliberate protocol and security change. One exception: the client may smooth
  its own avatar's motion between snapshots, as a purely visual effect, which the standing rules already allow.

## 5. Protocol v0

The transport is as decided (`docs/architecture.md`, "Transport"). JSON text messages carry control. A binary
message is `[u32 header length][JSON header][array bytes]`, little-endian.

**Client to server.** Every message carries `seq`, and the reply echoes it.

| Message | Fields | Notes |
|---|---|---|
| `hello` | `protocol: 0`, `token` | first, and only once; the token travels here, not in the URL |
| `act` | `region`, `action`, `params` | the SEM `structure` modulator's vocabulary (`strike`, `ignite`, `extinguish`), validated before anything is applied |
| `time` | `request: pause \| resume \| set_scale`, `scale` | goes to the `TimeAuthority` |
| `snapshot` | (none) | asks for a full snapshot now |

**Server to client.**

| Message | When | Carries |
|---|---|---|
| `welcome` | after a valid `hello` | `session`, `actor`, `role`, `tick_s`, `physics_period_s`, `day_length_s`, `epoch`, rig name, `dx`, `shape` |
| `tick` | each tick, throttled per session | `tick`, `world_time_s`, `time_of_day_s`, requested and effective scale, paused |
| snapshot (binary) | when cells changed, at most `snapshot_hz` per session, and on request | the header: `protocol`, `tick`, `world_time_s`, `shape`, `axis_order: "zyx"`, and for each array its name, dtype, offset, stored and uncompressed size, and compression (`none` in v0) |
| `time_decision` | a reply to `time` | granted, refused with a reason, or pending (reserved for a vote) |
| `error` | a refused message | `code`, `message`, `in_reply_to`; the world is unchanged |

- **Axis order is Godot's, fixed now.** Arrays are sent in z, y, x order with x varying fastest, which is what
  `ImageTexture3D` expects. A golden fixture holds the convention, so the client never transposes.
- **`advance` is not in the client's vocabulary.** The host's clock moves time. Tests and experiments step the host
  directly, through the same `tick()`.
- **Compression stays off in v0**, with the fields reserved. A roadmap item tries zstd at several levels once real
  scenes exist, measuring snapshot size, encode and decode time, and client upload time per profile.
- **Snapshot volume.** A full snapshot each time cells change, capped at `snapshot_hz` (proposed 2 Hz), is about
  6.4 MB/s per client at the rig profile on a full tile, and 52 MB/s at max. That's fine on localhost and not
  sustainable beyond it. Sending only changed regions comes with step 3, where B5 measures it.

## 6. What 2a and 2b ship

**2a, `phase1/protocol`:**
- the pure protocol codec;
- sessions with the token, Origin and loopback checks;
- `TimeAuthority` and `HostOnly`;
- `WorldHost` with `tick()`, the intent queue and its ordering, and a stepped (headless) pacer and a wall pacer at
  a constant scale;
- the intent log, with a replay test;
- `max_substep_s` replacing `min_substeps_per_turn`, with its cross-tier test;
- golden wire fixtures (B3) and the B14 refusals;
- one end-to-end test over a real localhost WebSocket.

**2b, `phase1/lanes`:**
- lane channels and threads;
- the thinking lane interface, its deadline semantics and a deterministic stub (no LLM in tests);
- the dial under load, with dilation reporting;
- per-lane meters;
- per-session snapshot cadence;
- the B5 rows for the simulation, network and thinking lanes.

Both PRs run the standard review round plus the lenses this design triggers (`docs/code_review.md`).

## 7. Risks and downsides

- **Holding the world for a late thought can stall it**, and the effective scale can drop well below the dial.
  The meters make that visible, and the deadline values are tunable data.
- **Moving physics to a period changes when heat is applied** relative to intents: up to `physics_period_s` of
  latency between an `ignite` and its first heat. The cross-tier and period-split tests have to show that the
  outcome class holds.
- **The max profile can't keep real time on a full tile** until Phase 2's "Scale" item lands.
- **Maxim changes are needed before NPC substrates run in the simulation lane** (items 10 to 13). Until then, lanes
  and protocol are built and tested with stubs. The risk is building the lanes around the wrong shape before Maxim's
  side is designed.
- **Thread lanes under the GIL** give no CPU parallelism for pure-Python work. Moving a lane to a process is designed
  for, but not built.
- **Determinism is narrower with live models:** replays are bit-identical, fresh runs only match in outcome class.

## 8. Open questions for the review and the owner

1. Hold the world for a late thought (deterministic in world time, can stall) or apply it on arrival (never stalls,
   timing depends on load)?
2. Proposed values: `tick_s` = 0.1 s, `physics_period_s` = 0.5 s, `snapshot_hz` = 2. Are any of them wrong for the
   physics, the substrate or the feel?
3. At 1× and 24-hour days, a play session sees little of a day. Should the default dial be above 1×, so a world
   day takes, say, an hour, or should the world run at 1× with fast-forward only as the player's choice?
4. Does stepping the substrate at the world tick (10 Hz) keep the reflex loop's real job, against Maxim's 30 Hz?
5. How does the SCN get a day that isn't 24 hours: a day-length-aware `TemporalSignature`, or a world clock that
   reports phase?
