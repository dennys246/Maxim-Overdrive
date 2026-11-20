# Delta round 6, step 3b(a): Executor and Wire integrity

**Range:** `git diff 7cacb3f 2cd24fb`.

**Method:** a `git archive 2cd24fb` copy with the worktree's venv. The baseline is green: input_allowlist, corpus,
lint_gates, validation and act_validation (677 tests). Harness: `_durable/3b_review/delta6_mutate.py`. Every plant
uses a private name, so the gate registry is not the thing that goes red.

## N-g: fixed

| replant | red |
|---|---|
| tiers: `path.read_text()` on the handed-in path | `test_a_path_holder_..._what_it_names[tiers]` |
| data: `getattr(Path(p), 'read_text')()` | the path-holder test for data, plus a corpus row |
| tiers: `getattr(loaders, 'Path')(p)` | the gate-API check, the path-holder test and the re-export rule (3 tests) |

## Can each new test fail?

All red:

| guard | plant |
|---|---|
| numeric allowlist | `np.rec.fromfile(p)` in heat; `np.load(p)` in encoding |
| numeric "exactly today" | an unused `numpy.cumsum` in the core list |
| any-module re-export rule | `from simcore.core.frames import np`; `_F.np.load`; `getattr(_F, 'np')`, each in bridge |
| tiers path-holder allowlist | `path.is_file()`; the handed-in `read_text` |
| `resolve` removed from path arithmetic | `.resolve()` restored in `data_dir` turns the data path-holder test red |

Two plants of mine went red for the wrong reason:

- `getattr(np, 'load')(p)`: the bare `np` is itself an unlisted name.
- `a.tofile(p)` with `a: np.ndarray`: the annotation `numpy.ndarray` is unlisted.

Re-planted without the annotation, `a.tofile(p)` stays **green**. That is the stated "methods on arrays are values"
blind spot, not a finding.

**One mutation stays green:** `existing_directory` returning `Path(candidate)` instead of
`Path(candidate).resolve()`. Nothing pins the new resolve (N-h).

## Wire: caller-visible changes

| symbol | change | callers | effect |
|---|---|---|---|
| `loaders.existing_directory` | returns the resolved directory | `data.data_dir`; its own test | Intended: the filesystem read moved into the gate. |
| `data.data_dir(here=None)` | no longer resolves `here` first; the gate resolves the candidate it finds | tests, `materials()`, `action_limits()`, `rig_profile()` | Same result when `__file__` is a real path. It differs when the package directory is reached through a symlink: before, `parents[1]` of the *resolved* directory was the checkout; now it is `parents[1]` of the link's location. A symlinked checkout (`site-packages/maxim_overdrive → repo/src/maxim_overdrive`) used to find `repo/data` and now finds no data, unless `_data` is present. Rare (editable installs give a real `__file__`), but it is a change. |
| `scripts/lint_inputs.py` `IN_SRC` | numpy and scipy IO names removed; `__loader__` and `__spec__` added | `check_inputs`, the corpus | numpy IO is now held by the per-layer numeric allowlist (shown red above). The coverage moved; it didn't vanish. |
| `tests/_imports.py` API | `data_attribute_violations` → `path_holder_violations(module, source)` | `test_input_allowlist` only | Internal to the tests. |

No `src` signature changed. The README, the Godot gate and the scripts are unaffected.

## New findings

**0 BLOCKER, 0 SHOULD-FIX, 1 NIT.**

### N-h. NIT: `src/simcore/adapters/loaders.py::existing_directory`: the `resolve()` this fold moved into the gate has no guard

Removing it leaves all 677 tests green. Without it, `data_dir()` would return an unresolved path. That is harmless
with a real `__file__`, but it is the exact behaviour the fold moved on purpose.

There is also the symlink difference described in the wire table. `here.parents[1]` is now taken before resolving,
so a symlinked package directory finds a different checkout candidate than before.

One test closes both: make `here` a symlink to a `src/maxim_overdrive` directory inside a temporary checkout, then
assert two things:

- `data_dir(here)` is the real `data` directory (`.resolve()` of the target), so removing the gate's `resolve` goes
  red;
- the intended behaviour for a symlinked package is stated either way, matching what the fold decided.
