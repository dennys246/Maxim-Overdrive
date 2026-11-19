# Design review: boundaries.md, Wire integrity lens

- **Lens:** Wire integrity (what must move or be rewired by the migration; what ends up with no caller or a
  silently broken path)
- **Design under review:** `docs/design/boundaries.md` at 47add00 (mainly "Migration" and "Enforcement")
- **Code surveyed:** `phase1/act-validation` at 2f200b5, plus the branch topology of every live branch
- **Date:** 2026-11-16
- **Counts:** 3 BLOCKER, 6 SHOULD-FIX, 5 NIT

The design calls the rename "mechanical". It isn't. About 70 references name the package (25 files: every `src/`
module, 13 test files, `pyproject.toml` x4, `CLAUDE.md`, `README.md`, `docs/code_review.md`, `scripts/prepush.sh`).
Most are imports, and a missed import fails loudly. The dangerous references are the handful that name the package
*as a scope*: coverage `source`, the determinism AST scan's `PACKAGE`, the tooling test that pins coverage `source`,
and the `force-include` target. A mechanical `s/maxim_overdrive/maxim_world/` keeps every one of them passing and
quietly makes each one engine-only. Meanwhile a new package takes the old name and nothing measures it. Three of the
findings below were reproduced in a scratch repo rather than reasoned out. Those experiments are noted inline.

## BLOCKER

### W1. In-flight branches rebase new modules silently into the game package

`docs/design/boundaries.md::Migration` (the rename plus "creates an empty `src/maxim_overdrive/`")

**Scenario.** Any branch alive across the rename that *adds* a file under `src/maxim_overdrive/`, such as
`phase1/sim-clock` adding `src/maxim_overdrive/clock.py` or a protocol branch adding `codec.py`, rebases with no
conflict. Modified files follow the rename. **New** files land in the game package. Git's directory-rename detection
only fires when the old directory is gone, and the design recreates it in the same PR.

Reproduced with git 2.50.1 in a scratch repo:

- Rename plus a new `__init__.py` in one commit: `Successfully rebased`, and `src/mo/clock.py` (containing
  `import time`) ended up in the game package.
- Rename and game package in two separate commits: same silent result, so splitting the commits does not help.
- Rename with no game package: git stops with a conflict and proposes `src/mw/clock.py`, which is the correct place.

Once misplaced, the file is invisible to the AST scan (W2), to coverage (W2) and to B-3's core contract. B-1 lets
the game import the engine, so nothing goes red. A clock module that imports `time` would sit outside the sealed
simulation it was written for.

**Fix.**
- Don't create `src/maxim_overdrive/` in `phase1/boundaries`. Create it with the first game content (see W4).
- If it must exist, add a test pinning its contents to an allowlist (today `{"__init__.py"}`), so a stray rebased
  file goes red.
- Either way, the migration step should say: "after rebasing over the rename, `git diff --name-status` against the
  pre-rebase branch must show no `A src/maxim_overdrive/...`".

### W2. Three scope-defining references become engine-only, and the game package becomes a blind spot

`pyproject.toml::[tool.coverage.run].source`,
`tests/test_tooling_config.py::test_coverage_measures_branches_over_src_and_scripts`,
`tests/test_determinism.py::PACKAGE`

- `source = ["maxim_overdrive", "scripts"]` becomes `["maxim_world", "scripts"]` under a mechanical rename, and the
  tooling test that pins it is rewritten in the same sed, so it now *enforces* the hole. CLAUDE.md says "Coverage
  measures `src/` and `scripts/`". That rule would be false, and its cited guard would still pass.
- If instead the game package is added by name (`["maxim_world", "maxim_overdrive", "scripts"]`), it still
  doesn't work. Reproduced with coverage 7.17.3 and pytest-cov 7.1.0: a package listed by name in `source` that no
  test imports contributes **nothing**. Its unimported modules (`game/lab.py`, two statements, 0% run) were not in
  the report. Total stayed 100%, `fail_under = 100` passed, and exit was 0.
  - Coverage did emit `CoverageWarning: Module game was never imported (module-not-imported)`, but it is not a Python
    warning that pytest's `filterwarnings = ["error"]` escalates. So "warnings are errors" does not cover it.
  - With `source = ["src"]` (a path), the same unimported file showed at 0% and the gate failed, as it should.
  - A never-imported empty game package plus a misplaced file (W1) is exactly this case.
- `PACKAGE = ROOT / "src" / "maxim_overdrive"`:
  - Renamed mechanically, the determinism scan covers only the engine. Game content (scenarios, NPC rosters, scene
    authoring), which writes the world's initial state, is never scanned for `random` or `time`.
  - Not renamed, the scan walks an empty package and passes vacuously: a test that cannot fail.

**Fix.**
- Make `source` path-based (`["src", "scripts"]`), or list both packages *and* add a test asserting that the set of
  top-level packages under `src/` equals the measured set.
- Make the AST scan iterate every package under `src/`, minus an explicit non-simulation list, and assert it found
  more than zero files per package.
- Rewrite the tooling test to derive its expectation from `src/`, not from a literal name.
- Prove each by planting an untested module in the game package and watching the gate go red.

### W3. `lint-imports` from a worktree would check the main checkout's code

`scripts/prepush.sh` (the new import-linter step), with CLAUDE.md "Commands" (`PYTHON=<venv>/bin/python
scripts/prepush.sh` in a worktree without its own `.venv`)

**Scenario.**
- No worktree has a `.venv` (checked: `.worktrees/*/.venv` is absent), so every worktree gate runs the main
  checkout's interpreter.
- That venv's editable install is `_editable_impl_maxim_overdrive.pth` containing
  `/Users/dennyschaedig/Scripts/Maxim-Overdrive/src`.
- Verified: running that Python from `.worktrees/act-validation` resolves `maxim_overdrive.__file__` to the **main
  checkout's** `src/` (currently on `phase1/realtime-design`), and `data_dir()` to the main checkout's `data/`.

Today every gate step is immune to this:
- pytest uses `pythonpath = ["src"]`;
- mypy works from `files`;
- `lint_standards.py` works from `__file__`;
- the determinism subprocess sets `PYTHONPATH` explicitly.

import-linter (grimp) finds root packages by import resolution, and it adds the current directory to `sys.path`,
not `src/`. So it would be the first gate step that analyses whichever tree the `.pth` points at. During the
migration window that tree may have no `maxim_world`, which fails loudly. Once the main checkout is on a post-rename
branch, the worktree gate prints `prepush: PASS <sha>` having checked the contracts against **different code**. That
breaks the "PASS for the exact commit" rule in the very workflow CLAUDE.md prescribes.

**Fix.**
- Run it as `PYTHONPATH="$PWD/src" "$PY" -m importlinter.cli` (or the `lint-imports` equivalent) in `prepush.sh`.
- Add a test that runs the contracts with a violating import planted in a temp copy, or at least asserts grimp
  resolves `maxim_world` under this repo's `src/`.
- Add `importlinter` to the preflight import list on the `"$PY" -c 'import maxim, ruff, ...'` line, so a stale venv
  fails before a minute of tests rather than mid-gate.

## SHOULD-FIX

### W4. The empty game package is capability with no caller, and it causes W1 and W2

`docs/design/boundaries.md::B-1` ("`maxim_overdrive` becomes the game package, empty at first")

CLAUDE.md, "A fix ships with a caller": nothing imports the empty package, nothing ships in it, and its only consumer
is the B-1 contract.
- That contract is satisfiable without the package. "`maxim_world` must not import `maxim_overdrive`" can be enforced
  by a forbidden contract (or the AST scan) whether or not the target exists, and it is provable by planting the
  import.
- Meanwhile its existence breaks the README (W7), creates the rebase trap (W1) and needs the coverage and scan
  rewiring (W2) before it holds a line of code.

**Recommendation.**
- Rename now, but create `maxim_overdrive/` in the PR that brings the first game module (the lab), with its tests,
  coverage scope and allowlist in that same PR.
- If the owner wants the name reserved now, accept W1's allowlist test as the price.

### W5. The `_data` mapping is never exercised, and the failure is misleading when it breaks

`pyproject.toml::[tool.hatch.build.targets.wheel.force-include]`, `src/maxim_overdrive/config.py::data_dir`

- `data_dir()` returns `Path(__file__).parent / "_data"` if that directory exists, else `here.parents[1] / "data"`.
  The mapping `"data" = "maxim_overdrive/_data"` must become `"maxim_world/_data"`, and the design says so. But no
  test or CI step builds or installs the wheel: `.github/workflows/test.yml` does `pip install -e`.
- In a checkout or editable install the fallback always wins. The editable install even copies a stale `_data` into
  `site-packages/maxim_overdrive/_data` (it's in the venv's RECORD), which nothing reads.
- Scenario: the target is left at `maxim_overdrive/_data`, or the data is attached to the game package.
  - Every local and CI run stays green.
  - An installed wheel has `site-packages/maxim_world/` with no `_data`, so `data_dir()` falls back to
    `.../lib/python3.14/data`.
  - `RigProfile.load("laptop")` raises `FileNotFoundError` on a path that names neither package.

**Fix.**
- Add a test asserting that the `force-include` target's first component equals
  `Path(maxim_world.config.__file__).parent.name`. It's cheap and needs no build.
- Make the fallback refuse with a clear message when neither location exists, rather than returning a nonexistent
  path.

### W6. `MAXIM_OVERDRIVE_ALL_TIERS` is split across files that no test ties together

`scripts/prepush.sh` (line 52), `tests/conftest.py::ALL_TIERS`, `CLAUDE.md`, `README.md`, `docs/code_review.md`
(`MAXIM_OVERDRIVE_*`)

The engine's tier variable is named after the game. If the rename tidies it in `conftest.py` but not in `prepush.sh`
(or the reverse), the gate silently stops running the 0.05 m `max` tier. That tier is the resolution rule's
cross-tier evidence. Nothing fails: `ALL_TIERS` just shrinks to `FAST_TIERS`.

**Fix.** Decide the name explicitly in the design (keeping it is fine). Add a test that the variable `prepush.sh`
exports is the one `conftest.py` reads, or that a gate run collects `max` parameters.

### W7. "Updates imports in ... docs" is unsafe as a sed and incomplete as a list

`docs/design/boundaries.md::Migration`

- **Kept-verbatim records.** `docs/design/reviews/realtime_lanes_coop/determinism.md` and five research notes under
  `docs/design/research/` cite `src/maxim_overdrive/...` as it stood at a named commit. The reviews are "kept
  verbatim" by rule. A mechanical rewrite of `docs/` falsifies the record, for example "the AST scan reads only
  `src/maxim_overdrive`". Exclude `docs/design/reviews/` and `docs/design/research/`, and say so.
- **Omissions from the list.** "Docs that change" omits:
  - `README.md`: the quick-start does `from maxim_overdrive import Box, RigProfile, Scene, World`. After the rename
    that imports the empty game package and raises `ImportError`, and no test runs the README.
  - `docs/code_review.md` (the `MAXIM_OVERDRIVE_*` row);
  - the CLAUDE.md Commands block (W6).

### W8. The contracts as written are partly unexpressible; prove each one, and guard the step itself

`docs/design/boundaries.md::Enforcement` (B-2, B-3, B-12), `scripts/lint_standards.py::symbol_present`

- **B-3 can't be written as stated.**
  - It lists `os.urandom`, which is an attribute, not a module. import-linter can forbid `os` or nothing. The AST
    scan must keep that one, so say so.
  - Forbidding `time`, `random`, `socket` and `asyncio` needs `include_external_packages = true`. Each one must be
    proven by a planted import.
  - The host, transport and thinking lane don't exist yet, so how the contract treats nonexistent modules has to be
    checked, not assumed.
- **B-12** forbids `tests`. `tests` is importable only from the repo root (tests do `from tests.conftest import
  ...`), so the contract must name it in a form grimp resolves.
- **The guard citation.** The new CLAUDE.md rule's guard must name the gate step, for example
  `scripts/prepush.sh::lint-imports`, plus a config test.
  - `symbol_present` on a non-`.py` file is a word match. `pyproject.toml::importlinter` would stay satisfied with
    every contract deleted.
  - A guard citing only `pyproject.toml` counts as "checked" in the lint's tally, even if `prepush.sh` never runs the
    tool.

### W9. Sequencing: nothing is on `main` yet, and four branches will cross the rename

`docs/design/boundaries.md::Migration` ("lands after PR 1 and before `phase1/sim-clock`")

- `main` is still `d02c0a2 Initial commit`.
- `phase1/act-validation` (PR 1) is 25 commits ahead of it.
- `phase1/standards` (1 ahead, 8 behind PR 1), `phase1/design-v2` (7 ahead, 8 behind) and `phase1/realtime-design`
  each fork from intermediate points of PR 1's line.
- `phase1/transport` and `foundations/world-server-v0` are older still. `transport`'s `server/` is what
  `NOT_SIMULATION = {"server"}` anticipates.
- `standards` edits 13 test files that import the package; each import line it touched conflicts.

"After PR 1" is not enough. The design should name a merge order (PR 1, then standards, then design-v2 and
realtime-design, then boundaries). It should also say which stale branches are abandoned, and require W1's
post-rebase check for any branch that survives the rename.

## NIT

### W10. A wire value changes under the sed, and nothing pins it

`src/maxim_overdrive/sem_env/bridge.py::to_maxim_entity`

`metadata={"source": "maxim_overdrive.sem_env", ...}` is data handed across the Maxim membrane. A sed changes it to
`maxim_world.sem_env`, and no test asserts it (grep finds none). Decide it, then pin it with a test, or derive it
from `__name__`.

### W11. CLAUDE.md's Layout paths aren't checked

CLAUDE.md "Layout" (four `src/maxim_overdrive/...` paths)

`lint_standards.py::check_guards` checks only `Guard:` citations, and none of those name `src/` today, so the rename
breaks no guard. That also means a missed Layout line goes stale silently. List it explicitly in the migration's doc
changes.

### W12. Stale bytecode in old subdirectories

The worktrees' untracked `__pycache__/` directories

After `git mv`, the ignored `src/maxim_overdrive/{world,sem_env,imagination}/__pycache__/` stay put. They make
`maxim_overdrive.world` importable as an empty namespace package inside the game package. It fails loudly at the
first submodule import, but it's confusing. Add `git clean -fdX src/` to the migration step.

### W13. Identity strings

`src/maxim_overdrive/__init__.py` (the docstring "Maxim Overdrive world server" and `__version__`),
`pyproject.toml::[project].name` / `description`

- Moving `__version__` to the engine while the distribution stays `maxim-overdrive` is fine, but write it down.
- The description ("World server for Maxim Overdrive") becomes the engine's.

### W14. The AST scan's exemption keys on a path component

`tests/test_determinism.py::NOT_SIMULATION`

The exemption is keyed on the first path component (`"server"`). B-1 puts "the game's server entry point" in
`maxim_overdrive`, and the engine's host in `maxim_world`. Once the scan spans both packages (W2), state which
package's `server` is exempt, so the exemption can't silently widen to the other.

## What I checked and found clean

- **CI.** `.github/workflows/test.yml` has no package or path references.
- **Client.** There is no Godot client, and `prepush.sh` refuses `client/`.
- **TEMPORARY markers.** There are none in code, and no `src/maxim_overdrive` paths in the roadmap's marker lists.
- **mypy.** `files = ["src", ...]` picks up both packages.
- **ruff.** It treats `src/` packages as first-party by default.
- **Editable installs.** The existing `.pth` points at `src/`, so they keep importing after the rename without a
  reinstall.
- **diff-cover.** It works by git rename detection, and today everything is a changed line anyway against the
  initial-commit `main`.
- **`lint_standards.py`.** It has no hard-coded package path; `ROOT` comes from `__file__`.
- **`tests/test_sem_compat.py`.** Its only references are imports.
