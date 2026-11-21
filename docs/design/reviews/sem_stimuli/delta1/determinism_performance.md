# Delta round 1: SEM stimuli v2, Determinism, replay and Performance lens

Design: `docs/design/sem_stimuli.md` v2 at `3e97ac9`, against my round-1 report
(`docs/design/reviews/sem_stimuli/determinism_performance.md`), `fold.md`, L3 (`3_world_side.md`), `boundaries.md`
§6.3, `npcs_and_sem.md` §6.3 and §6.6, `realtime_lanes_coop.md` §7, `architecture.md` Known gaps and B5. One new
measurement, `digest_form.py` in this directory (fire-research venv, load 3.1–5.4).

**A correction of my own round-1 advice comes first.** DP-N2 said a chained hash "still finds the first bad tick by
bisection". That is false. A chain stored every N ticks localises a divergence to an N-tick window, not to a tick:
inside the window the replayer has no reference values to compare against. v2 copied my sentence into §5. See
DP2-N1.

## Status of round-1 findings

| Id | Status | Reason |
|---|---|---|
| DP-B1 | fixed | Ids by sorted name in the header, the handshake only checks (§4.2); body instances and bindings in `join` (§5); under D5 (c) every body is built and digested every tick, membership from logged records (§4.5), so the step schedule no longer enters the digest |
| DP-B2 | fixed | Batch invariance is contract, with a lint and a T11 plant (§7.2, §6.3); fork-join stays serial until the plant exists (§8 item 3). The contract's reach is too narrow for v2's new kernels: DP2-S2 |
| DP-S1 | fixed | One frame per tick (§4.2), so `offset_us` orders correctly; `StimulusEvent` defined, `caused_by` is data, not a key. Residual tie-break: DP2-N2 |
| DP-S2 | fixed | The tick is pinned (§4.1). **I accept the author's rejection of my reorder.** Under a zero-order hold, step 3 integrates the interval (T−1, T], during which the fields from the physics step at T−5 were in force; my order (physics before tissue) would have integrated that interval against fields that did not yet exist. The author's order is the more correct one, keeps D10 and allows the lane overlap. `fields_sequence` plus `tick` identify the input, since tissue at T is saved state |
| DP-S3 | fixed | Flux, visibility and contact live in `core/body/irradiance.py`, run every tick for every body, independent of cadence (§7.1); staleness measured against every-tick refresh first (§8 item 2) |
| DP-S4 | fixed | Refresh and clustering bounds, the tissue tolerance and the cutoff floors are header truth constants (§5); staggering by index is gone (§8); the items are retitled as value-changing law parameters |
| DP-S5 | open | The totals table, the budget, the counter gate and the p99 meter are in §8. Still missing is the worst case I asked for, a crowd moving near the fire. The table costs stationary bodies, and the 100-NPC forecast is stale. See DP2-B1. Counter thresholds may wait for the irradiance-law PR (trigger: that PR's B5 row) |
| DP-S6 | fixed | Reductions in the core in fixed order, digested; canonical values, not codec bytes; deltas ruled out; codec goldens (§3.2, §5) |
| DP-S7 | fixed | T9's worker half compares writes and pain events at 1×, 20× and two seeded delay schedules, strict red until M6 and M8; §5 states the tier-2 caveat |
| DP-S8 | deferred | v2 rules bodies ledger-only (ANALOG, §3.1) and defines T11's perturbation set. I accept deferring the non-conservation figure. **Trigger:** the irradiance-law PR records it as a Known gap with a number. **Condition:** where body absorption overdraws the flame's unreceived share, it may not be resolved by prorating or clamping each body's flux, because that makes A's flux depend on B and on the summation order. Book the overdraft as a ledger residual instead |
| DP-N1 | fixed | The reuse cache is gone from §8 |
| DP-N2 | fixed | A chain at log v0's interval, which is what I asked for. My advice that it supports per-tick bisection was wrong (DP2-N1) |
| DP-N3 | fixed | §2.3: floored to integer µs once |
| DP-N4 | fixed | §5: length-prefixed |
| DP-N5 | fixed | §4.3: `agent_failed(protocol)` in tick T's merge; §4.5: inert NPCs are built and digested, not sent |

Counts: 13 fixed, 1 deferred, 0 rejected, 1 open.

## The budget: is it plausible?

**The arithmetic in v2 §8 is internally consistent, but its basis is mixed, and it costs the wrong case.** The
10-NPC row sums correctly (50 + 65 + 15 = 130 ms; 50 + 165 + 30 = 245 ms), and 10% of 1.4 s is 140 ms.
On a like-for-like basis:

- **Load.** Row 1 (~50 ms) is at L3's heavy load (5.6–7.8). The visibility row's lower bound is divided by the
  Executor's 2.2–2.7× factor and its upper bound isn't. The denominator, 1.4 s per world second, is the heat law
  *lightly loaded* (`architecture.md` Known gaps: 0.7 s CPU per `advance(0.5)` at 1.92×10⁶ cells). The 2.2–2.7×
  factor was measured on the skin kernel only (Executor's rerun); applying it to ray sampling is an extrapolation.
- **Points.** The heading says 58 points, but the numbers are L3's 48. Skin at 10 ms plus quadrature at 38–49 ms
  per world second (4.9 ms per evaluation × 10 ticks, or the 100-NPC per-NPC rate) gives 48–59 ms, which is "~50" at
  48 points. The visibility row's 165 ms is 82 × 2, also at 48 points. At 58 points both scale by 1.21.

Recomputed, lightly loaded, at 58 points, 0.1 m, one flame, **stationary bodies**:

| | 10 NPCs, per world second |
|---|---|
| skin (one substep per tick) and quadrature every tick | ~21–32 ms |
| per-point visibility, refreshed once per physics step | ~73–90 ms |
| delivery | ~15–30 ms |
| **total** | **~110–150 ms against 140** |

So, for stationary NPCs, the owner's D12 is at the target, not 1.75× over it. **For moving NPCs the budget is not
plausible without clustering.** That is the case the budget exists for, and DP2-B1 shows why. The worker's own body
step is not in either figure (DP2-S1).

---

## New findings

### DP2-B1 (BLOCKER). §8 costs stationary bodies, but its own refresh rule makes a moving body refresh visibility up to every tick: 2.5–5× the visibility row in the budget's own case

`sem_stimuli.md::8` (the table; "Visibility refreshes each physics step and whenever a body's sites move more than
a declared distance"; "100 NPCs at a fire forecasts 1.7–2.1 wall seconds per world second"); `::10` D11, D12.

The visibility row is "per physics step", so it counts one refresh per 0.5 s. A body walking at about 1.4 m/s
(**M**) moves 0.14 m per tick and 0.7 m per physics step. The motion trigger exists because 0.7 m of staleness is the
physics review's S4 failure (stepping out from behind a wall into 20 kW/m², with pain due at 1.1 s). So the declared
distance must be well under 0.7 m:

- at 0.14 m or less, a walking body refreshes every tick, which is 5× the row;
- at 0.35 m, it refreshes every 2–3 ticks, about 2×.

A crowd near a fire flees, and fleeing is faster than walking.

**Failure scenario.** Ten NPCs flee a burning stall at a running pace, with the declared distance at 0.1 m. Each
refreshes visibility every tick: 10 refreshes per world second, not 2. Lightly loaded at 58 points, visibility is
~365–450 ms per world second, and the total is ~0.4–0.5 s, or 3–3.5× the 140 ms target. With two flames it is about
double that. The owner reconfirmed D11 and D12 at "~130–245 ms", which is the stationary figure.

**The 100-NPC forecast is stale.** "1.7–2.1 wall seconds per world second" is my round-1 figure, computed for the
shared 9-ray occlusion that D11 replaced. v2's own 100-NPC column sums to 1.3–2.4 s of stimuli. With physics at 1.4 s,
that is **2.7–3.8 wall seconds per world second for stationary bodies**, and more when they move.

**Fix.**
- Add a moving-crowd row: refreshes per world second as a function of the declared distance at walking and running
  speeds, per emitter.
- State the table's basis in one place: load, 58 points, 0.1 m tier (the ray cost scales as 1/dx, Physics N1), one
  emitter.
- Correct the 100-NPC forecast.
- Put D12 back to the owner with these figures and a **named failure path**: what happens if measured clustering
  doesn't bring the moving case under target. The candidates are a coarser visibility law with a stated error,
  fewer NPCs, or dilation accepted at 10 NPCs. §11.3 names the risk, but no decision covers it. The fix costs a
  table row and a decision, no code. It is a BLOCKER because an owner ruling rests on a figure that is wrong for the
  case it rules on.

### DP2-S1 (SHOULD-FIX). Four per-tick costs that v2 creates are not in the budget, and the two barrier levers it removes are not superseded by name

`sem_stimuli.md::8`, `::2.4` (error-controlled substeps, implicit contact), `::4.1` step 5, `::0` (D5 (c)), against
`npcs_and_sem.md` §6.6 ("Its cost").

1. **Error-controlled substeps.** Row 1 assumes one substep per tick. §2.4 says one isn't enough exactly near the fire
   (1.25 K basal at 80 kW/m²; contact 20% late). Skin costs about 1 ms per substep at 10 NPCs (L3 §5), so four
   substeps per tick near the fire add ~30 ms at heavy load.
2. **The implicit contact system** over object surface nodes and skin: not costed at all.
3. **The worker's body step every tick.** Under D5 (c) every NPC parks every tick, and the tick joins at step 7. The
   tick's wall time therefore includes the slowest worker's Maxim body step, which nobody has measured (it waits on
   M16). Only the transport round trip (50–200 µs) is in the delivery row.
4. **Emitters.** Every row except skin is per emitter, and the table says "one flame".

`npcs_and_sem.md` §6.6 sets the barrier's levers: "only agents due this tick (by rate divisor) get a round trip;
frames go as deltas". v2 removes both: every body parks each tick, and deltas are ruled out. §6.1 supersedes other
sections by name, but not this one.

**Failure scenario.** At the 20× fast-forward that T9 and D3 assume, 10 NPCs park 2,000 times per wall second. That is
0.1–0.4 s per wall second of transport alone, before any body step, with no lever left to pull.

**Fix.**
- Add rows 1–4 to §8: substeps as a counter with a measured distribution near the fire, contact as unmeasured, and
  the worker body step as unmeasured and on the critical path.
- Supersede §6.6's levers by name, and restate the barrier cost under D5 (c).
- Say whether 20× is still a target when NPCs are near a fire.

### DP2-S2 (SHOULD-FIX). Batch invariance is banned for matrix-vector calls only, but v2's new kernels have three more ways to couple bodies through the batch

`sem_stimuli.md::7.2` ("Batch invariance is contract … A lint bans BLAS matrix-vector calls and `einsum`"), `::2.4`
(contact "one implicit system"; "error-controlled substeps per point"), `::8` (clustering), `::6.3` T11 (one plant:
a batched `@`).

1. **Contact.** Suppose the implementation assembles every contact in the tick into one sparse system and solves it
   with `scipy.sparse.linalg.spsolve` (SuperLU, with a fill-reducing column ordering). Then A's skin values depend
   on the size and ordering of the whole system, including B's contact with a different object across the map.
   This is the same class of defect as DP-B2's dgemv, and the lint doesn't see it.
2. **Substeps.** A vectorised Thomas solve over all columns takes one shared dt. "Per point" is the design, but the
   cheap implementation steps the batch at its minimum dt. Then B's hand on a hot plate changes A's substep count,
   and with it A's bits. The work counter shows the cost; nothing shows the coupling.
3. **Clustering.** "Points share a ray set" doesn't say *whose* points. Suppose two bodies standing side by side
   are clustered together. Then B joining changes A's rays, and so A's visibility, through no physical path (bodies
   don't shade in v1).

**Failure scenario.** For each of the three: B touches a stove, or B joins out of sight. A's tissue bits change, and
T11 goes red only if one of its runs happens to give B a contact or put B near A. Its one plant is a batched `@`,
so none of these is planted.

**Fix.**
- Contact systems are solved per connected component (per object and the skins on it), assembled in a canonical
  order.
- Each point's substep sequence is a function of its own state; a batch shares dt only among points that need the
  same dt.
- Clusters never span bodies.
- Add a T11 plant for each: a global sparse solve, a batch-minimum dt, a cross-body cluster.
- Extend the lint to `scipy.sparse.linalg` and `scipy.linalg` in `core/body`.

### DP2-S3 (SHOULD-FIX). The save names three things and the load check verifies only tick T, so carried law state can be lost without the check going red

`sem_stimuli.md::5` ("The save: tissue, visibility and pending events; frames are recomputed on load and must match
the digest").

The laws now carry state across ticks that isn't tissue or "visibility" as values:
- each body's visibility-refresh reference pose and its last refresh tick (§8's motion trigger is a distance since
  then);
- the error controller's state, if it warm-starts its dt from the previous tick, as most controllers do;
- contact pairing and the contact state of each sub-column;
- the event coalescing counters (§4.3).

Recomputing tick T's frames on load matches whether or not these were saved, because they affect only the *next*
decision.

**Failure scenario.** A save at tick T omits the refresh reference pose, and the load resets it to the current pose.
At T+3, a body that has moved 0.12 m since its last refresh, against a 0.1 m bound, doesn't refresh in the loaded run
but does in the original. The load check passed, and the stimulus digest goes red at T+3 as an apparent
nondeterminism bug.

**Fix.**
- Define the save as all of `core/body`'s carried state, and give the controller a memoryless-per-tick rule or save
  its dt.
- Add a test: save at an arbitrary tick, load, and run k ticks past at least one refresh, one controller change and
  one contact change, bit-identical with the unbroken run.
- Plant an omitted reference pose.

### DP2-S4 (SHOULD-FIX). The per-tick digest goes through the header's config canonicaliser, which costs 8% of the budget for nothing

`sem_stimuli.md::5` ("through `checks`' canonicaliser"), against `boundaries.md` §6.3: "One digest form: SHA-256
over a canonical serialisation of the loaded, typed value (sorted keys, fixed number format)". That canonicaliser
is built for config. `checks.py` doesn't have it yet.

I measured a 250-row `BodyFrame` (`digest_form.py`):

| Form | Time |
|---|---|
| sorted-key JSON, then SHA-256 | 110 µs |
| length-prefixed little-endian IEEE bytes, then SHA-256 | 2.9 µs |

At 10 NPCs and 10 ticks, that is ~11 ms per world second against a 140 ms target, and ~110 ms at 100 NPCs. A "fixed
number format" that isn't shortest-round-trip would also let §5's one-ulp plant pass. The plant guards that, which
is good, but the design should not invite it.

**Fix.** The per-tick array digest hashes dtype, shape and little-endian bytes per field, length-prefixed. The
config canonicaliser stays for the header. Say which in §5. The ulp plant then holds both.

### DP2-N1 (NIT). "Bisection finds the first bad tick" is false at log v0's interval (my round-1 error)

`sem_stimuli.md::5`. A chain stored every N ticks finds the first bad *window*. Either store the per-tick digest
(32 B per tick, about 1.15 MB per world hour), or say "the first bad interval; per tick only when the reference run
is available to recompute". §5's plant test says "red … at the first affected tick". That holds in the harness,
where both runs compute per-tick digests, and not from a log alone.

### DP2-N2 (NIT). `local_id`'s assignment order is the tie-break, and it is unspecified

`sem_stimuli.md::4.2`. Events sort by `(offset_us, kind rank, local_id)`, and `local_id` "counts within this NPC".
Two same-kind events at the same µs order by whatever order the producer counted them in, which is insertion order:
the thing DP-S1 said must not be the key. Assign `local_id` after sorting by a world-side canonical key (source id,
then site). v1 has no producer, so the trigger is the first event row's PR.

### DP2-N3 (NIT). T11's "B's body affects A only physically, in sight" is the wrong criterion

`sem_stimuli.md::6.3` T11. Under v1 bodies don't shade, so the only B→A path is contact through a shared object. B
cooling a pipe in another room changes what A feels when it touches the pipe, out of sight, and that is legitimate.
Write "only through world state (shared objects, the ledger), never through the batch or allocation".

### DP2-N4 (NIT). The target is a ratio to a denominator that will move

`sem_stimuli.md::8` ("under 10% of the physics step's wall time"). When the heat law is compiled, or fire adds kernels,
the ratio shifts with no change to stimuli: a 4× faster heat law turns the same stimuli "over budget". Put the
counter thresholds and an absolute figure (ms per world second at 10 NPCs, at the 0.1 m tile, lightly loaded) in the
B5 row, with the ratio as commentary.

## Checked, no finding

- **Lane overlap (§4.1).** Steps 3–4 finish before 5 and 6; physics at T reads no agent output at T. The on/off
  replay gate can fail: a leak changes world state and the T+1 frames.
- **Membership (§4.5).** `agent_ready`'s wall-dependent arrival can't move the digest; frames are built regardless.
- **Header (§5).** Registry rows, id maps (code-point sort) and truth constants, with bodies and bindings in `join`,
  make the frames a function of tier-1 content.
- **The ulp plant (§5)** sits below a bypassed header check, so it exercises the digest, not the refusal.
