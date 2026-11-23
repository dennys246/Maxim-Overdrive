# Delta round: Executor and Trust boundary, phase1/fuel-leftovers (uncommitted, against 2586ed7)

Reviewer: Executor + Trust boundary, delta after round 1's folds. I set each status from the tree, not from the fold
table's claims.

## What I ran

- `.venv/bin/pytest -q -p no:cacheprovider tests/test_golden_fuel.py tests/test_golden_stability.py
  tests/test_fuel_fixtures.py --cov=scripts --cov-branch`: 69 passed. `golden_fuel.py`, `golden_stability.py` and
  `fuel_fixtures.py` do not appear in the report, which skips covered files, so all three are at 100% line and branch.
- `.venv/bin/python scripts/godot_check.py`: `godot_check: PASS` on this tree (one run).
- **Client mutation runs.** I copied `client/` into my scratchpad with only `test_fuel_snapshot.gd` and
  `test_golden_shot.gd` kept, imported it, and ran `run.gd` headless with HOME and XDG moved into the scratchpad. The
  unmutated baseline gave `PASS 23 tests`. Each mutation below was applied alone, then reverted:

| Mutation | Result |
|---|---|
| `frame_problems` returns `[]` instead of `_temperature_problems()` | red: 5 failures (+inf, −inf, NaN, 6,004, −273.25) |
| `>=` MIN made `>` | red: "−273.0 °C, on the clip, passes" |
| `<=` MAX made `<` | red: "6000.0 °C, on the clip, passes" |
| condition rewritten as `t_c < MIN or t_c > MAX` (NaN passes) | red: 0x7e00 only |
| `TEMPERATURE_MAX_C` = 6500 | red: 6,004 refused, and "the maximum agrees" |
| loop checks row 0 only | red: 5 failures |
| `show_steady`'s rebuild guard can never fire (`<`) | red: "another structure rebuilds" |
| `show_steady` ignores a refusal | red: "a refused frame" |

  I checked the f16 bit patterns by hand: 0x6DDC is 6,000, so 0x6DDD is 6,004; 0xDC44 is −273, so 0xDC45 is −273.25.
  The test's comment is correct.
- **Python mutation runs.** A pytest plugin in my scratchpad patched the loaded `golden_fuel` module. To show the
  plugin was really applied: `_mean_y` set to 0 turned `test_a_fade_the_log_overwrote_is_found[rig,max]` red, and
  `FADE_SHARE` set to 1e-9 turned two tests red. Results for the measure itself are under ET-S1.
- `grep` for `back_to_front|use_view_direction|permute_` over `client`, `scripts`, `tests` and `client_objects.md`
  finds nothing. The sort is fully gone.

## Status of round 1 findings

| Id | Status | From the tree |
|---|---|---|
| E-S1 (centre sort misorders off-centre crossings) | **fixed** | The sort is removed. `fuel_rod_fringe.gdshader` splits the colour at coverage 0.5 (`fade_half`). `test_a_rods_colour_core_then_fade_…` pins the priorities [0, 1, 2, 3] and `fade_half` [default, true]. The crossing stick is 0.15 m off the log's centre, so the fixture no longer stacks the centres. The Linux deletion numbers (0.396 → 0.021) are the author's; I could not rerun Docker. |
| E-S2 (rebuild after a camera turn unguarded) | **fixed** (moot) | No view-dependent state remains. |
| E-S3 (transforms vs instance texture after permute) | **fixed** (moot) | No permutation. Instance i is geometry row i again. |
| E-S4 (fade bar fragile on rig/max, cannot fail on laptop) | **fixed** on rig/max; **deferred** on laptop (owner, ruling 8) | rig/max: the bar is 0.071, the deletion reads 0.021 (3.4× below the bar) and intact reads 0.396 (5.6× above). Laptop: excluded by `FADE_TIERS`, and `test_the_fade_is_not_judged_on_laptop` asserts that. Reason: the upscale smears the core into the band. Trigger: step 8's "Remaining" names "a laptop measure of the outer fade, freshly derived". The check no longer claims to guard laptop. |
| E-N1 ("linear on every tier") | **fixed** | `checklists.md` step 8 and §7.2 now say "rig and laptop". |
| E-N2 (`_show_next`'s guard never seen to fire) | **fixed** | `GoldenShot.show_steady` and `test_the_update_frame_must_reach_the_pass_steady` cover steady, rebuild and refused. I made the rebuild guard and the refusal branch fail in turn, and the test went red each time (table above). |
| TB-S1 (ruling 6 overclaims; decoder option missing; no trigger) | **fixed** | Ruling 6 now names exactly what was measured (llvmpipe, linear tonemapper, +∞) and says other tonemappers, NaN and other drivers were not measured. Ruling 9 adds the decoder refusal, so NaN and ±∞ can no longer reach the shader through `show_fuel`, and the need for a trigger lapses. The shader comment is narrowed to match. |
| TB-N1 (`use_view_direction` accepts an overflowing vector) | **fixed** (moot) | The function is removed. |
| TB-N2 (missing-`_next` and rebuild branches untested) | **fixed** | The rebuild and refusal branches are tested and proved (above). The missing-`_next` file goes through `fuel_usable`, whose missing-fixture branch `test_an_undrawable_fuel_fixture_is_refused` already covers. |

## The folds' new checks: do they fail when what they guard breaks?

- **Temperature refusal (`FuelSnapshot._temperature_problems`).** Every rejection path was proved red by the
  mutations above: +∞, −∞, NaN, just above the clip and just below it. Both inclusive edges were proved too, as was
  agreement with the shader's constants.
- **Validate, then mutate.** `FuelPass.show_fuel` still runs `frame_problems()` first and returns before any
  palette, rebuild or texture upload. The size check over `FRAME_COLUMNS` (which includes
  `segments.surface_temperature_c`) runs before `_temperature_problems`, so `decode_half` cannot read past a short
  column. The refusal is loud: it returns a message, and `golden.gd` and `RenderStage` surface it.
- **The server side agrees.** −273 and 6,000 are exact in f16, so a value the server clips in float64 and then casts
  can never land outside the client's range. A NaN survives `np.clip` and is now refused for the whole frame, which
  is the loud failure ruling 9 asked for.
- **`show_steady`** is proved (above).
- **The fade bar.** The bar's value is pinned (`test_the_fade_bar_is_half_the_coverage_models_share`, and the
  message string). An erased fade is refused on rig and max. Two gaps remain, below.

## New findings

### ET-S1 SHOULD-FIX: `scripts/golden_fuel.py::_fringe_findings` / `_mean_y`: nothing tests that the fade is measured in linear light

Ruling 8 says the bar is 1/14 *in linear light*, and the derivation (shares add in linear light) depends on that. But
no test pins `_mean_y`'s transfer function. I verified this by mutation, using the plugin above on
`tests/test_golden_fuel.py`:

- `_mean_y` replaced by `_mean_l` (L*): all tests pass.
- `_mean_y` replaced by luminance of the sRGB-encoded values, with no linearisation: all tests pass.

The synthetic band colour is MID = 140 between DARK = 30 and BRIGHT = 220. Its share is 0.35 in Y, 0.61 in L* and
0.58 in sRGB, so it clears 1/14 under every measure.

Failure scenario: a refactor drops the linearisation or routes the band through `_mean_l`, the helper beside it. On
the shipped llvmpipe frames, an L* or sRGB measure compresses dark-to-mid differences upward. A partly overwritten
fade could then read above 1/14 while its linear share is below it, and every test stays green.

Fix (the arithmetic is verified, the test is not written): add a synthetic case whose band is sRGB 60 over DARK 30
and under BRIGHT 220. Its linear share is 0.046, so it must be refused. Its L* share (0.18) and sRGB share (0.16)
would pass, so the case separates the three measures. A direct check works too, such as `_mean_y` of sRGB 188 ≈ 0.50.

### ET-N1 NIT: `research/fuel_antialiasing.md` (the D1 table): the measured intact share is 2.8× the model the bar is derived from, and the record doesn't say why

Ruling 8 derives the bar as half of the coverage model's 1/7 (0.143). The measured intact share on rig and max is
0.396, and the deletion reads 0.021 rather than the model's 0, which the code attributes to bloom. A model that
under-predicts its own measurement by 2.8× is not describing what the check measures. Saturation of the stick's core
compressing `core_gain`, or bloom adding to the band, are plausible causes, but neither was measured.

The bar still separates intact from deleted with good margins, so this is not a defect in the check. The risk is
different: the record presents 1/14 as derived from a model, and the measurement doesn't follow that model.

Failure scenario: a future change halves the fade's width, a partial break. It could still read well above 0.071,
because the measured share comes mostly from something other than coverage. A reader trusting "half the model's
share" would expect the check to catch a halving.

Fix: one sentence in the note saying intact measures 2.8× the model, with the suspected cause marked unmeasured.

### ET-N2 NIT: `client/addons/engine/render/fuel_snapshot.gd::frame_problems` docstring and the `FRAME_COLUMNS` comment are stale

The docstring still says the per-frame check holds "the columns … to their row counts' sizes … and state is 0 or 1".
The `FRAME_COLUMNS` comment still says "The rest change every frame and are only held to their size". Since ruling 9,
`surface_temperature_c` is also range-checked.

Failure scenario: a reader concludes that temperature is unchecked and adds a second check, or adds a new per-frame
f16 column assuming the size check is all that exists.

### ET-N3 NIT: `client/tests/unit/render/test_fuel_snapshot.gd::test_the_per_frame_check_refuses_a_temperature_outside_the_clip` edits row 5 only

An off-by-one that skips the last segment row (or the first five rows) would still pass. My "row 0 only" mutation
went red, but a `rows − 1` loop would not, because row 5 is not the last row. Setting the bad value on the last row as
well would close this. Unverified.

## Summary

| Id | Severity | One line |
|---|---|---|
| ET-S1 | SHOULD-FIX | "In linear light" is untested: swapping `_mean_y` for L* or for unlinearised sRGB leaves every test green (verified by mutation) |
| ET-N1 | NIT | Intact fade share 0.396 is 2.8× the model's 1/7 the bar is derived from; the record doesn't say why |
| ET-N2 | NIT | `frame_problems` docstring and `FRAME_COLUMNS` comment still say per-frame columns are only size-checked |
| ET-N3 | NIT | The temperature test edits only row 5; an off-by-one that skips the last row would pass |

Statuses: E-S1, E-S2, E-S3, E-N1, E-N2, TB-S1, TB-N1 and TB-N2 are fixed. E-S4 is fixed on rig and max, and deferred
on laptop by ruling 8, with the trigger in step 8's Remaining. No BLOCKER.
