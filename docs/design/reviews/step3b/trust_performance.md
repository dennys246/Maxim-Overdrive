# Pre-push review: Trust boundary and Performance, `phase1/gates`

Diff: `git diff origin/main...HEAD` (d54edc6 plus merge 3a0d482). I read the code and ran probes on a copy
(`scratchpad/3b/review/copy`) using the worktree's venv. I did not modify the worktree. All timings are CPU time
(`process_time`), the minimum of 2 to 5 runs, on a heavily loaded machine. Treat them as orders of magnitude.

Counts: **1 BLOCKER, 6 SHOULD-FIX, 8 NIT.**

## BLOCKER

### B1. `src/simcore/core/scene.py::Cylinder.mask`, reached through `src/simcore/core/imagination.py::place`: one JSON number crashes the imagination gate with `OverflowError`

`Cylinder.__post_init__` accepts any finite radius. `place` then voxelizes. `Cylinder.mask` computes
`self.radius_m**2` on a Python float, and that raises `OverflowError` when the radius is above about 1.34e154. The
neighbouring `volume_m3` uses `r*r` for exactly this reason (its comment says "`**` raises on overflow"). `mask` does
not.

Probe: `place(grid, {"name": "c", "primitives": [{"kind": "cylinder", "center_xy_m": [1.5, 1.5], "radius_m": 1e200,
"z_m": [0, 0.5], "material": "wood"}]}, (0, 0, 0))` raises **`OverflowError: (34, 'Result too large')`**, not
`SpecRejected`.

This contradicts three things:
- `place`'s docstring: "every malformed shape is a rejection, never another exception".
- CLAUDE.md: "Imagined objects enter only through `place`, which validates them".
- The new registry row `imagination.py::place` with status "meets". §5.4 requires "one exception type
  (`ValueError`)".

An LLM's spec is exactly this kind of JSON. `Scene.build` has the same crash for an authored cylinder, though its
row is honestly "to-be".

Why the tests miss it: the property test
`tests/test_validation.py::test_an_imagined_object_from_any_json_is_placed_or_refused_...` caps valid geometry.
`_good_cylinder` radii lie in [0.1, 0.9]. `_number` lies in [-5, 5]. Origins lie in [0, 3]. `_bad_primitive` almost
never assembles all four required cylinder keys. So no example comes near a magnitude edge (the "measure fuzz reach"
rule).

Fix:
- Use `self.radius_m * self.radius_m`, or better, refuse any coordinate or radius beyond `MAX_EXTENT_M` in the
  `Box` and `Cylinder` constructors. A tile is at most 1 km, so a 1e154 m radius is not a shape.
- Add magnitude strategies (`st.floats(allow_infinity=False)` without bounds, plus 1e150 to 1e308) to the place and
  scene fuzzers.
- Count how many examples reach `mask`.

The same family gives numpy overflow `RuntimeWarning`s: `(x - cx)**2` with an origin or centre near 1e200. Those are
harmless in production, but they become errors under the test suite's warnings-as-errors rule.

## SHOULD-FIX

### S1. `scripts/lint_inputs.py::unsafe_findings` and `::input_findings`: aliases and indirect spellings evade both rules, so the docstring's claim is false

The docstring says: "read from the syntax tree so spacing, aliases and line breaks can't hide a call". Matching is
done on literal dotted names (`yaml.load`, `np.load`, `json.loads`, `eval`), with no resolution of import aliases.
Probes on the real functions:

| Source | Caught? |
|---|---|
| `import yaml as y; y.load(s, Loader=y.Loader)` | **no** (unsafe check) |
| `from yaml import unsafe_load; unsafe_load(s)` | **no** |
| `from yaml import load, Loader; load(s, Loader=Loader)` | **no** |
| `getattr(yaml, "unsafe_load")(s)` | **no** |
| `importlib.import_module("pickle").loads(b)`, `__import__("pickle")` | **no** |
| `import _pickle` | **no** (`UNSAFE_MODULES` lacks `_pickle`) |
| `np.load(p, allow_pickle=flag)`, `np.load(p, **{"allow_pickle": True})` | **no** (literal `True` only) |
| `builtins.eval(s)`, `e = eval; e(s)` | **no** |
| `import numpy as n; n.load(p)` in `src/simcore/core/` | **no** (input rule) |
| `from os import environ as env`, `import sys as s; s.argv` | **no** |
| `import json as j; j.loads(s)` | no, but the import-linter `input-primitives` contract catches the import in `src/` |

Concrete failure: inside `src/simcore/adapters/loaders.py`, the one module where `ignore_imports` lets `yaml` in,
write `import yaml as y` and then `y.load(path.read_text(), Loader=y.Loader)`. That passes import-linter and both lint
rules. `yaml.Loader` builds arbitrary Python objects (`!!python/object/apply`), so a scene or material file could then
run code. In `scripts/` and `tests/` the import-linter contract does not apply at all, so every unsafe-decoder row in
the table above stands unguarded there.

Fix:
- Build a per-module alias table from `Import` and `ImportFrom` (local name to canonical dotted name) and match
  canonical names.
- Flag the `importlib.import_module`, `__import__` and `getattr` routes when their argument is a banned literal, and
  flag any `getattr(yaml, ...)`.
- Add `_pickle`, `builtins.eval` and `builtins.exec`.
- Treat a non-literal `allow_pickle` and `**kwargs` as unsafe.
- Either make it hold or narrow the docstring's claim.

### S2. `scripts/lint_gates.py::GATES` and `::entry_points`: entry points with no row, and protocol detection evaded by inheritance

The registry only requires rows for public callables in `GATE_MODULES`. Untrusted data reaches several core
callables outside those modules, and none of them has a row:

- `src/simcore/core/applier.py::Applier.apply`, the §5.3 stage-2 (authorization) check. Per the `TEMPORARY(phase1/agents)`
  note, the host's step will call it directly with logged intents, bypassing `StructureModulator.execute`. Its
  refusal path `_check_region` echoes `region` without `shown`.
- `src/simcore/core/scene.py::primitives_from_data`, `::Box` and `::Cylinder`. `place` calls them with LLM data, and
  B1 sits in one of them.
- `src/simcore/core/materials.py::Material` and `::MaterialTable`, `src/simcore/core/limits.py::ActionLimits`, and
  `src/simcore/core/world.py::HeatSource`. The commit message names Material and MaterialTable alongside RigProfile
  and Budget as validating constructors (§5.1), but only RigProfile and Budget have rows.

Detection gap (probed with `entry_points`):
- `class Door(StructureModulator): def execute(self, affordance, params): ...` in a new module yields **no** protocol
  methods. `_members` sees only names defined in the class body, so a subclass that overrides `execute` and inherits
  `name` and `affordances` needs no row.
- The same holds for `self.name = ...` set in `__init__`, for a tuple assignment (`name, affordances = ...`) and for a
  class defined inside a function.

Subclassing `StructureModulator` is the obvious way to add a door or vehicle modulator, so this is a likely route,
not a contrived one.

Fix:
- Add `core/applier.py` and `core/scene.py` (or at least the named callables) to the registry.
- Detect protocol classes by base name as well: any class whose bases include a registered protocol class is itself
  a protocol class.

### S3. `scripts/lint_gates.py::GATES`: `StructureModulator.execute` and `place` are marked "meets", but §5.4 is not met

§5.4 says: "anything agent-facing (errors, receipts) uses a **closed code vocabulary**, never exception text". Both
rows break it:
- `execute` returns `ModulatorResult.error = str(ActionRefused)`, which is free text.
- `place` raises `SpecRejected(f"malformed spec: {exc}")`, which wraps another exception's text.

Neither has a code. `place` also allocates the full-grid `union` and voxelizes every primitive before its extent and
mass budgets are checked (S4), and §5.4 says "budgets checked before allocation".

The registry is the stated source of truth for "which gates meet this bar" (§5.4, last line). "meets" is therefore a
false claim on two LLM-facing gates. Fix: either use `to-be: <step>` (the closed code vocabulary has no step in the
roadmap that I found; `grep "closed code"` finds only design docs), or add the codes.

### S4. `src/simcore/core/imagination.py::place` and `::Budget`: extent and mass are checked after voxelization, so the docstring "Every limit is checked before anything is allocated" is false

`footprint_of(placed)`, `across_m` and `mass` depend only on authored geometry. They are computed only after
`union = np.zeros(grid.shape)` and 32 `p.mask(grid)` calls. Measured on the alley (40 × 8 × 6 m at 0.1 m, 1.92e6
cells): a spec of 32 boxes 10 m wide costs **60 ms** to refuse for size. A geometry-only check would refuse it in
microseconds.

Moving it forward costs nothing, and it closes a cheap CPU lever for an LLM or a guest. The occupancy and region
checks need the grid. Extent and mass do not. Fix: check extent, mass and footprint overlap right after `_read`.

### S5. `src/simcore/core/grid.py::MaterialGrid.paint`: every paint rebuilds every region, at O(P·R·cells) with allocations

Main narrowed region masks in place (`np.logical_and(..., out=other.cells)`). The branch builds, for each region on
each paint, a new `Region(other.cells & ~mask, ...)`. That is a fresh `~mask` (recomputed inside the loop), a fresh
`&`, and `frozen()`'s `tobytes` copy. For a 1.9 MB grid that is three full-grid allocations per region per primitive.

Measured on the alley with 40 named regions:

| Operation | origin/main | branch | change |
|---|---|---|---|
| `Scene.build` | 315 ms | 392 ms | +25% |
| `place` (32 primitives) | 396 ms | 578 ms | +46% |

cProfile of one `place`: `paint` takes 0.43 s of 0.74 s, across 1,285 `frozen` calls.

Both costs are quadratic in practice:
- `build` with N named primitives does about N²/2 rebuilds.
- `place` does P × R rebuilds.

At the max profile (5e6 cells, 2.6× the alley), with a tile of about 200 regions, one imagined 32-primitive object
would cost several seconds of simulation-lane CPU. That is the lane every NPC waits on, and an LLM triggers it.

Fix:
- Compute `~mask` once.
- Skip regions whose footprint box doesn't meet the primitive's bounds (`boxes_overlap`).
- In `place`, paint one union per material, not one mask per primitive. This also removes the second `p.mask(grid)`
  per primitive: 64 mask evaluations today, 137 ms.

Until then, `place` and scene build need a B5 row. The current B5 trigger (step 5a) covers turn time and snapshots,
not `imagine`.

### S6. Out of the diff, but it bears on "does it fit": physics at the alley runs about 3× slower than real time

This is not caused by the branch: `advance(0.5)` costs the same on main, 1,411 ms against 1,387 ms. It answers the
brief's question directly, though.

| Tile at 0.1 m | `advance(0.5)` CPU time | substeps |
|---|---|---|
| alley, 1.92e6 cells | 1.45 s | 16 |
| 5.04e6 cells | 3.9 s | 16 |

With "physics every 0.5 s", the heat law alone takes about 2.9× (alley) to 7.7× (5e6 cells) the wall-clock budget,
before any NPC or the client.

The window does fit (see the Performance section below). The physics does not. Record it with these numbers now (a
B5 row or an architecture known gap), rather than at step 5a.

## NIT

- **N1.** `src/simcore/adapters/sem/bridge.py::RegionInstrument.__init__` and
  `src/simcore/core/frames.py::Frame.reading`: an unhashable `quantity` (or `region`, for `reading`) raises
  `TypeError` ("cannot use 'list' as a dict key"), not `ValueError`, and the row is marked "meets". Only code calls
  these today. Add an `isinstance(quantity, str)` guard.
- **N2.** `src/simcore/core/frames.py::Frame.reading` recomputes on every call. On the alley: integrity 1.4 ms,
  breached 7.6 ms (scipy labelling), temperature_max 0.45 ms. A full sweep of 40 regions × 4 quantities costs about
  0.4 s per observer per frame. The frame is immutable, so a per-frame memo is free. It is lab-only today, but
  `to_maxim_entity` hands these instruments to Maxim.
- **N3.** `src/simcore/core/applier.py::Applier._ignite` and `::_extinguish` open a full window, copying all four
  channels twice (about 54 MB on the alley, 2.5 ms), just to change the sources dict. It is fine now. Note it for the
  sim-clock step, where the step owns one window for all intents.
- **N4.** `src/simcore/core/grid.py::CellStore.writing`: the freeze in the `else` branch is outside the `except`.
  If `frozen()` raises (a `MemoryError` is plausible at the max profile, where a window briefly holds three copies, 42
  B/cell, about 210 MB at 5e6 cells), the channels are left as the writable copies. Also, `World.writing` has already
  swapped in the new `_sources`. The result is a half-applied, unfrozen window. Freeze into locals, then commit.
- **N5.** `src/simcore/core/imagination.py::place` "too large" message: `{across_m:.2f}` of 2e154 prints 155 digits
  (probe output). It is bounded at about 320 characters, so not a flood, but `:.3g` reads better and keeps the echo
  short.
- **N6.** `src/simcore/core/applier.py::Applier._check_region` echoes `region` raw, not through `shown`. It is safe
  only because every caller pre-validates the region. Use `shown` or a closed code.
- **N7.** `scripts/lint_gates.py::_row_problems` checks that a row's test module "names" its gate by substring. Short
  names such as `read`, `name`, `unit` and `value` occur in almost any test file, so the check cannot fail for them.
- **N8.** `src/simcore/core/intents.py::Strike.__post_init__` catches only `ValueError`. Then
  `Strike(1.0, 0.2, range(10**20))` escapes as `OverflowError`, because `len()` overflows in `finite_vector`. JSON
  cannot produce this, so it is a Python-caller edge case. `finite_vector` could catch `OverflowError` around `len`.

## Performance: the write window and frames, at tile scale

Cost per window: `CellStore.writing` copies the four channels on entry (`arr.copy()`) and again on exit
(`frozen()` → `tobytes`). That is 14 bytes per cell each way:

| Grid | Cells | Copied per window | Measured CPU time |
|---|---|---|---|
| alley | 1.92e6 | about 54 MB | 1.8 to 3.1 ms |
| max profile | 5.04e6 | about 141 MB | 5.1 ms |

Frame publication (`CellFrame.of`) is a few attribute reads and a shallow copy of the regions dict. It is negligible,
and inside those numbers.

What one window means for each kind of work, on the alley:

| Work | Total | Window's share |
|---|---|---|
| `advance(0.5)` | 1.45 s | 0.1 to 0.2% |
| strike | 16.5 ms | about 2 to 3 ms |
| ignite | 2.5 ms | mostly the window |
| 20 accepted actions per second | — | about 50 ms/s of copies, about 5% of one core |

**Verdict:** the double copy fits at this scale and does not need its own B5 row now. The second copy is the price of
irrevocable read-only memory. A `memoryview(...).toreadonly()` of a bytearray would avoid it, but `.base.obj` gives
the writable bytearray back, so the copy is justified. What does need budgets now are `place` and scene build (S5)
and the heat law itself (S6).

Allocation per primitive and quadratic paths:
- `paint`'s region rebuild (S5).
- The duplicate `p.mask` in `place` (S5).
- `Region.__post_init__` copying every mask. This is fine on its own, but it multiplies S5.
- No other quadratic path in the diff: `_on_region` and the footprint checks are O(R) on bounding boxes.

## Claims verified

- **The read-only arrays really are irrevocable** (commit message, `readonly.frozen`). Re-enabling write is refused
  with `ValueError` five ways: `setflags(write=True)`, on `.base`, `np.add(..., out=a)`, `as_strided(writeable=True)`,
  and through a `view()`. **True.**
- **"The write window copies every channel twice per window"** (brief). **True**: copy on entry, `tobytes` on exit.
  Measured above.
- **"`place` checks a primitive count and a name length before allocating, and voxelizes one mask at a time instead
  of stacking"** (commit message). **True**, but each mask is computed twice, and the extent and mass budgets come
  after allocation (S4).
- **The SEM membrane's echo is bounded.** Probes against `execute`: a 100,000-character string value, a
  100,000-character key, `10**5000`, a `point_m` list of a million items, a list or dict `target`, `None` params, and
  a list or dict affordance. Every one returns a failed result with a message of at most about 100 characters, and no
  exception escapes. **True.**
- **"The membrane's unknown-region refusal is a `ValueError`"** (commit message). **True** for `StructureModulator`
  and `RegionInstrument`, including an unhashable region. An unhashable quantity is the exception (N1).
- **`lint_gates` passes on the real tree** (`check_gates` returns `[]`). **True.** Its gaps are what it does not ask
  for (S2).
- **"bans pickle, marshal, unsafe yaml loaders, `np.load(allow_pickle=True)`, eval and exec everywhere"** (commit
  message). **True only for literal spellings** (S1). It is conservative in one direction: `L = yaml.SafeLoader;
  yaml.load(s, Loader=L)` is flagged as unsafe, which is a false positive and harmless.
- **"Physics is unchanged"** (commit message). Consistent with the timing: `advance` costs the same on main and the
  branch. I did not recheck the digests.
- **`World.writing` rolls back the sources** when the body raises. **True**: the assignment comes after the `yield`.
  The one exception is a failure inside the freeze (N4).
