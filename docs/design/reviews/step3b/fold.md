# Step 3b part (a) review round: fold

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
| Trust B1 | `Cylinder.mask` raised `OverflowError` through `place` | `scene.py::_coordinates`: every coordinate and radius is finite and within `MAX_EXTENT_M` (1 km) before any arithmetic; `mask` squares as `r * r`. New `tests/test_extremes.py`: extremes (±1e300, 1e200, 1.4e154, ±2 km, inf, nan, −0.0, 10**400, 10**20) through the constructors, `place` and `Scene.from_dict`, and two property tests that count their reach (derandomized). Measured: place, of 400 examples, 500 primitives built, 149 valid, 16 masks computed; scene, every example builds a primitive, and the floors (20% valid, 10% masked) hold | against HEAD (19 red, including the `OverflowError`); reverted (16 red) | open |
| Trust S1 | `lint_inputs` missed aliases and indirect spellings | `scripts/lint_inputs.py` rewritten: an alias table (`import x as y`, `from x import y as z`, `np`), `_pickle`, `eval`/`exec` named in any way, a non-literal `allow_pickle`, `numpy.load(**kw)`, `getattr` on yaml/pickle/marshal/builtins/importlib, `import_module`/`__import__` of an unsafe name; in `src/simcore/`, `importlib`, `__import__` and a computed `getattr`; tomllib, plistlib, configparser, fileinput. The docstring says what it can't see. 24 evasions are permanent tests in `tests/test_lint_gates.py` | reverted (HEAD's module: 23 red) | open |
| Trust S2 | registry gaps; protocol detection evaded by inheritance | rows for `Applier.apply`, `primitives_from_data`, `Box`, `Cylinder`, `Material`, `MaterialTable`, `ActionLimits`, `HeatSource`; `_protocol_classes` follows base classes across modules, so a subclass overriding `execute` needs a row; the test-name check reads identifiers from the syntax tree (N7). Three gaps it found (`.check`, `Material`, `primitives_from_data` never named) got direct rejection tests | reverted (HEAD's module: 11 red) | open |
| Trust S3 | `execute` and `place` claimed "meets" without §5.4's closed codes | status `partial: free-text refusals until the refusal-code enum (plan step 3b part b, WT-S1)` on every agent-facing gate (parse_action, the actions and their checks, `Applier.apply`, `place`, the primitives, `execute`) | reverted (part of the 11) | open |
| Trust S4 | `place` allocated before its extent and mass budgets | `imagination.py::_within_world_rules`: extent, ownership and mass from authored geometry, before any mask; `_voxelize` masks each primitive once and refuses "occupied" inside the window, which rolls back. Refusal order changes: inside a named solid's footprint now reads "belongs to", first | against HEAD (3 red, a mask computed first); reverted (occupied) | open |
| Trust S5 | `paint` rebuilt every region per paint | `grid.py::CellStore._take_cells`: only the box the mask covers is read, and only a region the paint takes cells from is copied, narrowed in place and refrozen once at window exit. CPU, min of 5, 1.92×10⁶ cells, 40 named regions, lightly loaded: build 110–115 ms vs main 141–149; place (32 primitives) 88–95 ms vs main 179–193 | reverted (the region-narrowing test, 2 red); profile first (`_take_cells` was 315 of 380 ms) | open |
| Trust S6 | physics slower than real time | Known gap in `docs/architecture.md` (net 25 words shorter) and B5's row. Measured again: `advance(0.5)` at 1.92×10⁶ cells is 0.68–0.74 s lightly loaded (the review's 1.45 s was under heavy load), the same on main | — (docs) | open |
| Exec S1 | the writable sources dict outlived the window | `world.py::World.writing` commits `MappingProxyType(dict(sources))`, after the grid's window commits | reverted (red) | open |
| Exec S2, Arch S1 | the membrane held `World`; re-exports bypassed the contracts | `region_parts(applier, frames, region)`, `to_maxim_entity(applier, frames, region)`; `simcore.core.world` joins `membrane-reads-frames`' forbidden list; `tests/test_ownership.py`: no `.grid`, `.sources`, `.advance`, `.writing`, `.cells`, `.publish`, `._world` or `._feed` in adapters or protocol, and no name imported from an allowed module that is, or comes from, a forbidden one. Wording fixed in CLAUDE.md, the applier's docstring and the fold message | planted (peek, two re-exports, `import World`: each red) | open |
| Arch S2 | a failure while the window closed left it writable and half-committed | `CellStore.writing` builds the frozen channels and the region table inside the `try`, and commits only after; `World.writing` commits the sources after the grid | against HEAD (writable at 99 °C); reverted (red) | open |
| Arch S3 | `place` an unmarked fourth window owner | `TEMPORARY(phase1/sim-clock)` in `imagination.py::_voxelize` (step 5a's intent log, where `imagine` becomes an intent kind), listed in the roadmap; the CLAUDE.md rule names the exception | the marker lint went red until the roadmap listed it | open |
| Arch S4 | `shown` echoed addresses and hash-seed order | `checks.py::_BoundedRepr`: only str, int, float, bool, None and containers of them print by value, anything else as `<a Type>`; sets sorted by their echo. A three-seed subprocess test (`ALLOWED_SPAWNS` entry added) | against HEAD (`<a _Thing>` test red); reverted (the seed test red) | open |
| Arch S5 | the frame design's costs were not recorded | boundaries §10's as-built note: two copies per cell window, a frame pins a whole grid (about 100 MB at 5×10⁶ cells), a B5 row for frames pinned per agent. Ignite and extinguish now open a sources-only window, `World.writing(cells=False)`, which copies no cell and publishes no frame. Skipping copies for a cell window that changes nothing was not done: it needs a change test as costly as the copy | reverted (ignite with a cell window: red) | open |

## NITs

Folded:
- **Exec N1:** `time_s` after an advance (reverted: red).
- **Exec N2, Arch N4:** the `on_close` docstring.
- **Exec N3:** one voxelization per primitive.
- **Exec N4:** the writer scan sees `copyto`, `fill`, `put` and tuple-unpacking targets (which hid `CellStore.writing`).
- **Exec N5:** rollback compared by value.
- **Exec N6, Arch N2:** `CellFrame` refuses writable arrays, and `of` refuses an open window.
- **Arch N1:** the region table swaps like the channels.
- **Arch N3:** observers get a `FrameView`, which cannot publish.
- **Arch N6:** `centroid_m` is private, and the turn is counted after the window.
- **Trust N1:** an unhashable quantity is a `ValueError`.
- **Trust N4:** see Arch S2.
- **Trust N5:** `:.3g`.
- **Trust N6:** `_check_region` echoes through `shown`.
- **Trust N7:** see Trust S2.
- **Trust N8:** `finite_vector` survives a length that overflows.

Not folded:
- **Exec N4's** `getattr(w.grid, "temperature")[0] = 1` and an aliased opener (`cm = w.writing`): the scans don't follow values. At rest the arrays raise anyway.
- **Trust N2:** a per-frame memo of readings. The instruments are lab-only, and a memo is an optimization owed to a profile.
- **Trust N3:** see Arch S5.
- **Arch N5:** see Trust S1.

Physics digests: byte-identical to fa27d5f at 0.2, 0.1 and 0.05 m (f7429cba…d256, e9e57122…a0ca, e68e6d7b…db5c).
