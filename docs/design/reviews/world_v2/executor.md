# Design review: Executor (world_v2.md)

Design: `docs/design/world_v2.md` at `d596418` (branch `phase1/design-v2`). Lens: Executor, design-time. Are the
design's claims about the existing code, its measurements and its sources true?

Read against: the research notes (`research/signals/`, `research/states_of_matter/`), v1 and its review files
(`reviews/realtime_lanes_coop/`), the code on `.worktrees/act-validation` at `02cd9e3` (that worktree also has
uncommitted edits from another session, which I didn't touch), and Maxim at `4b773ef8` (read-only).

Re-measured on act-validation, by importing its `src/` from a scratch script (nothing in either repo changed):
- the fiercest allowed fire (500 kW, r = 0.3 m) on the crate-only 3×3×2 m scene, turns 1 to 22, at all three rigs
  (5 s at max);
- the 3600 s Gaussian closed-form heat case, under today's semantics and under the design's "count of physics
  steps" semantics.

## BLOCKER

### E1. Under v2, the fuel model's acceptance gate flips by oxygen starvation, whether or not the rate is reconstructed

- **Location:** §3.0, last paragraph ("The requirement is that a cell's rate estimates the integral … well enough at
  the coarsest rig to flip `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`"),
  together with §1 and §3.5 (sealed fires starve); `tests/test_act_validation.py::SCENE` and `_burn_every_turn`.
- **What happens:** that gate runs on `Scene((3, 3, 2), (crate,))`, which has no zones and no vents. Under v2 that
  scene is a sealed room, which §1 and §3.5 say can burn only about 1 to 3 kg of the 130 kg crate. The open volume
  is 17.78 m³, so about 4.95 kg of O₂. Burning down to the 10% end of §3.1's ramp uses about 2.6 kg of O₂, which
  is 34 MJ, or 2.3 to 2.8 kg of wood at 12 to 15 MJ/kg. The crate's mass fraction then stays above 0.97 at every
  rig, so "integrity" (now mean strength) can't spread by 0.1, and a starved fire can't pass 2000 °C. The gate goes
  green on any per-cell rate law, including today's threshold, once O₂ exists. Its call shape breaks too:
  `ignite(power_w=500 kW)` is today's source semantics, and the research turns `ignite` into a spark in joules
  (architecture.md §4, row 6).
- **Failure:** PR 7 flips the strict red gate, removes the band-aid in `data/world/actions.yaml`, and claims §3.0's
  requirement is met. The reconstruct-decide-integrate requirement has then never been tested, and the cross-rig
  divergence returns in the vented bay, which the exit test (§9) depends on.
- **Fix:** restate the acceptance gate as a vented scene (the §9 burn bay, or the crate scene plus a vent to an
  ambient reservoir) in which the crate actually burns away, checked on every turn at every rig, with the outcome
  margin of §3.3. Rewrite the fiercest-fire gate's action in v2's `ignite` semantics. Say what an un-zoned (v0)
  scene's air is: one sealed zone, or an ambient reservoir (architecture.md §1.3 allows either). The gate's meaning
  depends on that choice.

## SHOULD-FIX

### E2. The "0.99% to 1.84%" figure was measured under the reading of the rig field that §5 rejects. The chosen reading gives different numbers, and one of them breaks today's order test

- **Location:** §5, first bullet ("laptop rises from 0.99% to 1.84% against a 2% bound, measured"); §11 row 2.
- **What happens:** DX2 measured 1.84% by passing the new field as `min_substeps` to a single 3600 s `heat.step`.
  That is the reinterpretation. Under §5's own semantics (`heat.step` takes physics steps, so 7200 × 0.5 s at
  1 / 2 / 6 substeps), I measured:

  | rig | today (1 × 3600 s, min 4/16/64) | DX2's reading (1 × 3600 s, min 1/2) | design (7200 × 0.5 s) |
  |---|---|---|---|
  | laptop | 0.995% | 1.84% | **1.29%** |
  | rig | 0.114% | 0.114% | **0.341%** |
  | max | 0.0089% | n/a | **0.086%** |

  The finer dt removes the forward-Euler time error that was cancelling the spatial error (benchmarking.md §1). So
  rig and max get *worse*, by 3× and 10×. `tests/test_heat.py::test_error_falls_with_resolution` asserts
  `fine < coarse / 4`. Under the design that is 0.00341 against 0.00321, so it **fails**. And the architecture
  doc's "1% / 0.1% / 0.01%" becomes 1.3% / 0.34% / 0.086%.
- **Failure:** if PR 3 (sim-clock) lands before PR 2's order test is replaced, a correct change turns a test red,
  and the tempting fix is to loosen the `/ 4`, which the rules forbid. If PR 2 lands first, the design still
  quotes the wrong figure.
- **Fix:** replace the figure with the table above, and say that PR 3 depends on PR 2's split space and time order
  test (benchmarking.md L2) replacing `test_error_falls_with_resolution`. Re-derive the architecture doc's
  closed-form figures there.

### E3. "Converting every cell takes 5.1 ms" misquotes the research: every cell costs 63.9 ms, and the 5.1 ms rests on a cache no PR builds

- **Location:** §2.3, second sentence.
- **What happens:** architecture.md §1.2 gives 63.9 ms for the full H→T inversion at max (bench2), and 5.1 ms for
  the latent correction only "with the per-cell property arrays cached (v1 §2.3's caching fix) and only 0.1% of
  cells at a transition" (bench3). The decision for temperature plus progress still holds, since that form pays
  only at transitions. But the sentence is false, and the cache it depends on isn't in §11. PR 3 lists
  "preallocated temporaries", and §5's "per-material bounds" covers `stable_dt` only (see N7).
- **Fix:** quote both numbers with their conditions, and name the PR that builds the per-cell property cache
  (keyed on `topology_version`).

### E4. P1 cites the wrong invariant of `scene_actor_affordances.md`

- **Location:** §7, P1 row ("`scene_actor_affordances.md` invariant 2").
- **What happens:** in `M/docs/plans/deferred/scene_actor_affordances.md`, "Load-bearing invariants", invariant 2 is
  "AUT cannot call `OrchestratorActorTool`". The default-target rule is invariant 5 ("Target resolution is
  explicit"), together with the schema's `"target": (str, "player")`. The `OrchestratorActorTool` docstring in
  `M/src/maxim/simulation/tools.py` numbers that same rule 2, which is where the "2" came from.
  act-validation's `docs/roadmap.md` Phase 3 item 11 gets it right ("invariant 5 … the docstring numbers the same
  rule 2").
- **Failure:** a Maxim proposal that names invariant 2 argues against a rule P1 doesn't touch (the AUT allowlist),
  and Maxim's review rejects or misreads it.
- **Fix:** "invariant 5 (the docstring's rule 2) and the schema default `target="player"`".

### E5. TF2 excludes refusals made before `tool.run`, not before the modulator. Overdrive's validator and N5 both run inside `tool.run`

- **Location:** §6, "A stale refusal is a percept …" ("Maxim's TF2 already excludes refusals the game makes before
  the modulator runs"); §7 N5.
- **What happens:** TF2 (`M/docs/plans/tool_failure_credit.md`) books failure credit "only when the invocation
  reached `tool.run`". `ModulatorAffordanceTool.execute` (`M/src/maxim/embodiment/tool_bridge.py:521-583`) is
  `tool.run`. Inside it, `check_affordance_requires` is called first, and a refusal there returns
  `success=False` and is booked, because the tool ran. Then `modulator.execute` runs, where
  `StructureModulator.apply` and `parse_action` refuse. So a refusal "before the modulator runs" is still booked if
  it happens in N5's world-backed `check_affordance_requires`, and every Overdrive validator refusal is booked
  too. Only a check that runs before Maxim's tool invocation is exempt.
- **Failure:** PR 10 puts the staleness check in the modulator or in `check_affordance_requires`, which is where it
  naturally reads live cells, and Bio D2's state-blind NEGATIVE comes back.
- **Fix:** say "before Maxim's `tool.run`", and say where the stale check runs: in the simulation lane, before the
  tool call is dispatched to Maxim. Note in N5 that its refusals are booked under TF2, so N5 must never carry
  staleness.

### E6. "The 453 ms `_power_field` cost disappears" leaves out the research's caveat, and the root fix it needs isn't in any PR

- **Location:** §5, second bullet.
- **What happens:** the 453 ms is CP-1's figure (`concurrency_performance.md`), one source on the 16×10×4 m tile at
  5.12 M cells. Its root cause is that `sphere_overlap` makes 64 passes over the whole grid
  (`world/world.py:40-59`, unchanged on act-validation). architecture.md §3.2 says the sphere deposit "remains
  only for external sources such as a spark or a torch". v2's `ignite` is still a source until PR 7, and a spark
  or torch after it. CP-1's root fix (overlap only over the sphere's bounding box) isn't listed in §11.
- **Failure:** PRs 3 to 6 run at 1 / 2 / 6 substeps per 0.5 s step with the full-grid overlap per `advance`, which
  is X1's 2.6–10× cost. A spark at max after PR 7 still costs about 450 ms per call.
- **Fix:** "disappears for fires; sources keep it until the bounding-box fix", and put the bounding-box fix in PR 3.

### E7. §3.1 says today's burning "doesn't converge"; §3.0 and the probe it cites say it does

- **Location:** §3.1, first measured reason; compare §3.0 ("today's law converges, slowly").
- **What happens:** physics.md §0's table at 90 s gives 0.504 / 0.500 / 0.583 / 0.583 / 0.583 from dx 0.2 to
  0.0125 m. It is non-monotone across the game's three rigs and constant from 0.05 m down, so in the 1-D probe it
  converges. The honest claim is "non-monotone across the game rigs, with a spread of 0.25 at 120 s". The same
  table shows the proposed energy-limited law with a 0.07–0.08 spread across the game rigs at R = 0.25 m. That is
  inside the gate's 0.1, but not by §3.3's 2× margin. That error is first order, from the source edge cutting a
  coarse cell. This is the very case §3.0 says converging doesn't cover.
- **Fix:** reword §3.1's bullet, and add that the probe's energy-limited spread is 0.07–0.08 at R = 0.25 m, which
  is why §3.0's reconstruction requirement is needed on top.

### E8. The probes behind the design's decisions aren't committed, so its measured numbers can't be reproduced

- **Location:** §2.3 (5.1 ms), §3.1 (the slab and ignition tables), §4 (0.6 / 3.8 / 28.8 ms); architecture.md says
  its scripts are "beside this file", and physics.md says they ran "from the scratchpad".
- **What happens:** `bench.py`, `bench2.py`, `bench3.py`, `exp1d.py`, `stefan.py` and `run2.py` exist nowhere in
  the repo or its history (searched all worktrees and `git log --all`). I could check the ignition table
  analytically: a lumped first cell takes ρc·dx·ΔT/q″ = 600·1700·0.2·330/5e4 = 1346 s at 0.2 m (the table says
  1350), and the closed form gives 5.23 s. The slab table and the benchmark timings can't be checked.
- **Fix:** commit the probes under `docs/design/research/states_of_matter/probes/` (or land them in PR 2's
  `verify/`), or mark the numbers "not reproducible" until PR 2 re-measures them.

### E9. §6's PR numbers are v1's, and contradict §11

- **Location:** §6, last bullet ("PR 3 builds the lane skeleton; PR 4 only adds to it … PR 3's golden fixtures
  already include the `busy` error code").
- **What happens:** in §11, PR 3 is `phase1/sim-clock` and PR 4 is material table v1. The lane skeleton is in #5
  (protocol) and the thinking lane in #10 (lanes).
- **Failure:** PR 3 (sim-clock) is scoped to include the lane thread and `host_seq` and fixtures, or #5 omits them.
- **Fix:** renumber to #5 and #10.

### E10. "Cost is O(changed region)" for support connectivity isn't supported by a measurement, and the quoted relabel timings measure something else

- **Location:** §4, second bullet.
- **What happens:** the 0.6 / 3.8 / 28.8 ms figures are `ndimage.label` of all *open* cells on the synthetic tile
  (architecture.md §1.6). §4 labels *solids against anchored support*. Whether a cluster is still anchored is
  non-local: removing one cell can detach a cluster of any size, so the label has to cover the whole affected
  component, not the changed region. The only local figure (0.67 ms, one 2×2×4 m column) isn't a support test.
- **Fix:** say "a full relabel of solids costs about the open-cell figures (to be measured); the incremental bound
  is the affected component, not the changed cells", and add the measurement to PR 2 or PR 7.

### E11. Numbers from memory that the design relies on, unmarked

The design marks only q″_f as from memory. These also come from the research's from-memory lists
(physics.md §0 to §5 and the closing list) and feed decisions here:
- **Kawagoe's 0.5·A√H** (physics.md B-8, from memory). It is the vent model of §2.2, and so the "burns away" half
  of the exit test (§9, Q1).
- **ΔH_c,eff = 12.4 MJ/kg** (Tewarson, from memory). It produces §1's "1.2 kg". Babrauskas's verified 12–15 MJ/kg
  gives 1.0–1.2 kg, so the conclusion is robust, but the number isn't verified.
- **The 10% end of the extinction ramp** (§3.1). physics.md calls the CFAST sources "conflicting" and asks the
  design to "cite both". §3.1 states it as fact.
- **Char strength ≈ 0.1 of virgin and Eurocode's k_y,θ** (physics.md §3, from memory). They are the
  "temperature-dependent factor from a data table" of §3.2.
- **The heat-balance skin's 10–15% profile constant** (physics.md §1, from memory). §3.4's "thermally thick
  ignition: the same time at every cell size" rests on it.

**Fix:** mark each one *from memory* where §1, §2.2, §3.1 and §3.2 use it, and list them as PR 4's (material
table v1) verification items.

## NIT

- **N1. "The 3×3×2 m scene's air holds about 4 kg of O₂"** (§1). That is true of the cross-tier scene (crate plus a
  3.6 m³ wall: 14.18 m³, 3.96 kg; benchmarking.md). The fiercest-fire gate's scene has no wall: 17.78 m³, about
  4.95 kg (world_fields.md says 5.0). And "1.2 kg" assumes extinction at 15%, while §3.1 ramps down to 10%, which
  gives about 2.2–2.8 kg. Both are far below 130 kg, so the outcome class stands. Name the scene and the
  extinction point.
- **N2. "Goes out in a few turns"** (§3.5). The time depends on the heat release rate: physics.md's 5–7 turns is at
  full power, and benchmarking.md's well-mixed reference at 60 kW is about 40 turns. v2's fire power is emergent,
  so say "after about 1 kg of O₂ is used", not a turn count.
- **N3. "Agrees across rigs within 1 °C"** (§1). The source (act-validation `docs/architecture.md`) says laptop
  against rig. Re-measured at turn 22: 317.00 / 316.39 / 313.97 °C, so max is 3 °C off. The driver ratio
  (rig/laptop) is 1.33–1.50 over turns 11–22, as stated, and 1.19 at turn 10. The integrity figures
  0.703 / 0.567 / 0.514 at turn 22 reproduce exactly (0.7032 / 0.5672 / 0.5138).
- **N4. "Clamping created mass in SS13"** (§2.6). world_fields.md and physics.md §4 say SS13's *negative moles*
  came from unportioned sharing, and that clamping *would* create mass. Reword.
- **N5. Name the tile.** The 5.1 MB per region, the 5 ms per region read and the 453 ms are all on the synthetic
  16×10×4 m tile at 5.12 M cells. The crate scene at max is 144 k cells, 0.14 MB per region mask.
- **N6. "Estimated state is about 91 B/cell"** (§2.5). 91 B is the whole footprint: 21 B saved, 4 derived,
  24 caches, 24 temporaries and 18 frame (architecture.md §3.1), estimated from dtypes. It omits §2.1's `loose`
  flag, packing fraction and per-face skin state. Call it "footprint" and add the new fields.
- **N7. "Precomputed per-material bounds remove the per-substep rebuild of conductances"** (§5). The bounds remove
  `stable_dt`'s per-call rebuild. The per-substep rebuild is `heat.substep` calling `_face_conductances` every
  substep (`world/heat.py:56-73`), and only a cached conductance array removes it.
- **N8.** architecture.md §1.4's illustrative `wood_flaming` doesn't close its own mass balance (1 + 1.15 = 2.15 in,
  1.6 + 0.53 + 0.004 + 0.016 + 0.25 = 2.40 out). The loader §2.5 specifies would refuse it. Fix it before it's
  copied into `data/`.
- **N9. "Maxim's cerebellum would learn that `ignite` does nothing"** (§1, P3). It is true in effect. Mechanically,
  `ForwardModel.update` learns the absolute post-call readings per parameter bucket, not a delta
  (`M/src/maxim/embodiment/cerebellum.py:369-399`). On a crate that is already burning, it learns "hot after
  ignite", which is right for the wrong reason. P3's evidence should say that.
- **N10. "Costing microseconds"** (§2.2, zone exchange) is an estimate in architecture.md §3.5, not a measurement.

## Checked and found correct

- **The convergence numbers.** Turn-22 integrity 0.703 / 0.567 / 0.514 (re-measured). The laptop and rig mean
  temperatures agree within 1 °C, and the degradation driver is 1.3–1.5× larger at rig (re-measured, turns 11–22).
  `damage.thermal_degrade` is a kinked threshold, `rate·max(0, T − T_c)` on cell means, then deletion at
  integrity 0.
- **The ignition numbers.** The closed form is 5.2 s, derived from the erfc surface solution with wood's
  k = 0.15, ρ = 600, c = 1700, ΔT = 330 K and 50 kW/m². The heated layer √(αt) is 0.87 mm at 5 s.
  t ∝ dx for a cell-mean threshold (lumped estimate 1346 s at 0.2 m).
- **The sealed-room arithmetic** for the cross-tier scene: 3.96 kg of O₂, and 129.6 kg of crate. Huggett's
  13.1 MJ/kg O₂ is marked verified in physics.md, with a citation.
- **The cost numbers.** The 3× / 1.5× / 1.125× substep cost (DX1). The 97–183 ms substep and the 453 ms
  `_power_field` are quoted correctly from CP-1. The 0.6 / 3.8 / 28.8 ms, 128 / 512 / 2048 MB, 7 / 58 / 466 MB
  and 41 MB frame figures are quoted correctly from architecture.md.
- **The 1-D slab table** (0.504 / 0.500 / 0.583 and 0.791 / 0.739 / 0.713) is quoted correctly from physics.md.
- **Regions.** On act-validation, `Region.cells` is a full-grid bool `Mask`, `paint` takes cells from earlier
  regions, `scene._check_no_solid_overlaps` exists, and both known gaps (a destroyed region claims its space;
  overlap judged on boxes) are in `docs/architecture.md`.
- **The known gaps §2 closes.** "Air only conducts", the power falling back into air, a destroyed cell losing its
  heat, and the fuel gap are all listed. The two strict fire red gates exist with those names.
- **The `ignite` band-aid.** It is `TEMPORARY(phase1)` in `data/world/actions.yaml`.
- **Maxim, the cerebellum:** `entity_state` is read right after `modulator.execute` in the same call, and fed to
  `observe_from_action` (`tool_bridge.py:580-590, 864-890`). A failed result returns before it, and drops
  metadata.
- **Maxim, the wall clock:** drift dt is `time.time() - _last_poll` (`body.py:292-298`), and
  `FailureMode.last_fired = time.time()` (`sem.py:1560`).
- **Maxim, scene entities:** they are never ticked. The only drift caller is `Embodiment.evaluate_failures`, and
  the actor tool builds an ephemeral `Embodiment(scene_entity)` per call (`simulation/tools.py:879`), with
  `_last_poll = 0`.
- **Maxim, couplings:** they are parsed and never read (no reader of `couplings` / `modulations` in `src/maxim`).
- **Maxim, `world_set_axis`:** it writes root sensors only (`root.sensors`, `root.vital_metrics`), takes
  `owner=`, and clamps to the range. The Minecraft backend uses it with `owner="minecraft_bridge"`, and
  `minecraft_player.yaml` declares `health` and `oxygen`.
- **Maxim, `requires`:** it is checked via `hasattr(modulator, "check_affordance_requires")`, which Overdrive's
  modulator lacks, so a declared `requires` gates on nothing (N5's premise).
- **Maxim, TF2:** the text is quoted correctly (the scope problem is E5). GL2b's `NociceptorSpec` is planned in
  `autonomic_layer.md`.
- **The finding ids, which say what the design says:** DD1, DD2, DD3, DD4, DD5, DD7 (thread-scoped, the widened
  list, proven by a planted `time.time()`), DD10, DA-1, DA-2, DA-3, DA-7, DA-10, DX1, DX2 (the "count of physics
  steps" alternative is in it), DX7, Bio D1, Bio D2.
- **v1's section numbers** cited (§2, §2.3, §4, §4.4, §7) exist with those contents.
- **N4 and N8 are done on act-validation:** the bridge refuses a foreign target with "name the <region> as the
  target", and it generates limit descriptions.
- **Volumetric fog** needs Godot 4's Forward+ renderer (Q5).
