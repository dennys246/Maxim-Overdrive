# Fire model v1 design review: Bio-faithful integration

Reader: Bio-faithful integration lens (`docs/code_review.md`). Design: `docs/design/fire_model.md` at
`phase1/fire-design` 54358fd, with lesson 24 and research L6 and L6b. Maxim was read only through git at
origin/main 437ec7b1 (2026-11-20). The membrane as built was read in the `gates` worktree
(`src/simcore/adapters/sem/bridge.py`).

Counts: 1 BLOCKER, 8 SHOULD-FIX, 5 NIT.

## What I checked and found true at origin/main

These research claims hold, so the findings below don't dispute them:

- `DEFAULT_CLUSTER_FEAR_FAILURE_MODES = {"drive:health", "drive:oxygen"}` (`src/maxim/decisions/nac.py:425`).
  The invariant "a burn is **not** added to the fear set" is at `docs/plans/autonomic_layer.md:233-234`.
- `NociceptorSpec` is designed in `autonomic_layer.md` §3.2 (threshold "in sensor units", `<owner>`), and
  `git grep NociceptorSpec origin/main -- src` finds nothing. GL2b is "not started", and `src/` work waits for
  the decomposition fence (the plan header). The R-1 arithmetic (a burn is 0.04 of DRIVE pain) is right.
- `world_set_axis` reaches root sensors only, clamps to the declared range, and refuses an anonymous write to a
  live-owned sensor (`src/maxim/embodiment/audio_localization.py:692-765`). `_resolve_sensor_slot` exists
  (`embodiment/sem.py:1407`).
- TF2 ("only tools that ran") is in `docs/plans/tool_failure_credit.md:59`. The counter-prior hearth's
  "NEVER in the description" comment is in `cradle_false_hearth.yaml:10`.
- The proximity plan is deferred, its v1 exposure is "binary in-scene = exposed", and its revive trigger is as
  quoted. `adaptive_nociception.md`'s trigger (b) is as quoted.
- `thalamic_relay.md:925` ("Nociceptors sensitize; they do not habituate") and `:1444` ("a track adds no
  adaptation of its own") are as quoted. The variant-body decision is at `DECISIONS.md:1464`.

The design's core split is the right one, and I agree with it on the merits: the world computes the stimulus
at the receptor and Maxim does the transduction (§5.1). So are the fraction rule (§5.3), "a fruitless act
succeeds" (§5.4) and the must-never list (§5.5). The findings are about where the design hands Maxim something
that doesn't exist, mis-scopes an ask, or leaves a divergence unnamed.

---

## BLOCKER

### B1. MP-2 argues against a recorded Maxim decision without naming it, and its routing would put the warning band on a track with no learner

**Location:** `fire_model.md::§11` item 8; `research/fire_ladder/6b_maxim_perception.md::§4 MP-2`;
`origin/main:docs/plans/thalamic_relay.md:881-882` and `:941`;
`origin/main:docs/plans/reviews/grounding_gl1/bio-faithful.md` N4.

The research calls MP-2 "a question to GL2b, not a new plan", and it asks for two nociceptor classes: a fast
receptor at about 46 °C feeding `nociceptive_fast`, and a slow one at 41–45 °C (C fibres) feeding
`affective_slow`.

Maxim already ruled on this. Its GL1 bio-faithful review N4 raised two fibre populations, and the decision was
"just add 'FUNCTIONAL: one threshold for both fibre classes' to the fan-out's docstring". `thalamic_relay.md`
records it at l.881-882. Under TR18 (`thalamic_relay.md:941`), the sinks of `affective_slow` are "only sinks
that are not PainBus subscribers … No cluster fear, no memory tag, no prompt line". So the second half of MP-2
pushes back on a recorded decision. CLAUDE.md requires such a pushback to name the decision ("Push back on
Maxim") and to cite what Maxim's origin/main has ("Search Maxim before proposing"). MP-2 does neither, and
§11.8 asks the owner to send it now.

**Failure scenario.** Maxim adopts MP-2 as written. An NPC stands near a crate fire at 1–2 kW/m². Its basal
skin warms through 41–45 °C for tens of seconds: the learn-before-harm window that §5.2 calls "the agents' case
for this design". That band crosses only the C-fibre receptor, whose track feeds record-only sinks. No PainBus
learner hears it and no situation fear forms. The window the design argues for exists in the world and is
discarded in the agent. Fear forms only at about 46 °C, near the onset of damage.

**Fix.** Split MP-2:
- **(a) Physical units.** A `NociceptorSpec` on a °C sensor of a variant body, with physiological defaults.
  This really is a question. §3.2 already takes thresholds "in sensor units", and its values are "the owner's,
  decided at GL2b(ii)'s start". Route it as input to that calibration decision.
- **(b) Two fibre populations.** This is a pushback. Name N4 and TR18, and say which learner the slow band
  should feed. Bring the evidence: the closed-form time a skin model spends in 41–46 °C under the ladder's
  fluxes.

---

## SHOULD-FIX

### S1. "Burns as health until GL2b" doesn't exist on a humanoid body, and it isn't a stopgap

**Location:** `fire_model.md::§5.1` (Tissue damage) and `::§12` (last bullet);
`research/states_of_matter/sem.md::N6` ("the proven Minecraft path for oxygen and health");
`origin/main:src/maxim/_data/components/bodies/base_humanoid.yaml:57`;
`origin/main:src/maxim/embodiment/body.py:304-307`; `origin/main:src/maxim/embodiment/spec.py:325-360`.

The design writes "a Henriques integral into the region's integrity or `health`". On `base_humanoid` (and the
bodies that extend it, such as `infant_humanoid`), health is `health: derived`. `evaluate_failures` recomputes
`vital_metrics["health"]` from modulator integrities on every call. `health` isn't in `root.sensors`, so
`world_set_axis(emb, "health", …)` returns False. A direct `health` sensor beside modulator sub-sensors is a
`ConfigurationError` (C5, `spec.py:341-360`).

That leaves two routes, and neither is free:
- **The integrity route** writes `<part>.integrity` sub-sensors, which needs MP-5 (OD-C10).
- **The health route** needs a flat body shaped like Minecraft's (`minecraft_player.yaml`: a root `health` with
  `modality: world`), which has no per-part somatosensation.

N6's "proven path for health" holds only for flat bodies.

**Failure scenario.** Phase 4 builds NPCs on a humanoid variant and writes burn damage to `health` through
`world_set_axis`. The call returns False, fail-soft. The NPC is incinerated with full health, no pain and no
fear, and no test is red unless someone asserts on the return value.

The framing is also wrong. The Henriques integral into `health` is the permanent design: health doesn't go away
when GL2b lands. What GL2b adds is pain before damage. "Burns as health" names what is permanent, not the gap.
`drive:health` is already NOCICEPTIVE and in the fear set, so health loss does condition fear. It is learning
from injury, and Maxim's real mechanism does that job correctly.

**Fix.** State the body shape. Make MP-5 a prerequisite of per-part damage, or choose a flat body and name
that divergence. Reword §12: "until GL2b, an NPC learns fire only from injury, never from the pain that comes
first."

### S2. MP-1 is scoped too wide and argued without Maxim's own precedent

**Location:** `fire_model.md::§11` item 8; `6b_maxim_perception.md::§4 MP-1`;
`origin/main:src/maxim/decisions/nac.py:511-516` and `:3390-3403`; `origin/main:src/maxim/hivemind/bundle.py:476`;
`origin/main:src/maxim/hivemind/ingest.py:652`.

- **(a) Two asks in one.** The fear allowlist is `NACConfig.cluster_fear_failure_modes`, a per-config field,
  and `record_cluster_fear` checks `self.config`. An agent's own burn fear therefore needs only a variant
  config once GL2b exists. That is no edit to the shipped default, and it may need no re-run of T1-13 to T1-15.
  The shipped default matters only for **hivemind transport**: the bundle scrub and the ingest bound enforce
  the default, not the receiver's config (nac.py's "HONEST LIMIT" comment). Hivemind transport is exactly
  Overdrive's Phase 5 rumour mechanism ("fear spreads between NPCs through hivemind merges"). Split MP-1 into
  (i) local, by config, and (ii) transport, by editing the default and re-running the ledger rows.
- **(b) The precedent is missing.** `nac.py:511-515` says `drive:oxygen` was added at Exp 60 "so air-hunger
  pain books drowning-fear onto the underwater cluster before tissue damage … rather than collapsing into
  generic injury fear (bio-faithful lens, Exp 60)". That is MP-1's argument, already accepted by Maxim for
  another modality. MP-1 should cite it.
- **(c) The "game evidence" can't exist yet.** The scenario needs `drive:<part>.thermal:noxious` (GL2b) and
  NPC bodies (Phase 4). It also needs a definition of "no health loss": Henriques damage accrues above about
  44 °C, so noxious trials always carry some. The criterion is "health loss inside the drive's comfort band".

**Failure scenario.** Maxim's review sees "edit a hivemind wire boundary, re-run three ledger rows" for a need
a config line meets. It defers the ask, and Phase 5's rumour of fire fear is never filed as its own ask.

### S3. Sight, and the fractions read "through a percept", have no channel in Maxim, and the stopgap is an unnamed analogue

**Location:** `fire_model.md::§5.1` (Sight), `::§5.3`, `::§11` item 8 ("R3 with an NPC *watching* needs no
Maxim change"); `6b_maxim_perception.md::§5`; `origin/main:src/maxim/agents/modality.py:124`;
`origin/main:docs/plans/deferred/passive_sense_discovery.md`.

Maxim's SIGHT maps to the vision substrate, which handles camera detections only. Passive sense discovery is
deferred with zero code, and P-E/OD-C8 are unbuilt. Overdrive's light and visibility work is in Phase 2, and
its NPCs arrive in Phase 4. "Watching needs no Maxim change" therefore rests on L6b §5's flame-in-view written
as root `world` sensors. That stopgap has two problems:
- **It isn't vision.** It is an ANALOG divergence that the design doesn't name.
- **It fails the design's own leak test 1.** A sensor computed from "luminous flame volumes" carries the
  stimulus's identity: an instrument at the eye measures luminance, not "flame". A lamp should excite it too.
- **The fractions have nowhere to go.** The §5.3 fractions ("burning", "charred") have no percept channel
  either, so until OD-C8 the only way they can reach an NPC is the omniscient `RegionInstrument` that §5.5
  forbids.

**Failure scenario.** In Phase 4 an NPC "watching" R3 gets `flame_luminance` from anywhere in the tile, with no
line of sight. It "learns" to fear fire through a wall, from a sensor that only fires for fire.

**Fix.** Make the stopgap generic: luminance, angular size and flicker of whatever is in view, after line of
sight. Tag it ANALOG, and say that the fractions stay lab instruments until OD-C8.

### S4. Leak test 2 misfiles tissue physics, and lesson 24 exports the error

**Location:** `fire_model.md::§5.1` (leak test 2 against the Heat and Tissue rows);
`lessons_maxim_in_games.md::24`; `6b_maxim_perception.md::§4 MP-3`.

Test 2 says: "Does the parameter have a value in a physiology paper? Then it's the receptor's, and it lives in
Maxim". The world-side rows in the same table then use physiology-paper parameters: the Henriques P and ΔE/R,
skin k and ρc, and a basal depth of 0.1 mm. MP-3 also has the world moving `core_temperature`, which is body
heat balance, while Maxim's body YAML drifts that sensor. The rule a reviewer needs is: tissue, the body's own
matter and its heat and damage, is world physics; **transduction** (threshold, gain, adaptation, latency) is
the receptor's. Core temperature needs an owner: world-written with `drift_rate: 0` (N6), or Maxim-drifted,
never both.

**Failure scenario.** A later reviewer applies test 2 as written and moves the Henriques integral into Maxim.
That is a second heat path into the body, which §5.5 forbids. Or a Maxim reader takes lesson 24's tests as
engine guidance and puts skin conduction in the agent.

### S5. Retiring `ignite` and `extinguish` from NPCs has no mechanism, and `strike` isn't addressed

**Location:** `fire_model.md::§5.4` (last bullet), `::§5.5`; `gates:src/simcore/adapters/sem/bridge.py`
(`StructureModulator.affordances`, `region_parts`, `to_maxim_entity`).

`to_maxim_entity` gives every region Entity the `structure` modulator (`strike`, `ignite`, `extinguish`) and
every `RegionInstrument`. Nothing separates a lab Entity from one an NPC sees. The `ignite` description, "it
burns until extinguished", puts an outcome in the text, which breaks §5.5's fourth rule on the shipped
membrane. `strike(energy_j)` is the same chosen-magnitude god verb ("no NPC emits a chosen wattage"; nor a
chosen joule count), and the design is silent on it.

**Failure scenario.** Phase 4 hands an NPC the existing region Entity. Maxim's tool generation exposes
`crate_ignite` and `crate_temperature_max`, and the NPC sets fires with a typed wattage and reads a room's
maximum through a wall.

**Fix.** Use two builders (lab and NPC), with a golden test of the NPC-facing tool surface (N7) that contains
no `ignite`, `extinguish` or `RegionInstrument`. Decide `strike` the same way: a body act with a held thing.

### S6. Credit for `apply` is OPEN until OD-A16, and the act's own timing is wrong

**Location:** `fire_model.md::§5.4` (Acts table); `npcs_and_sem.md:65` (O30: OD-A16 gates Phase 4),
`:725-732`; `origin/main:docs/plans/latent_forward_model.md` (the entity_state row).

Ignition arrives tens of seconds after `apply`, and Maxim credits at call return: the cerebellum reads
`entity_state` inside the call, and `tool_bridge` drops `result.metadata`. Every `apply` therefore books the
same success, whether the target is cardboard or steel. "A fruitless act succeeds" is right, but without OD-A16
it teaches nothing about ignition either, and the design doesn't say so. The table also puts `light` and
`apply` "with R3", though both need held items, and the same table says item entities come later ("needs item
entities"). NPCs arrive in Phase 4 in any case.

**Fix.** Mark the credit for `light` and `apply` as an OPEN divergence that OD-A16 closes, and time them with
item entities.

### S7. The Maxim asks duplicate existing ids and revise a recorded timing silently

**Location:** `fire_model.md::§10`, `::§11` item 8; `world_v2.md:322-345`; `states_of_matter/sem.md::3b`;
`roadmap.md::Phase 3`.

- **Renamed asks.** MP-4 is world_v2 P3, sem.md P3 and OD-A16. MP-5 is P4 and OD-C10 (L6b admits OD-C10).
- **A timing revised without a row.** world_v2 §7 deferred "burn pain … (GL2b's `NociceptorSpec`)" and "a
  review of the Wire-4 allowlist" to Phase 4's body-model design. §11.8's "ask now" revises that, but §10
  doesn't list it.
- **Nothing is filed.** No MP item has a roadmap row or a draft in `docs/maxim_upstream/`.

**Failure scenario.** Maxim receives an MP-5 and a P4 for the same `world_set_axis` change, and an MP-4
alongside the existing OD-A16 amendment. That is the duplicate lesson 13 exists to prevent.

**Fix.** Reuse the existing ids, add a §10 row for the timing change, and add roadmap rows when the owner
rules.

### S8. The exit claims an NPC lesson, and the design drops the research's learning confound

**Location:** `fire_model.md::§7` ("It gives NPCs the lesson they need later"); `6_biofaithful_sem.md::§5`.

Phase 1 has no NPCs, and starting a fire is stage 5 of L6's agent curriculum: "the physics ladder is a
prerequisite, not a curriculum order". L6 §5's confound, that an LLM-primary NPC already "knows" fire burns
(Maxim's Exp 38 counter-prior hearth), appears nowhere in the design. From the agents' side the exit is sound
as a world test; the claim about NPCs is not.

**Failure scenario.** In Phase 4, NPCs avoid the alley fire, and this is cited as the exit's lesson being
learned. It is the LLM prior.

**Fix.** Drop the claim. Carry L6 §5's ordering and the substrate-side or counter-prior measurement rule into
§12.

---

## NIT

- **N1.** No divergence carries Maxim's EARN, ANALOG or OPEN intent (`origin/main:docs/plans/bio_faithful_roadmap.md`
  exists). The root-sensor skin stopgap, flame-in-view and credit for `apply` are ANALOG or OPEN.
  `fire_model.md::§5`.
- **N2.** §11.8 relies on MP-3 to MP-6, which only L6b defines. A design that asks the owner to rule should
  carry a one-line table of the asks. `fire_model.md::§11`.
- **N3.** L6 §4 P-F3 attributes a "phantom-credit concern" to the proximity plan. The phrase is in
  `world_set_axis`'s docstring, not in the plan. MP-3 also changes the plan's exposure from deltas
  (`_apply_sensor_deltas`) to absolute writes; say so. `6_biofaithful_sem.md::§4`.
- **N4.** The client "may add purely visual effects", so the player can see flicker or smoke that no NPC
  senses. Name it as a known asymmetry. `fire_model.md::§5.1` (Sight).
- **N5.** §10 retires `ignite` and `extinguish` as NPC verbs but doesn't list `states_of_matter/sem.md` N3's verb
  list (`ignite`, `extinguish`) as revised. `fire_model.md::§10`.
