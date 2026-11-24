# Delta round: Architecture and Wire integrity, phase1/fuel-leftovers (uncommitted, against 2586ed7)

Reviewer: Architecture + Wire integrity (delta). Read: `fold.md`, both round 1 reports, `owner_rulings.md` 6–9, the
whole code and docs diff, `fuel_pass.gd::show_fuel`, `client_objects.md` §3.3/§4.1/§7.4, `contracts.md`,
`src/simcore/protocol/encoding.py`, `scripts/fuel_fixtures.py`. Ran: `wc -w` against 2586ed7 on every changed doc;
a >120-column scan; `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_fuel_fixtures.py
tests/test_golden_stability.py tests/test_golden_run.py` (83 passed); `scripts/fuel_fixtures.py --check` (rc 0);
a numpy f16 rounding check (AW-D1); greps for the removed sort (`use_view_direction`, `back_to_front`, `permute_`,
`_rod_bytes`: no hits in `client/`, `scripts/`, the design or the plans). Did not run Godot.

## Status of round 1 findings (set from the tree)

| Finding | Status | Evidence in the tree |
|---|---|---|
| A1 sort by centre | fixed | Sort removed. `fuel_pass.gd::_init`: depth (priority 0) → `rod_core` (1) → `rod_fade` (2) → flames (3); `fuel_rod_fringe.gdshader` discards by `(coverage < 0.5) != fade_half`, so each fragment falls in one half. The order no longer depends on instance order or yaw by construction. `fuel_fixtures.py:179-184`: the stick crosses 0.15 m off the log's centre. `test_fuel_pass.gd` holds the chain and the priorities |
| A2 no shipped caller of `use_view_direction` | fixed (moot) | No camera obligation remains: the API, the sort and the cached buffers are gone |
| A3 fade bar round, laptop guards nothing | fixed | `FADE_SHARE = 1/14`, derived in the comment and held by `test_the_fade_bar_is_half_the_coverage_models_share`; `FADE_TIERS = ("rig", "max")`; the §7.2 row says "on rig and max". Deletion 0.021 against 0.071 is a clear margin. Stale laptop numbers remain beside it: AW-D3 |
| A4 ruling 6 / unguarded clamp | fixed | Ruling 6 narrowed to what was measured; ruling 9 adds `FuelSnapshot._temperature_problems`, run on every frame from `show_fuel` before anything is drawn, with a test of +∞, −∞, NaN, 6,004 and −273.25 and both edges. The shader copy is tied to the decoder's by `test_the_temperature_clip_is_the_shaders`. The tie to the owner and the producer is missing: AW-D1 |
| A5 design doc grew | fixed | `research/fuel_antialiasing.md` 1,124 → 1,120; `client_objects.md` 5,176 → 5,153. `checklists.md` 9,198 → 9,301 (+103), a plan already past the cap: still for the owner, not this branch's defect |
| N1 `CROSSINGS[0]` decides the pair | fixed | `FADE_PAIR`, compared by value |
| N2 `"shaded_update"` in many places | fixed | `GoldenShot.UPDATE`, `FUEL_ONLY`, `NEXT_SUFFIX` in GDScript. `golden_run.py::SHOTS` and `golden_fuel.py::FIXTURE_NEXT` keep Python literals, held only by the golden run itself |
| N3 `TOWARD_CAMERA` untied | fixed | `test_the_leaning_plank_faces_the_golden_camera` parses `iso_camera.gd`'s yaw and elevation (passes) |
| N4 wrapping, branch name | fixed for what it named | Step 8's paragraph wraps at 120; the branch reference is gone. The fold adds a new 179-column line to the research note: AW-D5 |
| W1 silent forgotten call | fixed (moot) | as A2 |
| W2 interface not in §4.1 | fixed | §4's anti-aliasing bullet states the three passes and ruling 7. No other module now depends on rod draw order |
| W3 §7.2 deletion fails only on rig/max | fixed | the row names the tiers; `test_the_fade_is_not_judged_on_laptop` |
| W4 "linear on every tier" | fixed | §7.2 and the checklist say "measured on rig and laptop" |
| W5 stale comments on instance order | fixed (moot) | `_place` and the shader header are main's text again |
| W6 turn re-upload cost | fixed (moot) | no turn re-upload. The fold adds a new per-frame cost the design does not show: AW-D2 |
| W7 ruling 6: trigger, authorship, widening, three copies | fixed | Ruling 9 checks the clip at a layer every renderer reaches, so the deferral no longer needs an HDR trigger; "Recorded by the author from the owner's answers in the session" marks authorship; the shader comment now says "on llvmpipe with the linear tonemapper"; the checklist and the shader cite the ruling rather than restating it |
| W8 thin margin | fixed | the new bar is derived; the measured deletion (0.021) is 0.05 under the bar (0.071), the baseline (0.396) far above |
| W9 column test on one fixture | fixed | parametrized over `ff.FIXTURES` (passes) |
| W10 transform/row pairing | fixed (moot) | instance i is geometry row i again |

## New findings from the folds

### AW-D1 SHOULD-FIX: the temperature clip has two client copies tied to each other, but neither is tied to its owner or to any producer, and the decoder's comment claims a server clip that doesn't exist

`client/addons/engine/render/fuel_snapshot.gd::TEMPERATURE_MIN_C` / `TEMPERATURE_MAX_C`;
`client/addons/engine/render/fuel_object.gdshaderinc::FUEL_MIN_C` / `FUEL_MAX_C`; `client_objects.md` §3.3.

- **Defect.** The owner of the clip is §3.3's `surface_temperature_c` row ("raw, clipped to [−273, 6000]"). It is not
  a registered contract (`contracts.md` registers the column names only). The fold creates a second client copy and
  ties the two together (`test_the_temperature_clip_is_the_shaders`, a string match). Nothing ties either copy to
  §3.3, and nothing ties the producer to it, because no producer clips. `src/` has no fuel-segment encoder
  (`grep surface_temperature src` finds nothing). The stand-in producer, `scripts/fuel_fixtures.py::content`, writes
  `s.temperature_c` raw, with no clip. The constant's comment, "§3.3's clip of surface_temperature_c, which the server
  applies", describes code that doesn't exist. Before the fold, a mismatch between producer and client only changed
  the glow at the extremes. Now the client refuses the whole frame, so a mismatch has a much worse failure.
- **Failure scenario (rounding verified, the rest unverified).** The server's fuel encoder lands later and clips at
  −273.15, the absolute zero that `scene.py` and `materials.py` already use. `np.float16(-273.15)` is −273.25
  (I ran this: −273.15 → −273.25, −273.0 → −273.0, 6,003.9 → 6,004.0). Any segment at the floor then reaches the
  client as −273.25, which `_temperature_problems` refuses. `show_fuel` returns the problem and keeps the last good
  frame, so fuel freezes on screen. The client's tests stay green, because they hold the client to itself.
  `encoding.py:34` shows the pattern already exists: the cell channel's clip is an inline literal with no tie to the
  client either (that predates this branch).
- **Fix direction (unverified; review doesn't design).** Hold every copy to the owner: register the clip with §3.3 as
  its owner, or add a Python test that reads both GDScript constants against §3.3's row. Name the producer's clip as a
  test to write at the step that builds the fuel encoder. Until then, the comment should say what is true: §3.3
  specifies a server clip, and no server code applies one yet.

### AW-D2 SHOULD-FIX: §4.1 still says a steady fuel frame costs 0.08–0.09 ms and uploads "without a loop"; the shipped steady frame now runs a 2×10⁴-iteration GDScript loop at 1.5–1.8 ms

`docs/design/client_objects.md` §4.1 (line 187: "a steady frame 0.08–0.09 ms"; line 188: "Segment state uploads on
every cell-frame message (2 Hz), without a loop"); `fuel_pass.gd::show_fuel` docstring ("a steady burn costs a
compare, a short check and its segment uploads"); §7.4 ("Decode-and-upload gains a steady fuel frame … measured in
§4.1").

- **Defect.** `show_fuel` calls `frame_problems` on every frame. `frame_problems` now ends in `_temperature_problems`,
  which runs `decode_half` once per segment. The author measured it at 1.5–1.8 ms at 2×10⁴ segments, 17–22 times the
  steady frame §4.1 states, and half of `client_rendering.md` §8's 3 ms decode-and-upload budget. The number is
  recorded only in B5's row. The design, which §7.4 names as the place the steady frame is measured, still gives the
  old figure, and the docstring still says "a short check". This is a claim about the shipped path that the fold made
  false.
- **Failure scenario.** The step that wires `show_snapshot` to the stream budgets the client's 3 ms from §4.1's
  0.08 ms. It finds 1.5–1.8 ms of fuel decode already spent, or never finds it, since nothing meters it (B5).
- **Fix direction (unverified).** Replace §4.1's figure and its "without a loop" with the measured steady frame, check
  included. This is a number swap, so the design does not grow. Then correct the docstring.

### AW-D3 SHOULD-FIX: the laptop exemption cites L* numbers from the removed sort, not the shipped two-pass shader

`docs/plans/checklists.md` step 8 ("the upscale smears the core into the band: 17.8 L* against 13.6 with the fade
overwritten"); `tests/test_golden_fuel.py::test_the_fade_is_not_judged_on_laptop` (comment "17.8 L* intact, 13.6
overwritten, measured").

- **Defect.** 13.6 L* is round 1's laptop reading with rods unsorted (architecture A3, wire W3), and 17.8 L* is the
  sorted baseline. Both measured the old mechanism with the old L* measure. The shipped shader on laptop measures
  0.258 (two passes) against 0.233 (one pass) as a linear share, the figures in the research note's table. The
  conclusion still holds, because laptop still can't tell the deletion from the baseline. But the plan and the test
  present numbers from a mechanism that no longer ships, labelled "measured". The design-side record (the research
  note) and the plan now disagree.
- **Failure scenario.** Whoever derives the laptop measure, the checklist's "Remaining" item, starts from 17.8
  against 13.6 L*. That is a gap of 4.2 L* that the shipped shader never showed.

### AW-D4 SHOULD-FIX: the research note says the goldens passed a second run after re-recording, and the fold table says that run is pending

`docs/design/research/fuel_antialiasing.md` "The goldens" ("re-recorded 2026-11-22 (the leaning plank, its splinter
and the moved crossing added) … and a second run passed against them (27 shots, …)"); `reviews/fuel_leftovers/fold.md`
last line ("Goldens re-recorded from the Linux baseline after the folds (the moved crossing); a confirming run is
pending").

- **Defect.** The two documents contradict each other about the same run. The crossing moved in the fold, so a second
  run from before the fold doesn't confirm these PNGs. I can't verify either claim from the tree. Whichever is
  stale, one of them claims a result that, by the other, hasn't happened.
- **Fix.** Make them agree with what was run. If the confirming run hasn't happened yet, the research note shouldn't
  say it passed.

### AW-D5 NIT: §7.4 and the frame-time record describe two rod passes; the shipped rod draws three

`client_objects.md` §7.4 ("the object pass, both rod passes and the flames"); `research/fuel_antialiasing.md`'s
frame-time table. Every rod now draws one more blended pass (core and fade split). Most fragments discard in one half,
but each fragment's coverage is computed twice. The table's figures predate the split, and the frame time of the
shipped shader is unmeasured. This is the Performance lens's call. I note it because §7.4 says "both", and that is now
wrong.

### AW-D6 NIT: a new unwrapped line in the research note

`docs/design/research/fuel_antialiasing.md:88` is 179 columns ("…so a front fade lands on a rear rod in any order. The
check, on rig and max (ruling 8): …"). This is the pattern N4 named, reintroduced by the fold.

## Checked and fine

- `show_fuel` runs `frame_problems`, and with it the temperature check, before any check that could draw. So a
  refused frame changes nothing (TB2-B1 holds), on the steady path and the rebuild path alike.
- `_temperature_problems`' `not (t >= lo and t <= hi)` refuses NaN, and the test covers a quiet-NaN pattern.
- The rulings record keeps the decisions in `reviews/`. The design's §9 is a link, so `lint_contracts.py`'s
  "rulings in a design" rule holds. Ruling 6's narrowing matches the shader comment's narrowing, and ruling 7's claim
  ("any crossing, yaw and instance order") follows from priority ordering by construction, not from one measurement.
  It is worded as a mechanism, which is right.
- The update shot is wired on the shipped check path: `golden_run.SHOTS` → `golden.gd::_draw` → `_show_next` →
  `GoldenShot.show_steady`, which refuses a rebuild. `fuel_findings` calls `update_findings`. The fixture `--check`
  covers `fuel_ramp_next`.
- `fade_half` is set only on `rod_fade`, and the unit test reads it after `use_pixel_metres`, so `_param`'s uniform
  fan-out doesn't clobber it.

## Summary

| Id | Severity | One line |
|---|---|---|
| A1–A5, N1–N4, W1–W10 | fixed (A2, W1, W5, W6, W10 moot) | see the status table |
| AW-D1 | SHOULD-FIX | The clip is tied shader ↔ decoder only: nothing ties it to §3.3 or a producer, and no producer clips. A producer clipping at −273.15 (f16 −273.25, verified) would freeze fuel |
| AW-D2 | SHOULD-FIX | §4.1's "steady frame 0.08–0.09 ms, without a loop" and `show_fuel`'s "short check" are false now that the per-frame check costs 1.5–1.8 ms |
| AW-D3 | SHOULD-FIX | The checklist and the laptop test cite 17.8/13.6 L* from the removed sort; the shipped laptop numbers are 0.258/0.233 |
| AW-D4 | SHOULD-FIX | The research note says a second golden run passed after re-recording; `fold.md` says the confirming run is pending |
| AW-D5 | NIT | §7.4 says "both rod passes"; the rod draws three, and the frame time of the shipped split is unmeasured |
| AW-D6 | NIT | `fuel_antialiasing.md:88` is a 179-column line |
