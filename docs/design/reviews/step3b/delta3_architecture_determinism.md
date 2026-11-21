# Third delta round: Architecture, and Determinism and replay — `git diff a3d7b07 d9b22d8`

Every result below comes from my own probes on `git archive` exports of d9b22d8, a3d7b07 and fa27d5f in the scratchpad
(`delta3_copy`, `a3_copy`, `base3`, plus `cyl3.py`). The worktree was not touched.

## Status

| id | status | evidence |
|---|---|---|
| D1 (attribute chains through module objects) | **fixed** | I re-planted both root-package spellings: `import simcore` with `simcore.core.frames.damage.region_breached(...)` in `protocol/encoding.py`, and `from simcore import core as _core` with `_core.applier.damage.strike` in `adapters/sem/bridge.py`. import-linter still reports "8 kept" (it can't see attributes), but `test_nothing_outside_the_core_imports_a_forbidden_module_through_an_allowed_one` now goes **red** for both. Both spellings are permanent cases in `test_the_reexport_scan_catches`. The agreed stance is written plainly in three places: `applier.py`'s module docstring, the comment block above `PEEKS` in `tests/test_ownership.py`, and boundaries §10's as-built note. They say capability passing is the guard, and the scans are tripwires that don't follow values, local aliases, `getattr`, default arguments or `sys.modules`. Judged against that stance, D1 is closed. |
| N-1 (`holding` invisible to the scans) | **fixed** | `window_openers` counts `holding`, and `PEEKS` includes it. A planted `with g.holding():` in the bridge turned `test_..._reach_no_world_state_by_attribute` and `test_only_the_named_owners_open_the_write_window` red. Both are permanent catch tests. |

Unplanted, the targeted `tests/test_ownership.py` and `tests/test_determinism.py` pass (147; the subprocess and
hash-seed tests were deselected because the machine was loaded).

## Determinism: the knife-edge cylinder and the box scene

Setup: a cylinder at (1.5, 1.5), z 0 to 0.8 m, radius √0.08 = 0.28284271247461895 m, beside the concrete wall. The
scene is ignited, then advanced 5 turns, using `tests.test_determinism.digest`.

| tree | 0.2 m barrel cells | 0.2 m cylinder digest | 0.2 m box-scene digest | 0.1 m cells / digest |
|---|---|---|---|---|
| fa27d5f | 20 | `f1460e37…` | `f7429cba…` | 192 / `99126e09…` |
| a3d7b07 (`r*r`) | **24** | `55231b56…` | `f7429cba…` | — |
| d9b22d8 (`r**2`) | 20 | `f1460e37…` | `f7429cba…` | 192 / `99126e09…` |

The builder's report is confirmed. a3d7b07 changed this barrel from 20 cells to 24 at 0.2 m, and d9b22d8 restores
fa27d5f's bytes for this scene at 0.2 and 0.1 m and for the box scene. My round-2 D4 said `r*r` was "the better one".
On this machine it changed an outcome against fa27d5f, which the Box-only digest could not show. The revert is right
for this branch.

## New findings

**Counts: 0 BLOCKER, 0 SHOULD-FIX, 1 NIT.**

### N-2 (NIT) The revert keeps this machine's bytes, but `radius_m**2` is the platform-dependent form
`src/simcore/core/scene.py::Cylinder.mask` (its comment); `tests/test_determinism.py::test_a_cylinder_mask_squares_its_radius_as_fa27d5f_did`

At the knife edge, on this machine:
- `r**2` = `0.07999999999999996`, and `math.pow` gives the same.
- `r*r` = `0.07999999999999997`.
- The corner cells' `(x−cx)² + (y−cy)²` = `0.07999999999999996`.

So the outcome turns on how `pow` rounds. Python's float `**` calls libm `pow`, which this macOS build doesn't
round correctly for this input. `r*r` is a single IEEE multiply, the same on every platform. On a libm whose `pow`
returns the correctly rounded square, fa27d5f's own code gives 24 cells here, not 20. So "matches fa27d5f" holds per
machine, not across machines.

The test's comment says honestly that it can't distinguish the two where `pow` rounds exactly. But `scene.py`'s
comment reads as though `r**2` were the stable choice and `r*r` the one that "would move knife-edge cells". It's the
other way round across platforms. CLAUDE.md promises only the outcome class across machines, so this breaks no rule.
But it matters the day replay goldens are first recorded ("on one numerical stack").

*Suggestion:* say this in the `scene.py` comment. Then schedule the switch to `r*r` (or to `np.square`, a single
multiply) for the moment goldens are first committed (step 5a's intent log), as a recorded outcome change. That
beats keeping a libm-dependent threshold for good. Knife-edge authored radii are also a resolution-rule smell: a
binary inside/outside decided at a cell centre lying exactly on the boundary is what the outcome margin exists for.

## Architecture notes, no finding

- The fold kept the scans as tripwires and did not grow them into a reachability analysis, which matches the agreed
  stance. Its stated blind spots match what my round-2 probes found (alias, `getattr`, default argument, tuple
  assignment, `sys.modules`).
- The `repr_bool` change (`repr(bool(x))`) and the frames docstring's "whether or not the window changed a cell" are
  accurate against the code.
- `scripts/lint_inputs.py` and the new `tests/test_lint_inputs_corpus.py` belong to the Trust lens. I read them only
  for layering, and found no import of `src/` internals that would invert the layers.
