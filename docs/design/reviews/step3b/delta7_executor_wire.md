# Delta round 7, step 3b(a): Executor and Wire integrity

**Range:** `git diff 2cd24fb`, the uncommitted fold.

**Method:** an rsync copy (no `.venv`, no `.git`) with the worktree's venv. The baseline is green: input_allowlist,
corpus, lint_gates, validation and act_validation (694 tests). Harness: `_durable/3b_review/delta7_mutate.py`.

## N-h: fixed

Each mutation turns `test_a_symlinked_package_finds_the_data_beside_the_real_package` red:

| mutation | red |
|---|---|
| `real_path` returns `Path(path)` unresolved | yes |
| `existing_directory` returns `Path(candidate)` unresolved | yes |
| `data_dir` skips `real_path` | yes |

Each of the three resolutions is pinned by its own assertion.

## Can the new tests fail?

### `EXTERNAL_NAMES` and its exactness check

| plant | red |
|---|---|
| `import contextlib` + `contextlib.os.environ` in heat | the layer check and the exactness check. grimp allows `contextlib`, so only the name list catches it. |
| an unlisted `math.e` in heat | the same two tests |
| an unused `math.e` entry in the core list | the exactness check |
| the attribute-chain rule reverted to numpy and scipy only | 12 tests, including every `test_a_module_reached_through_an_allowed_one_is_refused` case |

### The six core-planted corpus rows

Under that same reverted rule, run against the corpus alone, five of the six turned red (rows 109, 110, 111, 113 and
114). Row 112 (`from dataclasses import sys`) stays green there, and that is correct: it is held by the
`from x import y` branch, which my mutation left alone.

Planting the corpus rows in `protocol` instead of beside their own module turns row 115 red. That row is the clean
`import math; math.sqrt(2.0)` in the core, which the protocol's list doesn't allow. So the beside-the-module placement
is load-bearing and tested.

### The symlink test

All three mutations above turn it red.

## Wire: caller-visible changes

| symbol | change | callers | effect |
|---|---|---|---|
| `loaders.real_path(path)` (new; in `__all__`; registry row "no input") | — | `data.data_dir` | New API. |
| `data.data_dir(here=None)` | resolves `here` before any path arithmetic | tests, `materials()`, `action_limits()`, `rig_profile()` | This restores the symlink behaviour from before fold 6: a symlinked package finds `data/` beside the real package. With a real `__file__`, the result is unchanged. |
| `loaders.existing_directory` | still returns a resolved path | `data_dir`, tests | Unchanged from 2cd24fb; now pinned. |
| `scripts/lint_inputs.py` | comments only (`NUMERIC_NAMES` → `EXTERNAL_NAMES`) | — | None. |

No signature changed. The README, scripts and the Godot gate are unaffected.

## New findings

**0 BLOCKER, 0 SHOULD-FIX, 0 NIT.**

I checked whether `external_names` loses a name hidden behind a call, such as `math.sqrt(2.0).hex()`. The
`math.sqrt` chain is still recorded, and a method on the call's result is the stated "methods on values" blind spot.
I found nothing new in this fold under the Executor or Wire integrity lens.
