# Fire model v1: Physics and resolution review

Lens: Physics and resolution. Design: `docs/design/fire_model.md` @ 54358fd. Read: the design, the charter,
CLAUDE.md rules, `world_model.md` §3, the three spikes' results, `char_oxidation.md` §0, `fire_ladder/1`, `2`, `3`,
`5` §3, `7`. Tags: **V** primary source read by me (NIST TN 2102), **S** secondhand or via V7, **M** memory, **D** derived.

**Counts: 4 BLOCKER, 10 SHOULD-FIX, 5 NIT.**

## BLOCKERS

### B1. Patch state is cell-keyed and single-valued, so ignition and extinction threshold a cell-sized mean
`fire_model.md::§2.1` (surface patch row), `§3` item 5, `§4.1` "Deposit"

Patches are keyed (cell, slot, patch), "per element and per exposed cell face", with one `T_s`, one char node and
one ignited fraction (L3 rows 87, 230). §4.1's quadrature in metres is integrated over the patch *before* the
patch's single 1D model decides m'' ≥ m''_cr: a threshold on a mean over an area ∝ dx², which CLAUDE.md's "decide at
the point" rule forbids.

*Failure scenario.* A wall flame covers half of a 0.2 m patch: the patch averages 12.5 kW/m² (25 × 0.5) and stays
below m''_cr, while at 0.05 m the covered sub-patches get 25 kW/m² and ignite. The front advances in dx-sized jumps,
so R2b's class depends on dx. Heating history is averaged too: freshly covered and long-covered parts share one
profile. No law moves the ignited-area fraction, and the spikes' area-split parts (Ui/Iw/Ic) are gone.

*Fix.* Give the ignited and unignited areas of each patch separate 1D states, as the spikes' area-split did, and
add a cited law that moves the boundary between them: front speed from the flame object's footprint in metres.
Size patches in metres along each element, independent of the cell (L5 §4 already suggests receiver patches of
about 0.2 m "with a deterministic per-face split by area"). Then add the dx/3 and 2dx/3 offset test to R2 as well
as R2.5.

### B2. K = 2 slots per cell makes the fuel's representation itself depend on the grid
`fire_model.md::§2.1` (element row, K = 2), `§6` R3a and R4

An object that straddles cells becomes one element per cell, and a cell holds at most two elements. Jiang's
dowels sit at 0.75–1.5 cm spacing, so a 0.2 m cell holds about 13 × 13 dowels per layer (D). TN 2102's crib has
38 mm sticks at about 2.7 cm gaps (D, below), about 15 sticks per 0.2 m cell, while a 0.05 m cell holds one or two.
Above two, the only geometry left is `bed`, which places its surfaces statistically. So the R3a array and the R4 crib
are discrete sticks on the fine grid and a statistical bed on the coarse one. The gap criterion R3a grades doesn't
exist in a bed. That makes the mechanism change with dx, which is a resolution-rule violation before any physics runs.

*Failure scenario.* R3a at 0.2 m becomes a bed, which has a porosity but no gap, so "no sideways spread at 1.5 cm"
can't be evaluated; at 0.05 m it runs on discrete dowels. The cross-grid comparison compares two models.

*Fix.* Key elements by object, unbounded per cell, with per-cell shares only for grid coupling. Or make every ladder
scene a bed on every grid and drop R3a's gap criterion.

### B3. The flame's energy is booked more than once: contact flux is added on top of χ_r·Q and (1 − χ_r)·Q
`fire_model.md::§4.1` "Flux onto surfaces" and "Into the gas", `§3` item 4, `§2.3` invariant 3

§4.1 sends χ_r·Q out as radiation and (1 − χ_r)·Q to the zone, and separately gives surfaces inside the flame
10–30 kW/m² of contact flux (≥ 50% radiative, L2 §1.2, S), debited from neither. §3 also adds a "flame" flux (the
spikes' q''_f) to burning patches, which sit inside their own cluster's flame and so can get both. world_model §3
(S5) requires feedback "debited from the heat release"; the design drops that.

*Failure scenario (D).* A wall flame per unit width, with L2's metric form x_f = 0.043·Q'^(2/3) and 25 kW/m² over
x_f:
- at Q' = 5 kW/m, x_f = 0.126 m and the contact power is 3.1 kW/m, 63% of Q';
- at Q' = 30 kW/m, x_f = 0.415 m and the contact power is 10.4 kW/m, 35% of Q'.

On top of 0.3 + 0.7 = 1.0·Q', the ledger books 1.35–1.63 Q'. Invariant 3 fails, or "closes" with the term on both
sides (the 1,000× pattern §2.3 warns of). The extra feedback props up burning, so R1–R4 could pass for an unphysical
reason.

*Fix.* Write the flame ledger as one equation per cluster:
- Q = Q_contact,rad + Q_rad,view + Q_rad,escape + Q_contact,conv + Q_gas;
- Σ radiative terms = χ_r·Q;
- Q_gas = (1 − χ_r)·Q − Q_contact,conv.

State that a surface inside the flame gets contact flux only, with no view-factor term on top. State that a burning
patch's own flame flux *is* its cluster's contact flux, so §3's "flame" term is not a second source. Add a closed-form
ledger test: a cluster with known geometry over known receivers.

### B4. Three R2 pass criteria cannot fail, because they grade the model's own inputs
`fire_model.md::§6` R2 row; `§4.1` "Geometry", "Flux onto surfaces"

- **(b) "flame height in the correlation band".** The model *computes* x_f from that correlation (§4.1), so the
  check is tautological.
- **(b) "wall flux peaking at 10–30 kW/m²".** The in-flame flux is *imposed* at 10–30 (§4.1). Also tautological.
- **(a) "no spread cold".** The design has no opposed-flow mechanism: no forward heat transfer ahead of the flame
  foot, no de Ris/LIFT Φ, no foot extinction. With nothing to carry the flame against the flow, the model gives no
  downward or lateral spread at any temperature, so the cold half passes trivially. The preheated half (1.2–3.0 mm/s,
  derived from LIFT parameters, not measured [V7 6]) can then only fail, and the design hasn't said what produces it.

The charter makes a test that cannot fail a BLOCKER.

*Fix.* For R2b, grade something the correlations don't fix: pyrolysis-front position against time, or the
acceleration exponent, against a measured upward-spread dataset (the FDS-validated PMMA panels, class only, or
Leventon). Run R2b on all grids with the B1 front law. For R2a, either add a cited opposed-flow foot law (de Ris's
Φ, so T_s,min emerges) or drop R2a and say opposed spread is a gap. (R2.5: N4.)

## SHOULD-FIX

### S1. A per-patch extinction law at cone scale contradicts R4's own oracle
`fire_model.md::§3` item 5; `§0.4`; `§4.1` "Inside a bed"

The extinction value carried from the spikes is Emberley's 3.7 g/m²s, measured on a 0.1 m cone specimen. TN 2102
Test 13 peaks at 396 ± 18 kW with ΔH_c,eff 16.3 MJ/kg (V, Table 1 row 13), so 24.3 g/s at the peak. Its exposed
area, from 56 × 56 × 46 cm, 3.8 cm sticks (V) and 39.39 kg, with an assumed density of 400–550 kg/m³ (M), is 7.8–10.7
m² (D: 89–122 sticks, about 12 layers). **The area-mean mass flux at the peak is 2.3–3.1 g/m²s (D)**, below 3.7 at
every density and at or below the 2.7–8.3 species band's low end. A per-patch "goes out below m''_cr" therefore
predicts that NIST's crib flames out at its own peak.

Extinction belongs to a flame, not a patch: inside a cluster, a patch below the cone value still feeds a flame
anchored elsewhere. This is likely part of why hot-surface F went out with 33–40% left; the design blames only the
missing flux.

*Fix.* Evaluate flaming extinction per flame object: cluster Q and its anchoring, with m''_cr scaled by setup, since
Plathner reports 19.2 against 2.0 g/m²s by sample size (S). A patch inside a sustained flame keeps feeding it.
Pre-register the check above: a fully involved TN 2102 crib must not flame out at m'' ≈ 2.5 g/m²s.

### S2. "Ignition and extinction by one m''_cr" is inconsistent with the design's own sources
`fire_model.md::§3` item 5; `§12` first bullet; `§6` R0, R1

§12 says Lyon & Quintiere's 24 kW/m² is the *onset* (flash) criterion and 66 the *sustained* (fire-point) one.
MaCFP's t_ig is defined at Q'' ≥ 24 kW/m² [V7 2c, 12]. That is m'' ≈ 1.0 g/m²s for PMMA (24/24.5) and about
1.6 g/m²s for pine (24/15) (D). Extinction data sit at 2.7–8.3 g/m²s. One threshold can't hit both: set it at the
ignition value and extinction comes late against Emberley; set it at the extinction value and R0's t_ig comes late
against MaCFP's definition. A single threshold with no hysteresis also lets a patch flicker on and off at the value.

*Fix.* Two criteria with a gap between them: flash, or attachment, at the data's own t_ig definition, and sustain or
extinction at the fire-point value. Pre-register which event R0's model time is compared with.

### S3. R1's extinction band and its white-pine curves can't both pass
`fire_model.md::§6` R1; `§3` "Two checks"

MaCFP-4's white pine burns steadily at 25 kW/m² at about 3.8 g/m²s [V7 point 1]. So for that species in that rig,
the critical external flux is below 25, at or under the band's 24 floor. The band (24–57) mixes six species and
radiata CLT. Grading R1's pine curves *and* "extinction in the cited band" leaves about 1 kW/m² of room (24–25). The
design says "R1 pins the band for the species it grades", but no extinction dataset for *Pinus strobus* is named.

*Fix.* Name the extinction dataset for the graded species, or grade extinction only as "no sustained flaming when the
heater is removed", plus a sustain at 25 that matches MaCFP-4.

### S4. Fit and grade on the same data
`fire_model.md::§3` "The rate law…", "Fitted parameters"

R0 "fits both [rate laws] to the MaCFP data", and the fitted parameters are "re-fitted by our model to R1's data".
R0 and R1 are then graded against the same MaCFP curves, so passing the envelope is partly guaranteed. "Apparent
L_g ≈ 15 kJ/g produced, not input" weakens to a consistency check when MLR against flux is in the fit set.

*Fix.* Pre-register a held-out split: fit at 30 and 60 kW/m², grade at 25, 50 and 75. Grade PMMA's 65 kW/m² point
from a fit at 25, and the reverse.

### S5. Replacing 6b–6d silently drops in-bed radiation, the draught and O₂
`fire_model.md::§3` item 4 ("εσ(T_s⁴ − T∞⁴)"); `§0` header ("replaces 6b–6d"); `§4.1`

6c carried P1 slat-to-slat radiation, an Ergun draught, O₂ use and Chilton–Colburn exchange (`bed.md` §1). The
design radiates every surface to T∞ and keeps none of it. Interior char facing char at 600–900 °C loses almost
nothing net (`char_oxidation.md` §0.3); radiating to 20 °C it loses ~23 kW/m². R4 would fail on this alone.

*Fix.* Keep a surface-to-surface term: view-factor exchange among element surfaces, or the bed's P1 with the B2 fix.
State what replaces the draught and the O₂ accounting, or record them as gaps with numbers.

### S6. Oxygen: TN 2102's crib is probably in the porosity-limited regime, and the exit crate is packed with cardboard
`fire_model.md::§4.1` (no O₂ term); `§6` R4; `§7`

With the same assumed densities, Heskestad's φ = s^½·b^½·A_v/A_s is 0.008–0.041 cm (D), so 1 − exp(−50φ) is
0.32–0.87, below the "transition near 0.05" (L2 §3.1, S). That explains L2's unattributed measured/ideal ratio of
0.5–0.75. Dense cribs are "limited by availability of oxidizer" (McAllister & Finney via L2, S); hot-spike F's O₂
demand already exceeded supply for 29–30% of flaming. With no in-bed O₂ or flow limit, the peak is overpredicted by
up to ~1.8× at 450 kg/m³, outside R4's ×1.5. The exit crate is "packed with cardboard" (§7): denser still, unnamed.

*Fix.* Pre-register the crib's porosity regime from its real stick count (TN 2102 doesn't give it; ask NIST or
measure the photos). Add an in-bed O₂ and draught term, or record it as the gap R4 leans on.

### S7. Char oxidation's role in sustain and residue is unstated
`fire_model.md::§2.2` (char → CO/CO₂ "Phase 1: the outside reservoir"); `§6` R4

With char yield 0.25 (L1 §4), "≤ 10% residue" passes only through char oxidation, which the design gives unlimited
O₂ and doesn't turn off under flame (`char_oxidation.md` §0.5 says to). Concurrent with flaming it props up burning,
masks R1 extinction, and passes the residue class whatever the flames do. TN 2102's residue was measured after the coals were "spread
out and raked into a water bath" at about 48 min (V).

*Fix.* Turn char oxidation off under flame cover. Grade the residue at 48 min to match the protocol, and grade the
ember-phase duration (≥ 18 min tail) as well.

### S8. The correlations are used outside their fitted ranges, and the design doesn't say what happens there
`fire_model.md::§4.1` "Geometry", "Flux onto surfaces"

- **Delichatsios and Hasemi** were tested for x_f of 0.3–1.4 m. Kindling and starter flames are 0.1–0.3 m (D: 5 kW/m
  gives 0.13 m), and a 20 mm stick isn't a wide wall.
- **The in-flame flux** of 10–30 kW/m² was measured on walls. Jiang's 3.2 mm dowels and Finney's 1.27 mm combs heat
  by convection, with h rising roughly as d^−½. The design's own §0.1 mechanism is a size-dependent convective flux
  that a fixed wall value understates on fine fuel, so R3a's dowels may never ignite in the model.
- **Heskestad**'s range 7 < Q^(2/5)/D < 700 (S, single source, via Zalosh) holds for a 1 kW, 2 cm flame (50) and for
  the crate (26). Its real limit is source shape: no rule picks D for a cluster of vertical sticks, or picks sheet
  against cylinder.
- **Emberley's 3.7** was measured on a 0.1 m cone specimen backed by 150 mm CLT, and is applied to 20 mm slats
  burning on both faces, where the core heats as in the back-face second peak (S1).

*Fix.* For each correlation, state the fitted range and the behaviour outside it: refuse the scene, use a cited
alternative (for in-flame heating on thin elements, h(d, u)·(T_f − T_s) plus flame radiation), or report the run as
an extrapolation. Write the sheet-or-cylinder choice and D as continuous functions of the cluster's geometry, not a
switch.

### S9. Clustering decides the outcome, has no cited rule, and is discontinuous
`fire_model.md::§4.1` "Clustering"

Flame height is non-linear in Q, so the merge decision changes the flux: two 1 kW stick flames give L = 0.21 m each
(L2, D), merged 2 kW gives about 0.29 m. "Connected burning area in metres" needs a distance threshold, and none is
given. In R3a that threshold decides Jiang's 0.75 cm and 1.5 cm classes. A merge is a step change in footprint, and
§4.3's loop amplifies steps.

*Fix.* Use a cited merging criterion (Thomas, or Delichatsios on flame merging, still unread), or a smooth merge
weight over a cited distance band. Add the gap-sweep band gate L5 §3(c) proposes to R3's pass criteria. §6's R3 row
dropped it, keeping only §4.3's general sentence.

### S10. Ignition outside a flame needs a pilot rule
`fire_model.md::§3` item 5; `§12` "Unpiloted ignition"

m''_cr is a piloted criterion. A target outside every flame, heated only by view-factor radiation, would "ignite"
under §3 at piloted levels (wood CHF about 12 kW/m², S) instead of autoignition's 25–35 (M). The design lists this as
open but doesn't state the interim rule.

*Fix.* Ignition requires m'' ≥ m''_ign and a pilot: the patch inside, or within a cited distance of, a flame or a
hot-gas region above its autoignition temperature. Until autoignition is cited, unpiloted ignition is refused and
recorded as a gap.

## NITs

- **N1. Where does (1 − χ_r)·Q go?** `§4.1` sends it to "the zone (the outside reservoir)", while `§4.2` says "the gas
  grid carries the plume's energy". Pick one. If it goes to the grid, state the deposit footprint, by overlap.
- **N2. χ_r is unspecified.** Cite one per fuel and flame scale.
- **N3. The R4 pilot isn't modelled.** Its 0.75 kg of crinkle paper (V) sets the time to peak (±40% graded), and
  paper isn't a ladder material until R3. State its model, or use a prescribed-HRR pilot measured from Test 13's
  early curve.
- **N4. R2.5 is verification, not validation.** χ_r·Q to round-off is guaranteed by construction. Keep it as a unit
  test, and don't count it as a physics pass.
- **N5. No rung grades moisture**, a shipped variant. Pin each rung's moisture; grade its effect on t_ig at R0.

## The "may be correct physics" claim (§0.4, §1 row 4)

It is sound only for **one isolated surface**, and partly even there.
- **For:** the closed form is right (D: 0.9σ(823⁴ − 293⁴) = 23.0 kW/m²). TN 2102 says "a single pallet is difficult
  to burn without a heat source to sustain the fire" (V, §4.2).
- **Against:**
  - (a) The graded species, white pine, sustains at 25 kW/m² in MaCFP-4 (S3).
  - (b) The case cited is C_F, a fully lit crate, not one surface. Its going out conflicts with the R4 oracle's
    area-mean flux of 2.3–3.1 g/m²s at the peak (S1).
  - (c) The spike also lacked surface-to-surface radiation (S5).

So C_F's miss more likely comes from three model choices: a per-patch cone-scale extinction law, no surface-to-surface
exchange, and no in-flame feedback. §1 should say "single surfaces: probably correct; crate F: probably an artefact,
for these reasons". R1 can't decide F. R4 can.

## What would make R3 or R4 fail for a reason the design hasn't named

In order of likelihood:
1. per-patch extinction (S1);
2. no surface-to-surface radiation (S5);
3. in-bed O₂ and draught (S6), worse with cardboard packing;
4. the grid-dependent switch between discrete elements and a bed (B2);
5. the merge rule (S9);
6. a wall in-flame flux applied to thin fuel (S8);
7. char oxidation during flaming (S7).

Moisture is minor at the graded moisture contents (N5).

## Checked and sound

D* (0.060/0.080 m, D); the 23 kW/m² closed form (D); TN 2102's crib, Test 13 numbers, pilot and quench (V); the
design follows V7 on Emberley, FDS crib versions and D*/dx; §8's integrators, substep caps and area hygiene.
