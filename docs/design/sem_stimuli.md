# The SEM stimulus interface (design v4, 2026-11-21)

**Status:** v4, the contract only (owner, 2026-11-21: the split). It folds delta round 2
(`reviews/sem_stimuli/delta2/`; its `fold.md` maps each finding, and the reviewers set its status). Laws, their
numbers and their tests moved to `docs/plans/checklists.md` ("The SEM stimulus laws" and the 5a, 5b and agent-line
sections); this document doesn't repeat them. The owner ruled D1–D14 (§10); D12 is provisional, D15 open.
Research: `research/sem_stimuli/`, L1–L7.

**Read at:** Overdrive `0918685`; Maxim at local `origin/main` **`043eab8f`**, not fetched. **Tags:** **V** primary,
**S** secondhand, **M** memory, **D** derivation or measurement; ANALOG, EARN, OPEN as in `fire_model.md` §5.1.

**Bars (the standards being drafted, 2026-11-21).** Verification bars hold now; a validation miss is a Known gap;
a perception or learning bar may be a **future bar** (a strict red gate naming the upstream issue, a Phase 3 row, a
passing world-side half). Each gate's plant is in the checklist.

## 0. The answer in one page

- **The line.** The world computes the physical stimulus *at the receptor's site*, tissue physics included. Maxim
  transduces it: thresholds, gain, adaptation, latency, pooling.
- **Frozen, the contract:** rows, units, site sets, cadence; the site grammar; `BodyFrame`, `BoundFrame`, `Binding`;
  the tick placement; failure and lifecycle rules; digest lanes and their keys; version rules; receipt kinds; the
  gates; the module seams and import contracts.
- **Replaceable, the laws:** every model, versioned; a swap touches only agents binding a row it produces, and only
  that row's lanes (§5). They run in the sealed core, `core/body/` and `core/stimuli/`, behind fail-closed contracts.
- **How it arrives:** after bodies move and before agents step, the core builds each NPC's `BodyFrame`, reduces it by
  validated bindings into a `BoundFrame`, and digests both. The contract is D5 (c), every body each tick; until a body
  has a pain path, delivery and the Maxim body step run at the cognition rate (D14, §4.6).
- **v1 is one row,** `tissue_temperature`. Burns reach Maxim through its damage path, not a sensor (§3.3).
- **Limits:** Phase 4's first body has **no felt heat the substrate acts on** (no drive, nociception, damage or fear
  yet), and the LLM sees each sensor's name, unit and value, so no learning claim rests on an LLM-primary NPC (§6.4).

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
| `reads`, `derivation_version` | no | the perceivable fields its model opens (§7.4); the model's version |

A row's lane key adds its **producers**, derived, never hand-kept (§5). The world declares no saturation range: the
body YAML does, and `world_set_axis` clamps (`audio_localization.py:748-761`) yet returns `True` (§4.4).

### 2.2 The rows and cadence

**v1, frozen now:** `tissue_temperature`, `celsius`, at each declared depth of each `skin` point, cadence `tick`; its
`valid` range and rounding freeze with the tissue law's PR. `core_temperature` joins when bound. **Later rows** freeze
with their field's design: contact and vibration, joints and vestibular (ANALOG); radiance after line of sight from
**surface** temperatures only (`luminance` the EARN stopgap); `sound_event` per ear; gas per breath.

The world ticks at 0.1 s and steps physics at 0.5 s. `tick` rows read fields held from the last physics step, a
zero-order hold: a sensor never interpolates fields, which would invent states the simulation never had.

### 2.3 What binds every law

The laws (tissue, outer boundary, flux, occlusion, contact, damage) and their tests are in the checklist. The contract
holds them to five rules:
- **Per point, never a mean before a non-linear law:** flux, visibility, sinks and damage are evaluated per skin point
  (a body-wide shade or ambient makes burns 3× late, **D**; hence D11 (a)), and read through field interfaces over
  volumes in metres.
- **Accuracy is a header truth constant in kelvin, never a rig field** (D20), with its Ω error recorded beside it.
- **Carried state is declared and saved** (§5): what a law keeps across ticks is in the store, never rebuilt from a
  coarser published state. Contact's object-side sub-mesh lives for the whole contact (§7.1).
- **Cell faces exchange nothing with bodies in v1** (owner, S4): strict red gates on face contact and face emission,
  and a Known gap with its number.
- **Every body–world coupling gets a cross-tier test with an outcome margin.**

## 3. The body

### 3.1 One body model

**This extends `tile_and_client.md` §2.1's body; it adds no second one.** The tile's 245 kJ/K store is the **core
node**, sole producer of `core_temperature`; skin columns are its surface layer. One ledger line, `bodies`, books
radiant flux (debited from the flame's unreceived share), contact heat (against the object), exchange with the
ambient at the skin, perfusion (skin–core) and metabolism. Absorption overdrawing a flame's share is a ledger residual,
never a prorated flux, which would make A's flux depend on B. Bodies don't shade in v1 (ANALOG, Q4). **`npc_key` is
`body_key`.**

**Tissue has one home:** `body/store.py` implements the field registry's `body_points` container kind, registering
its arrays as fields (`world_v2.md` §2.5). The `FieldReader` opens read-only views of them, with no copy; save status
comes from the registry entry.

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
depths; pooling is the class's. An invalid table refuses the join as a logged `agent_failed(build)` before any
reduction; replay reads `join` through the same gate. **The worker checks only what it alone sees:** Maxim sensor
names, equal unit strings (`celsius` can't bind `celsius_norm`), ranges, no mean on a pain path. A **`bindings_digest`**
goes in `welcome` and every `BoundFrame`; the worker refuses a mismatch with its own table, planted by editing only the
worker's copy.

### 3.3 Phase 4's first body

A flat body YAML in Maxim's format: root skin sensors (`skin_hand_left_temp`), `modality: world`, `drift_rate: 0`,
`celsius`, **no `drive:`** (which would make burns DRIVE-class): `fire_model.md` §5.1's stopgap, **EARN** on OD-C10.

- **`overdrive_world`,** one Overdrive modulator, hosts the backend (§4.4); its `world_owned_sensors` is the bound
  sensor set, and all its affordances go to the outbox.
- **Region modulators for damage:** the 17 regions group onto modulators with vital sub-sensors, `fire` affinities,
  `health: derived` weights and failure modes (ANALOG); the map lands with the first body's YAML. `apply_damage`
  silently returns 1.0 without sub-sensors (`spec.py:1034-1036`, OD-I7), so a build test plants a burn and requires
  integrity to fall, red on a stripped modulator. **No failure mode triggers on a bound sensor field** (§6.4).
- **Rest at the midpoint:** `scripts/lint_body_rest.py`, a port of Maxim's lint, lands with the first body; the range
  is **OPEN** until measured (checklist).
- **Damage:** burned area becomes an `apply_damage(amount, "fire")` delta once M17 rules; until then burns stay world
  state. Burned area is never bound to a sensor. ANALOG.

## 4. Delivery

### 4.1 The tick (D10, amended by insertion)

1. apply records; 2. move bodies; **3. contact and tissue substeps** over (T−1, T] against held fields; **4. build,
reduce and digest every body's frames**; 5. agents step on tick T's `BoundFrame`; 6. physics, on physics ticks;
**7. merge** step outputs; 8. outputs.

**The overlap:** step 6 may run beside step 5, joining before step 7, because agent intents apply at `apply_tick >
observed_tick` and step 5 writes nothing step 6 reads. `npcs_and_sem.md` §9 states no minimum, and its apply rule
gives equality at `L_us = 0`, so this contract sets it: **every agent intent has `L_us ≥ 1`**, refused otherwise, and
a test plants `L_us = 0`.

**Its gate runs live,** since replay runs no agents, with no wall timing: stub replies released at host hooks in two
fixed orders, overlap on and off, then a replay with `maxim` blocked; the stub stream includes a cell-writing intent,
and the replay leg is the one that must go red on the planted early merge (toy model, **D**).

**Threads:** step 4 runs in the simulation lane. A host pump thread encodes, sends, receives and stamps arrivals,
handing off only through a queue step 7 drains, so it touches no world state. The host scatters, then gathers.

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
    events: tuple[StimulusEvent, ...]  # first available at this tick only

@dataclass(frozen=True)                # simcore/core/stimuli/wire.py; what crosses the channel
class BoundFrame:
    schema_version: int
    registry_digest: bytes             # of the bound rows; checked against `welcome`
    bindings_digest: bytes             # of the binding table (§3.2)
    npc_key: str
    tick: int
    value: NDArray[float64]            # one per binding, in binding order, this tick
    events: tuple[StimulusEvent, ...]  # every BodyFrame's events since the last delivery
    receipts: tuple[Receipt, ...]      # every receipt since the last delivery (§6.2)
```

- **Beside `Frame`, never inside it:** a `BodyFrameFeed` keyed by `npc_key`; `FrameView` never reaches it.
- **Deep frozen:** `__post_init__` refuses writable arrays and arrays whose base chain doesn't end in immutable
  `bytes`; a constructor-site scan holds "only `core.stimuli` builds one".
- **Ids** come from sorted names, in the header. The worker checks `npc_key` against its channel's actor and that
  `tick` rises, then drops `tick` (D4).
- **`BodyFrame` is per tick and divisor-independent;** a `BoundFrame` is assembled at delivery, concatenating the
  undelivered ticks' events and receipts under the byte budget, so nothing is lost at any divisor.
- **`StimulusEvent`** is `(tick, offset_us, kind, site_id, local_id, value, caused_by)`, sorted by `(tick, offset_us,
  kind rank, local_id)`; `local_id` is assigned per NPC after sorting by a world-side key (source id, site);
  `caused_by` is the NPC's own pid or null. A `pid` is allocated per NPC, never globally. Latency: zero for
  intent-made events, up to six ticks for physics-made ones. v1 has no producer; a gate holds `events` empty until
  sound lands.

### 4.3 Bounds and failure

- **Events are capped per delivered frame** by a byte budget that is a header truth constant, refused at start unless
  below the measured socket buffer; overflow coalesces by `(kind, site)` into count and peak. Inert and failed NPCs
  accumulate nothing. Gates: a burst keeps the agent alive; a failed NPC's buffer stays empty for 10,000 ticks.
- **A non-finite value in the core is a world bug:** the server stops loudly. The decoder refuses NaN, ±Infinity and
  `1e400`; the worker refuses `bool`.
- **`False` from `world_set_axis` is an error;** values are validated before any write; the host ends the agent as
  `agent_failed(protocol)` in tick T's merge.
- **A partial send is normal** (8,192 of 20,000 bytes, then `BlockingIOError`, **D**): the remainder waits in a
  per-channel outbox. Only ceiling expiry is `hung`; only `BrokenPipeError`, `ConnectionResetError` or EOF is
  `crashed`. **Inbound,** a `step_output` merges only when whole; a partial one at expiry is discarded with the `hung`
  record.

### 4.4 The worker

- **The push:** `world_set_axis(emb, sensor, value, owner="overdrive_world")` per binding. **The body step**
  (`Embodiment.evaluate_failures()`, M4): on a cognition tick the host pushes but doesn't step, so the agent's own
  tick steps the body in Maxim's W-4 order (`substrate_proposal.py:808-839`, `grounding.md:451`); on other ticks the
  host steps it: one `evaluate_failures` per agent step on a cognition tick. A publish between passes keys to the
  last cluster stash, ANALOG until M4 answers.
- **The backend:** `live_world_set_sensors` withholds drive credit on affordances whose `self_effect` touches those
  keys (`tool_bridge.py:548-560`), filled only from a modulator backend's `world_owned_sensors`
  (`bootstrap.py:552-561`). Ours hangs on `overdrive_world`; `execute` appends an intent and **returns a fixed
  `pending`: no name, no metadata**; `live_world_set_sensors` equals the bound set, and credit flows through settle
  (M18).
- **One writer, checked by value:** Maxim never stores `owner`, and other paths write `vital_metrics`
  (`body.py:674-682`, `cerebellum_modulator.py:260`). At each push the worker records the expected stored value (the
  pushed value clamped to the declared range, a bite counted when they differ); **before the next push** it compares
  each bound sensor with that record, a window covering the body step and cognition. A difference is
  `agent_failed(protocol)`.
- **Threads:** the baseline is taken at `agent_ready`, after the Maxim session opens; at every park the multiset of
  thread **names** must equal it (a same-name restart passes, a new thread doesn't), and session close and open run
  outside a park, each re-baselining. A difference is `agent_failed(protocol)`. OD-EA7 is unmet on today's pymaxim,
  so the real-Maxim test is strict red until it lands.

### 4.5 Agent outputs and the lifecycle

**Posture, gaze and breathing are intent kinds,** applied next tick through the stage-1 parser like `Strike`, with
ranges in `ActionLimits` and a gate-registry row each; refusals are `malformed` or `limit` receipts. An inert or
failed agent breathes on a default schedule, so a crashed NPC is still poisoned.

| Event | World side | Log record |
|---|---|---|
| join | bindings validated (§3.2); tissue at its steady profile; frames built and digested | `join` with body and bindings, or `agent_failed(build)` |
| not ready, worker build refused | inert; built and digested, not sent | `agent_ready`; `agent_failed(build)` |
| `agent_failed` | tissue goes on; built and digested, not sent | `agent_failed(reason)` |
| restart | checks rerun; first delivery carries no events or receipts of the previous life, the dropped counts logged | `agent_ready` |
| leave | tissue, events, visibility freed | `leave` |

Membership comes from logged records, never delivery.

### 4.6 Until a body can feel (D14)

**A pain path** is a PainBus publish driven by a bound skin sensor whose onset precedes Ω = 1 at the same point,
shown by §6.3's fingertip test on real pymaxim. Pain from damage-driven failure modes doesn't count: it comes after
the burn. Roadmap Phase 4's gate points at that test.

**D5 (c) stays the contract; until a pain path exists, push and body step run at the cognition rate;** tissue and
frames still run every tick. **Known gap,** entered in `docs/architecture.md` with `phase1/agents`' code: the agent
sees values only at cognition ticks, so values inside a contact window, and their timing, are lost (a 0.2 s touch of
70 °C steel leaves the basal value 5.7–10.8 K above rest at the next step, against a 43.2 °C peak, **D**).

**T16, two gates,** each landing with the contact law as `xfail(strict=True, raises=AssertionError)`, so a missing
law is an error, not an xfail (checked, **D**):
- **T16a, delivery (verification), red under D14:** at divisor 10, for every tick inside a 0.2 s contact, the stub's
  push log holds that tick's `BoundFrame` value. It flips only once the barrier's B5 row exists (concurrency F2).
- **T16b, a future bar (M4, #1176):** on a fixture body with a skin drive whose band edge lies between the next-step
  value and the peak, a PainBus publish stamped between cognition steps; the world-side half is T16a.

No Phase 4 NPC meets fire before a pain path exists (roadmap Phase 4).

## 5. Replay, digest, versioning

**Replay reproduces the world, never the agents** (`boundaries.md` §6.2); frames are recomputed, not logged.

- **Lanes, never dense ids.** A row lane is keyed by `(name, derivation_version, producers)`, where `producers` is the
  sorted `(law, version)` set of the laws stepping the fields in its `reads`, computed by a completeness check from
  the registry. Each lane chains, per tick, SHA-256 over its `(npc_key, site index, value)` arrays in `npc_key` order:
  dtype, shape and little-endian bytes, length-prefixed, after the row's rounding. An **events lane** per NPC covers
  `BodyFrame.events`. Each NPC's **bound lane**, over `BoundFrame` values and receipts, is keyed by `(npc_key,
  BoundFrame version, receipt-vocabulary version, bindings_digest, reduce version, bound row keys)`. The config
  canonicaliser is for the header only.
- **Replay compares lanes whose key is unchanged,** refuses when a changed lane is one an NPC in the log bound, refuses
  an unknown format version by name, and reports skipped lanes. Adding a row, or an unbound row's law swap, keeps
  replay goldens green.
- **Localisation:** chains stored at log v0's interval find the first bad *interval*; the first bad tick needs a
  reference run.
- **The header:** `STIMULUS_SCHEMA_VERSION`, the `BoundFrame` and receipt versions, rows by sorted name with unit,
  site set and version, each law's version, the lanes, id maps, truth constants (K tolerance and its Ω error, the
  event byte budget, refresh and clustering parameters, cutoff floors). Bodies and bindings ride `join` records.
- **The save** holds all carried `core/body` and `core/stimuli` state as the registry and §7.1 declare it, contact
  sub-meshes and pending events included; a save anywhere reloads bit-identical.
- **Plants** (checklist, 5a): a law change moving a digested value by one rounding quantum; an order reversal in
  `reduce.py` on one-sided exposure; a producer's version bumped alone; an unbound row added (green).
- **Tier 2 isn't bit-identical on real Maxim** until M6 and M8 land.

**Version rules (F1, F15):** a new meaning gets a new name; a better estimate bumps `derivation_version` or the law's
version, goldens regenerated in a commit saying so; adding a row is non-breaking; removing or renaming one bumps
`STIMULUS_SCHEMA_VERSION`; an agent home records its bound lane keys, refused on a change the load doesn't name (D13).
**Each format has a version and a gate row:** body instance (5b); binding table, `BoundFrame`, receipt, `welcome`,
`step_output` (`phase1/agents`); the save's body state (the first law).

**Reserve now** in `phase1/sim-clock`'s log: lane chains, header slots, and `join`, `leave`, `agent_ready` and
`agent_failed` records.

## 6. Trust

### 6.1 Capabilities, and what this supersedes

The NPC builder gets only `(npc_key, its BoundFrame source, its actor-bound outbox)`. Superseded by name: the
membrane factory's frame source (`boundaries.md` §7.1, `npcs_and_sem.md` §6.5); the per-agent pinned frame
(`boundaries.md` §4.2–§4.3; `npcs_and_sem.md` §7.2–§7.3); the NPC path's pinned actor table (`tile_and_client.md`
§4); `npcs_and_sem.md` §6.6's barrier levers (D14's interim restores "due agents only").

**D10 splits `region_parts`:** modulators stay in the membrane; the instrument builder becomes a lab builder. The
environment entity is `phase1/agents`' design (T8, T13), which maps `StructureModulator.execute`'s refusals to §6.2.

### 6.2 Receipts

**The receipt path is a stimulus path:** today it carries `absorbed_j`, fire text, existence by name and footprint
bounds by bisection. Superseding `npcs_and_sem.md` §6.6's "measured effect":
- **`execute` returns `pending`;** the **receipt is `(pid, kind)`**, in the first `BoundFrame` delivered after its
  intent applies (`L_us ≥ 1`, §4.1).
- **v1 kinds are target-independent (D15, open):** `malformed`, `limit`, `accepted`. Whether the target existed, was
  in reach or was hit is logged host-side only, and the effect arrives as stimuli. With no vision or touch row there is
  no perception predicate from A's own frame, so `applied` against `unavailable` would be an existence and footprint
  oracle. Target-dependent kinds return, as a receipt version bump, when a row defines "perceived" as "some value in
  A's frame depends on it".
- **Gates:** T4, T5, T11 over receipt bytes and the `execute` return, T11 sweeping a target's existence, position and
  a strike point across a footprint edge; T12's sentinel in `absorbed_j`; at divisor 10, a receipt reaches the next
  delivery.

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
| T9 | one fixed intent stream, divisors 1–50: `BodyFrame`s byte-identical, `BoundFrame` event and receipt content equal as a multiset over a common window (plant: a model reading `dt_ticks`); worker half at 1×, 20× and both release orders, strict red until M6, M8 |
| T10 | `QUANTITIES`, the registry, each sensor set pinned |
| T11 | ids, allocation, unread material fields, tier, B's state, motion and joining out of sight: A bit-identical; B reaches A only through world state. Control: a fire moved into view changes A. Plants: batched `@`, global sparse solve, batch-minimum dt, cross-body cluster, a refresh budget shared across bodies (red when B runs, **D**), B on the same floor object, emitters summed in append order |
| T12 | sentinel scan of every byte to A's worker; plants: A built from B's store, a channel misroute |
| T13 | golden LLM surface on real pymaxim: the tool surface, the auto-sense section and the `body_state` section |
| T14 | no row in `QUANTITIES`; every row has receptors |
| T15 | per hazard, cue onset at the receptor precedes the damage integral's onset; lead recorded (L6 R1) |
| T16 | §4.6: T16a delivery per tick (verification), T16b pain between steps (future bar) |

With a pain path: fingertip contact on 70 °C steel under `noci_heat` exceeds threshold before that point's Ω reaches
1; until then a build check refuses a mean on `noci_heat`. Host load leaks through the wall clock until D3 lands.

### 6.4 What the LLM sees, and what may be claimed

Maxim shows the LLM world-modality sensors three ways at `origin/main`: generated `SensorReadTool`s
(`tool_bridge.py:1068-1082`); the `sense` tool (`tools/discovery.py:88-125`), which auto-sense runs on every percept
with a transcript (`loop_perception.py:265-391`); and the `body_state` section behind
`MAXIM_ENABLE_BODY_STATE_PROMPT` (`memory_hub.py:58-77`), with a `WARN:` verdict near a failure trigger
(`body.py:806`). So the LLM reads "skin_hand_left_temp … celsius … 47.3", and 47 °C means "burning" to it. The worker
refuses to start with that flag set. No learning claim from an LLM-primary NPC alone (L6 R15): a claim needs a
substrate-side measure, a physical counter-prior or between-NPC dose–response, pre-registered in a Maxim harness; M19
asks to withhold all three. **Blocking** (Kamin, **S**): a privileged predictor takes the prediction error, so the
physical cue is never learned.

## 7. Placement and modularity

### 7.1 Modules

| Module | Owns | Layer |
|---|---|---|
| `core/body/spec.py`, `geometry.py`, `sites.py` | body instance and saved-state data; site sets in body metres; sites in world metres | body: spec |
| `core/body/store.py` (5b) | pose, core node, tissue, visibility and contact state as `body_points` fields; its own write window | body: store |
| `core/body/tissue.py` | the column operator and per-point error estimate; steps untouched sub-columns | body: laws |
| `core/body/irradiance.py` | radiant flux per point: view factors, occlusion, visibility and its refresh | body: laws |
| `core/body/contact.py` | each touched component on one time grid it owns, from tissue's operator and the carried sub-mesh | body: above tissue |
| `core/stimuli/wire.py` | `BoundFrame`, `StimulusEvent`, `Receipt` and kinds, binding-table plain data; imports only `checks` and numpy | stimuli: leaf |
| `core/stimuli/schema.py`, `frame.py` | rows, vocabularies, binding validation, the `StimulusModel` protocol; `BodyFrame` | stimuli |
| `core/stimuli/models/<name>.py` | one per row family; reads perceivable fields; writes nothing | stimuli: models |
| `registry.py`, `run.py`, `reduce.py`, `events.py` | the tuple, order and handout; reduction; the pending-event and coalescing state, owned and saved by layer 6 | stimuli |
| `adapters/agents/` | Maxim-side checks, the push, the value and thread checks | adapters |

`core/body` sits beside cells; `core/stimuli` above intents, since `BoundFrame` carries `Receipt` (5c). This
supersedes `boundaries.md` §2.2's map by name.

**Contact has one owner:** `contact.py` steps touched components in step 3, before `tissue.py` steps the rest,
writing skin through the store's window and the object through the solid law's exchange API, **against its own
carried sub-mesh**, kept from onset to release (rebuilt each tick, painless 90 °C wood hurts at 0.4–2.35 s, **D**).
**The store's writers** are an allowlist in `boundaries.md` §6.4's table, held by an ownership scan: load, motion, the
applier, `tissue.py`, `irradiance.py`, `contact.py`.

**Stimuli sit above the laws** (L7): tissue reaches models only through the `FieldReader`; the laws run every tick,
whatever an agent's cadence. **5a's composition note gets three seams:** a per-tick law slot;
the two-rate contact exchange, ledgered antisymmetrically (`world_v2.md` §2.6); the `body_points` container and a
multi-writer `radiant_emitters` table.

### 7.2 Registration and batch invariance

```python
# core/stimuli/registry.py: the one place a stimulus is named
from simcore.core.stimuli.models import tissue_temperature
STIMULI: tuple[StimulusModel, ...] = (tissue_temperature.MODEL,)
```

- **A declaration registry,** no plugins (`importlib` banned in the core); lanes and ids sort by name; each model is
  `prepare` then `kernel`, the kernel with a closed-form test and a B5 row.
- **Batch invariance is contract.** Accelerate's dgemv moved 19 of one NPC's 48 values by 1 ulp once 9 others were
  stacked (**D**). So each body computes at its own shape. A contact component is the patches sharing object-side
  sub-mesh nodes within the tick, never an object, with its own termination and substeps; an untouched point's
  substeps depend only on its own state, a touched one's on its component, which is world state. Clusters never span
  bodies. **No budget is shared across bodies:** any cap on refresh or work is per body and per emitter, from that
  body's own state (a shared cap made A's refresh ticks depend on B's running, **D**). A point's flux sums emitters in
  stable-key order. A lint bans BLAS matrix-vector calls, batch-axis `einsum`, `scipy.linalg` and
  `scipy.sparse.linalg` in `core/stimuli` and `core/body`; T11 plants each.
- **N + M, not N × M:** emitters append to `radiant_emitters`; a new sense is a module, a `STIMULI` line, a site set
  and data.

### 7.3 Import contracts, fail-closed

In import-linter 2.6, `protected` sees direct imports only, and a nonexistent allowed importer resolves to nothing.

| Contract | Rule | Lands |
|---|---|---|
| `body-protected` | `protected` on `simcore.core.body`; allowed: layer 6's modules (`Simulation`, the applier, the frame publisher), `simcore.core.stimuli`, `simcore.adapters` | 5b, with `store.py` |
| `body-layers`, `stimuli-layers` | `layers` with `containers`: body `contact` above `tissue \| irradiance` above `store` above `spec \| geometry \| sites`; stimuli models above `registry \| run \| reduce \| events` above `frame \| schema` above `wire` | 5b; the tissue row's PR |
| `stimuli-protected` | `protected` on `simcore.core.stimuli`; allowed: layer 6's modules, `simcore.adapters` | the tissue row's PR |
| adapters' reach | skip-layer's recursive classification holds adapters to `CORE_PUBLIC_SURFACE`, which gains only `body.spec`, `stimuli.wire`, `stimuli.schema`; `MEMBRANE_SURFACE` subtracts all three | 5b |
| models allowlist | a grimp test: models import only `stimuli.schema`, the field-reader type, `body.geometry`, `body.sites`, `checks` | the tissue row's PR |
| `stimuli-independent` | `independence` over `simcore.core.stimuli.models.*` | the tissue row's PR |
| `agents-reads-body-frames` | `forbidden`, `allow_indirect_imports = false`; its list equals `_core_modules() − AGENTS_SURFACE` plus `adapters.sem.bridge`; `AGENTS_SURFACE` = `stimuli.wire`, `intents`, `limits`, `checks`; a grimp test requires the surface to be closed under imports | `phase1/agents` |
| `maxim-through-adapters` | the worker module joins `allowed_importers`, its test with it | `phase1/agents` |

A test asserts every allowed importer exists. On toy packages (**D**), `spec` importing `store` breaks `body-layers`,
and a surface module importing `readonly` fails the closure test.

### 7.4 Checks that fail the gate on drift

- **Completeness:** every model is in `STIMULI` once; every `reads` names a **perceivable** registered field; every
  law that steps a read field declares a version (§5's producers). `perceivable` defaults false; material ids and
  table constants never are; making a field perceivable is a reviewed data change with a planted test.
- **Honest reads:** a recording `FieldReader` asserts each model opened exactly its `reads`.
- **No central switch:** an AST lint fails on a registered name as a literal comparison or key outside its module,
  schema, data, the generated vocabulary, the binding loader and `tests/`; receptor or unit literals, and `spec.name`
  against a variable, are review's.
- **Purity:** the writer scan, a golden vocabulary, an `__all__` allowlist on `core/stimuli`.

## 8. Budget

**Target, absolute:** ~140 ms of stimuli and delivery per world second at 10 NPCs near a fire, with deterministic
work counters (substeps, rays, refreshes, frames, bytes, parks) that replay exactly, and counter thresholds in the B5
row; a counter gate reads parks from the log. The cost table, its basis and the refresh arithmetic are in the
checklist. Moving NPCs are the hard case: refreshing every point every tick costs ~3× the target (**D**).

**D12, provisional.** The refresh budget is per body and per emitter (§7.2), which loses the pooling a shared cap
would allow when few NPCs move; the worst case and the bound are unchanged. Acceptability is an outcome measurement
on one body, at the scene's maximum emitter count: time to pain and burned area against every-tick refresh, stepping
from behind a wall into 20 kW/m². D12 is re-ruled on that number before the irradiance law's code; if nothing meets
it, the paths are a coarser visibility law with a stated error, fewer NPCs near a fire, or dilation. 100 NPCs is a
later target.

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
| M4 (absorbs M16) | a host's `evaluate_failures()` (`body.py:258`) between cognition steps, on the injected clock, and how a publish between passes is keyed (`embeddable_agent_DRAFT.md` §7) | **Question** to GL3.B0, #1176, `autonomic_layer.md` §1.2a; OD-A10 |
| M5–M8 | drift, PainBus refractory, NAc window, reading stamps on world time | **Citations** of OD-A1, OD-A2, `world_clock_release_DRAFT.md` §3.5, §4 |
| M9 | burn as pain, two fibre classes, per-NPC receptor draws | **Question** to GL2b, GL3 |
| M10 | fear from burns: "a burn is **not** added" (`autonomic_layer.md:233-234`) | **Pushback**, with a harness scenario under `tests/` on a fixture body with a pain path, outside Phase 4's scenes |
| M11, M12 | vision, touch, smell channels; per-ear signals | **Question** to GL3; **EARN** when sound lands |
| M13 | credit tolerating a delay | **New**, Phase 2 |
| M14 | the proximity plan reads a declared `heat_output` | **Pushback** (T3, T5) |
| M15 | thermal adaptation: no plan owns it (searched "habituat", "adaptive set-point", "salience-layer"; `archive/world_channel_weighting.md:221`) | **New**; OPEN |
| M17 | a world-caused burn through `apply_damage` (`spec.py:1025`; only `src/` caller `simulation/tools.py:665`) | **Question** to GL2b, TR22 |
| M18 | the modulator-backend path in the embedded build (`bootstrap.py:538-561`) | **Question** to OD-A10 |
| M19 | withholding every LLM rendering of world-modality sensors: read tools, `sense` and auto-sense, the `body_state` section (`acting_coach_body_state_ablation.md` owns the flag); whether the embedded build registers `sense` | **Question** to OD-A11 |

M2 stays withdrawn (the rest rule covers it). **The wall-clock gap is the largest unmet assumption** (L2 §8).

## 10. Decisions

**Ruled 2026-11-20:** **D1** the port's `frame` is the `BoundFrame` source (O36); **D2** the registry is code
primary; **D3** the wall-clock pushback; **D4** the injected clock is machinery; **D5** (c); **D6** flux internal;
**D7** answered; **D8** the flat stopgap body; **D9** for O34; **D10** split `region_parts`; **D11** (a),
per-point visibility (reconfirmed 2026-11-21).

**Ruled 2026-11-21:** **D12, provisional:** 10 NPCs near a fire, re-ruled on §8's one-body measurement before the
irradiance law; 100 later. **D13:** a bound lane key's change refuses an agent home unless the load names it. **D14:**
D5 (c) stays the contract; until a pain path (§4.6) exists, delivery and the body step run at the cognition rate, a
Known gap held by T16a; a pain path is a prerequisite for Phase 4's fire scenarios. M16 merges into M4. **S4 (the
owner's):** no exchange with cell faces in v1, a Known gap with strict red gates. **The split (the owner's):** this
document holds the contract; laws and their tests are in the checklist.

**Open:** **D15**, v1's receipt kinds: target-independent (`malformed`, `limit`, `accepted`; recommended, §6.2), or
keep `applied` and `unavailable` as a named ANALOG existence and footprint leak, recorded by T11. **D12's trade:**
the per-body budget gives up pooling (§8); the owner confirms it with D12's re-ruling.

## 11. Steps, open questions and risks

### 11.1 Where the work lands

| Step | Work |
|---|---|
| 5a (sim-clock) | §5's reservations (lanes with their keys, header slots), §7.1's seams, recursive `_core_modules` with every module and `__init__` classified |
| 5b (bodies) | `body/spec.py`, `geometry.py`, `store.py`, `sites.py`; the core node; the body-instance format; `body-protected`, `body-layers`, the store's writer scan; posture, gaze and breath intents with their gates |
| `phase1/agents` | `stimuli/wire.py` and binding validation, the `BoundFrame` codec, receipts and goldens, each versioned with a gate row; `adapters/agents`, its contract and closure test, value and thread checks; the overlap gate; the environment entity; D10; T16a and D14's Known gap |
| with `tissue_temperature`, before Phase 4 | `schema.py`, `frame.py`, `reduce.py`, `events.py`, the stimuli contracts, §7.4's checks; the laws, in the checklist's order (B28 first); the save's body state; §6.3's gates; the first body, its YAML digest, worker check and `lint_body_rest.py`; T16b |

`foundations_plan.md` owns order; the checklist owns the items.

### 11.2 Open questions

- **Q1.** The `skin` point count. **Q3.** Face skins (S4). **Q4.** Bodies shading each other: a Known gap when
  irradiance lands. **Q5.** Ventilation's owner. **Q6.** Skin feedforward (L1 §9.1). **Q7.** Whether the embedded
  build opens the Maxim session in build or at first step (§4.4 assumes it opens before `agent_ready`).

### 11.3 Risks, said plainly

- **The first body has no felt heat the substrate acts on:** under substrate-primary movement (roadmap Phase 4) an
  NPC would walk into fire while its body reads unhurt, hence D14.
- **Visibility may not fit the 10-NPC budget for moving NPCs** at any per-body cap meeting the outcome bound (§8).
- **If M4 is answered no,** every tick is a full Maxim step (unpriced) or D14's interim stays; the fallback is a
  logged wake predicate (concurrency S6 (d)).
- **D15's recommended receipts** leave an NPC unsure a strike landed until a touch or vision row exists.
- **The taint scan can't see an oracle smuggled through arithmetic;** review holds that.
