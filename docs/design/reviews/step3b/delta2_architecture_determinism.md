# Second delta round: Architecture, and Determinism and replay — `git diff 8c1de1e a3d7b07`

Every status below comes from the tree at a3d7b07 and from my own probes on an exported copy
(`scratchpad/3b/review/delta2_copy`, `probe_d1.py`, `probe_d2.py`, `cyl.py`). The worktree was not touched.

## Status of my delta findings

| id | status | evidence |
|---|---|---|
| D1 module-attribute chains | **open** (narrowed) | **Caught:** both spellings I reported, `import simcore.core.frames as fr; fr.damage…` and `from simcore.core import applier; applier.damage.strike`, plus `import simcore.core as sc; sc.frames.damage.strike`. **Not caught**, and also passing import-linter, are the two that start at the root package. I planted `import simcore` with `simcore.core.frames.damage.region_breached(...)` in `protocol/encoding.py`, and `from simcore import core as _core` with `_core.applier.damage.strike` in `adapters/sem/bridge.py`. Result: **"Contracts: 8 kept, 0 broken"**, both ownership scans **passed**, and at runtime `_hit().__module__ == "simcore.core.damage"`. The cause is in `tests/test_ownership.py::_simcore_names`: it binds a name only when `a.name.startswith("simcore.")` or `node.module.startswith("simcore.")`, so the bare root `simcore` is never bound. *Fix:* match `name == "simcore" or name.startswith("simcore.")` in both branches, and add the two spellings to `test_the_reexport_scan_catches`. Value-flow spellings are also missed: a local alias `m = frames; m.damage`, `getattr(frames, "damage")`, a default argument `def f(m=frames)`, tuple assignment, and `sys.modules[...]`. That is the same class the author already rejected for the peek scan ("the scans don't follow values"), and I accept that reason for these. |
| D2 sources-only windows skip publication | **fixed** | `World.writing(cells=False)` publishes after the sources commit. Probe: an ignite advances the sequence by 1, and the frame's temperature `is` the previous frame's (no copy). Extinguish publishes too, and a refused second extinguish doesn't. A sources-only window that raises commits nothing, publishes nothing, and releases `_held`. Boundaries §10 now says "copies none but still publishes". Lesson 23's "every write window that closes publishes" and the test's `[0, 1, 2, 3, 3]` are both true again. |
| D3 `World.writing` "changes nothing" overclaim | **fixed** | The docstring states the order: cells commit, frame publishes, sources commit. It also says that a failure while publishing would leave the cells committed and the sources not. |
| D4 cylinder bit-identity not evidenced | **fixed** | `test_a_cylinder_scene_is_bit_identical_on_a_rerun` exists, and the commit message limits its claim to that scene. I compared independently at 0.2 m, fa27d5f vs a3d7b07, radii 0.37, 0.3 and 0.5 m (ignite, then 5 advances): the digests and barrel cell counts were identical (`8e8ca053…`/36, `44bdd04f…`/36, `0906b9ee…`/84). |
| D5 two independent locks | **fixed** | `CellStore.holding()` and `writing()` share `_refuse_a_second_owner`. Probe: cells inside holding, holding inside cells, and holding inside holding are all refused, and afterwards `is_writing` and `_held` are both False. |

Regression checks:
- The S2 freeze-failure injection (3rd `frozen` call, cells plus a source) still rolls back fully: temperature 20.0, read-only, no sources, sequence 0.
- `digest(run(0.2))` is still `f7429cba…d256`.
- `shown` of numpy scalars is value-only (`np.float32(0.1)` gives `0.10000000149011612`, run-independent). A set of 2,000 elements echoes `<a set of 2000>`. `np.str_` echoes `<a str_>`.

## New findings

**Counts: 0 BLOCKER, 0 SHOULD-FIX, 1 NIT.** D1's residual stays as D1, still SHOULD-FIX and open.

### N-1 (NIT) `holding()` is a window opener that neither scan sees
`src/simcore/core/grid.py::CellStore.holding`; `tests/test_ownership.py::window_openers`, `::PEEKS`

`window_openers` matches only calls named `writing`, and `PEEKS` doesn't include `holding`. Code that calls
`grid.holding()` gets the single ownership without being listed in `WINDOW_OWNERS`. That code could be a new core
function, or, through `world.grid` (already a peek), the adapters. It gains no write access, since the cells stay
read-only and the sources dict is yielded only by `World.writing`. But while it holds ownership, every
`advance`/`apply` is refused with `WindowClosed`, and that is a stall the ownership tests would not attribute. The
only caller today is `World.writing`, already an owner. *Fix:* treat `holding` as an opener in `window_openers`, and
add it to `PEEKS`.

## Architecture notes, no finding

- `holding()` is the right shape: the single-owner rule now lives in one place (`_refuse_a_second_owner`) instead of
  two flags, and `World.writing` is again a short two-way choice.
- Republishing on sources-only windows uses the owner-holding frame design exactly as intended: no copy, the
  cadence is kept, and §4.2's after-frame promise holds for every applied intent.
- `checks.py` (layer 0) now imports numpy. That is allowed in the core and adds no upward import.
