# SEM stimulus interface, lens 5: the contract as a format, its replay, its trust boundary and its evolution

Research only. Read at `phase1/sem-stimulus` (35a1702): the briefed docs, code and Bio reviews. Maxim read with `git show` at
the local `origin/main` ref **043eab8f** (dated 2026-11-20 20:23; not fetched by me, so it may lag).

## 0. The answer in brief

- **The stimulus is computed in the core, and it can only be.** The skip-layer rule (`boundaries.md` §2.2) forbids
  `engine.adapters.*` from importing `engine.cells`, `engine.laws` or `engine.geometry`.  A stimulus at a receptor is a
  reduction over cells and fields in metres, so the adapter can't compute it. Tissue (skin conduction, the Henriques
  integral) is world physics (`fire_model.md` §5.1), so it is core *state*.
- **Yes, a per-NPC body frame beside the world frame.** It is forced by O13. Each real agent runs in its own worker
  process (`npcs_and_sem.md` O13, §6.3). A `CellFrame` is 64–80 MB per tile at 0.1 m (`boundaries.md` §4.2) and
  holds every region, material and body, so it can't and mustn't cross the pipe. `AgentPort.step`'s `frame` has to be
  a small, versioned, pickle-free value holding one NPC's stimuli: a `BodyFrame`.
- **It reaches Maxim by push,** through `world_set_axis(owner=…)` on the worker side, the pattern Maxim's own
  Minecraft backend uses (`embodiment/backends/minecraft.py:1-35`, `:92`).  Maxim builds the `SensorReading`
  itself on read (`spec.py:820-840`), with the YAML's `unit` and `time.time()`, so "real units" is a build-time
  check against the body YAML.
- **Replay reproduces every reading by recomputation, and a digest proves it.** Stimuli are derived, like receipts
  (`boundaries.md` §6.2), so they're never log inputs.  A per-tick stimulus digest over the bytes
  pushed makes a drifting replay go red on its first drifting tick.
- **Interest management may change cost, never values.** `npcs_and_sem.md` §2.1 already rules "multi-rate is
  allowed; thinning is not". Every NPC that steps gets its full body frame, computed on its fixed schedule. The only
  savings allowed are those that are bit-identical by construction.

## 1. Where it lives: two frames, one publication

A **frame** (`core/frames.py`) is an immutable snapshot published when a write window closes. The `Frame` covers the tile, holds tens of MB and never leaves the simulation lane. The `BodyFrame` covers one NPC's
receptor sites, holds a few hundred bytes, is built by a new `engine.laws.receptor` (layer 4), and crosses to that
NPC's worker through the channel codec (`npcs_and_sem.md` §6.6).

**Inputs:** the latest `Frame`, the NPC's pose and tissue (world state), and its receptor sites in metres; a pure
function, so the same world gives the same bytes.

**Tissue is state; stimulus is derived.** Skin temperature and the damage integral are world state (digested,
saved). Incident flux and contact temperature are re-derived. That split decides what a save holds (§3).

**The lab builder stays separate.** `RegionInstrument` (`bridge.py:715`) is an oracle by its own docstring;
`fire_solid.md` §2 pins `QUANTITIES` cell-only. The stimulus registry is a different table with different types, so
a region quantity can't be bound to a body.

## 2. How it reaches Maxim, and when

### 2.1 The push, checked against Maxim's code

`world_set_axis(embodiment, sensor_name, value, *, default_range, owner)` (`audio_localization.py:692`) does four
things worth knowing:
1. It writes **root sensors only** (`root.sensors`), so per-part sites need OD-C10.
2. It writes **a bare float** into `vital_metrics`, with no unit and no stamp.
3. It **clamps silently** to the sensor's declared `reading_schema["range"]`.
4. It returns `False`, **fail-soft**, when a sensor is undeclared or the body owns it live and the caller gave no
   `owner`.

Then Maxim's YAML sensor `read()` builds the `SensorReading` with the YAML `unit` and `timestamp=time.time()`
(`spec.py:820-840`). The Minecraft backend is the precedent: per tick, measured truth goes into declared world-owned
sensors with `owner="minecraft_bridge"`, and "the body YAML is the contract for what this agent can sense".

What follows for the contract:
- **Units are agreed at build, not carried.** At agent build the adapter checks each binding: the registry's unit
  must equal the bound YAML sensor's `unit:` string exactly. Maxim's unit strings are free text (`hp`, `points`,
  `level` in `minecraft_player.yaml`), so there's no shared closed vocabulary to check against. Overdrive keeps one
  (world_model F1 already demands it), and asks for one upstream under OD-C9.
- **Range belongs to Maxim, and it isn't cosmetic.** In `minecraft_player.yaml` the range midpoint is the A4-neutral
  rest point. Saturation is transduction, which is the receptor's job (fire_model §5.1, test 2), so the world sends
  the physical value and never clamps it. The world's registry carries a physical *validity* range instead (flux ≥
  0, finite). A value outside it is a bug, and the core raises on it. The adapter meters how often Maxim's clamp
  bites.
- **`False` is an error, never a skip.** The fire_model Bio review's S1 scenario (an NPC "incinerated with full
  health") is exactly a swallowed `False`. Every bound write that returns `False` fails the step loudly
  (CLAUDE.md, "No silent exception swallows").
- **Bound sensors are world-owned** (`live_world_set_sensors`, `drift_rate: 0`; `boundaries.md` §4.3).
- **Unchecked alternative:** `spec.py:821` reads a `_backend` when attached, which could return Overdrive-built
  readings. I didn't check whether drives and pain read through it or `vital_metrics`; push is the proven path.

### 2.2 Cadence: three clocks and two lanes

- **World.** `tick_us` = 100,000 (0.1 s); physics every 5 ticks (0.5 s); a frame is published after each physics
  step and after each tick that applied an intent (`boundaries.md` §4.2).
- **Pose moves per tick, fields per physics step.** Stimulus values are evaluated at the NPC's pose *at the tick
  it steps*, against the held fields (fire_model §9.2 saves the radiation field), so an NPC that walks into radiant
  flux at tick 3 of a period feels it at its next step, not at the next physics step.
- **Tissue integrates every tick against the piecewise pose,** whether or not the agent steps. Once per physics step
  with the end pose would average exposure across positions, the average-then-threshold error CLAUDE.md forbids.
  Physics substeps vary by rig (`realtime_lanes_coop.md` §2.3), so the tissue model needs its own cross-tier test.
- **The agent steps** at an integer divisor of the tick with a per-actor phase (`npcs_and_sem.md` §2.1) and gets the
  body frame pinned at that tick (`npcs_and_sem.md` §7.3), never "the latest", so the dial can't change it. Discrete
  events since its last step ride along as an ordered list (§2.1: "discrete percept events accumulate").
- **Across lanes.** The simulation lane builds and encodes body frames in `Simulation.step`; each worker pushes its
  own inside `step`; the barrier (`npcs_and_sem.md` §6.3) holds tick T+1 until every agent has parked.
- **Timestamps.** The body frame's header (tick, frame sequence) is host-owned and stripped before Maxim sees it
  (`npcs_and_sem.md` §3.1). Maxim then stamps the wall clock (`spec.py:839`): the recorded OPEN divergence "two clocks
  reach one agent" (§12.2), closing with OD-C2 and OD-A2. The contract adds no clock.

**The game-engineering idea: sampling a fixed timestep.** Between physics steps the world *is* its last state (a
zero-order hold). Renderers hide that by interpolating between states; a sensor must not, since interpolation
invents states the simulation never had. So hold the *field*, and evaluate it at the observer's *current* pose.

## 3. Replay: reproducing every reading

`boundaries.md` §6.2: replay reproduces the world bit for bit and never the agents, and derived values are
recomputed and checked against a per-tick digest. Stimuli fit that rule exactly:

- **Not logged:** body frames; they derive from logged inputs (pose from movement intents).
- **Digested every tick:** `stimulus_digest = SHA-256(canonical(BodyFrame) for each stepping NPC, in npc_key order)`.
  It covers the **bytes actually sent**. Any Overdrive noise is drawn host-side, before encoding, from the keyed
  stream `(npc, stream, tick, sensor)` (`npcs_and_sem.md` §3.4). I recommend none: receptor noise is transduction,
  Maxim's; world-side noise (photon shot noise in dim light) only if earned.
- **In the header** (§6.3, the content digests): the stimulus registry (with each row's `derivation_version`), the
  receptor-site tables and the tissue constants, all through the one canonicaliser.
- **In the rerun manifest:** each NPC's bindings and its body YAML digest, since those belong to the agent. A
  binding mismatch refuses a tier-2 rerun, and a registry mismatch refuses a tier-1 replay.
- **In the save:** tissue state (F5). Body frames are derived (F15), recomputed on load, and their digest after load
  must equal the running one (`fire_solid.md` §5.5's pattern).
- **A test:** replay with `maxim` blocked from import (as §6.2 already requires), compare `stimulus_digest` tick by
  tick, then plant a one-ulp change in a tissue constant and watch it go red on the first exposed tick.

So "what did the NPC sense at tick T?" is tier 1, from the log alone; "what did it do with it?" stays tier 2.

## 4. Versioning: the stimulus schema

**A registry row is an identity (F1):** `name` (a quantity, never a verdict), `unit` (closed, linted vocabulary),
`valid` (physical validity, not saturation), `receptor` (§7.4's rule), `site_kind`, `reduction` (in metres, never a
cell count) and `derivation_version`, under one `STIMULUS_SCHEMA_VERSION`.

**Evolution rules:**
1. **New meaning, new name.** A point value becoming an area mean, or skin-surface temperature becoming basal-layer
   temperature, gets a new row. The old row stays until no fixture uses it.
2. **Better estimate, same meaning:** bump `derivation_version`. Goldens are regenerated in a commit that says so
   (§6.3).
3. **Adding a row is non-breaking.** An NPC binds only what its body declares, the Minecraft rule.
4. **Removing or renaming a row** bumps `STIMULUS_SCHEMA_VERSION`. Readers refuse unknown versions loudly.
5. **Site vocabulary.** Site names must match Maxim body part names once OD-C10 lands. Until then every site is a
   root sensor (a flat body, or a named stopgap: the root-sensor skin, EARN on OD-C10 per delta1 NS2).

**The body frame's wire form** is a table, by F2–F4: column-major; an integer key column (stimulus id, site id,
both from name maps carried in the agent's build handshake, like `welcome`'s recipe map); `f64` values; no strings
per frame. Golden fixtures and a round trip ship with it. It joins the worker channel's codec (`npcs_and_sem.md`
§6.6), which already refuses pickles.

## 5. The trust boundary: proving what an NPC can't see

fire_model §5.5 forbids omniscient instruments and any exposure of flammability, ΔH_c or φ. Maxim's tool generation
and discovery read every sensor an Entity carries (fire_solid Bio B1), so whatever a builder attaches *is* exposed.
The proof has to rest on capabilities, not convention.

**By construction:**
- **The NPC builder is handed only** `(npc_key, its BodyFrame source, its actor-bound intent outbox)`. It never
  gets a `FrameSource`, an `Applier` or the world. This is the same capability passing the membrane already uses
  (`applier.py` docstring; CLAUDE.md), narrowed to one body. `region_parts` and `RegionInstrument` move under
  `tests/` (delta1 NS3's fix).
- **One body frame per channel;** no API takes two `npc_key`s.

**Checked by tools:**
- **An import contract on the NPC builder module.** It may not import `engine.sim.frames`' `Frame`, `engine.adapters.sem.bridge`'s lab
  classes or `engine.materials`. That last one matters: today's skip-layer rule *allows* adapters to import
  `engine.materials` types, which is a hole for exactly the "material constant" leak.
- **A golden tool surface** (fire_model §5.4): build an NPC entity on real pymaxim, run Maxim's tool generation, and
  compare the tool names and parameter schemas to a committed fixture. No `ignite`, no `extinguish`, no
  `strike(energy_j)`, no `*_temperature_max`.
- **A registry disjointness test:** no stimulus name is in `QUANTITIES`, and every row has a receptor (§7.4).
- **A sentinel taint scan** (the planted-render idea from `npcs_and_sem.md` §6.1, applied to values). Build a scene
  in which:
  - one material constant (say a ΔH_c), a region's interior maximum, and NPC B's tissue temperature each carry a
    distinctive sentinel value;
  - nothing gives any of them a physical path to NPC A (B is out of radiative view, and the material isn't burning).

  Scan every byte sent to A's worker, and every `vital_metrics` write in A, for the sentinels' encodings. Then
  plant a leak (bind B's site to A) and watch the scan go red: that proves the guard by deleting it.
- **A non-interference property test** (Hypothesis): perturb anything about NPC B or a remote region that has no
  physical path to A, and A's body frame stays bit-identical. Then perturb something that *does* reach A
  physically (move a fire into A's view) and check that A's frame changes. That's the negative control, without
  which the test can't fail.
- **Material constants** may shape a value only through physics (emissivity shapes flux), never appear as a field.
  The taint scan catches verbatim copies only, not arithmetic smuggling: a stated blind spot, as the ownership scans
  state theirs.

**A later case to rule out now.** Phase 5 hacking is "a `target_effect` on another body's sensors" (`roadmap.md`).
It must be an intent that changes world state (B's cyberware), which B's own body frame then reflects, never a write
into B's frame or bindings. Only `engine.laws.receptor` writes a body frame.

## 6. Interest management under determinism

**The concept.** In netcode, *interest management* (relevancy, area of interest) decides which entities each client
is told about; it may be lossy because it only changes what a client *draws*. Simulation LOD (distant actors
simulated coarsely or not at all) changes what *happens*; games accept that because their NPCs are props. Here they
aren't, so the two stay apart:
- **Replication interest** (what the client receives): free to cull, since the client is display only.
- **Simulation interest** (whose stimuli are computed): bound by §2.1, "never lowers an NPC's substrate rate to keep
  pace". When the host can't keep up, the world dilates.

**What's allowed (bit-identical by construction):**
1. **Compute on the agent's own fixed schedule** (divisor and phase from logged data), events accumulated between.
2. **Reuse when the inputs are unchanged.** Key each NPC's last body frame on `(frame sequence of the fields it
   reads, pose, tissue version)`, with a cached-equals-fresh test per kind of change (`realtime_lanes_coop.md` §2.3's pattern).
3. **Physical cutoffs, the same for everyone.** Drop a radiating source below a flux threshold at the receptor, for
   every NPC alike, with the dropped energy ledgered (fire_model §9.2).
4. **Deterministic parallelism.** Body frames may be computed in parallel, but they're assembled and digested in
   `npc_key` order, and their reductions use fixed-order sums (fire_solid §5.4, DP-S2), never `np.sum` over a
   gathered subset.

**Not allowed:** any rule keyed on distance to the player, the wall clock, host load or the dial. Player distance
would even replay (the pose is logged), but the same NPC would feel the same fire differently depending on where the
camera was. **Dormancy** (an NPC in another tile) is a logged world-state transition needing its own design, not an
optimisation. Phase 4 has three NPCs; B5 measures before any of this.

## 7. The proposed contract

```python
# engine.laws.receptor (layer 4): stimulus physics at sites, in metres; no IO, no clock
def stimuli(frame: CellFrame, held: HeldFields, pose: Pose, tissue: TissueState,
            sites: SiteTable, registry: StimulusRegistry) -> tuple[StimulusValue, ...]: ...

# engine.sim (layer 6): published beside Frame, one per stepping NPC
@dataclass(frozen=True)
class BodyFrame:
    schema_version: int                 # STIMULUS_SCHEMA_VERSION
    npc_key: str                        # persisted identity, not the actor allocator's integer
    tick: int                           # host-owned header; stripped before Maxim
    basis_sequence: int                 # the Frame it was derived from; host-owned
    values: tuple[StimulusValue, ...]   # (stimulus_id, site_id, value: float), sorted by (stimulus_id, site_id)
    events: tuple[StimulusEvent, ...]   # discrete events since this NPC's last step, ordered by (apply_us, id)

# engine.adapters.agents: build-time binding, checked against Maxim's body YAML
@dataclass(frozen=True)
class Binding:
    stimulus: str
    site: str
    sensor: str        # a Maxim root sensor (sub-sensors after OD-C10); unit must equal the registry's
                       # it must be in live_world_set_sensors, with drift_rate 0

# worker side, inside AgentPort.step: for each binding, world_set_axis(emb, sensor, v, owner="overdrive_world");
# a False result fails the step; no time field is passed on.
```


## 8. What to decide now, and what can wait

**Decide now.** Each is cheap and stops a wrong shape setting:
1. **The body frame is what `AgentPort.step`'s `frame` means.** This touches the agent half, which is frozen (O19).
   It is a definition, not a redesign (O13 already rules the world frame out), but the owner should rule it, not have
   it inferred; Maxim's review of the embeddable-agent draft (O36) needs the same definition for its `step`.
2. **The stimulus registry is separate from `QUANTITIES`,** with F1 identity and a closed unit vocabulary.
3. **Delta1 NS3, ruled:** `region_parts`, `RegionInstrument` and `to_maxim_entity`'s lab surface move under
   `tests/`. Fire_solid Bio S3 already gives it a trigger: before step 5 ships vocabulary v1. Without this, nothing
   stops Phase 4 picking up the oracle builder.
4. **The NPC builder's import contract forbids `engine.materials`,** closing the hole the general adapter rule
   leaves open.
5. **Slots in the formats:** a `stimulus_digest` field in the per-tick digest, and the registry in the header's
   content digests, reserved when `phase1/sim-clock` defines the log. Adding them later is a log-format bump.
6. **Physical values, no world-side clamp, `False` is an error.** This is a rule for the adapter PR (`phase1/agents`).

**Can wait, each with its trigger:**
- the actual rows (flux, contact, airway), until the first NPC body (Phase 4), designed by the NPC fire note;
- site vocabulary and per-part binding, until the body-shape decision (delta1 NB2) and OD-C10;
- whether Overdrive adds any noise, until a world-side noise source is earned;
- the `_backend` sensor alternative, until someone checks whether Maxim's drive and pain paths read through it;
- caches, cutoffs and parallel assembly, until B5 measures a cost;
- dormancy and tile streaming, until a second tile exists;
- sub-tick reflex substeps on one body frame (`npcs_and_sem.md` §9), with the sim-clock decision;
- pulled in-world instruments (a thermometer's display seen by an NPC), until OD-C8.

**Risks, said plainly:**
- **The push path has three Maxim gaps** that this contract can only name, not close: root-only writes (OD-C10), a
  free-text unit with no closed vocabulary (an OD-C9 ask), and wall-clock stamps on read (OD-C2). Until they
  close, every Phase 4 body is flat or carries named stopgaps.
- **The taint scan can't see an oracle smuggled in through arithmetic.** Only review and the receptor-first rule
  hold that line.
