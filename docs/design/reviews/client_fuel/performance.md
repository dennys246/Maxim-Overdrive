# Performance review: phase1/client-fuel (step 8 fuel pass), round 1

Reader: Performance lens. Tree: `git diff 69483d9` plus untracked files, as they stood on 2026-11-22. I measured on a copy of `client/` in `<scratchpad>/rev_perf/client/` with Godot 4.7.2 on the M2, using `HOME` and XDG under that directory. The fixture is `tools/fuel_aa/frame_time.gd::_many`: 2,000 rods and 2×10⁴ segments, the world limits. Load average was 10–14 on 8 cores, so treat the absolute values as rough. The ratios held across three runs. The bench script is `rev_perf/client/bench/bench.gd`, and the frame-time rerun is `rev_perf/client/bench/ft.gd`. I did not touch the worktree or its git state.

## Summary

| ID | Severity | Location | One line |
|---|---|---|---|
| P-B1 | BLOCKER | `fuel_pass.gd::_rebuild`, `fuel_geometry.gd::segment_tops`/`_rod`/`_vector`, `fuel_snapshot.gd::column` | The shipped rebuild takes 52–71 ms. The design cites 3.6–3.8 ms, which is 15–19× less. |
| P-S1 | SHOULD-FIX | `fuel_snapshot.gd::problems` | 29–41 ms on each trigger change. This is unbudgeted, so an insertion costs about 85–110 ms in all. |
| P-S2 | SHOULD-FIX | `fuel_snapshot.gd::trigger_bytes`, `fuel_pass.gd::show_fuel` | Building the trigger bytes costs 174–377 µs per message. The design cites a 30 µs compare. |
| P-S3 | SHOULD-FIX | `tools/fuel_aa/frame_time.gd`, `research/fuel_antialiasing.md` | The frame-time table can't be rerun: the tool no longer parses, and its "edge" shader is gone. |
| P-N1 | NIT | `fuel_pass.gd::use_palette`, `tests/support/render_stage.gd::show_fuel` | Every call to the stage's `show_fuel` forces a full rebuild. |
| P-N2 | NIT | `fuel_object.gdshaderinc::instance_at`, `fuel_rod.gdshader`, `fuel_slab.gdshader` | Each fragment does 8 `texelFetch`es, 4 of them per-instance constants. Rods run the fragment shader twice, and the slab's `discard` turns off early-z. |
| P-N3 | NIT | `scripts/golden_fuel.py::_mean_l` | It converts the whole frame to Lab once per call: 6.4 s of the 7.8 s `fuel_findings` takes. |
| P-N4 | NIT | `client_objects.md` §4.1 | The text says `state` is the instance texture's fourth byte. The shipped code reads a separate `state_tex`, one more fetch per fragment. |

## Findings

### P-B1 BLOCKER: the rebuild is 15–19× the cost the design cites

**Where:** `client/addons/engine/render/fuel_pass.gd::_rebuild` and `::_place`, `fuel_geometry.gd::transform`, `::segment_tops`, `::_rod_tops` and `::_vector`, and `fuel_snapshot.gd::column`.

**Defect.** `client_objects.md` §2, §4.1 and §7.4 state the rebuild as "3.6–3.8 ms per insertion". That figure came from the design's probe (`performance.md` P-S2), not from this code. I measured the shipped path at the limits:

| Part | Headless | Windowed, opengl3 |
|---|---|---|
| Full rebuild through `show_fuel` (cleared `_trigger`) | 55.1–71.4 ms | 52.2–53.8 ms |
| `FuelGeometry.segment_tops` (2×10⁴ segments) | 31.2–35.3 ms | 25.6–26.3 ms |
| Flame `set_instance_transform` loop, 2×10⁴ calls | 3.8–6.7 ms | 4.0 ms |
| `FuelGeometry.transform` × 2,000 | 16.8–22.7 ms | 16.5–16.6 ms |

**Cause.** `FuelSnapshot.column` formats a string (`"%s.%s" % [...]`) and does a dictionary lookup on every call. `_vector` also builds `prefix + "x" + suffix`. The geometry code calls `column` inside per-row loops:
- 8 lookups per rod in `_rod`.
- 3 per object in `_write_instance`.
- 3 per object plus 8 per object in `segment_tops`/`_rod_tops`.

Each segment then builds a `Transform3D`, appends it to a typed Array and runs `append_array`, and each transform is uploaded with its own `set_instance_transform`.

The flames also bring back what §4.1 rejected on cost. §4.1 says "one instance per segment would cost 4.4–6.9 ms in GDScript". §5.3 now draws one quad per segment row, placed by that same GDScript loop, at 26–35 ms.

**Failure scenario.** At step 7, every insertion message (an `imagine`, a scenario spawn) stalls the main thread for about 50–70 ms. That is 3–4 dropped frames at 60 Hz, or about 6–8 with P-S1 added. The B5 row and §7.4 would be seeded with 3.6–3.8 ms, a number this code does not achieve. That breaks "Performance has budgets, measured, not guessed" and "a claim … is measured on the shipped path".

**Fix (verified).** Fetch each column once per rebuild with `column(...).to_float32_array()` and similar calls. Then write a `PackedFloat32Array` in MultiMesh's 12-float layout and assign `multimesh.buffer` once.
- **Flames:** `_tops_hoisted` in `bench.gd` takes 5.3–5.7 ms and gives a buffer identical to the shipped one (240,000 floats, max abs diff 0).
- **Rods:** `_rods_hoisted` takes 2.06–2.23 ms and is identical to `FuelGeometry.transform` (max abs diff 0). Caveat: every fixture axis is +x, so the near-vertical `EAST` branch was not exercised.
- **Projected total:** about 7.5–8 ms, plus `_write_instance`, which needs the same hoisting (unmeasured).
- **Alternative:** correct the three doc sites and the B5 row to the measured 52–71 ms. That keeps the stall, though, and the per-segment loop contradicts §4.1's own reasoning.

### P-S1 SHOULD-FIX: `problems()` costs 29–41 ms on each trigger change, and nothing budgets it

**Where:** `client/addons/engine/render/fuel_snapshot.gd::problems`, `::_geometry_problems`, `::_rod_problems` and `::_object_problems`.

**Measured (headless, limits):**

| Part | Time |
|---|---|
| `problems()` | 28.8–41 ms |
| `_geometry_problems` | 34–43 ms |
| `_rod_problems` (within it) | 15–21 ms |
| `_object_problems` | 7.5 ms |
| `_segment_key_problems` | 2.0–2.5 ms |

**Causes:**
- The same per-row `column()` and `_vector` string lookups as P-B1.
- `_object_problems` calls `recipe_ids.values().has(...)` and `kind_ids.values().has(...)`, which allocate a fresh Array on every row.
- `_geometry_problems` calls `_kind_name(kind)`, a linear scan, on every row.

**Failure scenario.** The docstring says `problems()` runs "when trigger_bytes() changes", so it falls in the same message as the rebuild. An insertion then costs about 85–110 ms on the main thread at the limits. No design row or B5 row names this cost. No production caller exists yet, so step 7's decoder would inherit it unmeasured.

**Fix (unverified).** Use the same hoisting as P-B1. Build the value sets once before the loop. Look up kind names through an inverted dictionary built once.

### P-S2 SHOULD-FIX: the per-message cost is the concatenation, not the cited compare

**Where:** `client/addons/engine/render/fuel_snapshot.gd::trigger_bytes`, called from `fuel_pass.gd::show_fuel`.

**Defect.** `client_objects.md` §2 and §7.4 add "a native byte compare … 30 µs" to the decode-and-upload budget. The shipped code first concatenates 222,000 bytes into a new array on every cell-frame message, rebuilding `tables()` along the way:

| Step | Time |
|---|---|
| `trigger_bytes()` | 174–377 µs |
| The compare itself | 7–15 µs |
| Steady `show_fuel` (no rebuild; checked with `rebuilds` unchanged after 50 calls), headless | 207–462 µs |
| Steady `show_fuel`, windowed | 267–291 µs |
| `_row_texture` per R8 column, windowed | 17–18 µs, so the uploads themselves are cheap |

**Failure scenario.** `client_rendering.md` §8 has a 3 ms decode-and-upload budget that is already broken (B5). This pass adds 0.27–0.46 ms per message against the 0.13–0.19 ms the design cites, and most of it is an allocation that serves no purpose.

**Fix (verified for cost).** Hold the previous frame's trigger columns as a `Dictionary[String, PackedByteArray]`, which is free because the arrays are copy-on-write. Compare column by column with an early exit. Measured: 18–31 µs for all 15 columns against a separately built snapshot. Whether it is behaviourally equal to the concatenation was not tested. One caveat: per-column comparison must also compare the row counts, or one column growing while another shrinks could match. Today the concatenation leaves the same gap.

### P-S3 SHOULD-FIX: the anti-aliasing frame-time record can't be reproduced

**Where:** `tools/fuel_aa/frame_time.gd` and the "Frame time" table in `docs/design/research/fuel_antialiasing.md`.

**Defect.** The tool is committed as the source of the table, but it no longer runs against the shipped code:
1. It calls `fuel.use_pixel_metres(10.0 / 720.0)`, which is now a parse error ("Too few arguments", expected 2).
2. Its `edge` mode loads `res://addons/engine/render/fuel_rod_edge.gdshader`, which is not in the tree.
3. Its `none` mode now draws the shipped rod shader, which is the edge-coverage shader, so the "None" row would no longer measure hard edges.

The record says the single stick's stability was re-measured after the switch to `depth_prepass_alpha`. It does not say that for frame time. With `depth_prepass_alpha` the rod fragment shader runs twice: in the opaque prepass and in the blended pass.

**Rerun of the shipped path.** I patched only the arity and added `off` (fuel hidden) and `noflame` modes. Results at 1280×720, `--disable-vsync`, two runs, minimum / median of 300 intervals:

| Mode | Run 1 | Run 2 |
|---|---|---|
| Off | 3.97 / 4.47 ms | 4.17 / 4.80 ms |
| Shipped, no flames | 4.14 / 4.65 ms | 4.39 / 4.89 ms |
| Shipped, with flames | 4.18 / 4.62 ms | 4.53 / 5.04 ms |

So "costs about nothing" holds on the M2: the shipped pass with flames adds about +0.2–0.4 ms. But the record cites a path that no longer exists, and llvmpipe cost is still unmeasured (open item 3).

**Failure scenario.** The next person who reruns the record at a Godot upgrade or a shader change gets a parse error, or numbers for the wrong shader.

**Fix (unverified).** Repoint the tool at the shipped API, give it its own hard-edge variant, and re-record the table on the shipped shader with flames, saying which depth mode was used.

### P-N1 NIT: `use_palette` always forces a rebuild

**Where:** `client/addons/engine/render/fuel_pass.gd::use_palette` sets `_trigger = PackedByteArray()` unconditionally. `client/tests/support/render_stage.gd::show_fuel` calls `use_palette`, then `show_fuel`, on every call.

**Failure scenario.** Every stage call rebuilds, at 52–71 ms at the limits. This is test-only today, but it is the template step 7's wiring will copy. Calling the pair per message would rebuild every message, at about 25× the message's steady cost.

**Fix (unverified).** Invalidate only when `_recipe_slots` actually changes. Alternatively, rewrite only byte 3 of the instance image.

### P-N2 NIT: fragment work that is per-instance

**Where:** `client/addons/engine/render/fuel_object.gdshaderinc::instance_at`, `::fuel_colour`, `fuel_rod.gdshader::fragment` and `fuel_slab.gdshader::fragment`.

**Defect.** Each rod and slab fragment does 8 `texelFetch`es. Four of them are constant across the instance: 3 for `instance_at` and 1 for `state_tex` at `object_row`. They could be fetched once in `vertex()` and passed as `flat` varyings; the shaders already use `varying flat int`.
- Rods run this fragment shader twice because of `depth_prepass_alpha`.
- `discard` in the opaque slab shader disables early-z for the slab draw on most GPUs.

**Cost.** On the M2 at the golden view this is noise (P-S3's numbers). It is unmeasured at 120 px/m with large slabs, and under llvmpipe, where fragment cost is CPU time. Fix unverified.

### P-N3 NIT: `golden_fuel._mean_l` runs Lab over the whole frame for each mask

**Where:** `scripts/golden_fuel.py::_mean_l`, called by `_contrast` and `flame_findings`.

**Defect.** Each call converts a whole 1280×720 frame with `gm.lightness(rgb)` and only then masks it. That is 30 calls at 0.2 s each.

**Measured on `docker_golden_2`.** `fuel_findings` takes 7.8–8.6 s, and 6.4 s of that is `srgb_to_lab`. Converting `rgb[mask][None]` instead gives the identical mean (28.36987047552506 both, on `fuel-rig.png`) in 0.008 s instead of 0.26 s.

**Fix (verified).** Mask before converting, or cache L* per frame.

### P-N4 NIT: §4.1 says something different from what ships

**Where:** `client_objects.md` §4.1.

**Defect.** §4.1 says the instance texture holds "the row's three bytes and `state`", and that "`state` updates the RGBA8 texture's fourth byte". In the shipped code:
- Byte 3 is the recipe's palette slot (`fuel_pass.gd::_write_instance`).
- `state` is its own `state_tex`, uploaded every message (2,000 B, cheap) and read with one more fetch per fragment.

Performance itself is fine, but the doc describes a different path than ships. This is a wire/architecture-lens overlap.

## Checked and found adequate

- **Golden job against the 120 s per-call timeout.** I read the author's Docker runs (`scratchpad/docker_golden.log` and `docker_golden_2.log`, emulated linux/amd64 llvmpipe):

  | Call | Time |
  |---|---|
  | `golden.tscn`, 8 shots per tier | 10.4–17.0 s |
  | `cutaway_check.tscn` | 12.2–13.9 s |
  | `stability_check.tscn`, 32 frames | 9.1–9.4 s |

  The worst call is 17 s of 120 s. For comparison, CI on main had 3.0–4.4 s per golden call at 4 shots (run 44999709089).
- **`golden_stability`.** `stability_findings` takes 3.5 s on the real frames, and `ideal_coverage` 23 ms per frame. Its 256 `mgrid`s per call are wasteful but harmless.
- **`golden_fuel.strip`.** It works per segment with windowed bounds: 147 calls, 0.64 s.
- **`FuelSnapshot.state_problems`** costs 54–90 µs per frame, and **`first_rows`** 83–139 µs.
- **The flame pass on the GPU.** 2×10⁴ always-present quads collapse to zero area in the vertex shader. Drawing them costs noise against the no-flame mode on the M2. `custom_aabb` (±1000 m) means they are never culled, and that costs nothing measurable at this count.
- **Row-texture upload.** `duplicate` + `resize` + `create_from_data` + `update` costs 17–18 µs per column, windowed. The in-place `update` path holds while the row count holds.

## Not measured

- Anything under llvmpipe beyond wall time per Godot call.
- Slab-heavy scenes: the bench fixture has no slabs, so `_slab`, `_slab_tops` and the slab half of `problems` were not exercised.
- Behaviour above 2,000 objects.
