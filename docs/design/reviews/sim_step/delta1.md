# Step 5a PR 3: delta round 1 (all six lenses)

Reviewer: independent; Physics and resolution, Executor, Architecture, Wire integrity, Determinism, Performance.
Tree: unstaged changes plus untracked files in `.worktrees/sim-laws` on HEAD 3b4c493. I edited nothing there; every plant
ran in a copy (`scratchpad/delta1/tree`).

**Counts: 0 BLOCKER, 0 SHOULD-FIX, 4 NIT (new). Round 1: 17 fixed, 1 deferred (accepted), 0 rejected, 0 open.**

## Status table

| # | Finding | Status | Read from the tree |
|---|---|---|---|
| PE S1, AW S1, DP S1 | stale deposit entry after a rollback | **fixed** | `window.py::WindowOwner.writing` calls the `on_roll_back` listeners after `_roll_back`; `Deposit.__init__` registers `_forget`. All three reproductions read equal, 0.0 W in the destroyed cell. Deleting the loop turns exactly one test red. See §2 |
| PE S2 | bar 3's plant can't separate its halves | **fixed** | `_orders_agree` and `_each_order_refines`, plus three plants that assert which half fails. Each half's deletion turns one plant's final `not _splitting_holds` red |
| PE S3 | bar 2b covers less than claimed; `None` onset raises `TypeError` | **fixed** | small fire added; `ALL_SPACINGS`; `None` onsets are assertions; docstring and message narrowed. I reran your first-order plant (`b2b.py`) on the extended gate: RED at 0.2 m (onset moved 5 against a bar/4 of 2.25) and at 0.1 m (precondition). Bar 2b at all tiers: 3 passed |
| PE N1, AW N2 (half) | `advance` accepts a step of 0 s or less | **fixed** | refuses `interval_us <= 0`; parametrized test at 1e-7, 0, −1, no turn counted. Residual in N-c below |
| PE N2, AW N2, DP N1 | float interval; `of_ticks` not tied to it | **deferred** (accepted) | Reason: exact for every `SimConfig` below 2⁵³ µs, and `Simulation` is the only caller and derives both from one config. Trigger: PR 4 retires `World.advance` (checklist row present) |
| PE N3 | replan trigger compares the bound with the refined dt | **fixed** | `limit < dt * refine`, and `more = refine * ceil(...)`. Restoring `limit < dt`: refine 2 and 4 red. Dropping `refine *` from `more`: the same two red. Refine 1 unchanged |
| PE N4 | test references share the new deposit | **fixed** | `_reference_overlap` is PR 2's `sphere_overlap` body (diffed against `pr2/`: only the signature and docstring differ). `_reference_advance` reaches `Deposit` through `_power_field`, pinned transitively |
| PE N5, AW N4 | stale Known gap and fire_solid row | **fixed** | 0.539 / 0.370 / 0.381, 137/104 |
| PE N6 | "11 and one sliver" | **fixed** | |
| AW S2 | §6 against the registry; unchecked appender | **fixed** | `fields.APPENDERS`, held by a test to the inputs and to `simcore.core` modules |
| AW S3 | CLAUDE.md, verify_harness §4 and §6 stale | **fixed** | the layout lists `exposure.py` and `deposit.py`; the verification rule and verify_harness §4 and §6 name space-alone and bar 2b; verify_harness shrank |
| AW S4 | three statements of `prepare`'s deferral | **fixed** | the checklist, `simulation.py`, the marker, the roadmap and the message all say PR 4. They agree, though "the one statement" is loose: four places still state it |
| AW S5 | deferrals not in the checklist | **fixed** | "Deferred from PR 3's review" block, each row with its PR |
| AW N1 | exposure types in deposit | **fixed** | moved to `exposure.py`; `deposit` imports them |
| AW N3 | docstring restates §3; §7 says insertion order | **fixed** | |
| AW N5 | `check_laws` identity special case | **fixed** | unconditional in `_group` and `Simulation.__init__` |
| DP S2 | §7 cost false; bar 7 unrecorded | **fixed** (record), with the caches' deferral ruled in §3 | §7 now carries the PR 3 measurement, labelled as one, and the estimate is labelled as an estimate |
| DP N2 | the fraction is a float | **fixed** | `Deposit.power` docstring |
| DP N3 | cached arrays writable | **fixed** | `frozen` on both; `test_a_cached_entry_cannot_be_written` |

## Checks run (working tree)

- pytest on deposit, exposure, simulation, heat, laws, determinism, fields, cross_tier, act_validation, ownership,
  tooling_config, validation, frames and damage: **737 passed, 1 skipped, 6 xfailed**. Bar 2b under
  `MAXIM_OVERDRIVE_ALL_TIERS=1`: 3 passed (0.2, 0.1, 0.05 m).
- ruff check and format: clean. mypy: clean (109 files). lint-imports: 10 kept. lint_standards: PASS (21 checked, 27
  backlog).
- Word budgets: sim_core 3,771 against 3,774 in the index; fire_solid 5,969 → 5,964; verify_harness 1,241 → 1,240.

## 2. The rollback fix

- **Reproductions, rerun on the working tree:** `rollback_plant.py` gives cached == fresh, max diff 0.0 W, 0.0 W in
  cell B. `rollback.py` gives equal, 0.0 W into the destroyed cell. `rev/plant_cache.py` gives equal to the reference,
  max diff 0.0, cache keys `[]` after the rollback. Two needed one import edit first (`standing` moved to `exposure`, AW N1); the edited copies are in
  `scratchpad/delta1/`.
- **Deletion proof, verified:** with the listener loop removed from `window.py` in the copy, the only failure is
  `test_a_window_that_rolls_back_leaves_no_entry_a_later_state_could_reuse` (61 others passed).
- **Soundness:** `topology_version` has one writer, the commit's `+=`, and one restorer, `_roll_back`. Clearing everything is conservative: entries at
  versions at or below the restored one would still be valid. The sources-only window (`holding`) rolls nothing back
  and changes no topology, so it needs no hook.

## 3. Rulings on the three "proposed, for the owner" items

1. **§7 rollback eviction: accept.** A rewound version names two states, so either the key changes or rollback evicts.
   A never-rewinding epoch breaks §7's key rule and the eager build on load; a window participant adds a second
   saved state. The eviction is the smallest correct rule, and PR 4's caches inherit it. Wording caveat:
   N-a.
2. **§8 refined replan trigger: accept.** Before the fix, a refine-4 run could keep substeps of up to 1.7 × bound/4
   after a tightening, so a refinement study compared a refined run that wasn't a refinement of a stable step. With
   `limit < refine·dt` and `more = refine·ceil(rem/limit)`, every later substep is at most bound/refine (up to an
   ulp). Refine 1 is byte-identical, so shipped digests don't move. Both halves are guarded (two plants, both red).
3. **`stable_dt` and conductance caches deferred to PR 4, no later than the digest: accept, with a condition.**
   Reason: §5 ties `stable_dt`'s cache to `bound_reads`, which is PR 4's, so building it now would mean building it
   twice. PR 3 doesn't regress the shipped path (0.88–0.96× at 0.1 m). Condition: bar 7 is measured in PR 4 with the digest in and both caches in,
   and the PR doesn't hand off if 0.1 m exceeds 1.0×. The row says "no later than the digest", which implies this;
   make it explicit when PR 4's checklist is cut. The 0.2 m 2.4× is recorded and not gated, as §11 row 7 says.

## 4. New findings

**N-a. `docs/design/sim_core.md` §7, the proposed eviction sentence: "So a cache's contents are a function of state"
doesn't follow from the new rule.**
- After a rollback the cache is empty. The same state reached without a rollback, or rebuilt eagerly on load, holds
  that state's entries. That was already loose between a bump and the next call (old-version entries sit there), and
  the rollback makes it plainly untrue.
- What stays true is that every hit equals the uncached path.
- Failure scenario: PR 4's bar 6 holds `WorkCounters` "identical on replay", and the eager build "reproduces them on
  load". A session that rolled back once rebuilds lazily, while its save reloaded builds eagerly, so their rebuild
  counts differ, and a reader of §7 expects them equal.
- Fix (unverified): word it as "a cache's hits are a function of state", or state what a rollback leaves for PR 4's
  counters.

**N-b. `src/simcore/core/window.py::WindowOwner.writing`: a rollback listener that raises replaces the window's
exception and skips the later listeners.**
- Failure scenario: PR 4 adds the conductance and `stable_dt` listeners. If the first raises, the later caches keep
  their rewound-version entries, and S1 recurs for them: an unstable `stable_dt` with no error.
- Fix (unverified): state in `on_roll_back`'s docstring that listeners must not raise, or run every listener before
  re-raising.

**N-c. `src/simcore/core/world.py::World.advance`: `seconds = inf` raises `OverflowError` from `round`, not the
step's refusal.**
- `nan` gives numpy's `ValueError`, not the refusal message.
- Verified: nothing is applied (`time_us` 0, turn 0), so this is only the error's type and message.
- It's interim: PR 4 retires `advance`, and `Simulation` passes only finite intervals.
- Fix: check `finite_real` first, or let it go with `advance`.

**N-d. `tests/test_deposit.py::test_a_window_that_rolls_back_…`: the red-first test drives a bare `Deposit` through
`constructing`, not the shipped sequence.**
- The shipped sequence: `Simulation.step` with `substep_refine` > 1, a physics step that raises after an editing
  substep, then a strike before the next physics tick.
- The hook lives in the one `WindowOwner.writing` every window uses, so the code path is the same. But no test shows
  the shipped path reaching it.
- Optional: one `Simulation`-level test.

## Commit message

The claims I re-measured hold (rollback deletion proof, the replan plant, bar 2b at three spacings, the frozen
reference, the 1/5 strangler test). The fold table's author statuses are superseded by this table.
