# Snapshot fields the renderer assumes

The rendering half of step 8 was built before protocol v0 (step 7) froze, so it reads **fixtures**, not wire frames.
This lists every field it assumes, for step 7 to confirm or change. The renderer's seam is `CellSnapshot`
(`client/addons/engine/render/cell_snapshot.gd`); step 7's decoder fills that object, and nothing under
`client/addons/` reads this fixture format. The fixtures are made by `scripts/client_fixtures.py` and read by
`client/tests/support/snapshot_fixture.gd`.

## Cells (the cell frame)

The channels themselves (names, dtypes, meanings, the RG8 upload of `region`) are `client_rendering.md` §4.2's, which
owns them; the fixtures follow it. What §4.2 doesn't say, and step 7 must settle:

| Field | Assumed here | Note for step 7 |
|---|---|---|
| `shape` order | `[nz, ny, nx]`, C order, x fastest (§4.1) | The engine's grid is `[x, y, z]`: the encoder must transpose (`client_fixtures.wire_order`). |
| cell size | `cell_m`, metres | `simcore.protocol.encoding.snapshot` calls it `cell_size_m`; §4.1 names none. |
| origin | cell (0, 0, 0)'s corner is the world's origin | The box, the cut boxes and actor positions assume it; streaming would need a field. |
| `region` | ids 1, 2, … in authoring order | `encoding.snapshot` sends no region channel, and the engine has no region ids yet. |
| `surface_glow` | §4.2's quantity | `encoding.snapshot`'s `glow` has §4.2's scale but the cell-mean temperature, not the envelope skin: renaming the key is not enough. |
| `burning` | §4.2 | Not in `encoding.snapshot` yet. |
| `temperature_c` | not read | No pass draws it yet. |

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
