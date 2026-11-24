# Architecture lens, delta round 2: torch_pilot.md (the uncommitted fold on fcc6e55)

I read the fold's diff in `docs/` and the whole folded `docs/design/torch_pilot.md` (4,439 words, under the 6,000 budget). Against it I checked:
- tile §3.2 and §6, fire_solid §7, client_objects §7.3, sim_core §3 and §6;
- the roadmap's Phase 1, checklists steps 5b, 6 and 9, and boundaries' layer table;
- `src/simcore/core/{applier,deposit,world,grid}.py` and the red gates in `tests/test_cross_tier.py` and `tests/test_act_validation.py`;
- `.worktrees/subcell-design/docs/design/subcell_solids.md` at ed2c9ae (§3.1, §4.3, §7.1, §12).

I ran `scripts/lint_contracts.py::check_contracts` in-process over the working tree's `.md` files and it returned `[]`. I wrote nothing.

## 1. Status table (read from the tree)

| Id | Status | Evidence |
|---|---|---|
| A-B1 | **open** | Fixed: §9.4 rewrites no gate, and Q6 now raises the scope question. Still broken: Q6's recommended trigger can't happen (A2-B1). A fourth gate that drives `ignite` is missing. §10's roadmap row doesn't edit the roadmap's Phase 1 requirement "It must flip the strict red gate `test_the_fiercest_allowed_fire_…`", nor the Phase 0 claim (A2-S1). |
| A-B2 | fixed (conditional on Q9) | The preamble takes D-S2 for Phase 1. tile §6 already reads "This scenario is the crate's, Phase 2" (tile.md:363). §10 turns fire_solid §7's D-S2 row and client_objects §7.3 into links. The sibling docs stay stale until Q9's edits land on this branch, so they must land before merge. |
| A-S1 | fixed | §7: the 6.2 design must choose profiles across the width or a footprint-sized sub-profile, and "6.2's partial transfer alone doesn't fix it". Q4 says the same. |
| A-S2 | fixed | §0 item 2: the 6.2 held-flame design "defines what becomes of a saved one". The false migration claim is gone. |
| A-S3 | fixed | §10's roadmap row lists `core/solid.py` under Phase 2 for `TEMPORARY(phase2/6.2)`. §7's last bullet flags q''_fl as an extrapolation. |
| A-S4 | fixed for every item I listed | §10 now has fire_model §5.4, §10.2 and §12; fire_solid §1.3, §2, §4.4, §5.1, §5.4, §5.5 and §7; sim_core §6 and §9; client_objects §5.4; the roadmap. Other stale owners remain (A2-S1). |
| A-S5 | fixed | §3 "One query, two policies"; §10's placement puts the query in `core/fuel_geometry.py` (layer 2) and the tie rule in the applier. A residual on units and layers is A2-N2. |
| A-S6 | fixed | §2's lifecycle names the appender (the applier), the cut (the applier) and the remover (`Simulation`, in the slot where `source_exposure` is cleared). `region_gone` is limited to cell targets. Residuals are A2-N1. |
| A-S7 | fixed | §2 and §9.3: at 6.1b, a digest rebuilt from the tables and records. checklists step 9 gains the round trip and golden. |
| A-S8 | fixed | §2 records `object_id` and `region_id`. §3 adds candidates of every role. Q1 carries four points to the sub-cell session. New conflicts are A2-S2. |
| A-N1 | fixed | §5 makes it a lab instrument under `tests/`, not `WorkCounters`. |
| A-N2 | fixed | §6 adds r_t ≥ W/2. §7 gives the 2.7% dilution and the narrow-on-wide strict gate. Q7 asks about legibility. |
| A-N3 | rejected | §10 is a change list, not a decision or fold table. client_objects §8 is the precedent, and `check_contracts` returns `[]`. I agree. |

## 2. Delta findings

**A2-B1. Q6's recommendation and §9.4's "`ignite`, its last producer" contradict what step 5b ships. The gates break at 5b, not 6.1b.** Location: `torch_pilot.md::§9.4` and `§11 Q6`. **Contract.**

What 5b ships, read in the tree:
- tile §3.2 retires `ignite` in vocabulary v1 at 5b (`intent.kinds … | not: ignite`).
- The same 5b ships an interim `kindle` that deposits by sphere volume overlap, a marked band-aid (checklists step 5b, tile §3.2). That deposit is today's `HeatSource` → `sources` → `_power_field` → `deposit.sphere_overlap` path (`applier.py:135`, `deposit.py:41,106`).
- §10's tile row says that band-aid is removed at 6.1b.

So each of the following fails:
- **The mechanisms can't go at 5b.** Q6 says "delete `HeatSource`, `sources` and `_power_field` with `ignite` at 5b", but 5b's own `kindle` needs them until 6.1b.
- **`ignite` is not the last producer.** The sphere `kindle` is.
- **The gates turn red at 5b.** They drive `ignite` through the SEM bridge (`test_cross_tier.py:76`, `:147`, and the act-validation gates). Once 5b drops `ignite`, their precondition raises `RuntimeError`, which is not their `raises=AssertionError`, so the strict gates fail at 5b whatever Q6 rules.
- **Q6's alternative is already excluded.** "Keep `ignite` as a lab path" contradicts tile's `intent.kinds` contract.
- **There is a fourth gate.** `test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig` (`test_cross_tier.py:94`, trigger "roadmap Phase 2, 'Close the known gap'") drives `ignite` too. §9.4 counts "three" and never mentions it. Deleting `_power_field` would silently drop a gate whose trigger is in Phase 2.
- **§2 is anchored on members Q6 deletes.** It digests the pilot "beside `sources`" and removes it "in the slot where `source_exposure` is cleared". Under Q6 as recommended, both members are gone.

**Failure scenario:** the owner rules Q6 as recommended. The 5b builder either can't delete `sources` because the sphere `kindle` uses it, or deletes it and 5b's `kindle` has no deposit. Meanwhile four strict gates fail at 5b on `RuntimeError`.

Proposed fix (unverified):
- Move the deletion to 6.1b, with the sphere band-aid.
- At 5b, move the gates' precondition from `ignite` to the sphere `kindle` on a cell region. That keeps their subject, `_power_field` and the centroid rule, red until 6.1b.
- Name all four gates in §9.4.
- Anchor §2's digest position and removal slot to something that survives Q6.

**A2-S1. §10 still leaves stale owners that contradict the fold.** Location: `torch_pilot.md::§10`. **Contract.** None of these is listed:
- **tile §3.2, the red-gate sentence:** "`test_a_fire_that_has_burned_its_fuel_stops_heating` is rewritten to use `kindle` when step 6 flips it". This directly contradicts §9.4.
- **tile §3.2, the lifecycle bullet (tile.md:216):** the pilot "ends … when its region is gone", with no qualifier. §2 limits that to cell targets.
- **tile §3.2, the `actions.yaml` bullet:** `max_power_w`. §10's tile row names only the item's fields and the 0.2 m floor.
- **The roadmap's Phase 1:** "It must flip the strict red gate … `test_the_fiercest_allowed_fire_…`" and "Needed before the Phase 1 exit (the slab) is gated". The Phase 0 claim "Breach and fire outcomes agree across rigs" also stands, and Q6 says it "passes to §9.2". §10's roadmap row covers only 6.1b and the markers.
- **checklists step 5b:** "removed by step 6's skin" should name 6.1b, and it must carry A2-B1's move of the gates' precondition.
- **`docs/architecture.md` Known gaps:** the gaps that close by deletion under Q6.

**Failure scenario:** after Q9's edits, the step 6.1b builder follows tile §3.2's rewrite instruction, or the roadmap's "must flip", and rewrites a gate onto a target with no observable. That is round 1's convergent blocker, back by a different route.

**A2-S2. The sub-cell design contradicts three things Q1's message doesn't carry.** Location: `torch_pilot.md::§2`, `§3` and `§11 Q1`, against `subcell_solids.md` §7.1, §12 (S0) and §4.3. **Contract.**
- **Who owns the target rule, and when it is built.** subcell §7.1's `kindle` row cites "`fire_model.md` §2.2's metric nearest-surface query" and says it is built in "6.4". torch §3 claims the rule whole and builds it at 6.1b.
- **fire_solid §2 gets opposite edits.** S0, which lands before 6.0a and therefore before 6.1b, rewrites §2 so that "object-only acts are refused with the existing `wrong_target` until S3". Q1 recommends excepting `kindle` in that same text. Whichever design merges second contradicts the first. Q1 offers "this exception" as news to the other session, not as a conflict with S0.
- **When a region is gone.** subcell §4.3 defines it as having "no live cell and no object in state `live` or `failed`", so after S1 a region holding only a burnt-out fuel object is gone. torch §2 says "a pilot on it continues", and §3's candidate rule takes "every row … burnt out included", which after S1 also admits state `removed` (3). §2 limits its rule to "6.0–6.1" and leaves the post-S1 behaviour undefined.

**Failure scenario:** S0 merges first. The slab's `kindle` is then refused with `wrong_target`, and step 8's exit can't apply. Or Q1's exception merges first, and S0 silently reverts it.

**A2-N1. The `region_gone` cut has no triggering record, and the cutter isn't a declared writer.** Location: `torch_pilot.md::§2` (Cut short). Contract for the writer column, mechanism for the rest.
- A region is destroyed by topology during a tick's physics. The applier only applies records in step 1, and boundaries' `record.kinds` has no region-gone record. So "the applier sets `end_tick` … in that tick's step 1" has no input that would tell it to.
- §10's sim_core §6 row lists "its appender, remover and resolver" and leaves out the cutter.
- Step 6.1b's lifecycle tests list `leave` mid-interval but not a region destroyed mid-interval.

**Failure scenario:** a wall that was kindled is destroyed. Its pilot stays live until `end_tick`, so `pilot_live` refuses the actor's next `kindle`.

The checklist for step 6.1b should carry the test.

**A2-N2. Layer and unit details of the "one query".** Location: `torch_pilot.md::§3` and `§10` placement. **Mechanism.**
- **Layer:** the cell candidates are `Region`s by their authored footprint. `Region` lives in `core/grid.py`, which is layer 3 ("cells"), and boundaries says layer 2 has "no cells". A layer-2 query can take only footprints passed in as primitives.
- **Units:** the query's ranked output has no stated distance type. `kindle` works in f64 metres with a 1 mm band. `strike` works in µm against `contact_tolerance_um`, with a cell-before-object tie-break.

**Failure scenario:** two quantizations of the same geometry rank the same point differently for the two acts.

Step 6.1b should carry a test that `fuel_geometry` imports nothing from `grid`, plus one cross-act ranking case. Proposed fix (unverified): return f64 metres and let `strike` quantize.

**A2-N3. Nothing outside this design records §7's "fixed in the 6.2 design".** Location: `torch_pilot.md::§7` and `§10`. **Mechanism (tracking).** No row in the 6.2 checklist or fire_solid §7 carries the obligation. Only the strict gate's reason will name it. A row in step 6.2's checklist should carry it.

## Counts

- **Round 1 statuses:** 10 fixed, 1 open (A-B1), 1 rejected (A-N3), 0 deferred.
- **New findings by severity:** 1 BLOCKER (A2-B1), 2 SHOULD-FIX (A2-S1, A2-S2), 3 NIT (A2-N1, A2-N2, A2-N3).
- **New findings by kind:** 4 contract (A2-B1, A2-S1, A2-S2, and A2-N1's writer column), 2 mechanism (A2-N2 to step 6.1b, A2-N3 to step 6.2).

A2-B1 is a new contract blocker in text the fold added (Q6 and §9.4). Under the charter it must fold or the owner overrules it; it can't be deferred.
