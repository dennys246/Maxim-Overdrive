# Delta round 4: Trust boundary and Performance, step 3b(a)

Scope: `git diff d9b22d8 3b0918a`, probed on a `git archive 3b0918a` copy (worktree venv, `lint-imports --no-cache`,
planted modules in a second copy). The worktree is untouched.

## Status

| id | status | evidence |
|---|---|---|
| D3-S1, missing input primitives | **fixed**, with new gaps listed under D4-S1 | Every one of my 12 rows is refused. `os`, `io`, `zipfile`, `urllib`, `sqlite3`, `mmap`, `posix`, `nt`, `pkgutil` and `asyncio` are now forbidden imports in the contract. `np.memmap` and `np.fromregex` are in `IN_SRC`. A planted `import os` breaks the contract (control). |
| D3-S2, false positives on bound names | **fixed** | `bound_names` resolves only unbound names. None of these is flagged any more: a parameter `input`, `open`, `code`, `pickle` or `ctypes`; a local `json`, `marshal` or `code`; `re.compile`; `m.compile()`; `r.code`. An unbound bare `code` is still flagged, which is correct. The real tree has 0 findings. |
| D3-N1, unsafe spellings | **fixed** | Caught: `np.load(f, *a)`, `read_array(f, True)`, `runpy`, `code`, `FunctionType(compile(...))`, `ctypes`, `jsonpickle`, and `L(f, None, True)` with `load` aliased. `attrgetter` is recorded in `NOT_COVERED`. |

## The design

**The four ignores are justified, and minimal.**
- `loaders -> pathlib` and `loaders -> yaml` are the gate itself.
- `tiers -> pathlib` only wraps a path for `read_yaml`, and `tiers` sits above `loaders` in the layers, so it can't
  move there.
- `data -> pathlib` is the game saying where its data lives. However, it calls `is_dir()`, and `rig_profile(name)`
  joins an unchecked name into a path. See D4-N2.

**Giving up the seven rows is sound** (capability passing: with file, stream and socket constructors forbidden, the
engine reads only through objects a gate hands it; an unbound `getenv` is a `NameError`). One exception: a computed
`getattr` on an allowed module, `getattr(np, name)(p)`, reaches `numpy.load` unseen (D4-N1).

**The `__import__` route is closed.** `__import__('os').environ`, `__builtins__['__import__']('os')`,
`globals()['__builtins__']['__import__']` and `getattr(__builtins__, 'open')` are all caught by the lint.
`importlib`, `sys.modules` and `vars(builtins)` all need an import the contract forbids.

**Re-export from a gate is open.** That is D4-S2.

## New findings

### SHOULD-FIX

**D4-S1. `pyproject.toml::input-primitives`: the denylist misses standard-library modules, a dependency and numpy
entry points that read files, the environment, the network or processes.**

Every module below, planted in `src/simcore/protocol/`, passed both the contract and the lint:

- **Filesystem:** `_io`, the C module behind `io` (`_io.open(p).read()`); `xml.etree.ElementTree.parse(p)`;
  `inspect.getsource`; `genericpath.exists`; `wave.open`; `logging.config.fileConfig`; `zipimport`.
- **Environment and host:** `posixpath.expanduser`, which reads `HOME`; `platform.node()`; `getpass.getuser()`;
  `pwd`; `locale`; `sysconfig`; `site`; `netrc`.
- **Network and processes:** `_socket`, `_posixsubprocess`, `concurrent.futures.ProcessPoolExecutor`, `signal` and
  `fcntl`.
- **Third-party:** `scipy.io.loadmat`, which ships, since scipy is a dependency; `np.lib.npyio.load`, because
  `IN_SRC` has `numpy.load` but `np.lib.npyio.load` is a different dotted name; `np.lib.npyio.NpzFile`; and
  `np.DataSource().open(url)`, which reads from the network.

A standard-library denylist can't be completed. The root fix is an allowlist: `src/` imports only `__future__`,
`collections(.abc)`, `contextlib`, `dataclasses`, `math`, `numbers`, `reprlib`, `types`, `typing`, `numpy(.typing)`,
`scipy` (`special`, `ndimage`), `maxim` (in the membrane) and `simcore`. A tooling test holding every `simcore` and
`maxim_overdrive` import to that set, plus the gates' named extras, refuses `_io`, `xml` and `scipy.io` until
justified. Until then, add the modules above to the denylist and the numpy names to `IN_SRC`, each a corpus row with
verdict "input".

**D4-S2. `tests/test_ownership.py::_forbidden_for`: the re-export scan doesn't cover `input-primitives`, so a module
can import a forbidden module through a gate.**

The contract sets `allow_indirect_imports = true`. The re-export scan only reads the `skip-layer` and
`membrane-reads-frames` contracts. So these lines, in `src/simcore/protocol/` or in `maxim_overdrive`, pass the
contract, the lint and the scan:
- `from simcore.adapters.loaders import Path; Path(p).read_text()`
- `from simcore.adapters.loaders import yaml; yaml.safe_load(s)`
- `from simcore.adapters import loaders; loaders.yaml.safe_load(s)`

`tiers` and `data` re-export `Path` the same way.

Fix: add `input-primitives` to `_forbidden_for`, exempting each ignore's own module. Add the three lines above as
corpus or scan rows.

### NIT

- **D4-N1.** `scripts/lint_inputs.py::_unsafe_call` uses dotted-name equality for its positional and starred checks.
  Corpus rows that still pass: `np.lib.npyio.load(f, None, True)`, `np.lib.npyio.NpzFile(f, True)`,
  `functools.partial(np.load, mmap_mode=None)(f, None, True)` (all three caught by prefix matching; the keyword
  forms already are), and `getattr(np, name)(p)` in `src/`, which needs a computed `getattr` on an imported module
  refused.
- **D4-N2.** `src/maxim_overdrive/data.py::rig_profile` has no row in the gate registry. It is now one of the
  contract's three exempt filesystem readers, but it is not in `INPUT_GATES`. It also builds a path from an
  unchecked `name`: `rig_profile("../../x")` reads any `*.yaml` the process can reach. The name is an operator flag,
  so the risk is low. Check it against `[A-Za-z0-9_-]+` and give the function a row.

## Performance

`check_inputs` over 95 files takes 767 ms of CPU (minimum of 3), down from 1.26 s at d9b22d8, because the tables are
smaller.

## Counts

- My delta-3 findings: 3 fixed, 0 open.
- New: **0 BLOCKER, 2 SHOULD-FIX** (D4-S1, D4-S2), **2 NIT**.
