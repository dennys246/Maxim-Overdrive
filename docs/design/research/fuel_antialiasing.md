# Fuel anti-aliasing: MSAA against analytic edge coverage (2026-11-22)

**Why:** owner ruling 3 on `client_objects.md` §4.2: prototype MSAA and analytic edge coverage at step 8, and choose by
the stick-stability check and frame time. A 20 mm stick is 0.6–2.4 px across the zoom range, so it is drawn at the 2 px
floor, and without anti-aliasing its covered area per length jumps as the camera moves by less than a pixel: it crawls.

**Measured on** the owner's M2, Godot 4.7.2.stable.official.ed1daf0bf, Compatibility. The shipped shader's stability
was then measured under llvmpipe too, in the golden image built from `ci/godot-golden/Dockerfile` (below); its frame
cost there is not measured.

## The measure, fixed before measuring

Step 8's checklist holds the parameters, written before either candidate was measured (`delta1_five_lenses.md` S7):
the stick 20 mm x 1 m at 72 and 30 px/m, rig (scale 1.0) and laptop (0.5) tiers, the fuel coverage pass; 4 px bins in
world space along the axis, two dropped at each end; 8 camera offsets of k/8 output px on both screen axes; per bin
(max − min) / mean over the offsets; its 95th percentile; the reference an ideal line of the drawn width at exact area
coverage, at the same geometry; the bar 2x the reference. Code: `scripts/golden_stability.py`. The comparison's frames
came from a one-off tool, since removed, that drew its own stick: its MSAA row can't be rerun. The gate's
`client/tests/stability_check.tscn` draws the committed `fuel_stick` fixture, and `golden_stability.findings` judges
it, on every golden run.

## Stability (renderer ÷ ideal; the bar is 2.0)

| Mode | Rig, 72 px/m | Rig, 30 px/m | Laptop, 72 px/m | Laptop, 30 px/m |
|---|---|---|---|---|
| None (hard edges) | 2.05 | 1.18 | 5.78 | 6.11 |
| MSAA 4x | 1.37 | 1.71 | **4.54** | **3.31** |
| Analytic edge coverage | **1.09** | **1.00** | **1.20** | **0.78** |

The shipped rod shader (two passes, below) measures, through the gate's own scene:

| Where | Rig, 72 px/m | Rig, 30 px/m | Laptop, 72 px/m | Laptop, 30 px/m |
|---|---|---|---|---|
| M2 | 1.10 | 0.99 | 1.20 | 0.78 |
| llvmpipe, the golden image | 1.08 | 0.98 | 1.20 | 0.78 |

**Why MSAA fails the laptop tier:** at render scale 0.5 the 2 px floor is one rendered pixel, and MSAA's four samples
inside one pixel can't hold a pixel-wide line's area steady; the upscale to output pixels then spreads each step.
Edge coverage fades over exactly one rendered pixel at every scale (`render_pixel_m` = output pixel ÷ scale).

## Frame time (the golden view, the cell volume and 2,000 rods, 2x10^4 segments)

At the comparison, two runs each on a heavily loaded machine (load average 63–75), so the absolute values are rough:

| Mode | Minimum frame | Median frame |
|---|---|---|
| None | 4.08–4.12 ms | 4.72–4.77 ms |
| MSAA 4x | 4.53–4.54 ms | 4.93–5.01 ms |
| Analytic edge coverage | 4.07–4.19 ms | 4.75–4.88 ms |

The shipped pass, two runs each, `tools/fuel_aa/frame_time.gd` (its modes now `off`, `noflame`, `shipped`):

| Mode | Minimum frame | Median frame |
|---|---|---|
| Fuel pass hidden | 3.75–3.86 ms | 4.21–4.25 ms |
| Shipped, no flames | 3.88–3.99 ms | 4.30–4.42 ms |
| Shipped, with flames | 4.00–4.05 ms | 4.36–4.43 ms |

## Choice: analytic edge coverage on rods

It holds the bar on every tier, costs about nothing over hard edges, and touches only the fuel pass. MSAA would also
change the cell raymarch and so re-record every golden (§6.5).

## What this leaves open

1. **The measure discriminates weakly on the rig tier** (the owner's question, step 8's review fold). A hard-edged
   synthetic line scores 1.9–2.1x the ideal (`tests/test_golden_stability.py`), about the bar itself. With the
   shipped shader's fade deleted, rig measured 2.12x at 72 px/m and 1.16x at 30 px/m; the laptop tier's 5.8–5.9x is
   what fails the check. A regression confined to the rig tier would pass. The parameters were fixed before measuring,
   so they are not retuned here.
2. **Slabs have no edge coverage.** A slab's edges (a 20 mm thickness seen side-on) are hard. Coverage for a box's
   silhouette is a different calculation; step 8's checklist holds it.
3. **llvmpipe's frame cost** is unmeasured.
4. **Rod ends have hard edges:** the mesh widens radially only, and the stability measure drops the end bins.

## Depth: how edge coverage and crossing sticks were reconciled

Edge coverage blends, so rods draw in the transparent pass, and what writes depth decides who occludes whom.

| Depth from | Result | Measured |
|---|---|---|
| Every covered fragment (`depth_draw_always`) | each stick's faint fringe hid its neighbour in a pile | pile's laptop coverage 0.42 of rig's |
| Fragments at alpha 1 only (`depth_prepass_alpha`) | a floored stick writes almost no depth, so crossing sticks occlude by draw order | pile 0.91 of rig's; the crossing check fails on every tier (7.1–7.7 L* against 15) |
| An opaque core at coverage ≥ 0.5, the fade blended after it | the core shows its colour, a hard step in the edge's ramp | crossing passes; stability fails on laptop (2.55–2.62x) |
| **Shipped:** a depth-only pass at coverage ≥ 0.5, then the colour blended over the whole ramp | depth over exactly the drawn silhouette; a lone rod's ramp intact | crossing 42–73 L*; stability as tabled above; pile 0.89 of rig's |

**At a crossing the ramp is not intact** (step 8 delta review, client rendering D1, measured on the M2): the front
rod's outer fade is overwritten when the rear rod comes later in instance order (7 px on rig by up to 122/255, 55 px on
laptop by up to 66/255, in the committed fixture), and its inner fade blends against what is behind both rods, not
the rear rod (rig fuel-ID 132–208/255 where 255 is right). That brings back, at each crossing, the step at coverage 0.5
the opaque core was rejected for; nothing measures crawl in a pile. Step 8's checklist holds the choices: rods sorted
back to front per camera yaw (the outer half only), and a crossing in the stability measure.

## The goldens

The fuel goldens (`client/tests/goldens/compat-llvmpipe-mesa25.2.8-0ubuntu0.24.04.4-llvm20.1.2-godot4.7.2/*/fuel.png`)
were recorded 2026-11-22 from a golden run in an image built from this branch's `ci/godot-golden/Dockerfile`, and a
second run passed against them (24 shots, 6 goldens, cut-away). They count once CI's own golden job passes on them.
