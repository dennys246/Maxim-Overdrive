# Design review: Executor (world_model.md)

Design: `docs/design/world_model.md` at `66310f4` (branch `phase1/design-v2`), design v3 part 1. Lens: Executor,
design-time. Are its claims about the code, its measurements and its sources true, and does the fold table fold
what each finding asked?

Read against: the six v2 review files (`reviews/world_v2/`), the research (`research/states_of_matter/`), the
committed probes, and the code on `.worktrees/act-validation` at `2f200b5`. Nothing in either repo was changed.

Re-measured here (numpy and scipy from the project venv, pymaxim 1.3.3, this machine; each run under 3 s):
- `probes/bench.py`, `bench2.py` and `bench3.py`, as committed;
- a heat-substep benchmark of my own (scratchpad, not committed): act-validation's `heat.substep` and `stable_dt`
  on a synthetic 16×10×4 m tile (floor, 0.4 m outer and interior walls, 40 crates of 0.6 m; 29% solid), against a
  cached-conductance substep with preallocated buffers, in f32 and in f64, plus the tracemalloc peak at 0.05 m;
- the sealed-room O₂ arithmetic in moles, for both 3×3×2 m scenes;
- the pymaxim import-binding count, and whether `datetime.datetime.now` can be patched.

Counts: **2 BLOCKER, 7 SHOULD-FIX, 6 NIT**, plus the fold-table audit.

## BLOCKER

### X1. The case against 0.05 m inverts its source: DLP measured 0.05 m at about 1.6× *faster* than real time

- **Location:** §1.1, first bullet ("0.05 m doesn't: about 1.6× real time in a quiet room even after caching, and
  slower during a fire (DLP, measured)"); §12 Q1 ("0.1 m, as measured above").
- **What the source says:** `determinism_lanes_performance.md`, "Performance": "**Quiet room:** about 0.3 s per
  0.5 s step, roughly 1.6× real time." 0.5 / 0.3 = 1.67: the simulation runs 1.6× *faster* than the world clock.
  "Slower than real time" applies only to "During a fire **with unbatched relabels**: about 0.55 s". §6 of this
  document batches relabels once per physics step (DLP S-6), so by this design's own rules the fire case is about
  0.3 + 0.047 = 0.35 s per 0.5 s step, still faster than real time.
- **The estimate also assumed v2's 6 substeps per physics step at max.** That count came from today's 64 substeps
  per 6 s turn (DX1), a rig minimum that D20 abolishes. Stability alone allows far more: `stable_dt` on the tile is
  173 / 47 / 12 s at 0.2 / 0.1 / 0.05 m (re-measured, concrete, wood and air). This document never states the
  substep rule at the truth resolution (see X4), so the cost of a physics step at 0.05 m is not known from anything
  it cites.
- **Failure:** the owner answers Q1 on a measurement that says the opposite of what §1.1 reports. 0.1 m may still be
  the right answer (dial headroom for cradles, memory of 512 to 640 MB at 0.05 m, 412 MB of transients today), but
  those are not the reasons given, and "real time" is not the bar: v1's time dial wants multiples of real time.
- **Fix:** restate: "0.05 m runs a quiet room at about 1.6× real time after caching (DLP, 6 substeps per step,
  surface exchange estimated), and about 1.4× during a fire with batched relabels". Then state the actual reason
  for 0.1 m as a dial ceiling per resolution, with the substep rule, and ask Q1 against that.

### X2. "Goes out" is defined as reaching a limit the ramp approaches only exponentially, so the sealed acceptance gate can't pass (S9 not folded)

- **Location:** §3, "'Goes out' is defined (S9)"; §10, the sealed half of the fuel acceptance test ("goes out by
  the §3 definition").
- **What happens:** §3 says flames are extinguished "when the zone's O₂ fraction falls to the extinction limit, with
  a ramp from 15% to 10%". With a linear ramp, HRR ∝ (X − 0.10) / 0.05, so dX/dt ∝ −(X − 0.10) and X reaches 0.10
  only as t → ∞. S9 says exactly this ("the fire never goes out in finite time") and asked for "out" to be defined
  as HRR below a declared W per m³ of zone for a declared time, under S4's band gate. The document cites S9 and
  writes the definition S9 rejected. If "the extinction limit" means 15%, the ramp below it is dead text.
- **Failure:** `phase1/fuel-combustion` implements the ramp, the sealed scene's HRR decays exponentially, and the
  gate "goes out" never turns green, or the implementer picks a threshold on the spot, which is a loosened gate
  chosen after seeing the result.
- **Fix:** define "out" as S9 asked (HRR per m³ below a declared value for a declared time), name it a binary outcome
  under the band gate, and put the numbers in `data/`.

## SHOULD-FIX

### X3. The sealed-room figures don't name their scene, and the two quoted in §3 and §10 come from different scenes

- **Location:** §3 ("the 3×3×2 m sealed scene burns 1.07 kg of fuel down to 15% and about 2.0 kg down to 10%"),
  §10 ("Its 5 kg of O₂ can burn only about 2.5 kg of the 130 kg crate"), §11.
- **Re-derived in moles** (CH₁.₇O₀.₇₂, water as vapour, 13.1 MJ/kg O₂, 12.4 MJ/kg):
  | scene | open volume | O₂ | burned to 15% | burned to 10% |
  |---|---|---|---|---|
  | cross-tier (crate + wall) | 14.18 m³ | 3.95 kg | 1.07 kg | 2.03 kg |
  | fiercest-fire gate (crate only) | 17.78 m³ | 4.96 kg | 1.34 kg | 2.55 kg |
  Every number in the document is right for *its* scene, and S9's are reproduced exactly (31.6 mol O₂ to 15%,
  60.1 mol to 10%). But §3 calls the cross-tier scene "the 3×3×2 m sealed scene", and §10's gate scene is also a
  3×3×2 m sealed scene. A reader takes 2.0 kg and 2.5 kg as a contradiction. E-N1 asked for exactly this ("Name the
  scene and the extinction point").
- **They are also not pure derivations.** Both rest on the pyrolysate formula and ΔH_c,eff = 12.4 MJ/kg, which §11
  lists as from memory, but §3 says "by derivation" and §10 marks nothing. The outcome class is robust (both ≪ 130
  kg), the figures aren't verified.
- **Fix:** name the scene at each figure; mark the two inputs *from memory* at the point of use (E11's fix).

### X4. The truth resolution has no stated time-step rule, so the cost, the dial and E2's order test all float

- **Location:** §1.1, §9, §10 row 3 (E2).
- **What happens:** v2 had 1 / 2 / 6 substeps per 0.5 s step, tied to the rigs. D20 makes rigs rendering tiers, and
  the document never says what sets the substep count at 0.1 m: stability (1 per step on the tile), a fixed
  minimum, or an accuracy criterion. E2 showed the answer moves the closed-form error by 3× to 10× and decides
  whether `tests/test_heat.py::test_error_falls_with_resolution` passes. The "headroom at real time" claim also
  depends on it (4 ms at one substep, 8 ms at two).
- **Fix:** state the substep rule for the truth and for the 0.05 m reference (they must use the same rule, or the
  convergence test measures time error too), and give the resulting cost per physics step and the dial ceiling.

### X5. "Headroom for zones, skins and fuel" is a projection labelled as a measurement, and its caches go stale in a fire (A-SF-8 is unfolded and unlisted)

- **Location:** §1.1 ("That leaves headroom … (DLP, measured)"); §9 ("cached conductances").
- **What happens:** the 14 ms and 3.9 ms are measured (reproduced below). The headroom for skins on *every* exposed
  face (§3 now requires them), zone exchange and fuel is not: DLP estimated the surface exchange at about 60 ms per
  substep at max as "not measured". P1's skin prototype used 16 nodes in the first 5 cm per face; nobody has costed
  that on the tile. And the cached-conductance figure assumes k and ρc change only on `set_material`. Architecture
  SF-8 showed that burning cells change k and ρc every step through fuel mass, char and bound water, so caches keyed
  to `topology_version` are stale or must be rebuilt per substep (today's 11–14 ms at 0.1 m). SF-8 is in this part's
  scope and isn't in the fold table or the "Not in this part" list.
- **Failure:** `phase1/sim-clock` builds topology-keyed caches; `phase1/fuel-surface` changes ρc per cell; heat
  silently uses the pre-burn properties, and the ledger closes anyway because the flux is still antisymmetric.
- **Fix:** label the headroom "derived, estimate" with the per-step budget written out; fold SF-8 (a property
  dirty mask, or rebuild per affected chunk as DLP S-6 also asked), and cost the face skin.

### X6. "Published once per physics step" recreates Architecture SF-9's stale-after-action bug

- **Location:** §9 ("Region reductions … published once per physics step as a frozen object").
- **What happens:** DLP S-12 asked for one bincount pass and a frozen publish. Architecture SF-9 showed that a cache
  refreshed per physics step returns pre-strike integrity to a sensor read between an action and the next physics
  step, which teaches the cerebellum that `strike` does nothing. §9 folds S-12 in the form SF-9 rejects; SF-9 is in
  neither list.
- **Fix:** key the publish to a cell-write version that actions and physics both bump (SF-9's fix), and list SF-9.

### X7. "The four ownership known gaps close" overclaims for a destroyed region

- **Location:** §5, last sub-bullet.
- **What happens:** act-validation's `docs/architecture.md` Known gaps has the three bullets (a destroyed region
  still claims its space; overlap judged on boxes, with its authoring cost; a carved region's centroid in air). §5
  decides "is this point on the region" and "does this fire touch the region" on the authored CSG. An authored CSG
  doesn't shrink when the crate burns away, so a strike on a burnt-out crate's old box is still "on the crate",
  which is the first gap restated. The id array removes the cell-ownership half; the reach and placement half needs
  the CSG intersected with what remains (live mass, or the sub-box recession of §3).
- **Fix:** say how a region's footprint shrinks with destroyed mass, or keep that gap open with its condition.

### X8. E8 is only half folded: the numbers the design leans on hardest still have no committed script

- **Location:** header ("measured (with its probe in `research/states_of_matter/probes/` or a review file)"); fold
  row "E8 probes: committed".
- **What happens:** the committed probes are the research's six (`bench*.py`, `exp1d.py`, `stefan.py`, `run2.py`),
  and they reproduce (below). The figures this part actually decides on are from the reviews: P1–P3 (`wall_skin.py`,
  `ablate2.py`, `pilot.py`: "from the scratchpad … not committed"), and every DLP number (14 / 3.9 ms, 412 MB, 23 /
  88 ms, relabels: "Scripts are in the session scratchpad, not committed"). E8 asked that measured numbers be
  reproducible. I could reproduce the DLP heat figures only by writing a new script.
- **Fix:** commit the review probes beside the research's, or mark those figures "measured once, not reproducible"
  until `phase1/verify` re-measures them.

### X9. E11 is partly folded: the list exists, but the marks at the point of use and the verification owner don't

- **Location:** §3 (sealed figures, ignition row's critical heat flux), §10 (2.5 kg), §11.
- **What happens:** E11 asked that each from-memory number be marked where used, and listed as material table v1's
  verification items. §11 lists them; only the extinction limits are marked in place; no PR owns the verification
  (row 5 says only "Material table v1, strict"). §11 also omits Carslaw and Jaeger's convective closed form, which
  physics.md lists as from memory and which is P1's benchmark, the reference for the skin.
- **Fix:** mark in place, add C&J, and make verification an item of row 5.

## NIT

- **N1. Severity totals.** The header's "19 BLOCKER, 73 SHOULD-FIX, 35 NIT" adds the files' stated counts for
  BLOCKER and NIT, but `wire_trust.md` states 4 BLOCKER and has 3 (F1, F5, F14) and states 13 SHOULD-FIX and has 15.
  By the findings themselves it is 18 / 73 / 35; by the stated counts, 19 / 71 / 35.
- **N2. Relabel cost.** §6 picks 6-connectivity, so its cost is 0.6 / 3.9 / 31 ms; the quoted ranges include the
  26-connected figures it rejects.
- **N3. Memory with f64 caches.** §4 mandates f64 caches, which DLP S-10 counts as the +24 B that takes the figure to
  the top of its range. The estimate is about 125 B/cell (80 MB at 0.1 m) plus the face table, which now holds
  skins on every exposed face, not only fuel faces.
- **N4. §9's 23 / 88 ms are at 0.05 m.** At the truth resolution the bincount is about 3 ms per field (bench.py).
  Quote the truth figure.
- **N5. The latent-correction cost grows with the transitioning fraction.** bench3 gives 5.5 ms at 0.1% of cells
  but 181 ms at 50%, nearly 3× the 65 ms full conversion. §4's "proportionally less" holds for the sparse case only.
- **N6. P2's "lit the crate".** The probe is a face-flux and closed-form t_ig calculation, not a crate run. "A
  corner pilot's face reaches T_ig in 1.5 s at 0.05 m and never at 0.2 m" says what was measured. At the truth
  resolution the corner pilot gives 6.3 s against 1.5 s at the reference, which is the band §3 must gate.

## Fold table audit (rows in this lens's scope, and factual rows)

**False:**
- **S9 "goes out" → §3.** §3 writes the definition S9 rejected (X2).
- **S8 → "§8 (identity), Known gaps".** The document has no Known gaps section and doesn't record breach venting
  with S8's numbers; §8's identity rule doesn't define `temperature_max` as a reduction in metres, which S8 asked.
- **"Every v2 finding within this part's scope".** Missing from both the table and the "Not in this part" list:
  E10 (relabel locality; in substance folded by §6 via DLP S-6), Architecture SF-8 (X5), SF-9 (X6), SF-10 (fines
  fraction; partly dissolved by D20, which should be said), SF-16 (rig-bound saves; D20 dissolves it, say so),
  SF-17 (= DLP S-11, folded but unlisted), wire F17 and F18 (presumably part 2), DLP N-1 (folded in §8), N-2, N-4,
  and the executor and physics NITs (only E-N8 is cited).
- **"DLP … S-5 (the thinking lane and its latency mode)".** DLP S-5 is settling per cluster (an order-independent
  rule and a fixed point), a rubble finding that belongs with §7, not part 2.

**Partial:**
- **E1 → §10.** Vented and sealed scenes are stated. Not folded: rewriting the gate's `ignite(power_w=500 kW)` in
  the new `ignite` semantics, and saying what an un-zoned scene's air is (E1: "the gate's meaning depends on that
  choice"). The sealed half rests on X2's undefined "goes out".
- **E2 → §10 (3).** The split order test and its ordering before sim-clock are folded. The re-derived figures and
  the architecture doc's closed-form numbers aren't, and the substep rule they depend on is unstated (X4).
- **E3 → §4.** Both numbers are now quoted with their conditions (correct). The PR that builds the per-cell
  property cache isn't named, and SF-8 makes its invalidation key wrong (X5).
- **E8 → probes.** Research probes only (X8).
- **E11 → §11.** List only (X9).
- **S6 → ignition row.** Losses and a critical heat flux are folded. Pinning t_ig against erfc, and moisture or a
  declared dry fuel, aren't.
- **DLP S-6 → §6.** Batching and 6-connectivity folded; rebuilding caches per affected chunk isn't.
- **DLP S-7 → §8.** Library versions and the dirty flag folded; part 1's outcome-deciding config (connectivity,
  zone exchange coefficient, gap aperture rules) isn't named as hashed config.
- **DLP S-12 → §9.** Folded in the form SF-9 rejects (X6).
- **E7 → "Not in this part".** It is about the burning law, which this part replaces (§3, ablation row). Answer it
  as superseded rather than deferring it.

**Folded as asked** (checked): A-SF-7 and E6 (bounding-box overlap and caching in sim-clock), DLP-B1 (§2, §6),
DLP S-3 (operator and relative tolerance), S-4, S-8, S-9, S-10, S-11, E-N8 (`wood_flaming`), P1–P3 evidence rows,
S1, S3, S4, S5, S7.

## Checked and found correct

- **14 ms and 3.9 ms at 0.1 m.** Re-measured: today's substep 1.4 / 11.3 / 97 ms and cached 0.5 / 3.4 / 31.7 ms at
  0.2 / 0.1 / 0.05 m, against DLP's 2 / 14 / 113 and 0.6 / 3.9 / 34.6 (my tile and properties differ; the ratios
  match). **f64 caches cost the same as f32** (3.2 ms at 0.1 m, 30.3 at 0.05), so §4's f64 mandate doesn't
  invalidate the 3.9 ms. Today's `stable_dt` costs 10 ms per call at 0.1 m.
- **412 MB** of temporaries in today's substep at 0.05 m: reproduced exactly (tracemalloc).
- **Research probes** reproduce: full H→T 65.4 ms at 0.05 m (63.9 quoted), 7.8 ms at 0.1 m; the sparse cached
  correction 5.5 ms (5.1 quoted); label of open cells 0.6 / 3.8 / 27.9 ms.
- **Memory:** 640,000 cells at 0.1 m × 100–125 B = 64–80 MB.
- **Sealed rooms:** 3.95 kg O₂ (cross-tier), 4.96 kg (gate), 1.07 / 2.03 kg and about 2.5 kg, 129.6 kg crate (X3
  for naming).
- **Quoted review numbers:** P1 (104 / 104 / 85 against 48; skin 47.9 / 48.1 / 48.1), P2 (1.5 s, never), P3 (0.205
  / 0.268 / 0.311 against 0.370; 0.370 with sub-boxes), S1 (0.30 / 0.35 / 0.375 against 0.40), S3, S7 / DLP S-3
  (0.18% loss, 0.0 with per-gap transfers), DLP S-9 (2.5e-6 °C), S-3 (about 1e11 J), S-12 (23 against 88 ms), S-6
  ranges, `wood_flaming` (2.15 in, 2.40 out).
- **`0.6 / 0.2` is 2.9999999999999996** in Python.
- **The tripwire facts:** 18 pymaxim 1.3.3 modules bind `uuid4` or `datetime` at import, and `datetime.datetime.now`
  can't be patched (`TypeError: cannot set 'now' attribute of immutable type`).
- **PR 1's eight review rounds:** eight round commits on act-validation (rounds 1 and 2, the review round, five delta
  rounds).
- **PR 1 code claims:** `scene._check_no_solid_overlaps` exists; reach and placement read authored footprints
  (`sem_env/bridge.py`); the three ownership gap bullets exist with the four items §5 names.
- **The 130 kg crate and the gate's unvented scene** (E1), and §11's verified items (Huggett, the ignition closed
  form and heat-balance constants, the voxel-sphere area limit, the two O₂ masses).
