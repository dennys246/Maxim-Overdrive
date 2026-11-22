# Step 8 shader: Executor

Scope: `git diff 35a1702...HEAD` (c656c33, ce06d7b) in `.worktrees/client-shader`. I read every changed GDScript, shader include, script and test, and both commit messages.

What I ran (read-only):
- `.venv/bin/python -m pytest tests/test_client_fixtures.py tests/test_golden_measures.py tests/test_golden_run.py`: 29 passed.
- The headless client runner on a copy of `client/` in a mktemp directory: `client-tests: PASS 28 tests`.

What I could not run: `golden_run.py` itself, because the brief forbids windowed Godot. So I have not reproduced any rendered number in the commit (96.4%, 98.6%, |ΔL*| 4.7, 0.0 L*, ΔE 11). They are the author's measurements, not mine.

## BLOCKER

None found. Every check I looked at can fail: the measure tests feed synthetic failing frames, the fixture tests feed bad headers, the golden_run tests use a fake Godot in each failure mode, and the commit gives deletion proofs on the real shader for the crack, glow and cut.

## SHOULD-FIX

**S1. `client/addons/engine/render/cell_volume.gdshaderinc::find_hit`: `groove_t0` is never reset, so floor behind a cracked silhouette draws black.**
- `groove_t0` is set the first time a cracked cell turns out to be all groove (`!cv.solid`). It is cleared only when the function returns.
- If the ray then leaves through air and hits a solid cell farther on, `h.depth_m = (h.t - groove_t0) * cell_m` counts the whole air gap as fissure depth.
- Scenario: a ray grazes the corner of a cracked edge cell of the crate. The path through that cell is short, so with 2 to 4 substeps every sample can fall within `half_w` of a Voronoi boundary. The ray then goes on to the floor about 1 m behind.
- Result: `depth_m` is about 1.0, `fissure_shade = exp(-14) ≈ 8e-7`, so that floor pixel draws black. `on_face` is also false there, so AO and hatching are skipped.
- That gives a dark fringe along the silhouettes of cracked cells. It is deterministic, so it is baked into the three new goldens, and the crack check may be scoring it as "edges".
- Fix: reset `groove_t0` to -1 whenever the walk steps into a cell that is not drawn. Test it with a fixture of one cracked cell over a floor, judged on the floor pixels.

**S2. `scripts/golden_measures.py::CUTAWAY_ADVISORY`: the exemption is twice as wide as the conflict it covers.**
- The commit says the crate hides the body "at two yaws" at `crate-south` and `crate-east`.
- The advisory set is keyed by sample only, so all four yaws of both samples become notes: 8 frames ungated instead of 2.
- Scenario: a cut regression that leaves `wall_south` standing at yaw step 0 while the player is at `crate-south`. The pass rate drops, `golden_run` prints an advisory, and the job still passes.
- Fix: key the advisory by (sample, k) for exactly the two measured pairs. Add a test that a non-advisory yaw of `crate-south` below 95% is a finding.

**S3. The commit promises a deletion proof for the depth write; the next commit doesn't give one.**
- c656c33 says: "the depth swap needs the goldens: next commit". ce06d7b says nothing about depth.
- So `DEPTH = ndc.z * 0.5 + 0.5` in `cell_volume.gdshaderinc::fragment` has never been shown red.
- I believe the cut-away check would catch it on any renderer. Without the write, the box's front-face depth is used, every hit cell behind a body overwrites it, and the visible fraction collapses. But that is reasoning, not a run.
- Fix: run that deletion once, on the Mac or in Docker, and record it in the commit message, or correct the message.

**S4. `client/tests/golden.gd::_draw` / `_ready` and `client/tests/cutaway_check.gd::_ready` / `_pair`: no refusal path except headless runs under a test.**
- Untested in `golden.gd`: no shots, a malformed shot, an unknown pass, a bad fixture, an unknown tier, no player actor, a wrong frame size, a failed `save_png`.
- Untested in `cutaway_check.gd`: a missing `--out=`, a bad fixture, no frame, a failed `save_png`. Its headless refusal is untested too.
- The only scene test, `tests/test_godot_gate_fixtures.py::test_the_golden_scene_refuses_a_headless_run_instead_of_hanging`, still passes `--out=` to `golden.tscn`, an argument that scene no longer reads.
- The commit itself reports that a refusal message crashed its own refusal path (an Array formatted as the argument list). This class of bug only shows up when the path runs.
- B7 names the gap ("the scene's refusal paths tested"), so it is visible. But this is the step that owes it, and GDScript has no diff-cover backstop.
- Fix: a few headful runs with bad arguments under the golden job's Xvfb, or move the argument parsing into a static function the headless runner can call.

## NIT

- **N1. `client/tests/cutaway_check.gd`, header comment:** it cites `scripts/golden_measures.py::cutaway_findings`. That function doesn't exist; it is `cutaway_report`.
- **N2. `scripts/golden_measures.py::cutaway_report`: two ways the gate can be wrong without saying so.**
  - It never checks that all 12 × 4 = 48 pairs are present. If `SAMPLES` shrinks, or the scene stops early with exit 0, fewer frames are judged and nobody is told.
  - `golden_run.draw_all` reuses `out/cutaway` (`mkdir(exist_ok=True)`). Stale frames from an earlier run in the same `--out` are judged as if they were new.
- **N3. Same function, a missing `-without.png`:** `load_rgb` raises, so the job crashes with a traceback instead of reporting a finding.
- **N4. `client/tests/golden.gd::_draw` via `RenderStage.volume_bounds_m("crate")`:** when the fixture has no `crate` region this returns an empty AABB. The camera then aims at the world origin and draws a silently wrong frame instead of refusing.
- **N5. `client/tests/support/snapshot_fixture.gd::_read_actors`:** if two actors share an id, the second silently overwrites the first.
- **N6. `client/addons/engine/render/volume_textures.gd::bricks`:** it hard-codes `>> 2` where `BRICK` is the constant. Changing `BRICK` would break the bricks without any error.
- **N7. `client/addons/engine/render/cutaway.gd` header, and §2 "No pops":** the claim holds only while the player is within a side wall's x range.
  - Scenario: the player is on the pavement west of x = 1.2 m and the camera is at yaw 135. For `wall_south` the nearest point is the wall's west corner, and dot(q − p, f) changes sign as the player walks east toward x = 1.2 (at (0.2, 1.0) it is cut; at (1.2, 1.0) it is not).
  - So the cut flips while the player walks, not only when a turn starts. The code comment says "inside it", which is accurate; §2's flat "a side wall's face is never crossed" goes further than that.

## Checked and found sound

- **Fixtures:** `client_fixtures.py` transposes x, y, z correctly and its crack ramp arithmetic is right (64 + 38 per column, 64 to 254). The staleness test fails when a fixture changes or goes missing.
- **Fixture reader:** every header field is type-checked before use. SHA-256 is checked before inflating, and the inflated size is capped at 4 MB. Each refusal case in `test_every_malformed_header_is_refused` reaches a distinct branch.
- **Uploads:** the slice and brick layouts match the shader's `texelFetch` coordinates. The asymmetric-snapshot test pins every axis.
- **Ray walk:** `walk_at` picks the right entry cell on both + and − faces. `MAX_STEPS = 320` covers the 208-cell worst case. Palette indices are clamped to 0–15.
- **Tier variants:** both shader variants compile under the load check (`load_all`). `use_tier` picks the variant per tier, and a test checks it.
- **`golden_run` wiring:** a failed draw stops all judging (tested). The measured findings gate the job and the advisory notes don't (tested). The result reports 6 shots and 3 goldens, matching `SHOTS` and `TIERS`.
