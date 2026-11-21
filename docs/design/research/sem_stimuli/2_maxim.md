# SEM stimulus interface, lens 2: what Maxim has and plans on the receiving side

Maxim read through git only at **origin/main `043eab8f`** (2026-11-20 20:23 -0700, PR #1718); no fetch, checkout or working tree. Every `path:N` is `origin/main:path` at that commit.

## 0. In brief

1. **Stimuli don't travel as `SensorReading`s.** A world reaches a Maxim body as a float written into
   `Entity.vital_metrics` through `world_set_axis` (`src/maxim/embodiment/audio_localization.py:692-763`). Drives,
   pain and both substrate channels read `vital_metrics` directly (`embodiment/body.py:634-665`,
   `runtime/substrate_proposal.py:209-243`). `SensorReading` is only what `SpecSensor.read()` builds afterwards, with
   a wall-clock timestamp (`embodiment/spec.py:837`). The interface therefore needs **no change to a frozen SEM
   type**. What it does depend on, and what constrains it, is a set of helpers that are not frozen: the body YAML, the
   writer and the readers.
2. **What works today:** root sensors only; `modality: world` (or `audio`), or a `drive:` block, or both; drift 0;
   the world as the single writer. Exp 60 earned this on Minecraft (`_data/components/bodies/minecraft_player.yaml`).
3. **Ownership is weaker than the earlier research implied.** A sensor becomes refuse-anonymous-writes only when a
   *modulator backend* declares it in `world_owned_sensors`, through `build_executor(modulator_factory=)`
   (`runtime/bootstrap.py:552-561`). `owner=` is a log tag, not an ACL, and nothing stores it (`audio_localization.py:719-722`).
4. **Everything temporal runs on Maxim's wall clock:** drift, drive-pain latching, the PainBus refractory, the NAc
   causal window and reading timestamps. None of them sees the world's `time_s`. A world that runs faster or slower
   than real time breaks all five, and only drift and the NAc windows have a plan to move to world time
   (`docs/plans/experience_clock_decay.md`, PROPOSED).
5. **Every receptor-side design is unbuilt:** the `NociceptorSpec` (GL2b), the Receptor registry and
   AfferentTracks (GL3.B1-B3), `PhysicalEventId`, adaptation and proximity sensing. The only piece built is GL2a's
   record-only `InteroceptiveOutcome`.

## 1. The frozen SEM types, and what may be added

| Type | Shape and forward-compat path | What the interface can use |
|---|---|---|
| `SensorReading` | frozen, slots. `sensor_name, entity_name, value: Any, unit, timestamp, extra` (`embodiment/sem.py:38-65`). `extra` is the CC3 escape hatch for additive metadata. It must be JSON-serialisable and is left out of eq and hash (`:42-58`). | Nothing on the write path. `SpecSensor.read` sets `timestamp=time.time()` and never fills `extra` (`spec.py:822-838`). |
| `ModulatorResult` | frozen, slots. `success … error, metadata` (`sem.py:68-78`). Its docstring has **no** CC3 marker, although Maxim's CLAUDE.md:105 requires one. | Acts only, for example Minecraft's `metadata["outcome_valence"]="neutral"` on a timeout (`embodiment/backends/minecraft.py:11-19`). |
| `AffordanceSchema` | SHAPE-FROZEN at 1.0. **Additive fields with defaults, appended at the end, are non-breaking**; a required field is a major bump (`sem.py:107-118`). There is precedent: `speech_param` was added that way (#1261, `:136-140`). | `requires`, `self_effect` and `target_effect` are deltas. On sensors that a live stream owns, `self_effect` is filtered (`embodiment/tool_bridge.py:622-635`). |
| `Entity` | A plain class with `__slots__`: `name, entity_type, sensors, modulators, parent, children, metadata, vital_metrics, failure_modes, drive_specs, drive_breach_severity` (`sem.py:827-839`). Save format 1.1 (`:30`). | Two slots are planned: `Entity.nociceptor_specs` (GL2b, `docs/plans/autonomic_layer.md:677`), and a per-sensor last-writer kind map beside `vital_metrics` that persists with a format bump (TR23, `docs/plans/thalamic_relay.md:2123`). |
| Drive specs | `HomeostaticDriveSpec` and `EntropicDriveSpec` are SHAPE-FROZEN (`sem.py:182-245`). `coupled_to` and `modulated_by` are parsed but never read (`autonomic_layer.md` R-4, `:214`). | Their shape can't grow. That is the reason GL2b puts nociception in a separate spec. |

Overdrive's `_compat.py` mirrors the first three; they serve the world-as-Entity direction (`bridge.py` regions), not stimulus delivery.

## 2. Body YAML sensor declarations

- **Root sensors** (`_parse_entity`, `spec.py:445-460`) accept `unit` (free text, default `"unknown"`), `range`
  `[lo, hi]` (which sets the type to float), `initial`, `modality` and `drive`. `_build_reading_schema` stores
  `range`, `initial` and `modality` (`spec.py:630-677`).
- **`modality:`** may be `audio` or `world` only (`embodiment/sensory_streams.py:68`). An unknown tag raises.
  `interoception` is not declarable; a `drive:` block makes a sensor interoceptive (`spec.py:660-675`). **On a
  modulator sub-sensor, `modality:` is a parse error** (`spec.py:556`).
- **`rest:` is not parsed.** No reader under `src/` matches it. The A4 neutral point is the **range midpoint**
  (`similarity/encoder.py:580`), so `rest:` in `minecraft_player.yaml` is documentation. Only the declared range
  places the resting value.
- **Units are free text, and the pain arithmetic runs in sensor units.** It computes
  `min(1, (|v-set_point| - comfort_band) * pain_scale)` (`sem.py:278-281`). Rescale the range and the pain changes.
  Minecraft uses hp in `[0,40]` with a band of 6 and `pain_scale` 0.5 (`minecraft_player.yaml:26-36`). The infant's
  thermal sensors are `celsius_norm` in `[-1,1]`, not °C (`_data/components/bodies/infant_humanoid.yaml:43-76`).
- **Drift:** `drift_rate` is applied per wall second (`sem.py:435-450`). It defaults to 0.001 when omitted
  (`spec.py:290, 309`), so a world-owned sensor must say `drift_rate: 0` explicitly. Entropic drift also clamps the value
  to `[0,1]` whatever range is declared (`sem.py:446-450`).
- **Body shapes:**
  - `base_humanoid`: `health: derived` from part integrities (`base_humanoid.yaml:57-62`). Pain comes through failure
    modes `concussion`, `exhaustion`, `crippled`, `injury` (health < 0.2, pain 0.7) and `overburdened` (`:191-201`).
    `hunger` has no drive here (`:20-23`). Only the torso has a `fire` affinity (`:118`).
  - C5 forbids a direct `health` sensor next to component sub-sensors (`spec.py:319-361`).
  - `infant_humanoid` adds entropic hunger and thirst, homeostatic `core_temperature`, and sub-sensor drives on
    `arms.thermal`, `arms.pressure` and `head.thermal`, all with nonzero drift (`infant_humanoid.yaml:20-105`).
- **Sensors are owned by whoever writes them.** Nothing in the YAML marks an owner. Ownership comes from a
  backend's `world_owned_sensors`; the Minecraft factory derives it from the attached entity's `modality: world`
  sensors (`backends/minecraft.py:170-198`).

## 3. `world_set_axis`

What the code does (`audio_localization.py:692-763`):
- **Root only.** It checks `sensor_name in root.sensors` and writes `root.vital_metrics[name]` (`:727-762`). A
  dotted name such as `arms.thermal` returns `False` quietly. There is no sub-sensor path and no child-entity path.
- **Clamping.** It clamps to the declared range, else to `default_range`, else writes the raw float (`:747-762`).
  **NaN slips through.** `max(lo, min(hi, nan))` evaluates to `hi` (I checked this in Python), so a NaN `health`
  reads as the top of its range. With no range, the NaN is written raw. The game's `checks.py` finite rule has to
  hold on the game's side, because Maxim won't catch it.
- **Ownership.** An anonymous write (`owner` falsy) to a sensor in `embodiment.live_world_set_sensors` is refused
  with one warning (`:733-743`). Any non-empty `owner` passes, and an unlisted sensor accepts every writer. The set
  is filled only from modulator backends at build time (`bootstrap.py:552-561`). The Minecraft pump goes through
  that route (`backends/minecraft.py:64, 73-112`).
- **What the write leaves out.** It publishes no pain and calls no `evaluate_failures` (`thalamic_relay.md:376`).
  The pain lands on the next agent-loop pass that evaluates the body (`autonomic_layer.md:130-141`).

Other write paths:
- There is no public writer for sub-sensors. `tool_bridge.py::_write_sensor` / `_apply_sensor_deltas` (`:103, :125`)
  and the narrator's `SetEntitySensorTool` resolve dotted names through `sem.py::_resolve_sensor_slot`
  (`:1407-1437`), but they are tool and narrator paths stamped `narrated` (`thalamic_relay.md:1195-1206`).
- `SpecModulator.apply_damage(amount, damage_type)` distributes typed damage by `damage_affinities`
  (`spec.py:1025`). It is reached through `DamageComponentTool`, which also publishes its own `PainSignal`
  (`autonomic_layer.md:150-152`).
- `attach_backends(sensor_factory=)` exists (`spec.py:1160-1182`), but `bootstrap` passes only `modulator_factory`
  (`:539-542`). A sensor backend would change only what `read()` returns; drives and encoders would still read
  `vital_metrics`. That leaves two truths, so don't use it.

**Planned (GL3.B1, unbuilt).** TR23 stores the writer's kind at write time and replaces raw writes with "one
kind-taking setter" (`thalamic_relay.md:2123`). The Minecraft pump writes `experienced`
(`thalamic_relay.md:1196`). Rescue, heal and respawn need an **apparatus window** opened by the host
(TR22, `:1264-1270`). For Overdrive, writes the world causes would be `experienced`, while respawns and other god
writes need that window.

## 4. Modalities and their substrates

- **Body channels.** There are three: `interoception` (drives), `audio` and `world` (`substrate_proposal.py:449-452`).
  All three have frozen centroids (`similarity/ec.py:463`), and only `world` is A4-gained (`sensory_streams.py:50-58`).
  A drive-bearing `modality: world` sensor feeds both world and interoception (`minecraft_player.yaml:14-20`).
- **Vision.** A `vision` percept is built from object detections (`agents/perception_agent.py:236-254, 375`), a path
  whose live source is the camera and YOLO. No body sensor may declare vision (`sensory_streams.py:68`). A world
  has no seam for vision.
- **Smell, touch and sound percepts map to text.** `SubstrateModality = Literal["text","vision","interoception"]`,
  with everything else defaulting to `"text"` (`agents/modality.py:84-106`). The `SMELL` and `TOUCH` rows are stubs
  (`:38-41`). Spatial sound reaches the substrate only as the `azimuth` sensor.
- **Adding a channel.** "One tuple entry … plus its tag in `DECLARABLE_MODALITY_TAGS`" (`sensory_streams.py:17-22`).
  That is a src change, and GL3's modality registry would own it (`thalamic_relay.md:557`).

## 5. Receptor, nociceptor and afferent-track designs

| Design | Where | Status at 043eab8f |
|---|---|---|
| `InteroceptiveOutcome` (signed body-consequence record) | `sem.py:516-571` | **Built** (GL2a, #1194). Record-only; nothing acts on it (`autonomic_layer.md:3`). |
| `NociceptorSpec`: `nociceptor: {modality: heat\|cold\|mechanical\|chemical, direction, threshold, pain_scale}` on a sensor beside its drive; band `drive:<s>:noxious`, source `nociceptor:<s>`, NOCICEPTIVE; a **variant body** only | `autonomic_layer.md:658-749`, GL2b(ii) `:1136-1160` | **Not started** (`:3`). It waits for the decomposition fence, for #1161 and for nociception step 2 (the ReactionBus refractory collision, `:700-708`). The thresholds are the owner's, set at the stage's start. It reads sub-sensor **state** in sensor units, and the shipped example is `arms.thermal`, a sub-sensor no world can write today. |
| Two-sided corrective need (heat) | `autonomic_layer.md:751-764`, GL2b(i) | Not started; fenced. |
| `ReceptorSpec` / `ReceptorRegistry`, derived from body YAML at bind time; `clock: realtime\|turn`, derived from the experience-clock driver | `thalamic_relay.md:557, 676-697` | GL3.B0 built (census and red gates, #1201). GL3.B1 onward waits on the fence (`:3-7`). |
| AfferentTracks: seven are named; only `nociceptive_fast` and `affective_slow` get built, at GL3.B3, as a thermal fan-out with the flag OFF. Latency is counted in **loop passes**, "ordinal, not metric" | `thalamic_relay.md:875-941`, `:1737` | Unbuilt. Minecraft sensors are mapped to tracks (`:926-933`). |
| TR18: every PainBus publish stays at the transduction pass; `affective_slow` feeds **only sinks that are not PainBus subscribers** (record-only) | `thalamic_relay.md:941, 2118` | Decided 2026-10-24. |
| Adaptation. Nociceptors "sensitize; they do not habituate" (`thalamic_relay.md:925`). Adaptation lives at the producer, never in a track or a consumer (`:1004`; `autonomic_layer.md:735`). | `docs/plans/deferred/adaptive_nociception.md` | **Deferred.** It revives on chronic harmless pain or on over-tagging. There is **no plan for thermoreceptor or olfactory adaptation** (rate coding, fast fade). |
| Proximity sensing (a fire's `heat_output` without touch) | `deferred/sem_environmental_proximity_sensing.md:2` | Deferred, zero code. It revives when "a homeostatic drive must be relieved by *sensed* ambient environment". |

## 6. How readings reach learners

- **Pain production.** `evaluate_failures` drifts the body, then publishes:
  - drive pain as `EXTERNAL_SIGNAL` with `failure_mode="drive:<name>"`, once on entering the band and again only
    when the breach deepens (`body.py:400-437, 483-517`);
  - failure-mode pain with `failure_mode=<name>` (`body.py:590-622`).
- **Classification.** `classify_pain` makes `drive:*` DRIVE, except `drive:health`, which is NOCICEPTIVE
  (`proprioception/pain.py:134, 147-159`).
- **PainBus.** Its refractory is 0.5 s per `(entity, failure_mode)`, on `time.monotonic()`
  (`proprioception/pain_bus.py:125, 196-218`). Its subscribers and their thresholds:

  | Subscriber | Threshold | Where |
  |---|---|---|
  | memory | 0.4 | `:388-405` |
  | Wire-2 | 0.3 | `:489-544` |
  | NAc | 0.3 | `:583-625` |
  | Wire-4 situation fear | 0.3 | `:654-708` |

- **Wire-4 is narrow.** It writes fear onto **the `world` cluster active at that pass**, so an `audio`-channel cue
  never counts (`pain_bus.py:696`). The failure mode must be in `{"drive:health","drive:oxygen"}` (`decisions/nac.py:425`).
  Outside the set the write is a no-op (`:3402`), and the hivemind ingest refuses any other mode (`hivemind/ingest.py:652-657`).
- **The allowlist is closed.** It is a recorded invariant: "No stage edits it; a burn is not added"
  (`autonomic_layer.md:233-234`). No host can reach it either, because `build_bio_stack` builds `NACConfig` without
  it (`runtime/bio_stack.py:358`) and so does `agent_factory.py:1227`.
- **Humanoids form no situation fear today.** Their `injury`, `concussion` and `crippled` modes aren't in the set,
  and they have no `drive:health`.
- **The rest of TR18.** Under the planned tracks the slow path never adds a learner (`thalamic_relay.md:941`).

## 7. Credit for delayed effects

- **NAc causal links.** They join an outcome to events within `temporal_window_seconds=300` of **wall** time
  (`nac.py:439, 1316-1343`). Eligibility decays ×0.9 per pass (`:3707`).
- **Wire-4 has no window at all.** Fear goes to whatever world cluster is current when the pain arrives. So a
  delayed harm, such as a toxin's malaise, writes fear onto the place where it is felt, not onto its cause.
- **Effects measured later.** On live-owned drive sensors the modeled `self_effect` credit is filtered, and "no
  measured credit exists yet". The fix Maxim names is "Stage 5's act-now-credit-later pending map"
  (`tool_bridge.py:617-635`; `deferred/sem_motor_binding.md:5, 18`). It is deferred until a second robot body exists.
  **OD-A16** (Overdrive `docs/roadmap.md:188`: receipts, settle, exactly-once credit) is that same pending map,
  approached from the host side. Present it as a question to `sem_motor_binding.md`'s Stage 5 and to OD-A18 / B2,
  not as a new ask.
- **The latent forward model** (GL4, `docs/plans/latent_forward_model.md`) predicts the **phasic consequence of
  one's own invocation** (`:383-425`). It doesn't bridge hours. Its target is GL2a's record. S0a has not started;
  S1 waits for the post-fence `PhysicalEventId` (`:14-40`).
- **No Maxim plan covers credit that tolerates a delay**, such as conditioned taste aversion. Searched `docs/plans` for taste, delay, eligib, lookback, retro. `lookback_primitive.md` decided against a new
  look-back store (`:5`), and `latent_forward_model.md:128` mentions Garcia aversions only to set them aside.

## 8. Timing and rate assumptions

| What | Clock | Where | Planned |
|---|---|---|---|
| Drive drift dt | `time.time()` since `_last_poll`; runs through pauses | `body.py:293-298`; `experience_clock_decay.md:43-45` | `Embodiment.advance(dt)` on the experience clock (`experience_clock_decay.md:93, 223-227`). PROPOSED, no src change. |
| Drive-pain latch, `PainSignal.timestamp` | wall | `body.py:502, 599` | — |
| PainBus and ReactionBus refractory, 0.5 s | monotonic and wall | `pain_bus.py:125, 196` | **Stays wall-clock on purpose** (`experience_clock_decay.md:287`) |
| NAc causal window 300 s; event ids `time_ns` | wall | `nac.py:439, 1316` | Moves to `temporal_window_us` (`experience_clock_decay.md:211`); A3 covers the ids (`overdrive_refactor_candidates.md:114-175`) |
| `SensorReading.timestamp` | wall at `read()` | `spec.py:837` | — |
| Minecraft pump | 0.5 s wall, with a 5 s staleness gate; never evaluates pain | `simulation/minecraft_harness.py:60, 290-333`; `thalamic_relay.md:376` | — |
| Pain latency | the next loop pass that evaluates the body; a pass can block up to 8-15 s on live Minecraft, or 300 s on the LLM path | `thalamic_relay.md:333-346, 890-895` | GL3 counts passes, not ms |

**The consequence.** Maxim has no notion of world time at the body. If Overdrive steps the world faster than real
time, then:
- drift undershoots;
- the 0.5 s refractory merges distinct burns into one;
- the 300 s window covers more world time than intended.

If Overdrive steps it slower, the same three break the other way. Today a host-driven NPC also has nothing that
calls `evaluate_failures` per step. That is part of the stepped-think item in `overdrive_refactor_candidates.md`
(tier B).

## 9. Verdict for the interface

**What the interface can rely on today, with no Maxim change:**
- root `modality: world` sensors with `drift_rate: 0` and ranges whose midpoint is the rest value;
- root homeostatic or entropic drives that the world writes;
- `world_set_axis(owner=…)` with ownership claimed through a modulator backend's `world_owned_sensors`, following
  the Minecraft pattern;
- pain on the next evaluated pass;
- Wire-4 fear from `drive:health` or `drive:oxygen` on a **flat** body only.

**What needs a Maxim change, and which plan owns it:**

| Need | Owning plan |
|---|---|
| Per-part skin written by the world (dotted `world_set_axis` plus `modality:` on sub-sensors) | No plan owns it. GL3.B1's kind-taking setter (TR23) is the natural home, so ask there. |
| Burn as pain | GL2b(ii) `NociceptorSpec`. Its thresholds are in sensor units, so the world's unit choice is an input to that calibration. |
| Heat need | GL2b(i) |
| World time at the body | `experience_clock_decay.md` (#1361) plus A3. The **refractory** is excluded by §(g): push back with the time-scaled-world evidence. |
| Fear from burns, or from humanoid injury modes | Contradicts `autonomic_layer.md` §1.4. Argue against that decision by name. |
| New modality tags (smell, vision for a body) | GL3 registry; `modality_resolution_and_alignment.md` and `cross_modal_perception_fabric.md` revive when GL3.B1 ships. |
| Delay-tolerant credit | No plan. That makes it a new proposal, so check `memory_2d2_retroactive_tagging.md`'s leftovers first. |

**Where an Overdrive ask would duplicate an existing plan:**

| Ask | Already owned by |
|---|---|
| Receptor, track and first/second-pain timing | GL3.B3 |
| Nociceptor adaptation | `adaptive_nociception.md` |
| Proximity heat | the proximity plan; its trigger arguably fires once a world-owned ambient field relieves a drive |
| Credit at settle | the Stage-5 pending map / OD-A18 |
| Provenance of world writes | TR22 and TR23 |

## 10. What the earlier game-side research got wrong or left out

1. **`signals/maxim_senses.md` §0.1, §1, and 6b's split.** Both call the world sensor "world-owned" through
   `owner=`. In fact ownership is enforced only for sensors a modulator backend declares; `owner` is an unstored tag
   (§3). Overdrive has to ship a backend, or every writer is trusted.
2. **`maxim_senses.md` §2 and §4.7 rely on resting values.** The `rest:` key they lean on is not parsed. Only the
   range midpoint counts (§2).
3. **`maxim_senses.md` P-B** proposes adding `air_hunger` and `malaise` to the allowlist. That is the same recorded
   invariant NB1 named for burns (`autonomic_layer.md:234`), and the allowlist is also the hivemind wire boundary.
   P-B has to name and argue against that invariant.
4. **`maxim_senses.md` P-D** says "Maxim's eligibility windows are short". In fact NAc links reach back 300 s of
   wall time, and the binding gap is elsewhere: Wire-4 has *no* window, and everything is keyed to wall time, not
   world time (§7, §8).
5. **P-A (`world_set_axis` for sub-sensors) isn't enough on its own.** `modality:` on a sub-sensor is a parse error
   (`spec.py:556`), so per-part skin still couldn't join the world channel. It would reach only interoception,
   through a drive.
6. **Neither document addresses time.** Drift, the refractory and the causal windows all run on Maxim's wall clock
   (§8). This is the largest unmet assumption for a stepped world.
7. **6b §0 calls the sub-sensor write, the fear-set rule and an olfactory receptor "in Maxim `src/`".** For the
   fear-set rule the obstacle is a recorded decision, not missing code. The olfactory receptor has no plan at all,
   and adaptation of any kind other than the deferred nociceptor plan has none either.
8. **The NaN-clamps-to-top behaviour** of `world_set_axis` was never noted. The game's finite check is the only
   guard (§3).
9. **Delta-1's corrections still hold at 043eab8f:** humanoids have no `drive:health` (`base_humanoid.yaml:57`), and
   local fear needs a src change (`bio_stack.py:358`).
