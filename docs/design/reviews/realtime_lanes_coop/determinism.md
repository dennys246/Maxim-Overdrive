# Determinism and replay lens: realtime_lanes_coop.md (design v0, at 52e64f0)

Reader brief: `docs/code_review.md`, the **Determinism and replay** row. Reviewed: `docs/design/realtime_lanes_coop.md`
against CLAUDE.md ("Game engineering"), `tests/test_determinism.py`, `docs/standards_backlog.md` (B2, B14),
`src/maxim_overdrive/world/{world,heat}.py`, and pymaxim's source at the Maxim repo's `src/maxim`.

Counts: **2 BLOCKER, 7 SHOULD-FIX, 3 NIT.**

---

## D1. BLOCKER: Maxim agent code reads the wall clock and OS entropy well beyond the clocks the design lists

**Location:** design §2 "Substrate and the hybrid runtime", §3 (the three-clock table, Phase 3 items 10 to 13);
`tests/test_determinism.py::scanned_files`.

The design names three Maxim clocks (ExperienceClock, SCN/TemporalSignature, Default Network). pymaxim has
`time.time()` in 178 files, `uuid4` in 27, the stdlib `random` in 15 and builtin `hash(` in 13. Some sit right
on the path an in-game agent runs:

- `maxim/memory/hippocampus.py` (capture): `obs_hash = hash(text...)`, then
  `now = time.time()`, then "deduped if `now - last_seen < dedup_window_s`". Whether an observation goes into memory
  depends on the **wall** time between observations.
- `maxim/memory/hippocampus.py` and `memory/base.py`: memory ids are `str(uuid4())`, and
  `hippocampus_persistence.py` sorts records by `m.id`.
- `maxim/default_network/{arbiter,inhibition,gaze_manager,background_tasks}.py`: `time.time()` for inhibition expiry and
  switching. Item 11 covers this, but only for the Default Network.

**Failure:** take a live session at 1x where an NPC sees "fire in the crate" on ticks 100 and 120 (2 s of world time,
2 s of wall time, outside a 1 s dedup window, so it is stored twice). Its replay runs unpaced, as the design says replays
and tests do, so the same two ticks are microseconds apart in wall time and the second observation is deduped. The NPC's
memory now differs, so the next deliberation request is built from different state. The logged result is then applied
to a different agent. The replay isn't bit-identical, and a bug that appears in the live run won't reproduce from
its log. The same mechanism makes fresh runs depend on the dial (30x packs observations into a shorter wall interval),
which is exactly what decision 2 rules out. The uuid ids alone are enough to make agent state differ between any two
runs. None of this is visible to the AST scan, which reads only `src/maxim_overdrive`.

**Fix:**
- Widen Phase 3 into one contract, "an in-game agent is deterministic given injected time and randomness": every
  agent subsystem gets an injected world clock, a seeded generator and an id source (memory capture, consolidation,
  the Default Network, the SCN, retrieval tie-breaks, `hash()`-keyed tables). Items 10 and 11 become instances of it,
  and it goes through Maxim's own process.
- On the Overdrive side, add a **runtime tripwire** test, since an AST scan can't reach site-packages. During
  `WorldHost.tick()` in a replay test, patch `time.time`, `time.monotonic`, `uuid.uuid4`, `random.*` and
  `os.urandom` so they raise, then step real pymaxim agents.
- Add a replay test with real agents, run under several `PYTHONHASHSEED`s and at two pacings.
- Until that lands, the design should say that bit-identical replay covers the world and stub agents only.

## D2. BLOCKER: the intent log's contents are unspecified, and the design's whole claim rests on them

**Location:** design §2 ("Ordering is part of the contract"), §2 "The thinking lane and determinism", §4 (the
TimeAuthority decision), §6 ("the intent log, with a replay test"); backlog B2 ("every accepted intent with its turn").

The design says what goes into the log in three scattered places (results, decisions, "the tick the host assigns"),
but never what one log record is. It also never says what makes a log complete. Each gap below lets the replay
diverge:

1. **The assigned tick isn't recorded (B2 says "turn").** The tick is assigned on arrival, from wall timing. If the log
   holds raw client messages, the replay has no way to rebuild their ticks. The record has to be the post-assignment,
   post-validation tuple: `(tick, actor, order, intent values)`.
2. **The run's length isn't recorded.** Ticks with no intents still run physics and substrates. If a session ran 9,000
   ticks with its last intent at tick 400, a replay that stops at the last record is 8,600 ticks short.
3. **Session and actor lifecycle isn't recorded.** If a join spawns an avatar or a leave removes one, that is a world
   change at a wall-timed tick (see D4).
4. **There is no header.** A replay against a rig or material YAML edited since the session (all in `data/`) diverges
   silently. Needed: format version, protocol version, code sha plus a dirty flag, pymaxim version, numpy and Python
   versions and the platform (bit-identity holds only on one machine), and the scene, rig, material table and world
   config (`tick_s`, `physics_period_s`, `day_length_s`, `epoch`, deliberation delays) as **contents or content
   hashes**, not paths. Also the World RNG seed and each agent's initial state, or its hash: "a life it actually
   lived" is state, and it is an input.
5. **Who writes the log isn't stated.** In co-op, if network lanes log on receipt, two sessions' records interleave in
   arrival order. Only the simulation lane may produce log records, in the order it applied them, and the record lane
   writes that single-producer FIFO stream as it comes.

**Failure:** two co-op clients, a 2a replay test that logs the decoded messages, and replay by re-queueing them.
Session A's `ignite` arrived on tick 41 live, but in replay it is dequeued on tick 0, so the crate burns 4.1 s earlier
and the digests differ.

**Fix:** specify the log format in the design as a versioned format (CLAUDE.md requires one, B3 and B4 style). It needs a
header as above. It needs records for intent, session join and leave (with the actor assigned), time decision,
thought result, thought failure, and an end marker with the final tick. It also needs a **state digest every N ticks and
at the end**, so a replay reports the first tick that diverges instead of just "differs". Replay feeds those records into the
same `WorldHost.tick()` through a log-backed input source (one code path) and refuses, loudly, a header it doesn't
match. Update B2's text from "turn" to "assigned tick".

## D3. SHOULD-FIX: (tick, actor, seq) isn't a total order as specified, and seq is client-chosen

**Location:** design §2 ("Ordering is part of the contract"), §5 ("Every message carries `seq`").

- `seq` comes from the client and is only "echoed". Nothing requires it to be unique or increasing. Two `act`s with
  the same seq in one tick tie on the key, and their order then falls back to arrival order on the channel.
- Same-tick order changes state bits, not only outcomes. `World.sources` is a dict. `_power_field` sums
  `src.power_w * weights` in insertion order (floating point, so the order changes the bits), and the digest hashes it
  in insertion order. `ignite` then `extinguish` and `extinguish` then `ignite` give different outcomes.
- A client can also reorder its own intents within a tick by choosing seqs (send seq 9, then seq 2). That may be
  fine, but it should be a decision, not an accident.
- When an intent's tick is assigned isn't stated: while the simulation lane is mid-tick, while it holds for a
  thought, or while paused. Can `act` apply while paused, and if so at which key?

**Failure:** a replay implementation that re-sorts records by `(tick, actor, seq)` breaks a tie differently from the live
host's stable sort over arrival order, so `sources` gets a different insertion order and the bits differ.

**Fix:** the ordering key uses a **host-assigned** per-session counter (the client's `seq` is only for the reply echo), or the
protocol refuses a non-increasing `seq` with an error. Log records in applied order, and replay in log order without
re-sorting. State the drain rule: intents are taken at step 1 of the tick that runs next. While paused or held they wait
in the channel, and an `act` never applies outside `tick()`. Add a test: two sessions, same tick, conflicting intents,
under three hash seeds.

## D4. SHOULD-FIX: actor ids aren't specified to be deterministic, across reconnects or for NPCs

**Location:** design §4 ("The host assigns the actor").

Actor id is the second field of the ordering key, so the numbering decides who acts first within a tick. The design
doesn't say how ids are made. If they come from connection order, that is wall timing: in co-op, whoever's client
connects first sorts first. If they come from `uuid4`, they come from OS entropy, and server/ is exempt from the scan. A
reconnect then gets either a new actor (a new avatar, with the old one orphaned) or the old one, and the design says
neither. NPC actor ids have to come from the scene's roster in a defined order, not from dict or set iteration. Players
and NPCs share one namespace, so the scheme also decides whether players act before NPCs in a tick. And the id needs
one type, since an int and a str don't compare.

**Failure:** live, the host joins at wall 0.2 s and the guest at 0.3 s, so the host is actor 1. In a second run of the
same scripted scenario, the guest's process starts faster, and both strike the same wall on tick 50 in the opposite
order. With the logged actor ids the replay is fine; a fresh scripted co-op test is flaky.

**Fix:** actors come from a deterministic allocator in the simulation lane: NPCs from the roster in sorted order,
players as `player:<n>` by join order with the join logged (D2). A reconnect presenting the session's resume
credential rebinds to the same actor. Decide and write down whether players sort before NPCs.

## D5. SHOULD-FIX: the wall-clock timeout makes fresh-run NPC behaviour depend on the dial and on pause, and its decision path is unspecified

**Location:** design §2 "The thinking lane and determinism" (hold up to a wall-time timeout, then `thought_failed`), §8
Q1.

The argument for holding is that NPC timing then doesn't depend on the dial. That holds only when no timeout fires. The
wall budget for a thought is about `d / time_scale + timeout`: at 30x the hold starts 30 times sooner in wall time, so
the same model latency produces more `thought_failed` at fast-forward than at 1x, and NPC behaviour again depends on the
dial. If the timeout keeps counting while the world is paused during a hold, pressing pause can fail a thought.
Logging `thought_failed` (as the design says) makes the replay correct, but only if:

- **the simulation lane decides the timeout**, reading an injected clock, not a worker. It logs `thought_failed` with
  its apply tick before it moves on.
- **a result that arrives after its failure is dropped**, never applied at a later tick, and counted in the meter.
  Without that rule, a late result that arrives at tick 230 for a thought failed at tick 200 changes the live world with
  no log record, and the replay diverges.
- **admission control is a logged decision or a world-time rule.** That means the in-flight cap and the priorities
  ("an NPC the player is talking to thinks first"). If a full pool defers or drops a request, that is a wall-dependent
  decision too.

**Failure:** run a fresh session twice, once at 1x and once at 30x, with a model whose latency is 1.5 s, `d` = 2 s and
`timeout` = 1 s. At 1x the reply lands. At 30x the NPC fails the thought and acts on reflex.

**Fix:**
- Restate the property as "independent of the dial up to timeouts, which are logged and metered per dial value".
- Freeze the wall timeout while the dial is paused.
- Make the sim lane the only authority for failure, and drop late results.
- Test the timeout path with an injected fake clock (no sleeps, per CLAUDE.md).
- For Q1, from this lens: either policy replays bit-identically *if* the apply tick is logged. Holding only buys
  dial-independence of fresh runs with a deterministic stub, which is still worth having because it is what makes
  scripted tests reproducible.

## D6. SHOULD-FIX: no order for several thoughts due on one tick, and requests aren't pinned to tick-T state

**Location:** design §2, simulation lane step 2 ("apply thoughts whose deadline is this tick"); §3 item 13.

- Step 2 gives no order among thoughts due on the same tick. A worker pool returns them in completion order.
- Request ids aren't specified. Maxim's own ids are `uuid4`.
- The request itself has to be built **by the simulation lane, from state at tick T**, as a frozen message. If the
  thinking lane builds prompts by reading `World`, agent memory or a shared snapshot while the simulation lane
  advances, the prompt depends on scheduling. That doesn't break a log replay, but it breaks fresh runs with the
  deterministic stub, whose output is a function of the prompt, and the 2b tests depend on those runs.
- Cancellation (item 13) racing a result needs the same "sim lane decides, then logs" rule as D5.

**Failure:** NPCs A and B both get a result due at tick 50, both acting on the same door. A's completes first in run 1
and B's in run 2, so the door ends in a different state. With the stub, the 2b test is flaky.

**Fix:** request id = `(request tick, actor, per-actor counter)`, assigned in the sim lane. At tick T + d, wait for
**all** thoughts due on that tick, then apply them in request-id order. Requests carry a frozen copy of the inputs
they need. Specify where in the tick a thought applies relative to the tick's intents and to the substrate step
(the diagram implies intents, then thoughts, then substrate, then physics; make it normative).

## D7. SHOULD-FIX: world time should be integer ticks; float seconds give a second clock and fragile rounding

**Location:** design §1 ("The world's time is `tick × tick_s`", "a multiple of `tick_s`", "Time of day is
`(epoch + tick × tick_s) mod day_length_s`"), §2 (`T + d`, with d in world seconds); `world/heat.py::step`
(`grid.time_s += seconds`), `world/world.py::snapshot` (`time_s`).

Each of these is deterministic on its own, but each is a place where two pieces of code that should agree won't
(host vs replay tool, server vs Maxim's SCN, a validator vs the tick loop). Measured in CPython:

- `0.5 % 0.1 == 0.09999999999999998` and `0.3 / 0.1 == 2.9999999999999996`. A naive "is `physics_period_s` a multiple
  of `tick_s`" check refuses 0.5, and `int(period / tick_s)` turns 0.3 into 2 ticks.
- A deliberation `d` = 0.7 s gives `0.7 / 0.1 == 6.999999999999999`, so `int` gives 6 ticks and `ceil` or
  `round` give 7. The apply tick depends on which one a given reader happens to call.
- `k * 0.1` differs from the decimal value for about 33% of ticks below 100,000 (for example, tick 3 reports
  `world_time_s = 0.30000000000000004`).
- `grid.time_s` is a **second world clock**, accumulated by `+=` in `heat.step` and included in the determinism digest.
  With the proposed 0.5 s period it stays exact, since 0.5 is dyadic. With a period of 0.3 s, ten accumulated steps give
  `2.9999999999999996` against `30 × 0.1 = 3.0000000000000004`. That contradicts "Nothing else is the world's time".
- `epoch` has no type. If it is a calendar date, converting it needs `datetime`, which the scan bans in the simulation.

**Fix:**
- Make the tick the only clock. World config holds `tick_s` plus **integer** `physics_period_ticks`, `day_length_ticks`
  and per-request deliberation ticks. Alternatively, keep seconds in YAML but convert once at load by an exact rule,
  refusing values that aren't integral multiples (`Fraction(str(x))` is exact).
- Make `epoch` integer seconds (or ticks) from a fixed calendar origin.
- Compute `time_of_day_ticks = (epoch_ticks + tick) % day_length_ticks`, and convert to float seconds only at the edges
  (wire, percepts).
- Derive `grid.time_s` from the tick instead of accumulating it, or drop it from `World`. Put the integer tick in the
  digest.

## D8. SHOULD-FIX: the server/ scan exemption will cover the new host code unless the package is split

**Location:** `tests/test_determinism.py::NOT_SIMULATION`, design §2 and §6 (where `WorldHost`, the pacer, the
TimeAuthority, the log and the thinking lane live isn't stated).

The exemption exists because transport has to read the clock and OS entropy (timeouts, the token). The 2a/2b code
puts the deterministic core and the wall-reading code side by side: `WorldHost.tick()` and ordering, the log and replay,
`TimeAuthority`, the thought deadline logic, against the wall pacer, the thought timeout and token generation. If all of
it goes in `server/`, nothing static stops `uuid4()` as an actor or request id, `time.monotonic()` reaching a log record
or a thought decision, or `random` jitter in the thinking queue. B14's planned test only checks that no wall duration
reaches `World.advance`, which is narrower. Set iteration (for example `for s in self.sessions` over a set) is caught by
no scan. The hash-seed subprocess test covers only `run()`, the bare World scenario.

**Failure:** `WorldHost` keeps `sessions: set[Session]` and iterates it to drain per-session channels, which assigns intra-tick
order by `PYTHONHASHSEED`. `server/` is exempt, and no existing test runs the host under different hash seeds.

**Fix:**
- Put the simulation lane, ordering, actor allocation, the log and replay, `TimeAuthority` and thought scheduling in a
  **scanned** package (for example `host/`).
- Keep `server/` to transport, the pacer and wall-clock adapters, all behind an injected `WallClock` protocol.
- Add a test that `host/` never imports `server/`.
- Extend the hash-seed subprocess test to a host replay with two or more sessions and two or more stub NPCs.
- Extend B14's row to say what the exemption now covers.

## D9. SHOULD-FIX: the live-model promise is misstated

**Location:** design §2 ("A fresh run with live models is reproducible only in outcome class, as across machines"), §7
last bullet, §1 "The dial" ("A run at 0.25× and a run at 30× with the same intents on the same ticks are
bit-identical").

"Outcome class" is the resolution rule's promise for the **same inputs** at different precision. LLM variance changes the
inputs: one sample has the NPC put the fire out and another has it flee, which is a different outcome class. Live player
input lands on wall-dependent ticks too, so a fresh live run isn't reproducible even with no model. The claim is a
contract (charter: "a claim is a contract"), and as written it promises something no test could check.

**Fix:** state three tiers.
1. **Replays** from a log are bit-identical on one machine and match in outcome class across machines.
2. **Fresh runs with scripted intents on fixed ticks and the deterministic thinking stub** are bit-identical at any
   dial and pacing. 2a and 2b test this, after D5's timeout caveat.
3. **Fresh runs with live models or live players are not reproducible.** The log is the only reproduction.

## D10. NIT: define which interval a physics step covers

**Location:** design §1 (physics period), simulation lane step 4.

On physics tick k, `advance(physics_period_s)` runs after step 1. An `ignite` on tick k − 4 and one on tick k both get the
whole period's heat. That is deterministic, but it is a semantic, and changing it later breaks every committed log.
Write it down (for example: physics runs on ticks where `tick % P == 0` with `tick > 0`, after intents, and covers
`(k − P, k]`), and give it a place in the log format version.

## D11. NIT: make it structurally impossible for a snapshot to feed back

**Location:** design §2 ("published snapshot (immutable)"), §5 (`snapshot` request, `world_time_s` in headers);
`world/world.py::snapshot`.

The arrays are copies, so a write to them can't reach `World`. They are still writable, though, so "immutable" isn't
true. A `snapshot` request served by a network lane reading `World` directly could also be torn mid-tick.

**Fix:**
- Set `flags.writeable = False` on published arrays.
- Serve `snapshot` requests from the last published snapshot, or queue them to the simulation lane.
- Specify that no client-echoed value (`tick`, `world_time_s`, `seq`) is ever read as an input to the world.

## D12. NIT: the period-split test can show the bit-level behaviour too

**Location:** design §1 (`max_substep_s`, "one 6 s advance and as twelve 0.5 s advances").

At laptop, 0.5 / 1.5 means 1 substep per period, so 12 per 6 s against 4 today. At max, `ceil(0.5 / 0.094)` is 6, so
72 per 6 s against 64. That is fine for the outcome class. Also assert that the stepped host at P ticks gives the same
digest as direct `World.advance` calls, so the host adds no hidden state.

---

## Checked and found sound

- **One owner of `World`.** If only the simulation lane mutates it, thread scheduling can affect only *which tick*
  an input lands on. That is recorded, so it is replay-safe. Moving a lane to a process doesn't change this.
- **The dial changes only how often `tick()` runs, and `tick()` takes no duration.** This is the right shape. No wall
  value enters `World` through the clock path, and B14's planned check fits it.
- **No `advance` in the client vocabulary, and the actor comes from the session.** Clients can't move time or spoof
  another actor's place in the order.
- **Logging time decisions rather than re-running the policy** is correct. The dial isn't world state (D2 still needs
  the decisions in the record stream for a faithful session replay).
- **Thought results read from the log in replay, never from a live model.** This is correct, given D5 and D6.
- **Held thoughts make apply ticks independent of latency** for every thought that doesn't time out. The request
  tick T is deterministic when the request comes from substrate state or from a logged intent.
- **The heat solver's sub-stepping** (`heat.step`) is a pure function of the grid and `seconds`. Splitting a period
  into substeps involves no wall or ordering input.
- **The existing guards** (`test_two_runs_are_bit_identical`, the hash-seed subprocess test, the AST scan with its
  pinned positive and negative cases) are sound for what they cover today: `World` alone. D1 and D8 are about what
  they will stop covering.
