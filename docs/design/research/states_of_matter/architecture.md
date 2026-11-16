# States of matter as the world model: an architecture that builds without rework

Research note for design v2 (successor to `docs/design/realtime_lanes_coop.md` v1), 2026-11-15. Read against
`.worktrees/act-validation` at `56eed51` (plus that worktree's uncommitted edits, which another session is making:
`Region(cells, footprint)` in `world/grid.py`), the v1 design and its 11 review files, `docs/architecture.md`,
`docs/roadmap.md`, `CLAUDE.md`, and the two earlier notes `signals/world_fields.md` and `signals/benchmarking.md`.
No repo file was changed. Measurements were run here, in numpy, best of 5, on a synthetic 16×10×4 m tile (four
rooms behind 0.4 m walls); the scripts are `bench.py`, `bench2.py` and `bench3.py` beside this file. Material
property values below are textbook orders of magnitude, given from memory, and must be checked before they go into
`data/`.

## The answer in one paragraph

Make **phase the container a quantity lives in, not a tag on a cell.** Solids live in rig cells, as today. Gases
live in **zones** (authored rooms, joined through measured **gaps**), and liquids live in **pools** held by zones.
A phase transition is then a **transfer between containers** that always carries mass and enthalpy together: a
steel cell that finishes melting leaves the grid and its kilograms and joules go into the zone's molten-steel pool;
wood that burns turns cell fuel and zone O2 into zone CO2, H2O, CO and soot plus heat; a frozen pool paints cells
back. This one decision does most of the work. Fluids become independent of the rig by construction, so the
resolution rule costs nothing for them and the dx⁻⁵ cost of per-cell transport disappears. It gives mixtures (air
with 2% CO), which Oxygen Not Included's one-element-per-cell model can't represent. It makes conservation a ledger
over a handful of containers that a test can close to round-off. And it keeps the per-cell state small: 21 saved
bytes per cell instead of 14 today. The tempting alternative, a per-cell phase tag with liquids and gases simulated
on the rig grid (the Noita and ONI shape), makes free surfaces and gas transport rig-resolution problems: expensive,
rig-dependent at every threshold, and impossible to mix. What has to be designed now is not the physics. It is the
container model, a **field registry** that drives the save, snapshot, digest and memory budget, a
**channel-generic snapshot and save grammar** with grids, channels and tables, **material table v1** with phases,
transitions and reactions, **authored zones in the scene format**, a **single choke point for cell mutation**, and
the **solid state variable** (temperature plus latent progress). All of these have to land before the first golden
fixture and save v0 are committed.

## 1. The data model

### 1.1 Containers by phase, each at its natural resolution

| Container | Phase | Resolution | Holds (state) | Why here |
|---|---|---|---|---|
| **Cell** | solid | rig cell (0.2 / 0.1 / 0.05 m) | material, integrity, temperature, latent progress, fuel | Fine geometry is what destruction, cracks and glow need, and it is what the rig buys. |
| **Zone** | gas | per authored zone (a room, the alley) | species masses (kg), gas internal energy | Well-mixed rooms are rig-independent by construction, cost O(zones), and have closed forms (CFAST and Barotrauma both live here). |
| **Pool** | liquid | per zone, per liquid | volume or mass per liquid (kg), pool enthalpy | The level comes from the zone's open-volume profile, so it is exact to the volume and needs no free-surface solver. |
| **Debris** | solid, loose | per zone, per material | kg and enthalpy of rubble | Today `damage.strike` deletes mass (`grid.destroy`); a conserved world needs somewhere for it to go. |
| **Gap** | (topology) | per zone pair | open area by height (m²), door aperture | Gaps carry the flows between zones, and their areas are measured from fine cells. |
| **Source** | n/a | entity | a spark or torch (J, W, sphere) | External heat only. A fire is no longer a source; it is cells that are burning (§1.5). |
| **Body** | n/a | per agent (Phase 4/5) | dose, breath, wetness | Accumulators belong to agents (mechanism E in `world_fields.md`), saved with agent homes in save v1. |

**The transfer rule** (a design rule for v2, with a test): every transition moves mass and enthalpy together from
one container to another, and **moves what the storage actually lost**. If fuel is stored as float32 and a burn
step computes 1.234 g in float64, the amount credited to the zone is `float64(old_f32) − float64(new_f32)`, not
the computed value. The ledger then closes to round-off even with float32 storage. The **budget test**: for every
element-like species and for energy, Σ cells + Σ zones + Σ pools + Σ debris changes by exactly the sources minus the
sinks plus the boundary flux, per physics step, at every rig. It replaces the heat-only check in `heat.heat_energy_j`
and closes two of today's known gaps by construction: "destroying a cell removes its heat with it" (the enthalpy
goes to debris) and the fuel gap (a fire can only release what its cells' fuel and its zone's O2 hold).

### 1.2 What a cell holds

| Field | dtype | Units (per unit volume) | Kind | Saved | B/cell |
|---|---|---|---|---|---|
| `material` | u8 | enum (the solid phase: steel, ice, char …; 0 = open) | state | yes | 1 |
| `integrity` | f32 | 1 | state, monotone without repair | yes | 4 |
| `temperature` | f64 | °C (K offset) | state, intensive | yes | 8 |
| `latent` | f32 | fraction of the next transition's latent heat absorbed, [0, 1) | state | yes | 4 |
| `fuel` | f32 | kg/m³ of combustible left | state, conserved via the ledger | yes | 4 |
| `original_material` | u8 | enum | derived (rebuild from the scene and placed specs) | no | 1 |
| `region` | u16 | id into a name table | derived | no | 2 |
| `zone` | u8 (u16 if over 255 zones per tile) | id | derived from authored zone volumes | no | 1 |

**State variable: temperature plus latent progress, not enthalpy.** This is the decision that has to come before
save v0, because it changes the meaning of an already-saved field. The enthalpy method is the right scheme, but a
solid cell only ever holds its solid phase (a cell that finishes melting leaves the grid), so H factors exactly into
(T, latent): below the transition H = ρc·T; at it, T = T_m and latent = (H − ρc·T_m)/L. Storing the factored form
keeps T, which is what conduction, sensors, glow and `degrade_*` read, and pays the inversion only where cells are at
a transition. Measured at max (5.12 M cells), the full H→T inversion with per-material gathers costs 63.9 ms
(bench2), against a heat substep of 97–183 ms (CP review). With the per-cell property arrays cached (v1 §2.3's
caching fix) and only 0.1% of cells at a transition, the correction costs 5.1 ms (bench3), about 4% of a substep.
The per-substep rule: compute ΔE per cell from the flux, as today. For cells where T + ΔT would cross T_m, or that
have latent > 0, put the energy into latent instead of T. A cell whose latent reaches 1 completes the transition,
which is a topology event (§1.6). This is also the cleanest place for the drywall and concrete heat sinks, whose
bound water leaves as steam (§1.4).

**Regions become an id array.** At `56eed51` each region is a full-grid bool mask (`regions: dict[str, Mask]`, and
still `Region.cells: Mask` in the uncommitted edit): 1 B per cell per region, 5.1 MB per region at max, so 50 named
objects cost 256 MB. `paint` already makes regions exclusive ("a later paint takes cells from any earlier region"),
so one `u16` array plus a name table holds the same information for 10 MB. `RegionSensor.value` also does
`g.temperature[mask]` over the full grid on every read (O(N), about 5 ms at max). At 10 Hz, with many NPCs reading
many regions, that is a hidden budget item. Cache region reductions per physics step, since cells change only on
physics steps and actions, and slice by the footprint's bounds.

### 1.3 What a zone holds (and its gaps and pools)

Zones are **authored in the scene in metres** as boxes aligned to the 0.2 m grid, and they partition the tile.
Anything unassigned belongs to a per-tile `outside` zone, which may be a reservoir with fixed composition and
temperature (the alley's open top). Membership is by cell centre, which is exact at every rig because the boxes sit
on multiples of the coarsest cell (the same rule `MaterialGrid.empty` already enforces for extents). Zones never
merge, so their ids, names, SEM entities and save keys stay stable. A breach makes a **gap** between two zones, not
a new zone.

| Table | Column | dtype | Units | Kind |
|---|---|---|---|---|
| zones | `name`, `id`, `kind` (closed / reservoir) | str, u8, enum | | authored |
| | `open_volume_m3` | f64 | m³ | derived, updated incrementally |
| | `species_kg[s]` for the fixed species list | f64 | kg | state |
| | `gas_energy_j` (or T) | f64 | J | state |
| | `pressure_pa`, `mole_fraction[s]`, `temperature_c` | f64 | | derived |
| | `upper_layer_*` (two-zone smoke layer) | | | reserved, not built |
| pools | `(zone, liquid)` → `mass_kg` | f64 | kg | state |
| | per zone `pool_energy_j` | f64 | J | state (one pool temperature per zone) |
| | `level_m` | f64 | m | derived from the zone's open-volume profile V(z) |
| debris | `(zone, material)` → `mass_kg`, `energy_j` | f64 | kg, J | state |
| gaps | `(zone_a, zone_b)` sorted, `area_m2`, `area_by_z_m2[]` (0.2 m bins) | f64 | m² | derived, updated incrementally |
| | `aperture` (door or vent entity, 0..1) | f32 | 1 | state, on the door entity |

The pool level comes from V(z), the zone's open volume below height z, built from fine cells (exact to the cell
volume, so it converges). It handles displacement for free: an imagined crate dropped into water removes open volume,
and the level rises without any extra code. The gap's area-by-height bins say whether a liquid can pass (a hole
above the waterline passes none) and drive Torricelli or orifice flow.

Sizes: 100 zones × (8 species + about 8 other columns) × 8 B is about 13 KB. Tables are negligible in memory and on
the wire.

### 1.4 How the material table grows (material table v1)

Today `data/materials/core.yaml` has no `version`, open key sets, and one property set per material
(`config.MaterialTable.load`). v1 adds a version, closed keys, and three namespaces: solids (cell materials, u8 ids,
stable forever), liquids (pool ids), and gas species (a fixed, ordered list, never an open dict, as the SS13 LINDA
lesson in `world_fields.md` says). Illustrative shape:

```yaml
version: 1
species:            # fixed order; index = position; saves and the wire store this order
  - {name: n2,  molar_mass_kg_mol: 0.028, cp_j_kgk: 1040}
  - {name: o2,  molar_mass_kg_mol: 0.032, cp_j_kgk: 918}
  - {name: co2, molar_mass_kg_mol: 0.044, cp_j_kgk: 844}
  - {name: co,  molar_mass_kg_mol: 0.028, cp_j_kgk: 1040}
  - {name: h2o, molar_mass_kg_mol: 0.018, cp_j_kgk: 2010, condenses_to: water, dew_c: 100}
  - {name: soot, aerosol: true, extinction_m2_kg: 8700}
  - {name: agent_a}  # two or three reserved slots for toxins and spill vapours
liquids:
  water:        {id: 1, density_kg_m3: 998, specific_heat_j_kgk: 4186, conductivity_w_mk: 0.6,
                 freeze: {at_c: 0, latent_j_kg: 334000, to_solid: ice},
                 boil:   {at_c: 100, latent_j_kg: 2257000, to_species: h2o}}
  molten_steel: {id: 2, density_kg_m3: 7000, specific_heat_j_kgk: 820,
                 freeze: {at_c: 1450, latent_j_kg: 270000, to_solid: steel}}
solids:
  air:   {id: 0}                      # "open": no solid here
  steel: {id: 2, density_kg_m3: 7850, specific_heat_j_kgk: 490, conductivity_w_mk: 50,
          fracture_energy_j_m3: 2.0e+8,
          melt: {at_c: 1450, latent_j_kg: 270000, to_liquid: molten_steel}}
  ice:   {id: 6, density_kg_m3: 917, specific_heat_j_kgk: 2100, conductivity_w_mk: 2.2,
          melt: {at_c: 0, latent_j_kg: 334000, to_liquid: water}}
  drywall: {id: 5, ..., bound_water_kg_m3: 170, dehydrate: {from_c: 100, to_c: 200, to_species: h2o}}
  wood:  {id: 4, ..., fuel_kg_m3: 600, burns: wood_flaming}
  char:  {id: 7, ..., fuel_kg_m3: 150, burns: char_glowing}
reactions:
  wood_flaming:
    ignite_c: 300                      # surface temperature (see §5, risk 1)
    burn_flux_kg_m2_s: 0.01            # per exposed area: the front regresses at flux / fuel_kg_m3, at every rig
    heat_of_combustion_j_kg: 1.5e+7
    o2_kg_per_kg: 1.15                 # about 13.1 MJ per kg O2 (Huggett); the loader test checks the ratio
    yields_kg_per_kg: {co2: 1.6, h2o: 0.53, co: 0.004, soot: 0.016}
    radiative_fraction: 0.3            # to nearby solids; the rest goes to the zone's gas
    extinguish_o2_mole_fraction: 0.15
    residue: {solid: char, kg_per_kg: 0.25}
```

What the loader checks (under B12, every rejection path tested): closed key sets; ids unique and in range; every
referenced phase, species and reaction exists; transition temperatures ordered (melt < boil) and finite; latent heats
non-negative; and **each reaction closes its mass balance**: 1 + o2 = Σ yields + residue, to 1e-9. A reaction that
creates mass is a data bug, refused at load. The 13.1 MJ/kg O2 ratio is a test on the shipped table (±10%), not a
loader rule, because a toxin reaction may break it on purpose. `fracture_energy_j_m3` and `degrade_*` stay as gameplay
calibration. `degrade_*` should shrink to "softening" once burning, melting and dehydration carry the physical
part, but keep it in v1 so the existing cross-tier numbers survive the migration (§4).

Glass has no true melting point. Give it a gameplay melt (about 1400 °C, a small L) and record that in Known gaps.

### 1.5 The field registry

The registry is **data, and a declaration**: it says what exists, so the save, the snapshot, the digest, the memory
check and the lints can all read it. It is **not** a plugin framework. Solvers stay concrete modules (`heat.py`, a
new `combustion.py`, `zones.py`), as `benchmarking.md` advises. One file, `data/world/fields.yaml`, versioned,
hashed into the log header:

```yaml
version: 1
grids:
  cells: {resolution: rig}             # the rig's cell_size_m
  topo:  {resolution: fixed, cell_size_m: 0.2}   # reserved: a fixed-resolution gas grid, chunk maps (§3.3)
fields:
  - name: temperature
    container: cell                    # cell | zone | pool | debris | gap
    grid: cells
    phase: solid
    quantity: {unit: degC, intensive: true}
    dtype: f64
    law: conserved_with_latent         # conserved | conserved_with_latent | sourced | monotone | derived
    saved: true
    default_for_older_saves: null      # null = no migration: an old save without it is refused
    snapshot: {channel: temperature_c, dtype: "<f2", encoding: float, clamp: [-273, 6000], required: false}
  - name: fuel
    container: cell
    grid: cells
    phase: solid
    quantity: {unit: kg/m3, intensive: true}
    dtype: f32
    law: conserved
    ledger: carbon_mass                # which budget it joins
    saved: true
    default_for_older_saves: material.fuel_kg_m3 * integrity
    snapshot: {channel: char, dtype: u8, encoding: {linear: {scale: ..., offset: 0}}, required: false}
  - name: species_kg
    container: zone
    phase: gas
    quantity: {unit: kg, intensive: false, per: species}
    dtype: f64
    law: conserved
    saved: true
    snapshot: {table: zones, columns: [o2_mole_fraction, co_ppm, soot_kg_m3], required: false}
processes:                             # §3.4: who steps what, how often, in what order
  - {name: heat,       every_ticks: 5, substeps: rig, reads: [...], writes: [temperature, latent]}
  - {name: combustion, every_ticks: 5, writes: [fuel, species_kg, temperature]}
  - {name: zones,      every_ticks: 5, writes: [species_kg, gas_energy]}
  - {name: pools,      every_ticks: 10}
```

Declared for every field: container, grid (rig cell, fixed metres or per zone), phase, unit and intensive or
extensive (**cell fields must be per unit volume; zone fields are extensive**, with intensive views derived from the
zone's volume), dtype, conservation law and the ledger it joins, saved or derived, the migration default for older
saves, and the snapshot channel or table column with its quantization and its `required` flag. Bytes per cell come
from the dtypes; caches and temporaries are declared per process. The registry is a frozen tuple in code after load,
in declared order, so iterating it is deterministic.

The lints this makes possible (under `scripts/lint_standards.py`): every saved field is in `digest()`; every field
with `law: conserved` has a budget test; every snapshot channel has a decode test on both sides (B3); the rig's
memory budget covers the registry (§3.1).

### 1.6 Topology: one choke point, incremental updates, the cost

Everything derived from topology (zone open volume, gap areas, pool V(z), caches for k and ρc, stability, chunk
dirtiness) is fed by **one mutation path**. Cells change material only through `MaterialGrid.set_material(mask, id)`
(today: `paint`, `destroy`, and `imagination.spec.place` through `paint`). It bumps `topology_version` and returns
the changed cells. v1 §2.3's cache version counter is the same counter, so build it once, in PR 2. The rule, with a
test, is the SS14 firelock lesson: **derived topology is brought up to date in the same substep as the change that
caused it.** Overdrive already fixed the same class of bug for heat (power recomputed after a substep that destroys
cells).

Incremental update for each changed cell: zone open volume ± dx³; for each of its six faces on a zone boundary with
both sides open, the gap area for (zone, neighbour zone) ± dx² (also binned by z); V(z) for its zone ± dx³ at its
height. That is O(changed cells), exact, and never relabels anything.

Measured full-recompute costs, for reference and for load and verification (this machine, bench.py):

| Operation on the 16×10×4 m tile | 0.2 m (80 k) | 0.1 m (640 k) | 0.05 m (5.12 M) |
|---|---|---|---|
| `ndimage.label` of all open cells | 0.6 ms | 3.8 ms | 28.8 ms |
| `bincount` reduction per zone (volumes, means) | 0.4 ms | 3.0 ms | 24.5 ms |
| open-volume fraction coarsened to the 0.2 m topo grid | 0.1 ms | 2.6 ms | 12.2 ms |
| label of one 2×2×4 m column (a local relabel) | 0.03 ms | 0.10 ms | 0.67 ms |
| label on the fixed 0.2 m topo grid | 0.6 ms at every rig | | |

Because zones are authored and never merge, labelling isn't needed on the hot path. It is needed for one thing
later: **sealed pockets** (a cavity blasted inside a thick wall, or a barricade that seals half a room). Do that on
the fixed 0.2 m topo grid (0.6 ms per tile at any rig) when a topology event touches a zone, and make a sealed pocket
a child zone with a deterministic id (parent, then lowest topo-cell index). Defer it, and record the gap: "a wall
built across a zone doesn't seal it; an interior cavity counts as its zone's volume".

## 2. Formats

### 2.1 One container grammar for the snapshot and the save

v1 §7 already frames a snapshot as `[u32 header length][JSON header][array bytes]`, little-endian, z-y-x axis order,
z-up, with a dtype vocabulary and refusal of unknowns. Keep that framing and make the header **self-describing and
channel-generic**: each array names its own grid, and per-zone data travels as **tables** with named columns.
Today's `world.snapshot` returns one `shape` and fixed keys (`tests/test_snapshot.py::test_snapshot_shapes_dtypes_and_metadata`
asserts exactly that), so every new field would be a protocol break.

```json
{
  "format": "mo-frame", "version": 0, "kind": "full",
  "protocol": 0, "tick": 1200, "world_time_us": 120000000,
  "registry": {"version": 1, "sha256": "…"}, "materials": {"version": 1, "sha256": "…"},
  "grids": {
    "cells": {"shape": [40, 100, 160], "axis_order": "zyx", "frame": "z-up", "cell_size_m": 0.1, "origin_m": [0, 0, 0]}
  },
  "channels": [
    {"name": "material", "grid": "cells", "dtype": "u8", "units": "enum:solid", "encoding": {"kind": "enum"},
     "required": true, "offset": 0, "stored_size": 640000, "size": 640000, "compression": "none"},
    {"name": "glow", "grid": "cells", "dtype": "u8", "units": "1",
     "encoding": {"kind": "linear", "scale": 0.00392157, "offset": 0.0}, "required": false, "...": "…"},
    {"name": "zone", "grid": "cells", "dtype": "u8", "units": "enum:zone", "encoding": {"kind": "enum"}, "required": false}
  ],
  "tables": [
    {"name": "zones", "rows": 4, "key": "zone",
     "columns": [{"name": "o2_mole_fraction", "dtype": "<f4", "units": "1"},
                 {"name": "temperature_c", "dtype": "<f4", "units": "degC"},
                 {"name": "level_m", "dtype": "<f4", "units": "m"}],
     "offset": 3200000, "stored_size": 48, "size": 48, "compression": "none"}
  ]
}
```

- **Encoding vocabulary (closed):** `enum`, `linear` (scale, offset, clamp), `float` (raw `<f2` or `<f4`), and `log`
  reserved for concentrations that span decades (CO in ppm). Each channel's declared quantization error must sit
  below the smallest difference that matters to an outcome it shows (`benchmarking.md` §2).
- **Unknown channels and columns:** a reader **refuses an unknown `required` channel and ignores an unknown optional
  one**. The writer takes `required` from the registry: required means a client that ignored it would draw something
  false. Adding an optional channel or column bumps the registry version, not the protocol. A new encoding kind,
  dtype, grid kind, compression or `kind` value bumps the protocol, and old readers refuse it loudly, as v1 §7 says.
- **`kind: "delta"` is reserved now, not built.** Its layout is per chunk: `base_tick`, plus per channel a list of
  chunk indices and their bytes. A client that doesn't hold `base_tick` refuses the delta and asks for a full frame.
  Chunks are 16³ cells at every rig. A chunk is wire-only and carries no physics, so its size in cells, not metres,
  is fine. The tile is 40 / 520 / 1300 chunks at 0.2 / 0.1 / 0.05 m. Dirty means the chunk's quantized bytes differ
  from the last published frame, which is exact and needs no bookkeeping. Compare cost at max is about 10 ms
  (estimate).
- **Header size** is about 2 KB with full descriptors: negligible against 0.6–41 MB of arrays, and worth it for
  `websocat` and fixtures. Static catalogues (zone names, the material table, the registry's channel list) also go
  in `welcome` (v1 §7 already lists the material table and regions there).
- **Godot side:** one texture per cell channel, as v1 says. Tables are small typed arrays. Partial updates of an
  `ImageTexture3D` are likely whole-texture in 4.7.2; keep a CPU-side mirror, apply deltas to it and re-upload.
  Verify this on the pinned engine before freezing the delta layout.

### 2.2 The save is the same grammar, lossless

A save is `kind: "save"` in the same framing (magic `MOSAVE\0` before the u32), with lossless dtypes (`<f8`, `<f4`,
`u8`, `<u2`) and only `saved: true` fields. Its header carries: the format version; the registry version and the
**registry, material table, scene (with zones) and placed imagined specs embedded in full**, not just hashed, so a
save is readable without the repo at that commit; the rig name and `cell_size_m`; the world config; the tick; the RNG
state (`numpy` PCG64's `bit_generator.state` is JSON-able); the entity tables (sources, doors with apertures); the zone,
pool and debris tables; and v1 A12's checkpoint items (queued records, thoughts in flight with their deadlines).
Derived fields (`original_material`, `region`, `zone`, gaps, V(z), caches) are **recomputed on load and checked
against a digest stored in the save**, which catches drift between the save and the derivation code.

- **Rig-bound:** a save loads only at its own `cell_size_m`, refused loudly otherwise. Conservative coarsening (sum
  the fine cells) is easy, but refinement is ambiguous. Co-op guests never need a save: they receive the host's
  frames.
- **Older registry versions:** a missing field is filled from its declared `default_for_older_saves`, or the load is
  refused if there isn't one. That keeps "add a field" from becoming a hand-written migration each time, and keeps
  "change a field's meaning" (temperature to enthalpy, say) a deliberate version bump with a migration.
- **The heavy-mode test** (Factorio FFF #315, from `benchmarking.md` L7): save at tick T, load, run to T + N, and the
  digest equals the uninterrupted run's, at every rig. This is what catches state the save forgot. Every field the
  registry marks `saved` is in it automatically.

### 2.3 Golden fixtures (B3, B4)

Committed under `tests/fixtures/wire/` and `tests/fixtures/save/`, decoded by Python and by the GDScript tests:
1. a full frame on an **asymmetric** 3×4×5 grid (a different value at each corner; v1 W-F4) with every v0 channel
   and a two-row zone table;
2. a frame with an **unknown optional channel and an unknown table column**, which a reader must decode, ignoring
   both;
3. a frame with an **unknown required channel**, which a reader must refuse;
4. a frame with an unknown encoding kind, and one with an unknown `kind`, both refused;
5. a save v0 that every later loader must still load, or refuse with a message naming the version;
6. an intent log v0 with its matching save checkpoint.

Old fixtures are never deleted. A change that breaks one needs a migration or a version bump.

### 2.4 How this fits v1's protocol and intent log

- `welcome` (v1 §7) adds the registry's channel catalogue, the zone list (id, name, kind, footprint) and material
  table v1 with phases. The client learns what "molten_steel" looks like from data.
- The `tick` message is unchanged. Zone tables ride on frames.
- `act` is unchanged in grammar. The affordance set will grow (open or close a door, pour, spray), and
  `extinguish` changes meaning: in the fuel model it can no longer pop a source (`StructureModulator.apply` does
  `sources.pop` today). It has to become smothering or applying water, which is physics. That bumps
  `ACTION_LIMITS_VERSION` and the affordance descriptions, and Maxim's tool text changes with them.
- The **intent log header** (v1 §7) adds content hashes for the registry, material table v1 and the scene format
  version. The state digest every N ticks walks the registry in declared order over saved fields and tables. A
  second digest of derived fields catches cache drift. Records are unchanged.

## 3. Determinism and performance

### 3.1 Per-rig memory budget

Per cell, for the phase model with v1's caching fix (16×10×4 m tile; estimates from dtypes, not measured):

| Item | B/cell | 0.2 m (80 k) | 0.1 m (640 k) | 0.05 m (5.12 M) |
|---|---|---|---|---|
| Saved state (material, integrity, temperature, latent, fuel) | 21 | 1.7 MB | 13 MB | 108 MB |
| Derived (original_material, region u16, zone u8) | 4 | 0.3 MB | 2.6 MB | 20 MB |
| Caches keyed by `topology_version` (k, ρc, three face conductances, T_m and L per cell), f32 | 24 | 1.9 MB | 15 MB | 123 MB |
| Solver temporaries (flux sum, per-axis flux, ΔT), f64, preallocated with `out=` | 24 | 1.9 MB | 15 MB | 123 MB |
| Frame: 8 channels at 1 B, plus temperature f16, plus the joined buffer | 18 | 1.4 MB | 12 MB | 92 MB |
| **Total** | **≈ 91** | **≈ 7 MB** | **≈ 58 MB** | **≈ 466 MB** |
| Today, for comparison (14 B plus 1 B per region, and transient peaks) | 14 + 1/region | 1.1 MB | 9 MB | 72 MB, plus 5 MB per region and about 300 MB peak in `heat.substep` |

Caches can be float32 without losing conservation. Exactness comes from the flux's antisymmetry (each face's `q` is
computed once and added to one side and subtracted from the other), not from the precision of the coefficient. A
fixed 0.2 m gas grid, if adopted later, adds about 40 B × 80 k = 3.2 MB per tile **at every rig**. Zone tables are
kilobytes. Proposed rig fields, checked at load against the registry's bytes × cells: `memory_budget_mb` of 128 /
512 / 2048 for laptop / rig / max, which is 3–4× headroom for one tile, or two tiles resident at max. Adding a field
then fails loudly at load on the max profile instead of swapping. Wire it into B5.

### 3.2 Per tick, per physics step, per substep, per event

| Cadence | Work | Cost driver |
|---|---|---|
| per heat substep (1 / 2 / 6 per physics step, v1 §2.3) | conduction over **solid cells only**; the latent correction; solid-to-zone surface exchange, h·A·(T − T_zone) | heat dominates: 1.5 / 12 / 97–183 ms full grid today (CP review). The latent correction adds about 5 ms at max (bench3). |
| per physics step (every 5 ticks, 0.5 s) | combustion over burning cells (sparse); zone exchange (§3.5); radiative share deposited near burning cells | sparse, plus O(zones²) |
| slower (every 10 or more ticks, declared in the registry) | pool evaporation and boiling, condensation, soot settling, later structural support | O(zones), or O(changed) |
| per topology event (in the substep that caused it) | incremental zone volume, gaps, V(z), cache rebuild over affected chunks, frame chunks dirty | O(changed cells) |
| per tick (0.1 s) | nothing in physics; frames rate-limited (v1: 2 Hz during a fire); SEM reads from cached reductions | O(1) per read |

Two things move in v1's cost model.

**First, X1's 453 ms `World._power_field` at max goes away, not just gets cached.** Fire power comes from burning
cells (burn flux × exposed area × ΔH_c), so it is sparse. The sphere-overlap deposit remains only for external
sources such as a spark or a torch, which v1's caching fix covers.

**Second, air cells leave the conduction solve.** The zone's gas exchanges heat with solid surfaces instead. That
removes most cells from the solve wherever the tile is mostly open, once the solve runs over active chunks or solid
bounding boxes. It is also a physics change: today's crate cross-tier numbers and `_power_field`'s "falls back into
air" path both depend on air conducting. It ships with a closed form (Newton cooling of a lumped block in a zone,
τ = ρcV/(hA)) and a cross-tier test, and the crate numbers in `docs/architecture.md` are re-derived, not carried over.

Surface area is counted from voxel faces, which overestimates a diagonal or curved surface by a factor (up to √3 for
a 45° plane, 4/π for a cylinder's side). That bias is about the same at every rig, so the resolution rule holds, but
record it in Known gaps with the numbers.

### 3.3 Fixed-resolution gas grid vs per zone

| | Per zone (recommended now) | Fixed 0.2 m gas grid (later, if a tile needs it) |
|---|---|---|
| Rig independence | by construction | by construction (the same 0.2 m grid at every rig, fed by measured open fractions; coarsening costs 0.1 / 2.6 / 12.2 ms full tile) |
| Cost | microseconds | 80 k cells × 8 species, about 1 substep per physics step at an eddy diffusivity of 0.01 m²/s: an estimated 10–15 ms per physics step |
| What it gives | well-mixed rooms, O2 starvation, smoke per room, flooding by level; closed forms | local gradients: smoke drifting down the alley, a fire starving locally, buoyant layering |
| What it lacks | gradients inside a room (until two-zone layers) | correct transport physics (diffusion is a stand-in for convection); more tests |

Design the **consumer interface** so the swap doesn't touch consumers. Combustion, SEM sensors and frames read gas
through `gas.at(zone)` and `gas.over(mask)` (a reduction), never a raw array. The wire grammar already supports a
`topo` grid channel beside the zone table. A two-zone smoke layer (CFAST) and the gas grid compete for the same job
("crouch under the smoke"). Decide between them in Phase 2 from a tile that needs one.

### 3.4 How v1's Simulation lane runs several processes on different periods

v1 §2.1 fixes the order within a tick: apply records, step agents, run physics on ticks where
`tick % physics_every_ticks == 0`, emit. Generalize step 3 to the registry's `processes` list:

```
for p in registry.processes:                 # declared order, fixed, hashed into the log header
    if tick % p.every_ticks == 0:
        p.step(world, dt_us = p.every_ticks * tick_us)   # integer interval; substeps = p.substeps(rig)
        world.flush_topology()                # events raised inside p are already applied (§1.6)
```

- Periods are integers in world config, so they are rig-independent. Only substeps scale with the rig, as v1's
  `substeps_per_physics_step` does. Slow processes therefore have the same time discretization at every rig, which
  is what the resolution rule needs.
- Every `every_ticks` must be a multiple of the base physics period (5), checked at load, so coupled processes always
  meet on the same tick.
- Strongly coupled processes (combustion, O2 and heat) share a period. Each consumes against the state at its start,
  **clamped by what is available** (a fire can never take more O2 than its zone holds), and transfers exactly (§1.1).
  Each operator conserves on its own, so operator-splitting order is a precision question that is the same at every
  rig.
- Rules for determinism inside the processes: species, zones and gaps iterate in sorted id order, never over a
  `set`. No `np.unique` over floats. Float reductions run over arrays of the same shape every run (pairwise
  summation is deterministic for a given shape, so chunk sleeping must decide its active set deterministically). The
  small zone linear solve runs in one thread, or as a fixed-iteration hand-written solve, because multithreaded BLAS
  isn't guaranteed bit-identical. Add `OPENBLAS_NUM_THREADS=1` to the hash-seed subprocess test and assert it.

### 3.5 Zone exchange, stiffness, and chunk sleeping

- **Zone exchange:** per physics step, build the zone-graph Laplacian from gap conductances Q_ij (an exchange
  coefficient × open area × aperture, plus buoyant doorway flow later) and take one **implicit** step,
  (I + dt·V⁻¹L) m′ = m. It is unconditionally stable when a wall is fully gone (a huge gap), conserves total mass to
  round-off because L is symmetric, and costs microseconds at 100 zones. Pressure is quasi-steady: equalized across
  any gap above a declared area. A sealed zone generating steam (×1600 expansion at 100 °C) builds derived pressure,
  which is gameplay to reserve (doors blown open, vessels bursting) but not to build in Phase 1.
- **Chunk sleeping (Noita):** design the chunk map now (16³ cells, shared with frame deltas), and build sleeping in
  Phase 2 "Scale" with the **exact-zero criterion only**: skip a chunk when it and its one-cell halo are uniform in T
  with no sources, exchange or transitions, so the skipped update would be exactly zero. That is bit-identical to not
  sleeping. A tolerance-based sleep changes bits and the error differs per rig, so it needs its own cross-tier and
  determinism tests. The chunk activity mask itself costs 0.3 / 1.3 / 7.9 ms (bench2, 1 m chunks).

## 4. Migration: the order with the least rework

Today: `material u8`, `original_material u8`, `integrity f32`, `temperature f64`, a full bool mask per region,
`time_s` float; `World.sources` holds fires as sphere sources; `snapshot()` has fixed keys; the scene, material table
and rig loaders have no versions (`actions.yaml` has one).

| # | Step | Lands with | Why at this point |
|---|---|---|---|
| 0 | **Design v2**: this container model, the registry, the frame and save grammar, material table v1, authored zones. Owner accepts it. | doc PR | before PR 2's code, because PR 2 builds the caching counter |
| 1 | PR 1, `phase1/act-validation`, as is | this branch | |
| 2 | **PR 2, `phase1/sim-clock`, plus:** `set_material` as the single mutation point with `topology_version` (the same counter as v1's cache); regions as a `u16` id array; preallocated solver temporaries; the rig YAML gains `memory_budget_mb` beside `substeps_per_physics_step`; the registry as a frozen in-code table for today's four fields, driving `digest()` | v1 PR 2 | v1 already touches the rig YAML, the caches and the clock here, so this adds little scope and avoids a second migration of each |
| 3 | **Material table v1** (version, closed keys, solids, liquids, species, reactions, the mass-balance check), with only today's six solids populated, plus air's composition as N2 and O2 | a small PR before PR 3 | `welcome` and the log header embed it, and B12's open item is the same work |
| 4 | **PR 3, `phase1/protocol`, with the channel-generic grammar from its first fixture:** grids, channels, tables, `required`, the encoding vocabulary, `kind: delta` reserved, the registry hash in headers, fixtures 1–4 and 6 (§2.3) | v1 PR 3 | **the protocol freeze**: the grammar has to be generic before the first golden fixture, even with only today's channels in it |
| 5 | **Scene format v1 with authored zones** (a `version`, zone boxes on the 0.2 m grid, an outside reservoir), the zone, gap and debris tables, incremental topology, `RegionSensor`-style zone sensors (`o2_fraction`, `temperature`), air cells out of the conduction solve with surface exchange, and debris for strikes | new `phase1/zones` | the fuel model needs O2 per zone and somewhere to put its heat and products |
| 6 | **The fuel model**: the `fuel` field, reactions from data, burning cells as the fire, the radiative and convective split, char residue, the O2 clamp and extinction; `ignite` becomes a spark (energy in J) rather than a power source; `extinguish` redefined; flips `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`; removes the `TEMPORARY(phase1)` envelope in `data/world/actions.yaml` | `phase1/fuel` (already a Phase 1 item) | the crate scenario's gated outcome has to include O2 from the start, or it flips later (`world_fields.md`: a sealed crate room starves in about 7–8 turns, and today's crate catches at turn 15) |
| 7 | **`latent` and transitions in solids** (melt, dehydration), even if only drywall's and concrete's bound water are live in Phase 1 | with 6, or right after | it fixes the solid state variable before any save exists |
| 8 | **Save v0**, generated from the registry, with the heavy-mode test and fixture 5 | Phase 1 save item | after 6 and 7, so no saved field changes meaning later; added fields are additive from here on |
| 9 | Pools (melting into them, freezing out of them, evaporation, boiling, condensation, Torricelli between zones), surface films, pockets, chunk sleeping, delta frames, the gas grid or two-zone layers | Phase 2, each with its closed form and cross-tier test | additive under the registry and the grammar |

**What has to land before the protocol freeze (step 4):** the grammar, not the fields. That means grids with per-grid
cell size and origin, channels with units, encoding and `required`, tables, the reserved `delta` kind, the registry and
material table hashes in the header, the welcome catalogue, and the fixtures.

**What has to land before save v0 (step 8):** every change to the *meaning* of a saved field: temperature plus
latent (not enthalpy), the region id array, fuel, the zone, pool and debris tables, the embedded scene with zones, and
the `default_for_older_saves` mechanism. New fields after that are additive.

**What changes in v1 itself:**
- §2.1: `StepOutputs` carries the zone table. Save contents grow (§2.2).
- §2.2: world config gains the process list and periods (in `data/world/fields.yaml`, hashed).
- §2.3: the caching fix is keyed by `topology_version`; X1's power-field cost goes away for fires (§3.2); the rig YAML
  gains `memory_budget_mb`; the cost table is re-measured after air leaves the solve.
- §6: zone and air sensors join the SEM bridge (still Maxim's frozen `SensorReading`, values as floats, no new
  fields); body dose is Phase 4 or 5 agent state.
- §7: the frame header grammar (§2.1 here) replaces the fixed-array header; `welcome` grows; the intent log header
  hashes the registry and material table; `extinguish` changes meaning.
- §8: insert material table v1 before PR 3, and `phase1/zones` and `phase1/fuel` before save v0.
- Supersedes: `docs/architecture.md` "The world is material cells" (per cell: material, integrity, temperature)
  and the Known gaps for convection, destroyed-cell heat and the fuel gap; CLAUDE.md's layout line for `world/`.

## 5. Risks and an opinion

### Risks, with what holds each

1. **Binary transitions are where the rigs disagree.** Ignition, melt completion and "a gap opened" are thresholds on
   one cell. A coarse cell's mean temperature lags the true surface temperature (the late-burn lag in
   `docs/architecture.md` is this effect), so ignition would come later at 0.2 m. Holds: rates per unit area, so the
   burning front regresses at flux ÷ fuel density in m/s at every rig; ignition tested against a **reconstructed
   surface temperature**, T_s ≈ T_cell + q″·dx/(2k), instead of the cell mean; gap flows proportional to measured open
   area, so a one-cell crack at max moves almost no gas and the zone-level outcome agrees even where the topology
   doesn't; and cross-tier tests on zone-level outcomes (minimum O2, time the fire goes out, level) rather than on
   cell counts. Each new transition gets the outcome-margin rule from `benchmarking.md` (L4).
2. **Stiffness.** Big gaps, boiling and runaway combustion. Holds: the implicit zone step, clamps on available
   reactant, and quasi-steady pressure.
3. **Conservation with float32 storage.** Holds: transfer what the storage lost, plus the ledger test.
4. **Authoring burden and unsealed barricades.** Zones are a level-design task, and a barricade doesn't seal a zone
   until pockets land. Holds: a loader that refuses zones off the 0.2 m grid or overlapping each other, and the
   pocket rule recorded in Known gaps with a red gate.
5. **Bandwidth at max.** 8 B/cell is a 41 MB full frame at max, and 82 MB/s at 2 Hz. Holds: delta frames by chunk,
   reserved now and built when B5 measures the need.
6. **The client sees a world defined in tables.** Liquid planes clipped to zone volumes and haze from the zone table
   are cheap and look good, but the shader needs the `zone` channel and the table, and colour must never be the only
   signal (CLAUDE.md client standards: water also changes shading and refraction; smoke also changes contrast).

### What to design now

The container model and the transfer rule; the registry as data; the channel-generic frame and save grammar with
`required`; material table v1 with phases, transitions, reactions and the mass-balance check; authored zones in a
versioned scene format; `set_material` with `topology_version`; regions as ids; temperature plus latent as the solid
state; the process list with integer periods; the gas consumer interface; and the chunk map's shape.

### What to defer, and say so in Known gaps

Pools and liquid flow; sealed pockets; the gas grid or two-zone layers; pressure-driven failure; boiling points that
depend on pressure; surface films (puddles, blood, soot); structural support for debris; chunk sleeping; delta
frames; zstd; rig-portable saves.

### What would be over-engineering

- A field **plugin framework** with discovery and dynamic loading. A YAML declaration plus concrete solver modules is
  the abstraction until the third field.
- A general **chemistry engine** (reaction networks, equilibrium, Arrhenius kinetics per species). A short list of
  data-declared reactions with fixed yields is the game.
- **Per-cell multiphase**: volume of fluid, or a liquid and gas phase tag per cell, which brings free surfaces and
  CFD at rig resolution. It is the expensive, rig-dependent path this design exists to avoid.
- **Enthalpy everywhere**, for gases and pools too. One temperature per zone and per pool is enough.
- **Mixed-rig co-op or rig-portable saves**: guests draw the host's frames.
- **Compression or deltas before B5 measures** that they are needed.
- A schema language for tables beyond name, dtype and units.

### Opinion

The owner's choice is a good organizing principle *because* it maps onto the resolution rule: each phase has a
natural resolution, and putting it there makes the hardest rule in the repo cheap to keep. The risk is building the
wrong version of it: a per-cell phase tag looks closest to "states of matter" and is the most expensive thing to
undo. Phase 1 needs only three of these pieces live: O2 and products per zone, fuel per cell, and bound water as the
first latent transition. Everything else should arrive as data rows, registry entries and table columns that the
grammar already carries. If step 4 (the generic grammar) and step 8 (save v0 after the state variable is settled) go
in that order, no later phase change should need a format migration.
