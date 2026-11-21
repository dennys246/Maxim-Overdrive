# Delta round 5, step 3b(a): Executor and Wire integrity

**Range:** `git diff 3b0918a 7cacb3f`.

**Method:** a `git archive 7cacb3f` copy with the worktree's venv. The baseline is green: `test_input_allowlist`,
the corpus, `test_lint_gates` and `test_validation`, 468 tests. Harness: `_durable/3b_review/delta5_mutate.py`.

Plants appended to `tiers.py` must be private (`_sneak`). A public one turns `test_lint_gates` red for an unrelated
reason (a gate-module entry with no row). My first run made that mistake, so every result below comes from the rerun
with private names.

## S-d status: fixed for the reported route

| replant | result |
|---|---|
| tiers: `from pathlib import Path` + `Path(path).read_text()` | **red**: `test_every_layer_imports_only_...` and `test_each_allowlist_names_exactly_...` |
| data: `Path(p).read_text()` | **red**: `test_the_data_locator_uses_only_path_arithmetic`, plus a corpus row |
| data: `open(p).read()` | **red**: the data allowlist, a corpus row, and `test_a_planted_open_...` |

Two residual routes stay **green** (N-g below).

## Can each new test fail?

All red:

| test | mutation |
|---|---|
| per-layer allowlist | `import platform` in `encoding` |
| "exactly what's imported today" | an unused `"json"` entry in core's allowlist |
| `__all__` importer check | tiers taking `Path` from loaders |
| `__all__` contents | adding `"Path"` to loaders' `__all__`: the parametrized refusal cases go red, so `__all__` is effectively pinned |
| `data` path-arithmetic allowlist | adding `is_dir` to `PATH_ARITHMETIC` |
| `rig_profile` rejections (refusing a name such as `../../x`) | the regex as `.*` (7 red); the regex allowing dots (`..` and `rig.yaml` red); `match` instead of `fullmatch` (5 red) |

The fixture that plants each import (`planted_imports`) runs grimp on a copy with 28 plants plus a core `os` and a
gate `importlib`. Each is asserted individually, so the per-plant cases can't pass vacuously.

## Wire: did public signatures change for any caller?

| symbol | change | callers | intended? |
|---|---|---|---|
| `RigProfile.load(path)` | `str \| Path` → `FilePath` (the same union, now named in loaders) | `data.rig_profile`, tests | Yes. No behaviour change: `read_yaml` does `Path(path)`. |
| `data.data_dir(here=None)` | signature unchanged; the error text is now "no game data (installed, then checkout): none of … is a directory" | tests (regex updated) | Yes. No shipped caller parses the text. |
| `data.rig_profile(name)` | refuses any name outside `[A-Za-z0-9_-]+`, with a `ValueError` | tests only. `git grep` finds no caller in `scripts/`, `client/`, `ci/` or the README, and the Godot gate doesn't load rigs | Yes (Trust D4-N2). The shipped `laptop`, `rig` and `max` all pass. |
| `loaders.__all__`, `data.__all__` (new) | non-gate src may import only these names | src modules (tests are exempt) | Yes. The current src passes. |
| `loaders.existing_directory`, `FilePath` (new) | new API | `data_dir`, tiers | Both are registered gate rows. |
| `input-primitives` import contract | removed; the tests now carry the rule | `lint-imports`, CLAUDE.md's guard citation (updated to the two allowlist tests) | Yes. The citation names tests that exist and go red. |
| README example | uses only `data.materials()` and `data.action_limits()` | — | Unchanged. |

## New findings

**0 BLOCKER, 0 SHOULD-FIX, 1 NIT.**

### N-g. NIT: `tests/_imports.py::data_attribute_violations` and the tiers module: two routes past the new allowlists

Planted with private names, all 468 tests stayed **green** for each of these:

1. **tiers, `path.read_text()` on the `FilePath` handed in.** `RigProfile.load` receives a real `Path` from
   `data.rig_profile`. The allowlists see imports; the lint deliberately doesn't follow values (corpus `NOT_COVERED`:
   "a method on an object handed in"). So the one engine module that holds a path by design could open it, against
   its own docstring ("this only decodes").
2. **`getattr` with a literal name.** `getattr(Path(p), 'read_text')()` in data, and `getattr(_L, 'Path')` on the
   loaders module from tiers. The data allowlist only inspects attribute nodes, and the `__all__` check only inspects
   imports and attribute chains.

Both are the "values and names as values" blind spot the design already states, so this is a NIT, not a SHOULD-FIX.

Cheap closes, if wanted:

- apply `data_attribute_violations`-style attribute allowlisting to `tiers` (its body needs none of the path methods);
- make the data allowlist refuse a `getattr` whose literal names an attribute outside `DATA_ATTRIBUTES`.

Pin both spellings in the corpus with their verdicts either way.
