# The SEM stimulus interface (design v5, 2026-11-21)

**Status:** v5, the contract only, and the last paper fold (owner, 2026-11-21: the next review is on code). It folds
the final round (`reviews/sem_stimuli/final/fold.md`). Laws and their tests are in `docs/plans/checklists.md`. Rulings:
§10. Research: `research/sem_stimuli/`.

**Read at:** Overdrive `ceb04fd`; Maxim at local `origin/main` **`043eab8f`**, not fetched. **Tags:** **V** primary,
**S** secondhand, **M** memory, **D** derivation or measurement; ANALOG, EARN, OPEN as in `fire_model.md` §5.1.

**Bars** (`phase1/standards-bars`): verification now; a validation miss is a Known gap; a perception or learning bar
may be a future bar (a strict red gate naming the issue, a Phase 3 row, a passing world-side test). Every strict red
gate states `raises=`; every gate's plant is in the checklist.

## 0. The answer in one page

- **The line.** The world computes the physical stimulus *at the receptor's site*, tissue physics included. Maxim
  transduces it: thresholds, gain, adaptation, latency, pooling.
- **Frozen, the contract:** rows, units, site sets, cadence; `BodyFrame`, `BoundFrame`, `Binding`; the effector
  commands; the tick placement; failure and lifecycle; lanes and keys; versions; receipt kinds; gates; module seams
  and import contracts.
- **Replaceable, the laws:** every model, versioned, in `core/body/` and `core/stimuli/`; a swap touches only agents
  binding a row it produces, and only that row's lanes (§5).
- **How it arrives:** after bodies move, the core builds, reduces and digests each NPC's frames every tick; a
  `BoundFrame` message is assembled at delivery. The contract is D5 (c), every body each tick; until a body has a pain
  path, delivery and the Maxim body step run at the cognition rate (D14, §4.6).
- **v1's rows** are `tissue_temperature` and `core_temperature`. Burns reach Maxim through its damage path (§3.3).
- **Thermoregulation:** the world is the plant, the NPC the controller (§3.1).
- **Limits:** Phase 4's first body has no felt heat the substrate acts on, and the LLM sees each sensor's name, unit
  and value, so no learning claim rests on an LLM-primary NPC (§6.4).

## 1. The split, and the leak tests

C-fibre heat nociceptors fire at a fixed temperature at receptor depth (40.4 ± 2.2 °C, 20–570 µm) while surface
temperature at threshold rises with heating rate (**V**, Tillman et al. 1995). So the world sends tissue temperature
at declared depths, and Maxim owns transduction, set points, drives and pain.

**The leak tests** (lesson 24): could an instrument there measure it without a nervous system (the world's)? Is it a
threshold, gain, adaptation, pooling or latency (the receptor's)? Receptor depth is anatomy the body declares;
incident flux (D6), coverage, clothing and partial contact are internal to the tissue law.

## 2. The stimulus schema

### 2.1 A row

| Field | Identity | Meaning |
|---|---|---|
| `name`, `unit` | yes | a physical quantity, never a verdict; a closed unit vocabulary shared with the field registry |
| `site_set`, `cadence` | yes | where (§3) and when (§2.2) |
| `valid` | yes | physical validity, rounding policy, empty-patch rule |
| `receptors`, `pooling` | no | receptor classes it can feed, pooling per class (§3.2) |
| `tag` | no | ANALOG, EARN or OPEN; closing one bumps `derivation_version` |
| `reads`, `derivation_version` | no | the perceivable fields its model opens (§7.4); the model's version |

A row's lane key adds its **producers**, derived, never hand-kept (§5). The world declares no saturation range: the
body YAML does, and `world_set_axis` clamps (`audio_localization.py:748-761`) yet returns `True` (§4.4).

### 2.2 The rows and cadence

**v1, frozen now:** `tissue_temperature`, `celsius`, at each declared depth of each `skin` point, cadence `tick`; its
`valid` range and rounding freeze with the tissue law's PR; `core_temperature`, `celsius`, at the core node, cadence
`tick` (§3.1). **Later rows** freeze
with their field's design: contact and vibration, joints and vestibular (ANALOG); radiance after line of sight from
**surface** temperatures only (`luminance` the EARN stopgap); `sound_event` per ear; gas per breath.

The world's tick and physics step are `tile_and_client.md` §6.1's (T3). `tick` rows read fields held from the last
physics step, a zero-order hold: a sensor never interpolates fields, which would invent states the simulation never
had.

### 2.3 What binds every law

The laws (tissue, outer boundary, flux, occlusion, contact, damage) and their tests are in the checklist. The contract
holds them to five rules:
- **Per point, never a mean before a non-linear law:** flux, visibility, sinks and damage are evaluated per skin point
  (a body-wide shade makes burns 3× late, **D**; hence D11 (a)), and read through field interfaces over
  volumes in metres.
- **Accuracy is a header truth constant in kelvin, never a rig field** (D20), with its Ω error recorded beside it.
- **Carried state is declared and saved** (§5): what a law keeps across ticks is in the store, never rebuilt from a
  coarser published state. Contact's object-side sub-mesh lives for the whole contact (§7.1).
- **Cell faces exchange nothing with bodies in v1** (owner, S4): strict red gates on face contact and face emission,
  and a Known gap with its number.
- **Every body–world coupling gets a cross-tier test with an outcome margin** (`world_model.md` §3).

## 3. The body

### 3.1 One body model

**This extends `tile_and_client.md` §2.1's body, superseding by name its exchange-volume convection, "no
metabolism" and closed forms (2026-11-21); it adds no second body.** The tile's 245 kJ/K store is the **core node**,
sole producer of `core_temperature`; skin columns are its surface layer. One ledger line, `bodies`, books every watt,
signed: radiant flux (debited from the flame's unreceived share), contact heat (against the object), convection and
radiation at each skin point against the ambient (in Phase 1 a fixed reservoir, PH2-S1), perfusion (skin–core),
evaporation and metabolic heat. Absorption overdrawing a flame's share is a ledger residual, never a prorated flux,
which would make A's flux depend on B. Bodies don't shade in v1 (ANALOG, Q4). **`npc_key` is `body_key`.**

**Thermoregulation: the world is the plant, the NPC the controller** (PH2-S2 (c), owner, 2026-11-21). The core is
free. The plant is a metabolic source (about 80 W basal, **M**), skin blood flow as the skin–core conductance, sweat
as evaporative loss and shivering as raised metabolism, each within a cited range (checklist). **The effector
commands are contract:** `skin_blood_flow` (L/min), `sweat_rate` (g/min) and `metabolic_rate` (W), per body, an
intent kind (§4.5). Until Maxim drives them (M20), a marked ANALOG stand-in controller in the body law sets them,
labelled to move into Maxim; an NPC's command is refused `malformed` until its body declares agent regulation, a
body-instance field reserved now. So `core_temperature` moves: it rises beside a fire and falls in the cold until
shivering saturates.

**Tissue has one home:** `body/store.py` implements the field registry's `body_points` container kind, registering
its arrays as fields (`boundaries.md` §9.1). The `FieldReader` opens read-only views of them, with no copy; save
status comes from the registry entry.

**The grammar is engine code; body instances are game data** (`boundaries.md` §2.1, BF-15). Site sets are in
body-local metres: `skin` (regions of points: position, normal, area, depths), `eyes`, `ears`, `nostrils`, `mouth`,
`head`, `joints`, `body`; `skin` is 17 regions, 58 points (L3, Q1).

### 3.2 Bindings and pooling

Maxim's bodies are root-only (`audio_localization.py:727-762`; `modality:` on a sub-sensor raises, `spec.py:556`), so
the contract delivers per site and bindings reduce in the core, in fixed order, in `core/stimuli/reduce.py`.
**Pooling is fixed by receptor class:** `thermo_skin` by area mean, `noci_heat` by maximum (else a 60 °C fingertip
beside a 33 °C palm reads 46 °C); it belongs in Maxim's receptor registry, **EARN** on GL3.B1 and OD-C10.

**A binding table is plain data in `core/stimuli/wire.py`; its validation against the body is in `schema.py`, run
when `join` is applied:** the row exists; sites lie in its site set and the body; `single` has one site; no mean spans
depths; pooling is the class's. An invalid table refuses the join as a logged `agent_failed(build)`; replay reads
`join` through the same gate. **The worker checks only what it alone sees:** Maxim sensor names, equal unit strings
(`celsius` can't bind `celsius_norm`), ranges, no mean on a pain path. A **`bindings_digest`** goes in `welcome`
(`client_rendering.md` §4.1) and every `BoundFrame`; the worker refuses a mismatch with its own table.

### 3.3 Phase 4's first body

A flat body YAML in Maxim's format: root skin sensors (`skin_hand_left_temp`), `modality: world`, `drift_rate: 0`,
`celsius`, **no `drive:`** (which would make burns DRIVE-class): `fire_model.md` §5.1's stopgap, **EARN** on OD-C10.

- **`overdrive_world`,** one Overdrive modulator, hosts the backend (§4.4); its `world_owned_sensors` is the bound
  sensor set, and all its affordances go to the outbox.
- **Region modulators for damage:** the 17 regions group onto modulators with vital sub-sensors, `fire` affinities,
  `health: derived` weights and failure modes (ANALOG). `apply_damage` silently returns 1.0 without sub-sensors
  (`spec.py:1034-1036`, OD-I7), so a build test requires a planted burn to lower integrity. **No failure mode
  triggers on a bound sensor field** (§6.4).
- **Rest at the midpoint:** `scripts/lint_body_rest.py`, ported from Maxim; the range is **OPEN**.
- **Damage:** burned area becomes an `apply_damage(amount, "fire")` delta once M17 rules; it is never bound. ANALOG.

## 4. Delivery

### 4.1 The tick (D10, amended by insertion)

1. apply records; 2. move bodies; **3. contact and tissue substeps** over (T−1, T] against held fields; **4. build,
reduce and digest every body's frames**; 5. agents step on tick T's `BoundFrame`; 6. physics, on physics ticks;
**7. merge** step outputs; 8. outputs.

**The overlap:** step 6 may run beside step 5, joining before step 7, because agent intents apply at `apply_tick >
observed_tick` and step 5 writes nothing step 6 reads. `npcs_and_sem.md` §9 states no minimum, so this contract does:
**every agent intent has `L_us ≥ 1`**, refused otherwise. **Its gate runs live** (replay runs no agents), with no
wall timing: stub replies, including a cell-writing intent, released at host hooks in two fixed orders, overlap on
and off, then a replay with `maxim` blocked. Every leg's lanes and record stream must be equal; on the planted early
merge the replay leg goes red (toy, **D**).

**Threads:** step 4 runs in the simulation lane. A host pump thread encodes, sends, receives and stamps arrivals,
handing off only through a queue step 7 drains, so it touches no world state.

### 4.2 The frames

```python
@dataclass(frozen=True)                # simcore/core/stimuli/frame.py; host only
class BodyFrame:
    schema_version: int
    npc_key: str
    tick: int
    fields_sequence: int               # the published Frame its held fields came from
    stimulus_id: NDArray[int32]        # sorted by (stimulus_id, site_id); read-only
    site_id: NDArray[int32]            # index within the row's site set for this body
    value: NDArray[float64]
    events: tuple[StimulusEvent, ...]  # first available at this tick, coalesced per tick (§4.3)

@dataclass(frozen=True)                # simcore/core/stimuli/wire.py; what crosses the channel
class BoundFrame:
    schema_version: int
    registry_digest: bytes             # of the bound rows; checked against `welcome`
    bindings_digest: bytes             # of the binding table (§3.2)
    npc_key: str
    tick: int
    value: NDArray[float64]            # one per binding, in binding order, this tick
    events: tuple[StimulusEvent, ...]  # the undelivered ticks' BodyFrame events, as coalesced
    receipts: tuple[Receipt, ...]      # every receipt since the last delivery, never coalesced
```

- **Beside `Frame`, never inside it:** a `BodyFrameFeed` keyed by `npc_key`; `FrameView` never reaches it.
- **Deep frozen:** `__post_init__` refuses writable arrays and arrays not based on immutable `bytes` (`readonly`); a
  constructor-site scan holds "only `core.stimuli` builds one".
- **Ids** come from sorted names, in the header. The worker checks `npc_key` against its channel's actor and that
  `tick` rises, then drops `tick` (D4).
- **Per tick, independent of delivery:** `BodyFrame`, the bound values and their digests (§5). A `BoundFrame` message
  concatenates the undelivered ticks' events and receipts and adds no loss, so its content is the same at every
  divisor (toy, **D**); the only loss is §4.3's per-tick coalescing, which the events lane digests.
- **`StimulusEvent`** is `(tick, offset_us, kind, site_id, local_id, value, caused_by)`, sorted by `(tick, offset_us,
  kind rank, local_id)`; `local_id` is assigned per NPC after sorting by (source id, site); `caused_by` is the NPC's
  own pid or null; pids are per NPC. v1 has no producer; a gate holds `events` empty until sound lands.

### 4.3 Bounds and failure

- **Events are capped per tick per NPC** by a byte budget, a header truth constant; overflow coalesces that tick's
  events by `(kind, site)` into count and peak. A delivery's bound, the budget times the largest cognition divisor
  (a header constant), is refused at start unless below the measured socket buffer. Receipts are never coalesced;
  `ActionLimits`' per-step intent cap bounds them. Inert and failed NPCs accumulate nothing. Gates: a burst keeps the agent alive; a failed NPC's buffer stays empty for 10,000 ticks.
- **A non-finite value in the core is a world bug:** the server stops loudly. The decoder refuses NaN, ±Infinity and
  `1e400`; the worker refuses `bool`.
- **`False` from `world_set_axis` is an error;** values are validated before any write; the host ends the agent as
  `agent_failed(protocol)` in tick T's merge.
- **A partial send is normal** (**D**): the remainder waits in a per-channel outbox. Only ceiling expiry is `hung`;
  only `BrokenPipeError`, `ConnectionResetError` or EOF is `crashed`. A `step_output` merges only when whole; a
  partial one at expiry is discarded with the `hung` record.

### 4.4 The worker

- **The push:** `world_set_axis(emb, sensor, value, owner="overdrive_world")` per binding. Per-part sensors
  (`arms.thermal`) need OD-C10, since `world_set_axis` is root-only today. **The body step**
  (`Embodiment.evaluate_failures()`, M4): on a cognition tick the host pushes but doesn't step, so the agent's own
  tick steps the body in Maxim's W-4 order (`substrate_proposal.py:808-839`); under D5 (c) the host steps it on other
  ticks, under D14 never. A publish between passes keys to the last cluster stash, ANALOG until M4 answers.
- **The backend** hangs on `overdrive_world`, so `live_world_set_sensors` (`tool_bridge.py:548-560`, filled from
  `world_owned_sensors`, `bootstrap.py:552-561`) equals the bound set; `execute` appends an intent and **returns a
  fixed `pending`: no name, no metadata**; credit flows through settle (M18).
- **One writer, checked by value:** Maxim never stores `owner`, and other paths write `vital_metrics`
  (`body.py:674-682`). At each push the worker records the expected stored value (clamped to the declared range, a
  bite counted); **before the next push** it compares each bound sensor with it. A difference is
  `agent_failed(protocol)`.
- **Threads:** the baseline is taken at `agent_ready`; at every park the multiset of thread **names** must equal it.
  Session close and open run outside a park, each re-baselining and logging the delta, which must be empty or name
  threads Maxim's session restarts. A difference is `agent_failed(protocol)`. **Maxim starts its `LLMCall` thread at
  the first LLM call** (`llm_worker.py:665`), against OD-EA7 ("the thread count is unchanged by building and
  stepping"), so today every real NPC fails at its first park after thinking: real NPCs wait on OD-EA7.

### 4.5 Agent outputs and the lifecycle

**Posture, gaze, breathing and the thermoregulatory effectors are intent kinds,** applied next tick through the
stage-1 parser like `Strike`, with ranges in `ActionLimits` and a gate-registry row each. The worker sends intents as
wire data and stage 1 parses them host-side, so the worker imports nothing from `intents`. An inert or
failed agent breathes on a default schedule, so a crashed NPC is still poisoned.

| Event | World side | Log record |
|---|---|---|
| join | bindings validated (§3.2); tissue at its steady profile; frames built and digested | `join` with body and bindings, or `agent_failed(build)` |
| not ready, worker build refused | inert; built and digested, not sent | `agent_ready`; `agent_failed(build)` |
| `agent_failed` | tissue goes on; built and digested, not sent | `agent_failed(reason)` |
| restart | checks rerun; first delivery carries no events or receipts of the previous life, the dropped counts logged | `agent_ready` |
| leave | tissue, events, visibility freed | `leave` |

Membership comes from logged records, never delivery. The `agent_ready` and `agent_failed` records are
`npcs_and_sem.md` §6.6's.

### 4.6 Until a body can feel (D14)

**A pain path** is a PainBus publish, seen by a subscriber, driven by a bound skin sensor, whose onset leads Ω = 1
at the same point by at least a cited withdrawal latency plus one cognition interval. It is shown on real pymaxim
with fingertip contact on 70 °C steel, under D5 (c), at the dial's maximum divisor over every cognition phase, the
lead recorded in ticks. Pain from damage-driven failure modes doesn't count. Roadmap Phase 4's gate points at it.

**Until a pain path exists, push and body step run at the cognition rate;** tissue and frames still run every tick.
**Known gap,** entered with `phase1/agents`' code: values inside a contact window, and their timing, are lost (a
0.2 s touch of 70 °C steel leaves the basal value 5.7–10.8 K above rest at the next step, against a 43.2 °C peak,
**D**).

**T16, three gates,** landing with the contact law; a red one is `xfail(strict=True, raises=AssertionError)`, so a
missing law is an error (checked, **D**):
- **T16a, delivery (verification), red under D14:** at divisor 10, for every tick inside a 0.2 s contact, the stub's
  push log holds that tick's bound value. It flips only once the barrier's B5 row exists (concurrency F2).
- **T16b, the world half (verification), green:** on a fixture body with a skin drive, the per-tick bound value
  crosses the drive's band edge on a tick between cognition steps, whatever D14 says.
- **T16c, a future bar (M4, OD-A22):** on that fixture under D5 (c), on real pymaxim, the between-pass publish joins
  its crossing tick (the host tick of the `evaluate_failures` call whose subscriber saw it), not the last cluster
  stash. Today it publishes but keys to the stash, so lifting D14 can't flip it; Maxim's out-of-band producer
  (`autonomic_layer.md` §3.1.4, G9) does. The refractory runs on the wall clock (M6), so the fixture has one entry.

## 5. Replay, digest, versioning

**Replay reproduces the world, never the agents** (`boundaries.md` §6.2); frames are recomputed, not logged.

- **Lanes, never dense ids.** A row lane is keyed by `(name, derivation_version, producers)`, where `producers` is the
  sorted `(law, version)` set of every law upstream of its `reads`: the transitive closure over each law's declared
  reads and writes, computed from the registry. Each lane chains, per tick, SHA-256 over its `(npc_key, site index,
  value)` arrays in `npc_key` order (dtype, shape, little-endian bytes, length-prefixed, after rounding). An **events
  lane** per NPC covers `BodyFrame.events`, as coalesced. Each NPC's **bound lane** chains, every tick and
  independent of delivery, the reduced values in binding order plus the receipts produced that tick, keyed by
  `(npc_key, BoundFrame version, receipt-vocabulary version, bindings_digest, reduce version, bound row keys)`; T9
  holds delivery to it.
- **Replay compares lanes whose key is unchanged,** refuses when a changed lane is one an NPC in the log bound, refuses
  an unknown format version by name, and reports skipped lanes. Adding a row, or an unbound row's law swap, keeps
  goldens green. Stored chains find the first bad *interval*; the first bad tick needs a reference run.
- **The header's stimulus slots** are `boundaries.md` §6.3's.
- **The save** holds all carried `core/body` and `core/stimuli` state as the registry and §7.1 declare it, contact
  sub-meshes and pending events included; a save anywhere reloads bit-identical.
- **Tier 2 isn't bit-identical on real Maxim** until M6 and M8 land.

**Version rules:** F1 and F15 are `world_model.md` §8's; adding a row is non-breaking; removing or renaming one bumps
`STIMULUS_SCHEMA_VERSION`; an agent home records its bound lane keys, refused on a change the load doesn't name (D13).
**Each format has a version and a gate row:** body instance (5b); binding table, `BoundFrame`, receipt, `welcome`,
`step_output` (`phase1/agents`); the save's body state (the first law). **`phase1/sim-clock` reserves** the lanes,
header slots and the `join`, `leave` and agent lifecycle records (§4.5; `boundaries.md` §6.1).

## 6. Trust

### 6.1 Capabilities, and what this supersedes

The NPC builder gets only `(npc_key, its BoundFrame source, its actor-bound outbox)`. Superseded by name: the
membrane factory's frame source (`boundaries.md` §7.1, `npcs_and_sem.md` §6.5); the per-agent pinned frame
(`boundaries.md` §4.2–§4.3, `npcs_and_sem.md` §7.2–§7.3); the pinned actor table (`tile_and_client.md` §4);
`npcs_and_sem.md` §6.6's barrier levers.

**D10 splits `region_parts`:** modulators stay in the membrane; the instrument builder becomes a lab builder
(`boundaries.md` §4.4). The
environment entity is `phase1/agents`' design (T8, T13), which maps `StructureModulator.execute`'s refusals to §6.2.

### 6.2 Receipts

**The receipt path is a stimulus path:** today it carries `absorbed_j`, fire text, existence by name and footprint
bounds by bisection. Superseding `npcs_and_sem.md` §6.6's "measured effect":
- **`execute` returns `pending`;** the **receipt is `(pid, kind)`**, in the first delivery after the merge that
  refused or applied its intent (`L_us ≥ 1`, §4.1).
- **One home:** `stimuli.wire`. `intents` keeps its refusal codes and layer 6 maps them to kinds; this supersedes by
  name `boundaries.md` §2.2's "receipts" in 5b and `settle`'s receipt type.
- **v1 kinds are target-independent (D15), decided by stage 1 alone:** `malformed`, `limit`; any stage-2 result is
  `accepted`. Whether the target existed, was in reach or was hit is logged host-side only; the effect arrives as
  stimuli. With no vision or touch row, `applied` against `unavailable` would be an existence and footprint oracle.
  Target-dependent kinds return, as a receipt version bump, when a row defines "perceived".
- **Gates:** T4, T5, T11 over receipt bytes and the `execute` return, T11 sweeping every target-dependent refusal the
  applier returns (existence, air, gone, footprint, burning state), per affordance; T12's sentinel in `absorbed_j`.

### 6.3 The gates

Each is first shown red on its plant (checklist); T2 merged into T1 in v2.

| # | Gate |
|---|---|
| T1 | no drive or pain write from the world (grep gate, review rule) |
| T3 | a lamp and a plate of equal flux give equal stimuli; control: a lamp brought into view changes the frame |
| T4 | a hazard behind a wall changes nothing until something physical crosses |
| T5 | a material differing only in a combustion constant gives identical streams before any thermal event |
| T6 | probe: constants or occluded state decodable from pre-event frames |
| T7 | text denylist over every NPC-visible string, receipts and `pending` included |
| T8 | sensors, units, ranges independent of the scene |
| T9 | one fixed intent stream, divisors 1–50: `BodyFrame`s byte-identical, `BoundFrame` event and receipt content equal as a multiset over a common window (plant: a model reading `dt_ticks`); worker half at 1×, 20× and both release orders, strict red until M6, M8 |
| T10 | `QUANTITIES`, the registry, each sensor set pinned |
| T11 | ids, allocation, unread material fields, tier, B's state, motion and joining out of sight: A bit-identical; B reaches A only through world state. Control: a fire moved into view changes A |
| T12 | sentinel scan of every byte to A's worker; plants: A built from B's store, a channel misroute |
| T13 | golden LLM surface on real pymaxim: the tool surface, the auto-sense section and the `body_state` section |
| T14 | no row in `QUANTITIES`; every row has receptors |
| T15 | per hazard, cue onset at the receptor precedes the damage integral's onset; lead recorded (L6 R1) |
| T16 | §4.6: T16a delivery and T16b the world half (verification); T16c between-pass keying (future bar) |
| T17 | future bar (M20, OD-C12): the NPC regulates its own temperature; world half: the plant's closed forms |

Until §4.6's pain-path test passes, a build check refuses a mean on `noci_heat`. Host load leaks through the wall
clock until D3.

### 6.4 What the LLM sees, and what may be claimed

Maxim shows the LLM world-modality sensors three ways: generated `SensorReadTool`s (`tool_bridge.py:1068-1082`);
the `sense` tool, which auto-sense runs on every percept with a transcript (`loop_perception.py:265-391`); and the
`body_state` section behind `MAXIM_ENABLE_BODY_STATE_PROMPT` (`memory_hub.py:58-77`). So the LLM reads
"skin_hand_left_temp … celsius … 47.3", and 47 °C means "burning" to it; the worker refuses that flag. No learning
claim from an LLM-primary NPC alone (L6 R15): a claim needs a substrate-side measure, a physical counter-prior or
between-NPC dose–response, pre-registered in a Maxim harness; M19 asks to withhold all three. A privileged predictor
takes the prediction error (blocking, Kamin, **S**), so the physical cue is never learned.

## 7. Placement and modularity

### 7.1 Modules

| Module | Owns | Layer |
|---|---|---|
| `core/body/spec.py`, `geometry.py`, `sites.py` | body instance and saved-state data; site sets in body metres; sites in world metres | body: spec |
| `core/body/store.py` (5b) | pose, core node, tissue, visibility and contact state as `body_points` fields; its own write window | body: store |
| `core/body/tissue.py` | the column operator and per-point error estimate; steps untouched sub-columns | body: laws |
| `core/body/irradiance.py` | radiant flux per point: view factors, occlusion, visibility and its refresh | body: laws |
| `core/body/contact.py` | each touched component on one time grid it owns, from tissue's operator and the carried sub-mesh | body: above tissue |
| `core/stimuli/wire.py` | `BoundFrame`, `StimulusEvent`, `Receipt` and kinds, binding-table plain data; imports only `checks`, `readonly` and numpy | stimuli: leaf |
| `core/stimuli/schema.py`, `frame.py` | rows, site sets, binding validation (`phase1/agents`); the `StimulusModel` protocol (the tissue row); `BodyFrame` | stimuli |
| `core/stimuli/models/<name>.py` | one per row family; reads perceivable fields; writes nothing | stimuli: models |
| `registry.py`, `run.py`, `reduce.py`, `events.py` | the tuple, order and handout; reduction; the pending-event and coalescing state, saved by layer 6, written only by `events.py` in step 4 (`boundaries.md` §6.4) | stimuli |
| `adapters/agents/` | Maxim-side checks, the push, the value and thread checks | adapters |

`core/body` sits beside cells and `core/stimuli` above it; stimuli imports nothing from `intents` (§6.2). This
supersedes `boundaries.md` §2.2's map by name; the layer order stays §2.2's.

**Contact has one owner:** `contact.py` steps touched components in step 3, before `tissue.py` steps the rest,
writing skin through the store's window and the object through the solid law's exchange API, **against its own
carried sub-mesh**, kept from onset to release (rebuilt each tick, painless 90 °C wood hurts at 0.4–2.35 s, **D**).
**The store's writers** are an allowlist in `boundaries.md` §6.4's table, held by an ownership scan: load, motion, the
applier, `tissue.py`, `irradiance.py`, `contact.py`.

**Stimuli sit above the laws** (L7): tissue reaches models only through the `FieldReader`; the laws run every tick,
whatever an agent's cadence. **5a's composition note gets three seams:** a per-tick law slot;
the two-rate contact exchange, ledgered antisymmetrically (`world_v2.md` §2.6); the `body_points` container and a
multi-writer `radiant_emitters` table, each row keyed `(writer law, source object id, primitive id)`, the key that
orders sums and refresh.

### 7.2 Registration and batch invariance

```python
# core/stimuli/registry.py: the one place a stimulus is named
from simcore.core.stimuli.models import tissue_temperature
STIMULI: tuple[StimulusModel, ...] = (tissue_temperature.MODEL,)
```

- **A declaration registry,** no plugins (`importlib` banned in the core); lanes and ids sort by name; each model is
  `prepare` then `kernel`, the kernel with a closed-form test and a B5 row.
- **Batch invariance is contract.** Stacking bodies moved one NPC's values by 1 ulp in Accelerate's dgemv (**D**),
  so each body computes at its own shape. A contact component is the patches sharing object-side sub-mesh nodes
  within the tick, never an object, with its own termination and substeps, solved in canonical order by its smallest
  `(object id, sub-mesh node id)`; an untouched point's substeps depend only on its own state. Clusters never span
  bodies. **No budget is shared across bodies:** any cap on refresh or work is per body and per emitter (a shared cap
  made A's refresh depend on B, **D**). A point's flux sums emitters in key order. A lint bans BLAS matrix-vector
  calls, batch-axis `einsum`, `scipy.linalg` and `scipy.sparse.linalg` in `core/stimuli` and `core/body`.
- **N + M, not N × M:** emitters append to `radiant_emitters`; a new sense is a module, a `STIMULI` line, a site set
  and data.

### 7.3 Import contracts, fail-closed

In import-linter 2.6, `protected` sees direct imports only, and a nonexistent allowed importer resolves to nothing.

| Contract | Rule | Lands |
|---|---|---|
| `body-protected` | `protected` on `simcore.core.body`; allowed: layer 6's modules (`Simulation`, the applier, the frame publisher), `simcore.core.stimuli`, `simcore.adapters` | 5b, with `store.py` |
| `body-layers`, `stimuli-layers` | `layers` with `containers`: body `contact`, `tissue \| irradiance`, `store`, `spec \| sites`, `geometry`; stimuli `run`, `registry \| reduce \| events`, `models`, `frame \| schema`, `wire` (top to bottom) | 5b; the tissue row's PR |
| `stimuli-protected` | `protected` on `simcore.core.stimuli`; allowed: layer 6's modules, `simcore.adapters` | the tissue row's PR |
| adapters' reach | skip-layer's recursive classification holds adapters to `CORE_PUBLIC_SURFACE`, which gains only `body.spec` (5b), `stimuli.wire` and `stimuli.schema` (`phase1/agents`); `MEMBRANE_SURFACE` subtracts each as it lands | each module's step |
| models allowlist | a grimp test: models import only `stimuli.schema`, the field-reader type, `body.geometry`, `body.sites`, `checks` | the tissue row's PR |
| `stimuli-independent` | `independence` over `simcore.core.stimuli.models.*` | the tissue row's PR |
| `agents-reads-body-frames` | `forbidden`, `allow_indirect_imports = false`; its list equals `_core_modules() − AGENTS_SURFACE` plus `adapters.sem.bridge`; `AGENTS_SURFACE` = `stimuli.wire`, `checks`, `readonly`; a grimp test requires the surface, with each member's parent packages, closed under imports | `phase1/agents` |
| `maxim-through-adapters` | the worker module joins `allowed_importers`, its test with it (`boundaries.md` §8.1) | `phase1/agents` |

Every `forbidden` list derived from `_core_modules()` sets `as_packages = false`, and its equality test asserts it;
a test asserts every allowed importer exists. On toy packages (**D**, rerun for v5): the orders above keep every
import §7.2 needs and break on `spec → store` and `models → run`; a package in a forbidden list blocks `stimuli.wire`
unless `as_packages = false`.

### 7.4 Checks that fail the gate on drift

- **Completeness:** every model is in `STIMULI` once; every `reads` names a **perceivable** registered field; every
  law declares its reads, writes and version (§5's producers). `perceivable` defaults false; material ids and
  table constants never are; making a field perceivable is a reviewed data change with a planted test.
- **Honest reads:** a recording `FieldReader` asserts each model opened exactly its `reads`.
- **No central switch:** an AST lint fails on a registered name as a literal comparison or key outside its module,
  schema, data, the generated vocabulary, the binding loader and `tests/`.
- **Purity:** the writer scan, a golden vocabulary; `core/stimuli/__init__.py` imports nothing.

## 8. Budget

**Target, absolute:** ~140 ms of stimuli and delivery per world second at 10 NPCs near a fire, with deterministic
work counters (substeps, rays, refreshes, frames, bytes, parks) that replay exactly, thresholds in the B5 row. The
cost table is in the checklist. Moving NPCs are the hard case: refreshing every point every tick costs ~3× (**D**).

**D12, provisional.** Per-body, per-emitter budgets lose pooling; the worst case is unchanged. D12 is re-ruled, before
the irradiance law's code, on one body at the scene's maximum emitter count: time to pain and burned area against
every-tick refresh, stepping from behind a wall into 20 kW/m². If nothing meets it: a coarser visibility law with a
stated error, fewer NPCs near a fire, or dilation. **Above the maximum emitter count** no value changes: it is
logged, the counters read it, and D12's basis no longer holds.

**Allowed,** as law parameters with tolerance tests: physical cutoffs, the same for everyone; the refresh schedule; a
fork-join over published read-only arrays, serial until T11's plants exist. **Forbidden:** rules keyed on player or
camera distance, wall clock, host load or the dial: **simulation interest** may change cost, never values
(`npcs_and_sem.md` §2.1).

## 9. What Maxim must change

Each is a Phase 3 item through Maxim's process. **Question:** a plan owns it. **Pushback:** names a recorded decision.
**New:** searched, not found.

| # | Need; evidence at `origin/main` | Kind |
|---|---|---|
| M1 | sub-sensor writes with `modality:` (`spec.py:556`) | **Question** to TR23's setter (GL3.B3), extending OD-C10 |
| M4 (absorbs M16) | a host's `evaluate_failures()` (`body.py:258`) between cognition steps, on the injected clock, and how a publish between passes is keyed | **Question** to `autonomic_layer.md` §3.1.4's out-of-band producer (G9), #1176 for the in-pass half; OD-A22 |
| M5–M8 | drift, PainBus refractory, NAc window, reading stamps on world time | **Citations** of OD-A1, OD-A2, `world_clock_release_DRAFT.md` §3.5, §4 |
| M9 | burn as pain, two fibre classes, per-NPC receptor draws | **Question** to GL2b, GL3 |
| M10 | fear from burns: "a burn is **not** added" (`autonomic_layer.md:233-234`) | **Pushback**, with a harness scenario on a fixture body with a pain path |
| M11, M12 | vision, touch, smell channels; per-ear signals | **Question** to GL3; **EARN** when sound lands |
| M13 | credit tolerating a delay | **New**, Phase 2 |
| M14 | the proximity plan reads a declared `heat_output` | **Pushback** (T3, T5) |
| M15 | thermal adaptation (searched "habituat", "adaptive set-point", "salience-layer") | **New**; OPEN |
| M17 | a world-caused burn through `apply_damage` (`spec.py:1025`; only `src/` caller `simulation/tools.py:665`) | **Question** to GL2b, TR22 |
| M18 | the modulator-backend path in the embedded build (`bootstrap.py:538-561`) | **Question** to OD-A10 |
| M19 | withholding every LLM rendering of world-modality sensors (read tools, `sense` and auto-sense, `body_state`); whether the embedded build registers `sense` | **Question** to OD-A11 |
| M20 | thermoregulation's controller: effector outputs and §3.3's two-sided need (R-2). Searched for thermoreg, shiver, sweat, vasoconstrict, vasomotor, perfusion: only the `core_temperature` drive | **Question** to `autonomic_layer.md` §3.3; OD-C12 |

M2 stays withdrawn. **The wall-clock gap is the largest unmet assumption** (L2 §8).

## 10. Decisions

This document's decisions (20 rulings) are kept as records, with their dates, owner sections and status, in `decisions/sem_stimuli.md`.

## 11. Steps, open questions and risks

### 11.1 Where the work lands

| Step | Work |
|---|---|
| 5a (sim-clock) | §5's reservations (lanes with their keys, header slots), §7.1's seams, recursive `_core_modules` with every module and `__init__` classified |
| 5b (bodies) | `body/spec.py`, `geometry.py`, `store.py`, `sites.py`; the core node with its metabolic source and closed-form steady state; the body-instance format; `body-protected`, `body-layers`, the store's writer scan; posture, gaze and breath intents with their gates |
| `phase1/agents` | `stimuli/wire.py`, `schema.py`'s rows, site sets and binding validation, the `BoundFrame` codec, receipts and goldens, each versioned with a gate row; `adapters/agents`, its contract and closure test, value and thread checks; the overlap gate; the environment entity; D10; D14's Known gap |
| with `tissue_temperature`, before Phase 4 | the `StimulusModel` protocol, `frame.py`, `reduce.py`, `events.py`, the stimuli contracts, §7.4's checks; the laws, in the checklist's order (B28 first), the thermoregulatory plant and stand-in among them; the save's body state; §6.3's gates; the first body, its YAML digest, worker check and `lint_body_rest.py`; T16a–c, T17 |

`foundations_plan.md` owns order; the checklist owns the items.

### 11.2 Open questions

- **Q1.** The `skin` point count. **Q3.** Face skins (S4). **Q4.** Bodies shading each other: a Known gap when
  irradiance lands. **Q5.** Ventilation's owner. **Q6.** Skin feedforward (L1 §9.1). **Q7.** Whether the embedded
  build opens the Maxim session in build or at first step (§4.4 assumes it opens before `agent_ready`).

### 11.3 Risks, said plainly

- **The first body has no felt heat the substrate acts on:** a substrate-primary NPC would walk into fire, hence
  D14.
- **Visibility may not fit the 10-NPC budget for moving NPCs** at any per-body cap meeting the outcome bound (§8).
- **If M4 is answered no,** every tick is a full Maxim step or D14's interim stays; the fallback is a logged wake
  predicate.
- **D15's receipts** leave an NPC unsure a strike landed until a touch or vision row exists.
- **Real NPCs can't run past their first LLM call** until OD-EA7 lands (§4.4).
- **The taint scan can't see an oracle smuggled through arithmetic;** review holds that.
