# States of matter through SEM: what SEM can carry, who should simulate, and what to change

Maxim at `4b773ef8` (read-only). Overdrive worktree `phase1/act-validation` at `56eed51`. `M/` means
the Maxim repo root. `O/` means the Overdrive worktree
the Overdrive repo (branch phase1/act-validation). Neither repo was modified.

## 0. The answer in brief

- **No: phase transitions should not be simulated through SEM.** SEM is good at three things: naming what
  can be sensed and done, turning that into tools, and carrying the results into Maxim's learning. It has no
  machinery that can run matter. Its only dynamics are a linear drift on a body's drives and threshold
  failure modes. Both run on the wall clock (`M/src/maxim/embodiment/body.py:293-298`,
  `M/src/maxim/embodiment/sem.py:1560`), only on the agent's own body tree, and per entity, not per cell. The
  couplings that could have linked one quantity to another are parsed and never read
  (`sem.py:146-180`; `M/docs/plans/autonomic_layer.md` R-4), and Maxim has reserved them for drive
  interaction.
- **Yes: SEM is the right way to expose phases and to act on them.** That means phase fractions as sensors
  on objects and on fixed volumes of space, cause verbs (heat, cool, pour, ignite, vent) as affordances, and
  world-owned body sensors (immersion, wetness, skin temperature) written through `world_set_axis`. The world
  does the physics (enthalpy per cell, inside `World.advance`) and Maxim does the feeling and the learning.
- **Phases expose three real SEM defects** that the game should push upstream:
  1. **Effects that take time are invisible to learning.** The cerebellum learns from a sensor read taken in
     the same call as the action (`M/src/maxim/embodiment/tool_bridge.py:585-590, 884-890`). A melt arrives
     several `World.advance` calls later, so the forward model learns that "heat does nothing".
  2. **The schema can't say whether an affordance is done to the entity or done by it** (delta round BF-1).
  3. **A malformed or misdirected call is booked as a world failure** (TF2; review BF-1 and BF-2).
  A versioned extension path and world-owned sub-sensors complete the list.
- **The cleanest division:**
  - The **world** owns matter, transitions, and the exchange between bodies and matter.
  - The **SEM bridge** owns the vocabulary: entities, sensors, verbs, validation and its version.
  - **Maxim** owns what the NPC feels, predicts and remembers.
  - A material's phase diagram is world data (`O/data/materials/`). It is not a SEM spec.

## 1. What SEM can express today

### 1.1 State: sensors

| Property | What Maxim does | Where | Consequence for phases |
|---|---|---|---|
| Value type | `SensorReading.value: Any`. In practice every learning and pain path reads only `reading_schema["type"]` of `"float"` or `"int"`: `Entity.read_scalar_sensors`, `Embodiment.evaluate_failures`, `body_state_summary` | `sem.py:38-65, 909-921`; `body.py:309-316, 704-708` | **No categorical sensors.** "Phase = liquid" has to be a number. This is the right answer anyway: phase *fractions* are volume reductions, they converge with resolution, and they don't jump at a rig-dependent instant. Overdrive already encodes a boolean as a float (`breached`, `O/src/maxim_overdrive/sem_env/bridge.py` `RegionSensor.reading_schema`). |
| Schema types | `float` with a range, `ndarray` with a shape and dtype, or a free `type`. Optional `modality` (`world`, `audio`, ...) is validated loudly | `M/src/maxim/embodiment/spec.py:630-660` | A declared range is what A4 and P1 normalisation use (`M/src/maxim/runtime/substrate_proposal.py:160-183`). Phase fractions get `[0, 1]` for free. |
| Escape hatch | `SensorReading.extra` (CC3 path (a)): additive, JSON-only, excluded from equality | `sem.py:42-56` | Diagnostic context such as `cell_size_m` belongs here. It is not a place for phase state that the NPC is meant to learn from. |
| Two stores | A sensor's value lives in `Sensor.read()` **and** in `vital_metrics`. Failure triggers read `read()`. `requires` gates, drive reads and the effect writers read and write `vital_metrics` (`_sensor_location`, `SpecModulator.check_affordance_requires`) | `sem.py:1387-1461`; `spec.py:1080-1134` | Overdrive's sensors read cells live and leave `vital_metrics` empty. So a declared `requires: {liquid_fraction: 0.1}` on a world entity would gate on nothing. Overdrive has to implement `check_affordance_requires` itself; the bridge looks it up by `hasattr` (`tool_bridge.py:521`). |
| Timestamps | `SpecSensor.read` stamps `time.time()` | `spec.py:819-836` | Overdrive stamps `grid.time_s` (`bridge.py` `RegionSensor.read`). Keep it that way. |

### 1.2 Dynamics

- **`drift_step`** (`sem.py:435-451`) is pure and linear. A homeostatic drive moves toward `set_point` at
  `drift_rate` per second. An entropic drive moves in one direction and is clamped to [0, 1]. There is no
  energy, no latent heat and no dependence on anything outside the drive.
- **`tick_vital_drift`** (`body.py:634-685`) is driven by `evaluate_failures`, with
  `dt = time.time() - _last_poll` (`body.py:293-298`). There is also a legacy drift keyed on names
  (`fatigue`, `durability`, ...).
- **Failure modes** (`sem.py:1463-1574`) are threshold triggers (`> < >= <= ==`) on one reading each,
  combined by `any` or `all`, optionally persistent with a recovery condition. They stamp
  `last_fired = time.time()` and draw on a fixed vocabulary of six base names.
- **`CouplingSpec` and `ModulationSpec`** are shape-frozen, "1.0 interface, deferred", parsed and never read.
  `autonomic_layer.md` R-4 says they "stay reserved for drive interaction and are not repurposed".
  `M/docs/plans/deferred/sem_environmental_proximity_sensing.md` calls them "the wrong axis" for exposure
  across entities.
- **Who runs it.** The NPC's loop evaluates only its own body tree (`root.walk()`). A scene entity's drives
  and failure modes run only inside `OrchestratorActorTool`, on an ephemeral `Embodiment(scene_entity)`
  built per call (`M/src/maxim/simulation/tools.py:879`). Its `_last_poll` starts at 0, so **it never
  drifts.** Maxim has no engine for world dynamics. Its dynamics are the body's own (interoceptive).

### 1.3 Effects

- **`self_effect`** is a constant map of sensor deltas applied to the *executor's own body*.
  **`target_effect`** is the same kind of map applied to a resolved `target` body, and is silent with no
  target (`sem.py:81-139`; `tool_bridge.py:125-168, 758-767`). Both write `vital_metrics`, clamped to the
  declared range.
- **The deltas ignore the parameters.** A 1 J strike and a 1 MJ strike declare the same effect.
- **The phantom-credit guard** filters `self_effect` keys that a live stream owns
  (`live_world_set_sensors`; `tool_bridge.py:627-642`; `M/docs/plans/deferred/sem_motor_binding.md`
  decision 3: "the modeled azimuth self_effect is a fabrication").
- **For world entities, `target_effect` must stay empty.** Written into a region's `vital_metrics`, it
  would be a second, fabricated state beside the cells, which `RegionSensor` never reads. The same
  principle as the phantom-credit guard, applied to the world.
- **On success, `ModulatorResult.metadata` is the live extension channel.** It is spread into the tool's
  output (`tool_bridge.py:920`), and two keys are understood: `outcome_valence` (D53) and
  `measured_drive_transitions` (`tool_bridge.py:678-679, 967-970`;
  `M/src/maxim/hardware/reachy/motor_backend.py:385-393`).
- **The forward model learns from a read taken in the same call.** `entity_state` is read from the acted-on
  entity's sensors right after `modulator.execute` and fed to `cerebellum.observe_from_action(actual=...)`
  (`tool_bridge.py:585-590, 864-890`). Overdrive's own rule is "actions change cells; only `World.advance`
  moves time". So `ignite` (it only registers a `HeatSource`) and every phase transition read as *no
  change*. Only `strike`, which destroys cells inside the call, gives the cerebellum a true delta.

### 1.4 Affordance semantics: done to vs done by (BF-1)

One `AffordanceSchema` type carries two readings, and nothing tells them apart:

- **The item reading (done to, or done with).** `generate_tools_for_entity` registers `{entity}_{aff}` in the
  *agent's* registry (`tool_bridge.py:1086-1104`). Calling it is the agent doing something to or with the
  entity: `cradle_fire_pit.yaml` `touch` and `warm_self` (the `self_effect` lands on the toucher), and
  `minecraft_bread.yaml` `eat_bread`. To decrement the loaf itself, bread declares
  `target: {default: minecraft_bread}` and `target_effect: {portions: -1}`. Its comment calls this "zero new
  mechanism". It is the done-to case expressed with a self-target workaround.
- **The actor reading (done by).** `OrchestratorActorTool` has the entity perform the affordance on a target,
  which defaults to `"player"` (`simulation/tools.py:730-870`). Example: `dragon.breathe_fire`.
- **Imagined entities have no tools.** They are observe-only: "the agent interacts with scene entities using
  its own body's tools, not the entity's affordances" (`M/src/maxim/imagination/trigger.py:539-540, 762-764`).
  That is a third model: verbs live on the body.

Overdrive's `structure` modulator is the item reading (`strike`, `ignite`, `extinguish` are done *to* the
region). The delta round measured what follows: `actor(entity="crate", affordance="ignite")` with its
documented default target is refused, and only `target="crate"` works. Maxim reads that call as "the crate
ignites the crate".

### 1.5 Booking results (TF2, refusal kinds)

- **A failed result loses its metadata and books a NEGATIVE.** `ModulatorAffordanceTool.execute` returns
  `ToolOutput(success=False, error=result.error)` and drops `metadata` (`tool_bridge.py:582-583`). Under
  TF2 the call reached `tool.run`, so it "ran", and `ToolPainBridge.record_tool_failure` books an attributed
  NEGATIVE on `tool:<entity>_<aff>` (`M/docs/plans/tool_failure_credit.md` TF1–TF3, Stage 2).
- **A `requires` block is booked the same way.** It returns `success=False` with
  `side_effects["affordance_blocked"]` (`tool_bridge.py:521-535`). This is the intended "can't fly with a
  broken wing" chain.
- **Only the executor can exempt a refusal from learning.** `GATE_REFUSAL_KINDS` keeps refusals out of NAc,
  pain and goal credit, and only the executor produces those kinds (#1315). `INVALID_INPUT` and
  `VALIDATION` exist but aren't in the set (`M/src/maxim/tools/base.py:60-87`).
- **Argument checking is minimal.** `Tool._validate_input` checks only that required keys are present
  (`base.py:714-731`).

### 1.6 World-owned sensors

- **`world_set_axis` writes root sensors only.** It clamps to the declared range and takes an `owner=`
  (`M/src/maxim/embodiment/audio_localization.py:691-760`). Sub-sensors such as `arms.thermal` live on a
  modulator's `vital_metrics` and are unreachable this way (`maxim_senses.md` P-A).
- **`attach_backends(sensor_factory=...)` can attach a live root sensor**, but it changes only `read()`,
  not `vital_metrics` (`spec.py:1160-1189`). That is why the Minecraft path writes through `world_set_axis`.

### 1.7 Versioning

- **CC3 gives two paths** (`M/CLAUDE.md:105`; `M/docs/lessons/frozen-dataclass-forward-compat.md`):
  `SensorReading` takes path (a), with `extra`. `AffordanceSchema`, the drive specs, `CouplingSpec` and
  `ModulationSpec` are `SHAPE-FROZEN at 1.0`.
- **Appending a defaulted field to `AffordanceSchema` has happened three times.** Its docstring says
  "additive fields appended at the end stay non-breaking", and only a *required* field needs a major bump.
  The precedents are `target_effect` (PR #213), `always_active` and `speech_param` (#1261). The drive specs
  say any new field is a major bump.
- **`ModulatorResult` has no CC3 marker at all.** Its docstring is "Outcome of a modulator action."
  (`sem.py:68-78`). Its `metadata` dict works as a hatch in practice.
- **The only version number is `ENTITY_FORMAT_VERSION = "1.1"`, for Entity JSON** (`sem.py:26-30`). Maxim
  has no version for the SEM protocol itself. Overdrive's `_compat` mirror tracks it by comparing fields
  (`tests/test_sem_compat.py`).
- **Learning keys on names, exactly.** NAc's `cluster_reward_bias` matches on `tool_signature` exactly
  (`M/docs/plans/deferred/sem_motor_binding.md` decision 1). In effect, the names of SEM sensors and
  affordances are a persisted format: rename `crate_ignite` and an NPC's learned links are orphaned.

## 2. The options for state transitions

Scale, from `O/docs/architecture.md`: a 16×10×4 m tile is about 80 k cells at 0.2 m, 640 k at 0.1 m and
5.1 M at 0.05 m. An SEM entity is a Python object tree with per-sensor `read()` calls.

### (a) The world simulates; SEM only exposes. **Recommended.**

**Physics.** Use an enthalpy method per cell, folded into `heat.step`:
- Each cell holds volumetric enthalpy. Temperature and phase fraction both follow from it, using the
  material's `melt_c`, `boil_c` and latent heats **per unit volume**. A transition is a plateau in
  temperature while the latent energy is absorbed, never a "centre crosses a threshold" event. That is the
  resolution rule's own deposition principle.
- Each phase is its own material id (`ice`, `water`, `steam`; `steel` and `molten_steel`), or there is one
  phase-fraction array per cell.
- **Closed-form tests:** the plateau of a lumped block under constant power (`t = ρLV/P`, exact), and the 1-D
  Stefan problem (Neumann's similarity solution for the melt front, `s(t) = 2λ√(αt)`).
- **Cross-tier test:** "did the ice melt, did the pool boil dry" agrees at every rig.

**Motion of matter is the hard part**, and it is world work whatever SEM does. Stage it:
1. Phase in place: melt, freeze and boil with no flow.
2. Gas as diffusion plus sources. This is Phase 2's gas item. Without convection it pools and does not rise,
   which is a known gap.
3. Liquid flow as a volume-conserving cellular automaton, held to a conservation property test.

**SEM exposes** fractions and cause verbs (§3). It never decides an outcome.

| Criterion | Assessment |
|---|---|
| Determinism | Inside `World.advance` and seeded. Bit-identical. |
| Scale | numpy over every cell. Sensors stay reductions over masks, as now. |
| Resolution rule | Holds by construction: latent heat per unit volume, phase from cell-average enthalpy, sensors as volume fractions. |
| Bio-faithful (D1, `M/docs/experiments/DESIGN_REVIEW.md:33`) | The world *affords* the signal: water a body stands in is cells, and immersion is the overlap of a body box with liquid cells. Nothing is a synthetic number. |
| SEM's job | Doing its real job: tool generation, gating, prompt formatting and learning, all on a world-backed entity. |
| Cost | All the physics is new world code. Entity identity becomes a real problem once matter moves (§3, N1). The forward-model blind spot (§1.3) is exposed in full. |

### (b) SEM drives the transitions (drift and failure modes as world dynamics). **Reject.**

- **Wall clock.** Drift `dt` is host time (`body.py:293`) and failure modes stamp `time.time()`. A slow LLM
  turn would melt more ice. That breaks Overdrive's determinism rule and "only `World.advance` moves time".
  Maxim itself already moved memory onto experience time for exactly this reason
  (`M/src/maxim/runtime/experience_time.py`: "a slow model must not make the agent forget faster").
- **Wrong physics.** `drift_step` is a constant rate toward a set point. It has no energy budget, no
  latent plateau and no conservation. A failure mode is a step function on one scalar, so an entity would
  change phase as one block. That is the coarse rig's late-burn lag (integrity 0.55 vs 0.37) made total:
  outcome classes would depend on how regions were cut, not on physics.
- **Wrong scale.** Per-entity Python objects cannot stand in for millions of cells, and dynamics per
  region cannot conduct heat between regions.
- **It wouldn't run.** Scene entities are never ticked (§1.2). Making them tick needs a Maxim change whose
  only purpose is a physics engine.
- **Caricature (Bio-faithful lens).** Drives are interoceptive by design: what a body feels about itself. A
  puddle with a homeostatic "liquidness" drive caricatures the mechanism. It also puts world authority
  inside the agent framework, where every NPC process would hold a copy of the world's state.

### (c) Hybrid: SEM declares the phase diagram, the world executes it. **Only the world-data half.**

- **The useful half already exists in kind.** The material table declares and the world executes
  (`O/data/materials/core.yaml` declares `degrade_above_c` and the solver executes it). Adding `melt_c`,
  `boil_c`, `latent_*_j_m3` and `phase_of` is the same pattern. That *is* option (a).
- **SEM has no field for a phase diagram.** Putting one into Maxim (a spec type for transitions) would
  give an agent framework a physics schema it can't execute and that no other Maxim world needs. Under the
  "Push back on Maxim" rule this would be a request Maxim should refuse.
- **What an NPC can legitimately get from the diagram is knowledge**, through two routes:
  - Generated description text ("steel softens past 550 °C and melts near 1500 °C"). This is BF-2's
    description stopgap, generated from data so it cannot drift.
  - Learning from experience: the cerebellum and NAc seeing `heat` followed by `liquid_fraction` rising.
    This needs the delayed-measurement fix (P3).

## 3. Refinements

### 3a. What Overdrive can do now, inside the frozen types

- **N1. Three kinds of entity, named by `entity_type`** (a free string, so no Maxim change):
  - `structure` (today): an authored object, with a fixed mask of its authored cells. Its sensors report
    what has become of *its* matter: `solid_fraction`, `melted_fraction`, `integrity`, `temperature_*`.
  - `zone` (new): a fixed volume of space, such as a room, a pit or a vent. Its identity doesn't depend on
    where matter has gone. Sensors: `liquid_fraction`, `liquid_depth_m` (a volume divided by footprint, so
    it doesn't depend on the rig), `gas_<species>_fraction`, `smoke_fraction`, `temperature_mean`. Zones
    are the clean answer to "what is the entity when the ice became a puddle and then steam": the puddle is
    whatever liquid is in the zone.
  - `matter`, for tracked connected bodies ("the puddle", "the cloud"): **defer.** It needs deterministic
    component tracking with stable ids across splits and merges, and two coarse cells as a minimum size.
    It is a real design, not a sensor.
- **N2. Phase sensors are fractions, never labels.** Each is `<phase>_fraction` or `<species>_fraction`,
  with unit `ratio` and range `[0, 1]`, volume-weighted over the mask. A derived label such as
  "mostly liquid" can go in the description or in `extra`, and never feeds learning. Every sensor ships
  with a cross-tier test.
- **N3. Affordances are causes; sensors report effects.**
  - The verbs are `heat(power_w, radius_m)`, `cool`, `pour_onto`, `ignite`, `extinguish` and `vent`.
  - There is never a `melt` or `freeze` verb: an outcome as a command would let the LLM decree physics and
    would give the forward model nothing to learn.
  - Group verbs into modulators by what they act through (`structure`, `thermal`, `fluid`).
  - World entities declare no `target_effect`, and no `self_effect` until bodily costs arrive (Phase 5).
  - D1 check per hazard: each phase hazard (flooding, steam, toxic gas) needs a relieving act (leave, vent,
    drain) and a cue before the harm (`maxim_senses.md` §4).
- **N4. A refused target says what works.** The target rule stays. The refusal text names the call shape
  that works ("call `crate_ignite` directly, or `actor` with `target='crate'`"), and a test drives Maxim's
  real call shapes, including `OrchestratorActorTool`'s default target (delta round BF-1).
- **N5. `requires` reads the world.** Implement `check_affordance_requires` on world modulators against live
  cells (`pour` needs liquid present, `extinguish` needs a fire), so a world-state precondition is a
  `requires` block, a faithful world lesson, and not an error inside `execute`. Malformed calls keep being
  refused in `parse_action`. Overdrive must not dress them up as successes (P2 is the fix).
- **N6. World-owned body sensors, at the root.**
  - Immersion (head and torso liquid fraction), `wetness`, skin temperature and airway irritation, each a
    volume reduction around a body part at least two coarse cells across.
  - Written once per turn after `World.advance` with `world_set_axis(owner="overdrive_world")`, on sensors
    the body YAML declares as `modality: world` with `drift_rate: 0`. This is the Minecraft `oxygen` and
    `is_in_water` pattern, which needs no Maxim change.
  - Each part's thermal sensor needs P4. Until then, a root-level sensor per part (`arms_skin_c`) is a
    **named** stopgap, not a silent one: mark it `TEMPORARY(phase3)`.
- **N7. Version Overdrive's SEM vocabulary.**
  - Put the entity types, sensor names, units, ranges, affordance names and parameters in
    `data/sem/vocabulary.yaml` with a version.
  - Pin the generated tool surface (`generate_tools_for_entity` on a reference scene) as a golden fixture.
  - A rename needs a version bump and a migration note. NPC memories key on those names exactly, so the
    vocabulary is a save format in effect.
- **N8. Limits appear in descriptions** (BF-2), generated from `ActionLimits` and the material table.

### 3b. What needs Maxim: Phase 3 pushback proposals

| # | Proposal | Argues against | Evidence from Overdrive |
|---|---|---|---|
| **P1** | **Declare done-to vs done-by on the affordance:** an appended, defaulted `AffordanceSchema` field (for example `acts_on: "target" \| "self"`, default `"target"`, today's meaning). For `"self"` (patient-side): `OrchestratorActorTool` refuses with an executor-made call-error kind (never NAc), and `target_effect` resolves to the entity itself without the bread workaround. | The reading of `SHAPE-FROZEN` that rules out appended fields (contradicted by the class's own docstring and its three precedents), and `scene_actor_affordances.md`'s assumption that every scene affordance is agent-side (target defaults to the player). | Delta round BF-1: the actor tool's documented default is refused on every Overdrive region. `minecraft_bread.yaml` needs `target: {default: <itself>}` to express "done to me". The alternative, an entry in `Entity.metadata`, is the untyped hatch CC3 rejected for `AffordanceSchema` because typos stay silent. |
| **P2** | **Validate arguments in the executor, and add a call-error refusal kind** (the worktree roadmap's Phase 3 item 10). The amendment from delta-round BF-2: declare or exempt Maxim's own call keys (`target`), and let parameters declare a **range**, for example `(type, default, (lo, hi))` or a JSON schema, so limits are visible before the NPC fails. A misdirected target (P1) is the same kind. | TF2's "reached `tool.run`, therefore ran", for SEM modulator tools. It keeps #1315's rule that a tool body can't exempt itself. | The 33 probes in `O/tests/test_act_validation.py`. Review BF-1: a typo in JSON books a NEGATIVE with RPE about 0.5 on `tool:crate_strike`, and the link ignores state. |
| **P3** | **Measured credit for world-backed effects that arrive after the call.** A world-backed modulator returns a handle; the world reports a sensor transition after it steps (world time) through the D53 pattern (`measured_drive_transitions`, generalised to `measured_sensor_transitions`). The cerebellum learns from that report instead of `entity_state` read inside the call. This is the "act now, credit later" pending map that `sem_motor_binding.md` already says must exist before any dispatch that doesn't block. | The forward model's assumption that an effect is complete when `execute` returns (`tool_bridge.py:585-590, 884-890`). | `ignite` today, and every phase transition: a latent plateau lasts several turns by physics. Measured: `ignite` changes no cell until `World.advance`, so the cerebellum would learn a zero delta for every fire. |
| **P4** | **`world_set_axis` for modulator sub-sensors**, through the one resolver (`_resolve_sensor_slot`), with the same ownership refusal. | Its "root sensors only" scope (`audio_localization.py:727-733`). | Burns, scalds and frostbite are per part (`arms.thermal`, `head.thermal` on `infant_humanoid.yaml`). `maxim_senses.md` P-A. |
| **P5** | **Body drift, `FailureMode.last_fired` and `SpecSensor.read` timestamps on world time.** This joins #1361's `Embodiment.advance` and the design's item 15 (deterministic agents); it adds two clocks those lists don't name. | `evaluate_failures`' wall-clock `dt` (`body.py:267-298`). | Scalding or drowning onset measured in turns must not depend on LLM latency. Maxim already made this argument for memory (`experience_time.py`). |
| **P6** | **A SEM protocol version.** A `SEM_PROTOCOL_VERSION` constant ("1.0" now, a minor bump per appended defaulted field), the written rule "appended and defaulted is minor; a required field or a change of meaning is major", and a CC3 marker on `ModulatorResult`. Mirrors such as Overdrive's `_compat` can then assert a version range, not just compare fields. P1 and P2 would land as SEM 1.1. | The implicit status quo: three post-1.0 additions with no version recorded, and a `ModulatorResult` with no forward-compatibility path declared, against CC3's own rule. | `O/tests/test_sem_compat.py` turns red on any field change with no way to say "compatible minor". Overdrive's CLAUDE.md forbids adding fields Maxim lacks, so every SEM extension the game needs has to arrive as a Maxim version. |
| **P7** (low) | **Keep refusal detail for the observer, not the learner:** pass a failed `ModulatorResult.metadata` through to `ToolOutput.side_effects` under a fixed key, to the audit log and the LLM's carryover only. | The silent drop at `tool_bridge.py:582-583`. | Overdrive's refusals carry the parameter name, which is useful for the LLM to correct itself. Today it survives only as prose. This must not become an exemption from learning (#1315). |

**Not proposed, deliberately:**
- Categorical sensor values. Fractions are better physics and work today.
- Repurposing `CouplingSpec` or `ModulationSpec`. Maxim's R-4 reservation is right.
- A phase-diagram type in SEM (§2c).

## 4. My view: the cleanest division of labour for a game built around phases

1. **The world owns matter and all of its change.** That means enthalpy, phase, flow, diffusion, combustion
   and fuel, plus the exchange between each body and the cells (immersion, wetness, heat flux, burn and dose
   integrals), all in `World.advance`, seeded and deterministic. Every piece ships with a closed form and a
   cross-tier test. The phase diagram is material data. This is where most of the effort goes, and it is
   the part no protocol can do for you.
2. **The SEM bridge is a membrane, not a simulator.** It names and version-pins the vocabulary: entities
   (structures, zones, later matter), fraction sensors, cause verbs. It validates every call (the trust
   boundary), stamps world time, and writes world-owned body sensors once per turn. It must never hold state
   of its own: no `vital_metrics` on world entities, no `target_effect`.
3. **Maxim owns the NPC's side:** what each body feels (drives and failure modes on body sensors: scald,
   frostbite, drowning), what it predicts (the cerebellum, once P3 lets it see delayed effects), what it
   fears and remembers (NAc, Wire-4, the hippocampus), and which tools it is offered. Maxim never runs the
   world.

The honest summary for the owner: the protocol's value here is not that it "already measures the necessary
components". It measures nothing on its own: Overdrive's sensors measure cells. Its value is that whatever
the world exposes through it becomes something the NPC can act on, feel and learn from, unchanged. Phases are
also the best test so far of SEM's weakest assumption, that an action's effect is complete when the call
returns. Fixing that upstream (P3) is the most valuable refinement this work can give Maxim. P1, P2 and P6
are what make the protocol honest about who acts, what counts as a failure, and how it grows.
