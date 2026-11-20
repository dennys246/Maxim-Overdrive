# Delta round: Architecture, and Determinism and replay — step 3b(a) fold

Scope: `git diff 3a0d482` in `.worktrees/gates` (the fold is staged and uncommitted), read against
`docs/design/reviews/step3b/fold.md`. Every status below comes from the tree and from my own probes on a copy
(`scratchpad/3b/review/delta_copy`, with `probe_delta.py` and `probe_echo2.py`), not from fold.md. The worktree was
not touched.

## Status of my round-1 findings

| id | status | evidence from the tree |
|---|---|---|
| S1 re-exports and `World` in the membrane | **fixed** (the scenario as reported); a residual is new finding D1 | `region_parts` and `to_maxim_entity` now take `(applier, frames, region)`, and the bridge no longer imports `World`. `simcore.core.world` is in `membrane-reads-frames`. I re-planted the original lines: `from simcore.core.world import heat` and `from simcore.core.frames import MaterialGrid` in `encoding.py`; `from simcore.core.applier import damage`, `from simcore.core.world import World` and `peek(world)` reading `world.grid` in `bridge.py`. The result was **contract BROKEN** (`import World`), `test_..._reach_no_world_state_by_attribute` red (`.grid`), and `test_..._through_an_allowed_one` red for all three re-exports. |
| S2 a failure while the window closes | **fixed** | `CellStore.writing` builds `channels` and `table` inside the `try` and commits them in the `else`. Injected `MemoryError` at the 2nd, 5th and 6th `frozen` call, in a window that writes the cells, paints a new region and adds a source. Each time, the temperature, the region list, the sources and the frame sequence were all restored, the owners were read-only, `is_writing` was False, and a write at rest was refused. |
| S3 `place` an unmarked owner | **fixed** | `TEMPORARY(phase1/sim-clock)` in `imagination.py::_voxelize`. The roadmap lists `src/simcore/core/imagination.py` under it. Step 5a is the sim-clock step (checklists §5a carries the same marker for `heat.py`). The CLAUDE.md rule now names the exception. |
| S4 non-deterministic echo | **fixed** | Ran `probe_echo2.py` under `PYTHONHASHSEED=1,2,3`: identical md5. Instances echo as `<a Thing>`. Mixed sets print sorted by their echo, and dicts in insertion order. `bytes` echo as `<a bytes>`, which is fine. |
| S5 the deviation's costs | **fixed**, but its fix introduced new finding D2 | The §10 as-built note gives two copies per cell window and about 100 MB pinned per frame. B5 has the per-agent row. Ignite and extinguish use `World.writing(cells=False)`: no cell copy, no frame. |
| N1 region table mutated in place | **fixed** | Inside a window, regions live in `_masks`/`_meta`, and `_regions` is swapped at commit. Probe: the proxy held across a failed window shows 27 cells, the same as the grid. |
| N2 `CellFrame` immutability by caller only | **fixed** | `of` raises `WindowClosed` inside a window, and `__post_init__` refuses a writable array. Both probed. |
| N3 public `publish` | **fixed** | `World.frames` is a `FrameView` with no `publish`. `_feed` is in the peek scan. |
| N4 `on_close` docstring | **fixed** | The docstring now says "closes without raising, whether or not it changed anything". |
| N5 `_pickle` and lint holes | **fixed** | `import _pickle` and `numpy.lib.format.read_array(allow_pickle=True)` are now findings. `_pickle` is in the lint, but not in the `input-primitives` contract list. The lint is the guard that holds it, so I accept that. |
| N6 `centroid_m` public; `_turn` in the window | **fixed** | `_centroid_m` is private. `self._turn += 1` is after the `with`. |

Determinism re-check: `digest(run(0.2))` on the fold is `f7429cba…d256`, the same as origin/main. The targeted
`tests/test_ownership.py` and `tests/test_frames.py` pass (65).

## New findings

**Counts: 0 BLOCKER, 2 SHOULD-FIX, 3 NIT.**

### D1 (SHOULD-FIX) Module-attribute traversal still reaches the laws from the adapters and the protocol
`tests/test_ownership.py::reexports`, `::peeks`; `pyproject.toml` `skip-layer`, `membrane-reads-frames`

The re-export scan reads only `from simcore.X import name`, and the peek scan bans only state attributes. A module
imported whole, with a law reached through it as an attribute, passes every check. I planted, on the copy, in
`protocol/encoding.py`:
`import simcore.core.frames as _fr`, `from simcore.core import applier as _ap` and
`return _fr.damage.region_breached(frame, "crate"), _ap.damage.strike`. In `adapters/sem/bridge.py`:
`from simcore.core import frames as _frm` and `_frm.damage.region_integrity`.
Result: **"Contracts: 8 kept, 0 broken"**, and both new scans **passed**.

*Scenario:* the protocol layer calls `world_module.damage.strike(...)` or `frames.heat...` to compute something for
display or a debug intent. The skip-layer rule, "adapters and protocol reach no cells, laws, geometry", is broken
with the gate green. This is the same class as S1, narrower now that the common `from … import` spelling is caught.

*Fix:* add the forbidden modules' short names (`damage`, `heat`, `scene`, `imagination`, `readonly`; `grid` is
already there) to `PEEKS` for files outside the core. Or have `reexports` also resolve `ast.Import` and
`from simcore.core import <module>`, then flag any attribute of that module whose value comes from a forbidden
module. Add each planted spelling above to `test_the_reexport_scan_catches` or `test_the_peek_scan_catches`.

### D2 (SHOULD-FIX) Sources-only windows break the publish cadence that §4.2, lesson 23 and a test name still promise
`src/simcore/core/world.py::World.writing` (`cells=False`); `src/simcore/core/applier.py::Applier._ignite`,
`_extinguish`; `docs/lessons_maxim_in_games.md` §23; `docs/design/boundaries.md` §4.2 "Cadence", §11.1 2c;
`tests/test_ownership.py::test_the_shipped_path_publishes_a_frame_after_each_application_and_each_advance`

After the fold, an applied ignite or extinguish publishes no frame. The probe shows `ignite publishes: False`, and
the test now asserts `[0, 0, 1, 2, 2]`. Three texts still say otherwise:
- §4.2: "a frame is published … after each tick that applied an intent, so a receipt's after-frame exists on its
  apply tick".
- §11.1 2c: "frames published after each application and each advance".
- Lesson 23: "every write window that closes publishes, so an application's effect is in the next read". It cites
  this test as the one that holds that, and the test's name still says "after each application".

The as-built note records "publishes nothing" in one clause. But it doesn't say this changes §4.2's receipt
contract. When `phase1/agents` stamps receipts with their after-frame, an ignite has none.

The cost argument doesn't need the change. Frames hold immutable owners, so republishing the current cells under a
new sequence costs one small object and no copy. A sources-only window could call `_publish` as it closes, skipping
the grid copy and keeping the cadence. *Fix:* either republish on sources-only windows (preferred, since it keeps
§4.2 and lesson 23 true at no cost) or amend §4.2, §11.1, lesson 23 and the test name to "every window that changes
cells", and record the receipt consequence for `phase1/agents`.

### D3 (NIT) `World.writing` overclaims "changes nothing" when a close callback raises
`src/simcore/core/world.py::World.writing`

With `cells=True`, the grid commits, then runs its callbacks (`_publish`), and only then does the world commit the
sources. Probe: with a callback that raises in a window that sets the temperature to 77 and adds a source, the grid
holds 77.0, the sources are not committed, and no frame is published. The docstring says "a window that raises, in
its body or while it closes, changes nothing". The trigger is now only an internal failure in `_publish`, since
forging a frame is no longer possible. Either commit the sources before the grid's callbacks run, or narrow the
docstring.

### D4 (NIT) `Cylinder.mask`'s `r**2` to `r*r` is not covered by the bit-identity evidence
`src/simcore/core/scene.py::Cylinder.mask`

On this machine, `r**2 != r*r` for 1,377 of 10⁶ uniform radii in [0, 1000]. Python's float `**` goes through libm
`pow`, which isn't correctly rounded here. So the threshold moves by an ulp, and a cell centre lying exactly on the
circle can change sides. The fold's digests use a Box-only scene (`tests/test_determinism.py::SCENE`), and no
shipped data file has a cylinder. The change is the better one, since `r*r` is correctly rounded everywhere and helps
cross-machine agreement. But fold.md's "byte-identical" says nothing about cylinders. Say so in the fold record, or
add a cylinder to the determinism scene.

### D5 (NIT) The two windows are separate locks, so "one owner at a time" doesn't span them
`src/simcore/core/world.py::World.writing`; `src/simcore/core/grid.py::CellStore.writing`

A `cells=False` window sets only `_sources_open`, so while it is open, `grid.writing()` (that is, `place`) can open.
Inside a cell window, `World.writing(cells=False)` is refused only because the world's flag is set, and `place`'s
direct `grid.writing()` bypasses the world's flag. No shipped path nests them. A one-line comment, or having `place`
go through `World`, would keep the single-owner rule visible.

## Architecture notes on the fold, no finding

- `CellStore` grew `_window_table`, `_take_cells`, `_region_table` and `_region_names`. They are still one job (the
  owner's window over channels and regions), split along it, and the size is within its limits. `place` is now three
  named steps (`_read`, `_within_world_rules`, `_voxelize`), and the budgets are checked before any cell exists.
- In-window `grid.regions` returns frozen snapshots (verified: `writeable=False`), so no writable mask escapes a
  window. `_masks` is None after close.
- Region order is preserved: `_meta` mirrors table order, and a new region is appended. The 0.2 m digest
  confirms it.
