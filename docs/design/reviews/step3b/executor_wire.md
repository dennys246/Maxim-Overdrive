# Pre-push review, phase1/gates (3b part a): Executor and Wire integrity

Range: `git diff origin/main...HEAD` at 3a0d482 (d54edc6 plus a merge of origin/main). I re-ran every mutation on a
copy of the tree (rsync, no `.git`), with the worktree's venv and `PYTHONPATH=<copy>/src`, and confirmed that
`simcore` and `maxim_overdrive` imported from the copy. I ran the targeted modules, not the gate. With no `.git` in
the copy, the tests that call `git ls-files` (`test_every_shipped_data_file_is_at_its_formats_current_version` and two
in `test_tooling_config.py`) fail there whatever the code does. I deselected them or ignored them; they are not
findings. The harness is in `scratchpad/3b/review/mutate.py`.

Counts: **0 BLOCKER, 2 SHOULD-FIX, 6 NIT.**

## SHOULD-FIX

### S1. `src/simcore/core/world.py::World.writing`: the writable sources dict outlives the window, and the read-only test only covers construction

`World.writing` yields `sources = dict(self._sources)`, then commits `self._sources = MappingProxyType(sources)`. The
proxy wraps the same dict the caller still holds. The grid's window was built to prevent exactly this (DR-B4: "no
handle outlives the window"), but for the heat sources the handle stays live after the window closes.

Failure scenario, run on the worktree's code:

```python
with w.writing() as s: pass
s["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1e6)   # after the window has closed
dict(w.sources)          # {'fire:x': ...}: the world's sources changed outside the window
w.frames.latest.sequence # still 1: no frame was published for the change
w.advance()              # the crate heats to 71.6 °C from a fire no applier lit
```

Only core code can hold that dict today: the window-opener scan restricts `writing()` to the named owners. So the
trigger is narrow, and that is why this is not a BLOCKER. But it breaks the stated invariant ("World.sources is a
read-only mapping that only the applier changes", boundaries §4.1), and it is the very failure mode that §4.1
rewrote the window to remove.

The guard has a hole too. `tests/test_ownership.py::test_the_region_table_and_the_sources_are_read_only_mappings`
writes `w.sources` only on a freshly built world, whose sources came from `__init__`. I mutated the commit line to
`self._sources = sources` (a plain, writable dict after the first ignite) and all 549 tests in ownership, frames,
constructors, sem_bridge, act_validation, imagination, snapshot and validation stayed **green**. The commit's
"writable sources" proof is real for the constructor: I mutated `__init__` to a plain dict and the test went red. But
it does not cover the path that ships, where every ignite and extinguish replaces the mapping.

Fix: commit a copy, `MappingProxyType(dict(sources))`. Add two tests: after `execute("ignite", ...)`, `w.sources`
refuses `__setitem__`; and a dict kept past `with w.writing() as s` changes nothing when written.

### S2. `src/simcore/adapters/sem/bridge.py::region_parts` / `to_maxim_entity`: "the membrane reads the world only through frames" is held by imports alone, and the code can bypass it without anything turning red

The membrane still receives a `World` (`region_parts(world, region)`, `to_maxim_entity(world, ...)`), and `World`
exposes `.grid`. The `membrane-reads-frames` contract forbids importing `simcore.core.grid`. It does not forbid
reaching the grid as an attribute, and `simcore.core.world` is on the allowed surface.

Proof: in the copy I replaced `solid = frames.latest.is_solid(region)` with
`solid = world.grid.regions[region].solid`. Then:

- ownership, frames, sem_bridge, act_validation and tooling_config were all green (the only failures were the two
  git-environment ones);
- `lint-imports` reported "8 kept, 0 broken";
- `mypy` reported "no issues".

mypy does refuse a planted `self._frames.latest.cells` inside `RegionInstrument`, because that field is typed
`FrameSource`. So the commit's "mypy refused a planted peek through Observation" is true. But `region_parts` holds the
concrete `FrameFeed` and the `World`, and in that scope `.cells` and `.grid` both type-check.

The commit and the checklist do say "B-13's import half", and that wording is honest. Overstated:

- CLAUDE.md now says "observers read published frames, never the world", with no guard behind it;
- the applier's docstring says the membrane "holds an Applier, which exposes no grid, so it can't write or read the
  world any other way", while the same module takes a `World` and calls `world.frames`.

Under the charter this is "a rule kept by luck rather than by a check".

Fix, either of:

- make the membrane's entry points take `(applier, frames)`. The game layer, or a tiny core factory, pulls them off
  the `World`. The bridge then never holds a `World`, and `simcore.core.world` leaves `MEMBRANE_SURFACE`;
- or add an AST test that `simcore/adapters/sem/*.py` uses no attribute named `grid`, `sources`, `advance`, `cells`
  or `writing`, proven by planting the line above.

## NIT

- **N1. `tests/test_snapshot.py::test_snapshot_shapes_dtypes_and_metadata` does not guard `time_s`.** It reads only
  a frame at t=0. I mutated `"time_s": frame.time_s` to `"time_s": 0.0` and everything stayed green. `time_s` is a
  wire field the client will read. Take the frame after one `advance()`. The gap predates this branch, but this
  branch rewrote the line.
- **N2. `src/simcore/core/grid.py::CellStore.on_close`: the docstring says "after each window that changed
  something".** It actually runs after every window that closes without raising, including `with w.writing(): pass`.
  That is harmless, since an extra frame is still correct, but say what it does. Lesson 23's "every write window that
  closes publishes" is the accurate wording.
- **N3. `src/simcore/core/imagination.py::place` now voxelizes every primitive twice,** once for the union and once
  to paint it. At the 32-primitive budget that doubles the mask cost the comment says it bounds. Painting the masks
  from a single pass (paint inside the union loop, then check `union.any()` and roll back by raising) would keep it to
  one pass. For the Performance lens.
- **N4. `tests/test_ownership.py::_Writes` / `window_openers`: the static scans miss some spellings:**
  `np.copyto(g.temperature, x)`, `g.temperature.fill(0)`, `getattr(w.grid, "temperature")[0] = 1` (all three probed:
  not flagged), and an aliased opener (`cm = w.writing; with cm():`). At rest the arrays raise anyway, so this matters
  only for code that runs inside someone else's window (a `power` or `on_substep` callback). Worth a line in the
  docstring saying what the scans don't see, or add `copyto`, `fill` and `put` to the call checks.
- **N5. `tests/test_ownership.py::test_a_window_that_raises_changes_nothing` compares
  `dict(g.regions) == before[1]`.** That works only because rollback restores the same `Region` objects, so the tuple
  comparison short-circuits on identity. With equal-but-distinct objects it would raise "truth value of an array is
  ambiguous" (it did under my M3b) instead of a clear assertion. Compare by `is` or by keys plus `np.array_equal`.
- **N6. `src/simcore/core/frames.py::CellFrame` does not freeze what it is given.** `CellFrame.of` passes the
  read-only owners, but the constructor (and `dataclasses.replace`, which `test_snapshot.py` uses) accepts writable
  arrays. That contradicts "frozen means deep" (§5.1). A `__post_init__` that rejects writable arrays (or freezes
  them) would make the claim true of the type, not only of `of`.

## Wire integrity

| Contract | Producers before → after | Consumers before → after | What each consumer gets |
|---|---|---|---|
| `encoding.snapshot(grid)` → `snapshot(CellFrame)` | grid → `frames.latest.cells` | `tests/test_snapshot.py` only (no server or client caller yet; `golden_run.py` and `src/maxim_overdrive` don't call it) | The same keys, dtypes and values. `cell_size_m` stays (correctly: the renderer needs it). `material` is still a copy. `time_s` is unguarded (N1). |
| `SensorReading.extra` | `{"cell_size_m": dx}` → `{}` | Maxim memory and episode code pass `extra` through. No pymaxim 1.3.3 code reads `cell_size_m` (searched site-packages) | The BF-N4 drop. Held by `test_frames.py` (M9 red). |
| `Entity.metadata` | `{source, cell_size_m}` → `{source}` | Maxim (no reader of `cell_size_m`) | Held (M9b red). |
| `SensorReading.timestamp` | `grid.time_s` → `frame.time_s` | Maxim | Equal on every shipped path: every advance publishes. |
| `StructureModulator(world, region)` → `(applier, frames, region)`; unknown region `KeyError` → `ValueError` | bridge | `region_parts`, tests (`test_validation`, `test_act_validation`) | All updated. No `except KeyError` callers left in src or scripts. |
| `RegionSensor(world, …)` → `RegionInstrument(frames, …)`; unknown region `KeyError` → `ValueError` | bridge | `region_parts`, tests | Updated. Old name only in design and research docs (historical). |
| Bridge exports removed (`parse_action`, `Strike`, `Ignite`, `Extinguish`, `ActionRefused`, `MAXIM_CALL_KEYS`, `StructureModulator.apply` / `centroid_m`) | bridge → `core.intents` / `core.applier` | tests only; README uses only `to_maxim_entity` and `execute` | README example still valid. |
| `ModulatorResult.params` / `metadata` | `StructureModulator.apply` → `Applier.apply` `Outcome` → `_from` | Maxim | Same keys and values. Stage-2 refusals still carry the finite params (as on main). Strike metadata is still `{destroyed_volume_m3, absorbed_j}`. |
| `World.sources`: dict → read-only mapping; `World(sources=)` kwarg added | world, applier | tests that wrote `w.sources[...]` (rewritten to `execute` or the constructor) | Read-only only until the first applier write (S1). |
| Cell writes outside a window now raise | grid | `heat.step`, `damage.*`, `paint`, `place`, `Scene.build`: every caller in src opens the window (grep) | Tests updated to open it. |
| `Budget` gains `max_primitives=32`, `max_name_chars=64` | imagination | `place` callers: tests only; no data file carries specs | New refusals, tested (M11 red). |
| `RigProfile` validates in the constructor; the message changed | tiers | `RigProfile.load`, tests | Shipped rigs load. Whitespace-only names are now refused (new behaviour, tested). |
| `known_keys` / `checks` refusal text, via `shown` | checks | every loader and its tests | Same text for ordinary keys. Bounded (M10 red). |
| Frame publication (new lifecycle) | `CellStore.writing` close → `World._publish` | `RegionInstrument`, `frames.latest` | Published after every successful window; nothing on a raising window (M5, M5b red). |

## Claims verified

Every mutation below was planted in the copy and run against the eight targeted modules:

- **Grid window and freezing.** These went red: the window keeping its writable owners (M1); a freeze that only
  clears the flag (M2); no rollback (M3), rollback skipping regions (M3b) and rollback skipping the clock (M3c);
  nested windows allowed (M4); publication removed (M5); a publish on a raising window (M5b); a frame sharing the
  live region table (M6).
- **Planted writer and opener in the membrane.** Both went red (M7, M8).
- **Other mutations.** These went red: the cell size back in a reading and in entity metadata (M9, M9b); unbounded
  echo (M10); the budget skipped (M11); Budget not validating (M12); Material not validating (M13).
- **Writable sources.** Red only for the constructor; green on the applier's path (S1).
- **Extra mutations of mine, all red.** Applier missing its air check, its gone check or its limits recheck;
  `Region` masks not frozen; `RigProfile` not validating; a refused strike opening a window; `place`'s name check
  removed; `MaterialTable` lookups writable; the frame time stamp; the modulator accepting an unknown region.
- **"publication removed also turned test_sem_bridge's strike-then-read red".** True:
  `test_strike_moves_the_integrity_sensor[0.2]`.
- **"The writer scan flags main's own bridge (apply, _ignite)".** True: `writers()` on
  `origin/main:src/simcore/adapters/sem/bridge.py` returns exactly `StructureModulator.apply` and
  `StructureModulator._ignite`.
- **Planted imports.** The four `PLANTED` cases in `test_tooling_config.py` pass: each plant turns `lint-imports`
  red with the named contract. So do the contract-shape tests and all of `test_lint_gates.py` (the four §5.2
  registry proofs are real, non-vacuous tests).
- **mypy refuses `.cells` through `Observation`.** True: `"Observation" has no attribute "cells"`. Only inside the
  `FrameSource`-typed field, though (S2).
- **Determinism digests unchanged.** `test_determinism.py` (88 tests, default tiers) passes against its unchanged
  stored digests. I did not run the 0.05 m tier.
- **Every writer to the cells in src opens the window,** and only the seven listed owners do. Confirmed by grep for
  `damage.strike`, `heat.step`, `.paint(` and `place(`.
- **"Each gate module is held at 100% branch coverage by the floor".** True: `fail_under = 100`.
- **Lesson 23's "a planted mutation of World.__init__" (removing `on_close`) turns `test_sem_bridge` red.**
  Consistent with M5.
