# The SEM stimulus interface (design v1, 2026-11-20)

**Status:** DRAFT for a deep design review before any code, with Bio-faithful integration among its lenses. It rests
on seven research lenses, copied verbatim into `research/sem_stimuli/` and cited as L1–L7 (`1_receptors.md` …
`7_modularity.md`).

**Revisions read.** Overdrive `phase1/sem-stimulus` at `5ff1b7c`; Maxim by `git show` at local `origin/main`
**`043eab8f`** (2026-11-20, PR #1718), not fetched here. "Read here" marks claims this author read; others name
their lens.

**Tags.** External numbers: **V** primary source, **S** secondhand, **M** memory, **D** derivation or measurement.
Divergences: ANALOG, EARN, OPEN, as in `fire_model.md` §5.1.

## 0. The answer in one page

- **The line.** The world computes the physical stimulus *at the receptor's site*, tissue physics included (skin
  conduction, burn damage, head shadow). Maxim transduces it: thresholds, gain, adaptation, latency, pooling.
- **Frozen, the contract (§2–§6):** each row's name, unit, validity range, site set, receptor class, cadence and
  divergence tag; the site grammar; the `BodyFrame` and its wire form; the push path and failure rules; the replay
  digest; the version rules; the trust tests.
- **Replaceable, the laws (§2.4):** every model computing a value. A swap bumps the row's `derivation_version`, and
  never renames a row or changes its unit, sites or cadence.
- **Where it runs:** the sealed core, after every law: `simcore/core/stimuli/`, one module per stimulus, registered in
  one tuple. The skip-layer contract keeps adapters from reading cells, so nothing else can compute it.
- **How it arrives:** one `BodyFrame` per NPC per step, a table of `(stimulus, site, value)` at the step tick, sent
  over the worker channel and pushed into Maxim root sensors with `world_set_axis(owner=…)`. No frozen SEM type
  changes.
- **Replay and trust:** stimuli are derived, never logged, with a per-tick digest; the NPC builder gets one NPC's
  frame source and nothing else, and fourteen tests, each shown red on a planted leak, hold it.
- **Limits:** five Maxim gaps bound Phase 4's first NPC (§9). The largest owner decision: the `BodyFrame` as
  `AgentPort.step`'s `frame`, which edits the frozen agent half (O19; §10 D1).

## 1. The split, and the leak tests

**Receptors respond to tissue state at their own site.** C-fibre heat nociceptors fire at a fixed temperature at
receptor depth (40.4 ± 2.2 °C; depth 20–570 µm, mean ~0.2 mm) while the surface temperature at threshold rises with
heating rate (**V**, Tillman et al. 1995, L1 §2.1). Sent surface or air temperature, a receptor would have to fake a
rate-dependent threshold. So the world sends temperature at a declared depth.

| Side | Owns | Examples |
|---|---|---|
| World (core) | the stimulus at the site, and the tissue physics producing it | temperature at receptor depth; Henriques damage; pressure at each eardrum after head and pinna; gas in the inhaled volume; core temperature from a heat balance |
| Maxim | transduction | warm/cool coding and adaptation; nociceptor thresholds and sensitisation; spatial summation; pupil; cone projection; cochlear filtering; olfactory sorption; set points, drives, pain |

**The leak tests** (lesson 24, as corrected by `reviews/fire_model/bio_faithful.md` S4):
- **T1, instrument.** Could an instrument at that spot measure it without a nervous system? Then it is the world's.
- **T2, transduction.** Is it a threshold, gain, adaptation or latency? Then it is the receptor's.

**Boundary cases, ruled (L1 §10):**
- **Receptor depth** is anatomy the world computes at: the body declares depths per site. This corrects
  `fire_model.md` §5.1's hard-coded "~0.1 mm".
- **The pupil** is a neural effector: the world sends radiance, Maxim applies the pupil.
- **Breathing** is physiology: the agent reports its breathing state; the world integrates concentration over the
  inhaled volume.
- **Incident flux is not delivered.** No receptor senses W/m²; thermal and heat-pain receptors read tissue
  temperature (L1 §11). Flux is the tissue law's input and a lab quantity (§10 D6).

## 2. The stimulus schema

### 2.1 A row

A row is an identity for the life of the format (world_model F1).

| Field | Meaning |
|---|---|
| `name` | a physical quantity, never a verdict (`tissue_temperature`, never `hot`) |
| `unit` | from a closed vocabulary shared with the field registry |
| `valid` | **physical validity** (finite; T ≥ −273.15 °C); outside it the core raises |
| `receptor` | the receptor class fed, from a closed vocabulary (`thermo_skin`, `noci_heat`, …) |
| `site_set`, `cadence` | where (§3) and when (§2.3) it is evaluated |
| `tag` | none, ANALOG, EARN or OPEN, with the divergence named; closing it is a new row |
| `reads`, `derivation_version` | the fields its model may open; the law's version (F15) |

All but the last row are frozen. **The world declares no saturation range.** Saturation is transduction (T2): the
body YAML declares the sensor's `range`, and `world_set_axis` clamps to it (`audio_localization.py:748-761`, read
here). The world sends the physical value and meters how often the clamp bites.

### 2.2 The rows

**v1** rows are frozen now, for the first NPC body (Phase 4). The others fix what the Phase 2 light, sound and gas
designs must deliver (the long-term tracker asks this design to); each freezes when its field's design is accepted.

| Row | Quantity, unit | Site set | Cadence | Tag | Status |
|---|---|---|---|---|---|
| `tissue_temperature` | temperature at each declared depth, `celsius` | `skin` points × depths | tick | — | **v1** |
| `exposed_area_fraction` | share of a point's area uncovered (clothing, contact), ratio | `skin` points | tick | — | **v1** |
| `burned_area_fraction` | share of a region's area with Ω ≥ 1, ratio: tissue **state**, delivered as part integrity | `skin` regions | tick | EARN (OD-C10) | **v1** |
| `core_temperature` | from a body heat balance, `celsius` | `body` | tick | — | v1 if the body makes it world-owned (one owner, `fire_model.md` §5.1) |
| `contact_pressure`, `contact_shear`; `vibration_band_power` (> 40 Hz, ANALOG) | Pa over the contact patch | `skin` points; vibration at hands and face | tick | — | with items (Phase 4) |
| `joint_angle`, `_velocity`, `_torque` | rad, rad/s, N·m | `joints` | tick | ANALOG (no load on kinematic bodies) | bodies (5b) |
| `head_angular_velocity`, `specific_force` | rad/s; m/s², never "tilt"; impacts as peak and duration | `head` | tick | ANALOG above 5 Hz | bodies (5b) |
| `spectral_radiance`; `flicker_depth`, `_frequency` (ANALOG) | a few fixed bands per visible source, with angular position and solid angle, after line of sight | `eyes` | physics | — | light field; `luminance` (cd/m², ANALOG: V(λ) is a receptor property) is the stopgap |
| `sound_event` | arrival time (integer µs), octave-band level at each ear, onset rise time | `ears` | event | ANALOG | sound field |
| `inhaled_concentration`, `airway_irritant`; `arterial_gas` | mol/m³ or ppm per species per inhalation; PCO₂, PO₂ (kPa), pH | nostrils, mouth, eyes; `body` | breath; tick | — | gas zones; air hunger, never "low O₂" |

The receptor side of each row is L1 §11's table.

### 2.3 Cadence, and senses faster than the world

The world has two rates (`realtime_lanes_coop.md` §2.2): a 0.1 s tick, at which poses move, and a 0.5 s physics step,
at which fields change.

| Cadence | Evaluated | Nyquist limit | Used for |
|---|---|---|---|
| `tick` | at the NPC's pose at its step tick, against held fields | 5 Hz | tissue, vestibular, joints, contact |
| `physics` | from fields recomputed each physics step | 1 Hz | radiance, flicker descriptors |
| `event` | per event, stamped in integer µs within the tick | none | sound, impacts |
| `breath` | per inhalation the body reports | the breath | smell, airway |

**The game-engineering idea: sampling a fixed timestep.** Between physics steps the world *is* its last state, a
zero-order hold. Renderers interpolate between states; a sensor must not, since that invents states the simulation
never had. So the field is held and evaluated at the observer's *current* pose (L5 §2.2).

**Senses faster than the world** get physical summary statistics, never samples or perceptual words, each ANALOG
with a cross-tier test: vestibular thresholds are flat at 1–5 Hz (**V**, Valko et al. 2012), flicker fusion reaches
~50–90 Hz (**S**), flame puffing is 4.7 Hz at D = 0.1 m (**D** from ~1.5·D^−½, **S**). Interaural differences are
under 0.7 ms (**M**), so arrival times are integer µs; a tick would erase direction (L3 §1.5).

### 2.4 Frozen and replaceable, v1

| Row | Frozen | Replaceable law, today's choice |
|---|---|---|
| `tissue_temperature` | name, `celsius`, declared depths, `skin` points, `tick` | a 3-layer Pennes column per point (0.1 / 2 / 10 mm; 45 nodes), Torvi & Dale properties (**S**); later sweating, lateral conduction |
| `exposed_area_fraction` | name, ratio, sites | clothing as a column layer |
| `burned_area_fraction` | name, ratio, regions; Ω ≥ 1 at the basal layer as the definition | Henriques constants (P = 1.43×10⁷² s⁻¹, ΔE/R = 55,000 K, **S**), integrated inside the step |
| flux onto skin | internal, not delivered | analytic cylinder view factors; occlusion per (emitter, region group) on a fixed schedule; contact by a coupled column checked against effusivity |

**The tissue integrates every tick, for every body, whether or not its agent steps.** One 0.5 s step is 12.1% late on
pain at 20 kW/m² and 11% late on a 70 °C steel burn; 0.1 s is within 3% everywhere (L3 §1.1, **D**). One step per
physics step on the end pose would also average exposure across positions. The tissue step is a **truth constant,
never a rig field** (`substeps_per_physics_step`, `realtime_lanes_coop.md` §2.3), or a rig would change a burn (D20).

**Damage is per point.** A region half at 15 kW/m² and half at 5 first burns at 6.2 s; one column at the mean, at
11.8 s (**D**, L3 §1.1). A region's damage is its burned-area fraction (%TBSA, **M**).

## 3. The body

**The body grammar is engine code; body instances are game data** (`boundaries.md` §2.1, BF-15). A body declares site
sets in body-local metres, with no cells and no pose: `skin` (regions, each with quadrature points: position, normal,
area, depths), `eyes`, `ears` (±0.0875 m, **M**), `nostrils`, `mouth`, `head`, `joints`, `body`. L3 sizes `skin` at 18
regions and 58 points on a 1.85 m² adult (**D** on **M** anthropometry); a convergence test fixes the count (§11.2).
Each row names its site set, because thermal is coarse and summing while touch is fine only at hands and face (L1).

**Maxim's bodies are coarser and root-only (read here).**
- `base_humanoid` has four parts and `health: derived`, weighted head 0.3, torso 0.35, arms 0.15, legs 0.2
  (`_data/components/bodies/base_humanoid.yaml:57-62`).
- `world_set_axis` writes root sensors only (`audio_localization.py:727-762`); a dotted name returns `False`.
- `modality:` on a modulator sub-sensor raises (`embodiment/spec.py:556`), so a sub-sensor write couldn't join the
  world channel anyway.

**So the contract delivers per site, and a binding reduces.** The `BodyFrame` carries values at receptor resolution.
Each NPC's **binding** (§4.1) maps a row and a set of sites onto one Maxim root sensor with a declared reduction, the
area-weighted mean or the maximum. Both pass T1 (an instrument array reports them); which one a receptor would use is
transduction, so the binding names it as an ANALOG. The binding is replaceable, the per-site contract is not: when
OD-C10 lands, bindings move to sub-sensors and the `BodyFrame` doesn't change.

**Phase 4's first body** is a flat Overdrive body YAML (game data in Maxim's format): root sensors such as
`skin_hand_left_temp`, with `modality: world`, `drift_rate: 0` and the row's unit. This is `fire_model.md` §5.1's
root-sensor skin stopgap, **EARN** on OD-C10. Burn damage can't reach a derived `health` (`spec.py` C5, per L2 §2),
so per-part burns wait on OD-C10 too (§10 D8).

## 4. Delivery

### 4.1 The path

| Step | Where | What |
|---|---|---|
| 1 | core, simulation lane, after every law at tick T | `stimuli.run` evaluates the registry for each NPC due at T, at its pose at T, and builds its `BodyFrame` |
| 2 | host | encodes it into that NPC's `step` message: the worker codec's closed-schema JSON through the strict decoder (`npcs_and_sem.md` §6.6) |
| 3 | worker | the adapter decodes it, re-checks finiteness, and for each binding calls `world_set_axis(emb, sensor, value, owner="overdrive_world")` |
| 4 | worker | Maxim's embedded `step(agent, world_dt_us, frame)` runs; drives and pain read `vital_metrics` |

```python
@dataclass(frozen=True)                # simcore/core/stimuli/frame.py
class BodyFrame:
    schema_version: int                # STIMULUS_SCHEMA_VERSION
    npc_key: str                       # persisted NPC identity
    tick: int                          # host-owned header, stripped before Maxim
    basis_sequence: int                # the Frame it was derived from; host-owned
    stimulus_id: NDArray[int32]        # column-major, sorted by (stimulus_id, site_id)
    site_id: NDArray[int32]
    value: NDArray[float64]
    events: tuple[StimulusEvent, ...]  # since this NPC's last step, by (apply_us, id)

@dataclass(frozen=True)                # simcore/adapters/agents, checked at agent build
class Binding:
    stimulus: str
    sites: tuple[str, ...]
    reduction: Literal["area_mean", "max", "single"]
    sensor: str                        # a Maxim root sensor
```

Ids come from name maps in the agent's build handshake, as `welcome`'s recipe map does; no strings per frame (F2–F4).

**Push, not a pulled sensor.** L7 proposed a generic `ReceptorSensor` that Maxim pulls. But drives, pain and the
substrate read `Entity.vital_metrics`; an attached backend changes only what `SpecSensor.read()` returns
(`spec.py:820-823`, read here), so a pulled sensor gives the body two truths. Maxim's Minecraft backend pushes
(`embodiment/backends/minecraft.py`, read here).

### 4.2 Build-time checks

Maxim's units are free text (`hp`, `points` in `minecraft_player.yaml`), and pain runs in sensor units:
`min(1, (|v − set_point| − comfort_band) · pain_scale)` (`embodiment/sem.py:278-281`, read here). A unit mismatch is
a wrong pain, not a crash. So the adapter refuses to build an agent unless every binding's sensor:
- is a root sensor whose YAML `unit` equals the row's unit string exactly;
- says `drift_rate: 0` on any drive; the default is 0.001 per second (`spec.py:290`, read here);
- is in `live_world_set_sensors`, which only a modulator backend's `world_owned_sensors` fills
  (`runtime/bootstrap.py:552-561`, read here), so Overdrive ships one. `owner=` is "a SELF-DECLARATION for logs and
  review, not an ACL" (`audio_localization.py:720-721`): the guard is that nothing else in the worker writes;
- has a `range` containing the row's operating band, so the clamp is rare, not the transfer function.

### 4.3 Failure handling

- **`False` is an error, never a skip.** It fails the step, and the host ends the agent as `agent_failed(protocol)`
  (`npcs_and_sem.md` §6.6). A swallowed `False` is the fire review's "incinerated with full health".
- **NaN can't cross.** Maxim clamps NaN to the range's top (`max(lo, min(hi, nan))` is `hi`, checked here) and writes
  it raw without a range (`audio_localization.py:760-762`). So the core raises on any non-finite or invalid value, the
  strict decoder refuses `NaN` and `Infinity` (`boundaries.md` §9.1), and the worker re-checks, each proven by a
  planted NaN. There is no world-side clamp.
- **Pain needs an evaluation.** `world_set_axis` evaluates nothing; pain lands on the next pass that calls
  `evaluate_failures` (L2 §3), and a host-called step has none yet (§9 M4).

### 4.4 Cadence against the step and the lanes

- **Agents step** at an integer divisor of the tick with a per-actor phase, and get the frame computed at that tick,
  never "the latest" (`npcs_and_sem.md` §2.1, §7.3), so the dial can't change what an NPC feels. Events since the last
  step ride along; continuous rows are sampled at the step tick (§11.2 Q2).
- **Across lanes:** the simulation lane builds frames inside the step; each worker pushes its own inside `step`; the
  barrier holds tick T+1 until every agent is parked (`boundaries.md` §7.1). A park is a 50–200 µs round trip (**D**,
  `npcs_and_sem.md` §6.6), so only agents due this tick get a frame.

## 5. Replay, digest, versioning

**Replay reproduces the world, never the agents** (`boundaries.md` §6.2):
- **Not logged.** A `BodyFrame` is a pure function of logged inputs and world state.
- **Digested every tick:** `stimulus_digest = SHA-256(canonical(BodyFrame) for each stepping NPC, in npc_key order)`,
  over the bytes sent. It catches stimulus-path changes the world digest can't see.
- **In the header:** the registry with each row's `derivation_version`, the site tables and the tissue constants,
  through the one canonicaliser.
- **In the rerun manifest:** each NPC's bindings and body YAML digest. A binding mismatch refuses a tier-2 rerun; a
  registry mismatch refuses a tier-1 replay.
- **In the save:** tissue state (node temperatures and Ω per point, f64; clothing; dose), held occlusion with each
  NPC's schedule phase, pending sound events (L3 §6). Frames are recomputed on load, and their digest must match.
- **The test:** replay with `maxim` blocked, compare digests tick by tick, then plant a one-ulp change in a tissue
  constant and watch it go red on the first exposed tick. "What did the NPC sense at tick T?" is then tier 1.

**Version rules (F1, F15):**
1. **New meaning, new name.** A point value becoming an area mean is a new row; the old one stays while a fixture
   uses it.
2. **Better estimate, same meaning:** bump `derivation_version`; regenerate goldens in a commit that says so.
3. **Adding a row is non-breaking:** an NPC binds only what its body declares.
4. **Removing or renaming a row** bumps `STIMULUS_SCHEMA_VERSION`; readers refuse unknown versions loudly.
5. **A schema or derivation change is a body change for a learner** (L4 §6). An agent home records the registry
   digest it trained on; loading it under another is refused unless a migration says why that is safe.

**Reserve now,** in `phase1/sim-clock`'s log: `stimulus_digest` in the per-tick digest and the registry in the
header. Adding them later is a log-format bump.

## 6. Trust

### 6.1 Capabilities

- **The NPC builder gets only** `(npc_key, its body-frame source, its actor-bound intent outbox)`: never a
  `FrameSource`, an `Applier` or the world. It is the membrane's capability passing, narrowed to one body. No API takes
  two `npc_key`s, and only `simcore.core.stimuli` writes a `BodyFrame`.
- **The lab builder is separate.** `RegionInstrument` (`adapters/sem/bridge.py:48`) is an oracle by its own docstring;
  it moves under `tests/` (§10 D10). The registry is a different table from `frames.QUANTITIES`, with different types,
  so a region quantity can't be bound to a body.
- **The materials hole is smaller than L5 said.** `skip-layer` allows adapters to import `materials`, but
  `membrane-reads-frames` already forbids it to `simcore.adapters.sem` (`pyproject.toml`). The hole is real only for
  the coming `simcore.adapters.agents`.

### 6.2 The tests

Each is first shown red on a planted leak.

| # | Test | Catches |
|---|---|---|
| T1, T2 | ownership, as a review rule plus a grep gate: no drive or pain write from the world | a second heat path |
| T3 | **source swap** (L6): a lamp of equal radiance and flicker, a hot plate of equal flux, give equal stimuli | rows only fire excites |
| T4 | **occlusion** (L6): a hazard behind a wall or in a closed crate changes nothing until something physical crosses | omniscient reductions |
| T5 | **counterfactual material** (L6): materials alike in every reduced field, differing in a combustion constant; byte-identical streams before any thermal event | material constants as inputs |
| T6 | **probe** (L6; an experiment, not the gate): decoding material constants, occluded state or labels from pre-event frames above chance is a leak; future heat from present warmth is the signal | unnamed leaks |
| T7 | **text denylist** (L6) over every NPC-visible string: names, descriptions, affordances, refusals, errors, harness lines | telegraphed answers (Maxim Exp 38, 44) |
| T8 | **sensor-set invariance** (L6): sensors, units and ranges independent of the scene | hazard-detector sensors |
| T9 | **Δt and wall-time invariance** (L6): one history at different step sizes and LLM latencies, one stream | dial and latency leaks |
| T10 | **name stability** (F1): `QUANTITIES`, the registry and each NPC's sensor set pinned | silent meaning drift |
| T11 | **invariance** (L4 §7, L5 §5): vary entity ids and allocation order, material fields no receptor reads, render tier, another NPC's internals, a remote region; A's frame stays bit-identical. Negative control: a fire moved into A's view changes it | what T3–T5 miss |
| T12 | **sentinel taint scan** (L5): distinctive values in a ΔH_c, a region's interior maximum and NPC B's tissue; scan every byte to A's worker. Plant: bind B's site to A | verbatim copies, not arithmetic smuggling |
| T13 | **golden tool surface** on real pymaxim: no `ignite`, `extinguish`, `strike(energy_j)`, `*_temperature_max` | oracle acts (`fire_model.md` §5.4) |
| T14 | **registry disjointness**: no row name in `QUANTITIES`; every row has a receptor | a lab quantity on a body |

T11 is the strongest. The prior art's leak test is ablation (Habitat's PointNav winner fell to SPL 0.21 without
GPS+Compass, **S**); L4 found no automated non-leak test anywhere (**M**). Its fuzz reach is counted.

**Why leaks cost more than unearned knowledge.** A perfect privileged predictor takes the prediction error, so the
physical cue beside it is never learned (Kamin blocking, **S**, L6 §2.1). A faithful learner will block.

## 7. Placement and modularity

### 7.1 Modules

No existing module moves; the code's four layers (O24) hold.

| Piece | Owns | Module |
|---|---|---|
| Schema | rows, the closed unit and receptor vocabularies | `core/stimuli/schema.py` |
| Body grammar | site sets in body-local metres | `core/body/geometry.py` |
| Body store | pose and tissue state, with its own write window, as `FuelStore` has | `core/body/store.py` (5b) |
| Tissue law | skin column, Henriques, contact; in O34's law list | `core/body/tissue.py` |
| Site frame | each NPC's sites in world metres at one publication | `core/body/sites.py` |
| Models | one module per row family; return `(npc, site)` arrays, write nothing | `core/stimuli/models/<name>.py` |
| Registry, runner | the tuple; a `FieldReader` scoped to each model's `reads` | `core/stimuli/registry.py`, `run.py` |
| `BodyFrame` | one `stimuli` part of `Frame`, never a method per modality | `core/stimuli/frame.py` |
| Binding, push | build checks, `world_set_axis` | `adapters/agents/` (worker side) |

**Stimuli sit above the laws** (L7, against L5's `engine.laws.receptor`): they read every law's fields, and no law
knows who senses it. The tissue law *writes* tissue state, so it is a law; the stimulus model only reads it.

### 7.2 Registration

```python
# core/stimuli/registry.py: the one place a stimulus is named
from simcore.core.stimuli.models import burned_area, exposed_area, tissue_temperature
STIMULI: tuple[StimulusModel, ...] = (tissue_temperature.MODEL, exposed_area.MODEL, burned_area.MODEL)
```

- **A declaration registry, not a plugin framework.** `importlib` is banned from the core, so there is no discovery;
  the tuple's order is the run order, deterministic and digestible.
- **`prepare` then `kernel`** (O34's per-law split): `prepare` reconstructs fields over each site's patch in metres,
  never "a cell"; `kernel` is arithmetic, with a closed-form test and a B5 row.
- **N + M coupling, not N × M.** Fire and plasma append rows to a shared `radiant_emitters` field the flux model
  reads. A new phenomenon is a law and its rows; a new sense is a module, one line in `STIMULI`, a site set and data.

**The anti-pattern today:** a region quantity lives in `frames.QUANTITIES`, the `Frame.reading` chain and
`RegionInstrument.reading_schema`'s name test (`bridge.py:72-75`), so a fifth quantity silently gets the temperature
range.

### 7.3 Import contracts

| Contract | Rule |
|---|---|
| `stimuli-independent` | `independence` over `simcore.core.stimuli.models.*`; shared helpers go to geometry or a reductions module |
| `stimuli-read-only` | models import no `world`, `applier`, `intents`, `imagination`, `scene`, `heat`, `damage`, `body.store`, `body.tissue`, fuel or solid laws |
| `laws-blind-to-senses` | no law, store or geometry module imports `simcore.core.stimuli` |
| `membrane-reads-stimulus-frames` | adapters import `stimuli.schema` and `stimuli.frame` only |
| `agents-no-materials` | `simcore.adapters.agents` imports no `simcore.core.materials` (§6.1) |
| `maxim-through-adapters`, amended | the agents adapter's worker module joins `allowed_importers`, as `boundaries.md` §8.1 lists it |

`tests/test_tooling_config.py`'s `CORE_PUBLIC_SURFACE` and `MEMBRANE_SURFACE` gain `stimuli.schema` and
`stimuli.frame`. Each entry is proven by a planted import when its module is born; L7 left unverified that a wildcard
`independence` works on a one-child package.

### 7.4 Checks that fail the gate on drift (L7 §4)

- **Registry completeness:** every module under `models/` is in `STIMULI` once; every `reads` names a registered
  field; the contracts' module lists equal the packages that exist.
- **Honest reads:** a recording `FieldReader` asserts each model opened exactly its `reads`.
- **No central switch:** an AST lint fails on a registered name used as a literal in a comparison, case or key
  outside its own module, data file and schema.
- **Generated tests per row:** a closed form, a cross-tier test at 0.2/0.1/0.05 m and a validity check.
- **Order and purity:** writers before readers, stimuli last; stimuli write nothing (the writer scan); a golden
  vocabulary regenerated from `STIMULI`; an `__all__` allowlist on `core/stimuli/__init__.py`.

L7's inherited-surface and fan-in budgets are general tripwires, proposed as backlog rows.

## 8. Cost and interest management under determinism

**Per physics step, 48 points per NPC** (L3 §5, **D**, on an M2 at load 5.6–7.8, so pessimistic by an unknown factor):

| Kernel | 10 NPCs | 100 NPCs |
|---|---|---|
| skin, 45 nodes, 5 substeps | ~5 ms | ~46 ms |
| flame to points, analytic, 10 flames | ~0.2 ms | ~1.9 ms (**S**, `fire_model.md` §8.3) |
| occlusion, every point to one flame | ~82 ms | ~820 ms |
| occlusion, 9 rays per (flame, NPC), 10 flames, staggered N = 4 | ~4 ms | ~38 ms |

The skin is affordable; occlusion is the budget. Stimuli get their own B5 line, with work counters as the gate.

**The game-engineering idea: interest management.** In netcode it decides which entities each client is told about;
it may be lossy because it only changes what a client draws. Simulation level of detail changes what *happens*, and
games accept it because their NPCs are props. Here they aren't, so **replication interest** (what the client gets)
may cull freely, while **simulation interest** may change cost, never values: "multi-rate is allowed; thinning is
not" (`npcs_and_sem.md` §2.1). When the host can't keep up, the world dilates.

**Allowed, because bit-identical by construction** (L5 §6):
1. An NPC's stimuli are evaluated only at its step ticks; tissue and dose integrate every tick for every body, so a
   non-stepping NPC still burns.
2. Reuse when inputs are unchanged, keyed on (field sequences read, pose, tissue version), with a cached-equals-fresh
   test per kind of change.
3. Physical cutoffs, the same for everyone: a source below a declared SI floor at the receptor is dropped for every
   NPC, its energy ledgered; halving the floor must change values within tolerance.
4. Staggered occlusion (NPC i on steps ≡ i mod N), held results saved, N = 1 near emitters by a rule in metres;
   staleness measured and gated before any N > 1 (L3 didn't measure it).
5. Parallel evaluation, assembled and digested in `npc_key` order with fixed-order reductions.

**Forbidden:** any rule keyed on distance to the player or camera, the wall clock, host load or the dial. Games budget
perception by wall time (UE sight's 5 ms `MaxTimeSlicePerTick`, a 4.24 quote, **S**) and by player distance; both
make what an NPC feels depend on who watches. **Dormancy** (an NPC in another tile) needs its own design.

## 9. What Maxim must change

Each becomes a Phase 3 item in `docs/roadmap.md` when the owner rules, through Maxim's process. **Question:** an
existing plan owns it. **Pushback:** names a recorded decision. **New:** searched, not found.

| # | Need | Evidence at `origin/main` | Kind |
|---|---|---|---|
| M1 | World writes to sub-sensors, and `modality:` on them | root-only (`embodiment/audio_localization.py:727-762`); sub-sensor `modality:` raises (`embodiment/spec.py:556`) | **Question**, extending OD-C10, to TR23's "one kind-taking setter" (`docs/plans/thalamic_relay.md:2123`; GL3.B3) |
| M2 | A neutral point separate from the range | `rest:` is unparsed (L2 §2); the A4 neutral is "the literal normalized 0.5 (range midpoint)", and a set-point-aware variant "must not be improvised (plan decision D1)" (`similarity/encoder.py:572-584`). Skin rests near 33 °C, so its range must centre there, which also sets the clamp | **Pushback** against that decision D1 (`docs/limits/l11_sensor_dilution.md`, not read here), with the skin case |
| M3 | A closed unit vocabulary | free-text units (`minecraft_player.yaml`); pain in sensor units (`embodiment/sem.py:278-281`) | **Question** to OD-C9 |
| M4 | The embedded `step` evaluates the body after a push | nothing evaluates pain on a host-called step (L2 §3, §8) | **Question** to OD-A10 |
| M5 | Drift on world time | `now = time.time()`, `drift_dt = now - self._last_poll` (`embodiment/body.py:293-295`) | **Question** to `docs/plans/experience_clock_decay.md` S4 (PROPOSED); `drift_rate: 0` dodges it |
| M6 | The PainBus refractory on world time | 0.5 s per `(entity, failure_mode)` on `time.monotonic()` (`proprioception/pain_bus.py:196`), kept wall-clock "on purpose" as "motor/IO rate limits; hardware safety" (`experience_clock_decay.md` §(g)) | **Pushback** against §(g)'s row: at a 20× dial two burns 0.5 s apart in world time arrive 25 ms apart and merge, at 0.5× never; under the barrier wall time follows host load, so tier-2 reruns differ. Keep it for robots; let a stepped world supply the clock |
| M7 | The NAc causal window on world time | `temporal_window_seconds: float = 300.0` (`decisions/nac.py:439`) | **Question**: the planned `temporal_window_us` (per L2) |
| M8 | Reading stamps on the body clock | `timestamp=_time.time()` (`embodiment/spec.py:837`) | **Question**: OD-C2, filed |
| M9 | Burn as pain | GL2b "not started" (`docs/plans/autonomic_layer.md` status); `NociceptorSpec` thresholds are in sensor units (L2 §5), so `celsius` feeds its calibration; per-instance draws unknown (L6 §5) | **Question** to GL2b |
| M10 | Fear from burns and humanoid injury | allowlist `{"drive:health", "drive:oxygen"}` (`decisions/nac.py:425`); "a burn is **not** added to the fear set" (`autonomic_layer.md:233-234`); humanoids have no `drive:health` (L2) | **Pushback** against that invariant, with the first NPC fire scenario's failing run |
| M11 | Channels for vision, touch, smell | `DECLARABLE_MODALITY_TAGS` is `{AUDIO_TAG, WORLD_TAG}` (`embodiment/sensory_streams.py`) | **Question** to GL3's modality registry |
| M12 | Per-ear signals, not a world-set azimuth | `base_humanoid.yaml`'s `azimuth` | **OPEN**; question when sound lands |
| M13 | Credit tolerating a delay (a toxin's malaise) | none found by L2; `memory_2d2_retroactive_tagging.md` unchecked | **New**, Phase 2, after that check |

Every Maxim path in this table was read here except those marked "per L2" or "not read here".

**The wall-clock gap is the largest unmet assumption** (L2 §8). Drift, drive-pain latching, the refractory, the NAc
window and reading stamps run on Maxim's wall clock, and only drift and the window have plans. A world stepped faster
than real time makes drift undershoot, merges burns and widens credit; slower breaks them the other way.

## 10. Decisions for the owner

| # | Decision | Recommendation, and why |
|---|---|---|
| D1 | **The `BodyFrame` is what `AgentPort.step`'s `frame` means,** which edits the agent half frozen at v3.1 (O19) | Rule it as a definition, not a redesign: O13 already rules out the world frame (a `CellFrame` is 64–80 MB per tile at 0.1 m), and Maxim's review of the embeddable draft (O36) needs it. Fold it into `docs/maxim_upstream/embeddable_agent_DRAFT.md` |
| D2 | **The registry's form:** YAML (`world_v2.md` §2.5) or code (`boundaries.md` §9.1, "the in-code field registry is primary") | Code primary, with a generated committed artifact compared byte for byte: rows are bound to model modules, and data can't import code. Rule the field registry the same way at once |
| D3 | **Maxim's wall-clock time against world time,** and the route | File M6 as a pushback now; hold M5 and M7 as questions to #1361; a strict red gate in `phase1/agents` that merges two world-separated burns at 20× carries the evidence |
| D4 | **Lesson 11 ("agents need world time, injected") against time research §8.4 ("the NPC should never receive the world clock as such")** | No conflict under O4: the injected clock is *machinery* (drift, stamps, windows); cognition gets no time field. This contract carries none; `world_dt_us` reaches the machinery through `step`. Confirm, and reword lesson 11 to "machinery time" |
| D5 | **Waking a slowly stepping agent on a strong stimulus** without a designer event (L4 §5) | (a) no waking: onsets wait in `events`; (b) a world-side onset (dF/dt above an SI floor) forces a logged step, which risks becoming lesson 4's designer event; (c) every body steps each tick in its worker and only cognition is slow, at a round trip per tick. Recommend (a) for Phase 4 with a test measuring the lead time lost, and (c) as the target, decided with Maxim |
| D6 | Incident flux is internal, not delivered (§1) | Rule it; reword `fire_model.md` §5.1's table |
| D7 | What the LLM sees of numeric stimuli ("skin 47 °C" means something to an LLM; L6 §2.2) | Ask Maxim whether world-channel values reach the prompt; T7 covers names, not numbers |
| D8 | Phase 4's first body: the flat stopgap (EARN on OD-C10), or wait | The stopgap, every reduction in its ANALOG list |
| D9 | Phenomena under `simcore.core.laws.<name>` (so a `phenomena-independent` contract works, L7) or flat, as `fire_solid.md` §7 places fire | A ruling for O34's law list |
| D10 | The lab surface (`region_parts`, `RegionInstrument`) moves under `tests/` (delta1 NS3) | Before step 5 ships vocabulary v1, so Phase 4 can't pick up the oracle builder |

## 11. Open questions and risks

### 11.1 Conflicts between the reports

| Conflict | Resolution |
|---|---|
| Who declares a row's range: L7's `StimulusSpec.value_range` or Maxim's body YAML (L5) | Maxim's: saturation is transduction (§2.1) |
| A pulled `ReceptorSensor` (L7) or push (L2, L5) | Push: drives and pain read `vital_metrics` (§4.1) |
| Stimuli beside the laws (L5) or above them (L7) | Above (§7.1) |
| "Body frame" means values (L5) or site geometry (L7) | Values, per the owner's brief; geometry is the site frame |
| L3 publishes a body region's mean and maximum; L6 R6: no region-wide mean or max reaches an NPC | R6 is about world regions read from anywhere; body points are the receptor's own sites, and a binding's reduction is a named ANALOG (§3) |
| One region list (L3) or per-modality granularity (L1) | Per-modality site sets; L3's list is `skin` |
| Noise: the world's (L4), none (L5), physical variability only (L6) | Consistent once split: v1 adds none; receptor noise is Maxim's; physical variability only when earned, from keyed streams (`npcs_and_sem.md` §3.4) |

**Errors found in the lenses:** L5 places `RegionInstrument` at `bridge.py:715` (it is `:48`); L5's materials hole
is narrower than stated (§6.1); L2 puts TR23's setter at GL3.B1, while TR23's own row says GL3.B3.

### 11.2 Open questions

- **Q1.** The `skin` point count: add points until a region's burned fraction and maximum stop changing, limb
  edge-on to a flame (L3 named the test and didn't run it).
- **Q2.** Is a sample at the step tick enough for slow agents on thermal rows? A time reduction the receptor doesn't
  perform is omniscient (L6 §1.5), so the default is the sample.
- **Q3.** Face skins on every exposed face (6.2) before a hot wall can warm an NPC; a Known gap until then.
- **Q4.** One body shading another. **Q5.** Who owns ventilation rate for dose (COHb, FED).
- **Q6.** The `_backend` sensor path stays unused: `read()` returns the backend's value (`spec.py:822-823`) while
  drives read `vital_metrics`, a second truth.

### 11.3 Risks, said plainly

- **Phase 4's first NPC feels fire only as temperature on a flat body,** with no burn pain until GL2b and no fear until
  M10's invariant moves. Honest, and weaker than the fire design hoped.
- **The taint scan can't see an oracle smuggled through arithmetic;** review holds that line.
- **Occlusion cost is unmeasured on a real tile.**
- **M numbers to verify before `data/`:** thermoreceptor depths (Hensel 1951), ISO 13732-1, anthropometry and
  Lund–Browder shares, ear spacing, tidal volume.
- **Maxim was read at an unfetched local ref;** re-read each cited path at a fetched `origin/main` before filing.
