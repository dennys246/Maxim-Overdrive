# Executor (design review): `docs/design/torch_pilot.md` at fcc6e55

Read-only. I reran `reviews/torch_pilot/numbers.md` with the worktree's `.venv/bin/python`, and wrote scratch only under `/private/tmp/claude-501/exec/`. I also ran `scripts/lint_standards.py`, which printed PASS with 0 findings.

**Claims that check out against the tree:**
- The three red gate names, all strict with `raises=AssertionError`:
  - `tests/test_cross_tier.py:133`
  - `tests/test_act_validation.py:287`
  - `tests/test_act_validation.py:826`
- The graded fluxes: PMMA 50 and 65, pine 25, 50 and 75 (fire_solid §4.5). So 65 is the lower of the two highest, and 25 is both rungs' floor.
- fire_solid §2's `fuel_only_region` refuses every act and reading on an object-only region (Q1 holds).
- fire_solid §7 places q''_fl in `tests/fire/` (Q2 holds).
- The slab segments lie on one face, and a strip flips whole (§1.1, §1.2).
- κ → ∞ recovers surface absorption (§4.1).
- tile §3.2's `pilot_live`, `target: null` and `hold`, and the tick schedule (t − 5, t].
- tile §2.2's pilots row is 10 B.
- sim_core §5.1 already anticipates "a pilot" as an input kind, and sem_stimuli §7.4's default is "not perceivable".
- The contracts.md "restates at 4": boundaries §6.2 shares exactly `actor_id`, `seq` and `apply_tick`.
- On Maxim b98954f7 (local clone), `lookback_primitive.md` says pruning happens at about 44 ticks.
- Every output line of numbers.md reproduces exactly.

## BLOCKER

**E-B1. The rewritten fiercest-fire gate cannot fail.** `docs/design/torch_pilot.md::§9.4` (second bullet).
- **What's wrong:** the rewrite keeps the bar "integrity within 0.1 on every grid". In 6.0–6.1 that bar has nothing to measure.
  - fire_solid §2 refuses every reading on an object-only region (`frames.Frame.reading` "refuses an object-only region, never 0.0").
  - Its table says "objects take no damage (6.2)".
  - If the rewrite instead targets a cell region, §4.4 says a cell target "deposits nothing in Phase 1".
- **Failure scenario:**
  - On the slab, the integrity reading raises `fuel_only_region`, which is not the gate's `AssertionError`, so the strict xfail fails as an error.
  - On a cell target, integrity is exactly 1.0 at every grid on every step, and the test passes whatever the physics does.
  - Either way, nothing it checks can turn it red. This is the loosening-by-rewrite that D-S5 warned about ("today's fiercest-fire gate checks integrity within 0.1 on every turn on every rig").
- **Kind:** contract. The gate's bar is what §1 says this design answers for NS8, D-S5 and A-S2.
- **Proposed fix (unverified):** name an observable that exists on fuel objects in 6.1 (for example the ledger's `contact_to_cells`, or the floor-skin peak), or say that the gate is retired with its Known gap carried, by the owner's ruling.

**E-B2. The ℓ/3 versus 2ℓ/3 overlap control is blind to centre sampling.** `docs/design/torch_pilot.md::§9.4` ("Exact overlap"), `§4.3`, and the checklist's "the ℓ/3 and 2ℓ/3 offsets".
- **What's wrong:** a disc is symmetric about its centre. Moving it by ℓ/3 against the strip lattice is the mirror image of moving it by 2ℓ/3, so any per-strip rule, exact or sampled, gives the same total at both offsets.
- **Failure scenario:** verified with `/private/tmp/claude-501/exec/cs.py`.
  - With centre-inside sampling, r = 0.1 and W = 0.1 give 0.0200000000 m² at offsets 0, ℓ/3 and 2ℓ/3.
  - With midpoint-chord sampling, the ℓ/3 and 2ℓ/3 totals are identical (0.0190241528) in every case I tried.
  - Centre sampling passes the control. Only offset 0 against ℓ/3 differs at all, and even that comparison is blind whenever 2r/ℓ is a whole number (r = 0.1 or 0.2, the exit's likely radii).
- **Kind:** mechanism (a build test), but as written it is a test that cannot fail.
- **Proposed fix (unverified):** compare each offset's total, and each strip's A_ov, against the closed form |disc ∩ face|, and use asymmetric offsets with a non-integer 2r/ℓ.

## SHOULD-FIX

**E-S1. The burned-fuel gate's rewrite is vacuous, and the Known gap it guards has no stated fate.** `§9.4`, first bullet.
- **What's wrong:**
  - The gate guards `World._power_field`'s fallback into air (fire_solid §3.1 names it as that gap's strict gate).
  - `HeatSource` is created only by `ignite` (`src/simcore/core/applier.py:135`). This design creates no source and heats no air cell (§0.1).
  - So a kindle-on-slab test of "peak < WOOD_FLAME_C" (2000 °C) passes without touching the guarded mechanism.
  - "After `t_out` the world gains no heat from the fire" is false as literally stated: the hot slab keeps conducting into the floor skin after flame-out.
- **Failure scenario:** the gate "flips" green while `_power_field`'s fallback and `World.sources` survive as unreachable code with an open Known gap. That is A-S2's "`HeatSource` and `World.sources` have no stated fate", still open.
- **Kind:** contract (a red gate's meaning).
- **Proposed fix (unverified):** state that `ignite`'s retirement removes sources and `_power_field`, closing the gap by deletion, and give the rewrite a bar that can be measured.

**E-S2. The deposit's clock is undefined at the 0.25 s step that §9.2 requires.** `§5`, `§9.2`.
- **What's wrong:** the formula hard-codes 5 ticks per physics step (n_t over (t − 5, t], and the step-mean q''·f·n_t/5). §9.2 then measures the band, and the time check, "at the 0.5 and 0.25 s steps". A 0.25 s step is 2.5 ticks of 0.1 s (tile §6.1).
- **Failure scenario:** the build step cannot write the dt/2 run without inventing either a tick schedule or a substep rule, and the choice changes the deposit's timing.
- **Kind:** contract (the clock).

**E-S3. 346 K is quoted "at the ceiling", but it was computed at 75 kW/m².** `§7` (second bullet), `§4.4`.
- **What's wrong:** the ceiling is 65 kW/m² (§6). I reran the same closed form at 65: a 300 K rise.
- **With re-radiation:** a 1-D implicit check (`conc.py`, ε = 0.9, which is my assumption, M) gives 283 K, or 303 °C. That is 3 K past concrete's `degrade_above_c: 300` (`data/materials/core.yaml`), and only for an arbitrary 60 s, not the item's hold.
- **Cell mean:** §4.4's 21 K is also at 75 kW/m²; at 65 it is 18.5 K.
- **Failure scenario:** a gap entry states a missed degradation with a 17% margin, when the margin is 1%, set by the hold time that §6 leaves open.
- **Kind:** Known-gap numbers (owned here).
- **Also:** fire_solid §4.6 says "65 kW/m² isn't verified" against FDS. The ceiling sits at a graded flux that has not been verified, and the design doesn't say so.

**E-S4. The 84% figure is mislabelled and depends on alignment.** `§6` (exit's footprint row), `§7`, numbers.md. Verified with `alt.py`.
- **The 84% (0.836) is the share of the energy that lands on the slab, not of the footprint's energy.** At W = r, only 60.9% of the disc lands on the slab, so 51% of the footprint's energy reaches fully covered strips.
- **It assumes the disc centre sits on a strip edge.** Centred mid-strip, the share is 0.732.
- **"At most 0.195" and "0.973" are not maxima.** Centred mid-strip they are 0.1987 and 0.9933.
- **Failure scenario:** the W ≤ r_t authoring rule is justified by a number that changes by 10 points with a 1 cm shift of the kindle point.
- **Kind:** derived number.

**E-S5. The "one-flash cap" is not a mechanism in fire_solid §4.4.** `§1`, `§5` ("the one-flash cap are fire_solid §4.4's").
- **What's wrong:** fire_solid §4.4 says "R0 and R1 count flashes per part and require at most one". That is a test assertion in the cone, where the heater never stops. There is no cap that refuses a reflash.
- **Failure scenario:** a part extinguishes while the torch is still on (or lands on it again), climbs back to m''_flash while piloted, and reflashes. The design's §9.1 beats (`t_flash`, the order) never say whether that is allowed or a failure.
- **Kind:** contract (pilot condition).

**E-S6. Two gates have no bar, so they cannot fail or flip.** `§9.2` ("Across grids"), `§7`'s strict red gate.
- **Across grids:**
  - verify_harness §4 says of `agrees`: "the test keeps its own bar on the spread". The design gives none for `t_flash`, `t_char` and `t_out`.
  - fire_model §6.1 and tile §6.3 item 8 give 10–15% for the crate's beats. Those are not carried over, and no source error is derived (CLAUDE.md: bars are derived from a source's error).
- **The §7 red gate** asserts a narrow footprint "flashes at the time" a full-cover slab does. There is no tolerance, so after 6.2's fix exact equality still fails, and the gate never flips. If the narrow case never flashes, `t_flash` is None and the comparison risks a `TypeError`, not `AssertionError`.
- **The in-time check** borrows fire_solid §6's max(0.5 s, 3%), stated for t_ig only, for `t_char` and `t_out` too.
- **Kind:** contract for the exit gate; mechanism for the red gate's form.

**E-S7. The target rule claims integer exactness it can't have, and it reads cells.** `§3`, `§0.3`, `§4.3`.
- **The geometry isn't integers.**
  - fire_solid §1.1 stores "geometry f64 per kind": origin, unit axes, radius.
  - A distance to a rod's lateral surface is |radial| − R, through a sqrt, so it is not a whole number of micrometres.
  - "Computed from `point_mm` × 1000 and the authored integers" and "exact … from the integer geometry" are therefore false. The 1 mm tie then depends on rounding rules the design doesn't state.
- **Cell regions are measured "by its cells' faces".** tile §3.2 measures against the "authored box surface", and fire_solid §1.3 judges "on authored geometry in metres, never on cells". Cell faces move with dx.
- **Failure scenario:** a point 40 mm from a wall's authored face can sit more than 50 mm from its 0.2 m cells' face. The receipt is `applied` at 0.1 m and `not_on_surface` at 0.2 m, so the outcome class differs by grid.
- **Kind:** contract.

**E-S8. The checklist promises a 6.1b save test that cannot be written at 6.1b.** `docs/plans/checklists.md` step 6 ("a save at a mid-pilot tick … bit-identical"), `§2`, `§9.3`.
- **What's wrong:** §2 itself says this is "step 9's save requirement". fire_solid §5.5 says "6.0–6.1 builds no save … Until then, §6 tests that the digest after a rebuild from the tables equals the running digest."
- **Failure scenario:** 6.1b's checklist item has no save format to round-trip. It gets skipped or stubbed, and the pilot record's save requirement has no test until step 9.
- **Kind:** mechanism (checklist).

**E-S9. "Thickness > 1 mm" is guarded by no file and no check.** `§3` ("which every `slab` recipe's geometry range does (fire_solid §5.1)").
- **What's wrong:** no recipe file exists (`data/` has only materials, rigs and world, and there is no `content/`). fire_solid §5.1 says only that recipes have "geometry ranges", with no lower bound tied to the tie band.
- **Failure scenario:** a future slab recipe 1 mm thick or thinner (a card sheet). Every kindle on its top face ties with the floor and is refused as `ambiguous_point`.
- **Kind:** contract (a loader refusal is needed, or the claim goes).

**E-S10. "Flash needs the pilot" cannot be set up on the shipped path.** `§9.4`, first row.
- **What's wrong:** by §5, a part is piloted exactly when the torch deposits on it (n_t ≥ 1 and A_ov > 0). "Flux on, pilot condition off" therefore needs a test-only knob that splits flux from pilot.
- **The cell is also ambiguous:** it lists "no flash, nonzero unpiloted count", which describes the passing state, not what the deletion turns red.
- **Unconsidered path:** §5 says "only the torch can raise a strip that far", but thermal lag after `end_tick` can carry a strip across m''_flash while it is unpiloted. That path is real, and the controls don't name it.
- **Kind:** mechanism.

## NIT

**E-N1. The citation of fire_model §10.1 says the opposite of what NN5 says.** `§3`: "the stale T4 rule that fire_model §10.1 revised (NN5)". NN5 (`delta1_executor.md:206`) says that §10.1's T4 row lists "only the deposit and the radius", and the current §10.1 row confirms it: "kindle's deposit and 0.2 m radius". §10.1 did not revise the target rule.

**E-N2. A dx claim is attributed to the wrong section.** `§9.2`: "the only place dx enters (fire_model §6.1)". fire_model §6.1 lists three dx paths and says nothing about uniqueness. The claim is fire_solid §3.2's, which names contact rows, the skin's far boundary and the straddle test.

**E-N3. The heater is not uniform-only.** `§1` says the cone heater "is uniform". fire_solid §6 already has a non-uniform-heater test, a linear 25 → 50 kW/m² heater averaged per segment, which is the length-direction analogue of the torch.

**E-N4. numbers.md promises a check it doesn't contain.** Its docstring says "closed form check", but the script has none; it uses trapezoid quadrature only.

**E-N5. The wire row is restated incompletely.** `§2`: "The wire's pilots row stays tile §2.2's (`actor_id`, `region_id`, `end_tick`)". tile §3.1 says each pilots row also carries `cause`. Separately, the record's `end_tick` is u64 against the wire's u32, with no stated narrowing.

**E-N6. The design edits other owners' rules without listing them in §10.**
- "Convective loss off over the covered share" changes fire_solid §3.1's ambient rule, and §4.4's convective-off rule covers only the cone flame.
- fire_solid §2's table row "`kindle`'s target … 6.4" becomes stale under 6.1b.

**E-N7. The char beat borrows a number for a different quantity.** §9.1's char beat uses tile §6.3 item 3's 10%, which is "≥ 10% of their fuel charred". The design applies it to fire_solid §5.6's residue ÷ remaining solid mass. It is tagged [engineering], but labelled as tile's number.

Count: 2 BLOCKER, 10 SHOULD-FIX, 7 NIT.
