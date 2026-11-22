# Wire integrity, delta 1: phase1/client-fuel (round 1 → delta 1)

**Scope.** I read the working tree as it stands on 2026-11-22: HEAD d91df0f, with the round-1 tree and the fold
uncommitted. I read it against `git diff 69483d9` plus the untracked files, my round-1 report, the author's
`fold.md` (which I treated as claims to check, not as statuses), `client_objects.md` §3–§5 and §7, and
`contracts.md`. I modified nothing in the worktree.

**What I ran:**
- `.venv/bin/python -m pytest -q tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_fuel_fixtures.py
  tests/test_golden_run.py`: 68 passed.
- On a copy of `client/` in the scratchpad, with HOME and XDG moved into it:
  - the headless import, then `tests/run.gd`. The 72 existing client tests pass. I added one probe test (W2-S1), and
    it fails.
  - `tools/fuel_aa/frame_time.gd` headless, `AA_MODE=shipped`. It loads, nothing is refused, and it prints a result.
- A deletion probe in Python: I monkeypatched `object_areas` to read red instead of green, and the body test then
  fails (480 > 400 px).

I did not run the golden image, `golden_run.py` or the gate.

**The tree moved while I reviewed it; read this first.** After I found W2-S1, `fuel_pass.gd`, `fuel_snapshot.gd`
and `test_fuel_pass.gd` changed on disk (a concurrent fold, marked "review TB2-B1"/"TB2-S1").
- `show_fuel` now runs `frame_problems()` first and builds no instances before every check has passed.
- `kind_name` is gone.
- I reran my W2-S1 probe on a fresh copy of the new tree: it is refused with `rebuilds = 1`, and the client suite
  passes 75 tests.

So, read from the tree now: **W2-S1 is fixed** (verified by the probe) and **W2-N3 is fixed** (the method is deleted).
Everything else below was read before that fold. I re-read `show_fuel` and the pass's comments after it: W2-N5's
stale comment (line 85) is still there. I did not re-review the rest of the concurrent fold.

## 1. Round-1 findings: fold status, read from the tree

| Finding | Status | What the tree shows |
|---|---|---|
| S1: `golden_fuel.segments` refuses nothing | **fixed** | Refuses: an unknown format or version, and a `data_size` or `data_sha256` mismatch (`ValueError`, 4 parametrised cases).<br>One name: `FIXTURE_NAME`, and `golden_run.FUEL_SCENE` is built from it.<br>Held: `test_the_reader_knows_the_writers_format_and_the_drawn_fixture` ties FORMAT/VERSION to `fuel_fixtures`. (Residual: W2-N6.) |
| S2: §4.1's texel layout is stale | **fixed** | §4.1 now states what `_place` writes and what `instance_at` decodes:<br>texel 0: first row (24 bits) and palette slot (slot 15 is magenta);<br>texel 1: count (u16) and object row (u16);<br>texel 2: ℓ's f32 bits;<br>`state` is its own R8 texture by object row.<br>All three statements agree. (Residual, an older line in the same section: W2-N1.) |
| S3: the floor in four places; footprints untested | **fixed** | One GDScript owner: `FuelPass.drawn_half_m`, called by `FuelFootprints._rod` and `stability_check._frames`. The shader's `max(radius_m, floor_half_m)` names it in a comment.<br>The kind walk is `FuelSnapshot.geometry_rows` everywhere: pass, flames, footprints, checks.<br>Footprints write `out[first[row] + k]`, so row order no longer depends on kind grouping.<br>`test_fuel_footprints.gd` holds them to the geometry, and its thin-rod case is meaningful: radius 0.01 is below the 0.0139 m pixel. |
| S4: `tools/fuel_aa` broken, cited as evidence | **fixed** | `stability_frames.gd` and `measure.py` are gone.<br>`frame_time.gd` drives the shipped `FuelPass` with the new `show_fuel(snap, regions)`. I ran it: no refusal, and it loads no missing shader.<br>The research record now cites `stability_check.tscn` for stability and says the MSAA row can't be rerun. (Residual: W2-N4.) |
| S5: the coverage channel's meaning; bodies in the area count | **open** (the encoding half) | **Bodies half fixed:** `object_areas` reads green, which the bodies' pure red never writes. I proved the test by deletion: reading red, `test_a_body_drawn_over_fuel_counts_no_fuel_area` fails.<br>**Open:** whether the fuel-ID coverage is linear or sRGB-encoded per tier (the direct path on rig, the buffered path on laptop). It is still unstated in §7.2 and untested. `golden_stability` reads red and `object_areas` reads green under the same assumption. The author records it as open, with no trigger, so it is not deferred. |
| N1: stale grammar copies | **fixed** | `golden.gd`'s header and `_fail` defer to `GoldenShot`, and `golden_shot.gd`'s message carries `[+<fuel>]`. |
| N2: orphan comment in `traversal.gdshaderinc` | **fixed** | It is gone. |
| N3: 0/1/2 view integers | **fixed** | `FuelPass.View` is used by `GoldenShot.FUEL_VIEWS`, `RenderStage.use_fuel_view`, `stability_check.gd` and the tests. The shader comment links `FuelPass.View`. The parser refuses a fuel fixture in `crack_mask`/`glow_mask`, and a fuel pass with no fuel fixture. |
| N4: recipe vocabulary twice | **fixed** | `test_the_recipe_palette_colours_every_recipe_the_fixture_names`. |
| N5: glow constants twice | **fixed** | `test_the_fuel_glow_starts_and_spans_as_the_cells_glow` holds 525/975 to `encoding.GLOW_START_C`/`GLOW_FULL_C`. |
| N6: `draw_all` docstring; missing files traceback | **fixed** | The docstring names three scenes.<br>A missing `segments.json` is a `draw:` finding.<br>A missing or short `stability.json` or `stab-*.png` is a finding (`golden_stability.findings`, tested), and so is an ideal of 0.<br>Trivial residual: the summary line still reads "cut-away" and doesn't mention stability. |
| N7: stale checklist and backlog | **fixed** | The S5 deferral is gone from `checklists.md`. B7 names the fuel golden, `golden_fuel.py`, `golden_stability.py`, and "§6.3's ID-mask areas for cells". |

**Counts:** of round 1's 5 SHOULD-FIX, 4 are fixed and 1 is open (S5's encoding half). All 7 NITs are fixed.

## 2. Contract table, rebuilt for the tree now

| Contract (owner) | Producer | Consumers | Agreement |
|---|---|---|---|
| Shot grammar `<fixture>[+<fuel>]:<tier>:<pass>:<png>`; 6 passes (`GoldenShot`, its one statement) | `golden_run.SHOTS` → `draw_all` | `GoldenShot.parse` → `golden.gd::_draw`; `test_golden_shot.gd` | Agrees. Cell masks with fuel, and fuel passes without fuel, are refused. |
| `SHOTS`: 8 per tier; `FUEL_SCENE = alley_cold+FIXTURE_NAME` | `golden_run` | `draw_all`'s missing-frame and footprint checks; every `golden_fuel` reader (`fuel-<tier>{,-noflame,-fuel_mask,-flame_mask}.png`) | Agrees: names are read from one tuple and one constant. |
| `FuelPass.show_fuel(snap, region_names) -> Array[String]` | `FuelPass` | `RenderStage.show_fuel` (which adds `use_palette`'s problems), `golden.gd`, `stability_check.gd`, `frame_time.gd`, `test_fuel_pass.gd` | Every caller found by grep passes two arguments and reads the return. `golden.gd` and `stability_check` fail the shot on any refusal. **But a refusal can arrive after a rebuild: W2-S1.** |
| `FuelPass.View {SHADED, FUEL_ID, FLAME_ID}` ↔ shader `fuel_debug` 0/1/2 | `use_view` (`_param`, all 4 materials) | `fuel_rod.gdshaderinc::rod_albedo`, `fuel_slab`, `fuel_flame` | Agrees: rod, slab and flame each branch on 1 and 2 as the enum names them. |
| `FuelSnapshot.structure()` / `problems()` / `frame_problems()` | `FuelSnapshot` | `FuelPass.show_fuel`; `FuelFixture` (`frame_problems`) | Structure excludes exactly `FRAME_COLUMNS`. `frame_problems` checks only the sizes of those columns and `state ∈ {0,1}`. The order in `show_fuel` is wrong: W2-S1. |
| `geometry_rows(kind)`: geometry row i = object row `geometry_rows(kind)[i]` | `FuelSnapshot` | `FuelPass._place`, `FuelGeometry.flame_buffer`, `FuelFootprints.of`, `_geometry_problems`, tests | One rule. `_geometry_problems` holds the geometry tables to it. |
| `kind_name(id)` | `FuelSnapshot` | the unit test only | No shipped caller (W2-N3). |
| Per-instance texture (`client_objects.md` §4.1) | `FuelPass._place`: bytes 0–2 `first`, 3 slot, 4–5 count, 6–7 object row, 8–11 ℓ bits | `fuel_object.gdshaderinc::instance_at` → `instance_fields` → flat varyings | Byte for byte, shader = writer = §4.1. `test_the_instance_texture_carries_exact_rows_past_half_float` reads every field, slot byte included. |
| `state_tex` (R8 by object row, every frame) | `show_fuel` via `_param` (all materials) | `burnt_out()` in `fuel_colour` (rod, slab) and in the flame `vertex()` | Agrees. The flame material receives it because `_param` loops over all four materials. |
| Segment textures (4 columns, 256-wide rows) | `show_fuel` `_row_texture` | rod, slab, flame (`ignited_tex`, `thickness_tex`) | Agrees. In-place updates read the current texture from the rod material, and every material holds the same `ImageTexture`. |
| `segment_object_tex` (RF, object row per segment row) | `_rebuild` → `FuelGeometry.segment_objects`, `_param_on("flame")` | `fuel_flame.gdshader::vertex` (`int(texelFetch(...).r)` at `row_at(INSTANCE_ID)`) | Agrees. Flame instance i is segment row i (`_flames` writes `(first+k)`), and `segment_objects` runs in the same object order. f32 is exact far past 2,000. Tested (`test_each_flame_knows_its_object_row`). |
| `flame_height_m` = `FuelPass.FLAME_HEIGHT_M` | `_init` `_param_on("flame")` | the flame shader's height; `_fit_boxes`' reach; `golden_fuel.FLAME_REACH_M` (= 2×) | One constant, and `test_golden_fuel` parses the .gd to hold the 2× relation. |
| Rod's two materials (`next_pass`) | `_materials["rod"].next_pass = rod_fringe`; `KIND_MATERIALS["rod"] = [rod, rod_fringe]` | `fuel_rod.gdshader` (depth), `fuel_rod_fringe.gdshader` (colour), both including `fuel_rod.gdshaderinc` | Every uniform reaches both: `_param` loops over all 4, and `_param_on("rod")` sets both. `test_a_rods_fringe_is_its_cores_next_pass_and_gets_every_uniform` compares every declared uniform. `uniform_names()` (13) is held to each shader's declarations. |
| `drawn_half_m` / `floor_half_m` | `FuelPass.drawn_half_m`; `use_pixel_metres(output_px_m, scale)` | rod shader (`max(radius, floor_half_m)`), `FuelFootprints`, `stability_check` (`drawn_px`) | One GDScript rule plus its GPU copy, cross-referenced. The output pixel size is derived in three places: `RenderStage` (`IsoCamera.pixel_metres(size, h, 1.0)`), `golden.gd` (`SIZE_M / HEIGHT`) and `stability_check` (`1/px_per_m`). They are equal today. |
| Footprints `<png>.segments.json`, `[ax,ay,bx,by,half_px]` in segment-row order | `golden.gd::_write_footprints` → `FuelFootprints.of` | `golden_fuel.footprints` (`with_suffix`) | Agrees. Order by `first[row]+k`, and the GDScript side is tested. |
| `stability.json` `{"<tier>-<px/m>": {ends×8, drawn_px}}` + `stab-<key>-<k>.png` | `stability_check.gd` (TIERS × PX_PER_M × OFFSETS) | `golden_stability.findings` (KEYS, OFFSETS) | Agrees. `test_the_stability_keys_are_what_the_scene_draws` parses the .gd. One producer: the old tool is gone. |
| Fuel fixture container v0 (`fuel_fixtures.py`) | `files/content(name)` for `fuel_ramp` and `fuel_stick` | `FuelFixture.gd` (format, version, digests); `golden_fuel.segments` (now checked) | Agrees. `stability_check.FIXTURE = "fuel_stick"` is held to nothing, but `FuelFixture.named` refuses loudly if it is missing. |
| New fixture objects: `rod_spent` (hot, ignited, state 1), `rod_gap`, `stick_cross`, `log_cross` | `fuel_fixtures.visible()` | `burnout_findings`, `dead_flame_findings`, `crossing_findings`, `object_areas` (per region), `test_the_fixtures_regions_carry_the_states_the_checks_read`; §7.1's fixture list | Region names are unique per visible object, so per-object areas aren't pooled (except `kindling_pile`, the padding, pooled as before). §7.1 names all four. The instance order "log later than stick" holds (object order). |
| Recipe palette | `recipe_palette.tres` | `RenderStage.show_fuel` → `use_palette` → `recipe_colours[16]`, slot 15 reserved | Held to `fuel_fixtures.RECIPES` by test. `PALETTE_SIZE` and `ROW_WIDTH` are held to the shader source by test. |
| Fuel goldens `goldens/<key>/<tier>/fuel.png` | recorded in the CI image (the author's claim) | `golden_findings` (`GOLDEN_SCENES = ("fire","fuel")`) | Paths agree. Their content I did not verify (§5). |

## 3. New findings

### W2-S1 SHOULD-FIX: `client/addons/engine/render/fuel_pass.gd::show_fuel` rebuilds before the per-frame check, so a refused frame can be half applied

- **Defect:** when the structure changed, `show_fuel` runs `problems()`, then `_rebuild(snap)`, and records `_structure`.
  Only after that does it run `frame_problems()` and return its refusals before uploading the segment and state
  textures. `problems()` checks the frame columns' sizes (via `_shape_problems`), but it never checks `state`'s
  values. So a frame that changes structure and carries `state = 2` gets:
  - new instances, a new instance texture and a new `segment_object_tex`;
  - the **previous** frame's segment and state textures;
  - and a refusal anyway.
- **Contradicts:** the method's own docstring ("a refused frame draws nothing new, and the last good one stays"),
  §3.2 ("A refused frame draws nothing new") and CLAUDE.md ("never ... a half-applied change").
- **Verified:** a probe test on the scratch copy: draw the fixture, change rod 0's radius, set `state[0] = 2`, call
  `show_fuel`. It returned `["object row 0 has state 2; only 0 and 1 are defined"]` with `rebuilds = 2`.
- **Failure scenario:** step 7's decoder delivers an insertion frame (new objects, so more segment rows) whose `state`
  byte is corrupt.
  - The new instances' `first` rows point past the old, shorter segment textures. `texelFetch` out of range is
    undefined in GLES 3, so the new objects draw with garbage or zero state.
  - `_structure` now equals the new structure, so the next good frame skips `problems()` and only uploads textures.
    The bad state is visible for at least one frame.
  - `test_a_refused_frame_draws_nothing_new` misses this: its second case changes a frame column's size, which
    `problems()` already catches.
- **Fix (unverified):** run `snap.frame_problems()` before the structural branch (or have `problems()` include it), and
  add the probe as a test that asserts `rebuilds` and `instance_count` are unchanged.

### W2-N1 NIT: `docs/design/client_objects.md` §4.1, the colour bullet, contradicts §3.2 and the code

- **What §4.1 says:** "An unknown recipe or kind is reported and drawn magenta."
- **What §3.2 and the code do:** both refuse "an unknown kind, recipe or region" (`_vocabulary_problems`,
  `_object_problems`), so such a frame draws nothing new. Magenta is only for a recipe welcome names that has no
  palette colour, or one past slot 14 (`use_palette`).
- **History:** the line predates the branch. The fold rewrote this section's magenta contract and left it.
- **Failure scenario:** step 7's implementer follows §4.1 and draws an unknown kind instead of refusing it.

### W2-N2 NIT: `docs/design/client_objects.md` §7.2's heading says `scripts/golden_measures.py`

The fuel rows (Burning, Char, Burn-through, Flame shape, Burnout, Crossing, per-object Tier agreement, Stick stability)
live in `scripts/golden_fuel.py` and `scripts/golden_stability.py`, which B7 cites correctly. A reader looking for the
burnout check in `golden_measures.py` finds nothing.

### W2-N3 NIT: `client/addons/engine/render/fuel_snapshot.gd::kind_name` has no caller on the shipped path

- **The claim:** its docstring calls it "the one rule the checks and the drawing both use, so they can't disagree".
- **What the tree does:** nothing but `test_fuel_snapshot.gd` calls it. The one rule actually used is `geometry_rows`.
- **Why it matters:** "a fix ships with a caller". A future reader may route a check through `kind_name` while the
  drawing uses `geometry_rows`, and that would recreate TB-B1's two rules.
- **Fix:** delete it, or fix the docstring.

### W2-N4 NIT: `tools/fuel_aa/frame_time.gd` is untracked, and no gate loads it

- **Why it matters:** the research record cites it as the frame-time tool to rerun. `godot_check.py` loads only
  `client/`. S4's breakage (a tool pointing at a deleted shader) was exactly this tool rotting unseen, and the same
  can happen at the next `FuelPass` signature change.
- **Fix:** commit it, and either load it in the gate's script-load step or record (as the B26 probes are) that it is
  rerun by hand at a fuel shader change.

### W2-N5 NIT: `fuel_pass.gd::_init`'s second ordering comment is stale

- **The comment** says "Rod fringes blend, so they sort with the flames in the transparent pass, by box centre".
- **What the code does:** both rod passes now blend, and ordering is by `render_priority` (0, 1, 2), as the comment
  three lines above says.
- **Fix:** drop the stale half.

### W2-N6 NIT: two loose ties

- `test_golden_fuel.py::test_the_reader_knows_the_writers_format_and_the_drawn_fixture` asserts
  `gf.FIXTURE_NAME in ff.FIXTURES`, which `"fuel_stick"` also satisfies. `== ff.NAME` states the intent.
- `golden.gd::_write_footprints` derives the output pixel as `SIZE_M / HEIGHT`, where `RenderStage` uses
  `IsoCamera.pixel_metres(size_m, size.y, 1.0)`. The values are equal today, but the footprints' floor and the
  shader's floor come from two derivations. Passing `IsoCamera.pixel_metres(...)` would make it one.

## 4. What I found sound

- **Every changed signature has every caller updated:**
  - `show_fuel`'s two-argument form (5 call sites plus the tests);
  - `use_view(View)` (`use_debug` is gone);
  - `golden_stability.findings` (`stability_findings` is gone from `golden_run`);
  - no reference remains to `fuel_rod_edge`, `stability_frames` or the old `FIXTURE` constant.
- **The rod's next-pass pair gets identical uniforms.** The flame-only uniforms (`flame_height_m`,
  `segment_object_tex`, `flame_flicker`) reach only the flame material, and the test's per-shader exclusion list
  matches what `_param_on` does.
- **Flame instance order equals segment-row order.** That is the index the flame shader uses for `ignited_tex`,
  `thickness_tex` and `segment_object_tex`.
- **The new fixture objects carry the states their checks read**, held by a test. Region names are unique, so the
  per-object agreement isn't pooled.
- **The cell OCCLUDER pass draws black**, so the fuel-ID frames' white comes only from fuel (and flames, in the
  flame mask). `mask_of` excludes the bodies' pure red.
- **The golden image's needs are still met:** `golden_fuel` imports only the stdlib, numpy and `golden_*`.

## 5. What I did not verify

- **The recorded `fuel.png` goldens against this tree.** I didn't run the golden image.
  - `fuel_snapshot.gd`'s mtime (02:54) is after the goldens' (02:52). It changes validation, not pixels, and the
    fixture still passes it in the unit run, so I expect no effect. But the author's "Linux PASS after recording" may
    predate that edit.
  - I viewed the rig golden by eye: the objects are present and the flame is visible.
- **S5's encoding question,** on either tier.
- **That render priority actually orders the rod depth pass, the rod colour pass and the flames** on Compatibility.
- **`frame_time.gd`'s numbers.** I only checked that it runs, headless.
- **The author's 16 + 5 deletion claims,** beyond the one I reran (the body test).
