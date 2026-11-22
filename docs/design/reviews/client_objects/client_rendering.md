# Client and rendering review: client_objects.md (D-B2), round 1, at 51c9660

Lens: Client and rendering. I read the diff (`docs/design/client_objects.md`, `tools/godot_probes/probe_fuel_objects.gd` and its two shaders), all of `client_rendering.md`, the built renderer (`cell_volume.gdshaderinc`, `crack.gdshaderinc`, `emission.gdshaderinc`, `debug.gdshaderinc`, `cell_volume.gd`), `client/tests/support/render_stage.gd`, `scripts/golden_measures.py`, step 8's `fold.md` (decisions 1–9), backlog rows B5, B7, B40, B41 and B42, and fire_solid §5.6.

**What I ran.** Godot 4.7.2.stable.official.ed1daf0bf, Compatibility, Apple M2. Everything ran on a copy of `tools/godot_probes/` at `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/review_client/probes/`, with HOME and XDG moved there. Nothing in the worktree or its git state was touched.

- **R0:** the shipped probe, unchanged.
- **R1, `rv_probe.gd`:** MultiMesh custom-data precision.
- **R2, `rv_gap.gd` and `rv_gap2.gd`:** where the burn-through gap actually lands, per segment.
- **R3, `rv_laptop.gd`:** the shipped probe at `scaling_3d_scale` 0.5.
- **R4, `rv_msaa.gd`:** MSAA at render scale 0.5, with a quad that writes `DEPTH`.

Nothing ran under llvmpipe.

**R0 reproduces the probe's coverage numbers.** CV 0.378 with no floor, 0.384 with the floor, 0.270 with MSAA, 0.228 with both. The RH 3-D midpoint read 0.5020. Its timings came out above the document's ranges: 0.83 ms and 6.5 ms for the instance builds, 69 µs for the upload. That is plausibly machine noise, but §2's ranges are not a bound.

---

## BLOCKER

### B1. `client_objects.md::§4.1` ("both whole numbers in floats, exact below 2²⁴"): Compatibility keeps MultiMesh custom data at half precision

**Defect.** The claim is false on the pinned renderer. In R1 I set `INSTANCE_CUSTOM.r` to odd whole numbers and tested their parity in the shader:
- 3 and 101 came back odd, so they were exact.
- 2049, 4097, 16777 and 20001 all came back even, rounded to the f16 grid.

Godot's GLES3 storage packs colour and custom data into half floats. The probe never caught this because its first rows were 0, 50 and 100.

**Failure scenario.** With more than 2,048 segment rows (the world limit is 2×10⁴):
- Every object whose first row lies above 2,048 reads the wrong segments.
- The offset is up to 4 rows between 4,096 and 8,192, and up to 8 rows above 16,384.
- So one stick draws its neighbour's temperature, char and burn-through. A burnt-through gap shows on the wrong object, and nothing on the client can see it.
- The renderer goldens use small fixtures, so they would pass. Only the scenario goldens would draw it, and only past 2,048 rows.

**Fix (unverified).** Two possible routes:
- Split the row into two custom-data components, each ≤ 2,048. R1 shows values that small stay exact.
- Or index a per-instance row texture by `INSTANCE_ID`.

The contract sentence must also name the real precision. That sentence is the interface between the decoder and the shader, so this is contract, not mechanism.

---

## SHOULD-FIX

### S1. `client_objects.md::§4.2` (burn-away is shape) and `§7.2` (the burn-through check): with thickness read per vertex, the probe's own mechanism fails the check

**Defect.** §4.2 says the vertex shader reads `thickness_fraction`, and it cites "ten burnt segments of fifty left 9 of 56 pixel steps empty" as evidence. Two things go wrong:
- Ring vertices are shared between neighbouring segments, so the radius tapers across the segment beside each ring.
- The mesh is shared across the kind, so its ring count can't match every object's `segment_count`, and its rings don't land on segment boundaries.

The cited result itself shows the gap one segment short. R2 measured drawn width against a full width of 48 px:

| Case | Burnt segment(s) drawn | Live neighbours drawn |
|---|---|---|
| rings 50, count 50, segments 20–29 burnt | segments 20 and 29 at 0–24 px | segments 19 and 30 at 34–48 px |
| rings 50, count 7, segment 3 burnt | 0–2 px | segment 2 at 14–48 px, segment 4 at 10–48 px |
| rings 7, count 7, segment 3 burnt | 0–26 px | — |

So a single burnt segment never shows a clean gap. The `discard` on the interpolated `v_thick` only catches fragments exactly at a ring.

**Failure scenario.** §7.2's "zero object-ID pixels over the burnt run; live runs at least the floor wide" fails on a correct server state. Or a build loosens the check to pass. Burnt-through segments appear half-drawn, and live segments look thinned.

There is also a cost. Any per-vertex scheme needs the shared mesh to carry as many rings as the longest object has segments. That is about 624 vertices per instance at 50 rings, and about 1.25 M vertices a frame at 2,000 objects, on llvmpipe.

**Fix (verified, R2 with `rv_rod_frag.gdshader`).** Look the segment up in the fragment, k = ⌊s·count⌋ from a smooth axial varying, and discard where thickness is 0. Every case above then draws burnt segments at exactly 0 px and live neighbours at a full 48 px, whatever the ring count. Partial thinning above zero needs its own treatment (unverified). The contract gap is that §4.2 never says what is drawn at a segment boundary.

### S2. `client_objects.md::§4.2` and `§7.2` ("Stick stability ≤ 25%", "at every tier"): the bar comes from the rig tier only, and the laptop tier measures over it

**Defect.** R3 is the shipped probe at `scaling_3d_scale` 0.5, with the floor at 2 output pixels as §4.2 specifies. For the 20 mm rod:

| Setup | Coverage CV |
|---|---|
| no floor (3 empty steps) | 0.502 |
| floor | 0.388 |
| MSAA | 0.376 |
| MSAA and floor | **0.300** |

At 0.5, the floor of two output pixels is one rendered pixel. That is right at the rasterisation threshold: a 12-sided silhouette is 0.966–1.0 px wide, so shallow slants miss pixel centres. Bilinear upscaling then smears the result.

**Failure scenario.** The check fails on the laptop tier with the very mechanism the probe recommends. Or the build runs the check on rig and max only, which §4.2's "at every tier" forbids.

There are also two problems with the bar itself:
- It was chosen after the measurement (§7.2 says so), so it is a ceiling fitted to one tier.
- It measures spatial variation along a stick in one static frame. Shimmer under camera motion, the thing "stability" names, is not measured (§2 admits this), and no check would catch temporal crawl.

### S3. `client_objects.md::§6.1`: the crack-severity rule contradicts itself and owner decision 4, and the per-cell fissure works against severity

There are three defects in four rules.

**(a) Rule 2 ("additive") against the stated mechanism.** The fissure is drawn "wherever no octave edge crosses it". When severity rises and a finer octave switches on across that cell, the fissure is removed. So a groove drawn at c is not drawn at c′ > c. The rule and the mechanism the document names for step 8 can't both hold.

**(b) Rule 3 ("every cracked cell … isolated or not") against rule 4 and decision 4 (polygons ≥ 12 px).** At the golden view a cell is 7.2 px. Severity is carried by nested octaves at cell × 2ⁿ, the finest at 14.4 px (0.2 m), so the coarse octaves at mild severity cross few cells. A rough Buffon estimate (derived, unverified) for a 0.1 m face:
- At a 0.2 m spacing it expects about 1.3 crossings.
- At 0.8–1.6 m it expects about 0.16–0.3, so 70–85% of cells are uncrossed.

Those cells all get a fissure. A mildly cracked block therefore draws a fissure network at cell pitch, about 7 px polygons, which is the "all groove, no face" that decision 4 and the comment in `crack.gdshaderinc` rule out. Because a fissure line per 7.2 px cell is about as dense as the finest octave, edge density at c = 0.25 is set by the fissures, not the octaves.

My estimate is:

| Severity | Octave edges | Fissures | Total density |
|---|---|---|---|
| c = 0.25 | about 0.017 | about 0.11 | about 0.13 |
| c = 0.5 | about 0.05 | about 0.095 | about 0.15 |

That is a ratio of about 1.13, under §7.2's 1.25× per step. So the severity check probably fails between the mild levels.

There is a further cost:
- Any c > 0, down to 1/255, draws the full fissure.
- So diffuse low damage, say thermal stress across a heated wall, draws a cell-pitch grid across the whole face.
- That reads as severe, which inverts rule 1.

**(c) Rule 1 says "rises strictly … from 0.25 to 1.0".** Octaves switch at thresholds, so density is a step function, constant within each band. Only the four tested points can rise. The text promises more than the mechanism or the check delivers, and it says nothing for 0 < c < 0.25.

**Cross-tier and zoom.** The octave is picked per rendered pixel (`crack_octave`), so the laptop tier's finest octave is one coarser in metres. More of its cells are uncrossed, which makes (b) worse there: at the golden view a laptop cell is 3.6 rendered px and a 1.5 px groove fills about 40% of it. At 30 px/m the coarsest polygon is about 3.2 m, larger than the crate, so the mild levels on the crate differ only by fissures. "At every tier" is claimed but measured only at the golden camera.

**Does it close B7's two gaps?** It closes the isolated-cell gap. For severity, as written it risks reopening the gap with the inverse defect, and it conflicts with decision 4. The speckle guard is unaffected, because speckle runs only on cold frames.

### S4. `client_objects.md::§5.2` (burning) and `§7.2`: no check guards `ignited_fraction`, and never-colour-alone for burning is unmeasured

**Defect.** §5.2 says burning adds brightness, and §5.3 says that before 6.2 burning shows *only* by brightness. No §7.2 row measures it:
- The glow row zeroes emission.
- The flame-shape row needs 6.2.

**Failure scenario.** A build that ignores `ignited_fraction`, or renders it as a hue shift alone, passes every check. On the laptop tier with bloom off, an ignited surface above about 1,230 °C is already flat white, so an additive burning term changes nothing there. That needs either a bar or a recorded gap.

### S5. `client_objects.md::§6.3` and `§7.2`: char on thin fuel ("darkening, a luminance change measured in L*") has no check

**Defect.** The crack row covers only "charred faces ≥ 12 px". Every stick at every zoom falls below that, and no row measures char darkening on sticks or names the deletion that would fail it.

**Failure scenario.** A build that ignores `char_fraction` on rods passes. That leaves owner question 1's recommended answer ("accept darkening") with no guard behind it.

### S6. `client_objects.md::§7.2` ("Tier agreement … the ID-mask areas now include fuel, within 15%"; deletion "floor in rendered pixels"): the deletion may not fail

**Defect.** If fuel is pooled into the existing crate, glowing-region and player masks, a floor in rendered pixels doubles only the sticks' area on laptop, from 2 to 4 output px. Measured against the crate's area, that is likely under 15%.

**Failure scenario.** The deletion proof passes with the defect in place, which makes it a test that can't fail. The contract needs to say that the fuel ID mask is compared separately, per kind.

### S7. `client_objects.md::§2` ("texelFetch of R8 and RH 2-D textures in vertex and fragment … all work"): the probe's own row check printed a mismatch the document doesn't report

**Defect.** R0 printed `seg colour s=10 red=0.259 expect=0.200` and `s=40 red=0.882 expect=0.800`. Output is linear (R1: an albedo of 0.2 reads 0.1961), so this is not an encoding effect.

The cause is the probe's geometry. It projects the axis point, but the visible surface point is displaced towards the camera along a view direction that has an axial component, here about 3–4 segments. So the probe can't confirm that a fragment reads its own row. Together with B1 and S1, the row-mapping evidence for §4.1 is weaker than §2 states.

**Fix (unverified).** Write per-segment unique values and read them along a head-on axis. R2's layout does this.

---

## NIT

- **N1. `§4.2` floor in output pixels:** the existing `pixel_m` uniform holds metres per *rendered* pixel (`iso_camera.gd::pixel_metres`). The floor needs a second, output-pixel quantity, or the laptop tier gets S6's defect by accident.
- **N2. `§4.2` the slab floor:** a floor on world thickness doesn't give 2 px on screen for slanted slabs. Projected thickness depends on the normal's screen component.
- **N3. `§4.3` interpolation:** a cross-fade of `surface_temperature_c` keyed by row blends unrelated segments after an insertion shifts the rows. It must key on (`object_id`, `seg`) or skip on a layout change.
- **N4. `§4.1` and `§3.2` `state` = 1 (burnt out):** what a burnt-out object draws is unspecified: nothing, residue, or char.
- **N5. `§4.3` picking:** "also tests objects" doesn't say the nearer of the cell hit and the object hit wins. It also doesn't say the CPU must apply the same per-segment burn-through gaps, so a burnt gap shouldn't be clickable.
- **N6. `§7.2` speckle "extended to the fuel fixture's cold frame":** the table says every row is proved by deletion, but this one has "—".
- **N7. `§4.1` upload:** the probe timed one RH and one RGBA8 texture. The design uploads one RH and three R8. It is cheap either way, but the measured configuration isn't the one specified.

---

## Checked, nothing found

- **Nothing fed back.** The fuel pass, textures, cross-fade, flicker and particles are visual only. The pick sends `point_mm` in `kindle`, and the server re-validates it (6.4's nearest-surface query). The MultiMesh rebuild is local. No client value reaches the server except through validated intents.
- **Depth composition.** The raymarch writes `DEPTH` in the opaque pass (`cell_volume.gdshaderinc::fragment`). An opaque MultiMesh tested against it composites correctly in either draw order. R4 shows a `DEPTH`-writing material renders under 4× MSAA at scales 1.0 and 0.5 without errors.
- **MSAA at render scale 0.5.** R4: MSAA changes the output at scale 0.5 too (lit pixels 1,436 → 1,866), so Compatibility applies it with 3-D scaling. Its cost under llvmpipe is unmeasured, as §7.4 and owner question 3 already say.
- **Cut-away.** Fuel never sits in a wall (fire_solid §1.3), so never cutting objects is consistent. The cut-away ratio's reference frame keeps fuel on both sides, so the 95% check is unaffected.
- **Bloom and flames.** Additive HDR flames after opaque geometry feed Compatibility's glow, as emission does today. Over a black night the flame's ≥ 15 L* bar "above the fuel" can fail on deletion. The flame-ID pass removed with flames gives 0 pixels, so the shape half can fail too.
- **Never colour alone.** Glow is brightness: HDR, plus bloom on rig and max, with the laptop's white band already in B7. The flame shape is ID pixels. Burn-through is gaps, once S1 is fixed. Burning and char on sticks are S4 and S5.
- **Probe numbers.** Coverage CVs 0.378, 0.384, 0.270 and 0.228 reproduced. RH 3-D linear filtering reads 0.502. MultiMesh custom data and `texelFetch` compile in vertex and fragment.
- **§3.5 byte arithmetic.** It checks out: 6 B per cell, row sizes 16, 36, 52, 11 and 38, total 1,738,400 B.
- **§2 sizes in pixels.** These check out too: sticks 0.23–1.8 px, 0.54–1.08 px at 72 px/m, and segments 0.6–2.4 px.
