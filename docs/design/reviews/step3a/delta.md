# Step 3a delta review (fold staged on c74a67f)

**Counts: 0 BLOCKER, 1 SHOULD-FIX, 5 NIT.**

## What I ran

All runs were on `git archive $(write-tree)` in `scratchpad/s3d`, using the worktree's `.venv/bin/python`, with
`PYTHONPATH=copy/src` and HOME/XDG inside the copy. The copy has since been deleted, along with a scratch venv and
wheel. The worktree was not touched: `git status` is unchanged.

**(1) Planted violations.**

- Clean copy: the gate's `lint_imports_command()` returns 5 kept, rc 0.
- I planted three violations:
  - `src/simcore/host.py` with `from maxim_overdrive import data`
  - `import pickle` in `core/heat.py`
  - `def _planted(): return open("x").read()` in `core/heat.py`
- Result:
  - import-linter: 2 broken (`engine-not-game`: `simcore.host -> maxim_overdrive.data`; `sealed-core`: `heat -> pickle`), rc 1.
  - `test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism` goes red on both "imports pickle" and "calls builtin open".
  - `test_every_child_of_the_engine_is_in_a_layer` goes red on `{'simcore.host'}`.
- Extra plant: `import tests.conftest` in `simcore/protocol/` breaks `tests-out`. Good.

**(2) The TEMPORARY marker.**

- `scripts/lint_standards.py` passes on the copy, made into a scratch git repo: PASS, 0 findings.
- Non-vacuity: I removed `` `src/simcore/core/heat.py` `` from roadmap Phase 1. The lint then fails with "list src/simcore/core/heat.py under Phase 1". The roadmap row is present at docs/roadmap.md:45.

**(3) `test_each_turn_takes_the_substeps_the_rigs_took`.**

- Passes clean, 2 cases (0.2 and 0.1 m without ALL_TIERS).
- `FLOOR_AREA_M2 = 0.17` makes it red. `min_substeps` returning 1 makes it red. It holds the floor.

**(4)** I checked each round-one SHOULD-FIX against the diff (table below).

**(5) Build and rig history.**

- I built a wheel in a scratch venv with hatchling: METADATA `Version: 0.0.1`, and `_data/rigs/*` is shipped.
- `pip install --no-deps -e .` into the scratch venv gives `importlib.metadata.version == simcore.__version__ == 0.0.1`, with `simcore` resolved to the copy's `src/`.
- Rig v1 history: `origin/main` has only rig v0. No ref other than `phase1/boundaries` carries `detail_radius_m`, and `4cbd7ec` is on no remote branch.

**Targeted tests:** test_tooling_config, test_isolation, test_sem_bridge and test_validation, filtered to the changed areas: 136 passed.

## Round-one SHOULD-FIX status

| id | folded? |
|---|---|
| S3A-S1 | yes (`engine-not-game` plus the layer-membership test; both proven above) |
| S3A-S2 | yes, as asked; see S3D-S1 for what the claim now overstates |
| S3A-S3 | yes: the marker, the roadmap row, per-call wording, the `test_heat.py` callers in 5a, and "5a" numbering. The commit-claim rewording is in the draft `s3af_msg.txt`. |
| S3A-S4 | yes: the field is deleted, and architecture.md:135 and roadmap.md:59 are fixed |
| S3A-S5 | yes: boundaries §10 "As built in 3a", plus `test_the_game_package_holds_only_its_data_until_the_lab` |
| S3E-S1 | yes: an equality assert, and `tests-out` is pinned |
| S3E-S2 | yes: W5 and W6 are done, and the rest is assigned to step 3b in checklists.md with the correct reason (the bridge still writes the world) |
| S3E-S3 | yes, with a test |
| S3E-S4 | yes: every named site is fixed. A leftover is in N4. |

None is missing.

## SHOULD-FIX

**S3D-S1. The core's file-IO ban has three open doors, while the pyproject, backlog and scan comments say "file IO" is banned.**
`pyproject.toml::sealed-core`, `tests/test_determinism.py::SEALED_CORE_BANNED`, `::core_findings`

- **Failure, proven on the copy.** I planted this in `core/heat.py`:
  ```
  import builtins, codecs, numpy as np
  builtins.open("x"); codecs.open("y"); np.load("z.npy"); np.fromfile("w")
  getattr(builtins, "exec")
  ```
  Import-linter reported 5 kept, and the scan test passed.
- **The three doors:**
  - `builtins` and `codecs` are not on the list.
  - `core_findings` matches only a bare `ast.Name` call, so `builtins.open` and an alias (`f = open; f(...)`) get through.
  - numpy, which the core imports, reads and writes files through `load`, `loadtxt`, `genfromtxt`, `fromfile`, `save*`, `memmap` and `ndarray.tofile`.
- **Why it matters:** the comment "What imports can't show (§3): builtins that read files" and B19's "file IO" claim are both broader than what is checked. Step 3b's checklist does carry "B-4's … banned unsafe calls", but it doesn't name these.
- **Fix:**
  - Add `builtins`, `codecs`, `fileinput`, `linecache`, `tokenize`, `zipfile`, `tarfile`, `gzip`, `bz2` and `lzma` to the shared list.
  - In `core_findings`, flag the numpy IO attribute calls through the existing `_dotted` helper (`np.load`, …, `.tofile`) and `scipy.io`.
  - Add each to `test_the_core_scan_catches`.
  - Or, if this is deferred: narrow the claim in the comment and in B19, and name these in the step 3b item.

## NIT

- **S3D-N1** `src/simcore/core/heat.py::_FLOAT_SLACK`. Its rationale is false. `math.ceil(3.9999999999999996)` is already 4; the slack only guards a quotient that lands just *above* an integer.
  - I removed `- _FLOAT_SLACK`, and both the per-turn test and `test_heat.py -k substep` stayed green. So the line runs under test, but its behaviour isn't tested.
  - None of 0.2, 0.1, 0.05, 0.08, 0.04, 0.025, 0.02 or 0.01 m gives a quotient above an integer.
  - Fix: reword the comment to the real case, and add a spacing whose quotient is `n + ε`, or drop the slack.
- **S3D-N2** `tests/fixtures/formats/v1/rig.yaml`. The golden's own header says "Never edit it", and the fold edited it while keeping `version: 1`.
  - This is safe: v1 exists only on this unpushed branch (origin/main has v0 only; no other ref has `detail_radius_m`).
  - But neither the fixture nor the draft commit message says that v1 was redefined before it shipped. A reader of the history sees a broken golden rule.
  - Fix: one line in the commit message saying v1 was redefined before it shipped.
- **S3D-N3** `heat.py::min_substeps`. Moving from `round` to `ceil` changes the floor at unshipped spacings (0.16 m: 6 becomes 7; any non-integer quotient now rounds up). That is harmless, since nothing ships off the three spacings. The commit says "an explicit rounding rule" but not that values changed elsewhere. State it.
- **S3D-N4** `tests/test_snapshot.py:1`. Its docstring still says `` `world.snapshot` `` (now `simcore.protocol.encoding.snapshot`), which is the same stale name S3E-S4 fixed in architecture.md. The other stale names (`imagination.spec.place` in `ip_and_licensing.md`, `world_model.md`, and boundaries §1–§4) sit in design docs, which are the owner's call under O22. Logging is now banned against §3's text; that is recorded only in a pyproject comment, not in boundaries §10's as-built note.
- **S3D-N5** `tests/test_tooling_config.py::_lint_imports`. It runs its own copy of the command string, not `prepush.sh`'s `lint_imports`. If the gate's line changes (for example to the no-op `-m importlinter.cli`), this test stays green, and only the string-presence test catches it. So S3E-N5's end-to-end ask is half met. Fix: extract the command from `prepush.sh` in the test, or run the function from the script.
