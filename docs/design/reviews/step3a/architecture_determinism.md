# Step 3a pre-push review: Architecture + Determinism and replay

Range: `52557b9..4cbd7ec` (tree at `c74a67f`). Read-only in the worktree. Runs were done on `git archive` copies in the
scratchpad (since deleted), using the worktree's `.venv/bin/python`.

**Counts: 0 BLOCKER, 5 SHOULD-FIX, 8 NIT.**

## What was checked

- **Placements.** These match the commit's layer map and boundaries §2.2/§3/§8.2: checks, materials, limits
  (ActionLimits, the type only, §2.2 5b), grid, scene, heat, damage, world and imagination in `simcore.core`; loaders
  and sem in `simcore.adapters`; tiers and encoding in `simcore.protocol`; data locations in `maxim_overdrive.data`.
  The core has no IO. Its only file-format helpers are `checks.format_version` and `known_keys`, and they work on
  data that is already parsed.
- **Determinism, measured.** I ran the old tree's `run("laptop")` and `run("rig")` against the new tree's `run(0.2)`
  and `run(0.1)`. The digests are identical: `f7429cba…d256` and `e9e57122…a0ca`. I did not run 0.05 m.
- **Determinism, read.** Nothing in the move changes order, dtype or defaults:
  - `load_materials` builds its dict comprehension in YAML order, as the old loop did.
  - `MaterialGrid.empty` gets `dx` through `finite_real`, the same float path `cell_size_m` took.
  - `snapshot` is byte-for-byte the old code.
  - The lookup arrays are still float64.
  - Defaults were removed (`materials=None`, `path=None`); none was changed.
- **min_substeps values.** `min_substeps` gives 4, 16 and 64. The quotients are 3.9999999999999996, 15.999999999999996
  and 63.99…, and `round` takes each to the right integer.
- **Sealed-core list against the scan.** The sealed-core list contains all six of `tests/test_determinism.py::BANNED_MODULES`.
  `numpy.random` can't be written as an import-linter target, because external packages are squashed to their top
  level. The AST scan still covers it over all of `src/`.
- **Rig v1 refusal.** `format_version` runs before `known_keys`, so a v0 file is refused for its version. A v1 file
  that carries `cell_size_m` is refused for an unknown key. Both paths are sound.
- **Sizes.** The largest function is `lint_guards.py::check_guards` at 34 code lines. The largest module is
  `bridge.py` at 422 lines. Nothing else in `src/` or `scripts/` comes near a limit.
- **Planted proofs** (on the copy):
  - `src/simcore/host.py` with `from maxim_overdrive import data; import threading`: all 4 contracts KEPT.
  - `src/simcore/core/planted.py` with `import tempfile, shutil, pickle, logging, queue`: all 4 contracts KEPT.

## SHOULD-FIX

**S3A-S1. Engine-never-imports-game holds only inside the four listed layers.** `pyproject.toml::[tool.importlinter]`
- **Failure:** a layers contract checks only modules that are in a layer. `simcore/__init__.py`, and any new direct
  child of `simcore` (§2.2 layer 8 `host`/`verify` is the next one expected), can import `maxim_overdrive`, `threading`
  or anything else, and the gate stays green. Proved by planting `simcore/host.py`.
- **Why it matters:** §10 lists "B-1 engine/game: import-linter forbidden contracts" as landing in boundaries, and
  `maxim_overdrive/__init__.py` claims "The engine never imports this package (import-linter)". That claim is false
  for this case.
- **Fix:**
  - Add `forbidden: simcore -> maxim_overdrive` (as_packages).
  - Add a tooling test that every direct child of `simcore` appears in `layers`, or in an explicit list of modules
    outside the layers. Prove both by planting an import.

**S3A-S2. The sealed core's banned list is shorter than its name says, and builtins get past both checks.**
`pyproject.toml::sealed-core`, `tests/test_determinism.py::findings`
- **Failure:** the contract is named "no clock, entropy, OS, file IO, concurrency", but it leaves out:
  - file IO: `tempfile`, `shutil`, `glob`, `pickle`, `marshal`, `shelve`, `dbm`, `sqlite3`, `mmap`
  - `logging`, which stamps records with the wall clock and writes files
  - concurrency: `_thread`, `queue`, `sched`
  - networking: `select`, `selectors`, `ssl`, `http`, `urllib`
  - `ctypes`, `zoneinfo`

  A planted core module importing five of them passed. Separately, builtin `open`, `__import__`, `exec`, `eval` and
  `input` are invisible to import-linter, and the AST scan doesn't look for them. So the core can read a file
  today without any check going red.
- **Why it matters:** §10 B-3 promised "one shared banned list; extended AST scan" in boundaries. The tooling test
  only asserts that the contract's list is a superset of the scan's, so the two lists can drift apart.
- **Fix:**
  - Extend the list.
  - Add a builtin-call finding (`open`, `__import__`, `exec`, `eval`, `input`) to the scan for files under
    `simcore/core/`.
  - Either derive both from one constant, or record that the extended scan is deferred, with a trigger.

**S3A-S3. The substep floor is a scheduled replacement with no `TEMPORARY` marker, and the claim made for it is too
broad.** `src/simcore/core/heat.py::FLOOR_AREA_M2`, `::min_substeps`
- **Floor or band-aid:** keeping the floor in a structure-only step is right, because the digests prove it is
  bit-identical. It is not an honest *accuracy floor of spacing*, though. The floor applies per call: the Fourier
  number per substep is α·T/0.16, which is fixed across spacings only at T = 6 s.
  - `World.advance(seconds)` is public. `advance(0.5)` at 0.05 m takes 64 substeps of 7.8 ms, and `advance(600)`
    takes 64 substeps of 9.4 s.
  - `tests/test_heat.py:23,44` pass `min_substeps(dx)` to 3,600 s calls, where the floor means nothing.
- **What it really is:** the retired rigs' per-call constant, kept for bit-identity.
- **The marker rule:** CLAUDE.md requires that something the plan removes carries
  `TEMPORARY(phase1/sim-clock): …` and a roadmap row. The comment ("plan step 5's fixed physics step replaces it")
  hides it from the marker lint.
- **Numbering:** the comment says step 5, the checklist says 5a.
- **Scheduling:** 5a is the correct place to revisit it. Step 4's harness drives laws with an explicit `dt` and never
  goes through `World` (checklist, step 4), so step 4 is not blocked.
- **Fix:**
  - Add the marker and list `heat.py` under Phase 1 in the roadmap.
  - Reword the comment and the commit claim to "per-call floor kept for bit-identity; accurate only at the 6 s turn".
  - Add the two `test_heat.py` callers to the 5a checklist item.

**S3A-S4. `detail_radius_m` is capability with no caller, and stale docs still describe the forbidden lever.**
`src/simcore/protocol/tiers.py::RigProfile.detail_radius_m`
- **Failure:** WT-1 (`reviews/world_model/wire_trust.md`) said `full_res_radius_m` "must be deleted, not carried
  along as reserved". The rename keeps it, gives it new meaning (client level of detail), and nothing reads it: no
  Python reads it, and nothing under `client/` reads rig files at all.
- **Stale docs:** `docs/architecture.md:135` ("`full_res_radius_m` is reserved for running far cells coarser") and
  `docs/roadmap.md:57` ("run cells beyond `full_res_radius_m` coarser") still describe the D21-forbidden lever, and
  name a field that no longer exists.
- **Fix:**
  - Make rig v1 just `version` and `name`. Add a detail field with the client code that reads it, as a v2 bump.
  - Correct both doc lines.

**S3A-S5. The game package exists before `phase1/lab`, against §2.1, and the deviation isn't recorded.**
`src/maxim_overdrive/`
- **Failure:** §2.1 (W1, W4) says the game package is created with the first game content, "not before". The reason
  it gives: an early package silently collects modules from rebased branches.
- **Why that bites here:** `maxim_overdrive` is the top layer, so a module that lands there escapes the sealed-core
  contract entirely, and several sessions share this repository. Putting `data.py` in the game is a reasonable
  placement (§3), but the commit doesn't say it overrides §2.1.
- **Fix:** record the deviation in the design or the plan. Add a tooling test that pins `maxim_overdrive`'s modules
  to `{__init__, data}` until `phase1/lab`.

## NIT

- **S3A-N1** `pyproject.toml::layers`. Putting protocol above adapters is justified. It matches §2.2, where protocol
  (7c) sits above the membrane (7b), and the order enforces BF-12 (sem ↛ encoding). Its one cost: it merges the 7a
  siblings `loaders` and `tiers` into one direction. `RigProfile.load` becomes the only file gate outside `loaders`,
  which contradicts the commit's "loaders: the file gates", and step 3b's gate registry has to find it there.
- **S3A-N2** `pyproject.toml::tests-out`. The banned list leaves out `tests` and `_pytest`. A shipped module that
  imports `tests.conftest` passes.
- **S3A-N3** `tiers.py::RigProfile.load`. The v0 refusal says "version must be 1, got 0" and doesn't name the move
  that WT-1 asked for ("cell_size_m left the rig, D20"). Someone with a customised rig file gets no hint about what
  changed.
- **S3A-N4** `tests/fixtures/formats/v0/rig.yaml`. Its header says `test_the_committed_v0_files_still_load` holds
  the reader to it, which is no longer true. Correct the claim in the test or in a note beside the fixture.
- **S3A-N5** `world.py::HeatSource.__post_init__`. A comment still cites `config.ActionLimits` and
  `sem_env.bridge`.
- **S3A-N6** `adapters/sem/bridge.py`. It is at 422 of 500 lines. Step 3b's gate/applier split should land before
  anything else is added to it.
- **S3A-N7** `scripts/lint_coverage.py`. Its docstring says "Standards check 4", but `lint_standards.py` numbers
  coverage 3 and sizes 4. Each module does keep one job; the split is clean.
- **S3A-N8** `heat.py::min_substeps`. `round()` rounds halves to even, so at a spacing where 0.16/dx² lands on .5
  the floor is decided by rounding mode rather than by intent. It is deterministic, but `math.ceil` states the
  intent.
