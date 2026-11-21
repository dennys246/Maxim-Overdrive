# SEM stimulus interface v3: Bio-faithful integration, delta round 2

**Read:** Overdrive `phase1/sem-stimulus` at `77e24bb` (`sem_stimuli.md` v3, `delta1/fold.md`, the v2→v3 diff of
`roadmap.md`, `lessons_maxim_in_games.md`, `embeddable_agent_DRAFT.md`, `long_term_features.md`). I read Maxim only
through `git show` and `git grep` at local `origin/main` **`043eab8f`**, and did not fetch. I measured on L3's column
(`_durable/sem_research/scratch/skin.py`) with two scripts in `scratch_bio_faithful/` (`t16.py`, `rest.py`).

**Correction first: my own delta-1 evidence was wrong.** My SF-3 said `percepts.py` and `agentic_runtime` call
`evaluate_failures` as a step of their own. The author dropped `agentic_runtime`, but `embeddable_agent_DRAFT.md` §7
now cites "`percepts.py:122` calls it alone". `EmbodimentPerceptSource` is dormant. Its docstring says "NEVER
production-wired … `EmbodimentPerceptSource(` never entered `src/`" (`percepts.py:1-17`), and Maxim's own census
lists it as "no production constructor" (`docs/plans/autonomic_layer.md` §1.2a). The production callers are
`runtime/substrate_proposal.py:837` (the substrate-primary tick), `runtime/loop_gates.py:309` (the LLM-primary tick)
and `embodiment/tool_bridge.py:776` (after an action). The draft carries my error to Maxim. SF-3 stays open, and the
rest of the fault is the search, below.

## Status of delta-1 findings

| Id | Status | Reason, read from the tree |
|---|---|---|
| SF-1 | fixed | §0 and §11.3 now say "no felt heat in any sense the substrate acts on". The owner ruled D14 (§10): D5 (c) stays the contract, with delivery at the cognition rate as a Known gap (§4.6), and a pain path is a prerequisite for Phase 4's fire scenarios. I checked `roadmap.md:293` ("no NPC meets fire before its body has a pain path"). That is my option (c) as the owner's decision, which the finding allowed. Two problems remain, and they are new: T16 can't be red (D2-B1), and "pain path" is never defined (D2-S1). |
| SF-2 | deferred (reviewer-set) | The guard is in §3.3: a planted-burn build test, red on a stripped modulator, so the no-op can't pass silently. OD-I7 is filed (`roadmap.md`), and its line numbers are right (`spec.py:1034-1036`). What is still missing is the actual map: which of the 17 regions go to which modulator, and the sub-sensors, `fire` weights, `health_weights` and failure modes. v3 names their kinds only. **Reason:** that is body-instance data under D8, and it can't be fixed before Q1's point count. **Trigger:** the first body's YAML PR (§11.1, last row). That PR states the map, tags it ANALOG, and carries the test. |
| SF-3 | open | Done: M16 is merged into M4, the question is now about `evaluate_failures`, and the LLM-only evidence is gone. **Missing:** (1) the draft cites a dormant caller (correction above). (2) The draft says "Searched, nothing found … for M4, a host-driven body step (terms "evaluate_failures", "body step")". That is false at `043eab8f`. `autonomic_layer.md` §1.2a is a census titled "Who calls `evaluate_failures`" (33 mentions in the file), and it names the Minecraft pump as the matching case: an external world that "writes sensors and never calls `evaluate_failures`". `grounding.md:451` schedules GL3.B0, "every `evaluate_failures` caller with its thread". GL3.B4's named prerequisite is "per-pass body transduction, independent of selection", settled with **#1176 (L1)** (`thalamic_relay.md:12`, TR19, G28). By §9's own key and the search rule, M4 is a **Question to GL3.B0 and #1176**, with OD-A10 for the host-driven build only. It is not an OD-A10 item with nothing found. **Fix (verified by reading):** cite `substrate_proposal.py:837`, `loop_gates.py:262-309` and `autonomic_layer.md` §1.2a; drop `percepts.py:122`; re-route as above; and add D2-S2's attribution question. |
| N-1 | fixed | §3.3 and §11.1 say `scripts/lint_body_rest.py` lands with the first body, planted off-centre. What the declaration-only check can't see is new D2-N1. |
| N-2 | fixed | M15 is **New**. It lists the terms searched, cites the closure at `archive/world_channel_weighting.md:221`, and tags downstream habituation ANALOG. |
| N-3 | fixed | §6.3 is one table. T3 and T11 have negative controls, and T15 has a pass rule ("cue onset at the receptor precedes the damage integral's onset; lead recorded"). |

**Counts:** 4 fixed, 1 deferred (reviewer-set), 0 rejected, 1 open. The author proposed no deferral or rejection on my
lens's rows. I make no ruling on other lenses' proposed deferrals (A-S10, F2).

## New findings in v3

### D2-B1 (BLOCKER). T16, the strict red gate holding D14's Known gap, passes on the day it is written

**Where:** `sem_stimuli.md::§4.6`, `::§6.3 T16`.

T16 reads: "a 0.2 s contact between steps at divisor 10 must change the agent's body state; strict red under D14".
Under D14, the push at the next cognition step carries "that tick's values", and tissue keeps the heat. I measured on
L3's column, with 20 mm steel in perfect contact, then release to the free boundary (`scratch_bio_faithful/t16.py`).
Rest at 0.1 mm is 32.45 °C. A 0.2 s touch of 70 °C steel peaks at 43.0 °C at release, and is still **38.2 °C (+5.8
K) 0.8 s later**, when the next cognition step runs. For 50 °C steel the numbers are 37.4 °C, then 35.2 °C (+2.7 K).
The pushed value differs by kelvins from the no-contact run, so the agent's body state changes, the `xfail(strict)`
passes unexpectedly, and the gate turns red as XPASS. The other direction fails too. With no pain path, per-tick
delivery leaves the **same** body state at the cognition step as cognition-rate delivery, because each per-tick push
overwrites the sensor. So "body state at the next step" can't tell the interim from the contract either way. What
D14 actually loses is an evaluation at the peak tick, which is the only thing an every-tick body step adds. As written,
the gap has no guard. By the project's rule, a test that can't fail as specified is a BLOCKER.

**Fix:** assert on what only an every-tick body step produces. Use a test-only fixture body (not the shipped
`drive:`-free body) with a homeostatic skin drive whose comfort band's upper edge lies between the next-step value and
the peak, say 40 °C for 70 °C steel held 0.2 s. Then require a PainBus publish, or a `FailureEvent`, stamped on a tick
between cognition steps. Under D14 this is red, because `evaluate_failures` never runs on the peak tick and the drive
latch only fires on band entry (`body.py`, the latch comment at about `:375-400`). It is green once the body steps
every tick. **Verified:** the physics is measured. The Maxim side is read only: I did not run pymaxim.

### D2-S1 (SHOULD-FIX). "Pain path", the trigger for D14 and for Phase 4's fire scenarios, has no definition, and the nearest one fires after the burn

**Where:** `sem_stimuli.md::§4.6`, `::§10 D14`, `::§3.3` (region modulators), `::§6.3` ("With a pain path …");
`roadmap.md:293`.

Two things wait on "a body with a pain path": delivery moving to every tick, and Phase 4 NPCs meeting fire. Neither
says what counts. The route §3.3 is building is M17 plus region modulators with failure modes, and it would meet the
words. `evaluate_failures` publishes pain on failure modes (`body.py:333-343`, `_publish_pain`). But that pain comes
only after integrity falls, that is after Ω ≥ 1, the burn. An NPC whose first pain is the burn has the gate open and
still walks into the fire, which is SF-1's scenario under another name. Its fear is also not settled: the Wire-4
allowlist and M10 are open.

**Fix:** define the term in §4.6 and D14. A pain path is a PainBus publish driven by a bound skin sensor whose onset
precedes Ω = 1 at the same point: the §6.3 fingertip test (`noci_heat` past threshold on 70 °C steel before that
point's Ω reaches 1), run on real pymaxim. Damage-driven failure-mode pain does not count. Point `roadmap.md:293` at
that test. **Verified:** by reading only. The criterion is the design's own fingertip test, unchanged.

### D2-S2 (SHOULD-FIX). The host's body step runs outside Maxim's W-4 order, so it takes the pain onset and keys fear to a stale situation

**Where:** `sem_stimuli.md::§4.4` ("the push … then the body step, `Embodiment.evaluate_failures()`"), `::§4.6`,
`::§9 M4`.

Substrate-primary, the Phase 4 movement mode, already steps the body inside every proposal. It runs
`nac.note_active_clusters(agent_id, clusters)` and then `embodiment.evaluate_failures()`, so that pain is "keyed to the
clusters noted above" (`substrate_proposal.py:808-839`). Maxim decided that order: "the Exp 58 W-4 order (encode →
`note_active_clusters` → pain → fear read → select) is unchanged" (`grounding.md:451`, G24). `loop_gates.py:279-281`
warns that calling it from outside a substrate-primary tick "would double the tick". §4.4 makes exactly that second
call, before the agent steps:
- **Drive pain:** it is published on band entry, then latched (`body.py`, `drive_breach_severity`). The host's call
  publishes the onset while the NAc stash still holds the *previous* proposal's clusters, and the proposal's own call
  then finds the latch set and publishes nothing. Wire 4 keys the burn's fear to where the NPC was a cognition step
  ago (up to 1 s at divisor 10).
- **Failure-mode pain:** two calls milliseconds apart share the PainBus `(entity, failure_mode)` refractory window
  (about 2 Hz, `loop_gates.py:294-295`), so the host's call again takes the publish.

Under D14 this happens on every cognition tick. Under D5 (c), on non-cognition ticks the host's call is the only one,
so every between-step pain is keyed to the last stash, which by design is never cleared between proposals
(`substrate_proposal.py:810-813`: only the next proposal rewrites it). This is the credit-assignment failure the design exists to avoid: the NPC learns
fear of the place it stood before the burn.

**Fix:** (1) §4.4: on a cognition tick the host pushes but does not step the body, so the agent's own tick does it in
W-4 order. On other ticks the host steps it. Add a gate: on a cognition tick, exactly one `evaluate_failures` call
per agent step, and pain keyed to that step's clusters. (2) Add to M4 the question of how a publish *between* passes
is keyed: to the stale stash, to none, or through #1176's per-pass transduction. Tag the stale key ANALOG until it is
answered. **Verified:** by reading the Maxim sources cited. I did not run it.

### D2-S3 (SHOULD-FIX). §6.4 and M19 list only the pull tools; Maxim also pushes every sensor's name, unit and value into the prompt

**Where:** `sem_stimuli.md::§6.4`, `::§9 M19`, `::§6.3 T13`.

§6.4 cites the generated `SensorReadTool`s (`tool_bridge.py:1068-1082`), and M19 asks Maxim to withhold
"world-channel read tools". Two more routes reach the LLM at `043eab8f`:
- **`UniversalSenseTool`, named `sense`** (`tools/discovery.py:88-125`), is core-universal and returns
  `{value, unit}` for every sensor on an entity. The loop's **auto-sense sweep** (`runtime/loop_perception.py:265-391`)
  runs it on each self-entity whenever a percept carries a transcript or CLI input. It injects "Body state (<self>):
  …" into the prompt "without choosing to call tools" (`prompt_builder.py:1909-1915`). In Phase 4, dialogue is what
  supplies transcripts, so every dialogue turn pushes "skin_hand_left_temp … 47.3 celsius" without being asked.
- **The Exp 44 `body_state` section** (`body.py:788-812`, through `memory_agent.py:1316`) is off by default behind
  `MAXIM_ENABLE_BODY_STATE_PROMPT` (`memory_hub.py:58-70`). When on, it prints every float sensor with its unit. Near
  a failure trigger on a sensor field it adds `WARN: <failure name> threshold at <v><unit>, pain <p>`. That is a
  verdict label in the LLM channel, and SF-2's region failure modes would produce it if they trigger on bound skin
  sensors.

A yes to M19 would therefore leave the push intact, and §6.4's surface audit (lesson 25: "audit what the agent's
language channel sees") is incomplete.

**Fix:**
- §6.4 lists all three routes with these citations.
- M19 widens to "every LLM-visible rendering of world-modality sensors: generated read tools, `sense` and §1.15
  auto-sense, and the Exp 44 `body_state` section". Keep it a Question to OD-A11, and cite
  `acting_coach_body_state_ablation.md`, which owns the flag.
- T13's golden adds the auto-sense and `body_state` prompt sections beside the tool surface.
- The worker refuses to start with `MAXIM_ENABLE_BODY_STATE_PROMPT` set.
- No failure mode in §3.3 triggers on a bound sensor field.

Whether the embedded build registers `sense` (today it is registered at `simulation/orchestrator.py:1517`) belongs
in M19. **Verified:** by reading only.

### D2-N1 (NIT). The ported rest lint checks a declaration, but skin's rest is a per-scene measurement

**Where:** `sem_stimuli.md::§3.3` ("Rest at the midpoint", "centred at 33 °C over [−4, 70] °C").

Maxim's lint requires the declared rest to equal the midpoint to `REL_TOL = 1e-9`
(`scripts/lint_body_rest_neutral.py:70`). It says whether the world actually rests there "is a MEASUREMENT, the
apparatus check's job". Skin rests where the scene puts it. On L3's column, at the surface and at 0.1 mm
(`scratch_bio_faithful/rest.py`), it rests at 28.5–28.7 °C at 5 °C ambient, 32.4 at 20 °C and 35.1 at 30 °C. That
gives A4 weights of 1.6–1.8·10⁻³, 3–5·10⁻⁶ and 1.8·10⁻⁴ (**D**). Seventeen regions resting in a 5 °C street add about
0.03 of constant weight, about one hand at 45 °C (0.034, §3.3). How A4 sums weights across sensors I didn't check, so
treat that comparison as indicative. **Fix:** state the rest per bound depth and ambient, and add an apparatus check
(Maxim's `exp60_water_check.py` is the pattern): the measured rest in the shipped scenes against the declared rest,
with the cold-street weight recorded under the OPEN range. **Verified:** the numbers are measured. The A4 summation is
not checked.

### D2-N2 (NIT). M10's evidence is a run that D14 forbids in Phase 4

**Where:** `sem_stimuli.md::§9 M10` ("with the first NPC fire scenario's failing run"), `roadmap.md:293`.

No Phase 4 NPC meets fire before a pain path exists, so "the first NPC fire scenario" can't be the evidence until
after the gate it is meant to argue for. **Fix:** name the run as a harness scenario under `tests/` on a fixture body
with D2-S1's pain path, outside Phase 4's scenes.

### D2-N3 (NIT). Line citation for the no-op

`sem_stimuli.md::§3.3` cites `spec.py:1035-1038`. The guard is `:1034` and the `return 1.0` is `:1036` (OD-I7 has it
right). My delta-1 SF-2 carried the same off-by-one. **Fix:** `:1034-1036`.

## Answers to the lens questions, v3

- **Stimuli, never labels?** The world side is clean. The one label risk is Maxim's `WARN` line in the `body_state`
  prompt (D2-S3), which a §3.3 failure mode triggering on a bound sensor would set off.
- **What may be claimed as learned?** §6.4's rule is sound. Its surface audit misses the auto-sense push (D2-S3), and
  the substrate side's credit would key fear to stale situations (D2-S2).
- **Fidelity to `origin/main`?** Most citations check out. The ones that don't are `percepts.py` (my error, now in
  the draft) and the W-4 order the body step breaks.
- **Upstream asks searched first?** M4 as merged with M16 fails the search rule. `evaluate_failures`, the term the
  draft says it found nothing for, is the subject of `autonomic_layer.md` §1.2a, GL3.B0 and #1176 (SF-3, open).
