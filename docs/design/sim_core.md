# The simulation core (step 5a): the composition and its contract

**Status:** step 5a's composition note (`foundations_plan.md` row 5a, O34), 2026-11-21, for review before code. It
holds only what other modules and tests depend on. Mechanisms that only running can check are tests in
`docs/plans/checklists.md` ("Step 5a"), each citing its section here. Where another document owns a contract, this
one links to it.

## 1. What 5a builds, and what it doesn't

**Builds:**
- the `Simulation` and its integer clock;
- the ordered law list;
- the field registry;
- the region-id array and `topology_version`;
- the caches;
- the intent-log writer and replay;
- the work counters;
- the move of every writer under `Simulation.step`.

**Lands on its line:** fire's 6.0a (`fire_solid.md` §0, §5.1) and the SEM contract's 5a half (`sem_stimuli.md`
§11.1).

**Doesn't build:**
- bodies and movement (5b);
- the protocol (step 7);
- agents and lanes (`phase1/agents`, `phase1/lanes`);
- the save (step 9);
- new physics.

## 2. Composition: no god object

`Simulation` composes five parts. Each part is its own type with one job, and `Simulation.step` only orchestrates
them, as a short list of named steps.

| Part | Type | Holds | Changes through |
|---|---|---|---|
| Cell state | `World` (kept, minus `advance`) | the `MaterialGrid`, `sources`, regions, `topology_version` | the laws and the applier, inside the write window |
| Body state | reserved slot | nothing in 5a; 5b's bodies (`sem_stimuli.md` §11.1's `body_points` container) | 5b |
| Ledger | reserved slot | nothing in 5a; `world_v2.md` §2.6 | the fuel and zone PRs |
| Clock | `Clock` | `tick: int` | `Simulation.step` only |
| Intent log | `LogWriter`, behind a protocol | the records, in key order | `Simulation.step` only |

- **`World` stops moving time.** `World.advance` goes, with its `TEMPORARY(phase1/sim-clock)` marker. The physics
  phase of `Simulation.step` runs the law list on `World`'s cells.
- **`grid.time_s` goes.** World time is the clock's tick times `tick_us` (§3). Sensors take a required keyword-only
  clock (`world_v2.md` §5).
- **One owner of time,** `Simulation` (`boundaries.md` §7.3). CLAUDE.md's "only `World.advance` moves time" becomes
  "only `Simulation.step` moves time" in 5a's PR.

## 3. The clock and the tick

- **The clock is an integer tick.** World microseconds are `tick * tick_us`, and nothing stores time as a float.
- **The truth constants:** `tick_us` and `physics_every` (ticks per physics step). Their values belong to tile T3
  (`tile_and_client.md` §6.1: 100,000 µs, every 5 ticks), and they are hashed world config in the log header.
- **The physics step length** is `P = physics_every * tick_us` µs. It's 500,000 µs, and 0.5 s is exact in binary.
  A law's `dt` in seconds is derived from integer microseconds at the start of each physics step, never accumulated.
- **The order within a tick** belongs to `realtime_lanes_coop.md` (D10), amended by insertion in
  `sem_stimuli.md` §4.1. 5a builds its steps 1 (apply records), 6 (physics on physics ticks) and 8 (outputs), and
  reserves 2–5 and 7 as no-op seams (`sem_stimuli.md` §7.1).
- **The 6 s turn is retired** (T3). `World`'s `turn_seconds` goes.

## 4. `Simulation`'s public interface

```
Simulation.from_scene(scene, materials, *, dx_m, config, laws=DEFAULT_LAWS) -> Simulation
Simulation.step(records: Sequence[LogRecord]) -> TickReport    # exactly one tick
Simulation.tick -> int
Simulation.frames -> FrameView                                   # the latest published frame (boundaries §4.2)
```

- **`step` takes the records whose `apply_tick` is this tick,** already in the log's key order (`boundaries.md`
  §6.2). It refuses a record for any other tick, and refuses records out of order. It applies them, runs physics on
  physics ticks, and publishes one frame.
- **Frames are published once per tick, at the end of the tick.** Today the applier publishes after each
  application (`boundaries.md` §4.1, 2c). From 5a, a strike and a read inside one tick see the frame from before
  the tick, and `tests/test_sem_bridge.py` moves to reading the next tick's frame.
- **`TickReport`** is frozen. It holds the tick, the receipts and refusals (derived values, `boundaries.md` §6.2),
  the per-tick digest, and the `WorkCounters` (§9).
- **`laws`** is part of hashed config. A test can pass a reordered tuple (§5); shipped code never does.
- **The applier is not public.** Every input reaches the world as a record through `step`, under the one-pipeline
  rule (`boundaries.md` §6.1). `region_parts` hands the membrane an applier only through the record path, and its
  move under the test tree is D10's (`sem_stimuli.md` §10).

## 5. The law list

- **A law is an object** with `name`, `version`, `reads` and `writes` (field names in the registry, §6),
  `stable_dt(state) -> float`, and `step(state, dt_s, ledger) -> Changes`. `Changes` holds the cells destroyed and
  whether topology changed.
- **The list is a fixed tuple, never discovered.** Its order follows `research/physics_spike/splitting.md` §6, rule
  1: transport, then exchange, then sources and projections, then losses. Each law states the invariants it reads
  and the ones it can break.
- **In 5a the tuple is `(heat, damage)`.** Damage stops being heat's `on_substep` callback and becomes the second
  law, run after heat in each substep. That split is a behaviour change only if it alters the arithmetic, and §11
  says which way it went.
- **Each law is split into `prepare` and an array-only kernel,** with a bit-identity parity test. That is the numba
  seam; numba itself waits for a profile that asks for it.
- **The reversed-order test** constructs a `Simulation` with `laws=tuple(reversed(DEFAULT_LAWS))` and asks
  `same_class_under_refinement` (`verify_harness.md` §4) for the same outcome class in both orders.
- **The header records** each law's `name` and `version` (`sem_stimuli.md` §5's slot).

## 6. The field registry

- **Code-primary** (`sem_stimuli.md` D2): one tuple of `FieldSpec` values in `engine.cells`, declaring for each
  field:
  - its name, dtype and units;
  - its container (cells, zone, pool, body);
  - whether it is saved or derived, with the default for older saves;
  - its snapshot channel and quantization, or none;
  - whether it is digested;
  - its writer laws.
- **Every reader takes it from there:** the grid's storage, the snapshot, the per-tick digest, the memory budget and
  the save.
- **A generated artifact,** `docs/generated/fields.md`, is committed and compared byte for byte by a test, so the
  field list can be reviewed without reading code.
- **This supersedes `world_v2.md` §2.5's `data/world/fields.yaml`.** Data can't import code, and fields are bound to
  the laws that write them.
- **Step 6's tables join this registry** (`fire_model.md` §10's row): one registry, not a second one.

## 7. Region ids, topology and caches

- **Regions become one `region_id` u16 array** (`world_v2.md` §2.4). Id 0 is unowned, and every other cell has
  exactly one owner. `Region` keeps its authored footprint (`world_v2.md` §2.4).
- **`topology_version: int`** increments whenever any cell's material or owner changes. Every cache keys on it.
- **The caches** (world_model §10 row 4):
  - face conductances, per topology version;
  - each source's sphere overlap, per `(source id, topology_version)`. The vertical slice found it recomputed over
    the whole grid on every advance, measured at about half a burning tick's CPU. It is computed over the source's
    bounding box, not the grid;
  - region reductions, once per physics step (`world_v2.md` §2.4).
- **Accumulations over named collections iterate in sorted-key order** (`boundaries.md` §6.2). Today
  `World._power_field` iterates `sources` in insertion order. That is deterministic on replay, but not the stated
  order; 5a makes it sorted.

## 8. The fixed physics step, replacing the substep floor

- **The rule** (`splitting.md` §6, rule 3): at the start of each physics step, `n = max(1, ceil(P_s / min over laws
  of stable_dt))`, and `dt = P_s / n` exactly. `stable_dt` returns infinity only for an unconditionally stable
  update.
- **One departure, for the owner (decision 1):** when a law's `Changes` tightens the stability bound mid-step
  (destruction turns a cell to air, which is far more diffusive), the rest of the step is replanned, split evenly at
  the new bound, as `heat.step` does since step 4. `splitting.md` fixes `n` at the start, with a mid-step check as a
  debug assertion only. That can't hold, because a fixed `n` past a tightened bound is unstable.
- **The substep floor goes:** `heat.min_substeps`, `FLOOR_AREA_M2`, its `TEMPORARY` marker and
  `tests/test_determinism.py::TURN_SUBSTEPS`.
- **Accuracy at `P`** is a verification bar (§10, bar 1). If the bar fails, a measured accuracy floor joins the
  rule, as a truth constant.

## 9. The work counters

`WorkCounters`, frozen, is part of each `TickReport`:
- `physics_steps`;
- `substeps` per law;
- `cell_substeps` per law (cells × substeps);
- `overlap_recomputes`;
- `cache_rebuilds`.

The counters are exact integers and deterministic: identical on a replay, and never wall time. B5's budgets and
step 4's deferred counters (`verify_harness.md` §7) read them.

## 10. Bars

| # | Bar | Kind | Source |
|---|---|---|---|
| 1 | At `P` = 0.5 s, 0.1 m: heat's time error is below its space error at the truth grid | verification | `verify_harness.md`'s time and space studies, rerun at `P`; measured at step 5a |
| 2 | The scenario agreement tests at the fixed physics step: same bars as today, now refining space alone | verification | the tests' existing bars (`tests/test_cross_tier.py`); the strict red gates stay strict |
| 3 | Laws in reversed order: same outcome class | verification | `splitting.md` §6, rule 4 |
| 4 | Replay: bit-identical world, per-tick digest equal | determinism | `boundaries.md` §6.2 |
| 5 | `prepare` plus kernel matches the unsplit law, bit for bit | determinism | §5 |
| 6 | `WorkCounters` identical on replay | determinism | §9 |
| 7 | CPU per physics step and memory, measured | process (B5) | the plan row ("CPU time measured") |

## 11. Bit-identity: which digests 5a breaks, and how that is recorded

- **They break:**
  - dropping the substep floor (a behaviour change owed to step 5a, `heat.py`'s marker);
  - the retired 6 s turn (T3);
  - sorted-key power accumulation, wherever the insertion order differed;
  - splitting damage out of heat's callback, if that changes the arithmetic.
- **They hold:** the conductance and overlap caches. They are proven bit-identical against the uncached path
  (checklist).
- **How it's recorded:** no golden digest is committed today. 5a's PR records each break in its commit message, and
  replaces `TURN_SUBSTEPS` with the new per-physics-step counts. Its log writer then records the first replay
  golden after 6.0a lands (`fire_solid.md` §0). From then on a golden changes only on a recorded change
  (`boundaries.md` §6.3).

## 12. Writers under `Simulation`

`boundaries.md` §6.4 owns the classification. 5a moves:
- **`World.advance`** to the physics phase of `Simulation.step`. Its marker goes.
- **The applier's own window** to the apply phase of `Simulation.step`. Its marker goes.
- **`imagination.place`** to the applier, as the `imagine` intent kind's stage 2 (CLAUDE.md, "until step 5a makes
  `imagine` an intent kind"). Its marker goes.
- **Construction** to `Simulation.from_scene`.

`tests/test_ownership.py`'s writer scan is updated to the new owners.

## 13. Formats on this line

- **The intent record, the header and the ordering key** are `boundaries.md` §6.2 and §6.3's. 5a writes them.
- **Kinds are ranked 0, 10, 20 and 30,** leaving room. Retired verbs are listed, and refusal codes stay append-only
  (`core/refusals.py`, from step 3b part (b)).
- **The header slots** `sem_stimuli.md` §5 reserves, with each law's version, and the scene once the header records
  one. At that point the scene format becomes held by others (`held_by_others`), and an old version migrates
  (checklist, from 3b(b)'s review).
- **6.0a's tables** declare their `Format`s beside their types, per #32's pattern, and join the registry (§6).

## 14. The SEM fold rows 5a settles

From `docs/design/reviews/sem_stimuli/` (owner, 2026-11-21: each build step names the rows it settles):

| Round | Rows |
|---|---|
| Round 1 | S2, A-S3 |
| Delta 1 | X2, A-S10, A2-S4 |
| Delta 2 | Y5, Y7, A3-S4, A3-S5, DP3-N2, DP3-N3, W11 |
| Final | S-F3, S-F4, N-F5, N3, N-S3, DP-F-S3, DP-F-N1 |

5a's reviewers set each row's status when they read the tree.
