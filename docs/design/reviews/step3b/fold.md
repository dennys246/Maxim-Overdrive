# Step 3b part (a) review: fold, delta rounds

Round 1's and delta round 1's fold records are in `fold_round1.md`, delta rounds 2 and 3's in `fold_round2.md`. The reports are `executor_wire.md`, `architecture_determinism.md`,
`trust_performance.md` and their `delta_` and `delta2_` rounds. Reviewers set every status (O25); the author sets none.

## Delta round 4

Each table below is copied verbatim from its report. The Executor's report has no status table, so its table of
mutations under "Can the new tests fail?" is copied instead.

### Executor and Wire integrity: set by the Executor and Wire integrity reviewer (O25)

Status of N-f: **fixed** (the report's heading).

| family dropped | red |
|---|---|
| `pathlib` | the encoding row, plus `test_only_the_file_gates_read_input_or_decode`, plus a corpus row |
| `urllib` | the `data.py` row, plus a corpus row |
| `subprocess` | the tiers row |
| `asyncio` | the encoding row, plus a corpus row |
| `posix` | the bridge row, plus a corpus row |

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| D3-S1, missing input primitives | **fixed**, with new gaps listed under D4-S1 | Every one of my 12 rows is refused. `os`, `io`, `zipfile`, `urllib`, `sqlite3`, `mmap`, `posix`, `nt`, `pkgutil` and `asyncio` are now forbidden imports in the contract. `np.memmap` and `np.fromregex` are in `IN_SRC`. A planted `import os` breaks the contract (control). |
| D3-S2, false positives on bound names | **fixed** | `bound_names` resolves only unbound names. None of these is flagged any more: a parameter `input`, `open`, `code`, `pickle` or `ctypes`; a local `json`, `marshal` or `code`; `re.compile`; `m.compile()`; `r.code`. An unbound bare `code` is still flagged, which is correct. The real tree has 0 findings. |
| D3-N1, unsafe spellings | **fixed** | Caught: `np.load(f, *a)`, `read_array(f, True)`, `runpy`, `code`, `FunctionType(compile(...))`, `ctypes`, `jsonpickle`, and `L(f, None, True)` with `load` aliased. `attrgetter` is recorded in `NOT_COVERED`. |

### The design change: allowlists, fail closed

Both reviewers found the same root cause: a denylist can't be completed. The rule is now three allowlists
(`tests/_imports.py`). Each names what is permitted, with a reason, so a route nobody named is refused.

- **Each layer's external imports, read from grimp's graph.** This is the graph import-linter checks. Today's
  imports, and nothing else, are allowed: the core gets the numeric set; `loaders` gets `pathlib` and `yaml`; the
  membrane gets `maxim`; the protocol gets `numpy`; `data` gets `re` and `pathlib`. A test also holds each list to
  exactly what its layer imports today.
  - grimp records an external package at its top level (`numpy.lib.npyio` is recorded as `numpy`), so numpy's and
    scipy's IO can't be told apart there. `lint_inputs` names them instead: `np.lib.npyio`, `np.DataSource`,
    `np.lib._datasource`, `scipy.io`, and their positional `allow_pickle`. It also refuses a computed `getattr` in
    `simcore`.
  - The `input-primitives` denylist contract is removed. On direct imports over the same graph, the allowlist is
    strictly stronger, so the contract added nothing.
- **What code outside a gate may take from it: the gate's `__all__`** (`loaders`, `data`). This closes D4-S2's
  re-exports of `Path` and `yaml`.
- **What `maxim_overdrive.data` may use: path arithmetic, plus `re.compile`, `fullmatch` and `RigProfile.load`.**
  `tiers` no longer imports `pathlib`, since a path is a `loaders.FilePath`. `data_dir` asks the new gate
  `loaders.existing_directory` instead of calling `is_dir` itself. Only `loaders` touches the filesystem.

Measured: with 3b0918a's own contract and lint, 33 of the 34 delta-4 rows that must be flagged pass unflagged. The
one it caught is the `pathlib` plant in a new module; S-d's real route went through `tiers`' own ignore.

### New findings, and what changed

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D4-S1 | the per-layer import allowlist; 28 plants in `tests/test_input_allowlist.py`, one per route and family, plus an extra import in a gate; every D4-S1 spelling is a corpus row | 3b0918a misses them; reverted (`os` allowed in the protocol: red) | open |
| Trust D4-S2 | `__all__` on `loaders` and `data`; `test_code_outside_the_gates_takes_only_their_api`, with six plants | reverted (`Path` taken through the gate: red; `Path` in `__all__`: red) | open |
| Exec S-d | `tiers` holds no `pathlib`. `data` is held to path arithmetic, and five filesystem methods are planted red. `sneak` is a corpus row in `tiers` and in `data` | reverted (`pathlib` back in `tiers`: red; `is_dir` in `data`: red) | open |
| Trust D4-N1 | positional `allow_pickle` for `np.lib.npyio.load` and `NpzFile`; a computed `getattr` in `simcore`. `functools.partial` outside `src/` is in `NOT_COVERED` (a function passed as a value) | reverted (red) | open |
| Trust D4-N2 | `data.rig_profile` refuses anything but `[A-Za-z0-9_-]+`, with eight rejection cases, and has a gate-registry row | reverted (8 red) | open |


## Delta round 5

Each table below is copied verbatim from its report.

### Executor and Wire integrity: set by the Executor and Wire integrity reviewer (O25)

S-d status: fixed for the reported route (the report's heading).

| replant | result |
|---|---|
| tiers: `from pathlib import Path` + `Path(path).read_text()` | **red**: `test_every_layer_imports_only_...` and `test_each_allowlist_names_exactly_...` |
| data: `Path(p).read_text()` | **red**: `test_the_data_locator_uses_only_path_arithmetic`, plus a corpus row |
| data: `open(p).read()` | **red**: the data allowlist, a corpus row, and `test_a_planted_open_...` |

Can each new test fail? (the report's mutation table)

| test | mutation |
|---|---|
| per-layer allowlist | `import platform` in `encoding` |
| "exactly what's imported today" | an unused `"json"` entry in core's allowlist |
| `__all__` importer check | tiers taking `Path` from loaders |
| `__all__` contents | adding `"Path"` to loaders' `__all__`: the parametrized refusal cases go red, so `__all__` is effectively pinned |
| `data` path-arithmetic allowlist | adding `is_dir` to `PATH_ARITHMETIC` |
| `rig_profile` rejections (refusing a name such as `../../x`) | the regex as `.*` (7 red); the regex allowing dots (`..` and `rig.yaml` red); `match` instead of `fullmatch` (5 red) |

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| D4-S1, the denylist missed modules | **fixed** | Each layer's allowlist now comes from grimp's graph, and every module I planted in round 4 is a permanent plant (`PLANTS`, plus the core `os` plant and a gate given `importlib`). |
| D4-S2, re-export through a gate | **fixed for the gates** | `gate_reexports` holds importers of `loaders` and `data` to `__all__`, both by `from` import and by attribute. All six of my spellings are permanent rows. The same hole is still open through modules that aren't gates (D5-S2). |
| D4-N1, positional `allow_pickle` and computed `getattr` | **fixed** | Refused: `np.lib.npyio.load(f, None, True)`; `getattr(np, n)(p)` in `src/simcore/`; and `partial(np.load, ...)` in `src/`, which is caught there by `numpy.load` and named outside `src/` as a blind spot. |
| D4-N2, `rig_profile` | **fixed**, with a new NIT (D5-N1) | Refused as `ValueError`: `../etc/passwd`, `/abs`, `a/b`, `..`, `rig\x00` and `rig\n`. It has a registry row. |

### The design change: the last denylist corners become allowlists

- **numpy and scipy by name** (`tests/_imports.py::NUMERIC_NAMES`). Each layer may reach only the dotted numpy and
  scipy names it uses today: 32 in the core and 4 in the protocol, held to exactly that set. They are counted from
  pure attribute chains and imports, through aliases. Methods on arrays are values, a stated blind spot.
  - The lint's numpy and scipy IO denylist is gone. `np.lib._npyio_impl`, `np.rec.fromfile`, `np.ctypeslib` and
    `scipy.sparse.load_npz` are refused because no list names them.
  - `__loader__` and `__spec__` are in the lint's `IN_SRC`, and `numpy.ctypeslib` is in `EVERYWHERE`.
- **Re-export through any internal module** (`internal_reexports`). A name taken from a `simcore` or
  `maxim_overdrive` module must be one it defines (`def`, `class`, assignment) or lists in `__all__`, or be its own
  submodule. This holds for `from m import n`, for an attribute chain through any import of `m`, and for
  `getattr(m, 'n')` with a literal name. `from simcore.core.grid import np` in the membrane is refused, and gates
  stay held to `__all__` by the same routes.
- **Path holders** (`PATH_HOLDERS`). `tiers` joins `data`: each may use path arithmetic and the few calls it names,
  by attribute or by literal `getattr`. `resolve` left path arithmetic, because realpath reads the filesystem; the
  gate `existing_directory` now resolves the directory it finds.

Measured: 7cacb3f's own checkers miss 15 of the 16 delta-5 rows that must be flagged. The one caught is
`scipy.sparse.load_npz` planted in the protocol, which had no scipy import; in the core it would have passed.

### New findings, and what changed

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D5-S1 | `NUMERIC_NAMES` with its exactness test and eight plants; `__loader__` and `__spec__` in `IN_SRC`; `numpy.ctypeslib` in `EVERYWHERE`; every spelling is a corpus row | 7cacb3f misses them; reverted (the check passing everything: 22 red; an unused name: red; `__loader__` dropped: red) | open |
| Trust D5-S2 | `internal_reexports` over every internal module, with six plants; the four rows from the report are in the corpus | 7cacb3f misses them; reverted (imported names counting as defined: 10 red) | open |
| Exec N-g | `tiers` is a path holder; a literal `getattr` counts as an attribute in path holders and as a hop through modules; `path.read_text()` on a path handed in, `getattr(Path(p), 'read_text')` and `getattr(L, 'Path')` are refused | 7cacb3f misses them; reverted (red) | open |
| Trust D5-N1 | `rig_profile`'s registry row now reads `partial: a missing rig file raises FileNotFoundError, not ValueError`, which is what it raises | — (registry) | open |
| Trust D5-N2 | `resolve` left `PATH_ARITHMETIC`; `data_dir` no longer calls it; the gate resolves | reverted (`resolve` allowed again: 3 red) | open |


## Delta round 6

Each table below is copied verbatim from its report.

### Executor and Wire integrity: set by the Executor and Wire integrity reviewer (O25)

| replant | red |
|---|---|
| tiers: `path.read_text()` on the handed-in path | `test_a_path_holder_..._what_it_names[tiers]` |
| data: `getattr(Path(p), 'read_text')()` | the path-holder test for data, plus a corpus row |
| tiers: `getattr(loaders, 'Path')(p)` | the gate-API check, the path-holder test and the re-export rule (3 tests) |

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| D5-S1, numpy and scipy IO | **fixed** | All nine of my rows are refused, by `NUMERIC_NAMES` or by the lint: `np.lib._npyio_impl.load`, `_format_impl.read_array`, `np.rec.fromfile`, `np.core.records.fromfile`, `np.ctypeslib.load_library`, `scipy.sparse.load_npz`, and `__loader__.get_data`, `__spec__.loader.get_data` and `globals()['__loader__']`. A bare `np` passed as a value is also flagged, as `numpy`, so `getattr(np, 'load')` fails closed. |
| D5-S2, re-export through internal modules | **fixed** | My four lines (`from simcore.core.grid import np`, with and without `as n`, and `g.np.load`) are all refused by `internal_reexports`. So is `vars(grid)['np'].load(p)`. |
| D5-N1, `rig_profile` exception type | **fixed** (the registry is honest) | The row now says `partial: a missing rig file raises FileNotFoundError`. `rig_profile("ok")` does raise exactly that. |
| D5-N2, `resolve` | **fixed** | `resolve` moved into `loaders.existing_directory`, and `PATH_ARITHMETIC` no longer lists it. |

### The design change: one name allowlist for every external module

`NUMERIC_NAMES` becomes `EXTERNAL_NAMES` in `tests/_imports.py`: each layer's full list of the dotted external
names it reaches, stdlib included, and a test holds each list to exactly today's use. The lists hold 57 names in
the core, 11 in `loaders`, 10 in the membrane, 7 in the protocol and 3 in `data`.

Names are counted from `from x import y` and from pure attribute chains, through aliases. So an allowed module
can no longer carry another with it: `reprlib.builtins`, `contextlib.os`, `dataclasses.sys` and `typing.sys` are
refused because no list names them. Methods on values stay a stated blind spot.

Measured: 2cd24fb's own checkers miss all 6 D6-S1 rows.

### New findings, and what changed

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D6-S1 | `EXTERNAL_NAMES` with its exactness test; seven plants in `tests/_imports.py`'s tests; the six spellings are corpus rows planted in the core itself, so the core's lists are what refuses them | 2cd24fb misses all 6; reverted (only numpy and scipy held: 12 red; an unused name on a list: red) | open |
| Trust D6-N1 | `getattr(grid, 'n' + 'p')` is a corpus row. It is not in `NOT_COVERED`: in `simcore` the lint refuses any computed `getattr`, so it was already caught at 2cd24fb. Outside `simcore` a run-time name would pass, which is a stated blind spot | caught at 2cd24fb and now | open |
| Exec N-h | the intended symlink behaviour: data is found beside the package's real location, as before fold 6. The new gate `loaders.real_path` resolves `here` before any arithmetic, and `existing_directory` resolves what it returns. `test_a_symlinked_package_finds_the_data_beside_the_real_package` pins both | reverted (each of the three resolutions removed: red) | open |

## Delta round 7

Trust + Performance (`delta7_trust_performance.md`). **Status set by the Trust reviewer (O25):**

| id | status |
|---|---|
| Trust D6-S1 | fixed |
| Trust D6-N1 | fixed in `src/simcore/` (outside it, a stated blind spot, accepted) |

New: 0 BLOCKER, 0 SHOULD-FIX, 2 NIT, both through a value (the stated blind spot). **Author's disposition, not a status:** both deferred as backlog row B29, triggered by plan step 3b part (b), which designs one reader per data format; a code change here would need another round for two NITs.

| id | what | status |
|---|---|---|
| Trust D7-N1 | dunder attributes on a value reach a module's globals | open (deferred, B29) |
| Trust D7-N2 | `data_dir()` hands out an unrestricted `Path` | open (deferred, B29) |

Executor + Wire (`delta7_executor_wire.md`). **Status set by the Executor reviewer (O25):**

| id | status |
|---|---|
| Exec N-h | fixed |

New: 0 BLOCKER, 0 SHOULD-FIX, 0 NIT. **The round converged:** no lens folds anything further in code.
