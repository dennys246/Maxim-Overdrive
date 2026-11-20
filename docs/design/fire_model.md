# Fire model v1: design for review (2026-11-20, draft)

**Status:** a design that changes the architecture, so it is reviewed before any code (CLAUDE.md, "Review before
push"), with the Bio-faithful integration lens among its readers. Nothing here is decided until the owner rules on
§11. It replaces step 6's laws 6b–6d (world_model D29, D30) and keeps 6a (open-air loss).

**Sources.** Seven research reports in `research/fire_ladder/` (L1–L6b, one per lens), an independent check of their
load-bearing claims (`research/fire_ladder/7_verification.md`), and the three fire spikes. Claims carry the report's
tag: **V** read in the primary source, **S** secondhand, **M** memory, **D** derived. A citation like [L2 §1.2] points
to the report section that holds the source. **Where the check corrected a report, this note follows the
check** (marked [V7 n] for its claim n); the reports themselves are kept as written.

## 0. The answer in one page

1. **Three spikes failed for one reason: our flames had no body.** In the porous-bed law (6c) a burning surface
   heats only itself; unburnt fuel sees only a radiative leak χ_r·q''_f. Real fire spreads mostly by the flame
   *touching* fuel ahead of it: fine fuels "will not ignite solely from radiation" below about 80 kW/m² (Finney
   2015, V), and in stick arrays upward spread is by contact and sideways spread by radiation (Jiang 2019, V)
   [L2 §0]. No shipped game spreads fire this way either; all of them use a fire object with a rule [L4 §0].
2. **The flames are too small for any grid we can afford.** A 1–2 kW flame has D* = 0.06–0.08 m (D), 0.3–1.6 cells
   across on our grids. FDS's validation cases span D*/dx of about 1 to 118, and its guide warns against reading a
   minimum off that table [V7 9]; resolving flames this small would still need millimetre gas cells, which would
   make Phase 1 a CFD project. Rate convergence is hard even for FDS: its 2021 runs of NIST's single crib peaked at
   ~800, 440 and 330 kW at 8, 4 and 2 cm (FDS 6.7.6), though current FDS gives 485, 392 and 389 kW against
   396 ± 18 kW measured [V7 3]; its PMMA spread cases still differ by grid [L2 §0, not re-checked].
3. **So both the fuel and the flame become sub-grid objects sized in metres**, beside the grid, not cells:
   - **fuel elements** (a stick, a slat, cardboard, a wax starter) carry component inventories and a 1D in-depth
     solid model per exposed surface, as FDS, Gpyro and ThermaKin do [L1 §1.2, L3 §1];
   - **flame objects** carry a height and a heat-flux footprint from cited correlations (wall flames: Delichatsios
     and Hasemi; free flames: Heskestad), heating fuel by contact inside the flame and by view-factor radiation
     outside it, deposited by overlap [L2 §1.2, §2.1, §5].
   Both are grid-independent by construction. Spread stays an outcome of heat transfer (T18), and correlations
   measured in fire labs are physics, not label rules [L4 §4].
4. **The crate going out in the hot-surface spike may be correct.** A lone timber surface self-extinguishes below
   an external flux of 24–57 kW/m² depending on species (45 ± 1 for radiata pine CLT; Emberley et al. 2017, FSJ
   91:327, and its companion species study) [V7 1], and a 550 °C char surface re-radiates ~23 kW/m², nearly all of one
   flame's 25 kW/m² (D) [L1 §2.3]. A crib keeps burning because its surfaces heat each other, which is exactly what
   flame objects inside a bed supply.
5. **We validate from the bottom up**, one mechanism per rung, against multi-lab data where it exists (§6). The
   pass bands are the literature's own spread between labs, and grids are graded on outcome class, never rate.
6. **NPCs sense physical stimuli at their receptors, never verdicts** (§5). This revises part of T18 and retires
   `ignite`/`extinguish` as NPC verbs.
7. **The Phase 1 exit becomes "build a fire against a crate"**: a fire starter, kindling, then the crate (§7). It is
   the order real fires are built in, and every beat is a graded rung.

## 1. What the evidence established

| Finding | Evidence | Consequence |
|---|---|---|
| A torch lights only the slat faces it heats; the bed never spreads | physics spike Q1 (all grids, all range ends) | 6c can't be the burning law |
| Kerosene in the pores doesn't spread it either | accelerant spike, λ_max 0.0129 | the fuel's distribution isn't the missing piece; T18's "spreads because its fuel is distributed" was wrong in that model |
| Hotter surfaces and an uncapped gas don't spread it | hot-surface spike, outcome 5 | the pins weren't the cause |
| A char layer with only its own flame's flux goes out | hot-surface C_F; Emberley et al. 2017 [V7 1]; closed form (D) | probably correct single-surface physics; R1 decides |
| Char handed over at 550–900 °C glows | `char_oxidation.md` | the glow question is a hand-over temperature question |
| Flames heat fuel ahead by contact; radiation alone rarely ignites fine fuel | Finney 2015, Jiang 2019 (V) [L2 §2.3] | the flame needs a body |
| Flames here are smaller than a cell | D* (D), FDS guidance (V) [L2 §0] | sub-grid flame objects, not resolved flames |
| Rates converge poorly across grids even in FDS (its 2021 crib runs; PMMA spread), though current FDS's crib peak converges at 4 and 2 cm | FDS Validation Guide [L2 §0, V7 3] | grade class across grids, as the resolution rule says; report rates with their observed order |
| K2_005's stall was a sliver area divided into a power, not the char layer | probe log (D) [L5 §0]; code read by the session | area hygiene and capped substeps (§4) |
| Sub-cell models sized in metres converged; cell-sized ones didn't | bed.md (diverged), hot-surface F (p = 1.87) [L5 §3] | the rule world_model §3 already states, confirmed |

## 2. Fuel: elements, inventories and transitions

### 2.1 Containers

Every ladder fuel is thinner than 0.1 m, so none can be cells under the thin-features rule (≥ 0.4 m) [L3 §0].
The model adds two sparse tables beside the dense grid [L3 §2.1]:

| Container | Holds | Status |
|---|---|---|
| **Cell** (dense) | structural owner material, region id, temperature, integrity | as today |
| **Element** (sparse, key (cell, slot), K = 2 slots, reserved in the format) | recipe id, region id, geometry in metres (`slab`, `cylinder`, `bed`), thickness or σ and β, **component inventories** (kg/m³ of cell), loadings | new; D30's bed is one element per cell |
| **Surface patch** (sparse, key (cell, slot, patch)) | the 1D solid state (§3), ignited-area fraction, flame-cover latch | replaces world_model §8's (cell, face) table |
| Zone, pool, fines | as world_model §2 and §7 | unchanged |

An object that straddles cells is one element per cell it occupies, each carrying its share of the inventories.
Element rows sort by integer key (cell index, slot); reductions are `bincount` by region, as today.

### 2.2 Every transition is an inventory move

| Transition | As an inventory move | Notes |
|---|---|---|
| virgin wood → char + volatiles | reaction on `virgin`: residue `char` at χ, the rest to gas species | char *thickness* is derived from char mass, never stored separately |
| char → CO/CO₂ + ash | heterogeneous reaction consuming O₂ (Phase 1: the outside reservoir) | glow and burnout; ash stays as an inert inventory until the element goes to fines |
| PMMA → MMA vapour | one reaction, no residue; the element's thickness shrinks | **PMMA doesn't melt or drip** in this sense: it is amorphous and gasifies first [L3 §0, Joseph 2015 V]. It is the non-charring, regressing reference |
| moisture → water vapour | evaporation on `water_l` at T_b | the accelerant spike's verified kernel |
| wax solid ↔ liquid | latent move `paraffin_s` ↔ `paraffin_l` at T_m with L_f | T18's loading, split by phase; the cap stays void fraction × ρ_L |
| liquid wax or kerosene → vapour | evaporation, then flames on the vapour | the accelerant spike's law |
| element burnt out | combustible inventories below a per-volume ε | the residue goes to fines through a transfer, never through `MaterialGrid.destroy` as written |

This makes the per-cell `latent` scalar redundant: one scalar can't carry moisture, wax and wood at once, and
phase-split inventories carry the progress exactly [L3 §2.3].

**Dripping is deferred** and recorded as a known gap. Pools have no position (world_model §2), so a drip can't make
a pool fire under its object, and real drips can either put a fire out or spread it [L3 §2.2, Joseph 2015 V]. Until
positioned puddles exist, a recipe whose melt exceeds its retention cap is refused at authoring. If a real dripper
is wanted, it is polypropylene or polyethylene, later.

### 2.3 Invariants

1. Mass per component and species changes only by boundary flux; a transfer is limited by the donor *before* it is
   applied, never clamped after.
2. Element balance (C, H, O) closes for every species with a formula, checked when the table loads.
3. The energy ledger closes per substep, **and** every law has a closed form: the ledger once booked a 1,000× units
   bug consistently on both sides.
4. Latches (ignited, flame-cover, burnt out) are in the state digest.

## 3. The solid: a 1D model per surface patch (R0, R1)

Each burning surface patch carries a 1D in-depth grid normal to the surface, sized in millimetres per material,
never by the world cell [L1 §1.2, L5 §1]:

1. finite-slab conduction with a specified back boundary (an element's far side, or its neighbour);
2. pyrolysis at an intrinsic heat of gasification L_g, leaving char at yield χ;
3. a char layer with ρ_c, c_c and k_c(T);
4. a surface balance: incident flux (external + flame) = εσ(T_s⁴ − T∞⁴) + h(T_s − T∞) + conduction inward (+ char
   oxidation);
5. ignition and extinction by a critical mass flux m''_cr, so R0 and R1 share one law [L1 §1.2].

**The rate law is R0's first question, not a default.** L1 recommends one-step Arrhenius kinetics; L3 recommends a
threshold (T_p, L_g) by default, as FDS allows through `REFERENCE_TEMPERATURE` (V). Both give a mass flux, so the
m''_cr criterion works under either. R0 fits both to the MaCFP data and keeps the simpler one that passes. Fitted
parameters (kinetics, L_g, k_c, char ε) are **re-fitted by our model to R1's data, never copied**: MaCFP lists more
than 13 property sets for one PMMA [L1 §4].

**Two checks on the solid model that are tests in themselves:**
- Wood's *apparent* heat of gasification from cone data is ~15 kJ/g (D: 14.6 and 15.7 from two independent fits to
  MaCFP-4; no published value found) [L1 §2.2, V7 11], against an intrinsic 1.6–2.6. A correct char model must
  *produce* the apparent value.
- With the cone heater stepped down, the slab must go out inside the species band (24–57 kW/m², at 2.7–8.3 g/m²s)
  [V7 1]; R1 pins the band for the species it grades.

**Inputs from the spikes to revisit:** the scene's wood is 600 kg/m³ against the graded pine's ~380, so the scene's
species must match the data it is graded against [L1 §4]. The spikes' k_c of 0.10 W/m·K is inside the fitted range
(about 0.08–0.30) [V7 11], not below it as L1 says; R1 re-fits it anyway.

## 4. Flames: sub-grid objects in metres (R2–R4)

### 4.1 The object

A **flame object** is a burning cluster's flame, with its geometry and flux set by cited correlations [L2 §1.2,
§2.1, §5]:

- **Clustering.** Burning patches group by connected burning area in metres, never by cell. Merging is a cited
  gap: no merging model was opened [L2 §5.2].
- **Heat release.** Q from the cluster's pyrolysis mass flux × ΔH_c,eff. The flame is fed by the fuel; nothing
  else sets its size.
- **Geometry.**
  - Against a surface: a sheet of height x_f = (4.65–6.1)·[Q'/(ρc_pT√g)]^(2/3), Delichatsios and Hasemi (V, tested
    for x_f of 0.3–1.4 m, with considerable scatter).
  - Free: a solid cylinder of height L = 0.235·Q^(2/5) − 1.02·D, Heskestad (V as applied; fitted on pool and burner
    fires, so kilowatt stick flames are an extrapolation, flagged).
  - Tilted by the draught.
- **Flux onto surfaces.**
  - Inside the flame (contact): 10–30 kW/m², with "no universal maximum" (V); Leventon's form ties the peak to
    burning rate (V, abstract) [L2 §1.2].
  - Above the flame tip: falls as ~x^-2.4 (V).
  - Outside the flame: radiation by analytic view factor from the solid flame, with surface emissive power set so
    the total radiated power is χ_r·Q exactly [L5 §3].
- **Deposit.** Incident flux is evaluated at quadrature points fixed in metres on each receiving patch and
  integrated over the patch; contact is a geometric overlap fraction. Nothing is decided at a cell centre [L5 §3].
- **Into the gas.** The convective part (1 − χ_r)·Q heats the zone (the outside reservoir in Phase 1) on the
  ledger.

Inside a bed (the crate), surfaces within a flame get the in-flame flux. That is the crib heat feedback the char
layer needs (§0.4). **No cited value for the flux inside a burning crib was found** [L2 §5.2]. That is R4's open
question, and it is graded against a measured crib rather than assumed.

### 4.2 What this model is not

- **Not a crib correlation as the burning law.** Heskestad's crib rate and NIST's crib tests are R4's oracle, never
  its mechanism: a correlation as the mechanism would make spread a property of the object, not of heat transfer
  (T18) [L2 §5.1].
- **Not resolved CFD.** The gas grid carries the plume's energy, not the flame's shape.
- **Not a rule.** No flame object ignites anything; it puts watts on surfaces, and each surface's 1D model decides.

### 4.3 The main risk: the feedback loop near threshold

Flux → pyrolysis → Q → flame height → flux. Near the spread threshold a small grid-dependent error flips the
outcome class; Jiang's race (burnout 13.6 s against neighbour ignition 19.8 s at a 1.5 cm gap, V) shows how thin
the margin is [L2 §5.2]. So binary outcomes keep CLAUDE.md's band and outcome margin, scenarios sit away from the
threshold, and the band's width across grids is itself gated [L5 §3]. The 13.6 s and 19.8 s are unverified (the
paper's full text wasn't reachable); its gap result is confirmed [V7 5].

## 5. What NPCs perceive and do

### 5.1 The split

The world computes the **physical stimulus at the receptor's location**. Maxim computes **transduction**:
thresholds, adaptation, pain kind, timing and learning [L6b §3.1].

| Quantity | World | Maxim |
|---|---|---|
| Heat on skin | incident flux per body region (W/m²) from flame objects and gas; skin and basal-layer (~0.1 mm) temperature from a skin conduction model; contact temperature from effusivity | warm and cool receptors (adapting), nociceptors (sensitising) |
| Tissue damage | a Henriques integral into the region's integrity or `health` | `drive:health` pain |
| Airway | irritant and soot concentration at the mouth (Phase 2, with buoyant smoke) | chemical nociceptor |
| Smell | vapour concentration per species at the nose (Phase 2) | olfactory receptor, adapting, gated by sleep |
| Sight | luminous flame volumes in view: luminance, angular size, flicker (~1.5 D^−1/2 Hz, S) | percept, salience |
| Sound | onset transients at the ear (Phase 2) | features |

Two leak tests a reviewer can apply [L6b §3.1]:
1. Could an instrument at that spot measure the value with no knowledge of the nervous system? Then it's the
   world's.
2. Does the parameter have a value in a physiology paper (a threshold in °C, an adaptation time)? Then it's the
   receptor's, and it lives in Maxim.

### 5.2 Why radiation matters to the agents

Radiant heat warns before it harms. On bare skin: at 2 kW/m², pain at ~45 s and a second-degree burn at ~187 s; at
10 kW/m², 5 s and 14 s (NOAA ALOHA from FEMA 1988, V) [L6 §1.1]. Pain leads damage by 3–6×. **Without flame
radiation the learn-before-harm window is zero**, and every fire lesson is contact-only. This is the agents' case
for this design over relaxing the exit.

### 5.3 What changes from T18

- **"Flammable" and "porous" are not sensors.** No receptor senses them, so as NPC inputs they are oracles that teach
  Maxim our table. Material *identity* (wood, cardboard, wax) is a noun through vision; "wood burns" is learned or
  told [L6 §1.3].
- **Booleans become fractions.** "Burning", "smouldering", "charred", "melting", "soaked" are continuous fractions in
  [0, 1], read only through a percept channel. A yes/no label thresholds a whole entity's mean: the D25 hazard T18
  itself cites. `states_of_matter/sem.md` N2 ("fractions, never labels") already said this; T18 contradicted it, and
  N2 is right.
- **Kept from T18:** physics owns the mechanism, the bridge reads it, and nothing spreads by an SEM rule.

### 5.4 Acts

The player's `kindle` already takes its power from a held item (tile spec T4). NPC acts follow the same rule: body
acts with held things, each driving physics [L6 §2].

| Act | What the world does | When |
|---|---|---|
| `light` a held starter | the starter's own cited flame | with R3 |
| `apply` a held flame to a target | its flame object touches the target; ignition is the physics' verdict | with R3 |
| `carry` / `drop` / `place` | moves an item; a burning stick's flame moves with it | needs item entities |
| `step_back` / `move` | flux falls with distance | needs bodies |
| `pour`, `cover`, `fan` | liquid, O₂ and airflow | Phase 2 |

- **A fruitless act succeeds as an act.** A flame applied to steel happens; the world shows no ignition. Refusing it
  would leak the rule into error text, and under Maxim's tool-failure credit (TF2) book a failure on the tool
  [L6 §2].
- **`requires` states only physical possibility at the actor** (holding a starter, in reach), never a predicted
  outcome.
- **`structure.ignite(power_w, radius_m)` and `structure.extinguish()` leave the NPC surface.** No NPC emits a
  chosen wattage, and `extinguish` deletes a heat source with no water, lid or oxygen. They stay as lab and test
  instruments, never NPC inputs.

### 5.5 What the bridge must never do

- decide an outcome from a label, or in the bridge;
- expose flammability, flash point, heat of combustion or φ as a sensor;
- threshold a whole entity's mean into a boolean an agent learns from;
- refuse an act because physics would make it fruitless, or put the outcome in a description or error;
- give an NPC an omniscient region instrument;
- write a second heat path into the body.

## 6. The validation ladder

Each rung adds one mechanism, is pre-registered, and is graded against measurements. **Across grids, only outcome
classes are graded; rates and times are reported with their observed order.** Within the data, the pass band is
the envelope of lab means, graded on curve features, not pointwise [L1 §5]. Each rung also gets a legibility check:
a short clip judged on "does this look like what fire does?"; a physical pass that looks wrong is a finding [L4 §5].

| Rung | Setup | Isolates | Graded against | Pass (class across grids; features within the data's envelope) |
|---|---|---|---|---|
| **R0 ignition** | one slab under a fixed radiant flux | heating and ignition | MaCFP-2 black PMMA (lab means 76–148 s at 25 kW/m², the 76 s lab a flagged outlier) [V7 2]; MaCFP-4 white pine (25–75 kW/m²) [L1 §1.3] | t_ig inside the envelope at every flux; the thick and thin closed forms; no surface cooling under constant heating |
| **R1 burning** | that slab, burning, then the heater stepped down | burning, char, extinction | MaCFP-4 pine curves at 30, 50, 60 kW/m² (first peak 161–235 kW/m² at 50, over only 4 labs) [V7 2]; Emberley et al. 2017 and its species study | first peak, plateau and second peak in the envelope (backing specified); apparent L_g ≈ 15 kJ/g produced, not input; extinction in the cited band |
| **R2 spread on one surface** | (a) a slab lit at one edge, cold and preheated; (b) a base-lit vertical slab | the flame sheet heating fuel ahead | Quintiere & Harkleroad, NBSIR 84-2943 Table 2 [V7 6]: no opposed spread on cold plywood or PMMA; 1.2 and 3.0 mm/s on plywood preheated to 250 and 300 °C, *derived* from its parameters, not measured; wall-flame height and flux | (a) no spread cold, spread preheated within ×2; (b) upward spread that accelerates, flame height in the correlation band, wall flux peaking at 10–30 kW/m² |
| **R2.5 the flame object alone** | prescribed Q over a burner; target patches at distances; the base offset by dx/3 and 2dx/3 | the flame's geometry and radiation, decoupled | analytic view factors; χ_r·Q conservation | absorbed power within a gated error on every grid; radiated power = χ_r·Q to round-off [L5 §3] |
| **R3 two bodies** | (a) Jiang's dowel array; (b) a wax starter beside a stick; (c) stick beside stick at several gaps | flame contact and radiation across a gap | (a) Jiang 2019 (V): sideways spread at 0.75 cm, none at 1.5 cm, upward at both; (b), (c): **no dataset exists** | (a) Jiang's class; (b), (c) reported as predictions, class only |
| **R4 crib** | NIST TN 2102's crib with its own pilot, then the alley's crate | everything together | TN 2102 Test 13: 396 ± 18 kW peak, ~5% residue [L2 §3.3, V7 3] | ≤ 10% residue (class); peak within ×1.5 and time to peak within ±40% on every grid; the crate reported, not graded |

**Materials.** PMMA first: fire science's reference, non-charring, best data. Then white pine. Cardboard joins at R3
as the exit's kindling (McKinnon 2012's layered board, V; no single-sheet dataset was found). The **fire starter**
has no published burning data at all [L1 §3]; paraffin itself is well characterised (Hamins 2005, V), so the starter
is modelled as the accelerant law plus fusion plus retention, and its first numbers come from a pre-registered bench
measurement (mass against time on a scale) or stay a prediction.

**Each rung's tests** follow L5 §5: closed forms, the identity pattern (a new term at zero reproduces the old digests
bit for bit), an n-cap test that feeds a sliver area and requires a bounded n and a finite T, subset independence
(a surface solved alone gives the same bits as in the batch), and a cost-regression gate from R4.

## 7. The Phase 1 exit

**Proposed:** the player builds a fire against a crate. They light a fire starter under kindling leaned on a crate
packed with cardboard; it catches, grows, and the crate cracks, glows and burns down [L4 §5].

- Every beat is a rung: the starter (R3b), the kindling (R3c), the crate (R4).
- It is how real fires are built: nobody lights a crate with a torch.
- It is legible: every player knows the sequence.
- It gives NPCs the lesson they need later, that small fires grow only with fuel arranged for them.

**What still decides it:** R3 and R4 have no oracle for 20 mm sticks or for this crate. The exit is therefore
graded as a *prediction that passes its class gates on every grid*, plus the human playtest, not as a match to data.

**The fallback, named now:** if R3 fails, the exit is whichever rung passes honestly (a burning slab with flame-out
and glow), and the crate moves to Phase 2. That is a decision for the owner when R3 lands, not a default.

## 8. Numerics and cost

### 8.1 Integrators

- **In-depth conduction:** backward Euler, or θ ≈ 0.55. At dt 0.5 s with nodes sized in metres, Crank–Nicolson
  rang (the surface cooled on 10 of 19 steps under constant heating, D) [L5 §2]. One linearisation of εσT⁴ at the
  front, as FDS does (V). A hand-written Thomas solve, vectorised over surfaces, with no BLAS.
- **Pyrolysis and char oxidation:** an exponential update per node at frozen temperature, with the energy sink
  computed from the mass consumed, so the ledger closes exactly. Patankar's form where sinks compete.
- **Every remaining explicit law has a hard cap on substeps** (e.g. 16). In tests, exceeding it fails loudly with
  the cell; in play, world time dilates (D21) and the dilation is reported. **No uncapped loop anywhere.**

### 8.2 Area hygiene (the K2_005 lesson)

- Route an absolute power by area share (W × A_part/ΣA), never W/A_part.
- A part below a minimum size in metres (e.g. (1 mm)²) is retired and its energy merged.
- Stability estimates count only parts above that size.

### 8.3 Cost (D, single-threaded numpy, load ~2.6) [L5 §4]

| Kernel | Measured | At the tile (16×10×4 m, ~20,000 surfaces assumed) |
|---|---|---|
| 1D implicit solve | ~8 ns per node | ~3.3 ms per solve: about one heat substep |
| Flame → face radiation, all pairs | ~23 ns per pair; 59 ms for 256 points × 10,000 faces | too slow every step |
| With analytic cylinder view factors, receiver patches of ~0.2 m and a visibility cache | ~5 ms for 10 flames × 20,000 faces (D, estimate) | affordable |

The 20,000-surface count is an assumption, not a scene measurement. The server is already over real time
(`advance(0.5)` ≈ 0.7 s at 1.92 × 10⁶ cells, `docs/architecture.md` Known gaps), so every rung carries a
cost-regression gate, and exact sleep plus a fire bounding box is the first optimisation to measure [L4 §5].
Results were bit-identical on repeat, and a surface solved alone gave the same bits as in the batch [L5 §4].

## 9. The material table v1

Shaped like FDS's MATL and REAC split, held to the strict loader [L3 §3]:

- **species** (ordered, with formulas and molar masses; a lumped pyrolysate's formula is solved, never typed);
- **components** (condensed: virgin softwood, char, ash, water, paraffin solid and liquid, PMMA);
- **transitions** (phase changes, no chemistry);
- **reactions** (reactant, rate law, yields to components and species, heat of reaction);
- **recipes** (what a scene or an imagined object may name: components, void fraction, bulk density);
- **variants** (the only knobs an imagined object may set, each bounded and cited, e.g. moisture fraction).

**The loader refuses**, each refusal tested:
- yields that don't sum to exactly 1 (stricter than FDS, which warns below 1);
- an atom balance that doesn't close;
- a Hess cycle that doesn't close, with reference enthalpies solved per component as FDS App. P.2 does;
- unordered transition bands, or a threshold without its cited range;
- a loading over its cap.

Everything is per unit mass or volume; no cell size appears in data. **Imagined objects** name a recipe, geometry in
metres and variants within cited ranges only: no component, reaction or free number. Out of range is refused,
never clamped, because a clamp makes the LLM's number partly authoritative [L3 §3].

## 10. Decisions this revises

| Decision | Revision | Why |
|---|---|---|
| world_model §5, one material per cell; T18's "no general solid mixtures" | one structural owner per cell plus K element slots | R3's starter touching a stick; every sub-cell fuel |
| CLAUDE.md's thin-features rule | scoped to resolved cells; sub-cell elements are exempt because their geometry is in metres | no ladder fuel can satisfy it; breaking it quietly would be worse |
| world_model §0 and §4, temperature plus latent progress per cell | phase-split inventories | one scalar can't carry several transitions; cheap before save v0 |
| world_model §8, the (cell, face) table | surface patches keyed (cell, slot, patch) | a bed's surfaces are interior |
| D29/D30's laws 6b–6d | replaced by §2–§4; 6a kept | the spikes |
| D26's deferral of pyrolysis and phase change to Phase 2 | pyrolysis and fusion enter with the ladder | R1 on PMMA *is* pyrolysis |
| T18's derived labels | fractions through percepts; no flammable or porous sensor | §5.3 |
| The bridge's `ignite` and `extinguish` | lab instruments only, not NPC verbs | §5.4 |
| `CellStore`'s four hand-named channels (`grid.py`, `frames.py`) | a channel registry, with the element and patch tables inside the write window, landing with material table v1 | the first rework this would otherwise force [L3 §2.3] |
| world_model §2, positionless pools | holds while dripping is deferred | §2.2 |

## 11. Decisions for the owner

1. **Adopt the model:** sub-grid fuel elements (§2), a 1D solid per patch (§3), and flame objects from cited
   correlations (§4), replacing laws 6b–6d. *Recommended.*
2. **Revise world_model §5 and the thin-features rule** as in §10. *Recommended; the alternative is ladder fuels at
   least 0.4 m thick, which aren't the ladder.*
3. **Replace "temperature plus latent progress" with phase-split inventories** before save v0. *Recommended.*
4. **Revise T18's labels and retire `ignite`/`extinguish` as NPC verbs** (§5.3, §5.4). *Recommended.*
5. **Adopt the ladder** (§6), with outcome classes graded across grids and rates reported. *Recommended.*
6. **Change the Phase 1 exit to "build a fire against a crate"** (§7), with the named fallback. *Recommended.*
7. **Defer dripping** as a known gap (§2.2). *Recommended.*
8. **Ask Maxim now** (Phase 3): MP-2 (nociceptors in physical units, a question to GL2b) and MP-1 (burn pain may
   condition situation fear, an amendment to the autonomic plan's recorded decision, with an experiment in a
   Maxim-owned harness), because both are on Maxim's clock and no rung where an NPC touches fire can be claimed as
   learning without them. MP-3 to MP-6 follow as L6b §5 orders them. *Recommended.* R3 with an NPC *watching* needs
   no Maxim change.

## 12. Open questions and risks

- **The ignition threshold:** the two numbers attributed to Lyon & Quintiere 2007 don't conflict. About 24 kW/m² is
  the heat release rate per area at flash (ignition onset), about 66 kW/m² the one for sustained burning [V7 12];
  the ±17 rests on secondary citations, since the paper was unreachable. McKinnon used 15 for cardboard. R0 grades
  t_ig directly and says which criterion it models.
- **No in-crib flux and no merging model** were found (§4.1). R4 measures the first against TN 2102.
- **No data for the starter, 20 mm sticks at gaps, or the crate** (§6).
- **The feedback loop near threshold** (§4.3).
- **Flame radiation is the cost risk**, not conduction (§8.3).
- **Unpiloted ignition** of a neighbour (radiant autoignition) has no criterion yet; Babrauskas's *Ignition Handbook*
  wasn't read [L1 §6].
- **Maxim's GL2b and GL3 haven't started.** Until they land, burns reach an NPC only as `health`, which is real
  damage, not pain, and must never be reported as fire learning [L6b §5].
