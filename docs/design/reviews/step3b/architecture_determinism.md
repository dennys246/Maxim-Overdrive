# Pre-push review: Architecture, and Determinism and replay — `phase1/gates` (3a0d482)

Diff: `git diff origin/main...HEAD` (d54edc6 plus the merge). Read against `docs/code_review.md`, CLAUDE.md,
`docs/design/boundaries.md` §2.2, §3, §4.1, §4.2, §4.4, §5, §6.4, §10, §11.1. Probes ran on a copy
(`scratchpad/3b/review/arch_copy`, with `scratchpad/3b/review/probe_arch.py` and `probe_echo.py`), with the worktree's
venv. The worktree was not touched.

**Counts: 0 BLOCKER, 5 SHOULD-FIX, 6 NIT.**

## SHOULD-FIX

### S1. The skip-layer and membrane contracts can be bypassed through re-exports and `World.grid`
`pyproject.toml::[tool.importlinter] skip-layer`, `membrane-reads-frames`; `src/simcore/core/world.py::World.grid`

import-linter records `from simcore.core.world import heat` as an import of `simcore.core.world` (allowed), not of
`simcore.core.heat`, because `heat` is an attribute of `world` and not a submodule of it. Every forbidden module is
re-exported by an allowed one: `world` exports `heat`, `damage`, `MaterialGrid`, `Scene`; `frames` exports `damage`,
`MaterialGrid`, `Region`; `applier` exports `damage`. On top of that, the membrane imports `World` and is handed one
(`region_parts(world, …)`, `to_maxim_entity(world, …)`), so `world.grid.temperature` is one attribute away. That is a
raw read of the cells that bypasses frames.

*Proven.* I planted these lines on the copy:
`from simcore.core.world import heat`, `from simcore.core.frames import MaterialGrid` (in `protocol/encoding.py`), and
`from simcore.core.applier import damage` plus `def peek(world: World) -> float: return float(world.grid.temperature.max())`
(in `adapters/sem/bridge.py`). The gate's own command reported **"Contracts: 8 kept, 0 broken."** The ownership scans
stay green too (`peek` reads and does not write). mypy accepts `peek`, because `World.grid` is typed `MaterialGrid`.
So the commit's "mypy refuses a peek" holds only for code typed against `Observation` (the instruments). It does not
hold for the membrane as a module, and B-13's import half ("the membrane reads frames … only") holds by convention.

*Scenario.* A later membrane change reads `world.grid.integrity[...]` to "speed up" a reading, or the protocol
imports `heat` via `world`. Every check stays green, and the rule "observers read published frames, never the world"
(CLAUDE.md, "Rules that matter here") is broken without anything going red.

*Fix direction.* (a) Have `region_parts` and `to_maxim_entity` take `(frames: FrameSource, applier: Applier)`
instead of `World`, so the membrane never holds a `World`. The host or game builds both. (b) Add a small AST lint, or
a test beside the contract-list tests: in `simcore.adapters` and `simcore.protocol`, a `from <surface module> import
X` must name something defined in that module. Alternatively, give the surface modules `__all__` and hold imports to
it. (c) Until sim-clock retires `World.grid`, consider naming it private-by-convention (`_grid`) for anything outside
the core.

### S2. A failure while the window is closing leaves the world writable at rest, committed and unpublished
`src/simcore/core/grid.py::CellStore.writing`

The freeze at exit is in the `else:` arm, which `except BaseException` does not cover. If
`{name: frozen(arr) …}` raises partway (a `MemoryError` from `tobytes()` on a large grid, or a `KeyboardInterrupt`),
`self._channels` is left as the window's **writable** copies, `_open` is reset to False, no callback runs, and
`World.writing` has already committed `self._sources`.

*Proven* (`probe_arch.py` §1: `frozen` made to raise on its second call). Afterwards the at-rest
`g.temperature.flags.writeable` is `True`, and `g.temperature[0,0,0] = 5.0` **succeeds with the window closed**. The
grid holds the body's writes (99.0), while `frames.latest` is still sequence 0 at 20.0, so observers and the world
now disagree. This breaks §4.1's "a write anywhere else raises" and the commit's "a window that raises is rolled back
whole". The trigger is narrow, but the large grids are exactly where it fires. *Fix:* build the frozen dict inside
the `try` and assign it last (or wrap the freeze in the rollback), and add a test that makes `frozen` raise at exit.

### S3. `place` is a fourth window owner and a second action path, unmarked and unscheduled
`src/simcore/core/imagination.py::place`; CLAUDE.md "Rules that matter here"; `docs/design/boundaries.md` §10
"As built in 3b(a)"

§4.1 admits two kinds of window owner (the step and construction). §6.4 classes `place` as "the applier: `imagine`".
§5.3 puts the `imagine` kind in `phase1/boundaries`. As built, `place` opens the grid's window itself, writes cells and
regions outside the applier, and is listed in `WINDOW_OWNERS` with the reason "has no intent kind yet". The
as-built note records the fact but no step that ends it. There is no `TEMPORARY(...)` marker and no roadmap row, so
the marker lint, which exists to show every open band-aid, can't see this one. The edited CLAUDE.md rule now reads
"Actions change cells, through `simcore.core.applier` only", directly under "Imagined objects enter only through
`simcore.core.imagination.place`". For the one action kind that exists in code without an intent, the two rules
contradict each other. *Scenario:* `phase1/sim-clock` moves the two marked owners into `Simulation.step`, the lint
reports nothing left, and `place` keeps opening its own window with no log record, a write path the replay can't
see. *Fix:* mark the `with grid.writing()` in `place` as `TEMPORARY(<the step that adds the imagine kind>)`, list it
in the roadmap, and word the CLAUDE.md rule so it names the exception until then.

### S4. Refusal echoes carry memory addresses and hash-seed-dependent set order
`src/simcore/core/checks.py::shown` (reached from `StructureModulator.execute` through `intents.parse_action`)

`shown` falls back to `repr` for instances, and reprlib prints a mixed-type set in iteration order. *Proven*
(`probe_echo.py`, run twice with `PYTHONHASHSEED=1` and `2`). `execute("strike", {"energy_j": Thing()})` returns the
error `energy_j must be a finite number, got <__main__.Thing object at 0x10b64ba10>`, with a different address on
each run. `shown(frozenset({1, "a", 2.5, b"x"}))` prints in a different order under each seed. The same file already
states the rule this breaks: `StructureModulator._target_label` exists so that refusals carry "no memory addresses,
which would differ between runs and break a replayed log's bytes". In-process Maxim callers can pass any object
(the actor tool already passes `Entity`), and the error text enters the agent's tool output and memory. This is
older than the diff (it was `!r` before), but this diff makes `shown` the one place every echo goes through, and
claims bounded echo as a gate property, so this is where to fix it. *Fix:* in `_BoundedRepr`, show only `str`, `int`,
`float`, `bool`, `None` and containers of them by value, and everything else as `<a TypeName>` (like
`_target_label`), with sets and dicts sorted by `shown` text. Add a two-seed test.

### S5. The "frame holds the owners" deviation is recorded without its costs
`docs/design/boundaries.md` §10 "As built in 3b(a)"; `src/simcore/core/frames.py` module docstring;
`src/simcore/core/applier.py::Applier._ignite`, `_extinguish`

The deviation itself is sound. I tried every path I could find: at-rest owners are `np.frombuffer(bytes)`, so the
WRITEABLE flag, `.base`, `out=` and slice views all refuse. The window works on fresh `copy()`s and swaps in new
frozen copies, and rollback restores the old (immutable) owners. **I found no in-place write to an owner on any
shipped path.** But the note says the frame "needs no copy" and leaves out where the copy went. Every window copies
all four channels twice: `arr.copy()` on entry, then `tobytes` into `frombuffer` on exit. That includes ignite and
extinguish, which change only the sources dict but still open the grid's window and publish a cell frame with no cell
change, against §4.2's "published on change". Second, a frame now **is** a full grid (about 21 B/cell, so roughly
100 MB at the 5×10⁶-cell max profile). §4.2 chose copies so that agents would get reductions, not grids, and plans
"one frame pinned per agent". With owner-holding frames, each distinct pinned frame retains a whole grid. *Scenario:*
at `phase1/agents`, 20 NPCs pinned to different frames retain about 2 GB, and each NPC's ignite costs four full-grid
copies. Neither is in the note or in B5. *Fix:* record both in the as-built note and as a B5 row. A sources-only
`World.writing` path (no grid window) would end the ignite and extinguish cost.

## NIT

- **N1** `src/simcore/core/grid.py::CellStore.writing`: the region table is mutated **in place** during a window
  (`paint` and `name_region` write `self._regions`), and rollback swaps in a copy. A `grid.regions` proxy taken before
  a failed window keeps the half-applied dict forever. Proven (`probe_arch.py` §2: the held proxy shows the crate
  with 0 cells, the grid shows 27). Nothing on the shipped path holds the proxy across windows (`CellFrame.of`
  copies), but copying the table on entry and swapping it on exit, as the channels do, would make the two symmetric.
- **N2** `src/simcore/core/frames.py::CellFrame` and `CellFrame.of`: nothing makes a frame immutable except the
  caller. `of` doesn't refuse an open window, where `grid.temperature` is the window's live writable copy, which the
  window goes on writing in place. The constructor doesn't freeze its arrays either: `tests/test_snapshot.py` builds
  frames with writable arrays through `dataclasses.replace`. Immutability holds on the shipped path only because
  `_publish` runs after close. Make `of` raise `WindowClosed` when the window is open, and have `__post_init__` check
  `not arr.flags.writeable`.
- **N3** `src/simcore/core/frames.py::FrameFeed.publish` is public, and the membrane holds the concrete `FrameFeed`
  (`region_parts`). Proven (`probe_arch.py` §3): a forged frame with `time_s=1e9` was accepted, and instruments
  reported `timestamp=1e9`. Make it `_publish`, reachable only through `World`.
- **N4** `src/simcore/core/grid.py::CellStore.on_close`: the docstring says "after each window that changed
  something", but the code calls back after every window that didn't raise, including an empty one and a
  sources-only one. Either fix the wording or skip unchanged windows (see S5).
- **N5** Holes in `scripts/lint_inputs.py` and the `input-primitives` contract, for "nothing unpickles" and "only the
  file gates read input". `import _pickle` (the C unpickler) passes both: proven, with the contract KEPT and
  `check_inputs` returning `[]`. Also missed: `numpy.lib.format.read_array(..., allow_pickle=True)` (only a callee
  named `load` is checked), `np.load(allow_pickle=flag)` with a non-constant flag, `importlib.import_module("json")`
  and `__import__` outside the core, `tomllib.load(s)`, `configparser`, `plistlib` and `fileinput.input`. These guard
  mistakes, not adversaries, but `_pickle` belongs in `UNSAFE_MODULES` and in the contract.
- **N6** `src/simcore/core/applier.py::Applier.centroid_m` is public, but its only callers are inside the class. The
  membrane needs `limits` and `apply` only. Making it private shrinks the surface S1 is about. Separately,
  `World._turn` is incremented inside the window but is not part of the rollback. That is safe today only because
  it is the last statement in the body. A comment, or moving it after the `with`, would make that explicit.

## Determinism and replay

- **Physics bit-identity: verified independently.** `tests.test_determinism.digest(run(0.2))` gives `f7429cba…d256`
  on both `origin/main` (whose `src/` equals fa27d5f's) and HEAD. I did not rerun 0.1 m or 0.05 m, because the machine
  was loaded. The digest function is unchanged in the diff except `MUST_SCAN` gaining `applier.py`.
- **Copy semantics:** `frozen` and `copy()` preserve bytes and dtype and give C-contiguous arrays, as `np.zeros` did.
  The laws run on numpy-allocated window copies, so their numerics see the same layouts as before.
- **Iteration order:** the new code iterates dicts in insertion order only (`_regions`, `QUANTITIES`, `sources`,
  `asdict`, `_on_close`). `known_keys` sorts its echoed keys. No set iteration, builtin `hash` or `id` reaches state.
  The one hash-seed or identity leak is S4, and it is in text, not state.
- **`place`'s change of order** (masks are now computed inside the window, during painting): `Box.mask` and
  `Cylinder.mask` read only `grid.mesh()`, which is geometry, so the result is unchanged.
- **Nothing reads a clock, and no new threads.** Frame publication adds `sequence`, which is deterministic. Replay
  doesn't exist yet. The window-bypassing `place` (S3) is what would escape a future log.

## Claims verified

- Commit: "the window swapping in read-only copies … a handle or view unlocked inside a window and written after it
  changes nothing". True (code plus `test_a_handle_or_view_unlocked_…`).
- "a window that raises is rolled back whole; one window opens at a time". True for body exceptions and nesting.
  False for an exception while closing (S2).
- "World.sources is a read-only mapping that only the applier changes". True: `MappingProxyType`, the writer scan, and
  `WINDOW_OWNERS`. "regions are a read-only mapping of frozen masks". True (`Region.__post_init__` freezes).
- "Frames … immutable without a copy". True on the shipped path. Construction doesn't enforce it (N2), and the costs
  aren't recorded (S5).
- "Sensors … typed against `Observation` … mypy refuses a peek". True for `RegionInstrument`. Not true for the
  membrane module, which takes `World` (S1).
- "skip-layer, membrane-reads-frames, input-primitives, each forbidden list held to the core's modules". True as list
  equality (`test_tooling_config.py`). The lists don't cover re-exports (S1) or `_pickle` (N5).
- "Physics is unchanged: digests byte-identical". Verified at 0.2 m (above).
- TEMPORARY markers: `World.advance` and the applier are on `phase1/sim-clock`, and `bridge.execute` is on
  `phase1/agents`, all listed in `docs/roadmap.md` under Phase 1. Each names a real removal moment (§4.1, §6.4).
  Missing for `place` (S3).
- Lesson 23: verified against pymaxim 1.3.3 `maxim/embodiment/tool_bridge.py` (`ModulatorAffordanceTool`). It calls
  `self._modulator.execute(...)` and then loops `sensor.read()` over every entity sensor ("Read back entity sensor
  state after action (cascade effects)"). One precision: it reads back only when the result succeeds, which matches
  `test_the_shipped_path_publishes_…` (a refusal publishes nothing). The cited tests exist.
- CLAUDE.md layout edits match the modules. The rule edit conflicts with `place` (S3). The new guards
  (`lint_gates.py::check_gates`, `lint_inputs.py::check_inputs`,
  `test_ownership.py::test_every_function_that_writes_the_world_is_in_the_core`) exist.
- §2.2 split: the gate half (parse, target and namesake checks, schema) stays in the membrane. The write half, with the
  reach and centroid checks judged from footprints, is in `simcore.core.applier`. `entity_key` and `shown` are in
  `checks`. Modules are split along responsibilities (`GridGeometry`, `CellStore`, `MaterialGrid`; `Frame` and
  `FrameFeed`; `Applier`). There are no god functions, and `Applier.apply` is a short decide-then-dispatch.
