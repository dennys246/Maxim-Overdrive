# Design review: `sem_stimuli.md` v1, Concurrency and lanes

**Reader:** Concurrency and lanes. **Read at:** Overdrive `3357439`: the design, `5_contract.md` whole and L3, L4, L7 in part, the charter, `CLAUDE.md`, `realtime_lanes_coop.md` §2, §4, `world_v2.md` §6, `boundaries.md` §4, §6.2, §7.1, `npcs_and_sem.md` §2.1, §4.4–4.5, §6.3, §6.6, §7, §9, `tile_and_client.md` §2.3, and `src/simcore/` (no lane, thread or channel code exists yet). Maxim by `git show` at the local `origin/main` ref `043eab8f`, **not fetched** (same ref as the author). Two numbers measured here (**D**): JSON cost of a v1 `BodyFrame` (Python 3.14.6 stdlib `json`, this Mac) and macOS's Unix-socket buffer (`sysctl`).

**Counts:** 2 BLOCKER, 9 SHOULD-FIX, 5 NIT.

## What holds (checked, no finding)

- **Only the simulation lane computes or mutates stimulus state:** tissue, dose, occlusion and events are core state; models are read-only by contract and the writer scan (§7.3, §7.4). Holes: S4, S8.
- **The thinking lane never touches stimuli;** requests are `Pending` values (`boundaries.md` §7.1).
- **The push runs on the agent's owner thread** (`npcs_and_sem.md` §6.3, §7.2); `False` ends the agent as `agent_failed(protocol)` (§4.3), the right exit.
- **Only agents due this tick get a frame** (§4.4); tissue integrates every tick for every body (§2.4).

## BLOCKER

### B1. The tick order contradicts the standing one, and the frozen `tick` has no single meaning
**`sem_stimuli.md::§4.1` (step 1), `§4.4`; against `realtime_lanes_coop.md::§2.1` (D10), kept by `world_v2.md` §6 ("a fixed order within a tick"), and `tile_and_client.md::§2.3`.**

The standing tick order is: records, move bodies, **agents**, **physics**, outputs. The design builds each frame "after every law at tick T" (§4.1; L7 line 192 says "after every law and before the frame publishes"). The barrier then holds T+1 until every agent parks (§4.4). That puts the agent step after physics at T, so one of the two is wrong, and the frozen `BodyFrame.tick` and "the frame computed at that tick" read differently under each:
- **Standing order:** an agent stepping at T gets tissue integrated to T−1 and fields from T−1's physics, at its pose moved at T.
- **This design's order:** it gets tissue integrated through T and fields from T's physics.

On a physics tick (every fifth) the two differ by 0.5 s of field and tissue, which is exactly what the §2.4 latency numbers measure (12.1% late on pain).

**The lanes consequence.** Under the standing order, physics at T doesn't depend on agent outputs at T: intents apply at `apply_tick ≥ observed_tick + L` (`npcs_and_sem.md` §9). So the simulation lane can run tick T's physics while the workers step on T's frames, and join at the end of the tick. Under this design's order the tick is strictly serial: laws, then stimuli, then encode, then the slowest worker, then decode. Workers sit idle during physics and the simulation lane sits idle during the barrier. At 100 NPCs, §8's per-physics-step stimulus cost (~46 + ~38 ms) adds directly to the barrier's 0.2–0.8 s/s (§6.6).

**Fold:** state the order (I recommend the standing one: frame at the start of tick T, after "move bodies"). Say whether physics overlaps the barrier, and test it: the same log with overlap on and off gives the same world digest and stimulus digest.

### B2. The frozen `BodyFrame` has no bound on `events`, so a burst ends an NPC and a failed NPC's queue grows forever
**`sem_stimuli.md::§4.1` (`events: … since this NPC's last step`), `§0` ("Frozen … the `BodyFrame` and its wire form"), `§5` (save: "pending sound events"); against `npcs_and_sem.md::§6.6` (codec "size budgets checked before allocation"; "a refused frame is killed").**

1. **Burst.** Event rows (sound, impacts) are stamped per event in integer µs (§2.3). The frozen form carries every event since the last step and sets no cap. An agent on rate divisor 10 in a firefight (gunshots, ricochets, a collapsing wall, 10 neighbours speaking) collects events for 10 ticks. Its frame can cross the codec's per-message size budget. The worker's strict decoder must then refuse it, and §6.6's rule kills the worker as `agent_failed(protocol)`. So the busiest moment in the scene kills an NPC. The cause is the world, not the agent, and the run is flagged tier 3.
2. **Unbounded growth.** After `agent_failed`, the NPC is "parked and inert (its body processes go on)" (§6.6), and it never steps again until an explicit restart. "Since this NPC's last step" then never resets, so the simulation lane's per-NPC event buffer (which is saved, §5) grows for the rest of the session. The same happens for any NPC that is not due for a long time: a coarse idle divisor (§6.6's third lever) or the dormancy this design defers (§8).
3. L3 §6 lists "cap and staleness counters" among digest state. The design adopted the digest list and dropped the cap.

**Fold, in the frozen form now:**
- A per-NPC, per-step event cap and a byte budget derived from the body (rows bound × sites + cap × event size).
- A deterministic overflow rule that is the same for everyone and keyed on nothing wall-time: coalesce by (stimulus, site) into a count and the peak, or keep the first K in `(apply_us, id)` order with a counted overflow.
- The host checks the budget **before sending**, so an oversize frame is a logged, replayable host decision and never a worker refusal.
- Events stop accumulating for an NPC that is inert, has left or is not stepping (S7).
- Test: a burst scene at divisor 10 delivers a capped frame and keeps the agent alive; a failed NPC's buffer stays at zero for 10,000 ticks.

## SHOULD-FIX

### S1. The wire cost is unbudgeted, and the full per-site table crosses where a flat body reads a handful of values
**`sem_stimuli.md::§4.1`, `§8` (cost covers kernels only); `5_contract.md::§1` ("a few hundred bytes").**

Measured here (**D**): one v1 frame at 58 skin points (tissue at d depths, plus `exposed_area_fraction` per point and `burned_area_fraction` per region) as closed-schema JSON:

| depths | rows | bytes | encode | decode (plain `json.loads`) |
|---|---|---|---|---|
| 1 | 134 | 3.3 KB | 55 µs | 37 µs |
| 3 | 250 | 6.1 KB | 103 µs | 71 µs |

The strict decoder's closed-schema and finiteness checks, plus the worker's second finiteness pass, add to the decode time. That makes L5's "a few hundred bytes" wrong by 10–20×.

At 20 NPCs stepping every tick at a 20× dial (4,000 frames per wall second), host-side encoding alone is about 0.2–0.4 s per wall second on whichever thread encodes, on top of §6.6's 0.2–0.8 s barrier. And the receiver discards most of it: Phase 4's flat body has a few root sensors, and the binding reduces 58 points to each one in the worker (§3).

**Fold:**
- Give the encode, digest, bytes per tick and worker decode-and-push each a B5 row.
- Decide where the binding's reduction runs. Running it host-side, from the bindings in the build handshake, sends only bound values: a few dozen bytes. The reduction stays a named ANALOG either way. The digest can still cover the full per-site table, which is what replay needs.
- Correct the size claim.

### S2. A blocking send to an untrusted worker can freeze the world, and a crash mid-send has no named exit
**`sem_stimuli.md::§4.1` (step 2), `§4.3`; against `npcs_and_sem.md::§6.6` ("A hung or dead worker never freezes the world"; "Everything from the worker is untrusted") and `realtime_lanes_coop.md::§4.1` (an exception in the simulation lane stops every lane).**

macOS gives a Unix stream socket 8,192 bytes of send space and 8,192 of receive space (`sysctl net.local.stream.*`, **D**). A 3-depth v1 frame is 6.1 KB before events, so with B2's events, or a `settle` queued ahead of it, one message exceeds the buffer.

**Scenario:** a worker parks, then stops reading, through a bug or deliberately (§6.6 treats it as untrusted). The host's `sendall` of the next frame blocks once both buffers fill. If the per-park wall ceiling is armed after the send, as in a usual send-then-`select` loop, nothing ever fires and the world freezes.

**The converse:** a worker that has died makes `sendall` raise `BrokenPipeError`. If delivery runs on the simulation lane, the lanes rule ("an exception in the simulation lane is a bug … stops every lane") turns one dead NPC into a dead server.

**Fold:**
- Sends are non-blocking, multiplexed with receives, and counted inside the same per-park ceiling.
- `BrokenPipeError`, `ConnectionResetError` and a short write map to `agent_failed(crashed)`, caught narrowly.
- Tests: a planted worker that parks and never reads, with a 64 KB frame, still lets the world advance after the ceiling; a worker killed between park and send gives `agent_failed(crashed)` and the server keeps running.

### S3. "Nothing else in the worker writes" is the only guard, and nothing holds it
**`sem_stimuli.md::§4.2` (third bullet).**

`world_set_axis` writes `vm[sensor_name] = v` with no lock, and `owner=` is "not an ACL" (`audio_localization.py:692-765`, read here). Maxim itself documents writers on other threads:
- `Embodiment.OutcomeWindow`: "the window keeps another thread's EVALUATIONS out, not its WRITES. A narrator write … lands on the body", and `_last_poll` is shared (`embodiment/body.py:95-110`).
- The live DoA feed is a poll thread that calls `world_set_azimuth(…, owner="doa_feed")` (`audio_localization.py:310-345`, `:455`).

If Maxim's embodied bootstrap starts either one inside a worker, a second writer races the push on the same `vital_metrics` dict, and the last write between push and read wins. That is a wall-clock-dependent percept, the "two truths" this design rejects for pulls (§4.1).

**Fold:** add a build-time check in the worker, after Maxim is built and before the first `step`: `threading.enumerate()` holds only the step thread, and each bound sensor's live owners are Overdrive's alone. Test it with a planted second writer, shown red. If Maxim needs a background thread, ask Maxim, as the push-path's Phase 3 item.

### S4. "Parallel evaluation" has no lane rule
**`sem_stimuli.md::§8` (allowed, item 5); against `boundaries.md::§4.1` ("the window is a single-thread guarantee") and `§4.2` ("Nothing outside the simulation lane holds a reference to `World`, the grid or `MaterialTable`").**

Evaluating stimuli in parallel means some other thread or process reads the held fields, the site frame and the tissue store. As written, that breaks §4.2's rule. A pool thread that keeps a reference past the join reads arrays the next window replaces, and the window guard can't see it, because the guard holds on the simulation thread only. A pool task that raises has no named exit.

**Fold:** define parallel evaluation as a fork-join inside `Simulation.step` that reads only published read-only arrays and is joined before any window opens. No task outlives the step. An exception in a pool task is a simulation-lane exception (fail loudly). Processes are out of scope (frames are tens of MB). Add a B5 row for CPU against wall time, since the GIL decides whether this pays.

### S5. `BodyFrame` is frozen only one level deep
**`sem_stimuli.md::§4.1` (`stimulus_id`, `site_id`, `value` as `NDArray`), `§7.1` (models "return `(npc, site)` arrays"); against `boundaries.md::§5.1` ("frozen means deep") and the `CellFrame.__post_init__` pattern in `src/simcore/core/frames.py`.**

`@dataclass(frozen=True)` stops reassignment, not `frame.value[3] = 1e9`. `world_v2.md` §9 schedules "preallocated temporaries" for `phase1/sim-clock`. A model that returns a view into a reused temporary yields a `BodyFrame` whose values change under the next tick's kernels. If encoding or digesting happens off the simulation thread, or after the next tick starts, the digest and the bytes sent disagree with what replay recomputes.

**Fold:** in `__post_init__`, refuse any writable or non-owning array (`readonly.frozen`, `base is None` after the copy), as `CellFrame` does. Test: a model returning a view of a scratch buffer is refused.

### S6. The wake-up decision (D5) ignores lane costs, and misses the option the corpus already has
**`sem_stimuli.md::§10 D5`; `npcs_and_sem.md::§2.1` (scheduled crossings; `dt_ticks` "a pure function of the actor's rate divisor and phase"), `§6.6` (barrier cost and levers).**
- **(a) No waking.** Safe for the lanes only with B2's cap. The lead time lost grows with the divisor.
- **(b) A world-side onset forces a step.** This makes `dt_ticks` depend on world state, so §2.1's rule needs amending: the schedule restarts at the forced tick, or it doesn't. It also concentrates round trips: one fire onset crossing 30 NPCs' floors in one tick forces 30 extra round trips in that tick, the scene's busiest, and a sustained fire degenerates into (c).
- **(c) Every body steps each tick.** This deletes §6.6's first lever ("only agents due this tick"). At 20 NPCs and 20× it is the full 0.2–0.8 s/s barrier, plus S1's ~0.4 s/s encoding. §6.6 says that makes 20× unreachable. Recommending (c) "as the target" needs those numbers beside it.
- **Missing (d): an agent-declared wake predicate.** At each step, the agent returns in `StepOutput` a threshold on its own bound rows, a receptor property and so Maxim's (T2). An example: "wake if `tissue_temperature` at any bound site exceeds 43 °C, or rises by more than X per tick". The simulation lane evaluates it each tick against the frame it already builds, at one comparison per bound row. This is §2.1's "threshold crossings are scheduled" carried across the process boundary. It is not a designer event, because the threshold is the receptor's. It costs a round trip only when it fires. It is replay-safe only if the predicate is a logged record, since replay doesn't run agents and the stimulus digest's set of stepping NPCs depends on it.

**Fold:** add (d) to D5 with its logging rule. Give each option's barrier cost at the §6.6 operating point. Say how a forced step interacts with an outstanding `Pending` (it is parked, so allowed) and with `dt_ticks`.

### S7. Joins, leaves, crashes, restarts and build refusals have no stimulus lifecycle
**`sem_stimuli.md::§4.2`, `§4.3`, `§5`, `§8` (allowed, items 2 and 4).**

Each start needs a stop, and the design gives none:
- **Join:** when tissue state is created and at what initial temperature; whether the first frame's events start at the join tick; what happens if the worker isn't ready (its Maxim import takes wall seconds) when the join applies. Either the barrier waits, which is dilation, or the NPC is inert until ready, and then readiness is a wall-time fact that must be a logged record.
- **Build refusal (§4.2):** "the adapter refuses to build an agent", with no reason code (§6.6 has `hung | crashed | protocol`), no log record and no world-side state. Is the body still in the world, burning?
- **Leave:** tissue, events, the reuse cache and the stagger phase are freed; the NPC leaves the digest set.
- **`agent_failed`:** whether the simulation lane keeps building frames for an inert NPC (wasted, or buffered: B2), or skips it.
- **Restart from the last saved home (§6.6, O45):** the build checks rerun, the name maps are re-sent, and the first frame's events are defined: since the restart tick, or since the failure?
- **Digest membership:** "for each stepping NPC" must be computed from the schedule plus logged records (`agent_failed`, joins and leaves) **before sending**, never from delivery success. Otherwise a worker dying mid-send at tick T drops it from the live digest while replay, which sees `agent_failed` only from its record's tick, keeps it.

**Fold:** add a lifecycle table (event → world-side state → frames → digest → log record), with a crash-injection test per row.

### S8. The `breath` cadence makes worker output a stimulus input, with no lane path named
**`sem_stimuli.md::§1` ("the agent reports its breathing state; the world integrates"), `§2.3` (`breath`: "per inhalation the body reports").**

This is the one place where the stimulus computation reads something produced in a worker. If the report arrives any way other than as a `StepOutput` value applied at a tick boundary and logged, inhaled dose depends on arrival time, and replay (which runs no agent) can't reproduce it. The cadence vocabulary is frozen now.

**Fold:** a breath report is a logged agent record through `StepOutput`, ordered by the one key (`boundaries.md` §6.2) and applied at the next tick. An inert, failed or absent agent breathes on a declared default schedule. Without that, an NPC that has crashed stops inhaling smoke and so stops being poisoned. Test: replay with `maxim` blocked reproduces the dose.

### S9. Lanes aren't each metered against their own budget
**`sem_stimuli.md::§8` ("Stimuli get their own B5 line"), `§2.1` ("meters how often the clamp bites").**

The one B5 line covers kernel work on the simulation lane. Missing:
- **Which thread encodes and digests** (§4.1 says "host"; the digest goes into the per-tick record that the simulation lane writes synchronously, `realtime_lanes_coop.md` §4.1), and its own row.
- **The worker's decode, check and push, inside the per-park wall ceiling.** On a CPU-starved host (20 workers on 8 cores) a slow park is killed as `hung`, a wall-dependent outcome. The stimulus push is new work inside every park and needs its own share of the ceiling.
- **The clamp-bite meter.** The range lives in the body YAML in the worker, so the world can't count clamps unless the worker reports them or the host loads the YAML.
- **Event-buffer depth and overflow counts** (B2).
- **The per-tick critical path** (B1), not only per-physics-step totals, because physics ticks are lumpy (`realtime_lanes_coop.md` §2.3, CP-9).

## NIT

- **N1. `sem_stimuli.md::§8` (allowed, item 4).** "NPC i on steps ≡ i mod N": `i` must be a phase fixed at join (derived from `npc_key`), never an index into the live NPC list. Otherwise one NPC leaving reshuffles every other NPC's occlusion staleness.
- **N2. `§8` (allowed, item 2).** The reuse cache needs a bound (one entry per NPC per row family) and eviction on leave or failure.
- **N3. `npcs_and_sem.md::§6.6` lever "frames go as deltas."** A delta needs worker-side state and breaks on restart, and it changes what "the bytes sent" means for the digest. Rule it out for `BodyFrame` or define keyframes. S1's host-side reduction is the smaller lever.
- **N4. `§4.1`.** The worker should check `BodyFrame.npc_key` against its channel's actor, bound at spawn (§6.6).
- **N5. `§2.4`, `§4.4`.** State the pause behaviour: no ticks, no tissue integration, no frames; the per-park ceiling keeps counting, the thinking-lane timeout stops (`world_v2.md` DD10).
