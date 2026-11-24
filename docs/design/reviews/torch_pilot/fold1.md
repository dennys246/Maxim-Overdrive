# Round 1 fold: `torch_pilot.md` (author's record, 2026-11-22)

**Round 1** reviewed fcc6e55 with six lenses: Executor, Physics and resolution, Architecture, Wire integrity,
Bio-faithful integration, and Determinism. Executor was added to the owner's five because `docs/code_review.md`
("Design reviews") requires it.

| Lens | BLOCKER | SHOULD-FIX | NIT |
|---|---|---|---|
| Executor (`round1_executor.md`) | 2 | 10 | 7 |
| Physics (`round1_physics.md`) | 3 | 8 | 7 |
| Architecture (`round1_architecture.md`) | 2 | 8 | 3 |
| Wire integrity (`round1_wire.md`) | 2 | 8 | 7 |
| Determinism (`round1_determinism.md`) | 1 | 7 | 2 |
| Bio-faithful (`round1_bio_faithful.md`) | 0 | 3 | 4 |

**The "Change" column is the author's claim, not a status.** The delta round's reviewers set each finding's status
(CLAUDE.md, O25). "Verified" says what the author ran; § numbers are the folded design's.

**The convergent blocker was the author's error.** E-B1, P-B2, A-B1 and W-B1 found, independently, that the draft
"flipped" all three `ignite` red gates by moving them onto paths that cannot fail. The fold rewrites none of them. Each
waits on Q6.

| Id | Change | Verified |
|---|---|---|
| E-B1, P-B2, A-B1, W-B1 | §9.4: no gate is rewritten; each stays strict until its mechanism is deleted (Q6). Beat 8 carries the burned-fuel meaning onto objects, with a deletion proof | read the three tests' bodies at fcc6e55 |
| E-B2 | §9.4: per-strip A_ov against fine quadrature, at asymmetric offsets 0.13ℓ and 0.71ℓ, r = 0.051 m | numbers.md: closed form against quadrature, worst strip 1.55×10⁻¹⁰ m² |
| P-B1, E-S7 | §3: cell regions by their authored footprint, never cells; distances in f64 metres, with no integer claim | `sim_core.md` §7 ("`Region` keeps its authored footprint") |
| P-B3, E-S6 | §9.2: across grids within max(e_dt, one step), where e_dt is the shipped step's measured error. The §7 gate uses that bar, and a never-flash case is an assertion | — |
| A-B2, W-S5 | the preamble claims D-S2 for Phase 1; §10 turns fire_solid §7's D-S2 row and client_objects §7.3 into links, and step 8 maps G1–G5 | read fire_solid §7, client_objects §7.3 |
| W-B2 | §2: the `face` enum, `centre_m` as f64, a `target` kind in place of a sentinel, `region_id`, the digest member (sim_core §9, empty adds no bytes), load refusals, step 9's save row | — |
| D-B1 | §2: the lifecycle in tick order (live by interval, cut by the applier in step 1, removed after the last covered physics step); checklist cases | `sem_stimuli.md` §4.1, sim_core §3 |
| E-S1 | §9.4: the burned-fuel gate's subject (`_power_field`) is named, and its fate is Q6 | `src/simcore/core/applier.py` `HeatSource` producer |
| E-S2, P-S6, D-S4 | §5: E_p,t written in `tick_us` and `physics_every`; holds in seconds; the time study halves `tick_us`; one named expression for ledger and solve | `SimConfig` fields, `simulation.py:60–61` |
| E-S3, P-N1 | §7: concrete at the new ceiling, with losses | numbers.md (march fixed by the author; 290 against 300 K lossless) |
| E-S4, P-N7, P-S4 | §6, §7: coverage over all offsets, the energy off the slab, and r ≥ W/2 so the disc fits the slab; "stays clear" becomes "reduced" | numbers.md |
| E-S5, P-N2 | §5, §9.1: no cap; a part may reflash only when piloted, and beat 3 asserts at most one flash per part | — |
| E-S8, A-S7 | §2, §9.3: at 6.1b, a digest rebuilt from records; save round trip and golden at step 9 | fire_solid §5.5 |
| E-S9, P-N6 | §3, §10: the catalogue refuses slab recipes ≤ 2 mm (a fire_solid §5.1 edit) | — |
| E-S10 | §5, §9.4: lag after `end_tick` named; the control deletes the pilot condition in a hold ending inside the band | — |
| E-N1 | §3: the NN5 citation removed; the target rule is now owned here | read fire_model §10.1 |
| E-N2 | §9.2: the dx path cited to fire_solid §3.2 | — |
| E-N3 | §1: fire_solid §6's non-uniform heater cited as the pattern | — |
| E-N4 | numbers.md: a closed-form check added | ran it |
| E-N5, W-N4 | §11 Q5: `seq` on the row; `end_tick` narrowing by refusal | — |
| E-N6 | §4.2: convective loss stays on before flash, so fire_solid §3.1 is untouched; §10 lists fire_solid §2's row | — |
| E-N7, P-N3 | §9.1: the 0.1 is `[engineering]` alone | — |
| P-S1 | §4.2, §6: losses on before flash; ceiling = min ε_r · 50 kW/m², the highest flux graded and FDS-verified | fire_solid §4.5, §4.6 |
| P-S2 | §4.2: absorbed whole, `[engineering]` | — |
| P-S3 | §7: the cold-gauge residual named; m''_flash's validation gap; energy off the slab; the Q2 extrapolation | numbers.md |
| P-S5 | §9.2: one margin rule for every binary beat, from its measured spread | — |
| P-S7 | §9.2: in-time convergence by first order; the 2× band margin dropped, and its absence from B30 raised (Q8) | `standards_backlog.md` B30 row read |
| P-S8 | §9.4: times to 25, 50 and 75% of the flaming area, as fire_solid §6 | — |
| P-N4 | §7: every rod `kindle` is an extrapolation (14.3 kW/m² ring mean) | numbers.md |
| P-N5 | §9.1: the tautological clause removed | — |
| A-S1 | §7, Q4: the fix is the 6.2 design's choice of mechanism; partial transfer alone isn't one | read fire_solid §1.2 |
| A-S2 | §0, §2: "6.2's held-flame design replaces it and defines what becomes of a saved one"; no migration is promised | fire_model §12 |
| A-S3 | §10: roadmap Phase 2 lists `core/solid.py` for `TEMPORARY(phase2/6.2)` | — |
| A-S4, W-S7 | §10: fire_model §5.4, §10.2 and §12; fire_solid §1.3, §2, §4.4, §5.1, §5.5; sim_core §6 and §9; client_objects §5.4; the roadmap; the 5b sphere band-aid | grepped each "6.4" |
| A-S5 | §3, §10: a ranked query in layer 2, the tie policy per act; the sub-cell session is told (Q1) | read subcell §7.1 |
| A-S6 | §2: the appender, the cut and the remover named; `region_gone` for cell targets only | — |
| A-S8 | §2, §3, Q1, Q5: `object_id` and `region_id` both recorded; candidates of every role | read subcell §1, §3.1, §12 |
| A-N1, W-N1 | §5: a lab instrument, not `WorkCounters` | — |
| A-N2 | §7: no spread beyond the footprint is a Known gap | — |
| A-N3 | §10 kept as a changes table (client_objects §8's precedent). It is the edit list Q9 asks to apply | lint_contracts: PASS |
| W-S1 | §10: `actions.yaml` bumps over 5b's v1; `torch.yaml` starts at v0; the ceiling is checked at item load, with a gate row | — |
| W-S2 | §10, Q5: `cause` needs `seq` on the row | tile §3.1 |
| W-S3 | the target rule is owned here, whole; fire_model §5.4 and tile §3.2 become links (§10) | — |
| W-S4 | §10: the 0.2 m floor test gives way to the two-strip floor | read the test |
| W-S6 | §3: beyond 50 mm is `not_on_surface`; burnt-out rows are candidates | — |
| W-S8 | checklist step 6: format and load refusals with gate rows | — |
| W-N2 | §3: the receipt's effect value is the derived target | — |
| W-N3 | §9.1: the residue share from the store, by fire_solid §5.6's definition | — |
| W-N5 | §9.1: `tests/scenarios/slab_exit.yaml` v0; its cap from §9.2 | — |
| W-N6 | §8: no object to aim at; the torch aims along the actor's facing | — |
| W-N7 | §1: links only | — |
| D-S1 | §2, §10: sim_core §9 member, empty adds no bytes | — |
| D-S2 | §2, §3: f64 metres, unrounded | — |
| D-S3 | §3: the face rule at edges and corners; checklist cases | — |
| D-S5 | §4.3: per pilot, scalar `math`, one call shape; cache keyed by the record and evicted on removal and rollback; §9.3 runs with a second pilot | — |
| D-S6 | §4.2: per part, pilots in key order, then the flame flux. The convective share is gone with losses on | — |
| D-S7 | §3: `pending` excluded | fire_solid §1.4 |
| D-N1 | §0, §2: 6.2's design defines saved pilots. A log break is a recorded change under sim_core §12 (not restated) | — |
| D-N2 | checklist step 9: the pilot records | — |
| B-S1 | §12: OD-A16's route is the roadmap row's. The `tool_failure_credit.md` and `roadmap_1_4.md` R4 lines and `nac.py`'s `time.time()` window are cited | `git show b98954f7:` each file; lines confirmed |
| B-S2 | §12: two delays, one of them "none in Phase 1" (OD-C8) | client_objects §5.4 |
| B-S3 | §6: NPC holds deferred to Phase 4's body design, each outside the band by its margin | tile §3.2 |
| B-N1 | §2: the record, the pilots table and `pilot_ended` are not perceivable | — |
| B-N2 | §3, §10: the agent receipt is always `accepted`; T11's sweep gains the cases | sem_stimuli §6.2 |
| B-N3 | §7: the torch heats no body | — |
| B-N4 | `lessons_maxim_in_games.md` lesson 35, in this commit; it quotes the amendment draft's slow-effects line | grepped the draft, line 55 |

**Not adopted:** none. Two decisions are flagged for the owner instead of folded:
- whether fire on structural cells leaves Phase 1 (A-B1's scope question), which is Q6;
- the exit slab's on-screen size, a consequence of P-S4's fold, which is Q7.
