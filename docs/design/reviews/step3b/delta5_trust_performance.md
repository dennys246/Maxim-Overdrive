# Delta round 5: Trust boundary and Performance, step 3b(a)

Scope: `git diff 3b0918a 7cacb3f`, probed on a `git archive 7cacb3f` copy using the worktree's venv. On the copy,
`test_input_allowlist.py` and the corpus pass (236).

**Correction first.** My D4-N1 row `np.lib.npyio.NpzFile(f, True)` was wrong. `NpzFile`'s second positional is
`own_fid`, and `allow_pickle` is third, which is what `PICKLE_POSITION` now encodes.

## Status

| id | status | evidence |
|---|---|---|
| D4-S1, the denylist missed modules | **fixed** | Each layer's allowlist now comes from grimp's graph, and every module I planted in round 4 is a permanent plant (`PLANTS`, plus the core `os` plant and a gate given `importlib`). |
| D4-S2, re-export through a gate | **fixed for the gates** | `gate_reexports` holds importers of `loaders` and `data` to `__all__`, both by `from` import and by attribute. All six of my spellings are permanent rows. The same hole is still open through modules that aren't gates (D5-S2). |
| D4-N1, positional `allow_pickle` and computed `getattr` | **fixed** | Refused: `np.lib.npyio.load(f, None, True)`; `getattr(np, n)(p)` in `src/simcore/`; and `partial(np.load, ...)` in `src/`, which is caught there by `numpy.load` and named outside `src/` as a blind spot. |
| D4-N2, `rig_profile` | **fixed**, with a new NIT (D5-N1) | Refused as `ValueError`: `../etc/passwd`, `/abs`, `a/b`, `..`, `rig\x00` and `rig\n`. It has a registry row. |

**The removed denylist contract lost nothing:** it covered the same two packages and never reached `scripts/` or
`tests/`, where `lint_inputs` still runs.

**Dynamic import stays closed:** the lint catches `__import__`; `importlib` and `sys` are in no allowlist.

## New findings

### SHOULD-FIX

**D5-S1. `scripts/lint_inputs.py::IN_SRC`: the numpy and scipy half of the rule is still a denylist, so the
allowlist's "fail closed" claim doesn't hold there, and a module global reads files with no import at all.**

All of these pass in `src/simcore/protocol/`:

| Spelling | What it does |
|---|---|
| `np.lib._npyio_impl.load(p)` | numpy 2's implementation module, not under `numpy.lib.npyio` |
| `np.lib._format_impl.read_array(f)` | the same, for the `.npy` format reader |
| `np.rec.fromfile(p)` | reads a file |
| `np.ctypeslib.load_library('x', '.')` | loads native code: a code runner, not only input |
| `scipy.sparse.load_npz(p)` | reads a file |
| `__loader__.get_data(p)` | reads any file the process can see, with no import and no builtin |
| `__spec__.loader.get_data(p)`, `globals()['__loader__'].get_data(p)` | the same |

Add each one as a corpus row. The root fix matches the rest of the fold: an allowlist of the numpy and scipy
attributes `src/` actually uses, held by a
test. Also add `__loader__` and `__spec__` to `IN_SRC`, and `numpy.ctypeslib` to `EVERYWHERE`.

**D5-S2. `tests/_imports.py::gate_reexports`: only gates are held to `__all__`, so any internal module re-exports
its externals to a layer whose allowlist refuses them, and the lint loses the numpy name on the way.**

| Line | Result |
|---|---|
| `from simcore.core.grid import np` in `simcore.adapters.sem` | `sem`'s allowlist names no numpy, so this gives `sem` all of numpy. Grimp records the import as internal. |
| `from simcore.core.grid import np as n; n.load(p)` | the lint's alias table resolves `n` to `simcore.core.grid.np`, not `numpy`, so `np.load` passes |
| `from simcore.core.grid import np; np.load(p)` | the same: the import overrides the lint's default `np → numpy` |
| `import simcore.core.grid as g; g.np.load(p)` | the same |

Fix: generalize `gate_reexports` to every internal module, refusing any name that is, or comes from, an external
module outside the importer's own allowlist. (`tests/test_ownership.py::reexports` already resolves origins.) Add the four lines as rows.

### NIT

- **D5-N1.** `src/maxim_overdrive/data.py::rig_profile` is registered as "meets", which promises `ValueError` only.
  But a well-formed name for a rig that doesn't exist (`rig_profile("ok")`) raises `FileNotFoundError` from
  `loaders.read_yaml`, which catches only YAML errors and `ValueError`. Map an `OSError` to `ValueError` in
  `read_yaml`, or mark the row partial.
- **D5-N2.** `tests/_imports.py::PATH_ARITHMETIC` includes `resolve`. That is not pure arithmetic: it calls
  `realpath` and stats the filesystem. Name it as the one exception.

## Performance

The allowlist runs grimp in a subprocess, once per tree; both test modules took about 1 s. No hot path changed.

## Counts

- My delta-4 findings: 4 fixed (one with a remaining part, carried as D5-S2), 0 open.
- New: **0 BLOCKER, 2 SHOULD-FIX** (D5-S1, D5-S2), **2 NIT**.
