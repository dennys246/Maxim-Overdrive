# Design review: Concurrency and lanes, and Performance

Design: `docs/design/realtime_lanes_coop.md` at 52e64f0. Reader lenses: Concurrency and lanes, Performance.

Measurements: Apple M2, the repo's `.venv` (numpy), best of 1 to 3 runs, taken 2026-11-15. "Tile" is a
16×10×4 m scene I built for this review: a concrete wall, a concrete floor, a 0.8 m wood crate and one 60 kW fire
of radius 0.3 m. Shapes are (80,50,20), (160,100,40) and (320,200,80): 80 k, 640 k and 5.12 M cells. Single runs
at max are noisy by about ±30% (substep at max measured 97, 98, 131 and 183 ms in separate runs).

| Per call, tile | laptop 0.2 m | rig 0.1 m | max 0.05 m |
|---|---|---|---|
| `heat.substep` | 1.5 ms | 12 ms | 97–183 ms |
| `heat.stable_dt` | 1.4 ms | 11 ms | 90 ms |
| `World._power_field` (one source) | 8.2 ms | 62 ms | 453 ms |
| `damage.thermal_degrade` (nothing hot) | 0.15 ms | 1.2 ms | 10 ms |
| `world.snapshot` (quantize) | 0.4 ms | 3.5 ms | 28 ms |
| joining the arrays into one `bytes` | 0.01 ms | 0.17 ms | 4.5 ms |
| snapshot bytes | 0.40 MB | 3.2 MB | 25.6 MB |
| `stable_dt` value | 210 s | 53 s | 13 s |

Peak traced allocation at max: 412 MB for one `substep` (temporaries) and 154 MB for one `snapshot`.

---

## BLOCKER 1. The cost model leaves out per-advance O(cells) work and the rounding up of substeps; the real fast-forward headroom is about a quarter of the table's

**Location:** design §1 "The rig profile's `min_substeps_per_turn` becomes `max_substep_s`" and "What it costs";
`world/world.py::World.advance`, `World._power_field`, `world/heat.py::step`, `heat.stable_dt`.

**Scenario.** The design says per-world-second cost "doesn't depend on `tick_s` or `physics_period_s`". Two
things in the code break that.

1. **Per-advance overhead.** `heat.step` calls `stable_dt(grid)` and `power()` (= `World._power_field`) once per
   call, and both are O(cells). `_power_field` runs `sphere_overlap` over the **whole grid** 4³ = 64 times per
   source. Today they run once per 6 s. With `physics_period_s` = 0.5 they run 12 times per 6 s. At the rig tile
   that's 12 × (11 + 62) = 876 ms per 6 s of world time, against 16 × 12.5 = 200 ms for all the substeps. The
   overhead now costs more than the physics. It also scales with the number of fires: five fires at max cost
   about 2.3 s per advance just for `_power_field`.
2. **Rounding up substeps.** The design's values `max_substep_s` = 1.5 / 0.375 / 0.094 s don't divide 0.5 s.
   `ceil(0.5 / max_substep_s)` gives 1 / 2 / 6 substeps per period, so 12 / 24 / 72 per 6 s instead of today's
   4 / 16 / 64: 3×, 1.5× and 1.125× the work. That also means it isn't "the same precision as today" (dt is
   finer). Precision getting finer is harmless, but the claim is wrong and the cross-tier test would compare
   different substep counts.

Measured on the tile, wall time per 6 s of world time, and the fastest dial it can sustain:

| | laptop | rig | max |
|---|---|---|---|
| today, one `advance(6.0)` | ~10 ms, ~600× | 282 ms, ~21× | ~7.6 s, ~0.8× |
| design as written (12 × `advance(0.5)`) | ~135 ms, **~44×** | ~1.2 s, **~5×** | ~14 s, **~0.4×** |
| with the fix below | ~20 ms, ~300× | ~300 ms, ~20× | ~7.9 s, ~0.75× |

The design's table ("about 190× / 18× / 0.8×") scales the crate figures linearly by 36. The substep cost actually
grew 40–70× from crate to tile at max, because of cache effects. The table matches today's code by coincidence,
not the design.

During a burn, any substep that destroys a cell recomputes `stable_dt` and `_power_field` (`heat.step`'s
`changed` branch). A fire that's actively eating a crate at max therefore costs up to 72 × (90 + 453 + 110) ms
≈ 47 s per 6 s, about 0.13×. That's the existing behaviour, but in real time it's what the player feels.

**Fix (root, before 2a ships the period change).**
- Compute `sphere_overlap` only over the sphere's bounding box of cells. The cost becomes O(cells in the sphere),
  which is under 1 ms. That's the root cause of the 453 ms.
- Cache the power field and the stability bound on `World`, behind a version that sources and `destroy` bump.
  Recompute only when the version changes, not on every `advance`.
- Make the rig field an integer `substeps_per_physics_period`, or require `physics_period_s / max_substep_s` to be
  an integer and validate that at load. The substep count then is what the profile says.
- Re-measure on a committed reference tile (not by scaling) and replace the table. The design says B5 sets the
  budgets "in step 3", but these numbers decide the step 2 shape and open question 3, so measure now.

## BLOCKER 2. NPC agent state would be mutated by two lanes; "one owner" covers `World` but not the agents

**Location:** design §2 "One owner of the world", "The thinking lane and determinism", "Substrate and the hybrid
runtime"; Maxim `src/maxim/runtime/agent_pool.py::AgentPool.run_turn`.

**Scenario.** Deliberation runs in the thinking lane. Today's `run_turn` (the only NPC turn API) **mutates the
agent while it deliberates**: `hippocampus.store_observation(...)` before the LLM call and `nac.observe(...)`
after it. It also reads `time.time()`. In Phase 4 the simulation lane steps the same agent's substrate every tick
(`NAc.recommend_action`). So an NPC's NAc and hippocampus would be written by a thinking-lane thread at a
wall-clock moment and read by the simulation lane at a tick. That's a data race (the swallowed-exception comment in
`run_turn` already cites a hippocampus race, #1135), and it breaks determinism: whether tick T's substrate saw the
observation depends on thread timing, and the intent log doesn't record it. A replay that reads only the thought's
*result* from the log would also never perform those memory writes, so replayed NPCs would diverge. `AgentPool`
also brings its own `ThreadPoolExecutor` (`run_round`), which is a second, unmanaged pool inside the lane.

**Fix.** Write the agent ownership rule into the design now, because 2b fixes the thinking-lane interface shape.
- The simulation lane owns every NPC's mutable state (substrate, memory, NAc), just as it owns `World`.
- A thought request carries a frozen context: the percept text and the memory excerpts it needs.
- A thought result is a pure value: the reply text plus the state effects to apply.
- The simulation lane applies the effects at the deadline tick, and they go into the log with the result.
- The thinking lane never calls back into the simulation lane or into a live agent. That also rules out the
  deadlock where a deliberating agent asks for a percept while the simulation lane holds for it.

This needs a Maxim API that splits "generate" from "apply". `run_turn` does both today, so it goes under Phase 3
(item 12 or 13, or a new item). The 2b stub must have the pure shape, so the lane isn't built around `run_turn`.

## BLOCKER 3. "Holds at that tick until it does" is a blocking wait that also blocks pause, shutdown and disconnects

**Location:** design §2 "The thinking lane and determinism"; §6 2b "deadline semantics".

**Scenario.** Implemented literally, the simulation lane blocks on the result channel (say with
`results.get(timeout=30)`). During that wait it doesn't drain its inbox:
- a host `pause` or `set_scale` waits up to 30 s;
- shutdown (Ctrl-C, the window closing, a test teardown) waits out the timeout and then logs a spurious
  `thought_failed`;
- a disconnecting session's removal isn't processed;
- intents pile up, all stamped with the held tick.

At 30× fast-forward with many NPCs, holds can follow each other back to back, so the host is unresponsive most of
the time. The design also doesn't say whether the wall timeout keeps running while paused. If it does, pausing
during a hold fails the thought just because the player paused, and the timeout's outcome then depends on the dial.

**Fix.** Make a hold a state of the simulation lane, not a blocking call.
- The lane waits on one multiplexed inbox (intents, time requests, session events, thought results, stop) with a
  timeout equal to whichever comes first, the next tick or the hold timeout.
- It keeps serving control while held: pause and resume apply, and intents are accepted and stamped for the held
  tick.
- The hold timeout counts wall time only while the dial is above zero.
- Stop ends a hold at once. A thought cut off by shutdown is logged as `cancelled_by_shutdown`, not
  `thought_failed`, or isn't logged at all if the log ends there.
- Tests (deterministic, with a stub thinking lane that never answers): pause during a hold is honoured within one
  inbox wait; stop during a hold joins every thread within a bound.

## SHOULD-FIX 4. The thinking queue: priority order inverts against deadlines, the backlog has no bound, and timed-out calls keep their workers

**Location:** design §2 "Thinking: ... The queue has priorities, so an NPC the player is talking to thinks first";
"At the timeout the thought resolves as `thought_failed`".

**Scenarios.**
- **Priority inversion.** A low-priority "plan for the day" with a deadline at T+50 sits behind a stream of
  high-priority dialogue requests with later deadlines. It starves, its deadline arrives, and the *whole world*
  holds for it. That's the reverse of what the priority meant to achieve.
- **Unbounded backlog.** At 30× an NPC that requests a thought every few world seconds creates 30 times as many
  requests per wall second. Only the hold caps the outstanding count, so it's bounded only by requests-per-tick ×
  d / `tick_s`, which is thousands of ticks for a long d.
- **Zombie workers.** The LLM call can't be cancelled (Maxim item 13 doesn't exist yet). After a thought times
  out, its call keeps a pool worker busy until the HTTP client gives up. If the HTTP timeout is longer than the
  hold timeout, N slow calls fill an N-worker pool, and every later request times out too: one slow model
  response turns into failed thoughts for everyone.

**Fix.**
- Dispatch earliest deadline first. Express priority by giving a request type a shorter d, not by reordering the
  queue.
- At most one outstanding deliberation per NPC (a new request supersedes the old one or is refused, and the
  choice is logged). The backlog is then bounded by the NPC count.
- Make the transport timeout of a model call shorter than the hold timeout, as a validated config invariant.
- Give every request an id, and discard (and meter) a result for an id that already resolved.
- Meter "workers busy on resolved requests".

## SHOULD-FIX 5. The design states no backpressure policy for any channel

**Location:** design §2, the lane diagram and "Each lane is metered separately"; §4 "Each session gets its own
snapshot".

**Scenarios.**
- **Intent spam.** A client sends 100 k `act` messages. They're decoded and queued faster than one tick drains
  them, and step 1 ("take the intents for this tick") drains them all in one tick. An `act` → `strike` is O(cells)
  (`damage.strike` builds full-grid fields), so one tick at max can last minutes.
- **Slow reader.** A client stops reading snapshots. If snapshots are queued per session at 2 Hz × 25.6 MB, the
  server's memory grows by 51 MB per second per stalled client.
- **Fast-forward.** `tick` messages at 30× would be 300 per second per session if "throttled" isn't defined in
  wall time.

**Fix.** Put a policy table in the design, one row per channel.
- Inbound intents: a bounded queue per session. When it's full, reply `error` with code `busy` and change
  nothing. Cap the intents drained per session per tick, with the rest staying queued for later ticks in order.
  This is deterministic because the stamped tick is logged.
- Outbound snapshots and `tick` status: a **latest-wins slot** per session (capacity 1, overwritten), never a
  queue. Throttle in wall time (at most `snapshot_hz` and 10 Hz wall, whatever the dial).
- Thinking: bounded by finding 4.
- Record: never drops (finding 6).

Each bound and each overflow count is a meter.

## SHOULD-FIX 6. Lifecycle and crash policy are unspecified, and the record lane can't be best-effort

**Location:** design §2 "record lane: intent log, metrics, autosave (later)"; §6 2b "lane channels and threads".

**Scenarios.**
- **Lost log tail.** The record lane is a separate thread with a queue. If the process crashes (the simulation
  lane raises inside `World.advance`, say), the queued tail of the log is lost. The intent log is "the bug report",
  and the intents that caused the crash are exactly the ones missing.
- **Silent unrecorded run.** If the record lane itself dies, the simulation keeps running unrecorded and nobody
  notices.
- **Dead world, live clients.** A simulation lane exception in a plain thread just ends the thread. Network lanes
  keep sessions open, and clients see a frozen world with no `error`.

**Fix.**
- Write the log synchronously from the simulation lane: append and flush each tick's records before the tick's
  effects are published. The bytes are small. A record lane, if any, then only handles metrics and autosave.
- Define a per-lane crash policy:
  - the simulation or record lane: fail-stop the host, send every session an `error` with a server-fault code,
    then close;
  - a network lane: end that session only;
  - a thinking worker: its request resolves as `thought_failed`.
- Make `WorldHost` a context manager. Start lanes as record (if any), then simulation, thinking, network, and stop
  them in reverse with sentinels and bounded joins.
- Guard it with a test that injects an exception into each lane in turn and asserts that every thread the host
  started has been joined (`threading.enumerate()` back to the baseline) and the client got the `error`.

## SHOULD-FIX 7. Network lane shape: asyncio and thread handoff, `websockets` defaults, Godot's receive buffer

**Location:** design §2 "network lanes, one per client"; §5 "Compression stays off in v0"; `docs/architecture.md`
"Transport".

**Scenarios and facts.**
- Python `websockets` is asyncio. "One lane per client" should be **one event-loop thread with one task per
  session**, not a thread per client. The handoffs:
  - loop to simulation lane: `queue.Queue.put_nowait`, which is thread-safe and never blocks the loop;
  - simulation lane to loop: `loop.call_soon_threadsafe` to fill a session's latest-wins slot and set its
    `asyncio.Event`;
  - never call `asyncio.Queue` methods from the simulation thread (not thread-safe), and never make a blocking
    `put` on the loop (it would stall every session).
- `websockets` enables permessage-deflate **by default** on the server. A Python test client negotiates it, so the
  "end-to-end test over a real localhost WebSocket" would deflate 25.6 MB snapshots in Python on the loop thread
  and measure a different path from the Godot client, which (to verify) doesn't negotiate it. Pass
  `compression=None` explicitly, and test that the negotiated extensions are empty.
- `websockets` caps an inbound message at 1 MiB (`max_size`) by default. Set it deliberately small for intents
  (say 64 KiB) as part of B14.
- `websockets` isn't in the venv yet, so pin it when 2a adds it.
- Godot 4 `WebSocketPeer.inbound_buffer_size` defaults to 64 KiB (to verify against 4.7.2). A 3.2 MB or 25.6 MB
  snapshot won't be received unless the client sets it above the largest snapshot of its profile. Golden fixtures
  should include one near the max size.

## SHOULD-FIX 8. Snapshot publishing: quantizing is already the copy, so encode once and share the bytes; "when cells changed" saves nothing during a fire

**Location:** design §2 step 5 "a snapshot when cells changed", "published snapshot (immutable)"; §4 "Each session
gets its own snapshot"; `world/world.py::snapshot`.

**Facts.**
- `snapshot()` already builds fresh arrays. Quantizing *is* the copy: 28 ms, 25.6 MB out and 154 MB of transient
  allocation at max.
- Publishing an immutable snapshot therefore costs no extra copy, if:
  - the arrays are frozen (`flags.writeable = False`);
  - the wire message is built **once per published tick** (4.5 ms at max) as one `bytes`;
  - all sessions share that object.
- Built per session instead, it's N × 33 ms on the simulation lane and N × 25.6 MB resident at max.
- "When cells changed" can't be detected cheaply by comparing arrays (O(cells) again). Use a world version
  counter. In practice temperature changes on every physics step whenever anything is warm, so 2 Hz is the steady
  state during play, not the exception.
- The 52 MB/s per client at max is mostly a memory-bandwidth and GPU-upload question on localhost. Check it in the
  client lens (texture upload of 4 × 5.12 M voxels twice a second).

**Fix.** State "one encode per published tick, shared across sessions; per-session cadence picks which published
snapshot to send" in the design. Add a version counter. Bound resident snapshots at (sessions in flight + 1)
× size.

## SHOULD-FIX 9. Physics ticks are lumpy: every fifth tick carries the whole step, and control waits behind it

**Location:** design §1 "Physics runs at its own period"; §2 the tick loop.

**Scenario.** With `tick_s` = 0.1 and `physics_period_s` = 0.5, ticks 1–4 cost about nothing, and tick 5 runs
`World.advance(0.5)`:
- rig: about 100 ms as designed, about 25 ms with the BLOCKER 1 fix;
- max: about 1.2 s, about 0.66 s fixed.

At rig and 1×, that one tick uses the whole 100 ms wall budget of a tick. A `pause` or an `act` that arrives during
it waits the full step, and the `tick` status stutters at 2 Hz. At max, "pause" lags by about a second.

**Fix.** No change to the physics. Meter **p99 tick wall time** and **control latency** (from a `time` request's
arrival to its decision being applied), not just mean tick time. Report dilation over a wall window, not per tick.
If control latency matters at max, the later fix is to split a physics step across ticks, which is a real design
change and should be noted as one.

## SHOULD-FIX 10. Fast-forward has a hard ceiling per profile, and open question 3's "a day in an hour" is out of reach on a tile

**Location:** design §8 question 3; §1 "the dial reports dilation"; §2 step 3 (substrate per tick).

**Numbers.** An hour-long day is 24×, which needs 24 world seconds per wall second:
- rig tile: physics alone costs 4.8 s per wall second as designed (5× sustainable), about 1.2 s with the fix
  (20×), so it dilates even fixed;
- max: below 1×.

At 24× ticks also run at 240 Hz. Per-tick work then dominates: Phase 4 substrate stepping at, say, 1 ms per NPC
for 20 NPCs is 20 ms per tick × 240 = 4.8 s per wall second.

**Fix.** Answer question 3 with numbers:
- the sustainable dial is min(physics headroom, `tick_s` / per-tick cost);
- a default dial above about 10× is laptop-only on a full tile today;
- make "max sustainable dial on the reference tile, per profile" a B5 row;
- budget per-NPC substrate cost per tick before Phase 4 picks the 10 Hz tick.

## SHOULD-FIX 11. GIL: other lanes' Python work slows the simulation lane

**Location:** design §2 "lanes are threads"; §7 "Thread lanes under the GIL".

**Measured.** numpy releases the GIL in its large-array loops, so a pure-Python thread kept about 90% of its rate
while a max-tile `substep` ran. The good news: network and thinking threads stay responsive during physics. The
cost: the same `substep` took 386 ms instead of about 100–180 ms (one run, noisy) while that thread spun. Every
Python-level piece of `substep` (index tuples, temporaries, about 20 numpy calls) waits for the GIL, and a busy
neighbour switches it away every 5 ms.

So a CPU-busy network lane (deflate, JSON-encoding arrays) or thinking lane (a Python-side embedding or the
hippocampus's own work) can roughly halve physics throughput.

**Fix.** Keep the network lane free of per-byte Python work: no compression, and arrays as raw buffers. Meter the
simulation lane's CPU time against its wall time (`time.thread_time` vs `perf_counter`) so contention shows as its
own number. Name in-process model inference as a reason to move the thinking lane to a process.

## SHOULD-FIX 12. The proposed meters and B5 rows aren't yet enough to set or hold the budgets

**Location:** design §2 "Each lane is metered separately"; `docs/standards_backlog.md` B5.

**Gaps.**
- B5 says "turn time". There's no turn any more. It needs:
  - physics-step time split into `stable_dt`, `_power_field` and substeps (BLOCKER 1 hid in that aggregate);
  - p99 tick time and control latency (finding 9);
  - the max sustainable dial (finding 10);
  - peak RSS per profile (412 + 154 MB transients at max);
  - simulation lane CPU vs wall (finding 11);
  - snapshot encode once per published tick and bytes per published tick;
  - per-session send latency and slot overwrites (dropped snapshots);
  - queue depths and overflow counts (finding 5).
- "Tokens per NPC" depends on what Maxim exposes. `TurnResult` carries `duration_ms` and no token counts in
  `run_turn`, so verify that, or list it as a Phase 3 item.
- A 20% regression gate on wall time is noisy on a laptop (±30% here at max). Use best-of-N on a fixed tile, or
  count operations (substeps, O(cells) passes per step) as a deterministic proxy that can't flake.
- Meters read the wall clock, so they must live outside the determinism-scanned simulation code and never feed
  `World` (B14 already says so for durations). Say that meters are write-only from the simulation's side.

## NIT 13. "A lane can move from a thread to a process without its code changing" overclaims

`queue.Queue` and `multiprocessing` queues differ in semantics: pickling, no shared ndarrays, and a feeder thread
that can deadlock on join if the queue isn't drained. A 25.6 MB snapshot crossing a process boundary costs a pickle
and copy (tens of ms) unless it goes through `shared_memory`. Say "the message types don't change", and require
message types to be picklable frozen dataclasses of plain values and read-only arrays.

## NIT 14. JSON `tick` messages are negligible; define the throttle in wall time

About 150 bytes × 10 Hz is about 1.5 KB/s per session, with an encode of microseconds. The only issue is the
throttle's definition at fast-forward (finding 5).

## NIT 15. Client disconnect mid-message

`websockets` delivers whole messages only, so a disconnect can't produce a half intent. Specify two things:
intents already stamped from a closed session still apply in order (they're in the log), and session removal is a
message through the simulation inbox, so it orders deterministically against intents.

---

## Checked and found sound

- **Single owner of `World`, frozen messages, and ordering by (tick, actor, seq) with the host stamping the tick on
  dequeue.** This is sound for determinism and replay of `World` (agent state is BLOCKER 2). No `hash()` or dict
  order is involved.
- **The dial changes only how often ticks run, and `tick()` takes no duration,** so the wall clock can't reach
  `World` through the pacer. Headless and paced modes share one path. Sound.
- **The observation that runs take exactly the minimum substeps is true:** `stable_dt` is 13–240 s on the tile,
  far above any substep. Calling `advance(0.5)` with today's `min_substeps_per_turn` costs 64 substeps per 0.5 s
  (measured 7.9 s per call at max), which confirms the design's reason for `max_substep_s`.
- **Snapshot sizes and rates check out:** 5 bytes per cell (u8 material, crack and glow, plus f16 temperature),
  3.2 MB and 25.6 MB per tile at rig and max, so 6.4 and 51 MB/s at 2 Hz.
- **Replays read thoughts from the log and never call a model.** Sound, given BLOCKER 2's effects are logged too.
- **Thinking-lane LLM calls are I/O-bound HTTP,** so threads suit them under the GIL, unless inference runs in
  process (finding 11).
- **Moving time to the host and removing `advance` from the client's vocabulary** closes the "client-supplied
  duration" path that B14 targets.
