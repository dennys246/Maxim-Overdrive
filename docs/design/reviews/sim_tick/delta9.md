# PR 4a follow-up (`phase1/sim-replay`) delta 9: the delta-8 fold, read from the tree

**Lenses:** Executor, Architecture, Wire integrity, Determinism and replay. One reader.

**Reviewed:** `git diff 8dcc0ff 5dc79b5`, the code half: `burn.src_tree` and `burn._git`, the `m5` call site, the
four M5 tests in `test_spike.py` (one changed, three new), and the errata intro and E18. I read the "Delta 8" table in
`fold.md` as the author's claim. Every status below is set from the tree. `bf493f4`, the branch head, is a merge of
main's #53: `git diff 5dc79b5 bf493f4 -- spikes src/simcore/core` is empty.

**How it was run.**
- **Tree:** `git archive bf493f4` at `<scratchpad>/delta9/tree` (the worktree was clean at `bf493f4`). Every mutation
  was restored afterwards; `diff -rq` of `spikes/` and `cmp` of `damage/thermal.py` against the worktree are clean,
  apart from caches.
- **Interpreter:** the worktree's venv. Pytest ran under `env -i` with `HOME` and `PYTHONPATH` set to the tree, and
  printed `simcore.__file__` (`<tree>/src/simcore/__init__.py`). The import-root probe deliberately ran without
  `PYTHONPATH`, and says where `simcore` came from.
- **Throwaway git:** each spike run, the lint and each probe got a throwaway `git init` and commit in the copy, with
  `-c commit.gpgsign=false`, removed afterwards. No real git config was read or written: the git-environment probe
  used a `HOME` and `GIT_CONFIG_GLOBAL` under `<scratchpad>`.
- **Scripts:** `.worktrees/_durable/sim_tick_review/delta9_scripts/`: `mutations.sh` (13 mutations), `probe_import_root.sh`,
  `probe_git_env.sh`, the candidate test `test_m5_src_wire.py`, and delta 8's `mutate.py`, `run_spike.sh` and
  `run_lint.sh`.
- **Ran:**
  - `spikes/specgen/test_spike.py`: 71 passed.
  - `scripts/lint_standards.py`: PASS, 0 findings.
  - The mutations and probes below.
- **Not run:** the full suite, mypy, ruff, import-linter and the gate; I did not check for a `prepush: PASS`. I did not
  probe a symlinked `src` or a stale `.pyc` whose source kept its size and mtime.

## Counts

**New findings: 0 BLOCKER, 2 SHOULD-FIX, 4 NIT.**

**Statuses set (5 rows):** D8-S1, D8-S2, D8-N1, D8-N2 and D7-N2 are all fixed. D8-S2's fold is right for the case it
names; D9-S1 and D9-S2 are what it leaves.

**The author's six mutations reproduce exactly.** Each turns exactly one M5 test red, the one the fold names:

| mutation of `burn.py` | red |
|---|---|
| M2: `m5` writes `"c6d4f10"` instead of calling `check_engine()` | `test_m5_checks_the_engine_before_it_burns_anything` |
| M3: the check moved below the burn loop | `test_m5_checks_the_engine_before_it_burns_anything` |
| M4: censor recorded after the integrity read | `test_m5_burn_returns_a_fire_on_air_and_a_burnout_as_the_golden_rows_say` |
| M5: the fire-on-air return deleted | `test_m5_burn_returns_a_fire_on_air_and_a_burnout_as_the_golden_rows_say` |
| M7: `src_tree` never refuses (`if False:`) | `test_m5_refuses_an_uncommitted_src_which_no_tree_names` |
| M8: `src_tree` returns `"0" * 40` | `test_m5_records_the_engine_it_burned_on` |

Mine: M1 (`check_engine` never compares) turns the refusal test red. M6 (T3's step) turns four red. M9 (status of
another path) turns the uncommitted-src test red. M11 (`src_tree(Path("/"))` in `m5`) turns the record test red. M10,
M12 and M13 stay green, below.

## New findings

### D9-S1 (SHOULD-FIX). `src_tree` names `protocol.ROOT`'s `src`, not the `src` Python imported
**Where:** `spikes/specgen/burn.py::src_tree` (its default `root=protocol.ROOT`), on the shipped path `score.py --m5`
→ `burn.m5`.

**What it records.** `protocol.ROOT` is the checkout that holds the spike's scripts (`HERE.parents[1]`). `simcore` is
imported from wherever the interpreter finds it. The worktree's venv has an editable install
(`_editable_impl_maxim_overdrive.pth`), so `simcore` resolves into the venv's own checkout, whatever the script's
checkout. CLAUDE.md tells a worktree without its own `.venv` to use another one's (`PYTHON=<venv>/bin/python`). In that
case the two checkouts differ, and so do the `src` that ran and the `src` that was recorded.

**Evidence (`probe_import_root.sh`):** I ran `burn.m5([])` with the tree copy's `spikes/specgen` first on the path and
no `PYTHONPATH`, as `python spikes/specgen/score.py` would run.
- **Clean copy:** `simcore` came from the venv's checkout, not the copy, and `protocol.ROOT` is the copy. The record
  read `948f5d35…`, which is the same `src` only because the two checkouts are at one commit.
- **Copy edited and committed:** I capped `damage.thermal`'s excess at 300 °C in the copy. The record read
  `{'matches': 'c6d4f10', 'src_tree': 'a50cf23c…'}`, so M5 says it passed the check on `a50cf23c`.
- **The copy's engine itself:** the same edit, imported from the copy (`PYTHONPATH`), gives `RuntimeError: M5 refuses to
  score: block no longer burns as it did on c6d4f10`.

So the output names a tree whose engine M5 would have refused to score. The check ran on one engine and the record
names another. Delta 8's D8-S2 asked that the record name the engine that ran. The dirty-tree refusal answers one way
it could fail; this is a second.

The same is true of the data. `maxim_overdrive.data` locates `data/` beside the imported package (`data.py`, line 33),
while `score.py::_current_data` hashes `protocol.ROOT / "data"`. E18 now leans on that hash for data.

*Scenario:* the scorer runs `score.py --m5` from a fresh worktree with the sim-replay venv, which is the documented
way. That worktree is at a later commit with a physics change. Its M5 numbers come from the venv's older engine, the
check passes on that engine, and the output records the later tree and its data hash. An auditor reproducing from the
recorded tree gets an engine that refuses.

*Fix (unverified):* refuse unless `simcore` and `maxim_overdrive` were imported from under `protocol.ROOT / "src"`,
or take the root from `simcore.__file__`. `generate.py::header` has the same property (D9-N2).

### D9-S2 (SHOULD-FIX). No test holds that `m5` refuses through `src_tree`
**Where:** `spikes/specgen/test_spike.py::test_m5_refuses_an_uncommitted_src_which_no_tree_names`,
`test_m5_records_the_engine_it_burned_on`, and `burn.py::m5`.

**What the tests reach.** The refusal test calls `src_tree(tmp_path)` directly. The record test calls `m5([])` on a
clean tree and compares with `HEAD:src`. Neither sees `m5` refuse a dirty `src`, which is the same hole D8-S1 found in
the engine check.

**Evidence (M13, `mutations.sh`):** I replaced `"src_tree": src_tree()` in `m5` with
`"src_tree": _git(protocol.ROOT, "rev-parse", "HEAD:src")`. That records the right tree on a clean tree and skips the
refusal. **All 7 M5 tests pass.**

*Scenario:* a refactor inlines the rev-parse into `m5`, or reads it from the run header. The suite stays green, and M5
again records `HEAD:src` on a dirty tree, which is D8-S2's exact failure.

*Fix (verified):* `delta9_scripts/test_m5_src_wire.py::test_m5_refuses_when_src_tree_refuses` monkeypatches
`burn.check_engine` to pass and `burn.src_tree` to raise, then asserts that `m5([])` raises. Copied into the tree, it
passes unmutated and fails under M13.

### D9-N1 (NIT). The refusal depends on the scorer's git config, and no test covers an untracked file
**Where:** `spikes/specgen/burn.py::src_tree` (`git status --porcelain -- src`).

**Evidence (`probe_git_env.sh`, a throwaway repo with one committed and one untracked file under `src`):**
- **Default config:** refused, `?? src/heat_new.py`. That is right, and it matters: an untracked `heat/__init__.py`
  would shadow a tracked `heat.py` at import.
- **`status.showUntrackedFiles = no` in the global config:** `src_tree` returned a tree hash and did not refuse. `git
  status` reads the user's config, and that setting is common in large repositories. A global `core.excludesFile`
  would hide files the same way.
- **No test sees the untracked case:** M10 (`--untracked-files=no`) leaves all 7 M5 tests green. The refusal test only
  edits a tracked file.

*Scenario:* a scorer whose global config hides untracked files has a new untracked module under `src` that a tracked
file imports through a fallback, or that shadows one. M5 records a clean tree that never held it.

*Fix (partly verified):* pass `--untracked-files=all`. With the hiding config in place, `git status --porcelain
--untracked-files=all -- src` lists `?? src/b.py`, where the default lists nothing. That is the verified half. The test
for an untracked file is unverified.

### D9-N2 (NIT). `generate.py::header` still records `HEAD:src` on a dirty tree
**Where:** `spikes/specgen/generate.py::header` (`"src_tree": _git("rev-parse", "HEAD:src")`) and its own `_git`.

The fold names this and leaves it. It is outside the diff and older than it. But it is the same defect at a second
call site, with a second `_git` helper, and run headers are where M1's verdicts are recorded. `score.py::read_run`
does not compare `src_tree`. A generation run in a checkout with an uncommitted `src` edit records a clean tree, and
it has D9-S1's import-root property too. There is a cost to fixing it now: `generate.py` is in `protocol.spike_tree`'s
digest, which a resumed run must match, so editing it while the nightly runs may be live would stop a resume.

*Scenario:* a nightly run in a worktree with a local `src` experiment writes headers that name `HEAD:src`. M1 numbers
are then attributed to an engine that didn't produce them.

*Fix (unverified):* one shared `src_tree` that both call. I'd defer it to the spike's next generation run, which is the
moment `generate.py` can change without breaking a resume. Deferring is the owner's call, not mine.

### D9-N3 (NIT). E18's data sentence is narrower than it reads
**Where:** `spikes/specgen/errata.md::E18` ("`score.py` refuses a run whose data files changed (`data_sha256`)").

**What `data_sha256` checks:** that the data at scoring matches the data recorded in the run header at generation. It
says nothing about the data since `c6d4f10`, the golden's engine. A data change committed before generation is in
both the header and the tree, so it passes that check. If it touches no wood property, it passes `check_engine` too:
delta 8 measured a drywall change that does exactly that. E18 names the `src` blind spot and implies the data are
fully held, when they are held only from the run's own start. Today there is no gap: `git diff c6d4f10 HEAD -- data`
is empty.

*Scenario:* the materials table is retuned for drywall before the next generation run. M5's drywall numbers move, and
neither check fires. E18 says data changes are refused.

*Fix (unverified):* make the sentence say "data changed since the run was generated", and add data to the stated blind
spot alongside `src`.

### D9-N4 (NIT). `src_tree` inherits the caller's git environment, including in the tmp-git test
**Where:** `spikes/specgen/burn.py::_git` (no `env=`), and `test_spike.py::test_m5_refuses_an_uncommitted_src_which_no_tree_names`.

**What is isolated, and what isn't.** The test's own `git()` helper passes an explicit environment: `PATH`, `HOME` set
to `tmp_path`, and `GIT_CONFIG_NOSYSTEM`. Its `init` and `commit` therefore never read the user's config or trigger
GPG, and the flags it uses (`-C`, `-c`, `status --porcelain --`) are old enough for any supported git. But the code
under test, `burn.src_tree(tmp_path)`, inherits the caller's whole environment.

**Evidence (`probe_git_env.sh`):** with `GIT_DIR` naming another throwaway repository, both the uncommitted-src test
and the record test fail with `M5 refuses to score: src has uncommitted changes … ?? src/`. The failure is loud.
Combined with the user's config (D9-N1), the test's result depends on more than `tmp_path`.

The repo's own rule is that tests run git only through `tests/_gitutil.py`. `spikes/` is outside `tests/` and the gate
doesn't run it, so this is a note, not a violation. A `GIT_DIR` that names the same repository's main checkout could
pass silently with the wrong `HEAD:src`. I did not construct that case.

*Fix (unverified):* `_git` strips `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` from the environment it passes.

## Checked, not findings

- **The fold's claims.** The six mutations are above. `test_m5_records_the_engine_it_burned_on` now compares the whole
  `engine` dict with `HEAD:src` read separately, so a constant (M8) or a wrong root (M11) fails it.
- **The wire test (D8-S1).** It patches the function, not `burn.GOLDEN`, which is right given `check_engine`'s
  default argument binding. It asserts both the refusal and that `burn` was never called.
- **The burn-returns test (D7-N2).** Its expected dicts come from the golden's rows: `legs`' fire on air, and `block`'s
  censor turn and integrity at `AT`, with `None` from the burnout on. It is not a re-derivation through `burn` itself.
- **`__pycache__`.** It is in `.gitignore`, which is tracked, so a checkout whose `src` holds caches stays clean: the
  tests pass in a copy that compiled its caches after the throwaway commit. A `src` with sources deleted and only
  `.pyc` left shows deletions and is refused.
- **Order on the shipped path.** `m5` builds `{"matches": check_engine(), "src_tree": src_tree()}` before its loop, so
  both refusals come before any burn. `score.py` imports `burn` only under `--m5`.
- **The spike's own code.** `src_tree` covers `src` only. An uncommitted edit to `burn()`'s aggregation is neither
  refused nor recorded, and `score.py`'s output records no code identity at all, although `protocol.spike_tree` exists.
  This is a property of the scorer that predates the diff, not of the fold.
- **The refused-ignite dict.** M12 (`"code": None` always) leaves every test green. `m5` uses only `ignited` from it,
  so no M5 number moves.
- **A dirty `src` while developing.** The record test now fails in a worktree with uncommitted `src` edits, and in a
  copy with no `.git`. That is the refusal working as intended, but the spike tests now depend on the checkout's
  state.
- **Errata text (D8-N1, D8-N2).** The intro reads "committed before any data exists … E18 is the one exception,
  below", and the rule paragraph keeps its exception. E18 names the six wood specs, the `src` blind spot, and "First
  written at 23:34 on 2026-11-22 … rewritten on 2026-11-23 in the folds of deltas 7 and 8". The lint passes.

## Status table

| id | status | evidence |
|---|---|---|
| D8-S1 | fixed | `test_m5_checks_the_engine_before_it_burns_anything` is red under M2 (the literal) and M3 (the check after the burns), and green unmutated. |
| D8-S2 | fixed | `src_tree` refuses `git status --porcelain -- src` output: red under M7, and the record test compares with `HEAD:src` and is red under M8. The scenario D8-S2 named, an uncommitted tracked edit, is refused. What it leaves is new: the recorded root is not the imported engine's (D9-S1), no test sees `m5` take the refusal (D9-S2), and the untracked case depends on the user's config (D9-N1). |
| D8-N1 | fixed | E18 says the golden is the six specs, all wood, and that a `src` change moving only another material's burn passes. Its data sentence is narrower than it reads (D9-N3). |
| D8-N2 | fixed | The intro's "committed before any data exists" names E18 as the one exception, and E18 gives its first and rewritten dates. |
| D7-N2 | fixed | `test_m5_burn_returns_a_fire_on_air_and_a_burnout_as_the_golden_rows_say` is red under M4 (the censor after the integrity) and M5 (the fire-on-air return deleted). The refused-ignite dict stays untested (M12), and no M5 number reads it. |
