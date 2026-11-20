# Delta round 3: Trust boundary and Performance, step 3b(a)

Scope: `git diff a3d7b07 d9b22d8`. I probed a `git archive d9b22d8` copy using the worktree's venv. The worktree is
untouched. On that copy, `tests/test_lint_inputs_corpus.py` and `tests/test_lint_gates.py` pass (145 tests).

## Status of my open findings (set from the tree)

| id | status | evidence |
|---|---|---|
| D2-B1, names inside a chain | **fixed** | Every row of my delta-2 table is caught: `os.environ.get` and `.copy()`, `environ.get` after `from os import environ`, `sys.stdin.read()` and `.readline()`, `sys.argv.copy()`, `__builtins__.eval`, `__builtins__.__import__('pickle')`, `builtins.__dict__.get('eval')` and `yaml.Loader.add_constructor`. |
| S1 (round 1), lint_inputs evasions | **fixed** for every spelling any round reported | All 40 round-1, delta-1 and delta-2 unsafe spellings are caught. The only exceptions are the five the docstring now names as blind spots or that need no ban: `importlib.util` loaders, `copyreg`, `__loader__`, `type(x).__init__` and `pickletools.dis`. The real tree is clean (0 findings). The remaining gaps are new spellings (D3-S1, D3-N1). |
| D2-N1, `importlib.__import__`, `sys.modules[...]`, `globals()`, `ForkingPickler` | **fixed** | All four are caught. |
| D2-N2, numpy bool echo | **fixed** | `shown([np.bool_(True), np.float64(2.5)])` gives `[True, 2.5]`. |
| B1, the cylinder overflow (re-checked after `radius_m**2` returned) | **still fixed** | A 1e200 radius is refused as `SpecRejected` by the 1 km bound before any arithmetic, and a 1,000 m radius is refused as "too large: 2000.00 m". |

## New findings

### BLOCKER

None.

### SHOULD-FIX

**D3-S1. `scripts/lint_inputs.py::INPUT`: the table lacks common input primitives, and the docstring does not list
them as blind spots, so "only an input gate reads input" still has holes.**

Each of these passes in `src/simcore/core/x.py`. Add each one as a corpus row with verdict "input":

1. `os.read(fd, 10)`
2. `os.fdopen(fd).read()`
3. `io.FileIO(p).readall()`
4. `np.memmap(p)`
5. `np.fromregex(p, 'x', float)`
6. `zipfile.ZipFile(p).read('x')`
7. `from urllib.request import urlopen; urlopen(u).read()`
8. `sqlite3.connect(p)`
9. `mmap.mmap(fd, 0)`
10. `import posix; posix.environ`, and the same with `nt.environ`
11. `pkgutil.get_data('x', 'a')`
12. `async def f(r): await r.readline()`, an asyncio stream

For contrast, `tarfile.open` and `importlib.resources` are caught, through `.open` and the `DYNAMIC` table.

Fix: add `os.read`, `os.fdopen`, `io.FileIO`, `numpy.memmap`, `numpy.fromregex`, `zipfile`, `urllib`, `sqlite3`,
`mmap`, `posix.environ`, `nt.environ` and `pkgutil.get_data` to `INPUT`. Name asyncio streams as a blind spot, or
add `read`, `readline` and `readexactly` to `READ_METHODS` behind the false-positive check in D3-S2.

**D3-S2. `scripts/lint_inputs.py::_Names.name`: a plain parameter or local named after a builtin or a module is
flagged in `src/`.**

`name()` maps any bare `input`, `open`, `eval` or `compile` to `builtins.<name>`. `INPUT` also holds the bare names
`json`, `yaml`, `environ` and `getenv`. So clean code is refused in `src/simcore/`:

| Code | Flagged as |
|---|---|
| `def f(input): return input.shape` | input |
| `def f(*, input=None)` | input |
| `def f(open: bool)` | input |
| `json = x.to_dict()` | input |
| `yaml = x` | input |

Ruff's flake8-builtins rules (`A`) are not selected in `pyproject.toml`, so nothing else bans these names. A
parameter called `input` is ordinary in array code.

`environ` as a parameter (`def f(environ): environ['PATH']`) is flagged too. That one is arguably intended, but it
is also undocumented. In `tests/`, `eval = model.evaluate()` is flagged as unsafe.

A lint that refuses clean code invites a workaround. Fix: resolve a bare name to `builtins.` or to a module only
when nothing in the module binds it, meaning no parameter, assignment target, `for` target, `with` target or `def`
name. Add the five rows above to the corpus with verdict "clean".

### NIT

**D3-N1.** Unsafe-decoder spellings that are neither caught nor named in the docstring. Add each as a corpus row,
either "unsafe", or "blind spot" with the docstring updated:

1. `np.load(f, *a)`, a starred positional that carries `allow_pickle`
2. `from numpy import *` followed by `load(f, None, True)`
3. `np.lib.format.read_array(f, True)`, a positional `allow_pickle`
4. `runpy.run_path(p)`
5. `code.InteractiveInterpreter().runsource(s)`
6. `types.FunctionType(compile(s, 'x', 'exec'), {})()`, exec without naming exec
7. `operator.attrgetter('unsafe_load')(yaml)(s)`
8. `ctypes.pythonapi.PyRun_SimpleString(b'x')`
9. `jsonpickle.decode(s)`. It is not in the lockfiles, so this row is only for completeness.

Already named as blind spots, and correctly left out: `__import__('pick'+'le')`, which builds the name at run time;
`d = builtins.__dict__; d['eval'](s)`, a value passed through a variable; and
`yaml.SafeLoader.add_constructor('!x', lambda l, n: ...)`, a registration that never names `yaml.constructor`.

## Performance

- **Lint cost.** `check_inputs` over the repository's 95 Python files (0.7 MB) takes 1.26 s of CPU on d9b22d8 and
  1.18 s on a3d7b07, minimum of 3 runs, under load. So rewriting it as one algorithm costs nothing measurable.
  `_Names.of` recomputes a chain's name from its root at every node of the chain, which is O(k²) in a chain of
  length k. That is negligible here, but it is the first thing to memoise if the gate's lint step ever matters.
- **Runtime.** Nothing changed: `checks.py` and `scene.py` changed one line each, and the rest of the `src/` diff is
  docstrings.

## Counts

My open findings (D2-B1, round-1 S1, D2-N1, D2-N2):
- fixed: 4
- open: 0

B1 was re-checked and is still fixed.

New: **0 BLOCKER, 2 SHOULD-FIX** (D3-S1, D3-S2), **1 NIT** (D3-N1). D3-S1 and D3-S2 are each stated as corpus rows
to add.
