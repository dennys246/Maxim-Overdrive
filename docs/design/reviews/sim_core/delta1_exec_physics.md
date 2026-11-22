# Step 5a design, delta round 1: Executor and Physics and resolution

Tree: `phase1/sim-clock` at 99917fb, diff `3b5937b..99917fb`; rulings from `reviews/sim_core/fold.md`.

**Correction first.** My own round-1 fix for P-N5 ("key region reductions on `topology_version`") was wrong, and
the fold took it as written. world_v2 §2.4 says region reductions are the SEM sensors, which read temperature, so a
key on topology alone serves stale readings after every physics step. New finding S1.

**Counts (new): 2 BLOCKER, 4 SHOULD-FIX, 5 NIT.** Round-1 rows (31): 29 fixed, 2 open, 0 deferred,
0 rejected; P-N5 is fixed as proposed, but the proposal was wrong (S1).

## Status of round-1 findings

| Id | Status | From the tree |
|---|---|---|
| X-B1 | fixed | §5.1 declared writers; `Topology` for every world edit; boundaries §6.4 rows amended. Residue N1, N4 |
| X-B2 | fixed | R2 (§5.1); §3 states the physics phase. New conflict: B1 |
| X-B3 | fixed (owner ruling R3) | §13 interim bridge path; checklist lists the 61 call sites. Residue S3 |
| X-S1 | fixed | per-load effects in `Changes`; inputs declared (§6); views and handles (§5) |
| X-S2 | fixed | per-record resolution keeps `REGION_GONE` (§5.1, owner-confirmed reading) |
| X-S3 | fixed | §7 keys: geometry on source value, weights on (value, `topology_version`) |
| X-S4 | fixed | §7 states the 1/64 condition and that an exact overlap is a digest break |
| X-S5 | fixed | `substep_refine`, typed `SimConfig`, `limits` (§4, §8) |
| X-S6 | fixed | frames carry `tick`, seconds derived (§3); cadence linked to tile §4. Checklist residue S4 |
| X-S7 | fixed | §14 links tile §3.1; the 0/10/20/30 bullet is gone |
| X-S8 | fixed | §8, checklist and roadmap agree |
| X-S9 | open (narrow) | tests now say how they fail, counters exact, memory deferral ruled. Missing: bar 5's "the law's reference path" still names no oracle (N5) |
| X-N1 | fixed | checklist ids lens-qualified |
| X-N2 | fixed | `simcore/core/fields.py` |
| X-N3 | fixed | §12: expected bit-identical, shown by a test |
| X-N4 | fixed | §7 cites Perf P3 |
| X-N5 | fixed | §4 whole-batch validation, `ValueError`; §2 `World.turn` goes |
| P-B1 | fixed | bar 3 compares orders; a planted clamp pair proves it can fail |
| P-B2 | fixed | §7 keys; checklist's re-ignite test fails under the old key |
| P-B3 | fixed | R2 defines the resolution tick, report and frame. See B1 for the cadence text |
| P-S1 | fixed | R2 puts the crater before the tick's physics, as today |
| P-S2 | open | onset is fixed (§3, closed form k = 1..5). The douse and the mid-interval change of a source, half of the original scenario ("extinguished at tick 10 loses its (5, 10] energy"), are not defined, and the state the rule needs isn't declared: B2 |
| P-S3 | fixed | §5; guard runs with `substep_refine` > 1 |
| P-S4 | fixed | bar 2b, 1 vs 4, from verify_harness §4 |
| P-N1 | fixed | §8 |
| P-N2 | fixed | §8 counts |
| P-N3 | fixed | §7 |
| P-N4 | fixed | §7 "a cache's key is the values its result reads" |
| P-N5 | fixed as proposed; proposal wrong | see S1 |
| P-N6 | fixed | bar 2 in seconds |
| P-N7 | fixed | checklist §13 lists the three CLAUDE.md lines |

## BLOCKER

**B1. sim_core.md::§5 "Cadence" against §5.1 "Strikes resolve in the apply phase" and sem_stimuli.md §4.1: `damage.loads`
has three positions in the tick.**
- §5 defines `per_tick` as "in the per-tick slot, D10 step 1, *after the records*", and puts `damage.loads` in it.
- §5.1 (and the owner's confirmed reading of R2 in fold.md) resolves each `Load` "right after *its own* record applies",
  so the next record's stage 2 sees the crater.
- sem §4.1 puts the per-tick body laws (contact, tissue: the seam §1 says §5 defines) in step 3, after step 2 moves
  bodies, not in step 1. One `per_tick` cadence can't be all three.
- **Failure scenario:** two strikes at tick 7, the first destroying the crate. Built from §5, the second succeeds
  with 0 m³; built from §5.1, it is refused `REGION_GONE`.
  Refusals are digest member 5 (§9), so replay goldens differ; and tissue in the same slot runs before bodies move.
- Fix (unverified): make load resolution part of the applier's per-record step (an `on_record` cadence, or say
  `damage.loads` is invoked by stage 2, not by the slot), and keep `per_tick` for sem §4.1's step 3.

**B2. sim_core.md::§3 "A source's energy in a physics step", §9 members, §6 inputs: the rule needs carried state that
no section declares, digests or saves.**
- §3 credits a source "its power times the number of ticks in the interval at whose end it existed". At the physics
  tick the integrator must know, for every source that existed during `(T − 5, T]`, which ticks it existed at and
  with which value. A source doused at tick 68 is no longer in `sources` at tick 70, yet owes 2 ticks (66, 67) under
  the rule; a re-ignite at tick 68 with a new radius owes 2 ticks at the old overlap and 3 at the new.
- That is state that lives across ticks inside the interval. §6 declares `sources` and `loads` as inputs, §5.1 says
  "loads are never carried state", and §9's member 3 is `sources` as (point, radius, power): no apply tick, no
  per-interval exposure, no removed-source residue. §2 promises "a replay from a loaded state" starts identically.
- **Failure scenarios** (verified by reading the rule against §9's member list; nothing to run yet): (a) a save at
  tick 68 after a douse restores without the 2 owed ticks, and tick 70's temperature differs from the live run while
  every digest up to 68 agreed; (b) the engineer resolves the ambiguity by dropping doused sources' energy, and the
  closed form "a source on for k ticks delivers `k · tick_us · power`" fails for any source that ends inside an
  interval, which the checklist's test (onset only, k = 1..5 "in its physics step") never exercises. tile §3.2's
  pilots need the same for every pilot that expires mid-interval.
- Fix (unverified): declare the per-interval exposure (per source key: value segments with tick counts, including
  removed sources) as an input field in §6, saved and digested (§9 member 3), cleared at each physics tick; state the
  douse and change rule in §3; extend the checklist's closed form to sources that end and change inside an interval.

## SHOULD-FIX

**S1. sim_core.md::§7 "region reductions, per `topology_version`": stale sensor readings.** Region reductions are
the SEM sensors (world_v2 §2.4), and they read temperature (and integrity), which change every physics step
without a topology change. The line contradicts the rule two lines above it ("a cache's key is the values its result
reads"). Failure: a crate heats for 30 s with no cell destroyed; every reading returns the first step's mean. My round-1 P-N5 proposed exactly this key. Fix
(unverified): key on `topology_version` and the write tick of each field the reduction reads (§9 already tracks
"a tick whose window wrote it").

**S2. sim_core.md::§5.1 "bumps `topology_version` once per batch", §7: "batch" is undefined, and the value is
digested.** Per-record load resolution needs the crater applied before the next record's stage 2, so a batch is at
least per record; thermal destruction is per substep. §9 member 1 hashes `topology_version`, so whether two strikes
in one tick bump it once or twice is replay contract, and so are `WorkCounters`' rebuild counts.
Failure: two builds bump per tick and per record; bar 4's goldens differ on the first tick with two topology edits.
Fix (unverified): define a batch as one requester's one invocation (one record's stage 2, one law's one substep).

**S3. sim_core.md::§13 "steps the simulation one tick for it": the interim bridge becomes a second owner of time.**
§2 makes `Simulation` the one owner of time, and CLAUDE.md says the membrane is handed "an applier and a frame view,
never the world"; under §13 it must hold a `Simulation` and call `step`. Every `execute` now advances world time by
0.1 s and, every fifth call, runs physics, so a test issuing three strikes runs three ticks, and a test that also
steps the simulation itself interleaves two clocks. The existing marker text (`bridge.py`, "execute applies
synchronously and logs nothing") no longer describes the band-aid, so "no new deferral" is true of the phase but not
of the marker's reason, and §13's CLAUDE.md list (checklist §13) omits the membrane sentence. Fix (unverified): say
what the bridge is handed in the interim (a submit-and-step callable owned by the test or host, not `Simulation`),
rewrite the marker's reason in 5a, and add the CLAUDE.md membrane line to checklist §13's list.

**S4. checklists.md::"Step 5a" §4 "none on a tick that changed nothing" contradicts the cadence owner.**
tile_and_client.md §4 publishes a frame "every tick on which any intent was applied or refused, or any actor or
pilot changed", so a receipt's after-frame always exists. A refusal-only tick changes nothing, so the checklist's
test forbids the frame tile requires. sim_core §4 ("publishes that tick's frame at the end of the tick") reads as
every tick, a third version. fold.md's A-B3 row still claims a boundaries §4.2 edit that 1270564 reverted
(Architecture's row to set). Failure: a strike refused `REGION_GONE`
at tick 9 has no after-frame, and `observed_tick` reafference breaks for refusals. Fix: the checklist test cites tile
§4's rule instead of restating it; §4 drops its own cadence sentence.

## NIT

- **N1. sim_core.md::§5.1:** "No second module writes `integrity`" while `Topology` writes "a new cell's
  `integrity`" in the same section. Say damage is its only *law* writer, `Topology` its declared construction writer.
- **N2. sim_core.md::§11 bar 3:** "the reversed law tuple" of `(damage.loads, heat, damage.thermal)` mixes cadences;
  reversing moves `damage.loads` without changing when it runs, so only heat and thermal swap. Say reversal is
  within a cadence.
- **N3. checklists.md::"Deferred (owner to confirm)":** the owner ruled on 2026-11-21 (fold.md); §1 already states
  it. Drop "to confirm".
- **N4. boundaries.md::§6.4 table:** still lists "the laws in `advance`" (advance goes), construction writing
  "cells, regions" directly (§13: through `Topology`), and no `Topology` row.
- **N5. sim_core.md::§11 bar 5:** "the law's reference path" names no oracle; once the law is split, the unsplit path
  is gone. Name where the reference lives (today's `heat.step` frozen as a test fixture, say).

## What I checked and ran

Read the diff, tile §3.2 and §4, sem §4.1, world_v2 §2.4, boundaries §4.2 and §6.4, `bridge.py`'s marker. No new
computation; B2's scenarios follow from the rule's text, not a run.
