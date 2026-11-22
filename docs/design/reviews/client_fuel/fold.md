# phase1/client-fuel round 1 fold: author's record

**The author's record, not a fold-status table** (O25): the delta round's reviewers set each finding's status from the
tree. Round 1 read `git diff 69483d9` plus the untracked files on 2026-11-22, in six lenses: `executor.md` (E),
`architecture.md` (A), `wire_integrity.md` (W), `client_rendering.md` (C), `performance.md` (P) and
`trust_boundary.md` (TB). Counts: 4 BLOCKER (TB-B1, TB-B2, TB-B3, P-B1), 32 SHOULD-FIX, 36 NIT.

**Corrections to the author's own claims, first.**
- "3.6–3.8 ms per rebuild" (§2, §4.1, §7.4) was the design probe's number, never this code's: the shipped rebuild took
  52–71 ms, plus 29–41 ms of checking (P-B1, P-S1). After the fold it is 14.1–14.5 ms with the check, at the limits (`tools/fuel_aa/rebuild_time.gd`; an earlier scratch probe read 13.8–14.2 ms).
- "Fringes must not write depth" (`depth_prepass_alpha`) traded one defect for another: a floored stick wrote almost no
  depth, so crossing sticks occluded by draw order (C-S1). The fold's crossing check fails that shader on every tier.
- "Draws magenta" for a recipe past the palette was false once 16 recipes existed (A3, S4, TB-N2, C-N5).
- §4.1's texel list described a layout the code never built (A2, S5, W-S2, C-S5, P-N4).
- C-S1's suggested fix, an opaque core at coverage 0.5, was folded first and broke the stability bar on laptop
  (2.55–2.62x against 2.0x). The shipped fix is a depth-only core (below).
- Two of the fold's own new tests passed vacuously at first: the headless renderer returns an identity transform and
  an empty box for any MultiMesh instance. Both now read the buffers FuelGeometry hands the pass.

## BLOCKERs

| Finding | Change | How verified |
|---|---|---|
| TB-B1 (kind decided by two rules) | `FuelSnapshot.geometry_rows(kind)` is the one rule; the pass, the flames, the checks and the footprints call it. Shared or out-of-range vocabulary ids are refused | client tests; deletion of each refusal goes red |
| TB-B2 (infinite rod sizes) | rod length and radius must be finite and positive, as slab sizes were | refusal tests over 0, −0.02, NaN, ∞ for every size column; deletion red (4 failures) |
| TB-B3, E-S3, C-N1 (`segment_count` 0) | refused | refusal test; deletion red |
| P-B1 (rebuild 52–71 ms) | columns decoded once (`to_float32_array`, `geometry_rows`); each MultiMesh buffer written in one assignment; the flame loop maps each object's base and direction once and writes only a flame's diagonal and origin | `tools/fuel_aa/rebuild_time.gd` at 2,000 objects, 2×10⁴ segments, M2 headless: insertion 14.1–14.5 ms (check 3.4–3.5 ms; flames 5.5–5.7 ms, rods 2.7 ms); steady frame 0.08–0.09 ms |

## SHOULD-FIX

| Finding | Change |
|---|---|
| TB-S1 (frame columns unchecked) | `FuelSnapshot.frame_problems()` every frame: each per-frame column holds its row count's size, `state` is 0 or 1 |
| TB-S2, P-S2 (trigger concatenation; unchecked frames) | `structure()`: the structural columns, row counts and vocabularies, compared natively against the last frame drawn, plus the region map. `FuelPass.show_fuel(snap, region_names)` owns the check and returns refusals; a refused frame draws nothing new (tested) |
| TB-S3 (row counts unbounded) | rows past fire_solid §1.3's limits (2,000 objects, 2×10⁴ segments) refused before any size is multiplied |
| TB-S4 (f16 ∞ drives glow to ∞) | the shader clamps `surface_temperature_c` to §3.3's [−273, 6000] |
| TB-S5, TB-N3 (untested refusals; ids unsorted) | every listed path has a case; `object_id`s must strictly rise |
| P-S1 (`problems()` 29–41 ms) | hoisted: 3.4–3.5 ms |
| P-S3, A9, W-S4 (`tools/fuel_aa` broken) | `frame_time.gd` repointed at the shipped pass (modes `off`, `noflame`, `shipped`) and rerun; `stability_frames.gd` and `measure.py` dropped, the record cites the gate's `stability_check.tscn` and says the MSAA row can't be rerun |
| A1 (two §7.2 bars rewritten without a ruling) | **open, the owner's**: burn-through lost its width clause; tier agreement moved to per object. Put to the owner in the hand-off |
| A2, S5, W-S2, C-S5, P-N4 (§4.1 stale) | §4.1 states the shipped layout: first row and palette slot; count and object row; ℓ's bits; `state` its own texture |
| A3, S4, TB-N2, C-N5 (magenta) | slot 15 is reserved for magenta: 15 real recipes; byte 3 asserted; a 17-recipe test |
| A4, S1, S2, C-S3 (flames ignore burnout and burn-through; burnout unguarded) | `segment_object_tex` gives each flame its object row; the flame collapses when the object is burnt out or its segment burnt through. Fixture: `rod_spent` at 1,200 °C reporting ignition, `rod_gap` with an ignited burnt-through run. Checks: burnout (< 15 L* over cold char) and dead flames. Deletions on real frames: burnout branch 84–96 L*; flame gate 243–322 px; its burn-through half 112–125 px |
| A5 (open items only in a research note) | slab edge coverage is in step 8's checklist; the rig-tier weakness is the owner's question; the hard-edge test is renamed and asserts the weakness, not a bar |
| A6 (design grew) | `client_objects.md` 5,179 words against 5,180; `client_rendering.md` 3,740 against 3,742. Cut: superseded §2 rows, §7.5, the stale B7 line, the MSAA bullet |
| A7 (llvmpipe claims) | the record and the design say what ran under llvmpipe: the goldens and §7.2's checks (stability 1.08, 0.98, 1.20, 0.78), not frame cost; the goldens' provenance is recorded |
| A8, W-N7 (checklist) | step 8's bullet splits built from remaining; the S5 deferral is gone (flames-off burning is built) |
| C-S1 (crossing sticks by draw order) | rods draw twice: depth only at coverage ≥ 0.5 (blended at alpha 0), then colour by coverage over the whole ramp; priorities order depth, colour, flames. Fixture: a hot stick across a cold log drawn later. Check: crossing ≥ 15 L*. Measured: crossing 42–73 L*; stability unchanged; the old shader fails crossing on every tier (7.1–7.7 L*) |
| C-S2 (flames vs blended rods; ±1000 m box) | flame `render_priority` 2; culling boxes from the data: rods and slabs from their buffers (`FuelGeometry.bounds`), flames from the objects' box grown by the flame height and half the widest flame. Tested, the bounds against a turned box's corners |
| C-S4 (slab floor buries the top) | the growth is anchored at the segmented face. **No fixture** of a stick resting on a slab: in step 8's checklist |
| E-S5 | as A2 |
| W-S1 (third reader refuses nothing) | `golden_fuel.segments` refuses an unknown format or version and a size or digest mismatch; `FIXTURE_NAME` is the one name `golden_run.FUEL_SCENE` uses; a test holds format and version to the writer's |
| W-S3 (floor in four places; footprints untested) | `FuelPass.drawn_half_m` is the GDScript rule the footprints and the stability scene call; `test_fuel_footprints.gd` holds the footprints to the geometry |
| W-S5 (red channel; bodies) | `object_areas` reads green, which the bodies' pure red doesn't write (tested). The encoding question (linear vs sRGB coverage per tier) is not tested: open |

## NITs

| Finding | Change |
|---|---|
| E-N1 | as A5 |
| E-N2 (in-place upload has no pixel gate) | not folded: a two-frame golden, in step 8's checklist |
| E-N3, W-N6 | `stability_findings` (now `golden_stability.findings`, A-N5) requires the four keys and eight offsets; a missing record, frame or footprint file is a finding, not a traceback; an ideal of 0 is reported |
| E-N4, TB-S3 | as TB-S3 |
| A-N1 | as C-S2 |
| A-N2 | each rod pass's render mode has its why in `fuel_rod.gdshaderinc` and the pass's header |
| A-N3 | as TB-S2 |
| A-N4 (row decoding three times) | partly: FuelSnapshot and FuelGeometry decode columns once each; FuelFootprints keeps its own per-row decoding as an independent oracle |
| A-N5 | as E-N3 |
| A-N6, W-N4 | a test holds `recipe_palette.tres` to `fuel_fixtures.RECIPES` |
| A-N7 | unchanged (noted) |
| A-N8 | the staged checklist commit goes first when signing works |
| C-N2 | slab axes must be perpendicular too (refused, tested) |
| C-N3 | rod ends: not folded, recorded here; the stability check drops the end bins |
| C-N4 | as C-S2 |
| C-N6 | `flame_colour.gdshaderinc` is the colour's one owner |
| P-N1, TB-N1 | `use_palette` rebuilds only when a slot changes (tested) |
| P-N2 | instance fields fetched in `vertex()` as flat varyings |
| P-N3 | Lab only over the masked pixels |
| TB-N4 (fixture reader paths) | not folded: test support, not a shipped trust boundary |
| W-N1 | `GoldenShot` is the grammar's one statement; `golden.gd` links it |
| W-N2 | the orphaned comment is gone |
| W-N3 | `FuelPass.View`; a fuel fixture in a cell mask is refused |
| W-N5 | a test holds the fuel glow constants to the encoder's |

## Evidence

- Client tests: 72 pass (headless) at the round-1 fold; 75 after delta 1. Python: the golden and fixture suites pass.
- Mac golden run (`--no-xvfb`, M2): PASS. Linux golden image, built from this tree under a session tag: PASS, 24 shots,
  6 goldens, cut-away, after recording the three fuel goldens; a first run had failed only on them (327–391 px blobs:
  the fixture gained three objects).
- Deletions, headless (16): each new refusal and pass mechanism; three survived at first (the magenta slot, the flame
  box's height term, the bounds' x term) and their tests were rewritten until red. Deletions on real frames (5):
  single-pass rods, the burnout branch, the flame gate, its burn-through half, hard edges: all red.
- Not verified: the coverage channel's encoding per tier (W-S5's first half); llvmpipe frame cost; the flames' render
  priority against the rods (C-S2's probe was the reviewer's, not rerun; no check can see it).

## Delta 1 (2026-11-22): what the author folded

The six lenses' delta reports are in `delta1/`; their status tables are the reviewers'. New findings and the author's
changes:

**Correction first:** the round-1 fold ran the rebuild before the per-frame check, so a refused frame was half applied
(TB2-B1, D-S1, W2-S1, E2-S1, found by four lenses independently), and the test written to catch it could not fail: it
"restored" a radius the fixture never had (TB2-B2, E2-S2).

| Finding | Change | How verified |
|---|---|---|
| TB2-B1 and its three duplicates | every check runs before anything is drawn: the per-frame check, then the structural check, then palette, rebuild and uploads | three tests; deletion of the order turns 2 red |
| TB2-B2, E2-S2 | the refused-frame test split in two: a refused structure, and a good structure with a refused frame (state 2; an insertion a row short), each asserting rebuilds, instance counts and the palette unchanged | deletion red |
| TB2-S1 | the pass keeps a deep copy of the structure it drew | test of an in-place edit; deletion red |
| TB2-S3 | `use_palette` stores the palette; the next frame drawn applies it, so a refused frame never recolours | asserted in the refused-frame test; deletion red |
| TB2-S2 (finite but huge geometry) | **not folded**: §3.2 needs a world-extent check that matches fire_solid §1.3, the design owner's; recorded for the owner |
| D-S2 (numbers from a scratch probe, in three places) | the probe is `tools/fuel_aa/rebuild_time.gd`; §4.1 holds the numbers, §7.4 and B5 link it |
| A2, W2-N1 | §4.1: a recipe without a colour, or past the palette, draws magenta |
| A8, W2-N2 | step 8's remaining list names §7.2's unbuilt checks and the groove view; §7.2's heading names all three modules |
| D1 (crossing rods' edge fade) | **recorded, not fixed**: the research record no longer claims the ramp intact at a crossing and gives the reviewer's numbers; sorting per yaw and a crossing in the stability check are in step 8's checklist |
| D2 (anchored slab growth hides in its support) | recorded in step 8's checklist with the stick-on-slab fixture |
| D3, PD-N3 | the rods' box grows by px · (1 + 1/scale), tested at a quarter-scale tier |
| E2-N3 | the flames' box allows flicker's 20%, `use_flicker` clamps to 0..1, a test holds the shader's factor to `FuelPass.FLICKER_HEIGHT` |
| E2-S3 (temperature clamp unguarded) | **not folded**: no fixture segment is non-finite; in step 8's checklist |
| W-S5's encoding half | in step 8's checklist, before the per-object area bar is relied on |
| C NIT 3 (rod ends) | in the research record's open items and step 8's checklist |
| D-N1, W2-N3 | `kind_name` deleted |
| D-N2 | `FuelGeometry.rod_flame_m` is the one rod flame-width rule |
| D-N4, W2-N5 | the ordering comments agree |
| PD-N1 | §7.4 links the research record's frame time |
| W N6 residue | the run's summary line names the stick-stability check |

Not folded, NITs, recorded here: D-N3 (`_row_texture` picks its material by key), D-N5 and W2-N6 (`golden.gd`'s own
pixel size), D-N6 (red vs green channel, uncited), D-N7 (a rationale inside §7.2's table), D-N8 (`fuel_fixtures.NAME`
a second copy of the fixture name), E2-N1 (the dead-flame check can name the wrong rod: they are 0.4 m apart, the
reach), E2-N2 (the palette-slot read has no golden-visible guard), PD-N2 (no close-zoom frame-time mode), TB delta
NITs (the limits are hand copies of `limits.yaml`; `_refused`'s loose substring).
