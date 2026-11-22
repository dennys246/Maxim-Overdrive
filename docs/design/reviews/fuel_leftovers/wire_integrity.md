# Wire integrity: phase1/fuel-leftovers (uncommitted, against 2586ed7)

Reviewer: Wire integrity lens. Read: `git diff 2586ed7`, the two untracked fixtures and `owner_rulings.md`, plus every
producer and consumer outside the hunks that I could find by grep (listed per row). Ran:
`.venv/bin/python scripts/fuel_fixtures.py --check` (rc 0) and
`.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_golden_stability.py tests/test_fuel_fixtures.py tests/test_golden_run.py`
(77 passed). I did not run Godot.

## The direct question: does the in-game camera call `use_view_direction`?

**No. There is no in-game camera.** `client/game/main.tscn` is one empty `Node3D`. `FuelPass.new()` appears only in
`client/tests/support/render_stage.gd:22` and the unit tests, and `IsoCamera.place` is called only from
`render_stage.gd::aim` and unit tests (`grep -rn "use_view_direction\|IsoCamera.place\|FuelPass.new" client`).
The only caller of `use_view_direction` outside unit tests is `RenderStage.aim`, a test fixture. The whole fuel pass has
no shipped caller yet, and that was already true before this branch. What the branch adds is a second obligation on
whoever builds the shipped scene: it must call `use_view_direction` on every camera turn, and if it forgets, nothing
reports it (W1).

## Contract table

| Contract | Owner section | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|---|
| Call `FuelPass.use_view_direction(forward) -> String` (new) | none (W2) | — → `RenderStage.aim` (test stage), unit tests | — → `FuelPass._upload_rods` | rods drawn in geometry-row order → sorted far to near when it is called; row order when it is not |
| Rod instance order (instance i ↔ geometry row i) | `client_objects.md` §4.1 says only "indexed by `INSTANCE_ID`" | `_place`: instance i = geometry row i → a permutation when `_forward` ≠ 0 | `fuel_rod.gdshaderinc` (`instance_at(INSTANCE_ID)`), `instance_images["rods"]`, `test_fuel_pass.gd` | the shader still reads its own row, because bytes and transforms are permuted together. `instance_images["rods"]` is now in draw order, not row order. The `_place` docstring and the shader header comment are stale (W5) |
| Instance texture upload cadence | §4.1 ("the rebuild is rare") | on a rebuild → on a rebuild and on a turn | GPU | a turn now re-uploads the rod transforms and the instance texture. No cost was measured (W6) |
| Fuel fixture `fuel_ramp_next.{json,bin.gz}` (new) | `client_objects.md` §3 | — → `fuel_fixtures.py::objects_next`, through the same `content()` as `fuel_ramp` | `golden.gd::_show_next`, `golden_fuel.py::FIXTURE_NEXT`, `test_golden_shot.gd`, `test_golden_fuel.py` | the same format and header generator as `fuel_ramp`. `--check` covers it (`stale()` iterates `FIXTURES`). The §3 column test (`test_every_table_carries…`) checks only `content()`'s default `NAME`, but `objects_next` reuses `objects()` and only changes temperatures, so this is low risk (NIT W9) |
| `fuel_ramp` fixture (changed: 79 objects, 2 slabs, regions 16–17) | §3 | `fuel_fixtures.py::visible` + `leaning` | `test_fuel_snapshot.gd`, `test_fuel_pass.gd` counts, `golden_fuel.py`, goldens | the counts were updated in every consumer I found. The goldens were re-recorded (3 PNGs) |
| Golden shot vocabulary `shaded_update`, `NEXT_SUFFIX`, PNG `fuel-<tier>-update.png` | `golden_shot.gd` / `golden_run.py::SHOTS` | — → `golden_run.py::SHOTS` | `golden_shot.gd::parse`, `golden.gd::_draw`, `golden_fuel.py::update_findings`, `test_golden_run.py` (24 → 27 shots) | consistent. The update frame's footprints are written from the *first* fixture's snapshot (`golden.gd::_write_footprints(snap…)`), which is correct only because the structure is identical, and the run itself checks that (`rebuilds` unchanged) |
| Check `crossing_findings` (now two pairs + fringe), `update_findings`, `area_findings` | `client_objects.md` §7.2 | — | `golden_run` → `fuel_findings` / `golden_stability.findings` | wired on the shipped check path (`fuel_findings` calls `update_findings`; `findings` calls `area_findings`) |
| Claims in §7.2, `checklists.md` step 8, `research/fuel_antialiasing.md`, `owner_rulings.md`, shader comment | see W3, W4, W7, W8 | | | |

## Findings

### W1 SHOULD-FIX: a shipped scene that never calls `use_view_direction` draws rods unsorted, and nothing reports it

`client/addons/engine/render/fuel_pass.gd::_forward` / `_upload_rods`

- **Defect.** `_forward` defaults to `Vector3.ZERO`, and `_upload_rods` treats zero as "draw in row order". The only
  code that sets it is `RenderStage.aim`, which is test support. Whoever writes the shipped camera (step 8's shipped
  scene, or wherever the iso camera gets a controller) calls `IsoCamera.place`, a static helper that knows nothing
  about `FuelPass`. If they don't also find and call `fuel.use_view_direction(-camera.transform.basis.z)` after every
  turn, the game draws the D1 crossing defect again: the rear rod overwrites the front rod's outer fade (7 px by up to
  122/255 on rig, per `research/fuel_antialiasing.md`). There is no error and no failing test, because every check
  draws through `RenderStage`, which does the call itself.
- **Failure scenario.** The shipped scene creates a `Camera3D` and a `FuelPass` and turns the camera with
  `IsoCamera.place(camera, target, IsoCamera.step_yaw(k), size)` on Q/E. Every golden still passes, and in play every
  crossing shows the overwritten fade.
- **Why this is my lens.** CLAUDE.md's "A fix ships with a caller" and "Push invariants into types": the D1 fix has
  no caller on the shipped path, and its one required collaborator (the camera's direction) is optional and silent.
  `checklists.md` step 8 lists the work as built ("Built on `phase1/fuel-leftovers`: rods sorted back to front per
  view direction"). Other rows in the same file say "done, no shipped caller until step 8 (the shipped scene …)", and
  this row doesn't.
- **Fix direction (unverified; review doesn't design).** At minimum, the checklist row should say "no shipped caller
  until the shipped scene", and the shipped-scene step should list the call as a test to write. A sturdier fix would
  make the camera's direction reach the pass through one owner, so that forgetting it fails loudly, not silently.

### W2 SHOULD-FIX: the camera → fuel-pass interface is not in the design that owns the pass

`docs/design/client_objects.md` §4.1

- **Defect.** Draw order is now part of the contract. The rods must be drawn far to near along the view direction,
  someone outside the pass must supply that direction on every turn, and the instance texture is re-uploaded then.
  §4.1 states none of this, and it still reads as if the instance texture is written only on a rebuild ("The rebuild
  is rare"). The only prose statements are in `research/fuel_antialiasing.md` (a research note) and `checklists.md`
  step 8. CLAUDE.md says interfaces between modules are contract and belong in the design (B32).
- **Failure scenario.** The author of the shipped scene reads §4.1, the owner of the object pass, and sees no
  obligation to pass a view direction. That leads to W1.

### W3 SHOULD-FIX: §7.2 says "rods unsorted" must fail the Crossing check, but it doesn't on laptop

`docs/design/client_objects.md` §7.2, the Crossing row; `scripts/golden_fuel.py::_fringe_findings`

- **Defect.** The table's third column is "Deletion that must fail it", and the Crossing row now lists "rods
  unsorted". The check runs on every tier (`fuel_findings` loops over `gm.TIERS`). By the author's own measurement, the
  deletion passes on laptop (13.6 L* against a bar of 4.2), and on rig and max it fails by only 0.8 L*. The research
  note and the checklist both record the laptop gap honestly, but the design row, which is the contract, claims a
  property the check doesn't have.
- **Failure scenario.** A later change that reorders rods breaks only the laptop tier. The design says the Crossing
  check catches it. It doesn't.
- **Fix direction (unverified).** The design row should say "(rig, max)", or the laptop gap should be cited where the
  row is.

### W4 SHOULD-FIX: "coverage linear on every tier (measured)" was measured on two tiers, in a different scene from the bar that relies on it

`docs/design/client_objects.md` §7.2 bullets; `checklists.md` step 8 ("coverage measured linear on every tier and checked by area (W-S5)"); `scripts/golden_stability.py::area_findings`

- **Defect.** `area_findings` runs inside `golden_stability.findings`, over `stability_check.gd::TIERS = ["rig",
  "laptop"]`. Max is never drawn there. The brief says the gamma-encoded deletion was "caught on every tier", but the
  check can't see max. W-S5's question (`reviews/client_fuel/fold.md`, W-S5 row) was about the per-object area bar,
  "Tier agreement". That bar reads `golden.gd`'s `fuel_mask` frames at 72 px/m on all three tiers. The new check
  measures the lone stick in `stability_check.tscn`. The two scenes share `RenderStage`, `use_pass(OCCLUDER)` with
  bloom off, and the `FUEL_ID` view, so the inference is plausible, but it is an inference, and the design says
  "(measured)".
- **Failure scenario.** A max-only setting (max differs from rig in `crack_substeps` and `ao_taps` today) starts to
  touch the fuel-ID target's encoding. §7.2 says linear was measured on every tier, and Tier agreement is relied on
  for max with no check that could see the change.
- **Fix direction (unverified).** Name the tiers and the scene where the measurement was taken, or add max to the
  stability scene's tiers.

### W5 NIT: two comments still describe instance order as row order

- `fuel_pass.gd::_place`'s docstring: "Instance i is geometry row i". This is false for rods once a direction is set.
- `fuel_object.gdshaderinc` header: "FuelPass writes them on a rebuild". They are now also written on a turn.
- `FuelPass.instance_images["rods"]` is a public field and is now in draw order. Its only reader outside the pass is
  `test_fuel_pass.gd`, and `_rod_position` there reads it correctly.

### W6 NIT: the turn re-upload has no cost on record

`fuel_pass.gd::_upload_rods`, `fuel_geometry.gd::permute_floats` / `permute_bytes`

§4.1 records the rebuild (14.1–14.5 ms) and the steady frame (0.08–0.09 ms) at the world limits. A turn now sorts and
permutes every rod with a `slice` + `append_array` per instance in GDScript, and re-uploads the transforms and the
instance image. That cost was not measured. B5 says budgets are measured, not guessed. This is the Performance lens's
call; I note it here because §4.1's numbers are now incomplete as a claim.

### W7 SHOULD-FIX: ruling 6 defers a check with no trigger, and its record doesn't show whose words it is

`docs/design/reviews/client_objects/owner_rulings.md` ruling 6; `checklists.md` step 8; `fuel_object.gdshaderinc` comment

- **Accuracy.** The technical content matches what I can check from the tree. `glow_curve` with `t_c` = +∞ gives
  `level` = +∞ times a finite, positive `hue` (span is clamped to 1, so it is `GLOW_WHITE`, with all three channels
  positive): +∞, not NaN, on every channel. A target that clips at 1.0 makes that identical to 6,000 °C, which is
  already over 1.0 (the glow curve's own comment says that every channel passes 1.0 from about 1,230 °C). So "the
  golden check could not fail" is consistent with the code. I did not reproduce the llvmpipe run.
- **Defects.**
  1. The deferred check's only trigger is "a renderer with an HDR target". No step in the roadmap or checklist
     schedules one, so in practice the finding is closed. CLAUDE.md (O25) requires a `deferred` finding to name a
     trigger that will fire. E2-S3 is now neither guarded nor tracked.
  2. Nothing in the tree marks the ruling as the owner's words relayed by the author, as O25 requires for a status
     the author sets after the owner decides. Rulings 1–5 were moved verbatim from the design. Ruling 6 is new text,
     not a transcription. If the owner did rule this way, record it as the author's record of the owner's ruling,
     with a date.
  3. The shader comment widens the claim: "Compatibility's 8-bit target saturates inf … so no frame here can see it".
     It was measured on llvmpipe only. On a real GPU, under the Compatibility renderer, the framebuffer format and any
     later tonemap (Reinhard's x/(1+x) gives inf/inf = NaN) belong to the driver and settings. The record in
     `owner_rulings.md` correctly says "on llvmpipe". The shader comment should too.
  4. The same reasoning is now written out three times (the ruling, checklist step 8, the shader comment). That is a
     one-owner-per-contract smell (B36). The copy an edit misses goes stale.

### W8 NIT: deletion margins on rig and max are thin, and the bar is derived but sits close to the deletion

`scripts/golden_fuel.py::FRINGE_SHARE`

The deleted case reads 6.5 L* against a 7.3 bar, 0.8 L* under it. The bar was written before measuring, as the rule
requires. My concern is the claim: `checklists.md` says "the check holds it on rig and max", and that is true by
0.8 L* on llvmpipe, the only place goldens are judged. The research note states the margin, but the checklist doesn't.

### W9 NIT: the §3 column-for-column test covers only the default fixture

`tests/test_fuel_fixtures.py::test_every_table_carries_client_objects_columns_with_their_dtypes_and_encodings` calls
`ff.content()`, which is `NAME` only. `fuel_ramp_next` and `fuel_stick` go through the same generator, so this is
low risk. Still, a fixture that claims the §3 format should be held to it, for example by parametrizing over
`ff.FIXTURES`. Unverified.

### W10 NIT: no test pairs a sorted rod's transform with its own instance row

`test_fuel_pass.gd::test_rods_draw_back_to_front_for_the_camera` checks the instance *bytes'* order after a sort.
`test_back_to_front_orders_instances_by_depth_and_keeps_ties` checks `permute_floats` on a synthetic buffer. Neither
test reads `fuel.rods.multimesh.buffer` after a sort to check that instance i's transform is the geometry of the row
its bytes name. Suppose a future edit permutes only one of the two arrays, or uses two different orders. The test that
reads bytes still passes, and every rod then draws another rod's segments. `_upload_rods` is correct today.

## What I checked and found consistent

- The sort key uses each rod's centre: `rod_buffer` puts the origin at `origin + axis·L/2`. Buffer floats 3, 7 and 11
  are the transform origin in a `TRANSFORM_3D` buffer, so the key is centre depth. Farthest first is correct for
  `forward = −basis.z`.
- `golden.gd` calls `show_fuel` before `aim`. So the first shot of each tier process builds in row order, then `aim`
  re-sorts it. Later shots in the same direction don't re-sort. The goldens are therefore drawn sorted.
  `test_a_turn_before_the_first_frame_builds_nothing` covers the reverse order (a turn before any frame).
- In `stability_check.gd`, the sub-pixel offsets move only the camera's origin, so the direction doesn't change and
  there is no re-sort per offset. `cutaway_check` turns the camera with no fuel loaded, and `_upload_rods` returns
  early.
- The update pass really is steady on the shipped `show_fuel` path: `_show_next` refuses the frame if `rebuilds`
  moved, so the in-place upload claim is measured where it runs.
- Both fixtures share one generator, `--check` passes, and `stale()` covers `fuel_ramp_next`.

## Summary

| Id | Severity | One line |
|---|---|---|
| W1 | SHOULD-FIX | `use_view_direction`'s only non-unit caller is the test stage. There is no in-game camera, and a forgotten call silently draws unsorted rods. The checklist row omits "no shipped caller" |
| W2 | SHOULD-FIX | The camera → FuelPass draw-order interface (and the re-upload on a turn) is not stated in `client_objects.md` §4.1 |
| W3 | SHOULD-FIX | §7.2 lists "rods unsorted" as a deletion the Crossing check must fail, but it doesn't on laptop |
| W4 | SHOULD-FIX | "Coverage linear on every tier (measured)" was measured on rig and laptop only, in the stability scene, not in the frames the Tier agreement bar reads |
| W5 | NIT | `_place` docstring and the shader header still say instance i is row i, written on a rebuild |
| W6 | NIT | The cost of the turn's sort, permute and re-upload is unmeasured, so §4.1's cost claims are incomplete |
| W7 | SHOULD-FIX | Ruling 6 is technically consistent with the code, but it defers E2-S3 with no trigger that fires, isn't marked as the author's record, and is restated three times. The shader comment generalizes beyond llvmpipe |
| W8 | NIT | The rig/max deletion misses the fringe bar by only 0.8 L*, and `checklists.md` says "holds" without the margin |
| W9 | NIT | The §3 column test covers only `fuel_ramp`, not `fuel_ramp_next` or `fuel_stick` |
| W10 | NIT | No test checks that a sorted rod's transform and its instance row still pair |
