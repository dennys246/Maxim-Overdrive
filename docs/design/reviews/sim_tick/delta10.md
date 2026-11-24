# PR 4a follow-up (`phase1/sim-replay`) delta 10: the delta-9 fold, read from the tree

**Lenses:** Executor, Wire integrity, and the generation path. One reader. The last round under "Delta 10's stop
rule" (`fold.md`).

**Reviewed:** `820fb29`'s own diff (`git show 820fb29`): `protocol.git`, `protocol.engine_tree` and `ENGINE`, the
call sites `burn.m5` and `generate.py::header`, the three new or rewritten tests in `test_spike.py`, and E18. Note that
`git diff 5dc79b5 820fb29` also carries `bf493f4`, the merge of main's #53 (`scripts/remote_gate.py` and its reviews);
I read only `820fb29`'s own seven files. I read the "Delta 9" table in `fold.md` as the author's claim. The head,
`8540ba0`, merges main's #64 and #58: `git diff 820fb29 8540ba0 -- spikes` is empty.

For the generation path I also read `run_window.sh`, `generate.py::run`, `done_samples` and
`HEADER_KEYS_THAT_MUST_MATCH`, `maxim_overdrive/data.py::data_dir`, `.gitignore`, plan §7, and the spike branch
`phase6/specgen-spike` (read-only, through its local mirror worktree).

**How it was run.**
- **Trees:** `git archive 8540ba0` at `<scratchpad>/delta10/tree` (the mutations), `tree2` (the generation probes) and
  `tree3` (the lint), plus `git archive 5dc79b5 spikes/specgen` at `<scratchpad>/delta10/old` (the pre-fold header
  code). Every mutation was restored afterwards; `diff -rq` of `spikes/` against the worktree is clean, apart from
  caches. The worktree's only change is the expected uncommitted `fold.md`.
- **Interpreter:** the worktree's venv, under `env -i` with `HOME` in the scratchpad. Each run printed
  `simcore.__file__`: `<tree>/src/simcore/__init__.py` for the tests, the simulated host worktree's `src` for the probes.
- **Throwaway git:** `git init` and commits in the copies, with `-c commit.gpgsign=false`, removed afterwards. No real
  git config was read or written.
- **Scripts:** `.worktrees/_durable/sim_tick_review/delta10_scripts/`: `mutations.sh` (13 mutations, each against the
  whole spike test file), `probe_generation.sh` with `header_probe.py` (the host setup), and delta 9's `mutate.py`,
  `run_spike.sh` and `run_lint.sh`.
- **Ran:** `spikes/specgen/test_spike.py`: 73 passed. `scripts/lint_standards.py`: PASS, 0 findings. The mutations and
  probes below.
- **Not run:** the full suite, mypy, ruff and the gate. I could not reach the spike's host. The generation answer comes
  from its scripts and docs, and from a local simulation.

## Counts

**New findings: 0 BLOCKER, 0 SHOULD-FIX, 3 NIT.** Under the stop rule the NITs go to the errata or a backlog row with
no code change, and no further round is needed.

**Statuses set (6 rows):** D9-S1, D9-S2, D9-N1, D9-N2, D9-N3 and D9-N4 are all fixed.

**The author's seven mutations reproduce exactly.** Each turns exactly one test red, out of 73:

| mutation | red |
|---|---|
| M1: `--untracked-files=all` dropped | `test_the_engine_tree_refuses_a_src_no_tree_names` |
| M2: `protocol.git` inherits the environment | `test_the_engine_tree_refuses_a_src_no_tree_names` |
| M3: the import check never refuses (`if False:`) | `test_the_engine_tree_refuses_an_engine_imported_from_another_checkout` |
| M4: the dirty check never refuses | `test_the_engine_tree_refuses_a_src_no_tree_names` |
| M5: `engine_tree` returns `"0" * 40` | `test_m5_records_the_engine_it_burned_on` |
| M6: `m5` records `protocol.git(ROOT, "rev-parse", "HEAD:src")` | `test_m5_and_the_run_header_record_the_engine_tree_and_refuse_with_it` |
| M7: `header` reads the same rev-parse | `test_m5_and_the_run_header_record_the_engine_tree_and_refuse_with_it` |

Mine:
- **M10** (the import check reads only `engine[:1]`): red, the import-root test.
- **M11** (`git status` of another path): red, the dirty-src test.
- **M13**, a control (`--ignored` added to the status): 39 red. Every test that builds a header refuses once
  `__pycache__` counts. That shows the shipped flags exclude ignored files, which a legitimate run needs.
- **M8, M9 and M12 stay green.** They are the three NITs below.

## The generation path

**The host's setup, from the scripts.** `run_window.sh` runs `"$root/.venv/bin/python" "$here/generate.py"`, where
`root` is the checkout that holds the script. Nothing sets `PYTHONPATH`, and `generate.py` doesn't touch `sys.path`.
`simcore` therefore comes from whatever that venv installed. The documented setup is the worktree's own `.venv`
(CLAUDE.md; plan §7: "runs in its own `.venv` on each machine"), built with `pip install -e`. The spike branch's local
mirror is set up that way: its `_editable_impl_maxim_overdrive.pth` names that same worktree's `src`. So under the
documented setup, `ENGINE` lies under `ROOT/src`, and the header passes. I can't see the host's venv. If it were
borrowed, or installed without `-e`, every run would now refuse before its first sample, with the message naming the
path. That is the intended behaviour, and it fails loudly.

**Simulated (`probe_generation.sh`):** a repository, a clone of it, a worktree of the clone at
`clone/.worktrees/spike`, and the engine imported from the worktree's `src`, as an editable install of that worktree
would import it.

| case | result |
|---|---|
| 1. old (`5dc79b5`) header code writes a run | written; `src_tree 948f5d35…` |
| 2. the worktree commits the new spike code and resumes that run | `RunRefused: … its spike_tree differs` |
| 3. a fresh run on the new code, then a resume of it, with `src/**/__pycache__` and a `src/maxim_overdrive.egg-info/` present | header written; resume ok |
| 4. the engine reached through `/tmp` (a symlink to `/private/tmp`), the spike dir through the other, and a symlink to the worktree | resume ok, all three |
| 5. the worktree's spike code with the origin's `src` (a borrowed engine) | refused: `imported from outside …/spike/src`, both packages listed |
| 6. an untracked `src/simcore/stray.py`; then a tracked edit | refused, both |
| 7. `burn.m5([])` on that dirty worktree; then clean | refused; clean: `{'matches': 'c6d4f10', 'src_tree': '948f5d35…'}` |
| 8. `GIT_DIR` naming the origin, inherited | resume ok: the variable is dropped |

- **`.resolve()` and symlinks.** Both sides are resolved: `ROOT` comes from `Path(__file__).resolve()` and
  `engine_tree` resolves each engine path. A symlinked path does not make a legitimate run refuse (case 4).
- **What the run writes under `src`.** It writes `__pycache__`, and an editable install's `*.egg-info` may land
  there. Both are in the tracked `.gitignore`, and `git status --porcelain` omits ignored files whatever
  `--untracked-files` says (case 3; M13 is the converse). Nothing in `src/` writes files at run time except
  `simcore/host/tokens.py`, which the spike doesn't use. Run files go to `run_window.sh`'s `<runs-dir>`, and the status
  covers `src` only. A resume does not refuse itself.
- **Data.** `data_dir` looks for `_data` beside the package first, then `../../data`. Imported from `ROOT/src`, that is
  `ROOT/data`, the directory `data_sha256` hashes. The venv's `site-packages/maxim_overdrive/_data` is a namespace
  directory with no `__init__.py`. The regular package in `src` wins, so the engine never reads that copy.
- **A resume of a run started before this change.** The runs in progress on the spike's host use `phase6/specgen-spike`.
  That branch's `generate.py` is byte for byte `5dc79b5`'s, and it does not contain this fold. While its worktree
  stays on its commit, those runs resume exactly as before. If the branch takes this change, a resume refuses loudly
  with "its spike_tree differs", before any sample is written (case 2). `simcore_commit` would refuse it anyway (any
  commit changes it). That refusal predates the fold, so the author's D9-N2 reasoning holds. The header's keys and
  `src_tree`'s meaning are unchanged: on a clean tree the old and new code record the same hash (case 1 against case 3).
  So old run files still score under the new `score.py`, whose `--m5` checks the scorer's own checkout, not the run's.
  The consequence for the owner, not a defect: the running S and R cells must finish on the spike branch's current
  commit, or restart.

## New findings

### D10-N1 (NIT). The import check is tested only against an unrelated path, not against `ROOT` outside `src`
**Where:** `spikes/specgen/protocol.py::engine_tree` (`src = (root / "src").resolve()`) and
`test_spike.py::test_the_engine_tree_refuses_an_engine_imported_from_another_checkout`.

**Evidence (M8):** with `src = root.resolve()`, so that anything under the checkout passes, all 73 tests stay green. The
test's stray path, `tmp_path/other/src/x.py`, isn't under the throwaway repository at all. The default-`ENGINE` call
isn't under it either.

*Scenario:* a refactor loosens the root to the checkout. An engine imported from an ignored copy under `ROOT` then
passes the check while `HEAD:src` is recorded, for example a `build/lib/simcore` left by `pip install .` with
`ROOT/build` on the path. No documented setup does this, so no shipped run fails today.

*Fix (unverified):* add a stray path at `repo/build/lib/simcore/__init__.py` to the test.

### D10-N2 (NIT). Nothing holds `ENGINE` to naming both packages
**Where:** `spikes/specgen/protocol.py::ENGINE`.

**Evidence (M9):** with `ENGINE = (Path(simcore.__file__),)`, all 73 tests stay green. The import-root test passes
explicit lists, and its default-`ENGINE` call refuses on `simcore` alone.

*Scenario:* `maxim_overdrive` is dropped from `ENGINE`. D9-S1's data half then reopens: a `maxim_overdrive` from
another checkout reads that checkout's `data/`, while the header hashes `ROOT/data`. Today `ENGINE` names both, and
both live in one `src`, so this needs a split install that no documented setup makes.

*Fix (unverified):* assert `{p.parent.name for p in protocol.ENGINE} == {"simcore", "maxim_overdrive"}`.

### D10-N3 (NIT). Only `GIT_DIR` is tested of the `GIT_*` variables dropped
**Where:** `spikes/specgen/protocol.py::git` and the dirty-src test.

**Evidence (M12):** dropping only `GIT_DIR` (`if k != "GIT_DIR"`) leaves all 73 tests green. `GIT_WORK_TREE` and
`GIT_INDEX_FILE` are dropped by the shipped code (I read it), but no test sets them.

*Scenario:* a narrowed filter lets an inherited `GIT_INDEX_FILE` make `status` compare against another index. The code
today drops the whole prefix, so this is test reach only.

*Fix (unverified):* `monkeypatch.setenv` `GIT_WORK_TREE` and `GIT_INDEX_FILE` beside `GIT_DIR`.

## Checked, not findings

- **Order.** `header` calls `check_frozen`, then `engine_tree`, then reads `HEAD`. `m5` calls `check_engine` (six golden
  burns), then `engine_tree`, both before any sample burns. On a dirty `src` M5 spends the golden replay before it
  refuses (case 7). That costs seconds and moves no number.
- **The planted test (D9-S2).** It monkeypatches `protocol.engine_tree`, and both call sites look it up through the
  module attribute at call time, so the patch reaches both. `check_engine` is patched to pass, so the refusal seen is
  `engine_tree`'s. The test covers both sites in one function: M6 and M7 each turn it red.
- **The untracked case (D9-N1).** The test writes `showUntrackedFiles = no` into the throwaway repository's own config,
  which `git status` reads. Under M1 it goes red, so the flag is what catches the file.
- **`GIT_DIR` in the test (D9-N4).** It points at a missing path. Under M2, git fails with `CalledProcessError`, not
  the `RuntimeError` the test expects, so it's red for the right reason. Case 8 shows the same with a real repository.
- **Shadowing by ignored files.** `--untracked-files=all` still omits ignored files. An ignored directory could shadow a
  tracked module only for a module named after an ignore pattern (`build`, `dist`). `git ls-files src` has none. A
  sourceless `.pyc` (ignored) imports only where no `.py` exists, so it can't replace a tracked module.
- **Spike tests on a dirty checkout.** Every test that builds a header (`write_run`, 8 call sites, 39 tests under M13)
  now refuses on a dirty or borrowed `src`. Delta 9 noted this for one test. `testpaths = ["tests"]`, so the gate
  doesn't run them. It's a developer's inconvenience, not a defect.
- **E18 (D9-N3).** The text now says "changed since it was generated", and says the data files are unchanged since
  `c6d4f10`, "though no check holds them to it". `git diff c6d4f10 8540ba0 -- data` is empty. "refusing … an engine
  imported from another checkout" matches the code.
- **Removed helpers.** `grep` finds no remaining `src_tree(` or `_git(` call. `burn.py` and `generate.py` dropped their
  `subprocess` imports, and the lint passes.

## Status table

| id | status | evidence |
|---|---|---|
| D9-S1 | fixed | `engine_tree` refuses unless both packages resolve under `ROOT/src`: red under M3 and M10. On the host simulation a borrowed engine is refused (case 5) and a legitimate worktree run passes (cases 3 and 4). Test reach is narrower than the check (D10-N1, D10-N2). |
| D9-S2 | fixed | `test_m5_and_the_run_header_record_the_engine_tree_and_refuse_with_it` is red under M6 (m5 inlined) and M7 (header inlined), green unmutated. |
| D9-N1 | fixed | `--untracked-files=all` is in the status call. The test sets `showUntrackedFiles = no` in the repository's config and adds an untracked file, and is red under M1. Ignored files stay excluded (M13). |
| D9-N2 | fixed | `header` records `engine_tree()`, read before `HEAD`. A dirty `src` refuses the header (case 6). The author's "not deferred" reasoning is right: a resume across commits already refuses on `simcore_commit`, and the running spike branch doesn't carry the change. |
| D9-N3 | fixed | E18 narrows `data_sha256` to "since it was generated", states the `c6d4f10` data diff is empty on 2026-11-23 (verified), and says no check holds the data to it. |
| D9-N4 | fixed | `protocol.git` drops every `GIT_*` variable. The test's `GIT_DIR` goes red under M2, and case 8 passes with a real foreign `GIT_DIR`. Only `GIT_DIR` is exercised (D10-N3). |
