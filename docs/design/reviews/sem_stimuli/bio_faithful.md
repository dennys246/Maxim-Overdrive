# SEM stimulus interface v1 (`sem_stimuli.md`): Bio-faithful integration

**Read:** Overdrive `phase1/sem-stimulus` at `3357439`. Maxim by `git show` only, at local `origin/main`
**`043eab8f79ea7f2af0686f567c47a02523a86659`** (2026-11-20 20:23 -0700). It is the author's unfetched ref; I did not fetch. Also read: the charter, CLAUDE.md, `npcs_and_sem.md`, lessons 11–24, the earlier bio reviews, and L1, L2, L6.

**Counts:** 3 BLOCKER, 8 SHOULD-FIX, 10 NIT.

## What I checked and found true at 043eab8f

Every §4 and §9 path below was re-read at the ref, and these claims hold:
- `world_set_axis`: root sensors only, a dotted name fails, range clamping, NaN clamps to `hi`, and the `owner=`
  docstring says it is no ACL (`audio_localization.py:720-762`).
- `spec.py`: sub-sensor `modality:` raises (`:556-558`); the drift default is 0.001 (`:290, 309`); readings are
  stamped with wall time (`:837`); a backend replaces `read()` (`:823`).
- `sem.py:271-280`: the pain formula. `body.py:293-298`: wall-time drift dt.
- `bootstrap.py:546-561`: the ownership fill. `base_humanoid.yaml`: `:57-62` and `:41`.
- `nac.py:425, 439` and `pain_bus.py:125, 196`.
- `experience_clock_decay.md`: §(g) `:287` and §(c) `:211`.
- `sensory_streams.py:68`; TR23 at GL3.B3 (`thalamic_relay.md:2123`, which reads through `_resolve_sensor_slot`, so
  M1's routing is sound); `autonomic_layer.md:3, 233-234`; `encoder.py:571-584`.

The push direction, the NaN rule, build checks 1–3 and the T1/T2 split are sound.

## BLOCKER

### B1. Step-tick sampling makes pain depend on the agent's step rate, contradicting `npcs_and_sem.md` §2.1 and the design's own T9

**Where:** `sem_stimuli.md::§4.4`, `::§8` item 1 ("An NPC's stimuli are evaluated only at its step ticks"), `::§11.2 Q2`,
`::§10 D5`, `::§6.2 T9`.

Continuous rows are sampled only at the NPC's step tick. Take an agent stepping every 5 ticks (0.5 s) whose hand
brushes a 70 °C plate for 0.2 s between two steps. Tissue integrates every tick, so receptor-depth temperature rises
and falls back, and `burned_area_fraction` may move. But no `tissue_temperature` sample ever shows the peak. The
NPC is damaged without a sensation. That is the "incinerated with full health" failure §4.3 names.

The design breaks two rules here:
- **`npcs_and_sem.md` §2.1** (owner-accepted). "Discrete percept events accumulate … so a coarse-rate process never
  misses a flash that lived one tick". Its step-size invariance test runs at 1, 2, 5, 10 and 50 ticks.
- **The design's own T9.** "one history at different step sizes … one stream" cannot pass when the samples are
  taken at step ticks by construction.

Biology agrees: a nociceptor fires during contact whatever cognition is doing.

D5's options do not escape this:
- (a) is the failure above.
- (b) is a world-side onset detector ("dF/dt above an SI floor"). That is a threshold, so leak test T2 puts it on
  the receptor's side. It is transduction done by the world.

**Fix:** make D5(c) the v1 rule, not a "target". Every body pushes its frame and steps its transduction each tick in
its worker; only cognition runs slower. The cost is the §4.4 round trip (50–200 µs, **D**) per NPC per tick. Measure
it, and cut cost by dilation rather than by thinning (§8's own rule). If the owner declines (c), the design must say
that sub-step contacts are unfelt and record a Known gap with numbers. T9 then becomes a strict red gate.

### B2. `exposed_area_fraction` is frozen as a v1 row although no receptor senses it

**Where:** `sem_stimuli.md::§2.2` (row 2, **v1**), `::§2.4` ("clothing as a column layer"), `::§6.2 T14` ("every
row has a receptor").

No thermoreceptor, nociceptor or mechanoreceptor reads "share of my area uncovered". L1 §1 asked for it when the
plan was a coarse region list. Under §3's 58 quadrature points it is redundant or a leak:
- **Redundant when clothing is a column layer (§2.4).** A covered point's tissue temperature already carries the
  clothing, and spatial summation emerges from per-point temperatures × areas.
- **A leak when coverage is partial within a point.** One column can't represent both the covered and the uncovered
  part, so the receptor model would have to blend `temperature × fraction`. That invents physics at the receptor, the
  "threshold a mean" error the resolution rule forbids ("reconstruct, decide at the point").
- **"Contact" in the definition** is sensed by touch (contact pressure, a row of its own), not by an area fraction.

**Failure scenario:** the `receptor` vocabulary needs an entry for this row to pass T14, so someone invents one. A
row that no receptor reads then becomes frozen "for the life of the format" (F1). An NPC also gets a scalar
"how exposed am I" that a human perceives only through the thermal and touch channels.

**Fix:** remove the row from v1. Partial coverage becomes more points, or covered and uncovered sub-columns with their
own areas, inside the tissue law. Exposure stays an internal tissue input, as §1 rules for flux (D6).

### B3. M2 pushes back against a decision Maxim reviewed and measured, and Maxim's rule already prescribes what the design wants

**Where:** `sem_stimuli.md::§9 M2` ("`docs/limits/l11_sensor_dilution.md`, not read here").

This breaks "Search Maxim before proposing": the owning plan was not found. At 043eab8f:
- **The plan exists.** "Plan decision D1" in `encoder.py` belongs to `origin/main:docs/plans/deferred/setpoint_aware_neutral.md`.
  Its four-lens review (2026-09-16) returned DO-NOT-BUILD and was deferred. It found that "a STATIC declared set-point
  is numerically identical to the range declaration the body already uses … build nothing in the encoder"
  (outcome item 2). It found that the adaptive reading fails on measurement (item 3).
- **`rest:` is read.** It is not parsed by `src/`, but `origin/main:scripts/lint_body_rest_neutral.py` (CI) requires
  every gained ranged sensor to declare `rest:` or a homeostatic `set_point`, and requires that value to equal the
  range midpoint. `docs/agents/bio-memory.md:165` states the rule.

So "skin rests near 33 °C, so its range must centre there" is not a case against D1. It is the rule Maxim already
lints. Filed as written, the pushback would argue against a measured, reviewed decision from a false premise ("`rest:`
is unparsed").

**Fix:** withdraw M2. Replace it with an Overdrive-side rule: every body YAML passes Maxim's rest-at-midpoint lint.
That lint scans only `src/maxim/_data/components/`, so whether it can take an external path is at most a small
question. The open problem the design does have is S1.

## SHOULD-FIX

### S1. The A4 gain makes painful skin temperatures nearly silent on the world channel, and §4.2's range rule makes it worse

**Where:** `sem_stimuli.md::§3` (first body: `modality: world`), `::§4.2` item 4 ("a `range` containing the row's
operating band, so the clamp is rare"); `origin/main:src/maxim/similarity/encoder.py:596, 751-752`.

The world channel is gained: `w = (|v−0.5|·2)^3` with `gain_modalities = {"world"}`. With rest at the midpoint
(B3) and a range wide enough to cover cold pain and burns, say [−4, 70] °C:
- 45 °C weighs (12/37)³ ≈ **0.034**;
- 60 °C weighs ≈ **0.39** (**D**, computed here).

The first noxious band contributes almost nothing to the situation encoding that NAc, Wire-4 and the ECs key on. A
narrow range ([13, 53]) restores salience but clamps everything above 53 °C, which is the clamp as the transfer
function that §4.2 forbids. The design must also say whether the skin sensors carry a `drive:` block. Interoception
is ungained, so a drive is where the signal survives. But then every burn is DRIVE-class pain on
`drive:skin_hand_left_temp`: never NOCICEPTIVE, never in the fear set. That is homeostatic discomfort standing in for
heat pain, an unnamed divergence.

**Fix:** state per first-body sensor its channel (world, drive or both) and its range, with the gain weight at 40,
45 and 60 °C. Tag "a skin drive stands in for nociception" as EARN on GL2b(ii). Treat range choice as transduction,
measured like Exp 60's saturation fix (#726), not picked for clamp rarity.

### S2. D7 can be answered now: the LLM sees every sensor's name, unit and value, and §4.2 forces the unit "celsius" into its tool list

**Where:** `sem_stimuli.md::§10 D7`, `::§4.2` item 1, `::§6.2 T7`; `origin/main:src/maxim/embodiment/tool_bridge.py:295-321`
(`SensorReadTool`: description "Returns value in {sensor.unit}", output `value` and `unit`), `:1002-1020`
(`EntitySenseTool`: the description lists every sensor name), `:1068-1082` (both generated for every entity with
sensors).

Every skin sensor therefore appears in the tool roster as "Read the skin_hand_left_temp sensor … Returns value in
celsius", and a call returns `47.3`. The build check requiring the YAML unit to equal `celsius` exactly guarantees the
LLM-meaningful string. L6 §2.2's "units as meaning" leak is shipped, not hypothetical. T7 checks names against a
denylist but not units or numbers.

The design also dropped L6's claim discipline (R15). Unlike `fire_model.md` §7 ("Not claimed", folded after fire
review S8), it has no section saying that an LLM-primary NPC avoiding fire measures the prior.

**Fix:** answer D7 in the design with these citations. Say per channel what the LLM sees (L6 §3.2). Add R15 as a
rule: no learning claim from an LLM-primary arm alone; substrate-side measures, a physical counter-prior or
between-NPC dose–response, pre-registered in a Maxim harness. Ask Maxim whether an embedded roster can withhold
world-channel read tools: OD-A11's closed roster is the natural owner, so this is a question to it.

### S3. "Burn damage can't reach a derived health" is false: Maxim has a per-part damage path, which the fire review already raised

**Where:** `sem_stimuli.md::§3` (last paragraph), `::§2.2` (`burned_area_fraction`, "delivered as part integrity");
`origin/main:src/maxim/embodiment/spec.py:1025` (`SpecModulator.apply_damage(amount, damage_type)`),
`base_humanoid.yaml:108-120` (torso `damage_affinities: fire: {core_integrity: 0.8}`, `integrity: weighted_mean`).

C5 forbids a direct `health` sensor. It does not stop typed damage. `apply_damage(…, "fire")` lowers
sub-sensor vital_metrics, `compute_integrity` derives integrity, `health: derived` follows, and `injury` fires at
health < 0.2 with pain 0.7 (`base_humanoid.yaml:199`). This is `reviews/fire_model/delta1_bio_faithful.md` NS1,
repeated.

Two consequences:
- per-part burns don't wait on OD-C10;
- the design has not said how `burned_area_fraction`, a state, becomes `apply_damage`'s delta, or who owns that
  write. It is a Maxim body-state write, not a receptor input, so TR22/TR23 provenance applies.

Separately, `burned_area_fraction` names no receptor. On the flat stopgap body it must not become a `modality: world`
root sensor. That would hand the NPC a damage gauge no nervous system has, and the read tool would display it (S2).

**Fix:** route damage through `apply_damage` (ask GL2b and TR22 whether a world-caused burn may call it, and with
which kind), or state why not. Forbid binding `burned_area_fraction` to any sensor. Tag "damage reaches the agent as
Maxim's integrity model, not through a receptor" as ANALOG.

### S4. M6 and M8 duplicate Overdrive's own upstream draft, and D3's evidence is claimed ahead of its test

**Where:** `sem_stimuli.md::§9 M5–M8`, `::§10 D3`; `docs/maxim_upstream/world_clock_release_DRAFT.md` §3.5 (the
"Reaction and pain gates" row and the `SensorReading` stamping row) and §4 (the PainBus row, quoting §(g));
`docs/roadmap.md` OD-A1, OD-A2; `origin/main:docs/plans/overdrive_refactor_candidates.md` §A3 ("the host's injection
point into the existing `ExperienceClockDriver`").

The world-clock draft already argues M6 against the same §(g) row, with a fairer framing: the gate is an
`[engineering]` de-duplication gate whose Bio-mapping is FUNCTIONAL, so the draft claims no perceptual basis. It
sequences the change after #1200's PainBus rewiring. D3's "file M6 as a pushback now" would put a second, differently
argued proposal on the same row. M8 is that draft's A-pre stamping row, and "OD-C2, filed" is not visible in Maxim at
043eab8f (no `OD-C2` anywhere in the tree).

The 20× merge is good evidence, but it belongs in the existing draft. It has one more argument to add: under
`experience_clock_decay.md` §(a) the robot runtime's driver is `realtime` on `time.monotonic`. Moving the refractory
onto the driver clock is a no-op on hardware, so §(g)'s "hardware safety" reason is untouched. Also, "a strict red
gate … carries the evidence" (D3) is lesson 20's claim-ahead. Write "will carry, once it lands". The gate must fake
`time.monotonic`, because tests may not use the wall clock.

**Fix:** M5–M8 become citations of OD-A1, OD-A2 and the world-clock draft (Maxim side: #1361 S3b and S4, candidates
A3). Fold M6's evidence into that draft's §4 row.

### S5. Maxim's deferred proximity-sensing plan isn't cited, and this design fires its revive trigger

**Where:** `sem_stimuli.md::§9`; `origin/main:docs/plans/deferred/sem_environmental_proximity_sensing.md:3` ("Revive
when a homeostatic drive must be relieved by *sensed* ambient environment"). L2 §9 flagged it, and the design dropped
it.

That plan's mechanism is an agent sensing a fire entity's declared `heat_output` by proximity. This design rejects
that mechanism as an identity-carrying stimulus (R5, T3: a lamp and a hot plate must excite the same receptor). The
first NPC stepping away from a fire to relieve a skin drive is exactly its trigger.

**Failure scenario:** the trigger fires in Maxim, and someone revives the plan as written. Maxim then ships the
`heat_output` reader the game's leak tests forbid.

**Fix:** add an M-row. It is a pushback against that plan's approach (by name, with T3 and T5 as the evidence), and
a statement that the world-computed tissue temperature satisfies its trigger.

### S6. Nothing adapts thermal input: the world is forbidden to, and Maxim has no plan to

**Where:** `sem_stimuli.md::§0` (Maxim owns "adaptation"), `::§9` (no row); L2 §5 ("no plan for thermoreceptor or
olfactory adaptation"); `origin/main:docs/plans/deferred/adaptive_nociception.md` (nociceptors only);
`setpoint_aware_neutral.md` outcome item 3 (habituation belongs "DOWNSTREAM … `tools/novelty.py`,
`attention/salience_map.py`", as "a separate salience-layer plan").

A hand held at 40 °C stays a constant world-channel reading forever. L6 §1.2's contingency argument ("adaptation
keeps contingency alive") needs some layer to adapt. The design assigns adaptation to Maxim, but no Maxim mechanism
or plan provides it for this signal, so the division is a caricature of the receptor's real job.

**Fix:** add an M-row. It is a question to the salience-layer route that the set-point review named, searched
against `adaptive_nociception.md`. Mark it OPEN until a measured need (a fixed warm reading diluting the world
channel) makes it EARN.

### S7. Binding reductions are free per binding, so a mean can hide a hot spot

**Where:** `sem_stimuli.md::§3` ("area-weighted mean or the maximum … the binding names it as an ANALOG"), `::§4.1 Binding`.

A palm point on a 70 °C plate, averaged over a hand region's points, barely moves `area_mean`, while that point's
nociceptors would fire at full rate. Which pooling a receptor class performs is transduction: summation for warmth,
labelled-line peak for nociception (L1 §1, §2). Leaving the choice to each NPC's binding lets a body author make
burns unfelt.

Under NS2's definitions the tag is also wrong. Overdrive intends Maxim's receptor registry (GL3 `ReceptorSpec`) to do
the pooling, so the tag is **EARN**, with trigger GL3.B1 and OD-C10, not ANALOG.

**Fix:** fix the reduction by receptor class in the schema (`noci_*` → max, `thermo_skin` → area mean), refuse
other pairings at build, and retag it EARN.

### S8. L6's rules R1, R8 and R14 and lesson 23 are dropped, and no lesson was recorded

**Where:** `sem_stimuli.md::§6.2`, `::§4.1`; L6 §6; `docs/lessons_maxim_in_games.md` 23.

- **R1, a cue before harm with measured lead time,** has no test. For contact burns at the step cadence (B1) the
  lead may be zero.
- **R8 and lesson 23.** Lesson 23 says Maxim's sensors pull, and that `ModulatorAffordanceTool` reads every sensor
  right after `execute` as "cascade effects". Under §4.1's push at step ticks, that read sees the frame from before
  the act: the efference copy matches nothing, and the cascade logs "no effect". The design must say that this
  read is not credit (OD-A16 and OD-A18 settle), add R8's per-act receipt test, and amend lesson 23, since push and
  pull now both hold, at different layers.
- **R14, per-NPC receptor draws.** These were searched in `thalamic_relay.md` and `autonomic_layer.md` and not
  found. They belong in M9 as a question to GL2b and GL3.
- **No lesson entry.** The commit adds no lesson, although it reverses push against pull, corrects the receptor
  depth, and finds NaN clamping to the top of the range (CLAUDE.md "Record lessons", B18).

## NIT

- **N1. The tags break NS2.** The `luminance` stopgap and M12's world-set azimuth are stand-ins Overdrive intends to
  replace (light field; per-ear `sound_event`), so both are EARN, not ANALOG or OPEN
  (`origin/main:docs/plans/bio_faithful_roadmap.md:12-15`).
- **N2. Old asks restated without their ids.** M1, M9 and M10 restate `fire_model.md` §11's MP-5, MP-2a/MP-2b and
  MP-1(i)/(ii) without the ids (fire review S7, repeated). MP-2b, the two fibre classes, has no row here at all.
- **N3. Contradictions left standing.** `fire_model.md:206` still says burn damage gives "`drive:health` pain, which
  already conditions fear", which is false on humanoids (NB2). Lesson 24 still lists "flux" as delivered. Add both to
  D6's list of rewordings.
- **N4. The M13 check is cheap, and it confirms "New".** `memory_2d2_retroactive_tagging.md` is a shipped ~5 s
  memory-retention window, not credit. Its leftovers are in `deferred/retro_tagging_extensions.md`. Close the note.
- **N5. M3 is mis-routed.** OD-C9 is a version rule. Searched `docs/plans` for "unit vocabulary", "closed units"
  and "unit registry": nothing found. The §4.2 build check already holds the line Overdrive-side. Drop M3, or file it
  as New.
- **N6. D4 is already settled.** OD-A2 already splits a machinery clock from a perceived-time port. Cite it.
- **N7. Light needs an SCN band.** OD-B8 ("light entrains the circadian scale") needs an ipRGC/melanopic band among
  `spectral_radiance`'s "few fixed bands". Reserve it.
- **N8. Clock leak in sound events.** `sound_event` arrival times should be offsets within the step, or interaural
  differences, never absolute world µs. Otherwise cognition reads a clock (D4).
- **N9. Blocking and the backend.**
  - "A faithful learner will block" is right, but NAc's ΣV is OPEN (`bio_faithful_roadmap.md:28`), so today's
    substrate won't block. Say so.
  - A modulator backend needs a modulator on the flat body to attach to (`bootstrap.py:554-557`).
  - Under TR23, `owner="overdrive_world"` must map to the `experienced` kind.
- **N10.** L1 §9.1's skin feedforward into the thermal drive has no row.

## The questions asked of this lens

- **Real job?** Not yet. Pain is thinned by cognition's rate (B1), salience is crushed by the A4 gain (S1),
  adaptation has no owner (S6), pooling is free per binding (S7), and Maxim's damage path is bypassed (S3).
- **Unsensable inputs?** `exposed_area_fraction` (B2), and `burned_area_fraction` if it is bound (S3).
- **Tags?** The binding reduction, luminance and azimuth should be EARN (S7, N1).
- **Asks?** M1, M4, M7, M9, M11 and M13 are sound. M2 is wrong (B3), M6 and M8 are duplicates (S4) and M3 is
  mis-routed (N5). The proximity plan (S5) and adaptation (S6) are missing.
- **Wall-clock pushback?** Sound in substance. It belongs in `world_clock_release_DRAFT.md`, with its evidence in the
  future tense.
- **LLM prior?** The leak tests are not enough: T7 misses units and numbers (S2), and R15 is gone.
