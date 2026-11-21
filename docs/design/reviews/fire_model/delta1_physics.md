# Fire model v2, delta round 1: Physics and resolution

Lens: Physics and resolution. Read on disk: v2 (staged), v1 at 08310d1, `fold.md`, round one, `world_model.md` §0/§2,
`tile_and_client.md` §5.2, `heat.py`, `core.yaml`, `fire_ladder/7`. Tags: **V** primary source read by me, **S** secondhand, **M** memory, **D**
derived. Web searches for cold thick-PMMA downward spread rates and for LIFT's PMMA Φ found no primary value, so both
numbers below are **M**.

**A correction to round one first.** Round one's S1 fix said "m''_cr scaled by setup". v2 adopted that wording
(§4.3, "cited per setup"), and it is wrong: it turns extinction into a free per-scene parameter, so R4's check can't
fail (P2-B2 below). The error was round one's, not the author's.

**Statuses: 9 fixed, 10 open, 0 deferred, 0 rejected. New findings: 2 BLOCKER, 7 SHOULD-FIX, 3 NIT.**

## 1. Status of the round-one findings

| Finding | Status | Reading of the tree |
|---|---|---|
| B1 patch mean thresholds ignition | **open** | Cell keying is gone. §2.1 sizes segments in metres, each with ignited and unignited parts and a front. Two things the fix needed are still missing. (a) The concurrent front law has no formula and no citation: §3.2 says only "the flame's footprint". (b) Flash is still decided on the unignited part's area-mean profile, and §3.2 doesn't say how a front crosses into the next segment. So spread can still jump by one segment length (P2-S3). |
| B2 representation depends on dx | **fixed** | §2.1: any number of objects per cell, and representation is authored. Rods are discrete at every spacing. |
| B3 flame energy booked more than once | **fixed** | §4.2 writes one partition. A segment inside a flame gets contact flux only. A burning segment's own flame flux *is* the contact flux. §6.2 adds a closed-shell ledger test. The partition has no positivity rule, and its gas term has no sink. Those are new defects in the fix (P2-B1, P2-S1), not B3 reopened. |
| B4 three R2 criteria can't fail | **open** | The flame-height and wall-flux criteria are gone. R2b grades front position, and R2a has a law (de Ris). Neither dataset is named, though, and R2a can still be tautological: Φ's source isn't required to differ from the graded dataset (P2-S4). R2b's 10–30 kW/m² wall flux is a knob nobody pre-registers. |
| S1 per-patch extinction against R4 | **fixed** | §4.3 decides extinction per flame, and R4 adds "not flamed out at ~2.5 g/m²s". The per-setup value that replaced it is P2-B2. |
| S2 one m''_cr | **open** | §3.2 adds flash at the data's own t_ig definition, so R0's event is now named. The "hysteresis" runs the wrong way, though: flash at 1.0–1.6 g/m²s, lone-surface extinction at 2.7–8.3. A flicker loop at flash is still possible (P2-B2(b)). |
| S3 R1 band and pine curves | **fixed** | §6.2 R1 grades sustain at 25 kW/m² (~3.8 g/m²s) and no sustained flaming with the heater off. That is the fix asked for. |
| S4 fit and grade on the same data | **open** | R0 is split: fit at 30/60, grade at 25/50/75, and PMMA 25 ↔ 65. R1 says only "on held-out fluxes" without naming a split. R4's species transfer is unstated (P2-S7). |
| S5 in-bed radiation, draught, O₂ | **open** | §3.3 adds segment-to-segment radiation. Fixed for radiation, but §3.1's surface balance still radiates to a single T_env, the overlapped cell's air temperature, and nothing states the view-factor complement (P2-S6). O₂ and the draught are named with a number (~1.8×) and a pre-check before R4. They aren't in `architecture.md` Known gaps yet. |
| S6 O₂ regime | **open** | The R4 trigger is acceptable: compute φ from the real layout before pre-registration. The cardboard-packed exit crate, denser still, has no trigger. "An O₂ supply term per bed volume" has no source. |
| S7 char oxidation under flame | **fixed** | §2.3 turns it off under flame cover. §6.2 R4 grades residue at 48 min and an ember tail of at least 18 min. |
| S8 correlations outside range | **open** | The wall correlation's range is stated and runs outside it are flagged as extrapolation. §4.2 names h(d, u) for thin elements. But h, u and T_f have no source or value. The wall 10–30 kW/m² has no conv/rad split. Horizontal upward faces (the R0/R1 sample, crib stick tops) have no contact law. "Blending by aspect" is not written as a function (P2-S2). |
| S9 clustering | **open** | §4.1 has a smooth merge band, pre-registered and uncited, and R3a's gap sweep gates it between grids. The band still decides R3a's graded class, and a smooth weight contradicts discrete min-key clusters (P2-S5, P2-B2(c)). |
| S10 pilot rule | **fixed** | §3.2: a pilot is required, and unpiloted ignition is refused and recorded as a gap. The "cited distance" isn't cited yet (P2-N1). |
| N1 where (1 − χ_r)Q goes | **fixed** | §4.2 picks the cells, by overlap. The physics of that choice is broken (P2-B1). |
| N2 χ_r unspecified | **open** | "Still to cite", with no trigger. It must be cited before R2.5, which absorbs χ_r·Q. |
| N3 R4 pilot | **fixed** | §6.2 R4 prescribes Q from Test 13's early curve. |
| N4 R2.5 is verification | **fixed** | §6.2 counts R2.5 as a unit test. |
| N5 moisture | **open** | §6.1 pins moisture per rung and says its effect on t_ig is graded at R0. No dataset varies moisture (MaCFP-4 conditions to one), so that grade has nothing to grade against. Name one, or drop the grade and record the gap. |

Fixed: B2, B3, S1, S3, S7, S10, N1, N3, N4. Open: B1, B4, S2, S4, S5, S6, S8, S9, N2, N5.

## 2. New findings on v2

### P2-B1 (BLOCKER). Q_gas has no sink in Phase 1 and comes back to the fuel through the cells, so the outcome depends on dx
`fire_model.md::§4.2` "Gas"; `§2.2` coupling; `§3.1` surface balance

§4.2 deposits Q_gas = (1 − χ_r)·Q − Q_contact,conv into "the overlapped cells' gas by overlap". It says this reaches
the outside reservoir "through those cells' open-air loss (6a)". That path doesn't exist:
- Law 6a is a loss from a solid's exposed faces (`tile_and_client.md` §5.2, V).
- Air cells only conduct (`heat.py` docstring: "air here only conducts"; air k = 0.026, V).
- The heat grid's outer boundary is insulated (V).

So about 70% of Q accumulates in stationary air with no buoyant removal. §2.2 then returns it to the fuel twice:
convection h(T_s − T_cell), and radiation to T_env = the cell's temperature.

*Failure scenario (D).* A 1 kW kindling flame gives Q_gas ≈ 0.7 kW:
- in one 0.2 m air cell (ρc·V = 1,206 × 0.008 = 9.6 J/K), +73 K/s;
- spread over the flame's own overlap at 0.05 m (~0.001 m³, 1.2 J/K), ~580 K/s.

Within seconds, cells near the flame pass flame temperature on the fine grid and stay far cooler on the coarse one.
A segment just outside the flame (R3b's stick beside the starter) is then heated by hot air at 0.05 m and barely at
0.2 m, so the class flips with dx. An in-flame segment is heated by contact at T_f *and* by the cell Q_gas heated: the same gas
twice, while the global ledger stays green.

*Fix.* In Phase 1, book Q_gas straight to the outside reservoir as a ledger line (the plume leaves upward), and
don't deposit it into cells. Heat segments above a flame from a cited plume law evaluated at the point (Heskestad or
McCaffrey centreline excess temperature and velocity against height, in metres), not from cell air. Air cells
overlapped by a flame are then excluded from the coupling's convection, or use the plume value. Add a test: the
same flame on all three grids, cell temperatures in its overlap held within tolerance, and red when the deposit is
put back.

### P2-B2 (BLOCKER). Per-flame extinction is not well-posed
`fire_model.md::§4.3`; `§3.2` "Two events, with hysteresis"; `§4.1` "Clustering"; `§6.2` R1, R4

**(a) The threshold is a free per-scene parameter.** m''_ext,flame is "cited per setup". The exit crate, R3b and R3c
have no setup and no citation. R4's pass, "not flamed out at about 2.5 g/m²s", grades a value picked for R4, so it
cannot fail: a test that can't fail is a BLOCKER under the charter. The fault starts in round one's S1 fix (correction
above).

**(b) The hysteresis runs the wrong way.** Flash is at m''_flash ≈ 1.0 (PMMA) and 1.6 g/m²s (pine) (§3.2, D). The
lone-surface extinction values are 2.7–8.3 (V7 1). A one-segment cluster that has just flashed sits below its own
m''_ext. The flame goes out that step, the part is still at flash, and it re-flashes the next: flicker at a
physics-step period, which is the outcome S2 asked to prevent. The data put flash below sustain (Lyon & Quintiere's 24
against 66 kW/m²). What's missing is the transient between them: the flame's own
feedback either drives m'' up through m''_ext or doesn't. v2 has no rule for that window, so R0's t_ig ("first
flash") and R1's sustain are decided by an unwritten rule.

**(c) Membership is undefined under a smooth merge.** §4.1 merges with a smooth weight, but §4.3 averages "over its
burning area" and §4.1 keys a cluster by its minimum member. With two flames at weight 0.5, which mean is
thresholded? Either the merge is discrete, which is the S9 step back again, or extinction needs a definition over
weighted membership.

*Fix.* Make extinction a function of the cluster's physical state, not a label. One option: a flame heat-balance
criterion in the spirit of Rasbash's, where the flame sustains while the fraction φ of ΔH_c fed back to the fuel
covers L_g plus surface losses (M). It reduces to the cone case for a lone surface and is evaluated on the same
§4.2 contact terms. Fit its one free constant at R1, hold it out at R4 with no refit, and pre-register. Define the
flash-to-sustain transient explicitly, for example a flame created at flash that is tested for extinction only after
an induction time of order its own residence time, with that time cited. Write extinction over weighted membership,
or make clusters discrete with an outcome margin (CLAUDE.md band rule).

### P2-S1 (SHOULD-FIX). The partition has no positivity constraint, and in the crib the contact term can exhaust Q_gas
`fire_model.md::§4.2`

Nothing requires Q_contact,conv ≤ (1 − χ_r)·Q, or Q_contact,rad + Q_rad,view ≤ χ_r·Q (that is, Q_rad,escape ≥ 0).
If either is violated, the identity still closes with a negative term: energy drawn from gas that doesn't have it.

*Failure scenario (D).*
- **Crib.** Heskestad's L for TN 2102 at its peak is 0.235·396^0.4 − 1.02 × 0.56 = 2.0 m, over a 0.56 m footprint.
  The flame cylinder therefore envelops all ~100 sticks, and every segment counts as "inside the flame". h for 38 mm
  sticks is 15–40 W/m²K (M), times T_f − T_s of 500–700 K, times 7.8–10.7 m² of area (round-one S1): 60–300 kW,
  against (1 − χ_r)·Q ≈ 277 kW. At the upper end Q_gas reaches zero. The crib interior isn't at T_f anyway: Heskestad's
  L is an intermittent envelope, not an isothermal volume.
- **Kindling.** For a 3.2 mm dowel at u ≈ 1 m/s, Re ≈ 21 and Nu ≈ 2.8, so h ≈ 60 W/m²K and ~60 kW/m² of contact
  (D). That alone can exceed a small flame's budget.

*Fix.* Write contact from a cited in-flame flux or temperature profile (it falls with height and with depth into a
porous array), scaled so the contact terms can't exceed their shares, and record when scaling binds. Add a ledger
test that forces the bound and checks every term stays ≥ 0.

### P2-S2 (SHOULD-FIX). The contact law is missing its inputs, and R1 will absorb the gap as a fit
`fire_model.md::§4.2` "Contact"; `§6.2` R0, R1

- T_f has no value and no profile.
- u in h(d, u) has no source, and Phase 1 air is still: a plume velocity would need a correlation.
- The wall 10–30 kW/m² has no conv/rad split, although L2 §1.2 (S) says at least 50% is radiative.
- A horizontal upward face (the cone sample of R0 and R1, crib stick tops) is neither "wall" nor "thin element", so
  it has no law.

R1's heater-off outcome and its sustain at 25 kW/m² are set by that feedback. An unstated feedback becomes a
parameter tuned in R1 and carried, untested, to R4.

*Fix.* Cite each input. Give a horizontal-face feedback (pool-like flame flux against sample size) whose value is
pre-registered, not fitted, at R1.

### P2-S3 (SHOULD-FIX). Segment size is the new resolution, and nothing tests it
`fire_model.md::§2.1` Segment; `§3.2` front; `§6.1`

Segments have "fixed size in metres per recipe class", with no value. Flash is decided on the unignited part's
area-mean profile. For concurrent spread, the heated length ahead of the front (x_f − x_p, of order 0.1–0.3 m for
kindling, D from §4.1's range) is comparable to any plausible segment. A segment longer than that averages heated
and cold fuel, which is B1's failure moved from cells to segments. §3.2 has one scalar front per segment and doesn't
say what happens when it reaches the segment's end. If the next segment ignites by flash on its mean, spread
advances by segment lengths. §6.1 sweeps dx, and §8.2 sweeps the retirement floor, but nothing sweeps segment size.

*Fix.* Fronts continue across segment boundaries along the object, with flash only for a part not adjacent to a
front. Give R2b and R3 a segment-size sweep (×0.5, ×2) under the same class-and-tolerance rule as dx. Write the
segment size per recipe as a value tied to the heated length.

### P2-S4 (SHOULD-FIX). R2a's de Ris law: Φ's provenance, T_ig, thickness and the direction switch
`fire_model.md::§3.2`; `§6.2` R2a

- **(a) Provenance.** V = Φ/[kρc(T_ig − T_s)²] imposes the speed, so R2a grades Φ, not a mechanism. LIFT's PMMA
  values (Φ ≈ 14 kW²/m³, kρc ≈ 1.0 (kW/m²K)²s, T_ig ≈ 378 °C; all M) give 1.1 × 10⁻⁴ m/s ≈ 0.11 mm/s at 20 °C (D).
  That is about 2× v2's ~0.05 mm/s (M), so the test can fail, as it should. But nothing stops Φ being fitted from
  R2a's own dataset. Pre-register Φ from a source other than the graded data.
- **(b) T_ig.** The solid model has no T_ig: flash is by mass flux. Define T_ig from the model (the surface
  temperature at m''_flash under R0's fit), or the spread law and the solid disagree.
- **(c) Thickness.** Downward spread over thin PMMA is roughly an order faster than over thick (M). The formula is
  the thick-regime one, so R2a's slab must be thermally thick for the test's duration, and the dataset must state
  thickness.
- **(d) Direction.** "Concurrent" against "opposed" is a switch by direction. A horizontal crib stick has lateral
  spread with flame below. Write the speed as continuous in the front's angle to gravity, or say which applies.

### P2-S5 (SHOULD-FIX). The merge band decides R3a's class, but Jiang attributes lateral spread to radiation
`fire_model.md::§4.1` Clustering; `§6.2` R3a

V7 5 (S, abstract) says Jiang's horizontal spread is "radiation-controlled". In v2, a neighbour inside the merge
band joins the cluster and gets contact heating. Outside it, the neighbour gets §4.4 view-factor radiation. The band
is uncited and "pre-registered", so placing it between 0.75 and 1.5 cm passes R3a by construction, through the wrong
mechanism. The cross-grid gate on the band can't detect that.

*Fix.* Derive R3a's lateral class from the radiation path. Show the class doesn't change when the band is swept
×0.5–×2, or cite the band (Delichatsios's group-fire correlation, or Thomas; M, both still unread).

### P2-S6 (SHOULD-FIX). Radiation to a single T_env at air temperature, and no view-factor closure
`fire_model.md::§3.1`; `§2.2` (radiation to the surroundings); `§3.3`

Air is transparent in Phase 1, yet §3.1 radiates to T_env, and §2.2 sets T_env to the overlapped cells' temperature.
Cells heated by Q_gas (P2-B1) then act as radiating walls: radiation beyond χ_r·Q. §2.2's "exposed segment, or by
exchange" is a switch. A segment that partly sees other segments and partly sees open air needs the complement
1 − Σ_j F_ij to the surroundings, with Σ_j F_ij ≤ 1 checked.

*Fix.* T_env is the radiative surroundings (ambient or the enclosure's solid faces), never air. Add a closure test:
a segment inside a closed array of known F_ij.

### P2-S7 (SHOULD-FIX). R4's transfer from R1 is not held out by rule, and its ×1.5 band sits inside a named error
`fire_model.md::§6.2` R1, R4; `§3.3`

TN 2102 says only "pine wood crib" (V7 3), while R1 fits MaCFP-4 white pine. If R4 refits properties to the crib,
fit and grade overlap. If it doesn't, the species difference is an unnamed error source. §3.3's O₂ estimate (up to
~1.8× high) is larger than R4's ×1.5 pass band, so a fail is already foreseen for a reason the design names but
doesn't bound.

*Fix.* Pre-register that R4 uses R1's parameters unrefit, with the species difference stated. Decide the O₂ term
from the φ pre-check before choosing the band.

### NITs
- **P2-N1.** The pilot's "cited distance" (§3.2) has no source yet. R0 and R1 need an authored pilot (the cone's
  spark), which §6.2's setups don't name. Without one, §3.2's own rule stops R0 from igniting.
- **P2-N2.** §4.1's "blending … by the cluster's aspect" should be written as a function before R2.5, so the
  continuity claim can be tested.
- **P2-N3.** §0 item 4's 2.3–3.1 g/m²s rests on an assumed density (M): tag it D(M).

## 3. What still makes R3 or R4 fail for an unnamed reason

In order: P2-B1 (Q_gas feedback, dx-dependent); P2-B2 (per-setup extinction, flicker at flash); P2-S1 (crib-sized cylinder gives every stick T_f contact); O₂, named but unbounded (P2-S7); the merge band choosing R3a's class (P2-S5); segment size (P2-S3); horizontal feedback tuned at R1 (P2-S2); lateral spread on horizontal sticks (P2-S4(d)).

## 4. Checked and sound

§4.2's identity closes algebraically; B2's fix; char off under flame; R0's held-out split; R1's heater-off criterion can fail; D* (0.3–1.6 cells) and Heskestad's L at 396 kW (D).
