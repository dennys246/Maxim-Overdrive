Inventory of contracts stated in more than one place: the world, physics and perception domain. Everything below was read at the worktree's HEAD. D means the section defines the contract, R means it references or links it. Contradictions come first.

## Contradictions (copies DIFFER)

1. **Phase 1 exit scenario**. There are six live definitions, and they name three different exits:
   - roadmap.md:55 (D): "light a slab with the torch, and watch it char, burn and flame out… The crate moves to Phase 2". vertical_slice.md:57 §3.3 and VS5 agree ("the torch-lit slab"). long_term_features.md:26 also agrees.
   - long_term_features.md:25 contradicts its own line 26: "'light a built fire' as the exit".
   - fire_model.md §7 :311 (D): "The player lights a built fire… starter under three or four sticks leaned on a crate", with the slab only as a fallback.
   - tile_and_client.md §6 :377–445 (D): the crate bed burns away, gated on `t_gone`, `t_crack` and `t_glow`. checklists.md step 8 :217 (R) still points at it.
   - world_model.md D26 :41 and foundations_plan.md §2 :16 (D): "set a crate on fire, watch it crack, glow and burn away by a fuel-mass law".
   - Proposed owner: roadmap Phase 1 "Exit", since the owner's fallback ruling lives there. Tile §6 and fire_model §7 should be marked superseded.
2. **Band gate vs outcome margin** (binary outcomes):
   - world_model.md §3 :135–137 (D) gates the band's **width**: "gate that width. This replaces v2's outcome-margin rule".
   - tile §6.3 item 7 :414 (D) gates the operating point: "The script's D is ≥ 2× the band's upper edge". verify_harness.md:57 (R) follows the tile: "operating point clears the band by its margin".
   - world_v2.md §3.3 :200 (D): "at least 2× its cross-rig spread".
   - sem_stimuli §2.3 :80 and npcs §2.1 :140 still say "outcome margin".
   - Owner: world_model §3. It needs to say which quantity is gated.
3. **Cross-grid convergence criterion**:
   - tile §6.3 item 8 :418: "Pass when |e₀.₁| ≤ tol, and (|e₀.₂| ≥ |e₀.₁| or |e₀.₁| ≤ tol/4)".
   - verify_harness §4 :60 `agrees`: "each coarser grid's error is no smaller than the next finer one's, **with no allowance**".
   - fire_model §6.1 (R) uses tile §6.3's tolerances. world_model §1.1 (D, the general rule) agrees with both at high level.
   - Owner: world_model §1.1 for the rule, verify_harness §4 for the predicate. Tile item 8 should link to them.
4. **Material data files and their split**:
   - fire_model §9.1 :386–392: "`core.yaml` v1"; "v0 fixtures migrate through a registered `materials_v0_to_v1`"; variants are their own part.
   - fire_solid §5.1 :345, :350: "v0, unchanged… `materials_v0_to_v1` is dropped"; "Variants live in their recipe file".
   - world_v2 §2.5 and world_model §8 define a single "Material table v1". tile §5.1 says "Each goes into material table v1".
   - Owner: fire_solid §5.1, the later and more specific text. fire_model §9.1 should keep only its refusal list or link.
5. **Snapshot channel names for fuel**. Four different names:
   - fire_model §9.2 :415: `segment_glow`, `burning`.
   - fire_solid §5.6 :425–429: `surface_temperature_c` f16 and `ignited_fraction`; "`burning` stays reserved"; "supersede fire_model §9.2's…".
   - client_rendering.md:120–121 and checklists step 7 :205: `surface_glow` (u8, offset 525 °C) and `burning`.
   - Owner: fire_solid §5.6. The client channel table must reconcile with it.
6. **Energy ledger lines**:
   - fire_model §9.2 :438: "Tile §5.4's `Δ(skins)` and `flame_radiative.unreceived` are replaced".
   - Still used: fire_solid §5.4 :398 ("in tile §5.4's equation… Δ(skins)"), sem_stimuli §3.1 :89 ("debited from the flame's unreceived share") and tile §2.1 :133.
   - Owner: one ledger section, proposed as fire_model §9.2, with the others linking.
7. **Object–grid coupling**:
   - fire_model §2.2 :69: "convection h(T_s − T_cell) with each overlapped cell". §2.1 :54 coupling row is "CSR".
   - fire_solid §3.1 :170: "Nothing an object loses enters an air cell". §1.1 :78: "No per-cell CSR", sorted COO `contact`.
   - Owner: fire_solid §1.1 and §3.1.
8. **Pyrolysis rate law**:
   - fire_model §3.1 :110: "The rate law is R0's choice", threshold or Arrhenius.
   - fire_solid §4.2 :223: "One rate law, FDS's n-step Arrhenius… threshold law is dropped".
   - Also stale: tile §5.1–5.2 (T_p, L_g, m'' = q''_net/L_g) and world_model §3's table rows for ignition, ablation and pyrolysis. fire_model §10.1 lists the tile rows as revised but not world_model §3.
   - Owner: fire_solid §4.2.
9. **Extinction ("goes out")**:
   - world_model §3 :139: "when the zone's O₂ fraction falls to the extinction limit, with a ramp from 15% to 10%". This is not in fire_model §10.1's revision list.
   - fire_model §4.3 per flame, :120: "decided per flame, not per part".
   - fire_solid §4.4 :252: "when the flaming part's mass flux falls below m''_ext". This is scoped to the cone, where a lone cluster equals the part.
   - fire_model §0.4 cites V7 1's flux band, while fire_solid says "not V7 1's 2.7–8.3 g/m²s".
   - Owner: fire_model §4.3. world_model's O₂ definition should be marked Phase 2.
10. **R0/R1 validation ladder grading**:
    - fire_model §6.2 :290–291: R0 "the rate-law choice"; R1 "no sustained flaming once the heater is removed" is a pass criterion.
    - fire_solid §4.5 :307: "The heater removed has no MaCFP-4 data: a prediction, not graded". Its PMMA is graded at "50, 65", where fire_model has only 65.
    - Owner: fire_solid §4.5 and §4.6 for R0 and R1. fire_model §6.1–6.2 for the other rungs.
11. **Scene format versions**:
    - tile §1.3 :80: "v0 migrates by the literal `spawns: []`". checklists 3b :67: "scene v0 is refused by version, not migrated".
    - fire_model §7 :326: "Scene v2… a registered migration from v1". fire_solid §5.2: "`SCENE_VERSION` is 0… a bump and a refusal test, not a migration".
    - checklists 3b :80: "Fuel-bed fields (φ, σ) on primitives". fire_solid :370: "Tile §1.3 drops `bed:` (done…)". The tile text is not done: §1.1 :62–64 still has the crate as "porous fuel bed… cells carry φ, σ", §1.3 still validates φ and σ, and §11 says "+ … bed fields".
    - Owner: fire_solid §5.2. The tile copy and checklists 3b need editing.
12. **`kindle` target and pilot**:
    - tile §3.2 :227: the named solid's "authored box surface lies within 50 mm… no deeper than 50 mm inside; two candidates is `ambiguous_point`"; `min_radius_m` = 0.2; deposit onto the bed skin.
    - fire_model §5.4 :246: "nearest the point within 50 mm, with a tie within 1 mm refused"; the pilot is a flame object, which "replaces the sphere deposit and the 0.2 m minimum radius".
    - Log `target`: tile :231 "`target: null`" vs boundaries §6.2 :412 "`target`: a stable id… resolved at the door".
    - Owner: fire_model §5.4 for derivation and pilot. Boundaries §6.2 for the log field.
13. **Flame radiation to receivers**:
    - tile §0 T14 and §2.1 :132 use the point source "q'' = χ_r·Q̇/(4πd²)", and the body also gets radiation "from each hot exposed skin face by a view factor".
    - fire_model §4.4 :184: analytic cylinder, "Receivers are segments, solid cell faces and body regions… revises T14".
    - sem_stimuli §2.3 :78: "Cell faces exchange nothing with bodies in v1". This contradicts tile's face-to-body radiation, which sem_stimuli §3.1's by-name supersession does not cover.
    - Owner: fire_model §4.4 for emission, sem_stimuli §2.3 for the body side.
14. **Body model leftovers**:
    - tile §8 :466 lists the divergence "no metabolism", but sem_stimuli §3.1 supersedes "no metabolism".
    - fire_model §5.1 :214: "Core temperature has one owner: world-written… or Maxim-drifted". sem_stimuli §3.1 :88 settles it as world-side: "core node, sole producer of `core_temperature`".
    - Owner: sem_stimuli §3.1.
15. **Divergence tags (ANALOG vs EARN)**:
    - fire_model §5.1 :223–224: skin stopgap "**ANALOG**"; in-view luminance "**ANALOG**".
    - sem_stimuli :128: "`fire_model.md` §5.1's stopgap, **EARN** on OD-C10"; §2.2: "`luminance` the EARN stopgap".
    - Owner: sem_stimuli §2.2 and §3.3.
16. **Push path into Maxim bodies**:
    - boundaries §4.3 :264 and npcs §7.2 :940: "a pure function of the agent's pinned frame".
    - world_v2 N6: written "after each advance".
    - sem_stimuli §4.4 pushes per binding from `BoundFrame` at the cognition rate (D14), and §6.1 supersedes the pinned frame "by name". The two older docs still define it.
    - Owner: sem_stimuli §4.4.
17. **Frame publication cadence**:
    - boundaries §4.2 :245: "after each physics step… and after each tick that applied an intent".
    - tile §4 :288: "every tick on which any intent was applied **or refused**, or any actor or pilot changed".
    - Owner: tile §4, the superset. Boundaries should link to it.
18. **Tick order (D10)**:
    - realtime §2.1 :82 (superseded): records, agents, physics, outputs.
    - tile §2.3 :169: records, **move bodies**, agents, physics, outputs.
    - sem_stimuli §4.1 :143: eight steps, adding contact and tissue, frame build and merge, with physics allowed to overlap the agent step.
    - Owner: sem_stimuli §4.1 now, or move it to the 5a composition note. Tile §2.3 should link.
19. **`kind_rank`**: tile §3.1 :206 uses "0… 1… 2… 3", while checklists 5a :113 says "ranked 0/10/20/30". The ordering key itself agrees in three places (see the agreeing list).
20. **Region ownership and whether the id array closes the PR 1 gaps**:
    - world_v2 §2.4 :107: "That removes PR 1's interim rule". architecture.md:107, :112 and :119: "(the region id array…) removes it/both".
    - world_model §5 :159: "That alone doesn't remove PR 1's interim rules"; it needs CSG, which is Phase 2.
    - fire_model §2.2 :67: "Region membership is cells ∪ objects". fire_solid §1.3 :112: "cells only or objects only; mixing comes with 6.2". This one is staged, not a contradiction.
    - Owner: world_model §5, with fire_solid §1.3 for objects.
21. **Thin-feature rule**:
    - architecture.md:48 and :123: "two of the coarsest rig's cells", with no exemption.
    - fire_model §10.1 :448: fuel objects are exempt as `rod`/`slab`/`bed`. It lists architecture's "How the rule is kept" as revised, but that text is unchanged.
    - architecture :123 would solve the imagination gap with the thin-feature rule. fire_model §9.2 :431: "`place` creates fuel objects for sub-cell geometry".
    - tile §1.1 :64 has its own scoping: "applies to the box, not the slats".
    - Owner: world_model §1.1, where the verification rule lives (CLAUDE.md also states it).
22. **Fuel scope and burn law in the roadmap**:
    - roadmap :36: "a cell's burn rate must estimate the integral… over the cell" (copied from world_v2 §3.0). fire_model §0.3 replaces that with sub-grid objects.
    - roadmap :72 "Moved from Phase 1 by D26: … fuel recession and pyrolysis" vs fire_model §10.1 "pyrolysis and fusion enter Phase 1".
    - roadmap :22 still has the clinic in Phase 1 (against D27), and its Open questions still ask about the 6 s turn length (against T3).
23. **Heat state, ledger tolerance and field registry** (world_v2 vs world_model):
    - world_v2 §2.3 :99 "5.1 ms" vs world_model §4 :146 "63.9 ms".
    - world_v2 §2.6 :142 "to 1e-10" vs world_model §4 :153 "relative, not 1e-10 absolute".
    - world_v2 §2.5 :117 "`data/world/fields.yaml`, a declaration" vs boundaries §9.1 :673 "The in-code field registry is primary" and checklists 5a :109 "one list in code". sem_stimuli §3.1 :103 still cites world_v2 §2.5 as the registry's home.
    - world_v2 §2.1 :68 solid cells hold "fuel mass f32" vs fire_model :60 "Inventories are kg per object and segment, never kg/m³ of a cell".
    - Owners: world_model §4. Boundaries §9.1 for the registry. fire_model §2.1 for fuel containers.
24. **Fire acts and affordances**:
    - world_v2 §7 N3 :316 verbs: "heat, cool, pour, ignite, vent, douse". world_v2 §8 :364: "`extinguish` changes meaning".
    - world_model §8: `extinguish` retired, `douse` added. fire_model §5.4: `ignite` and `extinguish` leave `parse_action`.
    - Owner: fire_model §5.4.

## Agreeing restatements (should collapse to one owner)

- **B-13 (percepts only through physical channels)**: boundaries §4.4 :270 (D); npcs §7.1 :922 (restates the first bullet nearly verbatim, cites §4.4); tile §8; fire_model §0.6 and §5. Owner: boundaries §4.4.
- **The stimulus split and leak tests**: sem_stimuli §1 :31 (D) and fire_model §5.1 :210 (D). Near-identical; sem_stimuli adds "pooling". Owner: sem_stimuli §1.
- **Region sensors as lab-only instruments, and `cell_size_m` dropped**: boundaries §4.4, npcs §7.1 and §7.3, fire_model §5.4–5.5, fire_solid §2, sem_stimuli §6.1, tile §10. Owner: boundaries §4.4.
- **`world_set_axis` behaviour** (root-only, OD-C10, clamps and returns True, False is an error): boundaries §4.3, npcs §7.2, fire_model §5.1, sem_stimuli §2.1 and §4.3–4.4. Owner: sem_stimuli §4.4.
- **Tick 0.1 s, physics every 5 ticks**: realtime §2.2 (superseded), tile T3 and §6.1 :381, sem_stimuli §2.2 :65, npcs §9 :1015, foundations T3. Owner: tile §6.1.
- **Ordering key**: boundaries §6.2 :427 ("stated here and nowhere else"), but it is also restated at tile §3.1 :196 and npcs §9 :1024.
- **Three clocks table**: npcs §1 :81 and boundaries §7.3 :562. Owner: npcs §1.
- **Verification rule**: world_model §1.1 is the owner. architecture "The verification rule", roadmap standing rules and verify_harness §6 reference it. The deposit rule (exact cell average or volume overlap) is stated in architecture :38, roadmap standing rules and world_model §3.
- **"Reconstruct, decide at the point, integrate upward"**: world_v2 §3.0 (D), world_model §3 and D25 (D, law table), roadmap :36. Owner: world_model §3.

## Superseded or revised docs that still define

- **realtime_lanes_coop.md** (marked superseded) still defines WorldConfig §2.2, tick order §2.1 and per-rig `substeps_per_physics_step` §2.3. world_v2 §5 :247 keeps it alive with "v1 §2 stands", and :249 keeps "The rig field".
- **world_v2.md** is not marked superseded, and world_model says "v2 §2.1 stands" (:103) and "v2 §8 stands" (:203). It still defines rig-cell containers, the fields.yaml registry, the 1e-10 ledger, the outcome margin, SEM N1–N8 and the lab exit (§9 :404).
- **tile_and_client.md §5** (constants, the four laws, the bed's numbers), **T14** and **§3.2's pilot deposit** were revised by fire_model §10.1 but carry no supersession marker. Only §2.1 has by-name notes. checklists step 6 is properly marked superseded.
- **world_model.md** D29, D30 and §3's ignition, ablation and pyrolysis rows were revised by fire_model and are unmarked.
- **fire_model.md** §3.1, §9.1 and §9.2 were overridden by fire_solid and are unmarked in fire_model.