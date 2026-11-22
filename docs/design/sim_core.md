# The simulation core (step 5a): the composition and its contract

**Status:** step 5a's composition note (`foundations_plan.md` row 5a, O34), 2026-11-21, folded from its round-1
review and its delta round (`reviews/sim_core/`). The owner then stopped the paper rounds (2026-11-21): what remains
is checked on 5a's code. The note holds only what other modules and tests depend on. Mechanisms that only running can
check are tests in `docs/plans/checklists.md` ("Step 5a"), each citing its section here. The owner's rulings and the
fold tables live in `reviews/sim_core/`.

## 1. What 5a builds, and what it doesn't

**Builds:** the `Simulation` and its integer clock; the ordered law list with cadences; the field registry; the
topology owner, the region-id array and `topology_version`; the caches; the per-tick digest; the intent log's format,
writer and replay; the work counters; the move of every writer under `Simulation.step`.

**Lands on its line:** fire's 6.0a (`fire_solid.md` §0, §5.1) and the SEM contract's 5a half (`sem_stimuli.md`
§7.1, §11.1), whose seams §5 and §6 define.

**Doesn't build:** bodies and movement (5b); the protocol (step 7); agents and lanes (`phase1/agents`,
`phase1/lanes`); the save (step 9); randomness (its seed slot is reserved, §14); new physics. Preallocated temporaries
and the memory budget (`world_v2.md` row 3) are deferred to B5's memory item, before step 9 (owner, 2026-11-21).

## 2. Composition: no god object

`Simulation` composes these parts. Each is its own type with one job; `Simulation.step` only orchestrates them, as a
short list of named steps (§3).

| Part | Type | Holds | Changes through |
|---|---|---|---|
| Cell state | `World` (kept, minus `advance`, `_power_field`, publication and construction) | the `MaterialGrid`, `sources`, regions, `topology_version`; `Simulation` holds `source_exposure` (owner, 2026-11-22, `reviews/sim_tick/fold.md`) | declared writers (§5.1), inside the write window |
| Topology | `Topology` | nothing of its own; it applies world-edit requests | requests, applied per batch (§5.1) |
| Body state | reserved | 5b's `body_points` container (`sem_stimuli.md` §7.1) | 5b |
| Ledger | reserved | `world_v2.md` §2.6 | the fuel and zone PRs |
| Clock | `Clock` | `tick: int` | `Simulation.step` only |
| Frames | `FrameFeed` | the published frames | construction (frame 0) and `Simulation.step`'s last step |

- **`Simulation` is a pure function of the records it is given.** The intent log's writer and its replay reader live
  in `engine.host` (`boundaries.md` §2.2, layer 8). The host logs what `TickReport` carries; `Simulation` writes no
  log.
- **One constructor,** `Simulation.from_scene`. It builds the world through the topology owner, builds every cache and
  member digest (§9) eagerly, and publishes the authored world as frame 0, so a run from construction and a replay
  from a loaded state start alike.
- **One owner of time,** `Simulation` (`boundaries.md` §7.3). `World.advance`, `World.turn`, `turn_seconds` and
  `grid.time_s` go.
- **Where the new types live** (`boundaries.md` §2.2's layers): `FieldSpec`, `Topology` and its request type with
  the cells, since laws (a layer above) emit requests; `Load` and `Changes` (with load effects) with
  the laws (owner, 2026-11-22, `reviews/sim_laws/fold.md`); `Clock`, `SimConfig`, `TickReport` and `WorkCounters` with the
  simulation.

## 3. The clock and the tick

- **The clock is an integer tick.** World microseconds are `tick * tick_us`; nothing stores time as a float. A
  frame carries the tick it was published on, and seconds are derived from it where an observer asks. Tick 0 is
  0 s; Maxim reading 0.0 as "no time" is OD-I1, already a Phase 3 row, not a host-side offset to add here.
- **The truth constants** `tick_us` and `physics_every` are tile T3's (`tile_and_client.md` §6.1). With
  `substep_refine` (§8) they make up `SimConfig`, a frozen type built in code, hashed into the log header. No data
  file carries them in 5a.
- **Tick 0 is construction** (owner, 2026-11-21): it runs no physics and publishes the authored world. The first
  `step` runs tick 1; `step` runs tick `T` and then sets `tick = T + 1`. A tick is a physics tick when
  `T % physics_every == 0`; its physics covers the interval `(T − physics_every, T]` (the interval is
  `tile_and_client.md` §3.2's). This section owns the phase rule; `realtime_lanes_coop.md` §2.1, a superseded record,
  is not edited.
- **A source's energy in a physics step** is the sum over the interval's ticks of the power of the source value that
  existed at the end of each tick, times `tick_us`, in integers. Ignite, douse and replacement take effect per tick.
  The state it needs is `source_exposure`, an input (§6): each live source's value carries the tick it took effect,
  and each value that ended inside the interval is a closed segment `(key, value, ticks)`. It is digested (§9) and
  saved, and cleared by each physics step.
- **`apply_us` only orders records in 5a.** Time below the tick reaches no law.
- **The order within a tick** is owned by `sem_stimuli.md` §4.1 (D10 as amended). 5a builds steps 1 (apply), 6
  (physics on physics ticks) and 8 (outputs), and the `per_record` and `per_tick` cadences (§5); the other steps stay
  no-op seams.

## 4. `Simulation`'s public interface

```
Simulation.from_scene(scene, materials, *, dx_m, config: SimConfig, limits, laws=DEFAULT_LAWS) -> Simulation
Simulation.step(records: Sequence[LogRecord]) -> TickReport    # exactly one tick
Simulation.tick -> int
Simulation.frames -> FrameView                                   # the latest published frame
```

- **`step` validates the whole batch before applying any of it:** every record's `apply_tick` is this tick, and the
  records are in the log's key order (`boundaries.md` §6.2). A bad batch raises `ValueError` and changes nothing.
- **Frame cadence is `tile_and_client.md` §4's,** refusal-only ticks included; a published frame is its tick's, taken
  at the tick's end. Observers inside a tick read the frame from before it, so an NPC's intent observed at tick T
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
  - `stable_dt(views) -> float` over `bound_reads`, a declared subset of `reads`, so its cache keys on those fields'
    versions (§7);
  - later, `prepare(views)` and a kernel: arrays and scalars in, preallocated outputs, every order-sensitive
    reduction in `prepare`. That is the numba seam; numba waits for a profile, and until then `step` gets the grid.
  - `step(grid, dt_s, inputs) -> Changes`, run narrowed to the law's writer token: a read outside `reads` or a
    write outside `writes` raises, and its writable arrays are revoked on return (owner, 2026-11-22,
    `reviews/sim_laws/fold.md`). A ledger handle joins when the ledger lands (§2).
- **`Changes`** holds the topology requests the law made (§5.1) and, per load, the effect it resolved.
- **Cadence** is one of:
  - `per_record`: in the apply phase (D10 step 1), right after each record's stage 2;
  - `per_tick`: at `sem_stimuli.md` §4.1's step 3, for the body laws;
  - `per_physics_step`: once per physics step, at its start, as `fire_solid.md` §3.2's solid and contact run;
  - `per_substep`.

  The orchestrator runs the groups in that order within D10's steps. A law's tuple position orders it within its
  group, and only there.
- **The tuple is fixed, never discovered,** ordered within each group by `research/physics_spike/splitting.md` §6,
  rule 1. In 5a it is `(damage.loads, heat, damage.thermal)`: `damage.loads` per record, heat and thermal degradation
  per substep (owner, 2026-11-21). Damage stops being heat's `on_substep` callback.
- **After any `Changes` with a topology request,** every law's `prepare` reruns (through the caches) before the next
  substep. Today the orchestrator refreshes source power after every editing substep, and that guard stays.
- **The header records the tuple in order,** with each law's `name`, `version` and cadence (`sem_stimuli.md` §5's
  slot). A log recorded under another order is refused.

### 5.1 The flow: declared, ordered writers, and one resolver per input kind (owner, 2026-11-21)

- **Inputs declare; laws resolve; observers read.** The applier turns each record into inputs (a heat source, a
  `Load`, a world-edit request) and writes no outcome. Laws resolve inputs by cadence and tuple order (§5). Observers
  read only published frames.
- **Every write is declared and ordered.** A field's registry entry lists its writers (§6), and the write window hands
  a handle only to a declared writer, refusing anything else. A field may have several writers, as splitting needs:
  `temperature`'s are heat and, as they land, the solid, contact, skin and bed laws (`splitting.md` §2.1). How
  contact's transfer is computed is `fire_solid.md` §3.2's.
- **One resolver per input kind.** Each declared input kind (a source kind, a `Load` kind; later a pilot or a flame
  flux) names exactly one resolving law in §6, and a test asserts it. Damage is the instance the owner named: every
  load kind resolves in the damage package, whose resolvers (one module per kind, a declared tuple) return
  increments that damage applies in key order. `integrity`'s writers are `damage.loads`, `damage.thermal` and
  `Topology` (a new cell's value); no law outside damage writes it.
- **Accumulated fields take declared contributions.** `radiant_emitters` (`sem_stimuli.md` §7.1) holds rows keyed
  `(writer, …)`, each written by its one writer; readers sum them in sorted key order.
- **World edits are requests, applied per batch.** `imagine`, the admin material edit (`boundaries.md` §6.1's host
  command), construction and destruction produce topology requests: `material`, `original_material`, `region_id`, a
  new cell's `integrity`, and keyed-table rows (`fire_solid.md` §1.4's `pending` and id counter, whose timing §1.4
  owns). A batch is one requester's one invocation: one record's apply (its stage 2 and its loads), one law's one
  substep, or construction. `Topology` applies a batch's requests in key order (an unkeyed request's key is its
  emission index: where paints overlap, the later wins) and bumps `topology_version` once per
  batch that changed a cell's value or the region table (owner, 2026-11-22, `reviews/sim_laws/fold.md`). It is `world_v2.md` §2.2's choke point.
- **Laws couple only through fields.** No law imports or calls another, held by an import contract; an operator two
  laws share lives in a module that is not a law. Contact's exchange with the solid is the declared field
  `contact_exchange`: per coupling row, written by contact each tick it runs, read and reset by the solid law at its
  physics step, saved, and booked by the ledger when it lands.
- **Strikes resolve on their own tick.** `damage.loads` runs per record: each `Load` resolves right after its
  record's stage 2, so the next record's stage 2 sees the crater; "gone" is authored geometry only, so a strike on
  a destroyed region destroys nothing (owner, 2026-11-22, `reviews/sim_tick/fold.md`). The crater is in that tick's frame and its effect in that tick's `TickReport`. No load outlives
  its record. One cell window serves the apply phase, opened only when a handle is needed.

## 6. The field registry

- **Code-primary** (`sem_stimuli.md` D2; owner, 2026-11-21): one tuple of `FieldSpec` values in
  `simcore/core/fields.py`, superseding `world_v2.md` §2.5's `fields.yaml`. Per field:
  - name, dtype and units;
  - container (cells, zone, pool, body, or a keyed table: fire's object, segment and coupling tables, `fire_model.md`
    §10, join here in 6.0a), grid and phase;
  - saved or derived, the default for older saves, and `required`;
  - its snapshot channel and quantization, or none;
  - whether it is digested, and whether it is perceivable (`sem_stimuli.md` §7.4, default false);
  - its conservation law and ledger, or none;
  - its writers, ordered: laws in cadence and tuple order, `Topology`, construction (and the save's loader), or an
    input appender (§5.1). This column is the writers' one owner.
- **Inputs are declared beside fields:** `sources`, `source_exposure` (§3) and the tick's `loads`, each with its
  appender (the applier; `Simulation` for `source_exposure`) and its one resolving law: heat for sources, damage for
  loads.
- **Every reader takes it from there:** storage, the snapshot, the per-tick digest, the save and sem_stimuli §5's
  producer closure, computed over every law in the tuple whatever its cadence.
- **A generated artifact,** `docs/generated/fields.md`, is committed and compared byte for byte by a test.

## 7. Region ids, topology and caches

- **Regions become one `region_id` u16 array** (`world_v2.md` §2.4). Id 0 is unowned. `Region` keeps its authored
  footprint.
- **`topology_version: int`** is Topology's version; §5.1 says when it moves.
- **A cache's key is the versions of what its result reads** (`CellStore.field_version`, which counts rollbacks,
  so no rolled-back window's key recurs; owner, 2026-11-22, `reviews/sim_tick/fold.md`). So:
  - face conductances, per `material`'s version;
  - each law's `stable_dt`, per the versions of its `bound_reads`;
  - each source's geometric overlap per its value `(point_m, radius_m)` (the grid's `dx` and shape are fixed), and
    its weights per `(source value, material's version)`. A re-ignite at a new radius misses;
  - region reductions, per `topology_version` and the write tick of each field they read.
- **A cache holds only what the current state needs:** entries for the current sources at the current versions,
  rebuilt at each tick's end, at construction and after a rolled-back tick (owner, 2026-11-22, `reviews/sim_tick/fold.md`; the
  rollback rule is the owner's, 2026-11-22, `reviews/sim_step/fold.md` S1). So a cache's contents are a function of state, and the eager build reproduces
  them on load.
- **The overlap is computed over the source's bounding box, padded by one cell.** That is bit-identical to the
  whole-grid computation while `sphere_overlap`'s values are multiples of 1/64, which its 4³ sub-sample guarantees:
  their sums are exact in any order (verified, `reviews/sim_core/fold.md`). An exact-overlap replacement would break
  that and must be recorded as a digest break (§12).
- **Cost, measured at PR 3 on the T3 tile** (`reviews/sim_step/round1_det_perf.md`), per 6 world seconds, against
  PR 2's `advance(6.0)`, with only the deposit's cache: 0.88–0.96× at 0.1 m and 2.4× at 0.2 m. With both caches
  (PR 4a, measured): 0.32–0.35× at 0.1 m and 0.72–0.98× at 0.2 m.
- **Accumulations over named collections iterate in sorted-key order** (`boundaries.md` §6.2; string keys by code
  point).

## 8. The fixed physics step, replacing the substep floor

- **The rule** is `splitting.md` §6 rule 3's, with its safety factor: at the start of each physics step,
  `n = substep_refine · max(1, ceil(P_s / min over laws of stable_dt))`, `dt = P_s / n`. `substep_refine` is hashed
  config, 1 in shipped play; tests raise it to refine time on the shipped path (§11).
- **Replan when a change tightens the bound** below `substep_refine · dt` (owner, 2026-11-21; the refined trigger
  owner, 2026-11-22, `reviews/sim_step/fold.md` N3): the rest is split evenly by the same rule. What remains
  is computed from counts, `(planned − taken) · dt`, never from a running float sum.
- **On shipped data `n` is 1** at every verification grid (heat's bound is 240, 60 and 15 s at 0.2, 0.1 and 0.05 m,
  measured), so the new substep is coarser than today's at 0.1 and 0.05 m, and the replan is reachable only from a
  constructed material table.
- **No substep floor** (PR 3 removed it). Only if bar 1 fails does a measured accuracy floor join the rule, as a
  truth constant (owner, 2026-11-21).

## 9. The per-tick digest

- **Scheme `sha256/raw-1`, two-level,** versioned in the header. Each member has its own SHA-256 over its bytes. The
  tick digest is a SHA-256 over: the scheme tag; the tick and `topology_version`; then, per member in order, its name,
  its numpy `dtype.str`, its ndim, its shape and its 32-byte member digest. Integers are u64 little-endian; a string
  is its u64 length and its UTF-8 bytes.
- **A member's bytes:** an array's C-order little-endian bytes. A record member (`dtype.str` `"rec"`, shape its row
  count) writes each row in order, strings and integers as above and reals as f64 little-endian.
- **Members, in order:**
  1. each digested registry field, in registry order;
  2. `sources`, sorted by key: key, point, radius, power and the tick the value took effect;
  3. `source_exposure`'s closed segments, sorted by key and then tick: key, value and ticks;
  4. regions, sorted by name: name, id and the footprint's scene digest;
  5. the tick's records in key order: index, refusal code (`refusals.py`; 0 for none) and effect values.
- **Not members:** `WorkCounters` (bar 6 checks them apart), loads (they never outlive their record) and
  `sem_stimuli.md` §5's per-lane digests, which are their own.
- **Member digests are seeded** by `from_scene` and on load, as the caches are. A member is rehashed only on a tick
  whose window wrote it, so a replay hashes the bytes the live run did.
- **Cost, measured on the T3 tile:** 1.7 ms for the four cell fields at 0.1 m (19 ms at 0.05 m) on a tick that writes
  all four (a physics tick, or a strike's), and about 0.7 µs to combine. c14n-1 JSON of the four fields at 10 ticks a
  second would be slower than real time (`temperature` alone is 76 ms at 0.1 m and 594 ms at 0.05 m).
  `boundaries.md` §6.2's derived-value check reads this digest.

## 10. The work counters

`WorkCounters`, frozen, is part of each `TickReport`. Each is an exact integer, never wall time:
- `physics_steps`, and `substeps` per law;
- `cell_substeps` per law: the cells its kernel iterates, times substeps;
- `stable_dt_evaluations`;
- cell windows opened, and cells they copied;
- frames published, and digest bytes hashed;
- power-field builds;
- rebuilds, per cache.

Tests hold them to exact expected values (for example `physics_steps == N // physics_every` after N steps from
construction). They are identical on any replay, because the caches and member digests are built eagerly (§2). B5's
budgets and step 4's deferred counters (`verify_harness.md` §7) read them.

## 11. Bars

| # | Bar | Kind | Source |
|---|---|---|---|
| 1 | At `P` = 0.5 s, 0.1 m: heat's time error is below its space error at the truth grid | verification | `verify_harness.md`'s studies, rerun at `P` |
| 2 | The scenario agreement tests at the fixed physics step, now refining space alone | verification | the tests' existing bars, restated in seconds; the strict red gates stay strict |
| 2b | Each scenario observable moves by under a quarter of its bar between `substep_refine` 1 and 4 | verification | `verify_harness.md` §4 (a space study's step is time-converged) |
| 3 | The forward tuple and the tuple reversed within each cadence group give the same outcome, and each order passes `same_class_under_refinement` over `substep_refine` | verification | `splitting.md` §6, rule 4 |
| 4 | Replay: the per-tick digest (§9) equal on every tick | determinism | `boundaries.md` §6.2 |
| 5 | `prepare` plus kernel matches the law's reference path, bit for bit: today's `heat.step` and damage callback, frozen as test fixtures | determinism | §5 |
| 6 | `WorkCounters` equal their expected values, and identical on replay | determinism | §10 |
| 7 | CPU per world second on the T3 tile, recorded at 0.2 and 0.1 m; at 0.1 m no worse than today's `advance(6.0)`, both caches in; B5's 20% regression gate after | process (B5) | `reviews/sim_core/delta1_perf.md` |

Bar 3 is proven able to fail by a planted order-sensitive pair of test laws (a clamp before and after a source).

## 12. Bit-identity: which digests 5a breaks, and how that is recorded

- **They break:**
  - dropping the substep floor (a behaviour change owed to step 5a);
  - the retired 6 s turn (T3);
  - sources integrated per tick (§3);
  - publication cadence, frame stamps and tick 0 as construction (§3, §4);
  - sorted-key power accumulation, only where three or more sources overlap one cell;
  - splitting damage out of heat's callback, if a test shows it alters the arithmetic (expected not to).
- **They hold:** a single strike's crater arithmetic, the conductance and overlap caches, and the bounding-box
  overlap (§7), each proven against its reference path.
- **How it's recorded:** 5a's PR names each break in its commit and commits the first replay golden (a log carrying
  its per-tick digests, §14). 6.0a regenerates it in a commit that says so. From then a golden changes only on a
  recorded change (`boundaries.md` §6.3).

## 13. Writers under `Simulation`

`boundaries.md` §6.4 owns the classification of code writers; 5a's PR amends its rows to §6's writer roles. 5a moves:
- **`World.advance`** to the physics phase of `Simulation.step`. Its marker goes.
- **The applier's window** to the apply phase. Its marker goes. `Strike` appends a `Load`; `imagine`
  (`imagination.place` as the intent's stage 2) and the admin material edit produce topology requests. That removes
  imagination's marker.
- **Construction** to `Simulation.from_scene`, through `Topology`.
- **The SEM bridge, until `phase1/agents`** (owner, 2026-11-21), keeps its existing `TEMPORARY(phase1/agents)`
  synchronous path. It is handed a submit-and-step port, an object its test or host owns, never the `Simulation`:
  `execute` submits its record and the port runs one tick for it, so a caller still sees the effect at once. In the
  interim, world time advances one tick per call, every `physics_every`-th call runs physics, the records aren't
  logged (a bridge-driven session can't be replayed), and no outcome bar may be measured through this path. The
  marker's reason is rewritten to say so; its phase and roadmap entry stay. Its `ModulatorResult` stops carrying the
  destroyed volume and absorbed energy, which are host-side effects (§4).

`tests/test_ownership.py`'s writer scan follows the new owners.

## 14. Formats on this line

- **The intent log** is a declared `Format` (`intent_log`, version 0, held by others, since bug reports carry logs):
  one c14n-1 record per line after a header record, and one `tick_digest` line per tick carrying §9's digest. Its
  reader refuses an unknown version or digest scheme, has a gate-registry row, and has golden fixtures for a record,
  a header and a digest line. The record, header and ordering key are `boundaries.md` §6.2 and §6.3's; `kind_rank` is
  `boundaries.md` §6.2's, with the two values 5a's v0 logs add (owner, 2026-11-21).
- **5a's logs carry action vocabulary v0** (`ignite`, `strike`, `douse`); 5b's v1 adds `kindle`, so the v0-log
  refusal test returns with 5b (`tile_and_client.md` §3.2, amended to match).
- **The header** is `boundaries.md` §6.3's. 5a adds `SimConfig`, the law tuple with each law's version and cadence,
  the digest scheme and the slots `sem_stimuli.md` §5 reserves.
- **6.0a's tables** declare their `Format`s beside their types, per #32's pattern, and join the registry (§6).

The SEM fold rows 5a settles are listed in the checklist's Step 5a section.
