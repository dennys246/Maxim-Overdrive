# Architecture lens: torch_pilot.md design review, round 1 (fcc6e55)

I read: `docs/design/torch_pilot.md`, the commit's diffs to fire_solid §7, checklists step 6 and contracts.md, and `reviews/torch_pilot/numbers.md`. I checked them against fire_solid §0–§8, fire_model §3.2, §4.1, §5.4, §7, §10.2 and §12, tile §2.2, §3.1–§3.4 and §6.2–§6.4, sim_core §5.1, §6, §7 and §10, client_objects §5.3–§5.4 and §7.3, the roadmap's Phase 1 and Phase 2, `data/world/actions.yaml`, the three red gates in `tests/test_cross_tier.py` and `tests/test_act_validation.py`, and the other session's `.worktrees/subcell-design/docs/design/subcell_solids.md` at ed2c9ae (§0, §1, §3, §5, §7.1, §12, §13). I worked read-only and ran no code.

---

**A-B1. The three `ignite` red gates would flip by losing their subject, not by being fixed. Kindling a cell is silently retired.** `docs/design/torch_pilot.md::§9.4` and `§4.4`. This is a contract defect: the roadmap's Phase 1 requirement names these gates and the `actions.yaml` band-aid as the bar.
- §4.4 makes a `kindle` on any cell region `applied` with zero deposit. So after 6.1b the shipped path has no way to heat a cell region by fire.
- Today `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn` (`tests/test_act_validation.py:287`) reads the crate's cell `integrity` through `region_parts` on every turn. §9.4 says it is "rewritten with `kindle` at §6's ceiling … keeping its bar (… integrity within 0.1)", but names no target.
  - **Failure scenario, slab target:** fire_solid §2 refuses every reading on an object-only region, and objects take no damage (fire_solid §2's table). The bar can't be read.
  - **Failure scenario, cell target:** nothing is deposited, integrity stays 1.0 on every grid, and the gate turns green while asserting nothing. CLAUDE.md calls a test that cannot fail a BLOCKER.
- `test_a_fire_that_has_burned_its_fuel_stops_heating` (`tests/test_cross_tier.py:133`) guards `World._power_field`'s fallback into air, a Known gap. Rewritten on the slab, it passes because of fire_solid §3.1's ambient rule. `_power_field` and the `sources` input kind stay untouched.
  - The design never says whether `sources` and `HeatSource` keep a producer once `ignite` retires, or whether they are deleted. Either the fallback still exists with no gate, or it is dead code nobody removed. Neither is a root-cause fix.
- The hollow-region gate is "closed by name" because kindle on cells now does nothing. The Known gap closes by deleting the capability, and the design doesn't say that.
- The Phase 0 exit claims "Breach and fire outcomes agree across rigs", and the roadmap and tile §6.4 still treat fire on cells as a capability. Retiring it is a scope decision that belongs to the owner, and it isn't in §11.

Proposed (unverified):
- Add an owner question that says kindle on cells is retired for Phase 1, and add the roadmap edit.
- Decide the fate of `sources`, `_power_field` and its fallback. Delete them with the producer, or keep their gate red.
- Rewrite each gate against an observable its new target actually has, such as the slab's flash class and ignited area across grids. Otherwise keep each gate strict-red and give it a named later trigger.

**A-B2. The slab exit's beats get a second owner, and the first owner's rows are left in place.** `docs/design/torch_pilot.md::§9` and the preamble ("That last answers D-S2 for Phase 1: tile §6 is the Phase 2 crate's, so the slab's beats had no owner"). This is a contract defect under one owner per contract.
- The beats did have an owner. `client_objects.md` §7.3 says "Their owner is tile §6 (D-S2)", and its trigger moved to "before step 8" (client_objects §9 ruling 4).
- fire_solid §7, whose row the commit edited next door, still lists "The tile §6 revision, before step 8 | D-S2".
- tile §6.2 still owns `tests/scenarios/alley_exit.yaml`'s script (tick 70: "region `crate` in the receipt"), and tile §6.3 and §6.4 still own the crate's beats, bands and controls.
- §9 links to tile §6.2's form, §6.3 item 7's band rule and item 9's determinism form, while it restates and replaces the beats.
- §10 lists none of fire_solid §7's D-S2 row, client_objects §7.3 or tile §6.
- **Failure scenario:** step 8 builds its script from tile §6.2 (the document that names the file) and gates `t_crack` and `t_glow` on bed cells the slab doesn't have, or gates torch_pilot's beats. Either way one of two "owners" is stale. A later revision of tile §6 for the crate in Phase 2 would silently diverge from §9.

Proposed (unverified): either torch_pilot §9 takes D-S2 explicitly, and §10 lists the fire_solid §7 row, client_objects §7.3 and tile §6.2–§6.4 becoming links or being scoped "Phase 2 crate", or the beats go into the tile §6 revision that D-S2 already names.

---

**A-S1. The strip-width red gate names a fix that doesn't fix it.** `docs/design/torch_pilot.md::§7`, first bullet, and §11 Q4. This is a contract defect: the strict gate's trigger is the contract other steps rely on.
- §7 says "Refinement across the width (6.2's partial transfer, `fire_solid.md` §1.2) is the verification … It is fixed in 6.2."
- fire_solid §1.2's partial transfer, "with an enthalpy merge", moves part of one strip's area from the unignited part to the ignited part. It doesn't give a strip more than one unignited profile across its width.
- A footprint covering 19.5% of a 0.5 m strip still heats one strip-mean profile after 6.2, which is averaging before thresholding.
- Resolution across the width needs tiles, which fire_solid §1.2 rejected on cost (1.2×10⁷ nodes). The sub-cell design gives tiles to structural objects only ("Fuel keeps its `segments`", subcell §3.1).
- **Failure scenario:** 6.2 lands partial transfer, the gate stays red, and no step owns the real fix. This is the "deferred hole" the charter forbids.

Proposed (unverified): name the real mechanism (per-tile profiles across the width, or a footprint-sized sub-profile) and the step that owns it. If none is planned, Q4 has to say so plainly.

**A-S2. The 6.2 "migration to a flame object" is not a plan.** `docs/design/torch_pilot.md::§0` item 2, `§2` last bullet, `§10` (item data). This is a contract defect: the save format and the item's data format depend on it.
- fire_model §4.1 makes flames stateless ("no flame state is saved"). fire_model §12 lists "a held flame's lifecycle" as not yet designed. So the migration target has no saved form, and its design is open.
- fire_model §5.4's flame object takes a prescribed Q in watts at a point. This pilot carries `flux_w_m2` and `radius_um` over a disc, and §10 makes the item's datum `flux_w_m2`.
  - tile §3.2 has the item carry `power_w` today.
  - The item format would therefore flip from power to flux at 6.1b and back to power at 6.2.
  - Migrating a mid-pilot save means mapping q''·πr² onto a flame heating "by §4", which changes the physics of a loaded game. A version bump on a user save also needs a migration that preserves meaning (CLAUDE.md, "Every format is versioned").
- **Failure scenario:** step 9's save v0 freezes `pilot.fields`. 6.2 then finds no defined target and no faithful mapping, and either refuses old saves or migrates them into different behaviour.

Proposed (unverified): state which datum survives 6.2, either Q plus a radius with the flux derived, or flux. Mark the record "replaced by 6.2's held-flame design, migration defined there". Don't assert a migration whose target is undesigned.

**A-S3. The two stand-ins are not marked as scheduled band-aids.** `docs/design/torch_pilot.md::§0` item 1 and `§11` Q2. This is a mechanism plus process defect.
- The prescribed-flux pilot stands in for fire_model §5.4's flame object. Q2's recommendation moves q''_fl, a fitted constant of the cone harness in `tests/fire/` (fire_solid §7 placement), into the shipped solid law. That stands in for the flame of fire_model §4.
- 6.2 removes both. CLAUDE.md allows a stand-in only as a `TEMPORARY(phaseN/step)` marker with its file listed under that phase in the roadmap. The design names neither, and §10 has no roadmap row.
- Q2 also puts a constant fitted with the heater on and the convective loss off (fire_solid §4.5) onto every flaming part on the shipped path: rods, partly covered strips and footprints. That is outside the conditions it was fitted under, and it should be flagged as an extrapolation.
- **Failure scenario:** 6.2 lands its flame while the shipped q''_fl still applies. The two heat a flaming part twice, and no lint or roadmap row points at the leftover.

Proposed (unverified): §10 adds the roadmap Phase 2 listing for `core/solid.py`'s pilot and q''_fl paths and requires the markers in 6.1b's code.

**A-S4. §10's list of edits elsewhere is incomplete, so stale owners would survive the merge, which Q6 exists to prevent.** `docs/design/torch_pilot.md::§10`. This is a contract defect. Not listed:
- **fire_model §5.4:** "The torch's pilot is a flame object … replaces the sphere deposit and the 0.2 m minimum radius" is false for Phase 1 and needs a Phase 1 qualification and a link.
- **fire_model §10.2 and §12:** the 6.4 row and "flipping the two fire red gates … (proposed: in 6.4)" now happen at 6.1b.
- **fire_solid §1.3:** `holds_fuel` is "built with its first (6.2, or `kindle` in 6.4)". The design never says whether 6.1b builds `holds_fuel`.
- **fire_solid §2:** the table row "`kindle`'s target | none | 6.4 (Bio N1)".
- **fire_solid §4.4:** on the shipped path, flash is now gated by §5's pilot condition rather than the "spark, present by definition".
- **sim_core §6:** the input list ("`sources`, `source_exposure` … and the tick's `loads`") gains the pilot input and its resolver.
- **sim_core §10:** a new work counter (see A-N1).
- **client_objects §5.4:** a fourth divergence (§8's "joins … §5.4's divergences").
- **The roadmap:** 6.1b enters Phase 1, and "6.2–6.4 … moved to Phase 2" previously carried the pilot.
- **Failure scenario:** a 6.1b builder reads fire_solid §2 and fire_model §5.4, sees "6.4" and "flame object", and builds neither the target function nor the pilot.

**A-S5. The target query sits in the wrong layer, and the sibling design has a second, different nearest-surface rule.** `docs/design/torch_pilot.md::§10` ("Placement: the record and the stage-2 target function in `core/applier.py`'s layer (6)") and `§3`. This is a contract defect for placement and a mechanism defect for the duplicate rule.
- The nearest-surface distance over fuel geometry and cell faces in µm is pure geometry. boundaries §1 and §2.2 define a geometry layer, and fire_solid §7 puts "metric overlap and contact tests" in `core/fuel_geometry.py` (layer 2).
- Putting the query in layer 6 means the applier both decides geometry and applies, against separation of concerns, and nothing below layer 6 can reuse it.
- subcell §7.1 defines `strike`'s target as "the smallest distance in µm, then a cell face before an object, then the smallest `object_id`": a tie-break where kindle refuses with `ambiguous_point`.
- **Failure scenario:** two nearest-surface implementations with opposite tie semantics, one per act. A point 0.5 mm from a slab and the floor is `ambiguous_point` for `kindle` and resolves to the floor cell for `strike`, and the two codes drift.

Proposed (unverified): the query goes in layer 2 and returns ranked candidates, and each act's stage 2 applies its own tie policy. Tell the sub-cell session, as Q1 already proposes for the refusal code.

**A-S6. The pilot input's end of life has no declared writer.** `docs/design/torch_pilot.md::§2` ("It ends at `end_tick`, or on leave or `region_gone`"). This is a contract defect: sim_core §6's writers column is "the writers' one owner".
- The applier appends the record at stage 2. Nothing names who removes it at `end_tick` (the solid law, which is its resolver? `Simulation`, as for `source_exposure`?), on leave (a session event), or on `region_gone`.
- `region_gone` isn't defined for a fuel object at all. Objects take no damage in 6.0–6.1, and a `burnt_out` object's region still exists (fire_solid §1.1).
- **Failure scenario:** the record stays live after a burnout. `pilot_live` then refuses the actor's next `kindle` until `end_tick`, or the solid law deletes its own input, breaking the rule that inputs declare and laws resolve (sim_core §5.1).

**A-S7. A 6.1b test can't run before step 9.** `docs/plans/checklists.md` step 6 ("a save at a mid-pilot tick and a rebuild of the overlaps, each bit-identical") and `torch_pilot.md::§9.3`. This is an ordering defect.
- Save v0 is step 9, after step 8 (checklists §"Step 9, save v0"). fire_solid §5.5 handles the same gap by testing that "the digest after a rebuild from the tables equals the running digest" until step 9.
- **Failure scenario:** 6.1b's checklist item can't be built, so it is skipped or faked with a test-only serializer that step 9's format later contradicts.

Proposed (unverified): at 6.1b, rebuild the digest from the pilot records; the mid-pilot save and load goes to step 9's checklist.

**A-S8. The design assumes fire_solid text that the merging sub-cell S0 revises, beyond Q1's refusal code.** `docs/design/torch_pilot.md::§2` (wire row) and `§3` (candidates). This is a contract defect if S0 lands as drafted, and S0 lands before 6.0a (subcell §1).
- **Regions:** §2 relies on "each fuel object is its own region (`fire_solid.md` §1.3), so the row names the object". S0 revises §1.3 so that "regions may mix" (subcell §12). Then the wire's pilots row, keyed by `region_id` (tile §2.2), can't identify the footprint's object.
- **Candidates:** §3 takes "every live fuel object … and every solid cell region". After S1, `ObjectStore` holds structure and inert objects too (subcell §3.1), and subcell §7.1 requires kindle's query over "cells and objects".
  - A structural object then lies outside the candidate set, so a kindle on a steel shelf in front of a wall resolves to the wall behind it.
- **Failure scenario:** S0 merges first, and torch_pilot's §2 and §3 are stale on arrival.

Proposed (unverified): add these two points to Q1's message to the sub-cell session, and phrase the candidate set by role.

---

**A-N1. The unpiloted-crossing count is a physics outcome, but the design files it under work counters.** `docs/design/torch_pilot.md::§5`. This is a mechanism defect. sim_core §10's `WorkCounters` are exact cost counters for B5 budgets, held to expected values in replay tests. A physics observable there mixes purposes, and sim_core §10 isn't in §10's edits. A TickReport field or a lab instrument fits it.

**A-N2. The exit's slab width depends on an open value.** `docs/design/torch_pilot.md::§6` ("The exit's footprint r_t ≥ W") and §11 Q3. This is a mechanism defect. The exit slab is 0.1 m wide and the torch radius is open, so the scene's validity hangs on Q3. Choosing the slab so that the known strip gap can't show is honestly flagged (Q4), but it means the exit proves nothing about a player aiming a narrower torch at a wider plank, and the playtest invites exactly that. The exit's known limits should say so.

**A-N3. §10 is a rulings-dependent edit table inside the design.** `docs/design/torch_pilot.md::§10` (heading "after the owner's rulings"). This is a process defect. client_objects §8 sets the precedent and lint_contracts may allow it, but it reads as a list of pending decisions. Once the rulings are in, the table belongs in `reviews/torch_pilot/`.

What I checked and found sound:
- The pilot as an input that the applier appends, with one resolver (the solid law), matches sim_core §5.1's "later a pilot".
- The overlaps are derived, rebuilt and not digested, consistent with sim_core §7's cache rule.
- 6.1b placed after 6.1 and 5b and before step 8 is consistent with fire_solid §0's order.
- The fire_solid §7 edit is one row, and the contracts.md registration is well-formed.

**Count:** 2 BLOCKER, 8 SHOULD-FIX, 3 NIT.
