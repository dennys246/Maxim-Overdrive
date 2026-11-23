# PR 4a (`phase1/sim-replay`) delta round 6: the delta-5 fold, the spike pin and the marker, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay.

**Reviewed:** `a1d22ff..ef4c5c8`, which is three commits.
- `9e3536a`, the delta-5 fold. I read it against `delta5.md` and the "Delta 5" table in `fold.md`.
- `79b5d91`, the merge of origin/main (#47, #50, #51, #54). I read its message, `git diff 79b5d91^1 79b5d91` for the
  spike, `git diff c6d4f10 79b5d91 -- spikes/specgen`, and `git show --remerge-diff 79b5d91`.
- `ef4c5c8`, the owner-ruled marker.

I set every status from the tree, not from the table.

**How it was run:** on a copy of `ef4c5c8` at `<scratchpad>/delta6/tree`. `diff -rq` against the worktree was clean
apart from caches, before and after. The interpreter was the worktree's venv under `-I`, with the copy's `src` and its
root first on `sys.path`, and `simcore.__file__` resolved into the copy. I extracted `c6d4f10` with `git archive` into
`<scratchpad>/delta6/c6d4f10`. Both copies needed a throwaway `git init` and commit, because `generate.py`'s run header
runs `git rev-parse HEAD`, and 10 spike tests fail without one. I removed both `.git` directories afterwards.
- **Scripts:** in `.worktrees/_durable/sim_tick_review/delta6_scripts/`: `run_tests.sh`, `run_spike.sh`, `mutate.py`,
  `mutate_roadmap.py`, `merge_sides.sh`, `probe_place_parity.py`, `probe_m5_port.py` and `probe_deepcopy_adopted.py`.
- **Tests:** `test_ownership.py` and `test_simulation.py` gave 148 passed.
  - `spikes/specgen/test_spike.py` on the copy gave 1 failed and 64 passed. The failure is M5, with the guard's
    `RuntimeError: M5 runs on the engine as of c6d4f10 ...`, as expected.
  - On `c6d4f10` it gave 65 passed. The branch's own `burn.py`, imported against `c6d4f10`'s `src`, passes the M5 test
    (1 passed, 64 deselected).
- **Lint:** `scripts/lint_standards.py` on the copy gave PASS with 0 findings.
- **Not run:** the full suite, import-linter, mypy, ruff and the gate. I did not check that `prepush: PASS ef4c5c8`
  exists.

## Counts

**New findings: 0 BLOCKER, 1 SHOULD-FIX, 3 NIT.**

**Statuses set (3 rows):**
- D5-N1: fixed.
- D5-N2: fixed.
- D5-N3: **open**. The new docstring replaces one wrong reason with another; see its row.

**Differs from the author:** the table leaves all three "open (for the reviewer)". I set D5-N3 open, not fixed. The
merge message's premise for the owner's pin is contradicted by a measurement (D6-S1). The owner should see that before
anything else in this round.

## New findings

### D6-S1 (SHOULD-FIX). E18's reason for the pin is false: M5 ported to `Simulation` reproduces `c6d4f10` bit for bit
**Where:** `spikes/specgen/errata.md::E18`, `spikes/specgen/burn.py::burn`, and the merge message of `79b5d91`.

E18 and the merge message both justify the pin with the same claim: "Porting M5 to `Simulation` would change its turn
to T3's 0.5 s physics step and move a pre-registered metric." The owner ruled on that premise. It is false. `SimConfig`
is not fixed at T3. A port can keep a 6 s physics step with either `SimConfig(tick_us=6_000_000, physics_every=1)` or
`SimConfig(tick_us=1_000_000, physics_every=6)`.

*Scenario (verified, `probe_m5_port.py`):*
- **The run:** four accepted specs on the 0.1 m truth grid: the spike's `crate`, the two-part `stool`, a plank and a
  cylinder drum. Each gets `Ignite(100 kW, 0.3 m)` and 30 turns of 6 s.
- **The two engines:** on `c6d4f10`, `burn.py`'s own body (`Applier(world).apply`, then `world.advance(6.0)`). On the
  branch, `Simulation(world, config=...)`, with the ignite as a `LogRecord` at tick 1.
- **What was recorded:** the solid-in-sphere count and `repr(region_integrity)` after every turn.
- **The result:** `cmp` reports the two JSON outputs identical for both configs.
- **It can tell them apart:** integrity moves, to 0.99844 for the crate and 0.56313 for the plank at turn 30.

So the port does not move the metric, at least for these specs and the quantities M5 reports. Temperatures were not
compared, and M5 doesn't report them.

The pin has costs that the ruling weighed against a move that doesn't happen:
- M5 cannot run on `main` once PR 4a merges.
- The M5 run must use a `c6d4f10` worktree. That freezes all of the spike's code there, not only the engine (see
  D6-N1).
- The spike's test suite stays red on the branch (D6-N2).

*Fix (verified as a probe; I did not run a ported `burn.py` under `test_spike.py`):* port `burn` to `Simulation` with
a 6 s physics step, keep `TURN_S = 6.0` as the step's length, and replace E18's reason with the measured equivalence.
**For the owner** to rule again. Re-pinning stays possible if the owner prefers it on other grounds.

### D6-N1 (NIT). The guard doesn't test "the engine as of `c6d4f10`", and the pinned run takes the spike's code with it
**Where:** `spikes/specgen/burn.py::burn` (`hasattr(World, "advance")`), `spikes/specgen/errata.md::E18`.

E18 says M5 runs "on the engine as of `c6d4f10`". The guard tests only whether `advance` exists.

*Scenario:* the engine has already moved without the guard noticing. `git rev-parse c6d4f10:src` is `970001b`, but
origin/main's `src` is `6524f6a`; the difference today is a docstring in `limits.py`. A physics change merged to main
before PR 4a would also pass the guard, and M5 would run on an engine E18 doesn't name.

The opposite side of the pin has its own drift. E18 says to run M5 "from a worktree at that commit". That runs
`c6d4f10`'s `score.py`, `protocol.py` and `burn.py`. So any spike fix merged after `c6d4f10` (the kind `code_delta1.md`
records as "a late fold before the first run") is absent from the M5 run.

Run headers record `simcore_commit` and `src_tree`, but `score.py` compares only `data_sha256`. Nothing ties a scored
run to the engine M5 burns on.

*Fix (unverified):* moot if D6-S1's port lands. Otherwise, check `src_tree` against `c6d4f10`'s, and say in E18 which
files the pinned worktree must carry.

### D6-N2 (NIT). The M5 test is left red, not a strict red gate, so nothing holds the guard
**Where:** `spikes/specgen/test_spike.py::test_m5_burns_an_accepted_spec_at_turns_of_6_s`.

On the branch, the test fails with the guard's `RuntimeError`. No test asserts that the guard fires, so a change that
broke it would go unnoticed. CLAUDE.md's rule for known-broken behaviour is `xfail(strict=True, raises=...)`, not a
standing failure.

The spike is outside `testpaths`, and the slice spike set the precedent of a red suite. Even so, anyone running the
spike's tests on main after the merge sees "1 failed" with no gate explaining it.

*Fix (unverified):* moot under D6-S1. Otherwise, `xfail(strict=True, raises=RuntimeError)` when `World` has no
`advance`.

### D6-N3 (NIT). E18 doesn't record that it precedes the first run, as the errata's process requires
**Where:** `spikes/specgen/errata.md::E18`.

The process reads: "a changed line here with the owner's ruling, never a change to a frozen file, and only before the
first run."
- **The ruling:** E18 carries the owner's ruling.
- **No frozen file changed:** `burn.py` is not in `freeze.sha256`. The five frozen files check OK with
  `shasum -a 256 -c`, and the merge's own edits touch only `burn.py` and `errata.md`.
- **Before the first run:** nothing in E18 or in the intro paragraph says so. The intro says it of E10 to E17, but it
  was not extended to E18. The tree holds no run output, so I can't establish the timing from it.

*Scenario:* a reader auditing the pre-registration can't tell whether E18 was added after data existed.

*Fix (unverified):* one clause in E18: "before the first run".

## Checked, not findings

- **The new test can fail (D5-N1).** Each mutation was made with `mutate.py` and restored:
  - Renaming `CellStore.adopt` and its one call in `simulation.py` to `take_cells` gave 1 failed,
    `test_each_owned_call_is_made_by_one_of_its_owners[adopt]`.
  - Renaming `claim` in `writers.py`, `physics.py`, `topology.py` and `scene.py` gave 1 failed, `[claim]`.
  - Renaming `constructing` in `scene.py` breaks the test module's import first (`ImportError`), which is loud anyway.
    `scene.py:356` is a real call, so the entry is not vacuous.
  - No entry is satisfied only by a definition. The check counts only `ast.Call` nodes, and `def claim` in `writers.py`
    is a `FunctionDef`.
- **A residual the delta didn't touch.** The `OWNED_CALLS` scan matches call names, so
  `from simcore.core.writers import claim as grant` followed by `grant(...)` in a law passes it. This is pre-existing
  and out of this diff.
- **The PR 4a group (D5-N2).** The new heading in `docs/plans/checklists.md` sits above the five PR 4a rows:
  incremental rebuilds, `rho_cp`, the refused `place`, the raising publication, and Arch S5. The caches row left under
  PR 3 is PR 3's own deferral (`sim_step/fold.md` DP S2), so it is correctly placed.
- **The other spike modules.** `generate.py`, `score.py`, `protocol.py`, `labelling.py` and `geometry.py` import
  `place`, `SpecRejected`, `MaterialGrid`, `Scene`, `Box`, `Cylinder`, `Primitive`, `primitives_from_data`, refusals
  and `digest`. None of them uses `World`, `Applier` or `advance`. The branch changed `imagination.py` only in a
  comment.
  - `probe_place_parity.py` placed 300 seeded specs (boxes and cylinders, 1–3 parts, five materials) on both engines.
    Every verdict and every accepted grid's digest (`material` and `solid` bytes) was identical: 86 accepted, 206
    `over_budget` and 8 `too_small`.
  - The probe reached only three verdict classes, so other refusal codes rest on `test_spike.py`'s own cases, which
    pass. M1 to M4 agree on these engines by construction, not by luck.
- **The marker.**
  - `lint_standards` passes with the marker in place.
  - With the roadmap bullet removed (`mutate_roadmap.py`), it reports
    `src/simcore/core/simulation.py:98: TEMPORARY(phase1/sim-clock): list src/simcore/core/simulation.py under Phase 1`.
    Two more findings in that run came from my backup file inside the copy, an artefact. No other Phase 1 text names
    `simulation.py`, so the listing is not satisfied by accident.
  - The comment is true: `Simulation.__init__` builds `CellFrame.of(world.grid, 0, tick=0, time_us=0)` from whatever
    grid it is handed.
  - The roadmap bullet names step 5a's PR 4b loader, the same `sim-clock` label as `imagination.py`'s marker for PR
    4b, and Phase 1 holds "Save format v0".
  - The marker marks a missing loader contract rather than band-aid code. The owner ruled for it, and I accept it.
- **The merge.**
  - `git diff c6d4f10 79b5d91^2 --stat` over `src tests scripts spikes pyproject.toml constraints .github client data
    ci` is empty: #47, #51 and #54 change no code.
  - `git show --remerge-diff 79b5d91` lists only `burn.py` (3 lines) and `errata.md` (1 line), so every other file is
    git's automatic merge.
  - Five files changed on both sides: `CLAUDE.md`, `docs/architecture.md`, `docs/design/fire_solid.md`,
    `docs/plans/checklists.md` and `docs/roadmap.md`. For each, `merge_sides.sh` checks that the lines main changed
    since the base (`53cd42c`) equal the lines the merge adds to the branch's parent, and the reverse. All five match
    both ways, so nothing was duplicated or lost.
  - Main's added lines in those files mention none of the APIs this branch retires (`advance`, `Applier(`, turns,
    PR 4).
- **Determinism and replay.** The fold changes a docstring and a test, and the marker adds a comment. M5's port
  equivalence (D6-S1) is a same-machine, bit-identical comparison.
- **Ahead of the hand-off.** origin/main has since moved by #52 and #55. `git merge-tree HEAD origin/main` reports
  conflicts in `CLAUDE.md`, `docs/architecture.md`, `tests/test_act_validation.py` and `tests/test_cross_tier.py`.
  #54's new Known gap in `architecture.md` says "PR #52 moves this list to `docs/known_gaps.md`; whichever lands second
  carries the entry". #52 has landed, so that next merge must carry the entry. It needs its own read.

## Status table

| id | status | evidence |
|---|---|---|
| D5-N1 | fixed | `tests/test_ownership.py::test_each_owned_call_is_made_by_one_of_its_owners`, parametrized over every `OWNED_CALLS` entry, counts only `ast.Call` nodes in the owner modules. Renaming `adopt` (definition and call) gives 1 failed, `[adopt]`. Renaming `claim` gives 1 failed, `[claim]`. `constructing` has a real call at `scene.py:356`. No entry is vacuous on the tree. |
| D5-N2 | fixed | `docs/plans/checklists.md`, Step 5a, has a new group, "Deferred from PR 4a's review (`reviews/sim_tick/fold.md`)". It sits above the three rows delta 5 named (the refused `place`, the raising publication, Arch S5), and also above D-S2's rebuilds and the `rho_cp` row. The row left under PR 3 is PR 3's DP S2. |
| D5-N3 | open | The finding was that `CellStore.__deepcopy__`'s docstring gives the wrong reason. The new one says a deep copy "is a stepped state ... which a second simulation would publish as frame 0". On the shipped path, only a `Simulation` steps a grid, and it adopts the grid first. `_adopted` is a plain instance attribute: there are no `__slots__` and no `__reduce__` or `__getstate__` override (`probe_deepcopy_adopted.py`). So a default deep copy of a stepped grid would carry `_adopted = True`, and `Simulation(World(copy))` would raise at `adopt` before returning, publishing nothing. The stated hazard can't arise. The true one is that the copy would be a grid no simulation can own. That wording came from delta 5's own unverified fix, and verifying it was the author's step. Error message and refusal are right. |
