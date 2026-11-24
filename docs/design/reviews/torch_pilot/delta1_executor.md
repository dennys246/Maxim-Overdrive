# Executor, delta round 2: `docs/design/torch_pilot.md` (working tree over fcc6e55)

I worked read-only. I reran numbers.md's script with the worktree's `.venv/bin/python -I`, using a scratch copy under `/private/tmp/claude-501/e2/`. Every printed line reproduces. I also ran `scripts/lint_standards.py`: PASS, 0 findings.

## 1. Status of round 1's Executor findings (read from the tree)

| Id | Status | Evidence |
|---|---|---|
| E-B1 | fixed | §9.4: "None of the three `ignite` red gates is rewritten". Each gate stays strict until its mechanism is deleted (Q6). §0.6 agrees. |
| E-B2 | fixed | §9.4's "Exact overlap" row: per-strip A_ov against quadrature at offsets 0.13ℓ and 0.71ℓ, with r = 0.051 m (2r/ℓ not whole). The checklist says "asymmetric offsets". |
| E-S1 | fixed | §9.4 names `_power_field`, `HeatSource` and `sources`, and says each goes only with its deletion, under Q6. The old vacuous rewrite is gone. Beat 8's replacement has a wrong deletion proof (E2-S2). |
| E-S2 | fixed | §5: E_p,t is written in `tick_us` and `physics_every`, holds are in seconds, and the time study halves `tick_us`. This checks against `SimConfig`, where `physics_seconds` = physics_every·tick_us. §9.2 still has a problem with the steps it names (E2-S1). |
| E-S3 | fixed | §7: 45 kW/m² for 60 s gives about 190 K with losses (numbers: 187 K, reading about 3% low) and 208 K lossless; the cell mean is 12.8 K. The ceiling is now based on 50 kW/m², the FDS-verified flux. One residual error: E2-N2. |
| E-S4 | fixed | §6 and §7: 84% is gone, and the ranges are taken over 40 offsets (0.973–0.993, 0.195–0.199, 0.662–0.666, all reproduced). One residual caveat: E2-N3. |
| E-S5 | fixed | §5: "A part that goes out may flash again only when piloted". Beat 3 asserts at most one flash per part in the exit. |
| E-S6 | fixed | §9.2 "Across grids" is max(e_dt, one physics step). §7's gate uses that bar, and a never-flash case is an assertion. The borrowed max(0.5 s, 3%) is gone. Its replacement has new defects (E2-S1). |
| E-S7 | fixed | §3: f64 distances in metres, no integer claim; cell regions by their authored footprint (`sim_core.md` §7). |
| E-S8 | fixed | §2: the save is step 9's, and 6.1b uses the digest rebuild. The checklist's step 9 row was added, and step 6's save item removed. |
| E-S9 | fixed (contract) | §3 and §10: the catalogue refuses slab recipes ≤ 2 mm, as an edit to fire_solid §5.1. The 6.1b checklist names no test for that refusal (E2-S4). |
| E-S10 | deferred to 6.1b (reviewer) | §5 and §9.4 now name the lag path and drop the test knob. The control still exists only if a lag crossing exists, and nothing shows one does (E2-S3). Trigger: 6.1b's first measurement of the unpiloted-crossing count. |
| E-N1 | fixed | §3 no longer cites NN5 or §10.1; this document owns the rule. |
| E-N2 | fixed | §9.2 cites `fire_solid.md` §3.2. Line 199 lies inside §3.2 (lines 184–202). |
| E-N3 | fixed | §1 cites fire_solid §6's non-uniform heater. |
| E-N4 | fixed | numbers.md now checks the closed form against quadrature: worst strip 1.55e-10 m², reproduced. |
| E-N5 | fixed (pending Q5) | Q5 adds `seq`, and `end_tick` narrows to u32 by refusal. §10 adds the tile §2.2 row. |
| E-N6 | fixed | §4.2: losses stay on before flash, so fire_solid §3.1 is untouched. §10 lists fire_solid §2. |
| E-N7 | fixed | §9.1 beat 4: the 0.1 is `[engineering]` alone. |

## 2. New findings in the fold

### SHOULD-FIX

**E2-S1. §9.2's in-time gate names two steps, needs three, and can fail on a correct scheme.** `torch_pilot.md::§9.2` ("In time").
- **The runs don't match the check.** The text runs "`tick_us` and `tick_us`/2 (the 0.5 and 0.25 s steps)", then asserts |t(dt/2) − t(dt/4)| ≤ |t(dt) − t(dt/2)|. That needs a dt/4 (0.125 s) run that the design never lists. fire_solid §6 runs dt, dt/2 and dt/4, and §4.3 says so.
- **The beats are quantized.** `t_flash`, `t_char` and `t_out` are each "the first physics step" at which something happens, so each is rounded up to its step.
- **Failure scenario:** take a true flash at 10.30 s with a first-order error of 0.2·dt (worked by hand).
  - The three steps give 10.5, 10.5 and 10.375 s.
  - Then |t(dt) − t(dt/2)| = 0 and |t(dt/2) − t(dt/4)| = 0.125 s, so the gate fails on a scheme that converges.
  - e_dt = 0 then also collapses the across-grid bar to "one physics step".
  - The checklist dropped round 1's "three grids and two steps" item, so nothing at 6.1b names these runs at all (E2-S4).
- **Kind:** contract for the list of runs, which e_dt and the §7 red gate depend on. Mechanism for the quantization: 6.1b should carry a test that interpolates each beat's crossing within its step, or that compares within a one-step allowance.
- **Fix (unverified):** list dt/4, and define each beat's time by interpolating its threshold crossing.

**E2-S2. Beat 8's deletion proof names the wrong deletion.** `torch_pilot.md::§9.1` beat 8, and the "Out stays out" row of §9.4.
- **What's wrong:**
  - Beat 6 defines `t_out` as the first step with no flaming part.
  - If extinction is deleted, no part ever goes out, so `t_out` never occurs before the cap and beat 6 fails.
  - Beat 8 ("from `t_out` to the cap") then has no interval to check, so it is vacuous or undefined. It is not what turns red.
- **What beat 8 actually guards:** a reflash or a flame flux after `t_out`. That is the analogue of the burned-fuel gate (a fire still heating after its fuel is spent). Its deletion would be the pilot condition, or a flame flux that isn't gated on flaming.
- **Failure scenario:** the claim "this carries the burned-fuel gate's meaning onto fuel objects" is "proved" by a deletion that reddens a different beat. A flame flux leaking from an extinguished part is never shown to turn beat 8 red.
- **Kind:** mechanism. 6.1b should carry the test: a deletion that keeps `t_out` defined and makes q''_fl apply to a part that is not flaming, and beat 8 must then go red.

**E2-S3. The "flash needs the pilot" control depends on a phenomenon nobody has shown.** `§9.4` first row, `§5` ("which the solid's lag can produce").
- **What's wrong:**
  - On the shipped path, piloted ⇔ deposited (§5).
  - So deleting the pilot condition changes behaviour only if some part crosses m''_flash after the pilot's last covered step.
  - Whether the in-depth Arrhenius m'' keeps rising after the surface flux stops depends on the material and the hold. No number in numbers.md or fire_solid shows that it does.
- **Failure scenario:** the unpiloted-crossing count is 0 for every hold. The control cannot be built, and the pilot condition has no deletion proof on the shipped path.
- **Kind:** mechanism. 6.1b should carry it: measure the count over holds first. If it is zero everywhere, the design must say the pilot condition cannot be tested on the shipped path and add a lab-only split of pilot from flux, reported as such.

**E2-S4. The 6.1b checklist dropped work the design says 6.1b does.** `docs/plans/checklists.md` step 6 ("Added by D-B2").
- **Missing items:**
  - §9.2's band, margin, in-time and across-grid study. §9.2 says "values at 6.1b", and round 1's checklist had "the band in D at three grids and two steps"; it is gone.
  - §9.3's bit-identical stepped, unpaced and replay runs.
  - The cell-target, no-deposit, nothing-heats-air case (in round 1's list, now gone).
  - The ≤ 2 mm slab-recipe refusal (§3, §10).
  - The two delays that lesson 35 and §12 say are "measured separately at 6.1b".
  - §6's "measured at 6.1b" NPC-hold margins.
- **Also:** step 8's checklist does not map G1–G5 onto §9's beats, which §10 says it does.
- **Failure scenario:** the build follows the checklist (CLAUDE.md: "a mechanism … goes to its build step's checklist"). It ships the exit with no measured band, so D and the cap are unset and §7's red gate has no bar.
- **Kind:** mechanism (checklist), carried by 6.1b and step 8.

**E2-S5. Beat 7 contradicts beat 3 when `end_tick` is not a physics tick.** `§9.1` beats 3 and 7, `§5`.
- **What's wrong:**
  - A physics step ending at tick t covers (t − `physics_every`, t].
  - With `end_tick` = 12, the step at t = 15 has n_t = 1 (tick 11), so it is piloted and a flash there is legal under beat 3.
  - Beat 7 then requires `t_flash` < `end_tick`, and 15 < 12 is false.
- **Failure scenario:** the checklist's own "`end_tick` on and off a physics tick" case, or any NPC hold that isn't a multiple of 0.5 s, turns beat 7 red on correct physics. This is likeliest in the band case, which the pilot control uses.
- **Kind:** contract. The beats are owned here, and step 8 maps G1–G5 onto them.
- **Fix (unverified):** state beat 7 as `t_flash` ≤ the last covered physics step.

**E2-S6. The pilot record's `target` reuses an intent-record field name with a different type and meaning.** `§2` table, `docs/design/contracts.md` (the pilot.fields note).
- **What's wrong:**
  - boundaries §6.2's `target` is "a stable id (a region name or persisted entity id), resolved at the door".
  - §3 says `kindle` logs `target: null`.
  - The pilot record's `target` is a u8 kind (0 fuel object, 1 cell region).
  - contracts.md justifies raising the restate count to 4 by saying the record "shares" `target` because it "records its target". It doesn't: same name, different contract.
- **Failure scenario:**
  - A replay or save reader that joins the intent and pilot records by field name reads `null` against `0`.
  - The registry's count was raised on a false premise, which weakens B36's copy detection for `pilot.fields`.
- **Kind:** contract.
- **Fix (unverified):** rename the field (for example `target_kind`) and restore the count.

**E2-S7. Q6's text tells the owner that structural fire's cross-rig claim "passes to §9.2". §9.2 tests no structure.** `§11` Q6.
- **What's wrong:** §9.2 measures fuel-object beats only, and §7 says the torch heats no structural cell.
- **Failure scenario:** the owner rules Q6 believing the Phase 0 cross-rig fire claim is still verified. In fact it is retired for structure until 6.2's skins (D-S3), with no gate.
- **Kind:** contract (a roadmap exit claim).
- **Fix (unverified):** say that the claim is retired for structure, carried as a Known gap with a 6.2 trigger, and replaced for fuel by §9.2.

### NIT

**E2-N1. A dangling section reference.** `§10`'s `sem_stimuli.md` row cites "§4.1's and §4.4's `applied`-with-no-deposit cases". The folded design has no §4.4; §4 ends at §4.3. Mechanism: the T11 sweep at 6.1b.

**E2-N2. The 300 °C onset time is the lossless figure.** `§7`: "reaches concrete's 300 °C onset only past about 110 s".
- 110 s is the closed form's lossless time: 208·√(110/60) ≈ 282 K.
- With losses, my rerun of numbers.md's march gives 225 K at 90 s, 246 K at 110 s, 264 K at 130 s and 280 K at 150 s, so onset is about 145–150 s even after the march's ≈3% low bias.
- "Only past" is true as a lower bound, but it sits in a sentence about the with-loss value and understates the margin by about 35%. This is a Known-gap number.

**E2-N3. The "disc lies on the slab" claim assumes a centred point.** `§6` (footprint row) and `§7` ("none at r = W/2").
- numbers.md places the disc on the slab's centreline, but `centre_m` is wherever the player's point lands.
- Off-centre across the width, r = W/2 overhangs the slab, and the "none lost" and 0.973 floor no longer hold.
- The exit script must state a centred point. Mechanism: step 8's script, and a 6.1b off-centre case.

**E2-N4. The flux floor and ceiling convert differently.** `§6`.
- The ceiling converts the cone's graded flux to the torch's by ε (50 → 45 kW/m²). The floor does not: "below 25 kW/m²" against an absorbed equivalent of 22.5.
- So Q3(b)'s range "25 kW/m² to §6's ceiling" excludes torch fluxes from 22.5 to 25 kW/m², which lie inside the graded range.
- Kind: contract (Q3's bounds).

**E2-N5. Two §9.4 rows don't name a deletion that turns them red.**
- **"Segment independence":** halving the strips is a refinement, not a deletion.
- **Its 25/50/75% area times are quantized by whole-strip flash.** About 5 strips (20% each) at ℓ against 10 (10% each) at ℓ/2. So "time to 25%" is a different strip's flash in the two runs.
- **"Only the segmented face takes it":** whether "ignore `face`" reddens the test depends on how it is deleted. A side-face disc is vertical, and its true intersection with horizontal strip rectangles has zero area.
- Mechanism, for 6.1b: interpolate the area times, and specify the deletion as "project the disc into the segmented face's plane".

## Counts

**Statuses (19):**

| Status | Count | Ids |
|---|---|---|
| fixed | 18 | 2 BLOCKER; 9 SHOULD-FIX, E-S9 among them, whose fix is in the contract but has no checklist test; all 7 NIT |
| deferred | 1 | E-S10, to 6.1b |
| rejected | 0 | |
| open | 0 | |

**New findings (12):** 0 BLOCKER, 7 SHOULD-FIX, 5 NIT.

| Kind | Count | Ids |
|---|---|---|
| Contract | 6 | E2-S5, E2-S6, E2-S7, E2-N2, E2-N4, and E2-S1's list of runs |
| Mechanism | 7 | E2-S2, E2-S3, E2-S4, E2-N1, E2-N3, E2-N5, and E2-S1's quantization |

E2-S1 has a contract half and a mechanism half, so the two kinds sum to 13.

**What carries the mechanism findings:**
- **6.1b:** E2-S1's interpolation, E2-S2, E2-S3, E2-S4, E2-N1, E2-N3's off-centre case and E2-N5.
- **Step 8:** E2-S4's G1–G5 mapping and E2-N3's script.

No new contract blocker. E2-S5 and E2-S6 are the contract items that should fold before code.
