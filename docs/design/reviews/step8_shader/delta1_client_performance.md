# Step 8 shader, delta 1: Client and rendering, Performance

Scope: `git diff --cached ce06d7b` plus the three re-recorded `fire.png` goldens. I edited nothing in the worktree and did not run the gate, Docker or windowed Godot.

Method:
- Scanned the old and new goldens with numpy.
- Wrote a float32 port of the fold's `walk_at`, `skip_brick` and face-normal entry. It runs against a float64 reference DDA (a plain cell-by-cell ray walk) on the alley material and region arrays saved in round one, at the golden camera.
- Ran one headless Godot probe on a mktemp copy of `client/`, with HOME in a mktemp directory.

Every number below is labelled **measured** or **derived**. Scratch work is in `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/fb8c693b-b475-44b8-86f3-99160cb687c9/scratchpad/d1/`.

**Headline:** the traversal fix creates a new defect (N1), and the re-recorded goldens lock it in. It replaces one or two holes per frame with 47 single-pixel dark dots per rig and max frame.

## Fold status (set from the tree)

### client_rendering.md

| Finding | Status | Evidence |
|---|---|---|
| S: hole at (543, 224) in rig and max | **open** | The cited pixel is now wall-coloured, (60, 59, 54) (measured). But the walk change that cured it adds 13–14 black and about 34 dark single-pixel dots per frame (N1). The guard round one asked for, a miss or axis check over solid pixels, was not built. That is why the regression shipped into the goldens. |
| S: laptop crack becomes speckle; §6.4 runs only on rig | **open (partly fixed)** | Fixed: polygons are now at least 12 px (0.4 m spacing on laptop, derived), and `colour_alone_findings` loops over `TIERS`. Not fixed: severity still has no shape signal. The fold made this worse on rig (N4). |
| S: 1.5 px floor not met on foreshortened faces | **fixed** | The pixel floor is divided by `abs(pick(r.d, axis))`, floored at 0.25, in both `carve` and `hit_normal`. There is a residual issue inside grooves (N5). |
| S: carving has no depth bound | **fixed** | `GROOVE_MAX_DEPTH_M` is 0.05 m along the ray, and the fissure floor is hit there. Residual edge cases are in N6. |
| S: misspelt uniform name fails silently | **fixed** | `test_every_uniform_the_node_sets_is_one_the_shader_declares` checks every name `_param` sets against `get_shader_uniform_list()` for both variants. It also holds the palette and cut-list sizes to the GDScript constants. |
| S: unknown material ids draw black | **fixed** | `use_palette` fills magenta and calls `push_error` for an uncoloured solid id or an id ≥ 16. Tested (id 2 reads magenta). |
| S: no deletion proof for the depth formula | **open, pending** | fold.md says the proof is "recorded in the fold commit". No such commit exists yet, so the tree can't show it. It flips to fixed when the commit message states the `DEPTH = ndc.z` run and its result. |
| S: `MAX_STEPS` sized for the alley only | **fixed** | The bound is `max_steps() = nx+ny+nz+4` (212 for the alley). Each iteration moves the walk at least one cell forward along some axis, so the bound holds (derived). My port's longest walk was 41 iterations over 20,000 rays (measured, emulated). |
| S: hatching aliases on laptop | **fixed / deferred** | The period floor is 8 px: 0.222 m on laptop, 0.12 m unchanged on rig (derived). The unmeasured-hatching part is deferred to **B30**; trigger: step 8, with `main.tscn`'s scene tree. |
| NIT: emission departs from §5.3 | **fixed** | §5.3 is corrected in place, and the 920 °C claim now says orange-red, below bloom. |
| NIT: `entry_axis` from distances | **fixed** | The axis now comes from the face normal (`v_face_normal = NORMAL`). BoxMesh normals are flat per face, so the interpolated varying is exact. The clamped-origin case on an uncrossed axis is also cured by the new nudge. |
| NIT: `centre_godot` duplicates the node's position | **fixed (documented)** | A comment states "translation only". There is no assert, and the half-extent is still taken from `position`. Acceptable, given round one offered "document or assert". |
| NIT: `texture()` inside divergent flow | **fixed** | Now `textureLod(…, 0.0)`, which is valid on `sampler3D` in GLSL ES 3.0 and in 3.30. |
| NIT: tonemapper choice has no why | **fixed** | A comment in `render_stage.gd::_init`. The black-night constraint is recorded in B30. |
| NIT: perspective ray path never exercised | **deferred** | B30, same trigger. |

### performance.md

| Finding | Status | Evidence |
|---|---|---|
| S: `bricks` takes 14–46 ms against a 3 ms budget | **deferred** | B5 now names it with the numbers. Trigger: step 7, before `show_snapshot` is wired to the stream. Remeasured: a second `show_snapshot` on the alley takes 17.1–17.7 ms headless (measured, 3 runs). It still dominates. |
| S: new GPU textures on every snapshot | **fixed (realloc)** | `_texture_of` calls `ImageTexture3D.update` when format and shape match. Headless probe: after a second `show_snapshot`, `material_tex` and `bricks_tex` are the same objects (measured, dummy renderer). Not fixed: the 48 `Image` slices per channel per call, and re-sending unchanged channels such as `region`. Both fit under B5's trigger. The path is untested (N7). |
| S: `region_cell_bounds` costs 100–170 ms | **deferred** | Recorded in B5 with the same trigger. `RenderStage` now recomputes only for a new snapshot object. A decoder that builds a new `CellSnapshot` per update still pays it every time; the docstring says so. |
| NIT: 8-tap AO reads 5 zero-weight taps | **fixed** | The algebra checks out: with fu′ = 2fu−1, the chosen side's weight fu′² equals the old `near.x` or `near.y`, and the far side's weight was 0. The same holds for the corner tap. The image is identical by construction, at 3 taps instead of 8 and 2 instead of 4. |
| NIT: carve recomputes the 27 feature points per substep | **open** | Not in fold.md and not in the backlog. It is now more redundant: at 0.2–0.4 m spacing the same 27 hashes repeat across 2–4 cells as well as across substeps. |
| NIT: `MAX_STEPS` justified by the wrong bound | **fixed** | Superseded by `max_steps()`. |
| NIT: redundant texel reads | **open** | Not addressed, not deferred. |
| NIT: golden job runtime unrecorded | **open (partly fixed)** | Each call now prints its wall time. The author's own numbers are 50.7 s and 64.7 s of 120 s under emulation (author-measured). Round one's ask was to split the cut-away scene by yaw above about 60 s. 64.7 s is over that, the fold added three pavement samples, and no split was made. |
| §5.5 still says 6-tap AO | **fixed** | The table says 8-tap. |

## New findings

### BLOCKER N1: `walk_at`'s nudge reports the wrong entry axis, and the goldens record 47 dark dots per frame
`client/addons/engine/render/traversal.gdshaderinc::walk_at` (via `skip_brick`)

**Measured in the goldens** (numpy; a "flat" pixel is one whose 8 neighbours lie within 6 of each other in RGB sum):

| Tier | Single-pixel dark dots on flat faces, old → new | Of which pure black, new |
|---|---|---|
| rig | 1 → 47 | 13 |
| max | 1 → 47 | 13 |
| laptop | 0 → 7 (2×2 blocks, 28 px) | — |

- They lie in regular lines on the pavement top (floor surface z = 4 cells) and on the top of wall_north. Neighbouring dots sit one step of (9, 14) px apart, for example (210, 371), (219, 385), (228, 399).
- Marked image: `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/fb8c693b-b475-44b8-86f3-99160cb687c9/scratchpad/d1/marked_rig.png`.

**Mechanism (reproduced in float32 emulation, all 16 sampled dot pixels):**
- The walk finds the **correct cell** but with axis x or y. The reference says z, a top face.
- `skip_brick` jumps at t_x, where the ray crosses an x or y brick face just before it reaches the brick's z = 4 face.
- `walk_at` then floors z at `p + d·1e-3`. With d.z = −0.643, that is −6.4e-4 cells (derived), which pushes z past the boundary into the floor cell. Meanwhile `w.axis` still says x.
- The floor cell is drawn and shaded as a vertical face. Its normal is wrong, and `out_cell` is the solid floor neighbour, so the AO taps are all occluded.
- The +x face points away from the key light, which gives about (0, 0, 3). So the "black" pixels are wrong-axis shading, not discards. The y-axis cases give a sum of about 61–132 against the floor's 263.

**Failure scenario:** in play, every flat top face shows sparkling dots along brick edges, and they move as the camera pans. The goldens now require them.

**The old cure was incomplete:** fold.md checked only that pixel (543, 224) turned wall-coloured. Nobody scanned the rest of the frame.

**Fix:**
- Make the axis agree with the nudged cell. After choosing the cell at `p + d·ε`, set `w.axis` to the axis whose entry boundary into that cell (the one behind it along the ray) has the largest t, and set `w.t` to that t.
- Add the round-one guard: a debug pass that writes the hit axis or a miss, checked against an exact reference over solid pixels. Or add a `golden_measures` check that flags isolated single-pixel outliers on flat faces. The numpy filter above finds all 47.
- Then re-record the goldens.

### NIT N2: the nudge reads the neighbouring cell on an uncrossed axis
`traversal.gdshaderinc::walk_at`

- **Emulated:** 10 of 10,764 hits (0.09%) report a cell one step past the reference on an uncrossed axis. The nudge skips the cell the ray clips for at most 1e-3 cells.
- The shaded point `p` is still on the true ray. But material, crack and glow are read from the neighbour, so at a material or crack boundary a pixel shows the wrong cell's state.
- It disappears with N1's fix if the fix also takes the cell from the exact crossing.

### SHOULD-FIX N3: at the default 12 m zoom the crack spacing sits exactly on an octave boundary
`client/addons/engine/render/crack.gdshaderinc::crack_spacing_m`

- At 12 m and an effective height of 720 px (rig at 720p, laptop at 1440p × 0.5), 12·pixel_m/cell_m is exactly 2 in real arithmetic. In float32 it is 2.0000002, so ceil(log2) gives 2 and a 0.4 m spacing, where exact arithmetic gives 0.2 m (derived). At 1440p × 1.0 the value is 1.0000001, which flips between 0.1 and 0.2 m.
- GLSL `log2` precision is implementation-defined. Which crack network the default view draws therefore depends on the GPU and driver, and on llvmpipe against Metal.
- If zoom is ever tweened, every frame that passes the boundary swaps the whole network.
- Related: the lattices at different octaves are not nested, so every octave change at a wheel step pops the pattern wholesale. With pixel_m = 0 (`log2(0)` is undefined; a viewport of height 0 gives inf) the spacing is undefined.
- Panning does not swim: the spacing is fixed to the world.
- **Fix:** choose the octave in GDScript with hysteresis (for example `floor(log2(x) + 0.5)` held until x moves 10% past the boundary). Pass `crack_spacing_m` as a uniform, and refuse pixel_m ≤ 0 in `use_pixel_metres`.

### SHOULD-FIX N4: the slant correction removes severity-by-shape on rig as well
`crack.gdshaderinc::groove_half_width_m`

At the golden zoom (pixel_m = 0.01389 m on rig and max, derived), the ray at elevation 40° and yaw 45° meets faces at these cosines:

| Face | Cosine | Pixel floor (half-width) | Floor wins for |
|---|---|---|---|
| Vertical faces | 0.542 | 0.0192 m | c < 0.96 (was 0.52) |
| Top faces | 0.643 | 0.0162 m | c < 0.81 |
| Laptop, any face | — | 0.032–0.038 m | every c ≤ 1 |

- So c from 0.25 to 0.96 draws identical grooves on rig walls, and only char colour tracks severity. That is the CLAUDE.md never-colour-alone rule this finding raised in round one.
- §6.4 tests crack against no crack, not severity, so nothing catches it.
- This is an owner decision: make the groove area or the polygon density scale with c above the pixel floor, or accept "presence only" and record it.

### NIT N5: the slant and the floor's normal use the last internal crossing, not the visible face
`crack.gdshaderinc::carve`, `cell_volume.gdshaderinc::find_hit`

- Inside a groove, `w.axis` is the internal boundary the walk last crossed. The groove's half-width therefore changes from cell to cell within one groove.
- The fissure floor is shaded with that axis's face normal, at a depth of 0.05 m and `fissure_shade` 0.50 (derived), with no AO.
- A crack's floor therefore shows blocky cell-shaped patches at different lighting levels. The fix is to carry the entry face's axis from the first cell of the groove.

### NIT N6: the depth bound has gaps
`cell_volume.gdshaderinc::find_hit`

- `floor_t` is checked only when no sample is solid. A solid sample past `floor_t` in the same cell gives a depth up to about one cell beyond 0.05 m.
- A groove that leaves drawn material (a crate's edge, a cracked cell at the volume's face) before `floor_t` resets `groove_t0` and walks on. It shows what is behind, or discards.
- Rays only exit this way within 0.5 ray-cells of a back face, so it is limited to silhouette edges.

### SHOULD-FIX N7: the in-place texture update has no test
`client/addons/engine/render/volume_textures.gd::_texture_of`, `cell_volume.gd::_texture`

- No unit test calls `show_snapshot` twice; `grep reuse|show_snapshot client/tests/unit` finds two single calls. CLAUDE.md requires a behaviour change to ship with its test.
- My headless probe shows the textures are reused (measured). Under the dummy renderer it cannot show that the contents change or that a different shape gets a new texture.
- The OpenGL `texture_3d_update` path on Compatibility is unverified on a GPU.
- **Fix:** add a test that a same-shape second snapshot reuses the texture object, a new shape or format allocates a new one, and `get_data()` (or a golden pass across two snapshots) shows the new contents.

### NIT N8: the hatch period moves with zoom above its floor
`lighting.gdshaderinc::hatch`

- At the default 12 m on a 720 px rig, the period is max(0.12, 8 × 0.01667) = 0.133 m (derived).
- The phase is anchored at the world origin, so each zoom step moves the stripes across the cut walls by several periods.
- This is acceptable as a look, but anchoring the phase per region or face would stop the jumps.

## Checked, nothing found

- **`max_steps()` as a loop bound:** non-constant loop bounds are legal in GLSL ES 3.0 (only ES 2.0's Appendix A forbids them) and in 3.30. Both variants compiled and drew the goldens.
- **`skip_brick`'s fallbacks:**
  - The `<= w.t + 1e-4` fallback can only fire when the brick exit coincides with the cell exit. A cell step is then exact.
  - The same-brick fallback is a correct cell step.
  - Neither can cycle, because `advance` is monotone.
  - In emulation, all 132,683 skips were jumps. The fallbacks never fired at the golden camera.
- **Sentinels:** `cells = 0` makes `inside()` false, so the walk returns within 4 iterations and the pixel discards. That holds even though `cell_m = 0` makes the origin NaN or inf. A glow scale of 0 makes the glow 0.
- **Near-side AO:** the image is identical (algebra above).
- **`textureLod`, `crack_edge` with spacing ≥ cell:** the 3×3×3 search still covers the jitter range.
- **The `pixel_m` order dependence:** fixed by `_update_pixel_metres`.
