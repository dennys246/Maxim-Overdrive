# World, time and states of matter (design v2, 2026-11-16)

> **Superseded 2026-11-16 by `world_model.md`, `npcs_and_sem.md` and the tile documents,** which replace it. Kept as the record of how the decisions were reached.

**Status:** DRAFT, for a design review before any code. It supersedes `realtime_lanes_coop.md` (v1), which stays as
the record of the decisions and reviews that led here. Sources:
- v1 and its two review rounds (`reviews/realtime_lanes_coop/`, including the four `delta1_*.md` files on v1,
  folded here for the first time);
- the signals research (`research/signals/`) and the states-of-matter deep dive (`research/states_of_matter/`:
  physics, SEM, gameplay, architecture);
- the owner's decisions below.

Finding ids (DD1, DA-2, X1 …) point into those files. Numbers marked *from memory* in the research are not yet
verified and must be before they go into `data/` or `docs/`.

## 0. Decisions

**Owner, 2026-11-15 (v1):**
1. Real time with pause, on a fixed tick.
2. The time scale is a dial (pause is a separate state).
3. Day length is a knob, held at 24 hours.
4. Time control is host-only, behind a policy a vote can replace.
5. The work is split into several PRs.
6. Bio-faithful integration is a standing review lens.
7. Neither the world nor the NPC waits for a thought. Needing to wait is evidence for the hybrid experiments.
8. The dial stays free, with fast-forward presets for waiting and sleeping.
9. The hybrid plan is revived for simulated bodies (a pushback in Maxim).
10. Push back on Maxim where the game shows it's wrong (CLAUDE.md).

**Owner, 2026-11-16:**
11. **Waiting is defined in world time.** An NPC never waits in world time: it lives from its request to the reply
    on its substrate.
12. **States of matter are the organising principle of the world model,** and state transitions are a central part
    of the game.
13. **The world simulates matter; SEM exposes it.** SEM is the membrane to Maxim, and is refined here; it doesn't
    run physics.
14. **Rubble is matter, not bookkeeping:** fractured solids stay solid cells, loose and disconnected, and the client
    groups them into rubble meshes. There is no "debris" container.
15. **The development tile is a lab.** A tightly controlled space for experiments, with NPCs as paid study
    participants. The game opens at the end of an experiment that has failed and run out of control.
16. PR 1 is the action trust boundary only. Physics divergence it found is recorded and gated, not patched.
17. The verification harness comes after this design.
18. Temperature plus phase-change progress is the stored heat state (§2.3).

## 1. What changed from v1

- **Matter has containers by phase** (§2). Solids and loose solids live in rig cells; gases, and later liquids,
  live in zones (rooms) authored in metres. A transition moves mass and energy from one container to another.
- **Burning becomes a rate, not a threshold** (§3). The measured cause of today's fire divergence across rigs is a
  threshold on cell-mean temperature: the crate's mean temperature agrees across rigs within 1 °C, while the
  degradation driver differs 1.3–1.5×. Ignition gets a surface-skin model sized in metres, since the heated layer
  (about 1 mm) is below every rig's cell.
- **A sealed crate fire can't burn away** (§3.5). The 3×3×2 m scene's air holds about 4 kg of O₂, enough to burn
  about 1.2 kg of a 130 kg crate. Fires need vents, and the development tile is designed around them (§9).
- **v1's thinking rule is made precise** (§6). Delivery is at `max(T + d_min, first tick after arrival)` through a
  thought source with three implementations (DD1, DA-1). Stale refusals reach the NPC as a percept, never as NAc
  credit (Bio D2). Headless cradles use a world-time latency mode (Bio D1, DA-2).
- **SEM is refined as a membrane** (§7), with seven Maxim proposals. The most valuable is credit for effects that
  arrive after the call: today Maxim's cerebellum would learn that `ignite`, and every phase transition, does nothing.
- **Formats carry self-describing channels** (§8), so a new field never forces a protocol bump. Save v0 comes last
  (§11), after the fields whose meaning could still change.
- **The tile, the exit test and the core loop change** (§9, §10).

## 2. Matter: containers by phase

### 2.1 Where each phase lives

| Phase | Container | State | Resolution |
|---|---|---|---|
| Solid | rig cells | material u8, temperature f64, phase-change progress f32, fuel mass f32, integrity f32 (mechanical damage only), region id u16 | the rig's cell |
| Loose solid (rubble) | rig cells | the same, plus a loose flag and a packing fraction | the rig's cell |
| Gas | zones | moles of a fixed species list (N₂, O₂, CO₂, CO, H₂O, fuel vapour, soot and fines, two or three agent slots); zone enthalpy; pressure derived | per zone |
| Liquid (Phase 2) | pools held by zones | volume per species; level from the zone's open-volume profile; enthalpy | per zone |

- **Rig-independent by construction where it matters most.** A zone's quantities are integrals over cells, and
  fluxes between cells and zones are written per m² with no `dx`, so neither can change an outcome class when the
  rig changes. Free-surface liquid per cell is the one representation that can't be made rig-independent cheaply,
  so it is deferred (research/states_of_matter/physics.md §1).
- **No gas in cells.** An air cell's temperature becomes its zone's. That closes two known gaps by construction:
  "air only conducts", and "a fire's power falls back into air".
- **A per-cell phase tag is rejected** (the Oxygen Not Included shape). It is expensive, it splits the rigs at
  every threshold, and it can't hold "air with 2% CO".

### 2.2 Zones

- **Zones are authored in metres,** aligned to the 0.2 m grid, in scene format v1. Zones never merge. A breach
  creates a **gap** between two zones, whose open area is measured by volume overlap.
- **Vents connect zones to an ambient reservoir from the start** (Kawagoe-style inflow), so fires can be fed. Rooms
  are isobaric, so there is no pressure solver.
- **Zone exchange is one implicit step on the zone graph:** stable for a fully open gap, conservative, and costing
  microseconds.
- **Topology has one choke point.** Every material change goes through `set_material`, which bumps a
  `topology_version`. Zone volumes, gaps and the volume profile update incrementally, in the same substep as the
  change, which avoids SS14's stale-firelock bug.
- **Deferred, recorded as a known gap:** detecting sealed pockets that weren't authored (a barricade that seals
  half a room).

### 2.3 The stored heat state

A solid cell only ever holds its solid phase, so enthalpy factors exactly into temperature plus phase-change
progress. The architecture research measured this as cheap: converting every cell takes 5.1 ms at the max rig with
cached property arrays, against a 97–183 ms heat substep. It keeps today's heat tests unchanged (an L1 regression:
with no transitions, results match the old tests to 1e-12). **Decided (18):** temperature plus progress. Zones
and pools store enthalpy, which is natural there.

### 2.4 Regions as one id array

Today each region is a full-grid bool mask: 5.1 MB per region at the max rig, so 50 objects cost 256 MB.
- **Regions become one `region_id` u16 array,** and each cell has exactly one owner. That removes PR 1's interim
  rule (named solids can't overlap, `scene._check_no_solid_overlaps`) and its two known gaps: a destroyed region
  still claiming its space, and overlap judged on bounding boxes.
- **A `Region` keeps its authored footprint** for "is this point on it" and for where fires land. Its cells become
  `region_id == id`, reached through one accessor (PR 1's `Region.cells` users move to it).
- **Region reductions** (the SEM sensors) are cached once per physics step, not recomputed on every read (about
  5 ms per read at max today).

### 2.5 The field registry and the material table

- **`data/world/fields.yaml`, a declaration, not a plugin framework.** For each field it declares:
  - container, grid (rig cell, fixed metres or zone) and phase;
  - units (intensive per unit volume for cells, extensive for zones) and dtype;
  - conservation law and ledger;
  - whether it is saved or derived, with a default for older saves;
  - its snapshot channel, quantization and `required` flag;
  - the process that steps it, and how often.
  
  `MaterialGrid` holds fields from the registry instead of one attribute each.
- **Material table v1:** versioned, with closed key sets and sections for solids, liquids, an ordered gas-species
  list, and reactions.
  - Transitions name their target (melt to molten steel, boil to water vapour).
  - The loader refuses any reaction whose mass balance doesn't close to 1e-9, and checks the atom balance in C, H,
    O and N.
  - A test on the shipped table checks about 13.1 MJ released per kg of O₂ consumed, ±10% (Huggett 1980,
    verified).
  - The first latent transition is bound water in drywall and concrete, which leaves as steam: the cheapest one
    with real gameplay.
- **A memory budget per rig** (`memory_budget_mb`, proposed 128 / 512 / 2048) is checked against the registry when
  a world loads. Estimated state is about 91 B/cell: 7 / 58 / 466 MB per tile at laptop / rig / max.

### 2.6 The ledger

Every process is one transfer: limited by what the donor holds, applied antisymmetrically, never clamped
afterwards (clamping created mass in SS13). Per substep, cells plus zones plus pools change by sources minus
outflow, to 1e-10, at every rig, with a Hypothesis property over random scenes. The ledger closes two known gaps by
construction: a destroyed cell losing its heat, and the fuel gap.

## 3. Burning, ignition and phase change

### 3.0 The principle: reconstruct, decide at the point, integrate upward

Every resolution problem found so far applied a non-linear decision to a coarse average:
- degradation and ignition were thresholds on a cell's mean temperature;
- breaching is a threshold on whole cells;
- reach and fire centres were decided from voxelized cells.

The heat field converges; the decisions on it didn't. So, as a standing rule (CLAUDE.md, owner decision
2026-11-16):
- **No threshold or non-linear rate on a cell's mean** where the outcome depends on structure inside the cell.
- **Reconstruct the sub-cell profile,** from neighbours or a surface model sized in metres. Evaluate the law on it
  and integrate over the cell. This is the standard finite-volume approach: reconstruct, then evaluate.
- **Each consumer reads at its own scale:** NPC sensors as reductions over volumes in metres, zones as integrals,
  the client at its own level of detail.
- **Fineness is spent where gradients are.** Adaptive refinement near fronts is the Phase 2 "Scale" item.

This is also the fuel model's acceptance requirement. "A rate that converges with resolution" isn't enough: today's
law converges, slowly (integrity at turn 22 is 0.703 / 0.567 / 0.514), and still leaves the red gate red. The
requirement is that a cell's rate estimates the integral of the point-wise rate over the cell well enough at the
coarsest rig to flip `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`.

### 3.1 One transition kernel

Energy above a component's transition enthalpy converts it, at its latent heat. A condensed product stays in the
cell; a gas product goes to the zone, carrying its sensible enthalpy.

| Transition | Law | Where |
|---|---|---|
| Melting, solidification | progress plateau at T_m (a mushy band for glass and polymers) | cell |
| Pyrolysis (fuel to fuel vapour plus char) | energy-limited at the surface once ignited: ṁ″ = q″_net / (L_g + c·(T_p − T_bulk)); volumetric when a cell's bulk passes the pyrolysis point | face, cell |
| Surface ignition | a heat-balance skin per exposed fuel face, depth in metres; ignite when the surface temperature reaches T_ig | face |
| Combustion | per zone: fuel vapour burned at min(supply, O₂ limit), with an extinction ramp from 15% down to 10% O₂; 13.1 MJ per kg O₂ | zone |
| Evaporation, condensation | ṁ″ = h_m·(ρ_sat(T_s) − ρ_zone) | face or pool and zone |
| Boiling | energy-limited, ṁ = q/L_v | pool, cell |
| Extinguishing | water mass per m² per second, as a sink of c·ΔT + L_v, with the vapour going to the zone | face |

**Measured reasons for each choice** (research/states_of_matter/physics.md §0):
- **Today's threshold-and-delete burning doesn't converge.** At 90 s, slab integrity is 0.504 / 0.500 / 0.583
  from coarse to fine. Energy-limited mass loss gives 0.791 / 0.739 / 0.713, converging steadily.
- **A cell-mean ignition threshold has an error proportional to cell size.** Igniting at 350 °C takes 1,350 s at
  0.2 m cells and 25 s at 3 mm, against 5.2 s in closed form. The skin model fixes this by construction.
- **Flame feedback onto a burning face is a fixed flux per m²** (about 25–35 kW/m² for wood, *from memory*), never
  a fraction of the heat release, whose loop gain above 1 runs away.

### 3.2 Strength and removal

Strength follows the remaining solid mass fraction, times a temperature-dependent factor from a data table. The
integrity sensor becomes mean strength, which converges. A cell becomes loose when it loses its connection to
support (§4), and air only when its mass reaches zero, after its contents move to the zone.

### 3.3 What still flips

`breached` stays a threshold on connectivity, so near its threshold it can still flip between rigs (PR 1's strict
red gate). The cure is an outcome-margin rule, not a better kernel: a decisive value must sit at least 2× its
cross-rig spread from its threshold. The research adapts that from ASME V&V 20. **Open for the owner (Q3):** how
the resolution rule treats outcomes at a class boundary.

### 3.4 Benchmarks

The full ladder is in research/states_of_matter/physics.md §5 and research/signals/benchmarking.md. The minimum
set, before the fuel model is admitted:
- **One-phase Neumann melting:** first order in space, gated by an envelope, not a pairwise order band.
- **A block melted at constant power:** exact.
- **Thermally thick ignition:** the same time at every cell size.
- **Steady planar ablation:** exact for boxes.
- **Sealed-room O₂:** linear decline, then the extinction ramp.
- **Adiabatic room heating:** exact.
- **The ledger.**
- **Ventilated burning,** judged as an outcome class.

These also flip PR 1's two strict red gates on fires, which the fuel model is required to do.

### 3.5 Sealed and vented fires

A sealed room fire chars a surface and goes out in a few turns. That's the "a fire goes out" test, and it
retires `tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`. "Burns away" needs a vent:
the tile provides one by design (§9).

## 4. Rubble: loose solids, grouped by the client

- **A strike or a burn no longer deletes solid mass.** Fractured cells stay solid with a `loose` flag and a
  packing fraction. Rubble is porous, so gas still flows through it at a reduced open area.
- **Connectivity finds loose clusters on events, not per turn.** It runs `ndimage.label` on solids against
  anchored support (the floor, authored fixtures), from the same `topology_version` choke point. Cost is O(changed
  region); a full relabel takes 0.6 / 3.8 / 28.8 ms per tile at laptop / rig / max.
- **Settling under gravity follows a rule written in metres:** an angle of repose, with a pile's height and
  footprint set by its volume. It is not a falling-sand update that moves a fixed number of cells per step, which
  would make piles depend on the rig. Settling is per cluster, on events.
- **Outcomes are judged by volume,** never by fragment count. A fragment can't be smaller than a cell, so laptop
  rubble is 0.2 m chunks and max rubble 5 cm chunks; the rubble volume and pile height are what agree.
- **Fines go to the zone.** Mass finer than any cell (dust, powder) becomes the zone's soot-and-fines species,
  which the gas model already carries.
- **The client groups disjoint loose clusters into rubble meshes.** That's purely visual, so a weak machine draws
  a coarse pile and a strong one draws fragments. The snapshot carries the `loose` channel; the grouping is the
  client's.
- **For Maxim, a chunk is a real thing,** an entity an NPC can perceive and use (later: carry, throw, climb), which
  is where grounded concepts come from.

## 5. Time and the simulation

v1 §2 stands (one `Simulation` owning `World`, one integer clock, a fixed order within a tick), with these folds:

- **The rig field is substeps per physics step,** and `heat.step` takes a count of physics steps, not seconds, so
  the field has a single meaning (DX2). The heat tests' 3600 s case is rewritten, not reinterpreted, and its error
  figures are re-derived (laptop rises from 0.99% to 1.84% against a 2% bound, measured).
- **No "at no extra cost" claim** (DX1). The new rig values do 3× / 1.5× / 1.125× today's substeps on laptop / rig
  / max. Precomputed per-material bounds remove the per-substep rebuild of conductances. Fire power comes from
  burning cells, so the 453 ms `_power_field` cost at max disappears rather than just being cached.
- **One clock for sensors.** `SensorReading.timestamp` and the snapshot's time are world time from the tick. A
  required keyword-only clock replaces `grid.time_s` for `RegionSensor` (DX7, DA-10).
- **Everything `Simulation.step` reads is hashed world config:** action limits, `max_age_ticks`, the stub's
  parameters, per-tick limits, the heat-source cap, staleness rules (DD4, DA-7). A test checks that the
  simulation can't read server config.
- **The determinism tiers** (v1 §4.4) are restated:
  1. Replays are bit-identical on one machine.
  2. Scripted runs whose inputs carry their ticks are bit-identical at any dial (DD5). A scripted client over the
     wire is tier 3, so B7's golden screenshots run as a log replay.
  3. Live models or live players aren't reproducible.
- **The tripwire is thread-scoped** (DD7). It raises only on the simulation thread inside `step`, records hits in
  the test's own list, covers `os.urandom`, `secrets`, `datetime`, the monotonic clocks and the numpy random
  globals, and is proven with a planted `time.time()`.

## 6. Lanes and thinking

v1 §4 stands (one owner, explicit channels, backpressure, lifecycle, meters), with decision 11 made precise:

- **A thought source decides delivery, with three implementations behind one apply path** (DD1, DA-1). The
  simulation lane reads it in `step`:
  - **Stub:** computes its result synchronously and releases it from checkpointed state at exactly T + L. It has
    no thread, which keeps tier 2.
  - **Live:** uses the inbox. A result applies at `max(T + d_min, first tick after arrival)`, so a thought never
    lands faster than an NPC can think, and the world never waits.
  - **Replay:** reads the log.
- **Headless cradles and experiments use the world-time latency mode** (Bio D1, DA-2). Each request kind declares
  a delay d in ticks. The host may block in *wall* time so that a thought lands at exactly T + d in *world* time.
  The NPC still lives through T..T + d on its substrate, so it never waits in world time (decision 11). This is
  tagged ANALOG: deliberation time as a declared constant. Without it, cradles at about 300× would abandon almost
  every thought, at a rate set by the host's GPU.
- **The log splits inputs from derived decisions** (DD2).
  - Inputs, which replay feeds: intents, thought results and worker failures, each matched by request id
    `(tick, actor, n)`, never by actor.
  - Decisions the `Simulation` makes itself, which replay recomputes and asserts equal to the logged copy:
    abandoned, cancelled, stale, dropped late, and a request record with a hash of its context.
- **One total order per tick** (DD3). The simulation receives arrivals in inbox order, sorts them by one total key,
  then assigns `host_seq`. Log order is apply order, and a replay never sorts.
- **A stale refusal is a percept for the next thought, never NAc credit** (Bio D2). Through Maxim's failure path
  it would write a negative, state-blind causal link on the tool, caused by latency and scaled by the dial. Maxim's
  TF2 already excludes refusals the game makes before the modulator runs. A stale-plan learning signal is raised
  as a Maxim question.
- **The worker's wall timeout stops counting while paused** (DD10).
- **PR 3 builds the lane skeleton; PR 4 only adds to it** (DA-3). PR 3 has the simulation-lane thread,
  `host_seq`, the log write and the outbound slots. PR 4 adds the thinking lane, the meters and the
  crash-injection tests. PR 3's golden fixtures already include the `busy` error code.

## 7. SEM: the membrane between the world and Maxim

SEM has no machinery that can run matter (research/states_of_matter/sem.md §1):
- its drift is a fixed rate toward a set point, and its failure modes are thresholds on single readings, both on
  the wall clock;
- the couplings between quantities are parsed but never read;
- scene entities are never ticked.

So the world simulates and SEM exposes.

**Overdrive does now, inside Maxim's frozen types:**
- **N1. Three entity kinds:** `structure` (an authored object, as today), `zone` (a fixed volume of space, which
  keeps a stable identity as matter moves), and `matter` (tracked puddles, clouds and rubble clusters; deferred).
- **N2. Phase sensors are fractions,** never labels: solid, liquid and gas fractions, wetness, gas readings.
  Maxim's learning paths read only numbers, and fractions converge across rigs.
- **N3. Affordances are causes, never outcomes:** heat, cool, pour, ignite, vent, douse; never `melt`. No
  `target_effect`, because it would create a fake second state beside the cells.
- **N4.** A refused target names the call that works, tested through Maxim's real call shapes. Done in PR 1.
- **N5.** A world-backed `check_affordance_requires` that reads live cells. Today a declared `requires` on a world
  entity would gate on nothing.
- **N6. Root body sensors owned by the world:** immersion, wetness and skin temperature, written through
  `world_set_axis(owner="overdrive_world")` after each advance. This is the proven Minecraft path for oxygen and
  health.
- **N7. A versioned vocabulary in `data/sem/vocabulary.yaml`,** with a golden fixture of the tool surface. NPC
  memories key on tool and sensor names exactly, so a rename orphans what an NPC learned.
- **N8.** Limits generated into affordance descriptions. Done in PR 1.

**Maxim proposals, under roadmap Phase 3:** each names what it argues against, and follows Maxim's own process.

| | Proposal | Argues against |
|---|---|---|
| P1 | An appended `acts_on` field that separates done-to from done-by (PR 1's item 11) | reading "shape-frozen" as "no appended fields"; `scene_actor_affordances.md` invariant 5 |
| P2 | Validation in the executor, with a call-error kind and declared ranges, exempting Maxim's own injected keys (PR 1's item 10) | TF2 |
| **P3** | **Measured credit for effects that arrive after the call** ("act now, credit later", generalising D53's measured transitions). Maxim's cerebellum learns from sensor values read in the same call, and Overdrive changes cells only in `advance`, so today every phase transition would be learned as having no effect. | the assumption that an action's effect is complete when the call returns |
| P4 | `world_set_axis` for sub-sensors such as `arms.thermal` | |
| P5 | Body drift, `FailureMode.last_fired` and sensor timestamps on world time | joins #1361 and the deterministic-agent item |
| P6 | A `SEM_PROTOCOL_VERSION` with a written minor and major rule, and a forward-compatibility marker on `ModulatorResult` | |
| P7 | Keep a refusal's metadata for the audit log and the LLM's carryover only, never for learning | |

**Deliberately not proposed:** categorical sensors, repurposing the couplings, or a phase-diagram type in SEM.

The rest of the Maxim list (the receptor-first proposals from research/signals/maxim_senses.md) joins these when the
body model is designed (Phase 4):
- burn pain and a two-sided corrective need (GL2b's `NociceptorSpec`);
- a nausea drive that tolerates delayed credit, for toxins and radiation;
- unconsciousness as a body state;
- percepts gated by line of sight;
- a review of the Wire-4 allowlist.

## 8. Protocol and formats

v1 §7 stands (closed schemas, one final reply per message, two-stage validation, the intent log), with these
changes:
- **Frames are self-describing.** The header lists grids (each with its own shape, cell size and origin), channels
  (dtype, units, an encoding from a closed list, `required`) and tables with typed columns (per-zone gas, pools).
- **Old readers** refuse an unknown required channel and ignore unknown optional channels and columns.
  - Adding an optional channel bumps the registry version, not the protocol.
  - A new encoding, dtype, `kind` or compression bumps the protocol.
  - `kind: delta` is reserved, not built.
- **Six golden fixtures,** including an unknown optional channel (must be ignored), an unknown required channel
  (must be refused) and an asymmetric grid.
- **`welcome`** adds the channel catalogue, the zone list and material table v1. The intent log header hashes the
  registry and the material table.
- **`extinguish` changes meaning:** water as an energy and O₂ sink, not a deleted heat source. It bumps the
  action-limits version.
- **The save uses the same grammar, losslessly,** tied to one rig's cell size. It embeds the registry, the material
  table, the scene with its zones, and the placed imagined specs. Derived fields are recomputed on load and checked
  against a stored digest. A "heavy mode" test saves, loads and continues, and must match an uninterrupted run bit
  for bit.

## 9. The development tile: the lab

**Why a lab.** It is the one place where a controlled environment is the fiction, so the benchmark ladder's
scenes are rooms in it, and "a failed experiment run out of control" is a reason for every phase hazard at once.
It also needs fewer bespoke assets than the heist (which stays a long-term goal), since its look comes from the
snapshot channels.

**Rooms, each designed for a phase and a lesson.** A proposal, for the owner to shape:

| Room | Phases and transitions | What an NPC can learn | Warning cue | Relief action |
|---|---|---|---|---|
| Sealed test chamber | combustion in a fixed O₂ budget | fires starve when sealed | CO₂ air hunger, smoke | leave, open the door |
| Vented burn bay | ventilated burning, smoke layer, rubble | how fire grows and burns away | glow, heat on skin, crackle | retreat, douse |
| Cryo store | LN₂ boil-off displacing O₂; frost | silent hypoxia is invisible, so trust the instrument | fog, hiss, the O₂ meter (none from the body) | leave, ventilate |
| Coolant loop and bench | coolant boiling; burns from steam | where Overdrive's heat debt goes | hiss, steam, heat | step away, vent |
| Wet lab (Phase 2) | spills, evaporation, toxic vapour | delayed malaise from a spill room | smell, then malaise later | avoid the room |
| Lower level (Phase 2) | flooding, immersion, breath | drowning, finding an air pocket | rising water, breath | swim up, an air pocket |

**Study participants.** NPCs come in for the day for a paid study:
- It explains why ordinary people are in a controlled lab, and why they're instrumented: their sensors and the
  wall readouts are part of the fiction.
- It gives the SCN a real daily rhythm: arrival, sessions, going home.
- Their cradled lives outside the lab answer "why did I sign up?". That's what the Phase 4 cradle writer needs.

**The opening:** the end of an experiment that has failed and run out of control.

**Story questions for the owner** (rights reserved): were participants told the truth; what the experiment was;
who survives; whether the ripperdoc clinic is part of the lab or its aftermath.

**Every hazard gets an authored escape:** a vent, a door, an air pocket. Without one the NPC learns helplessness,
not avoidance. An invisible hazard (CO, low O₂, LN₂ boil-off) is shown to players and NPCs alike only through an
instrument; the instruments could be cyberware, which would make a hazard a reason to visit the ripperdoc.

**Proposed exit test (Q1),** replacing the roadmap's alley crate: in the lab, a fire lit in the sealed chamber
starves, and one in the vented bay burns its fuel away. Both must look the same, apart from detail, at the laptop
and rig profiles, with the outcome margin of §3.3. A burning crate can still be the vented bay's fuel.

## 10. The core loop: Overdrive as heat debt

Pushing a body past its limits (the Overdrive mechanic) overruns the cyberware's cooling, and cooling works by
changing phase: sweat evaporates, coolant boils, you plunge into water. So where you are sets how long you can
Overdrive: in the rain, longer; in a burning bay, shorter. This ties the game's central mechanic to the matter
model, and is the strongest gameplay argument for decision 12 (research/states_of_matter/gameplay.md §1). It sits
beside the owner's action-energy and homeostasis idea (roadmap Phase 5): a body's energy store and its heat budget
are the two limits Overdrive spends.

## 11. Order of work

| # | PR | What |
|---|---|---|
| 0 | | This design accepted, after its review round. |
| 1 | `phase1/act-validation` | The action trust boundary (in review). |
| 2 | `phase1/verify` | The verification harness, after this design (decision 17): heat retrofitted (its order test fixed), the late-burn convergence recorded, exact performance counters. |
| 3 | `phase1/sim-clock` | The `Simulation`, the integer clock, substeps per physics step, `set_material` and `topology_version`, the region id array, preallocated temporaries, `memory_budget_mb`, and the registry for today's fields driving the digest. |
| 4 | | Material table v1. |
| 5 | `phase1/protocol` | Protocol v0 with the self-describing frame grammar from its first fixture, plus the lane skeleton (DA-3). **This is the protocol freeze:** the grammar must be generic, though the fields need not exist yet. |
| 6 | `phase1/zones` | Scene format v1 with zones and gaps; air out of the conduction solve. |
| 7 | `phase1/fuel` | Fuel mass, surface skin, pyrolysis, O₂ and products per zone, vents, strength by mass fraction, loose solids. It flips the fire red gates and removes the ignite band-aid. |
| 8 | | Phase-change progress, with bound water as the first transition. |
| 9 | | **Save v0, only now,** so no saved field changes meaning afterwards. |
| 10 | `phase1/lanes` | The thinking lane, meters, crash injection. |
| 11 | `phase1/lab` | The lab tile, its benchmark rooms, and the Godot client (v1's steps 4 and 5). |

Phase 2 adds pools, melting and freezing, evaporation, sealed pockets, chunk sleeping, delta frames and a fixed gas
grid.

## 12. Risks, and what not to build

- **Binary transitions can still split rigs:** ignition, melt completion, a gap opening, `breached`. They are held
  by per-area rates, the skin model, flow proportional to open area, zone-level outcomes, and the outcome-margin
  rule (§3.3).
- **Other risks:**
  - stiffness;
  - float32 conservation, which needs transfers in float64;
  - authoring zones, and barricades that don't seal;
  - full frames at the max rig, at about 41 MB.
- **Not now:**
  - a plugin framework or chemistry engine;
  - per-cell multiphase flow or CFD, and a pressure solver;
  - lava flow;
  - boiling points that depend on pressure;
  - rig-portable saves;
  - compression or delta frames before B5 measures a need.

## 13. Open questions for the owner

1. The exit test (§9): replace the alley crate with the lab's sealed and vented fires?
2. The lab's story questions (§9).
3. How the resolution rule treats outcomes at a class boundary: the outcome-margin rule (§3.3), or another?
4. Instruments as cyberware (§9)?
5. The client's minimum renderer: volumetric fog needs Godot's Forward+, so a low-end tier needs a fallback.

## Supersedes

When this design is accepted, these change in the PR that lands each piece:
- `realtime_lanes_coop.md` becomes a record, superseded by this file.
- `docs/architecture.md`:
  - the cell model, "The game is turn-based", the transport's buffer advice and head-of-line note;
  - the known gaps this design closes, which become "Fixed" notes with numbers once measured.
- `docs/roadmap.md`:
  - Phase 1's tile, exit test and fuel item;
  - the "Turn length" question;
  - Phase 3's list, renumbered to fold in v1's items and P1–P7 (PR 1's items 10 and 11 become P2 and P1);
  - Phase 4's "dialogue screen and turn order";
  - Phase 2's gas, liquid and structural items.
- CLAUDE.md: "only `World.advance` moves time" (becomes `Simulation.step`), the cell model in Layout, and "RNG
  owned by `World`".
- `docs/standards_backlog.md`: B2 (the replay's inputs), B5 (per-lane and per-field budgets), B7 (golden
  screenshots as log replays), B12 (fields.yaml and material table v1).
