## Status check: round 2 of the torch-pilot review (Executor, Physics, Architecture, Determinism, Bio), read from the tree at 94e85fe

I worked read-only. Two things went into scratch at /private/tmp/claude-501/x3/: a rerun of numbers.md's march, and nothing else. I checked Maxim at b98954f7 with `git show` only.

**One correction to fold2.md:** its E2-S6 row says contracts.md's count is "back to 4". The tree has 6. TP5 raised it after the fold, and the stated rationale (tile §2.2's pilots row shares five names) is consistent with the count. The tree is right and fold2 is stale.

### Numbers rerun
- **Onset time:** numbers.md's march at 45 kW/m², scaled ×300/290 plus 20 °C, gives 284 °C at 120 s, 302 at 140 s and 310 at 150 s. So "about 140 s" holds (crossing at about 138 s).
- **Other figures:** 190/187/208 K, 12.8 K, 2.7%, 22% and 39%, 14.3 kW/m², and 30 B for TP5's row all check against numbers.md's printed output and the dtypes.

### Status table

| Id | Status | Evidence |
|---|---|---|
| E2-S1 | fixed | §9.2 "In time" runs `tick_us`, ½ and ¼. §5's last bullet interpolates each beat within its step. Checklist 6.1b says "three grids and three steps … interpolated beat times". |
| E2-S2 | deferred (6.1b) | §9.4's "Out stays out" deletion is now "apply q''_fl to a part that isn't flaming". The checklist carries it ("beat 8's by a flame flux on a part that isn't flaming"). |
| E2-S3 | deferred (6.1b) | Checklist: "the unpiloted-crossing count over holds, measured first. If it is zero … the design says so". |
| E2-S4 | fixed | Checklist 6.1b restores §9.2's measurements, §9.3's bit-identical runs, the cell-target no-deposit case, the ≤ 2 mm refusal and the two delays. Step 8 maps G1–G5 to the beats. The NPC holds moved to Phase 4 (§6 row). |
| E2-S5 | fixed | §9.1 beat 7: "`t_flash` falls no later than the pilot's last covered physics step". |
| E2-S6 | fixed | §2 uses `target_kind`, and the marker matches. contracts.md is 6 with a true rationale (see the correction above). |
| E2-S7 | fixed | §9.4 and TP6: fire on structure leaves Phase 1. The roadmap's Phase 0 line is qualified. §7 gives the 6.2 skins as the fix. |
| E2-N1 | fixed | §10's sem_stimuli row: "off-face and cell-target … cases (§4.1)". |
| E2-N2 | fixed | §7: "after about 140 s". Reproduced. |
| E2-N3 | fixed | §6: "a disc centred on the slab's centreline", and the plank is "kindled at its centre". No off-centre 6.1b case was carried, but that is advisory. |
| E2-N4 | fixed | §6: "below ε_r · 25 kW/m² … converted as the ceiling is". |
| E2-N5 | fixed | §9.4 rows: "a refinement, not a deletion", interpolated area times, and "project the disc … more than 1 mm below its top edge". The checklist carries both. |
| P2-S1 | fixed | §3: cell regions "by its authored solid primitives … never … `footprint_of`'s bounding box". `not_on_surface` applies only when no candidate is within 50 mm. world_model §5 is cited. A new defect from this text is X3-3. |
| P2-S2 | fixed | §9.2: s_floor is the contact closed form's verified 3% (fire_solid §6 table: "within 3% of 39·ΔT"), carried to each beat. §7's red gate uses it. |
| P2-S3 | fixed | §6: "FDS-verified for PMMA … pine is graded only". §7 adds the PMMA surface-absorption gap with −6.2% and +42 s. |
| P2-S4 | fixed | §6 defines ε_r as the least fixed ε, with fitted char ε excluded. The charred-surface case is a §7 gap. |
| P2-S5 | fixed | §9.2 Margin: max(spread, one quantum). |
| P2-S6 | **open** | The runs and the interpolation are fixed. The bar's form is not: "|t(dt/2) − t(dt/4)| ≤ |t(dt) − t(dt/2)|. That checks convergence" still passes a stall with equal non-zero differences, so the claim it states is false at equality. This is the contract half P2-S6 named. |
| P2-S7 | fixed | Beat 3: "Reflashes are counted and reported". |
| P2-S8 | fixed | §7: "Torch and flame fluxes add after flash … bounded by q''_t · A_ov over [`t_flash`, `end_tick`)". |
| P2-S9 | fixed | Checklist 6.1b restores the band, margin, e_dt and s_floor measurements, and the ceiling-formula test. |
| P2-N1 | fixed | Same text as E2-N2. |
| P2-N2 | fixed | §6's last bullet puts the item's values first, then D and the cap from the band runs. |
| P2-N3 | fixed | §7: "187 K by a march that reads 3% low". |
| A-B1 | fixed | Through A2-B1 below. |
| A2-B1 | fixed | §9.4 names all four gates, the crate gate among them. At 5b the precondition moves to the sphere `kindle`, and at 6.1b the gates close by deletion (TP6). Checklist 5b carries the move. §2 no longer anchors on `sources` or `source_exposure` ("a position sim_core's edit assigns"). A new defect from TP6 is X3-2. |
| A2-S1 | **open** | Fixed: tile §3.2's red-gate sentence, lifecycle and `max_power_w`; the roadmap's "must flip" line 43; the Phase 0 claim; checklist 5b. Still stale: roadmap line 36, "Needed before the Phase 1 exit (the slab) is gated … well enough at the coarsest rig to pass the gate", while line 44 says that gate closes by deletion. |
| A2-S2 | fixed (this tree) | fire_solid §2: "every act but `kindle` (TP1)". The candidate rule defers to the sub-cell design's states, and §2's cut is `leave`-only, so the meaning of "gone" no longer matters. TP1 says the sub-cell session was told, which I can't verify. The S0 overwrite risk lives on that branch. |
| A2-N1 | fixed | Moot: §2 says only `leave` cuts a pilot. |
| A2-N2 | **open** | fold2 lists it as deferred to 6.1b, but the 6.1b checklist has no layer-import test for `fuel_geometry` and no cross-act ranking case. A deferral with no carrier isn't one. |
| A2-N3 | deferred (6.1b) | §10's roadmap row: at 6.1b, "Phase 2 lists … the strip-width red gate". TP4's owner section is §7. Trigger: 6.1b's roadmap edit. fold2 omits A2-N3 entirely. |
| D-B1 | fixed | §2 "Cut short only on `leave` … Nothing else ends a pilot early". The cell-target `region_gone` cut is gone. This also covers D2-S5, its residue, which is not counted twice. |
| D-N1 | fixed | §2: "a recorded break under `sim_core.md` §12". The §10 sim_core row agrees. |
| D2-B1 | fixed | §5: the solid refines by `tick_us` alone. The script is in seconds and its loader converts to ticks. Runs start in reach. §9.1 states the departure from tile §6.2. D's quantum is a coarsest tick, so the conversion is exact at ½ and ¼. |
| D2-S1 | fixed | §2 "Removed … or at the cut itself when every covered tick has already been integrated". I traced L = 121, 122 and 123 (apply 70) and each is removed. The checklist has L ≡ 1 (mod `physics_every`). |
| D2-S2 | fixed | §2: "An empty member still hashes … a recorded break". sim_core §9 gains member 6. |
| D2-S3 | fixed | §3: "less than 1 mm farther than the nearest" in both places. `centre_m` is "the nearest point on the resolved face". |
| D2-S4 | deferred (6.1b) | Checklist: "its cache keyed with the object's geometry, or geometry held immutable while referenced (D2-S4)". |
| D2-N1 | fixed | One phrasing (D2-S3). |
| D2-N2 | **open** | Step 9's row is unchanged ("load refusals, a round trip at a mid-pilot tick, and a golden"). Neither phase case is named: a save between `end_tick` and removal, or a save at the cut. fold2 says "to 6.1b", but the 6.1b list has no save phases either. |
| B2-S1 | fixed | Roadmap OD-A16 row: the lesson 35 and §12 evidence, the draft's "Slow effects" paragraph to be revised before upstream, and "6.1b records the two delays". Checklist 6.1b records both, with "none" in Phase 1. |
| B2-N1 | fixed | §12 and lesson 35 name both paths. Verified at b98954f7: `nac.py:3707` `decay_eligibility(factor=0.9)`, prune `< 0.01` (3721), `max_reward_bias = 0.20` (473), `temporal_window_seconds = 300.0` (439), `now = time.time()` (3715). `lookback_primitive.md:27-35`: 0.3 on completion, credited through `credit_node`. `tool_failure_credit.md:77-80` and `roadmap_1_4.md:69-71`'s quote ("credits the NEXT call") are exact, and so is the draft quote (line 55). |
| B2-N2 | fixed | §6 row: "outside every shipped recipe's flash band under this item's flux and radius, measured when the holds are set; `torch.yaml` gains them then, with a version bump". The measurement goes to Phase 4's body design. |

### New contract findings from the fold or the rulings (X3-)

**X3-1 (Architecture), SHOULD-FIX. The interim `kindle` from 5b to 6.1b has no buildable target rule or refusal rule.**
- **Locations:** tile §3.2 ("Stage 2 derives the target by `torch_pilot.md` §3's rule"); fire_solid §2 ("refused by every act but `kindle` (TP1)" in 6.0–6.1); torch §10 placement.
- **The defect:** the fold deleted 5b's own rule (box surface within 50 mm, no deeper than 50 mm). Nothing in tile §3.2 limits §3's rule to 6.1b, yet §3 is built at 6.1b in `core/fuel_geometry.py`, with fuel-object candidates. The four red gates now depend on 5b's sphere `kindle` (TP6), so its target rule is load-bearing.
- **Failure scenarios:**
  - The 5b builder implements §3 early, somewhere else. 6.1b then has two queries, which breaks §3's "one query".
  - Or 5b and 6.0–6.1 merge before 6.1b. A sphere `kindle` on an object-only region is then accepted (TP1's exception is unconditional), and it deposits into the air cells around the fuel. That is the behaviour the burned-fuel gate exists to catch.
- **Fix (unverified):** state 5b's rule for cell regions and its module, and make TP1's exception take effect at 6.1b.

**X3-2 (Architecture and Determinism), SHOULD-FIX. TP6's 6.1b deletions are not routed to the documents that own those inputs.**
- **Locations:** §9.4 and §10 against sim_core §1 (table, line 29), §3 (`source_exposure`, line 64), §6 (inputs, line 168) and §9 (digest members 2 and 3), and boundaries:220 and :523 (`sources` as an applier-written input, including `douse`).
- **The defect:** §9.4 deletes `HeatSource`, `sources` and `_power_field` at 6.1b. §10 routes no sim_core edit removing `sources` or `source_exposure`, and records a digest break for the pilots member only. `source_exposure`'s fate isn't stated at all.
- **Failure scenario:** one builder keeps members 2 and 3 as empty members, so the digest is unchanged by them. Another drops them, which is a second, unrecorded break. Both comply, and their digests differ.

**X3-3 (Physics), SHOULD-FIX. Measuring a cell region by its authored primitives ignores what has happened to the region since.**
- **Location:** §3, which says a cell region is "never measured by its cells". The fold introduced this through P2-S1.
- **The defect:** a region destroyed by a strike, or cratered, stays a full-size candidate. §3 never says when `region_gone` (tile §3.4, stage 2) applies to `kindle`.
- **Failure scenario:** a wall is destroyed and its cells are now air. A `kindle` at its former face returns `applied` with a cell target. From 5b to 6.1b the sphere then heats air. From 6.1b the receipt is `applied` on nothing, where `region_gone` was the right answer.

**X3-4 (Architecture), SHOULD-FIX. Phase 2 documents still rely on gates that TP6 deletes.**
- **Locations:** tile §6.4's last control row ("`test_a_fire_that_has_burned_its_fuel_stops_heating` flips green; its gate is removed") and roadmap Phase 2, line 74 ("Close the known gap: the coarsest rig's late-burn lag"). That known gap is the crate gate's, and TP6 closes it by deletion at 6.1b.
- **Failure scenario:** the Phase 2 crate builder's deletion-proof control names a gate that no longer exists. The crate's burned-fuel property then ships with no control that a deletion turns red.

**X3-5 (Executor), NIT. Four small defects:**
- §10's roadmap row still says "under Q2", which is dangling now that the questions are ruled. It means TP2.
- §7's "r = 0.05 m on a 0.5 m plank" means 0.5 m wide, but next to TP7's 0.6 m-long plank it reads as a length.
- fire_solid §2 cites "(TP1)" but doesn't link torch §3, which TP1's own text requires.
- fold2's "count back to 4" (see the correction at the top).

**Noted, not counted:** fire_solid §2's consumer table still says "empty tables add no bytes". That contradicts sim_core §9's framing, the same error D2-S2 fixed in torch §2. It predates the fold.

### Counts
- **Statuses (43 findings):** 35 fixed, 4 deferred (E2-S2, E2-S3 and D2-S4 to 6.1b; A2-N3 to 6.1b's roadmap edit), 0 rejected, 4 open (P2-S6, A2-S1, A2-N2, D2-N2).
  - By lens: Executor 10 fixed and 2 deferred; Physics 11 fixed and 1 open; Architecture 4 fixed, 1 deferred and 2 open; Determinism 7 fixed, 1 deferred and 1 open; Bio 3 fixed.
  - The open items are all small, but they are open. The paper rounds are stopped, so a reviewer would have to re-read them after a fold.
- **New findings:** 0 BLOCKER, 4 SHOULD-FIX (X3-1 to X3-4), 1 NIT (X3-5, four items).
- **Where to fold:** X3-1 and X3-2 are contract defects introduced by TP6 and the fold, and should fold on this branch before merge. X3-3 should fold too, or go to the owner.
