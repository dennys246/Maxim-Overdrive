# SEM stimulus, lens 3: how the world computes stimuli correctly, at its own scale, and at what cost

Research note, 2026-11-20, read-only against `.worktrees/sem-stimulus` at 35a1702. Tags: **V** read at the source
named; **S** secondhand (a repo document that says it verified the value); **M** from memory, to verify before
`data/`; **D** my derivation or measurement. Measurements are in `scratch/` (`skin.py`, `geom.py`, `*.json`), run on
an Apple M2 with numpy 2.5.5 and threads at 1. **Load was 5.6–7.8 on 8 cores throughout**, so timings are
pessimistic by an unknown factor. Counts are exact.

## 0. The answer

1. **Per body, the world needs these models; the first two are Phase 1.**
   - A 1-D skin column per body quadrature point, with Henriques damage at the basal layer.
   - Incident flux on those points from flames and hot surfaces, after occlusion.
   - Contact: a coupled column, with effusivity as its closed-form test.
   - Radiance in view, after line of sight.
   - In Phase 2, sound at the ears and concentrations in a breathing volume.
2. **None of them reads a cell.** The body is capsules in metres with quadrature points fixed on them. The grid enters
   through four couplings only: occlusion by solid cells, emission from cell faces, contact with a cell face, and
   zone gas. One cross-tier test isolates each (§3).
3. **One backward-Euler skin step per 0.5 s physics step isn't enough at high flux (D).** It's within 4% of a
   converged reference up to 10 kW/m². At 20 kW/m² it's 12% late on pain, and on 70 °C steel in the hand it's 11%
   late on the burn. Five substeps bring every case within 3%.
4. **Occlusion is the cost risk.** At 100 NPCs per physics step: skin ~46 ms at five substeps, quadrature view
   factors 38 ms per flame, per-point occlusion ~0.8 s. Only coarsened, scheduled occlusion is affordable (§5).
5. **Two gaps the design doesn't cover yet.**
   - Damage computed on a region's mean flux is averaging-then-thresholding again: 1.9× late on the first burn,
     measured (§1.1).
   - Radiation or contact from a wall needs the wall's surface temperature, and that exists only where 6.0b builds
     face skins (§1.2).

## 1. Per stimulus: the model, its reduction, its sources

### 1.1 Skin temperature and tissue damage (Phase 1)

**Model.** Each quadrature point gets a three-layer Pennes column.
- **Layers:** epidermis 0.1 mm, dermis 2 mm, subcutis 10 mm, with Torvi & Dale's properties, perfusion and
  metabolic heat.
- **Boundaries:** the base is held at 37 °C; the surface has h = 8 W/m²K plus radiation; absorptance is 0.95.
- **Damage:** the Henriques integral at the basal layer (P = 1.43×10⁷² s⁻¹, ΔE/R = 55,000 K, above 317 K; Ω = 1 is
  a second-degree burn).

All of these are **S** from `physics_spike/body.md` §3 (via Jasiński 2003). The world publishes temperatures. Pain
thresholds (43–44.8 °C) are Maxim's receptor parameters (**V**, fire_model §5.1; 6b §3.1, leak tests).

**Anchors.**
- body.md's column sits inside its anchors (**S**): Jasiński +5%; Hoschke's 15 s at 4 kW/m² against 13.5–18.1 s.
- My reference gives 63 s to pain and 144 s to a burn at 2 kW/m² (**D**). NOAA ALOHA gives 45 s and 187 s (**S**,
  `7_verification.md` row 8). That is inside the anchors' scatter, not on them.

**Convergence (D, `skin.py convergence`).** The reference has 89 nodes at Δt = 0.005 s; production has 45 nodes.
Each cell is the error in time to pain / time to burn.

| Flux | Pain, ref | Burn, ref | Δt = 0.5 s | Δt = 0.1 s (5 substeps) |
|---|---|---|---|---|
| 2 kW/m² | 63.4 s | 144.4 s | +0.4% / +0.2% | +0.2% / +0.2% |
| 5 | 12.0 | 35.3 | +1.1% / +0.5% | +0.3% / +0.3% |
| 10 | 3.40 | 11.8 | +3.9% / +1.0% | +0.9% / +0.3% |
| 20 | 1.11 | 3.96 | +12.1% / +2.6% | +2.8% / +0.8% |

Crossings are interpolated inside the step, and Ω is integrated on that linear reconstruction. With 18 nodes, pain
at 10–20 kW/m² is 2.5–7.6% late even at Δt = 0.1 s, so 45 nodes is the floor.

**Damage must be integrated inside the step and per point.** The damage rate's sensitivity is d ln(dΩ/dt)/dT ≈ 0.5
per K at 45–58 °C (**D**), so a 1 K error at the basal layer is a 65% error in rate. This is the resolution rule's
non-linear law again, in time and in area:
- **In time:** taking Ω on the step's end temperature instead of its reconstruction differs by 2.6% at 20 kW/m²
  and 0.5 s (**D**).
- **In area:** take a region half at 15 kW/m² and half at 5. It first burns at **6.2 s**. One column at the mean, 10
  kW/m², burns at **11.8 s** (**D**, `mean_vs_points.txt`).

So each point gets its own column. A region's damage is the burned-area fraction, the fraction of its area with
Ω ≥ 1, which is how burn medicine measures (%TBSA, **M**). Its published temperature is the area mean and the
maximum, both instrument readings. Which one a receptor takes is Maxim's choice (receptors summate over area: **S**,
6b §1.1).

**Not modelled:** sweating, vasodilation, lateral conduction. Clothing is a layer on the column, as in body.md.

### 1.2 Radiation onto body regions

**Flames (Phase 1).** Each flame cluster is one solid emitter, and its emissive power makes its radiated power
exactly χ_r·Q (**V**, fire_model §4.4; 5_numerics §3).
- **Irradiance** at a point with normal n is E·∫cosθ₁cosθ₂/(πr²)dA over the visible emitter, times the point's
  unoccluded fraction.
- **Check:** my quadrature of body.md's 777 kW cylinder (0.677 × 2.68 m, E = 38.5 kW/m²) gives 12.24 kW/m² at 1 m,
  against body.md's analytic 12.4 at the hottest height (**D**, **S**).
- **Accuracy:** 16×8 side patches plus 16×2 top patches are within 0.7% at 1–3 m (**D**).

**Hot surfaces.** These are char faces, embers and a fire-heated wall: q = Σ εσT_s⁴·F(dA_s → point).
- **The emitter must be at its surface temperature.** εσT⁴ on a cell mean is a non-linear law on a mean.
- **Fuel segments have one (fire_solid §4); solid cell faces don't.** 6.0b builds skins on contact faces only (**V**, fire_solid §3.2), and a heated wall's
  cell mean is badly wrong at 0.2 m (P1: 104 against 48 MJ/m², **V**, world_model §3). Until 6.2 puts skins on
  every exposed face, "a hot wall warms an NPC" is a Known gap.
- **Distant face groups** can merge into point emitters by a distance rule in metres. body.md's far-field form is
  1.25× high at 1 m and exact by 2 m for a 0.6 m face (**S**).

**Convection.**
- Phase 1 air is still and has no gas in cells (**V**, world_model §2), so the body loses to the ambient reservoir.
- A point inside a flame's volume gets contact convection h(d)·(T_f − T_s), sized by the limb's diameter (**V**,
  fire_model §4.2).
- "Inside" is decided per point against the flame's shape in metres, so its band depends on point density, not dx
  (**D**).

**Ledger:** bodies are receivers in Q_rad,view (**V**, fire_model §4.2), so the ledger gains Δ(bodies).

**Not covered:** one body shading another (ray–capsule tests are cheap; a separate decision).

### 1.3 Contact

**Model.** A column through the object's surface layer and the skin, as one implicit system, using fire_solid
§3.2's Robin contact (**V**). Perfect contact, or a cited contact resistance (**M**). Its long-time closed form is the
interface between two semi-infinite solids, T_c = (e₁T₁ + e₂T₂)/(e₁ + e₂) with e = √(kρc) (**M**, textbook).

**Measured (D, `skin.py contact`).** With the dermis's e = 1,327, the coupled interface reaches the formula within
0.3 K by 10 s, for every material and temperature tested.

| Held | 50 °C | 60 °C | 70 °C |
|---|---|---|---|
| steel | pain 3.9 s, no burn | pain 0.5 s, burn 14 s | pain 0.25 s, burn 2.9 s |
| concrete | none in 120 s | pain 4.2 s | pain 1.0 s, burn 29 s |
| wood | none | none | none |

- **The order matches** ISO 13732-1's material ordering (**M**; check its numbers before using it as an anchor).
- **The 0.5 s step is too coarse.** At Δt = 0.5 s, steel at 70 °C burns 11% late (3.26 s against 2.93); at 0.1 s,
  2.3% (**D**, `geom.py contact_dt`).
- **The grid enters** through the face's temperature (the same face-skin gap as §1.2). Contact is decided by
  capsule–face overlap in metres, never by "the cell the hand is in".

### 1.4 Radiance in view, after line of sight

- **What is physical:** the stimulus is radiance arriving at the eye. Luminance is that radiance weighted by the
  human photopic curve V(λ), which is a receptor property, so it fails leak test 2.
  - The faithful form is radiance in a few fixed bands, with direction and visible solid angle (**D**).
  - Luminance is a stopgap, and fire_model §5.1 already names it ANALOG (**V**).
- **Glow spans eight decades (D, `geom.py luminance`; ε = 0.9, V(λ) by a Gaussian fit, M).**
  - 400 °C: 3×10⁻⁵ cd/m²; 525 °C: 0.006; 700 °C: 1.2.
  - 900 °C: 77; 1,000 °C: 382; 1,200 °C: 5,050.
  - A lit room is ~10–100 cd/m² (**M**): embers stand out only in the dark, so publish ambient radiance too, on a
    log scale.
- **Flicker can't be sampled.** Puffing runs at about 1.5·D^−½ Hz (**S**, 6b §1.1).
  - That is 4.7 Hz at D = 0.1 m and 1.8 Hz at 0.68 m (**D**). The 0.5 s step's Nyquist limit is 1 Hz, and flames
    are stateless per step (**V**, fire_model §4.1).
  - So flicker is a derived band frequency and depth, never samples (**D**).
- **Reduction:** the visible fraction is the share of rays from the eye to the emitter's quadrature points that pass
  the solid cells. Phase 2 smoke adds Beer–Lambert attenuation over exact path lengths (**V**, world_fields B).

### 1.5 Sound at the ears (Phase 2)

- **No wave equation:** at 0.05 m it would need Δt ≤ 8.4×10⁻⁵ s (**V**, benchmarking §2).
- **The model is event-driven** (**V**, world_fields). For each sound event:
  - octave-band source power;
  - a direct path, using the occlusion ray kernel;
  - portal paths over the room graph;
  - a reverberant term per room from V and its absorption (Hopkins–Stryker, **M**).
- **Stimulus:** band level and arrival time at each ear, the two ears ±0.0875 m apart on the head (**M**).
- **Arrival time is continuous world time.** Interaural differences are under 0.7 ms (**M**), so rounding to a
  step erases direction.
- **Divergence, OPEN:** Maxim takes a world-set normalised azimuth today (**V**, `base_humanoid.yaml`, Maxim
  origin/main 043eab8f, not refetched). Per-ear signals would replace it.

### 1.6 Concentrations at the nose and mouth (Phase 2)

- **Gas** is read only through `gas.at(zone)` and `gas.over(mask)` (**V**, world_model §2).
- **The breathing sample** is a sphere of tidal volume: 0.5 L (**M**) gives r = 0.049 m (**D**).
- **Concentration:** Σ_z C_z·overlap_z/V. Against a two-layer smoke zone (**V**, world_fields), the overlap changes
  smoothly as the interface crosses the face. There is no yes/no flip.
- **Near small sources,** well-mixed zones understate the concentration. A sub-zone plume object in metres is the
  answer (**D**).
- **Dose needs an owner decision.**
  - COHb and FED (Coburn–Forster–Kane; Purser; **M**) are tissue state, so they're the world's (**V**, fire_model
    §5.1).
  - Ventilation rate is physiology, which is Maxim's.

## 2. Body regions as geometry

Maxim's `base_humanoid` damages four parts: head, torso, arms and legs (weights 0.3 / 0.35 / 0.15 / 0.2; **V**,
origin/main 043eab8f). The world's regions can be finer and reduce onto those parts by area. Sized from the adult
Lund–Browder chart (**M**), on a DuBois area of 1.85 m² for 175 cm and 70 kg (**M**), with standard segment lengths
(**M**), the capsule radii come out plausible (**D**, `geom.py body`):

| Region (paired ×2) | Share | m² | Shape | Points |
|---|---|---|---|---|
| head | 7% | 0.129 | sphere r 0.101 | 6 |
| neck | 2% | 0.037 | r 0.059, 0.10 m | 2 |
| trunk front / back | 13% each | 0.240 each | elliptic cylinder | 4 each |
| buttocks (+ genitalia) | 6% | 0.111 | trunk capsule | 2 |
| upper arm | 4% | 0.074 | r 0.039, 0.30 m | 4 |
| forearm | 3% | 0.055 | r 0.033, 0.27 m | 4 |
| hand | 2.5% | 0.046 | box better than r 0.039 | 2 |
| thigh | 9.5% | 0.176 | r 0.065, 0.43 m | 4 |
| lower leg | 7% | 0.129 | r 0.048, 0.43 m | 4 |
| foot | 3.5% | 0.065 | r 0.040, 0.26 m | 2 |

- **Count:** 18 regions, 58 points (**D**); limbs get four, since flux falls with the cosine around a cylinder.
- **Fix the count by convergence:** add points until a region's burned fraction and its maximum stop changing, with a
  limb edge-on to a flame. That test is independent of dx. I didn't run it; §5 uses 48 points.

## 3. Grid independence: one cross-tier test per coupling

Each test runs at 0.2 / 0.1 / 0.05 m with the scene offset by 0, dx/3 and 2dx/3 (**V**, 5_numerics §3(d)). Each
binary outcome gets a band gate (**V**, world_model §3).

| Stimulus | Scene | Gated |
|---|---|---|
| Skin alone | grid-free unit test (**V**, fire_solid §3.2) | node and Δt convergence; Hoschke and Jasiński |
| Flame radiation | a prescribed-Q burner; a body at 1–3 m; then a wall cutting the view partway | flux against the analytic cylinder; visible fraction against the exact share; time to Ω = 1; the band of distances where "burn in 60 s" disagrees |
| Hot surface | a face skin held at a fixed T, a body parallel to it | flux against the parallel-rectangle view factor (**M**); a strict xfail on the cell-mean path until face skins exist |
| Contact | 70 °C steel, a hand capsule on its face, the slab edge at each offset | effusivity at long times; time to Ω = 1; contact area from overlap |
| Radiance in view | a glowing face behind a wall edge, the eye swept in 5 mm steps | visible solid angle against exact geometry; no stair-steps of width dx |
| Sound | two rooms and a door entity | V and A from integer cell counts; Sabine RT60 = 0.161 V/A (**V**, benchmarking §3); arrival time |
| Concentration | a sealed room with a source; an interface swept past the nose | the well-mixed C(t); the sphere-cap overlap |

## 4. Multi-rate on a fixed schedule

The schedule is part of the law. Every stage's phase is state, and so is every held field (**V**, fire_model §4.4).

- **Every substep (five per step):** skin columns, Henriques and contact, as §1.1 and §1.3 measured.
- **Every step:**
  - flames' E and shape (flames are stateless, **V**);
  - unoccluded analytic view factors;
  - convection;
  - breathing samples.
- **Every N steps, staggered by NPC** (NPC i recomputes on steps where step ≡ i mod N): occlusion per (emitter,
  region group) and the vision visibility set.
  - **The risk is motion.** A running NPC (~3–5 m/s, **M**) moves 6–10 m in four steps, and flux falls 2.6× from
    1 m to 2 m (**S**, body.md §2).
  - So near emitters, N drops to 1 by a criterion in metres decided from world state (allowed by D21, **V**), or the
    staleness is measured and gated. I didn't measure it.
- **Events:** sound per event. Topology changes invalidate held occlusion in the per-step topology batch (**V**,
  fire_model §8.2).

## 5. Cost per NPC per physics step

**D**, at the load above, with 48 points per NPC.

| Kernel | 10 NPCs | 100 NPCs | Basis |
|---|---|---|---|
| Skin, 45 nodes, 1 substep | 0.99 ms | 7.5 ms | measured (~35 ns per node-step) |
| Skin, 5 substeps | ~5 ms | ~46 ms | measured at 1 and 10 substeps, interpolated |
| Flame → points, 160-patch quadrature, per flame | 4.9 ms | 38 ms | measured (49–64 ns per point-patch) |
| Flame → points, analytic, 10 flames | ~0.2 ms | ~1.9 ms | 40 ns per pair (**S**, fire_model §8.3) |
| Occlusion, every point to 1 flame, sampled at dx/2 | ~82 ms | ~820 ms | measured (~50 ns per sample) |
| Occlusion, 9 rays per (flame, NPC), 10 flames | ~15 ms | ~150 ms | scaled from the measured rate |
| the same, N = 4 staggered | ~4 ms | ~38 ms | ÷4 |

- **The skin is affordable.**
  - A compiled Thomas solve runs at 7.5–8.5 ns per node (**S**, 5_numerics §4), which would cut 46 ms to about 10.
  - Sleeping quiet columns is safe: a subset solved alone gave the same bits as the batch (**D**, measured).
- **View factors must be analytic, or shared.**
  - For a convex emitter wholly above a point's tangent plane, irradiance is n·**q**, with **q** the irradiance
    vector. Computing **q** at a few positions per body shares it across the normals; it fails where the emitter
    straddles the plane (**D**, not measured).
- **Occlusion is the budget.**
  - Options: a coarse occupancy pyramid; a visibility cache keyed on the topology version (**V**, 5_numerics
    §4 (iii)); exact DDA path lengths, which Beer–Lambert reuses.
  - The server is reportedly already over real time on the big tile. That figure is **unverified**: 5_numerics
    couldn't find it. Stimuli need their own budget line, with work counters as the primary gate (**V**, fire_model
    §8.3).

## 6. What goes in the replay digest

**State, in the digest and the save:**
- pose and capsule placement;
- per point, skin node temperatures and Ω (f64);
- clothing nodes;
- dose accumulators;
- held occlusion and visibility, with each NPC's schedule phase;
- sound events arriving after this step;
- the bodies' ledger terms;
- cap and staleness counters.

**Derived, with a `derivation_version` (F15):** flames, unoccluded view factors, region reductions and the
SensorReadings.

**A check, not state:** a per-step hash of each NPC's stimulus vector (bits, unit, timestamp), which catches a bridge
change the world digest can't see (**D**).

**Reductions** use `bincount` or fixed-order sums (**V**, fire_model §8.2), in (body, region, point) order.

## 7. Open, by consequence

1. Per-point burned-area damage against Maxim's four parts and its derived `health`. This needs `world_set_axis` for
   sub-sensors (**V**, OD-C10).
2. Face skins on every exposed face before walls can radiate to an NPC or be touched (6.2).
3. Radiance bands against luminance; who owns ventilation rate; per-ear timing against azimuth.
4. An occlusion budget, and the staleness measurement, before any N > 1.
5. Point-count convergence; check the **M** numbers (ISO 13732-1, anthropometry, Lund–Browder).
