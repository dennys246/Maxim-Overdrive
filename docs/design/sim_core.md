# The simulation core (step 5a): the composition and its contract

**Status:** step 5a's composition note (`foundations_plan.md` row 5a, O34), 2026-11-21, folded from its round-1
review (`reviews/sim_core/`). It holds only what other modules and tests depend on. Mechanisms that only running can
check are tests in `docs/plans/checklists.md` ("Step 5a"), each citing its section here. Where another document owns
a contract, this one links to it. The owner's rulings and the fold table live in `reviews/sim_core/fold.md`.

## 1. What 5a builds, and what it doesn't

**Builds:** the `Simulation` and its integer clock; the ordered law list with cadences; the field registry; the
topology owner, the region-id array and `topology_version`; the caches; the per-tick digest; the intent log's format,
writer and replay; the work counters; the move of every writer under `Simulation.step`.

**Lands on its line:** fire's 6.0a (`fire_solid.md` §0, §5.1) and the SEM contract's 5a half (`sem_stimuli.md`
§7.1, §11.1), whose three seams §5 and §6 define.

**Doesn't build:** bodies and movement (5b); the protocol (step 7); agents and lanes (`phase1/agents`,
`phase1/lanes`); the save (step 9); randomness (its seed slot is reserved, §14); new physics. Preallocated temporaries
and the memory budget (`world_v2.md` row 3) are deferred to B5's memory row, before step 9.

## 2. Composition: no god object

`Simulation` composes these parts. Each is its own type with one job; `Simulation.step` only orchestrates them, as a
short list of named steps (§3).

| Part | Type | Holds | Changes through |
|---|---|---|---|
| Cell state | `World` (kept, minus `advance`, `_power_field`, publication and construction) | the `MaterialGrid`, `sources`, regions, `topology_version` | declared writers (§5.1), inside the write window |
| Topology | `Topology` | nothing of its own; it applies world-edit requests | requests, applied in key order (§5.1) |
| Body state | reserved | 5b's `body_points` container (`sem_stimuli.md` §7.1) | 5b |
| Ledger | reserved | `world_v2.md` §2.6 | the fuel and zone PRs |
| Clock | `Clock` | `tick: int` | `Simulation.step` only |
| Frames | `FrameFeed` | the published frames | `Simulation.step`'s last step only |

- **`Simulation` is a pure function of the records it is given.** The intent log's writer and its replay reader live
  in `engine.host` (`boundaries.md` §2.2, layer 8). The host logs what `TickReport` carries; `Simulation` writes no
  log.
- **One constructor,** `Simulation.from_scene`. It builds the world through the topology owner and builds every
  cache eagerly, so a run from tick 0 and a replay from a loaded state start with the same caches.
- **One owner of time,** `Simulation` (`boundaries.md` §7.3). `World.advance`, `World.turn`, `turn_seconds` and
  `grid.time_s` go.
- **Where the new types live** (`boundaries.md` §2.2's layers): `FieldSpec` and `Changes` with the cells;
  `Load` with the laws, so damage can read it and `intents` imports it; `Clock`, `SimConfig`, `TickReport` and
  `WorkCounters` with the simulation.

## 3. The clock and the tick

- **The clock is an integer tick.** World microseconds are `tick * tick_us`; nothing stores time as a float. A
  frame carries the tick it was published on, and seconds are derived from it where an observer asks. Tick 0 is
  0 s; Maxim reading 0.0 as "no time" is OD-I1, already a Phase 3 row, not a host-side offset to add here.
- **The truth constants** `tick_us` and `physics_every` are tile T3's (`tile_and_client.md` §6.1). With
  `substep_refine` (§8) they make up `SimConfig`, a frozen type built in code, hashed into the log header. No data
  file carries them in 5a.
- **`step` runs tick `T` and then sets `tick = T + 1`.** A tick is a physics tick when `T % physics_every == 0` and
  `T > 0`; its physics covers the interval `(T − physics_every, T]` (the phase and the interval are
  `realtime_lanes_coop.md` §2.1's and `tile_and_client.md` §3.2's). Tick 0 runs no physics: nothing existed before it (owner, 2026-11-21).
- **A source's energy in a physics step** is its power times the number of ticks in the interval at whose end it
  existed, times `tick_us`, in integers. An ignite at tick 66 and one at tick 69 then differ, as tile's per-tick
  overlap rule requires, and a closed-form test holds it (checklist).
- **`apply_us` only orders records in 5a.** Time below the tick reaches no law.
- **The order within a tick** is owned by `sem_stimuli.md` §4.1 (D10 as amended). 5a builds
  steps 1 (apply), 6 (physics on physics ticks) and 8 (outputs), and the per-tick law slot (§5); 2–5 and 7 stay no-op
  seams.

## 4. `Simulation`'s public interface

```
Simulation.from_scene(scene, materials, *, dx_m, config: SimConfig, limits, laws=DEFAULT_LAWS) -> Simulation
Simulation.step(records: Sequence[LogRecord]) -> TickReport    # exactly one tick
Simulation.tick -> int
Simulation.frames -> FrameView                                   # the latest published frame
```

- **`step` validates the whole batch before applying any of it:** every record's `apply_tick` is this tick, and the
  records are in the log's key order (`boundaries.md` §6.2). A bad batch raises `ValueError` and changes nothing.
- **Frame cadence is `tile_and_client.md` §4's;** 5a publishes that tick's frame at the end of the tick. Observers inside a tick read the frame from before it, so an NPC's intent observed at tick T
  applies at T + 1 or later, and its effect is first in that tick's frame.
- **`TickReport`** is frozen and host-side. It holds the tick, the refusals, the effects of each record (a strike's
  destroyed volume and absorbed energy are effects, logged host-side), the per-tick digest (§9) and the
  `WorkCounters` (§10). It is never a stimulus: an agent's receipt is `sem_stimuli.md` §6.2's `(pid, kind)`, and no
  stimulus or wire path reads `TickReport`.
- **`laws`** is hashed config. A test can pass a reordered tuple (§5); shipped code never does.
- **The applier is not public.** Every input reaches the world as a record through `step` (`boundaries.md` §6.1),
  with one interim exception, §13's bridge.

## 5. The law list

- **A law is anything in the declared tuple,** whatever its cadence: physics laws, damage, and later the body laws
  (tissue, irradiance, contact). Each has `name`, `version`, `cadence`, `reads` and `writes` (sorted tuples of
  registry field names, §6), and:
  - `stable_dt(state) -> float`, a function of the fields it reads, so it caches like them (§7);
  - `prepare(views)` and a kernel: arrays and scalars in, preallocated outputs, every order-sensitive reduction in
    `prepare`. That is the numba seam; numba waits for a profile.
  - `step(views, handles, dt_s) -> Changes`. It receives read-only views of its `reads` and write handles for its
    `writes` only, so an undeclared read or write is a type error, not a convention.
- **`Changes`** holds the topology requests the law made (§5.1) and, per load, the effect it resolved.
- **Cadence** is one of `per_tick` (in the per-tick slot, D10 step 1, after the records), `per_physics_step` (once
  per physics step, at its start, as `fire_solid.md` §3.2's solid and contact run) or `per_substep`. The orchestrator's
  steps follow from it.
- **The tuple is fixed, never discovered,** ordered by `research/physics_spike/splitting.md` §6, rule 1. In 5a it is
  `(damage.loads, heat, damage.thermal)`: load resolution per tick, heat and thermal degradation per substep (owner,
  2026-11-21). Damage stops being heat's `on_substep` callback.
- **After any `Changes` with a topology request,** every law's `prepare` reruns (through the caches) before the next
  substep. Today `heat.step` refreshes source power after every destroying substep, and that guard stays.
- **The header records the tuple in order,** with each law's `name` and `version` (`sem_stimuli.md` §5's slot). A
  log recorded under another order is refused.

### 5.1 The flow: declared, ordered writers, and one resolver per kind of effect (owner, 2026-11-21)

- **Inputs declare; laws resolve; observers read.** The applier turns each record into inputs (a heat source, a
  `Load`, a world-edit request) and writes no outcome. Laws resolve inputs in the tuple's order. Observers read
  only published frames.
- **Every write is declared and ordered.** A field's registry entry lists every law that writes it, in tuple order
  (§6). The write window hands a write handle only to a declared writer, and refuses anything else. Several writers
  of one field are allowed when declared, as splitting needs: `fire_solid.md` §3.2's contact law writes cell
  temperature in its exchange, before heat, as one antisymmetric transfer (`world_v2.md` §2.6).
- **One resolver per kind of effect.** All damage resolves in damage; all heat input from sources resolves in heat.
  A new damage source (ballistic, chemical, electrical) adds a load kind and a resolver module in a declared tuple
  inside the damage package. Each resolver returns increments; damage applies them in key order. No second module
  writes `integrity`.
- **Accumulated fields take declared contributions.** `radiant_emitters` (`sem_stimuli.md` §7.1) holds rows keyed
  `(writer law, …)`, each row written by its one law; its owner sums them in sorted key order.
- **World edits are requests, and one owner applies them.** `imagine`, admin `set_material`, construction and
  destruction each produce topology requests (`material`, `original_material`, `region_id`, a new cell's
  `integrity`). `Topology` applies them in key order and bumps `topology_version` once per batch. It is the choke
  point `world_v2.md` §2.2 names.
- **Laws couple only through fields.** No law module imports or calls another, held by an import contract. Where
  `sem_stimuli.md` §7.1 has contact write the object "through the solid law's exchange API", contact writes a
  declared exchange field that the solid law reads.
- **Strikes resolve in the apply phase, on their own tick** (owner, 2026-11-21). Each `Load` is resolved by
  `damage.loads` right after its record applies, in key order, so the next record's stage 2 sees the crater, as
  today (`REGION_GONE` still refuses a second strike on a destroyed region). The crater is in that tick's frame and
  its effect in that tick's `TickReport`. No load waits across ticks, so loads are never carried state.

## 6. The field registry

- **Code-primary** (`sem_stimuli.md` D2; owner, 2026-11-21): one tuple of `FieldSpec` values in
  `simcore/core/fields.py`, superseding `world_v2.md` §2.5's `fields.yaml`, whose columns it carries. Per field:
  - name, dtype and units;
  - container: cells, zone, pool, body, or a keyed table (fire's object, segment and coupling tables, `fire_model.md`
    §10, join here in 6.0a);
  - saved or derived, the default for older saves, and `required`;
  - its snapshot channel and quantization, or none;
  - whether it is digested, and whether it is perceivable (`sem_stimuli.md` §7.4, default false);
  - its conservation law and ledger, or none;
  - its writers, an ordered tuple of laws (§5.1), plus `Topology` for topology fields.
- **Inputs are declared beside fields:** `sources` and the tick's `loads`, with the applier as their only appender.
- **Every reader takes it from there:** storage, the snapshot, the per-tick digest, the save and sem_stimuli §5's
  producer closure, computed over every law in the tuple whatever its cadence.
- **A generated artifact,** `docs/generated/fields.md`, is committed and compared byte for byte by a test.

## 7. Region ids, topology and caches

- **Regions become one `region_id` u16 array** (`world_v2.md` §2.4). Id 0 is unowned. `Region` keeps its authored
  footprint.
- **`topology_version: int`** increments once per topology batch.
- **A cache's key is the values its result reads.** So:
  - face conductances and each law's `stable_dt`, per `topology_version`;
  - each source's geometric overlap per its value `(point_m, radius_m)` (the grid's `dx` and shape are fixed), and
    its solid-weighted, normalised weights per `(source value, topology_version)`. A re-ignite with a new radius
    under the same id then misses the cache, as it must;
  - region reductions, per `topology_version`.
- **The overlap is computed over the source's bounding box, padded by one cell.** That is bit-identical to the
  whole-grid computation while `sphere_overlap`'s values are multiples of 1/64, which its 4³ sub-sample guarantees:
  their sums are exact in any order (verified, `reviews/sim_core/fold.md`). An exact-overlap replacement would break
  that and must be recorded as a digest break (§12).
- **The caches are 5a's precondition, not an optimisation.** Measured on the T3 tile at 0.1 m, 5a at `P` = 0.5 s
  without them is about 2.6× today's CPU per world second; with the power field and stable bound cached, about
  0.46× (`reviews/sim_core/round1_performance.md`, P3).
- **Accumulations over named collections iterate in sorted-key order** (`boundaries.md` §6.2; string keys by code
  point). Today `World._power_field` iterates `sources` in insertion order; 5a moves source power into heat's
  `prepare`, sorted.

## 8. The fixed physics step, replacing the substep floor

- **The rule** is `splitting.md` §6 rule 3's, with its safety factor: at the start of each physics step,
  `n = substep_refine · max(1, ceil(P_s / min over laws of stable_dt))`, `dt = P_s / n`. `substep_refine` is hashed
  config, 1 in shipped play; tests raise it to refine time on the shipped path (§11).
- **Replan when a change tightens the bound** (owner, 2026-11-21): the rest of the step is split evenly at the new
  bound. What remains is computed from counts, `(planned − taken) · dt`, never from a running float sum.
- **On shipped data `n` is 1** at every verification grid (heat's bound is 240, 60 and 15 s at 0.2, 0.1 and 0.05 m,
  measured), so the new substep is coarser than today's at 0.1 and 0.05 m, and the replan is reachable only from a
  constructed material table.
- **The substep floor goes:** `heat.min_substeps`, `FLOOR_AREA_M2`, its `TEMPORARY` marker and
  `tests/test_determinism.py::TURN_SUBSTEPS`. Only if bar 1 fails does a measured accuracy floor join the rule, as a
  truth constant (owner, 2026-11-21).

## 9. The per-tick digest

- **Scheme `sha256/raw-1`,** versioned in the header. Each member is written as a length-prefixed name, then dtype,
  shape (u64, little-endian) and the C-order little-endian bytes.
- **Members, in order:**
  1. the tick and `topology_version` (u64);
  2. each digested registry field, in registry order;
  3. `sources`, sorted by key (point, radius and power as f64);
  4. regions, sorted by name (footprint and id);
  5. the tick's refusals and effects, in record key order.
- **Not members:** `WorkCounters` (bar 6 checks them apart) and loads (they never outlive their tick).
- **A field's bytes are rehashed only on a tick whose window wrote it.** Owners are immutable at rest, so an unchanged
  field reuses its last digest.
- **Cost, measured on the T3 tile:** 1.7 ms for the four cell fields at 0.1 m (19 ms at 0.05 m), on physics ticks
  only, about 3.4 ms per world second at 0.1 m. c14n-1 JSON of `temperature` alone is 76 ms, which at 10 ticks a
  second would be slower than real time. `boundaries.md` §6.2's derived-value check reads this digest.

## 10. The work counters

`WorkCounters`, frozen, is part of each `TickReport`. Each is an exact integer, never wall time:
- `physics_steps`, and `substeps` per law;
- `cell_substeps` per law: the cells its kernel iterates, times substeps;
- `stable_dt_evaluations`;
- cell windows opened, and cells they copied;
- frames published, and digest bytes hashed;
- power-field builds;
- rebuilds, per cache.

Tests hold them to exact expected values (for example `physics_steps == ticks // physics_every`). They are identical
on any replay, because the caches are built eagerly (§2). B5's budgets and step 4's deferred counters
(`verify_harness.md` §7) read them.

## 11. Bars

| # | Bar | Kind | Source |
|---|---|---|---|
| 1 | At `P` = 0.5 s, 0.1 m: heat's time error is below its space error at the truth grid | verification | `verify_harness.md`'s studies, rerun at `P` |
| 2 | The scenario agreement tests at the fixed physics step, now refining space alone | verification | the tests' existing bars, restated in seconds; the strict red gates stay strict |
| 2b | Each scenario observable moves by under a quarter of its bar between `substep_refine` 1 and 4 | verification | `verify_harness.md` §4 (a space study's step is time-converged) |
| 3 | The forward and reversed law tuples give the same outcome, and each order passes `same_class_under_refinement` over `substep_refine` | verification | `splitting.md` §6, rule 4 |
| 4 | Replay: the per-tick digest (§9) equal on every tick | determinism | `boundaries.md` §6.2 |
| 5 | `prepare` plus kernel matches the law's reference path, bit for bit | determinism | §5 |
| 6 | `WorkCounters` equal their expected values, and identical on replay | determinism | §10 |
| 7 | CPU per world second on the T3 tile at 0.1 m no worse than today's `advance(6.0)`, both caches in; B5's 20% regression gate after | process (B5) | `reviews/sim_core/round1_performance.md` P3 |

Bar 3 is proven able to fail by a planted order-sensitive pair of test laws (a clamp before and after a source).

## 12. Bit-identity: which digests 5a breaks, and how that is recorded

- **They break:**
  - dropping the substep floor (a behaviour change owed to step 5a);
  - the retired 6 s turn (T3);
  - sources integrated by their tick overlap (§3);
  - publication cadence and frame stamps (§3, §4);
  - sorted-key power accumulation, only where three or more sources overlap one cell;
  - splitting damage out of heat's callback, if a test shows it alters the arithmetic (expected not to).
- **They hold:** a single strike's crater arithmetic, the conductance and overlap caches, and the bounding-box
  overlap (§7), each proven against its reference path.
- **How it's recorded:** 5a's PR names each break in its commit and commits the first replay golden (a log and its
  per-tick digest chain). 6.0a regenerates it in a commit that says so. From then a golden changes only on a
  recorded change (`boundaries.md` §6.3).

## 13. Writers under `Simulation`

`boundaries.md` §6.4 owns the classification; this branch amends its rows. 5a moves:
- **`World.advance`** to the physics phase of `Simulation.step`. Its marker goes.
- **The applier's window** to the apply phase. Its marker goes. `Strike` appends a `Load`; `imagine`
  (`imagination.place` as the intent's stage 2) and admin `set_material` produce topology requests. That removes
  imagination's marker.
- **Construction** to `Simulation.from_scene`, through `Topology`.
- **The SEM bridge, until `phase1/agents`** (owner, 2026-11-21), keeps its existing `TEMPORARY(phase1/agents)`
  synchronous path: `execute` submits its record and steps the simulation one tick for it, so a caller still sees the
  effect at once. Its `ModulatorResult` stops carrying the destroyed volume and absorbed energy, which are host-side
  effects (§4). No new deferral: the marker and its roadmap entry already name `phase1/agents`.

`tests/test_ownership.py`'s writer scan follows the new owners.

## 14. Formats on this line

- **The intent log** is a declared `Format` (`intent_log`, version 0, held by others, since bug reports carry logs):
  one c14n-1 record per line after a header record. Its reader refuses an unknown version, has a gate-registry row,
  and has golden fixtures for a record and a header. The record, header and ordering key are `boundaries.md` §6.2 and
  §6.3's; `kind_rank` is `tile_and_client.md` §3.1's table, which `phase1/agents` extends for its kinds.
- **5a's logs carry action vocabulary v0** (`ignite`, `strike`, `douse`); 5b's v1 adds `kindle`, so a v0-log refusal
  test returns with 5b (`tile_and_client.md` §3.2).
- **The header** records `SimConfig`, the law tuple in order, each law's version, the digest scheme, the slots
  `sem_stimuli.md` §5 reserves, a reserved run-seed slot, and the scene by its digest. A scene referenced by digest
  stays a repo-only format (`fire_solid.md` §5.2).
- **6.0a's tables** declare their `Format`s beside their types, per #32's pattern, and join the registry (§6).

The SEM fold rows 5a settles are listed in the checklist's Step 5a section.
