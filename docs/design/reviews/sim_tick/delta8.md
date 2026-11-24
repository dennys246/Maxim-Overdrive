# PR 4a follow-up (`phase1/sim-replay`) delta 8: the delta-7 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay. One reader.

**Reviewed:** `git diff 9de55a3 8dcc0ff` (8 files): `burn.check_engine`, `burn.trajectory`, `burn._src_tree` and
the `engine` key in `burn.m5`'s output; `m5_golden_c6d4f10.json`, now six specs; `m5_golden_recorder.py`; the three
M5 tests in `test_spike.py`; E18 and the errata intro; the `CellStore.__deepcopy__` docstring. I read the "Delta 7"
table in `fold.md` as the author's claim. Every status below is set from the tree.

**How it was run.**
- **Trees:** `git archive 8dcc0ff` at `<scratchpad>/delta8/tree` (the worktree was clean at `8dcc0ff`), and
  `git archive c6d4f10` at `<scratchpad>/delta8/c6d4f10`. Every mutation was restored afterwards. `diff -rq` of
  `spikes/`, `cmp` of `core.yaml` and of `thermal.py` against the worktree are clean, apart from caches.
- **Interpreter:** the worktree's venv. Probes ran under `-I` with the tree's `src`, its root and `spikes/specgen`
  first on `sys.path`. Pytest ran under `env -i` with `PYTHONPATH` set to the tree. Each run printed
  `simcore.__file__`, and every one resolved into the tree it was meant to (the re-record into the `c6d4f10` archive).
- **Throwaway git:** the spike tests, the lint and the `src_tree` probe each got a throwaway `git init` and commit in
  the copy, removed afterwards.
- **Scripts:** `.worktrees/_durable/sim_tick_review/delta8_scripts/`: `rerecord.sh`, `mutations.sh`,
  `mutations_wire.sh`, `probe_src_tree.sh`, `probe_blind_spot.py`, `probe_deepcopy.py` (delta 7's), the candidate
  tests `test_m5_wire.py` and `test_m5_burn_returns.py`, and delta 7's `mutate.py`, `run_spike.sh` and `run_lint.sh`.
- **Ran:**
  - `spikes/specgen/test_spike.py`: 68 passed.
  - `scripts/lint_standards.py`: PASS, 0 findings.
  - The re-record, six mutations of `burn.py`, two of the engine (`data/` and `src/`), the `src_tree` probe and the
    deep-copy probe, below.
- **Not run:** the full suite, `tests/test_simulation.py` (the only `src` change is a docstring), mypy, ruff,
  import-linter and the gate. I did not check for a `prepush: PASS 8dcc0ff`.

## Counts

**New findings: 0 BLOCKER, 2 SHOULD-FIX, 2 NIT.**

**Statuses set (5 rows):**
- D7-S1: fixed. Its test and its record are new findings, D8-S1 and D8-S2.
- D7-S2 (the owner's ruling): E18's text matches it. The intro's opening paragraph is not qualified (D8-N2).
- D7-N1: fixed.
- D7-N2: **open**.
- D5-N3: fixed.

**Differs from the author:** the fold says D7-N2 is folded by adding `legs` and `block` to the golden. That covers the
engine's rows for a fire on air and a burnout. It doesn't cover `burn()`'s returns for them, which is what D7-N2's
scenario names. Both mutations from that scenario still leave every test green.

## New findings

### D8-S1 (SHOULD-FIX). No test holds that `m5` calls the check, or calls it before it burns
**Where:** `spikes/specgen/test_spike.py::test_m5_refuses_to_score_on_an_engine_that_moved`,
`test_m5_records_the_engine_it_burned_on`, and `spikes/specgen/burn.py::m5`.

**What the tests reach.** The refusal test calls `check_engine(moved)` directly, with a path. The record test calls
`m5([])` and checks `matches == "c6d4f10"`, a constant that could just as well be written in. No test sees `m5` refuse,
and with no samples, the order of the check and the burns can't be observed.

**Evidence (`mutations.sh`, four M5 tests each run):**
- **M1:** `check_engine` never compares. 1 failed: the refusal test. Its guard works as far as it goes.
- **M2:** `m5` writes `{"matches": "c6d4f10", ...}` instead of calling `check_engine()`. **4 passed.**
- **M3:** the check moved below the burn loop. **4 passed.**
- **M6:** T3's step, `SimConfig(tick_us=100_000, physics_every=5)`. 3 failed, and each refusal reads "M5 refuses to
  score: crate". The golden itself can fail.

*Scenario:* a later edit to `m5` drops the call, or moves it after the burns to report it alongside them. The suite
stays green. M5 then scores on a moved engine, the exact failure D7-S1 was opened for. Today the shipped path is right:
`score.py --m5` calls `burn.m5`, and `burn.m5`'s first statement is the check, before any burn. I read it there, and
`score.py` is the only caller that produces an M5 number.

*Fix (verified):* `delta8_scripts/test_m5_wire.py::test_m5_checks_the_engine_before_it_burns_anything` monkeypatches
`burn.check_engine` to raise and `burn.burn` to record its calls, then runs `m5` on one accepted sample. It asserts the
refusal and that nothing was burned. Copied into the tree, it passes unmutated and fails under M2 and under M3
(`mutations_wire.sh`). One thing to watch: `check_engine`'s default `golden_path=GOLDEN` is bound when the function is
defined, so monkeypatching `burn.GOLDEN` would not move the check. That is why the test patches the function.

### D8-S2 (SHOULD-FIX). `src_tree` records HEAD's `src`, not the `src` M5 ran on, and no test can tell the two apart
**Where:** `spikes/specgen/burn.py::_src_tree`, and `test_spike.py::test_m5_records_the_engine_it_burned_on`.

**What it records.** `git rev-parse HEAD:src` names the committed tree. Python imports the working tree.

**Evidence (`probe_src_tree.sh`, a throwaway git in the copy):**
- **Clean:** `src_tree` is `948f5d35…`, which is `HEAD:src`. That is right.
- **`src` dirty:** I appended a line to `heat.py` without committing it, and `git status` shows ` M
  src/simcore/core/heat.py`. `m5` still records `948f5d35…`. It names a tree that is not the one it ran on, and it
  says nothing.
- **Not a git checkout:** `m5` raises `CalledProcessError` (exit 128), after the check has run. That is loud, which is
  correct.
- **The test:** with `_src_tree` mutated to return `"0" * 40`, `test_m5_records_the_engine_it_burned_on` still passes.
  It checks only the length, 40.

*Scenario:* the scorer runs M5 in a checkout with an uncommitted `src` edit, perhaps a local experiment, or a change
to wood-free physics that the golden doesn't reach (D8-N1). The check passes, and the output names a clean tree. An
auditor who reproduces M5 from that `src_tree` gets a different engine, and has nothing to tell them so. D7-S1 asked
for the record so the scored file could show which engine it burned on. On a dirty tree it shows the wrong one.

*Context:* `generate.py::header` records `src_tree` the same way, `HEAD:src`. That is outside this diff and was
already there, but the new code copies the pattern.

*Fix (partly verified):* refuse when `git status --porcelain -- src` is non-empty, or record that it was dirty. A test
should compare `src_tree` with `git rev-parse HEAD:src`. That half is verified:
`test_m5_wire.py::test_m5_records_heads_src_tree` passes unmutated and fails with the constant
(`mutations_wire.sh`). The dirty-tree refusal is unverified.

### D8-N1 (NIT). The golden is six wood specs, and E18 claims it catches any engine that would move an M5 number
**Where:** `spikes/specgen/errata.md::E18` ("a later engine that would move one stops M5 instead"), and
`m5_golden_c6d4f10.json`.

**What the golden covers:** eight wood primitives, all ignited at one point, the protocol's offset, 100 kW. Specs can
use five materials (`arms.yaml`: concrete, steel, glass, wood, drywall) and any geometry the budget allows. So the
golden samples the engine; it can't prove the universal claim.

**What I measured (`probe_blind_spot.py`):**
- **A data change:** drywall's `degrade_above_c` lowered from 150 to 120, and glass's from 500 to 400. `check_engine`
  passes, and a 40 x 40 x 50 cm drywall box's integrity at turn 30 moves from 0.6864 to 0.5359. That path is still
  caught on the shipped path, though not by this check: `score.py::read_run` refuses any run whose header
  `data_sha256` differs from the tree's data.
- **A `src` change:** I capped `damage.thermal`'s excess at 300, 500 or 800 °C. At 300 and 500, the check refuses on
  `block`. At 800, nothing moves, drywall included. I didn't find a natural `src` change that slips past, so I can't
  show a concrete case. The gap is in what is claimed.

*Scenario:* a `src` change keyed to a property wood doesn't have, such as a steel conduction path or a law for
interfaces between two solids. It moves M5 for steel or mixed specs, and the check passes. E18 says it couldn't.

*Fix (unverified):* say what the check is: a sentinel over six wood specs, with data held by `score.py`'s
`data_sha256` check. Or add one spec per material, and one mixed-material spec, to the golden.

### D8-N2 (NIT). The errata intro still says the file came before any data existed
**Where:** `spikes/specgen/errata.md`, the opening paragraph ("It is committed before any data exists, so no reading
can be chosen to rescue a result").

**What the fold changed:** it qualified the rule sentence ("only before the first run; E18 is the one exception").
**What it left:** the factual claim two lines above, with no exception. E18 itself says it was written "possibly after
generation began", and its 2026-11-23 rewrite (`8dcc0ff`, 09:26) came after the first window opened.

**A related point:** E18 still says "Written at 23:34 on 2026-11-22", although its text was rewritten on 2026-11-23.
The ruling dates let a reader infer the rewrite, but the row doesn't say when its current text was written.

*Scenario:* a reader of the intro takes every row to predate the data, and only finds the exception if they read the
next paragraph. Delta 7 asked for this very sentence to name E18. *Fix (unverified):* add "E18 excepted" to that
sentence, and give E18's rewrite its date.

## Checked, not findings

- **The re-record (`rerecord.sh`).** I copied the branch's `m5_golden_recorder.py` into the `c6d4f10` archive and ran
  it per its docstring, `python -I spikes/specgen/m5_golden_recorder.py <out>` from the archive's root. `simcore`
  resolved into the archive, and the recorder took `POWER_W`, `TURNS` and `TURN_S` from the archive's own `burn.py`.
  `cmp` with the committed `m5_golden_c6d4f10.json` reports them identical, in 1.8 s.
- **`legs` and `block` are what the fold says.**
  - **`legs`:** 0 solid cells in the sphere at turn 0, and the ignite succeeds, so it is a fire on air. Its integrity
    ends at 1.0.
  - **`block`:** 8 solid cells at turn 0. Its integrity falls from turn 4 and reaches 0.1077 at turn 9. At turn 10
    there is no solid left, integrity reads 0.0, and it stays 0 to turn 30. That is a burnout, and it lands on `AT`'s
    first turn.
  - **Burns partway:** `plank` ends at 0.5631, and `crate` and `stool` at 0.99844. The test's "burns partway"
    assertion holds.
- **The order on the shipped path.** `score.py` imports `burn` only under `--m5` and calls only `burn.m5`.
  `burn.m5` runs `check_engine()` and then `_src_tree()` before its loop. `check_engine` uses the same `lit` and
  `turns` that `burn` uses, so the check exercises the code that scores. No other file calls `burn.burn`.
- **An exact comparison.** Rows are `[int, repr(float) | None]`, compared as lists after a JSON round trip, so the
  comparison is bit for bit on the float. There are no duplicate spec names, and specs run in the file's order. No
  RNG, clock or hash is involved.
  - **Across machines:** the golden is a same-engine replay. On another machine, a different float result would make
    it refuse, which is loud, not silent. CLAUDE.md promises only the outcome class across machines, so the scorer
    may need to run where the golden was recorded. I didn't test another machine.
- **The `engine` key.** M5's cells are keyed `model/arm`, so `"engine"` can't collide with one. No consumer in
  `score.py` iterates M5's keys.
- **D5-N3.** `probe_deepcopy.py` ran on the new tree with the refusal deleted at run time. A fresh, an adopted and a
  stepped grid each fail with `cannot pickle 'mappingproxy' object`. Copying each attribute alone, only `_materials`
  (`MaterialTable`) fails. With it memoised, the deep copy succeeds. The docstring now names the material table, and
  that is true.
- **D7-N1.** The recorder is committed at `spikes/specgen/m5_golden_recorder.py`, the test comment and E18 cite it,
  and it re-records the committed bytes (above).
- **The lint** passes on the tree.

## Status table

| id | status | evidence |
|---|---|---|
| D7-S1 | fixed | On the shipped path, `score.py --m5` calls `burn.m5`, which runs `check_engine` before any burn and records `{"matches", "src_tree"}`. The check refuses at T3's step (M6, three tests red with "M5 refuses to score: crate") and at a saturating damage law with a 300 or 500 °C cap (`block`). The golden re-records `cmp`-identical on `c6d4f10`. What the fold leaves unguarded is new: no test holds the call or its order (D8-S1), and the record can be false on a dirty tree (D8-S2). |
| D7-S2 | owner's ruling; the text matches | E18 reads "owner, 2026-11-23: E18 stands as the one exception to 'only before the first run', because it changes no number and M5 runs at scoring (delta 7, D7-S2)". The intro's rule sentence names the exception and the reason. The intro's first paragraph still says the file came "before any data exists" (D8-N2). |
| D7-N1 | fixed | `spikes/specgen/m5_golden_recorder.py` is committed, and its docstring's usage re-records the golden byte for byte from `git archive c6d4f10`. |
| D7-N2 | open | The golden now holds a fire on air (`legs`, 0 solid at turn 0) and a burnout (`block`, solid gone at turn 10), so the engine rows for both are held. `burn()`'s returns are not. M4 (censor recorded after the integrity) and M5 (the fire-on-air return deleted) leave all 68 spike tests green, which is the scenario D7-N2 named. The refused-ignite dict is still untested too. *Fix (verified):* `delta8_scripts/test_m5_burn_returns.py` derives `burn()`'s expected dicts for `legs` and `block` from the golden's rows. It passes unmutated and fails under M4 and under M5. |
| D5-N3 | fixed | The docstring names "the material table's mappingproxy". `probe_deepcopy.py` confirms `_materials` is the only attribute that fails alone. |
