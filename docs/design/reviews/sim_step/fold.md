# Step 5a PR 3 (`phase1/sim-laws`, unstaged on PR 2's fold): round 1 fold

Round 1 ran three readers, six lenses, on the unstaged PR 3 diff over 3b4c493: `round1_physics_exec.md` (Physics and
resolution, Executor), `round1_arch_wire.md` (Architecture, Wire integrity) and `round1_det_perf.md` (Determinism,
Performance). 0 BLOCKER, 10 SHOULD-FIX (one defect, the deposit cache after a rollback, reported by all three), 14
NIT. This table is the author's account. **Every status is "open (for the reviewer)"** until a reviewer reads it from
the tree (O25). Items marked **proposed, for the owner** change a contract's wording or defer work, and the owner
rules on each.

## How the rollback fix works (S1)

- **The defect.** `Deposit` keyed its solid weights on `(point_m, radius_m, topology_version)`. A window that rolls
  back restores `topology_version` with the cells, but the deposit lives outside the window, so it kept the entry it
  built inside. A different edit then reached the same version number and hit that entry: the reviewers measured
  75 W per cell landing in a destroyed (air) cell. Reachable on the shipped path whenever a physics step refreshes
  power after an edit (`substep_refine` > 1, or a replan) and a later substep raises.
- **The root.** sim_core §7 says a cache's contents are a function of state. After a rollback they weren't: the
  state went back, the cache didn't. A version number identifies a state only along one history, and a rollback
  starts a second history from the same number.
- **The fix.** `WindowOwner.on_roll_back(callback)` (`window.py`), beside `on_close`, registered at rest only: after
  `_roll_back` restores the saved state, and before the exception propagates, each listener runs. `Deposit.__init__`
  registers its `_forget`, which empties both caches, so every `Deposit` is safe, including one a test builds
  directly. The conductance and `stable_dt` caches §7 plans will use the same hook (checklist row below).
- **Why this one, not the alternatives.** A counter that never rewinds would keep stale entries until the next
  call's eviction and would make the cache's key differ from §7's "the values its result reads". Rolling the cache
  back with the window would need the deposit to become a window participant, a second saved state for one cache.
  The eviction keeps §7's key and its rule, and adds one case to it.
- **Proposed, for the owner:** sim_core §7's eviction sentence now reads "Replacing, removing or bumping evicts, and
  so does a window's rollback, which restores the version a later edit can reach again".
- **Proof.**
  - Red first: `tests/test_deposit.py::test_a_window_that_rolls_back_leaves_no_entry_a_later_state_could_reuse`
    failed before the fix (cached differed from fresh) and passes after.
  - The three reviewers' reproductions, rerun on the fixed tree:
    - `rollback_plant.py`: cached == fresh, max diff 0.0 W, 0.0 W into destroyed cell B;
    - `rev/plant_cache.py`: equal to the reference, max diff 0.0, cache keys empty after the rollback;
    - `rollback.py`: equal, 0.0 W into the destroyed cell.
  - Deleting the listener loop in a scratch copy turns the test red, and nothing else changes.

## Fold table

| # | Finding | Fold | Status |
|---|---|---|---|
| PE S1, AW S1, DP S1 | `deposit.py::Deposit.power`: a stale cache entry after a rollback | Above | open (for the reviewer) |
| PE S2 | Bar 3's plant can't show either half failing alone | `_splitting_holds` is now `_orders_agree` and `_each_order_refines`. `test_the_splitting_bar_fails_on_each_half_alone` runs three plants: both halves fail (the old pair); the order half alone (a source holding the crate at 1000 C, and a clamp that decides once per physics step, keyed on the grid and its `time_us`); the refinement half alone (a clamp on `dt < 3 s`). Each asserts which half fails. Deleting a half in a scratch copy (`bar3_halves.py`): with the refinement half gone, the refinement-only plant passes the bar; with the order half gone, the order-only plant does. So each deletion turns a test red | open (for the reviewer) |
| PE S3 | Bar 2b covers fewer scenarios than claimed; a `None` onset raises `TypeError` | Extended and narrowed. `_observables` adds the small fire (no catch at either refine, crate and wall over 0.99), and the gate runs on `ALL_SPACINGS`, so 0.05 m too under all tiers. Measured at 0.05 m: onset 89 and 90, crate 0.381 and 0.382, burn times 101 and 101, 121 and 122, peak 1039 and 1025 C. A `None` onset is now an assertion. The docstring and the commit message now say what it covers: this module's passing scenarios. The two strict red gates and act_validation's fiercest allowed fire fail their own bars at refine 4, so they have no margin to take a quarter of, and they join when their gates flip (checklist). Strikes run no substep. The reviewer's first-order plant wasn't rerun against the extension | open (for the reviewer) |
| PE N1, AW N2 (half) | `World.advance` accepts a step of 0 s or less, and time runs backward | Refused: "a positive whole number of microseconds". The test is parametrized over 1e-7, 0.0 and -1.0, and none counts a turn | open (for the reviewer) |
| PE N2, AW N2, DP N1 | The interval goes through a float; `of_ticks` isn't tied to it | Not changed. Deferred to PR 4, which retires `World.advance` (checklist row). Its trigger: `advance` goes | open (for the reviewer) |
| PE N3 | The replan trigger compares the bound with the refined dt | Fixed. It now triggers when `limit < dt * refine`, and splits the rest by the same rule, so after a replan every substep is at most bound / refine. Refine 1 is unchanged, so shipped bits are too. New test `test_a_replan_keeps_each_substep_within_the_bound_over_refine`; restoring `limit < dt` turns refine 2 and 4 red. **Proposed, for the owner:** §8's replan bullet now names the refined trigger | open (for the reviewer) |
| PE N4 | The test references share the new deposit | `test_deposit.py::_reference_overlap` freezes PR 2's whole-grid `sphere_overlap`. `_reference_power` uses it, and the 200-example Hypothesis test now also holds the new whole-grid overlap to it bit for bit. `test_laws.py::_reference_advance` still calls `World._power_field`. It is pinned through `test_deposit` rather than frozen in place | open (for the reviewer) |
| PE N5, AW N4 | Stale docs: the Known gap's 0.55, and fire_solid's "4, 16 or 64" | The Known gap now reads 0.539, 0.370 and 0.381 (6 s turn, refine 1). fire_solid's row reads "stability's count, no floor (5a PR 3)", with no words added | open (for the reviewer) |
| PE N6 | The replan test's docstring says "11 and one sliver" | Now: 11 even substeps for the rest, 20 in all | open (for the reviewer) |
| AW S2 | §6 says the applier appends every input; the registry says `simulation`; the appender is an unchecked string | §6 now reads "the applier; `Simulation` for `source_exposure`". `fields.APPENDERS = (APPLIER, SIMULATION)`, and `test_every_input_names_a_known_appender_and_it_is_a_core_module` holds each input to the vocabulary and each name to a `simcore.core` module | open (for the reviewer) |
| AW S3 | CLAUDE.md's layout and verification rule, and verify_harness §4 and §6, are stale | The layout adds `exposure.py` and `deposit.py`. The rule says the scenarios refine space alone at the fixed step and are held time-converged by bar 2b. verify_harness §4 and §6 say the same, in the past tense for the floor (no words added) | open (for the reviewer) |
| AW S4 | Three statements of where heat's `prepare` is deferred | One statement: the checklist's "Deferred from PR 3's review" block says PR 4, as the marker, the roadmap and `simulation.py` already did. The commit message no longer says "§5 defers it until a profile" | open (for the reviewer) |
| AW S5 | PR 3's deferrals aren't in the checklist | Added under step 5a, each with its PR: exposure in the digest and save; the exposure a raising step loses; the scenarios off the 6 s turn, and bar 2b's gates; frames' tick, bars 4–7, and `advance`'s interval; `prepare` and `bound_reads`; the two caches (proposed) | open (for the reviewer) |
| AW N1 | Deposit holds the exposure's types | `Source`, `Point`, `Share`, `Exposure` and `standing` moved to `exposure.py`. `deposit` imports them from there, and so do `world` and the tests | open (for the reviewer) |
| AW N3 | `exposure.py`'s docstring restates §3; §7 still says insertion order | The docstring links §3 as the energy rule's owner and keeps only what the module holds. §7's stale sentence is cut | open (for the reviewer) |
| AW N5 | `check_laws` skips the default tuple by identity | Now unconditional in `Simulation.__init__` and in `physics._group`, PR 2's identity case too. Its cost per physics step is a loop over three laws and five fields. The `pyproject.toml` line is unchanged (cosmetic) | open (for the reviewer) |
| DP S2 | §7's expected cost is false at PR 3, and bar 7 has no record | §7's prediction (0.7×, 1.4–1.6×) is replaced by the measurement, labelled as one: per 6 world seconds on the T3 tile, 0.88–0.96× at 0.1 m and 2.4× at 0.2 m with only the deposit cache, 42% `stable_dt` and 24% conductances at 0.1 m. The 0.35× and 0.75× with those caches are labelled an estimate. **Proposed, for the owner (checklist):** the conductance and `stable_dt` caches per `topology_version`, with the rollback eviction, in PR 4 and no later than the per-tick digest, since the digest's 1.7 ms per writing tick would take 0.96× to about 1.1×. The caches aren't built here | open (for the reviewer) |
| DP N2 | The share fraction is a float, while §3 says "in integers" | The `Deposit.power` docstring says the ticks are integers, the fraction is the energy rule's one float, and 2 in 5 holds only to rounding. §3 unchanged | open (for the reviewer) |
| DP N3 | Cached arrays are writable | The overlap and the weights are `readonly.frozen` when built. The bits are unchanged: the references and the strangler tests are green. `test_a_cached_entry_cannot_be_written` | open (for the reviewer) |

## Word budgets

`sim_core.md` stayed at 3,771 words against its index's 3,774: §6, §7 and §8 gained the amendments, and the cost
prediction, the insertion-order sentence and §8's floor-removal list came out. `fire_solid.md` and
`verify_harness.md` did not grow. `checklists.md` grew by the PR 3 block, the pattern PR 1 set.

## Checks run on the folded tree

- Clean: `ruff check` and `ruff format --check` on src, tests and scripts; `mypy`; `lint-imports` (10 kept);
  `lint_standards` (PASS, 21 by check and 27 in the backlog); `check_plan` (PASS).
- pytest on the touched and neighbouring modules: 1,076 passed, 1 skipped and 6 xfailed (the strict gates).
- Bar 2b at 0.05 m under all tiers: passed.
- Branch coverage of the changed core modules: 100%. The one miss is `world.py:69`, unchanged.
- PR 3's recorded break is unchanged: the strangler tests hold the tuple to the reference byte for byte at the
  floor's count, and the refine 1 break test is green.
- The full gate (`prepush.sh`) wasn't run: the tree is unstaged and dirty by design.
