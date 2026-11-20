# Ladder research 3: material state transitions and the data model (2026-11-20)

Lens: how pyrolysis, charring, melting and dripping, evaporation, smouldering and burnout fit the world model, and
what the material table must carry for R0–R4. Research only; no repository file was changed.

Tags: **V** I read it in the primary source (section given); **S** secondhand (search summaries, reviews);
**M** from memory; **D** derived by me. Repo claims are cited as `file::section`. Sources read: FDS 6.11.2 Technical
Reference Guide (TRG) and User's Guide (UG), downloaded from the `FDS-6.11.2` GitHub release; Joseph &
Tretsiakova-McNally, *Materials* 8 (2015) 8793 (melt-flow review). Gpyro and ThermaKin full texts could not be
fetched (an HTML wall, a 503), so everything about them is S or M.

## 0. The answer, first

1. **Every ladder fuel is thinner than a cell.** A stick (~20 mm), cardboard (~3–5 mm), a slat (20 mm), a wax-sawdust
   starter and a PMMA sheet are all below 0.1 m (M for the typical sizes). CLAUDE.md's thin-features rule asks for
   ≥ 2 cells of 0.2 m, which is 0.4 m. **None of R0–R4's fuels can be cells.** They have to be sub-cell fuel
   *elements* with their geometry in metres, as FDS does for anything it can't resolve (vegetation particles, the
   boundary fuel model; UG §17.3, TRG §9.1.1, V). D30's porous bed already does this for the crate, with one element
   per cell and nothing to say so.
2. **R3 breaks "one material per cell."** A starter touching a stick will often share a cell with it. So the
   smallest model that carries R0–R4 is **a dense cell grid for resolved structure, plus a sparse element table
   keyed (cell, slot)**. Each element has its own material, region, geometry, component inventories and surface
   state. This refines world_model §5's one-owner rule; it doesn't throw it out.
3. **Transitions are inventory moves between components, never a material swap on a cell.** Virgin → char → ash, and
   solid wax → liquid wax, move kilograms between component inventories on an element. Volatiles, moisture vapour and
   evaporated loading leave as gas species. Melt beyond what the pores retain is free liquid. That is FDS's
   formulation (TRG §7.2.3, eqs 7.33–7.37, V), and it makes the per-cell `latent` scalar redundant.
4. **Dripping is out of reach for the ladder as the world model stands.** Free liquid lives in a per-zone pool with
   no position (`world_model.md::§2`). A drip spread over a whole zone's floor can't make the pool fire under an
   object, which is the very mechanism that makes dripping matter (Joseph 2015 §1, V). Either defer dripping and pick
   ladder materials and orientations that don't depend on it, or bring Phase 2's positioned puddles forward.
   I recommend deferring it.
5. **"PMMA melts" is a wrong premise.** PMMA is amorphous: it has no melting point and softens above T_g ≈ 105 °C
   (M). In furnace tests its "volatilisation occurred prior to the melt dripping stage", and it burned to zero
   residue in UL-94-type tests (Joseph 2015 §3, V). For R2 it is the classic *non-charring, regressing* solid, not a
   melting one. If the ladder needs a real dripper, that's PP or PE (first drip at 12–14 s against 61–62 s for
   PMMA, 2 mm samples, Wang et al. via Joseph 2015 §3, S).

## 1. How real fire codes represent the condensed phase

**FDS (V, TRG ch. 7, App. P; UG §8.3.8, §9.3).**
- **Geometry.** Each wall cell carries a **1-D in-depth grid normal to the surface**: a stack of **layers** in
  metres, each a **mixture of components** by mass fraction, with volume-averaged k and summed ρc; volume fractions
  needn't sum to 1, which is how porosity enters (UG §8.3.8; TRG §7.1.3, eqs 7.25–7.28, §7.2.3 fn 3).
- **Reactions.** Up to 10 per component (UG §9.3.1), r = ρ^n·A·e^(−E/RT)·X_O₂^n·T^n (TRG eq 7.34), yielding
  **solid residues** (NU_MATL), **gas species** (NU_SPEC) and **particles** (NU_PART: "for example, melting or brand
  formation", App. P). Gas leaves instantly (§7.2.3). REFERENCE_TEMPERATURE (peak mass-loss T) may stand in for A
  and E (UG §9.3.3).
- **Mass rule.** Yields summing above 1 are an **error**. Below 1 is only a warning, "lost mass" (App. P.1). We should
  be stricter, because world_model §2 says mass is never silently deleted.
- **Energy.** FDS solves **reference enthalpies of every solid component** so each heat of reaction is
  Hess-consistent (App. P.2): a conservation check we lack.
- **Liquids.** A pool is **a thermally thick solid** that evaporates by Clausius–Clapeyron and Raoult (§7.2.4).
- **Shrinking.** Node sizes scale by Σρ_s,α/ρ_α, densities divided to conserve mass (§7.2.5). **Recession is a
  layer thinning, not cells disappearing.**
- **Burn-away.** A coarse cell goes when its BULK_DENSITY mass is gone, "a specific fuel mass per unit volume that is
  independent of the grid resolution", conduction 1-D (UG §9.3.9). **Mass per volume in the coarse cell, structure on
  a 1-D surface grid in metres.**
- **Vegetation.** Sub-grid fuel is described by **packing ratio β, surface-to-volume σ, moisture and thickness**.
  Absorption is κ = C_s σβ, and convection enters as a volumetric source σβq''_c (UG §17.3, eqs 17.41–17.43). This is
  D30's fuel bed, almost term for term.

**Gpyro (S):** arbitrary condensed and gas species and reactions, porosity and permeability per species, Darcy
volatile flow, mass-conserving swelling (Lautenberger & Fernandez-Pello 2009). **ThermaKin (S):** a reacting mixture
of components with a swelling factor and in-solid gas transport (Stoliarov & Lyon 2008, *FSS* 9:1141).
**Wildland:** particles, a boundary fuel layer, or an empirical level set (UG §17, V); Rothermel inputs are σ and β
(TRG §13, V). None represents a fuel element as cells.

**What a game can take:**
1. Components and reactions as **data**, with residues and yields and a refused mass excess.
2. **Geometry in metres on a surface sub-model**, never cells.
3. A **threshold-or-Arrhenius** choice per reaction: FDS itself lets REFERENCE_TEMPERATURE stand in for A and E.
4. Shrinkage as a thickness state.
5. **Enthalpy consistency solved or checked at load**, as App. P does.

**What to leave:** in-solid gas transport, permeability and in-depth radiation, needed for intumescents and
composites the ladder lacks (D).

## 2. Mapping each transition onto the world model

### 2.1 The containers

| Container | Holds | Status |
|---|---|---|
| **Cell** (dense, 0.1 m) | structural owner material, region id, temperature, integrity | as today (`gates/src/simcore/core/grid.py::CellStore`) |
| **Element** (sparse, keyed by (cell, slot), slot < K) | recipe id, region id, geometry (`slab` / `cylinder` / `bed`), thickness or σ, β, component inventories (kg/m³ of cell), loadings, surface patches | **new**; D30's bed is K = 1 |
| **Surface patch** (sparse, per element and per exposed cell face) | T_s, the lumped char-node state, ignited area fraction, flame-cover latch | generalises `world_model.md::§8`'s face table |
| **Zone** | gas species kg, gas energy; in Phase 1 an outside reservoir with ledger lines | world_model §2 |
| **Pool** (per zone, no position) | free liquid kg and enthalpy | world_model §2; **can't carry a drip** |
| **Fines** | destroyed solid mass | world_model §7 |

### 2.2 Each transition

- **Virgin → char + volatiles (softwood, cardboard).** This is a reaction on the element's `virgin` inventory: residue
  `char` at yield χ_c, and the rest goes to a gas species `pyrolysate`. The char's *thickness* is derived:
  δ_c = (char kg/m³)/(ρ_c·σ) on a bed or slab. It is never stored separately. The surface patch holds T_c, as in
  `char_oxidation.md::§5.1` and `hot_surface_spike/results.md::§1`.
  **One truth:** element inventories are the conserved state; the patch holds only derived or energy state. A char
  *cell material* (`states_of_matter/architecture.md::§1.4`, `residue: {solid: char}`) is wrong for sub-cell fuels:
  char forms within millimetres of the surface (D).
- **Char → CO/CO₂ + ash (smouldering, glow, burnout).** A heterogeneous reaction consumes O₂ from the zone or the
  reservoir and yields `ash` as a residue. Wood ash is ~0.3–1% of dry mass (M).
  - **Burnout** means the element's combustible inventories are below ε, a per-volume constant.
  - **The ash stays** as an inert inventory, and goes to fines when the element is removed. It is never deleted
    (`world_model.md::§2`).
- **PMMA → MMA vapour (no char).** A single reaction with no residue; the element's thickness shrinks by FDS's
  factor (TRG §7.2.5, V). **That is sub-cell recession for free** on a sub-cell slab. D30 moved recession to Phase 2
  for *cells*; for elements it is one float.
- **Moisture → water vapour.** This is an evaporation transition on the `water` component, energy-limited at T_b or
  by a film law. It is the same kernel the accelerant spike verified against m·L_v/q''
  (`accelerant_spike/results.md`, E4(i), interpolated). Its product is the gas species `h2o`.
- **Wax loading (the R3 starter).** The starter is a sawdust bed element carrying a `paraffin` loading, which is T18's
  loading field (`physics_spike.md::The accelerant's form`). The loading has **two inventories**, `paraffin_s` and
  `paraffin_l`. Melting at T_m with latent L_f moves mass between them; nothing else changes. Liquid wax then
  evaporates or gasifies to a `paraffin_vap` species. The **cap** is void fraction × ρ_L, as decided (owner, T18).
  - **Over the cap** is free liquid that drains (T18: Phase 2). Paraffin expands ~10–15% on melting (M), so the
    loader must refuse a starter whose *molten* volume exceeds the cap, or a drip path must exist (D).
- **Solid wax or PMMA melting into pools, and dripping.** There is no honest home for this today:
  - A positionless pool (world_model §2) can't put the drip under the object.
  - Dripping can *extinguish* the source (PET, PA-6, PC) or *spread* the fire (Joseph 2015 §1, §3, V), so ignoring
    it silently changes the outcome class.
- **Volatiles to zone gas.** Every gas yield goes to the zone (in Phase 1, the outside reservoir) as named species
  mass. The ledger line is "species mass to atmosphere". The flame's heat release is computed from that mass, not
  from a separate fire budget.

### 2.3 Which decisions hold, and which I'd revisit

| Decision | Verdict | Why |
|---|---|---|
| Containers by phase (`world_model.md::§2`) | **holds** | Every transition above is a transfer between containers |
| T18's loading field | **holds; generalise it** | to a loading on an *element*, phase-split into inventories; the cap holds |
| **One material per cell** (`world_model.md::§5`; T18's "no general solid mixtures") | **revisit** | R3's contact and every sub-cell fuel. Keep one *structural* owner per cell and add K element slots. Regions: each element carries its own region id, so `bincount` reductions still work (`world_model.md::§9`) |
| **Thin-features rule** (CLAUDE.md, `docs/architecture.md`) | **revisit, explicitly** | It can't hold for any ladder fuel. Scope it to resolved cells, and state that sub-cell elements are exempt because their geometry is in metres. Quietly breaking it would be the worst outcome |
| **Temperature + latent progress per cell** (`world_model.md::§0`, v2 decision 18, §4) | **revisit before save v0** | One `latent` scalar can't carry moisture, wax and PMMA at once. Phase-split inventories carry the progress exactly, and the enthalpy inversion pins T at T_m while both inventories are non-zero (`states_of_matter/physics.md::§2`). Cheap now, because save v0 isn't committed (`world_model.md::§10` row 11) |
| **Face table keyed (cell, face 0–5)** (`world_model.md::§8`) | **revisit** | A bed's surfaces are interior: the hot-surface spike already used "Iw as one lumped surface per cell" (`hot_surface_spike/results.md::§4`). Key patches by (cell, slot, patch) |
| **Positionless pools** (`world_model.md::§2`) | **holds only if dripping is deferred** | See §2.2 |
| D26/D30 deferring pyrolysis and phase change to Phase 2 | **contradicted by the ladder** | R1 on PMMA *is* pyrolysis. The ladder needs both, so the data model has to carry them now |
| Hard-coded cell channels (`gates/src/simcore/core/grid.py::CellStore.__init__`, `frames.py::CellFrame`) | **revisit before step 5** | Four channels are named by hand in two places. Inventories and elements need a registry-driven channel set and the element and patch tables inside the same write window (`boundaries.md::§4.1`) |
| `MaterialGrid.destroy` turns cells to air with their mass and heat gone (`gates/.../grid.py::destroy`) | **known, and it compounds** | Every transition that ends in removal must go through a transfer to fines, never through `destroy` as written |

## 3. The material table (v1 proposal)

Its shape follows FDS's MATL/REAC split, held to the strict loader (`world_model.md::§8`). It is per unit mass or per
unit volume throughout; nothing is per cell. Numbers below are placeholders marked M.

```yaml
version: 1
species:                         # ordered; index = position; saved in this order
  - {name: o2, formula: {O: 2}, molar_mass_kg_mol: 0.032}
  - {name: h2o, formula: {H: 2, O: 1}, ...}
  - {name: pyrolysate_wood, formula: derived}   # the loader solves it from the reaction's atom balance (D)
  - {name: mma, formula: {C: 5, H: 8, O: 2}}
components:                      # condensed, the unit an inventory is kept in (FDS MATL)
  virgin_softwood: {density_kg_m3: 1530, cp: {table: ...}, k: {table: ...}, h_ref: solved}  # S, T18
  char:     {density_kg_m3: ..., ...}
  ash:      {inert: true, ...}
  water_l:  {...}
  paraffin_s: {...}
  paraffin_l: {...}
  pmma:     {density_kg_m3: 1190, ...}            # M
transitions:                     # change of phase, no chemistry
  paraffin_melt: {from: paraffin_s, to: paraffin_l, at_c: 60, latent_j_kg: 2.0e5, band_c: [55, 65]}   # M
  water_evap:    {from: water_l, to_species: h2o, law: clausius_clapeyron, t_b_c: 100, latent_j_kg: 2.257e6}
reactions:
  softwood_pyrolysis:
    reactant: virgin_softwood
    rate: {threshold: {t_c: 300, l_g_j_kg: ...}}           # or {arrhenius: {a_per_s, e_j_mol, n_s, n_o2}}
    yields: {components: {char: 0.20}, species: {pyrolysate_wood: 0.80}}    # sums to exactly 1
    heat_of_reaction_j_kg: ...
  char_oxidation: {reactant: char, consumes: {o2: ...}, yields: {components: {ash: ...}, species: {co: ..., co2: ...}}, ...}
recipes:                         # what a scene or an imagined object may name (cell materials and element fills)
  softwood:  {components: {virgin_softwood: 0.88, water_l: 0.12}, void_fraction: 0.61, bulk_density_kg_m3: 600}
  cardboard: {...}
  pmma_sheet: {components: {pmma: 1.0}, void_fraction: 0.0}
  wax_sawdust: {matrix: sawdust, loadings: {paraffin_s: {kg_m3: ..., max: cap}}}
variants:                        # the only knobs an imagined object may set, each bounded and cited
  softwood: {moisture_mass_fraction: [0.06, 0.20]}
```

**Loader rules** (each rejection path tested, under B12):
- Yields sum to 1 to 1e-12, refused either way (stricter than FDS App. P.1).
- Atom balance closes for every species with a formula. A lumped pyrolysate's formula is *solved*, never typed.
- Every reaction closes a **Hess cycle**: h_ref is solved per component, as in FDS App. P.2, and a reaction whose heats
  can't be reconciled to a tolerance is refused (D).
- Transition bands are ordered, and every threshold carries its cited range.
- Recipe fractions sum to 1, and each loading cap is void_fraction × ρ_L.

**Resolution independence:**
- Inventories are kg/m³ of cell, and geometry is in metres (thickness, σ in 1/m, β).
- Rates are per m² of surface or per m³ of component.
- A cell size never appears in data, and the cross-tier suite proves it.

**Imagined objects:** `imagination.place` already refuses unknown materials (`gates/src/simcore/core/imagination.py`,
lines 100–101); keep it. The LLM names a **recipe**, geometry in metres and **variants within cited ranges** only: no
component, reaction or free number. "Soaked in kerosene" is a loading checked against the cap. Out of range is
refused, never clamped (clamping makes the LLM's number partly authoritative, D). Kinetics are physical columns in
engine data (`boundaries.md::§8.2`), never content.

## 4. Determinism and conservation

**Invariants for every transition** (`states_of_matter/architecture.md::§1.1`'s transfer rule):
1. **Mass per component and per species.** Σ elements + cells + zones + pools + fines changes only by boundary flux.
   The amount credited is what the donor's storage lost (`float64(old) − float64(new)`).
2. **Element balance** (C, H, O, N) for every species with a formula, which is automatic once reactions close at
   load.
3. **The energy ledger.** Sensible + latent + chemical, closed per substep to world_model §4's relative tolerance.
   The ledger alone isn't enough: it missed a 1,000× units bug (`physics_spike.md::Results`, 4a).
4. **Monotone latches.** Ignited, flame-cover and burnt-out are in the digest (`physics_spike.md::What steps 5a and 6
   should take`).
5. **Inventories never go negative.** A transfer is limited by the donor *before* it is applied, never clamped after.

**Tests:**
- **Closed forms:** one-phase Stefan for the wax melt (first-order envelope, `states_of_matter/physics.md::§2`);
  PMMA steady ablation, thickness rate q''_net/(ρL_g) (D); the evaporation plateau m·L_v/q'' (accelerant E4(i)); the
  steady char T_c (hot-surface E3(i)); an Arrhenius TGA peak against Kissinger's βE/(RT_p²) = A·e^(−E/RT_p) (M);
  Hess closure on the shipped table.
- **Cross-tier.** Element-internal processes are grid-free by construction; test the *coupling* (area-overlap
  heating, element→cell exchange). The adversarial case is an object straddling cell boundaries: one element at
  0.2 m, several at 0.05 m, with equal summed inventories and outcome class.
- **Hypothesis:** random recipes, loadings and fluxes keep ledgers closed and inventories ≥ 0; measure reach.
- **The identity pattern.** With zero loading or zero inventory, a new term reproduces the old digests bit for bit
  (`accelerant_spike/results.md`, E4(ii)). Use it at every new transition.
- **Determinism.** Rows ordered by (cell index, slot) integer keys; reductions by `bincount`.

## 5. Recommendation and decisions for the owner

**The smallest data model that carries R0–R4 without rework:**
1. The **element table** (sparse, (cell, slot), K = 2 for now and reserved in the format), with recipe, region,
   geometry in metres, **component inventories** and loadings. It replaces D30's per-cell fuel fraction.
2. **Surface patches** keyed (cell, slot, patch), holding the char node, T_s, ignited fraction and latches. They
   replace the (cell, face) table before the grammar freezes.
3. **Phase-split inventories** replace the per-cell `latent` field.
4. **Material table v1** as in §3: components, transitions, reactions with residues, recipes and bounded variants.
   It refuses a mass excess and closes atoms and the Hess cycle at load.
5. **Gas yields go to named zone species** (the outside reservoir in Phase 1) on the ledger.
6. **Dripping is deferred:** an `excess_liquid` path that refuses at authoring until positioned puddles exist,
   recorded as a known gap with Joseph 2015's two outcomes.

**Phase 2 then only adds** puddles behind `liquid.at` (the refusal becomes a transfer), a soot species, and rubble
redistributing fines from removed elements; no saved field changes meaning.

**Decisions for the owner:**
1. **Accept sub-cell fuel elements** (K slots per cell) as a refinement of world_model §5, and scope the thin-features
   rule to resolved cells. *Recommended. The alternative is ladder fuels ≥ 0.4 m thick, which aren't the ladder.*
2. **Replace "temperature + latent progress" with phase-split inventories** before save v0. *Recommended.*
3. **Defer dripping**, and correct the ladder's PMMA premise: PMMA regresses and doesn't drip meaningfully. If a
   dripper is wanted, add PP as a later rung once puddles exist. *Recommended.*
4. **The threshold vs Arrhenius default per reaction.** Ship threshold (T_p, L_g), which FDS's REFERENCE_TEMPERATURE
   justifies and which has a closed form. Allow Arrhenius only where kinetics are cited and the cross-tier suite
   passes. *Recommended.*
5. **A registry-driven CellStore** with the element and patch tables inside the write window, landed with material
   table v1 (step 5), not after. *Recommended. The four hard-coded channels in `grid.py` and `frames.py` are the
   first rework this ladder would otherwise force.*

**Honest limits:** Gpyro and ThermaKin are S only; wax and PMMA values are M. This lens doesn't supply the missing
spread law (`hot_surface_spike/results.md::§5`): a good data model doesn't make the crate spread.
