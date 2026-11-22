# Executor review: phase1/client-fuel (step 8 fuel pass), round 1

Scope: `git diff 69483d9` plus the untracked files, read as the tree stood on 2026-11-22. I did not run the gate or `godot_check.py`. I did run:
- `.venv/bin/pytest tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_golden_run.py tests/test_fuel_fixtures.py`: 52 passed.
- Godot 4.7.2 (windowed, M2, Compatibility) on a copy of `client/` under `$D=/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/rev_executor/`, with HOME and XDG set to `$D`. On that copy I ran `stability_check.tscn` as shipped, a deletion probe and a two-frame probe scene of my own (`$D/client/tests/probe_update.gd`).

I modified nothing in the worktree.

## Findings

### S1 SHOULD-FIX: nothing guards the burnt-out branch or the `state_tex` path
Location: `client/addons/engine/render/fuel_object.gdshaderinc::fuel_colour` (`if (burnt_out) return colour;`), `fuel_pass.gd::show_fuel` (the `state_tex` upload), `scripts/fuel_fixtures.py::visible`.

**Defect.** The fixture's only burnt-out object is object 74 (`rod_spent`). I decoded it: every segment is at 20 °C with `ignited_fraction` 0. At those values the glow term (below the 525 °C start) and the burning term (ignited 0) are already zero, so the branch changes no pixel. Delete the `if (burnt_out)` block, or break the `state_tex` row mapping (for example, index `state_tex` by `INSTANCE_ID` instead of `object_row`), and every unit test, every fuel golden and every `golden_fuel` check stays green. No check reads `rod_spent` at all.

The commit claims "none of the light terms once an object is burnt out", and §4.3 states it as contract. Neither has a guard.

**Failure scenario.** A server sends a burnt-out object whose remaining char is still at 900 °C (§4.3: "draws its remaining segments … without glow"). The client draws it glowing, and nothing catches it.

**Does the mechanism work today?** Yes, verified by probe. All segment temperatures set to 1,200 °C: 8,205 px above r > 0.5. Then every state set to 1 and `show_fuel` called again: 0 px, with `rebuilds` still 1.

**Fix (unverified).** Put `rod_spent` at glow temperature with ignited > 0 in the fixture. Add a `golden_fuel` check that its segments are no brighter than a cold reference and that no flame-ID pixels sit above it. Prove it by deleting the branch.

### S2 SHOULD-FIX: the flame shader ignores burnt-out state and burnt-through segments
Location: `client/addons/engine/render/fuel_flame.gdshader::vertex`.

**Defect.** The flame reads only `ignited_tex`. It never reads `state_tex` or `thickness_tex`. §4.3 says a burnt-out object draws "without glow or flame". Likewise, a segment with `thickness_fraction` 0 has no surface, yet it would still raise a flame.

**Failure scenario.** A frame where an object turns burnt out while one segment still reports ignited > 0, or a burnt-through segment with ignited > 0. A flame tongue is drawn over a gap or over dead char. Nothing in the fixture exercises either case: burnt-through rows all have ignited 0, and so does the burnt-out rod.

**Fix (unverified).** Collapse the quad when the object's state is 1 or the row's thickness is 0. Look the object up by segment row. Covered by the same fixture change as S1.

### S3 SHOULD-FIX: `segment_count` 0 is accepted, and the shader clamp then has min > max
Location: `client/addons/engine/render/fuel_snapshot.gd::_object_problems`, `fuel_object.gdshaderinc::segment_row`.

**Defect.** No check refuses a count of 0 on an object with a positive length. The sum check and the key check both still pass, because that object simply contributes no keys. `segment_row` then computes `clamp(k, 0, inst.count - 1)` = `clamp(k, 0, -1)`, which GLSL leaves undefined. The row it returns is `first + (0 or -1 or k)`, and `first` is the next object's first row. So the fragment reads another object's state, which breaks §4.1's "the clamp keeps every fragment on its own object".

**Failure scenario.** An encoder bug, or a zero-length rounding, sends count 0 for a 0.3 m rod. The rod draws with its neighbour's temperature and burn-through.

**Fix (unverified).** Refuse a count below 1 in `_object_problems`, and add a row to `test_every_structural_check_refuses`.

### S4 SHOULD-FIX: a recipe past slot 15 doesn't draw magenta, and no test checks the recipe byte
Location: `client/addons/engine/render/fuel_pass.gd::use_palette` and `::_write_instance`.

**Defect 1.** The `use_palette` docstring and §4.1 both say that an unknown recipe, or a recipe past the palette, "draw magenta". But `_write_instance` falls back to `PALETTE_SIZE - 1` (slot 15). With 16 or more recipes, slot 15 holds the 16th recipe's real colour. So with 17 recipes, the 17th draws as the 16th, not magenta. No test runs this branch.

**Defect 2.** `test_the_instance_texture_carries_exact_rows_past_half_float` checks bytes 0–2 and 4–11, but not byte 3, the palette slot. Delete `bytes[at + 3] = slot` and byte 3 becomes the top byte of `first_row`, which is 0. Every object then draws `pine_rod`'s colour. No unit test fails. Only a CI golden could catch it: `pine_slab` and `pine_rod` differ by about 0.04–0.07 in sRGB, which may sit inside the golden tolerance.

**Fix (unverified).**
- Reserve one slot for magenta, or refuse more than 15 recipes.
- Assert byte 3 for the slab's instance in the existing test.
- Add a 17-recipe test.

### S5 SHOULD-FIX: two statements in `client_objects.md` §4.1 no longer describe the code
Location: `docs/design/client_objects.md` §4.1.

**False statement 1.** "three RGBA8 texels per instance: the row's three bytes and `state` …" and "`state` updates the RGBA8 texture's fourth byte and never triggers a rebuild". In the code, the fourth byte is the recipe's palette slot, and `state` lives in a separate `state_tex` (`fuel_object.gdshaderinc` header, `fuel_pass.gd::_write_instance`). The design is the contract for step 7's decoder and anything else that reads this texture, so it should match.

**Unmeasured number.** "3.6–3.8 ms per rebuild". `_rebuild` now also runs `FuelGeometry.segment_tops`, a GDScript loop that builds one flame transform per segment row, and calls `set_instance_transform` for each. That is the per-segment GDScript loop §2 itself measured at 4.4–6.9 ms at the limits (2×10⁴ rows). The rebuild cost at the limits is therefore unmeasured, and very likely above 3.8 ms. That shows up as a hitch on every insertion. §5.3's new "Cost" bullet doesn't mention it either.

**Fix (unverified).** Correct the texel layout text. Measure the rebuild at the limits (2,000 objects, 2×10⁴ segments) and write down the number, or move flame placement out of GDScript.

### N1 NIT: the stability check passes the anti-aliasing deletion on the rig tier
This is already disclosed in `fuel_antialiasing.md` open item 1; I reproduced it on the production shader. With `ALPHA = coverage >= 0.5 ? 1.0 : 0.0` in `fuel_rod.gdshader`, the ratios (bar 2.0) are:

| Frame | Ratio |
|---|---|
| rig-30 | 1.16 (passes) |
| rig-72 | 2.12 |
| laptop-72 | 5.78 |
| laptop-30 | 5.90 |

The claim "the check fails when anti-aliasing is deleted" is true for the check as a whole, but only the laptop tier carries it.

`tests/test_golden_stability.py::test_a_hard_edged_line_crawls_well_beyond_the_ideal` asserts `> 1.5 × ideal`. That is looser than the 2.0 bar the shipped check applies, so it doesn't show the shipped check would catch a hard edge on rig. The owner question stays open.

### N2 NIT: the in-place texture update has no gate on pixels
Location: `fuel_pass.gd::_row_texture`, the `texture.update(image)` branch.

The goldens draw one frame each, and the headless unit tests can't read texture contents. So "a burnout is a texture upload, never a rebuild" is held only for the rebuild count, not for what is drawn. Replace `texture.update(image)` with a bare `return texture` and every gate stays green, while burnouts stop showing.

It works today, verified by probe: 7,901 fuel-ID px, then 0 after setting every `thickness_fraction` to 0 and calling `show_fuel` again, with `rebuilds` 1. A two-frame variant of the golden scene, or of `stability_check`, would guard it.

### N3 NIT: `stability_findings` can pass with nothing measured, or crash
Location: `scripts/golden_run.py::stability_findings` and `::draw_all`.
- A `stability.json` of `{}` passes with nothing measured. No check requires the four keys rig-72, rig-30, laptop-72 and laptop-30.
- A missing `stability.json` raises `FileNotFoundError` (a loud traceback, but not a finding). `draw_all`'s "no frame at" sweep covers `SHOTS` only, not the 32 stability frames.
- If `ideal == 0` and the check fails, building the message divides by zero.

### N4 NIT: the instance encoding's limits are not checked on the client
Location: `client/addons/engine/render/fuel_snapshot.gd::problems`.

The instance texel packs `first_row` into 24 bits (byte 3 overwrites the top byte after `encode_u32`) and `object_row` into 16 bits. Nothing on the client refuses more than 65,535 objects or more than 2²⁴ segment rows. The fixture's 1 MB cap keeps these out of reach today, but step 7's decoder should refuse past the world limits (2,000 objects, 2×10⁴ segments), or past the encoding's own limits.

## What I checked and found sound
- **Handedness.** `FuelGeometry._rod` builds (across, axis, across × axis), determinant |a×b|² > 0. `_slab` builds (along, along×across, −across), determinant +1. `axes.gdshaderinc` is a rotation. The basis-fix deletion claim in d91df0f is consistent with the determinant test.
- **Flame ordering.** Flame instance i is segment row i: `segment_tops` walks objects in object order, and `_segment_key_problems` holds segments contiguous in that order.
- **Fixtures.**
  - `fuel_ramp` has 74 objects and 2,265 segment rows, minimum count 20, and the visible objects start past 2,048.
  - `fuel_stick` has 1 rod and 50 segments.
  - Burnt-through rows have ignited 0.
  - `fuel_fixtures.stale` now covers both fixtures.
- **Stability numbers.** The research doc says the production shader gave "the same four values". I reproduced rig-72 1.10, rig-30 0.99, laptop-72 1.20 and laptop-30 0.78, against the doc's 1.09, 1.00, 1.20 and 0.78. True within rounding. Drawn width is 2.0 px at both zooms, so both are floored.
- **Python check logic.** `golden_fuel`'s checks each have a passing and a failing synthetic test. The stability measure's bins, end drop and percentile are tested.
- **Shot parsing and the shared inflate.** `GoldenShot.parse` refuses the new malformed forms. The `SnapshotFixture.inflate` refactor keeps every refusal.
- **Snapshot refusals.** `FuelSnapshot.problems` has a refusal test for each listed §3.2 check, and for state > 1.
- **Pixel sizes.** `FuelFootprints` and `stability_check`'s `drawn_px` use the same `max(radius, output_px)` as the rod shader's `floor_half_m`.

## Not verified
- 1b's claim that the segment-key deletion fails exactly one of 46 tests: read and plausible, but not rerun.
- The "0.42 → 0.91" pile coverage numbers: not rerun.
- `object_areas`' per-object deletion claim (the floor in rendered pixels): needs the llvmpipe frames.
- The commit's "54 client tests PASS": not rerun.
