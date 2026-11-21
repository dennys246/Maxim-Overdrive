# Step 8 shader: Performance

Every number below is labelled. **Measured** means Godot 4.7.2 headless on this Apple M2, run on a scratch copy of `client/` (nothing in the worktree was touched), on `SnapshotFixture.named("alley_fire")` (120 × 40 × 48 = 230,400 cells; 59,312 solid; 936 of 3,600 bricks occupied; 696 cracked, 136 glowing, 36 burning). Each timing is the minimum of 20–50 runs, repeated over three runs. The spread between runs is wide (the machine is shared with other sessions), so I give ranges. **Derived** means arithmetic from the code. Nothing was measured on a GPU or on llvmpipe.

## SHOULD-FIX: the per-snapshot upload is 5–15× over §8's 3 ms, and no meter exists

**`client/addons/engine/render/volume_textures.gd::bricks`** (called by `CellVolume.show_snapshot` through `bricks_texture`)

- **Measured:** `VolumeTextures.bricks` takes **14–46 ms** at 230,400 cells. The whole `CellVolume.show_snapshot` takes 20–47 ms. Under the headless dummy renderer `texture()` costs only 54–64 µs, so almost all of that time is the GDScript brick loop (about 60–200 ns per cell iteration).
- **Derived:** §8's budget for decode plus all seven uploads is ≤ 3 ms, and §8's own probe gives 1.4–2.4 ms for the real uploads. The brick loop alone therefore uses 5–15× the whole budget.
- **Failure scenario:** step 7's decoder calls `show_snapshot` on every `update` at 2 Hz. Twice a second the main thread stalls for 14–46 ms. At 60 fps that is one to three dropped frames on every snapshot, a periodic hitch in play.
- **Max profile, derived:** at about 5×10⁶ cells the loop is ×21.7, so 0.3–1.0 s per snapshot. The snapshot stream could no longer be drawn at its own rate.
- **A GDScript tweak is not enough (measured):** skipping all-air rows with `slice().count(0)` gives the same bytes in 11.0–11.6 ms, against 15.9–20.7 ms for the shipped loop in the same run. It only halves the cost and is still almost 4× the budget.
- **Real fixes:**
  - Ship the 3,600-byte brick mask from the server. In numpy it is a reshape plus `any`, and protocol v0 is unfrozen.
  - Or compute it in native code.
- **The meter is missing:** §8 lists this row as "B5, gated in CI", but nothing in the client times anything (`grep get_ticks_usec client/` finds nothing). The budget is stated and unguarded. Today it is broken by the measurement above.
- **Severity:** this becomes a BLOCKER the moment step 7 wires `show_snapshot` to the stream. It is SHOULD-FIX now only because there is no live caller yet.

## SHOULD-FIX: every snapshot creates new GPU textures instead of updating them

**`client/addons/engine/render/volume_textures.gd::_texture_of`** and **`cell_volume.gd::show_snapshot`**

- **What happens:** each `show_snapshot` builds 7 new `ImageTexture3D`s through `create()`. Before that it slices each channel into one `Image` per z-slice, 48 per channel. That is about 290 `Image` allocations plus a full extra copy of all 1.84 MB of bytes, which the engine then joins back into one buffer. The old textures are freed when the material parameter is replaced.
- **Cost on OpenGL (Compatibility):** each `create()` means a texture is allocated and freed (`glTexImage3D`) on every update, instead of the data being rewritten into the existing texture (`glTexSubImage3D`). It also triggers a material uniform change per texture.
- **Fix:** `ImageTexture3D.update(Array[Image])` exists to rewrite an existing texture in place.
- **Failure scenario:** at 2 Hz on the alley this is waste inside the 3 ms budget. At the max profile it is 30 MB of reallocation per update (5×10⁶ cells × 6 B, derived). Every channel is re-sent, including `region`, which changes only on an `imagine`. With §8's 173–294 µs per 230k-cell channel-equivalent scaled ×21.7, that is 23–38 ms per update (derived), 8–13× the budget, before the brick loop.
- **Also needed:** create on the first `welcome` and update afterwards. Dirty-slice updates are the later step.

## SHOULD-FIX: `region_cell_bounds` costs about 100–170 ms, and nothing ties it to "once per region map"

**`client/addons/engine/render/cell_snapshot.gd::region_cell_bounds`** and **`client/tests/support/render_stage.gd::show_fixture`**

- **Measured:** **98–166 ms** at 230,400 cells. The cost is Dictionary `has`, `min` and `max` on each of the 59k region cells.
- **The guard is only a comment:** the docstring says "Run once per region map, not per frame". But `CellSnapshot` has no region-map version, so a caller cannot tell when the region map changed.
- **The only caller sets the opposite example:** `RenderStage.show_fixture` re-runs it on every snapshot shown. §4.2 says the region map changes after an `imagine` (a new region), so step 7 must either re-run it on every snapshot or guess.
- **Failure scenario:** a decoder copies `RenderStage`'s pattern, and every 2 Hz update pays about 100–170 ms, a stall of 6–10 frames. Even the correct pattern costs a 100+ ms hitch on every `imagine`. At the max profile that is 2.1–3.6 s (derived).
- **Fix:** give the snapshot a region-map version, or deliver per-region bounds from the server, which already has them, in the same way as the brick mask.

## NIT: the 8-tap AO fetches 5 taps that always weigh zero

**`client/addons/engine/render/lighting.gdshaderinc::face_ao`**

- **Why they weigh zero:** `near.x = max(0, 2fu−1)` and `near.y = max(0, 1−2fu)` are never both nonzero, and the same holds for `near.z` and `near.w`. At most 2 of the 4 edge taps and 1 of the 4 corner taps can contribute. Yet all 8 `occludes()` calls run, each a `drawn_at`: one `material` fetch, plus one `region` fetch and the cut-list loop when the cell is solid.
- **Derived cost:** at max, 8 taps cost up to 16 fetches per lit pixel when at most 3 taps (6 fetches) matter. That is about 10 wasted fetches per pixel. At 1280 × 720 with about 70% of the frame covered (my assumption), about 6.5 M wasted fetches per frame.
- **Impact:** small on a max-tier GPU, but it doubles the cost of AO, and on llvmpipe each fetch is many instructions.
- **Fix, branch-free:** step towards the near side only, e.g. `out_cell + u * (fu < 0.5 ? -1 : 1)` with weight `(2fu−1)²`. That gives 2 edge taps and 1 corner tap. It is the same image with 3 taps instead of 8 (4-tap mode becomes 2).

## NIT: the crack carve recomputes the same 27 feature points at every substep

**`client/addons/engine/render/crack.gdshaderinc::carve`** and **`::crack_edge`**

- **The redundancy:** `spacing = cell_m`, so `q` is the cell-space point and `base = floor(q)` is the hit cell itself for every substep inside the cell. The only exception is possibly k = 0 on the entry face, where a float floor can land in the neighbour. The 27 `lattice_hash` calls are therefore identical across all substeps.
- **Derived cost:** one hash is about 33 integer operations, and with the distance and compare work a substep is about 1,350 operations.
  - A cracked-face pixel stops at k = 0, so it pays about 1,350 operations. That roughly equals the whole traversal, about 35 iterations × about 40 operations.
  - A groove pixel at max (8 substeps) pays about 11,000 operations per cracked cell it passes through.
- **Divergence:** on a GPU, one groove pixel holds its whole 32-pixel warp for those 8 × 27 = 216 hash evaluations while its neighbours finished after 27.
- **Impact:** fine on the fire fixture, where only 696 cells are cracked. It becomes the dominant cost on a burned-out room at max, and on llvmpipe, where operations are paid serially.
- **Options:**
  - Hoist the 27 feature points out of the substep loop. That costs registers: 27 vec3 is 81 floats, which may spill on a GPU.
  - Or precompute the jitter into a 3-D texture. The trade has to be measured.
- **Not wrong**, but the "27 hashes per substep" cost is 8× more than it needs to be at max.

## NIT: `MAX_STEPS` is justified by the wrong bound

**`client/addons/engine/render/traversal.gdshaderinc::MAX_STEPS`**

- **What the comment says:** it justifies 320 by "nx + ny + nz = 208".
- **The real bound (derived):** the camera is fixed at 40° elevation, so a ray from the box top crosses about nz + 2 × (nz / tan 40°) × cos 45° ≈ 2.69 nz cells, which is about 129 for the alley. Brick skipping cuts a typical floor ray to about 30–40 iterations: about 30 brick skips through the air, then a hit on the floor's brick, whose top is a brick boundary at z = 4 cells. So 320 holds while nz ≤ about 119 cells (11.9 m), whatever nx and ny are.
- **Why it matters:** the comment points a future tile author at the wrong dimension.
- **Fixes:** fix the comment, or make the bound a uniform set from `cells`. Loops with uniform bounds are fine on GL 3.3.
- **It is also worth recording** that §5.2's "60–80 steps" estimate is pessimistic for this layout. That is derived from the code, not measured on a GPU.

## NIT: redundant texel reads per cell step and per hit

**`traversal.gdshaderinc::brick_empty`** (via `cell_volume.gdshaderinc::find_hit`), and **`cell_volume.gdshaderinc::shade`** / **`::hit_normal`**

- **The brick texel:** `brick_empty` is fetched at every cell step inside an occupied brick, up to about 10 times for the same texel.
- **`crack_at(h.cell)`** is fetched 2–3 times per hit: `find_hit`, `albedo_of` and `hit_normal`.
- **`material_at(h.cell)`** is fetched again in `shade`, after `drawn_at` already read it.
- **Impact:** on a GPU these hit the texture cache and cost little. On llvmpipe each is a full software fetch.
- **Fix:** carry the brick index and the hit's material and crack in `Walk` and `Hit`. This is cheap and also clarifies the code.

## NIT: the golden job's runtime against its 120 s timeout is unrecorded

**`scripts/golden_run.py::draw_all`**

- **The workload:**
  - `cutaway_check.tscn` draws 96 occluder frames at 960 × 540 in one Godot call. The occluder pass skips carving and AO (`debug_carves`, and the early return in `shade`), so it is the cheapest pass.
  - `golden.tscn` draws 6 shots at 1280 × 720. Each shot re-decodes the fixture (measured 15–55 ms) and re-runs `region_cell_bounds` (98–166 ms) and `bricks` (14–46 ms). That is about 1.6 s of CPU on the M2, and perhaps 2–4× that under emulation (derived). Each shot may also compile the nearest-filter shader variant on llvmpipe.
- **Derived estimate:** at about 30–40 iterations per pixel and about 2.4k operation-equivalents per occluder pixel, about 0.05–0.2 s per frame on a 4-vCPU AVX2 runner, so about 5–20 s for the cut-away scene. That estimate is unverified.
- **What suggests a margin:** c656c33's "Mac and llvmpipe agree exactly" means the cut-away scene finished under 120 s in Docker on Rosetta x86-64 emulation.
- **What is missing:** that run's wall time is recorded nowhere. Nothing warns as a scene approaches the timeout. And the cut-away cost grows linearly with samples × yaws.
- **Failure scenario:** more cut samples are added, or the GitHub runner is slower than Docker Desktop on the M2 (4 vCPU against Docker's allotment). The first sign is a timeout on CI.
- **Ask:**
  - Print elapsed seconds per Godot call in `golden_run` and in the logs.
  - State the local number in the hand-off.
  - If it is above about 60 s, split the cut-away scene by yaw.

## No finding

- **Per-frame CPU:** `CellVolume` has no `_process`, uniforms change only on aim, cut or tier, and nothing O(cells) runs per frame.
- **Mask passes:** they return before AO, carve and hatch, so the 96 cut-away frames are the cheap pass.
- **Texture memory:** about 1.4 MB at the alley and about 30 MB at the max profile (derived). Both are fine.
- **Laptop tier:** it renders a quarter of the pixels, and `pixel_m` includes the render scale, so the minimum groove width holds at half resolution.

## Unrelated to performance, for the owner

- §5.5 still says max uses 6-tap AO. The commit records the departure to 8 taps, but the table was not amended.
