# Determinism and replay lens, delta round 1: realtime_lanes_coop.md v1 (at 02338ef)

Reader brief: `docs/code_review.md`, the **Determinism and replay** row. Scope: (1) the fold of round-1 findings D1
to D12 (`determinism.md`); (2) the owner's decisions 7 to 10, above all §4.3 (no hold, apply on the first tick after
arrival, abandonment after `max_age_ticks`, wall timeout frees only the worker, the stub with fixed latency in ticks)
and their effect on §4.4's three tiers, §2 and §7, and the experiments in `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`.
Also read: CLAUDE.md "Game engineering", `tests/test_determinism.py`, the round-1 README.

Counts: **1 BLOCKER, 6 SHOULD-FIX, 3 NIT.**

---

## DD1. BLOCKER: tier 2 can't hold if the stub's results come through the inbox; the stub must be scheduled inside the `Simulation`

**Location:** §4.3 ("A thought applies on the first tick after it arrives"; "The test stub has a fixed latency in
ticks"), §4.4 tier 2, §4.1 (the simulation lane "waits on ONE inbox: intents, controls, thought results"), §8 PR 4.

v1 makes the apply tick a function of **arrival**, and arrival is wall time. "A fixed latency in ticks" is a property
of the stub's *output*, but the design never says how the stub delivers it. Read literally, the stub is a worker in
the thinking lane like the live model, and its result goes through the same inbox. Then the apply tick is
"the first tick boundary after the worker thread happens to `put` the result", and that is decided by thread
scheduling and pacing, not by the stub's latency.

**Failure:** a 2b test requests a stub thought at tick 100 with latency 10 ticks.
- Run A, paced at 1x: the worker sleeps or counts to tick 110 and puts the result. The simulation lane has 100 ms of
  wall time per tick, so it drains the result at the 110/111 boundary and applies it at tick 111.
- Run B, unpaced (headless, as the 2b tests run): the simulation lane does ticks in about 1 ms each (laptop, no
  physics tick). Whether the worker thread is scheduled before the boundary for 111, 112 or 140 depends on the GIL
  and the OS. The result applies at, say, tick 118. The NPC's door intent races a scripted `ignite` differently, and
  the digests differ.
- If instead the worker "waits until the simulation reaches tick 110", that wait is the thinking lane polling the
  simulation's tick across threads, and the result can still miss the boundary. If the simulation lane waits for it,
  that's the hold decision 7 forbids.

A fixed latency in ticks is only deterministic if nothing on a wall path sits between the request and the apply.

**Fix:**
- Make delivery a `ThoughtSource` seen by `Simulation.step`, with three implementations behind one apply path:
  - **stub:** computes the pure result synchronously when the request is made, and holds it in the `Simulation`
    (checkpointed state) to be released at exactly `T + latency_ticks`. No thread, no inbox.
  - **live:** the thinking lane and the inbox, as §4.3 describes (tier 3).
  - **replay:** reads `thought_result` and input `thought_failed` records from the log (tier 1).
- State the off-by-one: whether latency L means "applied at tick `T + L`" or "arrives at `T + L`, applied at
  `T + L + 1`". Under the "first tick after it arrives" rule these differ, and H2's 0 s arm needs a defined meaning
  (DD6).
- Tier 2's claim then rests on the stub never touching a thread. Its test runs the same scenario unpaced and at two
  pacings (and under three hash seeds), with a scripted thought that races a scripted intent on the tick it applies.
  Prove the guard by routing the stub through the inbox once and watching that test go red.

## DD2. SHOULD-FIX: the log mixes inputs with decisions the `Simulation` derives, and thought records lack the request id

**Location:** §7 "The intent log v0" (kinds: join, leave, time decision, intent, thought result, thought failed),
§4.3 (abandonment, cancellation, late arrivals dropped, stale refusals fed back to the NPC).

Under the new rule, a thought can end in five ways: applied; refused as stale at apply; abandoned at `max_age_ticks`
(world time, derived); cancelled by pain or salience (derived, §6 item 13); failed because the worker's wall timeout
fired (an input from wall time). Then a result may arrive after it was already ended and get dropped. The log has one
`thought failed` kind for two cases with opposite replay semantics. It has no kind for cancellation, and nothing for a
dropped arrival. And thought records carry `actor` but no request id.

**Failure scenarios:**
1. **Wrong request matched.** NPC 7's request `(200, 7, 3)` is abandoned at tick 260 and the NPC issues
   `(261, 7, 4)`. The old model call returns at tick 265. If the result record and the worker reply are keyed by
   actor ("one outstanding thought per NPC"), the late answer to request 3 is applied as the answer to request 4. That
   is logged, so the replay reproduces it, but it's a live bug that the log calls normal. If the record has no
   request id, the replay can't detect that request ids drifted between the live run and the replay either, and it
   applies a logged result to whatever request the NPC happens to have open.
2. **Abandonment applied twice, or not at all.** If the replay re-derives abandonment from `max_age_ticks` *and*
   reads `thought failed` from the log, the NPC gets two failure outcomes. If it only reads the log, a change to
   `max_age_ticks` (DD4) or to the abandonment code isn't caught. If it only re-derives, a wall-timeout failure (which
   can't be re-derived) is lost, and the replay keeps a thought open that the live run freed: the NPC issues its next
   request at a different tick, and from there every request id differs.
3. **Same-boundary race.** At the boundary for tick 260 the inbox holds the result for a request whose age reaches
   `max_age_ticks` at 260. Whether it applies or is abandoned depends on which check runs first. That's deterministic
   only if the `Simulation` makes both decisions in one fixed order. If the host drops "late" results before handing
   arrivals over (it holds the inbox) while the `Simulation` decides abandonment, the two can disagree across a code
   change, and a replay built on the `Simulation` alone diverges from the live host.

**Fix:**
- Split record kinds into **inputs**, which replay feeds (join, leave, time request with its decision, intent,
  `thought_result`, `thought_worker_failed`), and **derived decisions**, which replay recomputes and then **asserts
  equal** to the logged copy (`thought_abandoned`, `thought_cancelled`, `thought_stale`, `thought_dropped_late`).
  The first mismatch is reported like a digest mismatch, at its tick.
- Every thought record carries the request id `(tick, actor, n)`. Worker replies carry it too, and the `Simulation`
  matches on it, never on actor.
- Log a `thought_request` record (request id plus a hash of the frozen context) as a derived record. A replay whose
  agents produce a different request at a tick then fails at that tick, which is the earliest signal D1's agent
  nondeterminism will give.
- Log dropped late arrivals as inert audit records (applying them is a no-op). Tier 3 says "the log is complete",
  and H2's "abandoned thoughts" meter has to be computable from the log alone (DD6).
- Put every one of these decisions inside `Simulation.step`. The host only hands it arrivals in the order they came
  off the inbox (see DD3).

## DD3. SHOULD-FIX: three different orderings are stated for records within a tick

**Location:** §2.1 ("apply this tick's records in log order (joins, leaves, time decisions, intents, thought
results)"), §4.2 ("Each record gets `(tick, host_seq)` when the simulation lane takes it off its inbox"; "Thoughts due
on the same tick apply in request-id order"), §5 ("Same-tick conflicts favour whoever applies first in host order,
which is arrival order").

There are now three ordering rules. `host_seq` is arrival order. The parenthetical in §2.1 is a kind order. And §4.2
orders thoughts by request id, with leftover hold-era wording ("due on the same tick": under decision 7 nothing is
due, things arrive). These are only consistent if `host_seq` is assigned *after* sorting. If it's assigned on
arrival, which is what §4.2 says, then applying "in log order" and applying "by kind, then request id" are different
orders. A replay that sorts is D3's round-1 failure: tie-breaks differ from the live host's.

**Failure:** at the boundary for tick 50, the inbox holds, in arrival order: NPC 3's thought result (an `extinguish`,
requested at tick 40), then a player `ignite` on the same crate. `host_seq` follows arrival: the thought gets 1 and the
ignite 2. The live host follows §2.1's kind order (intents before thought results), so it applies the ignite and then
the extinguish, and the crate ends the tick unlit. A replay that follows §4.2 and applies "in log order" applies the
extinguish first (it refuses as stale, since nothing is burning) and then the ignite, so the crate ends the tick
burning. The NPC also learns a different outcome. The bits differ, and each reader followed a sentence in the design.

**Fix:** one normative rule, written once:
- At a tick boundary, the `Simulation` receives the arrivals for tick k **in inbox order**.
- It sorts them by a total key: kind rank, then `(session arrival index)` for client records, or request id for
  thoughts.
- It assigns `host_seq` in that sorted order, then writes and applies them.
- Log order is then apply order by construction, and a replay never sorts.

Decide explicitly whether a player intent and a thought arriving in the same drain are ordered by kind (deterministic
for tier 2) or by arrival (§5's current wording). Delete "due" from §4.2.

## DD4. SHOULD-FIX: values that decide outcomes live outside the hashed header

**Location:** §2.2 ("Server config (`snapshot_hz`, queue limits, rate limits, caps) is separate, in `data/server/`,
because it doesn't change the world"), §4.3 (`max_age_ticks` "in `data/`", the stub latency, the queue priority),
§7 (header hashes the scene, rig, materials, world config, roster; the simulation lane checks "per-tick limits"; "a cap
on heat sources").

Several values that change the world, or an agent, aren't in the hashed world config:
- **`max_age_ticks`** decides abandonment, which changes when the NPC issues its next request.
- **The stub's `latency_ticks`** (and any stub parameters) decide every tier-2 apply tick.
- **The per-tick limits and the heat-source cap** decide whether a simulation-lane check accepts an `ignite`.
- **The stale-refusal rule** decides what outcome the NPC learns from.

Some are said to be server config, which is defined as "doesn't change the world". In fact they do.

**Failure:** someone raises the heat-source cap in `data/server/` from 16 to 32 after a session in which the 17th
`ignite` was refused. If the replay re-runs stage-2 validation (it has to, for stale thoughts, because a stale
refusal feeds back to the NPC), the 17th `ignite` now succeeds. The header still matches, since `data/server/` isn't
hashed, and the replay silently diverges. The same edit to `max_age_ticks` breaks a tier-2 test with no header
change, and `git blame` doesn't point at a world file.

**Fix:**
- Move every value read inside `Simulation.step` into world config (or a hashed `data/world/thinking.yaml`):
  `max_age_ticks`, stub parameters, per-tick limits, the source cap, staleness rules.
- Leave in `data/server/` only what acts before a record has a tick: wall-time rate limits, queue sizes,
  `snapshot_hz`, the model call's wall timeout.
- Add a test that `Simulation` can't read server config. For example, `Simulation.__init__` takes only `WorldConfig`,
  and an AST check forbids the `Simulation` package from importing the server-config loader.

## DD5. SHOULD-FIX: tier 2 lost "on fixed ticks", so as worded it promises something false

**Location:** §4.4 tier 2 ("Scripted runs are bit-identical at any dial and any pacing, with stub agents").

Round-1 D9 put tier 2 as "fresh runs with **scripted intents on fixed ticks** and the deterministic thinking stub".
v1 drops the qualifier. A scripted client that sends its intents over the WebSocket (PR 3's end-to-end test, the B7
scripted scenario) gets ticks by arrival (§4.2, X8), so it is live input in the tier-3 sense.

**Failure:** the B7 scripted scenario sends `ignite` 2.0 s of wall time after `welcome`. At 1x it lands on about tick
20, and at 4x on about tick 80. The crate has burned four times longer by the time of the next scripted action, and
the golden screenshots differ. Nothing in the tier-2 wording warns a test author.

**Fix:** reword tier 2 as "runs whose inputs carry their ticks (a script fed to `Simulation.step`, or a scripted
client whose `act`s name a target tick, if the protocol ever allows one) with stub agents". State that a scripted
client over the wire, without target ticks, is tier 3 and is reproduced only by its log. If B7 needs a wire-level
scenario that's dial-independent, it needs a test-only "apply at tick" field. That is a protocol decision, refused
in v0's closed schema today, so B7 should instead run the scenario as a log replay through the host and the client.

## DD6. SHOULD-FIX: H2 and H6 aren't reproducible as designed

**Location:** `hybrid_1_5_line_DRAFT.md` ("replayed bit for bit"; H1, H2, H6; prerequisites), design §4.3, §2.3's
cost table.

1. **"Replayed bit for bit" needs more prerequisites than the draft lists.** H2 sweeps stub latency, but the NPC's
   substrate is real Maxim: NAc, drives, the DN and the SCN. Until #1361 (wall-clock decay), item 10 (`TemporalSignature`
   on the world clock) and item 15 (injected clock, RNG and ids) land, two runs of the same H2 arm differ (round-1 D1:
   hippocampus de-duplication on `time.time()`, `uuid4` ids). The draft names items 11, 12, 13, 15 and 16, but not
   #1361 or item 10. And it says the sweep can be "replayed bit for bit" without saying that this is true only after
   item 15.
   **Failure:** two H2 runs at latency 3 s, same seed. NPC memory dedup differs with wall pacing, the requests differ,
   and the curve point has variance that the pre-registration treats as zero.
2. **`max_age_ticks` truncates the sweep.** The 30 s arm is 300 ticks. If `max_age_ticks` is below 300, every thought
   in that arm is abandoned, so the arm measures abandonment, not latency. The pre-registration has to fix
   `max_age_ticks` relative to the sweep (or above its top), and record it in the hashed config (DD4).
3. **H2's 0 s arm is undefined** under "first tick after arrival" (DD1). Pre-register it as "applied at `T + 1`", or
   whatever DD1 fixes. Then note that H1's "world paused for each thought" arm is the same as that arm whenever
   deliberation content is a stub. It needs no pause mechanism in the game, which keeps decision 7's "never build the
   hold" intact.
4. **H6 is tier 3, and the draft doesn't say what makes it repeatable.** With a live model, its "dial sensitivity"
   also mixes in:
   - model sampling;
   - wall-latency drift (provider load, model version);
   - dilation: at the max profile the world can't reach 1x (§2.3), so a "4x" arm may run at 2x effective;
   - pause: the model's wall timeout keeps counting while the world is paused (§4.3), so pausing fails thoughts;
   - the wall-clock substrate reads in point 1, which make behaviour depend on the dial for reasons unrelated to
     thinking speed.

   **Failure:** H6 at 0.25x, 1x and 4x on the rig profile shows a behaviour difference that's driven by NAc decaying
   on the wall clock (faster per world second at 0.25x), not by thought latency. It gets reported as dial sensitivity
   of deliberation.
   **Fix:** pre-register H6 with:
   - a pinned model and version, temperature and seed if the provider supports one, and N repeats per arm with a
     stated statistic;
   - arms defined by **effective** scale from the tick status, with runs whose dilation exceeds a bound excluded;
   - per-call wall latency and world-tick latency recorded (a meter or side file; never world state);
   - no pauses during a run;
   - #1361 and items 10 and 15 as hard prerequisites.

   Add an **H2-live arm**: the live model with fixed-tick delivery (the `Simulation` releases the result at
   `T + L`, and a result that hasn't arrived by then counts as late). This separates "content from a real mind" from
   "latency", and it stays dial-independent whenever the model beats `L`.

## DD7. SHOULD-FIX: the tripwire, as described, is process-global and would be silently absorbed by the thinking lane

**Location:** §4.4 ("A tripwire test makes `time`, `uuid` and the global `random` raise inside `Simulation.step`").

Patching `time.time` and its neighbours patches the whole process. With lanes running, the thinking lane's worker (its
wall timeout) and the network lane's asyncio loop also start raising. Under §4.3 a worker's exception "arrives as a
message, applied and logged like any result". So a tripwire hit in a worker becomes a `thought failed` record, not a
test failure. Worse, a hit inside agent code reached from `step` and a hit in the worker look the same. The list is also
narrower than round 1's: it omits `os.urandom`, `secrets`, `datetime.now`, `time.monotonic` and `perf_counter`, and
numpy's global `np.random.*`.

**Failure:** a future Maxim agent calls `time.time()` during `step(2)`, inside a `try` in Maxim that logs and carries
on (Maxim has such handlers). Meanwhile the patched clock makes a worker fail, and the test sees only a thought
failure, which is a legal outcome, so the test passes.

**Fix:**
- Make the tripwire thread-scoped: the patched functions raise only when `threading.get_ident()` is the simulation
  lane's thread inside `step`, and the record of the hit goes to the test's own list, which the test checks, so a
  swallowing `try` in Maxim can't hide it.
- Run it headless (no lanes) first.
- Widen the list to round 1's: `time.*` clocks, `datetime.now`/`utcnow`/`today`, `uuid.uuid1`/`uuid4`, `random.*`,
  `os.urandom`, `secrets`, and `np.random` module-level functions.
- Prove it by planting one `time.time()` in a stub agent's step.

## DD8. NIT: round-1 folds that were missed or went stale under decision 7

- **D12 not folded.** §2.3 has the period-split cross-tier test, but not the assertion that a `Simulation` stepped P
  ticks gives the same digest as direct `World.advance` calls. The README says D10 to D12 were taken.
- **D10, partly.** "Physics runs on ticks where `tick % physics_every_ticks == 0`" includes tick 0, where "the
  interval that ends at this tick" is `(-0.5 s, 0]`. Say `tick > 0`, or say the first step's tick is 1. Also say whether
  a record "at tick k" is applied in the step that ends with the clock at k or the one that starts at k. The off-by-one
  matters for DD1 and H2's 0 s arm.
- **§2.1 save:** "the thoughts in flight with their deadlines" is hold-era wording. Under decision 7 a save holds
  each in-flight request's id, request tick and frozen context, plus any stub results pending release (DD1). On load,
  live in-flight thoughts can never return, so state the rule (re-dispatch, or abandon at once as a logged derived
  record). It has to be one rule, or a continued session and a reloaded one diverge.
- **README.md:** the cross-confirmed row for A9/D5/CP-3/Bio-5 still says "a held state that serves control, a
  budget", and "Not settled" still lists Q1. Both are superseded by decision 7 and should say so. The finding files
  stay verbatim, but the fold record should be current.
- **D2's dirty flag** (code SHA plus a dirty-tree flag) isn't in §7's header.

## DD9. NIT: say where the boundary between wall and world sits in code

**Location:** §4.1 (the simulation lane "assigns each record its tick and a host sequence number, writes it to the
log, then applies it"), §4.4 ("The host code lives in a package the AST scan covers; `server/` holds only the
transport"), §2.1 ("The host only collects inputs and paces calls").

§4.4 puts "host code" in the scanned package, but the host paces on the wall clock, so it can't pass the scan. D8's
split is right in spirit, but the line has to be drawn precisely. Tick assignment, `host_seq`, sorting, drop and
abandonment (DD2, DD3) belong in scanned code inside `Simulation.step`. The pacer, the inbox wait and the wall timeout
belong in `server/`, behind an injected `WallClock`. As written, a reader could put `host_seq` assignment next to the
pacer in `server/`, where the scan and the hash-seed test don't reach.

**Fix:** state that the only thing that crosses from `server/` into `Simulation.step` is "this tick's arrivals, in
inbox order, as validated frozen values". Everything after that is the `Simulation`'s.

## DD10. NIT: a pause fails live thoughts

**Location:** §4.3 (wall timeout frees the worker; its failure arrives as a message).

The model call's wall timeout keeps running while the world is paused, so a pause longer than the timeout turns
every in-flight live thought into a failure, applied on the first tick after resume. That's logged, so tier 1 holds.
But it's a player-visible effect of pressing pause (NPCs "forget what they were thinking"), and a confound for H6
(DD6). Options: let the worker's result wait in the inbox through a pause (the timeout only bounds the call, and a
result that came back during the pause is still a result), or record pause time in the meters so the analysis can
exclude it. Decision 7 isn't affected either way.

---

## Round-1 fold check

| Round 1 | v1 | Verdict |
|---|---|---|
| D1 agent wall clock and entropy | §4.4 (tiers, tripwire), §6 item 15 and #1361 | Folded. The tripwire is narrowed and process-global (DD7). The real-agent replay test is deferred correctly to item 15 |
| D2 log contents | §7 intent log v0 | Mostly folded: header, records, digest, end marker, single writer, untrusted reader. Missing the dirty flag (DD8), input vs derived split and request ids (DD2), hashed thinking config (DD4) |
| D3 total order, client `seq` | §4.2 `host_seq`, §7 increasing `seq` | Folded, but the within-tick ordering is now stated three ways (DD3) |
| D4 actor ids | §4.2 allocator, roster order, never reused | Folded. A host reconnect after a leave (§5) presumably gets a new actor, so the old avatar's fate should be stated. Minor |
| D5 timeout, late results, admission | §4.3, superseded by decision 7 | The rules that survive are kept (simulation lane decides abandonment in world time, late arrivals dropped). Fake-clock testing of the worker timeout isn't mentioned. Pause interaction in DD10 |
| D6 same-tick thoughts, frozen request, cancellation | §4.2, §4.3 | Request ids and frozen context folded. "Due" wording is stale, and cancellation has no log kind (DD2, DD3) |
| D7 integer clock | §2.1, §2.2 | Folded well: `tick_us`, `physics_every_ticks`, `day_length_ticks`, integer UTC `epoch_us`, `grid.time_s` removed, time of day in integers |
| D8 `server/` exemption | §4.4, §2.1 | Folded in intent; the boundary needs pinning (DD9) |
| D9 three tiers | §4.4 | Folded, but tier 2 lost "on fixed ticks" (DD5), and under the new rule it needs DD1 |
| D10 physics interval | §2.1 step 3 | Partly folded (DD8) |
| D11 snapshot feedback | §7 (read-only arrays, served from the last published snapshot) | Folded |
| D12 digest equality | — | Not folded (DD8) |

## Checked and found sound

- **Tier 1 survives decision 7 in principle.** Apply ticks are inputs assigned at a boundary by one thread and
  logged. Interleaving of thought results and client intents at a boundary is a wall-time fact recorded in `(tick,
  host_seq)`. With DD3's single ordering rule and DD2's request ids, a replay feeds the same arrivals and gets the same
  bits, whatever the thread scheduling or dial was live.
- **Dropped late arrivals replay identically.** Dropping one is a pure function of the `Simulation`'s open-request
  set at that tick, which is itself determined by logged records. A replay that never sees the arrival reaches the
  same state, provided the drop and abandonment decisions both sit inside `Simulation.step` (DD2 point 3).
- **Abandonment in world time** (`max_age_ticks`) is the right authority. It's re-derivable, independent of the
  dial, and doesn't stop at pause.
- **"Thinking speed depends on the dial" is confined to tier 3** and stated honestly. It doesn't touch the dial's
  promise for replays (§3.1: the dial changes only how often `step` is called).
- **The integer clock** (§2.1, §2.2) removes every float-rounding hazard D7 measured. `World.advance` gets a duration
  computed once from integers, so it is the same float every time.
- **Requests built in the simulation lane from tick-T state as frozen values, with results as pure values that pass
  the same validator**, keep the model off `World` entirely. Stale refusal at apply is computed from world state at
  the apply tick, so it is deterministic given that tick.
- **The world-time abandonment and the wall timeout don't conflict.** The first decides the world; the second only
  frees a worker and becomes an input record. Once DD2 splits the kinds, the design keeps them apart.
- **One owner of `World`, the single writer of the log, and a crash flush that includes the record that caused it**
  remain sound for replay as the bug report.
