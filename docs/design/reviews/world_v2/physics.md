# Design review: world v2, Physics and resolution lens

Reader: Physics and resolution. Design: `docs/design/world_v2.md` at `d596418` (draft). Code read:
`.worktrees/act-validation` at `02cd9e3` (`world/{grid,scene,heat,damage}.py`, `sem_env/bridge.py`, the red gates
in `tests/test_act_validation.py` and `tests/test_cross_tier.py`). Sources read: CLAUDE.md, `docs/code_review.md`,
`docs/architecture.md` (Known gaps), `research/states_of_matter/{physics,architecture}.md`,
`research/signals/{world_fields,benchmarking}.md`.

Six throwaway probes were run from the scratchpad (each under a second, except where noted). They are not
committed. Their numbers are quoted below, and each one can be rebuilt from its description:
- `area.py`: exposed face area and volume of centre-voxelized shapes, against the true values;
- `ablate.py` and `ablate2.py`: energy-limited surface ablation of a 0.6 m box on the floor, done per face and
  then with a sub-box reconstruction;
- `pillar.py`: the real `damage.strike` on a 0.4 m concrete pillar, then a 6-connected label to the floor;
- `pilot.py`: face-mean flux of a Gaussian pilot, thermally thick t_ig, and the heat-balance-integral constants;
- `wall.py` and `wall_skin.py`: a 0.4 m concrete wall exposed to an 800 °C zone (h = 25 W/m²K, ε = 0.9), with the
  face flux evaluated at the cell mean, at a half-cell linear reconstruction, and with a fixed-metre skin.

## Summary

The principle in §3.0 is right, and v2 applies it to exactly one law: ignition, through the skin. **Five other laws
in v2 still decide at a cell's mean or a cell's boundary,** where the outcome depends on structure inside the cell.
Four of them are central to the exit test. Each one was measured here, and each has a fix that follows §3.0 and was
shown to work in a probe:

| | Law | Where it decides at the cell | Measured disagreement | The §3.0 fix (measured) |
|---|---|---|---|---|
| **P1** | Cell-to-zone heat exchange (convection, radiation) | evaluated at the cell-mean temperature | wall heat uptake after 1200 s: 104 / 104 / 85 MJ/m² at laptop / rig / max, against 48 converged (2.2× at laptop) | a fixed-metre skin on every exposed face: 47.9 / 48.1 / 48.1 |
| **P2** | Ignition by a pilot | the skin is driven by the face-mean flux, and each face ignites as a whole | a pilot on a shared corner: never at laptop (12.5 kW/m² against about 11.4 kW/m² of losses), 1.5 s at max | an area-overlap deposit plus a sub-face ignited fraction from the flux footprint in metres |
| **P3** | Energy-limited surface ablation | each exposed face removes mass from its cell linearly, so corners and edges empty 3× and 2× too fast | box remaining mass at t = 0.1 L/v: 0.205 / 0.268 / 0.311, exact 0.370; burnout about 35% early at laptop | per-cell sub-box recession: 0.370 / 0.370 / 0.370 |
| **P4** | Support and collapse (§4, `loose`) | 6-connectivity of whole cells after a per-cell damage threshold | a struck 0.4 m pillar falls at laptop at 1/7.5 of the strike energy the continuum needs (1/2.4 at rig, 1/1.7 at max) | decide support on an integral in metres (the intact cross-section, a min cut), with damage evaluated at points |
| **P5** | Rubble, chunks and fines | the fragment size is the cell | specific surface 6/dx (4× more burning and exchange area at max); a 0.2 m concrete chunk is 19 kg, a 5 cm one 0.3 kg; "finer than a cell" is a rig-defined cutoff | a fragment size in metres, carried per volume |

The claim in §2.1, that fluxes "written per m² with no `dx`" can't change an outcome class, is false as stated
(P1). A flux law per m² contains no `dx`, but its driving temperature does, whenever the cell mean stands in for the
surface. The skin is what removes the `dx`, so the skin belongs on every exposed face that exchanges heat, not only
on fuel faces.

The benchmark list (§3.4) wouldn't catch P1 to P5. Each is invisible to a slab, a lumped block or a well-mixed room.
§3.3's outcome-margin rule chooses which scenarios may be tested; it doesn't bound how badly the rigs disagree.
Proposals for both follow.

## BLOCKER

### P1. Surface exchange is evaluated at the cell mean, and the zone energy balance diverges across rigs by 2×

`world_v2.md` §2.1 ("Rig-independent by construction … fluxes … per m² with no `dx`"), §2.2, §3.1; research
architecture §3.2 ("solid-to-zone surface exchange, h·A·(T − T_zone)"); research physics §1 ("heat now crosses faces
into the room by a convective coefficient h").

**Failure scenario.** The vented burn bay heats its gas, and the walls take most of that heat. That heat uptake is
the classic dominant loss in a compartment fire. The exchange is h·(T_zone − T_s) + εσ(T_zone⁴ − T_s⁴), with T_s
the surface temperature. The design gives the cell no surface temperature, so T_s is the cell mean. In concrete
(α ≈ 8×10⁻⁷ m²/s) the heated layer after 20 minutes is √(αt) ≈ 3 cm, thinner than every rig's cell. A coarse
cell's mean therefore stays cold, and the wall keeps absorbing at nearly the full cold-wall flux. Measured
(`wall.py`, 0.4 m concrete, 800 °C zone):

| after | method | 0.2 m | 0.1 m | 0.05 m | 0.0125 m | 0.003125 m |
|---|---|---|---|---|---|---|
| 300 s | flux at the cell mean | 26.0 MJ/m² | 26.0 | 26.0 | 21.6 | 18.9 |
| 300 s | half-cell linear reconstruction, T_s = T_c + q·dx/2k (research architecture §5's proposal) | 3.7 | 7.0 | 12.1 | 17.6 | 17.9 |
| 1200 s | flux at the cell mean | 104.2 | 104.2 | 84.7 | 53.8 | 48.2 |
| 1200 s | half-cell linear reconstruction | 14.9 | 28.0 | 41.7 | 46.3 | 46.5 |
| 300 / 1200 s | **fixed-metre skin** (16 nodes over the first 5 cm, then the rig's cells; `wall_skin.py`) | **18.9 / 47.9** | **18.9 / 48.1** | **18.9 / 48.1** | | |

Taken at the cell mean, laptop's walls absorb 2.2× the converged heat, so its zone gas runs colder. The linear
reconstruction errs the other way, by 3× at laptop, because a linear profile across a 0.2 m cell isn't the erfc
profile of a 3 cm skin. Only a reconstruction sized in metres converges. Zone gas temperature then feeds
everything downstream: wall and crate surfaces, flame spread (§3.1 has no flame zone yet, so spread is driven by
zone gas alone), the NPCs' "heat on skin" cue (§9), steam from bound water (§2.5), and the Overdrive heat-debt loop
(§10). That is an outcome-class split on the exit test's vented bay.

**Fix (follows §3.0).** Extend the surface skin from "per exposed fuel face" to **every exposed solid face that
exchanges heat with a zone**. Every flux between a face and a zone (convection, radiation, flame feedback,
extinguishing water, evaporation, steam) is evaluated at the skin's surface temperature. The skin's energy is part
of its cell's energy, never a second store: the cell's mean is the integral of the skin plus the rest of the cell.
Both the probe and FDS do it this way (FDS's 1-D solid mesh is independent of the gas mesh).
- Use a fixed-metre 1-D subgrid, which the probe shows converging to 0.4% at every rig, not a two-parameter
  heat-balance integral (see S6).
- **Cost:** at max the tile has about 200 k exposed faces, so 16 nodes each is about 3.4 M node updates per skin
  step, comparable to a heat substep.
- **The cheaper option, which also holds the rule by construction:** keep skins on a fixed 0.2 m face lattice at
  every rig (about 13 k skins per tile), area-weighted onto the fine faces. That is "each consumer reads at its own
  scale" applied to the surface.

Decide between the two before `phase1/zones` (PR 6), because "air out of the conduction solve" lands there.

**Benchmark to add:** a semi-infinite solid with a convective boundary. The closed form is Carslaw and Jaeger's
erfc(η) − exp(Bi + Bi²τ)·erfc(η + √τ·…) (*from memory*; derive and pin it), the same at every rig. Add a radiative
variant, judged by the energy absorbed per m² at 300 and 1200 s, gated cross-tier at a few per cent.

### P2. Pilot ignition decides per face, on the face-mean flux, and flips the outcome class with the pilot's placement

§3.1 ("Surface ignition … per exposed fuel face … ignite when the surface temperature reaches T_ig"); research
physics §7 step 3 ("`ignite` becomes a pilot with a finite energy … deposited by overlap").

**Two problems.**
1. **A pilot deposited by volume overlap heats a volume, and the skin needs a flux per m².** As written, a volumetric
   pilot never drives the skin. The deposit rule has to be extended: a surface source is deposited by **area
   overlap on the exposed faces**, in W/m².
2. **Even then, the skin sees the face-average flux, and t_ig ∝ 1/q″² is strongly non-linear.** This is exactly
   averaging before deciding. Measured (`pilot.py`): a 2 kW pilot with σ = 5 cm (peak 127 kW/m², t_ig at the peak
   0.81 s), wood from `data/materials/core.yaml` (kρc = 1.53×10⁵):

| cell | centred on a face: face-mean flux, t_ig | on a corner shared by four faces: face-mean flux, t_ig |
|---|---|---|
| 0.2 m | 45.6 kW/m², 6.3 s | **12.5 kW/m², 84 s without losses; with the about 11.4 kW/m² of re-radiation and convection at 350 °C, never** |
| 0.1 m | 93.2 kW/m², 1.5 s | 45.6 kW/m², 6.3 s |
| 0.05 m | 117.3 kW/m², 0.95 s | 93.2 kW/m², 1.5 s |

So the same lighter at the same point lights the crate in 1.5 s at max and never at laptop. The pilot's position
relative to the grid, which no player controls, decides it.

**Fix (§3.0).** Reconstruct the flux footprint in metres; the pilot's profile is analytic. Each face then holds an
**ignited area fraction**, the measure of {x on the face : the skin at flux q(x) has reached T_ig}. Computing it
needs only the skin's response at a few flux levels per face, or the closed form for a constant-flux thermally thick
skin.
- The burning area is Σ fraction × dx², and pyrolysis and flame feedback scale with it.
- Add a minimum pilot size in metres (the "a source smaller than a cell heats one cell" gap is the volumetric twin
  of this).
- Losses in the skin are mandatory (S6), or every positive flux eventually ignites.

**Benchmarks to add:**
- **Pilot translation invariance:** the same pilot shifted by ¼, ½ and ¾ of a coarse cell must give the same t_ig
  and ignited area within a stated tolerance at every rig.
- **The critical heat flux:** below it, no ignition at any rig; above it, ignition at every rig.

### P3. Per-face ablation empties corner and edge cells 3× and 2× too fast, and the box burns out early at coarse rigs

§3.1 (pyrolysis "energy-limited at the surface"), §3.4 ("Steady planar ablation: exact for boxes").

B-5 is exact for a **slab**. A box isn't a slab. A cell exposed on k faces loses mass at k·q″·dx²/(L_g + …) at a
constant rate, but the true remaining volume of a corner region eroded from three sides is (dx − vt)³, which
shrinks at a falling rate. Corner and edge cells empty early. The staircase this leaves keeps its full face area
while the true shape's area shrinks, so the error compounds. Measured (`ablate.py`, a 0.6 m box on the floor burning
on five faces, recession speed v, the exact remaining fraction (L − 2vt)²(L − vt)/L³):

| t (units of L/v · 0.6) | exact | 0.2 m | 0.1 m | 0.05 m | 0.025 m |
|---|---|---|---|---|---|
| 0.05 | 0.637 | 0.567 | 0.588 | 0.598 | 0.617 |
| 0.10 | 0.370 | **0.205** | 0.268 | 0.311 | 0.339 |
| 0.15 | 0.188 | **0.027** | 0.078 | 0.122 | 0.151 |
| 0.20 | 0.074 | 0.000 | 0.004 | 0.022 | 0.041 |

The convergence is first order. Laptop burns the box out at about 0.19 against an exact 0.30, which is 35% early.
This is the exit test's "burns its fuel away", with the burnout turn off by a third at laptop. It also perturbs
every downstream integral (O₂ use, HRR history).

**Fix (§3.0, measured).** Reconstruct each surface cell's remaining solid as a **sub-box**: one recession depth per
axis, advanced by the faces exposed on that axis; the mass fraction is Π(1 − r_a/dx), and the exposed area shrinks
with the sub-box. `ablate2.py`: **0.624 / 0.637 / 0.637, then 0.370 / 0.370 / 0.370, then 0.182 / 0.187 / 0.188**
against exact 0.637 / 0.370 / 0.188. Burnout is exact at every rig. It costs three f32 per surface cell, only on the
active mask.
- For curved or staircase fuel it is no longer exact, which is one more reason for S3's "box-aligned fuel in
  Phase 1".
- **Replace B-5's slab with the whole box burning on five faces**, against the closed form above, at every rig.

### P4. Support and collapse decided by connectivity of whole cells: a pillar falls at laptop at 1/7.5 of the energy

§3.2 ("A cell becomes loose when it loses its connection to support"), §4 ("Connectivity … `ndimage.label` on
solids against anchored support"), §3.3 (only `breached` is named as a flip risk).

**Measured with the shipped `damage.strike`** (`pillar.py`). A 0.4 m × 0.4 m × 2 m concrete pillar is two coarse
cells wide, so it satisfies the thin-features rule. It is struck at mid-height on one side (σ = 0.15 m), with the
energy set so the continuum crater radius R is as listed. Then a 6-connected label asks whether the top is still
attached to the floor. In the continuum the pillar is cut only when R ≥ √(0.4² + 0.2²) = 0.447 m.

| R (m) | 0.30 | 0.33 | 0.36 | 0.38 | 0.40 | 0.42 | 0.44 | 0.45 |
|---|---|---|---|---|---|---|---|---|
| exact | held | held | held | held | held | held | held | falls |
| laptop | held | **falls** | falls | falls | falls | falls | falls | falls |
| rig | held | held | held | held | **falls** | falls | falls | falls |
| max | held | held | held | held | held | **falls** | falls | falls |

E ∝ exp(R²/2σ²), so laptop drops the pillar at **1/7.5** of the strike energy the continuum needs, rig at 1/2.4
and max at 1/1.7. The band is a factor, not a margin. It is the same mechanism as PR 1's breach red gate (a
threshold on whole cells, then topology), with a far more visible consequence: half a pillar turns to rubble and
falls on one rig and stands on another. §3.3 and §12 name `breached` but not `loose` or collapse. The outcome-margin
rule can't hold this, because a margin can only choose scenarios away from the band, and a player's strike lands
anywhere.

**Fix (§3.0).**
1. **Evaluate damage at points, then integrate.** Each cell holds the damaged volume fraction, the measure of
   {x in the cell : the point energy density ≥ fracture}, computed in closed form per axis for a Gaussian strike,
   just as the deposit already is. Never `clip(cell mean / fracture)`.
2. **Decide support on an integral in metres:** the intact load path's cross-section, as a **min cut** on the face
   graph with capacity = intact area fraction × dx², against a declared minimum ligament area in m² per material.
   - A min-cut value is an integral, so it converges.
   - Run it per event on the affected cluster's bounding region, or on the fixed 0.2 m topo grid that research
     architecture §1.6 already proposes for pockets, so the decision is the same at every rig by construction.
   - A connectivity label on whole cells may still find the clusters once support is decided, but it must not
     decide support itself.
3. **Add a ligament benchmark:** this pillar at R = 0.30 / 0.40 / 0.44 / 0.46 must hold, hold, hold and fall at
   every rig.

Until then, record collapse as a known gap with these numbers and a strict red gate. The tile shouldn't contain a
pillar a player can cut.

### P5. Rubble's scale is the cell, so its area, its chunks and its fines all depend on the rig

§4 ("A fragment can't be smaller than a cell", "Fines go to the zone. Mass finer than any cell", "a chunk is a real
thing, an entity an NPC can perceive and use").

- **Area.** Rubble is porous and gas flows through it (§4), so the faces between loose cells are exposed. Specific
  surface is then 6(1 − ε)/dx per m³: **4× more burning, pyrolysis and convective area per m³ of rubble at max than
  at laptop.** A burning rubble pile burns about 4× faster at max. Judging outcomes by volume doesn't help, because
  the rate is the problem.
- **Chunks as entities.** A 0.2 m concrete chunk is 19.2 kg and a 5 cm chunk 0.3 kg. "Can I pick this up or throw
  it" is an outcome class handed to Maxim (§4, §7 N1 `matter`), and it flips by rig. (A Bio lens issue too: an NPC's
  grounded concept of "rubble" would differ by rig.)
- **Fines.** "Finer than any cell" is a cutoff set by the rig, so the zone's dust loading is rig-dependent. It is
  also undefined which mechanism produces sub-cell mass at all.

**Fix.** Give fracture a **fragment size in metres**: a per-material constant, or a function of the strike's energy
density evaluated at points (a Grady-type relation, *to be sourced*). Carry it per volume (a `fragment_m` field on
loose cells).
- Burning and exchange area come from a_s = 6(1 − ε)/d_frag, not from faces.
- Fines are the declared mass fraction below a fixed size in metres (for example 1 mm).
- SEM `matter` entities are built from fragment size and cluster volume, not from cells.
- Then the client's grouping stays purely visual, as §4 intends, and the snapshot carries `fragment_m` along with
  `loose`.

## SHOULD-FIX

### S1. `breached` (and any strength threshold) is decided at the cell, where a line integral in metres converges

§3.2 ("strength follows the remaining solid mass fraction"), research physics §3 ("`breached` stays a connectivity
test on cells with strength below ½").

A 0.4 m wall ablated uniformly from one face to depth d has a partial surface cell with strength (1 − frac) on top
of fully consumed cells. "Strength < ½ in every cell of a line" fires when d > 0.4 − dx/2: **at 0.30 / 0.35 /
0.375 m at laptop / rig / max**, against a true burn-through at 0.40 m. Time to breach is 25% early at laptop. That
is a pure threshold-on-the-mean effect, with no topology involved. **Fix:** breach when the remaining thickness along
the wall's normal, Σ (strength or mass fraction) × dx over the line in metres, falls below a declared thickness in
metres (0 for burn-through, larger for "too weak to hold"). It is an integral, and with P3's sub-box it is exact for
planar ablation. It also gives `breached` a continuous decisive value for §3.3's margin.

### S2. Energy-limited pyrolysis reads T_bulk from the cell mean, and its volumetric branch is a cell-mean threshold

§3.1 ("ṁ″ = q″_net / (L_g + c·(T_p − T_bulk)); volumetric when a cell's bulk passes the pyrolysis point").

- **The volumetric branch fires on the cell mean.** That is §3.0's forbidden case: the measured ignition probe has
  a surface cell's mean reaching 350 °C at t ∝ dx (1350 s at 0.2 m, 340 s at 0.05 m). With the volumetric branch,
  max starts gasifying the whole surface cell about 1000 s before laptop.
- **T_bulk is ambiguous and double-counts.** If q″_net also enters the cell's enthalpy through conduction, the
  sensible term c·(T_p − T_bulk) is paid twice. If it doesn't, nothing preheats the solid. At the cell mean,
  1/(L_g + cΔT) varies by up to (1.8 + 0.48)/1.8 ≈ 1.27 between a cold coarse cell and a preheated fine one (wood,
  L_g *from memory*).

**Fix:** one energy path.
1. The face flux enters the skin (P1).
2. Gasification happens where the skin's surface reaches T_p, at L_g only, with conduction into the solid resolved
   by the skin.
3. "Volumetric" is triggered by a declared thermal thickness in metres (a primitive thinner than about
   2√(α·t_burn)), never by a cell's bulk temperature.

The steady-ablation closed form then holds for the right reason: conduction ahead of the front is resolved.

### S3. Centre voxelization makes fuel mass and fuel area rig-dependent, and v2 dropped the research's known gap

`scene.py` assigns a cell to a primitive when its centre is inside. Measured (`area.py`):

| shape | 0.2 m: V and A ratio | 0.1 m | 0.05 m | fine limit |
|---|---|---|---|---|
| sphere r = 0.3 m (two sub-cell offsets) | V 0.57–0.78, A 0.85–1.27 | V 0.93–1.20, A 1.38–1.70 | V ≈ 1.0, A 1.485 | A → 1.50 (verifies the research's "about 1.5×, from memory") |
| cylinder r = 0.3, h = 0.6 | V 0.38–1.13, A 0.57–1.23 | V 0.99–1.13, A 1.18–1.23 | V ≈ 1.0, A 1.18 | lateral → 4/π |
| a 0.6 m box off the 0.2 m grid | V 0.30 or 1.0, by offset | V 0.58 or 1.0 | 1.0 | exact |

With HRR ∝ exposed area and burn duration ∝ fuel mass, a cylindrical fuel's fire differs by up to 2× in power and
3× in fuel between laptop and max. Research physics §1 required "record the choice as a known gap"; v2 doesn't say.

**Fix:**
1. v2 adds a fuel-mass field. Initialize it by **exact volume overlap** (per-axis closed forms for boxes, quadrature
   for cylinders), not by centres. Then the fuel budget is exact at every rig.
2. In Phase 1, the scene loader **refuses fuel primitives that aren't boxes aligned to the 0.2 m grid**. Today it
   accepts the `test_act_validation.py:714` crate at 1.25 m.
3. Record the non-box area gap with the table above.

The zone volume suffers the same centre voxelization, but only at O(dx·area / V), which is small for rooms.
"Rig-independent by construction" (§2.1) is true for aligned geometry and first order otherwise; say so.

### S4. The outcome-margin rule chooses tests; it doesn't bound the band, and a three-rig spread isn't an error bound

§3.3, Q3.

- **It is a test-selection rule.** "A decisive value at least 2× its cross-rig spread from its threshold" is a
  rule for which scenarios may be canonical. In play, strikes and pilots land anywhere, so the band in P2 and P4 is
  what players meet.
- **The spread isn't an error bound.** It is measured on three grids, one of which is often pre-asymptotic (the
  crate's 0.55 / 0.37 / 0.38 is oscillatory per Celik). 2× of that isn't a safety factor in any V&V sense: GCI uses
  Fs = 1.25 with three grids in the asymptotic range, and 3 with two grids.

**Proposal for Q3.** Keep the margin rule for canonical tests, and add a **band gate**: for each binary outcome
(ignited, breached, fell, starved, burned away), measure the band of the controlling input (strike energy, pilot
power and offset, vent area, fuel mass) inside which the rigs disagree, and gate its width at a declared fraction of
the threshold (for example ±10%). The band is in physical input units, so the rule says what a player can
experience.
- P4 fails it today (7.5×), P2 fails it (never versus 1.5 s), and P1 to P3 shift the bands of starved and burned
  away.
- An outcome may be declared non-gated only as a known gap with its band recorded.
- The margin itself should also be stated in input units (how far the scenario's strike energy sits from the
  threshold energy), not output units.

### S5. Flame feedback is fixed per m², but nothing ties it to combustion that is actually happening

§3.1 ("Flame feedback … a fixed flux per m²"). Per-m² rather than a fraction of the HRR is right, since it bounds
the loop gain. But the zone burns fuel vapour at min(supply, O₂ limit) with an extinction ramp. If the faces keep
"burning" (receiving 25–35 kW/m²) while the zone starves, pyrolysis keeps gasifying a sealed crate with no heat
release to pay for it. That fails the ledger, and the sealed fire never "goes out" in the solid.

**Fix:** q″_f × (the zone's extinction factor f(X_O₂)). The face's flame flux is debited from the HRR in the
ledger, and capped by it (the min of the two). Pin both in B-6, which must show pyrolysis stopping, not only HRR.

### S6. Skin model details: the quadratic profile is 15% early, there are no losses, and moisture is missing

§3.1, §3.4 ("Thermally thick ignition: the same time at every cell size").

- **Verified by derivation (`pilot.py`):** a quadratic heat-balance-integral profile gives t_ig/t_exact = 0.849
  (15% early) and a cubic 0.955 (4.5% early). The research's "about 10–15% for quadratic, from memory" is the upper
  end. t_ig = (π/4)·kρc·ΔT²/q″² is correct (it follows from T_s = 2q″√(αt/π)/k). With the shipped wood it gives
  5.2 s at 50 kW/m², matching the design.
- **The benchmark is necessary but not sufficient.** "The same time at every cell size" is satisfied by any skin
  that ignores the cell, including a wrong one. Pin the absolute time against erfc (research physics B-4 says so;
  v2's §3.4 dropped "pins the constant").
- **Losses are missing.** Include re-radiation and convection at the skin's surface temperature. Without them there
  is no critical heat flux: any positive flux eventually ignites, which is a wrong outcome class that no cross-tier
  test catches. From the loss estimate, CHF ≈ 11 kW/m² for T_ig = 350 °C (literature about 10–13 kW/m², *from
  memory*).
- **Moisture is missing.** Wood's moisture is a latent sink in the skin that delays ignition. Either model it in the
  skin, or declare dry fuel in Phase 1.
- P1's fixed-metre subgrid removes the profile-constant question entirely, and the same skin then serves P1, P2 and
  S2.

### S7. Zone exchange: the operator as written isn't conservative, and a symmetric exchange isn't a vent

§2.2 ("one implicit step on the zone graph … conservative"); research architecture §3.5:
"(I + dt·V⁻¹L) m′ = m".

- **The operator.** With m the masses and the flux Q_ij·(c_i − c_j) on concentrations c = m/V, the system is
  dm/dt = −L·V⁻¹·m. Conservation needs 1ᵀ·L·V⁻¹ = 0, which holds because L has zero column sums. The written
  (I + dt·V⁻¹L) conserves only for equal volumes. Write the operator explicitly in the design as
  (I + dt·L·V⁻¹) m′ = m. The ledger test would catch the other form, but it costs a debug cycle.
- **A vent isn't diffusion.** A symmetric exchange coefficient × area is diffusion between zones. Kawagoe inflow
  (ṁ ≈ 0.5·A√H kg/s) and the isobaric expansion outflow are directional and buoyancy-driven. They need an advective
  term (inflow of ambient at the bottom of the opening, outflow of zone gas), upwinded, which the implicit step
  handles if L is built from the directed flows.
- **B-8 should be a closed form, not "an outcome".** HRR_max ≈ 1.5 MW·A√H is the steady state of the vent model,
  and it is internally consistent (0.5 × 0.233 × 13.1 MJ/kg O₂ = 1.53 MW·m^-5/2). Gate it within a stated
  tolerance at every rig, with the opening authored and aligned.
- **√H of a breach hole** should come from the z-binned gap area (research architecture's 0.2 m bins), which is the
  same at every rig if the area converges.

### S8. Breach holes as vents, and `temperature_max`: two consumers that still read cells

- **Breach holes.** Gap area for a breach hole is a face count × dx². For a crater-sized hole it is quantized in
  0.04 m² steps at laptop (a 0.3 m diameter hole, 0.07 m² true, is 0 to 0.16 m² by offset), and the vent flow scales
  with A√H. Until P4's point-wise damage and S1's thickness rule give a reconstructed open area, keep the exit test's
  vents authored and aligned, and record breach venting as a known gap with these numbers.
- **`temperature_max`.** `RegionSensor`'s `temperature_max` (`sem_env/bridge.py`) is a max of cell means, so it is
  hotter at finer rigs wherever there is a gradient. §2.4 caches the region reductions but doesn't define their
  scale. Define each sensor as a reduction in metres: the max over a fixed 0.2 m averaging window, or the skin
  surface temperature for "how hot is the surface". CLAUDE.md now says no consumer reads "a cell".

### S9. Sealed-room numbers: 1.1 kg at 15%, about 2.0 kg at the design's 10%, and "goes out" needs a definition

§1, §3.5. Recomputed in moles (14.18 m³ of air at 20 °C is 589.6 mol, 123.5 mol O₂ = 3.95 kg ✓). For CH₁.₇O₀.₇₂
(*formula from memory*) with water as vapour, X_O₂ reaches 0.15 after 1.01 kg of O₂ (13.2 MJ, 1.07 kg of volatiles
at 12.4 MJ/kg). It reaches the design's own ramp floor of 0.10 after 1.92 kg of O₂ (25 MJ, 2.0 kg).
- So §1's "about 1.2 kg" uses 15% as extinction, while §3.1's ramp keeps burning, more slowly, down to 10%. Neither
  number changes the conclusion (sealed ≪ 130 kg).
- **"Goes out" needs a definition.** With a linear ramp the approach to 10% is exponential (research B-6), so the
  fire never goes out in finite time. Define "out" as HRR below a declared W per m³ of zone for a declared time.
  That is a binary outcome, so it belongs under S4's band gate.
- **"Within a few turns" depends on the burning area.** At about 200 kW/m², one face of the crate (0.36 m², 72 kW)
  takes 180 s for 13 MJ; five faces take about 37 s. Give the scenario's burning area and HRR when the number is
  quoted.

### S10. Settling by angle of repose needs continuous heights, and a closed form

§4 ("an angle of repose, with a pile's height and footprint set by its volume").
- **The quantization problem.** At 0.2 m with tan 35° ≈ 0.70 (concrete rubble angles 35–40°, *from memory*), the
  allowed height step between neighbouring columns is 0.14 m, less than one cell. Any one-cell step violates it, so
  a cellular relaxation on whole cells flattens every pile at laptop and keeps slopes at max. To be in metres, the
  rule must run on a 2-D height field per floor patch, with continuous column heights (a partially filled top cell
  through the packing fraction), and only then be voxelized by volume overlap.
- **No numbers yet.** The design gives no angle of repose or packing fraction (random loose packing is about
  0.55–0.6, *from memory*).
- **Benchmark to add:** a cone of volume V on a flat floor, h = (3V·tan²θ/π)^{1/3}, with the height and footprint
  radius the same at every rig to a stated tolerance.

## NIT

- **§2.3's premise contradicts §3.1.** "A solid cell only ever holds its solid phase, so enthalpy factors exactly"
  is contradicted by §3.1's melting plateau in the cell (a mushy, part-liquid cell). The factoring is still exact:
  (T, progress) is a bijection with H given the plateau. But state that the update is done in enthalpy form
  (ΔH = dt·div F + q, then invert), not as a temperature step plus a "latent correction" that can overshoot the
  plateau. The ledger test would catch the latter.
- **f32 progress.** f32 progress against a 1e-10 ledger: for steel at max, ρL·V_cell ≈ 2.6×10⁵ J, and one f32 ulp
  near 0.5 is about 0.015 J per cell per update. Apply research architecture's "credit what the storage actually
  lost" rule to progress and fuel mass explicitly in §2.6.
- **Thin features are also created dynamically.** The thin-features rule covers authored geometry, but ablation and
  craters create sub-coarse ligaments as play goes on. Say in §12 that dynamic thinness is held by S1 and P4's
  integral rules, not by the authoring rule.
- **The deposit rule needs a surface case.** CLAUDE.md's deposit rule ("cell average or volume overlap") needs a
  surface clause ("area overlap on exposed faces, for a flux") once P2 lands.

## Numbers the design relies on that are from memory

Verified here, by derivation or measurement:
- t_ig = (π/4)kρcΔT²/q″², and 5.2 s at 50 kW/m² with the shipped wood;
- about 1350 s for the 0.2 m cell mean to reach 350 °C (lumped ρc·dx·ΔT/q = 1346 s);
- the heat-balance-integral constants (quadratic 0.849, cubic 0.955);
- the voxel sphere's area limit (1.485–1.499, at 0.05, 0.025 and 0.0125 m);
- the internal consistency of Kawagoe's 0.5 A√H with 1.5 MW·A√H;
- the sealed-room O₂ mass (3.95 kg).

**Still from memory, and must be sourced before `data/`:**

| Number | Used for |
|---|---|
| L_g 1.5–2 MJ/kg, T_p 300–350 °C, T_ig 350 °C | wood pyrolysis and ignition |
| flame feedback q″_f 25–35 kW/m² | §3.1 |
| Tewarson's yields (1.27 / 0.004 / 0.015) and ΔH_c,eff 12.4 MJ/kg | products |
| the pyrolysate formula CH₁.₇O₀.₇₂ | the atom balance |
| Kawagoe's coefficients themselves | the vent |
| extinction at 10% and 15% (conflicting sources) | the ramp |
| steel T_m and L | melting |
| Eurocode 3 k_y,θ | σ(T) |
| char strength ≈ 0.1 | strength by mass fraction |
| wood's critical heat flux (about 10–13 kW/m²) | S6 |
| Carslaw and Jaeger's convective closed form | P1's benchmark |
| angle of repose and packing fraction | §4, which gives none |
| a fragment-size relation | P5, which has none |
| dry-ice and two-phase Neumann data | research only |

## Where the rigs will still disagree, and how to gate it honestly

Even with every fix above, these keep a band, because they are binary decisions at a front:
1. **Ignition onset and the ignited area near the critical heat flux.** The skin makes t_ig the same, but the
   per-face area fraction has an O(dx) edge.
2. **Collapse near the minimum ligament area.** A min cut converges at first order.
3. **Burn-through, and `breached`, of a non-planar or staircase fuel.**
4. **"Goes out" and "burned away", near their declared thresholds.**
5. **Anything downstream of breach-hole venting,** until the hole's area is reconstructed.
6. **The late burn on curved fuel** (S3), unless Phase 1 refuses it.

**The honest gate.** S4's band gate in input units, per binary outcome, measured by sweeping the controlling input
across its threshold at each rig. It is recorded in the results file, as `benchmarking.md` L4 proposes, and gated
on width.
- Where the band can't be met yet, a strict red gate holds it, and Known gaps gets the band's width as a number.
  P4's 7.5× would be such a gap today.
- **The exit test (Q1)** should be gated only at laptop and rig, as the design says, with authored, aligned vents,
  box-aligned fuel and no cuttable supports in the two rooms.

**Additions to the §3.4 minimum set:**
- the whole box burning on five faces (replacing the slab, P3);
- wall heat uptake from a hot zone (P1);
- pilot translation invariance and the critical heat flux (P2, S6);
- the struck pillar's ligament (P4);
- planar burn-through measured as a thickness (S1);
- a closed-form vent (S7);
- the repose cone (S10).

Each costs well under a second on small grids.

## What I checked and found sound

- **§3.0's principle,** and its adoption as the fuel model's acceptance test (flip the red gate at the coarsest rig,
  not "converges eventually").
- **Zones authored in metres and aligned to the 0.2 m grid.** Grid origins are 0 and the rigs nest exactly (2× and
  4×), and the centre test assigns aligned boxes exactly at every rig (half a cell of margin), so aligned zone
  volumes and aligned authored gaps are exact by construction.
- **The zone-graph exchange per physics step.** It runs on the same dt at every rig, so it adds no rig dependence
  of its own, apart from S7's operator.
- **No gas in cells, and no per-cell phase tag.** Both remove thresholds rather than add them.
- **Energy-limited ablation** is exact for a planar slab at every rig. With P3's sub-box it is exact for boxes.
- **Flame feedback as a flux per m², never a fraction of the HRR.** That bounds the loop gain (with S5's coupling).
- **Strength by mass fraction,** as a region-mean sensor: a linear functional, so it converges. The decisions taken
  on it are the problem (S1, P4).
- **The ledger:** donor-limited antisymmetric transfers, no clamping, f64 for H and zone inventories.
- **Temperature plus progress against enthalpy.** They are equivalent given the plateau, and the 1e-12 L1 regression
  against today's heat tests is a good guard.
- **An envelope gate (error ≤ C·dx) for Neumann melting,** not a pairwise order band. That is right for enthalpy
  methods.
- **The sealed-crate conclusion** (it chars and starves, and can't burn away), and the measured diagnosis of today's
  divergence (a threshold on the cell mean, t ∝ dx).
- **Huggett's 13.1 MJ/kg O₂,** verified in the research, with a ±10% shipped-table test.
- **Outcomes judged by volume rather than fragment count.** Correct, but P5 shows it isn't enough.
