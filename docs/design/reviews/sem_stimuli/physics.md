# SEM stimulus design review: Physics and resolution

Reader: Physics and resolution lens. Design `docs/design/sem_stimuli.md` at `3357439`; research L1, L3 and L3's
scratch (`_durable/sem_research/scratch/`). I re-read the scratch scripts, re-summarised their JSON, and ran two new
probes on L3's column unchanged: `_durable/sem_review/probes/probe.py` (high flux, shared occlusion, partial contact)
and `stagger.py` (staggered against coupled contact). Tags: **V** primary source read here, **S** secondhand, **M**
memory, **D** derivation or measurement here.

**Counts: 2 BLOCKER, 9 SHOULD-FIX, 6 NIT.**

## What I checked and found right

- §2.4's numbers match the scratch. A 0.5 s step is +12.1% on pain at 20 kW/m². Steel at 70 °C burns at 3.262 s
  against 2.927 s (+11.4%). A region half at 15 kW/m² and half at 5 burns at 6.2 s, and one column at the mean at
  11.8 s (`convergence.json`, `contact_dt.json`, `mean_vs_points.txt`).
- The Henriques sensitivity of 0.50–0.54 per K at 45–58 °C holds for the constants used (55,000/T²).
- The receptor-depth argument (Tillman 1995) supports a declared depth.
- The zero-order-hold rule for fields is right, and so are crossings interpolated inside a step and Ω integrated on
  the linear reconstruction.
- Flame puffing at 1.5·D^−½ gives 4.74 Hz at D = 0.1 m (Cetegen and Ahmed's correlation, **M** for the paper).
- Integer-µs arrival times are fine against an ITD JND of about 10 µs (**M**).
- The tissue step as a truth constant, and every body integrated every tick, are right in kind (D20).

## BLOCKERs

### B1. Occlusion as costed is shared per (flame, NPC), so damage runs on a mean flux: 3× late

`sem_stimuli.md::§2.4` ("occlusion per (emitter, region group)"), `::§8` (the "9 rays per (flame, NPC), staggered
N = 4" row), against `::§2.4` "Damage is per point".

The design's own rule is that damage is per point, because Henriques on a mean is late. Its only affordable occlusion
is 9 rays per (flame, NPC), from L3 §5: one visible fraction shared by all 48 points. The per-point form costs 82 ms
per flame at 10 NPCs and 820 ms at 100. A "region group" is no better unless the groups line up with the occluder's
edge, and no rule in metres says they do.

**Failure scenario.** An NPC stands behind a waist-high counter with a fire beyond it, so the upper body is exposed
and the legs are shaded. With one shared fraction (0.5), every point gets half the flux (**D**, `probe.py` B; times
are first pain and first burn):

| Exposed points at | Per point | Shared fraction |
|---|---|---|
| 10 kW/m² | 3.4 s, 11.8 s | 12.0 s, 35.3 s |
| 15 kW/m² | 1.7 s, 6.2 s | 5.7 s, 18.7 s |
| 20 kW/m² | 1.1 s, 4.0 s | 3.4 s, 11.8 s |

That is 3× late on both, and pain arrives after the true burn. The error comes from averaging then applying a
non-linear law, CLAUDE.md's rule. It changes with ray placement against the cell lattice, so it is tier-dependent too.

**Fix.** Make visibility per point, or per point cluster with a geometric bound in metres (the points' angular
spread seen from the emitter below a declared limit), and cost that honestly. Keep the cost table's per-point row as
the baseline, and treat the 38 ms row as an optimisation still to be earned. Add a test: a body half behind an
occluder edge must give burned-area fractions within tolerance of per-point ray casting.

### B2. The per-row "generated cross-tier test" can't fail where dx doesn't enter

`sem_stimuli.md::§7.4` ("Generated tests per row: … a cross-tier test at 0.2/0.1/0.05 m").

The v1 rows (`tissue_temperature`, `exposed_area_fraction`, `burned_area_fraction`) read only the body, which is in
metres, and flames, which come from fuel objects in metres. A generated per-row scene with a body near a burner runs
identically on every grid. The test passes and guards nothing (charter: a test that cannot fail is a BLOCKER). The
grid enters only through L3 §3's four couplings:
- occlusion by solid cells;
- emission from cell faces;
- contact with a cell face;
- zone gas.

The design drops L3's per-coupling table. §0 claims "each stimulus a reduction in metres, with a cross-tier test",
and nothing in the design makes that test able to fail.

**Fix.** Freeze the tests per coupling, not per row. Use L3 §3's table: offsets of 0, dx/3 and 2dx/3, a band gate
for each binary outcome (world_model §3), and a wall edge cutting the view partway. Show each one red by planting a
cell-centre occlusion or a cell-mean face temperature. Strict red gates belong on the face-skin gap (Q3) and on
luminance from cell means (S9).

## SHOULD-FIX

### S1. "0.1 s is within 3% everywhere" is false, by L3's own measurement

`sem_stimuli.md::§2.4`; L3 §0 item 3 ("Five substeps bring every case within 3%").

In `contact_dt.json`, steel at 70 °C hits pain at 0.298 s at Δt = 0.1 s and 0.249 s at 0.005 s: **+19.7%**. Only the
burn is within 3% (+2.3%). At fluxes above L3's 20 kW/m² ceiling, which matter for an NPC walking through or beside
flames (a contact flux h(d)(T_f − T_s) plus flame radiation), the error grows (**D**, `probe.py` A, Δt = 0.1 s against
the reference):

| Flux | Pain | Burn | Largest basal error at a tick |
|---|---|---|---|
| 20 kW/m² | +2.8% | +0.8% | 0.31 K |
| 40 kW/m² | +6.4% | +1.8% | 0.63 K |
| 80 kW/m² | +8.9% | +2.5% | 1.25 K, which is +87% on the damage rate |

A fixed step bounds the error only over the range tested.

**Fix.**
- State the accuracy as a temperature error in K at the declared depths, plus Ω error. The pain threshold is Maxim's
  (T2), so "time to 44.8 °C" isn't the world's metric.
- Choose either a finer constant step, or error-controlled substeps per point decided from world state, which stays
  deterministic and grid-free (fire_model §8.1's "substep locally, per part"). Count them like cap events.
- Extend the convergence table to 80 kW/m² and to contact.

### S2. The contact coupling is unspecified and conflicts with fire_solid's scheme; contact conductance dominates

`sem_stimuli.md::§2.4` (flux row: "contact by a coupled column checked against effusivity"); `fire_solid.md::§3.2`
(Robin contact with the other side frozen at the step's start, once per 0.5 s step).

L3 measured one implicit coupled system at 0.005 s. Production contact touches another law's state: a fuel segment's
profile, or a face skin. That state steps at 0.5 s with the other side frozen. The design doesn't say which scheme
body contact uses, or who books the heat the hand draws from the object. Staggered against coupled, at 70 °C (**D**,
`stagger.py`):

| Object, h_c (W/m²K) | 0.005 s (≈ coupled) | 0.1 s staggered | 0.5 s staggered |
|---|---|---|---|
| wood, 10⁴ | no pain; basal peak 41.9 °C | 43.6 °C | **pain at 0.5 s; 49.9 °C** |
| steel, 10⁴ | pain 0.19 s, burn 2.58 s | 0.30 s, 3.10 s | 0.5 s, 5.0 s |
| steel, 10³ | 0.85 s, 8.6 s | 0.90 s, 8.7 s | 1.5 s, 9.0 s |
| concrete, 10⁴ | 0.33 s, 18.9 s | 0.5 s, 20.6 s | 0.5 s, 25.5 s |

- At 0.5 s, gripping a 70 °C wooden handle hurts when physically it can't. That is an outcome-class flip.
- At 0.1 s, steel still burns 20% late.
- The contact conductance moves pain on steel by 4.5× (0.19 s against 0.85 s), more than any step choice, and the
  design leaves it "a cited contact resistance (**M**)".

**ISO anchor, now V.** CENELEC Guide 29, Table A.1, reproducing ISO 13732-1, gives the 1-min burn thresholds:
uncoated metal 51 °C, ceramics, glass and stone 56 °C, plastics and wood 60 °C; 48 °C at 10 min for all. L3's
contact table has concrete at 60 °C with no burn in 120 s, and wood at 70 °C with none. At face value both contradict
ISO's outcome class. Part of the gap is configuration: L3's 20 mm insulated block cools, while ISO's surfaces are
held hot. The claim "the order matches ISO" is ordinal only. Effusivity is a short-time closed form and doesn't
validate burns.

**Fix.**
- Specify body contact as one implicit system over the object's surface nodes and the skin, at the tissue substep.
- Book the hand's heat out of the object's inventory, on the ledger.
- Cite h_c.
- Add ISO Table A.1 as an anchor, in its own configuration (held surface temperature, 1 and 10 min).

### S3. Partial contact on one point is a non-linear law on a mean

`sem_stimuli.md::§2.2` (`exposed_area_fraction`), `::§2.4`.

A hand has 2 points, each about 0.023 m² (L3 §2). A grip covers part of a point. One column per point with a blended
boundary (contact on fraction f, free on 1 − f) decides Ω for the whole area. Against near-isothermal 70 °C steel
(**D**, `probe.py` C, h_c = 2×10⁴), the blended column at f = 0.3 burns the *whole* point at 2.0 s. The truth is 30%
of the area at 1.47 s, so the burned-area fraction is 1.0 against 0.3. With low h_c it errs the other way.

**Fix.** Give a point in partial contact two sub-columns, contact and free, weighted by area. Or require contact site
sets fine enough that a point is wholly in or out, with a convergence test in metres (L1 already says hands need
fine patches). The design must say which.

### S4. Staggered occlusion keyed on NPC index breaks T11 and the "bit-identical" claim

`sem_stimuli.md::§8` ("Allowed, because bit-identical by construction", item 4: NPC i on steps ≡ i mod N),
`::§6.2` T11.

- Staggering changes values. That's why §8 itself gates it on measured staleness, so the heading is false for items
  3 and 4.
- Keyed on an index or `npc_key`, two identical bodies at identical poses feel differently. Vary entity ids or
  allocation order, as T11 does, and A's frame changes: T11 goes red by construction.
- **Failure scenario.** At N = 4 and 0.5 s per step, held occlusion is up to 2 s stale. An NPC stepping out from
  behind a wall into 20 kW/m² feels nothing for up to 2 s. Pain is due at 1.1 s and the burn at 4.0 s (reference),
  and the reverse case over-burns.

**Fix.** Re-evaluate on motion. An NPC's occlusion is recomputed when its sites have moved more than a declared
distance in metres, or the topology or emitter set changed, since the last evaluation. That rule is decided from world
state, independent of id, and meets D21. Measure staleness against N = 1 before any of this ships.

### S5. Pose and flux cadence are unspecified, and radiance's `physics` cadence contradicts the hold rule

`sem_stimuli.md::§2.3`, `::§2.4`, `::§8` (cost table).

- §2.4 rejects "one step per physics step on the end pose", which implies the flux follows the pose every tick. L3
  §4 and the §8 cost table compute view factors once per physics step. Over 5 ticks a running NPC (3–5 m/s, **M**)
  moves 1.5–2.5 m, and flux falls 2.6× from 1 m to 2 m (**S**). If the flux is held, the tissue integrates exposure
  at a stale position. If it's per tick, the analytic cost rises 5× (about 9.5 ms at 100 NPCs) and occlusion more.
- `spectral_radiance` is marked `physics` cadence. Under the design's own zero-order hold, emitters are held but
  angular position and visible solid angle depend on the eye's pose, the most pose-sensitive quantity there is. It
  should be `tick` against held emitters.

**Fix.** State that each tissue substep's flux is evaluated at that tick's pose against held emitters and held, or
motion-refreshed, visibility. Re-cost the table. Move radiance to `tick`.

### S6. "Analytic cylinder view factors" for arbitrary body normals is unverified

`sem_stimuli.md::§2.4`, `::§8` ("flame to points, analytic … ~0.2 ms, **S** fire_model §8.3").

- The 40 ns per pair comes from fire_model, for fuel-segment receivers. Closed forms for a cylinder to a differential
  element exist for particular orientations (vertical and horizontal targets, **M**).
- L3's shortcut, n·**q**, fails when the emitter straddles the point's tangent plane. L3 says so and didn't measure
  it. For a 0.68 m flame at 1 m, that happens for limb points within about ±19° of grazing, which is exactly Q1's
  edge-on case.
- The measured quadrature (0.7% accurate) costs 38 ms per flame at 100 NPCs, 200× the cited analytic figure.
- Self-shadowing (an arm shading the trunk) isn't modelled. Q4 covers only another body.

**Fix.** Cost the quadrature until an arbitrary-orientation form is measured against it. Add ray–capsule
self-occlusion, or record it as a Known gap with a number.

### S7. A binding's `area_mean` feeding a threshold receptor is a threshold on a mean

`sem_stimuli.md::§3` ("area-weighted mean or the maximum … the binding names it as an ANALOG"), `::§4.2`.

Maxim's pain is `min(1, (|v − set_point| − band)·scale)`, a threshold in sensor units. Bind a hand's points by
`area_mean` to a nociceptive sensor, and a fingertip at 60 °C beside a palm at 33 °C reads about 46 °C. Worse, a
burning point under the threshold-crossing area can show no pain, which inverts "pain leads damage" (fire_model §5.2).
Naming it ANALOG doesn't make it scale-free: the outcome depends on how many points the body declares. Warm and cool
summation may average; a heat-pain threshold must not.

**Fix.** Add a build check. A binding to any sensor feeding a pain or nociceptor path uses `max` or `single`. Add a
test: fingertip contact on 70 °C steel gives pain before the fingertip point's Ω reaches 1.

### S8. The damage model is unanchored, and its constants are secondhand

`sem_stimuli.md::§2.4` (Henriques P = 1.43×10⁷², ΔE/R = 55,000 K, **S**), `research/physics_spike/body.md` §3.

- body.md's only second-degree anchor fails: Jasiński's 17.8 s is "not reached in 18 s (the model is slower)". The
  "+5%" L3 cites is the first-degree case.
- The design frozen-defines `burned_area_fraction` as Ω ≥ 1 at the basal layer, which is fine as a definition, but
  every convergence number is against the model's own reference.
- I couldn't trace 1.43×10⁷²/55,000 to a primary source (searched; nothing found). Torvi and Dale's flash-fire model
  is commonly given with Weaver–Stoll's split constants (**M**). With those, the sensitivity below 50 °C is about
  0.9 per K, not 0.5, so §2.4's sensitivity and the step errors depend on the choice.

**Fix.** Before `data/`: name the primary source for the constants, and grade Ω = 1 against at least two published
second-degree times (Stoll and Chianta's curve, ISO 13732-1, ALOHA). Record the Jasiński miss as a Known gap with its
number.

### S9. Luminance and radiance from cell-mean temperatures is the hot-wall gap again, unrecorded

`sem_stimuli.md::§2.2` (the `luminance` stopgap), `::§11.2` Q3.

Q3 records the face-skin gap for flux only. Visible radiance is far steeper than σT⁴: L3's own table goes from
1.2 cd/m² at 700 °C to 77 at 900 °C, about ×8 per 100 K. A glowing char face at 700 °C inside a 0.2 m cell whose mean
is 200 °C publishes essentially nothing at 0.2 m and visible glow at 0.05 m, so "sees the embers" flips with the tier.

**Fix.** Radiance rows read surface temperatures only (fuel fronts, face skins). Give the cell-mean path a strict red
gate, and put this in Q3.

## NITs

- **N1. The cost table's basis.** It uses 48 points; §3 sizes the body at 58, so skin and per-point costs are
  understated by 21%. The occlusion rate was measured at dx = 0.1 m with samples at dx/2, so the cost scales as 1/dx
  and doubles on the 0.05 m tier. Say which tier the table is for.
- **N2. Declared depths and the mesh.** Depths that fall between nodes (Tillman's 0.15 mm) need interpolation on the
  column's profile, and node convergence was shown only at the 0.1 mm node. Require nodes at the declared depths, or
  include the depths in the convergence test.
- **N3. Sound.** A straight-line path difference between ears ±0.0875 m apart gives an ITD of at most 0.51 ms.
  Woodworth's spherical head gives 0.66 ms (**M**), so a world that owns "head shadow" needs a diffraction model or
  under-reports lateral ITD by about 25%. The onset rise time can't come from a 0.5 s simulation. It is source data,
  an ANALOG: say so.
- **N4. Flicker.** `flicker_depth` has no law and no citation; only the frequency has a correlation. Either cite a
  model of radiance modulation depth or drop the row until one exists. The 50–90 Hz fusion figure is beside the point:
  flame flicker at 1–10 Hz is far below fusion, and the reason for a descriptor is the world's 2 Hz physics rate.
- **N5. The ledger.** The skin column's Dirichlet 37 °C base and its perfusion term are reservoirs. "Δ(bodies)" needs
  core-flux and perfusion terms, or energy won't close.
- **N6. Quantisation.** `burned_area_fraction` steps in 1/n per region (a hand: 0, ½ or 1). Its band gate should use
  area in m², and Q1's point-count convergence should run before the row freezes its operating meaning.

## Sources

- [CENELEC Guide 29 (Table A.1, reproducing ISO 13732-1)](https://boss.cenelec.eu/media/Guides/CLC/29_cenelecguide29.pdf)
- [Torvi & Dale 1994 entry](https://data.zhenzhi.com/details/1/989209258) (scope only; constants not verified)
