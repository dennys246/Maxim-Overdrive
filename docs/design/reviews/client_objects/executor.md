# Executor review: client_objects.md (D-B2), round 1, at 51c9660

Reader: Executor. Scope: the diff `origin/main...HEAD` (merge base 2e67af2): `docs/design/client_objects.md` (4,368 words, under the 6,000 cap) and `tools/godot_probes/probe_fuel_objects*`. I ran nothing in the worktree. I ran the probe and four reviewer variants on a copy under `.../scratchpad/review_executor/probes` (windowed, Compatibility, Apple M2, Godot 4.7.2). A gate was running at the same time (load average about 12 on 8 cores), so my timings come from a loaded machine.

## Summary

| # | Severity | Location | One line |
|---|---|---|---|
| E-B1 | BLOCKER | §4.1, §2 | MultiMesh custom data is half-float on Compatibility, so a "first segment row" above 2048 is wrong (verified) |
| E-B2 | BLOCKER | §7.2 stick stability, §2, §4.2, §10 q3 | The probe's coverage measure gives 0.22–0.25 on a perfectly anti-aliased line, so the ≤ 25% bar measures the sampler (verified) |
| E-S1 | SHOULD-FIX | §2 "R3's sticks, 7.5–15 mm" | 0.75–1.5 cm is the gap between sticks, not their diameter, and the section cited is wrong |
| E-S2 | SHOULD-FIX | §6.1 | The named mechanism contradicts properties 1 and 2 |
| E-S3 | SHOULD-FIX | §4.1–§4.2, §7.2 burn-through | Shape sampled per vertex; the bar "over the burnt run" is undefined |
| E-S4 | SHOULD-FIX | §3.2 decoder checks, §4.1 | No check ties `segment_count` to length/ℓ; an unclamped k reads a neighbour's rows |
| E-S5 | SHOULD-FIX | §3.3 `char_fraction` | The denominator is ambiguous, and burn-through gives 0/0 |
| E-N1–N6 | NIT | various | Citations, a measured layout that differs from the design's, labels |

## BLOCKER

**E-B1. `docs/design/client_objects.md::§4.1` ("Per-instance custom data … whole numbers in floats, exact below 2²⁴") and §2 ("MultiMesh custom data … all work").**
The defect: on Compatibility, `INSTANCE_CUSTOM` reaches the shader at half precision. I wrote a reviewer probe (`rev_custom.gd`) with one MultiMesh quad per value, custom data r = v and g = v − 1, and a shader that tests `int(r+0.5) == int(g+0.5)+1`. Results: 100 ok, 2047 ok, 2049 fails, 4097 fails, 16385 fails, 20001 fails. The difference r − g reads 0 at every value from 2049 up, which is f16's integer spacing. The design's probe passed only because its first rows are 0, 50 and 100.
Failure scenario: a scene at the 2×10⁴-segment limit. Every object whose first row is above 2048 reads the wrong rows: another object's temperature, ignition and thickness, rounded down by up to 16 rows near 2×10⁴. Burn-through gaps and glow appear on the wrong sticks, and no check in §7 is built to catch it, because the fixtures are small.
Fix: *unverified*. Carry the row base some other way, for example as two exact halves (r + 2048·g) or in a per-instance data texture, and add a fixture whose first row is above 2048.

**E-B2. `docs/design/client_objects.md::§7.2` "Stick stability" (bar ≤ 25%), with §2's 38%/27%/23% and §4.2's "the floor alone doesn't remove the staircase: 38% → 38%".**
I reproduced the probe's numbers exactly: CV of the 20 mm rod 0.378 with no floor, 0.384 with the floor, 0.270 with MSAA, 0.228 with MSAA and the floor, and 0.048 for the 0.2 m rod.
The defect is in the measure. `_measure_rod` sums 17 pixels fetched at *rounded* positions along the normal. That is a digital line, and it aliases by itself. I applied the same sampler, in numpy, to an ideal line with exact pixel-area coverage at the probe's projected angle (32.7°, 60.5 px/m): it gives **CV 0.254 for a 1.44 px line and 0.223 for a 2 px line**. A hard, centre-sampled line gives 0.378, the probe's no-AA number to three digits.
So MSAA plus the floor (0.228) already sits at the measure's own floor for a perfect renderer. A correct analytic-AA renderer without the floor (0.254) would fail the bar, and so would any added error of about 0.03. The measure also flips §4.2's conclusion. Binned over area in 4 px axial bins, the real frames give 0.100 with no floor and **0.060 with the floor alone** (ideal lines: 0.060 and 0.027), so the floor alone does reduce the variation.
Failure scenario: at step 8, owner question 3 ("choose by the stability check") picks between MSAA and analytic coverage using a number that cannot tell either from a perfect line. A correct build can then fail the gate on sampler noise.
The bar was also set after the probe measured 0.23 (the design says so), and it is labelled `[engineering]`. CLAUDE.md's rule against post-hoc bars is written for physics and NPC bars, so this is not a rule break, but there is no derivation behind the 25%.
Fix: *partly verified*. A measure that integrates area, with bins wider than a pixel, and is calibrated against a synthetic ideal line drawn in the same fixture. I ran the 4 px binned version above, but I did not choose a bar.

## SHOULD-FIX

**E-S1. `docs/design/client_objects.md::§2` row "R3's sticks, 7.5–15 mm" (cited as `fire_model.md` §5.4), and the rows and claims derived from it.**
`fire_model.md` §5.4 says "R3's sticks at 0.75–1.5 cm *separate* by more than that". §6.2 gives the same numbers as R3a's dowel *spacings*. They are gaps, not diameters. The dowels are 3.2 mm (`research/fire_ladder/2_flame_spread.md:118`), and the exit's sticks are 20 mm (D-B2's own text: "can't draw a 20 mm stick").
Recomputed: a 20 mm stick is 0.6–2.4 px across the zoom range (1.44 px at the golden view), and a 3.2 mm dowel is 0.10–0.38 px.
What follows from the error:
- §2's consequence "thin fuel is narrower than a pixel at every zoom" is false for the exit's sticks.
- §4.2's "a 7.5 mm stick and a 15 mm stick look the same" rests on sizes no rung uses.
- At 120 px/m, a 20 mm stick (2.4 px) is wider than the floor, so the floor's effect depends on zoom.

Question 1's conclusion survives (still far below 12 px). Fix: restate the row from the sources above (*derived*).

**E-S2. `docs/design/client_objects.md::§6.1` (the four properties against the stated mechanism).**
- Property 1 says density "rises strictly with severity, from 0.25 to 1.0". "Octaves, each switched on above a severity" gives a step function, constant between the switch points. The four-block check can't see that.
- Property 2 says a groove drawn at c is drawn at every c′ > c. The fissure is drawn "wherever no octave edge crosses" the cell, so when a coarser octave's edge reaches a cell as c rises, that cell's fissure is removed. The groove disappears, which breaks property 2, the very thing the rule promises ("never swims").

Failure scenario: an isolated cell at c = 0.3 shows its fissure; at c = 0.5 an octave edge crosses the cell and the fissure moves. Fix: *unverified*. Either keep the fissure once drawn, or weaken the properties to match the mechanism.

**E-S3. `docs/design/client_objects.md::§4.1–§4.2` (the vertex shader reads `thickness_fraction`) and §7.2 "Burn-through: zero object-ID pixels over the burnt run".**
- The probe's shader samples thickness only at vertex rows. `CylinderMesh` with `rings = 50` has vertex rows every 1/51 of the length, and the discard uses the *interpolated* `v_thick`. So shape exists only at vertices, and burnt edges taper over a ring span.
- With one shared unit mesh per kind, a rod whose segment count exceeds the mesh's rings has segments with no vertex inside them. Those segments are never sampled. At 0.02 m segments, a 2 m rod has 100 of them.
- I ran a reviewer variant: a 20 mm rod with 100 segments on the same mesh. The runs I burnt each held a vertex row and did show gaps (empty axial columns at 12–15, 25 and 42–44). A segment with no vertex row can't show one; that part is *derived* from the shader.
- "Over the burnt run" isn't defined in screen space. For ideal geometry, the neighbours' round ends project ±0.54r along the axis, which is 1.6 px for the 0.1 m rod. So "zero ID pixels over the run's axial footprint" fails correct geometry, while a footprint shrunk by that amount passes. I measured zero lit pixels inside the shrunk band on the probe frames.
- The 9 of 56 empty steps the design cites is what ideal geometry would also give (12.1 px − 3.3 px). It doesn't show that the mechanism is right.

Fix: *unverified*. A per-fragment thickness fetch and discard, and a bar defined on the axial footprint shrunk by the projected radius.

**E-S4. `docs/design/client_objects.md::§3.2` "Checks the decoder runs" and §4.1 "k = ⌊s/ℓ⌋".**
The decoder checks Σ `segment_count` against the number of rows, but never checks `segment_count` = ⌈L/ℓ⌉ per object. The shader's k isn't clamped to the object's own count (the probe clamps s to 0.9999; the design doesn't say to). In f32, ⌊s/ℓ⌋ at s = L for L an exact multiple of ℓ gives k = count.
Failure scenario: a frame whose counts sum correctly but are distributed wrongly, or the last fragment of any whole-multiple rod, reads the next object's first row. Trust boundary: the client draws another object's state with no refusal. Fix: *unverified*. Add the per-object count check (with a stated tolerance in f32) and the clamp to the contract.

**E-S5. `docs/design/client_objects.md::§3.3` `char_fraction` = residue mass ÷ "the segment's solid mass".**
It's unclear whether that is the current or the initial solid mass. With the initial mass, PMMA's residue tops out at the inert fraction, 0.01 (fire_solid §4.2), and char severity never shows. With the current mass, a burnt-through segment is 0/0. The meaning of a wire name is contract (F1). Fix: *unverified*. Name the denominator and the value at zero mass.

## NIT

- **E-N1 `§7.2` "Tier agreement (§6.3, kept) … ID-mask areas".** The ID-mask areas are not measured today: `scripts/golden_measures.py` line 21 says "(§6.3's ID-mask areas are not measured yet.)", and B7 lists them as missing. "Kept" holds only for the ΔE half. The deletion "floor in rendered pixels" fails only if fuel gets its own ID mask.
- **E-N2 `§2`, `§4.1` timings.**
  - The upload was measured as RH + RGBA8 (two textures). The design specifies RH + three R8. My variant with the design's layout: 95–96 µs, against 46–77 µs for the probe's layout under the same load. Still far inside 3 ms.
  - The instance-build loop writes constants and computes no basis from axis and radius, so 0.46–0.57 ms is a lower bound.
  - Under load I measured 0.51–0.83 ms and 5.1–6.5 ms (the design: 0.46–0.57 and 4.4–5.8). Consistent with load, not a defect.
- **E-N3 the probe.** Its own check prints `s=10 red=0.259 expect=0.200` and `s=40 red=0.882 expect=0.800`. That's the probe's expectation being wrong, not the texture: the pixel at the projected axis hits the surface about 0.064 m (3.2 segments) further along, which predicts 0.264 and 0.864 (*derived*). The design is silent about it. Also, the probe tests R8 fetched in vertex and RH in fragment only, not "R8 and RH … in vertex and fragment".
- **E-N4 citations.**
  - §1 says "read at main 2e67af2", but `reviews/docs_contracts/rulings.md` (rows 10 and 79) exists only on origin/main after #37 (98e2342), not on this branch. The rows say what is claimed.
  - §2: fire_solid §1.1's 15.4–40 MB rejects a per-cell CSR for `contact`, not object lists for the raymarch.
  - §3.1: world_v2 §8's "bumps the registry, not the protocol" is stated for *optional* additions. The design makes every fuel table required, and world_v2 is silent on required additions.
  - §7.4: `client_rendering.md` §6.5's re-record-in-its-own-commit rule is about new builds, not a rendering change.
- **E-N5 `§7.1`** "rods of 10, 50 and 100 mm" are the probe's *radii*; §2 calls the same rods 20 mm and 0.2 m.
- **E-N6 `§7.2`** The header says every check is "proved by deletion", but the Speckle row has none.

## Checked and true

- **Zoom and sizes.** Zoom 30–120 px/m (size 6–24 m, `client_rendering.md` §1); golden view 72 px/m; a 0.1 m cell is 7.2 px; a 0.02 m segment is 0.6–2.4 px; a 1/255 front step is 0.0094 px at 120 px/m.
- **Row bytes.** `objects` 16, `rods` 36, `slabs` 52, `segments` 11, `flames` 38.
- **Table totals.** 32,000; 104,000; 220,000; 760,000.
- **Frame bytes.** 6 B × 230,400 = 1,382,400 (§4.2's 8 B less `surface_glow` and `burning`, 1 B each); the total of 1,738,400 is below 1,843,200 and below the 3.5 MiB cap (§4.3).
- **Crack groove (§6.2).** 0.02 × c × 72 = 1.44c half-width against the 0.75 px floor gives c ≈ 0.52, matching §5.4's worked 2.9 px at c = 1.
- **Probe numbers.** RH 3-D linear filter reads 0.5020 at the midpoint; 9 of 56 empty steps (8 with MSAA); every coverage CV the design cites, to three digits.
- **Existing code.**
  - `encoding.py::snapshot` sends `glow` computed from the cell-mean `frame.temperature` (§5.1's claim holds).
  - The client reads `surface_glow` and `burning` live (`cell_volume.gd`, `emission.gdshaderinc`, `cell_snapshot.gd`).
  - Unknown materials draw magenta (`cell_volume.gd`).
  - `golden_measures.py` has the glow (15 L*) and crack (8 L*, 2× edges, deletion by carving) checks plus speckle.
  - `client_fixtures.py` hand-places the fire channels.
- **Backlog.**
  - B5: 3 ms budget, broken by the `bricks` and `region_cell_bounds` loops.
  - B7: c = 0.25–0.96 draw the same grooves, the laptop draws none, and the laptop's flat white above 1,230 °C.
  - B40(2): particles unbuilt.
  - B42: as stated.
- **`reviews/step8_shader/fold.md`.** Decisions 4 (12 px, held), 5 (gain 7), 7 (severity by density, an edge in every cell) and 9 (the fire channels).
- **fire_solid.md.**
  - §1.1 tables, immutability, burnt-out rows stay.
  - §1.2 0.02 m strips, whole flip in 6.1.
  - §1.3 limits of 2,000 and 2×10⁴, no fuel in a solid footprint.
  - §2 `QUANTITIES` on cells.
  - §3.2 skins on contact faces only.
  - §5.4 `bincount` reductions.
  - §5.6 f16 and u8 columns, extensible, `burning` reserved.
  - §7's D-B2 row.
- **fire_model.md.** §4.1 minimum-member key, stateless; §9.2 tables; §10.2 6.4 before step 8; §7 fallback.
- **Other documents.**
  - `tile_and_client.md` §6.3 beats and §5.5's bed meaning of `crack`.
  - `world_model.md` §8 F1–F4 and F15.
  - `world_v2.md` §8: unknown optional columns ignored.
  - `boundaries.md` §8.3.
  - Snapshots at 2 Hz (`realtime_lanes_coop.md`).
  - D-B2 and A-S7 texts.
  - `FIELDS.md` exists.
