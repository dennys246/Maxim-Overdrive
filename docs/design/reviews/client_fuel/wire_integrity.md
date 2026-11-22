# Wire integrity review: phase1/client-fuel (step 8 fuel pass), round 1

Scope: `git diff 69483d9` plus the untracked files, read as the tree stands on 2026-11-22. I modified nothing. I ran one command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_fuel_fixtures.py tests/test_golden_run.py`, and all 52 passed. I did not run the gate, godot_check or Godot.

## Contract table

| Contract (owner) | Producers before → after | Consumers before → after | What each consumer gets |
|---|---|---|---|
| Shot grammar `<fixture>[+<fuel>]:<tier>:<pass>:<png>`, passes `shaded, crack_mask, glow_mask` → plus `shaded_noflame, fuel_mask, flame_mask` (owner: `golden_shot.gd` header) | `golden_run.draw_all` builds it from `SHOTS` | `GoldenShot.parse` → `golden.gd::_draw`; `test_golden_shot.gd` | Matches. `fuel_mask` and `flame_mask` map to `CellVolume.Pass.OCCLUDER` and a fuel view of 1 or 2; `fuel_mask` and `shaded_noflame` turn flames off. Stale grammar copies remain in `golden.gd` (header line 3 and the `_fail` text, line 32) and in `golden_shot.gd:35`'s message (N1). |
| `SHOTS`: 6 per tier → 8 per tier, `fuel-<tier>{,-noflame,-fuel_mask,-flame_mask}.png` | `golden_run.SHOTS` | `draw_all` (missing-frame check), `golden_fuel.FuelFrame.load`, `burn_through_findings`, `flame_findings`, `object_areas`, `test_golden_run.py` | The names agree, read in all four places. The summary line says "24 shots, 6 goldens, cut-away", and `test_golden_run.py:126` asserts it. |
| `GOLDEN_SCENES = ("fire","fuel")`; goldens at `goldens/<key>/<tier>/{fire,fuel}.png` | the untracked `fuel.png` × 3 under the existing key | `golden_findings` → `golden_compare.judge` (signature unchanged) | Correct. `client_rendering.md` §6.5 states the layout only down to `<tier>/`, so it is not stale. |
| `<png>.segments.json` footprints, `[[ax,ay,bx,by,half_px],…]` in segment-row order (new; owner: the `fuel_footprints.gd` docstring) | `FuelFootprints.of`, written by `golden.gd::_write_footprints` beside every fuel shot | `golden_fuel.footprints` (`with_suffix`, which agrees with GDScript's `get_basename()+…`) | The row order holds only if the segments are grouped by object in object-row order. Both sides assume that and neither checks it (S3). No GDScript test exercises `FuelFootprints`; only `golden.gd` calls it, and the Python side is tested on synthetic JSON (S3). |
| `stability/stability.json` `{"<tier>-<px/m>": {ends:[[ax,ay,bx,by]×8], drawn_px}}` plus `stab-<key>-<k>.png` (new) | `stability_check.gd` | `golden_run.stability_findings` → `golden_stability.stability` | Keys and file names agree. A second producer and consumer of the same measure use another format: `tools/fuel_aa/stability_frames.gd` writes `meta.json` and `<key>_<k>.png`, and `measure.py` reads luminance where the gate reads red (S4). |
| Fuel fixture container (`fuel_fixtures.py` FORMAT/VERSION 0) → now two fixtures, `fuel_ramp` and `fuel_stick`; `stale()` returns a list | `fuel_fixtures.files/content(name)` | `FuelFixture.gd` (format, version and digests checked); `golden_fuel.segments` (new reader); `test_fuel_fixtures.py` | `golden_fuel.segments` checks no format, version, size or digest (S1). |
| FuelSnapshot columns vs `client_objects.md` §3.2/§3.3 and the `contracts.md` rows `fuel.objects.columns` and `fuel.segments.columns` | `fuel_snapshot.gd` OBJECTS/RODS/SLABS/SEGMENTS (unchanged since part 1b) | FuelPass, FuelGeometry, FuelFootprints, stability_check, golden_fuel | Column names and dtypes match §3. |
| Per-instance texture layout (owner: `client_objects.md` §4.1) | `FuelPass._write_instance` | `fuel_object.gdshaderinc::instance_at` | Code and shader agree. The design document does not (S2). |
| FuelPass uniforms (`instance_tex`, the 4 segment textures, `state_tex`, `recipe_colours[16]`, `floor_half_m`, `fuel_debug`, `render_pixel_m` (rod only), `flame_flicker` (flame only)) | `FuelPass._param` / `_param_on` | `fuel_object.gdshaderinc`, `fuel_rod`, `fuel_slab`, `fuel_flame` | Every name is declared where it is set (read by hand). `test_fuel_pass.gd` holds them via `uniform_names()`. |
| `FuelPass.use_pixel_metres(output_pixel_m, render_scale)` (new) | — | `RenderStage._update_pixel_metres`; `test_fuel_pass.gd:88,128-129` | Every caller found by grep uses the two-argument form. `CellVolume.use_pixel_metres` keeps one argument (rendered pixel); the asymmetry is intended and documented. |
| Moved shader functions: `godot_to_world`/`world_to_godot` → `axes.gdshaderinc`; `face_lit` + KEY_* → `key_light.gdshaderinc`; `glow_curve` + GLOW_* → `glow_curve.gdshaderinc` | — | `cell_volume.gdshaderinc` (includes all three, before `traversal`/`lighting`/`emission`); `fuel_object.gdshaderinc` | No definition is left behind: `traversal` and `lighting` lost theirs, and `emission` now calls `glow_curve`. Include order is correct. The comment left at `traversal.gdshaderinc:36-37` now sits over nothing (N2). |
| RenderStage API: `fuel` member, `show_fuel(snap, recipes)`, `use_fuel_view(view, flames)` | — | `golden.gd`, `stability_check.gd` | Correct. `use_fuel_view`'s int (0/1/2) is a magic vocabulary stated in three places: `FuelPass.use_debug`, `GoldenShot.FUEL_VIEWS` and the shader comment (N3). |
| Recipe palette `res://game/recipe_palette.tres` (`pine_rod`, `pine_slab`) (new) | the hand-written .tres | `golden.gd`, `stability_check.gd` → `MaterialPalette.by_id` | It matches `fuel_fixtures.RECIPES`, but by hand: no test ties the two (N4). |
| Fuel glow start/span: 525 / 975 °C | `fuel_object.gdshaderinc` constants | `fuel_colour` | Cells get theirs from the wire (`encoding.GLOW_START_C` / `GLOW_FULL_C`); fuel gets them from constants. The values are equal today and nothing holds them together (N5). |
| CI golden image | Dockerfile installs numpy, scipy, pillow | `golden_run` now imports `golden_fuel`, `golden_stability`, `numpy`, `json`, `gzip` | All of these are present. `golden_fuel` deliberately avoids importing `fuel_fixtures`, which imports `simcore`. The fixture is read from the read-only `/repo` mount, which works. `run.sh` and `golden.yml` are unchanged and still correct. |

## Findings

### S1 SHOULD-FIX: `scripts/golden_fuel.py::segments` is a third reader of the fuel fixture container and refuses nothing
- **Defect:** it reads `tables[...]["columns"][name]` offsets straight into `np.frombuffer`. It never checks `format`, `version`, `data_size`, `data_sha256` or the row counts. CLAUDE.md requires that "Readers refuse versions they don't know, loudly." `FuelFixture.gd` does refuse; this reader doesn't.
- **Failure scenario:** a fixture regenerated at version 1 (say a reordered column, or `segment_count` widened to u32) is refused by Godot. If it is only reshaped, though, and the header still parses, `segments()` silently decodes wrong bytes. The checks then measure the wrong segments: "burning" compares arbitrary pixels, and a pass means nothing.
- It also keys the fixture by a hard-coded `FIXTURE = …/fuel_ramp.json`, a second copy of the name `SHOTS` carries in `"alley_cold+fuel_ramp"`. Renaming one leaves the checks reading a different fixture from the one drawn.
- **Fix:** check format, version and `data_sha256`, raising on a mismatch. Derive the fuel fixture name from `SHOTS` (or from one constant both use). Unverified.

### S2 SHOULD-FIX: `docs/design/client_objects.md` §4.1 states the per-instance texture layout, and the code does something else
- **The doc says:** texel 0 = "the row's three bytes and `state`"; texel 1 = `segment_count`; and "`state` updates the RGBA8 texture's fourth byte and never triggers a rebuild."
- **The code does** (`FuelPass._write_instance`, `fuel_object.gdshaderinc::instance_at`):
  - texel 0's fourth byte is the recipe's palette slot;
  - texel 1 carries `segment_count` plus the object's row;
  - `state` travels in a separate `state_tex` (one texel per object row), re-uploaded on every `show_fuel`.
- The design is this layout's one owner (B36), and its copy is now stale. The shader's comment, which is accurate, is a second statement of the contract.
- **Failure scenario:** a later step implements the play client's `state` update from §4.1. It writes byte 3 of texel 0, which overwrites the recipe slot and recolours the object, and burnt-out never shows.
- **Fix:** rewrite §4.1's bullet to the shipped layout and have the shader comment link to it. Unverified.

### S3 SHOULD-FIX: the footprint mirror (`client/tests/support/fuel_footprints.gd::of` ↔ `golden_fuel`, and the shaders) is untested on the GDScript side and re-derives three rules a third time
- **Re-derived rules:**
  1. The kind walk (`kind == rod` else slab, with `rod_row`/`slab_row` counters) now exists in `FuelPass._rebuild`, `FuelGeometry.segment_tops` and `FuelFootprints.of`.
  2. The segment span `[kℓ, min((k+1)ℓ, L))`.
  3. The 2 px floor `max(radius, output_pixel_m)`. That one is a fourth copy: `fuel_rod.gdshader` (`floor_half_m`), `fuel_footprints.gd::_rod` and `stability_check.gd::_frames` (`drawn_px`).
- **No unit test:** no unit test calls `FuelFootprints.of`, and `golden.gd` is its only caller. `test_golden_fuel.py` writes synthetic `segments.json`, so a GDScript-side change (row order, the floor, the slab centre line) is caught only by the CI golden job, and there only as a measurement failure, not as a mismatched contract.
- **Failure scenario:** someone changes the floor to 2 rendered px (the "floor in rendered pixels" deletion that §7.2 names) in the shader alone. `stability_check`'s `drawn_px` and the footprints keep the old width. The ideal line in `golden_stability` is then drawn at the wrong width, and the stability ratio is judged against the wrong reference.
- **Fix:** give the floor one owner, a FuelPass or FuelGeometry static (`drawn_half_m(radius, pixel_m)`) that the footprints and `stability_check` call, and add a unit test of `FuelFootprints.of` against `FuelGeometry` on the committed fixture (row count = segments rows; rod ends match the instance transform's axis). Unverified.

### S4 SHOULD-FIX: `tools/fuel_aa/` (untracked) is a broken second producer of the stability measure, and the research record cites it
- **Broken tool:** `tools/fuel_aa/stability_frames.gd:105` and `frame_time.gd:97` load `res://addons/engine/render/fuel_rod_edge.gdshader`, which does not exist in the tree. The header admits "the 'edge' mode loaded the candidate shader, which is now fuel_rod.gdshader", but the code was not changed.
- **Duplicated measure:** the tool builds its own stick, with `STICK_CENTRE (5.0, 2.0, 0.41)`, by poking `FuelSnapshot.columns`; the committed fixture's stick is at (4.5, 2.0). It also writes its own format (`meta.json`, `<key>_<k>.png`), which `measure.py` reads as luminance.
- **Claims:** `docs/design/research/fuel_antialiasing.md:16-17` cites this tool as where the stability frames come from. The line "The production rod shader … measured the same four values" names no tool. If `stability_check.tscn` produced them, the record should say so.
- **Failure scenario:** the record's own open question 1 asks for a rerun. The rerun fails to load a shader, or measures a different stick from the gate's.
- **Fix:** either commit the tool pointed at `fuel_rod.gdshader` and the fixture (or drive it through `stability_check.tscn`), or drop it and cite the gate's scene. Unverified.

### S5 SHOULD-FIX (unverified risk): what the fuel-ID mask's red channel means is assumed, never stated, and the two consumers that read it may disagree with each other
- **The assumption:** `golden_fuel.object_areas` and `golden_run.stability_findings` treat `R/255` of the fuel-ID mask as linear coverage. The rod writes `ALBEDO = 1`, `ALPHA = coverage` with `blend_mix`.
- **Where the risk comes from:** `render_stage.gd::NIGHT`'s comment records that Compatibility maps colour differently on its direct path (rig, scale 1.0, no bloom) and its buffered path (scale 0.5). Whether the blend happens before or after the sRGB encode then differs between rig and laptop. If it differs, laptop pixels read `srgb(α)` and rig pixels read `α`: a tier-dependent fringe inflation, which `AREA_WINDOW_PX` would partly absorb.
- **Second defect:** in the golden `fuel_mask` frame, bodies draw `BODY_ID` = pure red. `object_areas` reads the red channel alone, so a body pixel inside an object's widened strip counts as full fuel coverage. `mask_of` excludes pure red, but `object_areas` doesn't use it. Body 1 is at (5.5, 2.925) and the fuel objects are at x ≤ 4.6, so I expect no overlap today; I did not measure it.
- **Fix:** state the encoding of the coverage channel in §7.2. Check it with a test: draw one half-covered pixel on each tier and read it back. In `object_areas`, use a channel bodies don't write (or drop bodies from fuel shots). Unverified.

### N1 NIT: stale copies of the shot grammar
`client/tests/golden.gd` (header line 3 and `_fail` at line 32) and `golden_shot.gd:35` still say `<fixture>:<tier>:<pass>:<png>`. One owner: make `golden.gd` link to `GoldenShot`.

### N2 NIT: `client/addons/engine/render/traversal.gdshaderinc:36-37`
The comment describing the axis map now sits over nothing. Move it to `axes.gdshaderinc` or delete it.

### N3 NIT: the fuel view integers 0/1/2 are an unnamed vocabulary
They are stated in `FuelPass.use_debug`, `GoldenShot.FUEL_VIEWS`, `RenderStage.use_fuel_view` and the shader comment; `stability_check.gd` passes a bare `1`. Make them an enum on FuelPass.

Related: a cell-mask pass with fuel (`alley_cold+fuel_ramp:rig:crack_mask`) parses and draws shaded fuel into the crack mask. `SHOTS` never produces one, but the parser should refuse it.

### N4 NIT: the recipe vocabulary is stated twice
It is in `client/game/recipe_palette.tres` and `scripts/fuel_fixtures.py::RECIPES`, and no test ties them. A missing colour shows only as a `push_error` (and magenta) at golden time.

### N5 NIT: two copies of the glow constants
`fuel_object.gdshaderinc::FUEL_GLOW_START_C`/`SPAN_C` (525/975) duplicate the server's `GLOW_START_C`/`GLOW_FULL_C`, which the cells still receive over the wire. §5.1 sanctions the client constant once step 7 deletes the encoder's. Until then, a server change would make "a hot wall and a hot stick at one temperature glow alike" (`glow_curve.gdshaderinc`) false, and no test would notice.

### N6 NIT: `scripts/golden_run.py::draw_all`
- The docstring says "Both scenes", but there are three now.
- The missing-frame check covers `SHOTS` PNGs only. A missing `segments.json`, or a `stab-*.png` absent beside a present `stability.json`, raises `FileNotFoundError` out of `measured_findings`. The run then ends in a traceback with no `golden_run: FAIL` line.
- The summary line doesn't mention the stability check.

### N7 NIT: stale checklist and backlog text
- `docs/plans/checklists.md` still lists "the Burning check run with flames off (S5)" as deferred, but `golden_fuel.state_findings` implements it on the `-noflame` frame.
- `docs/standards_backlog.md` B7 still lists "§6.3's ID-mask areas" as missing, and doesn't mention the fuel golden, the fuel checks or the stick-stability check.

## One owner per contract: summary

| Contract | Places it is stated |
|---|---|
| Instance-texture layout | 2, and they conflict (S2) |
| 2 px floor | 4 (S3) |
| Fuel fixture name | 2 (S1) |
| Shot grammar | 3 (N1) |
| Fuel views | 4 (N3) |
| Recipe names | 2 (N4) |
| Glow start | 3 (N5) |
| Stability frame format | 2 (S4) |

The stability parameters sit in the checklist (correctly, as mechanism), and the code cites them without restating them as contract.

No BLOCKER: every producer/consumer pair on the shipped golden path agrees today, by reading, and the four Python test modules pass. The SHOULD-FIXes are a design document that contradicts the code, a reader that refuses nothing, an untested mirror, and a broken tool cited as evidence.
