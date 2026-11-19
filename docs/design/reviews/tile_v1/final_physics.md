# Tile spec v3: final Physics-and-resolution review

Lens: Physics and resolution, final round. Reads `tile_and_client.md` §2, §5, §6 and `world_model.md` §0 (D30).
Arithmetic was recomputed in the worktree's `.venv` (scipy `brentq` for every surface balance). Sources were checked on
the web where they could be found. Where a value could not be found online, the table says so: "reviewer's memory"
is no better than the author's.

**Verdict: not ready. The glow claim breaks global energy conservation, the bed has no in-bed transport, and the
burning state is a threshold on a cell mean. Three BLOCKERs, five SHOULD-FIX, four NITs.**

## Constants

| Constant | Spec | Literature | Source | Verdict |
|---|---|---|---|---|
| ΔH_c,eff, volatiles | 12.4 MJ/kg | ~12–13 MJ/kg effective for wood flaming; complete net heat of dry wood ~17–18 MJ/kg | Tewarson, SFPE Handbook, "Generation of heat and chemical compounds" (not found online; reviewer's memory); Babrauskas, "Effective heat of combustion for flaming combustion of conifers" (agris.fao.org record) | Plausible, unverified. Total 567 MJ = 17.5 MJ/kg sits at the complete-combustion ceiling, so the energy total is consistent. |
| Char yield χ | 0.25 | 0.15–0.35 depending on heating rate | Di Blasi 2008, "Modeling chemical and physical processes of wood and biomass pyrolysis", PECS 34 (reviewer's memory) | Confirmed as a range |
| ΔH, char → CO₂ | 32.8 MJ/kg | 32.8 is graphite → CO₂ (393.5 kJ/mol ÷ 12). Char (85–90% C) is ~30–32. **C → CO gives 9.2 MJ/kg C**, and CO is the main surface product above ~800 K | Arthur 1951, Trans. Faraday Soc., CO/CO₂ ≈ 2500·exp(−6240/T) (formula from memory, not confirmed online); Holzleithner, Geier & Shaddix 2013, Proc. Combust. Inst. 34 (the ratio depends strongly on T and on p_O₂) | **Constant fine; the product assumption is wrong by up to 44%** (FPH-B2) |
| L_g | 1.8 MJ/kg | ~1.8 kJ/g for Douglas fir in Tewarson's table; the *effective* L of charring wood rises as char deepens | Tewarson (memory); Urbas & Parker 2007, "Measuring the effective heat of gasification", Interflam (firedoc.nist.gov, no numbers online); Sibulkin 1986, FSS 1 | Plausible for virgin wood; understated for a charring bed (FPH-S1) |
| T_p | 380 °C | Piloted ignition surface temperatures of ~300–400 °C, rising as the flux falls | Li & Drysdale (cited via the Spearpoint & Quintiere search); Babrauskas 2002, "Ignition of wood: a review" (memory) | Plausible |
| q''_f | 25 kW/m² (15–35) | Not found online. Heskestad's 13.8 g/m²s × 1.8 MJ/kg = 24.8 kW/m², so 25 is *implied* by the crib correlation, not measured independently | see FPH-S1 | The cross-check is circular |
| Critical heat flux | 12 kW/m² | ~10 kW/m² lowest within 1.5 h; ~12 along the grain, ~8 end grain | Spearpoint & Quintiere 2001, Fire Safety J. 36(4):391–415 | Confirmed (along grain) |
| χ_r | 0.3 | ~0.25–0.4 for wood flames | Tewarson (memory) | Plausible, unverified |
| ε, h_c | 0.9, 10 W/m²K | char ε 0.85–0.95; h_c 5–10 for natural convection on a 0.6 m face, but 15–25 on 20 mm slat features | Incropera, natural convection correlations | ε confirmed; h_c is low for the bed's interior surfaces |
| Crib regression, 20 mm | 2.3×10⁻⁵ m/s | v = 2.2×10⁻⁶·b^−0.6 → 2.30×10⁻⁵ at b = 0.02 m, which recomputes exactly; the b^0.6 dependence is confirmed | Heskestad 1973 via Babrauskas, SFPE Handbook "Heat release rates" (exact form not found online); McAllister 2019, Front. Mech. Eng. 5:11 | Confirmed, *if fuel-surface controlled*. It may not be (FPH-S2) |
| Crib regime | not stated | Heskestad's porosity φ_H = s^½ b^½ A_v/A_s (cm); transition at **~0.05 cm** | McAllister 2019 (quoting Heskestad 1973) | Missing (FPH-S2) |
| Ember temperature | 920 °C (layer), 550 °C (face) | Smouldering maple embers measured at 750–1070 °C, mean 930 °C (ratio pyrometry); thermocouples read >200 K low | Kim 2019, "Imaging pyrometry of smoldering wood embers", PhD, U. Maryland (drum.lib.umd.edu/handle/1903/21928) | 920 matches small, well-ventilated embers. It is **not what this model's balance gives** (FPH-B2) |
| Extinction coefficient | σ/4 | β = σ/4 for randomly oriented convex elements (Cauchy's mean projected area = S/4); used for fuel beds as σβ/4 | Cauchy's formula; Albini 1985/Rothermel-type fuel-bed radiation (memory) | Correct for random elements; a crate's slats are aligned (FPH-S3) |

No *constant* in the table is wrong by more than ~30%. The **surface-heat assumption behind 6d (CO₂ at the surface)**
is wrong by up to 44%, and the **derived glow temperature** is high by 80–340 K.

## BLOCKERs

### FPH-B1. The bed's interior has no way to shed char-oxidation heat

`tile_and_client.md::§5.2 (6c, 6d)`. Every bed cell's char oxidises at the diffusion limit with ambient Y_O₂: 0.87 g/m²s
× 32.8 MJ/kg = 28.5 kW/m² × σ = 25, or **710 kW/m³** of bed. Only the envelope has a loss law (6a). Inside, heat moves
only by cell conduction through a wood-and-air mixture (k ~ 0.05–0.15 W/m·K). The bed's heat capacity is about
0.25 × 600 × 1,500 ≈ 225 kJ/m³K, so an interior cell heats at about **3 K/s**, passes 1,300 °C within about 7 minutes of
the ember phase, and is bounded only by its char running out. Steady state needs ΔT = q'''a²/2k ≈ 10⁵ K. The honest run
would trip the "max skin ≤ 1,300 °C" control (§6.4), and the ledger closes while the physics is wrong.

A real bed sheds that heat by radiation between elements (Rosseland conductivity k_r = 16σT³/(3β) with β = σ/4: about
84 W/m·K at 1,200 K) and by draught air (O₂ demand of 4.6 g/s of char is about 53 g/s of air, which carries out
**32–43 kW** at 900–1,100 K). Its interior O₂ is depleted downstream; the model has no O₂ (world_model §0 defers O₂ to
Phase 2).

**Fix:** add in-bed radiative diffusion (k_r in metres from σ, closed-form testable, grid-independent) and a draught
sink, or cap interior char oxidation by an O₂ supply set in metres. Recompute §5.3 with them. With k_r alone, a sphere
estimate gives a centre about 960 °C at an 830 °C envelope; a slab gives about 1,150 °C. Both are under 1,300 °C, but the
§6.4 floor bound (900 °C) is then wrong (FPH-S4).

### FPH-B2. The 920 °C ember layer creates energy; an honest balance gives 580–840 °C

`tile_and_client.md::§5.3 (Embers)`, `§5.2 (6a ℓ)`. "4 × 28 = 112 kW/m²" assumes 4 m² of char surface per m² of
envelope (σℓ). This bed has only **5.4 / 1.8 = 3.0**: a 0.16 m layer on a 0.6 m box is 0.29 m³, more than the bed's 0.216 m³.
The layers overlap. So 1.8 m² × 112 = 202 kW would leave the envelope, but all the char together makes only
5.4 × 28.5 = **154 kW**. Recomputed envelope temperatures (ε 0.9, h 10, T_amb 15 °C):

| Assumption | Envelope flux | T_envelope |
|---|---|---|
| Spec (4×, CO₂, no internal loss) | 112 kW/m² | 925 °C (impossible: exceeds generation) |
| Global, CO₂, all heat out through the envelope (upper bound) | 85.5 kW/m² | **837 °C** |
| Global, CO₂, minus ~35 kW of draught air | ~66 kW/m² | ~770 °C |
| Layer, 4×, CO₂, with internal convection by the same h that sets h_m | — | 824 °C |
| Global, CO at the surface (9.2 MJ/kg C, double the carbon rate, 56% of the heat), minus draught | ~29 kW/m² | **~570 °C** |
| Bare char face, CO₂ / CO | 28.5 / 16.0 kW/m² | 551 / 426 °C (spec's 550 recomputes) |

h_m is derived from h_c by the Chilton–Colburn analogy, so the same air that brings O₂ to each surface also cools it.
The spec counts the O₂ and drops the cooling.

**Glow conclusion:** under the spec's own 6d (CO₂ at the surface, no draught) the model probably shows ~830 °C and
**passes**, with ~200 K margin over 625 °C. That pass rests on two uncited modelling choices, not on constants. Under
the physically more defensible CO-dominant surface chemistry plus draught loss, it gives ~570 °C and **fails**. Real
embers reach ~930 °C (Kim 2019) because small elements have much larger h_m (h ∝ d^−¼ or steeper) and their CO burns
in the boundary layer. This model has neither. As specified, the glow criterion is not an honest pass: it is decided by
the product assumption.

**Fix:** correct §5.3 to the global bound (≤ 837 °C). Make the surface product a cited constant (the CO/CO₂ ratio as a
function of T), and say whether the CO's heat returns to the surface. Add the internal convective term. Size h_c for
20 mm features with a cited correlation. Then either the pre-registered failure path triggers or it doesn't; the
spec must not claim "margin" now.

### FPH-B3. Bed ignition and burning are thresholds on a cell-mean skin

`tile_and_client.md::§5.2 (6b, 6c)`, `§6.3 items 2, 4`. Each bed cell has *one* fuel-surface skin, and "burning" turns
on by a critical flux or T_p on that skin. A 0.2 m cell holds 0.20 m² of fuel surface, a 0.05 m cell 0.003 m². At
0.2 m the first ignited cell alone exceeds §6.3's 0.1 m² "ignited" criterion. At 0.05 m that takes 32 cells and a front
crossing 0.15 m. The front then advances a whole cell per cell-ignition delay, so its speed scales with dx. That is the
CLAUDE.md "averaging then thresholding" violation, inside the bed. The glow layer has the same problem: at 0.2 m,
ℓ = 0.16 m is smaller than one cell, so "envelope-layer skin" is the cell's skin. At 0.05 m it is spread over about
3 cells with a gradient, so the cross-grid t_glow compares different quantities.

**Fix:** carry a continuous burning-surface fraction per cell, advanced by a flame-spread rate in m/s (cited), and
define the envelope-layer temperature as an ℓ-weighted integral in metres, with its own sub-cell state when ℓ < dx.
Add a closed-form test: a 1-D bed front at constant speed, cross-grid.

## SHOULD-FIX

**FPH-S1. q''_f and L_g are not independent evidence.** `§5.1`, `§5.3 cross-check`. 25 kW/m² ÷ 1.8 MJ/kg reproduces
Heskestad's rate because 25 is what the rate implies. A charring bed's effective L grows with char depth (Urbas &
Parker 2007), so with a cited q''_f of 15 the bed gives 402 kW and 750 s, half the release. **Fix:** anchor m'' on the
cited crib correlation, and use q''_f only for the sustain margin, or cite a measured q''_f for cribs.

**FPH-S2. The crib regime is unchecked and the bed is borderline.** `§1.1`, `§5.3`. As square-stick layers (b = 2 cm,
s = 6 cm for φ 0.25, n ≈ 8 per layer): A_v = s²(n−1)² ≈ 1,764 cm², A_s ≈ 10.8 m², so φ_H = √6·√2·(1,764/108,000) ≈
**0.056 cm**, against the 0.05 cm transition (McAllister 2019, Heskestad 1973). A slightly denser crate is
ventilation-controlled: the rate falls below the fuel-surface rate, and the model has no O₂ to say so. **Fix:** state
φ_H for the content geometry, and require φ_H ≥ 0.1 cm (the slats' spacing) or record the regime as a Known gap.

**FPH-S3. ℓ = 4/σ assumes random orientation; a crate's slats are aligned.** `§5.2 (6a)`. Face-on plates give β = σ/2
(ℓ = 0.08 m); edge-on plates with 60 mm gaps let radiation in far deeper. The form σ/4 is right for random convex
elements. **Fix:** cite it as an isotropic assumption, or derive β per face from the slat orientation. Either way, cap
σℓ at the bed's surface per envelope area (FPH-B2).

**FPH-S4. The V_floor contact bound (900 °C) is set from the envelope, but the floor touches the bed's bottom.**
`§6.4`. The bottom face has no 6a loss; with FPH-B1's fix its temperature approaches the interior's, ~960–1,150 °C. The
honest run can exceed V_floor, a control red for the wrong reason. **Fix:** derive the bound from the interior solution
of FPH-B1, the maximum over the bed.

**FPH-S5. Convergence is measured against an unconverged reference.** `§6.3 item 8`. For a first-order event time,
e₀.₁ against 0.05 m is half the true error of 0.1 m, so tol = 15% is really ~30%. The rule's shape is sound: absolute
errors, the monotone-or-negligible clause, tol/4 for noise. But it never checks the observed order. **Fix:** compute
p = log₂((t₀.₂ − t₀.₁)/(t₀.₁ − t₀.₀₅)), require p > 0.5 and the same sign of the differences, and gate on the Richardson
error (or Roache's GCI) rather than e₀.₁. Without FPH-B3's fix, t_ignite and t_glow will not show a positive order.

## NITs

**FPH-N1.** `§5.3 Burn-out`. t_gone is at 1.62 kg remaining, so the ember phase burns 6.48 kg, not 8.1:
**1,410 s**, and t_gone ≈ 1,860 s (q''_f 25). Under CO surface chemistry the carbon rate doubles, giving ~700 s. The
5,400 s cap holds in all cases, and holds even if the char area halves as the bed collapses (~2,900 s).

**FPH-N2.** `§6.4 row 2`. "1,300 °C, the surface balance at 4× the flaming release flux" doesn't recompute: 4 × 144 kW/m²
balances at ~1,550 °C. 1,300 °C is ~312 kW/m² (2.2×). State the derivation. Also note that the 6a-deletion goes red only
in the ember phase (pyrolysis pins skins at T_p while flaming), so this control needs the `slow` tier.

**FPH-N3.** `§2.1`. The flaming numbers recompute (0.3 × 780/4π = 18.6 kW/m² at 1 m). But the point source is a
far-field model (Modak 1977; Beyler, SFPE Handbook). Here the flame is ~2.7 m tall (Heskestad: 0.235·Q̇^0.4 − 1.02·D,
D = 0.68 m) and the target is ~1.5 diameters away. A solid-flame estimate (E ≈ 35 kW/m², κ ≈ 0.8 m⁻¹, F ≈ 0.2–0.3) gives
**~7–10 kW/m²**, so the spec's figure is ~2× high. The ember-phase figure, 4–12 kW/m², is consistent with a 0.36 m²
face's view factor (3.6–10.6 kW/m² at 640–920 °C). The 9.3 kW uses absorptance 1, not 0.95.

**FPH-N4.** `§2.1`, `§6.2`. The scripted actor stays 0.5 m from the crate's axis-side face, 0.25 m from its skin,
through flaming: inside the near-field flame, ~30–50 kW/m². A lumped 245 kJ/K body warms 2.3 K/min while real skin
reaches pain in seconds at 10 kW/m². What D28 should feel is skin flux, not the mean of a lump: a threshold on a
mean, the same class as FPH-B3. Record it as a Known gap, or add a skin node.

## Controls under deletion

Ledger (drop a line): red. 6a (disable): red, but only in the ember phase (FPH-N2). Plume into floor: ~540 kW onto the
floor, red. Pilot resolved to `crate_far`: red. Burning never populated: red. xfail gate: red by construction. Every
control does fail under its deletion. Two may also fail the *honest* run: max-skin (FPH-B1, until in-bed transport
exists) and V_floor (FPH-S4).
