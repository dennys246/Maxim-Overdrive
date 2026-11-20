# Delta round, step 3b(a) fold: Executor and Wire integrity

**Range:** `git diff 3a0d482` against the uncommitted, staged fold in `.worktrees/gates`.

**Method:** I copied the worktree (rsync, without `.venv` or `.git`) and ran it with the worktree's venv and
`PYTHONPATH=<copy>/src`. All of the following pass on the copy: ownership, frames, constructors, sem_bridge,
act_validation, imagination, snapshot, validation and extremes, 656 tests in total. I deselected the one test that
needs `git ls-files`.

I then applied 19 mutations, one at a time (harness in `scratchpad/3b/review/delta/mutate.py`). I also ran the
README example against the worktree; it runs.

## Status of my round-1 findings (set from the tree)

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

### The fold's other claims I re-proved red (each mutation turned a named test red)

- **Arch S2, freeze and commit inside the try:** moving the freeze back to `else` turns
  `test_a_failure_while_the_window_closes_...` red. So does committing the sources before the grid's window.
- **Arch S5, the sources-only window:** an ignite that opens a cell window turns
  `test_a_window_that_changes_only_the_sources_...` red.
- **Nested World windows:** turns `test_the_world_window_has_one_owner_at_a_time_too` red.
- **`_take_cells`:** never copying a touched region turns a frames test red. Skipping the narrowing of in-window masks
  turns a validation test red.
- **`place`:** removing the occupancy check turns an imagination test red.
- **`_coordinates`:** removing the 1 km bound turns `test_extremes` red.
- **The turn counted after the window:** the `pass` mutation turns a validation test red.

## New findings

Counts: **0 BLOCKER, 3 SHOULD-FIX, 3 NIT.**

### S-a. SHOULD-FIX: `src/simcore/core/world.py::World.writing`: the two window locks are independent, so a sources window opens inside a grid window, and the grid's rollback does not undo it

`cells=False` takes only `World._sources_open`. `CellStore.writing` takes only `CellStore._open`. Neither checks the
other. So "one owner at a time" and "a window that raises changes nothing" no longer hold across the two. I ran this
on the worktree:

```python
with w.grid.writing():
    w.grid.temperature[:] = 500.0
    Applier(w).apply("crate", Ignite(1000.0, 0.3))   # succeeds: a sources-only window opens inside the grid's
    raise RuntimeError("grid window fails")
# temperature rolled back to 20.0, but w.sources == {'fire:crate': ...}: half the window committed
with w.writing(cells=False):
    with w.grid.writing(): ...                        # also allowed: two owners at once
```

Today no shipped path nests these:

- `advance` holds the sources lock, so nested applier calls are refused;
- `place` and `Scene.build` open only the grid's window, with nothing inside that applies.

So the trigger is narrow. But the rule is kept by luck: `test_the_world_window_has_one_owner_at_a_time_too` only
nests `cells=False` in `cells=False`.

**Fix:** in `World.writing`, refuse when `self._grid.is_writing`. For the reverse order, refuse a grid window while
the world's sources window is open (the grid can hold a reference, or the world can wrap the grid's lock). Test both
nestings.

### S-b. SHOULD-FIX: docstrings, design and lesson still say every application and every window publishes a frame; since the fold, ignite and extinguish publish none

The fold changed the publication contract: a sources-only window "publishes nothing". The test now asserts
`[0, 0, 1, 2, 2]`. These texts still claim the old contract:

- `src/simcore/core/frames.py` module docstring: published "after each write window closes, which is after each
  intent application and each advance".
- `src/simcore/core/world.py` module docstring: "Each window that closes publishes a frame".
- `docs/design/boundaries.md` §4.1: "Until sim-clock, the applier publishes a frame after each application". §10's
  as-built note says the opposite.
- `docs/lessons_maxim_in_games.md` §23 *Consequence*: "every write window that closes publishes", citing the test
  below as the guard.
- `tests/test_ownership.py::test_the_shipped_path_publishes_a_frame_after_each_application_and_each_advance`: the name
  states what its assertion now denies.

**Wire effect:** after `execute("ignite")`, Maxim's post-execute sensor read sees the same frame and sequence as
before. That is correct, since no cell changed. But any later consumer that takes "one frame per applied intent" as
a receipt (§4.2: "a receipt's after-frame exists on its apply tick") will find none for ignite or extinguish. The
change is defensible; the claims about it are wrong, and CLAUDE.md treats a claim as a contract.

**Fix:** rewrite the five texts. Rename the test, for example to `..._after_each_cell_change_and_each_advance`. State
in §4.2 that a sources-only intent has no after-frame, so step 5a's receipt design sees it.

### S-c. SHOULD-FIX: `src/simcore/core/applier.py::Applier._check_region`: the new `isinstance(region, str)` guard has no test that fails without it

The fold registers `Applier.apply` as a gate (`partial`). It adds a guard so that a non-string region is refused,
instead of raising `TypeError: unhashable` from `region in regions`, which is what 3a0d482 did. I dropped the
`isinstance` and all 656 targeted tests stayed **green**.

The guard is correct: on the worktree, `Applier(w).apply(["crate"], Ignite(1, 0.3))` returns a refused `Outcome`.
But the charter's Executor question ("would the test fail if the mechanism were deleted?") gets a no. Branch coverage
can't see it either, because it is an `or` inside one condition. The membrane only ever passes a `str`, so the
trigger is narrow, but this is a registered gate's rejection path.

**Fix:** add a parametrized test (`["crate"]`, `{"a": 1}`, `7`, `None`) asserting a refused `Outcome` naming the
value through `shown`.

### N-a. NIT: `tests/test_ownership.py::peeks`: `vars()` and `__dict__` subscripts evade the attribute scan

I planted `vars(vars(applier)["_world"])["_grid"].regions[region].solid` in `region_parts`. The scan, the import
contracts and the 656 tests all stayed green. The applier's docstring now says the import contracts and the scans
"keep it to" `limits` and `apply`. Either add `vars`, `__dict__` and a literal-name `getattr` to `PEEKS` handling, or
say in the docstring that the scan guards mistakes, not evasion (as `lint_inputs` does).

### N-b. NIT: `src/simcore/core/grid.py::CellStore._take_cells`: the copy-only-what-a-paint-takes optimization has no guard

Making the untouched-region check always copy (`elif True:`) left everything green. That is functionally correct,
which is why the suite can't see it; it is the Trust S5 speedup (`_take_cells` was 315 of 380 ms). If the measured
gain matters, a test that counts which regions get copied would hold it, for example asserting that a paint far from
every region leaves `grid._masks` empty.

### N-c. NIT: `src/simcore/core/checks.py::shown`: numpy scalars now echo as `<a float64>`

The fix for Arch S4 prints every non-plain type by type name. That includes numpy scalars, whose repr has no address
and is deterministic. So `finite_real(np.float64("nan"), "x")` now says "x must be a finite number, got
`<a float64>`", where it used to say `nan`. The same happens inside containers (`[<a float64>]`). JSON and YAML input
never carries numpy scalars, so the agent-facing text is unaffected. Internal callers (`Material` built from numpy, as
`test_constructors` does) lose the value in the message. Printing `float(x)` or `int(x)` for `np.floating` and
`np.integer` would keep it run-independent.

## Wire integrity: contracts the fold touches

| Contract | Before (3a0d482) → after | Consumers | What they get |
|---|---|---|---|
| `region_parts(world, region)` → `(applier, frames, region)`; `to_maxim_entity(world, region, type)` → `(applier, frames, region, type)` | bridge | README (updated, runs), tests (updated; all pass); no src or scripts caller | Same parts, same metadata. A positional old-style call now fails with a `TypeError` (no silent misuse). |
| `World.frames`: `FrameFeed` → `FrameView` (no `publish`) | world | instruments, modulator constructor, tests | `.latest` only. Typed `FrameSource`, which is unchanged. |
| Frame cadence: every window → cell windows only | world, applier | instruments (Maxim's post-execute read), tests | Same readings, since a sources change has no cell effect. Docs are stale (S-b). |
| `World.writing(*, cells=True)` new keyword | world | applier (`_ignite`, `_extinguish`), tests | Default is unchanged for `advance` and `_strike`. Lock interplay: S-a. |
| `CellFrame.__init__` refuses writable arrays; `CellFrame.of` refuses an open window | frames | world `_publish`, tests (`test_snapshot` now wraps with `frozen`) | Correct on the shipped path: `_publish` runs after `_open=False`. |
| `CellStore.regions` inside a window: a live table built from in-window masks; `_regions` swapped at close | grid | applier (outside windows), `place` (reads before its window), damage (doesn't read regions) | Each in-window read freezes a copy of every changed mask (a cost, no correctness issue). |
| `Applier.centroid_m` → private `_centroid_m`, no longer re-checks | applier | internal only (`_strike`, `_ignite`, both after `_check_region`) | Unchanged results. |
| `shown` echo text | checks | every refusal message | Plain values unchanged. Objects print as `<a T>`, sets sorted, numpy scalars `<a float64>` (N-c). |
| Primitive coordinates within 1 km; `Cylinder.mask` squares as `r*r` | scene | `place`, `Scene.build`, `primitives_from_data` | New refusals. Shipped scenes and data are inside 1 km. Digests are byte-identical per fold.md; I did not rerun them in this delta. |
| `place` refusal order: extent, ownership and mass before occupancy | imagination | callers of `place` (tests) | A spec that is both too heavy and occupied now reads "too heavy" (documented in fold.md). |
| `membrane-reads-frames` forbids `simcore.core.world` | pyproject | bridge (no longer imports it) | `lint-imports` is green per the tests; the planted-import tests in `test_tooling_config.py` were not rerun here. |
