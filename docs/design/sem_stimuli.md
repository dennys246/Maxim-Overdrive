# The SEM stimulus interface (design v2, 2026-11-20)

**Status:** v2, folding the seven-lens review of v1 (`reviews/sem_stimuli/`; `fold.md` maps each finding, and the
reviewers set its status). The owner ruled D1–D12 on 2026-11-20 (§10). Research: `research/sem_stimuli/`, L1–L7.

**Read at:** Overdrive `97599b3`; Maxim by `git show` at local `origin/main` **`043eab8f`**, not fetched.

**Tags.** Numbers: **V** primary source, **S** secondhand, **M** memory, **D** derivation or measurement.
Divergences: ANALOG, EARN, OPEN, as in `fire_model.md` §5.1.

## 0. The answer in one page

- **The line.** The world computes the physical stimulus *at the receptor's site*, tissue physics included. Maxim
  transduces it: thresholds, gain, adaptation, latency, pooling.
- **Frozen, the contract:** row names, units, site sets, cadence; the site grammar; the `BodyFrame` and the wire's
  `BoundFrame`; the tick placement; failure and lifecycle rules; the digest; version rules; the trust gates.
- **Replaceable, the laws:** every model computing a value, versioned per row. A law swap touches only agents that
  bind that row, as a logged body change (§5).
- **Where it runs:** the sealed core, one body model: `core/body/` (store, irradiance, tissue) and `core/stimuli/`
  (read-only models), behind fail-closed import contracts (§7.3).
- **How it arrives (D5 (c)):** every body, every tick. After bodies move and before agents step, the core builds each
  NPC's `BodyFrame`, reduces it by the NPC's bindings into a `BoundFrame`, digests both and sends the bound values.
  The worker pushes them with `world_set_axis` and steps the body; only cognition is slow.
- **Trust:** the NPC builder gets one body's bound values and an actor-bound outbox; receipts are in scope; twelve
  gates and a probe hold it.
- **v1 is one row,** `tissue_temperature`. Burns reach Maxim through its damage path, not a sensor (§3.3).
- **Limits:** Phase 4's first NPC feels heat as temperature, without burn pain until GL2b or fear until M10 moves.
  The LLM sees each sensor's name, unit and value, so no learning claim rests on an LLM-primary NPC (§6.4).

## 1. The split, and the leak tests

**Receptors respond to tissue state at their own site.** C-fibre heat nociceptors fire at a fixed temperature at
receptor depth (40.4 ± 2.2 °C; depth 20–570 µm) while surface temperature at threshold rises with heating rate
(**V**, Tillman et al. 1995, L1 §2.1). So the world sends temperature at depths the body declares.

| Side | Owns | Examples |
|---|---|---|
| World (core) | the stimulus at the site, and the tissue physics producing it | temperature at receptor depth; Henriques damage; eardrum pressure; inhaled gas; core temperature |
| Maxim | transduction | warm/cool coding and adaptation; nociceptor thresholds; pooling; pupil; set points, drives, pain |

**The two leak tests** (lesson 24): the **instrument test** (could an instrument there measure it without a nervous
system? the world's) and the **transduction test** (a threshold, gain, adaptation, pooling or latency? the
receptor's).

**Ruled cases (L1 §10):** receptor depth is anatomy the body declares; the pupil is Maxim's; breathing, gaze and
posture are logged intents (§4.5); **incident flux is internal** (D6), since no receptor senses W/m². **So is
coverage:** v1's `exposed_area_fraction` is withdrawn, because no receptor reads it; clothing and partial contact
are tissue-law inputs (§2.4).

## 2. The stimulus schema

### 2.1 A row

| Field | Identity | Meaning |
|---|---|---|
| `name`, `unit` | yes | a physical quantity, never a verdict; a closed unit vocabulary shared with the field registry |
| `site_set`, `cadence` | yes | where (§3) and when (§2.3) |
| `valid` | yes | physical validity with a rounding policy, and an empty-patch rule |
| `receptors`, `pooling` | no | receptor classes it can feed (one temperature feeds warm, cool and C fibres) and the pooling per class (§3.2) |
| `tag` | no | ANALOG, EARN or OPEN as versioned metadata; closing one bumps `derivation_version`, never the name |
| `reads`, `derivation_version` | no | the fields its model opens; the law's version |

**The world declares no saturation range:** that is transduction. The Maxim body YAML declares `range`, and
`world_set_axis` clamps (`audio_localization.py:748-761`). The worker counts clamp bites and returns them in
`StepOutput`.

### 2.2 The rows

**v1** is frozen now for Phase 4's first body. Each other row freezes when its field's design is accepted.

| Row | Quantity, unit; site set | Cadence | Status |
|---|---|---|---|
| `tissue_temperature` | at each declared depth, `celsius`; `skin` points × depths | tick | **v1** |
| `core_temperature` | the core node (§3.1), `celsius`; `body` | tick | v1 when bound |
| `contact_pressure`, `_shear`; `vibration_band_power` (ANALOG) | Pa; `skin` | tick | with items |
| `joint_angle`, `_velocity`, `_torque`; `head_angular_velocity`, `specific_force` | SI; `joints`, `head` | tick | bodies (5b), ANALOG |
| `spectral_radiance`, `flicker_frequency` (ANALOG) | fixed bands, one melanopic, with angular position and solid angle, after line of sight, from **surface** temperatures only; `eyes` | tick, against held emitters | light field; `luminance` is the stopgap, **EARN** |
| `sound_event` | offset within the tick (integer µs), octave-band level per ear, onset rise time (source data, ANALOG); `ears` | event | sound field |
| `inhaled_concentration`, `airway_irritant`, `arterial_gas` | per species per breath; PCO₂, PO₂, pH | breath; tick | gas zones |

`flicker_depth` waits for a cited law. Interaural timing needs a spherical-head model: straight paths under-report
lateral ITD by about 25% (0.51 against 0.66 ms, **M**). Burns are not a row (§3.3).

### 2.3 Cadence

The world ticks at 0.1 s, when poses move, and steps physics at 0.5 s, when fields change (`realtime_lanes_coop.md`
§2.2). `tick` rows are evaluated at the tick's pose against fields held from the last physics step; `event` rows per
event, offset within the tick, floored to integer µs once; `breath` rows per logged breath record (§4.5).

**The game-engineering idea: sampling a fixed timestep.** Between physics steps the world *is* its last state, a
zero-order hold. Renderers interpolate; a sensor must not, since that invents states the simulation never had.
Senses faster than the world get physical summary statistics, each ANALOG: yaw thresholds are flat at 1–5 Hz (**V**,
Valko et al. 2012), and flame puffing (4.7 Hz at D = 0.1 m, **D**) outruns the 2 Hz physics rate.

### 2.4 Frozen and replaceable, v1

| Piece | Frozen | Replaceable law, today's choice |
|---|---|---|
| `tissue_temperature` | name, unit, declared depths (a node at each), `skin` points, `tick` | a 3-layer Pennes column per point (0.1 / 2 / 10 mm), Torvi & Dale properties (**S**) |
| incident flux | internal | `core/body/irradiance.py`: view factors by quadrature until an analytic form for arbitrary normals is measured against it; per-point visibility (D11) |
| contact | internal | one implicit system over the object's surface nodes and the skin at the tissue substep, its heat booked out of the object's inventory |
| partial contact, clothing | internal | a partly touching point gets contact and free sub-columns weighted by area; clothing is a column layer |
| damage | Ω ≥ 1 at the basal layer defines a burned point | Henriques, constants to trace to a primary source (§11.2) |

**Accuracy is stated in kelvin, not time to pain,** since the pain threshold is Maxim's. A fixed 0.1 s step isn't
enough: contact pain on 70 °C steel comes 20% late, and radiant error reaches 1.25 K basal at 80 kW/m², +87% on the
damage rate (**D**). So the tissue law takes **error-controlled substeps per point**, decided from world state
against a tolerance in K, counted as work. The tolerance is a **truth constant in the
header, never a rig field** (D20). Convergence is shown to 80 kW/m² and for contact before the law ships.

**Every body integrates every tick, whether or not its agent thinks:** a 0.5 s step is 12.1% late on pain at
20 kW/m² (L3 §1.1).

**Damage is per point.** A region half at 15 kW/m² and half at 5 first burns at 6.2 s; one column at the mean, at
11.8 s (**D**). The same rule forces per-point visibility: one shared visible fraction for a body half behind a
counter makes pain and burn 3× late, pain after the true burn (**D**). Hence D11 (a).

## 3. The body

### 3.1 One body model

**This design extends `tile_and_client.md` §2.1's body; it adds no second one.** The tile's lumped 245 kJ/K store is
the body's **core node** and sole producer of `core_temperature`. Skin columns are its surface layer, added before
Phase 4, with bases at the core node's temperature. One ledger line, `bodies`, books every exchange: radiant flux
absorbed by skin points, debited from the flame's unreceived share as tile §2.1 does; contact heat, debited from the
object; perfusion and metabolism as named reservoirs. Bodies don't shade walls or each other in v1 (ANALOG, Q4).
**`npc_key` is `body_key`.**

**The grammar is engine code; body instances are game data** (`boundaries.md` §2.1, BF-15, whose "receptor models"
this reads as the site grammar and tissue law, since transduction is Maxim's). A body declares site sets in
body-local metres: `skin` (regions of quadrature points: position, normal, area, depths), `eyes`, `ears`,
`nostrils`, `mouth`, `head`, `joints`, `body`. L3 sizes `skin` at 17 regions and 58 points on a 1.85 m² adult (**D**
on **M**); Q1 fixes the count.

### 3.2 Bindings and pooling

**Maxim's bodies are root-only (read here):** `world_set_axis` writes root sensors (`audio_localization.py:727-762`),
and `modality:` on a sub-sensor raises (`spec.py:556`). **So the contract delivers per site, and a binding reduces,
in the core.** Each binding maps one row and some of its sites onto one Maxim root sensor. The core reduces after
building the `BodyFrame`, in fixed order (`bincount` or ordered `fsum`), so reduced values are digested and only they
cross the wire.

**Pooling is fixed by receptor class, never chosen per binding:** `thermo_skin` pools by area mean, `noci_heat` by
maximum, and a mean bound to a pain path is refused. Otherwise a fingertip at 60 °C beside a palm at 33 °C reads
46 °C, and a burn can go unfelt. Pooling belongs in Maxim's receptor registry, so this is **EARN** on GL3.B1 and
OD-C10; then bindings move to sub-sensors and the `BodyFrame` doesn't change.

**Build checks:** the row exists; the sites lie in its site set and the body; `single` has one site; a mean never
spans depths; units are equal strings. No unit transform exists, so a `celsius` row can't bind Maxim's
`celsius_norm` drives (`infant_humanoid.yaml:43-49`); a transform would be transduction.

### 3.3 Phase 4's first body

A flat Overdrive body YAML in Maxim's format: root skin sensors such as `skin_hand_left_temp`, `modality: world`,
`drift_rate: 0`, unit `celsius`, **no `drive:` block** (a drive would make burns DRIVE-class discomfort, never
nociceptive, never in the fear set). It is `fire_model.md` §5.1's stopgap, retagged **EARN** on OD-C10.

- **Rest at the midpoint:** every body YAML passes Maxim's `scripts/lint_body_rest_neutral.py` rule (read here),
  replacing v1's M2.
- **That rule's cost:** the world channel's A4 gain weighs a reading by `(|v−0.5|·2)³` (`encoder.py:596`, read
  here). Centred at 33 °C over [−4, 70] °C, 45 °C weighs 0.034 and 60 °C 0.39 (**D**), so the first noxious band
  barely registers. The range is a transduction choice, measured as Exp 60's fix was (#726): **OPEN**.
- **Damage goes through Maxim's integrity model:** `SpecModulator.apply_damage(amount, "fire")` lowers sub-sensor
  integrity, and `health: derived` follows (`spec.py:1025`, `base_humanoid.yaml:108-120`, read here). Burned area per
  region becomes that delta, a body-state write by the adapter, not a sensor push. Whether a world-caused burn may
  call it, under which TR22/TR23 provenance, is M17; until then burns stay world state. Burned area is never bound to
  a sensor, which would be a damage gauge no nervous system has. ANALOG.

## 4. Delivery

### 4.1 The tick (D10, amended by insertion)

1. apply records; 2. move bodies; **3. tissue substeps** over the tick just ended, at this tick's pose, against held
fields; **4. build, reduce and digest every body's frames**; 5. agents step on tick T's `BoundFrame`; 6. physics, on
physics ticks; 7. outputs.

At a physics tick an agent sees the previous physics step's fields, as the hold implies. Physics at T doesn't
depend on agent outputs at T (intents apply at `observed_tick + L`, `npcs_and_sem.md` §9), so the simulation
lane may run step 6 while workers run step 5, joining before step 7. A gate replays one log with that overlap on and
off and requires identical digests. v1's "after every law" placement would reverse D10 and serialise the lanes.

### 4.2 The frames

```python
@dataclass(frozen=True)                # simcore/core/stimuli/frame.py
class BodyFrame:                       # per site; never leaves the host
    schema_version: int
    npc_key: str
    tick: int
    fields_sequence: int               # the published Frame its held fields came from
    stimulus_id: NDArray[int32]        # sorted by (stimulus_id, site_id); read-only
    site_id: NDArray[int32]
    value: NDArray[float64]
    events: tuple[StimulusEvent, ...]  # this tick only, capped

@dataclass(frozen=True)
class BoundFrame:                      # what crosses the channel
    schema_version: int
    registry_digest: bytes             # of the bound rows; checked against `welcome`
    npc_key: str
    tick: int
    value: NDArray[float64]            # one per binding, in binding order
    events: tuple[StimulusEvent, ...]
```

- **Beside `Frame`, never inside it:** a `BodyFrameFeed` keyed by `npc_key`, published each tick by the simulation
  lane. `FrameView` never reaches it; the host hands each channel one key. `boundaries.md` §4.2's cadence stands.
- **Deep frozen:** `__post_init__` refuses writable or non-owning arrays, as `CellFrame` does; a constructor-site scan
  holds "only `core.stimuli` builds one".
- **Ids** come from sorted names, recorded in the header; the handshake only checks them. The worker checks
  `npc_key` against its channel's actor and that `tick` rises, then drops both. `fields_sequence` replaces
  `basis_sequence`, which collided with `basis_seq`.
- **`StimulusEvent`** is `(offset_us, kind, site_id, local_id, value, caused_by)`, sorted by `(offset_us, kind rank,
  local_id)`. `local_id` counts within this NPC, revealing no world activity. `caused_by` is the NPC's own intent pid
  when it caused the event, else null, so B's identity never reaches A. One frame covers one tick, so offsets order
  correctly. v1 has no producer; a gate holds `events` empty until sound lands.

### 4.3 Bounds and failure

- **Events are capped per tick** within a byte budget derived from the body; overflow coalesces by `(kind, site)` into
  a count and the peak. The host checks the budget before sending, so an oversize frame is a logged host decision,
  never a worker refusal. An inert, absent or failed NPC accumulates nothing. Gates: a burst scene keeps the agent
  alive; a failed NPC's buffer stays empty for 10,000 ticks.
- **A non-finite or invalid value in the core is a world bug:** the server stops loudly with tick and NPC logged.
  Each row declares its empty-patch rule. The strict decoder refuses NaN, ±Infinity and `1e400`; the worker
  re-checks and refuses `bool` (`float(True)` is 1.0). Each is planted.
- **`False` from `world_set_axis` is an error.** All values are validated before any write, so there is no partial
  push; the host ends the agent as `agent_failed(protocol)` in tick T's merge.
- **Sends never block:** non-blocking, multiplexed with receives, inside the per-park ceiling. `BrokenPipeError`,
  `ConnectionResetError` and a short write become `agent_failed(crashed)`. Gates: a worker that parks and never
  reads lets the world advance after the ceiling; a killed worker leaves the server running.
- **Pain needs an evaluation** the embedded step must make (M4).

### 4.4 The worker

- **The push:** `world_set_axis(emb, sensor, value, owner="overdrive_world")` per binding, then the body step. Under
  TR23 the owner maps to the `experienced` kind.
- **`live_world_set_sensors` does more than guard writes:** it withholds drive credit on affordances whose
  `self_effect` touches those keys (`tool_bridge.py:548-560`). Only a modulator backend fills it
  (`bootstrap.py:552-561`), and that backend takes over its modulator's `execute` (`spec.py:1136-1139`). So
  Overdrive's backend hangs on one named modulator, and its `execute` *is* the outbox path: append an intent, return.
  The first body declares no `self_effect` on skin sensors; a build test proves credit flows through settle (M18).
- **One writer:** after Maxim builds, the worker checks that `threading.enumerate()` holds only its step thread and
  bound sensors have only Overdrive's owners (Maxim has a DoA poll thread and narrator writes). Planted red.

### 4.5 Agent outputs that feed stimuli, and the lifecycle

**Posture, gaze and breathing are intent kinds,** logged through `StepOutput` and applied next tick. An inert, failed
or absent agent breathes on the body's default schedule, so a crashed NPC is still poisoned. Replay with `maxim`
blocked reproduces the dose.

| Event | World side, frames | Log record |
|---|---|---|
| join | tissue at the core node's temperature; built and digested from the join tick | `join`, with body instance and bindings |
| not ready, or build refused | inert; built and digested, not sent | `agent_ready` at first park; `agent_failed(build)` naming the check |
| `agent_failed` | tissue goes on; built and digested, not sent | `agent_failed(reason)` |
| restart | build checks rerun, maps re-sent; sent from that tick | `agent_ready` |
| leave | tissue, events, visibility freed; leaves the set | `leave` |

Digest membership comes from logged records, never delivery success. Each row gets a crash-injection test.

## 5. Replay, digest, versioning

**Replay reproduces the world, never the agents** (`boundaries.md` §6.2). Frames are a pure function of logged inputs
and world state, so they aren't logged.

- **The digest:** per tick, SHA-256 over every body's canonical `BodyFrame` and `BoundFrame` values, through
  `checks`' canonicaliser, length-prefixed, in `npc_key` order, chained across ticks. Codec bytes stay out of it, and
  deltas are ruled out for these frames. The log stores the chain at log v0's digest interval; bisection finds the
  first bad tick. A codec round trip plus committed goldens guard the wire form.
- **The header** (tier-1 content): registry rows by sorted name with unit, site set and `derivation_version`; id
  maps; truth constants (tissue tolerance, visibility refresh and clustering bounds, cutoff floors). Body instances
  and binding tables ride their `join` records.
- **The save:** tissue, visibility and pending events; frames are recomputed on load and must match the digest.
- **The test:** in the harness, bypass the header check and plant below it, in the law's code: one ulp on the surface
  conductance, which moves `tissue_temperature` on the first exposed tick. A second plant reverses binding order with
  the world unchanged. Both go red on the stimulus digest at the first affected tick.
- **Tier 2 isn't bit-identical on real Maxim** until M6 and M8 land: wall time follows host load under the barrier.

**Version rules (F1, F15):** (1) a new meaning gets a new name; (2) a better estimate bumps that row's
`derivation_version`, with goldens regenerated in a commit that says so; (3) adding a row is non-breaking, since no
NPC binds it yet; (4) removing or renaming a row bumps `STIMULUS_SCHEMA_VERSION`, and readers refuse unknown versions;
(5) **an agent home records only its bound rows,** `(name, unit, site set, derivation_version)`. A change to one is a
named, logged body change, refused unless the load names it (D13). Replay refuses only on a changed row some NPC in
the log bound.

**Reserve now** in `phase1/sim-clock`'s log: the digest chain, the header slots, and the `join`, `leave`,
`agent_ready` and `agent_failed` records.

## 6. Trust

### 6.1 Capabilities, and what this supersedes

The NPC builder gets only `(npc_key, its BoundFrame source, its actor-bound outbox)`. This supersedes, by name:
- `boundaries.md` §7.1, `npcs_and_sem.md` §6.5: the membrane factory took a frame source;
- `boundaries.md` §4.3, `npcs_and_sem.md` §7.2–§7.3: a frame pinned per agent (a worker can't pin a host frame);
- `tile_and_client.md` §4: the pinned actor table leaves the NPC path; other actors reach an NPC only as stimuli.

**D10 splits `region_parts`:** it builds the instruments and the `StructureModulator`s the shipped `to_maxim_entity`
uses. The modulators stay in the membrane; the instrument builder becomes a lab builder. The worker-side environment
entity (names, affordance text carrying `ActionLimits`, refusals) is designed in `phase1/agents` under T8 and T13.

### 6.2 Receipts and refusals

**The receipt path is a stimulus path.** Today it carries a strike's `absorbed_j` and `destroyed_volume_m3`
(material-dependent), "nothing is burning on the {region}" (a fire oracle), existence oracles by name, and footprint
bounds by bisection over `point_m`. This supersedes `npcs_and_sem.md` §6.6's "measured effect" projection:
- **A receipt is a closed vocabulary:** applied, or a refusal kind (`malformed`, `out_of_reach`, `not_perceived`,
  `limit`). Unknown, destroyed and unperceived targets all get `not_perceived`. No measured value, name or fact.
- **The effect arrives as stimuli** in the next tick's frame.
- **Gates:** T4, T5 and T11 run with intents issued over receipt bytes, T12 plants a sentinel in `absorbed_j`, and a
  per-act test checks the act's effect reaches the actor's next frame (L6 R8).

Lesson 23's post-`execute` cascade read now sees the pre-act frame; it is logging, never credit, which settle books.

### 6.3 The gates

Each is first shown red on a planted leak.

| # | Gate | Catches |
|---|---|---|
| # | Gate |
|---|---|
| T1 | ownership: no drive or pain write from the world (grep gate plus a review rule) |
| T3 | source swap: a lamp of equal radiance and a plate of equal flux give equal stimuli |
| T4 | occlusion: a hazard behind a wall changes nothing until something physical crosses |
| T5 | a material differing only in a combustion constant gives identical streams before any thermal event |
| T6 | probe (an experiment): decoding constants or occluded state from pre-event frames above chance |
| T7 | text denylist over every NPC-visible string, receipts included |
| T8 | sensors, units and ranges independent of the scene |
| T9 | frames byte-identical every tick at cognition divisors 1–50 (plant: a model reading `dt_ticks`); a worker half compares writes and pain events at 1×, 20× and two seeded wall-delay schedules, strict red until M6 and M8 |
| T10 | `QUANTITIES`, the registry and each sensor set pinned |
| T11 | vary entity ids, allocation order, unread material fields, render tier, B's agent state, B joining out of sight, a remote region: A's frames and tissue stay bit-identical. B's body affects A only physically, in sight. Plant: a batched `@` |
| T12 | sentinel scan of every byte to A's worker; plants: A built from B's store, a channel misroute |
| T13 | golden tool surface on real pymaxim |
| T14 | no row in `QUANTITIES`; every row has receptors |

T11 is the strongest, with its fuzz reach counted. A remote fire raising host load still changes A's Maxim dynamics
through the wall clock, a known leak until D3 lands. Another gate measures the cue's lead time before harm (L6 R1),
radiant and contact.

### 6.4 What the LLM sees, and what may be claimed

**D7, answered (read here):** Maxim generates a `SensorReadTool` per sensor ("Returns value in {sensor.unit}",
returning `value` and `unit`) and an `EntitySenseTool` naming every sensor (`tool_bridge.py:295-321`, `:1002-1020`,
`:1068-1082`). So the LLM reads "skin_hand_left_temp … celsius … 47.3", and 47 °C means "burning" to a language
model. No leak test removes that prior. So:
- **No learning claim from an LLM-primary NPC alone** (L6 R15, as `fire_model.md` §7): a claim needs a substrate-side
  measure, a physical counter-prior or between-NPC dose–response, pre-registered in a Maxim harness.
- **Ask whether an embedded roster can withhold world-channel read tools** (M19).

**Blocking.** A privileged predictor takes the prediction error, so the physical cue beside it is never learned
(Kamin, **S**): leaks cost more than unearned knowledge, for a faithful learner (today NAc's ΣV is OPEN).

## 7. Placement and modularity

### 7.1 Modules

| Piece | Owns | Module |
|---|---|---|
| Schema | rows; unit, receptor, pooling vocabularies; the `StimulusModel` protocol | `core/stimuli/schema.py` |
| Body grammar, site frame | site sets in body metres; sites in world metres at a tick | `core/body/geometry.py`, `sites.py` |
| Body store | pose, core node, tissue and visibility state, own write window | `core/body/store.py` (5b) |
| Irradiance law | flux per point: view factors, visibility and its refresh, contact coupling | `core/body/irradiance.py` |
| Tissue law | columns, sub-columns, substeps, Henriques | `core/body/tissue.py` |
| Models | one per row family; read tissue and held fields; write nothing | `core/stimuli/models/<name>.py` |
| Registry, runner | the tuple; the runner keeps only order and capability handout | `registry.py`, `run.py` |
| Frames | both frames, reduction, canonical values | `core/stimuli/frame.py` |
| Binding check, push | build checks, `world_set_axis` | `adapters/agents/` (worker) |

**Stimuli sit above the laws** (L7): they read every law's fields, and no law knows who senses it. Flux, visibility
and contact run every tick for every body in the irradiance law, so tissue input never depends on an agent's cadence.
Cutoffs are per-row law parameters; there's no due-set, since every body is evaluated each tick.

**Step 5a's composition note gets three seams:** a per-tick law slot beside the physics list; the two-rate contact
exchange, written to both sides and ledgered antisymmetrically (`world_v2.md` §2.6); and two containers, per-body
point state and a multi-writer emitter table (`radiant_emitters`).

### 7.2 Registration

```python
# core/stimuli/registry.py: the one place a stimulus is named
from simcore.core.stimuli.models import tissue_temperature
STIMULI: tuple[StimulusModel, ...] = (tissue_temperature.MODEL,)
```

- **A declaration registry, not a plugin framework:** `importlib` is banned from the core. Models are independent,
  so digests and ids sort by name, not tuple order.
- **`prepare` then `kernel`** (`docs/plans/checklists.md:103`): `prepare` reconstructs fields over each site's patch
  in metres; `kernel` is arithmetic with a closed-form test and a B5 row.
- **Batch invariance is contract.** Each body's values are computed at a shape fixed by its own body: Accelerate's
  dgemv moved 19 of one NPC's 48 values by 1 ulp once 9 others were stacked with it (**D**). A lint bans BLAS
  matrix-vector calls and `einsum` over a batch axis in `core/stimuli` and `core/body`; the per-NPC loop costs 0.13 ms
  against 0.04 ms at 100 NPCs.
- **N + M coupling, not N × M:** fire and plasma append to `radiant_emitters`; a new sense is a module, one line in
  `STIMULI`, a site set and data.

### 7.3 Import contracts, fail-closed

Denylists fail open (a law born under a new name escapes them), as `pyproject.toml`'s note before
`maxim-through-adapters` already says. The forms were checked on the pinned import-linter 2.6 (Architecture review).

| Contract | Rule |
|---|---|
| `stimuli-protected` | `protected` on `simcore.core.stimuli`: only the simulation composition, and adapters' `schema`/`frame` imports |
| `body-protected` | `protected` on `simcore.core.body`: the composition and `core.stimuli` |
| models allowlist | a grimp test: models import only `stimuli.schema`, the field-reader type, `body.geometry`, `body.sites`, `checks` |
| `stimuli-independent` | `independence` over `simcore.core.stimuli.models.*` |
| `agents-reads-body-frames` | `simcore.adapters.agents` imports no `world`, `applier`, `frames`, `grid`, `materials`, `core.body` or `adapters.sem.bridge` |
| `maxim-through-adapters` | the agents worker module joins `allowed_importers`, and its test changes with it |

v1 said `skip-layer` keeps adapters from cells; it doesn't (it allows `world`), hence the agents contract. `_core_modules` in `tests/test_tooling_config.py` becomes recursive in the
PR that creates the first subpackage, and every new module, `__init__` included, is classified. Adapters get site
names as handshake data. Each contract gets a `PLANTED` row.

### 7.4 Checks that fail the gate on drift

- **Completeness:** every module under `models/` is in `STIMULI` once; every `reads` names a registered field.
- **Honest reads:** a recording `FieldReader` asserts each model opened exactly its `reads`; the allowlist makes
  direct `grid` access an import failure.
- **No central switch:** an AST lint fails on a registered name used as a literal comparison or key outside its
  module, schema, data, the generated vocabulary, `adapters/agents` and `tests/`.
- **Cross-tier tests per coupling, not per row.** A body near a burner runs identically on every grid, so a per-row
  test can't fail. The grid enters through occlusion by cells, face emission, face contact and zone gas. Each
  coupling gets offsets of 0, dx/3 and 2dx/3, band gates and a wall edge across the view, shown red by a planted
  cell-centre occlusion or cell-mean face temperature. A half-shaded body's burned area matches per-point rays.
- **Purity:** stimuli write nothing (the writer scan); a golden vocabulary regenerated from `STIMULI`; an `__all__`
  allowlist on `core/stimuli/__init__.py`.

## 8. Cost and budget

**The budget (D12): 10 NPCs near a fire, gated by deterministic work counters** (column substeps, ray samples,
frames, bytes, parks per tick), which replay exactly; a wall-time p99 meter is advisory. Target: stimuli plus delivery under 10% of the physics step's wall time at 10 NPCs.

**Per world second** (2 physics steps, 10 ticks; 58 points; L3's kernels at load 5.6–7.8, 2.2–2.7× pessimistic per
the Executor's rerun):

| | 10 NPCs | 100 NPCs |
|---|---|---|
| skin, and quadrature flux every tick | ~50 ms | ~0.5 s |
| per-point visibility, one flame, per physics step | ~65–165 ms | ~0.65–1.6 s |
| delivery every tick: encode, digest, park round trip | ~15–30 ms | ~150–300 ms |

**At 10 NPCs that is ~130–245 ms against a target of ~140 ms** (physics runs about 1.4 s per world second).
Per-point visibility dominates and must be cut without changing outcomes. The
sanctioned cut: points share a ray set only while their angular spread seen from the emitter stays below a declared
bound, and split otherwise. Visibility refreshes each physics step and whenever a body's sites move more than a
declared distance, or topology or emitters change, from world state, never by NPC index. Both bounds are header
truth constants, and the cost is measured before the law ships. 100 NPCs at a fire forecasts 1.7–2.1 wall seconds
per world second; the world dilates.

**The game-engineering idea: interest management.** Netcode decides which entities each client hears about; it may
be lossy, since it changes only what a client draws. Simulation level of detail changes what *happens*, which games
accept because NPCs are props. Ours aren't: **replication interest** may cull, **simulation interest** may change
cost, never values (`npcs_and_sem.md` §2.1).

**Allowed, deterministic and independent of the observer** (they change values, so they're law parameters with
tolerance tests): (1) physical cutoffs, the same for everyone, energy ledgered, a halved floor changing values within
tolerance; (2) the refresh rule above, staleness measured against every-tick refresh first; (3) a fork-join inside
`Simulation.step` reading only published read-only arrays, joined before any window opens, a task's exception being a
simulation-lane exception; serial until T11's batch plant exists.

**Forbidden:** any rule keyed on player or camera distance, wall clock, host load or the dial. Games budget perception
by wall time (UE sight's 5 ms `MaxTimeSlicePerTick`, **S**) and player distance, so what an NPC feels depends on who
watches. Dormancy needs its own design. Delivery, the worker push and event-buffer depth each get a B5 row.

## 9. What Maxim must change

Each becomes a Phase 3 item through Maxim's process. **Question:** a plan owns it.
**Pushback:** names a recorded decision. **New:** searched, not found.

| # | Need; evidence at `origin/main` | Kind |
|---|---|---|
| M1 (MP-5) | sub-sensor writes with `modality:` (`audio_localization.py:727-762`; `spec.py:556`) | **Question**, extending OD-C10, to TR23's setter (`thalamic_relay.md:2123`, GL3.B3) |
| M2 | *withdrawn:* `setpoint_aware_neutral.md` is DO-NOT-BUILD; a static set point "is numerically identical to the range declaration" (`archive/world_channel_weighting.md:222`), which `lint_body_rest_neutral.py` enforces | replaced by §3.3 |
| M4 | the embedded `step` evaluates the body after a push (L2 §3) | **New**, nearest home OD-A10 |
| M5–M8 | drift, PainBus refractory, NAc window, reading stamps on world time (`body.py:293-295`, `pain_bus.py:196`, `nac.py:439`, `spec.py:837`) | **Citations** of OD-A1, OD-A2 and `world_clock_release_DRAFT.md` §3.5, §4, which already argues §(g)'s PainBus row |
| M9 (MP-2a, 2b) | burn as pain, two fibre classes, per-NPC receptor draws (not found in `thalamic_relay.md`, `autonomic_layer.md`) | **Question** to GL2b, GL3 |
| M10 (MP-1) | fear from burns: `nac.py:425`'s allowlist; "a burn is **not** added" (`autonomic_layer.md:233-234`) | **Pushback**, with the first NPC fire scenario's failing run once it exists |
| M11 | vision, touch, smell channels (`sensory_streams.py:68`) | **Question** to GL3 |
| M12 | per-ear signals, not a world-set azimuth | **EARN**; when sound lands |
| M13 | credit tolerating a delay; `memory_2d2_retroactive_tagging.md` is retention, not credit | **New**, Phase 2 |
| M14 | `deferred/sem_environmental_proximity_sensing.md` reads a declared `heat_output`; its revive trigger is this design's first NPC | **Pushback** against its mechanism (T3, T5) |
| M15 | thermal adaptation has no owner (`deferred/adaptive_nociception.md` covers nociceptors) | **Question** to the salience-layer route; OPEN |
| M16 | a body step without cognition, each tick (D5 (c)) | **Question** to OD-A10, `embeddable_agent_DRAFT.md` |
| M17 | a world-caused burn through `apply_damage` (`spec.py:1025`) | **Question** to GL2b, TR22 |
| M18 | the modulator-backend path in the embedded build (`bootstrap.py:538-561`) | **Question** to OD-A10 |
| M19 | withholding world-channel read tools (`tool_bridge.py:1068-1082`) | **Question** to OD-A11 |

v1's M3 is dropped (§3.2's check holds it). **The wall-clock gap is the largest unmet assumption** (L2 §8).

## 10. Decisions

**Ruled by the owner, 2026-11-20, as recommended:**
- **D1:** the port's `frame` is the `BoundFrame` source; the adapter consumes it, and Maxim's `step(…, frame)`
  carries nothing of it, so there is one route. Folded into `embeddable_agent_DRAFT.md` under O36.
- **D2:** the registry is code primary, with a generated artifact compared byte for byte; the field registry too.
- **D3:** the wall-clock pushback is filed as `world_clock_release_DRAFT.md`'s §4 row, with the 20× merge added; the
  gate *will* carry the evidence once it lands, faking `time.monotonic`.
- **D4:** no conflict under O4 and OD-A2: the injected clock is machinery; cognition gets no time field. Lesson 11
  reworded.
- **D5:** (c), every body steps each tick; only cognition is slow.
- **D6:** incident flux is internal; `fire_model.md` §5.1 and lesson 24 reworded.
- **D7:** answered (§6.4). **D8:** the flat stopgap body. **D9:** for O34's law list; this design needs only
  `core/body/`. **D10:** split `region_parts` before step 5's vocabulary v1 (§6.1).
- **D11:** (a), per-point visibility, clustered within a bound and refreshed on motion (§8).
- **D12:** 10 NPCs near a fire with a work-counter gate; 100 is a later target.

**Open, D13:** on a bound row's law change, refuse an agent home unless the load names it (recommended), or load
with a logged warning.

## 11. Steps, open questions and risks

### 11.1 Where the work lands

| Step | Work |
|---|---|
| 5a (sim-clock) | §5's reservations; §7.1's seams; `stimuli/schema.py`, `frame.py`; recursive `_core_modules` |
| 5b (bodies) | `body/geometry.py`, `store.py`, `sites.py`; the core node; the body-instance format (strict loader, version, gate row, fixtures) |
| `phase1/agents` | `adapters/agents` and its contracts; the binding format and loader; the `BoundFrame` codec and goldens; the environment entity; D10 |
| before Phase 4 | the tissue and irradiance laws, `tissue_temperature`, §6.3's gates, the first body |

`foundations_plan.md` still owns order.

### 11.2 Open questions

- **Q1.** The `skin` point count, a limb edge-on to a flame; L3's buttocks share disagrees with `geom.py`.
- **Q3.** Face skins before a hot wall warms an NPC or glows in view; radiance from cell means is a strict red gate.
- **Q4.** Bodies shading each other, and self-shadowing: a Known gap with a number when irradiance lands.
- **Q5.** Ventilation rate's owner. **Q6.** L1 §9.1's skin feedforward.
- **Before `data/`:** trace Henriques' constants to a primary source (none found; Weaver–Stoll's give about 0.9 per
  K below 50 °C, against 0.5); grade Ω = 1 against two published second-degree times; record Jasiński's miss as a
  Known gap; cite the contact conductance (it moves steel pain 4.5×); anchor on ISO 13732-1 Table A.1 (**S**, via
  CENELEC Guide 29) in its held-surface configuration.

### 11.3 Risks, said plainly

- **The first NPC feels fire only as temperature on a flat body,** weakly salient under the A4 gain, with no burn
  pain until GL2b and no fear until M10 moves.
- **Per-point visibility may not fit the 10-NPC budget** until clustering is measured.
- **D5 (c) needs M16.** If an embedded body can't step without cognition, every tick is a full step, or sub-tick
  contacts go unfelt, T9 turns strict red and a Known gap is recorded.
- **The taint scan can't see an oracle smuggled through arithmetic;** review holds that.
- **M numbers to verify before `data/`:** receptor depths, anthropometry, ear spacing, tidal volume. Re-read each
  Maxim path at a fetched `origin/main` before filing.
