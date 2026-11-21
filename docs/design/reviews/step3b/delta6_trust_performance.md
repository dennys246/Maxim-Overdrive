# Delta round 6: Trust boundary and Performance, step 3b(a)

Scope: `git diff 7cacb3f 2cd24fb`, probed on a `git archive 2cd24fb` copy using the worktree's venv. The worktree is
untouched.

## Status

| id | status | evidence |
|---|---|---|
| D5-S1, numpy and scipy IO | **fixed** | All nine of my rows are refused, by `NUMERIC_NAMES` or by the lint: `np.lib._npyio_impl.load`, `_format_impl.read_array`, `np.rec.fromfile`, `np.core.records.fromfile`, `np.ctypeslib.load_library`, `scipy.sparse.load_npz`, and `__loader__.get_data`, `__spec__.loader.get_data` and `globals()['__loader__']`. A bare `np` passed as a value is also flagged, as `numpy`, so `getattr(np, 'load')` fails closed. |
| D5-S2, re-export through internal modules | **fixed** | My four lines (`from simcore.core.grid import np`, with and without `as n`, and `g.np.load`) are all refused by `internal_reexports`. So is `vars(grid)['np'].load(p)`. |
| D5-N1, `rig_profile` exception type | **fixed** (the registry is honest) | The row now says `partial: a missing rig file raises FileNotFoundError`. `rig_profile("ok")` does raise exactly that. |
| D5-N2, `resolve` | **fixed** | `resolve` moved into `loaders.existing_directory`, and `PATH_ARITHMETIC` no longer lists it. |

## New findings

### SHOULD-FIX

**D6-S1. `tests/_imports.py::ALLOWED`: an allowed standard-library module's own imports are a re-export route the
allowlists don't hold. Plain attribute chains in the core reach the filesystem, the environment and pickle.**

`internal_reexports` follows chains only through `simcore` and `maxim_overdrive`. `NUMERIC_NAMES` covers only
numpy and scipy. The other modules the core is allowed carry modules of their own:
- `reprlib.builtins`
- `dataclasses.sys`
- `contextlib.os`
- `contextlib.sys`
- `typing.sys`
- `collections._sys`

Each of these passes all three checks (grimp allowlist, lint, re-export and numeric scans) in
`src/simcore/core/x.py`:

| Line | What it does |
|---|---|
| `import reprlib; t = reprlib.builtins.open(p).read()` | reads a file |
| `import contextlib; e = contextlib.os.environ.get('X')` | reads the environment |
| `import dataclasses; b = dataclasses.sys.modules['pickle'].loads(raw)` | unpickles |
| `from dataclasses import sys; e = sys.modules['os'].environ` | reads the environment; grimp records only `dataclasses` |
| `import typing; a = typing.sys.argv` | reads the command line |
| `import collections; m = collections._sys.modules['os']` | reaches `os` |

None of this is inside a stated blind spot. Each is a static attribute chain or a `from` import of a module
attribute, which is exactly what the fold refuses for internal modules. The `maxim` allowance in the membrane has the
same shape, since `maxim.*` is a whole package.

Fix: apply the `_hop` rule to every allowed external. Refuse any attribute chain, or `from m import n`, that reaches
an object that is a module, or that `m` only imported. The cleaner fix is a dotted-name list per external, like
`NUMERIC_NAMES`; the core uses about a dozen names outside numpy and scipy. Add the six lines above as corpus rows.

### NIT

**D6-N1.** `internal_reexports` covers `getattr(m, 'n')` only with a literal name. In `maxim_overdrive`, where the
lint's computed-`getattr` rule doesn't run, `getattr(grid, 'n' + 'p')` passes. This is a name built at run time, a
stated blind spot. Corpus row: `from simcore.core import grid` then `a = getattr(grid, 'n' + 'p').load(p)` in
`src/maxim_overdrive/`, verdict "blind spot".

## Performance

No runtime path changed. `existing_directory` adds one `realpath` at startup. The new scans call `importlib` and
`ast` per route at test time only.

## Counts

- My delta-5 findings: 4 fixed, 0 open.
- New: **0 BLOCKER, 1 SHOULD-FIX** (D6-S1, a concrete route to file, environment and pickle from the core), **1
  NIT**.
