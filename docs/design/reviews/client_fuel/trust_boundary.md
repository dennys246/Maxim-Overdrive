# Trust boundary review: phase1/client-fuel (step 8 fuel pass), round 1

Reader: Trust boundary lens. Tree: `git diff 69483d9` plus untracked files, read as it stood on 2026-11-22. Method: I read the seam (`fuel_snapshot.gd`, committed in 645e0d3 and unchanged in the working tree), the drawing side (`fuel_pass.gd`, `fuel_geometry.gd`, `fuel_object.gdshaderinc`, `fuel_rod/slab/flame.gdshader`), the fixture reader (`tests/support/fuel_fixture.gd`), its tests and `render_stage.gd`. I then ran probes in Godot 4.7.2 headless on a copy of `client/` under the scratchpad (`$D/rev_trust/`, HOME and XDG moved there, imported first). The unmodified copy's client suite prints `client-tests: PASS 57 tests`. I did not touch the worktree or its git state.

**Summary:** the seam catches what its tests exercise (wrong sizes, unknown recipe, region or kind, counts that sum wrong or are spread over the wrong objects, a geometry row on the wrong object, NaN origins, off-unit axes, non-positive sizes, bad state). Nothing I found crashes the client. A Godot `ERR_FAIL` is printed and returns 0. But I confirmed three ways a malformed table passes `problems()` and is then drawn wrongly:

- the pass reads past a geometry table;
- infinite geometry goes into the transforms;
- a fragment reads another object's segment.

The per-frame columns' sizes are checked only when the trigger changes. No row bound exists anywhere on the seam. There are 3 BLOCKER, 5 SHOULD-FIX and 4 NIT findings. All are `open`.

---

## BLOCKER

### TB-B1: `fuel_snapshot.gd::_kind_name` and `fuel_pass.gd::_rebuild` decide an object's kind by different rules, so a vocabulary with a duplicate id passes the check and makes the pass read past the rods table

- **Defect:** `_geometry_problems` names a kind id by the first vocabulary entry with that id (`_kind_name`). `_rebuild` and `FuelGeometry.segment_tops` instead test `kind == kind_ids["rod"]` and send everything else to slabs. Neither the seam nor `FuelFixture._ids` refuses two names sharing an id.
- **Failure scenario (run):** one slab object, `kind = 1`, `kind_ids = {"slab": 1, "rod": 1}`, an empty rods table and a matching slab row.
  - `problems()` returns `[]`, because `_kind_name(1)` is `"slab"` and the slab row is present.
  - `show_fuel` then puts the object in `rod_rows`, and `FuelGeometry._rod` decodes row 0 of the empty rods columns: 16× `ERROR: Condition "p_offset < 0 || p_offset > (int64_t(size) - 4)"`, from `fuel_geometry.gd:99` through `_place` and `_rebuild`.
  - The result is `rods.instance_count = 1`, `slabs.instance_count = 0`, with a rod made from zero geometry.
  - This also breaks the invariant `_place` documents ("Instance i is geometry row i, which FuelSnapshot holds").
- **Fix:**
  - Refuse two kinds that share an id in `_vocabulary_problems`. The same applies to recipes, since `use_palette` silently overwrites a slot when two names share a recipe id.
  - Better still, give the pass and the check one function that maps an id to a kind name, so they cannot disagree again.
- **Verified** (the first half): I added a uniqueness check to the copy. It reports `"two kinds share an id"` for `{"slab":0,"rod":0}` and `{"rod":0,"slab":1,"bark":0}`, and the suite still prints PASS 57.

### TB-B2: `fuel_snapshot.gd::_rod_problems` accepts an infinite rod length or radius

- **Defect:** §3.2 says the decoder refuses "non-finite geometry". The rod check is `length > 0.0 and radius > 0.0`, which `INF` passes. The slab check does test `sizes.is_finite()`, and the rod check does not.
- **Failure scenario (run):** with `rods.length_m[0] = INF` or `rods.radius_m[0] = INF`, `problems()` returns `[]`.
  - `FuelGeometry._rod` then builds a basis scaled by infinity and an origin of `origin + axis*inf*0.5` (inf or NaN).
  - That transform goes into the MultiMesh, so the MultiMesh's culling box becomes infinite or NaN.
  - The rod's vertex shader receives `length(MODEL_MATRIX[1])` = inf.
  - `_rod_tops` places a flame at `origin + UP*inf`.
- **Not tested:** no case covers `rods.length_m` at all (zero, negative, NaN or inf), or `radius_m` NaN or inf.
- **Fix:** `is_finite(length) and length > 0.0 and is_finite(radius) and radius > 0.0`, plus test cases.
- **Verified:** with that change in the copy, both INF cases are refused with `"rod row 0 has bad geometry … length inf"` / `"radius inf"`, and the suite still prints PASS 57.

### TB-B3: `segment_count = 0` passes, and the shader's clamp then reads a neighbouring object's segment

- **Defect:** nothing refuses `segment_count == 0`. The keys check accepts it, because an object with zero segments implies zero keys. In `fuel_object.gdshaderinc::segment_row`, `clamp(k, 0, inst.count - 1)` becomes `clamp(k, 0, -1)`. GLSL leaves that result undefined when min > max, and on common hardware it returns −1.
  - So the object's fragments read row `first - 1`, which is the previous object's last segment. For the first object they read row −1, a texel outside the texture.
  - They take that segment's thickness (burnt through or not), temperature, ignition and char.
  - §3.2's sentence "§4.1's clamp keeps every fragment on its own object" is then false.
  - The rod fragment shader also clamps `v_s` to `segment_m * 0` = 0 first, so every fragment of the object lands on that one foreign row.
- **Failure scenario (run):** a one-object snapshot with `segment_count = 0` and empty segment columns gives `problems() == []`.
- **Fix:** refuse `segment_count == 0` in `_object_problems`. fire_solid's segments rule gives L > 0, so ⌈L/ℓ⌉ ≥ 1, and a zero count is malformed. If zero is ever legal, the shader must discard on `inst.count == 0` instead.
- **Verified** (the refusal half): with the check in the copy, moving object 0's segments onto object 1 is refused with `"object row 0 has no segments"`, and the suite still prints PASS 57. I did not render the shader read. It follows from the GLSL definition of `clamp`.

---

## SHOULD-FIX

### TB-S1: the per-frame columns' sizes are checked only when the trigger bytes change, and `state_problems()` checks values, not size

- **Defect:**
  - `_shape_problems` checks that every column has `rows × dtype` bytes, but it runs only inside `problems()`, which runs only when `trigger_bytes()` changes.
  - `trigger_bytes()` leaves out `objects.state` and the four segment value columns: `surface_temperature_c`, `ignited_fraction`, `thickness_fraction` and `char_fraction`.
  - `state_problems()`, the one per-frame check, loops over whatever size `state` has.
  - `FuelPass._row_texture` uploads columns of any length without complaint.
- **Failure scenario (run):**
  - Draw the fixture, then replace `objects.state` with 1 byte and `segments.thickness_fraction` with 0 bytes, leaving the trigger unchanged.
  - `state_problems()` returns `[]`, and `show_fuel` accepts the frame without a rebuild.
  - The thickness texture is then one row of zeros, so every segment reads `thickness <= 0` and is discarded. The whole fire vanishes without a refusal.
  - With more than 256 objects, a short `state` column sends `row_at(object_row)` outside the texture, which is undefined in GLES3.
- **Fix:** have the per-frame check also hold each non-trigger column to `rows × dtype`. That is five integer compares, no row walk. Rename it to `frame_problems()`.
- **Unverified.**

### TB-S2: whoever compares the trigger can draw a frame nobody checked, and the trigger does not cover the inputs `problems()` depends on

- **Defect 1, a refused frame poisons the comparison:** §3.2 and the seam's doc say the checks run "when the trigger bytes differ from the last frame's". Read literally, this scenario is possible:
  - frame A is checked and drawn;
  - frame B changes structure and is refused;
  - frame C carries B's structure again.
  - C's trigger equals the last frame's (B's), so no check runs and C is drawn unchecked.
  - The comparison must be against the last **accepted** frame.
- **Defect 2, two independent trigger copies:** the pass keeps its own `_trigger`, and `use_palette` resets it. Step 7's decoder will keep another. Nothing ties "checked" to "rebuilt".
- **Defect 3, the vocabularies:** `problems()` also depends on `kind_ids`, `recipe_ids` and `region_names`, which `trigger_bytes()` leaves out.
  - Suppose a new welcome swaps the kind ids, or drops a region, and the object bytes are the same. No recheck runs.
  - Because RenderStage calls `use_palette` every frame (TB-N1), `_rebuild` does run, and it dispatches with the new vocabulary against geometry nobody rechecked. That is TB-B1's read past a table, reached without a duplicate id.
- **Fix:** one owner holds the comparison and the check together, for example `FuelPass.show_fuel(snap, region_names) -> Array[String]`.
  - It runs `problems()` when the trigger differs from the last *drawn* frame, refuses and returns the reasons if any, and only then rebuilds.
  - The trigger, or a welcome generation number, must cover the vocabularies and the region map.
  - Fix the "last frame's" wording in §3.2 in the same change.
  - If this waits for step 7, defer it with step 7's decoder as the trigger.
- **Unverified.**

### TB-S3: nothing bounds the row counts, and the drawing side has hard limits the seam never states

The drawing side depends on these limits:

- `_write_instance` stores the first row with `encode_u32` and then overwrites byte 3 with the recipe slot. A first row of 2^24 or more silently wraps, and the object reads another object's segments.
- `object_row` is a u16 (`encode_u16(at + 6, row)`). Past 65,535 objects, an object reads another object's `state`.
- The instance texture is `3 × n` texels and each segment texture is `256 × ⌈rows/256⌉`. A height above `GL_MAX_TEXTURE_SIZE` (16,384 typical, 2,048 the GLES3 minimum) fails at upload.
- `_shape_problems` computes `rows[table] * DTYPE_BYTES`, which overflows int64. **Run:** `rows["rods"] = 2^62` with empty rod columns gives `_shape_problems() == []`, since 2^62 × 4 wraps to 0 for every all-4-byte column. `problems()` would then loop 2^62 times in `_geometry_problems`, which is a hang.

The 3.5 MiB join cap admits roughly 58,000 objects, well past the instance texture's height limit. fire_solid's world limits (2,000 objects, 2×10⁴ segments, client_objects §1) would keep all of these safe, but the client never checks them.

- **Fix:** refuse rows past the world limits in `_shape_problems`, before the multiplication, taking the limits as a contract value from their one owner. Add a test at limit + 1.
- **Unverified.**

### TB-S4: `surface_temperature_c` is drawn with no client-side clip, and an f16 inf drives the HDR glow to infinity

- **Defect:** §3.3 has the server clip the value to [−273, 6000], and the client takes the f16 as it arrives.
  - With t_c = +inf (f16 `0x7C00`), `t_c > FUEL_GLOW_START_C` is true, so `glow_curve` returns hue × inf, and inf goes into the HDR target and the bloom blur.
  - NaN is mostly inert, because the comparison is false.
- **Fix:** clamp in `fuel_colour` (`t_c = clamp(t_c, -273.0, 6000.0)`, which also clips the server's own range), or refuse non-finite values in the per-frame check. The f16 column is small: 2×10⁴ halves.
- **Unverified.** I did not render it, so the effect on the bloom is inferred.

### TB-S5: the seam's rejection paths are not all tested (the charter aims at 100% branch coverage)

`test_fuel_snapshot.gd` does not exercise these paths:

- `_shape_problems`'s "no row count" branch: a row count missing or negative on the snapshot itself.
- `segment_length_m` NaN, inf or 0 (only −0.02 is tested).
- `rods.length_m` in any form.
- `rods.radius_m` non-finite.
- slab `length_m` and `width_m`, non-positive or non-finite.
- slab origin non-finite.
- `length_axis` off unit.
- a non-finite axis component: NaN on the axis rather than the origin.
- an object whose geometry row sits in the other kind's table with the right id. The only "rods rows" case changes an id to 70,000.

The fixes for TB-B1, TB-B2, TB-B3 and TB-S1 each add a path that needs a case too. Each case should be proved by deletion (Executor lens).

---

## NIT

- **TB-N1: rebuild every frame (Performance lens).** `render_stage.gd::show_fuel` calls `fuel.use_palette` before every `fuel.show_fuel`, and `use_palette` clears `_trigger`. **Run:** three RenderStage-style frames gave `rebuilds = 3`. Every frame through RenderStage rebuilds, which defeats §4.1's "the rebuild is rare". It also widens TB-S2's window. `test_only_a_structural_change_rebuilds` calls `use_palette` once, so it cannot see this.
- **TB-N2: recipes past the palette share a real recipe's colour.** `fuel_pass.gd::use_palette` / `_write_instance` say recipes past the 16 slots "draw magenta", but they fall back to slot `PALETTE_SIZE - 1`. Once 16 or more recipes exist, that slot is the 16th recipe's real colour, so an unpaletted recipe looks like a real one. The problem is reported, but the drawing contradicts the comment and §4.1's "drawn magenta". Give a dedicated magenta slot, or refuse.
- **TB-N3: object ids are neither sorted nor unique-checked.** §3.2 says `objects` rows are sorted by `object_id` and ids are never reused. Duplicate or unsorted ids pass every check. Nothing draws wrongly today, but §4.3's picking will key on the id.
- **TB-N4: fixture reader paths untested** (`tests/support/fuel_fixture.gd`). These refusals are not exercised:
  - `named()`'s "data must be a file name beside it" (a path-traversal guard);
  - an unreadable header;
  - a header that isn't a JSON object;
  - `rows` not whole or negative;
  - `columns` not an object;
  - a missing column;
  - a non-name recipe entry (`"recipes": [3]` covers only "not an object").
  
  `_ids` also accepts negative ids and ids beyond u8 or u16, and duplicates (TB-B1). The reader's header refusal otherwise looks complete: format, version, both SHA-256s, the `data_size` bound, offset and size inside the data, and dtypes are all checked before any column is used.

---

## Checked and sound

- `_shape_problems` runs first and short-circuits, so no row walk reads a short column (tested).
- Unknown kind, recipe and region are refused, and so are a kind name outside `DRAWABLE_KINDS` and state > 1.
- The keys check rebuilds the implied keys and compares them natively, which catches counts that sum right but are spread wrong (tested). Its allocations are bounded by the actual column sizes.
- The shader clamps `recipe` to 0..15, and `count` and `segment_length` come from checked u16 and f32 columns.
- `use_pixel_metres` refuses non-finite and non-positive values (tested).
- `inflate` bounds the decompressed size before parsing.

| ID | Severity | Status | Location |
|---|---|---|---|
| TB-B1 | BLOCKER | open | `fuel_snapshot.gd::_kind_name`, `fuel_pass.gd::_rebuild`, `fuel_geometry.gd::segment_tops` |
| TB-B2 | BLOCKER | open | `fuel_snapshot.gd::_rod_problems` |
| TB-B3 | BLOCKER | open | `fuel_snapshot.gd::_object_problems`, `fuel_object.gdshaderinc::segment_row` |
| TB-S1 | SHOULD-FIX | open | `fuel_snapshot.gd::state_problems`, `fuel_pass.gd::show_fuel` |
| TB-S2 | SHOULD-FIX | open (deferrable to step 7) | `fuel_snapshot.gd::trigger_bytes`, `fuel_pass.gd::show_fuel`, client_objects §3.2 |
| TB-S3 | SHOULD-FIX | open | `fuel_snapshot.gd::_shape_problems`, `fuel_pass.gd::_write_instance` |
| TB-S4 | SHOULD-FIX | open | `fuel_object.gdshaderinc::fuel_colour` |
| TB-S5 | SHOULD-FIX | open | `tests/unit/render/test_fuel_snapshot.gd` |
| TB-N1 | NIT | open | `tests/support/render_stage.gd::show_fuel`, `fuel_pass.gd::use_palette` |
| TB-N2 | NIT | open | `fuel_pass.gd::use_palette`, `fuel_pass.gd::_write_instance` |
| TB-N3 | NIT | open | `fuel_snapshot.gd::_object_problems` |
| TB-N4 | NIT | open | `tests/support/fuel_fixture.gd` |

The verified fixes for TB-B1, TB-B2 and TB-B3 were made only in the scratch copy, `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/rev_trust/client/addons/engine/render/fuel_snapshot.gd`. The author still needs to fold them, with tests.
