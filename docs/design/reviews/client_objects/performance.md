# Performance review: client_objects.md (D-B2), round 1, at 51c9660

Reader: Performance lens. I read the design, the probe and its shaders, B5, `client_rendering.md` §1, §4, §5.1–§5.6 and §8, `fire_solid.md` §1.1–§1.3 and §5.4–§5.6, `encoding.py` and `world.py`'s publication path. I ran everything on copies under `$D = /private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/b7bf205d-729f-449a-b38d-e830de582329/scratchpad/review_perf/`. Godot runs were windowed, opengl3 Compatibility, on the M2. The machine was heavily loaded throughout: load average 12 to 43, because the gate and other sessions were running. Absolute numbers are inflated, so I compare ratios taken under the same load. The repository and its git state were not touched.

**Summary.** I found 6 SHOULD-FIX, 3 NIT and no BLOCKER. The byte tables are all correct. The two measured client costs the design leans on, the rebuild and the upload, were not measured on the path the design specifies. Three costs on the design's path have no budget and no measurement:
- the decoder's per-frame key check;
- the vertex density that vertex-shader burn-away needs;
- the server's per-publish reductions.

## Findings

### P-S1 (SHOULD-FIX): `client_objects.md::§3.2` "Checks the decoder runs" (with §0.2, §4.1 "without a loop")

**Defect.** The decoder must check, on every frame, that "`segments`' key column [is] equal to the one the objects imply". The design does not say how often this runs or how. The obvious build is a GDScript loop over 2×10⁴ rows, and that alone exceeds the 3 ms decode-and-upload budget that §4.1 claims to respect. The same goes for "finite geometry, positive lengths, unit axes within 10⁻⁶": a loop over 2,000 rows, every frame, for data that is immutable.

**Measured** (`$D/proj/probe_perf_ext.gd`, two windowed runs, 50 repetitions each):

| Approach | min | median |
|---|---|---|
| GDScript key-check loop, 2×10⁴ rows (decode_u32 + decode_u16 + compare) | 3.1–3.2 ms | 4.4 ms |
| Native `slice ==` on the key bytes plus the geometry bytes against the last frame's (224 KB) | 30–31 µs | — |

**Failure scenario.** Step 7 builds the check as specified, as a per-frame loop. At the world limits, every 2 Hz frame then spends at least 3.1 ms on it on the M2, more under llvmpipe, before any upload. B5's already broken budget gets a third GDScript loop. Nothing in the design, and no meter, catches this; §7.4's budget rows don't list the decoder checks.

**Fix** (*verified* cost, via the native compare above). Run the structural checks only when the geometry and key bytes differ from the last frame's, the same trigger as the rebuild. Otherwise compare bytes natively.

### P-S2 (SHOULD-FIX): `client_objects.md::§4.1` "The rebuild is rare" (§2 row "Building 2,000 / 2×10⁴ instances"; §7.4)

**Defect 1: the cited number is not the rebuild's cost.** The 0.46–0.57 ms comes from `_time_buffers`, which writes eight constant floats per instance. The design's rebuild does more:
- decode 8 or 12 f32 per geometry row;
- validate the row;
- build a basis from the axis (two cross products and normalisations);
- compute the centre;
- write 16 floats, with the custom data.

I measured that path (`probe_perf_ext.gd` §4, 2,000 rods) at **3.6–3.8 ms min**. Under the same load, the unchanged probe gave **0.64–0.68 ms**, so the design's figure understates the real path about 5.7×.

**Defect 2: "rare" is false during a fire.** `state` is a column of `objects`, so every burnout changes the `objects` bytes and forces a full rebuild (§4.1: "this happens on insertion and on burnout"). In a fire of hundreds to 2,000 sticks, burnouts are spread over the burn. A rebuild then lands on many consecutive 2 Hz frames, in exactly the scene the exit test films. Those frames also carry the cell re-upload, which B5 already has at 14–46 ms for `bricks`.

**Failure scenario.** Step 8 reports the rebuild row as "0.46–0.57 ms per change". The real cost is about 3.7 ms on an idle-ish M2 and is paid on most frames of a burn. Frame time at the golden view then slips during the G-series beats, and the budget table has nothing that predicts it.

**Fix** (*unverified*). Measure the design's actual rebuild. One option is to keep `state` out of the bytes that trigger a rebuild; that is a choice for the author.

### P-S3 (SHOULD-FIX): `client_objects.md::§4.1–§4.2` (vertex-shader burn-away on "a unit cylinder or box")

**Defect.** The drawn radius is set per segment in the vertex shader from `thickness_fraction`. A vertex shader can only move vertices that exist. The shared unit mesh therefore needs at least one ring per segment of the *longest* object of its kind, and every one of the 2,000 instances pays that vertex count.

Nothing bounds segments per object: a 2.4 m plank has 120 segments, and a 10 m beam has 500. The design states no mesh density and no vertex budget. The probe hides the issue because its mesh happens to have `rings = 50`, equal to its segment count of 50.

**Measured** (`$D/proj/probe_vtx.gd`): 2,000 instances of the probe's own rod shader, golden camera, 1280×720, `--disable-vsync`, minimum frame interval over 120 frames, two runs.

| Rings | Vertices (about) | MSAA off | 4× MSAA |
|---|---|---|---|
| empty scene | — | 0.70–0.74 ms | 1.00–1.03 ms |
| 1 | 5.2×10⁴ | 0.94–0.98 ms | 1.61–1.63 ms |
| 50 | 1.3×10⁶ | 2.03–2.06 ms | 2.69–2.75 ms |
| 500 | 1.3×10⁷ | 9.67–9.73 ms | 10.29–10.45 ms |

That is on a GPU. Under llvmpipe, where the goldens are drawn, vertex work runs on the CPU and is unmeasured.

**Failure scenario.** A scene authors one long beam, or 6.2 adds long slabs, so the shared mesh is built at 500 rings. On the M2, the object pass alone then takes about 9 ms of a 16.7 ms frame, before the raymarch. On llvmpipe the golden job's timeout or frame time breaks. If the mesh is instead built coarser than an object's segment count, burn-through gaps silently disappear on long objects, and that is a correctness failure.

**Cross-lens note for Client and rendering.** Even with rings equal to segments, ring-sampled thickness interpolates across each boundary. Ten burnt segments of 50 should leave about 11.2 of 56 steps empty; the probe left 9 (8 with MSAA). I reproduced both. The gap is drawn roughly one segment short, which bears on §7.2's burn-through check.

**Fix** (*unverified*). State a vertex budget and a mesh-density rule in §4.1, and measure the pass at the world limits under llvmpipe.

### P-S4 (SHOULD-FIX): `client_objects.md::§3.5` frame bytes vs `client_rendering.md::§4.3` join cap and inbound buffer

**Defect.** The server "refuses at `join` a shape whose frame exceeds" 3.5 MiB. That check is a function of shape only: Σ(dtype bytes) × cells plus a header bound. Frames now also carry fuel tables, which grow during a session as `imagine` inserts objects, up to the world limits. The design computes bytes at one shape (230,400 cells) and never says that the join check must count the fuel tables at the limits.

**Recomputed:**

| Quantity | Bytes |
|---|---|
| Fuel tables at the limits, no flames | 32,000 + 104,000 + 220,000 = 356,000 |
| Fuel tables with the flame bound §3.4 states | 1,116,000 |
| Largest shape admitted on cells alone (6 B per cell) | 3,670,016 / 6 = 611,669 cells |

**Failure scenario.** A 600,000-cell shape passes the join check: 3,600,000 B of cells. Mid-session, objects are imagined up to the limits. The frame reaches 3,956,000 B, over the 3.5 MiB cap that the server promised to enforce. With 6.2's flames at the stated bound it reaches 4,716,000 B, over the client's 4 MiB `inbound_buffer_size`, and the WebSocket drops mid-fire.

**Fix** (*unverified*, arithmetic only). The join check counts fuel at the world limits. That admits 552,336 cells without flames, or 425,669 cells with the flame bound.

**Related, pre-existing, not D-B2's:** at the max profile of about 5×10⁶ cells, or the 0.05 m tile's 1,843,200 cells, the cell frame alone is 30 MB or 11.06 MB, both refused at join. "B5 gates the bytes per profile" (§3.5) should not read as though a max-profile frame exists.

### P-S5 (SHOULD-FIX): `client_objects.md::§3.1` "The core publishes the per-segment reductions … on the frame" and `§9` row 6.0b

**Defect.** The reductions run where frames are published. `world.py` publishes a frame on every window that closes (`grid.on_close(self._publish)`), which means every applied intent and every physics step, not once per client message. `thickness_fraction` and `char_fraction` reduce over nodes: 4.8×10⁵ padded nodes at the limit, with several density components. The design costs none of this, and B5 has no row for it, although fire_solid §1.3 sets the whole solid's budget at 25 ms per 0.5 s step.

**Measured with a stand-in** (`$D/red.py`, numpy, synthetic layout: 2×10⁴ segments, 2 parts, 12 nodes per part, 3 components; load average about 12):
- the four reductions plus quantization: **13.3 ms min** of 50;
- each node-level `bincount`: 2.4 ms.

This is a stand-in, not the FuelStore's layout. Idle numbers will be lower, but the shape holds: O(nodes) per publish.

**Failure scenario.** A burst of intents (strikes, or several NPCs acting in one step) closes several windows in one step. Each recomputes O(nodes) reductions that no client reads more than twice a second. The physics step exceeds its budget at the limits. The cause is invisible because the cost sits in "publication", not in the solid.

**Fix** (*unverified*). Cost it, and give it a B5 row. Whether to cache by fuel version or compute lazily at encode is the author's choice.

### P-S6 (SHOULD-FIX): `client_objects.md::§5.3` "A flame is a volume" and `§7.4` budgets

**Defect.**
- Flames are additive, depth-tested volumes ("a camera-facing stack") drawn after opaque geometry. Their cost is fill: stack layers × covered pixels, summed over flames. The count is unbounded here ("6.2 bounds the count").
- §7.4's frame-time row names the object pass and anti-aliasing but not flames.
- No trigger or owner row records that 6.2 must bound the cluster count by a client draw budget, not only by bytes.

**Failure scenario.** 6.2 bounds clusters by physics alone, say hundreds of clusters in the crate fire. Each is a stack of N quads over tens of thousands of pixels. On llvmpipe, which is fill-bound, the golden frame's time or timeout fails at 6.2's first fire golden. The design that owns the flame draw (§5) recorded no budget for it.

**Fix** (*unverified*). Add flames to §7.4's frame-time row, and put a "6.2 states a cluster bound against the client fill budget" requirement in §9's 6.2 row.

### P-N1 (NIT, but a mislabelled `[ran]`): `client_objects.md::§4.1` and `§7.4` "45–54 µs at 2×10⁴ rows [ran]"

The probe uploads one RH and one RGBA8 texture, as §2 states correctly. §4.1 specifies one RH plus three R8 textures and cites the same number. I measured the design's configuration (`probe_perf_ext.gd` §1): **131–161 µs min**, against **69–77 µs** for the probe's two-texture upload under the same load. That is about 2×, because the cost is per texture.

This is still well inside 3 ms, so it causes no budget failure. But a `[ran]` number is attached to a configuration nobody ran.

### P-N2 (NIT): `client_objects.md::§3.5` "plus headers"

The frame header lists every array by name, dtype, offset and size. The fuel tables add about 45 column entries: objects 7, rods 9, slabs 13, segments 6, flames 10. `client_rendering.md` §4.2's gate is "Σ(dtype bytes) × cells plus a header bound, taken from the registry", so that bound must grow with the registry. This should be said, or the frame-size gate under-bounds. The effect is a few KB.

### P-N3 (NIT): probe timing methodology (`probe_fuel_objects.gd::_time_buffers`)

The minimum of 50 matches `client_rendering.md` §8's rule, so the method is consistent. Weaknesses for this design:
- **What is timed is not the design's path:** P-S2 and P-N1.
- **Only the minimum is reported.** The key-check loop's median was 4.4 ms against a 3.1 ms minimum. A per-message hitch budget is better stated with the median beside the minimum.
- **Exclusions are fine but unstated.** It excludes the GPU side (Compatibility `update` is a driver copy; the GPU meter reads 0 per §8) and the first-upload warm-up. Both are acceptable but should be stated in §2.
- **"Uploads every frame" (§0.2, §4.1)** means every cell-frame message (2 Hz), not every render frame. The wording invites the wrong reading.

## Checked, nothing found

**Byte tables (§3.5), recomputed:**

| Table or total | Recomputed | Design |
|---|---|---|
| objects: 4+2+2+1+1+2+4 | 16 B | 16 B |
| rods: 4 + 8×4 | 36 B | 36 B |
| slabs: 4 + 12×4 | 52 B | 52 B |
| segments: 4+2+2+1+1+1 | 11 B | 11 B |
| flames: 6 + 8×4 | 38 B | 38 B |
| At the limits: 32,000 + ≤104,000 + 220,000 + ≤760,000 | — | matches |
| Cells: 6 B × 230,400 | 1,382,400 B | 1,382,400 B |
| Frame before flames | 1,738,400 B | 1,738,400 B |
| Today's frame (8 B × 230,400) | 1,843,200 B | 1,843,200 B |
| With flames at their stated bound | 2,498,400 B, under 3.5 MiB at this shape | — |

**Bytes per second:** 3.48 MB/s at 2 Hz before flames, at most 5.0 MB/s with them, on localhost. The `tick` head-of-line delay is smaller than today's, because the frame is smaller.

**Rebuild trigger compare:** native compare of the geometry bytes (about 136 KB) plus the segment keys took 30 µs (P-S1's table). Cheap, as the design says.

**Texture resize on growth:** an R8 256×h texture re-created as rows grow took 0.70 ms min including one frame, against 0.71 ms for an in-place `update` including one frame (`$D/proj/probe_recreate.gd`). Growing the texture height on insertion has no hidden first-upload cost at this size.

**MSAA cost on the M2:** 4× MSAA added about 0.3 ms to an empty 1280×720 frame and about 0.65 ms with 2,000 rods at 1 ring (P-S3's table). This is not a measurement on the raymarch or under llvmpipe. The design already requires llvmpipe to be measured before MSAA is chosen (§7.4, owner question 3), which is right.

**Probe reproduction:** I reran the unchanged probe twice and got its coverage values exactly: cv 0.378 / 0.384 / 0.270 / 0.228 for the 20 mm rod; 0.048 for the 0.2 m rod; 9 empty steps; RH 3-D midpoint 0.502. Timings were 0.64–0.68 ms (2,000), 6.7–6.9 ms (2×10⁴) and 69–77 µs (upload), higher than the design's from load alone.

**Picking (§4.3):** 2,000 analytic tests per click. By the per-row cost of my rebuild loop, about 2 ms per click. That is per click, not per frame, and acceptable.

**Server encode (cells, for scale):** 1.5 ms at 230,400 cells and 34 ms at 5×10⁶ (`$D/red.py`, loaded). The fuel tables' quantization is a small share of the per-publish work; the reductions (P-S5) dominate it.

**Memory per pinned frame:** the fuel view in f64 is about 0.64 MB of reductions plus about 0.2 MB of geometry, against about 100 MB of cells at 5×10⁶ (B5). Not material.

**Cross-fade (§4.3):** sampling two segment textures is negligible.

**Outside this lens, seen in passing:** the probe's "seg colour" lines read 0.259 and 0.882 against expected 0.200 and 0.800. That looks like an output colour-space conversion rather than the fetch, but §2's "all work" row rests on the lin3d value, not these.
