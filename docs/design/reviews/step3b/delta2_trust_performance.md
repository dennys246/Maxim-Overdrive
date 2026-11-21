# Delta round 2: Trust boundary and Performance, step 3b(a)

Scope: `git diff 8c1de1e a3d7b07`. I probed a `git archive a3d7b07` copy (`scratchpad/3b/review/d2copy`) using the
worktree's venv, and compared it with the `lint_inputs.py` of 3a0d482 and of 8c1de1e. The worktree is untouched.

**Correction first.** My delta-1 report missed a regression that 8c1de1e introduced and that a3d7b07 still has.
Round 1 had probed `os.environ.get('X')` and found it caught. In delta 1 I re-probed only calls used through an
attribute, not names used through an attribute. That second case is D2-B1 below.

## Status of my delta findings (set from the tree)

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

## New findings

### BLOCKER

**D2-B1. `scripts/lint_inputs.py::_inner` and `::_read_hit`: a read name or unsafe name used through an attribute
is never judged, so `os.environ.get(...)` passes in `src/simcore/`. 3a0d482 caught it; 8c1de1e broke it, and a3d7b07
keeps it broken.**

The chain skip judges a chain only at its end. So `os.environ`, as the value of `os.environ.get`, is skipped, and
the end `os.environ.get` is not in `READ_NAMES`. The check is an exact match, not a prefix match.

Input rule, in `src/simcore/core/x.py`:

| Spelling | 3a0d482 | 8c1de1e | a3d7b07 |
|---|---|---|---|
| `os.environ.get('X')` | caught | missed | **missed** |
| `os.environ.copy()` | caught | missed | **missed** |
| `from os import environ; environ.get('X')` | caught | missed | **missed** |
| `sys.stdin.read()`, `sys.stdin.readline()` | caught | missed | **missed** |
| `sys.argv.copy()` | caught | missed | **missed** |
| `os.environ['X']`, `'X' in os.environ`, `x = os.environ` | caught | caught | caught |

Unsafe rule (in any file):
- missed on all three revisions: `__builtins__.eval(s)`, `__builtins__.__import__('pickle')` and
  `builtins.__dict__.get('eval')(s)`;
- caught on 3a0d482, missed on 8c1de1e and a3d7b07: `yaml.Loader.add_constructor`.

This matters for two reasons:
1. `os.environ.get("NAME")` is the single most common way to read the environment. CLAUDE.md's "Only the file gates
   read input" has `scripts/lint_inputs.py::check_inputs` as its guard. The core is supposed to have no IO, but its
   other guards (the import-linter contracts and the determinism scan for clocks and RNG) don't cover `os`. So nothing
   in the gate would stop an environment-dependent branch landing in `src/simcore/`, and with it a hidden replay
   input.
2. The new docstring says the builtins table is caught when "read by name (`__builtins__`, ...)". The attribute form
   is not.

I checked the tree: `git grep` finds no `environ.`, `stdin.` or `argv.` in `src/` at a3d7b07, so nothing violates
the rule today. The guard is weaker than it was at 3a0d482 on its canonical spelling, and no test covers that
spelling.

Fix:
- In both rules, judge each chain at its end against every dotted prefix of its canonical name, so `os.environ.get`
  matches `os.environ` and `__builtins__.eval` matches `__builtins__`.
- Canonicalize `__builtins__` to `builtins`, so `__builtins__.__import__` falls under `DYNAMIC_IMPORTS`.
- Add the table's rows as permanent tests.
- For red-first, run 3a0d482's own input cases against the new module.

### SHOULD-FIX

None.

### NIT

- **D2-N1.** `scripts/lint_inputs.py::unsafe_findings` still misses `importlib.__import__('pickle')`, because
  `DYNAMIC_IMPORTS` lacks it, and `sys.modules['pickle']` and `sys.modules['builtins']`, which are subscripts with a
  literal. It also misses `globals()['__builtins__']` and `multiprocessing.reduction.ForkingPickler.loads`. The
  docstring's "a value passed through a container, code built at run time" covers most of these. Adding
  `importlib.__import__`, and flagging a `sys.modules[...]` whose literal is unsafe, costs one line each.
- **D2-N2.** `src/simcore/core/checks.py::_BoundedRepr`: reprlib dispatches nested values by type name, and numpy 2
  names `np.bool_` as `bool`. So `shown([np.bool_(True)])` prints `np.True_`, while `shown(np.bool_(True))` prints
  `True`. Both are run-independent and bounded, so this is cosmetic.

## Performance (this diff)

- The sources-only window (`CellStore.holding`) now publishes a frame. On the alley (1.92e6 cells), an ignite costs
  0.03 ms including the frame, because `CellFrame.of` copies no array. A strike, through the full cell window, costs
  17.6 ms under load, the same as before.
- Opening `grid.writing()` inside `World.writing(cells=False)` is refused with `WindowClosed`.
- `_SET_SORT_LIMIT = 1000` bounds the echo's sort. Nothing else in this diff runs per cell or per primitive.

## Counts

Delta findings:
- fixed: 7 (D-B1 and D-N1 to D-N6, D-N1 for its listed forms);
- open: 1 (round-1 S1, through D2-B1).

New: **1 BLOCKER** (D2-B1), **0 SHOULD-FIX**, **2 NIT**.
