# PR 4a follow-up (`phase1/sim-replay`) review round: the marker and the delta-6 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay. One reader.

**Reviewed:** `git diff origin/main 9de55a3` (9 files): `ef4c5c8` (the `TEMPORARY(phase1/sim-clock)` marker on
`Simulation.__init__` and its roadmap bullet) and `98810ce` (the delta-6 fold: M5's port to `Simulation.step`, the
golden and its test, E18, and the `CellStore.__deepcopy__` docstring). I read `9de55a3`, the merge, and the "Delta 6"
table in `fold.md` as a claim. Every status below is set from the tree.

**How it was run.**
- **Trees:** a copy of `9de55a3` at `<scratchpad>/delta7/tree`, and `git archive c6d4f10` extracted to
  `<scratchpad>/delta7/c6d4f10`. After every mutation was restored, `diff -rq` against the worktree was clean, apart
  from caches.
- **Interpreter:** the worktree's venv. Probes ran under `-I` with the tree's `src` and its root first on `sys.path`.
  Pytest and the lint ran under `env -i` with `PYTHONPATH=<tree>/src:<tree>`. Each run printed `simcore.__file__`,
  and every one resolved into the tree it was meant to.
- **Throwaway git:** the spike tests and the lint each got a throwaway `git init` and commit in the copy, removed
  afterwards.
- **Scripts:** `.worktrees/_durable/sim_tick_review/delta7_scripts/`: `rerecord.sh`, `probe_burn_parity.py`,
  `probe_tick1_and_names.py`, `probe_deepcopy.py`, `mutate.py`, `run_spike.sh` and `run_lint.sh`.
- **Ran:**
  - `spikes/specgen/test_spike.py`: 66 passed.
  - `tests/test_simulation.py`, `test_ownership.py`, `test_host.py` and `test_wire.py`: 512 passed, 1 skipped. The
    skip is `test_wire.py:186`, the slow tier.
  - `tests/test_lint_ids.py` and `test_lint_standards.py`, with git: 215 passed.
  - `scripts/lint_standards.py`: PASS, 0 findings.
- **Not run:** the full suite, mypy, ruff, import-linter and the gate. I did not check for a `prepush: PASS 9de55a3`.

## Counts

**New findings: 0 BLOCKER, 2 SHOULD-FIX, 2 NIT.**

**Statuses set (4 rows):**
- D6-S1: fixed.
- D6-N1 with D6-N2: fixed.
- D6-N3: fixed. What the fold now discloses is a new finding, D7-S2.
- D5-N3: **open**.

**Differs from the author:** the table leaves every row "open (for the reviewer)" and claims D5-N3 is folded. The new
docstring names the wrong table. A deep copy without the refusal fails on the *material* table's mappingproxies, and
the region table copies cleanly.

## New findings

### D7-S1 (SHOULD-FIX). Nothing that runs on a schedule holds the port, and M5's output doesn't say which engine it burned on
**Where:** `spikes/specgen/test_spike.py::test_m5_on_simulation_is_bit_for_bit_m5_on_world_advance`,
`spikes/specgen/burn.py::m5`, `spikes/specgen/score.py` (the `m5` call at line 490), and E18's "No M5 number moves".

**What changed.** The pin tied M5 to one engine. The port ties it to whatever `src` the scoring tree has.

**Why nothing catches drift.**
- The guard is the golden test, and it never runs on its own. `pyproject.toml` has `testpaths = ["tests"]`, and no
  file in `.github/`, `scripts/prepush.sh` or `pyproject.toml` names `spikes`.
- `generate.py`'s header records `simcore_commit` and `src_tree` for generation. `score.py` records no engine for M5,
  which it computes at scoring, and `burn.m5`'s output carries none either.

*Scenario:* a physics change lands on main before the scoring run, such as the Phase 1 fuel model or a PR 4b change to
heat or damage. The gate stays green, because the golden test is outside it. The scorer then runs M5 on the new
engine, and the solid-gone turns and integrity means differ from `c6d4f10`'s. E18 still says "No M5 number moves", and
the scored file can't show that it moved. Today the claim holds: the golden passes at `9de55a3`, and I re-recorded it
identical (see Checked). It is true at this commit only, and nothing keeps it true.

*Fix (unverified):* make M5 check itself before it burns. `burn.m5` could replay the four golden specs and refuse on
a mismatch; that costs about a second, since the two M5 tests ran in 1.2 s. It should also record the tree it ran on,
`git rev-parse HEAD:src`, in M5's output. Alternatively, E18 could name the engine M5 must score on and `score.py`
could refuse any other. **For the owner:** which of the two.

### D7-S2 (SHOULD-FIX). E18 says it may have been written after the first run began, which the errata's own rule forbids, and no ruling covers that
**Where:** `spikes/specgen/errata.md::E18`, and the intro paragraph.

**What the errata require.** The intro says the file "is committed before any data exists, so no reading can be
chosen to rescue a result". It adds that a later change is a changed line "with the owner's ruling ... and only before
the first run".

**What E18 now says.** "Written at 23:34 on 2026-11-22, inside the first nightly window, after generation may have
started but before any M5 result exists ... the spike's author confirms."
- **The window:** `run_window.sh` defaults to 22:00 to 08:00, and `98810ce` is stamped 23:37:25, so the time is
  consistent with the claim.
- **What the tree can't show:** whether generation had started. The tree holds no run output.
- **Earlier changes were inside the rule:** the earlier pin version (`79b5d91`, 18:35) was written before the window
  opened.
- **True:** "M5 runs at scoring". `score.py` imports `burn` only when M5 is requested.

**The defect.** The row admits it may break the "only before the first run" condition. Yet the only ruling it cites
is "Owner, 2026-11-22: port", a ruling on the substance, not on writing the change after the first run began. The
intro still says, without exception, that the file came before any data. "The spike's author confirms" is an open
confirmation, and nothing tracks it.

*Scenario:* someone audits the pre-registration after scoring. They see a change to how M5 runs, made possibly after
data existed, with no recorded decision that the exception was allowed. They can't tell an accepted exception from a
lapse. The change is in fact harmless: the port is bit-identical (below), and M5 is computed only at scoring. But the
record doesn't say the owner weighed that.

*Fix (unverified):* either the spike's author confirms that no generation had started, and E18 then says so plainly,
or the owner rules on the timing exception. E18 would then carry that ruling and its reason: the change moves no
number and M5 has no result yet. The intro's "before any data exists" should name E18 as the exception.

### D7-N1 (NIT). The golden's recorder is not in the repository
**Where:** `spikes/specgen/test_spike.py::test_m5_on_simulation_is_bit_for_bit_m5_on_world_advance` (its comment),
`spikes/specgen/m5_golden_c6d4f10.json`.

The test cites `.worktrees/_durable/sim_tick_review/delta6_scripts/m5_golden_recorder.py`. `.worktrees/` is in
`.gitignore` (`git check-ignore` confirms it), so the recorder is in no commit. The JSON's `engine` field says
`c6d4f10`, but nothing in the repository can re-derive it.

*Scenario:* a clone, CI, or a reboot that clears `_durable` leaves the golden with no reproducible provenance. A
reviewer who doubts it can't re-record it from the repo.

*Fix (unverified):* commit the recorder beside the golden, for example `spikes/specgen/record_m5_golden.py`, with its
`git archive c6d4f10` usage in its docstring. The test should cite that path instead.

### D7-N2 (NIT). The golden holds `lit` and `turns`, not `burn`'s own returns
**Where:** `spikes/specgen/burn.py::burn`, `spikes/specgen/test_spike.py`.

The golden test calls `burn.lit` and `burn.turns`. All four golden specs ignite, none is a fire on air, and none burns
out within 30 turns: the last solid counts are 80, 80, 47 and 86.
- **Untested in the spike suite:** three of `burn()`'s returns, which the fold restructured: the refused-ignite dict
  (`code`), the fire-on-air dict, and the censored path (`solid_gone_turn`, `None` integrities).
- **Tested:** `test_m5_burns_an_accepted_spec_at_turns_of_6_s` covers one uncensored accepted spec only.

*Scenario:* a later edit to `burn()` swaps the censor test to `solid == 0` after the integrity is recorded, or changes
the refusal dict. The golden test stays green.

My probe shows the three branches agree with `c6d4f10` today (Checked, below). *Fix (unverified):* add to the golden
one spec that burns out, such as the `block` below, censored at turn 10, and one fire on air (`legs`). Compare
`burn()`'s dict with the recorder's output of the old `burn()`.

## Checked, not findings

- **The merge.**
  - `git show --remerge-diff 9de55a3` is empty, so the merge was git's automatic one.
  - The merge-base with main is `79b5d91`. `git diff 79b5d91 98810ce` and `git diff 5960606 9de55a3` differ only in
    one blob-index line, for `docs/roadmap.md`, because main changed other hunks there. Their content is identical.
  - Main's roadmap changes since `79b5d91` are #52's `docs/known_gaps.md` repointing and #57's hello cap. Neither
    touches the new bullet. The merge brought in nothing beyond main.
- **The re-recorded golden.** I ran delta 6's recorder from `git archive c6d4f10` (`rerecord.sh`), and `simcore`
  resolved into that archive's `src`. `cmp` with the committed `m5_golden_c6d4f10.json` reports them identical.
- **`burn()` against the old `burn()`.** `probe_burn_parity.py` ran each tree's own `burn.burn` on eight specs.
  - **The results:** `crate` and `plank` stayed uncensored, `legs` was a fire on air, and `block`, `slab`, `cube` and
    `post` were censored at turns 10, 26, 23 and 23. `steelbox` was refused by `place` ("too heavy: 502 kg").
  - **The refused ignite:** with `--refuse`, which raises `POWER_W` to 600 kW, past `max_power_w`, both engines return
    `{"ignited": False, "code": "out_of_range"}` for every placed spec.
  - **The comparison:** the two JSON outputs are identical apart from my tree label, in both runs.
- **Tick 1.** `probe_tick1_and_names.py` spied on `Simulation.step`.
  - **The ignite tick:** it reported `(tick 1, 1 outcome, physics False, 0 substeps)`, so the fire-on-air check reads
    the placed grid with no physics, as the comments claim.
  - **The physics ticks:** 6, 12, …, 180, thirty in all, each 6.0 s (`CONFIG.physics_seconds`).
  - **Why only this configuration:** the golden test also goes red under `SimConfig(tick_us=6_000_000,
    physics_every=1)`. Tick 1 would then run physics together with the ignite. Delta 6 called that configuration
    equivalent too, which holds for its probe's per-turn rows but not for `lit`'s turn-0 read. The fold chose the one
    that is right.
- **`turns()` can't loop forever.** `SimConfig` refuses `physics_every < 1` (`_positive`), and every `step`
  advances the clock by one. So a physics tick comes within `physics_every` steps.
- **Names.** The new path builds a `LogRecord`, whose `target` passes `identity_key`, which allows 64 characters and
  no `:`. `place` uses `REGION_NAME`, which allows 128 and refuses `:` as `bad_name`. `imagination.Budget.max_name_chars` caps the
  name at 64. No name `place` accepts is refused as a target. I checked `a:b`, `fire:crate`, 64 x's, spaces, hyphens
  and case.
- **The golden can fail.**
  - **T3's step:** with `CONFIG` set to `SimConfig(tick_us=100_000, physics_every=5)`, it failed, `AssertionError:
    crate`, with 1 failed and 1 passed among the M5 tests.
  - **Restored:** the file was restored, and `cmp` with the worktree is clean.
  - **It can tell engines apart:** its last assertion holds, since `plank` ends at 0.5631.
- **The marker.**
  - **True:** `__init__` builds `CellFrame.of(world.grid, 0, tick=0, time_us=0)` from any grid.
  - **Accepted:** the lint passes with it.
  - **Red without its listing:** with the roadmap bullet removed, the lint fails with `src/simcore/core/simulation.py:98:
    TEMPORARY(phase1/sim-clock): list src/simcore/core/simulation.py under Phase 1 in docs/roadmap.md`. That is the
    only finding, and nothing else in Phase 1 names the file. The roadmap file was restored, and `cmp` is clean.
  - **What it cites exists:** the PR 4b checklist row (`docs/plans/checklists.md`, lines 267 and 268) and
    `sim_core.md` §2 and §3.
  - **An aside:** a marker citing an unknown step, `phase1/sim-done`, also passes. `TEMP_TARGET` checks the phase and
    the step's spelling, not the step itself. That is pre-existing, by design, and outside this diff.
- **Fit with main.**
  - **#57:** nothing in `src` outside `simulation.py` calls `Simulation(` or `from_scene(`, so the host doesn't reach
    the marked path.
  - **#52:** the diff writes nothing about Known gaps.
  - **#55:** `test_lint_ids.py` passes, as does the lint as a whole, on the new review ids.
- **Determinism.** The port is a same-machine, bit-identical comparison. It adds no RNG, clock or hash.

## Status table

| id | status | evidence |
|---|---|---|
| D6-S1 | fixed | `burn.py` steps `Simulation` with `SimConfig(tick_us=1_000_000, physics_every=6)` and the ignite as a tick-1 `LogRecord`. The golden re-recorded on `c6d4f10` is `cmp`-identical to the committed JSON. The test passes, and goes red at T3's config and at `physics_every=1`. `burn()` matches the old `burn()` on eight specs, covering each return, and on a refused ignite. E18's false premise is gone. Its lasting protection is D7-S1. |
| D6-N1, D6-N2 | fixed | The `hasattr(World, "advance")` guard and the `ENGINE` pin are removed from `burn.py`. `test_spike.py` gives 66 passed at `9de55a3`. Moot as the author says, and true in the tree. |
| D6-N3 | fixed | E18 now gives its time (23:34 on 2026-11-22, inside the 22:00 to 08:00 window; the commit is stamped 23:37) and says no M5 result exists. A reader can now tell. What it tells them is D7-S2. |
| D5-N3 | open | The new docstring says that, without the refusal, "a deep copy fails only by accident, on the region table's mappingproxy". `probe_deepcopy.py` deletes `CellStore.__deepcopy__` at run time. Deep copies of a fresh grid, a placed and adopted grid, and a grid stepped to tick 13 then all fail with `TypeError: cannot pickle 'mappingproxy' object`. Copying each attribute alone, only `_materials` (`MaterialTable`, whose `_by_name`, `_by_id` and `_lookups` are mappingproxies) fails. `_regions` copies cleanly. With `_materials` memoised, the whole stepped grid deep-copies, carrying `_adopted = True`. The claim names the wrong table. It also means a `MaterialTable` that stopped holding mappingproxies would make a deep copy succeed if the refusal were ever dropped. That is the "accident" point, but against a different object. The fix is to name the material table. |
