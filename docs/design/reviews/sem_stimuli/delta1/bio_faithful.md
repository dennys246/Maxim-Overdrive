# SEM stimulus interface v2: Bio-faithful integration, delta round 1

**Read:** Overdrive `phase1/sem-stimulus` at `3e97ac9` (`sem_stimuli.md` v2, `fold.md`, lessons 11 and 23–25,
`fire_model.md` §5.1, `embeddable_agent_DRAFT.md` §7, `world_clock_release_DRAFT.md` §3.5 and §4, roadmap Phase 4).
Maxim by `git show`/`git grep` only, at local `origin/main` **`043eab8f`**. I did not fetch.

**Correction first.** My round-1 S6 told the author to route thermal adaptation as "a question to the salience-layer
route". No such plan exists at `043eab8f`, so the author followed a framing of mine that was wrong (new N-2).

## Status of round-1 findings

| Id | Status | Reason, read from the tree |
|---|---|---|
| B1 | fixed | D5 (c) is v1 (§0, §4.1 step 3, §10). Tissue integrates every tick at the pose (§2.4). T9's oracle is byte-identical frames at divisors 1–50. The fallback is a strict red gate plus a Known gap (§11.3). What D5 (c) buys on the first body is new SF-1. |
| B2 | fixed | `exposed_area_fraction` withdrawn (§1). Partial contact and clothing are tissue-law sub-columns and layers (§2.4). |
| B3 | fixed | M2 withdrawn. It cites `setpoint_aware_neutral.md` and `archive/world_channel_weighting.md:222`, which I verified ("static set-point-aware neutral … numerically identical to the range declaration"). Bodies pass the rest rule (§3.3). The mechanism is missing: new N-1. |
| S1 | deferred | I accept the deferral. The channel is stated (world, no drive), with weights at 45 and 60 °C (0.034, 0.39) and the range OPEN, to be measured as #726 was. 40 °C is not listed, which is trivial. Reason: the range is a measurement, not a choice made at the desk. Trigger: before the first body's YAML is committed (§11.1 "before Phase 4"). The consequence of choosing no drive is new SF-1. |
| S2 | fixed | §6.4 answers D7 with `tool_bridge.py:295-321, :1002-1020, :1068-1082` (verified), adds R15's claim rule and M19 to OD-A11. Lesson 25 is recorded. |
| S3 | fixed | Damage goes through `apply_damage` (§3.3, verified at `spec.py:1025`). Burned area is never bound to a sensor and is tagged ANALOG. M17 goes to GL2b and TR22 (both exist: `autonomic_layer.md:3`, `thalamic_relay.md:104`). The adapter's write is named. On the flat body the path is a silent no-op: new SF-2. |
| S4 | fixed | M5–M8 are now citations of OD-A1, OD-A2 and the world-clock draft. D3 is written in the future tense and fakes `time.monotonic`. The draft's §4 row already carries the 20× argument (`world_clock_release_DRAFT.md:143`). My hardware-driver point isn't added, but the row's "motor and IO rate limits stay on the wall" covers it. |
| S5 | fixed | M14 is a pushback against the proximity plan's `heat_output` mechanism, with T3 and T5 as evidence. The path is verified. |
| S6 | fixed | M15 is filed as I asked. My framing was wrong: new N-2. |
| S7 | fixed | Pooling is fixed by receptor class, means are refused on pain paths, and it is tagged EARN on GL3.B1 and OD-C10 (§3.2). The first body binds no pain path, so its hot-spot case is in SF-1. |
| S8 | fixed | Each item is present: the R1 lead-time gate (§6.3), the R8 per-act test (§6.2), R14 in M9, and lesson 23 amended for push against pull. Lessons 23 and 25 are in this commit, and lesson 24 is reworded. The R1 gate has no pass rule: N-3. |
| N1 | fixed | `luminance` and M12 are tagged EARN. |
| N2 | fixed | MP-5, MP-2a/2b and MP-1 are on M1, M9 and M10. |
| N3 | fixed | `fire_model.md:205-206` and lesson 24 are reworded. "Humanoids lack `drive:health`, so no fear yet" is true: the fear set is `{"drive:health", "drive:oxygen"}` (`nac.py`), and `base_humanoid.yaml` has `health: derived`. |
| N4 | fixed | M13 is New, Phase 2. |
| N5 | fixed | M3 is dropped. |
| N6 | fixed | D4 cites OD-A2. Lesson 11 is reworded. |
| N7 | fixed | A melanopic band is reserved (§2.2). |
| N8 | fixed | `sound_event` offsets fall within the tick (§2.2, §4.2). |
| N9 | fixed | §6.4 says ΣV is OPEN. §4.4 names the backend's modulator and maps the owner to `experienced`. |
| N10 | fixed | Recorded as Q6. |

**Counts:** 20 fixed, 1 deferred, 0 rejected, 0 open. I accept the author's one proposed deferral (S1). None of my
findings was proposed for rejection.

## New findings in v2

### SF-1 (SHOULD-FIX). The first body gives heat no valence, and Phase 4 moves its NPCs substrate-primary

**Where:** `sem_stimuli.md::§0` ("Phase 4's first NPC feels heat as temperature"), `::§3.3`, `::§11.3`, `::§10 D5`;
`docs/roadmap.md` Phase 4 ("Movement runs in substrate-primary mode (no LLM); speech goes to the LLM").

On the body §3.3 specifies, every route from heat to a valenced signal is closed:
- **No pain or relief:** drive pain and the credit diff come only from a `DriveSpec` (`sem.py:271-280`), and the skin
  sensors carry no `drive:`.
- **No nociception:** it waits on GL2b, which has not started (`autonomic_layer.md:3`).
- **No damage:** it is held as world state until M17 is answered (§3.3), and SF-2 adds that on a flat body it would
  be a no-op anyway.
- **Little salience:** the A4 weight is 0.034 at 45 °C (§3.3).
- **No fear:** M10.

What remains is a weakly weighted world-channel encoding with no consequence attached. Under the roadmap's
substrate-primary movement, nothing that selects a movement has any reason to leave a hot plate. The NPC walks
into fire and, because SF-2 means damage never reaches Maxim, its body reads unhurt. The LLM sees "47.3 celsius" but
only drives speech, so the NPC can say "it burns" while its legs stay put. A player would read that as a broken NPC,
and it is an unfelt burn of the very kind B1 and §4.3 set out to prevent.

D5 (c) is also bought for nothing on this body. The per-tick body step is `evaluate_failures` (SF-3). With no drive,
no skin failure mode and `drift_rate: 0`, it changes nothing for skin, yet it costs ~15–30 ms per world second at
10 NPCs (§8). I still back (c) as the contract, because it is right once any of the routes above opens. But §0's
"feels" and §11.3's "weakly salient" understate the state: the first body has no felt heat in any sense the substrate
acts on.

**Fix:** say this in §0 and §11.3 in those words. Give the owner a D14 with three options:
- (a) answer M17 and give the first body vital sub-sensors and failure modes (SF-2). That opens a late, coarse
  route: integrity, then health, then `injury` at health < 0.2. That route is not in the fear set.
- (b) a homeostatic skin drive, named ANALOG for nociception. It is DRIVE-class, as §3.3 says, but it is a valenced
  signal that movement can learn from.
- (c) ship Phase 4 with fire-free tiles, or record a Known gap that NPCs don't avoid heat.

Until one of these opens, defer the D5 (c) body step's cost row in §8, or justify it as contract readiness.

### SF-2 (SHOULD-FIX). `apply_damage` silently does nothing on a body without sub-sensors, and §3.3's body has none specified

**Where:** `sem_stimuli.md::§3.3` ("Damage goes through Maxim's integrity model … `base_humanoid.yaml:108-120`");
`origin/main:src/maxim/embodiment/spec.py:1035-1038`:
`if not self.vital_metrics: # No sub-sensors — can't take component damage / return 1.0`.

§3.3 calls the first body "a flat Overdrive body YAML: root skin sensors", but cites `base_humanoid`'s modulators to
show that damage works. On a modulator with no vital sub-sensors, `apply_damage(amount, "fire")` returns integrity
1.0 and writes nothing. On `base_humanoid` only the torso declares a `fire` affinity (`fire: {core_integrity: 0.8}`).
Head, arms and legs fall back to proportional damage, so a burned hand lowers `grip_strength` and `arm_mobility`
equally, an unstated ANALOG. The design also doesn't map 17 skin regions onto Maxim's modulators, or say which
`health_weights` and failure modes the first body declares.

**Failure scenario:** M17 is answered yes, and the adapter calls `apply_damage` on each region's modulator. Every
call returns 1.0, no integrity moves, and nothing reports it. The burn exists only in the world.

**Fix:** §3.3 states the first body's modulators: the skin-region grouping, the vital sub-sensors, `fire` affinities,
`health: derived` with weights, and its failure modes. Add a build test that a planted burn lowers the bound
modulator's integrity. Show it red on a modulator stripped of sub-sensors, so the no-op fails loudly rather than by
review. Tag the region-to-modulator map ANALOG. Note that the only caller in `src/` is the sim tool
(`simulation/tools.py:665`), which is what M17 asks about.

### SF-3 (SHOULD-FIX). M16 wasn't searched against Maxim's `src/`, and its evidence answers a different question

**Where:** `sem_stimuli.md::§9 M16`, `::§9 M4`; `embeddable_agent_DRAFT.md` §7 (M16);
`origin/main:src/maxim/embodiment/body.py:258` (`Embodiment.evaluate_failures`), `:293-297` (drift on `time.time()`
inside it), `:634` (`tick_vital_drift(dt)`); `origin/main:src/maxim/embodiment/percepts.py:122`;
`agentic_runtime.py:605`.

M16 asks whether "an embedded body [can] step every tick without cognition". It argues from two sources:
- `DECISIONS.md` G1–G4, which says the SensorEncoder body world "is the only path that acts without the LLM"
  (verified, `DECISIONS.md:758` onward);
- `bounded_stop.md:437`, which says `agentic_runtime` "runs without the LLM".

Both are about running without the **LLM**. The SensorEncoder body world *is* cognition (the EC, at 0.85 with frozen
centroids). Maxim can truthfully answer "yes" to the evidence as given and leave D5 (c) unsettled.

Meanwhile Maxim already has the body-only step. `Embodiment.evaluate_failures()` applies drift, evaluates failure
modes and publishes pain, with no cognition. `percepts.py` and `agentic_runtime` call it as a step of its own. Its
one defect for us is wall-time drift at `:293-297`, which is M5 and OD-A1. The search rule ("the relevant `src/`")
would have found it. M4 ("the embedded `step` evaluates the body after a push") is then the same ask, so §9 has two
rows, to two homes under OD-A10, for one method.

**Failure scenario:** Maxim's design session reads M16 as a request for a new body-step API. It designs one beside
`evaluate_failures`, which makes two body paths, or it answers the LLM question and closes the item.

**Fix:** merge M4 into M16 and re-word it as a question about the existing method: "May an embedded host call
`Embodiment.evaluate_failures()` once per world tick between cognition steps, on the injected clock (OD-A1, A2), and
is that supported in the host-driven build?" Cite `body.py:258, :293-297` and drop the LLM-only evidence. Add the
search terms to the draft (it lists "Searched, nothing found" only for OD-EA9).

### N-1 (NIT). Nothing in Overdrive can run Maxim's rest rule

**Where:** `sem_stimuli.md::§3.3` ("every body YAML passes Maxim's `scripts/lint_body_rest_neutral.py` rule");
`origin/main:scripts/lint_body_rest_neutral.py:63-64` (`COMPONENTS_DIR = REPO_ROOT / "src" / "maxim" / "_data" /
"components"`); `origin/main:pyproject.toml:249-259` (the wheel ships `maxim*` and `_data`, not `scripts/`).

The lint isn't in pymaxim and scans a fixed in-repo path, so an Overdrive body YAML is never checked. As written, the
rule is guarded by a document alone. **Fix:** name an Overdrive check that ports the rule (it requires `rest:` or a
homeostatic `set_point` at the range midpoint for every gained ranged sensor), with a planted off-centre body. Or ask
Maxim, under OD-A10, for an entry point that takes a path. Until then it needs a backlog row.

### N-2 (NIT). M15 is labelled "Question", but no plan owns thermal adaptation

**Where:** `sem_stimuli.md::§9 M15`; `origin/main:docs/plans/deferred/setpoint_aware_neutral.md:52-60`, which says
habituation lives in `tools/novelty.py` and `attention/salience_map.py` (both exist), and that "if wanted for the
world channel it is a separate salience-layer plan". No such plan exists: `docs/plans/archive/salience_abstraction_plan.md`
is archived and is about coordinates. `archive/world_channel_weighting.md:221` lists "adaptive set-point
(habituation in the encoder)" as dead.

By §9's own key, a "Question" needs a plan that owns the topic, so M15 is **New**. The cause is my round-1 wording.
There is also a divergence the row doesn't name. Warm and cold fibres adapt at the receptor, and novelty or salience
habituation is central, so landing adaptation there is an ANALOG. **Fix:** relabel M15 New with the terms searched
("habituat", "adaptive set-point", "salience-layer"). Cite the encoder route's closure, and tag the
downstream-habituation route ANALOG.

### N-3 (NIT). The gate table is malformed, and two gates can pass on a dead stimulus

**Where:** `sem_stimuli.md::§6.3`.

The table opens with a three-column header (`# | Gate | Catches`), then a second two-column header. v1's "Catches"
column is gone, and so is T11's negative control ("a fire moved into A's view changes it", v1 line 288).

T3, T4, T5 and T11 are invariance gates. A frame that never changes, such as a tissue law stuck at the core node's
temperature, passes all four. Their plants prove that leaks are caught, never that the world's regularity is
delivered. The R1 lead-time gate "measures" but has no pass rule.

**Fix:** repair the table. Restore T11's negative control and add one to T3, a lamp brought into view that must
change the frame. Number the R1 gate (T15) with L6's criterion: cue onset at the receptor precedes the onset of the
damage integral, per hazard, with the lead in seconds recorded.

## Answers to the lens questions, v2

- **Real job?** The contract now does the receptor's job: depth, every tick, per point, and pooling by class. The
  first *body* does not, because nothing valenced reaches the substrate (SF-1, SF-2).
- **Unsensable inputs?** None remain. Coverage and flux are internal, and burned area is never bound.
- **Tags?** They are correct after the fold, apart from M15's kind and its ANALOG (N-2).
- **Asks searched?** M14, M17, M18 and M19 check out against the tree. M16 and M4 missed `evaluate_failures` (SF-3),
  and M15 is mislabelled (N-2).
- **LLM claim discipline?** §6.4 is sound. Phase 4 moves its NPCs without the LLM, so the live risk there is the
  absence of any signal, not the LLM's prior (SF-1).
