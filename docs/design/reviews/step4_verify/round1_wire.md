# Wire integrity review: phase1/verify (origin/main 814dea9 ... 3108b6e)

Reader: Wire integrity lens. Read-only. Ran: `scripts/lint_standards.py` (PASS, 0 findings);
`pytest -p no:cacheprovider tests/test_verify.py tests/test_heat.py tests/test_tooling_config.py --durations=8`
(90 passed, 393.7 s). I could not run ad-hoc measurement scripts (the sandbox refused them), so the numbers I cite
are from the tests' durations or are the author's, and I mark them that way.

Counts: **BLOCKER 2, SHOULD-FIX 5, NIT 7.**

## What I checked

| Contract | Producers (before → after) | Consumers (before → after) | Result |
|---|---|---|---|
| `simcore.verify` API vs `verify_harness.md` §3–4 | none → `runs.py`, `convergence.py`, `agreement.py`, `bands.py`, `splitting.py` | tests only | Types match field for field. `converges` departs from §4 (S1). |
| `converges(..., order_tol=)`, `reference_converged` | new | `test_heat_is_first_order_in_time`, `test_verify.py` | §4 says three runs suffice; code needs four. The one shipped consumer never reads the flag (S2) |
| `Run.dt_s` meaning ("physics step length", §3) | new | `test_cross_tier.py::_grids`, `test_act_validation.py` (the turn, 6 s) | The scenario tests pass the turn, not the physics step (S3) |
| `heat.step` return value and loop end | `elapsed < seconds - 1e-12` → counted `taken < planned`, replan on tightening | `World.advance` (returns it), `test_heat.py`, `test_validation.py:140` | Same count at small n; no other reader of the count. Sliver can come back on the replan path (N5) |
| Import layers contract | 4 layers → 5 (`simcore.verify` between game and protocol) | `pyproject.toml`, `test_tooling_config.py::test_the_layers_contract_orders_game_verify_protocol_adapters_core` | Agree. CLAUDE.md Layout still says 4 layers (S5) |
| `verify-measures-only` forbidden contract | new | `test_tooling_config.py::test_the_verification_harness_imports_nothing_from_the_engine` | Config agrees with the test. No planted-violation case (N3) |
| `tests/_imports.py` ALLOWED / EXTERNAL_NAMES | new `simcore.verify` rows | `test_input_allowlist.py` (exact-equality over grimp) | Agree with the code's imports (`__future__`, `collections.abc`, `dataclasses`, `itertools.pairwise`, `math.{inf,isfinite,log,nan}`); matches §2's list plus `__future__` |
| "Nothing in `src/` imports it" (§2) | claim | none | True today, unguarded: the layers contract lets `maxim_overdrive` import it (N4) |
| `MAXIM_OVERDRIVE_ALL_TIERS` (the 0.05 m grid's gate) | fast tier = 0.2, 0.1 m | `test_heat_is_second_order_in_space` | Runs 0.05 m in the fast tier, unmarked, 327 s (B1) |
| Bars, old → new | see the next section | | One lower edge widened (B2); the rest unchanged |
| Rule wording: CLAUDE.md, architecture.md, code_review.md, world_model §1.1 | resolution rule → verification rule | readers | Mostly agree; stale copies in CLAUDE.md, roadmap, architecture.md (S5, N6) |
| Claims in architecture.md | "1% / 0.1% / 0.01%" → "1.28% / 0.34% / 0.08%"; "each module ships two tests through `simcore.verify`" | readers | Damage's closed-form test does not go through `simcore.verify` (S4) |
| Word budget | architecture.md 2,829 → 2,829 words (`wc -w` at both revisions) | B24 | Holds. CLAUDE.md +35, code_review.md +23: not design documents. `verify_harness.md` new, 980 words (≤ 6,000) |
| TEMPORARY marker and step names | `heat.py` `TEMPORARY(phase1/sim-clock)`; design says "step 5a" | roadmap, `fire_solid.md` ("sim-clock = step 5a") | Consistent |

## Bars: each original against its replacement

| Test | Before | After | Verdict |
|---|---|---|---|
| `test_cross_tier.py::test_fire_outcomes_agree_across_rigs` | `max(onsets) - min(onsets) <= 0.1 * min(onsets)` | `onset.spread <= 0.1 * min(onset.values)`, plus `converging is not False` | Same, plus a check (a no-op in the fast tier, where it is None) |
| `test_cross_tier.py::test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig` (xfail strict, `raises=AssertionError`) | `abs(coarse - fine) <= TIME_TOL * fine`, FAST_SPACINGS = [0.2, 0.1] | `errors[0] <= TIME_TOL * values[-1]`, sorted coarse to fine | Same. `TIME_TOL` unchanged at 0.15 |
| `test_act_validation.py::test_the_fiercest_allowed_fire_...` (xfail strict) | `max - min <= 0.1` per turn; flame ≤ `WOOD_FLAME_C` | `spread <= 0.1`; flame unchanged | Same |
| `test_act_validation.py::test_a_strike_breaches_a_thin_wall_the_same_at_every_rig` | `len(set(...)) == 1` | `same_class(...)` | Same |
| `test_heat.py::test_gaussian_spreads_as_the_heat_equation_says` | `< 0.02` | unchanged | Same |
| `test_heat.py::test_error_falls_with_resolution` → `test_heat_is_second_order_in_space` | `fine < coarse / 4` at (0.2, 0.1): observed order **p > 2** | `abs(p - 2) <= (dx_coarse / sigma_t)**2` per pair | **Lower edge widened** at the 0.2/0.1 pair (B2) |
| → `test_heat_is_first_order_in_time` | none | `abs(p - 1) <= lambda * dt_coarse`, chosen after measuring, owner ruling (a) recorded in the docstring | New bar; ruled |

## BLOCKER

**B1. `tests/test_heat.py::test_heat_is_second_order_in_space` runs the 0.05 m grid in the fast tier, unmarked, and
took 327 s.** The gate contract is that the default `pytest` runs 0.2 m and 0.1 m, and 0.05 m comes in only under
`MAXIM_OVERDRIVE_ALL_TIERS=1` (`tests/conftest.py::ALL_SPACINGS`, CLAUDE.md Commands); anything over a few seconds is
`slow` and gated behind a tier variable (CLAUDE.md, Testing, a standing rule). This test hard-codes
`(0.2, 0.1, 0.05)` and runs the study twice, the second time at four times the substeps.
`test_a_step_takes_exactly_the_substeps_it_plans_however_many` took 39 s, also unmarked. Failure scenario: a
developer runs `.venv/bin/pytest tests/test_heat.py` as CLAUDE.md says ("run the module you touched first") and waits
six minutes, five and a half of them in one test the fast tier was never meant to hold. The machine was shared with
other sessions, so the absolute time may be inflated, but a 0.05 m study at 64× the stable substep count is slow
anywhere. Fix (unverified): in the fast tier run the 0.2/0.1 pair against the closed form (`exact` needs only two
runs) and keep the three-grid study and the quarter-step rerun under `ALL_TIERS` with `slow`; cut the 20,000-substep
case or mark it.

**B2. `tests/test_heat.py::test_heat_is_second_order_in_space` widens the old bar's lower edge without a recorded
owner ruling.** The old `fine < coarse / 4` at 0.2/0.1 m meant an observed order above 2. The new bar at that pair is
`|p - 2| <= (0.2 / sigma_t)**2`. With steel's diffusivity, sigma_t is about 0.42 m, so the tolerance is about 0.23
and the bar accepts p ≥ about 1.77, an error ratio of about 3.4 instead of 4. The author's own measurement, 1.93 at
that pair, would fail the old bar. CLAUDE.md (Testing, three kinds of bar): "re-deriving one never widens it without
the owner's ruling". The time bar's docstring cites owner ruling (a). The space bar's says only "set before
measuring". The new bar is better science: it is two-sided, and it catches the 3.23 cancellation the old one
rewarded, while the old bar was measured at a different step and mixed errors. That is the case to put to the
owner, though, and it doesn't replace the ruling. Failure scenario: a regression that drops the scheme's spatial
order to about 1.8 at 0.2/0.1 m, which the old gate would have caught, now passes. Fix: record the owner's ruling in
the test and the commit, or show the old bar still holds under its own conditions. Not a code change.

## SHOULD-FIX

**S1. `src/simcore/verify/convergence.py::converges` departs from its contract in `verify_harness.md` §4.** The
design gives `converges(observable, runs, *, exact=None)` and says the reference study "needs three runs", with
`reference_converged` judged "between the two finest pairs". The code adds a required `order_tol` keyword. It takes
Richardson orders from successive differences, so n runs give n − 2 orders, not §4's
`ln(e_coarse/e_fine)/ln r` per pair, and it sets `reference_converged` only when there are at least two orders,
which needs four runs. `test_verify.py::test_three_runs_give_one_order_and_never_claim_a_converged_reference` makes
the gap a tested fact. Failure scenario: step 5a's author writes a three-grid (0.2/0.1/0.05) reference study from the
contract. Every call returns `reference_converged=False`, so the test either fails for no physical reason or gets
rewritten to stop reading the flag. The design is the contract (CLAUDE.md, owner 2026-11-21), so update §4 with the
signature, the four-run minimum and the Richardson definition. With `exact`, `reference_converged` is hard-coded
`True` (N1).

**S2. `tests/test_heat.py::test_heat_is_first_order_in_time` computes `order_tol` and never reads
`reference_converged`.** §4 says the flag is what such a study "must give", and the docstring of
`_against_reference` says the same. The test passes `order_tol=decay_rate * runs[-2].dt_s` and then asserts only
`len(study.orders) == 2` and each order's band. Each order within `lambda·dt_i` of 1 does not imply that the two
orders agree within `lambda·dt_{-2}`. Failure scenario: the two Richardson orders come out 1.0 ± the per-order bands
but differ by more than `order_tol`. The harness reports an unconverged reference and the test passes anyway: the
harness's one consumer on the shipped path ignores the contract's key output. Fix (unverified): add
`assert study.reference_converged, study`.

**S3. `tests/test_cross_tier.py::_grids` and `tests/test_act_validation.py` label `Run.dt_s` with the turn (6 s), but
the physics step varies with the grid, so these are not space-alone studies.** §3 defines `dt_s` as "physics step
length". `World.advance` takes `max(heat.min_substeps(dx), ceil(6 / stable_dt))` substeps, and both terms scale as
1/dx² (the floor gives 4, 16 and 64). The heat step is 1.5, 0.375 and 0.094 s at 0.2, 0.1 and 0.05 m, so the
scenario tests refine space and time together. `_check_space_study` passes only because the label is constant.
Three documents now claim otherwise. CLAUDE.md: cross-grid tests "measured through `simcore.verify` with space and
time refined apart (... `tests/test_cross_tier.py` [is] the pattern)". code_review.md's Physics lens asks for it.
`verify_harness.md` §6: "The harness passes explicit step counts, so its studies don't depend on the floor", which is
true of the heat studies and false of these. Failure scenario: a reviewer holds new physics to the
`test_cross_tier.py` pattern, sees `_check_space_study` accept it, and approves a cross-grid test whose agreement
comes from space and time errors cancelling, the same E2 failure this branch fixed for heat. Fix (unverified): say
in the design and in CLAUDE.md that until 5a's fixed step the World scenarios co-refine time and the label is the
turn, or name the field for what it carries. Don't call `test_cross_tier.py` the pattern for space-alone
refinement.

**S4. `docs/architecture.md` ("The resolution rule") says "Each physics module ships two tests, through
`simcore.verify`".** Damage's closed-form crater test (`test_act_validation.py::test_a_crater_of_radius_at_least_a_third_of_a_metre_matches_the_closed_form_...`)
does not use `simcore.verify`, and §5 says on purpose that those tests "stay as they are". Separately, the heat
errors "1.28% / 0.34% / 0.08%" are the space study's, at 64× the stable substep count, not the errors on the shipped
step (`test_gaussian_spreads...` bounds those at < 2%). I did not reproduce the numbers: the sandbox refused the
script. They are consistent with the docstring's orders of 1.93 and 2.03. Failure scenario: a reader takes 0.34% as
the game's heat error at 0.1 m, or takes damage as verified through the harness. Fix: "heat's studies go through
`simcore.verify`", plus "at a time-converged step".

**S5. CLAUDE.md still states the old layering and rule outside the edited paragraph.** Layout: "game > protocol >
adapters > core" (the contract's name is now "game > verify > protocol > adapters > core"), and the Layout has no
`src/simcore/verify/` entry. Testing: "Physics: a closed-form test and a cross-tier test." `docs/roadmap.md` standing
rules: "**The resolution rule:** a rig changes precision, never the outcome class", which also contradicts D20 (a rig
has no physics), plus "a cross-tier test, under the resolution rule". Design §6 scoped the wording change to three
places. world_model §1.1 says the standing rules change, and the roadmap restates one. Failure scenario: a new session
reads CLAUDE.md's Layout, sees no harness and four layers, and writes cross-grid checks by hand, or reads the
roadmap's rule and believes rigs still differ in physics. Fix: update those lines. Docs only.

## NIT

**N1. `convergence.py::converges`** returns `reference_converged=True` with `exact` although nothing was measured.
The flag reads "converged" when it means "not applicable". Prefer `None` there, or document it in §3.

**N2. `agreement.py::_check_space_study`** compares `dt_s` with `!=`, while `convergence.py::_ratios` uses the
relative `_close` (1e-9). Two runs built as `Run(dx, T/n, n)` with float-computed steps can be one study to
`converges` and refused by `agrees`. Share `_close`.

**N3. `tests/test_tooling_config.py`** checks `verify-measures-only` by reading its config. No case in
`test_a_planted_violation_fails_the_gates_import_command` plants `from simcore.core import grid` in
`simcore/verify/...`, and the commits record no deletion proof for the contract. Fix (unverified): add a planted case.

**N4. `verify_harness.md` §2 says "Nothing in `src/` imports it"** but nothing guards it. The layers contract allows
`maxim_overdrive → simcore.verify`. Fix (unverified): a forbidden contract, or cite a backlog row.

**N5. `src/simcore/core/heat.py::step`, the replan.** `planned = taken + ceil((seconds - elapsed) / dt)` can
over-count by one when the remainder is an integer multiple of `dt` up to rounding, which brings back a planned
sliver substep on the destruction path, the class of bug this branch fixed on the main path. Harmless physically;
`taken` is the only reader-visible effect (`World.advance` returns it). The fix is a relative tolerance on the
quotient.

**N6. `docs/architecture.md`** keeps the heading "The resolution rule" and the Known gap "fire outcomes don't yet keep
the resolution rule", while CLAUDE.md renames it. Its new quote also drops "a spacing may change precision, never the
outcome class", which CLAUDE.md keeps. The word budget is held exactly (2,829 → 2,829), so the fix is a rename, not
added text.

**N7. `tests/test_cross_tier.py::TURN_S = 6.0`** duplicates `World`'s default `turn_seconds`. It is only a label
today (see S3), but it goes stale silently if the default changes. The fix is to read it from the world or drop it.

`band_gate` and `same_class_under_refinement` have no caller outside `test_verify.py`. That is consistent with §5,
which gives them no gate this step, so this is noted, not counted.

## Not found

- The import contracts, `test_tooling_config.py` and `_imports.py` agree on `simcore.verify` exactly.
- The strict red gates stay strict with `raises=AssertionError`, and their preconditions still raise `RuntimeError`.
- No other reader of `heat.step`'s count. The commit's bit-identity claim (determinism digests and a 500 kW burn) is
  the author's. I did not rerun it.
- `lint_standards.py`: PASS.
