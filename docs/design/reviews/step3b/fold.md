# Step 3b part (a) review: fold, delta rounds

Round 1's and delta round 1's fold records are in `fold_round1.md`, delta round 2's in `fold_round2.md`. The reports are `executor_wire.md`, `architecture_determinism.md`,
`trust_performance.md` and their `delta_` and `delta2_` rounds. Reviewers set every status (O25); the author sets none.

## Delta round 3

Each status table below is copied verbatim from its report.

### Executor and Wire integrity: status set by the Executor and Wire integrity reviewer (O25)

| id | status | evidence (mutation → result) |
|---|---|---|
| N-d: the cylinder rerun test can't see a geometry change | **fixed** | `Cylinder.mask` returns to `radius_m**2`, as on fa27d5f. The rerun test is renamed `test_a_cylinder_scene_is_repeatable_in_process`, which no longer claims more than it does. The new `test_a_cylinder_mask_squares_its_radius_as_fa27d5f_did` pins the mask at the knife-edge radius. Each of these turns it red: `r*r`; `<=` instead of `<`; `radius*1.001`. Its comment states the limit: where pow rounds exactly, the two formulas agree and the test can't tell them apart (so on another libm the `r*r` mutation could pass). |
| N-e: frames.py "published when they change" | **fixed** | The docstring now says frames are published after each window closes, "whether or not the window changed a cell". That matches `World.writing`. |

### Architecture, and Determinism and replay: status set by the Architecture and Determinism reviewer (O25)

| id | status | evidence |
|---|---|---|
| D1 (attribute chains through module objects) | **fixed** | I re-planted both root-package spellings: `import simcore` with `simcore.core.frames.damage.region_breached(...)` in `protocol/encoding.py`, and `from simcore import core as _core` with `_core.applier.damage.strike` in `adapters/sem/bridge.py`. import-linter still reports "8 kept" (it can't see attributes), but `test_nothing_outside_the_core_imports_a_forbidden_module_through_an_allowed_one` now goes **red** for both. Both spellings are permanent cases in `test_the_reexport_scan_catches`. The agreed stance is written plainly in three places: `applier.py`'s module docstring, the comment block above `PEEKS` in `tests/test_ownership.py`, and boundaries §10's as-built note. They say capability passing is the guard, and the scans are tripwires that don't follow values, local aliases, `getattr`, default arguments or `sys.modules`. Judged against that stance, D1 is closed. |
| N-1 (`holding` invisible to the scans) | **fixed** | `window_openers` counts `holding`, and `PEEKS` includes it. A planted `with g.holding():` in the bridge turned `test_..._reach_no_world_state_by_attribute` and `test_only_the_named_owners_open_the_write_window` red. Both are permanent catch tests. |

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| D2-B1, names inside a chain | **fixed** | Every row of my delta-2 table is caught: `os.environ.get` and `.copy()`, `environ.get` after `from os import environ`, `sys.stdin.read()` and `.readline()`, `sys.argv.copy()`, `__builtins__.eval`, `__builtins__.__import__('pickle')`, `builtins.__dict__.get('eval')` and `yaml.Loader.add_constructor`. |
| S1 (round 1), lint_inputs evasions | **fixed** for every spelling any round reported | All 40 round-1, delta-1 and delta-2 unsafe spellings are caught. The only exceptions are the five the docstring now names as blind spots or that need no ban: `importlib.util` loaders, `copyreg`, `__loader__`, `type(x).__init__` and `pickletools.dis`. The real tree is clean (0 findings). The remaining gaps are new spellings (D3-S1, D3-N1). |
| D2-N1, `importlib.__import__`, `sys.modules[...]`, `globals()`, `ForkingPickler` | **fixed** | All four are caught. |
| D2-N2, numpy bool echo | **fixed** | `shown([np.bool_(True), np.float64(2.5)])` gives `[True, 2.5]`. |
| B1, the cylinder overflow (re-checked after `radius_m**2` returned) | **still fixed** | A 1e200 radius is refused as `SpecRejected` by the 1 km bound before any arithmetic, and a 1,000 m radius is refused as "too large: 2000.00 m". |

### The design change: the contract is the rule, the lint covers what imports can't show

This is the fourth round to find new holes in `lint_inputs`, so the rule is now structural rather than enumerated.

- **The `input-primitives` import contract is the load-bearing rule for modules.** Outside the file gates, nothing
  in `simcore` or `maxim_overdrive` imports a module that reads files (`os`, `posix`, `nt`, `io`, `pathlib`,
  `zipfile`, `mmap`, `sqlite3`, …), the environment (`os`, `sys`), the network (`urllib`, `http`, `socket`,
  `asyncio`, …) or processes (`subprocess`, `multiprocessing`), or that runs code by name (`importlib`, `runpy`,
  `code`, `ctypes`, `builtins`), or that decodes (JSON, YAML, TOML, INI, pickles).
  - Exactly four imports are ignored, each justified in the contract's comment: `loaders` imports `pathlib` and
    `yaml`, `data` imports `pathlib`, and `tiers` imports `pathlib` (it hands a path to `read_yaml`).
  - One planted import per family is a permanent test (`tests/test_tooling_config.py::PLANTED`). One of them is an
    extra import in a gate, which proves a gate is granted only what it is listed for.
- **`lint_inputs` shrinks to closed lists:**
  - the builtins (`open`, `input` and `__import__` in `src/`; `eval`, `exec` and `compile` everywhere), where a
    bare name counts only when the module doesn't bind it (D3-S2);
  - numpy's IO;
  - the decoders and code runners, banned everywhere because the contract doesn't reach `scripts/` and `tests/`.
- **The corpus judges every row by the contract and the lint together.** Each input row is planted as a module in a
  copy of `src/`, and the gate's own import command runs once over all of them. Rows the design deliberately leaves
  out are listed in `NOT_COVERED`, each with its reason, and asserted to stay unflagged.

Measured on the corpus (154 rows):
- **With d9b22d8's contract and lint:** 33 rows are wrong.
  - It gets 26 delta-3 rows wrong: D3-S1 misses, D3-S2 false positives, D3-N1 misses, and the `eval` local.
  - It flags 7 rows that the new design deliberately stops flagging: methods on an object handed in
    (`path.read_bytes()`, `sock.recv()`), an unimported `getenv`, and a computed `getattr`.

  Those 7 are coverage the old lint had and this design gives up, each for its stated reason.
- **With this fold:** 0 rows are wrong.

### New findings, and what changed

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D3-S1 | the widened `input-primitives` contract above; the corpus rows from D3-S1 (`os.read`, `os.fdopen`, `io.FileIO`, `np.memmap`, `np.fromregex`, `zipfile`, `urlopen`, `sqlite3`, `mmap`, `posix`/`nt.environ`, `pkgutil`, `asyncio`, `tarfile`, `importlib.resources`) | d9b22d8 misses them; reverted (memmap: red); planted, one per family (red) | open |
| Trust D3-S2 | `lint_inputs.bound_names`: a parameter, assignment, loop or `with` target, `def`, `class` or `except` name is the module's own; the five rows from D3-S2 and `eval = model.evaluate()` are clean rows | d9b22d8 flags them; reverted (4 red) | open |
| Trust D3-N1 | starred and `**` arguments to `numpy.load`/`read_array`, `read_array`'s positional `allow_pickle`, `runpy`, `code`, `ctypes`, `jsonpickle` and `compile` are caught. The star import and `operator.attrgetter` are in `NOT_COVERED` (ruff's F403; a name as a value) | d9b22d8 misses them; reverted (red) | open |
| Arch N-2 | `scene.py`'s comment: `r*r` is the single correctly rounded multiply and `radius_m**2` the libm-dependent form, kept only to match fa27d5f. Backlog B28: voxelize by volume overlap, with no knife edge, at step 4 or 5a, with this case as its evidence | — (docs) | open |
| Exec N-f | the knife-edge test also asserts the outcome: fa27d5f's 20 cells where `pow` differs from `r*r`, and the 24 that fa27d5f's own code gives where `pow` is exact (no skip) | reverted (`r*r`: red) | open |


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
