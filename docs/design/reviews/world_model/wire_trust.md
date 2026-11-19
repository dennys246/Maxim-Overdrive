# Wire integrity and Trust boundary review: the world model (design v3 part 1, draft, 66310f4)

Lenses: Wire integrity and Trust boundary (`docs/code_review.md`). Design: `docs/design/world_model.md` at 66310f4,
mostly §1.1, §5 and §8, plus the fold table. Earlier records read: `world_v2.md` §8, `realtime_lanes_coop.md` §2.2,
§2.3, §4.4 and §7, and `reviews/world_v2/wire_trust.md` (F1–F18, N1–N4). Code read for "before":
`.worktrees/act-validation` at 2f200b5 (`config.py::RigProfile`, `MaterialTable.load`, `ActionLimits`,
`world/grid.py::MaterialGrid.empty`, `world/scene.py::_check_no_solid_overlaps`, `world/world.py::snapshot`,
`sem_env/bridge.py`, `imagination/spec.py::place`, `data/rigs/*.yaml`, `data/world/actions.yaml`, `tests/conftest.py`,
`tests/test_act_validation.py`). I also checked the research's `wood_flaming` example
(`research/states_of_matter/architecture.md`).

None of the v3 contracts exist in code yet, so "after" means what the design says.
Counts: **3 BLOCKER, 12 SHOULD-FIX, 5 NIT.**

## Contract tables

### The rig profile becoming a rendering tier (§1.1, D20)

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| `data/rigs/*.yaml`, `config.py::RigProfile` | `name`, `cell_size_m`, `min_substeps_per_turn` (v1/v2 plan `substeps_per_physics_step`, v2 `memory_budget_mb`), `full_res_radius_m`; a loose loader: extra keys ignored, a missing key raises a bare `KeyError` → "rendering tiers: how much of the snapshot the client draws, and at what detail". **No fields named, no new home for the physics fields** | `World.from_scene(rig)`, `MaterialGrid.empty(rig)` (dx and shape), `World.advance` (`min_substeps`), `tests/conftest.py` (`FAST_TIERS`, `ALL_TIERS`), `test_cross_tier.py`, `test_heat.py`, `test_determinism.py`, `test_act_validation.py::test_every_shipped_rig_is_at_least_as_fine_as_the_smallest_action` (globs `data/rigs/`), `welcome` (v1: "the rig, `dx`"), the log header (v1: rig hash), the save (v2: "tied to one rig's cell size"; v3 §8: "validated against the scene and rig") | every one of them still reads physics from the rig. The design doesn't say which of them move to the truth resolution, which to a verification-grid parameter, and which drop the rig (WT-1, WT-4, WT-5) |
| Truth resolution, 0.1 m | none → "0.1 m base cells" (§1.1), owner question Q1 | grid build, save shape check, log header, `welcome`, frame `grids.cells.cell_size_m`, `SensorReading.extra["cell_size_m"]`, `ModulatorResult.metadata["cell_size_m"]` | no stated home (code constant? world config?), version or hash (WT-1) |
| "Coarsest rig" | `max(cell_size_m)` over `data/rigs/` = 0.2 m → undefined (the 0.2 m grid is now a verification grid) | CLAUDE.md thin-feature rule; `MaterialGrid.empty` extent alignment; `actions.yaml` `min_radius_m` and `min_sigma_m` and their test; F13's zone alignment grid | each rule silently changes its threshold or goes vacuous (WT-5) |
| `full_res_radius_m` | reserved: "cells beyond this from any agent may run coarser" → unmentioned | none yet | a machine-dependent resolution lever, which D21 forbids (WT-1) |

### Formats and messages (§5, §8)

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| `temperature_c` channel on air cells | `snapshot()`: cell temperature (air takes part in conduction today) → "stays cell temperature", but gas lives only in zones (v2 §2.1 stands) and air may leave the conduction solve (§4) | the Godot client, the SEM `temperature_mean` and `temperature_max` sensors on **air regions** (`bridge.py` builds a `RegionSensor` for every region, rooms included) | a value with no producer that tracks anything physical: the old name with an undefined meaning (WT-2) |
| `crack` | `1 − integrity` → unchanged; mean strength gets a new channel | client | consistent with F1 |
| SEM `integrity` sensor | mean of integrity → v2 said "becomes mean strength"; v3 says nothing | NPC learned links, by name | unknown (WT-13) |
| `extinguish` / `douse` | `parse_action` `extinguish {}` → retired; `douse` "with caps" | NPCs, clients, `act_result` readers, the intent log, `actions.yaml` | no params, caps, retire code, version bump or PR (WT-13) |
| Frame header | v2 grammar → plus: refuse a missing required channel; tables and grids follow the channel rule; column-major tables; refuse a "catalogue hash" mismatch | Python decoder, GDScript decoder | mostly folded; the "catalogue hash" is undefined and the materials hash is dropped (WT-11) |
| Per-face table | none → keyed by (cell index, face 0–5) | codec, save loader, fuel PRs | composite key against F4's single integer key; cell index undefined; no validation rule (WT-9) |
| Reserved `loose`, `packing_fraction` | none → declared, absent until Phase 2 | frames (fine as `required: false`), **saves** (no optional fields) | contradicts F5 unless a migration default is declared now (WT-10) |
| `region_id` and `regions_version` | per-region bool masks, names → u16 id array, ids never reused, version bumps "on every new region", "the protocol carries the change" | `welcome` region list, `act`, `act_result`, SEM entity ids, the save | removal doesn't bump; no transport named; the id counter isn't in the save (WT-7) |
| Zone and region names | one namespace (`act.region`) → "separate namespaces" | `act`, Maxim's `EntityMap` (one key space, `grid.entity_key`) | a collision that is legal in Overdrive and ambiguous in Maxim (WT-8) |
| Region CSG footprints | bounding box + centroid (`grid.Footprint`) → a CSG of boxes and cylinders, built from scene primitives and imagined specs | reach checks per `act`, fire placement, the overlap rule, the save (derived?) | no caps, no exact rule for touching, no derived or persisted status (WT-12) |
| Save v0 | none → no optional fields; embedded copies compared, never executed; also re-validated through `Scene.from_dict` and `spec.place` | save loader | the two rules contradict each other for the scene and specs, and `spec.place` refuses a legitimate save (WT-6) |
| Intent log header | v1: code SHA, versions, hashes of scene, rig, material table, world config, roster, seed → plus vocabulary, scene format, action limits, registry, numpy, scipy, BLAS, platform, dirty flag | replay loader | no rule for which mismatches refuse and which only report; "canonical serialisation" of what; truncated logs (WT-3, WT-14) |
| `data/world/fields.yaml` (registry) | v2 PR 3 → no PR in §10, no loader rules in §8 | codec, save, memory check, lints | unowned (WT-11, WT-15) |

## Findings

**WT-1. BLOCKER: §1.1 makes the rig profiles rendering tiers, but they still carry the physics, and the design names
no new home for it.**
Location: §1.1, §8 ("validated against the scene and rig"); `config.py::RigProfile`, `data/rigs/*.yaml`,
`world/grid.py::MaterialGrid.empty`, `world/world.py::World.advance`; v1 §2.3 (`substeps_per_physics_step` is a rig
field), v1 §4.4 tier 1 ("same scene, rig, world config and log").
Today a rig decides `cell_size_m` (the grid), the substep count (the bits of every heat step) and a reserved
`full_res_radius_m` ("cells beyond this from any agent may run coarser"). v2 added `memory_budget_mb`. §1.1 says only
that `laptop`, `rig` and `max` become "how much of the snapshot the client draws". If the files keep their physics
fields:
- a host at the `laptop` tier with `substeps_per_physics_step: 1` and a host at `max` with 6 produce different bits
  from the same scene and log, which is D20's failure;
- a save "validated against the scene and rig" written by a laptop-tier host is refused by a max-tier host, or, if
  the check reads `cell_size_m` from the tier file, it compares against 0.2 m and refuses every save;
- the log header hashes the rig (v1), so a bug report doesn't replay for an owner who renders at another tier.

`full_res_radius_m` is the one lever D21 forbids: resolution chosen by distance to an agent, which differs between
machines. It must be deleted, not carried along as "reserved".
Fix: split the contract, and say so in §1.1:
- truth resolution and substeps per physics step go into world config (`data/world/`), integers (for example cells
  per metre, not a float `0.1`), hashed into the log header and bound into the save;
- the verification grids (0.2 m and 0.05 m) become parameters of the verification harness in `tests/`, never
  shipped files a server can load;
- the rig YAML becomes `rendering tier v1`: versioned, read by the strict loader, rendering fields only. An old rig
  file with `cell_size_m` is refused with a message naming the move;
- `memory_budget_mb` describes the machine, not the world, so it goes in server config and never into a hash;
- `full_res_radius_m` is removed.

Producer → consumer migration list for `phase1/sim-clock`: `World.from_scene`, `MaterialGrid.empty`, `heat.step`
callers, `conftest.py`'s tier fixtures (which become verification-grid fixtures), the three cross-tier test files,
`test_every_shipped_rig_is_at_least_as_fine_as_the_smallest_action`, `snapshot()["cell_size_m"]`, the two SEM
`cell_size_m` metadata keys, `docs/architecture.md`'s resolution section, CLAUDE.md's resolution rule and thin-feature
rule, and the v1 `welcome` fields.

**WT-2. BLOCKER: "air cells' `temperature_c` stays cell temperature" keeps a name whose producer no longer exists.
That is F1's failure again.**
Location: §8 F1 bullet; §2 (v2 §2.1 stands: "no gas in cells"); §4 ("air leaves the conduction solve");
`world.py::snapshot`; `bridge.py::RegionSensor` (`temperature_mean`, `temperature_max` on every region, air rooms
included).
Once gas lives in zones, nothing in the air cells carries the gas's heat. Either the cells still conduct, in which
case their temperature is a second, unphysical gas state that disagrees with the zone, or they leave the solve and
freeze at ambient. Scenario: a room at 600 °C in its zone. A v0 client draws its air from `temperature_c` as 20 °C,
and the SEM `temperature_max` sensor on the room region reads 20 °C, so an NPC standing in the fire learns the room is
cool. The name, dtype and bytes are unchanged and the meaning is gone, which is exactly what F1 forbids. The fold
table sends S8 (`temperature_max`) to "§8 (identity)", but §8 doesn't say what `temperature_max` reads over air.
Fix: state the producer for air cells, and make it an identity:
- either `temperature_c` is defined over solids only, with a declared fill value for air (not NaN, which the codec
  refuses), plus an `is_solid` mask the client already has from `material`;
- or the channel is retired and replaced by `solid_temperature_c`, with the zone temperature as a zone column.

Either way, the SEM region sensors over air regions read the zone through `gas.over(mask)` (§2's interface) under
new names, and the old names on air regions are retired. A fixture test then holds that an air cell's `temperature_c`
is the declared fill.

**WT-3. BLOCKER: the fold table claims more than §8 folds. Eight F rows are partial and four findings have no row.**
Location: "Fold table"; the document's own A-B1 rule ("v2 claimed folds it hadn't made; this part carries a fold
table so the claim can be checked").
The audit is below. In short:
- partial: F1, F6, F7, F8, F10, F11, F12, F13, F15 and F16;
- in neither the table nor "Not in this part": F17 (vocabulary version consumer), F18 (`world_set_axis`) and N1–N4.

F17 and F18 plausibly belong to part 2, but the table says it lists "every v2 finding within this part's scope" and
names what's out of scope, and these appear in neither list. This is v2's A-B1 BLOCKER again, in the table built to
prevent it.
Fix: mark each row full or partial, and point each partial row at its finding below. Add F17 and F18 to "Not in this
part" (part 2), and N1–N4 to a row of their own.

**WT-4. SHOULD-FIX: the design doesn't say whether a rendering tier is server-side or client-side, so `welcome`,
`hello` and the shared snapshot are undefined.**
Location: §1.1; v1 §7 (`hello {protocol, token}`, a closed schema; `welcome` carries "the rig, `dx`"; snapshots
"encoded once per published tick and shared", CP-8).
- If the server downsamples per tier, CP-8's single encoding becomes one per tier, `hello` needs a `tier` field (a
  closed-schema change), and a session's frames carry a `cells` grid whose `cell_size_m` differs from `welcome`'s
  `dx`. That needs F6's "frame descriptors are authoritative for decoding" made explicit.
- If the client decimates, the tier never reaches the wire, and `welcome`'s `rig` field must go, or a client reads
  the host's tier as its own.

Fix: choose client-side level of detail (the simulation is identical everywhere, so the server has no reason to know
the tier). The server sends one truth frame. `welcome` drops `rig` and carries the truth grid. The tier is client
config only, never logged or hashed. State the frame budget for the full truth frame per tile in B5 (N4).

**WT-5. SHOULD-FIX: "the coarsest rig" is a threshold in four rules, and after D20 it has no referent.**
Location: CLAUDE.md ("thin features must be at least two cells of the coarsest rig"); `grid.py::MaterialGrid.empty`
(extents in multiples of the coarsest rig's cell); `data/world/actions.yaml` (`min_sigma_m: 0.2`, "at least the
coarsest rig's cell"); `test_act_validation.py::test_every_shipped_rig_is_at_least_as_fine_as_the_smallest_action`;
§8 F13 bullet ("grid alignment checked in integers", with no grid named).
If tier files lose `cell_size_m`, that test raises a `KeyError`. If they keep some value, it checks a rendering
number. The thin-feature rule drops from 0.4 m to 0.2 m if someone reads "coarsest" as the 0.1 m truth, and the
0.2 m convergence grid then sees one-cell walls.
Fix: name the coarsest verification grid (0.2 m) in world config as the alignment and thin-feature quantum, rewrite
the test against it, and update CLAUDE.md's rule in `phase1/verify` with §1.1's other rule changes.

**WT-6. SHOULD-FIX: the save's embedded scene and specs are both "compared, never executed" and "sent back through
`Scene.from_dict` and `spec.place`". `spec.place` would refuse legitimate saves.**
Location: §8 F5 and F14 bullets; `imagination/spec.py::place`.
§8 lumps "registry, scene and specs" under "compared, never executed", then sends the scene and specs back through
the live validators. For placed specs the save holds the only copy, so there is nothing to compare against. And
`place` is contextual: it refuses "that space is occupied" and "that space belongs to …" against the grid it's given.
Scenario: an NPC imagines a crate where a wall was destroyed an hour earlier. On load, re-placing it against the
initial scene refuses (the wall is there), and re-placing it against the saved cells refuses (the crate is there). A
good save becomes unloadable. A loader that skips the refusal to make it load is the band-aid.
Fix: split the embedded copies by authority:
- compared by canonical hash, never used: the registry, material table, action limits and world config;
- re-validated input: the scene, through `Scene.from_dict`, and the specs, through a context-free
  `imagination.spec.validate` (shape, materials, size and mass budget), factored out of `place`, which then calls
  it.

Then check consistency: each spec's region id and CSG match the saved `region_id` cells within the CSG, refused
otherwise. Replace "a save from a newer build" with "a newer save-format or registry version"; builds have no order.

**WT-7. SHOULD-FIX: region ids are versioned only on creation, and the transport and persistence are unnamed.**
Location: §5 (F10 bullet); v2 F10's fix (`regions_version` in the frame header, a `regions` message or table, never
reused "within a world or across its saves", a refusal on exhaustion).
- "Bumps on every new region" leaves out removal. A burnt crate leaves the region list, the client still lists it as
  a target, and an `act` on it gets a refusal the client can't anticipate.
- "The protocol carries the change" names no field or message.
- Never reusing ids across a save needs the next-id counter in the save. Without it, a loaded world hands id 7 to a
  new object and an NPC's SEM memory of entity 7 attaches to the wrong thing.
- u16 exhaustion and id 0 ("no region") are unstated.

Fix: bump on any change to the region set. Put `regions_version` in the frame header and add a `regions` message
carrying the full list on change. Make `next_region_id` a required save field, and refuse imagination with "too many
objects" at 65535.

**WT-8. SHOULD-FIX: "separate namespaces" makes a zone/region name collision legal, and Maxim resolves both in one
key space.**
Location: §5 (F11 bullet); `grid.py::entity_key`; v1 §7 `act {region, action, params}`.
F11 asked for both remedies: `act` targets `{kind, name}`, *and* the loader refuses a name used by both. v3 keeps
only the first in spirit, and doesn't say how `act` names a zone at all if `act.region` can't. Zones become SEM
entities (v2 N1), and Maxim's `EntityMap` resolves names after `entity_key` normalisation in one space. A zone `Lab`
and a region `lab` are separate in Overdrive and the same entity to an NPC's tool call `vent lab`.
Fix: one entity namespace across zones, regions and imagined names, judged after `entity_key`. Scene v1 and
`spec.place` refuse a collision. `act` gains an explicit target kind (`region` or `zone`) in the closed schema. Test
an imagined object named after a zone.

**WT-9. SHOULD-FIX: the per-face table's key breaks F4's single integer key, and its rows have no validation rule.**
Location: §8 (DLP S-11 bullet), §3 (skins on every exposed face), §1.2 (Phase 2 refinement).
- F4, folded in the bullet above it, says a table has "an integer key column". A (cell index, face) pair is two
  columns.
- "Cell index" is undefined: flat in `zyx` order? Of which grid?
- A face between two cells has two names. Which cell owns an exposed face, and what happens to the row when the
  neighbour burns away or the owner becomes air?
- On load: a row whose cell is air, whose face isn't exposed, a duplicate key, or a key out of range. Each must be
  refused (F14).
- Size: about 53,000 exposed faces on the synthetic tile's walls at 0.1 m (528 m² / 0.01 m²), times the skin's
  values per face. That's a B5 row, and probably `required: false` and unsent for the client.
- Phase 2 refinement (D21) changes what "cell index" means. If the key is a 0.1 m flat index, refinement is a format
  change, against §7's promise.

Fix: key = `cell_flat_index * 6 + face` as `<u4` (or `<u8`), with `cell_flat_index` over the truth grid in `zyx`
order. The owner is the solid cell, rows sorted by key, and the validation rules above go in the save's refusal
list. Declare that refined cells (Phase 2) get their own grid and their own face table, so the 0.1 m keys keep their
meaning.

**WT-10. SHOULD-FIX: reserved channels "absent until Phase 2" contradict "a save has no optional fields".**
Location: §7 (reserved `loose`, `packing_fraction`), §8 (F5, F12).
A Phase 1 save has no `loose` field. A Phase 2 loader, under "no optional fields", refuses every Phase 1 save, or
someone marks the field optional, which reopens F5. §7 promises Phase 2 "without changing a format".
Fix: declare the reserved fields now with literal migration defaults (`loose: 0`, `packing_fraction` the solid
value), and test it with a Phase 1 save fixture loaded by a registry that has them present. Or store them from
Phase 1 (1 + 4 B/cell, about 3 MB per tile at 0.1 m). For frames, declare them `required: false`.

**WT-11. SHOULD-FIX: the strict loaders' rules are named but not listed, and the registry loader has none.**
Location: §8 (F8, F12, F13 bullets).
- **Material table (F8):** "the strict loader that `ActionLimits.load` has" covers repeated keys, closed sections and
  the version. F8's other refusals are absent:
  - unique names across solids, liquids and species;
  - ids unique and in range, air = 0, ids stable against the fixture (lint);
  - a species cap; append-only species (lint);
  - transition targets in the right namespace, with no cycle;
  - finite, physical values.

  The atom balance also needs a closed formula per species (soot, char, the pyrolysate), and §3's "both cited in
  data" needs a citation key in the closed key set.
- **`fields.yaml` (F12):** only the migration-default rule is folded. F12's refusal list (unknown container, grid,
  dtype, encoding, law, unit, ledger or process; duplicate names; `every_ticks` < 1; bad clamps; a cell field not per
  unit volume) appears nowhere, and no PR in §10 builds the registry (WT-15).
- **Scene v1 (F13):**
  - The required `version` field and what happens to a v0 (unversioned) scene aren't stated. Today `spec.place` goes
    through `Scene.from_dict` too.
  - Only zone counts are capped. F13 asked for caps on primitives, gaps and vents too, and the CSG (WT-12) makes the
    primitive cap the bound on per-`act` reach cost.
  - The grid the alignment is checked against is unnamed (WT-5).
  - Reservoir composition rules, vent and door area and aperture rules, and "on the boundary between its zones" are
    unstated.

Fix: carry F8's, F12's and F13's lists into §8, or cite them as the acceptance list for each loader's PR.

**WT-12. SHOULD-FIX: the region CSG is a new geometry contract with no caps, no exact overlap rule, and no stated
derived or persisted status.**
Location: §5.
- Today's overlap rule is strict `<` on boxes (`boxes_overlap`: touching isn't overlap). "True overlap" between a
  cylinder and a box must keep that boundary convention, and must be decided with correctly rounded operations only
  (+, −, ×, ÷, sqrt), or a scene loads on one platform and is refused on another.
- Each `act` evaluates point-in-CSG, at O(nodes). The bound is the primitive cap, which v3 doesn't state (WT-11).
- Imagined specs (LLM output) feed the CSG. Say that they are unions only (air is refused today, so they can't carve)
  and capped in primitives.
- Is the CSG saved, or derived from the scene and specs? If derived, it is under `derivation_version` (F15). If it
  goes in `welcome`'s region list for the client, it is a wire format and needs fixtures.

Fix: state all four in §5, and add them to `phase1/fuel-combustion`'s rejection tests.

**WT-13. SHOULD-FIX: F1 and F7 are folded as examples, not as rules.**
Location: §8 (F1 bullet, F7 sub-bullet); `bridge.py::_ALLOWED_PARAMS`, `RegionSensor` (`integrity`).
- F1 asked for one rule across every vocabulary: channels, table columns, SEM sensors, affordances and intent types.
  A meaning change gets a new name, and the old one is still produced or is retired and refused as unknown. v3 states
  it for "a channel's or sensor's name" and gives three examples, but drops the retirement rule. It also doesn't say
  what happens to the SEM `integrity` sensor, which v2 turned into mean strength. And its lint checks units only,
  where F1 asked for units, grid and encoding kind.
- F7 asked for `douse`'s params (rate, point or face, duration), caps (`max_water_kg_s`, per-intent mass), a
  `retired` error code for `extinguish` that names `douse`, an `ACTION_LIMITS_VERSION` bump, and replay refusing a
  pre-bump log. v3 says "with caps". No PR in §10 adds `douse` or retires `extinguish` (WT-15). Retiring it early
  leaves no way to stop a fire.

Fix: state the rule in general form. Name the SEM `integrity` sensor's fate: it stays mechanical integrity, and
`strength` is a new sensor. Specify `douse` and give it a PR (with zones, `phase1/fuel-combustion`, since it needs
O₂ and liquids), with the retirement in the same PR.

**WT-14. SHOULD-FIX: the log header grows without a mismatch rule, "all-or-nothing" refuses every crash log, and the
hash's input is unnamed.**
Location: §8 (F14, F16 bullets); v1 §7 (end marker).
- The header now records numpy, scipy and BLAS versions, the platform and a dirty flag, alongside format versions and
  hashes. If replay refuses on any mismatch (F16), a bug report never replays on another machine or after a numpy
  update. If it refuses on none, the format versions aren't checked. Across machines only the outcome class is
  promised.
- A crash, the most common bug report, leaves a log with no end marker. "Loading is all-or-nothing" read literally
  refuses it.
- "SHA-256 over a canonical serialisation" doesn't say of what. Over the YAML bytes, a comment edit refuses every
  log. F16 asked for canonical JSON of the validated, loaded object.
- Does v1's header (code SHA, scene, world config, roster and seed hashes) still stand alongside v3's list? With
  WT-1, the rig hash must go and the truth resolution must come in.

Fix: two classes of header field. Format versions and content hashes refuse, naming the field. Library versions,
platform and the dirty flag are reported in the replay result, and bit-identity is promised only when they match. A
truncated log replays up to its last complete, valid record and reports the truncation. A corrupt record mid-log
refuses the whole log. Hashes are SHA-256 over canonical JSON (sorted keys, floats as `repr`) of the loaded object.

**WT-15. SHOULD-FIX: §10 gives no PR to three contracts §8 depends on.**
Location: §10.
- The field registry (`fields.yaml`) and its loader: v2 had it in PR 3. In v3, `phase1/protocol`'s "generic grammar"
  and `phase1/sim-clock`'s memory budget both need it.
- The intent log v0 and its header: v1 had it in the protocol PR. v3's §10 rows 6 and 10 don't mention it, and the
  save (row 11) is "after the lanes".
- `douse` and the retirement of `extinguish` (WT-13).

Fix: name a PR for each. The registry probably belongs in `phase1/sim-clock`, since its memory budget needs bytes per
cell, and the log in `phase1/protocol`.

**N1. NIT:** the "catalogue hash" in the frame rule (§8) is a new term. F6 asked that both `registry.sha256` and
`materials.sha256` be refused on mismatch. A material table changed mid-session otherwise decodes `material` ids
with the wrong names and colours. F6's precedence (frame descriptors decode, the catalogue sets up textures) and F4's
"rows in key order" and "unknown column dtype refused only if required" also didn't make it into the bullet list.

**N2. NIT:** v2's N1 (which of `format.version` and `protocol` a reader refuses on; a save magic and `kind`, so that
a save fed to the frame decoder is refused) and N2 ("a new grid kind, table layout or units vocabulary bumps the
protocol") are unaccounted for. See WT-3.

**N3. NIT:** the memory budget is checked "from the header's declared shape". Check the declared shape against the
shape the scene and truth resolution produce first, then the budget. Cap the header length (a u32 near 4 GB) and the
JSON nesting depth before parsing (F14).

**N4. NIT:** after WT-1, `SensorReading.extra["cell_size_m"]` and `ModulatorResult.metadata["cell_size_m"]` are a
constant handed to Maxim. They mean nothing to an NPC and become wrong under Phase 2 refinement. Drop them in
`phase1/sim-clock`, and check that no consumer reads them (none in this repo today).

**N5. NIT:** the research's reaction key `extinguish_o2_mole_fraction` reuses the retired affordance word in another
vocabulary. Name it `extinction_o2_mole_fraction`, so a grep for `extinguish` finds only the retirement. The
`wood_flaming` imbalance §8 quotes is correct: 1 + 1.15 = 2.15 in, and 1.6 + 0.53 + 0.004 + 0.016 + 0.25 = 2.40 out.

## Fold audit: F1–F18 against world_model.md

| F | Asked | Lands | Verdict |
|---|---|---|---|
| F1 | one identity rule for every vocabulary; units in identity, closed; lint units, grid, encoding vs fixtures; retire or keep | §8 | **partial:** examples rather than a general rule; retirement rule missing; SEM `integrity` unaddressed; lint checks units only; `temperature_c` "kept" with no producer (WT-2, WT-13) |
| F2 | refuse a missing needed channel; non-default linear-scale fixture | §8 | **folded** |
| F3 | unknown tables and grids follow the channel rule; new grid kind bumps protocol | §8 | folded, except the protocol bump (N2) |
| F4 | column-major, per-column offset, integer key, rows in key order, no strings | §8 | folded, except row order and unknown-dtype columns (N1); the face table breaks the key rule (WT-9) |
| F5 | no optional fields; code authoritative; compare, never execute; refuse a newer version | §8 | folded, but contradicts the F14 bullet for scene and specs (WT-6), and the reserved channels (WT-10) |
| F6 | refuse registry or materials hash mismatch; descriptor precedence | §8 | **partial:** "catalogue hash" only (N1) |
| F7 | retire `extinguish` with a code naming `douse`; params, caps; version bump; replay refuses | §8 | **partial:** "with caps" only; no PR (WT-13, WT-15) |
| F8 | strict loader plus the full validation list; keyed by name | §8 | **partial:** strictness and naming only (WT-11) |
| F9 | fixed zone dtype; `max_zones`, `max_gaps` in world config | §8 | folded for zones; `max_gaps` missing (WT-11) |
| F10 | never reused across saves; exhaustion refused; `regions_version` in the header; a `regions` message | §5 | **partial** (WT-7) |
| F11 | `{kind, name}` targets and refusing a collision | §5 | **partial, and the chosen half makes collisions legal** (WT-8) |
| F12 | literal, `null` or registered migration; plus the `fields.yaml` refusal list | §8 | **partial:** defaults only (WT-11) |
| F13 | version and v0 rule; refusals at every level; integer alignment; caps on primitives, zones, gaps | §8 | **partial** (WT-11) |
| F14 | every loader untrusted; budget before allocation; shape, size, offset checks; header cap; cell values; re-validation; all-or-nothing | §8 | folded, except the header cap (N3); the re-validation bullet conflicts with F5 (WT-6); all-or-nothing vs crash logs (WT-14) |
| F15 | the digest is checked only under the same `derivation_version`; across versions, recompute and report | §8 | **partial:** the field exists, the rule doesn't |
| F16 | add versions; canonical JSON of the loaded object; refuse a mismatch naming the field | §8 | **partial:** versions added; hash input and refusal rule missing (WT-14) |
| F17 | vocabulary version on agent homes and in the roster hash | — | **missing from both lists** (WT-3); belongs in part 2 |
| F18 | world-owned body sensor declarations and checks | — | **missing from both lists** (WT-3); belongs in part 2 |

## Rejection paths the implementing PRs must test

Each refusal is loud (a named error or an `error` reply), leaves the world, the log and any half-built object
unchanged, and has a test. PR numbers are §10's. v2's list (`reviews/world_v2/wire_trust.md`, 1–47) carries over
under these PR numbers. These are the additions and changes from v3:

**`phase1/sim-clock` (4):**
1. An old rig YAML carrying `cell_size_m` or substeps: refused, naming the world-config fields (WT-1).
2. A rendering-tier file with unknown, missing or repeated keys, or an unknown version.
3. World config: the truth resolution not a positive integer, or its alignment to the 0.2 m verification quantum
   broken; substeps per physics step < 1.
4. A scene extent that isn't a multiple of the 0.2 m quantum, judged in integers (WT-5).
5. A scene whose cell count at the truth resolution (and at 0.05 m for the harness) exceeds the memory budget,
   refused before any allocation.
6. Imagination past the u16 region-id space: refused, never wrapped. Ids never reused after a destroy (WT-7).
7. `regions_version` bumps on both creation and removal.
8. `fields.yaml`: v2 items 17–20, under strict YAML.

**Material table v1 (5):** v2 items 10–16, plus:
9. A species without a formula, or a formula with an unknown element; a reaction whose atom balance fails
   (`wood_flaming` as written is the fixture).
10. A missing citation where §11 requires one.

**`phase1/protocol` (6):** v2 items 1–9, plus:
11. A frame whose registry hash or materials hash differs from `welcome`'s, each tested separately (N1).
12. `hello` with a `tier` or any other unknown field: refused, under closed schemas (WT-4).
13. `act` naming a zone through `region`, or a region through `zone`, or with no target kind (WT-8).
14. `act` on a region removed since the last `regions` message: refused with a code that names the change.
15. Intent log header: a format version or content hash mismatch refuses, naming the field. A library or platform
    mismatch is reported, not refused (WT-14).
16. A truncated log replays to its last valid record and reports the truncation. A malformed record mid-log refuses
    the whole log.
17. Hash stability: a comment-only edit to a YAML file leaves its hash unchanged.

**`phase1/zones` (7):** v2 items 21–27, plus:
18. A zone and a region (or an imagined name) that collide after `entity_key`: refused (WT-8).
19. Caps: primitives, zones, gaps, vents.
20. A wall between zones thinner than two cells of the 0.2 m quantum.
21. `temperature_c` over air: the declared fill value, never stale cell temperature (WT-2).

**`phase1/fuel-surface` (8a):**
22. Face table: a key out of range, a duplicate key, keys out of order, a row on an air cell, a row on a non-exposed
    face, a non-finite skin value (WT-9).

**`phase1/fuel-combustion` (8b):**
23. CSG overlap: touching faces accepted; any positive-volume overlap refused; a box against a cylinder at tangency
    decided the same way in a process with another hash seed (WT-12).
24. An imagined spec over the primitive cap; an imagined spec that tries to carve.
25. `douse`: v2 items 28–29, plus a water mass over the per-intent cap, and `extinguish` refused with `retired`,
    naming `douse` (WT-13).

**Save v0 (11):** v2 items 32–41, plus:
26. A save whose registry, material table, action limits or world-config hash differs: refused or migrated by name,
    never used.
27. An embedded spec that fails `spec.validate`. A spec whose CSG and saved `region_id` cells disagree. A legitimate
    spec placed after a wall was destroyed loads (WT-6).
28. `next_region_id` missing, or not above every id in `region_id` (WT-7).
29. A Phase 1 save loaded by a registry declaring `loose` and `packing_fraction` present loads through their literal
    migration defaults (WT-10).
30. A save bound to another truth resolution: refused, naming it (WT-1).

## Checked and found consistent

- **F2 is folded as asked:** a decoder refuses a frame missing a channel it requires, and a non-default linear-scale
  fixture catches a decoder that hard-codes 1/255.
- **F3's main rule and F4's layout are folded:** column-major tables with per-column offsets, an integer key and no
  strings. An old reader can therefore skip an unknown optional column without knowing its dtype.
- **F5's core holds:** no optional fields, the code's registry and loaders authoritative, and the embedded registry
  never executed. That closes the crafted-save allocation and loop attack, which was the BLOCKER.
- **F9 is folded for zones:** the dtype is fixed at u16 and counts are capped, so a scene edit can't change the wire
  format.
- **F12's core is folded:** migration defaults are literals, `null` or a registered function name, so no data file
  is executable.
- **F14's main bullets are folded:** the budget is checked before allocation, cell values are validated, intents go
  through the first-stage validator, and loads are all-or-nothing.
- **F13's float trap is quoted correctly:** `0.6 / 0.2` is `2.9999999999999996` in IEEE doubles, so alignment must be
  judged in integers.
- **"Units are part of the identity, from a closed vocabulary"** is the right rule (F1's main ask), and so is
  `douse` replacing `extinguish` rather than redefining it.
- **`crack` stays `1 − integrity`, with a new channel for strength:** F1 is honoured for that channel.
- **D20 removes a whole class of wire problems.** With one truth resolution, a save never has to choose between
  rigs, and v1/v2's "save tied to one rig's cell size" becomes "tied to the truth resolution". That is simpler and
  safer, once WT-1 names where the truth lives.
- **§6's integer counts make the save's derived-state check sound,** as F15 needed: a recompute can equal an
  incremental state bit for bit.
- **§9's region reductions are published once per physics step as a frozen object.** That fits the
  lanes rule that every message crossing a lane is frozen. It adds no wire field.
- **Sleeping chunks change no format,** because results are bit-identical with sleeping on or off. Dilation is
  reported through v1's `tick` message, which already carries the requested and effective scale.
- **The `_compat` mirror is untouched:** nothing in this part adds a field to `SensorReading`, `ModulatorResult` or
  `AffordanceSchema`.
- **The `wood_flaming` imbalance quoted in §8 is arithmetically correct** (2.15 in, 2.40 out).
- **`MaterialTable.__init__` already refuses** duplicate ids, a missing `air` at 0 and ids outside u8, and
  `_StrictLoader` exists to reuse, so §8's "strict loader" has a working model in code.
