# Step 8 shader, delta 2: Client and rendering, Performance

Scope: the fold over ce06d7b. The author committed it during this round as 37b24be (the fold) and d934e6d (the goldens). The commit holds exactly the tree I read: the diff stat matches (44 files) and the three `fire.png` md5s match the files I scanned. Statuses below are read from d934e6d.

I edited nothing else and did not run the gate, Docker or windowed Godot. Scratch work is in `<scratchpad>/d2/`:
- `emu3.py`: a float32 port of the new `walk_at`, `advance` and `skip_brick`.
- `sweep3.py`: the port at the golden camera on the alley arrays.
- `fuzz3.py` and `diffs2.py`: random grids against a float64 DDA that uses the shader's tie rule.

Numbers are labelled **measured**, **emulated** (measured on the port), **author-measured** or **derived**.

**Headline:** the BLOCKER is fixed. I found no cell skip, wrong axis or loop at the golden camera or under fuzz, and the goldens are clean. Four NITs remain.

## Fold status (set from the tree)

### Delta 1 findings

| Finding | Status | Evidence |
|---|---|---|
| BLOCKER N1: wrong entry axis after a brick jump | **fixed** | Empty bricks are now crossed by exact `advance` steps, so the axis is always the one crossed. **Golden camera:** 10,774 of 10,774 hits match the reference cell and axis (emulated). **Fuzz:** 200 grids, 60,000 rays; no cell crossed with positive length was skipped. Every disagreement is an exact tie (emulated). **Goldens:** dots went 47 → 0 on rig and on max, and laptop went 28 px → 0 (measured). |
| (the guard asked for) | **fixed, with gaps** | `speckle_findings` runs from `golden_run.py`; for what it misses, see N11. |
| NIT N2: nudge read a neighbour | **fixed** | The nudge is gone, with 0 cases at the golden camera (emulated). A narrower t = 0 case predates the branch (N9). |
| SHOULD-FIX N3: octave on a boundary | **fixed** | `crack_octave` adds hysteresis and sets `crack_spacing_m`; pixel sizes ≤ 0 are refused. The test exists, and the commit records it going red without hysteresis. Residual: N10. |
| SHOULD-FIX N4: severity has no shape on rig | **deferred** (owner decision 7, B7) | Trigger: the owner's decision. |
| NIT N5, N6, N8 | **open** | fold.md names each as left open. |
| SHOULD-FIX N7: in-place update untested | **fixed** | `test_a_second_snapshot_updates_the_textures_in_place` covers both cases: the same shape reuses the texture, a new shape allocates one. Contents are covered only by the golden run's fire and cold shots through one stage. |

### Round-one rows still open after delta 1

| Finding | Status | Evidence |
|---|---|---|
| C: hole at (543, 224) | **fixed** | The pixel is wall-coloured, and the guard is built. |
| C: laptop crack speckle; §6.4 rig-only | **fixed / deferred** | The shape part is fixed; severity is owner decision 7. |
| C: no deletion proof for the depth formula | **fixed** | 37b24be's message: `DEPTH = ndc.z` fails all three goldens (591–902 px over ΔE 10). |
| P: carve recomputes 27 feature points | **open** | Named in fold.md. |
| P: redundant texel reads | **open** | Named in fold.md. |
| P: golden job runtime | **fixed** | 32.3 s and 32.0 s (author-measured, emulated amd64). That is under the 60 s split threshold. I did not remeasure. |

Every other row keeps delta 1's status.

## The new traversal

**Correctness**
- `skip_brick` returns as soon as the walk leaves the volume or the brick. The `!inside(...) ||` short-circuit keeps negative cells away from the truncating `/ BRICK`.
- Leaving a 4³ brick takes at most 3·3 + 1 = 10 advances (derived), so the cap of 12 never binds. The emulated maximum was 10.
- The axis comes only from `advance`, so it can differ from the reference only at exact ties, where either axis is correct. All 119 fuzz disagreements had |t_a − t_b| < 1e-9 (emulated).
- `advance` strictly increases t, and nothing re-derives the cell after entry, so the walk cannot cycle (derived).

**`max_steps()` is still sound**
- Every outer iteration performs at least one `advance` or returns.
- A ray crosses at most nx + ny + nz boundaries in the box, so outer iterations plus inner steps total at most nx + ny + nz + 1. That is within the bound of nx + ny + nz + 4, which is 212 for the alley (derived).
- The inner steps don't count against the bound, but they spend the same crossing budget: they shorten the outer count rather than lengthen the walk.
- The longest walks were 41 outer iterations at the golden camera and 0.74 of the bound in fuzz (emulated).

**Cost per ray against the old jump**

| | Per ray | Notes |
|---|---|---|
| Brick reads (emulated) | 10.3 | Unchanged: 132,706 against the jump's 132,683 |
| Cell reads (emulated) | 6.1 | — |
| Inner advances (emulated) | 41 | 4.0 per skip on average, 10 at most |
| ALU (derived, rough) | about 600 ops | The jump cost about 500 |

- Inner trip counts of 1–10 per lane add divergence.
- The unchanged chain of dependent `texelFetch` reads should still dominate on a GPU, so this is not a finding.
- The author's llvmpipe drop, 50.7/64.7 s to 32/32 s, mixes in the whole fold. It does not attribute any speedup to the walk; only B5's GPU budget can.

## Crack octave hysteresis

- **Holding band:** octave n is kept while the exact value lies in (n − 1.1, n + 0.1).
- **Zooming out:** the switch comes at n + 0.1, when polygons are 12·2^−0.1 = 11.2 px. The "at least 12 px" docstring overstates by 7% (derived).
- **Zooming in:** the switch down comes at n − 1.1, when polygons are 25.7 px (derived).
- **Stability:** jitter within a factor of 1.149 never swaps the pattern. Crossing a boundary swaps the whole network once each way, as a wholesale pop, because the octaves' lattices are not nested. The octave seen at a given zoom depends on the direction of approach. That is inherent to hysteresis, and acceptable.
- **Default view:** 12 m at 720 px gives exactly 1.0 in doubles (measured with Python's `math.log`), so octave 1 from a fresh start.
- **Golden values:** 0.737 on rig and max, 1.737 on laptop. Both sit 0.163 octave outside any held band, so the frames don't depend on the order tiers pass through one volume (derived).
- **The spacing is 0 before the first set:** see N10.

## New findings

### NIT N9: `walk_at` still floors the non-entry axes at t = 0
`client/addons/engine/render/traversal.gdshaderinc::walk_at`

- **Mechanism:** the non-entry axes use `floor(p)`. An entry point exactly on an integer, on an axis the ray steps negative along, starts one cell on the wrong side. `boundary_t` is 0 there, but if that cell is drawn it is returned as the hit, though the ray only touches its edge.
- **Failure scenario:** one pixel at a material boundary on the volume's face shows the neighbour's material, crack and glow.
- **Reach:** 0 cases at the golden camera. Fuzz with lattice-exact origins found 168 edge-only hits in 200 grids, including `advance`'s inherent ties, and none skipped a real cell (emulated).
- **Not a regression:** ce06d7b floored the same way.
- **Comment:** "can never place the walk on the wrong side" holds only after entry.
- **Fix:** use `int(ceil(p)) - 1` on negatively stepping axes, as the entry axis does. Also correct `skip_brick`'s "at most 3 * BRICK cells" to 3·BRICK − 2.

### NIT N10: `crack_spacing_m = 0` doesn't "draw no crack pattern"
`client/addons/engine/render/crack.gdshaderinc::crack_edge`, `carve`

- **Mechanism:** dividing by a spacing of 0 gives inf or NaN, so `e` is NaN and `e > half_w` is never true. Every cracked cell is all groove down to `floor_t`.
- **What it draws:** a uniformly darkened 5 cm recess, `fissure_shade(0.05)`, at the depth written (derived). `lip` evaluates to 0, so the unwritten `Carve.away` is harmless.
- **Reach:** latent, because only `render_stage.gd` calls `use_pixel_metres`. A game caller would show it on every frame between `show_snapshot` and the first `use_pixel_metres`.
- **Related:** `pixel_m`'s shader default is a plausible 0.01. That breaks traversal's own rule that sentinels draw nothing.
- **Fix:** treat a spacing ≤ 0 as uncarved (solid at k = 0) and give `pixel_m` a 0 sentinel. Add a unit test that a fresh volume's cracked cell draws its face.

### NIT N11: the speckle guard misses laptop, fire and cut frames
`scripts/golden_measures.py::speckle_findings`

- **What it scans:** only `cold-rig` and `cold-max`.
- **What it misses:**
  - Laptop is excluded because its defects are 2×2 blocks, yet that is the form delta 1 measured there: 28 px in 7 blocks.
  - The 60 cut frames are skipped, though they cover four yaws: the widest sample of ray directions.
  - The fire frames are skipped.
- **Failure scenario:** a tie flip that depends on yaw or on resolution passes the gate.
- **Fix:**
  - Scan laptop after a 2×2 box-down at both offset parities. It finds 0 on the current golden (measured).
  - Scan the cut frames.
  - Scan the fire frames outside the crack and glow masks.

### NIT N12: §10 says six owner questions; fold.md lists seven
`docs/design/client_rendering.md` §10: change "Six" to "Seven"; the word count stays the same.

## Goldens (measured)

| Tier | Flat-face dots, ce06d7b → d1 → now | 7×7-ring dots now | Pixels changed vs ce06d7b / vs d1 |
|---|---|---|---|
| rig | 1 → 47 → 0 | 0 | 4,073 / 73 |
| max | 1 → 47 → 0 | 0 | 4,104 / 74 |
| laptop | 0 → 28 px → 0 | 0 | 23,770 / 194 |

- **Max (330, 742), black at sum 10:** a groove line on the cracked wall patch, not a hole. ce06d7b has the same at (331, 742).
- **End-wall cut hatching:** about a 4–5 px period on the foreshortened face, identical to ce06d7b. This is B7's known aliasing.
- **Otherwise:** no holes, speckle or new artifacts.

## Checked, nothing found

- **Grid edges:** odd grid sizes leave partial bricks through `inside` (fuzz on 5–59 cells per axis, emulated).
- **Axis-parallel rays:** a zero direction component never selects `FAR` while another axis is finite (emulated).
- **Octave refresh:** `crack_octave` reruns on every `show_snapshot` and `use_pixel_metres`. A held octave across a `cell_m` change bends the floor by at most 0.1 octave (derived).
