# Known gaps

The one owner of the world's known physics and performance gaps (owner, 2026-11-22): what the simulation gets wrong
or can't yet do, stated with its numbers instead of hidden. Each gap names the step that closes it, and most are held
by a strict red gate (CLAUDE.md, "Known-broken behaviour gets a strict red gate"). A gap is added here, never in a
design document, and removed when its fix lands and its gate flips. Moved verbatim from `docs/architecture.md` on
2026-11-22, where the list had outgrown a document that must not grow.

**Known gaps (tracked, not gated yet):**
- NPC inference (no streaming yet, load versus failure, first hops, spend): `docs/design/inference_placement.md` §6.3.
- Late in a burn the coarsest rig lags (crate integrity 0.539 at 0.2 m vs 0.370 and 0.381 at 0.1 and 0.05 m after 150
  turns): a coarse cell degrades as one block. Onset agrees to within 5%. It falls below 0.7 at turn 137 at 0.2 m
  against 104 at 0.1 m (one substep per 6 s turn, 2026-11-22). Red gate: `tests/test_cross_tier.py::test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig`.
- Structural glow reads the cell-mean temperature, not the face's: a heated face glows late and dim, by up to
  q·(dx/2)/k in steady state (29 K per kW/m² for concrete at 0.1 m). Face skins would fix it
  (`docs/design/client_objects.md` §5.1; owner, 2026-11-22).
- No convection or radiation: air only conducts, so rooms heat too slowly and fires must sit on a material.
- Destroying a cell removes its heat (it becomes air at air's heat capacity). Measured: a 5.4-minute crate-and-pallet
  burn lost 42.2 of 84.0 MJ to 14 destroyed cells (commit 6e8f037).
- **Fires don't consume fuel: once nothing solid is left under a fire, it heats air.** `World._power_field` spreads a
  fire's power over the solid cells its sphere overlaps, and falls back to the air cells when there are none. Air has
  about 1/1000 of wood's ρc, so the runaway is enormous. On the 3×3×2 m crate scene at 500 kW, radius 0.3 m: the
  crate is gone by turn 50 at 0.2 m cells, and the peak is 207,350 °C at turn 50 and 2.67 million °C at turn 200;
  at 0.1 m it is 361,913 °C at turn 50 and 2.67 million °C at turn 200. The snapshot clamps at 6000 °C; the heat
  still conducts. The fix is a fire that goes out
  when it has nothing to burn. It blocks the exit test's "burn away", so it lands before the tile's crate scenario
  is gated. Red gate: `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`
  (`xfail(strict=True)`).
  *Fixed 2026-11-15, the other half:* power went into cells destroyed mid-turn (16,619 °C by turn 30); it is now
  recomputed after any substep that destroys cells (peaks 538 °C at 0.2 m, 613 °C at 0.1 m). Guards: `tests/test_heat.py::test_a_cell_destroyed_mid_turn_gets_no_more_source_power`
  and `tests/test_cross_tier.py::test_a_fierce_fire_never_heats_any_cell_past_the_flame_temperature`.
- **A source smaller than a cell heats one cell.** `World._power_field` puts all of a sub-cell source's power into
  the cell it sits in, so total power is right but its density is P/dx³: 64× higher at 0.05 m cells than at 0.2 m.
  Peak temperature near a spark therefore depends on the rig. *Closed for actions (2026-11-15):* an `ignite` must
  have a radius of at least 0.3 m and a `strike` a width of at least 0.2 m, the coarsest rig's cell
  (`data/world/actions.yaml`, held by `tests/test_act_validation.py`). A `HeatSource` built directly in code can
  still be smaller.
- **Fires diverge across rigs mid-burn, so fire outcomes don't yet keep the verification rule.** Measured at the
  largest fire actions allow (500 kW, 0.3 m radius) on the 3×3×2 m crate scene, recording crate integrity every
  turn: the spread across laptop / rig / max exceeds 0.1 on every turn from 18 to 27 and peaks at 0.19 at turn 22
  (0.70 / 0.57 / 0.51). It narrows near turn 30 only because the curves cross, and from about turn 30 the fuel gap
  takes over (at 40 turns, integrity 0.02 / 0.26 / 0.34 and peaks of 620 / 1.4×10⁵ / 1.4×10⁵ °C). Smaller radii or
  more power diverge sooner: at a 0.2 m radius the onsets are 11 / 8 / 7, and at 1 MW integrity at turn 30 is
  0.00 / 0.26 / 0.34. `temperature_max` diverges too (540 / 614 / 978 °C at turn 27). **The cause is measured:**
  the crate's mean temperature agrees between laptop and rig to within 1 °C through turn 22, so the crate's heat content agrees, but
  the degradation driver (the mean of the excess of each cell's temperature over the limit, in
  `damage/thermal.py`) is 1.3–1.5× larger at rig. The law does converge, slowly (integrity at turn 22 is 0.703 /
  0.567 / 0.514, roughly first order), but the coarse rig sits far off, because a threshold is applied to cell means
  (CLAUDE.md, "Reconstruct, decide at the point, integrate upward"). Scaling the rate by cell size would make the gate pass and is a band-aid; the law itself is held by a
  closed-form test at every rig (`tests/test_validation.py::test_thermal_degradation_follows_its_closed_form_at_every_rig`). The fix is the Phase 1 fuel model, with burning as a
  rate driven by heat content. Held by a strict red gate that checks the spread on every turn for 60 turns,
  `tests/test_act_validation.py::test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`.
  Until then, `ignite`'s ceilings in `data/world/actions.yaml` (at most 500 kW, a radius of at least 0.3 m) keep
  fires at the powers this physics has been measured at; they make no claim about agreement across rigs.
- **Strikes near the fracture threshold, and breaches of thin walls, flip across rigs.** Below the threshold nothing
  is destroyed at any rig, a guarantee of exact cell-average deposition. Craters with a closed-form radius of at least
  0.33 m (about 1.7 coarse cells; 4× the threshold and above at the 0.2 m minimum width on concrete) match the closed
  form within 25% at every rig. Between the two they don't: destroyed volume at laptop / rig / max is 0 / 0 / 0.001 m³ at 1.05× the
  threshold (about 2.5 MJ), 0.008 / 0.032 / 0.026 m³ at 1.5×, and 0.152 / 0.088 / 0.114 m³ at 3× (closed form
  0.109 m³). The crater radius goes to zero continuously at the threshold, so no minimum width removes the band.
  What an NPC acts on flips too: a 0.4 m concrete wall whose faces sit off the 0.2 m grid, struck at 1.5× the
  threshold, is breached at rig and max but not laptop (a strict red gate,
  `tests/test_act_validation.py::test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`). How the resolution
  rule should treat outcomes at a class boundary is an open decision.
- **A destroyed region still claims its space,** for strikes and for imagined objects alike (`spec.place` refuses
  a new object inside a burnt-out crate's old box). A crate burned to nothing still owns its authored box: a strike there
  is "on the crate", and `ignite` puts the fire into air. "Gone" only means a later paint took every cell. Ownership per cell (the region id array planned
  for design v2) removes it. Decided by the flames design (after R0–R1); `docs/design/world_model.md` §5
  disagrees.
- **Overlap is judged on bounding boxes, and it has an authoring cost.** Named solids may not overlap a later solid
  (`scene._check_no_solid_overlaps`, and `imagination.place` for imagined objects), and a cylinder's box corners
  count as its own, so two barrels close together can be refused although they don't touch. A solid window, sign or
  vent inside a named wall is refused too, so such a wall must be split into pieces or left unnamed. Per-cell
  ownership (design v2's region id array) removes both. Decided by the flames design (after R0–R1).
- **A region carved hollow keeps its authored centroid.** Air may carve into a named solid (a doorway), but the
  solid's footprint and centroid stay those of the authored box. With a doorway through a wall's middle, the
  centroid is in air: `ignite` puts the fire in the doorway, where it heats only air, and an aimless strike lands
  there too. Refusing such a fire by its cells was tried and withdrawn: off the coarse grid that decision
  depends on the rig (a 0.33 m fire was accepted at laptop and rig, refused at max). Held by a strict red gate,
  `tests/test_act_validation.py::test_a_fire_on_a_region_carved_hollow_heats_the_region_not_air`. Per-cell ownership
  with authored geometry (design v2) removes it.
- **Whether an imagined object fits in the world can depend on the rig.** `imagination.place` refuses an object
  "smaller than one cell at this resolution" when it covers no cell centre, which can happen at the coarse rig and
  not at a finer one, and at the truth grid too. Measured at the offset (0.503, 0.503, 0.003) m, 2026-11-22: a wooden
  footstool with 4 cm parts and a glass aquarium on a steel stand are refused at 0.1 m, and a steel locker of 1 cm
  sheets at 0.05 m (D34). Its size and mass budgets are rig-independent; this check
  isn't. The thin-features rule (`docs/design/world_model.md` §1.1) as a minimum authored size
  would remove it.
- **`place` accepts an object that loses most of its geometry, or lies partly outside the world.** A wooden table,
  with a 1.2 × 0.8 × 0.04 m top and four 0.05 m legs (0.0455 m³), placed at (0.5, 0.5, 0) in an empty scene,
  voxelizes to 0.032 m³ at 0.2 m and 0.007 m³ at 0.1 m: its top vanishes at both spacings. `place` refuses only an
  object that covers no cell centre, and it never checks the placed bounds against the grid, so a part below z = 0
  is clipped silently (spec generator spike review, 2026-11-22). The bounds refusal lands at step 5a, where `place`
  becomes the `imagine` intent's stage 2; red gate:
  `tests/test_imagination.py::test_an_object_partly_outside_the_world_is_refused`. Lost geometry waits on spec v1's
  sub-cell geometry (`docs/design/fire_model.md`).
- **`region_breached` picks its axis from cell extents, so the axis can change with the spacing.** It tests for a hole
  along `argmin` of the region's index extents, with ties going to x. A 0.6 × 0.6 × 0.55 m box at (0.5, 0.5, 0) has
  extents [2, 2, 2] at 0.2 m, so x, and [5, 5, 4] at 0.1 m, so z. For furniture whose thinnest axis is z, "breached"
  means a burned path from the legs' slice to the top's. The fix is `world_model.md` §1's breach by remaining
  thickness in metres, at step 8a (`phase1/fuel-surface`). Red gate:
  `tests/test_damage.py::test_a_hole_through_the_thinnest_authored_axis_is_a_breach_at_every_rig`.
- **A region's temperature reading can leave its declared range.** `RegionInstrument` declares
  `temperature_max` as [-273, 6000] °C, but the fuel gap lets legal fires drive cells far past that (about 4×10⁵ °C
  after 60 turns of a 500 kW fire, once the crate has burned away). The reading isn't clipped, because clipping
  would hide the gap; the fuel model is the fix.
- **Physics runs slower than real time at tile scale.** `advance(0.5)` takes 0.7 s of CPU at 1.92×10⁶ cells (a
  40×8×6 m tile at 0.1 m) lightly loaded, 1.4× real time (about 3.6× at 5×10⁶ by scaling); under heavy load 1.2–1.45 s
  (2.3–2.9×) and 3.9 s at 5×10⁶ (7.7×). Main is the same (`process_time`, min of 2–5 runs; step 3b). 0.05 m is about
  60× slower than 0.1 m. Step 5a owns it (B5); far cells never run coarser (D21).
