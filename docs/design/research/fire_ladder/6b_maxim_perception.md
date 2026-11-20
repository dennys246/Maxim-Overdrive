# How a Maxim agent should perceive fire and material states: a candidate Maxim change

Research and design only; nothing edited. Maxim read through git at **origin/main `437ec7b1` (2026-11-20 13:49
-0700)**; Overdrive at `phase1/fire-research` `124ad83`. Companion to `6_biofaithful_sem.md` (same directory),
which holds the bio sources not repeated here. Tags: **V** read in a primary source or its abstract; **S**
secondhand; **M** memory; **D** my derivation or design judgement.

## 0. In brief

- **The split that keeps both sides honest:** the world computes the *stimulus at the receptor* (tissue
  temperature at receptor depth, irritant and odorant concentration at the mucosa, radiance in the line of sight,
  sound pressure at the ear). Maxim computes *transduction*: thresholds, intensity coding, adaptation and
  sensitisation, pain kind, latency track, learning. Neither side needs the other's rules (D).
- **No change to the frozen SEM types is needed** (`SensorReading`, `ModulatorResult`, `AffordanceSchema`). What
  is needed lives in Maxim `src/`: GL2b's `NociceptorSpec` (a new frozen type plus an `Entity` slot),
  `world_set_axis` for sub-sensors, the fear-set rule, and later an olfactory receptor (§3).
- **Most needed first:** burn nociception and radiant warmth on the skin, then vision of flame. Smell and
  hearing can wait (§1.3).
- **Of the six proposals, four are questions or amendments to existing Maxim plans**, not new plans (§4).

## 1. The modalities fire touches

### 1.1 Receptor biology

| Sense | Transduction | Threshold, physical units | Adaptation | Latency |
|---|---|---|---|---|
| Innocuous warm | warm C fibres (TRPV3/4-class, **M**) | detects skin rises of ~0.1–0.3 °C over large areas; spatial summation lowers the threshold with area (Bazett & McGlone, Bohnenkamp & Pasquay, cited in Hardy & Oppel 1937, *JCI* 16:533; **S**, excerpt) | strong: responds to rate of change, adapts to steady skin temperature inside a neutral zone of roughly 30–36 °C (**M**) | slow (C fibre) |
| Innocuous cool | TRPM8, "activated by thermal stimuli in the cool to cold range" (**V**, McKemy et al. 2002, *Nature*; Peier et al. 2002, *Cell*, abstracts) | ~below 25 °C at the channel (**M**) | strong, as warm | Aδ, faster than warm (**M**) |
| Heat pain | TRPV1, "activated by increases in temperature in the noxious range" (**V**, Caterina et al. 1997); about 43 °C (**S**) | monkey C mechano-heat nociceptors: median 41 °C; type II Aδ: median 46 °C; type I Aδ: above 53 °C (**V**, Treede et al. 1995, *J Physiol* 483:3, abstract) | **sensitises, does not habituate** (Maxim's own GL3 plan says the same, `origin/main:docs/plans/thalamic_relay.md` ~l.925) | type II Aδ ~120 ms at 15 m/s, "the only… short enough to explain first pain"; C ~100 ms response latency but ~1 m/s, so second pain arrives later (**V**, Treede 1995; **S** for the 1 m/s) |
| Radiant heat on skin | the same thermo- and nociceptors, via skin heating | warmth at very low flux over large areas (**S**, Hardy & Oppel); pain at 2 kW/m² in 45 s, 10 kW/m² in 5 s (**V**, NOAA ALOHA/FEMA table) | as above | set by skin heating, seconds |
| Smoke irritation | TRPA1 on nociceptors, activated by "environmental irritants, such as acrolein" (**V**, Bautista et al. 2006, *Cell*, abstract; acrolein is a smoke product, **M**) | species-specific | sensitises (**M**) | fast (trigeminal/airway) |
| Smell of smoke and volatiles | olfactory receptors, combinatorial (**M**) | species-specific detection thresholds (**M**) | **fast**: intensity falls sharply within a sniff to minutes, thresholds rise after ~20 min, recovery is quick (**S**, several psychophysics papers via search) | ~0.5 s (**M**); gated by sleep (**V**, Carskadon & Herz 2004) |
| Flame sight | photoreceptors; flicker and luminance | flame puffing ~1.5 D^−1/2 Hz (**S**) sits far below flicker fusion (~50–60 Hz, **M**), so flicker is visible | light adaptation (**M**) | ~100 ms |
| Crackle | cochlear hair cells | rapid-rise transients are the cue frogs use (**V**, Grafe et al. 2002) | moderate (**M**) | ~10 ms |

Two consequences for design (D):
- **Thermoreceptors and nociceptors at one site are different receptors with different kinetics.** Warmth adapts;
  burn pain sensitises. One drive on one sensor (Maxim's `arms.thermal` today) can't be both.
- **First and second pain have a timing gap.** Maxim's planned GL3 tracks already encode it
  (`nociceptive_fast` and `affective_slow`, `thalamic_relay.md` §AfferentTracks).

### 1.2 What the agent does with each

- Warmth and cold drive **thermoregulation** (approach or leave a fire, shelter). These are homeostatic drives Maxim
  has, cold side only.
- Burn pain drives **withdrawal** and **fear learning**. Radiant pain leads damage by 3–6× in time (NOAA table), so
  the cue reaches the agent before the harm does.
- Smell, irritation, sight and sound are **distal cues**: their whole value is predicting heat before it arrives.
  Chimpanzees with experience monitor fire and anticipate its movement (**V**, Pruetz & LaDuke 2010).

### 1.3 Which first, and why (D)

1. **Heat nociception plus radiant warmth on the skin.** Maxim has the drive and pain machinery. A burn is the
   unconditioned stimulus every other fire lesson hangs on, and today a burn is 0.04 of DRIVE discomfort that no
   learner hears (`origin/main:docs/plans/autonomic_layer.md` R-1).
2. **Vision of flame.** It's the main distal cue for a waking human, and the one the ladder's watched rungs need.
3. **Smoke irritation**, through GL2b's planned `chemical` modality. It waits on buoyant smoke in the world anyway.
4. **Olfaction and audition.** They need a world vapour field and sound propagation (Overdrive Phase 2), and in
   Maxim an olfactory receptor with fast adaptation, which no plan has.

## 2. What Maxim has today, per modality (origin/main 437ec7b1)

| Modality | Has | Missing |
|---|---|---|
| Thermoreception | `infant_humanoid.yaml` `arms.thermal` and `head.thermal`: `unit: celsius_norm`, range [−1, 1], homeostatic drive (`set_point 0`, `comfort_band 0.5`, `pain_scale 0.4`, `drift_rate 0.0008`) (`origin/main:src/maxim/_data/components/bodies/infant_humanoid.yaml`); `core_temperature` | physical units; receptor adaptation (rate coding); a heat-side corrective need (R-2); per-part world writes |
| Nociception | `PainKind`, PainBus and its learners; `classify_pain` treats `drive:health` as NOCICEPTIVE; `NociceptorSpec` designed (`autonomic_layer.md` §3.2: modality heat, cold, mechanical or chemical; threshold in sensor units; channel 1 `drive:<s>:noxious`; channel 2 latch) | **not built**: `git grep NociceptorSpec origin/main -- src` finds nothing. GL2b "not started" (status 2026-10-18). Burns excluded from the fear set by design (`autonomic_layer.md` §1: "a burn is **not** added to the fear set"; `origin/main:src/maxim/decisions/nac.py:425` `{"drive:health", "drive:oxygen"}`) |
| Radiant heat | `cradle_fire_pit.yaml` `heat_output: 0.9` that nothing reads; `deferred/sem_environmental_proximity_sensing.md` (v1: "binary in-scene = exposed", a Maxim-side field→drive map) | any reader; any exposure model; deferred with zero code |
| World writes | `world_set_axis(embodiment, sensor_name, value, *, default_range, owner)`, "any declared root sensor", clamps to the declared range (`origin/main:src/maxim/embodiment/audio_localization.py:692`) | sub-sensors such as `arms.thermal` |
| Smell | `SensoryModality.SMELL` mapped to `"text"` (`origin/main:src/maxim/agents/modality.py`) | any receptor, adaptation or substrate. Searched: `olfact` appears only in `grounding.md`, `thalamic_relay.md` and `autonomic_layer.md` text |
| Irritation | the `chemical` value reserved in the `NociceptorSpec` design | everything else |
| Vision (non-camera) | `SensoryModality.SIGHT` → vision substrate (camera detections only) | percepts gated by line of sight for a world body (`deferred/passive_sense_discovery.md`; Overdrive's P-E and OD-C8) |
| Audition | azimuth by direction of arrival, `listen`/`turn`, `world_set_axis` | loudness and event features; nothing fire-specific is needed |
| Receptors and tracks | `ReceptorSpec` and `AfferentTrackSpec` designed with `latency_passes`, `gain`, `refractory_passes` (`thalamic_relay.md` ~l.676–712); GL3.B0 built (census and red gates) | GL3.B1+ wait on the decomposition fence. A track "adds no adaptation of its own" (invariant, ~l.1444): adaptation belongs at the producer |
| Adaptation | `deferred/adaptive_nociception.md` (pain gain; habituation and sensitisation keyed on damage) | thermoreceptor and olfactory adaptation: searched `adapt` in the plans above; nothing for innocuous receptors |
| Delayed effects | `tool_bridge.py` ~l.580–590, 884 read `entity_state` in the call; `latent_forward_model.md` (~l.209) calls it a "live defect for this purpose" | the settle path (Overdrive OD-A16, OD-A18) |

## 3. The interface split

### 3.1 Who computes what (D)

| Quantity | World server (physics) | Maxim (receptor and cognition) |
|---|---|---|
| Radiant and convective heat on the skin | incident flux per body region (W/m²), from flame volumes and gas, as an area integral over the region | none directly: no receptor reads flux |
| Tissue temperature | skin surface and basal-layer (~0.1 mm) temperature per region from a skin conduction model; contact temperature from effusivity | warm and cool receptors (rate-coded, adapting) and nociceptors (threshold, sensitising) read it in °C |
| Tissue damage | the Henriques/Arrhenius integral written to the region's integrity or `health` | `drive:health` pain (NOCICEPTIVE) |
| Airway | irritant and soot concentration at the mouth sphere (mol/m³ or ppm) | chemical nociceptor (TRPA1-class threshold) |
| Smell | odorant concentration per species at the nose | olfactory receptor: per-species threshold, log or power-law intensity, adaptation, sleep gating |
| Sight | which entities are in view, with luminance, angular size and flicker band power of luminous volumes, after line of sight | the percept, salience and learning |
| Sound | sound pressure and onset transients at the ear | loudness and features, already in azimuth's pattern |

**The rule (D):** the world stops at the **physical stimulus at the receptor's location**. It never writes "pain",
"warm", "smells of smoke" or a drive value. Maxim never needs a material constant, a flux, a flame model or a
cell. Two leak tests a reviewer can apply:
1. Could this world value be measured by an instrument at that spot with no knowledge of the body's nervous system?
   If yes, it's the world's.
2. Does this Maxim parameter have a value in a physiology paper (a threshold in °C, an adaptation time
   constant)? If yes, it's the receptor's.

Thresholds and adaptation are therefore **Maxim's, in physical units**. Today's normalized `celsius_norm` and
owner-chosen thresholds blur exactly this line.

### 3.2 Against the frozen SEM types

- **`SensorReading`** (`sensor_name, entity_name, value: Any, unit, timestamp, extra`) carries a °C, W/m² or ppm
  value with a real unit string. **No change.** World time already goes in `timestamp`.
- **`AffordanceSchema`**: perception needs nothing from it. Fire acts are covered in `6_biofaithful_sem.md` §2.
  **No change.**
- **`ModulatorResult`**: only delayed credit touches it (`metadata`, or OD-C5 `settles`). That is not a perception
  change.
- **`Entity`** is not a frozen dataclass, but it has `__slots__` (`origin/main:src/maxim/embodiment/sem.py` ~l.819).
  GL2b's `Entity.nociceptor_specs` (`autonomic_layer.md` §3.2) is therefore a `sem.py` src change. Overdrive's
  `_compat` mirrors only the three dataclasses, so the mirror is unaffected (D).
- **What does need Maxim src changes:**
  - (a) `NociceptorSpec`, a new CC3 path-(a) frozen type (planned);
  - (b) `world_set_axis` reaching sub-sensors through `_resolve_sensor_slot` (Overdrive OD-C10, unverified there);
  - (c) receptor-side adaptation for innocuous thermal and olfactory receptors (unplanned);
  - (d) the fear-set rule (a decision).
- **Body YAML, not types:** a physical-units sensor (`unit: celsius`, `range: [-20, 80]`) and its drive
  (`set_point: 33`, a band in °C) need no type change. Under Maxim's 2026-09-19 decision they belong on a
  **variant body** (`extends:`), so the cradle's EARNED calibration isn't moved (`origin/main:DECISIONS.md`
  2026-09-19). A variant renames tool signatures and re-runs its baseline arms. That cost is real and stated there.
- **Stopgap with no Maxim change:** per-region root sensors (`arms_skin_c`, `head_skin_c`) written by
  `world_set_axis` and marked `TEMPORARY(phase3)` in Overdrive (`states_of_matter/sem.md` N6).

## 4. Proposals, ready for Maxim's process

Process key, from Maxim: a sub-plan or `src/` change gets a **three-lens review before the PR**
(`origin/main:CONTRIBUTING.md` "Pre-merge three-lens review"). A new experiment gets a **pre-registration, a
four-lens design review** (confounding, bio-faithful, wiring, environment) **and a ledger entry**
(`origin/main:CLAUDE.md`; `docs/experiments/DESIGN_REVIEW.md`). Game runs never go on Maxim's ledger, so every
experiment below runs in a **Maxim-owned harness**. Overdrive's numbers only motivate it.

**MP-1 (was P-F1). Burn pain may condition situation fear.**
- *Touches:* `autonomic_layer.md` §1 invariant ("a burn is not added to the fear set"); `nac.py:425`
  `DEFAULT_CLUSTER_FEAR_FAILURE_MODES`, a hivemind wire boundary; ledger rows T1-13 to T1-15 (Exp 60–62), whose
  re-run triggers fire on any change to the set.
- *Duplicate?* **An amendment to an existing plan's recorded decision**, not a new plan.
- *Argument:* a burn excluded from fear means the agent learns fire only from injury, never from the pain that
  precedes injury by 3–6×. Animals and people learn fire from pain (D, with **M** that heat pain is a standard human
  fear-conditioning US).
- *Game evidence:* a scenario where radiant flux crosses the noxious threshold without health loss on some trials,
  showing that situation fear forms only on the trials with health loss.
- *Process:* the allowlist edit is src (three-lens). The behavioural claim is a new experiment (prereg, four-lens,
  ledger).
- *Experiment:* a "hearth classroom" on Exp 60's apparatus pattern, on a variant body with GL2b. A warmth gradient
  (the CS) predicts noxious heat (the US) with no tissue damage. Arms: noxious mode in the set; the current set; a
  fear-ablated arm. Measure: P(withdraw before the US). Confound guard: no `drive:health` change in any arm.

**MP-2 (was P-F2). Nociceptors and thermoreceptors in physical units, two nociceptor classes.**
- *Touches:* `autonomic_layer.md` §3.2 and §8 ("threshold: <owner>", calibrated to the cradle's +0.6 delta), and
  GL3's `nociceptive_fast`/`affective_slow`.
- *Duplicate?* **A question to GL2b**, not a new plan.
- *Proposal:*
  - allow `NociceptorSpec` on a °C sensor of a variant body;
  - default thresholds from physiology: a fast receptor at ~46 °C (type II AMH to `nociceptive_fast`) and a slow
    one at ~41–45 °C (C fibres to `affective_slow`), per Treede 1995 (**V**);
  - keep the infant's normalized calibration untouched.
- *Game evidence:* a closed-form skin model with a cross-tier test that the noxious crossing time agrees across
  grids, and its time series under the ladder's fluxes.
- *Process:* inside the GL2b sub-plan (three-lens). Any behaviour claim rides MP-1's experiment.

**MP-3 (was P-F3). The host owns exposure; Maxim owns attribution.**
- *Touches:* `deferred/sem_environmental_proximity_sensing.md` (v1's binary exposure and Maxim-side field→drive
  map).
- *Duplicate?* **An amendment to a deferred plan.** Its revive trigger ("a homeostatic drive must be relieved by
  *sensed* ambient environment") is what a fire you warm yourself by provides.
- *Proposal:* for embedded worlds, v1 becomes "the world writes skin and core-relevant stimuli through
  `world_set_axis`; Maxim reads no `heat_output`". The plan keeps its hard question: how tool-less ambient pain
  attributes to NAc, with `transition_based_drive_pain.md`.
- *Game evidence:* a run where `core_temperature` moves with distance from a fire and no affordance is called.
- *Process:* sub-plan amendment (three-lens). Maxim's own cradle keeps v1 if it wants, because a world with no
  physics needs a stand-in (D).

**MP-4 (was P-F4). Delayed effects (ignition, flame-out, char).**
- *Touches:* `tool_failure_credit.md`, `latent_forward_model.md` S0a, and Overdrive OD-A16/OD-A18.
- *Duplicate?* **Yes. A question to those plans**, carrying the evidence: the ladder's ignition-delay series joined
  by invocation id.

**MP-5 (new). `world_set_axis` for sub-sensors.**
- *Touches:* `audio_localization.py::world_set_axis` ("root sensor" scope) and the `perception_pipeline_placement.md`
  guardrail ("if an `AxisSpec` type starts to appear, stop and use the body YAML", quoted in the function's
  docstring).
- *Duplicate?* **Overdrive's OD-C10 already lists it** as an ask. I found no Maxim plan for it (searched `sub-sensor`
  in the placement plan, no hits). New to Maxim, small.
- *Proposal:* resolve the name through `_resolve_sensor_slot` with the same ownership refusal. No new type, which
  is consistent with the guardrail.
- *Evidence:* burns are per part. A root-sensor stopgap duplicates every part.
- *Process:* src change (three-lens). No experiment: an engineering fix with a deletion-proved test.

**MP-6 (new, later). Receptor adaptation for innocuous senses, and an olfactory receptor.**
- *Touches:* `adaptive_nociception.md` (pain only, deferred), the GL3 invariant that tracks add no adaptation
  ("adaptation belongs at the producer"), and `modality.py` SMELL→text.
- *Duplicate?* Partly: it extends `adaptive_nociception.md`'s producer-side principle to warm, cool and olfactory
  receptors. Propose it as **a question to that plan first**.
- *Argument:* thermoreceptors and olfaction adapt in seconds to minutes (§1.1). Without adaptation a lingering smoke
  smell is a constant cue that predicts nothing new, and fear learning saturates on it. That is the plan's own
  revive trigger (b), "over-tagging from repeated pain", in a non-pain form.
- *Evidence:* a run showing cue saturation from an unadapted smoke sensor.
- *Process:* sub-plan (three-lens). The behaviour claim needs an experiment.

**Not proposed:**
- A SEM label vocabulary, and any frozen-type field (§3.2).
- A smell substrate in EC. It needs evidence that the text mapping fails.

## 5. Order against the ladder

| When | Item | Why |
|---|---|---|
| Before R3 (fire starter lights a stick, an NPC watching) | **Overdrive-only:** world computes flame-in-view (luminance, size, flicker) after line of sight, plus per-region skin temperature as root `world` sensors (the `TEMPORARY(phase3)` stopgap). No Maxim change. | Watching needs sight and a warmth cue; it doesn't need burns. R3's NPC can perceive without any Maxim PR. |
| Before any rung where an NPC touches fire, or any claim that NPCs *learn* fire | **MP-2** (GL2b with physical units), then **MP-1** (prereg in a Maxim harness) | Without GL2b a burn is unheard (R-1). Without MP-1, fire fear comes only from injury. These are on Maxim's clock (GL2b waits on the decomposition fence), so ask now. |
| Alongside per-part burns | **MP-5** | Small src change. Removes the stopgap. |
| When warming by a fire matters (cold scenes) | **MP-3** | It's the deferred plan's own trigger. |
| Whenever ignition credit matters | **MP-4** | Already in flight as OD-A16; just add the evidence. |
| After Phase 2 smoke and vapour fields | Smoke irritation (GL2b `chemical`), **MP-6** | No world stimulus exists to transduce before then. |

**The honest risk (D).** Maxim's GL2b and GL3 work are both gated on the decomposition fence and not started. If
Overdrive needs NPCs that *learn* fire before that fence lifts, the game will be tempted to fake burn pain through
`health`. That is acceptable only as a named stopgap: health loss is real damage, not pain. It teaches avoidance
late, and it must not be reported as fire learning.
