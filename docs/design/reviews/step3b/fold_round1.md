# Step 3b part (a) review: fold, round 1 and delta round 1

The round's reports are `executor_wire.md`, `architecture_determinism.md` and `trust_performance.md` (each restored by
its reviewer). Branch `phase1/gates` at 3a0d482, folded in the working tree. The status column is the reviewer's to
set (O25), so every row is `open`.

"Red first" says how the fix's test was shown to fail without the fix:
- **against HEAD:** the new test was run unchanged against 3a0d482's `src/` (from `git archive`);
- **reverted:** the fix was undone in the tree, the test went red, and the fix was restored;
- **planted:** what the guard forbids was planted and the guard went red.

## BLOCKER and SHOULD-FIX

| id | finding | what changed, and where | red first | status |
|---|---|---|---|---|
| Trust B1 | `Cylinder.mask` raised `OverflowError` through `place` | `scene.py::_coordinates` bounds every coordinate and radius to 1 km before any arithmetic; `mask` squared as `r * r` (fold 3 restored `radius_m**2`; see fold.md, delta round 2). `tests/test_extremes.py` covers the extremes, with two derandomized property tests counting reach (place: 400 examples, 500 primitives built, 149 valid, 16 masked) | against HEAD (19 red); reverted (16 red) | open |
| Trust S1 | `lint_inputs` missed aliases and indirect spellings | `scripts/lint_inputs.py` resolves import aliases and catches the report's spellings; its docstring says what it can't see; 24 permanent evasion tests | reverted (HEAD's module: 23 red) | open |
| Trust S2 | registry gaps; inheritance evaded detection | the eight rows; protocol classes found through bases; the test-name check reads identifiers (N7), which found three untested gates, now tested | reverted (HEAD's module: 11 red) | open |
| Trust S3 | "meets" without §5.4's closed codes | agent-facing gates read `partial: … refusal-code enum (plan step 3b part b, WT-S1)` | reverted (in the 11) | open |
| Trust S4 | `place` allocated before its budgets | `_within_world_rules` (extent, ownership, mass) before any mask; `_voxelize` masks once and refuses "occupied" inside the window, which rolls back | against HEAD (3 red); reverted | open |
| Trust S5 | `paint` rebuilt every region per paint | `_take_cells` reads the mask's box and copies only regions it takes cells from. 1.92×10⁶ cells, 40 regions, lightly loaded: build 110–115 ms (main 141–149), place 88–95 ms (main 179–193) | reverted (2 red); profiled first | open |
| Trust S6 | physics slower than real time | a Known gap and B5's row, with the load conditions | — (docs) | open |
| Exec S1 | the sources dict outlived the window | `World.writing` commits a copy, after the grid | reverted | open |
| Exec S2, Arch S1 | the membrane held `World`; re-exports bypassed the contracts | `region_parts`/`to_maxim_entity` take `(applier, frames, …)`; `world` is forbidden to the membrane; scans for peeks and re-exports | planted (each red) | open |
| Arch S2 | a failing freeze left the window writable | frozen copies built before any commit | against HEAD; reverted | open |
| Arch S3 | `place` an unmarked owner | `TEMPORARY(phase1/sim-clock)` in `_voxelize`, roadmap row, CLAUDE.md rule | the marker lint | open |
| Arch S4 | `shown` echoed addresses and seed order | plain values by value, others as `<a Type>`, sets sorted; three-seed test | against HEAD; reverted | open |
| Arch S5 | costs unrecorded | boundaries §10 and B5; ignite and extinguish open a sources-only window | reverted | open |

## NITs

Folded: Exec N1, N2, N3, N4 (copyto, fill, put, tuple targets), N5, N6; Arch N1, N2, N3, N4, N6; Trust N1, N4, N5,
N6, N7, N8. Not folded: Exec N4's `getattr` spelling and aliased opener (the scans don't follow values; the arrays
raise at rest), Trust N2 (no profile asks for a memo), Trust N3 and Arch N5 (covered by Arch S5 and Trust S1).

Physics digests: byte-identical to fa27d5f at 0.2, 0.1 and 0.05 m (f7429cba…d256, e9e57122…a0ca, e68e6d7b…db5c).

## Delta round

The delta reports are `delta_executor_wire.md`, `delta_architecture_determinism.md` and `delta_trust_performance.md`.
Each status table below is copied verbatim from its report. The new findings follow, with what changed; their
status is for the reviewers to set (O25).

### Executor and Wire integrity: status set by the Executor and Wire integrity reviewer (O25)

| id | status | evidence |
|---|---|---|
| S1 sources dict outlives the window | **fixed** | `World.writing` commits `MappingProxyType(dict(sources))`. Reverting it to `MappingProxyType(sources)` turns `test_the_sources_stay_read_only_after_an_ignite_and_a_dict_kept_past_its_window_changes_nothing` red. The test writes the mapping after an ignite (the shipped path), so the gap I reported is closed. |
| S2 membrane held `World`, held by imports only | **fixed** | `region_parts` and `to_maxim_entity` now take `(applier, frames)`. `simcore.core.world` joins `membrane-reads-frames`, and README and tests are updated. Planting `frames.latest.cells.regions[...]` or `applier._world.grid...` in `region_parts` turns `test_the_adapters_and_the_protocol_reach_no_world_state_by_attribute` red. Residual: N-a below. |
| N1 `time_s` untested | **fixed** | Hard-coding `"time_s": 0.0` turns `test_snapshot_shapes_dtypes_and_metadata` red (it now checks a frame after `advance`). |
| N2 `on_close` docstring | **fixed** | The docstring now says "closes without raising, whether or not it changed anything". The module-level docstrings went stale in the other direction (S-b). |
| N3 `place` voxelizes twice | **fixed** | `_voxelize` computes one `p.mask(grid)` per primitive. Moving `solid = grid.solid` after painting turns a constructors test red, so the occupancy ordering is held. |
| N4 scan spellings | **fixed** for `copyto`, `fill`, `put` and tuple-unpacking targets (each has a catch test). The residual (`getattr`, an aliased opener) is **rejected** by the author with a reason I accept: the scans don't follow values, and the arrays raise at rest. |
| N5 rollback compared by identity | **fixed** | `_same_regions` compares names, footprints, solidity and `np.array_equal` of the masks. |
| N6 `CellFrame` accepts writable arrays | **fixed** | Removing the `__post_init__` check turns `test_a_frame_refuses_writable_arrays_and_a_grid_whose_window_is_open` red. Removing `of`'s open-window check turns it red too. |

### Architecture, and Determinism and replay: status set by the Architecture and Determinism reviewer (O25)

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

### Trust boundary and Performance: status set by the Trust and Performance reviewer (O25)

| id | status | evidence |
|---|---|---|
| B1 Cylinder overflow through `place` | **fixed** | `scene.py::_coordinates` bounds every coordinate and radius to 1 km before any arithmetic, and `mask` squares as `r*r`. A radius of 1e200, 1.4e154 or 1e300, a centre of 1e200, an origin of 1e308, and an origin of 999 with a 2 m box are all refused as `SpecRejected`. `Scene.build` with a 1e200 radius refuses with `ValueError`. |
| S1 lint_inputs evasions | **open** | Every literal spelling I listed is now caught except `importlib.import_module("pickle").loads(b)` and `__import__("pickle").loads(b)`. Those slip through because of a new chain-skip defect, which also blinds checks that worked before (D-B1 below). |
| S2 registry gaps and inheritance | **fixed** | Rows exist for `Applier.apply`, `primitives_from_data`, `Box`, `Cylinder`, `Material`, `MaterialTable`, `ActionLimits` and `HeatSource`. Planted modules: a direct subclass, an attribute base (`bridge.StructureModulator`), a two-level subclass and a sensor subclass are all flagged. The `import ... as SM` alias base and `self.name` set in `__init__` are not, and the docstring says so. A tuple assignment is not flagged and is not documented (D-N3). `check_gates` is clean on the tree. |
| S3 "meets" without closed codes | **fixed** (the registry is now honest); the codes themselves are **deferred** | Every agent-facing row now reads `partial: free-text refusals until the refusal-code enum (plan step 3b part b, WT-S1)`. The trigger is real: `docs/design/tile_and_client.md` §3.4 and its step table put "the refusal-code enum" in 3b. |
| S4 budgets after allocation | **fixed** | `_within_world_rules` checks extent, ownership and mass before any mask is computed. A spec refused for extent now costs 0.66 ms (main: 58.7 ms). An "occupied" refusal raised inside the window rolls back: material and regions are unchanged, the arrays are read-only, no frame is published and the window is closed. |
| S5 paint rebuilt every region | **fixed** | `_take_cells` copies only the regions a paint takes cells from, and reads only the box the mask covers. Under load on the alley (1.92e6 cells, 40 regions): build 220 ms (main 272), `place` with 32 primitives 121 ms (main 340), and one paint over 38 regions inside a window 9 ms. Each mask is computed once. |
| S6 physics slower than real time | **deferred** (B5 row, step 5a), honest with one wording NIT | The Known gap reads: 0.7 s lightly loaded at 1.92e6 cells, 1.45 s under heavy load, 3.9 s at 5e6 (loaded), "1.4–7.7× real time", with min-of-N, `process_time` and the date. The numbers are stated with their conditions. The range's ends, though, come from different load conditions (D-N4). |
| N1 unhashable quantity | **fixed** | `RegionInstrument` raises `ValueError` and `Frame.reading` raises `ValueError` for a list. |
| N2 uncached `Frame.reading` | **rejected** (author's NIT call) | The reason given, lab-only and no optimization without a profile, is acceptable. Revisit when an NPC percept reads frames. |
| N3 a full window for ignite and extinguish | **fixed** | `World.writing(cells=False)`: ignite copies no cells, publishes no frame, and commits the sources. |
| N4 freeze failure half-commits | **fixed** | A `MemoryError` planted in the third `frozen()` call: the temperature is rolled back, the arrays stay read-only, the sources are unchanged, no frame is published and the window is closed. |
| N5 `.2f` echo | **fixed**, with a new wording NIT (D-N2) | |
| N6 raw region echo | **fixed** | An unknown region is now echoed through `shown`. A 1e6-character region gives a 66-character message. The other two messages echo only a name already in the table. |
| N7 substring test-name check | **fixed** | `_identifiers` reads names from the syntax tree. |
| N8 `range(10**20)` | **fixed** | Refused as `ActionRefused ... got <a range>`. |

### New findings, and what changed

"Against 8c1de1e" means the new test was run against the committed fold's code before the fix and failed. "Reverted"
means the fix was undone in the tree, the test went red, and the fix was restored.

| id | what changed, and where | red first | status |
|---|---|---|---|
| Trust D-B1 | `scripts/lint_inputs.py::_inner` skips only an `Attribute` or `Name` inside a longer chain, never a call, so `open(p).read()`, `Path(p).open().read()`, `np.load(p).copy()`, `json.loads(s).get`, `np.load(..., allow_pickle=True).item()`, `importlib.import_module("pickle").loads` and `__import__("pickle").loads` are findings again; permanent tests for each. The NIT spellings: a positional `allow_pickle`, `__builtins__`, `vars(builtins)`, `builtins.__dict__`, the C loaders, and a constructor registration naming `yaml.constructor`. The docstring states the rest | against 8c1de1e (13 red); reverted (7 red) | open |
| Arch D1 | `tests/test_ownership.py::reexports` also follows attribute chains on every imported simcore object (`import simcore.core.frames as fr; fr.damage…`, `from simcore.core import applier; applier.damage.strike`, `simcore.core.world.heat`) | 8c1de1e's scan returns no finding for either plant | open |
| Arch D2, Exec S-b | a sources-only window publishes a frame again when it closes (the same immutable owners, no copy), so every application has its after-frame and the frames.py and world.py docstrings, boundaries §4.1, lesson 23 and the test name are true; the test asserts `[0, 1, 2, 3, 3]` again | against 8c1de1e (3 red); reverted (2 red) | open |
| Exec S-a, Arch D5 | one owner across both windows: `CellStore.holding()` is the sources-only window's ownership, and `writing()` and `holding()` each refuse while either is open. An ignite inside a raising grid window is now refused, and nothing commits | against 8c1de1e (red: the fire was kept); reverted, both directions (red) | open |
| Exec S-c | `test_the_applier_refuses_a_region_that_is_not_a_name` (`["crate"]`, a dict, `7`, `None`) | reverted (the string check removed: 2 red) | open |
| Arch D3 | `World.writing`'s docstring states the order: the cells commit, the frame publishes, the sources commit; a failure while publishing would leave the cells committed and the sources not (no shipped path raises there) | — (docs) | open |
| Arch D4 | The digest scene has boxes only. A new `test_a_cylinder_scene_is_bit_identical_on_a_rerun` reruns a scene with a cylinder (radius 0.37 m). Compared by hand, that scene's digest is identical on fa27d5f's code and the fold at 0.2 and 0.1 m. That holds for this scene, not for every radius: `r*r` and `r**2` differ by an ulp for about 0.14% of radii, so a cell centre on the circle could change sides | — (a rerun test; the digest comparison is in the hand-off) | open |
| Exec N-c | `shown` echoes a numpy scalar's value (`np.float64(1.5)` as `1.5`) | against 8c1de1e; reverted | open |
| Trust D-N5 | a set of more than 1,000 elements echoes as `<a set of n>`, with no sort | against 8c1de1e; reverted | open |
| Trust D-N2 | the refusals use `.2f` and `.0f` again (bounded now that coordinates stay within 1 km) | against 8c1de1e (`2e+03`) | open |
| Trust D-N6 | `Frame._region` raises `ValueError` | against 8c1de1e; reverted | open |
| Trust D-N3 | `lint_gates._members` sees tuple targets (`name, kind = …`) | against 8c1de1e; reverted | open |
| Exec N-a | the peek scan flags `vars(...)` and `.__dict__` | the scan's own catch tests | open |
| Exec N-b | `test_a_paint_far_from_every_region_copies_no_region_mask` holds the Trust S5 speedup | reverted (`elif True`: red) | open |
| Trust D-N4 | `docs/architecture.md` and B5 give like-for-like ratios: 1.4× lightly loaded at 1.92×10⁶ cells (about 3.6× at 5×10⁶ by scaling), 2.3–2.9× and 7.7× under heavy load | — (docs) | open |

Not folded: Trust D-N1's yaml constructor registered without naming `yaml.constructor`, which the docstring now
names as unseen.

Owner decisions, 2026-11-20, recorded in `docs/plans/checklists.md`:
- step 5a retires `place`'s write window;
- the agent line decides frame retention per agent before agents land.
