# Step 8 shader: Wire integrity

Scope: `git diff 35a1702...HEAD` (c656c33, ce06d7b), plus every producer and consumer of the contracts it touches outside the hunks. I ran `.venv/bin/python -m pytest tests/test_client_fixtures.py tests/test_golden_measures.py tests/test_golden_run.py tests/test_client_project.py`: 47 passed. I did not run Godot, the golden job or prepush. Every rendered number below comes from the commit messages, not from my own measurement.

## Contract table

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| `golden_run.py` CLI (`--out`, `--godot`, `--no-xvfb`, `--timeout`) | unchanged | `ci/godot-golden/run.sh`, `golden.yml`, `test_client_project.py:233`, CLAUDE.md | Same flags. `--out` held one frame and a log before; now it holds 6 frames, `golden.log`, `cutaway.log`, `cutaway/` with 48 pairs, and `*.diff.png`. The artifact upload takes the whole directory, so it keeps all of it. CLAUDE.md still says "draws the same frame". |
| `SHOTS` / frame names | one frame → 6 `(name, fixture, tier, pass)` | `golden_findings` (`fire-<tier>.png`), `golden_measures.colour_alone_findings` (`cold-rig.png`, `fire-rig.png`, `fire-rig-{crack,glow}_mask.png`), `agreement_findings`, `test_golden_run.py` | The names agree across all three: checked by reading them. The PASS line is now "6 shots, 3 goldens, cut-away", and the test asserts it. |
| `golden.tscn` command line | `--out=<png>` → repeated `--shot=<fixture>:<tier>:<pass>:<png>` | `golden_run.draw_all` (new form); `test_godot_gate_fixtures.py:251` still passes **`--out=`** | The gate fixture still gets the headless refusal, because that check runs first. Its "no x.png" assertion is now vacuous (N1). |
| `cutaway_check.tscn` command line and `cut-<sample>-k<k>-{with,without}.png` | new | `golden_measures.cutaway_report` (`CUT_FRAME` regex, `CUTAWAY_ADVISORY` names) | Python matches whatever pairs exist. It knows neither the sample list nor the count (S3). The advisory names are a mirror of the GDScript `SAMPLES` keys that nothing checks. |
| Goldens layout `goldens/<key>/<tier>/fire.png` and `golden_compare.judge(log, png, GOLDENS, name, diff)` | `<key>/renderer/boxes.png` → `<key>/{laptop,rig,max}/fire.png`; the key is unchanged (`compat-llvmpipe-mesa25.2.8-0ubuntu0.24.04.4-llvm20.1.2-godot4.7.2`) | `golden_findings` | `judge`'s signature is unchanged. The key still comes from the golden scene's log, which is correct. The goldens were drawn under Rosetta-style emulation, and the commit says plainly that the first GitHub run is the real check. |
| Fixture container (`overdrive-client-snapshot-fixture` v0) | new: `scripts/client_fixtures.py` | `client/tests/support/snapshot_fixture.gd`, `test_client_fixtures.py` (the staleness check) | Field names, dtypes, offsets, `<u2` LE and both digests agree between writer and reader (read on both sides). The version is refused unless it is 0. |
| FIELDS.md versus `simcore/protocol/encoding.py::snapshot` and §4.1–§4.2 | doc only | step 7 | `shape` order, `cell_m`/`cell_size_m`, `glow`/`surface_glow` and missing `burning` are all named. Missing from the notes: `encoding.snapshot` has **no `region` channel**, and its `glow` is cell-mean temperature, not §4.2's envelope skin temperature (N3). |
| Grid axis order | engine `[x,y,z]` → fixture `[z,y,x]` C order (`wire_order`) | `CellSnapshot.index`, `VolumeTextures.slice` (one z-slice per Image), shader `texelFetch(ivec3(x,y,z))`, `IsoCamera.to_godot` | Consistent. `test_client_fixtures` pins cells by `[z,y,x]` and `test_cell_volume` pins the box at (12, 4.8, 4). |
| `CellSnapshot` seam (step 7 fills it) | new | `CellVolume.show_snapshot`, `Cutaway.flagged_boxes`, `RenderStage` | It carries shape, `cell_m`, 5 channels, region names and glow calibration. It does **not** carry the material vocabulary: `RenderStage` takes it from `SnapshotFixture.material_ids` (S4). |
| Shader uniforms versus `cell_volume.gd` | new | `*.gdshaderinc` | Every name agrees by grep, along with types and sizes: `cells` ivec3/Vector3i, `palette[16]`/`PALETTE_SIZE` 16, `cut_ids[8]`/`MAX_CUT` 8, and int, float and sampler3D types throughout. Nothing would catch a name drifting, and several defaults equal the fixture's values (S2). |
| Material ids | `data/materials/core.yaml` (0–5) → fixture `materials` → `MaterialPalette.by_id` | shader `palette[clamp(material,0,15)]` | Ids 0–5 agree with core.yaml, and `palette.tres` names all five solids. An id ≥ 16 is silently dropped by `use_palette` and drawn as id 15 (S5). |
| Region names and ids | `tile_and_client.md` §1.1 (hand-copied into `PRIMITIVES`) → ids 1..6 in authoring order | `cutaway.tres` (`wall_south`, `wall_north`, `wall_end`), `golden.gd` (`crate`), `test_cutaway.gd` constants 2..5 | Geometry matches §1.1 box for box. No shipped scene file exists yet (`data/world/` holds only `actions.yaml`), so nothing ties `PRIMITIVES` to §1.1 (N4). |
| §2 cut rule (edited) | doc: box centre → nearest point | `cutaway.gd`, `test_cutaway.gd`, `cutaway_check.gd`, T1/T11 | The code matches the new text. The new "No pops: a side wall's face is never crossed" is false at the alley mouth (S1). |
| B7 row (edited) | standards_backlog | CLAUDE.md Guard lists, §6 | Mostly accurate. It does not repeat §6.5's claim that prepush runs the measured checks, which is false (S6). |
| Godot gate | `godot_check.py` unchanged | new `.gd` files are loaded by `load_all.gd`; `.uid` files are committed (`.gdshaderinc` included, though `test_client_project` only globs `.gd`/`.gdshader`) | No shader is compiled by the gate: the dummy renderer under `--headless` compiles nothing, so a shader error surfaces only in the golden job (S7). |

## Findings

### SHOULD-FIX

**S1. `docs/design/client_rendering.md` §2 "No pops" / `client/addons/engine/render/cutaway.gd::cut_regions`: the nearest-point rule still cuts the wrong wall and pops at the alley mouth.** The side walls start at x = 1.2 m and the floor starts at x = 0, so the player can stand at x < 1.2 (the spawn is (0.6, 2.0)). There the nearest point of `wall_north` is its corner (1.2, 3.6). At yaw 45, f = (−0.707, 0.707), and for a player at (0.6, 3.35) the test gives dot(q − p, f) = 0.707·(−0.6 + 0.25) < 0. So `wall_north` is cut, even though it is behind the player: the same failure the commit says it fixed. Walking east past x ≈ 0.95 flips the cut back without any rotation, which §2 forbids ("the flag flips only at tween start"). The same thing happens to `wall_south` at yaw 135. `test_a_side_walls_cut_never_depends_on_where_along_it_the_player_stands` samples x ≥ 1.5 only, and `cutaway_check.gd::SAMPLES` has no point at the mouth. So both the amended doc sentence and the commit's "never pops for a side wall" overclaim. Fix: take only the across-wall component for a side wall, or clamp only along the wall's long axis. Then add mouth samples (x = 0.3, 0.9 at y = 0.65 and 3.35) to both tests.

**S2. `client/tests/unit/render/test_cell_volume.gd::test_a_snapshot_sizes_the_box_and_sets_the_uniforms`: it cannot detect a uniform-name mismatch.** `ShaderMaterial.set_shader_parameter` caches any name, so `uniform(&"cells")` returns whatever was set whether or not the shader declares it. That makes the test a round trip through a dictionary. Worse, the shader defaults equal the fixture's values: `cell_m = 0.1`, `glow_offset_c = 525.0`, `glow_scale_c = 3.8235294` (= 975/255). Rename `glow_scale_c` or `cell_m` on either side and every unit test, every golden and every measured check still passes. The breakage would show only on a fixture or server with another spacing or calibration. Fix: assert that the names `cell_volume.gd` sets are the names the shader source declares. A Python text scan of the `.gdshaderinc` files is enough if `Shader.get_shader_uniform_list()` is empty under the dummy renderer. Also set the shader defaults to sentinels (say `cell_m = 0.0`) so a missed wire draws nothing.

**S3. `scripts/golden_measures.py::cutaway_report` and `CUTAWAY_ADVISORY`: the gate's coverage and its exemption live on two sides that nothing ties together.**
- (a) Python accepts any number of pairs ≥ 1. If `cutaway_check.gd::SAMPLES` is cut to one easy sample, the job stays green while §2's "along both walls … at all four yaws" quietly stops being tested.
- (b) The exemption is per sample at **all four yaws**. Both the commit and the docstring say the crate hides the body "at two yaws". So a real regression at the other two yaws of `crate-south` or `crate-east`, such as a cut that stops cutting `wall_south`, prints only an advisory line.
- (c) Renaming any sample to `crate-south` exempts it silently.

Fix: make the Python side hold the expected `(sample, k)` set (48 pairs) and refuse missing or extra pairs. Exempt only the two measured `(sample, k)` pairs.

**S4. `client/addons/engine/render/cell_snapshot.gd`: the seam lacks the material vocabulary.** The docstring says it carries "the vocabularies that name their values", and FIELDS.md says step 7's decoder fills this object. The palette lookup, though, needs name → id, and `RenderStage.show_fixture` takes that from `SnapshotFixture.material_ids`, a test-only class under `tests/support/`. Step 7's decoder, filling `CellSnapshot` exactly as specified, leaves the game with no way to colour cells unless it rebuilds this side channel. Fix: move `material_ids` onto `CellSnapshot` (FIELDS.md already lists it under `welcome`), and have `problems()` refuse a snapshot without it.

**S5. `client/addons/engine/render/cell_volume.gd::use_palette` / `lighting.gdshaderinc` (`palette[clamp(material,0,15)]`): material ids are u8 (§4.2), but the palette holds 16 entries.** When `data/materials/` grows past id 15, `by_id` returns the colour, `use_palette` drops it without a word, and the shader draws that material in id 15's colour (black today). Nothing refuses it. Fix: refuse, or `push_error`, on any vocabulary id ≥ `PALETTE_SIZE` in `use_palette`, and test it. Or size the palette from the vocabulary as a 1-D texture.

**S6. Claims about the Mac and about prepush.** `client_rendering.md` §6.5 says "`prepush` runs the B6 gate, plus the tier-agreement and greyscale checks when a GPU context exists". `scripts/prepush.sh` has no reference to `golden_run` or `golden_measures`. That sentence predates the diff, but this diff is the one that made those checks real, so it now promises a gate that doesn't exist. Separately, `golden_run.py --no-xvfb` on a Mac always exits 1, because `judge` refuses non-llvmpipe three times. The "advisory, measured checks run" path therefore can't be read from its exit status. A measured-check failure and the expected refusal look the same unless someone reads stderr. Fix: correct §6.5 (an in-place edit, no growth) and the B7 row. Have `--no-xvfb` skip `golden_findings` with one printed line, so its exit code reflects the measured checks.

**S7. The gate and the shader (`scripts/godot_check.py`; the B6 row).** No step of `prepush` compiles a `.gdshader` or `.gdshaderinc`: `load_all.gd` loads `.gd` only, and the headless dummy renderer compiles no shaders. A shader syntax error, or a uniform type that mismatches the GDScript, passes prepush and fails only `golden.yml`. B7 records that `golden.yml` is not yet a required check. So a broken shader can reach `main` with `prepush: PASS`. Fix: name this in B6's "Still open" with its trigger (the golden job becoming required). Or add a windowed shader-compile probe to the golden job's import step.

**S8. The deletion-proof claim: c656c33 promises "the depth swap needs the goldens: next commit".** ce06d7b records the goldens but reports no depth-swap deletion proof. §6.2 requires one ("swapping the depth formula fails the capsule golden"). The capsule (actor 2 at `wall_north`'s face) is judged only by `golden_compare` on llvmpipe, which can't run on the Mac. So nobody has shown that the depth line is guarded, and CLAUDE.md calls a test that cannot fail a BLOCKER. Fix: run the proof in the golden image and record it, or state in the hand-off that it is open.

### NIT

**N1.** `tests/test_godot_gate_fixtures.py::test_the_golden_scene_refuses_a_headless_run_instead_of_hanging` still passes the retired `--out=` flag. Its "no x.png" assertion can no longer fail for the right reason. Pass a `--shot=…:<tmp>/x.png` instead.

**N2.** `test_client_project.py::test_every_script_and_shader_is_committed_with_its_uid` globs `*.gd` and `*.gdshader` but not `*.gdshaderinc`. Today they are covered only indirectly, by the import's "creates nothing" check. Add the glob.

**N3.** FIELDS.md should also note that `encoding.snapshot` sends no `region` channel at all. It should also say that its `glow` scaling matches §4.2 but its quantity doesn't: it is cell-mean temperature × solid, while §4.2's `surface_glow` is the envelope skin temperature. As written, "which matches 975/255" invites step 7 to rename the key and stop there.

**N4.** `scripts/client_fixtures.py::PRIMITIVES` is a hand copy of tile §1.1, and `ALLEY` uses `SCENE_VERSION` where §1.1's YAML says `version: 1`. When the alley scene file lands in `data/world/`, build the fixtures from it, so one source of geometry feeds both server and client.

**N5.** `client_rendering.md` §5.5 still says max uses "6-tap" AO, while `max.tres` has `ao_taps = 8` and `RenderTier.problems()` refuses 6. The commit raises this for the owner, but the design document and the tier data disagree on a value the tier test pins. Edit the cell once the owner decides.

**N6.** CLAUDE.md's Layout omits `scripts/golden_measures.py`, `scripts/client_fixtures.py`, `client/tests/support/`, `client/tests/fixtures/` and `cutaway_check.tscn`. Its Commands line still says `golden_run.py … draws the same frame`.

**N7.** Shipped-path note: nothing in `client/game/` instantiates `CellVolume`, since `main.tscn` is an empty `Node3D`. Every rendered check measures `tests/support/render_stage.gd`'s wiring: tier → viewport scale, bloom toggling per pass, `pixel_m` from the render scale, cut from feet. The game will have to rebuild that wiring. The commit's claims are true of the test stage, so the hand-off should say "measured on RenderStage", not "the client".

## Checked and found consistent

- `SHOTS` names against `golden_measures` and `golden_findings`.
- The `judge` signature, and the golden key read from the golden scene's log.
- The `run.sh` and `golden.yml` invocation and artifact path.
- Fixture writer against reader: fields, dtypes, LE u16, digests, the 4 MiB cap.
- RG8 byte order: writer, `region_cell_bounds`, shader r + 256·g, and the probe in `godot_probes.md`.
- `[z,y,x]` order and the to-Godot rotation.
- Uniform names, types and sizes (by grep).
- Region ids 2–5 in `test_cutaway.gd` against the fixture's map.
- Material ids against `core.yaml`, and the palette covering every solid.
- §1.1 geometry against `PRIMITIVES`.
- `glow_emission(0) = 0`, as FIELDS.md claims.
- The 86.7% (docstring) and 13.3% (commit) cut-away figures agree.
- The B7 row's 128 versus 256 bit statement is worded honestly.
