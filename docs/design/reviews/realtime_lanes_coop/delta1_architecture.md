# Architecture lens, delta round 1: realtime_lanes_coop.md (design v1 with owner decisions 7 to 10, at 02338ef)

Reader: Architecture. Inputs: CLAUDE.md (including "Push back on Maxim"), `docs/code_review.md`, `docs/architecture.md`,
`docs/roadmap.md`, `docs/standards_backlog.md` (B15), the design v1, `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`,
this lens's round-1 file and `README.md` here. Checked against code: `world/world.py`, `world/grid.py`, `world/heat.py`,
`sem_env/bridge.py`, `scripts/lint_standards.py::check_guards`. Checked against Maxim: `docs/plans/experience_clock_decay.md`
§(g), `docs/plans/deferred/hybrid_substrate_reflex_runtime.md` (revive trigger, BL-1 to BL-5), `outstanding.md` M76,
`decisions/nac.py::recommend_action`.

Counts: 3 BLOCKER, 13 SHOULD-FIX, 8 NIT.

## Round-1 fold check (A1 to A16)

| Id | Verdict | Notes |
|---|---|---|
| A1 | Folded, one gap | `Simulation` owns tick, config, RNG, agents (§2.1). Gap: the SEM bridge's sensor timestamp and `snapshot()["time_s"]` read `grid.time_s`, which §1 removes, and `World` has "no clock of its own". See DA-10. |
| A2 | Folded, two gaps | Header, records, digests, fixtures (§7). Gaps: which header fields refuse on mismatch, and no record size bound for LLM content. See DA-8. |
| A3 | Folded | §4.3 frozen request and pure result, item 16. |
| A4 | Folded | §2.3 integer rig field, caching, re-measure. Known-gap numbers must be re-measured, not only relabelled (DA-15). |
| A5 | Folded | §2.1, §2.2 integers. |
| A6 | **Partly missed** | `host_seq` and integer actor ids are in. How NPC-originated intents (agent step, §2.1 step 2) enter the order, and at which tick, isn't. See DA-5. |
| A7 | Folded | One validator (§7). Its shape across two stages needs fixing in PR 1 (DA-9). |
| A8 | Folded | §5. The physical meaning of co-op on a loopback-only listener went with the dropped scope list (DA-19). |
| A9 | Superseded by decision 7 | Apply-on-arrival with the applied tick logged keeps replays exact. But the stub path now contradicts it (DA-1). |
| A10 | Folded | §4.1, item 15. |
| A11 | **Partly missed** | "Supersedes" exists but omits `docs/code_review.md`, two CLAUDE.md lines that now contradict the design, and several roadmap and backlog lines. See DA-15. The Phase 4 dialogue model is listed as stale but not given its replacement. |
| A12 | **Partly missed** | The save holds "the thoughts in flight with their deadlines", but the load rule (cancel, or re-issue) isn't decided, and under decision 7 there are no deadlines. See DA-6. |
| A13 | Folded | §4.1. |
| A14 | Folded, one gap | `data/world/` vs `data/server/` (§2.2). But caps the simulation lane enforces are in the unpinned file (DA-7), and B12 isn't updated. |
| A15 | Folded | §3.1. |
| A16 | Folded | §7 `time` row. |

## BLOCKER

### DA-1. Tier 2 ("scripted runs bit-identical at any dial") contradicts "a thought applies on the first tick after it arrives"
**Where:** §4.3 ("A thought applies on the first tick after it arrives"; "The test stub has a fixed latency in ticks"),
§4.4 tier 2, §8 PR 4 ("the thinking lane with its stub and late-thought semantics"), the hybrid draft's H2 ("a stub
with a fixed latency in ticks").
**Scenario:** PR 4 puts the stub in the thinking lane's worker pool, as the design describes the lane. A request at
tick T with stub latency L=10 returns from the worker within microseconds of wall time. Under the rule as written it
applies at T+1, not T+10. If the stub instead sleeps until "tick T+10", it has to read the simulation's tick from
another thread, and at a fast dial or unpaced the simulation has passed T+10 before the worker wakes. Arrival then
depends on scheduling, and tier 2 fails. The only way to apply at exactly T+10 through the arrival rule is to hold
the world for the stub, which decision 7 forbids. H2's latency sweep depends on exactly this mechanism.
**Fix:** One delivery rule for every thought: **apply at `max(request_tick + min_latency_ticks, first tick after
arrival)`**, with the applied tick logged. A stub's result is computed when it's requested (it is a pure function)
and goes into the simulation lane's own scheduled queue, so nothing waits. A live model has `min_latency_ticks = 0`
unless an experiment sets one. That gives tier 2 at any dial, gives H2 its exact sweep (with live models too), and
leaves decision 7 intact. Write the rule in §4.3, cite it in §4.4 tier 2, and make PR 4's test "same log at 0.25×,
1×, 30× and unpaced, with the stub".

### DA-2. Q2's answer, "NPCs live most of their days in headless cradles, unpaced", leaves cradle NPCs almost no thoughts
**Where:** §3.4 (third bullet), §9 Q2, owner decision 8, §4.3 (nothing waits; `max_age_ticks`).
**Scenario:** Unpaced means the host calls `step` as fast as it can (§3.1). With the caching fix the laptop runs about
300× (§2.3). A 2 s live LLM call then lasts about 600 world seconds. With one outstanding thought per NPC, an NPC
gets about 1/300 of the deliberation per world hour that it gets in play, and any `max_age_ticks` short enough to
matter in play abandons most of them. The NPC arrives at play with days lived almost entirely on substrate, its
memory writes (which come from thoughts, §4.3) mostly missing. The owner chose decision 8 partly on this bullet,
and with decision 7 it doesn't deliver what it says. (With a stub, the cradle has no real deliberation either.)
**Fix:** Say what a cradle trades. The honest options:
- (a) Pace cradles at the dial play uses, so deliberation per world second matches play, and pay a real day per
  cradle day (in parallel across NPCs).
- (b) Give cradles a declared `min_latency_ticks` (DA-1) matched to play's measured latency, and step unpaced only
  while no thought is in flight. This is a hold in all but name, so it needs the owner's explicit ruling against
  decision 7. It also belongs to the hybrid line's control arm (H1), not the shipped host.
- (c) Accept substrate-only cradles and say so in §3.4, with the memory consequence.

Record the choice as owner decision 11. Until then, §9 Q2's answer is not settled, and §3.4 shouldn't present it as
settled.

### DA-3. PR 3 builds a host without lanes, and PR 4 rewrites it
**Where:** §8 PRs 3 and 4, §4.1.
**Scenario:** PR 3 ships sessions over a real WebSocket, the host's pacing, the intent log and the B14 refusals.
PR 4 adds "the lanes, backpressure". So in PR 3, `Simulation.step` runs either on the asyncio loop thread or in an
ad-hoc thread. On the loop, a rig physics tick (about 100 ms) blocks every session's I/O, including the `hello`
deadline, which makes the deadline tests timing-dependent. Either way, PR 4 moves several things into the simulation
lane: `host_seq` assignment, the synchronous log write, and the outbound path (latest-wins slots and
`call_soon_threadsafe`). That rewrites PR 3's host, which is the tear-out A1 was about, moved one PR later. The
`busy` reply (bounded inbound queue, §4.1) is an error code in protocol v0's listed vocabulary (W-N3). If it lands in
PR 4, the vocabulary changes after PR 3 has committed the golden fixtures.
**Fix:** Move the ownership skeleton into PR 3: the simulation-lane thread, its one inbox, `host_seq`, the log
written synchronously, the bounded inbound queues with `busy`, the outbound slots, and the host as a context manager
that joins its threads. PR 4 then adds only the thinking lane and its stub (with DA-1's rule), the meters and the
crash-injection tests, and changes nothing in protocol v0. Another way: put lanes before protocol, driven in PR 3 by
an in-process test client.

## SHOULD-FIX

### DA-4. Same-tick order is stated three ways, and "deadline" survives from v0
**Where:** §2.1 ("apply this tick's records in log order"), §4.1 (`host_seq` assigned when a record is taken off the
inbox), §4.2 ("Thoughts due on the same tick apply in request-id order"), §2.1 save ("thoughts in flight with their
deadlines"), §3.1 ("thought deadlines never reach a percept"), §4.3 line 1 ("applies both at the deadline").
**Scenario:** Two thought results reach the inbox in the same tick, B before A, where A has the lower request id.
Under §4.1 B gets the lower `host_seq` and applies first in log order. Under §4.2 A applies first. PR 4's
implementer picks one and the other section is false. "Deadline" describes v0's deliberation time `d`, which
decision 7 removed. The only world-time bound left is `max_age_ticks`.
**Fix:** One rule. Simplest: the lane drains its inbox at the tick boundary, sorts thought results by request id,
then assigns `host_seq`, so log order and request-id order agree. Replace "deadline" with "the tick it applies at"
(§4.3), "request tick and age" (§2.1 save) and "thought latency" (§3.1).

### DA-5. NPC-originated intents have no stated tick or place in the order (A6, missed)
**Where:** §2.1 (step order: records, then "step agents", then physics), §4.2.
**Scenario:** In Phase 4 the agent step (2) produces substrate intents at tick T. The design doesn't say whether they
apply inside step (2) at T, which puts them after players' T intents and before physics, or as records at T+1. Either
is deterministic, but the choice decides whether a player's and an NPC's same-tick conflict always goes to the
player. That contradicts "same-tick conflicts favour whoever applies first in host order, which is arrival order"
(§5), because NPC intents never arrive. It also decides whether they're logged (they needn't be, since they're
derived) and whether they pass the world-stage validator.
**Fix:** State it: intents an agent step produces at T are queued as T+1 records, pass the same world-stage
validator, aren't logged (they're recomputed in replay), and order after that tick's logged records by actor id.
Then update §5's conflict sentence to cover NPCs.

### DA-6. The save's in-flight thoughts have no load rule (A12, partly missed)
**Where:** §2.1 ("A save is a `Simulation` checkpoint plus ... the thoughts in flight with their deadlines").
**Scenario:** A save is taken while a live model call is in flight. On load the call is gone. If the load re-requests
it, the result lands at a tick that depends on when the save was taken. If the load drops it silently, the NPC never
learns that it failed. Under decision 7 there's no deadline to store.
**Fix:** The checkpoint stores in-flight requests (request id, request tick, frozen context hash). On load, every
live request is logged as `thought_failed` with reason `save_load` at the first tick, and the NPC gets the failure as
an outcome. A stub request is recomputed, since it's pure (DA-1), so tier 2 survives a save and load. Add a
save-and-load-mid-thought test to save v0's list.

### DA-7. Caps the simulation lane enforces live in unpinned server config
**Where:** §2.2 (server config: "queue limits, rate limits, caps" in `data/server/`, not hashed), §7 (the simulation
lane checks "the per-tick limits"; "a cap on heat sources"; "the log reader validates every record"), §8 PR 1 ("caps
from `data/`").
**Scenario:** A run records `ignite` at 400 kW with the source cap at 8. Someone lowers `max_power_w` to 300 kW or
the cap to 4 in `data/server/`. The replay runs `Simulation.step`, whose world-stage validator now refuses the
intent, or the log reader refuses the record. Either way the replay diverges or fails, and the header, which doesn't
hash `data/server/`, never noticed the change. A14's split was meant to stop exactly this.
**Fix:** Any limit that can decide whether a record changes the world (parameter ranges, the heat-source cap,
per-tick limits) is world config, in `data/world/`, hashed into the header. `data/server/` keeps only what never
changes the world: rate limits, queue depths, `snapshot_hz`, timeouts. Their refusals happen in the network lane
before a record exists. PR 1's caps go in `data/world/` from the start. Add both paths to B12.

### DA-8. The log header's match rule makes every golden fixture go red on each commit; records have no size bound
**Where:** §7 intent log v0 (header: "code SHA, pymaxim, numpy and Python versions, platform"; "refuses a header it
doesn't match"; "Golden fixtures").
**Scenario:** A golden log is committed at SHA X. The next commit has SHA Y, so the reader refuses the fixture. A
numpy patch release does the same. Either the fixtures are regenerated on every commit, which makes them useless as
"old fixtures stay committed", or the match is loosened ad hoc. A thought-result record carries LLM text (memory
writes) with no bound, so one runaway result grows the log without limit (round-1 A2).
**Fix:** Split the header into **pinned** fields, which are refused on mismatch (format and protocol versions; the
scene, rig, material, world-config and roster hashes; the seed; agent state hashes), and **provenance** fields,
which are recorded and reported but never refused (code SHA, library versions, platform). The cross-machine promise
is outcome class only, so a platform difference is a report, not a refusal. Bound record and field sizes in
`data/world/` (DA-7), and refuse an oversized thought result at apply time like any invalid intent.

### DA-9. PR 1's validator needs the shape PR 3's two stages will use
**Where:** §8 PR 1 (typed, frozen params, checks "inside `damage.strike` and `HeatSource`"), §7 (schema stage in the
network lane with no `World`; world stage in the simulation lane; "the same one PR 1 adds").
**Scenario:** PR 1 writes validation inside `StructureModulator.execute`, which holds a live `World`, and mixes range
checks with region lookups. PR 3 needs the schema stage on the network thread, where touching `World` is forbidden,
so it has to split PR 1's validator. That's a rewrite of the trust boundary one PR after its tests landed.
**Fix:** PR 1 ships two functions: a pure `parse_<action>_params(raw) -> FrozenParams` (types, finiteness, ranges,
caps from `data/world/`) that never sees `World`, and a world-stage check that takes `World`. The modulator calls
both. PR 3 reuses the first in the network lane unchanged.

### DA-10. Removing `grid.time_s` leaves the SEM bridge and the snapshot with no clock (A1, SEM part unfolded)
**Where:** §1 ("`grid.time_s` ... go"), §2.1 (`World`: "no clock of its own"), `sem_env/bridge.py::RegionSensor`
(`timestamp=self._world.grid.time_s`), `world/world.py::World.snapshot` (`"time_s": grid.time_s`), §6 item 10 ("one
world clock for every ... percept timestamp").
**Scenario:** PR 2 deletes `grid.time_s`. `RegionSensor` holds only a `World`, so it has no tick to stamp a
`SensorReading` with, and `snapshot()` loses its time key. The quick fix is to pass seconds in from the caller, or
keep a float on `World`, which brings back the second clock A1 removed. The design also doesn't say what a
`SensorReading.timestamp` means. Today it is seconds since tick 0, which Maxim reads as 1970. Item 10 wants world
time with the world's epoch.
**Fix:** In PR 2, make the clock a required keyword-only collaborator of the bridge (a read-only view of
`Simulation`'s tick and `WorldConfig`), per CLAUDE.md's "push invariants into types". Define
`SensorReading.timestamp` as world Unix seconds, `(epoch_us + tick × tick_us) / 1e6`. Move the snapshot's time
fields to `StepOutputs` (`tick`, `world_time_us`), matching the protocol header. List the bridge and snapshot under
"Supersedes".

### DA-11. "The dial never changes the outcome class" is false for live models, and the rig now changes NPC timing
**Where:** §3.1 ("never changes the bits of a replay or the outcome class of a run"), §4.3 ("thinking speed in world
time depends on the dial"; "Decision 2 still holds for replays and scripted runs"), CLAUDE.md "the resolution rule".
**Scenario:** §3.1 promises the dial never changes a run's outcome class, and §4.3 says it does with live models. The
same mechanism runs through dilation. At max on a tile the effective scale is about 0.75× (§2.3) and at laptop the
dial can run at 1×, so with the same 2 s model latency a max-rig NPC gets more thought per world second than a
laptop NPC. A rig profile then changes NPC behaviour, and possibly the outcome class (did the NPC flee the fire).
That is the resolution rule, reached through timing rather than physics. "Decision 2 still holds" points at the
wrong decision (2 is "the scale is one number").
**Fix:** Scope §3.1's promise to tiers 1 and 2. In §4.3, say plainly that with live models the dial and the rig's
dilation both change deliberation per world second. Record it as a known gap in `docs/architecture.md`, with numbers
from H6 once measured. Cross-tier tests with NPCs use the stub (tier 2), so the resolution rule stays gated where it
can be. Fix the decision reference.

### DA-12. "Push back on Maxim": "never work around it" collides with the marked-band-aid exemption, and the rule has no end state
**Where:** CLAUDE.md "Working" → "Push back on Maxim" ("Never work around it in this repo"), CLAUDE.md "Fix root
causes" (the `TEMPORARY(phaseN)` exemption), "Keep Maxim untouched", the ledger rule.
**Scenario:**
- Maxim's four-lens review declines item 10 (it keeps §(g)), or takes two releases to land it. The game still needs
  NPCs in Phase 4. "Never work around it" forbids even a marked, scheduled `TEMPORARY(phase4)` adapter that CLAUDE.md
  allows elsewhere, so Phase 4 stalls with no sanctioned path. The rule says how to push back, but not what happens
  when Maxim answers "no". The two possible failures are an endless re-proposal, or a quiet local fork.
- Ledger: CLAUDE.md says "Game runs never go on Maxim's results ledger". The roadmap says "Only pre-registered
  experiments go on it", and the 1.5 draft puts pre-registered experiments run in the game on it. The wording
  disagrees just as this rule makes game-sourced experiments routine.

There's no contradiction with "Keep Maxim untouched": both route through Maxim's process.
**Fix:**
- Add an end state. A declined proposal is recorded on its Phase 3 item with Maxim's reason, and the game's design
  adapts by its own review. Re-proposing needs new evidence.
- Change "never work around it" to "never work around it silently". A workaround while a proposal is open is allowed
  only as a `TEMPORARY(phaseN)` marker that cites the Phase 3 item.
- Align CLAUDE.md's ledger sentence with the roadmap: "Game runs never go on Maxim's results ledger; only
  experiments pre-registered through Maxim's process do, wherever they run".

### DA-13. B15's check would fail today, and half of it can't be mechanized as written
**Where:** `docs/standards_backlog.md::B15`, CLAUDE.md "Push back" ("Each proposal is an item under Phase 3 in
`docs/roadmap.md`"), §8 "Supersedes" ("When PR 2 lands ... the new Phase 3 items"), the hybrid draft ("Its
prerequisites are on Overdrive's Phase 3 list already").
**Scenario:**
- The rule is in force at 02338ef. `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md` exists, but `docs/roadmap.md`'s
  Phase 3 has only items 1 to 9, and none cites the draft. B15's first check would be red today.
- The hybrid draft's claim that its prerequisites are "on Overdrive's Phase 3 list already" is false: they're in the
  design, not the roadmap.
- "Supersedes" defers the roadmap update to PR 2, so the rule stays violated until code lands.
- B15's second check ("names the Maxim decision it argues against (if any)") can't be linted, because a lint can't
  tell an item that should name a decision from one that has none. "A lint can check both" overclaims.
- "Lands with: open" gives it no scheduled moment.
- The guard is honest that the substance (noticing a wrong Maxim decision) is review-only. But the Bio-faithful lens
  triggers only on NPC-facing diffs and design reviews, so evidence from, say, a performance diff isn't asked.
**Fix:**
- Put Phase 3 items 10 to 18 (and the #1361 prerequisite) in `docs/roadmap.md` when the design is accepted, not when
  PR 2 lands. Each item cites its draft and its Maxim decision.
- Reword B15: "every draft is cited by a Phase 3 item; every Phase 3 item carries a `Argues against:` field (a named
  decision or `none`) and, once filed, a `Maxim:` issue link". A lint can check that a field is present.
- Give B15 a landing moment, for example the PR that adds items 10 to 18.
- Add the pushback question to the always-on Architecture lens as well.

### DA-14. Item 10 pushes back on one row of #1361 §(g); the reflex and pain rows conflict with tier 1 too
**Where:** §6 items 10, 11, 15. Maxim `docs/plans/experience_clock_decay.md` §(g) ("What stays wall-clock on
purpose": "PainBus refractory, reflex cooldowns", for "motor/IO rate limits; hardware safety", and the loop
scheduling row).
**Scenario:** Item 10 argues against §(g)'s SCN row only. §(g) also keeps reflex cooldowns and the PainBus refractory
period on the wall clock by design. In the game those decide when an NPC can flinch again. On the wall clock they
make reflexes depend on the dial and the rig (Bio-11, DA-11), and tripwire §4.4 would fire inside `Simulation.step`.
Items 11 ("every DN timer on the injected clock") and 15 ("an injected clock across agent code") would collide with
§(g) in Maxim's review without naming it. That is exactly the omission the new rule forbids ("name the decision
you're arguing against").
**Fix:** Have item 10 (or 11 and 15) name every §(g) row the game needs moved: SCN, reflex cooldowns, PainBus
refractory. Offer a split Maxim can accept: wall clock for a physical body's hardware safety, world clock for a
simulated body, chosen by the body.

### DA-15. "Supersedes" misses lines that already contradict the design (A11, partly missed)
**Where:** §8 "Supersedes". Not listed yet:
- **CLAUDE.md:**
  - "Determinism": "one seeded `numpy.random.Generator` owned by `World`. Time comes from `World.advance`". The design
    gives both to `Simulation`, with per-agent RNGs derived from the seed (item 15).
  - "Layout": `world.py` "(turn loop ...)". New entries are also needed for the `Simulation` package, `server/`,
    `data/world/` and `data/server/`.
  - "Performance": "turn time and snapshot size".
  - "The client is untrusted input": "the per-launch token". There are now host and guest tokens.
- **`docs/code_review.md`** (not listed at all):
  - Performance lens: "the turn loop", "per turn".
  - Wire integrity, Lifecycle row: "turn start and end". It needs join, leave, tick and pause instead.
  - Executor: `World.advance` as the entry point. It becomes `Simulation.step`.
- **`docs/architecture.md`:**
  - the diagram ("fixed turn"; "Maxim agents (AgentPool)", which X4 and item 12 say isn't the path);
  - "interpolation between turns";
  - "Actions change cells; only `World.advance` moves time" in the SEM section (only CLAUDE.md's copy is listed);
  - "far less than a turn of physics";
  - the cost line;
  - the known gaps. They must be **re-measured**, not relabelled: they were measured at 4, 16 and 64 substeps per
    6 s, and the new counts are 12, 24 and 72.
- **`docs/roadmap.md`:**
  - Phase 1 "Save format v0: the world grid plus the scene spec". §2.1 makes it a checkpoint plus the log header.
  - Phase 1 has no line for sessions, tokens or co-op.
  - Phase 3's header "the 1.4 line items" and its exit, which covers only Exp 64. Items 10 to 18 serve Phase 4 and a
    proposed 1.5 line.
  - Phase 4's "dialogue screen and turn order", with what replaces it: real-time dialogue, the host may pause, the
    NPC keeps acting (H5).
  - Phase 4's "Movement runs in substrate-primary mode", now deferred to item 17.
- **`docs/standards_backlog.md`:**
  - B14's "since `server/` is exempt from the determinism scan". §4.4 moves the host into the scanned package.
  - B14's single token.
  - B12 needs `data/world/` and `data/server/`.
  - The "Lands with: Phase 1 step 2/3" cells. Step 2 is now four PRs; name them.
- **Code:** the SEM bridge timestamp and `snapshot()["time_s"]` (DA-10); the determinism scan's `server/` exemption in
  `tests/test_determinism.py`.

**Fix:** Add each line to "Supersedes" with what it becomes. Split the list: doc changes that state the accepted
design (roadmap, CLAUDE.md, the review charter) land on acceptance; code-truth changes land with the PR that makes
them true.

### DA-16. Phase 4 hangs on several Maxim items with no stated minimum and no fallback
**Where:** §4.4 ("Real Maxim agents join tier 1 only when §6's deterministic-agent items land"), §4.3 (needs item
16), §3.2 ("NPCs must not run against the world clock with their SCN on host time" until item 10), §6 items 10 to 18,
roadmap Phase 4.
**Scenario:** The design makes Phase 4's NPCs depend on items 10, 11, 12, 15, 16 and #1361, each through Maxim's
own review, which can decline or reshape any of them (DA-12). Nothing says which are hard prerequisites for the first
NPC on the tile, which only gate tier-1 determinism, and which are the 1.5 line's research. A decline of item 16
(generate vs apply) leaves §4.3's whole thinking-lane contract with nothing to call.
**Fix:** Add a dependency table to §6: for each item, which Phase 4 capability it blocks (NPCs at all, or NPCs in
tier 1, or the hybrid experiments), and what the game does if Maxim declines it. Mirror that in the roadmap's
Phase 4 entry.

## NIT

- **DA-17.** §1 says "Phase 3 grows from 4 items to 8 (§6)". §6 now has items 10 to 18, which is 9, plus the #1361
  prerequisite.
- **DA-18.** `README.md` in this directory is stale after decision 7. It says §4.3 folds A9 and the others as "a held
  state that serves control, a budget", it lists Q1 to Q4 as "Not settled", and it says the delta round waits for
  answers that now exist. Update it to point at decisions 7 to 10.
- **DA-19.** v1 dropped v0's "Deliberately not now" list: LAN play, NAT traversal, client prediction and rollback,
  accounts. With a `127.0.0.1` listener, co-op v0 means clients on the same machine (or an operator's own tunnel).
  Say so in §5, and restore the list, so PR 3 doesn't grow a LAN bind.
- **DA-20.** The hybrid draft's H1 control arm ("the world paused for each thought") should name where it runs: an
  experiment harness that calls `Simulation.step` only after a result is in, never `WorldHost`. That way decision 7
  stays true of the shipped host, and the draft's open question about how H1 is reported has a structural answer.
- **DA-21.** Item 17 says the movement-on-substrate, speech-on-LLM split is to be decided in a Maxim plan, but §4.3
  already settles the game's side: the NPC acts on substrate while it thinks. Item 11 also mixes id schemes ("BL-2,
  A3, A4"), where the plan's A3 and A4 are BL-4 and BL-5. Use the BL ids.
- **DA-22.** `substeps_per_physics_step` makes a rig's substep length depend on the world's `physics_every_ticks`. A
  world YAML with a 1 s period silently doubles every rig's substep. State the coupling, and have the world-config
  loader refuse a period whose substep at the coarsest rig exceeds today's precision.
- **DA-23.** §2.1 seeds the RNG "from the log header", but the log arrives in PR 3 and the `Simulation` in PR 2. Make
  the seed a required constructor argument in PR 2 that the log header later supplies.
- **DA-24.** The "stale-refusal rate" meter needs a distinct refusal code ("overtaken", in the listed vocabulary)
  and a definition the validator can compute. Otherwise "stale" is indistinguishable from any other invalid intent.

## What I checked and found sound

- **Decision 7's core mechanism.** Apply on the first tick after arrival, with the applied tick logged, keeps tier-1
  replays bit-identical without a hold. Abandonment by `max_age_ticks`, decided only by the simulation lane, with the
  wall-time timeout freeing only a worker, gives one owner for the failure. Fresh validation at apply time, with
  refusals returned as outcomes, is the right reconciliation. The removal of the `held` field and of "held world"
  from §3.3 and §7 is complete: no stale references to holding remain in the design's mechanism text, only the
  "deadline" wording (DA-4).
- **The per-NPC hybrid meters (§4.3)** are the right instruments for "needing to wait is a finding". They line up
  with H2's measures.
- **§6 routing.** Every Maxim change goes to Maxim's process, none is patched here, and item 10 names the decision
  (#1361 §(g), confirmed at `experience_clock_decay.md` §(g)) it argues against. The revive trigger in item 17
  matches the hybrid plan's banner ("a second robot body physically exists") and M76.
- **"Push back on Maxim"** doesn't contradict "Keep Maxim untouched": both route changes through Maxim's process. Its
  guard passes `lint_standards.py::check_guards` honestly, as a document plus a backlog row, and counts as
  review-held.
- **The hybrid draft** keeps itself off the ledger except for pre-registered experiments. It has a kill criterion and
  an honest null, and it marks the paused arm as a control only.
- **PR 1 first, on its own,** is right: it closes a live hole on a path NPCs use now, independent of everything else.
  **PR 2 before PR 3** is buildable: `Simulation`, the integer clock and the cost fix need no transport.
- **The numbers agree across sections:** 864,000 ticks a day at 100,000 µs; substep counts 1, 2 and 6 per 0.5 s step
  (12, 24 and 72 per 6 s, as round 1 measured); the cost table against §3.4's "24× isn't reachable on a rig tile";
  the review counts (22, 61, 24) against `README.md`.
- **§5 co-op** (token-bound roles, no promotion, host-leave pause as a logged decision, `HostOnly` never pending) is
  consistent with §4.2's ordering and §7's closed schemas.
