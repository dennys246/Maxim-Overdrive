# Step 8 shader, delta 1: Executor and Wire integrity

Scope: `git diff --cached ce06d7b` plus the three unstaged goldens, in `.worktrees/client-shader`.

**What I ran (read-only):**
- `pytest` on test_golden_measures, test_golden_run, test_client_project, test_client_fixtures, test_golden_compare, test_determinism and test_isolation: 233 passed.
- `test_godot_gate_fixtures.py -k golden_scene` under `MAXIM_OVERDRIVE_GODOT=1`: passed.
- The headless client runner on a mktemp copy: `client-tests: PASS 32 tests`.
- Mutations on that copy, each followed by a rerun of the runner (results below).
- Pixel analysis of the new goldens against ce06d7b's.

**What I could not run:** golden_run, cutaway_check or Docker. So the fold's rendered claims are the author's numbers, not mine: per-tier colour-alone passing at laptop and max, the four advisory pairs, 50.7/64.7 s, and the depth proof.

## Fold status (set from the tree)

| Finding | Status | Evidence from the tree |
|---|---|---|
| E S1 (`groove_t0` never reset) | fixed | `find_hit` resets it on an empty brick and on an undrawn cell. No targeted test was added (the one-cracked-cell-over-floor fixture was not built). Only the llvmpipe goldens guard it. |
| E S2 / W S3 / A1 (advisory too wide; pair set unchecked) | fixed | `CUTAWAY_ADVISORY` is 4 (sample, k) pairs. `cutaway_report` refuses missing, extra and half pairs. Tests cover each case, including crate-east k0 being gated. `test_the_sample_list_is_the_scenes` ties the list to the GDScript. I could not check which yaws are the real advisory ones. A wrong pick fails loudly in CI rather than hiding anything. |
| E S3 / W S8 / A5 / C (depth deletion proof) | **open** | The only record is fold.md's sentence that it is "recorded in the fold commit", and no fold commit exists yet. Nothing in the tree shows the run. It becomes fixed when the commit message carries the numbers. |
| E S4 (scene refusal paths untested) | partly fixed; rest deferred to B7 | Shot parsing and `usable` moved to `GoldenShot`, and each refusal is tested headless. Deleting the crate check turns the test red (verified). Still untested: golden.gd's no-shots, wrong frame size and `save_png` failure, and every refusal in cutaway_check.gd. fold.md says so, and B7's existing row names the gap. |
| E N1 | fixed | The header now cites `cutaway_report`. |
| E N2 | fixed | The 60-pair expectation is enforced, and `out/cutaway` is cleared with rmtree. The stale-frame test fails if the clearing is removed. |
| E N3 | fixed | `_pair_finding` reports a missing `-without.png` as a finding, and a test covers it. |
| E N4 | fixed | `GoldenShot.usable` refuses a fixture with no crate. Tested; the mutation turns it red. |
| E N5 | fixed | Duplicate actor ids are refused. Removing the check turns `test_every_malformed_header_is_refused` red (verified). |
| E N6 | fixed (GDScript) | `BRICK_SHIFT` is now the one constant. The shader's own `const int BRICK = 4` is still tied to nothing (new NIT N3). |
| E N7 / W S1 / A4 (pops on the pavement) | fixed | The short-side rule is in place. Restoring the nearest-point rule turns the sweep red at (0.3–0.95, 3.35) step 0 and (0.3–0.95, 0.65) step 1 (verified). Three pavement samples were added to the rendered check. |
| W S2 / C (uniform names; defaults equal the fixture's) | fixed | The test holds `uniform_names()` to `get_shader_uniform_list()` for both variants. Renaming `cell_m` in cell_volume.gd turns it red for both (verified). `cells`, `cell_m`, `glow_offset_c` and `glow_scale_c` now default to sentinels. |
| W S4 / A NIT 8 (vocabulary off the seam) | fixed | `CellSnapshot.material_ids` exists, `problems()` refuses it empty, and both are tested. No caller is left on `SnapshotFixture.material_ids` (grep). |
| W S5 / A7 / C (unknown material draws black) | fixed, with a gap | Magenta is pre-filled, and a test checks it (it goes red when the default goes back to black). The two `push_error` paths (an id of 16 or more; a solid material with no colour) run under no test. An id of 16 or more draws `palette[15]`, which is magenta only while id 15 is unused (new NIT N2). |
| W S6 (Mac exit status; §6.5's prepush claim) | fixed | `goldens=not args.no_xvfb`, with a test that a white frame passes under `--no-xvfb`. Removing the skip turns it red. §6.5 line 268 no longer claims that prepush runs the checks. |
| W S7 (no prepush step compiles a shader) | rejected (author's call, confirmed) | A garbage line appended to `lighting.gdshaderinc` makes the headless runner print `SHADER ERROR … Shader compilation failed`, which `godot_check`'s error scan fails on. The rejection holds for syntax errors only. A GDScript/uniform *type* mismatch is not a compile error and stays golden-job-only. |
| W N1 | fixed | The test passes a `--shot` and still passes. Its "no x.png" assertion is still vacuous, because under `--headless` the capture hangs before writing anything. |
| W N2 | fixed | The uid glob now includes `.gdshaderinc`. |
| W N3 / A NIT 9 | fixed | FIELDS.md adds the grid origin, the missing `region` channel and `glow`'s different quantity (read). |
| W N4 / A NIT 12 (third copy of the alley) | open (NIT) | fold.md doesn't address it. |
| W N5 | fixed | §5.5 now says `8-tap` (line 200). |
| W N6 / A NIT 13 | fixed | CLAUDE.md's Layout and Commands are updated. |
| W N7 / A3 (composition in test support) | deferred | B30 names it. Its trigger is "step 8, with `main.tscn`'s scene tree". |
| **C S1 (black pixel at 543,224)** | **open: the fold made this class worse** | That one pixel is now wall-coloured, but the re-recorded goldens add new holes on an uncracked face (new finding B1). |
| C slant floor; groove depth; `MAX_STEPS`; entry axis from the face normal; `textureLod` | fixed in code | Checked by reading. None can be tested headless. |
| C laptop speckle | fixed in code; claims unverified | `crack_spacing_m` changes the spacing in octaves, and colour-alone is now gated per tier. Whether laptop and max pass is the author's measurement only. |
| C hatching | deferred | The period floor is in code, and B30 records that no check measures hatching. |
| P textures recreated every snapshot | fixed in code, **untested** | Replacing `reuse.update(images)` with `pass` leaves all 32 client tests green (verified). New finding S1. |
| P bricks / region bounds cost | deferred | B5 carries the numbers and the trigger (before step 7 wires `show_snapshot`). |
| P AO NIT | fixed | The new near-side taps compute the same weights as the old `near` vector (checked algebraically). |
| P `MAX_STEPS` NIT | fixed | `max_steps()` is `nx+ny+nz+4`. |
| A NIT 10 (shader constants written twice) | partly fixed | The `palette[16]` and `cut_ids[8]` declarations are held by the test. The loop bound `i < 8` in `cutaway.gdshaderinc` and `clamp(material, 0, 15)` in `lighting.gdshaderinc` are not (N3). |

## New findings

### BLOCKER

**B1. `client/addons/engine/render/traversal.gdshaderinc::skip_brick` / `::walk_at`, and the three re-recorded goldens: the walk fix removed one hole and added about ten, and the new goldens lock them in.**
- **Evidence:** I compared each golden against ce06d7b's. I counted pure (0,0,0) pixels whose 8 neighbours are all bright. Rig went from 4 to 10, max from 2 to 11; small black blobs went from 8 to 15 in max.
- **Where:** the new holes sit at the same coordinates in rig and max: (880,243), (528,271), (232,278), (218,287), (513,333), (485,351), (470,413), (751,468), (737,477) and (694,557). At every one of them the old golden was a flat (93,90,80) face; I viewed 4 crops at 8× and each is a uniform face with one black pixel.
- **Why it is the walk:** the shader writes exactly 0 only when it discards (C S1's own analysis), so these rays now miss. The colour, and their spread over the frame, point to the floor's top face. That face sits at z = 4 cells, a brick boundary, which is exactly the double-boundary landing the fold changed (`walk_at`'s `floor(p + r.d*1e-3)`, and `skip_brick`'s same-brick and no-progress fallbacks).
- **Why the fold's proof missed it:** "0 exhausted rays" counts step exhaustion only. A ray that steps out through `!inside(w.cell)` is not counted, and it discards just the same.
- **Failure scenario:** every frame of the floor sparkles with see-through pixels. On another GPU the leaks move, and the goldens now certify the leak pattern as correct.
- **Fix:** the debug miss pass C S1 asked for (write 1 where `find_hit` returns false inside the box), asserted empty over solid-backed pixels in the golden job. Find the leak, then re-record.
- **Severity:** BLOCKER, because it is wrong on the shipped shader path and the fold re-records goldens that hide it.

### SHOULD-FIX

**S1. `client/addons/engine/render/volume_textures.gd::_texture_of` (the reuse branch) and `cell_volume.gd::_texture`: the in-place update runs under no gate test.**
- **Evidence:** deleting `reuse.update(images)`, so the old contents stay on screen, passes all 32 client tests.
- **Failure scenario:** step 7 streams snapshot 2. The update path is broken, so the screen keeps showing snapshot 1 (fire never spreads), and nothing in prepush notices.
- **Partial cover:** golden.gd alternates fire and cold through one `CellVolume`, so the golden job would probably catch it, via cold frames equal to fire frames failing colour-alone. That job is CI-only and not required (B7).
- **Fix, headless:** call `show_snapshot` twice with same-shaped snapshots and assert the texture object is reused; with a different shape, assert a new one. Assert the content too, if `ImageTexture3D.get_data()` reads back under the dummy renderer.

**S2. The three re-recorded goldens are unstaged while all the code is staged.**
- **Failure scenario:** a fold commit made from the index ships the new shader with ce06d7b's goldens. CI's golden job then compares new frames with old goldens: different crack spacing, groove depth and AO. All three tiers fail, or worse, someone re-records from that failure without looking.
- **Fix:** stage them with the fold, or (given B1) re-record after the leak fix and stage then.

### NIT

**N1. `scripts/golden_run.py::main` PASS line, and `tests/test_golden_run.py::test_matching_frames_pass_every_shot_is_drawn_and_the_logs_are_kept`.**
- Under `--no-xvfb` the line still says "3 goldens", although none were judged.
- `_main` always passes `--no-xvfb`, so the test named "matching frames pass" never judges a golden any more. Its per-tier golden setup is now dead weight.
- The judged-and-passing path through `golden_job` is untested end to end; `judge` itself is covered in test_golden_compare.
- Fix: print "goldens not judged" in the summary, and run that test with `XVFB=()` as the differing-frame test does.

**N2. `cell_volume.gd::use_palette`, FIELDS.md:**
- "an id over 15 … drawn magenta" holds only while id 15 has no material. The shader clamps an out-of-range id to `palette[15]`.
- Neither `push_error` path (an id of 16 or more; a solid material without a colour) has a test.

**N3. Shader constants still untied:**
- `traversal.gdshaderinc` `const int BRICK = 4` against `VolumeTextures.BRICK`.
- `cutaway.gdshaderinc` loop bound `i < 8` against `MAX_CUT`.
- `lighting.gdshaderinc` `clamp(material, 0, 15)` against `PALETTE_SIZE`.
- fold.md says "the shader's `8` and `16` are held by the uniform test". Only the two array *declarations* are held. The loop bound, the clamp and the brick size are not.

**N4. `tests/support/render_stage.gd::show_snapshot` caches region bounds by object identity (`snap != _snapshot`).** A decoder that mutates one `CellSnapshot` in place after an `imagine` keeps stale bounds, and the cut and the camera aim at the old region. The docstring states the condition; it lives in test support for now (B30).

**N5. `scripts/golden_run.py::draw_all`:** `shutil.rmtree(cut, ignore_errors=True)` then `cut.mkdir()`. A partial delete surfaces as a `FileExistsError` traceback, not a finding. That is loud, but untidy.

**N6. Timing headroom (`golden_run.draw`):** the cut-away scene now draws 120 frames (15 samples × 4 yaws × 2), up from 96. fold.md doesn't say whether its 64.7 s of 120 s was measured before or after the pavement samples were added.

## Checked and found sound

- **`golden_run` ↔ `golden_measures` contracts:** `TIERS` comes from one source (`gm.TIERS`). The 12 `SHOTS` names match `colour_alone_findings(out, tier)`'s `cold-/fire-<tier>[-crack|glow_mask].png`. `agreement_findings` still reads `fire-<tier>.png`.
- **`run.sh` and `golden.yml`:** they pass no `--no-xvfb`, so CI still judges goldens. The CLI is unchanged.
- **`use_palette(ids, colours)`:** its only callers are `RenderStage.show_snapshot` and two unit tests. `show_fixture` has no callers left.
- **`GoldenShot`:** a missing png is refused, as is a relative one (the stand-in Godot enforces the same rule). `split(":", true, 3)` keeps colons inside the path.
- **The gate fixture's `--shot` argument:** it uses the current flag form, and the test passes against real Godot.
- **New Python tests can fail:** deleting the skip, the rmtree, the pair-set check or the per-tier prefix each breaks a named assertion (read).
- **`max_steps()`:** with the no-progress fallback, every iteration advances at least one cell, so the bound holds.
- **Sentinels:** `cells = 0` makes `inside()` false, so an unset volume discards everything.
