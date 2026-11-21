# Fire model v1 → v2: the fold

Reviewed: `fire_model.md` at 54358fd. Folded into v2. **Status** is set by the reviewer in the delta round (O25);
until then every row reads `open`. The "Where" column is the author's claim of where v2 answers the finding; a
reviewer checks it against the tree.

The owner's rulings of 2026-11-20 (fire_model §11 items 1–3) settle A-B2, A-B3 and the cost model behind DP-S5.

## Executor

| Finding | Where in v2 | Status |
|---|---|---|
| B1 R2.5 conservation can't fail | §6.2 R2.5: closed receiver shell absorbs χ_r·Q, reciprocity, deletion of a cylinder face goes red; counted as a unit test | open |
| S1 one m''_cr for ignition and extinction | §3.2 flash at the data's t_ig definition; extinction per flame §4.3 | open |
| S2 apparent L_g circular, no band | §6.2 R1: reported, not graded; held-out fluxes | open |
| S3 R2(a) oracle is plywood; cold PMMA spreads | §6.2 R2a: cold PMMA downward dataset to find; LIFT speeds not used | open |
| S4 R4 oracle mismatch | §6.2 R4: residue at 48 min, ember tail, pilot as prescribed Q, layout from TN 2102, time to peak only once verified | open |
| S5 rates graded while saying never | §6.1: tile §6.3 tolerances kept across grids (owner ruling 2); data envelopes separate | open |
| S6 "bincount as today" false | §8.2 states bincount as the rule; no "as today" claim | open |
| S7 §10 omissions (region sensors, `kindle` deposit, T14, `imagination.place`, T13) | §10.1 rows; §5.4, §5.5 | open |
| S8 cost citation on the wrong branch, wrong tile | §8.3 cites gates `docs/architecture.md`, 40×8×6 m tile | open |
| S9 wall-flame correlation extrapolated | §4.1 flagged as extrapolation; R2b grades front position, not height | open |
| S10 n-cap test can't go red | §8.2 hygiene test: slivers below and above the floor, cap not hit, energy conserved, deletion of area-share routing goes red | open |
| S11 cross-grid gates near-vacuous | §2.2 coupling defined; §6.1 every gate names its dx path; straddle test | open |
| S12 `REFERENCE_TEMPERATURE` isn't a threshold law | §3.1 | open |
| S13 §0.1 overstates Finney and Jiang | §0.1 scoped per V7 4–5 | open |
| N1 `latent` isn't a field | §10.1 "the planned per-cell latent state" | open |
| N2 char glow temperatures | §1 row (outward faces marginal) dropped for length; `char_oxidation.md` stands | open |
| N3 accelerant E4(i) | the "verified kernel" claim is removed | open |
| N4 "severe pain", 2.8–5.8× | §5.2 | open |
| N5 Heskestad 0.235 tag | the coefficient is no longer quoted | open |
| N6 "smaller than a cell" | §0.2 "0.3–1.6 cells" | open |
| N7 sliver bug scope | §1 | open |
| N8 `ignite`/`extinguish` already retired | §5.4 cites T4 and F7 | open |
| N9 pine extinction band undefined | §6.2 R1: sustained at 25, no sustained flaming once the heater is removed | open |
| N10 5 ms for VF pairs | §8.3 uses the review's measured 40 ns analytic cylinder cost | open |

## Architecture

| Finding | Where in v2 | Status |
|---|---|---|
| A-B1 cell-keyed elements, K = 2 | §2.1 objects by persisted id, any count per cell; segments in metres; straddle test §6.1 | open |
| A-B2 rate convergence dropped | §6.1 kept (owner ruling 2) | open |
| A-B3 unsized programme, documents not revised | §10.1 rows; §10.2 sub-steps, ordering, time-box (owner ruling 3), size "unknown beyond five PRs" | open |
| A-B4 no consumers for new state | §9.2 wire tables, renamed channels, grammar before step 7, save, digest; §2.2 SEM reads segments | open |
| A-S1 T13, T14, T17, T5, tile §5.1–§5.4, §5.3 path | §10.1 | open |
| A-S2 `ignite`/`extinguish` as lab tools; red gates and band-aids without owners | §5.4 (out of `parse_action`; lab builder in tests; `kindle`'s pilot as a flame object). The two red gates and `actions.yaml`'s `TEMPORARY` ceilings: **not yet named in v2**; the author's proposal is that 6.4 flips the gates against `kindle` and retires the ceilings | open |
| A-S3 element–grid heat exchange undefined | §2.2 coupling: convection, contact conduction, radiation, by overlap | open |
| A-S4 laws that don't know elements; exemption undefined | §2.2 occupancy and the consumer list; §10.1 exemption defined (fuel recipes only, never structure). `damage.strike` and breach on fuel objects: **not yet specified** | open |
| A-S5 two act vocabularies; NPC verbs in Phase 1; the player can't build | §5.4 one `kindle`; no NPC acts in Phase 1; §7 the fire is authored, the player kindles | open |
| A-S6 no placement table; material table mixes owners | §9.1 split by owner. A per-layer placement table for the new code: **not yet in v2** | open |
| A-S7 species machinery with no consumer | §2.3 per-species zone state deferred; closure checks kept | open |
| A-S8 flame state, identity, order | §4.1 stateless, min-key id; §4.4 the held radiation field is state | open |
| A-S9 Maxim asks not routed | §11 item 10: roadmap rows and drafts on ruling | open |
| A-N1 O34's registry | §10.1 last row | open |
| A-N2 kg/m³ of cell | §2.1 kg per object | open |
| A-N3 validation materials | §9.1 test fixtures | open |
| A-N4 "every beat is graded" | §7 | open |
| A-N5 world_model §2 row | moved to §2.3 | open |

## Wire integrity and trust

| Finding | Where in v2 | Status |
|---|---|---|
| WT-B1 sub-cell fuel is air | §2.2 occupancy `solid \| holds_fuel`, consumer list, region membership; §9.2 wire tables | open |
| WT-B2 K = 2 acceptance depends on dx | §2.1 any count per cell | open |
| WT-B3 species by position | §9.1 by name with stable ids | open |
| WT-B4 imagined allocations unbudgeted | §9.2 spec v1, per-recipe ranges, budgets on objects, segments, nodes, area before allocation | open |
| WT-B5 exit scene unwritable | §7 scene v2 (rod with any axis, placement inside an owner's footprint for fuel), migration | open |
| WT-S1 v0 → v1, structural materials | §9.1 structural section kept, u8 ids stable, `materials_v0_to_v1` | open |
| WT-S2 incomplete refusals | §9.1 list | open |
| WT-S3 yields sum order-dependent | §9.1 `math.fsum`, key-sorted, 1e-12, both orders tested | open |
| WT-S4 `ignite` reachable through `execute` | §5.4 removed from `parse_action`; refusal test through `execute` | open |
| WT-S5 `kindle` stage 2 at sub-cell scale; vocabulary split; held-flame lifecycle | §5.4 derivation, tie rule, pilot as a flame object, vocabulary v1 amended. The held-flame lifecycle (expiry, `leave`, dropping): **not yet specified** | open |
| WT-S6 channel meanings | §9.2 new names `segment_glow`, `burning`, decoder fixtures | open |
| WT-S7 ledger lines | §9.2 enumerated | open |
| WT-S8 spec unversioned | §9.2 spec v1 | open |
| WT-S9 order against step 5's log writer | §9.1, §10.2 6.0 lands first | open |
| WT-S10 `requires` sensors; `target_effect` | §5.4 | open |
| WT-S11 digest and save cover latches only | §9.2 | open |
| WT-N1 path | header | open |
| WT-N2 retirements already taken; T18 labels on paper | §5.3, §5.4 | open |
| WT-N3 provenance key | §9.1 last refusal | open |
| WT-N4 `breached` stays | §5.5 lists `breached` among the region instruments an NPC never gets; it stays a lab quantity | open |
| WT-N5 "reserved in the format" | removed with K | open |

## Physics and resolution

| Finding | Where in v2 | Status |
|---|---|---|
| B1 patch mean thresholds ignition | §2.1 segments in metres with two parts; §3.2 front moves by a law at the front | open |
| B2 representation depends on dx | §2.1 authored representation, discrete rods at every spacing | open |
| B3 flame energy booked more than once | §4.2 one partitioned budget; a closed-shell ledger test §6.2 | open |
| B4 three R2 criteria can't fail | §6.2 R2b grades front position; R2a adds the de Ris foot law (§3.2) and a measured dataset | open |
| S1 per-patch extinction against R4 | §4.3 per flame; R4 must not flame out at ~2.5 g/m²s | open |
| S2 one m''_cr | §3.2 | open |
| S3 R1 band and pine curves | §6.2 R1 | open |
| S4 fit and grade on the same data | §6.2 held-out fluxes | open |
| S5 in-bed radiation, draught, O₂ dropped | §3.3 surface-to-surface radiation; O₂ and draught named as the R4 gap with a pre-check | open |
| S6 O₂ regime | §3.3 | open |
| S7 char oxidation under flame | §2.3 off under flame cover; R4 residue at 48 min and ember tail | open |
| S8 correlations outside range | §4.1 extrapolation flagged; §4.2 h(d, u) contact on thin elements | open |
| S9 clustering | §4.1 smooth merge band; R3a gap-sweep band gate | open |
| S10 pilot rule | §3.2 | open |
| N1 where (1 − χ_r)Q goes | §4.2 Q_gas | open |
| N2 χ_r unspecified | §4.2 "still to cite" | open |
| N3 R4 pilot | §6.2 prescribed Q | open |
| N4 R2.5 is verification | §6.2 | open |
| N5 moisture | §6.1 | open |

## Determinism and performance

| Finding | Where in v2 | Status |
|---|---|---|
| DP-B1 cap that "dilates" | §8.1 local substeps, implicit fallback, cap events in the digest, identical in play and test, world time never shortens | open |
| DP-B2 history-dependent visibility cache | §4.4 occlusion a pure function of current geometry; the held field between recomputes is saved state | open |
| DP-B3 K = 2 | §2.1 | open |
| DP-S1 delta form; Arrhenius forbids sleep | §8.1 delta form; §3.1 rate law graded on cost, Arrhenius needs a written cutoff | open |
| DP-S2 bounding box, cropped sums | §8.2 sleep on compact laws only; reductions over full tables; §4.4 cutoff as a law | open |
| DP-S3 clustering order, labels, RNG | §4.1 min-key ids, stateless flames; §8.2 sorted tables, topology batch, counter-based RNG | open |
| DP-S4 retirement erases slow spread | §8.2 merge into sibling, conserving everything; floor sweep | open |
| DP-S5 costs understated | §8.3 re-derived; flame count before R2.5; owner ruling 1 | open |
| DP-S6 no budget | §8.3 fire budget before R2.5; work counters primary | open |
| DP-S7 state not enumerated; lazy profiles | §3.1 profiles from authoring; §9.2 | open |
| DP-N1 cap 16 against heat's substeps | §8.1 caps per law | open |
| DP-N2 arm64 only | §12 CI offset test | open |
| DP-N3 one load, one stack | **not yet**: §8.3 cites the reports, which give load and stack | open |

## Bio-faithful integration

| Finding | Where in v2 | Status |
|---|---|---|
| B1 MP-2 against GL1 N4 and TR18, unnamed | §11 item 10: MP-2a (question) and MP-2b (named pushback, evidence) | open |
| S1 `health` can't be written on humanoids; not a stopgap | §5.1 body shape, OD-C10 prerequisite, reworded | open |
| S2 MP-1 scope and precedent | §11 item 10: MP-1(i) by config, (ii) transport; Exp 60 precedent | open |
| S3 sight has no channel; fractions have nowhere to go | §5.1 generic in-view luminance tagged ANALOG; fractions stay lab instruments until OD-C8 | open |
| S4 leak test 2 misfiles tissue | §5.1; lesson 24 | open |
| S5 lab and NPC not separated; `strike` | §5.4 two builders, golden tool surface, `strike` as a body act | open |
| S6 credit for `apply` OPEN; timing | §5.1 OPEN until OD-A16; §5.4 NPC acts in Phase 4 | open |
| S7 duplicate ids; world_v2 §7 timing | §11 item 10 reuses P3/OD-A16 and P4/OD-C10; §10.1 world_v2 §7 row | open |
| S8 NPC lesson claim; LLM prior | §7 "Not claimed" | open |
| N1 EARN/ANALOG/OPEN | §5.1 | open |
| N2 asks table | §11 item 10 | open |
| N3 phantom-credit attribution, deltas vs absolute | **not folded**: belongs to L6, kept as written | open |
| N4 client-only flourish | §12 | open |
| N5 sem.md N3 verbs | §10.1 | open |

## Not yet folded (the author's list, for the delta round)

A-S2's red gates and `TEMPORARY` ceilings; A-S4's `strike` and breach on fuel objects; A-S6's per-layer placement
table; WT-S5's held-flame lifecycle; DP-N3; Bio N3. The first four are design gaps v2 still carries.

## Delta round 1 (v2 as staged, committed as 3fd998b)

The reviewers set the statuses; the record is each report's status table, kept verbatim beside this file. Counts:

| Lens | Report | Fixed | Deferred | Open | New BLOCKER / SHOULD-FIX / NIT |
|---|---|---|---|---|---|
| Executor | `delta1_executor.md` | 21 | 0 | 3 | 2 / 8 / 7 |
| Architecture | `delta1_architecture.md` | 12 | 1 (A-S9, trigger: the owner's ruling on §11 item 10) | 5 | 2 / 11 / 5 |
| Wire and trust | `delta1_wire_trust.md` | 16 | 0 | 5 | 2 / 7 / 4 |
| Physics | `delta1_physics.md` | 9 | 0 | 10 | 2 / 7 / 3 |
| Determinism and performance | `delta1_determinism_performance.md` | 10 | 0 | 3 | 2 / 9 / 3 |
| Bio-faithful | `delta1_bio_faithful.md` | 11 | 0 | 3 | 2 / 5 / 4 |

Three of the round-1 fixes rested on advice the round-1 readers later retracted (the delta reports name them): the
Maxim fear-set facts and the "config only" route for MP-1 (Bio NB1, NB2), extinction "scaled by setup" (Physics
P2-B2) and the bitwise-equilibrium sleep predicate (DP D1-S2). The author folded them without checking each against
its source.

**The owner's ruling (2026-11-20, "B plus C").** Paper rounds stop here. v2 is recorded as the *direction*. The
build spec is a separate, small design for sub-steps 6.0 and 6.1 (fuel objects and segments, the 1D solid,
occupancy, formats, and the cone tests R0 and R1, which need no flame objects). FDS 6.11.1 (NIST) runs the same
cone cases as a reference implementation beside the MaCFP data. The flame design (6.2 on) is written after R0 and R1
have run. The open findings above carry into whichever of those documents owns them; none is closed by this ruling.
