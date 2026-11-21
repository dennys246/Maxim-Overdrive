# Snapshot fields the renderer assumes

The rendering half of step 8 was built before protocol v0 (step 7) froze, so it reads **fixtures**, not wire frames.
This lists every field it assumes, for step 7 to confirm or change. The renderer's seam is `CellSnapshot`
(`client/addons/engine/render/cell_snapshot.gd`); step 7's decoder fills that object, and nothing under
`client/addons/` reads this fixture format. The fixtures are made by `scripts/client_fixtures.py` and read by
`client/tests/support/snapshot_fixture.gd`.

## Cells (the cell frame)

| Field | Assumed | Source | Note for step 7 |
|---|---|---|---|
| `shape` | `[nz, ny, nx]`, arrays in C order, x fastest | `client_rendering.md` §4.1 | The engine's grid is indexed `[x, y, z]`; the encoder must transpose (`client_fixtures.wire_order`). One z-slice is then one Godot `Image`. |
| cell size | `cell_m`, metres, float | — | `simcore.protocol.encoding.snapshot` calls it `cell_size_m`; §4.1's header names none. |
| origin | cell (0, 0, 0)'s corner is the world's origin | — | The box, the cut boxes and actor positions all assume it; a frame with an offset (streaming) needs a field. |
| `material` | u8 material id, 0 = air | §4.2 | Solid means `material != 0`. |
| `region` | u16 `region_id`, little-endian, 0 = none | §4.2 | `encoding.snapshot` sends no region channel; the engine has region names but no ids yet. The fixtures number regions 1, 2, … in authoring order. |
| `crack` | u8, 1 − integrity, 0–255 | §4.2 | Any value > 0 carves (§5.4). |
| `surface_glow` | u8 counts, T = offset + scale · count | §4.2 | `encoding.snapshot` today names it `glow` and scales it 525–1500 °C over 0–255, which matches 975/255, but its quantity is the cell-mean temperature, not §4.2's envelope skin temperature: renaming the key is not enough. Count 0 means at or below 525 °C and emits nothing. |
| `burning` | u8 burning fraction, 0–255 | §4.2 | Not in `encoding.snapshot` yet. |
| `temperature_c` | not read | §4.2 | The f16 debug view has no pass yet. |

## Vocabularies (the `welcome` message)

| Field | Assumed | Note |
|---|---|---|
| region map | id → name, names unique | The cut-away finds walls by name (`client/game/cutaway.tres`). |
| material vocabulary | name → id, ids 0–15 | On `CellSnapshot.material_ids`. Albedo comes from `client/game/palette.tres` by name; an id over 15, or a solid material the palette lacks, is reported and drawn magenta. |
| `surface_glow` calibration | `offset_c`, `scale_num`, `scale_den`, integers | §4.1's integer rationals; the client divides. |

## Bodies (the `tick` message)

| Field | Assumed | Note |
|---|---|---|
| actor `id` | whole number; actor 1 is the player in the golden fixtures | The cut-away needs to know which actor is the local player; §4.1 doesn't say how. |
| actor `pos_mm` | `[x, y, z]` integer mm, the **feet** | The stump is feet + 0.3 m (§2), so `z` must be the feet, not the body's centre. |

## Container (fixtures only, not a proposal for the wire)

A JSON header (`format`, `version` 0, the fields above, per-channel `dtype`, `offset`, `size`, `data_size`,
`data_sha256`, `data_gzip_sha256`) beside a gzip file of the channels end to end. The compressed digest is checked
before inflating, because Godot's `decompress` prints its own `ERROR:` on a corrupt stream, and the gate fails on any
`ERROR:` line.
