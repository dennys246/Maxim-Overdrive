# Delta round 7: Trust boundary and Performance, step 3b(a)

Scope: `git diff 2cd24fb`, the uncommitted fold, probed on an rsync copy (no `.venv`) using the worktree's venv. On
the copy, `test_input_allowlist.py` and the corpus pass (300). The worktree is untouched.

## Status

| id | status | evidence |
|---|---|---|
| D6-S1, stdlib re-export route | **fixed** | All six of my lines are refused by `EXTERNAL_NAMES`: `reprlib.builtins.open`, `contextlib.os.environ.get`, `dataclasses.sys.modules['pickle']`, `from dataclasses import sys`, `typing.sys.argv` and `collections._sys.modules`. So are `contextmanager.__globals__[...]` (a pure chain), a bare `math` passed as a value, and `[np][0].load`. |
| D6-N1, computed `getattr` | **fixed in `src/simcore/`** (a corpus row was added) | In `src/maxim_overdrive/` it still passes, but the lint states its computed-`getattr` rule covers `src/simcore/` only. It is a stated scope, so I accept it. |

## New findings

### BLOCKER and SHOULD-FIX

None. Every route I found goes through a value, which is the stated blind spot ("methods on values").

### NIT

**D7-N1. Dunder attributes on a call's result reach any module's globals.** These pass all five checks in
`src/simcore/core/`:
- `contextlib.contextmanager(len).__globals__['os'].environ`
- `field().__class__.__init__.__globals__['sys'].argv`, after `from dataclasses import field`
- `'{0.__globals__[os].environ}'.format(contextmanager)`, where `str.format` reads attributes itself

These are adversarial spellings, not mistakes, so they fall within "guards mistakes, not adversaries". But the cost
of refusing them is one rule: in `src/`, refuse the attributes `__globals__`, `__builtins__`, `__subclasses__`,
`__code__` and `__closure__`, and any format string containing `{` followed by `.__` or `[__`.

Corpus rows:
1. `import contextlib` then `e = contextlib.contextmanager(len).__globals__['os'].environ`, verdict "input".
2. `from dataclasses import field` then `e = field().__class__.__init__.__globals__['sys'].argv`, verdict "input".
3. `from contextlib import contextmanager` then `s = '{0.__globals__[os].environ}'.format(contextmanager)`, verdict
   "input".

**D7-N2. `maxim_overdrive.data::data_dir` hands any caller an unrestricted `pathlib.Path`.** Planted as
`maxim_overdrive.game`, the line `t = (data_dir() / 'world' / 'x.yaml').read_text()` passes:
- `data_dir` is in `__all__`;
- `read_text` is a method on a value;
- `PATH_HOLDERS` binds only `data` and `tiers`.

This is the most natural mistake the rule exists to stop: game code reading a data file directly, skipping the
strict YAML gate. Capability passing holds only if the capability is narrow. Here the gate hands out the whole
filesystem, through `Path` arithmetic such as `.parent`.

There is no such caller today. Fix: either have `data_dir` return a gate-owned handle that offers only
`load_materials`, `load_action_limits` and `rig_profile`, or apply `PATH_HOLDERS` to every module that calls
`data_dir`.

Corpus row: `from maxim_overdrive.data import data_dir` then `t = (data_dir() / 'x.yaml').read_text()`, in
`src/maxim_overdrive/game.py`, verdict "input".

## Performance

The only runtime change is `real_path`, one `realpath` call at startup. Nothing in the simulation path changed.

## Counts

- My delta-6 findings: 2 fixed (D6-N1 within the lint's stated scope), 0 open.
- New: **0 BLOCKER, 0 SHOULD-FIX, 2 NIT** (D7-N1, D7-N2), with four corpus rows.
