# Step 3b part (a) review: fold, delta rounds 2 and 3

## Delta round 2

Each status table below is copied verbatim from its report.

### Executor and Wire integrity: status set by the Executor and Wire integrity reviewer (O25)

| id | status | evidence (mutation → result) |
|---|---|---|
| S-a: two independent window locks | **fixed** | `CellStore.holding()` and `writing()` share `_refuse_a_second_owner`. Each of these turns a test red: `holding` ignoring an open grid window (`test_one_window_at_a_time_and_none_at_rest`); `writing` ignoring `holding` (`test_the_grid_window_and_the_sources_window_share_one_owner`); a sources-only window that takes no lock (same test). An ignite inside a raising grid window is now refused with `WindowClosed`, and nothing commits. |
| S-b: stale "every application publishes" claims | **fixed** (by restoring the claim rather than the texts) | A sources-only window publishes again, on the same immutable owners. Removing that `_publish()` turns `test_a_window_that_changes_only_the_sources_..._still_publishes_a_frame` red. The five texts are true again; boundaries §10 now says "copies none but still publishes". One trace remains: the frames.py module docstring still opens "published when they change", which a sources-only republish is not (NIT below). |
| S-c: applier `isinstance` untested | **fixed** | Dropping the guard turns `test_the_applier_refuses_a_region_that_is_not_a_name[region0]` red. |
| N-a: `vars()` evades the peek scan | **fixed** | Removing the `vars` branch turns `test_the_peek_scan_catches[...vars...]` red. `.__dict__` is in `PEEKS`, with a catch case. |
| N-b: `_take_cells` speedup unguarded | **fixed** | The `elif True:` (always copy) mutation turns `test_a_paint_far_from_every_region_copies_no_region_mask` red. |
| N-c: numpy scalars echoed as type names | **fixed** | Removing the `np.floating` branch turns `test_an_object_echoes_as_its_type_never_its_address` red. The integer and bool branches are covered by the new scalar test. |

### Architecture, and Determinism and replay: status set by the Architecture and Determinism reviewer (O25)

| id | status | evidence |
|---|---|---|
| D1 module-attribute chains | **open** (narrowed) | **Caught:** both spellings I reported, `import simcore.core.frames as fr; fr.damage…` and `from simcore.core import applier; applier.damage.strike`, plus `import simcore.core as sc; sc.frames.damage.strike`. **Not caught**, and also passing import-linter, are the two that start at the root package. I planted `import simcore` with `simcore.core.frames.damage.region_breached(...)` in `protocol/encoding.py`, and `from simcore import core as _core` with `_core.applier.damage.strike` in `adapters/sem/bridge.py`. Result: **"Contracts: 8 kept, 0 broken"**, both ownership scans **passed**, and at runtime `_hit().__module__ == "simcore.core.damage"`. The cause is in `tests/test_ownership.py::_simcore_names`: it binds a name only when `a.name.startswith("simcore.")` or `node.module.startswith("simcore.")`, so the bare root `simcore` is never bound. *Fix:* match `name == "simcore" or name.startswith("simcore.")` in both branches, and add the two spellings to `test_the_reexport_scan_catches`. Value-flow spellings are also missed: a local alias `m = frames; m.damage`, `getattr(frames, "damage")`, a default argument `def f(m=frames)`, tuple assignment, and `sys.modules[...]`. That is the same class the author already rejected for the peek scan ("the scans don't follow values"), and I accept that reason for these. |
| D2 sources-only windows skip publication | **fixed** | `World.writing(cells=False)` publishes after the sources commit. Probe: an ignite advances the sequence by 1, and the frame's temperature `is` the previous frame's (no copy). Extinguish publishes too, and a refused second extinguish doesn't. A sources-only window that raises commits nothing, publishes nothing, and releases `_held`. Boundaries §10 now says "copies none but still publishes". Lesson 23's "every write window that closes publishes" and the test's `[0, 1, 2, 3, 3]` are both true again. |
| D3 `World.writing` "changes nothing" overclaim | **fixed** | The docstring states the order: cells commit, frame publishes, sources commit. It also says that a failure while publishing would leave the cells committed and the sources not. |
| D4 cylinder bit-identity not evidenced | **fixed** | `test_a_cylinder_scene_is_bit_identical_on_a_rerun` exists, and the commit message limits its claim to that scene. I compared independently at 0.2 m, fa27d5f vs a3d7b07, radii 0.37, 0.3 and 0.5 m (ignite, then 5 advances): the digests and barrel cell counts were identical (`8e8ca053…`/36, `44bdd04f…`/36, `0906b9ee…`/84). |
| D5 two independent locks | **fixed** | `CellStore.holding()` and `writing()` share `_refuse_a_second_owner`. Probe: cells inside holding, holding inside cells, and holding inside holding are all refused, and afterwards `is_writing` and `_held` are both False. |

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| D-B1, a chained call skipped | **fixed** | `_inner` now skips only a `Name` or `Attribute` that is the value of an attribute, never a call. Every chained call I tried is caught. In the input rule: `open(p).read()`, `Path(p).open().read()`, `np.load(p).copy()`, `json.loads(s).get()`, `builtins.open(p).read()`, `[open(p)][0].read()`, `io.open(p).read()` and `os.getenv('X').strip()`. In the unsafe rule: `np.load(..., allow_pickle=True).item()` and `[()]`, `importlib.import_module('pickle').loads`, `__import__('pickle').loads`, `.Unpickler(f).load()`, `[__import__('pickle')][0].loads`, `im('pickle').loads` with `im` aliased, `builtins.__import__('pickle').loads`, `getattr(importlib.import_module('pickle'), 'loads')`, the `marshal` and `shelve` chains, `yaml.unsafe_load(s).keys()`, `yaml.load(s).keys()`, and `from yaml import load; load(s).get()`. Permanent tests cover the listed cases (`CHAINED_UNSAFE`, `CHAINED_INPUT`). |
| S1 (round 1), lint_inputs evasions | **open** | The same skip mechanism still hides a read name or unsafe name that is used through an attribute. See D2-B1. |
| D-N1, the remaining spellings | **fixed** for each listed form | Caught: `np.load(p, None, True)`, the `SafeLoader` subclass with `yaml.constructor`, `__builtins__['eval']`, `vars(builtins)[...]`, `builtins.__dict__[...]`, and the C loaders. The attribute form `__builtins__.eval` is not caught (D2-B1). |
| D-N2, `:.3g` wording | **fixed** | The messages are back to `:.2f` and `:.0f`. With coordinates now bounded at 1 km, both stay short. |
| D-N3, tuple assignment hiding a Modulator | **fixed** | `_members` reads `Tuple` and `List` targets, and a permanent test plants one. |
| D-N4, the physics range mixing load conditions | **fixed** | `docs/architecture.md` and B5 now state each condition like for like: lightly loaded 1.4× (about 3.6× at 5×10⁶ cells by scaling), heavily loaded 2.3 to 2.9× and 7.7×. |
| D-N5, the set echo cost | **fixed** | `shown(set(range(10**6)))` takes 0.0 ms and returns `<a set of 1000000>`. A set of 1,000 takes 0.7 ms. |
| D-N6, `Frame._region` raised `KeyError` | **fixed** | It raises `ValueError` now. No source code catches `KeyError` from it (`git grep`). |

### The root cause, and the corpus

The lint kept losing spellings because the probes of each round were never pinned as tests, so each rewrite dropped
some silently. `os.environ.get` is an example: 3a0d482 caught it, and 8c1de1e lost it. Fold 3 makes two changes:

- **One algorithm.** `lint_inputs` canonicalizes every name, attribute, subscript and call to a dotted name, resolving
  import aliases, `__builtins__`, `sys.modules[...]`, the import functions and `getattr`. It judges every node, and
  matches every dotted prefix against the tables. There are no special cases per spelling, and no node is skipped.
- **A corpus.** `tests/test_lint_inputs_corpus.py` holds the 122 spellings that any round reported, each with its
  verdict: 102 must be flagged and 20 are clean.

Scored against each revision's `lint_inputs.py`:

| revision | wrong | missed, by round reported | false positives |
|---|---|---|---|
| 3a0d482 | 49 | round 1: 27, delta 1: 9, delta 2: 13 | 0 |
| 8c1de1e | 35 | delta 1: 14, delta 2: 21 | 0 |
| a3d7b07 | 15 | delta 2: 15 | 0 |
| fold 3 | 0 | — | 0 |

Spellings caught at 3a0d482 and lost later:
- **At 8c1de1e:** 15, among them `os.environ.get`, `sys.stdin.read`, `open(p).read()` and `yaml.Loader.add_constructor`.
- **Still lost at a3d7b07:** 7, the delta-2 table's `os.environ.get/.copy`, `environ.get`, `sys.stdin.read/readline`,
  `sys.argv.copy` and `yaml.Loader.add_constructor`.
- **Caught at 8c1de1e and lost at a3d7b07:** none.

The full listing is kept in the durable folder.

### New findings, and what changed

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D2-B1, D2-N1 | the one-algorithm `lint_inputs` above, plus the corpus. `importlib.__import__`, `sys.modules[...]`, `globals()['__builtins__']`, `multiprocessing.reduction` and `builtins.__dict__.get` are all caught. The docstring lists what it can't see | a3d7b07's lint gets 15 corpus cases wrong. Reverted: exact names only (1 red); `__builtins__` not canonicalized (4 red) | open |
| Arch D1 (residual) | `_simcore_names` binds the bare `simcore` package; both plants are in `test_the_reexport_scan_catches`. Docstrings, the scan comment and boundaries §10 say that capability passing is the guard, and that the scans are tripwires with stated blind spots. The scans are not extended further | a3d7b07's scan returns nothing for either plant | open |
| Arch N-1 | `holding` is an opener in `window_openers`, and a peek | a3d7b07's scans don't see it | open |
| Exec N-d | **A correction:** a3d7b07 changed physics. At radius 0.28284271247461895 m on the 0.2 m grid, the barrel's `r*r` mask had 24 cells, against fa27d5f's 20; the 0.37 m scene showed nothing because `0.37*0.37 == 0.37**2`. The 1 km bound already rules out the overflow, so `Cylinder.mask` is back to `radius_m**2`, and the knife-edge scene now matches fa27d5f (20 cells, the same digest). `test_a_cylinder_mask_squares_its_radius_as_fa27d5f_did` pins the formula at that radius. No golden digest is committed, because the standing decision (`TURN_SUBSTEPS`) promises only the outcome class across machines and CI runs on Linux. The rerun test is renamed `..._repeatable_in_process` | reverted (`r*r`: red) | open |
| Exec N-e | `frames.py`'s docstring: a frame is published after every window, whether or not a cell changed | — (docs) | open |
| Trust D2-N2 | a nested `np.bool_` echoes `True` | reverted (red) | open |

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
