# PR 4a (`phase1/sim-replay`) delta round 5: the delta-4 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay.

**Reviewed:** `git diff 94ca301 a1d22ff` (the delta-4 fold `8c032c5` and its follow-up `a1d22ff`), both commit
messages, `delta4.md`, and the "Delta 4" table at the end of `fold.md`. I set every status from the tree, not from the
table.

**How it was run:** I used a copy of `a1d22ff` at `<scratchpad>/delta5/tree`. `diff -rq` against the worktree was
clean apart from caches, before and after the mutations. The interpreter was the worktree's venv under `-I`, with the
copy's `src` and root first on `sys.path`. `simcore.__file__` resolved into the copy.
- **Tests:** `test_simulation`, `test_ownership` and `test_input_allowlist` gave 229 passed. `test_constructors`,
  `test_frames`, `test_act_validation`, `test_imagination`, `test_sem_bridge`, `test_exposure`, `test_laws`,
  `test_validation` and `test_determinism` gave 669 passed, 1 skipped, 5 xfailed and 1 failed. The failure is
  `test_every_shipped_data_file_is_at_its_formats_current_version`, which runs `git ls-files` and fails because the
  copy is not a repository. It is an artefact of the copy.
- **Static checks:** mypy (strict, from `pyproject.toml`) is clean on `grid.py`, `simulation.py`, `test_simulation.py`
  and `test_ownership.py`. Ruff check and format are clean on the four changed Python files. After a throwaway
  `git init` (removed afterwards), `scripts/lint_standards.py` gave PASS with 0 findings.
- **Mutations:** five, each restored and checked with `filecmp` against the worktree. They are listed under the rows
  they prove.
- **Scripts:** in `.worktrees/_durable/sim_tick_review/delta5_scripts/`: `run_tests.sh`, `mutate.py`,
  `rename_adopt.py`, `probe_warm_site.py` and `probe_owned_calls_reach.py`.
- **Not run:** the full suite, the 0.05 m tier, import-linter and the gate. I did not check whether
  `prepush: PASS a1d22ff` exists. The author's own message says `8c032c5` alone was red on two allowlist tests;
  `a1d22ff` makes them pass here.

## Counts

**New findings: 0 BLOCKER, 0 SHOULD-FIX, 3 NIT.**

**Statuses set (4 rows; the second covers two ids):** D4-N1 fixed, D4-N2 and Arch S5 deferred (I confirm the
author's status, with one caveat on the charter's wording), D4-N3 fixed, D4-N4 fixed (caveat D5-N1).

**Differs from the author:** nothing. Three rows were "open (for the reviewer)" and I set them fixed. D4-N2's
deferral was the author's, and I confirm it.

## New findings

### D5-N1 (NIT). The `adopt` entry in `OWNED_CALLS` has no non-vacuity check, so renaming the method leaves it guarding nothing
**Where:** `tests/test_ownership.py::OWNED_CALLS`,
`tests/test_ownership.py::test_only_each_writers_owner_narrows_claims_or_names_its_token`.

The scan keys on the string `"adopt"`. The planted case also spells `adopt`, so it stays red-capable whatever the
method is called. The full-tree test checks that it is not vacuous only for `as_writer` in `topology.py`. Nothing ties
the entry to the name `CellStore` actually defines.

*Scenario (verified, `rename_adopt.py`):* rename `CellStore.adopt` to `take_cells` and its one call in
`Simulation.__init__`. Then `test_ownership.py` and `test_simulation.py` give 144 passed. The entry now holds a name
that no code has, and a stray `grid.take_cells()` in `world.py` or a loader would pass the scan. That is D4-N4's
scenario, which the fold aimed to close. The failure would still be loud at runtime, which is why this is a NIT. The
same gap exists for `claim` and `constructing`; this diff adds one more entry of that kind.

*Fix (verified as a probe, `probe_owned_calls_reach.py`):* for each `OWNED_CALLS` name, assert that at least one owner
module calls it. On the tree, all four names are found in an owner. After the rename, the probe prints
`adopt: called in NO OWNER`. Turning the probe into an assertion in the full-tree test would make it go red.

### D5-N2 (NIT). The new PR 4b row is filed under "Deferred from PR 3's review"
**Where:** `docs/plans/checklists.md`, Step 5a, the bullet group "Deferred from PR 3's review
(`reviews/sim_step/fold.md`), each to the PR that owns it".

The row comes from PR 4a's review (`reviews/sim_tick/`, round 1 Arch S5 and delta 4 D4-N2). The group's heading names
PR 3's review and its fold file.

*Scenario:* a PR 4b author lists what PR 4a deferred to them. They look for a "Deferred from PR 4a's review" group
(the pattern that groups PR 1, 2 and 3), find none, and miss this row and the two earlier PR 4a rows already filed in
the same group (the refused `place`, "PR 4a delta", and the raising publication, "PR 4a delta 2"). The row's own text
cites its source, so a search for "D4-N2" or "Arch S5" still finds it. This diff didn't start the misfiling, but it
adds to it.

*Fix (unverified):* add a "Deferred from PR 4a's review (`reviews/sim_tick/fold.md`)" group and move the three PR 4a
rows into it.

### D5-N3 (NIT). `__deepcopy__`'s docstring gives the shallow copy's reason, which a deep copy doesn't have
**Where:** `src/simcore/core/grid.py::CellStore.__deepcopy__`.

The docstring says "Refused, as `__copy__`: one owner per set of cells." A deep copy shares nothing. It would be a
second set of cells, with its own versions and gate. The hazard it would carry is D4-N2's: a stepped grid's state
entering a new `Simulation` and being published as frame 0. It would also skip the scene, which would leave the
regions out. Before the fold, `copy.deepcopy` already failed incidentally on the `mappingproxy`. The refusal is
consistent with the design, but the stated reason is wrong. The error message, "build a new grid from its scene", is
the right instruction for both copies.

*Scenario:* a PR 4b author who wants a deep-copy fork for a save reads "one owner per set of cells" and decides that
a deep copy is a new owner, so the refusal must be overcautious. They remove it. The real reason, frame 0, is written
only in the PR 4b checklist row.

*Fix (unverified):* say that a deep copy would carry a stepped state into a new simulation's frame 0 (§3, the PR 4b
row), and that a grid comes from its scene.

## Checked, not findings

- **The copy refusal on shipped and tested paths.** I searched `src/`, `tests/`, `scripts/` and `spikes/` for
  `copy.copy`, `deepcopy`, `import copy`, `pickle`, `dataclasses.replace`, `asdict`, `astuple`, `copy.replace` and
  `__reduce`/`__getstate__`. None of the hits copies a grid or anything that holds one:
  - `test_formats` deep-copies YAML samples.
  - `test_validation` copies `DataPath`.
  - The `dataclasses.replace` calls in `test_frames`, `test_constructors` and `test_validation` act on `CellFrame` and
    material rows. `CellFrame` holds arrays, not the grid.
  - The `copy`, `replace` and `astuple` calls in the spikes act on spike-local dataclasses.

  Pickling is banned by `lint_inputs`. The 898 tests I ran include every `MaterialGrid` construction path (`Scene.build`,
  `MaterialGrid.empty`, `paint`, `name_region`, the imagination voxelizer), and they pass. Construction never copies
  the store. Its `.copy()` calls are numpy array copies.
- **`TypeError`** is the type `copy` itself raises for an object it can't copy (`cannot pickle ...`), and it is
  distinct from `adopt`'s `ValueError`. A caller can't mistake a copy refusal for an ownership refusal.
- **Annotations.** `-> NoReturn` and `memo: dict[int, object]` pass mypy strict with `warn_unreachable`. `copy` declares
  no `__copy__` on `object`, so there is no override conflict.
- **Size limits.** `lint_sizes` counts a class's public methods as the `def`s whose names don't start with `_`.
  Dunders are excluded, so `CellStore` stays at 11 of 12. `lint_standards` passes.
- **Remaining routes.** A subclass that overrides `__copy__`, `object.__new__` plus `__dict__.update`, and
  `copy._reconstruct` on `__reduce_ex__(4)` still copy a grid. All are deliberate, and no shipped code uses one. As
  delta 4 said of subclassing, no guard inside the core can stop them.
- **The retry test (D4-N1).** `probe_warm_site.py` shows that `World` accepts the source at (50, 50, 50). The refusal
  then raises from `Simulation.__init__` → `physics.warm` → `heat.warm` → `deposit.keep` → `geometry.cell_of`, with
  `grid._adopted` still `False`. So the `warm` case does refuse in `warm`, after `Physics` and `CellFrame.of`.
- **`OWNED_CALLS`'s reach.** The scan walks all of `src/` (adapters, protocol, game included) by call name. Today only
  `simulation.py` calls `adopt`, and nothing else in `src/` defines or calls a method of that name, so the scan flags
  nothing it shouldn't. `tests/` is not scanned, so test helpers that would adopt are unaffected. An unrelated future
  `adopt` method elsewhere in `src/` would be flagged. That would be loud, and it is the same trade the entries `claim`
  and `as_writer` make.
- **`tests/_imports.py`.** `typing.NoReturn` is used in the core only by `grid.py`'s new import.
  `test_input_allowlist.py` passes, including `test_each_name_list_names_exactly_what_its_layer_uses_today`, so the list
  names exactly what the layer uses. The reflow moves no other name.
- **Determinism and replay.** The diff changes no state the simulation reads. The copy refusal removes D4-N3's route,
  where one simulation's work counters depended on another simulation's steps.
- **Wire integrity.** No producer or consumer outside the hunks copies a grid, a `World` or a `Simulation`. A
  `copy.copy(world)` shares its grid, so a second `Simulation` over it is still refused by `adopt`. A
  `copy.deepcopy(world)` now raises the intended `TypeError` rather than the incidental `mappingproxy` one.
- **Out of the diff's scope:** `spikes/slice/tests` fails against the branch's `simcore` (`World.from_scene` no longer
  exists). This dates from `336eee8`, earlier in PR 4a, is not on `testpaths`, and is not caused by this delta.

## The PR 4b checklist row against D4-N2

The row matches D4-N2's scenario and numbers: a lit crate, run to tick 20, 28.6 °C, published at tick 0. It cites
round 1 Arch S5 and delta 4 D4-N2. It names the contract in §3 ("publishes the authored world"), it puts the work on
the loader ("states its tick and what frame 0 is for a loaded state"), and it asks for a test. The trigger is PR 4b's
loader, through the row's `PR 4b:` prefix. The row omits D4-N2's side note that a rebuilt grid carries no regions.
That note is about the fork's fidelity, not the frame-0 rule, so I don't count it as a gap.

**Caveat on the charter.** `docs/code_review.md` step 4 allows a code finding to be deferred only as a
`TEMPORARY(phaseN)` marker, and a finding with no code to mark only as a backlog row or a known gap. Arch S5 was a
SHOULD-FIX. The constructor that accepts the state is code. What is missing, though, is PR 4b's loader contract, not a
band-aid in PR 4a to mark. Delta 4 proposed exactly this checklist row as the deferral route. The plan already defers
the earlier SHOULD-FIX rows for PR 4b and PR 4a the same way. I accept the deferral on that practice. If the owner reads
step 4 literally, the row would need a marker on `Simulation.__init__` too.

## The fold.md Delta 4 section against delta4.md

The section claims 0 BLOCKER, 0 SHOULD-FIX and 4 NIT; delta 4 counts the same. It claims 9 fixed and 1 open of delta
3's rows, with D3-S1 and D2-S1 fixed and Arch S5 open, as D4-N2; delta 4's table matches. It says delta 4 found no
route to two simulations except a copy, which matches delta 4's "Checked" section and D4-N3. Each fold cell matches
the diff. The commit message's "run: 1 failed" for D4-N1, D4-N3 and D4-N4 matches my mutations below.

## Status table

| id | status | evidence |
|---|---|---|
| D4-N1 | fixed | The retry test is parametrized over `law-tuple` and `warm`. With `adopt()` moved to just after `Physics(...)` (`mutate.py after_physics`), the result is 1 failed: `[warm]`, at the retry line (`test_simulation.py:168`, `adopt` raising "already have their simulation"). The first construction's refusal comes from `physics.warm` (`probe_warm_site.py`). With `adopt()` moved before `Physics(...)` (`adopt_first`), the result is 2 failed, both cases. |
| D4-N2, Arch S5 (residual) | deferred (confirming the author's; reason: the loaded tick and frame 0 are PR 4b's loader contract; trigger: PR 4b's loader) | `docs/plans/checklists.md`, Step 5a, a `PR 4b:` row citing Arch S5 and D4-N2, with the measured scenario (tick 20, 28.6 °C, published at tick 0), §3's rule, and a test. The constructor still accepts the state, as the row says. See the charter caveat above, and D5-N2 for where the row is filed. |
| D4-N3 | fixed | `CellStore.__copy__` and `__deepcopy__` raise `TypeError`. With both deleted (`mutate.py no_copy`), the result is 1 failed, `test_cells_are_never_copied_...`, with "DID NOT RAISE TypeError" on `copy.copy`. Deleting only `__deepcopy__` would also go red: the incidental `mappingproxy` `TypeError` doesn't match "cells are not copied". No shipped or tested code copies a grid. See D5-N3 on the docstring. |
| D4-N4 | fixed | `OWNED_CALLS["adopt"] = {"simcore/core/simulation.py"}`. The full-tree scan passes. With the entry deleted (`mutate.py no_owned_adopt`), the result is 1 failed, `test_the_token_scan_catches[adopt]`. Caveat D5-N1: renaming the method leaves the entry vacuous, with 144 passed. |
