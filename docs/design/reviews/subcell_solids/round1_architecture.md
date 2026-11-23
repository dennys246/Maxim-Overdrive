# Sub-cell solids design, round 1: Architecture (2026-11-22)

The reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the fold.

**What the reader read:**
- `subcell_solids.md` at 1c701aa.
- The survey and D31–D35 at `phase6/specgen-spike` 91ebd0d.
- Designs: `fire_solid.md`, `fire_model.md`, `world_model.md`, `world_v2.md` §4, `boundaries.md` §2.2,
  `tile_and_client.md` §3.2 and §3.4, and `contracts.md`.
- `sim_core.md`, both at 703b745 and as #44 and #45 amended it on `origin/main` bfb12f8.
- On `origin/main`: `core/topology.py`, `core/fields.py`, `core/refusals.py`, `core/imagination.py`,
  `core/scene.py` and `tests/fixtures/scenes/alley_box.yaml`.
- PR #40's diff (`client_objects.md`, plus its edits to `fire_solid.md`), and `gh pr list`. #44 and #45 merged after
  the draft's base, and #46 builds #40's fuel pass.

**Totals:** 8 BLOCKER, 11 SHOULD-FIX, 5 NIT.

## BLOCKER

**A-B1. `subcell_solids.md::§2.1`: the threshold test gives two identical walls different representations,
depending only on where each sits.**
- t(p) = `min(max_m − min_m)` is a float64 subtraction, and the rule says "a part exactly at the threshold becomes
  cells".
- The shipped alley has four 0.4 m concrete walls and a 0.4 m floor, all exactly at the 0.4 m threshold.
- Verified in Python: `4.0 - 3.6` = `0.3999999999999999` (under 0.4), `0.4 - 0.0` = `0.4`, `12.0 - 11.6` =
  `0.40000000000000036`.
- So `wall_north` becomes a `structure` object while `wall_south` stays cells. The two walls then get different
  thermal laws, a different load path and different zone-gap behaviour.
- This is D34's defect class (the representation depends on where a part lands), moved from dx to position. §13's S1
  red-first test varies only the sub-cell offsets of three specs, so it would miss this.
- Fix: compare in integer micrometres (F13), as §4.1 and §6 already do. Verified only for this case:
  `round(4.0e6) - round(3.6e6)` = 400000.
- §2.2 should also say that the shipped walls sit exactly on the threshold, because any later change to the
  quantization flips them.

**A-B2. `§6`: whether a pane closes a gap depends on dx.**
- A pane blocks a gap only when it lies "within 1 mm of the gap plane", and gap planes are cell faces at multiples of
  dx.
- Zones are authored in metres but labelled by cells (world_model §2, §6), so each zone boundary snaps to a cell face.
- A pane at x = 0.25 m is within 1 mm of a face on the 0.05 m grid, but not on the 0.1 m grid (faces at 0.2 and 0.3)
  or the 0.2 m grid.
- Result: at 0.1 m the two zones stay joined through a closed window, and at 0.05 m they are separated. That is an
  outcome-class split across grids.
- S5's own test ("a pane separating two zones at every grid and offset") fails against this text. Checked by
  arithmetic only.
- The contract has to say how an object's plane maps onto the quantized zone boundary at any offset. The reader
  proposes no mechanism.

**A-B3. `§8.1`: nothing owns the load that cells put on objects, so the threshold test fails by construction.**
- The graph's vertices are live objects and anchors (an anchor is a cell region connected to the floor). A cell part
  resting on objects is neither.
- Scenario: a 0.42 m concrete slab, which §2.1 makes cells, on four 0.2 m steel posts, which are objects.
  - The slab is not a vertex, so its weight never enters the solve, and the posts never fail.
  - In Phase 2, D22's min cut on cells finds no cell path from the slab to the floor, so the slab counts as loose.
  - A 0.38 m slab is an object, so it does load the posts.
- §2.2 promises "the same outcome class for a block near the threshold … under one load". §13's 0.38/0.40/0.42 m
  test therefore can't pass.
- §2.1 makes mixed stacks normal, since one spec can give cells and objects together. D33's "a part that would be
  `loose`" has no meaning for a cell part.
- The contract must say how cell regions enter the graph as loads and as supports, and how D22 sees objects.

**A-B4. `§7.2`, `§6`, `§3.1`: object state changes never reach Topology, so derived tables go stale.**
- The design's state changes: destruction sets `state` to `removed`, failure sets `failed`, and a pane's breach must
  restore the open area "the next batch".
- What depends on topology: `contact` is rebuilt on insertion and on a `topology_version` change (fire_solid §1.1);
  blocked area and face-to-zone membership are recomputed per topology batch.
- On `origin/main` (#44; sim_core §5.1 as amended 2026-11-22; the `topology.apply` docstring), `topology_version`
  bumps only when a batch "changed a cell's value or the region table". An object's removal, failure or breach
  changes neither.
- Consequences: a removed object keeps its contact rows and keeps exchanging heat, and a breached pane keeps the two
  zones apart forever.
- §6 also contradicts §7.2: §6 counts "every live object" as blocking, and a breached pane is still `live`.
- Fix: route object state transitions through `Topology` as keyed-table requests (sim_core §5.1 already lists
  keyed-table rows), and say which transitions bump the version.

**A-B5. `§7.1`: strike on objects adds a second resolver for the `loads` input.**
- On `origin/main`, `fields.INPUTS` declares one resolver: `InputSpec("loads", APPLIER, "damage.loads")`. sim_core
  §5.1, an owner ruling, requires one resolving law per input kind, and a test asserts it.
- §7.1 makes `damage.objects` resolve strikes on objects, and §12 adds it to the tuple as its own law. A strike on a
  mixed region (which §4.3 now allows) would then resolve in two laws.
- `damage.objects` also has no cadence. If it isn't `per_record`, sim_core's rule that strikes resolve on their own
  tick breaks, and the next record's stage 2 doesn't see the damage.
- Fix (unverified): make object strike a resolver module inside `damage.loads`'s declared tuple ("one module per
  kind").

**A-B6. `§7.1`, `§11.3`: `ignite` is a retired act.**
- The registered contract in `tile_and_client.md` §3.2 is
  `intent.kinds: move move_to kindle strike douse imagine | not: ignite extinguish`. Vocabulary v1 retires `ignite` in
  favour of `kindle`, and fire_model §5.4 removes it from `parse_action`.
- §7.1 defines `ignite` on objects anyway. Its resolver is "heat, as for fuel", but no such fuel act exists, because
  fire_solid §2 refuses every act on an object. It also adds a new code, `not_flammable`.
- Either the row goes and `kindle`'s target rule covers objects that can't burn, or the owner reverses T4.

**A-B7. `§3.3`, `§7.2`: structural objects have no lateral resolution, and a law reads nodes that don't exist.**
- Each face is one segment, and each object has one profile across its thinnest dimension.
- §7.2's glass law reads "the ΔT between its centre node and its edge nodes". Pagni's criterion is the lateral
  gradient from the hot centre to the shaded edge, and the design has no nodes for it.
- A 2 m steel beam heated at one end is one lumped node, so `thermal_degrade` decides on the beam's mean. That is
  averaging then thresholding, which CLAUDE.md's reconstruction rule forbids.
- fire_solid §1.2 keeps 0.02 m strips for exactly this reason. This design drops them for structure as a special case.

**A-B8. `§11.2`: two different formats are both called "spec v1".**
- fire_solid §5.2's fuel spec v1 (name, recipe, kind, geometry, variants) ships with 6.0b, before S1.
- This design's structural spec v1 is `{spec_version: 1, name, primitives}`, and the merge is deferred: "decided at
  S1".
- After 6.0b ships, S1 must either redefine v1 (which F1 forbids) or the reader sees two shapes under one version.
- Formats are contract (B32, and CLAUDE.md's "Every format is versioned"). §2.1's "fuel recipe entry" row already
  assumes one spec can mix both.

## SHOULD-FIX

**A-S1. `§12` misses revisions for contracts this design takes over.**
- **fire_solid §7's owner table** still gives acts and damage on objects (A-S4) and every structural face (D-S3) to
  "the 6.2 design".
- **fire_solid §1.3 and §2** still say mixed regions and object acts arrive "with 6.2".
- **`douse` on objects:** fire_model's next revision owns this (D-N3).
- **The new codes' owner** is `tile_and_client.md` §3.4 (`refusal.codes`), and §12 doesn't list it. `check_contracts`
  over the tracked files passes, because §11.3's per-item counts sit below the restate count of 6, so only review can
  see this one.
- **Two more:** world_model §2's "Solids live in cells", and sim_core §5.1's resolver sentence together with
  `fields.INPUTS`.

**A-S2. `§10`, `§3.1` conflict with PR #40, which is in flight.**
- **`segments` changes meaning.** Its rows become faces, but #40's `client_objects.md` §3.2–§3.3, and fire_solid §1.2
  as #40 amends it, define segments as axial strips. Each strip has a `segment_length_m` ℓ, and the client finds a
  fragment's segment as k = ⌊s/ℓ⌋, which a face row breaks. #40 also forbids reinterpreting a table by kind.
- **New `state` values.** The design adds `failed` and `removed`, but #40's decoder refuses any `state` other than 0
  or 1.
- **The leak rule conflicts.** #40 rewrites fire_solid §5.6 as `FuelFrame`, which is "presentation only: not on
  `Observation`, unread by `adapters.sem`". But §7.3 and §9 have NPCs reading objects, and the design names no
  published object frame (site, cadence, leak rule).
- **The rename collides.** `FuelStore` → `ObjectStore` clashes with #40 and #46's `FuelFrame` and `fuel_version`, and
  with the contract markers `fuel.objects.columns` and `fuel.segments.columns`.
- The design should state its order against #40 and #46.

**A-S3. `§12`, `§8.2`, `§5.1`: the new laws are not declared.**
- **No law entries.** `objects.thermal`, `damage.objects` and `load` have none of the name, version, cadence, reads and
  writes that sim_core §5 requires.
- **No home for the thermal work.** Neither the structural thermal solve nor `thermal_degrade` on objects is assigned
  to a law.
- **An impossible order.** "`load` per_physics_step after the thermal laws" can't happen, because the
  `per_physics_step` group runs before `per_substep`, where `damage.thermal` runs.
- **No writer for `contact_exchange`.** Between a fuel object and a structure object, sim_core §5.1 says contact
  writes it and the solid law resets it, and the design names neither.
- **Three undeclared writers of `state`.** The solid, damage and load all write `objects.state`.

**A-S4. `§8.3`, `§8.4`: support is defined before D33 allows it, and `anchored` is undefined.**
- **D33 is pre-empted.** D33 says what "loose" means is settled with D32's bodies, and §8.4 defines it now. That
  revises a ruling, and §14 doesn't ask the owner.
- **`anchored` is never set.** `support` has an `anchored` value, nothing assigns it, and v1 has no joints.
- **Fixtures become unauthorable.** A ceiling pipe or a wall shelf is refused at scene build as `unsupported`.
- **Non-member vertices are ambiguous.** It isn't defined whether `inert` and `fuel` vertices pass a bearing path to
  what rests on them, for example a sheet on a fuel crate.

**A-S5. `§2.3`: the ½-overlap rule moves B28's knife edge; it doesn't remove it.**
- B28's real fix is a material fraction per cell. A ½ cut-off on the overlap fraction is still a binary decision on a
  float.
- A script over a 0.4 m part across offsets gives 2 cells at 0.2 m every time, 4 or 5 cells at 0.1 m, and 8 or 9 at
  0.05 m. The extra cell appears at the ½ tie, so "stable at every offset" is false at 0.1 m and 0.05 m.
- Mass from authored volume also creates a second mass truth: the cells' heat capacity and the fines left on
  destruction use counted cells.

**A-S6. `§13`, `§8.1`: the landing order is unstated.**
- **S1 assumes four things that aren't built:** CSG footprints, which D26 moves to Phase 2 (step 8b); B28's
  voxelization; mixed regions; and limits.yaml v0, from 6.0a.
- **The anchor test is cited to the wrong place.** S4 cites "world_model §6's anchor test". §6 only measures what it
  costs; the test itself is world_v2 §4's Phase 2 rubble connectivity.
- **No phase per step.** The branch is `phase2/`, while §5.2 and §8.3 describe Phase 1 behaviour.

**A-S7. There is no placement table (boundaries §2.2's layers), unlike fire_solid §7.**
- **The representation rule** needs one shared home, or the `scene` and `imagination` copies will drift.
- **D33's graph builder** must run before any write, so it can't live inside the `load` law.
- **The mechanics catalogue** has no layer.
- **Box and cylinder geometry** isn't placed against `core/fuel_geometry.py`.

**A-S8. `§3.1`: each shape gets two kinds.**
- Box is an axis-aligned slab, and cylinder is a rod with axis z. That splits kinds by where a part came from,
  although the design says kind and role are independent.
- Overlap and contact then need four kinds compared pairwise, and the client needs two extra tables.
- Fix (unverified): use the existing kinds. Also, `contact` gets a second key shape; one table should have one key.

**A-S9. `§6`: blocked area is "summed".** Two objects within 1 mm of the same gap plane on opposite sides count their
shared projection twice. The open area then goes negative, or gets clamped, which world_model §4 forbids. The blocked
area should be a union in integers.

**A-S10. `§11.3`: new codes duplicate existing meanings.**
- `not_on_object` repeats `not_on_region` or `not_on_surface` once §4.3 makes the footprint a union, so it is a special
  case.
- `overlaps_object` supersedes fire_solid's planned `overlaps_fuel`, but nothing retires that code.

**A-S11. `§7.3`, `§9`: the bridge surface changes without the NPC fire note.**
- §9 says the bridge changes only through that note's ruling.
- But extending `QUANTITIES` to objects changes every `StructureModulator` instrument, the surface fire_solid §7 keeps
  untouched so that NS3 isn't widened.
- §14 item 1 asks the owner about F1, but not about this ownership.

## NIT

- **A-N1.** PR #40 is an open draft. Call it "open", not "accepted".
- **A-N2.** The law name `load` collides with sim_core's `Load` and `damage.loads`, and §7.1 uses `Load` in the other
  sense.
- **A-N3.** `h_ref` and `h_contact` are thermal values sitting in `mechanics.yaml`, and `FuelCatalogue`'s name no
  longer matches what it validates.
- **A-N4.** `pose` is reserved with no frame semantics, so "no format change" can't be checked, and D32 may decline
  bodies.
- **A-N5.** §10 doesn't say that new kinds bump the protocol (client_objects §3.1).

## What the reader checked and found sound

- **Size:** 4,871 words, under the 6,000 limit.
- **Tables:** no fold, ruling or decision tables.
- **Contracts lint:** passes.
- **D35 (1)–(3):** implemented as ruled.
- **The survey's two conflicts:** both addressed, apart from A-B2 and A-B4.
- **§4.1** keeps one owner per cell.
- **§9** stays with `sem_stimuli.md` and boundaries §4.4, with no new affordance and no `maxim` import.
- **§5.3's ledger** is antisymmetric, with no clamping.
- **§11.4** follows fire_solid's digest and save pattern.
- **Altitude:** the text stays at the contract level, apart from §2.3's ½ rule and §5.2's 1 mm probe.
