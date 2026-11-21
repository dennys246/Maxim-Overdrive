# Fire model v1: Wire integrity and Trust boundary review

**Design:** `docs/design/fire_model.md` at 54358fd. **Code:** `.worktrees/gates` at 396ae10, read-only. **Maxim:**
`sem.py` at the local `origin/main` ref 437ec7b1 (not re-fetched).

**Counts:** 5 BLOCKER, 11 SHOULD-FIX, 5 NIT.

## 1. Contract table

"Designed" means specified in `tile_and_client.md` or `client_rendering.md`, not yet coded on gates.

| Contract | Producers before → after | Consumers before → after | What each consumer gets, before → after | Migration or bump named? |
|---|---|---|---|---|
| Material table format (`data/materials/core.yaml`, `MATERIAL_TABLE_VERSION = 0`) | `loaders.load_materials` (flat `materials:` with id, ρ, c_p, k, fracture, degrade, colour) → species, components, transitions, reactions, recipes, variants (§9) | `heat.py` (`rho_cp`, `conductivity` by cell id), `damage.py` (`fracture`, `degrade_*`), `imagination._within_world_rules` (`density_kg_m3`), `scene` and `paint` (material names), `snapshot` (`material` u8), `color_rgb`, the committed fixture `tests/fixtures/formats/v0/core.yaml` | per-id lookup arrays → unstated. §9 has no section for the structural cell materials (concrete, steel, glass, drywall) that every one of these reads | "v1" only. No migration, no plan for the v0 fixture, no word on u8 id stability ("saves store them") |
| Species and component identity | none → listed "ordered" (§9; L3 §3: "index = position; saved in this order") | inventories in saves, digests and the log header | → identity by position, against world_model F8 | No |
| Scene YAML (`SCENE_VERSION = 0`; designed v1 with `bed: {phi, sigma_m2_m3}`) | authors, `Scene.from_dict` → elements with a recipe, slot, geometry kind (`slab`, `cylinder`, `bed`), thickness or σ and β | `Scene.build`, `_check_no_solid_overlaps`, `paint` | box or upright cylinder of one material → unstated | No |
| Imagined-object spec (`SPEC_KEYS = {name, primitives}`, primitives name a `material`) | LLM → recipe, geometry in metres, variants (§9) | `imagination.place`, the spec's content hash (`ip_and_licensing.md` §6), logged `imagine` records, saves (F14) | material name → recipe plus variants | No version (specs have none today) |
| Save format (save v0, uncommitted) | none → element table, patch table, inventories, ragged 1D node states, latches (§2.3.4) | loader (F14: budget before allocation, all-or-nothing) | → unstated beyond "latches are in the digest" | "before save v0" for inventories only |
| Cell store channels (`CellStore._channels`, four hand-named; `CellFrame` fields) | `MaterialGrid` → a registry plus element and patch tables inside the window (§10) | `frames.CellFrame.of`, `Frame.reading`, `damage.region_*`, `encoding.snapshot`, tests | four arrays → registry-driven set | Named as a rework; no order against step 5 |
| The `solid` predicate (`material != AIR_ID`) | `MaterialGrid.solid`, `CellFrame.solid`, `paint`'s `solid=mid != AIR_ID` | `applier._check_region`, `StructureModulator.__init__`, `region_parts`, `imagination` overlap rule, `snapshot` (crack, glow × solid), `_power_field` | → unchanged, so a sub-cell fuel in an air cell is air | Not addressed |
| Snapshot channels (designed: `material`, `region`, `crack`, `surface_glow`, `burning`, `temperature_c`) and the Godot `frame_decoder.gd` | `encoding.snapshot` (today: `material`, `crack`, `glow`, `temperature_c`) → unstated | the Godot client (designed), goldens | skin and cell-fraction meanings → patch-and-slot meanings undefined; no element or flame table | No |
| Intent vocabulary | `parse_action` (`strike`, `ignite`, `extinguish`); designed vocabulary v1 adds `kindle`, retires `ignite` (T4) → NPC acts `light`, `apply`, `carry`/`drop`/`place`; `ignite`/`extinguish` kept "as lab and test instruments" | `StructureModulator.execute`, `Applier.apply`, the log (`kind_rank`), protocol v0 (T16) | → two vocabularies for one physics (player `kindle`, NPC `light` + `apply`) | No |
| `kindle` stage 2 (designed, tile §3.2) | applier → unstated | region derivation (50 mm of an authored box), deposit onto the 6b skin, item format (`power_w`, `radius_m`) | → 6b is replaced; the derivation rule is not revisited | No |
| SEM sensors | `RegionInstrument` (lab) → body flux per region (W/m²), skin and basal temperature, `health`, sight (§5.1) | Maxim receptors (MP-1, MP-2 pending) | → new names, units and ranges, none specified | Maxim asks named; names unnamed |
| SEM affordances and `_compat.py` | `StructureModulator.affordances` → body modulator acts using `requires` | Maxim tool generation, gating (`requires`), `target_effect` | → `requires` as "physical possibility" | Mirror: no field change, so no mirror change needed (checked) |
| Energy ledger lines (tile §5.4) | step 6 → §2–§4 laws | the ledger test, the closed forms | `Δ(skins)`, `flame_radiative` (`unreceived`), `combustion` → unstated | No |
| Intent log header (world_model §8) | records the materials version and hash → v1 | replay | → any log written before v1 is unreplayable unless migrated | No |

## 2. Findings

### BLOCKER

**WT-B1. Sub-cell fuel is air to every contract that reads cells.** `fire_model.md::§2.1`, `§10`.
Elements live "beside the dense grid", and the cell's structural owner is "as today". Every consumer on gates decides
"is there something here" by `material != AIR_ID`: `paint` sets `Region.solid` from it, `applier._check_region`
refuses "the X is air", `StructureModulator.__init__` refuses an air region, `region_parts` gives an air region no
modulator, `CellFrame.solid` gates `crack` and `glow` in `snapshot`, and `damage.region_integrity` reads
`material`/`original_material`. *Scenario:* the exit's kindling (20 mm sticks) and the wax starter sit in air cells.
`kindle` at a stick is refused at stage 2 because its cells are air. An NPC gets no `structure` modulator for it. The
client's raymarcher (which draws by `material`) shows nothing, and `burning`/`crack` are zeroed by `× solid`. The design needs (a) an occupancy predicate that counts elements,
and a list of every consumer that switches to it, (b) a defined region membership for elements (an element carries a
region id, but the `region` channel holds one u16 per cell), and (c) a wire table for elements and for flame objects
(world_model F2–F4 already give the table grammar: column-major, integer key, no strings). It names none of them.

**WT-B2. K = 2 slots makes acceptance depend on the grid spacing, and the exit scene exceeds it.**
`fire_model.md::§2.1` ("K = 2 slots, reserved in the format"), `§7`. *Scenario:* at the 0.2 m verification grid, one
cell at the crate's base can hold the crate's bed element, the cardboard packed inside, a leaned stick and the
starter: four elements. At 0.05 m the same objects spread over several cells and fit. Either the scene or `imagine` is
refused at 0.2 m and accepted at 0.05 m, which breaks the resolution rule (a spacing changes the outcome class), or the
excess is dropped silently, which is a partial change. The design names no overflow path and no refusal test. It needs
either a K derived from a bound that holds at the coarsest grid, or an overflow table, with a cross-tier test that
puts the exit's arrangement in one 0.2 m cell.

**WT-B3. Ordering species by position breaks world_model F8.** `fire_model.md::§9` ("species (ordered…)"), with
L3 §3's "index = position; saved in this order". world_model §8 F8: "species keyed by name, never by position".
*Scenario:* a later table inserts `co` before `co2`. With saves compared against the registry (F5), every existing save
is refused instead of migrated. With anything less strict, saved inventories land on the wrong species. Key species
and components by name, with a stable integer id in the file, and test a reorder that changes nothing.

**WT-B4. Imagined objects gain allocation dimensions with no budget.** `fire_model.md::§9` ("geometry in metres
and variants"), `§2.1`, `§8.3`. boundaries §5.4 requires budgets before allocation. `imagination.Budget` bounds
primitives, extent, mass and name length only. "No free number" is not true: thickness, σ and β are free numbers.
*Scenario:* an LLM spec names `cardboard` as a `bed` with σ = 10⁶ m²/m³ in a 3 m box, or a 3 m-thick `slab` whose 1D
nodes are "sized in millimetres" (about 3,000 nodes per patch). Patch and node counts, and flame-object counts, grow
without bound before any check. At 0.05 m a 3 m object is 216,000 elements. §8.3's cost estimate assumes 20,000
surfaces for the whole tile. The design must name per-recipe geometry ranges (refused, never clamped) and budgets on
elements, patches, nodes and surface area, all checked from the authored geometry before allocation, each with a
rejection test.

**WT-B5. The exit scene can't be written in any scene format that exists or is named.** `fire_model.md::§7`.
"Kindling leaned on a crate packed with cardboard" needs a tilted cylinder (the `scene.Cylinder` primitive is upright
only), and cardboard inside the crate's box. `scene._check_no_solid_overlaps` (and `imagination`'s copy of the rule)
refuses a later solid primitive whose box overlaps a named solid. Scene v1 (tile §1.3) carries `material` plus
`bed: {phi, sigma_m2_m3}`, with no recipe, slot or element geometry. *Scenario:* `alley_box.yaml` with cardboard in
the crate fails with "overlaps the named solid crate". Name scene v2 (element primitives, orientation, recipe, slot), its
migration from v1, and the change to the overlap rule (an element may sit inside an owner's footprint), with tests.

### SHOULD-FIX

**WT-S1. Material table v0 → v1: the existing consumers have no stated source.** `fire_model.md::§9`. The v1
sections (species, components, transitions, reactions, recipes, variants) have no home for concrete, steel, glass and
drywall as cell owners, nor for `fracture_energy_j_m3`, `degrade_*` and `color_rgb`, which `damage.py`, `heat.py` and
the client read by u8 id. *Scenario:* v1 lands, `MaterialTable.rho_cp` has no source for concrete, and the floor's heat
step has nothing to read. Say whether v1 keeps a `materials` (structural) section beside the new ones, whether u8 ids
stay stable, and whether `tests/fixtures/formats/v0/core.yaml` migrates (a registered `materials_v0_to_v1`, like
tile §3.2's `actions_v0_to_v1`) or is refused loudly with a test.

**WT-S2. The loader's refusal list is incomplete.** `fire_model.md::§9` ("The loader refuses"). It drops a rule L3
§3 had, and omits several that the gate contract (boundaries §5.4) implies. Each needs a rejection test:
- recipe component fractions summing to 1 (in L3, missing here);
- dangling references: a reaction whose reactant, yield or `consumes` names an undefined component or species, and a
  variant naming an undefined recipe or key;
- one name in two namespaces (a component and a species both `water`);
- sign and range on kinetics: a negative or zero `a_per_s`, a negative `e_j_mol`, or n < 0. With a negative A, §8.1's
  "exponential update" exp(−k·dt) grows, which creates mass;
- `void_fraction` outside [0, 1), a non-positive density, and bulk density inconsistent with Σ component densities ×
  (1 − void);
- the joint cap: moisture, wax and kerosene loadings that are each under void × ρ_L but overfill the void together;
- components without a formula: "atom balance for every species with a formula" leaves virgin wood, char and ash
  unchecked, so the reactions that matter most escape the conservation check. Require formulas (or elemental mass
  fractions) on every reacting component;
- a solved pyrolysate formula with a negative atom count, or two unknown formulas in one reaction (under-determined);
- the Hess solve: a singular or ill-conditioned system raises `numpy.linalg.LinAlgError`, not `ValueError`, which breaks
  "one exception type". Name the tolerance and the conditioning bound;
- a transition or reaction cycle that returns to its start with net heat.

**WT-S3. "Yields that don't sum to exactly 1" refuses valid tables, depending on order.** `fire_model.md::§9`.
In IEEE doubles `0.1 + 0.2 + 0.7 == 1.0`, but `0.7 + 0.2 + 0.1 == 0.9999999999999999` (checked). *Scenario:* the
same yields written in a different YAML order are refused. L3 said "to 1e-12". Specify `math.fsum` in key-sorted
order and a tolerance, and test both orders.

**WT-S4. "Lab instruments" leave `ignite` and `extinguish` reachable through the NPC gate.**
`fire_model.md::§5.4`, `§10`. On gates, `intents._ALLOWED_PARAMS` holds both, and `StructureModulator.execute`
accepts any affordance string that `parse_action` knows. *Scenario:* the two are removed from `affordances`, so the
tools disappear, but a hostile or hallucinated call `execute("ignite", {"power_w": 5000})` still parses and applies.
The design also contradicts T4 and F7, which already retire both from vocabulary v1, and an `ignite` lab source
deposits power into cells by `sphere_overlap` (`world._power_field`). That is a heat path the patches never see, so a
lab run with it doesn't test the shipped mechanism. Say where the instrument lives (a test fixture, or a host-command
kind with host-only authority, logged), remove both from `parse_action`, and add a refusal test through `execute`.

**WT-S5. `kindle`'s designed stage 2 doesn't survive sub-cell fuel, and the NPC acts split the vocabulary.**
`fire_model.md::§5.4`, and `tile_and_client.md` §3.2. Tile §3.2 derives the region as "the named solid whose
authored box surface lies within 50 mm"; two candidates is `ambiguous_point`. *Scenario:* R3c's sticks at gaps of
0.75–1.5 cm always give two candidates, so every `kindle` on kindling is refused. The deposit "onto the bed's skin
(6b)" is gone, since 6b is replaced. The torch item carries `power_w` and `radius_m`, while a starter is a recipe with
"its own cited flame", so the item format changes too. The player sends `kindle {point_mm, duration_ticks}` and the
NPCs `light` plus `apply`, which breaks boundaries §6.1 rule 1 (NPC and player intents share validators and the log)
unless one decomposes into the other. The lifecycle of a lit, held flame (what replaces `pilot_live`, its expiry, and
what happens on `leave`, on dropping it, or when the holder's cell burns) is unstated. Name vocabulary v2 (or amend
v1 before step 5 ships it), the log kinds and `kind_rank`, the derivation rule at sub-cell scale, and every new
stage-2 code.

**WT-S6. Snapshot channel meanings change, and world_model F1 says a new meaning takes a new name.**
`fire_model.md::§3`, `§10`. `surface_glow` is designed as "the envelope-layer skin temperature of the cell's exposed
faces", `burning` as "the burning fraction of the cell's fuel surface", and `crack` for a bed as its virgin fraction
(tile §5.5). With K slots and patches, the reduction is undefined: the maximum, area-weighted or owner-only? *Scenario:*
a cell holds glowing char on a stick element in an air cell; `surface_glow` is zero (`× solid`) or the stick's
temperature, depending on an unwritten rule, and the goldens' G3 (glow ≥ 15 L*) passes or fails on it. Define each
channel against patches and slots, rename any whose meaning changes, add the new units (kg/m³, W/m², fraction) to the
closed vocabulary, and give the Godot decoder fixtures for the new tables.

**WT-S7. The ledger's lines aren't enumerated, and two existing lines change meaning.** `fire_model.md::§2.3`
(invariant 3), `§4.1`. Tile §5.4's `Δ(skins)` becomes Δ(patch nodes) plus Δ(element inventories); latent lines
(fusion, evaporation) and the fines transfer are new; `flame_radiative.unreceived` loses most of its meaning, because
patches now receive radiation by view factor (this also revises T14, "the flame radiates into bodies by a point source
in Phase 1; into walls in Phase 2", and isn't listed in §10). With reference enthalpies solved per component (§9),
chemical energy is stored, so `combustion` as an input line is double-counted unless the bookkeeping changes.
§4.1 sends the convective part into "the zone (the outside reservoir)", but §4.2 says "the gas grid carries the
plume's energy", and world_model §2 has no gas in cells. List the lines.

**WT-S8. The imagined-object spec changes format with no version.** `fire_model.md::§9` ("Imagined objects").
`material` becomes `recipe`, plus `variants` and element geometry. `SPEC_KEYS` is closed and the content hash covers its
keys. *Scenario:* a save or log embedding a v0 spec (`material: wood`) replays through `place` (F14) after v1 and is
refused, or worse, `wood` resolves to a recipe of the same name with different contents. Version the spec. Say which
geometry kinds each recipe admits (`pmma_sheet` as a `bed`?), close the variant keys per recipe, and keep the bool
refusal (`finite_real` refuses `True`) under test.

**WT-S9. No order is stated against step 5's first log writer.** `fire_model.md::§10`, `§11` item 3. The log
header records the materials version and hash (world_model §8), and tile §3.2 used exactly this argument to avoid a v0
log for `kindle`. *Scenario:* step 5 ships the log writer on table v0; v1 lands in the ladder, and every committed
replay golden fails or needs a migration nobody planned. State that material table v1, the channel registry and the
element tables land before step 5's log writer, or name the log migration.

**WT-S10. The NPC acts lean on Maxim's `requires` and leave `target_effect` open.** `fire_model.md::§5.4`, `§5.5`.
In Maxim (`sem.py`, `AffordanceSchema`), `requires` maps sensor or integrity names to minimum floats, and a block
makes Maxim itself return a failure "explaining why", which goes into tool-failure credit. "Holding a starter, in
reach" therefore needs float sensors the body exposes (a holding sensor, a reach sensor), and the design names
neither. Separately, `target_effect` and `self_effect` write sensor deltas into bodies. *Scenario:* an act authored
with `target_effect: {thermal: …}` becomes the "second heat path into the body" that §5.5 forbids, with no check to
catch it. Name the sensors behind each `requires`, and add a test that refuses a fire act with a non-empty
`self_effect` or `target_effect`. The `_compat.py` mirror needs no change, since no field is added.

**WT-S11. The digest and save cover latches only.** `fire_model.md::§2.3` (invariant 4). The inventories, the
ragged per-patch 1D node arrays (node counts differ per material), the area retirements of §8.2, and the flame objects
if they persist (tilt, cluster identity) are all state. Otherwise two runs that differ in a node temperature share a digest.
A save loader that meets F14 needs a per-row node-count column, so it can check the budget
before allocation. Put every one of these in the digest and in the save schema.

### NIT

- **WT-N1.** `fire_model.md::header`: sources are cited as `research/fire_ladder/`. They live in
  `docs/design/research/fire_ladder/`.
- **WT-N2.** `fire_model.md::§10`: the rows retiring `ignite` and `extinguish` present as new decisions that T4 and F7
  already took. T18's `flammable` and `porous` sensors exist only on paper (no hit in `src/`), so say "the design
  revises" rather than implying code changes.
- **WT-N3.** `fire_model.md::§9`: "a threshold without its cited range". A loader can't check a citation, only a
  field. Name the closed provenance key it requires.
- **WT-N4.** `fire_model.md::§5.3`: say that the lab quantity `breached` (unit `bool`) stays.
- **WT-N5.** `fire_model.md::§2.1`: "reserved in the format": the save, the frame, or both?

## 3. What was checked and found sound

- The design adds no SEM fields, so `_compat.py` is untouched; MP-1 and MP-2 go through Maxim's process.
- "Refused, never clamped" (§9) matches `ActionLimits` and boundaries §6.1 rule 3.
- "A fruitless act succeeds" (§5.4) fits tile §3.4: no stage-2 code encodes an ignition outcome.
