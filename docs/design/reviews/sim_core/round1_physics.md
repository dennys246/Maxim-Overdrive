# Step 5a design review: Physics and resolution

Reviewer: Physics and resolution lens. Tree: `phase1/sim-clock` at 3b5937b (`docs/design/sim_core.md`, the Step 5a
checklist). Read: CLAUDE.md, `docs/code_review.md`, `splitting.md` §3 and §6, `world_model.md` §1.1,
`verify_harness.md` §4–§7, `realtime_lanes_coop.md` §2.1, `sem_stimuli.md` §4.1, `tile_and_client.md` §3.2,
`fire_solid.md` §4.3, `fire_model.md` §8, and `heat.py`, `damage.py`, `world.py`, `applier.py`, `verify/`.
Probes are in `_durable/sim_review/physics_scripts/` (`probe.py`, `bbox.py`, `reignite.py`), run with the
worktree's `.venv`.

**Counts: 3 BLOCKER, 4 SHOULD-FIX, 7 NIT.**

## Measured facts the findings rest on

- On the cross-tier scene, heat's `stable_dt` is 239.6 s at 0.2 m, 59.9 s at 0.1 m and 15.0 s at 0.05 m, so **n = 1
  at P = 0.5 s at every verification grid**. Air has the tightest bound in the table (17.4 s at 0.05 m). Today's
  substep is 1.5, 0.375 and 0.094 s. The fixed step is therefore *coarser* than today's at 0.1 m and 0.05 m (`probe.py` §1, §4).
- In one 0.5 s step at 0.1 m (a 60 kW, r = 0.3 m fire on the crate, and a 2 MJ, σ = 0.15 m strike at the fire's
  centre that destroys 136 cells), running heat before the strike loses **29.1 kJ of the 30.0 kJ** the fire put in
  during that step, compared with running the strike first. The heat goes into cells that are then destroyed
  (`probe.py` §2).
- On the same id, re-igniting a region replaces its radius (0.3 → 0.5 m: 160 → 604 overlapped cells) and changes no
  cell (`reignite.py`).
- The bounding-box overlap equals the full-grid overlap bit for bit: 600 random centres and radii, a third of them
  grid-aligned, no padding, 0 mismatches. The sums are equal too, because every value is a dyadic k/64 (`bbox.py`).

## BLOCKER

**P-B1. `sim_core.md::§5` ("The reversed-order test") and `§10` bar 3: the bar as written cannot fail.**
`same_class_under_refinement(outcome, run, factors)` returns one bool: does a *single* configuration give one class
across time refinements (`verify/splitting.py`)? It does not compare two law orders. Failure scenario: the forward
order gives class A at n and 10n, and the reversed order gives class B at n and 10n. Both calls return True, so bar 3
passes even though the order flipped the outcome. That flip is exactly the spike's 84 → 464 MJ pilot miss
(`physics_spike.md` row 3). A second problem: the call needs a `Run` refined in time, but `Simulation` exposes no
knob for that. P is a truth constant and n comes from `stable_dt`, so "10n" can't be asked of the shipped path.
That leaves bar 3 (and splitting rule 4's n/10n half, P-S4) with nowhere to run except a hand-built side loop.
*Fix (unverified):* add a hashed config integer `substep_refine` (default 1, multiplying n), as the spike's
scheduler does (`splitting.md` §3: `n = refine * …`). Bar 3 then asserts `outcome(forward) == outcome(reversed)`
directly, with `same_class_under_refinement` per order on top. The checklist adds a planted order-sensitive toy law
pair (a clamp before and after a source) that turns bar 3 red, per "prove a guard by deleting what it guards". With
`(heat, damage)` alone the bar is nearly vacuous: n = 1, and reversing only lags thermal degradation by one step.

**P-B2. `sim_core.md::§7`, "each source's sphere overlap, per `(source id, topology_version)`": the cache key is
stale on re-ignition.** `Applier._ignite` writes `sources[f"fire:{region}"]`, so re-igniting the crate with a new
radius keeps the id and changes no cell, and `topology_version` doesn't move. The cache then serves the 0.3 m
overlap for a 0.5 m fire (verified, `reignite.py`). The same happens after extinguish and re-ignite. The checklist's
test ("recomputed only on a new `topology_version` (counted)") would pass and lock the bug in. "Cached equals
uncached" catches it only if that test happens to re-ignite. The key is also wrong in the other direction: the
geometric fraction doesn't depend on topology at all, only the solid mask applied to it does. So every destruction
during a burn recomputes every sphere, which is the burning-tick cost the cache was meant to remove. *Fix
(unverified):* cache the geometric fraction on the source's value `(point_m, radius_m)` (dx is fixed per
`Simulation`), and the solid-weighted, normalised weights on `(source value, topology_version)`. Add a checklist
test that re-ignites with a new radius and compares against the uncached path.

**P-B3. `sim_core.md::§5.1` ("What it changes"), `§4` and `§3`: when a strike resolves isn't defined on 4 ticks
out of 5.** §5.1 resolves a strike "at damage's place in the tick", shows it "at the end of the same tick", and
carries its receipt "in that tick's `TickReport`". Damage is a law, though, and laws run only in step 6, "physics,
on physics ticks" (`tick % 5 == 0`). Failure scenario: an agent strikes at tick 7. The applier appends a `Load`, no
physics runs at ticks 7–9, tick 7's report has no receipt and its frame no crater, and the checklist's
`test_sem_bridge.py` "reads the next tick's frame" (tick 8) sees nothing. The only consistent readings are both
contract changes. Either loads wait for the next physics tick (up to 0.4 s late, receipt in a later report, and §4,
§5.1 and the SEM test restated), or damage's load resolution runs every tick outside the substep loop, in which case
damage isn't purely a law-list entry. The note also leaves open, for n > 1, which substep consumes the loads, and
whether loads resolve before or after thermal degradation inside damage. That order decides the receipt:
`damage.strike` counts `absorbed_j` over cells still solid, and the destroyed set can differ by float rounding of
`(i − s) − t` against `(i − t) − s`. *Fix (unverified):* state the rule in §5.1. For example: loads resolve once per
physics step, in the first substep, before thermal degradation, and the receipt lands in the physics tick's report.
Restate §4's frame sentence and the SEM test to match.

## SHOULD-FIX

**P-S1. `sim_core.md::§5.1` and `§11`: moving the strike after heat changes energy accounting, and neither section
records it.** Today a strike lands in the apply phase, before `advance`. In the new tick, heat runs first and damage
destroys afterwards, so one step's fire power goes into the doomed cells and is then deleted with them (the Known
gap "destroying a cell removes its heat", 42.2 of 84.0 MJ). Measured: 29.1 kJ of 30.0 kJ in one step at 0.1 m. The
outcome class is unaffected (no threshold reads that energy), but the digest breaks, the Known gap grows, and the
ledger (`world_v2.md` §2.6) has to book it. The physics: for a strike at a physics tick, heat-first is the *correct*
order (the cells existed throughout the interval). For a strike four ticks earlier it is wrong by 0.4 s. The error
is the timing convention (P-S2), not the order. *Fix:* add the break to §11's list, and add the per-step energy
effect to the Known gap's numbers.

**P-S2. `sim_core.md::§3`: how inputs that arrive mid-interval are weighted is unstated.** D10 runs physics "for the
interval that ends at this tick" after step 1 applies that tick's records. A source applied at tick T is therefore
credited the whole interval that contains T. Failure scenarios: a fire on ticks 1–4 delivers 0 J, a fire on ticks
5–9 delivers 0.5 s of power (backdated), and one extinguished at tick 10 loses its (5, 10] energy. `kindle` holds for
a duration in ticks (`tile_and_client.md` §3.2), so each pulse's energy is off by up to P × power. A closed-form
energy test (a source on for k ticks delivers k · tick_us · power) fails unless k is a multiple of 5. The spike's
scheduler did this exactly ("pilot power from the integer tick overlap", `splitting.md` §3), but 5a's note doesn't
carry it over, and no document owns the rule. *Fix (unverified):* §3 states that a source's energy in a physics
step is power × (its ticks inside (T−5, T]) × tick_us, in integers, with that closed-form test in the checklist.

**P-S3. `sim_core.md::§5` and `§8`: `prepare` is never said to rerun after a topology change that doesn't tighten
the bound.** §8 replans only "when a law's `Changes` tightens the stability bound". Today `heat.step` refreshes
source power after *any* substep that destroys cells. That is the 2026-11-15 fix for 16,619 °C in destroyed cells,
guarded by `test_a_cell_destroyed_mid_turn_gets_no_more_source_power`. If `prepare` runs once per physics step and
n > 1, the power field goes stale after a destruction in substep k. It is dormant today (n = 1 everywhere, measured)
and live as soon as n > 1: the spike's step-6 laws reach n = 5 at 0.05 m. *Fix (unverified):* any `Changes` with a
topology change re-prepares every law (through the caches) before the next substep, and the guard test runs with
forced n > 1 (it needs P-B1's `substep_refine`).

**P-S4. `sim_core.md::§10`: the scenarios at P are never shown to be time-converged.** Bar 2 becomes a space study
at a shared step P. `verify_harness.md` §4 (E2) requires a space study's shared step to be time-converged ("a
quarter of it moves each order by under a quarter of that order's bar"). Bar 1 shows this only for heat's closed
form, and by the explicit-Euler term it should pass by about 10³ (α·dt/dx² ≈ 1.1×10⁻³ for air at 0.1 m, 7×10⁻⁶ for
wood; estimated, unverified), so it says nothing about the coupled heat-and-damage scenarios. Splitting rule 4's
first half (n against 10n per scenario, within tolerance and in the same class) is missing from §10. Failure
scenario: damage's first-order degradation at 0.5 s shifts onset at every grid alike. Cross-grid agreement can't see
an error that is the same on every grid, and no bar would. *Fix:* add a bar per scenario: P against P/4 (or n
against 10n) moves each observable by under a quarter of its bar.

## NIT

**P-N1. `§8`, the replan's rationale.** Air's diffusivity is 2.16×10⁻⁵ m²/s against steel's 1.30×10⁻⁵ (1.7×) and
wood's 1.47×10⁻⁷. Destruction never tightens the bound below 0.5 s on shipped data at any verification grid, so the
replan is reachable only from a constructed table; the checklist test should say so. §11 should also note that the
new dt is coarser than today's at 0.1 m and 0.05 m.

**P-N2. `§8` against `§3`.** "As `heat.step` does" computes `remaining = seconds − elapsed` from a float sum, while
§3 says dt is "never accumulated". Replan from counts instead: `remaining = (planned − taken) · dt`.

**P-N3. `§7`, the overlap rule.** `sphere_overlap` is a 4³ sub-sample, not an exact overlap. Its volume error is
+0.8/−1.2% at 0.2 m, −0.4/+0.2% at 0.1 m and −0.1% at 0.05 m for r = 0.3 m (measured). The total is normalised, so
energy is exact and only its distribution is off. The note should state the rule, because the bbox's bit-identity
(verified) depends on the dyadic values: an exact-overlap replacement would change digests through summation order.

**P-N4. `§7`, conductances keyed on `topology_version`.** This holds only while conductivity doesn't depend on
temperature. State the general rule instead: a cache's key is the fields its value reads (from the registry, §6).

**P-N5. `§7`, "region reductions, once per physics step".** An `imagine` on a non-physics tick changes cells, and the
reductions then stay stale for up to four published frames. Key them on `topology_version`.

**P-N6. `§10`, bar 2.** Today's observables count 6 s turns (onset 94, 92, 90). Restate them in seconds. With 0.5 s
resolution, `agrees(...).converging`, which makes no allowance for resolution, is stricter than it is at 6 s. A
change there is a real measurement, not a reason to loosen the bar.

**P-N7. `§2`/`§12`, the CLAUDE.md edits.** Besides "only `World.advance` moves time", the verification rule's "until
step 5a's fixed physics step" and the Determinism rule's "Time comes from `World.advance`" also expire in 5a's PR.
The checklist doesn't list them.

## What holds

- The fixed-step rule itself (§8) is sound, and n = 1 makes it cheap.
- The bounding-box overlap is bit-identical to the full-grid one (verified).
- The conductance cache is exact for the current physics.
- Damage as the only writer of `integrity`/destruction leaves today's crater closed form unchanged: a single strike's
  arithmetic is the same.
- Order inside damage leaves the destroyed set unchanged up to rounding.
- Bars 4–7 can fail as written.
