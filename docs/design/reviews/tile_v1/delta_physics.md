# Tile spec v2, delta review: Physics and resolution

Target: the folded `docs/design/tile_and_client.md` (v2, working tree on `phase1/tile-spec`) against `physics.md`
(round 1) and D29 (`world_model.md` §0). Scope: what changed. Earlier findings that the fold closed (PH-S2's metric
areas, PH-S4's footprint and integer duration, PH-S6's machine scope, PH-N1, PH-N3) aren't repeated here.

**Counts:** 3 BLOCKER, 5 SHOULD-FIX, 3 NIT.

**What I recomputed** (derived; ε = 0.9, h_c = 10 W/m²K, T_amb = 15 °C):
- **Char-through times.** 0.3 m ÷ 0.65 mm/min = **27,692 s**, and 0.2 m gives **18,462 s**. Both match the spec.
- **`t_gone` by the spec's own 5% criterion.** With fronts from four sides and the top, the remaining volume is
  (0.6 − 2s)²(0.6 − s). It reaches 0.0108 m³ at s = 0.216 m, which is **19,950 s**.
- **Exposed-face loss.** At 600 °C it is 29.3 kW/m² radiative plus 5.9 convective. Over 1.8 m² that is **63.3 kW**,
  against a mean release of **58.1 kW** (1.61 GJ / 27,700 s).
- **Release per m² of burning face at β₀.** 1.083×10⁻⁵ m/s × 600 kg/m³ = 6.5 g/m²s, times 12.4 MJ/kg = **80.6 kW/m²**.
- **Surface equilibrium temperatures** (radiation plus convection balancing the flux):
  - the full release flux, 80.6 kW/m², gives **820 °C**;
  - 2× that gives 1,039 °C;
  - 4× gives 1,297 °C.
- **Loss at the glow threshold.** At 625 °C the face loses 32.9 + 6.1 = **38.9 kW/m²**.
- **The torch.** 2 kW over a 0.2 m radius is **15.9 kW/m²**.
- **The body.** τ = 70 × 3,500 / (10 × 1.9) = **12,895 s**, which matches the spec. Its exchange volume (r = 0.45 m,
  h = 2.0 m) is 1.27 m³ of air, which holds **1.53 kJ/K**. That makes the coupled τ **80 s**.
- **Concrete under a 4 kW/m² flux** (semi-infinite) rises **396 K** in 27,700 s.

**Taken from memory, to verify:**
- a radiative fraction of about 0.3 for wood flames;
- flame feedback of about 15–25 kW/m² on a 0.6 m face;
- a critical heat flux for wood of about 12 kW/m²;
- a char yield of about 0.2–0.3.

---

## BLOCKER

### DPH-B1. The burn law's driver is unspecified, and the uncited flame-feedback flux decides the exit

`tile_and_client.md::§5.1 plume_export`, `::§5.3`, `::§9 Q2`; `world_model.md::§3 Flame feedback`; D26 (pyrolysis
deferred)

D29 brought in recession (6c) but not pyrolysis, so nothing says what sets the recession rate. Two readings are
possible, and each breaks a different claim.

**(a) A prescribed char rate, β₀.** Then t_gone ≈ 19,950 s by construction.
- The crate can't self-extinguish, so §5.3's stated risk and Q2 are vacuous.
- Item 8's `t_gone` convergence tests only 6c's geometry. P3 already measured that at 0.370 at every grid, so this
  part of item 8 is near-unfailable.
- Release then has no energy cost: mass is lost whatever the surface heat balance (world_model S5's own objection).

**(b) A flux-driven rate** (mass loss = net surface flux ÷ heat of gasification). Then the spec's own numbers say the
block goes out.
- Even 100% feedback of the mean release (58 kW) is below the loss at 600 °C over the exposed faces (63.3 kW). With
  a physical feedback fraction of about 0.2–0.35, net gain is negative well below 600 °C.
- So the burn time, and whether the crate goes out, follows from q''_f, the "fixed flux per m²" of S5.
- §5.3 forbids tuning β but says nothing of q''_f, and the material table has no provenance row for it.

**Failure scenario.** Step 6 picks (b). The crate goes out at about 1,000 s. Someone raises q''_f from 20 to
45 kW/m² "to match β₀", and the exit passes with an uncited 2× calibration that no rule flags. Or step 6 picks (a),
and every gated time is geometry.

**Fix.**
- Before step 6, the spec names the driver. Flux-driven is the honest one. It means pulling S2's energy-limited
  pyrolysis into D29 as 6d, an owner amendment, or else stating (a) as a recorded Known gap ("burn rate prescribed,
  extinction not modelled").
- Give q''_f a cited value and a provenance row, under the same no-tuning rule as β.
- Write down now, before measuring, what the exit becomes if the crate goes out (Q2). Deciding after seeing the
  result is a post-hoc criterion.

### DPH-B2. Glow at 625 °C is not reachable from flame feedback alone, and the exit has no honest-failure path for it

`tile_and_client.md::§6.3 item 4`, `::§5.2`, `::§9 Q2`

At 625 °C an exposed face loses 38.9 kW/m², before conduction into the wood. Holding a skin there in steady state
needs feedback of at least 38.9 kW/m². That is **f ≥ 0.48** of the β₀ release per m² of burning face. A wood flame's
feedback fraction is about 0.2–0.35 (from memory). The torch alone gives 15.9 kW/m², which only reaches about
360 °C. Real glowing embers come from char surface oxidation (exothermic, at the surface), and D29 doesn't carry it.

**Failure scenario.** An honest q''_f of 20 kW/m² never gives 0.08 m² at 625 °C. Item 4 fails at every grid, and Q2
only covers burning away.

**Fix.**
- Extend Q2 to glow.
- Either add char oxidation to 6b (a heat release at the skin, on the ledger) as an owner amendment, or derive the
  glow criterion from the surface balance with a cited q''_f.
- Never lower 625 °C to whatever the run reaches.

### DPH-B3. The 2000 °C cap can't fail under its stated deletion once 6a exists, and the `crate_far` deletion doesn't move the pilot

`tile_and_client.md::§6.4`

**The 2000 °C row.** Its deletion is "disable `plume_export` (PH-B1: about 7,300 K)". That figure was round 1's
adiabatic number, with no surface loss. Under D29 every exposed face radiates. Depositing the whole release flux at
the skin settles at **820 °C**, and even 4× settles at 1,297 °C. A cell mean is never above its hottest skin, so the
row stays green with export disabled.

**The `crate_far` row.** Its deletion is "resolve the pilot's region as nearest wood". The nearest wood to
(6000, 2925, 725) is `crate` itself, so this deletion changes nothing.

**Failure scenario.** Both deletion proofs come out "still green". Under the charter, a test that cannot fail is a
BLOCKER.

**Fix.**
- **The 2000 °C row:** delete `open_air_loss` and `plume_export` together. Or replace the cap with a derived bound,
  max skin ≤ T_eq(q''_f + pilot flux) + margin, proved red by disabling 6a.
- **The `crate_far` row:** use a deletion that picks it, such as "the last wood region in the map" or "the region
  farthest from the point".

---

## SHOULD-FIX

### DPH-S1. `plume_export` is the physical split only for the convective part; the radiative remainder is an unreturned sink

`tile_and_client.md::§5.1 plume_export`

The convective plume does leave an open-topped alley, so exporting that part is honest. But "release minus
feedback" also exports the flame's radiation to its surroundings, about 0.3 × 58 kW ≈ 17 kW (radiative fraction
from memory). The north wall is **0.4 m** from the crate. Taking 20–30% of that radiation lands about 4 kW/m² on the
facing wall patch. Over 27,700 s that raises the concrete face by **about 400 K** (semi-infinite, derived), past
`thermal_degrade`'s 250 °C. The model's wall stays at ambient, so the V_floor and wall controls are checked against
a world that is colder than the real one.

**Fix.** Record a Known gap with these numbers: "the flame's radiation to the surroundings is exported, not
received; Phase 2 radiation returns it". Or split the line into `plume_convective` and `flame_radiative_unreceived`,
so the deferral is metered.

### DPH-S2. The ledger equation is missing the pilot and any skin store, and the closed-form test is tautological

`tile_and_client.md::§5.1`, `::§6.4 row 1`

There are three problems with the ledger:
1. **The pilot is missing.** The ledger "release = Δ(cells) + `plume_export` + `open_air_loss` +
   `removed_with_mass` + `bodies`" leaves out the pilot's P·D·0.1 s, so it can't close while the torch burns.
2. **The skin may hold energy.** If 6b's skin carries its own state, the ledger needs a Δ(skins) term. If it
   doesn't, the spec should say the skin is quasi-steady and stores no energy.
3. **The closed-form test proves nothing.** With export defined as release − feedback, "release = feedback +
   export" is an identity and cannot fail.

**Fix.**
- Add `sources` (the pilot) on the input side and Δ(skins) on the storage side.
- Replace the identity with a test of the deposit: Σ deposited to cells = q''_f × A_burning × dt, where A_burning
  comes from the face table independently.

### DPH-S3. V_floor is circular, and destroyed concrete still thresholds a cell mean

`tile_and_client.md::§6.4 row 3`, `::§5.2` ("`thermal_degrade` ... still drives concrete")

**The circularity.** V_floor comes from "step 6's measured contact temperature", which is measured in the same run.
The stated deletion, depositing `plume_export` into the floor, raises that contact temperature, so V_floor grows
with the fault it should catch.

**The cell-mean threshold.** Destroyed concrete comes from `thermal_degrade` on the cell mean, while V_floor comes
from a pointwise 1-D profile. Under a 600 °C contact, the profile passes 250 °C to a depth of 0.176 m in 27,700 s
(2√(αt) = 0.30 m). A 0.2 m cell's mean sits well under its surface temperature, so the control is more lenient on
coarser grids: D25's forbidden case, feeding a gate.

**Fix.**
- Fix the contact temperature before the run, for example at the derived surface equilibrium with the cited q''_f
  (DPH-B1), or at 900 °C as a bound.
- Compute V_floor by applying the same degrade law to the closed-form profile, integrated per cell at each grid. Or
  move the control to a metric: the volume of concrete whose reconstructed skin or profile exceeds X °C.

### DPH-S4. The body's closed form holds only against a held reservoir, and "warms slowly" near the fire is about nil

`tile_and_client.md::§2.1 heat exchange`, `::§9 Q5`

**The closed form.** τ = 12,895 s needs T_env held fixed. In an air box, the exchange volume holds 1.53 kJ/K against
the body's 245 kJ/K. The air reaches the body's temperature in **80 s**, and the body moves 0.6% of the gap. A test
"in a uniform box" without a Dirichlet clamp measures the 80 s mode.

**What heats the body.** Nothing in Phase 1 heats air except conduction: 6a sends the loss to ambient, not to the
neighbouring air. Standing 0.5 m from a 600 °C face, steady air conduction delivers k·ΔT/L ≈ 30 W/m², or **≈ 10 W**
over the facing area, and only after L²/α ≈ 11,000 s. Meanwhile a 37 °C body puts **≈ 418 W** into a 15 °C bubble of
air, which becomes the largest air heat source in the tile.

**Fix.**
- State the two-capacity closed form, or clamp the box.
- Restate the limit as "the body is fire-blind in Phase 1". D28's note then has to choose radiation, or a body that
  doesn't read fire.

### DPH-S5. The rule "0.2 m error ≥ 0.1 m error" fails on converged noise, and "remaining fuel" doesn't define char

`tile_and_client.md::§6.3 items 5, 8`

**The error rule.** Under (a) or 6c, P3 measured all three grids at 0.370. Errors then sit at the level of
quantisation: 0.5 s physics steps, and "first tick ≥ area" crossings. A 0.3% error at 0.2 m against 0.5% at 0.1 m
fails the rule on a converged answer.

**Char.** `t_gone` uses "remaining fuel ≤ 5%". If char (about 20–30% of the mass) isn't fuel, then 1.61 GJ is the
wrong release figure unless char oxidises. If char is fuel, the 5% threshold can't be reached without char
oxidation.

**Fix.**
- Use |e₀.₁| ≤ tol and (|e₀.₂| ≥ |e₀.₁| or |e₀.₁| ≤ tol/4), on absolute errors.
- Define fuel versus char and the ΔH that applies to each.

---

## NIT

### DPH-N1. The cap's ratio is stated against the wrong time

`::§5.3`. By item 5's own criterion, t_gone at β₀ is 19,950 s, not 27,700 s. The cap is then 1.8×, not 1.3×.
Corners char faster, which moves it earlier still.

### DPH-N2. The scale check calls a loss above the release "the same order"

`::§5.1`. Loss at 600 °C over the exposed faces (63.3 kW) exceeds the mean release (58.1 kW) when convection is
included. That shows extinction under (b) (DPH-B1), not consistency.

### DPH-N3. The skin's depth decides explicit stability and is unstated

`::§5.2`. h_r at 1,000 °C is about 420 W/m²K. A skin under about 0.25 mm of wood falls below the 0.5 s step's
stability limit. State its depth in metres.

**Cross-machine:** none new. §2.3 now says one machine, and §6.3 item 9 should add "on one machine" explicitly.
**Cell means:** concrete degrade (DPH-S3) and the `temperature_c` debug channel remain. The second is acceptable
because nothing gates on it.

**Verdict:** the fold fixed the bookkeeping, but the exit is still decided by an unspecified burn driver and an
uncited feedback flux, and two of its controls can't fail, so it is not ready for step 6.
