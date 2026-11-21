# Wire integrity and Trust boundary: `fire_solid.md` (6.0–6.1)

**Design:** `docs/design/fire_solid.md`, staged in `.worktrees/fire-design` (read from disk). **Code:** gates at
396ae10, read-only, with `data/`, `tests/fixtures/` and the tests that pin formats. **Prior round:**
`reviews/fire_model/delta1_wire_trust.md`, with each finding's status given in §3.

**Counts:** 3 BLOCKER, 11 SHOULD-FIX, 5 NIT.

## 1. Contract table

| Contract | Producers before → after | Consumers before → after | Version or migration named? |
|---|---|---|---|
| `data/materials/core.yaml` | v0 → v1 | `load_materials`, `data.materials()`, 12 modules, `test_the_committed_v0_files_still_load` (`golden.by_name == shipped.by_name`) | `materials_v0_to_v1` is named; **what it changes isn't** (S4) |
| `chemistry.yaml`, `variants.yaml` | none → `data/materials/` | none → `load_chemistry`, `load_variants`; the shipped-data test (one reader **per directory**) | v1. No owner for cross-file references (S4); breaks the directory test (S5) |
| `content/recipes/*.yaml` | none → game content (`content/` arrives at step 8) | none → `load_recipes`; `data.py` has no locator | v1. No id rule, no file order (S3) |
| `data/world/limits.yaml` | none → new | an unnamed loader; `place`, scene, save | **no version, loader, gate row or header entry** (S5) |
| Scene | v0 (`SCENE_VERSION = 0`) → "v2 from v1" | `Scene.from_dict`, `build`, `World.from_scene` | v1 isn't coded; tile §1.3's v1 `bed:` has no v2 mapping (S6) |
| Imagined spec | unversioned `{name, primitives}` → v1 `{recipe, kind, geometry, variants}` | `place`, `test_imagination.py`, step 5's `imagine` record | v0 status and the structural branch undefined (S6) |
| `place` call, `CellStore` window | paints inside its own window, rollback covers channels and masks → rows "in the topology batch" | tests; `World.writing`, applier, laws | the return value and the rollback of tables are unstated (S8) |
| `Region` record | `cells`, `footprint`, `solid` → plus `fuel_objects` | applier, imagination, frames, bridge, damage, the test digest (hashes `region.solid`) | §2 below |
| `region_id` u16, cell `region` channel | **neither exists at 396ae10** → object and wire columns | — | depends on 5a, unstated (S1) |
| `CellFrame` / `Frame` | channels and regions → tables (unstated) | `snapshot(frame: CellFrame)`, `Frame.reading`, bridge | S9 |
| Snapshot | cell dict → plus `objects`, `segments` | `tests/test_snapshot.py`; the client decoder (step 7) | segments columns missing (S9) |
| Save | **none; save v0 is step 9** (tile §11) → "every table and the counter" | an unnamed loader | **no format, version, loader or golden** (B2) |
| Digest | `test_determinism.py::digest`, **no committed golden** → plus tables | the identity test | N1 |
| Log header | **none in code** → "path and SHA-256, as today" | replay (step 5) | contradicts boundaries §6.3 (S7) |
| Ledger lines | tile §5.4 names → new names | the 6.1 conservation tests | one line unnamed (N4) |
| SEM affordances (vocabulary) | `strike`, `ignite`, `extinguish` on solid regions → the same on fuel-only regions | NPCs through `StructureModulator.affordances` | B1 |

## 2. The occupancy consumers against the code

I searched `src/` for `.solid`, `is_solid`, `AIR_ID` and `.cells.any()`. §2 has 7 rows. These readers are missing
or mis-stated:

| Reader | In §2? | Effect on a fuel-only region or a cell holding fuel |
|---|---|---|
| `applier._check_region`'s second check, `cells.any()` ("is gone") | no | An object-only region has no cells, so it is refused as "gone" |
| `World._power_field`: `frac * grid.solid` | no | `ignite` is admitted, but the deposit goes to the floor or air, never the object |
| `damage.strike`, through the newly admitted region | "unchanged" | succeeds with 0 J absorbed |
| `damage.region_integrity`, `region_breached`, through `Frame.reading` and `RegionInstrument` | "unchanged" | pristine cardboard reads **integrity 0.0** (damage.py:89); N-S1 is open |
| `Frame.is_solid` / `Observation.is_solid` (the bridge reads these) | no | the protocol's meaning changes silently |
| `StructureModulator.affordances` | no | advertises three actions that act on nothing |
| `applier._on_region` ("solids can't overlap") | mis-stated as a refusal | §1.3 allows cardboard in the crate's footprint, so a point inside both is "on" both, and a strike aimed at the cardboard breaks the crate |
| `imagination._within_world_rules`: refuses any overlap with a solid **footprint** | "§1.3" | contradicts §1.3's "may sit inside an owner's footprint where air" |
| `imagination._voxelize`: `mask & grid.solid` | "§1.3" | a structural box painted over a cell holding fuel is admitted unless it reads `occupied` |
| `grid.destroy`, `damage.thermal_degrade` | no | a floor cell under a slab becomes air, and the contact rows aren't invalidated |
| the test digest's `region.solid`; `kindle`'s target derivation (fire_model §2.2, step 5) | no | one field's meaning changes; one consumer was dropped |

## 3. The prior findings (status read from this tree)

- **N-B1:** fixed (§1.2).
- **N-B2:** partly fixed. Open: coupling rows (S10), the same-step race (S2), the scene and save budget paths.
- **N-S1:** open (B1, S1).
- **N-S2:** deferred to 6.4. The author routed it in §7, and I accept it, because the cone spark is prescribed.
- **N-S3:** partly fixed (S9).
- **N-S4:** partly fixed (S4, S5, S7).
- **N-S5:** open. §5.2 has no joint loading, density or retention check on a varied recipe.
- **N-S6:** open (S6).
- **N-S7:** partly fixed. The counter is saved, but the rule is wrong (B2).
- **N-N1:** open.
- **N-N4:** open (S6).

## 4. Findings

### BLOCKER

**B1. The occupancy table is incomplete. As written, admitted actions do nothing, and a sensor lies.**
`fire_solid.md::§2`. §2 widens `_check_region` and the bridge's construction to object regions, keeps `damage`
"unchanged", and omits `_power_field`, `Frame.is_solid` and `affordances`.
- *Scenario:* an NPC gets the Entity for an imagined cardboard box and sees `ignite`, described as "Start a fire at
  this structure's surface". It calls `ignite` and gets `success=True`, but the sphere heats the floor, so this is
  a no-op behind a true receipt.
- `strike` succeeds with 0 J absorbed.
- `integrity` reads 0.0, so the NPC perceives a destroyed box.

Fix: a row per reader in §2 above.
- In 6.0, fuel-only regions get no `strike`, `ignite` or `extinguish` affordance, and `_check_region` refuses them
  by code until a target law exists.
- Integrity and breached over an object-only region are NaN or refused, never 0.0.
- The "gone" check joins objects.
- Each rule gets a test that fails when the rule is deleted.

**B2. The save has no format, and its rule refuses the saves its own test makes.** `fire_solid.md::§1.3`, `§5.3`,
`§6`.
- **No format.** Gates has no save, and tile §11 puts save v0 at step 9. The design names no version, loader, gate
  row or committed golden (CLAUDE.md asks for a round trip plus a golden), and doesn't restate F14 (budget from the
  declared shape, all-or-nothing) for tables.
- **The rule contradicts the test.** §1.3 requires inventories "≥ 0 that sum to the recipe's mass". After the first
  pyrolysis step that is false, so §6's "save at every step of a cone run" refuses every save after ignition. "The
  recipe's mass" is undefined anyway: it depends on geometry and variants.
- **Mass is stored twice.** It is held as object kg and as node density × volume, and no rule ties the two.
- **Coupling.** §1.1 says it is rebuilt from geometry, and §5.3 saves every §1.1 table. A save whose coupling rows
  disagree with its geometry deposits heat into cells the object doesn't touch.
- **Unchecked fields.** Node offsets past `len(nodes)` are an `IndexError` (a crash, not `ValueError`). Front
  position, part areas and node thicknesses aren't checked, and neither is counter > max `object_id`.

Fix:
- Say whether 6.0 builds save v0 (and amend tile §11) or round-trips tables in memory (and drop "save").
- Check initial inventories against initial geometry plus variants, and current inventories as ≥ 0 and ≤ initial.
- Make one mass representation authoritative.
- Make coupling derived (a `derivation_version`), not saved.
- Check offsets as monotone and in bounds, front ∈ [0, 1], areas summing, node thicknesses summing to the object's
  thickness, and the counter.
- Name each refusal and test it.

**B3. 6.0's material v1 breaks fire_model's landing order.** `fire_solid.md::§5.1` against `fire_model.md::§9.1`:
"Material data v1 and the object tables land before step 5's first log writer". fire_solid never says 6.0 lands
before step 5. *Scenario:* step 5 records replay goldens with a v0 material digest. 6.0 then bumps and splits the
files, and boundaries §6.3 refuses every step 5 log ("a content mismatch is refused, loudly"). The way out is either
regenerating the goldens or a header migration nobody has designed. Fix: state the order, or design that migration.

### SHOULD-FIX

**S1. `region_id` and the "unchanged" u16 `region` channel don't exist at 396ae10.** `fire_solid.md::§1.1`, `§2`,
`§5.3`. Regions there are `dict[str, Region]` of masks (`grid.py::CellStore._regions`), and world_model §5 and O34 put
ids in 5a. Also unstated:
- whether a fuel object makes a region (named under `entity_key`) or joins one;
- whether a scene's `fuel: region:` must already exist;
- spec v1 has no `name`.

*Scenario:* each `imagine` mints a never-reused u16 (F10), and a long session exhausts it with no refusal. Fix: the
5a dependency, the region rule, and an exhaustion refusal.

**S2. The world-limit and overlap checks race their own batch.** `fire_solid.md::§1.1`, `§1.3`. Rows enter "only in
the per-step topology batch". *Scenario:* two `imagine`s in one step each pass the check against the pre-batch
tables, and together they exceed a limit or interpenetrate. Fix: stage 2 counts the pending rows in log order, with a
two-in-one-step test for each rule.

**S3. Recipe ids have no stability rule.** `fire_solid.md::§1.1` ("resolved by name"), `§5.1`, `§5.3`. Nothing
declares ids, and fire_model's "recipe name map" in the save was dropped.
- *Scenario:* adding a recipe file renumbers the rest in glob order. A saved `recipe_id 3` then loads as another
  fuel, the client's column changes meaning, and glob order is filesystem-dependent.
- Duplicate names across files, and recipe/material clashes (`wood`), have no refusal.

Fix: declared stable ids, a name ↔ id map in the save header and `welcome`'s catalogue, and sorted loading.

**S4. Four loaders, and no owner for the references between them.** `fire_solid.md::§5.1`. fire_model §9.1's
refusals include "dangling references (a variant's recipe or key)" and "one name in two namespaces", which span three
files. §5.1 gives them to `load_chemistry` alone. *Scenario:* `variants.yaml` names a deleted recipe, every loader
passes, and the first `imagine` raises `KeyError` at stage 2. Fix:
- one catalogue constructor over all four loaded tables, all-or-nothing, with a gate row;
- the recipe and variant refusals listed (min > max, non-finite, a default out of bounds, a range past the world
  limits);
- what `materials_v0_to_v1` changes. The v0-golden test asserts `golden.by_name == shipped.by_name`, so migration
  must equal v1 exactly.

**S5. `limits.yaml` has no version, loader, gate row or header entry, and it breaks an existing invariant.**
`fire_solid.md::§1.3`. It is absent from §5.1's table. `test_every_shipped_data_file_is_at_its_formats_current_version`
keys readers **by directory** ("each data directory has one reader and one format"), so `data/world/` with two
formats and `data/materials/` with three fail it.
- Unsaid: whether the per-spec object, segment and node budgets live in `imagination.Budget` (code today) or here.
- Unsaid: what a scene or save over the *current* limits gets (it should be refused with a code).

Fix: a §5.1 row, a per-file reader table in the test, and a header entry.

**S6. The scene and spec version chain doesn't match the code or tile.** `fire_solid.md::§5.2`. `SCENE_VERSION = 0`,
and v1 (tile §1.3, step 3b part b) isn't coded. Tile's v1 makes the crate `material: wood, bed: {phi, sigma}`, cells,
while §1.2 says fuel is always an object, so "v1 scenes load unchanged with no fuel" is false for the planned
`alley_box.yaml`. Fix one of the two:
- drop `bed:` from tile §1.3 before 3b ships it;
- name, in v1 → v2, the recipe a `bed:` becomes (F12).

Also say whether structural imagination survives spec v1 (N-S6), and that the unversioned spec v0 needs no migration
because nothing persisted it.

**S7. The header entry contradicts boundaries §6.3, and "as today" is false.** `fire_solid.md::§5.1`. No header exists
in `src/`. §6.3 fixes "SHA-256 over a canonical serialisation of the loaded, typed value… so a YAML comment change
doesn't refuse a replay". A file-bytes hash plus a path refuses a replay after a comment edit or from another
checkout. Fix: canonical digests keyed by logical name (no path), plus `limits` and the recipe set (one digest over
sorted names).

**S8. All-or-nothing doesn't reach the tables.** `fire_solid.md::§1.1`, `§5.2`. `CellStore.writing` rolls back
channels and masks only (grid.py:132–140), and §1.1 doesn't say the tables join it. *Scenario:* a scene's third
`fuel:` entry fails after rows for the first two were written, leaving two orphan objects. Fix:
- tables are window-owned (fresh copies, committed whole);
- a mid-batch refusal test asserts the tables are unchanged;
- `place`'s new contract is stated (synchronous rows, or deferred, and what it returns).

**S9. Snapshot columns are incomplete, and one premise is false.** `fire_solid.md::§5.3`.
- `surface_temperature_c` is u8 "display-quantised as `temperature_c` is", but `encoding.snapshot` sends
  `temperature_c` as **float16**. A u8 in °C saturates at 255 °C, below PMMA's and pine's ignition temperatures
  (about 300–400 °C), so every hot object reads 255.
- `segments` has no columns.
- The arity of `geometry` per `kind`, and whether "f32, 1 mm" means rounding to 1 mm or f32 precision, are unstated.
- The `welcome` catalogue entry is missing.
- `snapshot` reads a `CellFrame`, which has no tables, and the frame's objects part isn't designed.

**S10. Coupling rows are unbudgeted, and their count scales with dx.** `fire_solid.md::§1.3`. `holds_fuel` is defined
by coupling rows naming any cell, air included. *Scenario:* a 3 × 3 m slab at 0.05 m allocates thousands of rows
after every budget passed. A row limit would refuse at 0.05 m what it admits at 0.2 m, a different outcome class.
Fix: bound coupling from metric area at the finest tier before allocation, or keep contact rows only and define
`holds_fuel` geometrically.

**S11. Refusals aren't named.** `fire_solid.md::§6` ("Loader, scene, spec and world-limit refusals, each one").
`imagine`'s refusals are agent-facing, so boundaries §5.4 wants closed codes (the step 3b part b enum). Name and test
each one:
- `unknown_recipe`, `kind_not_admitted`, `geometry_out_of_range`, `unknown_variant`, `variant_out_of_range`,
  `joint_loading` (N-S5);
- `overlaps_fuel`, `overlaps_solid`, `outside_world`, `spec_budget` and `world_limit` (each by which limit);
- `bad_axis` (rods "with any axis": non-finite or zero);
- `version_unknown`, per file.

`outside_world` matters most. A partly outside object has coupling rows to cells that don't exist, which is an index
crash or dropped contact, and today's `place` only catches an object entirely outside. Related: overlap "with a solid
cell" is judged on cells, which the centre rule voxelizes differently by dx. *Scenario:* a slab at z = 0.45 m on a
floor ending at 0.45 m is refused at 0.2 m and admitted at 0.1 m. Judge overlap on authored geometry, in metres.

### NIT

- **N1.** `§6`: no golden digest is committed (`test_determinism.py:83–85`), so "today's digests bit for bit" is a
  same-commit A/B. Say how empty tables add no bytes while §5.3 digests every table.
- **N2.** `§2`: `frames.CellFrame.reading` doesn't exist. It is `Frame.reading` (frames.py:124).
- **N3.** `§5.1`: tile §1.3 plans only `content/scenes/`, not recipes. `content/` arrives at step 8, `data.py` has no
  locator for it, and the wheel's `_data` doesn't ship it. Engine tests need an Apache recipe fixture.
- **N4.** `§5.3`: "the energy leaving with the gas products" has no line name, and tile §5.4's `Δ(skins)`,
  `open_air_loss` and `combustion` aren't said to be kept or replaced.
- **N5.** `§2`: `applier._on_region` decides point ownership and refuses nothing. Its real change is in §2 above.

## 5. Checked and sound

- §1.2 closes N-B1.
- The objects table is integer-keyed, string-free and column-major (F2–F4).
- `burning` stays reserved (F1).
- The id counter is saved.
- `_compat.py` is untouched.
- The loaders stay in `adapters/loaders.py`, the only input gate (`lint_inputs.INPUT_GATES`).
- Steps 5 and 7 haven't landed, so B3's order is still achievable.
