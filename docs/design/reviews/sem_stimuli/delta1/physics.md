# SEM stimulus design, delta round 1: Physics and resolution

Reader: Physics and resolution lens. Design `docs/design/sem_stimuli.md` v2 at `3e97ac9`; my round-1 report
`reviews/sem_stimuli/physics.md`; the author's `fold.md`; L3 (`research/sem_stimuli/3_world_side.md`);
`fire_solid.md` §1.2 and §3.2; `fire_model.md` §4.4; `src/simcore/core/scene.py` and `grid.py`;
`docs/standards_backlog.md` B28. Statuses are read from the v2 text, not the fold table. Tags: **V** read here, **M**
memory, **D** my derivation.

**Counts: 9 fixed, 5 deferred, 1 rejected, 2 open. New: 0 BLOCKER, 7 SHOULD-FIX, 5 NIT.**

## Status of round-1 findings

| Id | Status | Reason |
|---|---|---|
| B1 | fixed | §2.4 and §10 D11 make visibility per point; §8 permits sharing only within an angular bound, a header truth constant; §7.4 carries the half-shaded burned-area test. One definitional gap is filed as new N5. |
| B2 | fixed | §7.4 tests per coupling (occlusion, face emission, face contact, zone gas) with offsets 0, dx/3, 2dx/3, band gates, a wall edge, and red plants. The gate is right, but the law it gates can't pass it yet (new S1, S4). |
| S1 | fixed | §2.4 states accuracy in K, adds error-controlled substeps per point decided from world state, makes the tolerance a header truth constant, and requires convergence to 80 kW/m² and for contact. It sets no Ω target (new N1). |
| S2 | deferred | The scheme is fixed: §2.4 has one implicit system over the object's surface nodes and the skin at the tissue substep, with the heat booked from the object. The h_c citation and the ISO 13732-1 anchor (§11.2, correctly tagged **S** via CENELEC) are deferred. I accept that: the reason is no data before `data/`, and the trigger is the tissue law's PR, which must not merge without both. Two new problems in contact: S4 and S5. |
| S3 | fixed | §2.4: a point in partial contact gets contact and free sub-columns, weighted by area. |
| S4 | fixed | §8 refreshes visibility at each physics step and on motion past a declared distance, topology change or emitter change, decided from world state and never from NPC index. Staleness is measured against refresh every tick first. Motion refresh isn't costed (new S6). |
| S5 | fixed | §2.3 and §4.1 evaluate `tick` rows and tissue substeps at the tick's pose against held fields. Radiance is `tick` against held emitters, and §8 re-costs flux every tick. The within-tick pose convention is a new problem (new S7). |
| S6 | deferred | §2.4 and §8 cost the quadrature until an analytic form for arbitrary normals is measured against it, which also covers the n·**q** straddle. Self-shadowing goes in Q4 as a Known gap with a number. I accept that, triggered by the irradiance law's PR, which must record the number. |
| S7 | fixed | §3.2 fixes pooling by receptor class, with the maximum for `noci_heat`, and refuses a mean on a pain path. The fingertip test I asked for is missing (new N4). |
| S8 | deferred | §11.2 lists: trace the constants, grade Ω = 1 against two published times, record Jasiński's miss. I accept, triggered by the tissue law's data. The Weaver–Stoll figure §11.2 cites lacks its tag (new N2). |
| S9 | fixed | §2.2 computes radiance from surface temperatures only, and §11.2 Q3 makes the cell-mean path a strict red gate. §2.2 doesn't say what the `luminance` stopgap reads. It must obey the same rule; I'm noting this, not filing it, since luminance isn't v1. |
| N1 | open | The 58-point basis isn't applied to the visibility row. §8's "~65–165 ms" at 10 NPCs works back to L3's 48-point figure (2 × 82 ms = 164). At 58 points it's 198 ms raw, or 73–90 ms after the 2.2–2.7× correction (**D**). I accept deferring the tier statement to the measured cost; the point count is an arithmetic fix due now. |
| N2 | fixed | §2.4 puts a node at each declared depth, and convergence is stated at those depths. |
| N3 | fixed | §2.2 states the ITD shortfall (0.51 against 0.66 ms, **M**) and makes rise time ANALOG source data. |
| N4 | fixed | §2.2 drops `flicker_depth` until a cited law exists. §2.3 now gives the 2 Hz physics rate as the reason. |
| N5 | open | §3.1 books perfusion and metabolism as named *reservoirs* although v2 now has a core node. Blood returns to the core, so perfusion is a skin–core-node exchange, not an external sink. Booked as written, the ledger closes but the core node's energy is wrong (new N3). |
| N6 | rejected | I accept the author's rejection: burned area isn't a row. Its quantisation (1/n per region) now lands in the `apply_damage` delta, and Q1's point-count convergence covers it. |

## New findings

### SHOULD-FIX

**S1. Occlusion against cells has no designed law, and the shipped voxelisation puts a knife edge in the shadow.**
`sem_stimuli.md::§2.4` (incident flux row), `::§7.1` (irradiance law), against `::§7.4` (the occlusion coupling test).

The irradiance law marches rays through solid cells, sampled at dx/2 (L3 §5). The grid is binary occupancy, and
shapes are voxelised by cell-centre inclusion (`scene.py::Cylinder.mask`; backlog B28, **V**). So an occluder's edge
sits on a cell boundary, up to dx/2 from where it was authored. The design names no reconstruction. §7.4's test will
go red on this, as it should. But the design gives the law nothing that can pass it, and "fix the physics" then has
no designed path.

**Failure scenario.** A counter top authored at z = 0.9 m on the 0.2 m grid: the cells there span [0.8, 1.0), with a
centre at 0.9. The 0.9 m face falls on that centre, a knife edge, which B28 documents for cylinders. At offset 0 the
top lands at 0.8 or 1.0 by one ulp; at dx/3 and 2dx/3 it moves by 0.07 m steps. Take a flame 2 m beyond the counter
and an NPC 0.5 m in front of it. A 0.1 m shift of the edge moves the shadow line on the body by about
0.1 × 2.5/2 = 0.125 m (**D**). That is about half the spacing of L3's points. Points in that band change visible
fraction by order unity: per B1's table, shared against per-point exposure is 3× on burn time. So burned area flips
across tiers, the outcome class.

**Fix.** §2.4 should name the occluder representation:
- intact authored geometry is occluded against its primitives in metres;
- altered cells get a transmittance from volume fraction, once B28 lands.

Make B28 a prerequisite of the irradiance law in §11.1. Alternatively, reconstruct the surface from neighbours. A
grid-only march is the planted red case, not the law.

**S2. The tissue column has no outer boundary condition: no loss to ambient, no convection when inside a flame.**
`sem_stimuli.md::§2.4`, `::§3.3`.

v2 lists irradiance and contact as inputs, and nothing else. The word "convection" appears nowhere in v1 or v2.

- **The rest state needs a loss.** The core supplies k·ΔT/L ≈ 0.4 × 4/0.012 ≈ 133 W/m² through 12 mm of tissue to
  hold the surface at 33 °C (**D**, k ≈ 0.4 W/mK **M**, ignoring perfusion). With no loss, the steady surface is
  37 °C. §3.3 centres the stopgap body at 33 °C, so every reading sits 4 K off-centre. That also cuts the headroom
  to the C-fibre threshold (40.4 °C, Tillman) from about 7 K to about 3.
- **The high-flux case needs convection.** S1's 40–80 kW/m² case, the one that forced error-controlled substeps, is
  a point inside a flame. L3 §1.2 models it as h(d)·(T_f − T_s), decided per point against the flame's shape in
  metres. v2 dropped that.

**Fix.** Make the outer boundary condition part of the tissue law:
- natural convection plus radiative exchange to the Phase 1 still-air ambient (h ≈ 5–10 W/m²K, **M**, to cite);
- immersion convection per point, decided against the flame's shape in metres;
- the energy booked on `bodies`.

Add a closed-form test: the steady Pennes profile at ambient. Add the immersion case to the 80 kW/m² convergence row.

**S3. Joining at the core temperature starts every NPC 4 K warm for about 20 minutes of world time.**
`sem_stimuli.md::§4.5` (join: "tissue at the core node's temperature"; restart likewise).

A uniform 37 °C column relaxes toward its steady profile on L²/α ≈ (0.012 m)²/1.2×10⁻⁷ m²/s ≈ 1,200 s (**D**,
α **M**). Perfusion shortens this only modestly. An NPC that meets fire in its first minutes starts about 4 K closer to
the nociceptor threshold, so pain comes early. The A4 gain also sees an off-centre rest for those minutes. Both
change with join time, a scene-authoring accident.

**Fix.** Initialise each column at its steady profile for the local ambient, solved directly (a tridiagonal solve,
grid-free), at join and restart. Test that a joined NPC's tissue doesn't change in its first second at ambient.

**S4. Body contact with a solid cell face has no law; in v1 it would read the cell mean.**
`sem_stimuli.md::§2.4` (contact row: "the object's surface nodes"), `::§7.4` (the face-contact coupling),
`::§11.2` Q3.

Fuel segments have surface nodes, and cells don't. fire_solid §3.2 builds skins on contact faces only (**V**), so
6.0b gives a skin only where a segment touches a cell, never where a body does. An NPC leaning on a wall heated from
the far side exchanges heat with the cell mean. At 0.2 m that mean is badly wrong (P1: 104 against 48 MJ/m², **V**
via L3 §1.2, world_model §3), and it moves with tier: an outcome-class flip on "burns their back on the wall". Q3
covers radiation and glow, not contact.

The same holds for face emission. v2 never says whether hot cell faces radiate to bodies in v1. If they don't, "a hot
wall doesn't warm an NPC" is a Known gap needing a number. If they do, it's from cell means, which Q3 forbids.

**Fix.** State v1's choice for both couplings:
- (a) build a face skin on body-contact faces, exactly as 6.0b does for segments, with the same Robin rule and the
  skin's far node on the cell mean; or
- (b) no cell exchange in v1, with strict red gates on the face-contact and face-emission cross-tier tests, and Known
  gaps in `docs/architecture.md` carrying the P1 number.

**S5. The contact system's object-side nodes are sized for 1 s, not for the tissue substep.**
`sem_stimuli.md::§2.4` (contact row), `fire_solid.md::§1.2` (first node ≤ √(α·1 s)).

The coupled contact system uses the object's surface nodes as fire_solid sized them. For wood (α ≈ 1.2×10⁻⁷, **M**)
the first node is about 0.35 mm. The penetration depth over a 0.1 s substep is 0.11 mm, 3.2× finer (**D**). By the
first-node rule, that node's diffusion time is about 1 s. Through the first second of a grip it behaves as a lumped
store, not a semi-infinite surface, which is the effusivity physics that keeps 70 °C wood painless (T_c ≈ 40 °C with
e_wood ≈ 300, e_skin 1,327). This is the same mechanism that made the staggered 0.5 s scheme hurt on wood in my round
1 (S2). **Not measured:** the lumped node is finite and cools under implicit coupling, so the sign and size of the
error are unknown.

**Fix.** Give the contact system an object-side sub-mesh refined to the substep's penetration depth, initialised from
the object's profile and conservatively remapped back, with its energy on the ledger. Add object-side node count as an
axis of §2.4's contact convergence. If the measurement shows no outcome change at fire_solid's sizing, a convergence
row is enough.

**S6. Motion refresh multiplies the visibility cost for moving NPCs, and §8 doesn't cost it.**
`sem_stimuli.md::§8` (cost table; "whenever a body's sites move more than a declared distance").

A walking or running NPC moves 0.3–0.5 m per 0.1 s tick (**M**, 3–5 m/s). With any refresh distance under that, a
moving NPC re-casts visibility every tick: 5× the per-physics-step row. Ten NPCs running near one flame cost about
5 × 198 ≈ 1 s per world second raw, or 0.37–0.45 s corrected (**D**), against a ~140 ms target already "at or over".
The refresh distance is a physics tolerance whose staleness changes outcomes, and S4's motivating case was a running
NPC. So it must be chosen from a measured outcome error first and costed second, never chosen to fit the budget.

**Fix.** Add a motion-refresh row to §8 at a stated refresh distance and speed. Fix the visibility row's point basis
(N1 above). State the tier. The ray march scales as 1/dx and physics as about 1/dx³, so the ratio to physics is worst
on the 0.2 m tier.

**S7. Holding the end pose across the tick quantises contact onset to 0.1 s, coarser than the substeps' tolerance.**
`sem_stimuli.md::§4.1` step 3 ("tissue substeps over the tick just ended, at this tick's pose").

Contact that begins at tick T's pose is integrated over (T−1, T], so it starts up to 0.1 s early. Under the opposite
convention it starts up to 0.1 s late. Either way the error is ±0.1 s on onset. On 70 °C steel, pain comes at
0.19–0.25 s (round-1 S2 table; L3 §1.3), so the onset error is 40–50% of time to pain. That is larger than the 20%
error §2.4 rejected the fixed 0.1 s step for. Error-controlled substeps can't remove it, because it sits in the pose
schedule, not the integrator. For radiation it is a harmless one-tick shift.

**Fix.** State the convention and its bound in §2.4's accuracy statement. Then either:
- interpolate contact onset inside the tick from the body's in-tick motion, which the body law defines, as v1 already
  does for crossings; or
- accept ±0.1 s, recorded as a Known gap with the steel number, and exclude it from the K tolerance's convergence
  claim.

### NITs

- **N1. The K tolerance needs an Ω target.** `::§2.4`. Damage-rate sensitivity is ΔE/R/T²: 0.50–0.54 per K with
  55,000 K at 45–58 °C (**D**), and 0.92 per K with Weaver–Stoll's 93,534 K at 45 °C (**D** on **M** constants). So a
  0.1 K basal error is 5–9% on the Ω rate, and 1.25 K is +87% (Henriques) or about +216% (Weaver–Stoll). Derive the
  K tolerance from a stated Ω error and record both in the header.
- **N2.** `::§11.2`: "Weaver–Stoll's give about 0.9 per K below 50 °C" is untagged. It came from my round-1 memory
  (**M**). My check, 93,534/(318 K)² = 0.92, is **D** on **M** constants. Tag it **M** until the primary source is
  read.
- **N3.** `::§3.1`: book perfusion as the skin–core-node exchange (blood at core temperature, heat returned to the
  core), and metabolism as a source into the core node. Keep "reservoirs" for the ambient only (round-1 N5).
- **N4.** `::§6.3`/`::§7.4`: round-1 S7's test is missing: fingertip contact on 70 °C steel under `noci_heat` pooling
  gives a pain-path value above threshold before the fingertip point's Ω reaches 1. Add it to the gate list when a
  pain path exists. Until then, add a build-check test that a mean on `noci_heat` is refused.
- **N5.** `::§8`: "angular spread seen from the emitter" is undefined for an extended emitter. A 0.68 m flame at 1 m
  subtends about 38° (**D**). Define the spread as the maximum over the emitter's quadrature points, or from its
  nearest point, so the bound means one thing in the header.
