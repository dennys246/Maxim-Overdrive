# Architecture lens: phase1/fuel-leftovers (uncommitted, `git diff 2586ed7` + untracked)

Reader: Architecture. Read: the full code and docs diff, `fuel_pass.gd`, `fuel_object.gdshaderinc`, `glow_curve.gdshaderinc`,
`fuel_snapshot.gd::frame_problems`, `iso_camera.gd`, `render_stage.gd`, `client_objects.md` §3.3/§4/§7.2/§9,
`reviews/client_fuel/fold.md`, the new `owner_rulings.md`. Ran: word counts against 2586ed7, line-length scan, by-hand
depth arithmetic (below). Did not run Godot, pytest, or the gate.

Counts: 0 BLOCKER, 5 SHOULD-FIX, 4 NIT.

---

## SHOULD-FIX A1: `client/addons/engine/render/fuel_geometry.gd::back_to_front`, sorting by instance centre fixes D1 only where the centres line up

**Defect.** The sort key is the depth of each rod's centre. The doc comment says this "orders crossing rods by height
under the iso camera". That holds only when the two centres share a horizontal position. In the fixture they do, exactly:
`stick_cross` runs from (3.2, 1.6) along y for 0.5 m, so its centre is (3.2, 1.85), and `log_cross` runs from
(2.95, 1.85) along x for 0.5 m, so its centre is also (3.2, 1.85). The fixture is the one layout where a centre sort is
always right, so the check cannot see the sort fail on any other layout.

**Failure scenario (arithmetic, unverified in Godot).** Take the vector toward the camera, `TOWARD_CAMERA` =
(0.542, −0.542, 0.643). Move the stick so it crosses the log 0.2 m west of the log's centre: the stick's centre is at
(3.0, 1.85, z+0.105) and the log's at (3.2, 1.85, z+0.05). The stick's depth advantage is
0.542·(−0.2) + 0.643·0.055 = −0.073 m. A negative value means the stick sorts as farther away, so it draws first, the
log draws over its outer fade, and D1's defect comes straight back. Any crossing off-centre by more than about 0.065 m
along x or y inverts the order, which covers most real crossings in a pile. A long log under a short stick also yields no
correct order between centres.

**Why it is my lens.** The claim recorded in `checklists.md` step 8 ("rods sorted… D1's outer half; the check holds it
on rig and max") and in `research/fuel_antialiasing.md` ("Sorted since…") reads as a general fix. It is a fix for
crossings whose centres coincide. Either the limit is recorded with its numbers, or the root issue is addressed:
pairwise crossings have no correct global order by centre, and a sort by the depth of the closest point, or a per-pixel
method, is a design question for the owner. An off-centre crossing in the fixture would let the check see the
difference. (Unverified proposal; the author should measure it.)

## SHOULD-FIX A2: `client/addons/engine/render/fuel_pass.gd::use_view_direction`, nothing enforces the obligation to call it, and no design states it

**Defect.** The rod sort only happens if whoever moves the camera calls `use_view_direction`. Today the only caller is
`client/tests/support/render_stage.gd::aim`. The game has no camera yet (`client/game/main.tscn` is an empty
`Node3D`). The obligation that every camera mover must also tell the fuel pass is an interface between two modules
(`IsoCamera`/cut-away and `FuelPass`). It appears in no design section. `client_objects.md` §4 still describes rods as
"depth alone…, then colour blended by coverage" and says nothing about order. §7.2 names "rods unsorted" only as a
deletion.

**Failure scenario.** The game's camera controller, when it is built, calls `IsoCamera.place` and not
`use_view_direction`. `_forward` stays at zero and `_upload_rods` falls back to row order, so every crossing on the
shipped path is unsorted. No golden sees it, because the goldens go through `RenderStage.aim`, which does call it. The
failure is a silent no-op, the case "push invariants into types" exists to prevent.

**Fold options (unverified).** Make the coupling structural: `FuelPass` reads the active camera's basis when it changes,
or takes the camera as a required collaborator. At the least, state the contract in `client_objects.md` §4, in the
section that owns rod drawing, trading words elsewhere because the design must not grow.

## SHOULD-FIX A3: `client_objects.md::§7.2` (Crossing row) and `scripts/golden_fuel.py::_fringe_findings`, the row claims a deletion the check misses on laptop, and the laptop run guards nothing

**Defect.** The §7.2 table lists "rods unsorted" among the Crossing check's deletions, with no tier qualifier. By the
author's own measurement, on laptop the check passes with rods unsorted (13.6 L* against a 4.2 bar). `fuel_findings`
still runs `_fringe_findings` on every tier, so the laptop pass reads as coverage it doesn't give. Two places record the
laptop gap: `checklists.md` "Remaining" and the research note. The design's acceptance table, the contract other
readers trust, does not.

**Failure scenario.** A later change breaks the sort only on the half-resolution path, for example an upscale-specific
order. Laptop stays green, and a reader of §7.2 believes laptop is covered.

**Fix.** Qualify the row as "rods unsorted (rig, max)". Either stop running the fade measure on laptop until a laptop
derivation exists, or keep it and say in the code that it guards nothing there. Also note: on rig and max the deleted
case sits 0.8 L* under the bar (6.5 against 7.3). That margin is thinner than any other deletion proof on this branch.
`FRINGE_SHARE = 0.1` is a round number. Its comment derives it informally ("a quarter of coverage… more than a tenth"),
not from the source's error, so B30's rule for new bars applies. The Executor and Physics lenses may weigh this more.

## SHOULD-FIX A4: `owner_rulings.md` ruling 6 and `fuel_object.gdshaderinc` (the `FUEL_MAX_C` clamp), the record is accurate for the golden layer, but the clamp is now unguarded with no tracked trigger, and the layer where it could be checked isn't named

**Is the record accurate?** Mostly yes. Temperature feeds only the glow term:
`if (t_c > FUEL_GLOW_START_C) colour += glow_curve(...)`. Neither −∞ nor NaN passes that test. +∞ gives
`hue * level` = ∞ on every channel, because every `GLOW_WHITE` component is nonzero. 6,000 °C gives a level of about
1,100. An 8-bit Compatibility target saturates both to white. So "no frame can see it" holds for Compatibility goldens,
and removing a check that could not fail was the right call.

**What the record misses:**
1. **No tracked trigger.** "A renderer with an HDR target makes it checkable" names no step. `client_rendering.md`
   defers Forward+ to Phase 2 light. No roadmap row and no `standards_backlog.md` row carries the item. The charter
   requires a deferral without code to mark to be a backlog row, so the item lives only in prose. The clamp itself is a
   fold of TB-S4 (`reviews/client_fuel/fold.md`), a trust-boundary finding. That fold is now unguarded and untracked.
2. **The checkable layer exists today and isn't considered.** §3.3's contract is "clipped to [−273, 6000]", and
   `FuelSnapshot.frame_problems` already checks each frame's values (`objects.state > 1` is refused). A range check on
   `surface_temperature_c` there would be unit-testable on any renderer. It would also refuse NaN, which the shader
   clamp does not neutralize: GLSL `clamp(NaN, …)` is undefined. The record says "no frame can see it" and stops there.
   It doesn't say that the ruling chose an uncheckable layer over a checkable one, so the owner did not rule on that
   option. Review doesn't design; this is a gap in the decision record, for the owner to rule on.

**Failure scenario.** A server-side encoding bug emits f16 NaN or ∞. On Compatibility nothing refuses it, NaN may draw
as an arbitrary colour, and no test notices.

## SHOULD-FIX A5: `docs/design/research/fuel_antialiasing.md`, an existing design document grows (B24)

The file grows from 1,124 to 1,247 words (+123, measured with `wc -w` against 2586ed7). It lives under `docs/design/`,
and the budget rule says an existing design document does not grow. The new table and paragraph could move to the
review record or the checklist, or older text could be cut. `client_objects.md` shrank, 5,176 → 5,113, but only because
§9 moved out. Its §7.2 rows grew, so the net figure hides growth in contract text. That growth is allowed while the net
stays down, but it is worth stating in the hand-off. `checklists.md` grows by 115 words, 9,198 → 9,313. It is a plan
already far past the 2,500-word cap for new plans; flagged for the owner, not as a defect of this branch alone.

---

## NIT N1: `scripts/golden_fuel.py::crossing_findings` and `_fringe_findings`, the tuple's position stands for a role

`elif front == CROSSINGS[0][0]` and `_fringe_findings`' `front, behind = CROSSINGS[0]` make position 0 mean "the rod
pair that gets the fade check". If the pairs are reordered, the fade check silently moves to the slab pair, where it
measures nothing meaningful. `crossing_findings` now runs two checks. A separate `fade_findings(pair)` called from
`fuel_findings` would give each check one job.

## NIT N2: `client/tests/support/golden_shot.gd::parse`, the pass name `"shaded_update"` is owned in four places

The name appears in `PASSES`, in `NO_FLAMES`, in the inline list `["shaded_noflame", "shaded_update"]` of passes that
need fuel, and in `shot.update = parts[2] == "shaded_update"`, plus `golden_run.py::SHOTS`. A table of pass properties
would make adding the next pass a single edit.

## NIT N3: `scripts/fuel_fixtures.py::TOWARD_CAMERA`, a second owner of the camera's angles

It hard-codes the yaw of 45° and elevation of 40° from `iso_camera.gd` (`BASE_YAW_DEG`, `ELEVATION_DEG`), and nothing
ties the two together. `test_the_stability_keys_are_what_the_scene_draws` shows the existing pattern of parsing the
GDScript constant. If the camera's elevation changes, the plank stops facing the camera, and the C-S4 deletion proof
loses its derivation, whose own docstring shows a flat view can't see the deletion. Nothing goes red. This is close to
SHOULD-FIX, since the proof stays valid only by luck.

## NIT N4: `docs/plans/checklists.md` step 8, formatting and naming

The edited paragraph has unwrapped lines of up to 366 characters, against the file's 120-column wrap. "Sorted since
`phase1/fuel-leftovers`" in the research note names a branch, which stops meaning anything after merge. A step or a date
would hold up.

---

## Checked and fine

- The in-place path, `show_fuel` → segment textures and `state_tex`, never touches the instance texture or the
  transforms. The cached `_rod_bytes` and `_rod_transforms` therefore cannot go stale between rebuilds, and a re-sort
  after a camera turn uploads correct rows.
- The instance texture is permuted together with the transforms, so each instance's rows stay its own.
- Moving §9 to `reviews/client_objects/owner_rulings.md` follows "one owner per contract", which requires decision
  tables to live in `reviews/`. Citations in the form "owner ruling N" still resolve, and the numbering is kept.
- `ideal_coverage`'s edge-band rewrite is sound: a half-plane test with half a diagonal of margin, and every
  sample offset lies inside that disc. It is a refactor with one job.
- `area_findings`' bar comes from sRGB's own excess at the same geometry, a derived bar, not a round number.
- The Python modules are well under 500 lines, and no new function is near 40 lines.
