# Fire sub-steps 6.0–6.1 (`fire_solid.md`): Architecture lens

Reviewed: `docs/design/fire_solid.md` as staged on disk in `.worktrees/fire-design` (uncommitted, on top of ec74406).
I read it against `fire_model.md` v2 (§2, §3, §9, §10.2), `reviews/fire_model/fold.md` (the "B plus C" ruling),
`reviews/fire_model/delta1_architecture.md`, `delta1_wire_trust.md`, `delta1_executor.md`, the charter, CLAUDE.md,
`foundations_plan.md` §2, `tile_and_client.md` §1.2, §1.3 and §5.2, and `boundaries.md` §2.2, §3 and §4.1. I checked
the code at gates 396ae10: `core/grid.py`, `heat.py`, `world.py`, `applier.py`, `damage.py`, `frames.py`, `scene.py`,
`imagination.py`, `adapters/loaders.py`, `adapters/sem/bridge.py`, `protocol/encoding.py` and `pyproject.toml`.

**Counts:** 2 BLOCKER, 10 SHOULD-FIX, 6 NIT.

## The question asked: is §3's "convection to ambient" honest, or a band-aid?

**My verdict: it is an honest model choice, but the document under-states it, mis-owns it and doesn't guard it.**
Evidence that it is not a band-aid:
- It is the frozen tile's own boundary model, not something new. Tile §1.2 says "every exposed surface loses heat to
  ambient through 6a; the flame's convective plume leaves the open-topped alley" (D29, D30).
- It matches the rule the code already follows. `World._power_field` refuses to heat air because "power dumped into
  air cells would sit there, and how much of it did would depend on the grid spacing".
- For 6.1 it is literally true. A cone sample does lose to an open room.

What makes it look like a band-aid is the framing. §3 says it "settles the gas-sink blocker" and that "delivering that
heat is the plume's job" in 6.2. The root cause is not touched: Phase 1 air cells have no advection, so they can't
store heat. §3 avoids that cause instead of fixing it, and nothing guards the avoidance. Finding S1 has the details.

## BLOCKER

**A-B1. §2 lets object-only regions through the action and entity gates, but no action or sensor knows what an
object is. On the shipped path, `ignite` on a fuel object heats air or the floor, `strike` succeeds while doing
nothing, and the integrity sensor reads 0.**
`fire_solid.md::§2` (rows `applier._check_region`, `bridge.StructureModulator.__init__`, `region_parts`, `damage.py`).

Today `_check_region` refuses an air region, and `StructureModulator.__init__` refuses `not frame.is_solid(region)`.
§2 changes both to "refuse only a region with no solid cells and no objects", and makes `Region.solid` the same join.
Meanwhile:
- `damage.py` stays cells-only (§2's own row);
- `ignite` stays in `parse_action` until 6.4 (§7, A-S2/NS8);
- `StructureModulator.affordances` still offers `strike`, `ignite` and `extinguish` to any region that passes.

**Scenario.** A scene v2 has one fuel slab, region `plank`, lying on the concrete floor. An NPC (or a test through
`execute`) sends `ignite plank`.
1. `_check_region` now passes.
2. `_ignite` puts a `HeatSource` at the plank's footprint centroid.
3. `_power_field` finds solid cells only where the sphere reaches the floor, so it heats the floor. With a small radius
   it finds none and falls back to `frac`, the air cells. That is exactly the Known gap ("once nothing solid is left
   under a fire, it heats air"), the gas sink §3 claims to have closed.
4. The plank itself gets nothing, because a `HeatSource` has no coupling to objects.

`strike plank` returns `success=True` with `absorbed_j = 0`. `damage.region_integrity` returns `0.0` when a region has
no solid cells (`... if n else 0.0`), so a fresh plank's integrity sensor reads "gone" from the first frame, and
`breached` reads False.

**Fix.** In 6.0, keep the action gates as they are: `_check_region` and `StructureModulator` refuse a region with no
solid cells, each with a refusal test. Objects appear only in readings designed for them. Widen each gate in the
sub-step that gives that action an object meaning (6.2 for `strike`, 6.4 for `kindle`). Or name, per action, what it
does on an object now. "The same join" for every consumer is the wrong default.

**A-B2. The build order can't be executed as written. 6.0 needs 5a's registry, physics step, log header and digest,
and step 9's save. The plan says step 6 waits for 5b. v2's landing-order rule was dropped without a word.**
`fire_solid.md::§1.1` ("named in the field registry (O34)"), `§3` ("once per physics step"), `§5.1` ("in the log
header … as today"), `§5.3` ("Save and digest"), `§6` ("Save and load at every step"); `foundations_plan.md` §2 rows
5a, 6 and 9; `fire_model.md::§9.1` "Landing order", `§10.2` 6.0 "Before: step 5's log writer".

None of the things 6.0 leans on exists at 396ae10:
- there is no field registry (grep finds none);
- there is no fixed physics step (`World.advance` runs a 6 s turn of 4, 16 or 64 heat substeps under
  `TEMPORARY(phase1/sim-clock)`);
- there is no log header or SHA-256 anywhere in `src/`;
- there is no digest;
- there is no save format (step 9, which comes after step 8).

v2 required 6.0 to land *before* step 5's log writer, so that no replay golden is recorded on material v0. fire_solid
has no order at all, and D-S1 (formats frozen before the decisions that fill them) appears nowhere in §7. The plan's
step 6 row still reads "6a open-air loss, 6b skin, 6c porous bed, 6d char oxidation … tile §6.3 passes at three
grids" (D-N5, still open).

**Scenario.** Each possible order breaks:
- If 6.0 starts now, it has no registry or tick to name its tables in. It invents a coupling frequency on
  `World.advance` that 5a then replaces, so R1's frequency check grades a step that won't ship.
- If 6.0 waits for 5b as the plan says, 5a's log writer records replay goldens on material v0. 6.0 then re-records
  them, which is what v2's rule existed to prevent.
- The §6 "save and load at every step" test has no save codec to test until step 9.

**Fix.** Give fire_solid a "Blocked by and before" line. It has to say:
- 6.0 lands after 5a's registry and tick and before 5a's log writer records goldens, or it accepts a v0→v1
  re-recording and says so;
- §5.3's save list is a *requirement on step 9*, and 6.1 tests a round trip of in-memory state only;
- the plan's step 6 row is revised in the same commit.

## SHOULD-FIX

**A-S1. §3 is honest but mis-framed, unguarded and under-costed.**
`fire_solid.md::§3` "Convection and re-radiation".
- **Cite it as 6a on object surfaces** (tile §1.2, §5.2 "h_c(T_s − T_amb) + εσ(T_s⁴ − T_amb⁴)"), not as a new
  simplification. Then the `open_air_object` ledger line is 6a's line, and the reader can see it is a frozen decision.
- **"The plume's job, 6.2 owns it" contradicts tile §1.2,** where the plume *leaves* the alley. Preheat from a plume
  is a new law for 6.2 to design. It is not a stub being completed. Say which it is, or 6.2 will be read as owing a
  fix it was never scheduled to make.
- **Make the root rule an invariant with a guard:** "no law deposits power into air cells in Phase 1". Today only a
  comment holds it, and `_power_field`'s fallback breaks it (a Known gap with a red gate). A ledger or ownership test
  that sums the power deposited into `material == AIR_ID` cells, and must find zero for every law except the named
  fallback, would make §3 a checked rule instead of a convention.
- **The cost is under-stated.** "Hot gas doesn't preheat fuel above it" is one consequence of three:
  1. objects don't receive radiation from hot structural surfaces: a wall heated by the fire radiates nothing to
     the crate's cardboard;
  2. an object boxed in by solid cells still loses to the outside reservoir;
  3. an object in air that another source heated feels T∞.

  CLAUDE.md requires a Known gap in `architecture.md` with numbers, and §3 names none.
- **Permanent or scheduled?** If 6.2 replaces T_env = T∞, the code needs a `TEMPORARY(phase1/…)` marker and a roadmap
  file entry. If it stays for Phase 1, it is a Known gap. §3 is neither.

**A-S2. 6a for structural cells and the structural skin have lost their owner, and contact conduction couples to the
cell mean.**
`fire_solid.md::§3` "Conduction", `§6` straddle and coupling tests; delta1 D-S3; `heat.py` (insulated boundary,
"Convection and radiation are not modelled yet").

v2 carried 6a as a ledger line and the plan carries 6a and 6b. fire_solid has 6a only for objects. No code has 6a for
cells, and no sub-step owns it. D-S3 (keep the skin on structural faces) is also missing from §7. Contact conductance
"with the cell's temperature" applies a law to a cell's mean where the outcome depends on the surface: a 0.2 m concrete
cell's mean rises about 4× slower than a 0.05 m cell's under the same contact flux. That is the case the
reconstruct-at-the-point rule forbids, and world_model §3's skin exists to fix it.

**Scenario.** The straddle test at 0.2 m and 0.05 m. The slab sees a cooler floor at 0.2 m, draws more heat into it
and arrives at different floor and slab temperatures. Then either the test fails or someone widens tile §6.3's
tolerance, which is the forbidden fix.

**Fix.** Couple contact to a structural skin node sized in metres. Give the cell skin and 6a an owner (6.0 or a named
sub-step), and add §7 rows.

**A-S3. "Tables inside `CellStore`'s write window" makes `CellStore` a god object and copies every node table on
every window.**
`fire_solid.md::§1.1`; `grid.py::CellStore`.

`CellStore` is "the cells' owner". It defines 10 public members in its own body today: four channels, `regions`,
`time_s`, `is_writing`, `on_close`, `holding` and `writing`. Exposing `objects`, `segments`, `nodes` and `coupling`
takes it to 14, over the 12-member tripwire, and gives it a second reason to change. Its `writing()` copies every
channel on entry (`{name: arr.copy() …}`). Every applier action and every `advance` would then copy the node tables,
even a `strike` or a sources-only window that touches no object.

**Fix.** Add a `FuelStore` with the same window discipline. A world-level window composes both stores: one owner, and
a rollback whole across both. Name it in §7.

**A-S4. §7's placement table is two files for six concerns, with no layer, and nine pieces of new code have no
home.**
`fire_solid.md::§7` "Placement"; `boundaries.md` §2.2 (B-8 layers 2, 3, 4, 5a, 6, 7a).

The row "tables, the 1D solid, the kinetics → `core/fuel.py`, `core/solid.py`" mixes state (layer 3, with the window)
and laws (layer 4) without saying which file holds which. Coupling, which reads geometry and cells, has no module.
Missing rows:
- `holds_fuel`, the occupancy rule, and the region join (`grid.py` can't import a fuel module above it);
- the world-limits type and its loader (`core/limits.py`, `loaders.py`);
- scene v2's `fuel:` entries and §1.3's overlap rule (`scene.py`, or B-8's `geometry`);
- spec v1 (`imagination.py`);
- the save codec's split (boundaries §2.2: decoding in loaders, construction in sim);
- the digest and the ledger, neither of which exists;
- the migration registry `materials_v0_to_v1` presumes;
- the published frame's object part (`frames.CellFrame` is cells only, and §2 adds object reductions to it);
- the cone harness (heater, prescribed q''_fl, spark).

The last matters most. §5.3 books "the cone heater's input, the prescribed flame flux's input and the spark's input"
on the shipped ledger. That puts lab instruments in the shipped format, or in `src/`, unless the harness lives in
`tests/` and those lines belong to a test ledger. Say which.

**Fix.** One row per container and law, each with its B-8 layer, and the harness placed explicitly in `tests/`.

**A-S5. §7 claims to give "each open finding" an owner, but about a dozen delta-round-1 findings are missing.**
`fire_solid.md` line 8 ("§7 says which document owns each open finding") and `§7`.

I grepped fire_solid for every delta1 id. These are absent and not obviously answered in the text:
- Architecture: D-S1 (format order), D-S2 (tile §6 graded times), D-S3 (structural skin), D-S8 (FPH-B1 revision),
  D-S9 (the time-box in effort), D-S10 (what is held), D-S11 (imagined fuel with no caller), D-N2, D-N3 (`douse` on
  objects) and D-N5 (plan and roadmap rows);
- Executor: NS6 (tile §6.3 cited for a tolerance it doesn't have);
- Wire: N-S5 (joint variant checks) and N-S6 (structural imagining, the name `wood`).

Executor NB2 and NS3–NS7 are presumably 6.2's, but the table doesn't say so. Several Wire ones (N-S3, N-S4, N-S7) are
answered in the body without being cited, so a reviewer can't set their status. The ruling says "none is closed by
this ruling". An unlisted finding has no owner.

**Fix.** List every delta1 id with its owner or its § in this document.

**A-S6. Spec v1 and the world limits are a trust surface with no Phase 1 caller (D-S11, still open).**
`fire_solid.md::§1.3`, `§5.2`.

`imagine` has no wire message in v0 (T16), and Phase 1 has no NPC that acts. 6.0 still builds spec v1, variants, its
loader, `limits.yaml` and the per-call world-limit check. CLAUDE.md says "a fix ships with a caller". Variant joint
checks (N-S5) are owed before it is safe anyway.

**Fix.** In 6.0, `place` refuses fuel recipes, with a test. Spec v1, variants and world limits land when `imagine`
joins the wire. Scene v2 can carry fuel without them, because authoring is not an LLM path.

**A-S7. The snapshot tables are frozen with no consumer, and a defect: u8 °C saturates at 255 °C, below glow.**
`fire_solid.md::§5.3` "Snapshot"; `protocol/encoding.py::snapshot`.
- `surface_temperature_c` is u8 in °C, "display-quantised as `temperature_c` is". `temperature_c` is float16, clipped
  to −273…6000 °C, so the claim is false. A u8 in °C can't show 300–900 °C surfaces, and `GLOW_START_C` is 525.
- One column list is given for "an `objects` table and a `segments` table". It is unclear which table holds the
  surface temperature and the ignited fraction.
- D-B2's "`crack`'s source" is assigned to the client design pass. The client can only draw what the server sends. The
  char or damage column that replaces `crack` is a server format decision, and 6.0 is freezing the format without it.
- "6.1 is server-only", so nothing needs snapshot tables in 6.0.

**Scenario.** The client pass, before step 8, needs a char-depth column and a real temperature range. The grammar,
frozen at step 7, takes a version bump on day one: D-B2's second scenario.

**Fix.** Take the snapshot out of 6.0. Design it with the client pass before step 7, or declare the object tables
column-extensible in the grammar.

**A-S8. The save rules refuse every mid-burn save, mass has two truths, and two pieces of v2's save state were
dropped.**
`fire_solid.md::§1.1`, `§1.3` "Saves", `§5.3`; `delta1_wire_trust.md` N-S7; `fire_model.md::§9.2`.
- §1.3 validates "inventories ≥ 0 that sum to the recipe's mass". N-S7 asked for "within the recipe's initial mass".
  After any pyrolysis the sum is below the recipe mass, so §6's "save and load at every step of a cone run" is refused
  at step 2.
- The objects table holds "per-component inventories (kg)", and the nodes hold per-component density. "Inventories
  are kg per object, held per node" is two stores of one quantity. Keep one, and derive the other.
- Coupling is "rebuilt in the topology batch from geometry" and is also saved ("every table in §1.1"). Saved, derived
  state needs validating against a rebuild. Otherwise a forged save sends a segment's contact heat into arbitrary
  cells.
- v2's save carried "a recipe name map" and "the material-data hash". fire_solid's doesn't. Recipe ids u16 "resolved
  by name" across several `content/recipes/*.yaml` files have no stated assignment rule. Adding a recipe file can then
  renumber every recipe in an old save.

**A-S9. The two-part segment with a scalar "front position along the segment" is frozen into nodes and saves before
6.2 designs the front, and nothing in 6.1 exercises it.**
`fire_solid.md::§1.1` `segments` row.

A cone sample flashes all at once, so no 6.1 test moves the front. For a slab segment, "along the segment" has no
defined direction: a front can enter from any edge. 6.2's front law (opposed versus concurrent spread, an area moving
between parts and the profile mixing that implies) may need a direction, or no position at all, only the ignited area.

**Fix.** Freeze the area per part, which 6.1 needs. Leave the front's geometry to 6.2, outside save v1.

**A-S10. Material data v1 freezes before R0 picks the rate law (the content half of D-S1).**
`fire_solid.md::§4.1` (kinetics (a) and (b); k(T) and c(T) RAMPs), `§5.1`.

§5.1's loader validates "reactions" but not their form. If v1 can express only one of a threshold (T_p, L_g) and
n-step Arrhenius with a cutoff, R0's choice forces v2. RAMPs need a schema too.

**Fix.** Say v1 carries both forms and the RAMP schema, or freeze `chemistry.yaml` after R0. The cone fixtures can use
a provisional loader under `tests/`.

## NIT

- **A-N1.** `fire_solid.md::§5.1`: "path and SHA-256, as today". No log header or hashing exists in `src/` at 396ae10.
  It is boundaries §6.3 and 5a work.
- **A-N2.** `§5.1` and `§5.2`: "registered `materials_v0_to_v1`" and "a registered migration". No migration registry
  exists (`loaders.py` only refuses by version). Say that 6.0 builds it, and where.
- **A-N3.** `§4.1`: both kinetics are built. Say that R0's loser is deleted, so no law ships without a caller.
- **A-N4.** `§3` "Frequency": R1 is grid-free. Comparing it against "a run coupled at every heat substep" only means
  something in the straddle or floor scene. Move the check there.
- **A-N5.** `§1.1` and `§5.3`: the geometry columns are fixed (origin, axis, length, radius or thickness, width).
  `bed` (φ, σ, a box) will add columns to both the save and the snapshot. Declare geometry per kind now.
- **A-N6.** `§5.1`, `§6`: the FDS outputs and MaCFP data committed as fixtures are non-code assets. CLAUDE.md requires
  each listed with its source and licence before commit. Name that step.

## Checked, nothing found

- **Representation by authoring (§1.2)** removes the dx-dependent choice at its root, and the burning-wall gap is
  stated.
- **Segments and nodes sized in metres and millimetres,** never by cell, plus the segment-halving test: correct, and
  can fail.
- **The Thomas solve with no BLAS** keeps boundaries §3's banned list. The delta-form equilibrium test can fail.
- **The scope split:** flames, the client pass, the NPC note and step 5's vocabulary each have a named home.
- **§8** states honestly what 6.0–6.1 can't show.
