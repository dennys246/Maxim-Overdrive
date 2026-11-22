# phase1/fuel-leftovers: round 1 folds

Round 1 (2026-11-22): Executor, Architecture, Wire integrity, Client rendering, Trust boundary, Performance; no
BLOCKER. The owner ruled on three questions the findings raised (`../client_objects/owner_rulings.md` 7–9). The
"Author's fold" column is the author's claim; "Status" is set by a delta reviewer from the tree (O25).

| Finding | Author's fold | Status |
|---|---|---|
| A1, CR-1, E-S1: sort by centre right only where crossing centres line up | Ruling 7: the sort is removed; rod colour draws in two passes, every core (coverage ≥ 0.5) before any fade (`fuel_rod_fringe.gdshader` `fade_half`, `fuel_pass.gd::_init`: priorities depth 0, core 1, fade 2, flames 3). The crossing stick moved to 0.15 m off the log's centre. Deletion "single colour pass" (no fade material, the core drawing all coverage), Linux: rig/max fade share 0.396 → 0.021 (bar 0.071) | |
| A2, CR-3, W1: no shipped caller of `use_view_direction`; a host that forgets draws D1 | Moot: `use_view_direction`, `back_to_front`, `permute_*` and the cached rod buffers are gone; nothing needs the camera | |
| W2: §4.1 doesn't state the rod interface | `client_objects.md` §4 anti-aliasing bullet states the three passes and ruling 7 | |
| A3, W3, W8, E-S4, CR-2: fade bar round, 0.8 L* margin, can't fail on laptop, band mean 1/8 not 1/4 | Ruling 8: `golden_fuel.py::FADE_SHARE` = 1/14 in linear luminance (`_mean_y`), half the coverage model's 1/7 (band 1/8 over strip 7/8), judged on `FADE_TIERS` = rig, max; `test_the_fade_bar_is_half_the_coverage_models_share`, `test_the_fade_is_not_judged_on_laptop`; §7.2 row and checklist name the tiers | |
| A4, TB-S1, W7, CR-5: ruling 6 overclaims; TB-S4's decoder option not offered; no trigger | Ruling 6 narrowed to what was measured (llvmpipe, linear tonemapper, +∞); ruling 9: `FuelSnapshot._temperature_problems` refuses NaN, ±∞ and values outside [−273, 6000] per frame; `test_the_per_frame_check_refuses_a_temperature_outside_the_clip` (+∞, −∞, NaN, 6,004, −273.25 refused; both clip ends pass), `test_the_temperature_clip_is_the_shaders`. Shader comment narrowed | |
| A5: research note grew past its base | `research/fuel_antialiasing.md` 1,120 words (base 1,124); `client_objects.md` 5,153 (base 5,176) | |
| P-S1, W6, CR-7: sort cost unrecorded | Sort gone. The temperature check's cost, measured: 1.5 ms minimum, 1.8 median per frame at 2×10⁴ segments (headless, editor build, M2), in B5's row | |
| P-N1, P-N2: texture recreated per turn; animated turns | Moot (no sort) | |
| E-S2: no test of a rebuild after a camera turn | Moot (no sort) | |
| E-S3, CR-6, W10: no test that transforms and instance rows stay paired | Moot: instance i is geometry row i again, as on main | |
| TB-N1: `use_view_direction` accepts an overflowing vector | Moot (removed) | |
| TB-N2, E-N2: `_show_next`'s rebuild guard never seen to fire | Moved to `golden_shot.gd::show_steady`; `test_the_update_frame_must_reach_the_pass_steady` (steady next frame passes; `fuel_stick` rebuilds and is refused; a refusal is reported). Proved: the guard replaced by `false` turns exactly that test red | |
| W4, E-N1: "linear on every tier" measured on rig and laptop only | §7.2 and checklist say rig and laptop | |
| W5: stale comments in `_place` and the shader header | Moot: those files are back to main's text | |
| W9: column test covers only `fuel_ramp` | Parametrized over every fixture in `fuel_fixtures.FIXTURES` | |
| CR-4: the splinter's drawn depth is 29.8 mm (rig) / 43.7 mm (laptop), not 15.9 | `fuel_fixtures.py::leaning`'s docstring gives 29.8 mm (rig, max) and 43.7 mm (laptop) and the laptop margin, 1.9 mm; the measured deletion is caught on every tier (laptop 30.2 → −0.3 L*) | |
| N1: `CROSSINGS[0]` decides the fade pair | `FADE_PAIR` named, compared by pair | |
| N2: "shaded_update" in five places | `GoldenShot.UPDATE` and `FUEL_ONLY`; `golden_run.py` keeps its literal (Python, the shot list) | |
| N3: `TOWARD_CAMERA` untied to the camera | `test_the_leaning_plank_faces_the_golden_camera` reads `iso_camera.gd`'s yaw and elevation | |
| N4: unwrapped checklist lines; a branch name in the research note | Step 8's paragraph rewrapped; the note's branch reference removed | |
| P-N3: `area_findings` recomputes the ideal coverage | Open (NIT; 1.7 s a golden run) | |

Goldens re-recorded from the Linux baseline after the folds (the moved crossing); a second Linux run passed against them (27 shots, 6 goldens, cut-away, stick stability).

## Delta round 1 folds

Statuses of round 1's findings are in the three `delta_*.md` reports (all fixed but P-N3). Their new findings:

| Finding | Author's fold | Status |
|---|---|---|
| AW-D1: the temperature clip's copies tied only to each other; no producer clips | `fuel_fixtures.TEMPERATURE_CLIP_C`, the stand-in producer's; `test_every_fixture_temperature_is_inside_the_clip_and_the_clip_is_the_clients` holds every fixture inside it, both ends exact in f16, and the decoder's and shader's constants equal to it (the GDScript-only tie removed). The server's fuel encoder is step 7's: `FuelSnapshot`'s comment names it | |
| AW-D2, N-2: §4.1's 0.08–0.09 ms steady frame, "a short check", "a frame" | §4.1: a steady frame 1.80–1.83 ms, nearly all the temperature loop (0.10 ms without it); `show_fuel`'s docstring; ruling 9 and B5 say per snapshot (2 Hz) | |
| AW-D3: laptop's 17.8/13.6 L* were the sort's numbers | Checklist and the laptop test's comment: share 0.258 against 0.233 | |
| AW-D4: research note and fold table disagreed on the confirming run | The fold table was updated when the run passed (27 shots, 6 goldens) | |
| AW-D5, N-6: the third rod pass's frame cost unmeasured | B5's owed fuel row names it | |
| AW-D6, N-4: a 179-column line; the "Shipped" row describes one colour pass | Rewrapped; the row says core then fade. The note is 1,124 words, its base | |
| ET-S1: nothing pins the fade check to linear light | `test_the_fade_is_judged_in_linear_light`: an sRGB-60 band between 30 and 220 adds 0.046 linear, refused (L* would pass it). Proved: `_mean_y` swapped for `_mean_l` turns it red | |
| ET-N1, N-3: measured 0.396 against the model's 1/7, unexplained | `FADE_SHARE`'s comment and the research note: bloom adds to the band, so the bar is a floor, not a fit (inferred, not separated by measurement) | |
| ET-N2: docstrings said per-frame columns are only size-checked | `frame_problems` and `FRAME_COLUMNS` comments name the state and temperature checks | |
| ET-N3: the refusal test corrupts row 5 only | Rows 0, 5 and the last, each with all five values | |
| N-1: touching rods' widened shells interpenetrate, depth hides part of the front fade (model) | Recorded as a gap: ruling 7, the fringe shader's header, the research note and step 8's Remaining. No fixture yet | |
| N-5: fade over fade still in instance order | Open (NIT; at most 0.25 of the colour difference over sub-pixel patches, per the reviewer) | |
| P-N3: `area_findings` recomputes the ideal coverage (1.7 s a golden run) | Author proposes deferred, trigger: the golden job's time gets a B5 row or `golden_stability.py` next changes | |

## Delta round 2 folds

Statuses of delta round 1's findings are in `delta2_all.md`. Its new findings, and the open ones it named:

| Finding | Author's fold | Status |
|---|---|---|
| D2-1: the encoder's exact clip lives only in a comment | Step 7's checklist: the fuel encoder clips to exactly [−273.0, 6000.0], with a test against `FuelSnapshot`'s constants | |
| D2-2: §4.1's insertion figure predates the temperature loop | §4.1: 14.1–14.5 ms before ruling 9's loop, 18.7–21.0 ms after (loaded) | |
| D2-3: §3.2's per-frame check omits the temperature refusal | §3.2 names `surface_temperature_c` held to §3.3's clip (ruling 9) | |
| D2-4: N-1 recorded without numbers; "a gap"; §4.2 unqualified | Step 8's Remaining carries the model's numbers (39% of the front fade hidden, 10% of its core notched, the rear fade over the front core at 16–22%); ruling 7 reworded; §4.2 says "unless rods touch" | |
| D2-5: §7.4 "both rod passes"; §2's +0.24 ms row unlabelled | "the rod passes"; the row says two rod passes | |
| D2-6: two lines past 120 columns | Rewrapped | |
| ET-N1, N-3: bloom stated as the cause | "probably bloom; not separated by measurement" in `FADE_SHARE`'s comment and the note | |
| N-5: fade over fade unrecorded | Step 8's Remaining | |
| P-N3: trigger only in the fold table | Step 8's Remaining, with its trigger | |
