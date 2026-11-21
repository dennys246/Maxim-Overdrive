# Fire model v2, delta round 1: Wire integrity and Trust boundary

**Design:** `fire_model.md` v2 on disk (uncommitted, over 08310d1). **Code:** gates at 396ae10, read-only.

**Counts:** round-1 findings: 16 fixed, 5 open. New: 2 BLOCKER, 7 SHOULD-FIX, 4 NIT.

## 1. Status of the WT findings (for `fold.md`)

| Id | Status | Reason |
|---|---|---|
| WT-B1 | open | §2.2 gives the predicate `solid \| holds_fuel` and five of the consumers. "Region membership is cells ∪ objects" doesn't answer the half about the `region` channel: one owner per cell in a u16 `region_id`, `_take_cells`, the `bincount` reductions, `damage.region_*`. `client_rendering.md` still draws a fuel cell by `material` (see N-S1, N-S3) |
| WT-B2 | fixed | §2.1: any number of objects per cell; K is gone |
| WT-B3 | fixed | §9.1: species and components keyed by name, with stable integer ids |
| WT-B4 | fixed | §9.2: spec v1 has budgets on objects, segments, nodes and area, checked before allocation, and per-recipe ranges, refused and never clamped. The scene, save and world-level budgets are a new finding (N-B2) |
| WT-B5 | fixed | §7 scene v2: `rod` with any axis, placement inside an owner's footprint, a migration from v1. The overlap rule it implies is underspecified (N-B2) |
| WT-S1 | fixed | §9.1: structural section in `core.yaml` v1, u8 ids stable, `materials_v0_to_v1` |
| WT-S2 | fixed | §9.1's list covers every item, formulas included (chemistry row), plus `LinAlgError` re-raised. The conditioning bound is still unnamed (N-N1) |
| WT-S3 | fixed | `math.fsum`, key-sorted, 1e-12, both orders tested |
| WT-S4 | fixed | §5.4: both acts leave `parse_action`, a refusal test runs through `execute`, and the lab builder lives in tests |
| WT-S5 | open | The derivation and the tie rule are given, and vocabulary v1 is amended. Still missing: the held-flame lifecycle (author's own list); the pilots table (`region_id` u16) and the receipt's derived region, both against an object target (u32); the stage-2 codes (`region_gone`, `not_on_surface`, `pilot_live`) for objects; the item format (`torch.yaml` `radius_m` ≥ 0.2, `actions.yaml` `min_radius_m`) once the sphere deposit goes (N-S2) |
| WT-S6 | open | §9.2 says renamed channels get new names, then keeps `burning` under a new meaning ("the ignited area fraction" against the designed "burning fraction of the cell's fuel surface"). There is no reduction rule for segments that share a cell, no word on `surface_glow` (solid faces still receive radiation, §4.4) or on tile §5.5's bed-cell `crack`, and no new units |
| WT-S7 | open | The list exists, the `combustion` double count is resolved, and T14 is listed. It omits the pilot's prescribed Q as an input (the exit's only external input), the enthalpy carried away by gas products to the reservoir, Δ(bodies), and `removed_with_mass`. "Replaced" names two old lines and leaves `plume_convective` undecided |
| WT-S8 | fixed | Spec v1 is versioned, with admitted kinds and closed variant keys. Structural specs and the v0 disposition are new (N-S6) |
| WT-S9 | fixed | §9.1 landing order; §10.2 puts 6.0 before step 5's log writer and step 7's freeze |
| WT-S10 | fixed | §5.4: `requires` names body sensors (holding, reach); a test refuses `target_effect` and `self_effect` |
| WT-S11 | fixed | §9.2 lists profiles with node counts, inventories, fronts, latches, the held field, counters, and flames as derived with `derivation_version`. Residual gaps are N-S2 and N-S7 |
| WT-N1 | fixed | The header cites `docs/design/research/fire_ladder/` |
| WT-N2 | fixed | §5.3 "on paper only, none exists in `src/`"; §5.4 cites T4 and F7 |
| WT-N3 | fixed | "a threshold without its closed provenance key" |
| WT-N4 | open | The tree doesn't say `breached` stays a lab quantity. §5.5 only says an NPC never gets it; the "stays" exists only in `fold.md`'s Where column |
| WT-N5 | fixed | Removed with K |

## 2. Contract table, v2

| Contract | Producers before → after | Consumers before → after | What each consumer gets, before → after | Migration or version named? |
|---|---|---|---|---|
| `data/materials/core.yaml` | `load_materials` v0 → v1, structural only | `heat`, `damage`, `imagination` (density), `paint`, `snapshot.material`, client colour | per-u8 arrays → the same, ids stable | v1, `materials_v0_to_v1`. What changes from v0 isn't said (N-S4) |
| `chemistry.yaml` | none → engine loader | the solid and flame laws, the ledger, the loader's closure checks | → species and components by name, reactions, transitions | No version, no loader named (N-S4) |
| Recipes, variants | none → "game content", "read by `imagination`" | scene v2, spec v1, the save's recipe map | → kinds, ranges, knobs | No path, version, loader or log-header digest (N-S4) |
| Scene | `Scene.from_dict` v0 (gates; v1 designed with `bed:`) → v2 fuel objects | `Scene.build`, the overlap rule, `paint` | boxes and upright cylinders → `rod`/`slab`/`bed` with a recipe | v1→v2 named. v1 isn't coded yet (N-N4). No object budget (N-B2) |
| Imagined-object spec | `SPEC_KEYS {name, primitives}` → spec v1 (one recipe, one kind) | `place`, the content hash, `imagine` records | material primitives → one fuel object | v1 named. The structural path and v0 are unstated (N-S6) |
| Object, segment and coupling tables | none → topology batch | heat coupling, flames, snapshot, save, digest, kindle | → u32 object id, (id, index) segments, CSR coupling | Joins O34's registry. Id allocation, and whether coupling is state, unstated (N-S7) |
| Occupancy | `material != AIR_ID` → `solid \| holds_fuel` | `_check_region`, `StructureModulator`, `region_parts`, snapshot masks, overlap rule, kindle | → counts fuel | Consumer list given. `damage.region_*`, `Region.solid` from `paint`, the client draw rule missing (N-S1, N-S3) |
| Regions | `paint`/`name_region`, one owner per cell → "cells ∪ objects" | `region` channel (u16), `regions` message, `bincount` reductions, `region_integrity` | → undefined for object-only regions | No (N-S1) |
| Snapshot | `material, crack, glow, temperature_c` (designed `surface_glow, burning, region`) → object, segment and flame tables; `segment_glow`; `burning` | Godot decoder, goldens | → tables with no columns given | Decoder fixtures named; columns, dtypes, units and catalogue not (N-S3) |
| Save and digest | none → §9.2 list | the loader (F14), replay | → profiles, inventories, held field, counters | Header hash "refuse or migrate". Pilots, id counter and row validation missing (N-S2, N-S7) |
| Ledger | tile §5.4 → §9.2 list | ledger test, closed forms | `Δ(skins)`, `unreceived` → replaced | Incomplete (WT-S7) |
| `kindle` stage 2 | tile §3.2 (region within 50 mm, sphere deposit) → nearest object or solid, a 1 mm tie, the pilot as a flame object | applier, pilots table, receipt, log | region → object | "v1 amended". Pilots, codes and items unrevised (N-S2) |
| Bridge builders | one `to_maxim_entity` → NPC builder (golden surface) and a test-only lab builder | Maxim tool generation | `strike`, `ignite`, `extinguish`, instruments → none of them | Golden test named; `_compat.py` unchanged |

## 3. New findings

### BLOCKER

**N-B1. `place` picks the representation by grid spacing.** `fire_model.md::§9.2` ("`imagination.place` creates
fuel objects for sub-cell geometry, instead of refusing objects 'smaller than one cell'"). This contradicts §2.1 ("the
representation is authored, never chosen by dx"). *Scenario:* an LLM imagines a 0.15 m-thick wooden plank. At 0.2 m it
is sub-cell, so it becomes a fuel object and burns. At 0.05 m it is resolved, so it becomes wood cells, which §10.1's
exemption says are structure ("a plank wall stays cells"), and it doesn't burn. One spec gives two outcome classes
across tiers: the resolution rule, and the same defect as Physics B2 and WT-B2 come back for imagined objects. Fix: the recipe decides
(every fuel recipe is an object at every spacing, every structural material is cells), and `place` has a cross-tier
test that places one spec at 0.2/0.1/0.05 m and compares the representation.

**N-B2. Fuel objects have no overlap rule and no world-level count. The tables are unbounded across scenes, specs and
saves.** `fire_model.md::§2.1`, `§7` (scene v2), `§9.2`. On gates the grid bounds imagination (`_voxelize`: "that space is occupied").
v2 drops that bound for fuel, and no rule says whether two fuel objects may interpenetrate, or whether a fuel object may
overlap a solid primitive's volume or only the air inside an owner's footprint. Budgets are per spec only.
*Scenarios:* (a) an agent repeats one in-budget `imagine` of a 3 m `bed` at one spot. Each passes; the tables grow without
bound, past §8.3's 20,000-part basis. (b) A scene file, untrusted per F14 and from
strangers' machines (boundaries §5 table), declares 10⁶ rods. Scene v2 names no budget. (c) A save declares a 2³²-row
object table. F14 checks "the budget before allocation from the header's declared shape", but shape is validated
"against the scene and rig", and neither bounds object count. (d) A rod authored through a concrete wall sits in solid
cells. §2.2's convection "with each overlapped cell" then exchanges heat with concrete as though it were gas. Fix:
write the overlap rules (fuel against fuel; fuel against solid volume, as distinct from footprint air), and a world
ceiling on objects, segments, nodes and coupling rows, in data and checked in `Scene.from_dict`, `place` and the save
loader before allocation. Each needs a rejection test, and the repeated-`imagine` case needs its own.

### SHOULD-FIX

**N-S1. The region model can't hold "cells ∪ objects" as written.** `fire_model.md::§2.2`. On gates, a `Region` is a
cell mask, and `paint` → `_take_cells` gives each cell one owner. world_model §5 and §9 make that one u16
`region_id` array with `bincount` reductions. `client_rendering.md` §4 ships `region` per cell for picking. The
following changes are unstated:
- *Scenario 1:* a stick region whose sticks lie only in air cells owns no cells. `damage.region_integrity` returns
  `0.0` for an empty mask (line 90), so a pristine stick reads fully destroyed on the lab instrument.
- *Scenario 2:* the client picks the cell holding a stick and gets the room's id, or the room loses the cell.
- *Scenario 3:* each imagined fuel object is a region, and region ids are never reused (F10). A long session therefore
  exhausts u16.

Fix: define the region record (cells, objects, or both), the `region` channel's meaning for a cell holding
another region's object (F1: a new meaning gets a new name), the reductions over objects, and the id cap with a
refusal.

**N-S2. The pilot as a flame object contradicts stateless, derived flames, and the save drops it.**
`fire_model.md::§5.4`, `§4.1`, `§9.2`. Flames are "recomputed from segments each physics step… no flame state is
saved", ids are "the minimum member key", and the save lists flames as derived. The torch's pilot has no segments, a
prescribed Q, an end tick and an actor, so all of it is state. Three things are undefined: its key, whether it
clusters with burning segments (merging its Q into a cluster changes the cluster's height and partition), and its
place in the save. Tile §2.2's pilots table (`actor_id`, `region_id` u16, `end_tick`) and §3.2's `pilot_live`,
`region_gone`, `not_on_surface` and the receipt's "derived region" are all keyed by region, not by object id (u32).
`torch.yaml` (`radius_m ≥ 0.2`) and `actions.yaml` v1 (`min_radius_m = 0.2`) still encode the sphere deposit that §5.4
retires, and no version bump is named. *Scenario:* save mid-`kindle` and load: the pilot is gone, and the starter never lights. Name the pilot as a saved table (or a source row) keyed by `(actor_id, seq)`, its non-cluster
rule, and the revised pilots table, codes, receipt field and item and limits formats with their versions.

**N-S3. The new snapshot tables have no column specification, no size budget, and no client consumer.**
`fire_model.md::§9.2`. F1–F6 require per column a dtype, closed-vocabulary units, an offset, an integer key, and the
catalogue in `welcome` (tile §2.2's actor table is the form). v2 names the tables, `segment_glow` and the decoder fixtures, and nothing else. It
doesn't say how metric geometry is quantised (a rod's axis, a shrinking slab's thickness, the front position, flame
height), how recipe names become ids for the client (`welcome`'s catalogue, as for archetypes and items), or whether
`segment_glow` is a table column or a per-cell channel (the reduction question again). B5 gates snapshot size per
profile, and at §8.3's 52,000 parts a segment table published every physics step is hundreds of kB per frame,
unbudgeted. `client_rendering.md` isn't in §10.1. It still says "a fuel-bed cell draws as solid while it has fuel left"
and "flames from `burning`" at burning cells, so a stick in an air cell is drawn by nothing. Fix: column tables (dtype, units, offset/scale) for objects, segments and flames; the catalogue entries; a
snapshot-size budget at the R4 peak; and `client_rendering.md` §5 added to §10.1.

**N-S4. The new data files have no path, version, loader or log-header entry.** `fire_model.md::§9.1`. Only
`core.yaml` gets a version (v1). `chemistry.yaml` has none. Recipes ("game content") and variants have no file, no
version, no loader and no strict-loader statement. World_model §8 and tile §3.5 make the log header record "every
version… materials" and content digests. With four files and owners, "the material-data hash in the header" doesn't
say which. The refusal list has no entries for the recipe and variant contracts the spec relies on: range min > max,
non-finite or non-positive bounds, a range that admits geometry beyond a global safety ceiling (so content can't
authorise σ = 10⁶ m²/m³ and blow N-B2's budget), a variant default outside its bounds, and a geometry kind the
chemistry can't support. Nor does it say what `materials_v0_to_v1` changes, if v1's fields are "today's". *Scenario:* a recipe edit changes a range, and a replayed spec is refused with no header version to explain it.
Fix: path, version and strict loader per file; each file's version and digest in the log header and save header; the
recipe and variant refusals in §9.1's list.

**N-S5. Variants are bounded one by one, but the joint checks run only on base recipes.** `fire_model.md::§9.1`
("loadings whose joint volume exceeds the void"; "bulk density inconsistent"), `§9.2`. Variants are "the only knobs an
imagined object may set", and moisture, wax and kerosene are loadings. *Scenario:* a spec sets moisture and kerosene
variants, each within its own bound. Together they overfill the void, which the loader caught for the recipe and
`place` never re-checks. The liquid inventory then exceeds its retention cap, which §2.3 says must be "refused at
authoring" (dripping deferred). The same applies to mass: `Budget.max_mass_kg` uses `density_kg_m3` of a cell material
today, and must use bulk density plus the varied loadings. Fix: `place` and scene v2 run the joint-loading,
density-consistency and retention checks on the varied recipe, each with a rejection test.

**N-S6. Spec v1 and scene v2 leave structural objects and the name `wood` undefined.** `fire_model.md::§9.2`, `§7`,
`§9.1`. Spec v1 "names a recipe, a geometry kind". Today's `primitives` with a structural `material` (a steel beam, a
concrete block) have no place in it, and §10.1 says structure is never a fuel recipe. Either spec v1 keeps a structural
branch (then say so, and what its budget is), or imagining structure is withdrawn (then say so). Spec v0 has no persisted instance on gates; say "no migration needed". `wood` is a structural cell material in `core.yaml` v1 and presumably a component or recipe. The rule "one name
in two namespaces" either spans files, and refuses the shipped tables, or doesn't, and lets `material: wood` and
`recipe: wood` resolve to different things: WT-S8's "worse" case. Scene v1's crate is `material: wood, bed: {phi,
sigma}`, and the v1→v2 migration must name the recipe that becomes (F12: a literal or a registered function).

**N-S7. Saved object rows are validated only for size, and two pieces of state are missing.** `fire_model.md::§9.2`.
F14 requires "every saved cell value validated as the loaders validate data" and embedded specs re-run through
`place`. Objects are a new path into the world that bypasses `place` unless the save loader checks each row:
- the row traces to a scene primitive or a logged `imagine` (otherwise a save plants fuel objects no validator saw);
- the recipe admits the kind;
- inventories are finite and non-negative, and within the recipe's initial mass;
- the front lies within its segment;
- node counts are within the recipe's bound;
- geometry is within its authored range or a monotone shrink of it.

The **object id allocator** (u32, persisted) is state: replaying an `imagine` after load must mint the same id, and
the save doesn't carry the counter. **Coupling rows** are "recomputed in the topology batch". If that batch runs only on
topology change while geometry shrinks (PMMA, char), a loaded run recomputes them from current geometry where the
continuous run holds older weights, so save/load diverges. Fix: list the row validations with rejection tests; save the id
counter; declare coupling either state (saved) or derived each step (with a `derivation_version`).

### NIT

- **N-N1.** `fire_model.md::§9.1`: "ill-conditioned beyond a stated bound": the bound isn't stated. Name it (for
  example, a condition number) so the refusal test has a number.
- **N-N2.** `fire_model.md::§5.4`: "R3's sticks at 0.75–1.5 cm separate by more than that" misreads the tie rule. The
  tie compares the point's two distances, not the sticks' separation, so a point at any contact line (the starter
  under a stick, a stick on the crate) always ties. Tile §3.2's "no deeper than 50 mm inside" was dropped, and a point
  inside a porous `bed` has no nearest-surface rule.
- **N-N3.** `fire_model.md::§8.1`: "the tick status" is a `tick` field missing from §9.2's grammar entries.
- **N-N4.** `fire_model.md::§7`: scene v1 isn't coded (`SCENE_VERSION = 0` at 396ae10; `scene.py` has no `bed`). Dropping
  `bed:` from v1 before step 3b ships it would leave v2 nothing to migrate.

## 4. Checked and sound

No SEM field is added (`_compat.py` untouched). Steps 5 and 7 haven't landed on gates, so the landing order is
achievable. Gates' `_ALLOWED_PARAMS`/`AFFORDANCE_OF` are the only parse paths for `ignite`/`extinguish`.
