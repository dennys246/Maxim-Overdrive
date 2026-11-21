# The SEM stimulus interface (design v3, 2026-11-21)

**Status:** v3, folding delta round 1 (`reviews/sem_stimuli/delta1/`; its `fold.md` maps each finding, and the
reviewers set its status). Round 1's table is `reviews/sem_stimuli/fold.md`. The owner ruled D1–D14 (§10); D12 is
provisional. Research: `research/sem_stimuli/`, L1–L7.

**Read at:** Overdrive `4b47d5b`; Maxim by `git show` at local `origin/main` **`043eab8f`**, not fetched. **Tags:**
**V** primary source, **S** secondhand, **M** memory, **D** derivation or measurement; ANALOG, EARN, OPEN as in
`fire_model.md` §5.1.

## 0. The answer in one page

- **The line.** The world computes the physical stimulus *at the receptor's site*, tissue physics included. Maxim
  transduces it: thresholds, gain, adaptation, latency, pooling.
- **Frozen, the contract:** rows, units, site sets, cadence; the site grammar; `BodyFrame`, `BoundFrame`, `Binding`;
  the tick placement; failure and lifecycle rules; digest lanes; version rules; receipt kinds; the gates.
- **Replaceable, the laws:** every model, versioned per row; a swap touches only agents binding that row, and only its
  digest lane (§5). They run in the sealed core, `core/body/` and `core/stimuli/`, behind fail-closed contracts.
- **How it arrives:** after bodies move and before agents step, the core builds each NPC's `BodyFrame`, reduces it by
  validated bindings into a `BoundFrame`, and digests both. The contract is D5 (c), every body each tick; until a body
  has a pain path, delivery and the Maxim body step run at the cognition rate (D14, §4.6).
- **v1 is one row,** `tissue_temperature`. Burns reach Maxim through its damage path, not a sensor (§3.3).
- **Limits:** Phase 4's first body has **no felt heat in any sense the substrate acts on**: no drive, no nociception
  until GL2b, no damage until M17, little salience, no fear until M10. The LLM sees each sensor's name, unit and value,
  so no learning claim rests on an LLM-primary NPC (§6.4).

## 1. The split, and the leak tests

C-fibre heat nociceptors fire at a fixed temperature at receptor depth (40.4 ± 2.2 °C, 20–570 µm) while surface
temperature at threshold rises with heating rate (**V**, Tillman et al. 1995). So the world sends tissue temperature
at declared depths, and Maxim owns transduction, set points, drives and pain.

**The leak tests** (lesson 24): could an instrument there measure it without a nervous system (the world's)? Is it a
threshold, gain, adaptation, pooling or latency (the receptor's)? **Ruled:** receptor depth is anatomy the body
declares; breathing, gaze and posture are logged intents (§4.5); incident flux (D6), coverage, clothing and partial
contact are internal to the tissue law.

## 2. The stimulus schema

### 2.1 A row

| Field | Identity | Meaning |
|---|---|---|
| `name`, `unit` | yes | a physical quantity, never a verdict; a closed unit vocabulary shared with the field registry |
| `site_set`, `cadence` | yes | where (§3) and when (§2.2) |
| `valid` | yes | physical validity, rounding policy, empty-patch rule |
| `receptors`, `pooling` | no | receptor classes it can feed, pooling per class (§3.2) |
| `tag` | no | ANALOG, EARN or OPEN; closing one bumps `derivation_version` |
| `reads`, `derivation_version` | no | the perceivable fields its model opens (§7.4); the law's version |

The world declares no saturation range: the body YAML does, and `world_set_axis` clamps
(`audio_localization.py:748-761`) yet returns `True`, so the worker counts clamp bites into `StepOutput`.

### 2.2 The rows and cadence

**v1, frozen now:** `tissue_temperature`, `celsius`, at each declared depth of each `skin` point, cadence `tick`; its
`valid` range and rounding freeze with the tissue law's PR. `core_temperature` joins when bound. **Later rows** freeze
with their field's design: contact and vibration, joints and vestibular (ANALOG); radiance after line of sight from
**surface** temperatures only (`luminance` the EARN stopgap); `sound_event` per ear (a spherical-head model, since
straight paths under-report lateral ITD by about 25%, **M**); gas per breath.

The world ticks at 0.1 s and steps physics at 0.5 s. `tick` rows read fields held from the last physics step, a
zero-order hold: a sensor never interpolates fields, which would invent states the simulation never had. Faster
phenomena get physical summary statistics, each ANALOG.

### 2.3 The v1 laws behind the contract

| Piece | Today's law (replaceable) |
|---|---|
| tissue | a 3-layer Pennes column per point (0.1 / 2 / 10 mm, a node at each declared depth), Torvi & Dale (**S**) |
| outer boundary | convection and linearised radiation to the local ambient (L3: h 8 W/m²K, ε 0.95, **M**, to cite); immersion convection per point inside a flame, against its shape in metres (L3 §1.2) |
| incident flux | quadrature view factors; per-point visibility (D11) |
| occluders | intact authored geometry occludes as **primitives in metres**; altered cells by volume-fraction transmittance once B28 lands; a grid-only march is the planted red case |
| contact | one implicit system per touched object over the skin and an object-side sub-mesh refined to the substep's penetration depth, remapped back conservatively |
| cell faces | **nothing in v1**: no face contact or emission to bodies, strict red gates on both, a Known gap with P1's number (104 against 48 MJ/m² at 0.2 m, **V** via L3). The fix: face skins on body-contact faces, as 6.0b builds |
| partial contact, clothing | sub-columns weighted by area; clothing is a column layer |
| damage | Ω ≥ 1 at the basal layer is a burned point; Henriques (§11.2) |

**Rest and join.** With that boundary, a column on a 37 °C core rests at 32.4 °C at the surface; without it, at 37;
started uniform at core temperature it needs 1,060 s to come within 0.1 K of rest (**D**, L3's 45-node column). So
join and restart start each column at its steady profile, by a direct solve. Closed-form test: the steady profile.

**Accuracy is in kelvin, from a stated Ω error:** Ω's rate moves 0.50–0.54 per K under Henriques (**D**), so 0.1 K
basal is 5–9%; the header records both. A fixed 0.1 s step makes 70 °C steel pain 20% late and radiant error 1.25 K
at 80 kW/m² (**D**), so the law takes **error-controlled substeps per point**, from the point's own state, memoryless
across ticks, against a **header truth constant, never a rig field** (D20). Convergence is shown to 80 kW/m², for
immersion, and for contact with object-side nodes as an axis.

**Pose within a tick.** Holding tick T's pose over (T−1, T] shifts radiation by a tick, but would quantise contact
onset to ±0.1 s, 40–50% of steel's time to pain (**D**), so contact onset and release are interpolated between poses.

**Damage is per point.** A region half at 15 kW/m² and half at 5 first burns at 6.2 s; one column at the mean, at
11.8 s; one shared visible fraction for a half-shaded body makes pain and burn 3× late (**D**). Hence D11 (a).

## 3. The body

### 3.1 One body model

**This extends `tile_and_client.md` §2.1's body; it adds no second one.** The tile's 245 kJ/K store is the **core
node**, sole producer of `core_temperature`; skin columns are its surface layer. One ledger line, `bodies`, books:
radiant flux, debited from the flame's unreceived share; contact heat, against the object; convection and radiation
to ambient at the skin, **convection's one receiver** (tile §2.1's exchange volume now meets the skin); perfusion as a
skin–core exchange; metabolism into the core. Only the ambient is a reservoir. Absorption overdrawing a flame's share
is a ledger residual, never a prorated flux, which would make A's flux depend on B. Bodies don't shade in v1
(ANALOG, Q4). **`npc_key` is `body_key`.**

**The grammar is engine code; body instances are game data** (`boundaries.md` §2.1, BF-15). Site sets are in
body-local metres: `skin` (regions of points: position, normal, area, depths), `eyes`, `ears`, `nostrils`, `mouth`,
`head`, `joints`, `body`; L3 sizes `skin` at 17 regions, 58 points (Q1). Instances and saved state are frozen data in
`core/body/spec.py`.

### 3.2 Bindings and pooling

Maxim's bodies are root-only (`audio_localization.py:727-762`; `modality:` on a sub-sensor raises, `spec.py:556`), so
the contract delivers per site and bindings reduce in the core, in fixed order, in `core/stimuli/reduce.py`.
**Pooling is fixed by receptor class:** `thermo_skin` by area mean, `noci_heat` by maximum (else a 60 °C fingertip
beside a 33 °C palm reads 46 °C); it belongs in Maxim's receptor registry, **EARN** on GL3.B1 and OD-C10.

**A `Binding` is a frozen spec in `core/stimuli/schema.py`, validated when `join` is applied:** the row exists; sites
lie in its site set and the body; `single` has one site; no mean spans depths; pooling is the class's. An invalid
table refuses the join as a logged `agent_failed(build)` before any reduction; replay reads `join` through the same
gate, so a hand-edited log is refused, never crashed on. **The worker checks only what it alone sees:** Maxim sensor
names, equal unit strings (`celsius` can't bind `celsius_norm`), ranges, no mean on a pain path. A
**`bindings_digest`** goes in `welcome` and every `BoundFrame`; the worker refuses a mismatch with its own table.

### 3.3 Phase 4's first body

A flat body YAML in Maxim's format: root skin sensors (`skin_hand_left_temp`), `modality: world`, `drift_rate: 0`,
`celsius`, **no `drive:`** (which would make burns DRIVE-class): `fire_model.md` §5.1's stopgap, **EARN** on OD-C10.

- **`overdrive_world`,** one Overdrive modulator, hosts the backend (§4.4); its affordances all go to the outbox.
- **Region modulators for damage:** the 17 regions group onto modulators with vital sub-sensors, `fire` affinities,
  `health: derived` weights and failure modes (ANALOG). `apply_damage` silently returns 1.0 without sub-sensors
  (`spec.py:1035-1038`), so a build test plants a burn and requires integrity to fall, red on a stripped modulator.
- **Rest at the midpoint:** Maxim's `lint_body_rest_neutral.py` scans only Maxim's components and isn't in pymaxim,
  so a port, `scripts/lint_body_rest.py`, lands with the first body, planted off-centre.
- **That rule's cost:** the A4 gain weighs a reading by `(|v−0.5|·2)³` (`encoder.py:596`); centred at 33 °C over
  [−4, 70] °C, 45 °C weighs 0.034 and 60 °C 0.39 (**D**). The range is measured before the YAML lands: **OPEN**.
- **Damage:** burned area becomes an `apply_damage(amount, "fire")` delta once M17 rules; until then burns stay world
  state. Burned area is never bound to a sensor. ANALOG.

## 4. Delivery

### 4.1 The tick (D10, amended by insertion)

1. apply records; 2. move bodies; **3. contact and tissue substeps** over (T−1, T] against held fields; **4. build,
reduce and digest every body's frames**; 5. agents step on tick T's `BoundFrame`; 6. physics, on physics ticks;
**7. merge** step outputs; 8. outputs.

**The overlap:** step 6 may run beside step 5, joining before step 7, because intents apply at `apply_tick >
observed_tick` (`npcs_and_sem.md` §9's lane minimum refuses equality) and step 5 writes nothing step 6 reads. **Its
gate runs live,** since replay runs no agents: stub workers behind the real channel emit intents and breath records
under two seeded wall-delay schedules, overlap on and off; digests and record stream must match, then a replay with
`maxim` blocked must match again. Planted red: a merge applying a `step_output` during step 6.

**Threads:** step 4 runs in the simulation lane; a host pump encodes, sends, receives and stamps arrivals, so the
per-park ceiling is judged on stamps during physics. The host scatters, then gathers: a tick waits for the slowest
worker, not the sum. Push plus body step fit inside the ceiling `phase1/agents` sets.

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
    events: tuple[StimulusEvent, ...]  # since this NPC's last delivered frame, capped

@dataclass(frozen=True)
class BoundFrame:                      # what crosses the channel
    schema_version: int
    registry_digest: bytes             # of the bound rows; checked against `welcome`
    bindings_digest: bytes             # of the binding table (§3.2)
    npc_key: str
    tick: int
    value: NDArray[float64]            # one per binding, in binding order
    events: tuple[StimulusEvent, ...]
    receipts: tuple[Receipt, ...]      # (pid, kind), §6.2
```

- **Beside `Frame`, never inside it:** a `BodyFrameFeed` keyed by `npc_key`; `FrameView` never reaches it.
- **Deep frozen:** `__post_init__` refuses writable arrays, as `CellFrame` does, and arrays whose base chain doesn't
  end in immutable `bytes`; a constructor-site scan holds "only `core.stimuli` builds one".
- **Ids** come from sorted names, in the header, never a digest key. The worker checks `npc_key` against its
  channel's actor and that `tick` rises.
- **`StimulusEvent`** is `(tick, offset_us, kind, site_id, local_id, value, caused_by)`, delivered in the first frame
  built after it, sorted by `(tick, offset_us, kind rank, local_id)`; `local_id` is assigned per NPC after sorting by a
  world-side key (source id, site); `caused_by` is the NPC's own pid or null. Latency: zero for intent-made events, up
  to six ticks for physics-made ones. "Since the last delivered frame" holds at any delivery divisor (§4.6). v1 has no
  producer; a gate holds `events` empty until sound lands.

### 4.3 Bounds and failure

- **Events are capped per frame** in a byte budget below the socket buffer; overflow coalesces by `(kind, site)` into
  count and peak, checked before sending. Inert and failed NPCs accumulate nothing. Gates: a burst keeps the agent
  alive; a failed NPC's buffer stays empty for 10,000 ticks.
- **A non-finite value in the core is a world bug:** the server stops loudly. The decoder refuses NaN, ±Infinity and
  `1e400`; the worker refuses `bool`. Each is planted.
- **`False` from `world_set_axis` is an error;** values are validated before any write; the host ends the agent as
  `agent_failed(protocol)` in tick T's merge.
- **A partial send is normal:** a non-blocking `send` took 8,192 of 20,000 bytes on a macOS Unix socket, then raised
  `BlockingIOError` (**D**). The remainder waits in a per-channel outbox, pumped inside the ceiling. Only ceiling expiry
  is `hung`; only `BrokenPipeError`, `ConnectionResetError` or EOF is `crashed`. Gates: a worker reading one byte at a
  time lives; one that never reads lets the world advance after the ceiling.

### 4.4 The worker

- **The push:** `world_set_axis(emb, sensor, value, owner="overdrive_world")` per binding, then the body step,
  `Embodiment.evaluate_failures()` (M4); under TR23 the owner maps to `experienced`.
- **The backend:** `live_world_set_sensors` withholds drive credit on affordances whose `self_effect` touches those
  keys (`tool_bridge.py:548-560`); only a modulator backend fills it (`bootstrap.py:552-561`), taking over that
  modulator's `execute` (`spec.py:1136-1139`). Ours hangs on `overdrive_world`; `execute` appends an intent and
  **returns a fixed `pending`: no name, no metadata**. A build test proves credit flows through settle (M18).
- **One writer, checked by value:** Maxim never stores `owner`, and other paths write `vital_metrics` directly
  (`body.py:674-682`, `cerebellum_modulator.py:260`), so before the body step the worker compares each bound sensor
  with what it pushed; a difference is `agent_failed(protocol)`. **At every park** the thread set must equal the
  post-build set (Maxim starts threads later: `concept_extractor.py:542-560`, `agentic_runtime.py:255`), as OD-EA7
  requires; planted red at the third step.

### 4.5 Agent outputs and the lifecycle

**Posture, gaze and breathing are intent kinds,** applied next tick; an inert or failed agent breathes on a default
schedule, so a crashed NPC is still poisoned.

| Event | World side | Log record |
|---|---|---|
| join | bindings validated (§3.2); tissue at steady profile; frames built and digested | `join` with body and bindings, or `agent_failed(build)` |
| not ready, worker build refused | inert; built and digested, not sent | `agent_ready`; `agent_failed(build)` |
| `agent_failed` | tissue goes on; built and digested, not sent | `agent_failed(reason)` |
| restart | checks rerun; first frame carries no events, the dropped count logged | `agent_ready` |
| leave | tissue, events, visibility freed | `leave` |

Membership comes from logged records, never delivery; each row gets a crash-injection test.

### 4.6 Until a body can feel (D14)

Stepping the first body's Maxim body every tick buys nothing yet. **D5 (c) stays the contract; until a body with a
pain path exists, push and body step run at the cognition rate**, with that tick's values and the events since the
last delivered frame; tissue and frames still run every tick. **Known gap,** entered in `docs/architecture.md` with
`phase1/agents`' code: a contact shorter than a cognition step reaches tissue, not the agent. **T16**, strict red: a
0.2 s contact between steps at divisor 10 must change the agent's body state; it flips when a pain path lands and
delivery moves to every tick. No Phase 4 NPC meets fire before that (roadmap Phase 4).

## 5. Replay, digest, versioning

**Replay reproduces the world, never the agents** (`boundaries.md` §6.2); frames are recomputed, not logged.

- **The digest is in lanes, one per row,** keyed by `(name, derivation_version)`, never dense ids. Each lane chains,
  per tick, SHA-256 over its `(npc_key, site, value)` arrays in `npc_key` order: dtype, shape and little-endian bytes,
  length-prefixed (2.9 µs for a 250-row frame, against 110 µs as sorted-key JSON, **D**). `BoundFrame` values and
  receipts are one lane per NPC. The config canonicaliser is for the header only; codec bytes and deltas stay out.
- **Replay compares lanes whose key is unchanged,** refuses only when a changed lane is one an NPC in the log bound,
  and reports skipped lanes. Adding a row, or an unbound row's law swap, keeps replay goldens green.
- **Localisation:** each lane's chain is stored at log v0's interval, which finds the first bad *interval*; the first
  bad tick needs a reference run recomputing per-tick lanes, as the harness has.
- **The header:** rows by sorted name with unit, site set and version; the lanes; id maps; truth constants (K
  tolerance and its Ω error, refresh cap K, clustering bound, cutoff floors). Bodies and bindings ride `join` records.
- **The save** holds all carried `core/body` state: tissue; visibility with each pair's last refresh tick and
  reference pose; contact state; coalescing counters and pending events (the substep controller is memoryless). Test:
  save anywhere, load, run past a refresh, a controller change and a contact change, bit-identical to the unbroken
  run; plant an omitted reference pose.
- **The plant test:** in the harness, below a bypassed header check, a 10⁻¹² relative change to the surface
  conductance. One ulp is too small: on L3's column it first moves a node at tick 120–152 and never at zero flux,
  while 10⁻¹² moves one at tick 0 (**D**). The test runs planted and clean, requires a first differing tick inside the
  run, and requires the per-tick lanes to name it. A second plant reverses order inside `reduce.py`, `join` unchanged:
  red on the bound lane. Adding an unbound row stays green; a bound-row bump goes red. Events get a plant with their
  first producer.
- **Tier 2 isn't bit-identical on real Maxim** until M6 and M8 land.

**Version rules (F1, F15):** a new meaning gets a new name; a better estimate bumps `derivation_version`, goldens
regenerated in a commit saying so; adding a row is non-breaking; removing or renaming one bumps
`STIMULUS_SCHEMA_VERSION`; an agent home records only its bound rows, refused on a change the load doesn't name
(D13). **Each format has a version and a gate row:** body instance (5b); binding table, `BoundFrame`, receipt
(`phase1/agents`); the save's body state (the first law).

**Reserve now** in `phase1/sim-clock`'s log: lane chains, header slots, and `join`, `leave`, `agent_ready` and
`agent_failed` records.

## 6. Trust

### 6.1 Capabilities, and what this supersedes

The NPC builder gets only `(npc_key, its BoundFrame source, its actor-bound outbox)`. Superseded by name: the
membrane factory's frame source (`boundaries.md` §7.1, `npcs_and_sem.md` §6.5); the per-agent pinned frame
(`boundaries.md` §4.2 and §4.3; `npcs_and_sem.md` §7.2–§7.3); the pinned actor table on the NPC path
(`tile_and_client.md` §4); `npcs_and_sem.md` §6.6's barrier levers (due agents only; deltas), since every body parks
each tick and deltas are ruled out (D14's interim restores the first).

**D10 splits `region_parts`:** modulators stay in the membrane; the instrument builder becomes a lab builder. The
environment entity is `phase1/agents`' design (T8, T13), which maps `StructureModulator.execute`'s refusals to §6.2.

### 6.2 Receipts

**The receipt path is a stimulus path:** today it carries `absorbed_j`, fire text, existence by name and footprint
bounds by bisection. Superseding `npcs_and_sem.md` §6.6's "measured effect":
- **`execute` returns `pending`;** the **receipt is `(pid, kind)`** in tick `T+L`'s `BoundFrame`.
- **Kinds, in precedence:** `malformed`, `limit`, `unavailable`, `applied`. **v1 merges unperceived and out of reach
  into `unavailable`:** with no vision row there is no perception predicate from A's own frame, and any order between
  them is a distance oracle. They split when a vision row defines "perceived" as "some value in A's frame depends on
  it". The effect arrives as stimuli next tick.
- **Gates:** T4, T5, T11 over receipt bytes and the `execute` return, T11 sweeping an unavailable target's position
  and existence; T12's sentinel in `absorbed_j`; a per-act test that the effect reaches the actor's next frame.

### 6.3 The gates

Each is first shown red on a planted leak; T2 merged into T1 in v2.

| # | Gate |
|---|---|
| T1 | no drive or pain write from the world (grep gate, review rule) |
| T3 | a lamp and a plate of equal flux give equal stimuli; control: a lamp brought into view changes the frame |
| T4 | a hazard behind a wall changes nothing until something physical crosses |
| T5 | a material differing only in a combustion constant gives identical streams before any thermal event |
| T6 | probe: constants or occluded state decodable from pre-event frames |
| T7 | text denylist over every NPC-visible string, receipts and `pending` included |
| T8 | sensors, units, ranges independent of the scene |
| T9 | one fixed intent stream, divisors 1–50: frames byte-identical (plant: a model reading `dt_ticks`); worker half at 1×, 20× and two delay schedules, strict red until M6, M8 |
| T10 | `QUANTITIES`, the registry, each sensor set pinned |
| T11 | ids, allocation, unread material fields, tier, B's state, B joining out of sight: A bit-identical; B reaches A only through world state. Control: a fire moved into view changes A. Plants: batched `@`, global sparse solve, batch-minimum dt, cross-body cluster |
| T12 | sentinel scan of every byte to A's worker; plants: A built from B's store, a channel misroute |
| T13 | golden tool surface on real pymaxim |
| T14 | no row in `QUANTITIES`; every row has receptors |
| T15 | per hazard, cue onset at the receptor precedes the damage integral's onset; lead recorded (L6 R1) |
| T16 | a contact between cognition steps changes the agent's body state; strict red under D14 |

With a pain path: fingertip contact on 70 °C steel under `noci_heat` exceeds threshold before that point's Ω reaches
1; until then a build check refuses a mean on `noci_heat`. Host load leaks through the wall clock until D3 lands.

### 6.4 What the LLM sees, and what may be claimed

Maxim generates a `SensorReadTool` per sensor returning `value` and `unit` (`tool_bridge.py:295-321`, `:1002-1020`,
`:1068-1082`), so the LLM reads "skin_hand_left_temp … celsius … 47.3", and 47 °C means "burning" to it. No learning
claim from an LLM-primary NPC alone (L6 R15): a claim needs a substrate-side measure, a physical counter-prior or
between-NPC dose–response, pre-registered in a Maxim harness; M19 asks to withhold world-channel read tools.
**Blocking** (Kamin, **S**): a privileged predictor takes the prediction error, so the physical cue is never learned.

## 7. Placement and modularity

### 7.1 Modules

| Module | Owns | Layer |
|---|---|---|
| `core/body/spec.py`, `geometry.py`, `sites.py` | body instance and saved-state data; site sets in body metres; sites in world metres | 2 |
| `core/body/store.py` (5b) | pose, core node, tissue and visibility state, its own write window | 3 |
| `core/body/irradiance.py` | radiant flux per point: view factors, occlusion, visibility and its refresh | 4 |
| `core/body/contact.py` | the joint skin–object solve, onset times, one antisymmetric ledger entry per substep | 4 |
| `core/body/tissue.py` | columns, outer boundary, sub-columns, substeps, Henriques | 4 |
| `core/stimuli/schema.py` | rows, vocabularies, `Binding` and its checks, the `StimulusModel` protocol | 5 |
| `core/stimuli/models/<name>.py` | one per row family; reads perceivable fields; writes nothing | 5 |
| `registry.py`, `run.py`; `frame.py`; `reduce.py` | the tuple, order and handout; frame types and canonical values; reduction | 5 |
| `adapters/agents/` | Maxim-side checks, the push, the value and thread checks | 7 |

This supersedes `boundaries.md` §2.2's map by name. **Contact has one owner:** `contact.py` writes skin through the
store's window and the object through the solid law's exchange API, at step 3, against the solid's last published
state: a fifth writer class, a per-tick law, in `boundaries.md` §6.4's table, so the write window opens each tick.

**Stimuli sit above the laws** (L7). Tissue reaches models only through the `FieldReader`, over 5a's per-body point
container, a perceivable field; flux, visibility and contact run every tick, whatever an agent's cadence. **5a's
composition note gets three seams:** a per-tick law slot; the two-rate contact exchange, ledgered antisymmetrically
(`world_v2.md` §2.6); per-body point state and a multi-writer `radiant_emitters` table.

### 7.2 Registration and batch invariance

```python
# core/stimuli/registry.py: the one place a stimulus is named
from simcore.core.stimuli.models import tissue_temperature
STIMULI: tuple[StimulusModel, ...] = (tissue_temperature.MODEL,)
```

- **A declaration registry,** no plugins (`importlib` banned in the core); lanes and ids sort by name.
- **`prepare` then `kernel`** (`docs/plans/checklists.md:103`), the kernel with a closed-form test and a B5 row.
- **Batch invariance is contract.** Accelerate's dgemv moved 19 of one NPC's 48 values by 1 ulp once 9 others were
  stacked (**D**). So each body computes at its own shape; contact solves per connected component (one object and its
  skins) in canonical order; a point's substeps depend only on its own state; clusters never span bodies. A lint bans
  BLAS matrix-vector calls, batch-axis `einsum`, `scipy.linalg` and `scipy.sparse.linalg` in `core/stimuli` and
  `core/body`; T11 plants each.
- **N + M, not N × M:** emitters append to `radiant_emitters`; a new sense is a module, a `STIMULI` line, a site set
  and data.

### 7.3 Import contracts, fail-closed

In import-linter 2.6's source, `protected` sees direct imports only, an allowed importer may import every
descendant, and a nonexistent allowed importer resolves to nothing, silently.

| Contract | Rule |
|---|---|
| `stimuli-protected` | `protected` on `simcore.core.stimuli`; allowed: `Simulation`'s module (layer 6), `simcore.adapters` |
| `body-protected` | `protected` on `simcore.core.body`; allowed: `Simulation`'s module, `simcore.core.stimuli`, `simcore.adapters` |
| adapters' reach | skip-layer's recursive classification holds adapters to `CORE_PUBLIC_SURFACE`, which gains only `body.spec`, `stimuli.schema`, `stimuli.frame` |
| models allowlist | a grimp test: models import only `stimuli.schema`, the field-reader type, `body.geometry`, `body.sites`, `checks` |
| `stimuli-independent` | `independence` over `simcore.core.stimuli.models.*` |
| `agents-reads-body-frames` | `forbidden`, `allow_indirect_imports = false`; a test asserts its list equals `_core_modules() − AGENTS_SURFACE` plus `adapters.sem.bridge`; `AGENTS_SURFACE` = `stimuli.schema`, `stimuli.frame`, `intents`, `limits`, `checks` |
| `maxim-through-adapters` | the worker module joins `allowed_importers`, its test with it |

`protected` guards inside the core; skip-layer's classification guards against adapters. A test asserts every
allowed importer exists; each contract lands with its first importer and a `PLANTED` row.

### 7.4 Checks that fail the gate on drift

- **Completeness:** every model is in `STIMULI` once; every `reads` names a **perceivable** registered field.
  `perceivable` defaults false; material ids and table constants never are; making a field perceivable is a reviewed
  data change with a planted test.
- **Honest reads:** a recording `FieldReader` asserts each model opened exactly its `reads`.
- **No central switch:** an AST lint fails on a registered name as a literal comparison or key outside its module,
  schema, data, the generated vocabulary, the binding loader and `tests/`; receptor or unit literals, and `spec.name`
  against a variable, are review's.
- **Cross-tier tests per coupling:** occlusion, face emission, face contact, zone gas, at offsets 0, dx/3, 2dx/3, band
  gates and a wall edge, red on planted cell-centre occlusion or cell-mean faces; a half-shaded body's burned area
  matches per-point rays. Face couplings are strict red in v1.
- **Purity:** the writer scan; a golden vocabulary from `STIMULI`; an `__all__` allowlist on `core/stimuli`.

## 8. Cost and budget

**Basis:** 58 points, the 0.1 m tier, the heat law lightly loaded (~1.4 s per world second), one emitter. Rays go as
1/dx and physics as 1/dx³, so 0.2 m is the worst ratio. **Target, absolute:** ~140 ms of stimuli and delivery per world second at 10 NPCs, with counter thresholds,
in the B5 row.

| 10 NPCs, per world second (**D**, L3 and the DP review) | Cost |
|---|---|
| skin (one substep per tick) and quadrature flux every tick | ~21–32 ms |
| visibility, each point once per physics step | ~73–90 ms |
| delivery: encode, digest, park | ~15–30 ms |
| **stationary total** | **~110–150 ms** |
| visibility every tick (ten running NPCs, 0.1 m refresh distance) | ~365–450 ms |
| error-controlled substeps near a fire | ~+30 ms at four substeps |
| contact system; the Maxim body step (critical path) | unmeasured |

All rows but skin scale with emitters.

**The refresh schedule (D12, provisional).** A point refresh costs c ≈ 63–78 µs (73–90 ms over 1,160 per world
second). Each tick the law refreshes at most **K point–emitter pairs**, oldest first among pairs whose body moved past
the declared distance, then oldest overall; each pair is also due once per physics step. Visibility then costs at most
10·K·c per world second, and no pair is staler than ⌈P/K⌉ ticks, P the due pairs. At K = 116: ~73–90 ms, and ten
running NPCs (P = 580) see up to 5 ticks, 0.5 s, about 2 m at 4 m/s. At K = 290: ~180–225 ms and 0.2 s. Acceptability
is an outcome measurement: time to pain and burned area against every-tick refresh, for a body stepping from behind a
wall into 20 kW/m² (pain at 1.1 s). **D12 is re-ruled on that number, with clustering measured, before the irradiance
law's code.** If no K meets both, the failure paths are a coarser visibility law with a stated error, fewer NPCs near
a fire, or dilation.

**100 NPCs** stationary: ~2.5–2.9 wall seconds per world second here (**D**; 2.7–3.8 on v2's mixed basis). A shared
cap holds cost but stretches staleness to 50 ticks: a later target.

**The barrier under D5 (c):** at the 20× dial, 10 NPCs make 2,000 parks per wall second, 0.1–0.4 s of round trip
before any body step. The B5 row gives cost at 1× and the dial's maximum, the highest dial sustainable at 10 NPCs,
and hung kills per 1,000 parks; whether 20× is a target near a fire follows. Work counters (substeps, rays, frames,
bytes, parks) replay exactly; a counter gate reads parks from the log.

**Allowed,** as law parameters with tolerance tests: physical cutoffs, the same for everyone; the refresh schedule; a
fork-join inside `Simulation.step` over published read-only arrays, serial until T11's plants exist. **Forbidden:**
rules keyed on player or camera distance, wall clock, host load or the dial. Games budget perception by wall time
(UE sight's 5 ms slice, **S**) and player distance; here **simulation interest** may change cost, never values
(`npcs_and_sem.md` §2.1).

## 9. What Maxim must change

Each is a Phase 3 item through Maxim's process. **Question:** a plan owns it. **Pushback:** names a recorded decision.
**New:** searched, not found.

| # | Need; evidence at `origin/main` | Kind |
|---|---|---|
| M1 | sub-sensor writes with `modality:` (`spec.py:556`) | **Question** to TR23's setter (GL3.B3), extending OD-C10 |
| M4 (absorbs M16) | may an embedded host call `Embodiment.evaluate_failures()` (`body.py:258`: drift, failure modes, pain, no cognition) once per world tick between cognition steps, on the injected clock (its drift reads `time.time()`, `:293-297`; OD-A1, A2), in the host-driven build? | **Question** to OD-A10, `embeddable_agent_DRAFT.md` §7 |
| M5–M8 | drift, PainBus refractory, NAc window, reading stamps on world time | **Citations** of OD-A1, OD-A2, `world_clock_release_DRAFT.md` §3.5, §4 |
| M9 | burn as pain, two fibre classes, per-NPC receptor draws | **Question** to GL2b, GL3 |
| M10 | fear from burns: "a burn is **not** added" (`autonomic_layer.md:233-234`) | **Pushback**, with the first NPC fire scenario's failing run |
| M11, M12 | vision, touch, smell channels; per-ear signals | **Question** to GL3; **EARN** when sound lands |
| M13 | credit tolerating a delay | **New**, Phase 2 |
| M14 | the proximity plan reads a declared `heat_output` | **Pushback** (T3, T5) |
| M15 | thermal adaptation: no plan owns it (searched "habituat", "adaptive set-point", "salience-layer"; `archive/world_channel_weighting.md:221` closes the encoder route); novelty or salience habituation would be ANALOG, since fibres adapt at the receptor | **New**; OPEN |
| M17 | a world-caused burn through `apply_damage` (`spec.py:1025`; only `src/` caller `simulation/tools.py:665`) | **Question** to GL2b, TR22 |
| M18 | the modulator-backend path in the embedded build (`bootstrap.py:538-561`) | **Question** to OD-A10 |
| M19 | withholding world-channel read tools (`tool_bridge.py:1068-1082`) | **Question** to OD-A11 |

M2 stays withdrawn (the rest rule covers it). **The wall-clock gap is the largest unmet assumption** (L2 §8).

## 10. Decisions

**Ruled 2026-11-20, as recommended:** **D1** the port's `frame` is the `BoundFrame` source, one route (O36); **D2**
the registry is code primary, its generated artifact compared byte for byte; **D3** the wall-clock pushback is the
world-clock draft's §4 row; **D4** the injected clock is machinery, cognition gets no time field; **D5** (c); **D6**
flux internal; **D7** answered; **D8** the flat stopgap body; **D9** for O34; **D10** split `region_parts` before
vocabulary v1; **D11** (a), per-point visibility (reconfirmed 2026-11-21).

**Ruled 2026-11-21:** **D12, provisional:** 10 NPCs near a fire under §8's capped schedule, re-ruled on a measured
number before the irradiance law; 100 later. **D13:** a bound row's law change refuses an agent home unless the load
names it. **D14:** D5 (c) stays the contract; until a body has a pain path, delivery and the body step run at the
cognition rate, a Known gap held by T16; a pain path is a prerequisite for Phase 4's fire scenarios. M16 merges into
M4.

## 11. Steps, open questions and risks

### 11.1 Where the work lands

| Step | Work |
|---|---|
| 5a (sim-clock) | §5's reservations, §7.1's seams, recursive `_core_modules` with every module and `__init__` classified; the frozen types wait for their first caller |
| 5b (bodies) | `body/spec.py`, `geometry.py`, `store.py`, `sites.py`; the core node; the body-instance format (strict loader, version, gate row, fixtures) |
| `phase1/agents` | `adapters/agents`, its contract, value and thread checks; binding format, `BoundFrame` codec, receipt and goldens, each versioned with a gate row; the environment entity; D10; T16 and D14's Known gap |
| with `tissue_temperature`, before Phase 4 | `schema.py`, `frame.py`, `reduce.py`, the protected contracts, §7.4's checks; the tissue, contact and irradiance laws (B28 first); the save's body state; §6.3's gates; the first body, its YAML digest, worker check and `lint_body_rest.py` |

`foundations_plan.md` owns order.

### 11.2 Open questions

- **Q1.** The `skin` point count; L3's buttocks share disagrees with `geom.py`. **Q3.** Face skins (§2.3). **Q4.**
  Bodies shading each other, self-shadowing: a Known gap with a number when irradiance lands. **Q5.** Ventilation's
  owner. **Q6.** Skin feedforward (L1 §9.1).
- **Clustering's bound:** angular spread is the maximum over the emitter's quadrature points (a 0.68 m flame at 1 m
  subtends about 38°, **D**).
- **Before `data/`:** trace Henriques' constants (Weaver–Stoll's would give about 0.9 per K below 50 °C, **M**);
  grade Ω = 1 against two published second-degree times; record Jasiński's miss; cite the contact conductance (it
  moves steel pain 4.5×) and ambient h; anchor on ISO 13732-1 Table A.1 (**S**); verify receptor depths,
  anthropometry, ear spacing and tidal volume.

### 11.3 Risks, said plainly

- **The first body has no felt heat the substrate acts on:** under substrate-primary movement (roadmap Phase 4) an
  NPC would walk into fire while its body reads unhurt, hence D14.
- **Visibility may not fit the 10-NPC budget for moving NPCs** at any K meeting the outcome bound (§8).
- **If M4 is answered no,** every tick is a full Maxim step (unpriced) or D14's interim stays; the cheap fallback is a
  logged wake predicate (concurrency S6 (d)), priced beside a full step per tick; T9 and T16 say which holds.
- **The taint scan can't see an oracle smuggled through arithmetic;** review holds that.
