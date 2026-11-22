# Architecture review: phase1/client-fuel, delta 1 (round 1 → fold)

**Read:** `git diff 69483d9` plus the untracked files (HEAD d91df0f, the fold uncommitted), `git diff --cached` (the
staged checklist paragraph), `reviews/client_fuel/fold.md`, my round-1 report, `client_objects.md` §2–§7,
`client_rendering.md` §4.1, `research/fuel_antialiasing.md`, `checklists.md` step 8, `standards_backlog.md` B5 and B7, and
lesson 26's new paragraph. The code I read: `fuel_pass.gd`, `fuel_snapshot.gd`, `fuel_geometry.gd`, every
`fuel_*.gdshader*` file, `flame_colour.gdshaderinc`, `tests/support/{fuel_footprints,golden_shot,render_stage}.gd`,
`tests/golden.gd`, `tests/stability_check.gd`, `scripts/golden_{fuel,stability,run}.py`, `scripts/fuel_fixtures.py`
(outline only) and `tools/fuel_aa/frame_time.gd`.

**Ran:**
- Word counts with `wc -w` against `git show 69483d9:<path>`.
- `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_fuel_fixtures.py tests/test_golden_run.py`: 68 passed.
- A headless Godot probe on a copy of `client/` under the scratchpad, with HOME and XDG moved there (D-S1).
- The client suite on that copy, with D-S1's fix applied: `client-tests: PASS 72 tests`.

Nothing in the worktree was written.

## Status of my round-1 findings (set from the tree)

| Finding | Status | What I read |
|---|---|---|
| A1, two §7.2 bars rewritten with no ruling | **open (owner's)** | §7.2 still has burn-through with no width clause (`golden_fuel.py::burn_through_findings` checks `.any()` per live segment) and tier agreement per object. No ruling is cited anywhere. The fold puts it to the owner in the hand-off, so it stays open until the owner rules. The hand-off has to name **four** edits to the accepted table, not two: the fold also added the **Burnout** and **Crossing** rows. Those make the table stricter, but they are still contract edits. The width gap is concrete: nothing holds the rod shader's floor to `FuelPass.drawn_half_m`. Only the llvmpipe goldens would see a floor drop from 2 px to 1 px, and they are judged only in CI. |
| A2, §4.1 stale | **open** | The texel list is fixed (`client_objects.md` lines 182–184 match `fuel_pass.gd::_place` and `fuel_object.gdshaderinc::instance_at`). But §4.1's Colour bullet (lines 198–199) still says "An unknown recipe or kind is reported and drawn magenta". §3.2's decoder list, six paragraphs up, now refuses an unknown kind and recipe, so the design contradicts itself. The code draws magenta only for a vocabulary recipe that the palette doesn't colour or that falls past slot 14. One sentence fixes it. |
| A3, an overflowing recipe drawn in a real colour | **fixed** | `UNCOLOURED_SLOT = PALETTE_SIZE - 1`. `use_palette` stops at slot 14, and `_place` defaults to slot 15. `test_a_recipe_past_the_palette_draws_magenta_never_a_real_colour` checks byte 3 and the palette's slot 15. |
| A4, the burnt-out rule with two owners | **fixed** | There is one `burnt_out(object_row)` in `fuel_object.gdshaderinc`, used by `fuel_colour` and by `fuel_flame.gdshader::vertex` through `segment_object_tex`. The fixture's `rod_spent` is hot and ignited. `golden_fuel.py::burnout_findings` and `dead_flame_findings` check it. I did not rerun the deletion proofs (that is the Executor lens's job). |
| A5, open items only in a research note | **fixed, except item (1), open (owner's)** | Slab edge coverage is now in the step 8 "Remaining" list. The hard-edge test is renamed `test_a_hard_edged_line_crawls_beyond_the_ideal_but_only_near_the_bar` and asserts the weakness. Item (1), "a rig-only regression passes", still lives only in the research record and `fold.md`. It is an owner question for the hand-off, and it stays open until the owner answers. |
| A6, design documents grew | **fixed** | `client_objects.md` is 5,179 words (base 5,180) and `client_rendering.md` 3,740 (base 3,742). The deleted §7.5 leaves no dangling link (grepped `docs/`). |
| A7, llvmpipe claims | **fixed** | The header says "Under llvmpipe only the goldens and §7.2's checks ran". The research record tables llvmpipe stability (1.08, 0.98, 1.20, 0.78) and records where the goldens came from (an image built from this branch, with a second run passing against them). |
| A8, the checklist doesn't say what's undone | **open (partly fixed)** | The step 8 bullet now splits built from remaining, and the S5 deferral is gone. Still wrong: "Remaining" leaves out four §7.2 rows that have no check: **Severity**, **Outlines**, the charred-face **Crack**, and **Speckle** extended to the fuel cold frame (`golden_measures.speckle_findings` still reads only `cold-{tier}.png`). It also leaves out the groove view (no fuel shader draws one). "§7.2's fuel checks, each proved by deletion" still reads as the whole table. §7.2's heading still names only `scripts/golden_measures.py`. My round-1 failure scenario still holds: the owner merges believing §7.2 is complete. |
| A9, `tools/fuel_aa` can't reproduce its record | **fixed** | `stability_frames.gd` and `measure.py` are gone, and `frame_time.gd` drives the shipped `FuelPass`. The record now says the comparison's MSAA row can't be rerun and points at the gate's `stability_check.tscn`. That is honest. The decision's evidence is now historical, which owner ruling 3 allowed. |
| N1, the flames' fixed 2 km box | **fixed** | `fuel_pass.gd::_fit_boxes` builds the box from `FuelGeometry.bounds`, grown by the flame height and the flame half-width. `test_culling_boxes_hold_what_the_shaders_draw` checks it. |
| N2, no engine why on the render modes | **fixed** | The why is in the headers of `fuel_rod.gdshaderinc`, `fuel_rod.gdshader` and `fuel_rod_fringe.gdshader`, and in `fuel_pass.gd::_init`. |
| N3, `show_fuel` trusts its caller | **fixed** | `show_fuel` now runs `problems()` on a structural change and `frame_problems()` on every frame. Its ordering has a new defect (D-S1). |
| N4, row decoding three times | **open (partly fixed)** | `FuelSnapshot._vectors` + `_at` and `FuelGeometry._xyz` + `_at` are still byte-for-byte the same helper in engine code. Footprints keeping its own decoding is right, because it is the test oracle. `stability_check.gd::_rod_point` adds a fourth decoding, in test support. NIT. |
| N5, `stability_findings` in the orchestrator | **fixed** | The check is now `golden_stability.findings(dir)`. `golden_run.measured_findings` is a list of calls. |
| N6, game palette keyed by fixture names | **fixed** | `tests/test_fuel_fixtures.py::test_the_recipe_palette_colours_every_recipe_the_fixture_names` holds `recipe_palette.tres` to `fuel_fixtures.RECIPES`. |
| N7, test-only state on an engine class | **rejected** | My own note asked for no change, and `FuelPass` has 8 public methods. |
| N8, pre-registration order | **deferred** | Trigger: the fold's first commit. The index holds only the S7 measure paragraph (`git diff --cached` read), and the fold says it is committed first. It is unverifiable until a commit exists. |

## New findings

### SHOULD-FIX D-S1: `fuel_pass.gd::show_fuel` rebuilds before the per-frame check, so a refused frame is half-applied
`show_fuel` runs `problems()` and then `_rebuild(snap)`, and updates `_structure`, before it calls `frame_problems()`.
`problems()` checks the sizes of the frame columns but not the `state` values, so a frame that is structurally new and
has a bad `state` byte passes the structural check and gets rebuilt. Only after that is it refused.

Measured in the scratch copy: draw the fixture, change rod 0's radius, set `state[0] = 2`, and call `show_fuel`.
- It returns `["object row 0 has state 2; only 0 and 1 are defined"]`, with `rebuilds` 1 → 2.
- A second identical call is refused again without a rebuild, because the structure now matches.

**Failure scenario:**
- A server bug inserts an object and emits a bad `state` in the same frame.
- The client draws the new instances, with their new first rows and segment counts, against the previous frame's
  segment and state textures, which hold fewer rows.
- That contradicts the docstring's "a refused frame draws nothing new, and the last good one stays", §3.2's "A refused
  frame draws nothing new", and CLAUDE.md's "never ... a half-applied change".
- `test_a_refused_frame_draws_nothing_new` doesn't reach this path: its bad frame column comes without a structural
  change.

**Fix (verified):** decide before doing. Run both checks first, then rebuild only if the structure changed. With that
reordering, the same probe refuses with `rebuilds` staying at 1, and the client suite passes 72 tests. Add the probe as
a test.

### SHOULD-FIX D-S2: the rebuild and steady-frame numbers sit in three documents, measured by a probe that isn't in the tree
"13.8–14.2 ms" and "0.09–0.10 ms" appear in:
- `client_objects.md` §4.1 (the rebuild);
- §7.4 (both numbers);
- `standards_backlog.md` B5 (both, plus the check's 3.4–3.5 ms).

`fold.md` names their source as `bench_fuel.gd (scratch probe)`, and no such file exists in the worktree (grepped). The
frame-time row cites `tools/fuel_aa/frame_time.gd`; the rebuild row cites nothing that can be rerun.

**Failure scenario:** this is the fold's own correction #1 repeated. A design number nobody can rerun from the tree,
stated in three places, goes stale on the next pass change, and only one copy gets updated. It also breaks one owner
per contract (B36): a budget row's value has one home.

**Fix (unverified):**
- Commit the probe beside `frame_time.gd`, or drop the numbers and cite the fold.
- Keep the value in one place (§7.4 or B5) and link to it from the others.

## NITs

- **D-N1 `fuel_snapshot.gd::kind_name`.** Its docstring says "the one rule the checks and the drawing both use", but
  only `test_fuel_snapshot.gd` calls it. The rule that is actually shared is `geometry_rows`. Dead code whose docstring
  claims ownership misleads the next reader at exactly TB-B1's site. Delete it, or say what it is for.
- **D-N2 the flame width is stated twice in one file.**
  - `FuelGeometry.flame_buffer` and `widest_flame_m` each write `maxf(4.0 * radius, MIN_ROD_FLAME_M)` and the slab
    width.
  - The four-floor-pixel minimum is in both `fuel_flame.gdshader::vertex` and `FuelPass._fit_boxes`.
  - If one copy changes, flames clip at the culling box.
  - The height got the right treatment (`FLAME_HEIGHT_M` feeds both the shader and the box); the width didn't. Derive
    `widest_flame_m` from the buffer's diagonal (unverified).
- **D-N3 `fuel_pass.gd::_row_texture`.**
  - `_materials["flame" if key == &"segment_object_tex" else "rod"]` is a special case that encodes which material
    `_param_on` gave a key.
  - A future key set only on slabs would never update in place, and would quietly allocate a new texture every frame.
  - A key → kind map next to `KIND_MATERIALS` would keep that in one place.
- **D-N4 `fuel_pass.gd::_init` comments disagree.** One comment says the rod passes are ordered "by priority, not
  distance". A few lines later another says fringes sort with the flames "by box centre", which is left over from the
  single-pass shader.
- **D-N5 `tests/golden.gd::_write_footprints`.** It computes the output pixel as `SIZE_M / HEIGHT`, where `RenderStage`
  uses `IsoCamera.pixel_metres(_size_m, size.y, 1.0)`. The two agree today, but this is a second copy of the rule that
  sizes every footprint. Call `IsoCamera.pixel_metres`.
- **D-N6 the ID view's coverage channel has two readers with two rules.**
  - `golden_fuel.object_areas` reads green (bodies write pure red).
  - `golden_stability.findings` reads red. It is right only because `stability_check.gd` hides the volume and draws no
    bodies.
  - Neither cites the other. Read green in both, or state the channel once.
- **D-N7 `client_objects.md` §7.2 Tier agreement row.** The parenthesis "(per object: pooled per kind, a thin stick's
  doubling hid)" is a decision's rationale inside a contract table. The rule says rationales go to `reviews/`.
- **D-N8 `golden_fuel.FIXTURE_NAME` and `fuel_fixtures.NAME`.**
  - Both are `"fuel_ramp"`. The test holds `FIXTURE_NAME in FIXTURES`, not equality with `NAME`. That is acceptable
    given the image constraint the module documents.
  - The fold's "the one name" holds only on the `golden_run` side.

## What I found sound

- **One kind rule.** `FuelSnapshot.geometry_rows` decides which table an object's row is in. The pass, the flames
  (`flame_buffer`), the footprints and `_geometry_problems` all call it, and `problems()` refuses shared or
  out-of-range ids. TB-B1's root cause is gone, not patched.
- **One floor rule on the CPU side.** `FuelPass.drawn_half_m` is what the footprints, the stability scene and the
  pass's tests call, and the shader's copy is labelled as one. (The CPU-to-GPU tie is A1's residue.)
- **The flame height has one owner:** `FLAME_HEIGHT_M` sets both the shader uniform and the culling box.
  `FLAME_REACH_M` in Python is tied to it by a test.
- **The stability keys** live in GDScript and in Python, held together by
  `test_the_stability_keys_are_what_the_scene_draws`. A key set that measures nothing fails.
- **Burnout is one helper** (`burnt_out`) used by both surface and flame. The flame-colour hue has one include.
- **The checks are split well.** `golden_fuel.py` and `golden_stability.py` each own their loading and judging, and
  `golden_run.measured_findings` reads as a list of named steps.
- **`GoldenShot` owns the shot grammar,** with a refusal for a fuel fixture in a cell mask.
- **The two rod passes** are a mechanism behind §4.2's contract sentence, and the why is recorded in the code.
- **The design budgets net down,** and §7.5's size estimate moved to the plan, where it belongs.
- **The pre-registration of the stability measure** stays in the checklist, ahead of the measurements in the index.

## What I did not verify

- Any deletion proof (Executor), or the two-pass depth ordering under `render_priority` on real hardware.
- That `next_pass` honours its own material's priority on Compatibility (Client and rendering).
- The llvmpipe goldens, which I can't rerun here.
- Whether the owner has ruled on A1 or A5 (1) out of band.
- `scripts/fuel_fixtures.py`'s new fixture rows, beyond their names.

## Counts

0 BLOCKER, 2 new SHOULD-FIX (D-S1, D-S2), 8 new NIT. Of round 1's 17 findings:
- **fixed (11):** A3, A4, A6, A7, A9, N1, N2, N3, N5 and N6, plus A5 apart from its item (1);
- **open (5):** A1 and A5 (1), which are the owner's, plus A2, A8 and N4;
- **deferred (1):** N8;
- **rejected (1):** N7.
