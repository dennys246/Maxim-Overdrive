# Delta round 2: SEM stimuli v3, Determinism, replay and Performance lens

Design: `docs/design/sem_stimuli.md` v3 at `77e24bb`, against my delta-1 report
(`reviews/sem_stimuli/delta1/determinism_performance.md`) and the author's `delta1/fold.md`. I reran the author's
`v3/plant.py` and it reproduces: one ulp first moves a node at tick 152 and 120 and never at zero flux; 10⁻¹² moves one
at tick 0; rest 32.38 °C; join 1,060 s. I wrote two new scripts, `scratch_determinism_performance/refresh_cap.py` and
`refresh_cap2.py`. They are pure Python and simulate §8's capped refresh schedule: 10 bodies, 58 points, one emitter,
0.1 m declared distance, 4 m/s running.

**A correction of my own delta-1 claim comes first.** Under "Checked, no finding" I wrote that the overlap on/off
replay gate "can fail: a leak changes world state and the T+1 frames". For v2's gate that was false. v2's gate only
replayed a log. Replay runs no agents, so step 5 is empty and overlap on and off run the same code. Concurrency F1 was
right. v3's gate is different, and it is settled below (DP3-N1): it can fail.

## Status of delta-1 findings (open or new)

| Id | Status | Reason (read from v3) |
|---|---|---|
| DP-S5 | fixed | §8 has the moving-crowd row ("visibility every tick … ~365–450 ms") and an absolute target. The counter thresholds stay deferred, as accepted in delta 1. Trigger: the irradiance-law PR's B5 row. `standards_backlog.md` B5 doesn't carry them yet, which is correct for a deferral |
| DP2-B1 | fixed | The basis is stated once (§8). The 100-NPC forecast is corrected: 10 × (110–150 ms) + 1.4 s = 2.5–2.9 s, which I checked. D12 is provisional and will be re-ruled on a measured outcome. The failure paths are named (§8, §10, §11.3). I checked the arithmetic: c = 73–90 ms ÷ 1,160 = 63–78 µs; 10·116·c = 73–90 ms; 10·290·c = 183–225 ms; ⌈580/116⌉ = 5 ticks; ⌈580/290⌉ = 2. **The capped schedule it introduces breaks batch invariance (DP3-B1), and its staleness bound is false as worded (DP3-S1)** |
| DP2-S1 | fixed | §8 now has rows for substeps, contact (unmeasured), the body step (unmeasured, critical path) and the emitter multiplier. §6.1 supersedes §6.6's levers by name, and the barrier under D5 (c) is restated. **I accept Concurrency F2's proposed deferral** of the numbers and of whether 20× is a target near a fire. Reason: the body step can't be measured before M4. Trigger: M4's answer or the first body-step measurement, whichever comes first. The substep row's basis is off: DP3-N4 |
| DP2-S2 | fixed | §7.2 solves contact per connected component in canonical order, gives each point its own substeps, never lets a cluster span bodies, and extends the lint to `scipy.linalg` and `scipy.sparse.linalg`. T11 plants all three. Two neighbours of the same class remain: the shared refresh cap (DP3-B1) and "component" defined by object (DP3-S3) |
| DP2-S3 | fixed | §5's save holds all carried `core/body` state, including each pair's last refresh tick and reference pose. The controller is memoryless (§2.3 and §5). The save-load test and the omitted-pose plant are both in |
| DP2-S4 | fixed | §5: lanes hash dtype, shape and little-endian bytes, length-prefixed; the canonicaliser is for the header only |
| DP2-N1 | fixed | §5: the chain finds the first bad *interval*; the first bad tick needs a reference run |
| DP2-N2 | fixed | §4.2: `local_id` is assigned after sorting by (source id, site) |
| DP2-N3 | fixed | §6.3 T11: "B reaches A only through world state" |
| DP2-N4 | fixed | §8: ~140 ms per world second at 10 NPCs, absolute, with the ratio dropped. Writing it into the B5 row rides DP-S5's trigger |

Counts: 10 fixed, 0 deferred, 0 rejected, 0 open. One proposed deferral ruled: Concurrency F2's numbers, accepted.

## Settling the lane-overlap gate (§4.1), against v3's text

v3's gate runs live: stub workers behind the real channel, two seeded wall-delay schedules, overlap on and off, then a
replay with `maxim` blocked. The planted red case is "a merge applying a `step_output` during step 6".

- **A replay-only gate cannot fail.** Concurrency F1 is right about v2. My delta-1 note was wrong.
- **v3's gate can fail, and the leg that guarantees it is the replay.** Take F1's scenario. The plant applies a
  posture intent on arrival instead of at T+1 step 1. With overlap **off**, step 5 gathers every reply before step 6
  starts. So the planted merge lands before physics at T, every time, and physics debits the flame's share against a
  pose that replay (posture applied at T+1) never sees. The live digest differs from the replay digest, so the gate
  goes red, with no dependence on wall time.
- **The on/off comparison alone is wall-dependent.** With overlap on, the plant changes state only if the reply
  arrives while step 6 is still running. On a fast host with a small test scene, a seeded delay can land after step 6
  ends, and that run stays green. So the "two delay schedules" don't make the plant red. The replay leg does. The
  plant must also emit an output that step 6 reads (posture or breath, not an empty `StepOutput`). See DP3-N1 for the
  wording fix.

## New findings

### DP3-B1 (BLOCKER). The shared refresh cap makes A's visibility depend on B's motion and presence, against §7.2's contract and T11

`sem_stimuli.md::8` ("Each tick the law refreshes at most **K point–emitter pairs** … oldest first"; "A shared cap
holds cost"), against `::7.2` ("Batch invariance is contract … clusters never span bodies"), `::6.3` T11 ("B's
state, B joining out of sight: A bit-identical; B reaches A only through world state") and `::3.1` (the overdraft is
"never a prorated flux, which would make A's flux depend on B").

K is one cap shared by every body. When the due pairs exceed K, the cap allocates refreshes, so B's pairs compete
with A's. Which tick A's pair refreshes at then depends on how many other pairs are due, and that depends on B's
motion and membership. This is the same class as a cross-body cluster. It just lives in the scheduler instead of the
kernel. It is deterministic, since B's motion is logged, but it violates the invariance contract. The design also
already rejected this pattern once, for the overdraft (§3.1).

**Measured** (`refresh_cap2.py`; A is the last body, stationary):

| Scenario | A's refresh sequence unchanged? |
|---|---|
| K = 116, the other 9 run instead of standing | **no** |
| K = 90, a stationary B joins at tick 13, out of sight | **no** |
| K = 90, a running B joins at tick 13 | **no** |
| per-body cap k = 12, the other 9 run | yes |
| per-body cap k = 12, a running B joins | yes |

A refresh recomputes visibility against the emitter's current quadrature points. In a fire those points move every
physics step, so a different refresh tick gives A different flux, and different tissue bits from then on.

**Failure scenario.** In a burning market, NPC A stands still by a stall. Nine others start fleeing. A's visibility
refreshes come at different ticks, so A's skin temperatures change bit-wise and time to pain moves, with no physical
path from the runners to A. T11, written as v3 has it, goes red. The cheap response is to narrow T11, which is the
loosened-test band-aid. **D12's outcome measurement is also wrong under a shared cap.** A body stepping from behind a
wall gets a different staleness depending on how many others are moving. So the number D12 is re-ruled on holds only
for the crowd it was measured with. It would have to be measured at the worst-case crowd, and the design doesn't say
so.

**Fix (verified in `refresh_cap*.py`).** Cap per body and per emitter: each tick, a body refreshes at most k of its
own pairs per emitter, oldest first by its own state. Then:
- the cost bound is 10·N·E·k·c, still bounded;
- staleness for a body is ⌈58/k⌉ ticks, a function of that body's state alone;
- the D12 measurement becomes a one-body test.

At k = 12 and N = 10, all running, the simulation gives a 5-tick worst case, the same as the shared cap at K = 116.
At k = 29 it matches K = 290.

**What it costs, said plainly.** A per-body cap loses pooling. When only two of ten NPCs run, a shared cap lets them
refresh every tick on the stationary bodies' slack. A per-body cap doesn't. The worst case and the cost bound are
unchanged. Only the favourable case gets worse.

Add a T11 plant: a shared cap, red when B runs. D12 then goes back to the owner with this trade-off.

### DP3-S1 (SHOULD-FIX). As worded, the priority starves stationary pairs, so "no pair is staler than ⌈P/K⌉ ticks" is false

`sem_stimuli.md::8` ("oldest first among pairs whose body moved past the declared distance, then oldest overall;
each pair is also due once per physics step").

The literal reading serves moved pairs strictly before physics-step-due pairs. A runner's pairs are due again every
tick, because 0.4 m per tick exceeds 0.1 m. So whenever the moved pairs alone fill K, step-due pairs never get a slot.

**Measured** (`refresh_cap.py`, 5 running and 5 stationary, K = 116):

| Rule | Runner staleness | Stationary staleness |
|---|---|---|
| moved first (literal) | 2 ticks | **100 of 100 ticks**: never refreshed |
| pure oldest first over all due pairs | 4 ticks | 6 ticks |

**Failure scenario.** A stationary NPC beside a wall that burns through keeps its pre-breach visibility for as long
as others run nearby. Its flux stays at zero while the field behind the wall is at 20 kW/m².

**Fix (verified).** Rank all due pairs, moved or step-due, by one key: the last refresh tick, then the body's sort
position, then the point id, then the emitter key. That is a total order from saved state, so a save and load
reproduces it. Then state the bound for that rule. Under DP3-B1's per-body cap the same rule applies within each
body.

### DP3-S2 (SHOULD-FIX). K doesn't scale with emitters, so a second flame breaks "due once per physics step" and the measured bound

`sem_stimuli.md::8` ("All rows but skin scale with emitters"; K is a header truth constant, §5; the worked cases are
at "one emitter").

Stationary demand is 58 · N · E pairs per physics step, which is 116·E per tick at N = 10.
- **At E = 2 and K = 116**, demand is 232 per tick. Every pair, stationary or not, is then refreshed every 10 ticks at
  best, not every 5. The schedule's own "due once per physics step" can't be honoured. The cost row stays flat, which
  is what hides it.
- **K = 116 is also exactly the one-emitter floor.** With all ten running, the simulation gives a 5-tick interval:
  once per physics step, the v2 behaviour the motion trigger was added to fix (Physics S4). At K = 116 the motion
  trigger buys nothing in the worst case. §8 gives the "0.5 s, about 2 m" honestly, but it doesn't say this.

**Failure scenario.** A second stall ignites. Every NPC's visibility staleness doubles to 1 s. The pain onset D12 was
re-ruled on, measured at one emitter, no longer holds, and no gate notices, because the counter gate checks cost, not
staleness.

**Fix (arithmetic, not run).**
- Make the cap per emitter, as DP3-B1's k per body-emitter does.
- Measure D12's outcome at the scene's maximum emitter count.
- Record the declared maximum in the header.
- Say in §8 that K = 116·E is the floor at which the motion trigger is inert.

### DP3-S3 (SHOULD-FIX). "Connected component (one object and its skins)" turns a floor into one global system

`sem_stimuli.md::7.2` ("contact solves per connected component (one object and its skins)"); `::2.3` ("one implicit
system per touched object").

If feet or seated regions are skin points touching the floor, a bench or a long pipe, then every NPC touching that
object is in one system. Contact is solved against the solid's last published state (§7.1), so two patches with
separate object-side sub-meshes share no unknowns. Defining the component by object identity still makes A's solve
include B's patch. A's bits then depend on B whenever the solver has any whole-system quantity: an iteration count, a
residual norm, a shared substep dt, or a pivot order.

**Failure scenario.** B walks onto the same floor slab 20 m away, out of sight. A's foot-contact solve now iterates
until the residual of a larger system falls below tolerance. A's skin bits change, and T11 goes red, or a test
without a shared floor never notices.

**Uncertain:** I haven't confirmed that v1's body sizes have floor contact. The rule is safe either way.

**Fix.** Define a component as the patches that share object-side sub-mesh nodes within the tick, not the object.
Give each component its own termination and substep decisions. Add a T11 plant: B on the same floor object, with a
shared residual.

### DP3-N1 (NIT). Write the overlap gate's delays as deterministic release points and its plant as "apply on arrival"

`sem_stimuli.md::4.1`.

"Seeded wall-delay schedules" means sleeps or wall timing in a test. CLAUDE.md's testing rule bans both, and as shown
above they don't make the on/off leg reliable.

**Fix.**
- The stub holds each reply until a host hook fires, for example "step 6 has started" or "step 6 has finished". That
  gives two deterministic schedules with no sleep.
- Phrase the plant as "the merge applies a `step_output` on arrival instead of at step 7", with an output that step 6
  reads.
- Say that the replay leg is the one that must go red.

### DP3-N2 (NIT). Events have no digest lane, although lanes are frozen contract

`sem_stimuli.md::0` (the digest lanes are frozen), `::5` (row lanes over `(npc_key, site, value)`; `BoundFrame`
values and receipts per NPC), `::4.2` (`events` in both frames).

No lane covers `events`, yet §5 promises "Events get a plant with their first producer". With no lane, that plant has
nothing to go red on. **Fix:** name the lane now, one per NPC over the sorted event tuple, and reserve it in 5a's log.

### DP3-N3 (NIT). The event byte budget must be a header constant, not read from the socket

`sem_stimuli.md::4.3` ("a byte budget below the socket buffer").

If the budget is derived from `SO_SNDBUF` at runtime, coalescing depends on the OS and the sysctl. The coalescing
counters are saved state (§5), so a save loaded on another host coalesces differently. **Fix:** make the budget a
header truth constant, and refuse to start when it isn't below the measured socket buffer.

### DP3-N4 (NIT). The substep row is on heavy-load basis inside a light-load table

`sem_stimuli.md::8` ("~+30 ms at four substeps").

That figure is mine from delta 1, and it was at heavy load: 1 ms per substep at 10 NPCs × 3 extra × 10 ticks. On the
table's stated basis it is about 11–14 ms, dividing by the Executor's 2.2–2.7×. It errs high, so it's harmless, but it
is a second basis. Relabel it, or divide it.

### DP3-N5 (NIT). Sum flux over emitters in a canonical order

`sem_stimuli.md::7.1` ("a multi-writer `radiant_emitters` table"), `::7.2` ("emitters append").

Float addition isn't associative. If a point's flux is summed in table order, and that order is append order, then
two things change bits with no physical cause:
- a load that rebuilds the table in a different order;
- a reordering of writers.

**Fix:** sort by a stable emitter key before summing; the save-load test covers it.

## Checked, no finding

- **Determinism of the schedule itself:** age, reference pose and the distance test all come from saved, logged
  state. With DP3-S1's total order it reruns bit-identically.
- **The digest's cost** at 2.9 µs × 10 × 10 ≈ 0.3 ms per world second fits inside the delivery row.
- **T9 under D14:** frames run every tick whatever the divisor, so byte-identical frames across divisors still hold.
- **The plant size** (10⁻¹²) reproduces on L3's column.

## Counts

Delta-1 findings: 10 fixed, 0 deferred, 0 rejected, 0 open. One proposed deferral (Concurrency F2's numbers) accepted.

New: 1 BLOCKER (DP3-B1), 3 SHOULD-FIX (DP3-S1–S3), 5 NIT (DP3-N1–N5). One correction of my own delta-1 note
(overlap gate).
