# Five-lens delta review: client_objects.md (D-B2), delta 1, at bbebd69

Reader: Executor, Architecture, Client and rendering, Performance, Bio-faithful integration. Scope: `git diff 065f84d bbebd69`, the six round 1 reports and `fold.md`.

I ran nothing in the repository. Everything I ran is under `.../scratchpad/delta_others/`:
- `rv_instid.gd` and `rv_instid.gdshader`, on a copy of `tools/godot_probes/` (Godot 4.7.2, Compatibility, M2, windowed);
- `segcount.py` (numpy, f32);
- `stab.py` (numpy, a supersampled ideal line and 4× MSAA).

**Summary:** 1 BLOCKER (contract), 8 SHOULD-FIX (5 contract, 3 mechanism) and 7 NIT. The fold fixes almost every round 1 finding. The new defects are in text the fold added:
- the decoder's segment-count tolerance refuses valid frames;
- the fuel view's step and cadence;
- a flame contradiction left in `client_rendering.md`;
- the outline rule.

## 1. Fold status (reviewer-set, read from the tree)

| Finding | Status | Evidence |
|---|---|---|
| A-B1 | fixed | client_objects §1 (roadmap exit), §2 (no flame object in Phase 1), §5.3, §7.3, §9 q4 |
| A-S1 | **open** | fire_solid §5.6 now owns the meanings, site, cadence and leak rule. Three things are missing: (a) step 7 doesn't depend on 6.0b (new S1); (b) fire_solid §7's placement table has no fuel-view row; (c) F1–F3 are not in fire_solid, although client_objects §8 says they are (new S2) |
| A-S2 | **open** | Most copies are now links: checklists steps 7–8, plan row 8, client_rendering §4–§6, §12. Still stale: client_rendering §5.3 "off in goldens", §7's scene tree "Flames → GPUParticles3D" with no `Fuel` node, and §5.5's flame-particle column (new S4) |
| A-S3 | fixed | §5.1: masked by `material` ≠ air, the filter blends solid neighbours only, the constants and `glow` key are deleted at step 7. The bound's number has a NIT (N1) |
| A-S4 | fixed | standards_backlog B42: trigger "step 8, when the provisional reads are deleted" |
| A-S5 | fixed (check added) | §7.2 Burning row. Its deletion proof may not fail (new S5) |
| A-S6 | fixed | §7.5; plan row 8; checklist step 8 |
| A-N1 | fixed | fire_solid §5.6 "exact for glow while one part has area" |
| A-N2 | fixed | §3.1 versioning bullet |
| A-N3 | fixed | §10 names an owner for each item |
| E-B1 | **fixed, verified** | §4.1 per-instance RGBA8 texture indexed by `INSTANCE_ID`. I ran 3,000 instances through a `flat` varying with `texelFetch`: 3,000 of 3,000 decoded exactly, 951 of them above row 2,048. Breaking the expected value turns all 3,000 red |
| E-B2 | fixed (defect) | §7.2: the per-row sampler and the 25% bar are gone. The new measure is underspecified (new S7) |
| E-S1 | fixed | §2: 0.6–2.4 px, 1.44 px at the golden view; dowel 0.10–0.38 px (recomputed) |
| E-S2 | fixed | §6.1: the fissure is gone, monotone is stated by band. Outlines bring a new conflict (new S6) |
| E-S3 | fixed | §4.2 per-fragment discard; §7.2 footprint shrunk by the projected radius |
| E-S4 | **open** | §4.1's clamp is fixed. §3.2's count check refuses valid lengths (new B1) |
| E-S5 | fixed | §3.3 and fire_solid §5.6: denominator is remaining solid mass, 0 when none remains |
| E-N1 | fixed | §7.2 "isn't built yet (B7)" |
| E-N2 | fixed | §2 and §4.1: 95–161 µs for the design's layout |
| E-N3 | fixed | the row-mapping claim is removed from §2 |
| E-N4 | fixed | §1 "read at main 98e2342"; §3.1 bump rule; §7.4 |
| E-N5 | fixed | §7.1 "radius 10, 50 and 100 mm" |
| E-N6 | fixed | §7.2 speckle row has a deletion |
| C-B1 | **fixed, verified** | as E-B1 |
| C-S1 | fixed | §4.2; §2 row (C-S1's R2) |
| C-S2 | fixed | §7.2: the bar is replaced by a relative measure that includes camera offsets |
| C-S3 | fixed | §6.1, §9 q2. Residual is new S6 |
| C-S4 | fixed | §7.2 Burning at 600 °C. Above the laptop's white band it is unrecorded (N7) |
| C-S5 | fixed | §7.2 Char darkening |
| C-S6 | fixed | §7.2 tier agreement per kind |
| C-S7 | fixed | §2 claim removed. The head-on readout is a step 8 fixture item: an author's deferral, accepted |
| C-N1–N7 | fixed | §4.2 output-pixel quantity and projected thickness; §4.3 skip on key change, nearer hit wins, gaps not hittable; §4.3 burnt-out draws char; §7.2 speckle; §2 upload layout |
| P-S1 | fixed | §3.2: checks gated on a native byte compare. The trigger's byte set is unnamed (N2) |
| P-S2 | fixed | §2 3.6–3.8 ms; §4.1: `state` leaves the trigger |
| P-S3 | fixed | §2 one ring. The number's attribution has a NIT (N3) |
| P-S4 | fixed | §3.5, client_rendering §4.3. Recomputed (3,670,016 − 356,000)/6 = 552,336 |
| P-S5 | fixed (costed) | §7.4, B5 row. The chosen cadence has a new cost defect (new S3) |
| P-S6 | fixed for Phase 2 | §5.3. The Phase 1 flame pass is unbounded in mechanism (new S8) |
| P-N1, P-N2 | fixed | §2; §3.5 |
| P-N3 | **open** (minor) | "every cell-frame message (2 Hz)" is fixed. The median beside the minimum, and the stated exclusions, are not adopted and no reason is given |
| Bio S1 | fixed | fire_solid §5.6 leak rule; checklist step 7 leak test. Its reach has a NIT (N2) |
| Bio S2 | fixed | §5.4, OPEN against OD-C8 (exists, roadmap l.254) |
| Bio S3 | fixed | §4.3: raw hit point, no snap. 1 output px at 30 px/m = 33.3 mm, inside 50 mm |
| Bio S4 | fixed | lessons §32 has Evidence and Consequence, and names OD-C8 |
| Bio N1, N2 | fixed | §3.1 no longer cites boundaries §8.3; §10 lists sight parity |

**Other numbers recomputed, and true:**
- ≥ 0.17 m for 12 px: 12/72 = 0.167 m.
- 36 K per kW/m²: 1000 × 0.05/1.4 = 35.7 K. The arithmetic is right; the conductivity isn't the shipped one (N1).
- +0.24 ms and +0.6 ms: from P-S3's table (0.94–0.98 against 0.70–0.74; 1.61–1.63 against 1.00–1.03).
- Word counts: client_objects is 5,099 words (≤ 6,000). client_rendering, fire_solid, fire_model and tile didn't grow.

## 2. New findings

### B1. BLOCKER (Executor; contract): `client_objects.md::§3.2`, "`segment_count` ≠ ⌈L/ℓ − 10⁻⁶⌉, computed in f64 from the f32 columns". The tolerance doesn't cover f32 rounding, so the decoder refuses valid frames.

**Defect.** Computed as specified (f32 L and ℓ, divided in f64), the ratio's error is about 1.2×10⁻⁷ × L/ℓ, relative. That exceeds the absolute 10⁻⁶ from about 10 segments up. Measured (`segcount.py`):
- integer-mm lengths 20–2,000 mm: **42 of 1,981** get the wrong count with the tolerance (0.36, 0.54, 0.60, 0.66, 0.68, 0.72, 0.74, 0.80 m, …);
- exact multiples of 0.02 m up to 2 m: 1,459 of 2,000.

The fold's justification, W F4's "19 of 1,981 off without it", was measured with f32 division, which is not the computation this sentence specifies.

The server's own count rule is unstated (it is F1, now parked at step 8; see S2). A naive f64 ⌈L/ℓ⌉ is wrong for 4 of 1,981 lengths too (0.14, 0.28, 0.56, 1.12 m). So the client's check can't match a rule nobody has written.

**Failure scenario.** A scene authors a 0.6 m rod. The server sends 30 segments. The client computes ⌈30.0000019 − 10⁻⁶⌉ = 31 and refuses every frame. The tile never draws.

**Fix (verified for the client half).** Use a relative tolerance, ⌈L/ℓ − 10⁻⁶·max(1, L/ℓ)⌉, in f64 from the f32 columns: 0 mismatches over every integer-mm length from 20 mm to 400 m. A 10⁻⁵ relative tolerance fails (29,930 mismatches), so the margin is narrow. The server's rule must be stated beside it, in fire_solid, before step 7 freezes the tables.

### S1. SHOULD-FIX (Architecture; contract): `fire_solid.md::§5.6` ("Step 7 builds it with its caller, the encoder") against `foundations_plan.md` rows 6–7.

**Defect.** Step 7's dependencies are 5b, 2 and 0d. Step 6 (6.0b, the FuelStore) depends on 5a and 5b. Nothing orders 7 after 6.0b, so step 7 may be built with no FuelStore to reduce.

Two further gaps:
- fire_solid §7's placement table has no row for the fuel view: no module, no layer.
- The view's site (on the published `Frame`, or computed in `protocol`) is never stated, although the leak rule ("not on `Observation`") and the cadence ("per physics step") both presume it is in the core.

**Failure scenario.** Step 7 lands first, as the plan allows. It either ships empty fuel tables with fixtures that test nothing, or invents a FuelStore stub. Either way the frozen v0 grammar is unexercised against real data.

**Fix (unverified).** Make row 7 depend on 6.0b, or move the view's build to 6.0b with step 7 as its caller. Add the placement row.

### S2. SHOULD-FIX (Architecture; contract): `checklists.md` step 8, "Questions for fire_solid's owner, answered before the fuel tables freeze", and `client_objects.md::§8` ("fire_solid §5.6: … and questions F1–F3").

**Defect.**
- The tables freeze at step 7, so a step 8 item can't precede the freeze.
- fire_solid §5.6 doesn't contain F1–F3, though §8 says it does.
- §3.2 already answers F1 (the `min((k+1)ℓ, L)` span and the count check) while the checklist calls it open.
- §3.2's slabs row still defers F2 to "fire_solid's to state".

**Failure scenario.** Step 7 freezes `origin` and the segment span. Step 8 then gets a different answer from fire_solid (a slab's segments run along the width, say), and the change is a protocol bump after v0.

**Fix (unverified).** Put F1–F3 in fire_solid with step 7 as their trigger.

### S3. SHOULD-FIX (Performance; contract): `fire_solid.md::§5.6` cadence ("once per physics step and insertion") with `client_objects.md::§7.4`.

**Defect.** §7.4 cites 13.3 ms at the limits against the solid's 25 ms step budget. That is 53% more on every physics step, and it doesn't say whether the cost sits inside the 25 ms or on top of it. A per-step cadence pays it:
- in headless runs, the cone harness, the three-grid ladder tests and replays, where no client reads the view;
- at time scales above 1×, where frames are still capped at 2 Hz. At 20× that is 40 reductions per wall second for at most 2 frames.

Computing at encode time, cached on `fuel_version`, is bounded by the frame rate and is never more work than per-step.

**Failure scenario.** At the limits the solid's step is about 38 ms against 25 ms. The test suite's fire tiers slow by about half, for a presentation quantity.

**Fix (unverified).** The author's choice. State the cadence against the budget it spends.

### S4. SHOULD-FIX (Client and rendering; contract, stale copy): `client_rendering.md::§5.3`, "Burning and flames: `client_objects.md` §5.2–§5.3. Visual only, and off in goldens".

**Defect.** client_objects §5.3 turns off only flicker. §7.2's Flame shape check ("flames off, emission kept" must fail it) needs flames drawn in goldens. The fold rewrote this very line and kept "off in goldens".

Also stale:
- §7's scene tree still has `Flames → GPUParticles3D` and no `Fuel` node beside `CellVolume`;
- §5.5's `Flame particles` column has no consumer in the new flame contract;
- B40(2) still names particles.

Drawing flames in goldens reverses a prior client_rendering ruling, and §9 doesn't raise it with the owner.

**Failure scenario.** Step 8 follows client_rendering and draws no flames in golden runs. The flame-shape check can then never pass, or it is quietly dropped.

### S5. SHOULD-FIX (Executor and Client; mechanism): `client_objects.md::§7.2` Burning row ("drop the ignited term").

**Defect.** The Phase 1 flame is an additive volume rising from each flaming segment, scaled by the same `ignited_fraction` (§5.3). Over the segment's own pixels it adds brightness, so deleting the surface term can leave ignited segments ≥ 15 L* brighter. In that case the check can't fail.

**Failure scenario.** A refactor drops §5.2's term. The flames' halo keeps the Burning check green, and a flaming surface without its flame (flames off, a tier without them) draws as merely hot.

**Fix (unverified).** Run the Burning check with flames off, or outside the flame-ID mask. This can be deferred to step 8.

### S6. SHOULD-FIX (Client and Architecture; contract): `client_objects.md::§6.1` rules 2 and 3.

**Defect.**
- Rule 3 removes the outline on an edge once the neighbour becomes cracked ("inner boundaries draw no outline"). So as damage spreads, drawn edges disappear. That contradicts rule 2's "the pattern only gains edges as damage grows, and never swims", which is stated per point and per cell's own c.
- "Cracked" has no threshold: any c ≥ 1/255 counts.

**Failure scenario.** A heated wall's diffuse low damage leaves scattered cells at 1/255 or 2/255 among zeros. Each isolated one draws a full four-edge outline at 7.2 px pitch: a grid that reads as severe, the inversion C S3 named. Separately, a crack front moving cell by cell makes outlines appear and vanish, which is visible swimming.

**Fix (unverified).** State a display threshold for "cracked". Scope rule 2 to the cell's own severity, or make outlines additive.

### S7. SHOULD-FIX (Executor; mechanism): `client_objects.md::§7.2`, the stability measure.

**Defect.** Several choices are left unspecified:
- whether bins are fixed in world space or in screen space;
- the offsets' direction and span (output or rendered pixel at laptop scale 0.5);
- the spread statistic and how it is aggregated (mean or max over bins, end bins);
- how the "ideal anti-aliased line drawn in the same fixture" is drawn.

If Godot draws it with analytic coverage, the reference is owner question 3's own candidate, which is circular. These choices decide the outcome.

In `stab.py` (1.44 px line at 32.7°, 4 px bins, 8 offsets), these choices moved the ideal's mean spread from 0.014 to 0.083 and 4× MSAA's from 0.037 to 0.113. MSAA came out 2.6× the ideal under one choice and 1.2× under another. These are derived numbers, from a rough pixel-centre binning.

**Failure scenario.** Step 8 picks the choice that passes the candidate it prefers. The check then decides owner question 3 by construction.

Defer to step 8's checklist as a test to write, with these parameters fixed before measurement.

### S8. SHOULD-FIX (Performance; mechanism): `client_objects.md::§5.3`, "flames are bounded by flaming segments".

**Defect.** The bound is 2×10⁴. The design names no instancing path, and the set of flaming segments changes every frame. Two obvious builds:
- a per-frame instance list, which is the GDScript per-segment loop §4.1 measured at 4.4–6.9 ms and rejected;
- 2×10⁴ always-present quads culled in the shader, a fill and vertex cost nobody has measured, under llvmpipe least of all.

**Failure scenario.** A burning slab of 25 segments is cheap, but a scene near the limits blows the decode budget or the golden job's frame time.

Defer to step 8 with §7.4's flame row.

### NITs

- **N1 (Executor), `client_objects.md::§5.1`.** The bound uses k = 1.4 W/m·K. The shipped concrete is 1.7 (`data/materials/core.yaml:22`), which gives 29 K per kW/m². At fire fluxes of 20–50 kW/m² the steady bound is 600–1,800 K, so as stated it bounds nothing useful. Also, the gap exists in the tree today (the encoder's cell-mean `glow`), but it reaches `docs/architecture.md` only at step 8.
- **N2 (Executor and Bio), `§3.2`, `§4.1`, fire_solid §5.6.**
  - "Key or geometry bytes" doesn't name which `objects` columns are included. A change to `kind`, `recipe_id` or `segment_count` alone would skip the checks.
  - `state` (only 0 or 1 is defined) and a NaN `surface_temperature_c` have no check.
  - The leak test ("`adapters.sem` never imports it") can't see `getattr(observation, "fuel")` on the concrete frame. Pinning `Observation`'s members plus mypy covers the typed path only.
- **N3 (Performance), `§2` and `§7.4`.**
  - The +0.24 ms was measured with the probe's per-vertex rod shader, not the per-fragment lookup (four `texelFetch` calls plus `discard`, which defeats early-z).
  - With a one-ring mesh, `thickness_fraction` in (0, 1) has no mechanism, so "drawn thickness is monotone" holds only vacuously.
- **N4 (Client), `§4.1`.** The clamp needs `segment_count` and ℓ in the shader. The RGBA8 texel is full, and custom data is exact only to 2,048. The path isn't stated.
- **N5 (Bio), `§4.3`.** The floored hit can lie up to about 23 mm from the true surface at 30 px/m. With sticks closer than that, the hover outlines A while the server's nearest-surface rule kindles B. Parity holds, but the feedback misleads.
- **N6 (Architecture), `fire_solid.md::§8`.** The fold deleted "a lone slab that flames out when the heater goes is the expected answer". That caveat bears directly on the slab exit, and the fold table doesn't record the deletion.
- **N7 (Client), `§7.2` Burning.** Tested only at 600 °C. On the laptop tier above about 1,230 °C, burning adds nothing to flat white, and that is unrecorded (B7 records glow only).

## 3. The other questions asked

- **Is the Phase 1 client-drawn flame consistent with CLAUDE.md?** Yes, as a "purely visual effect" driven by a snapshot column, nothing fed back, and §5.4 names the parity gap. But its height is a client stylisation (0.1–0.3 m, fire_model l.146's starter range, not a slab's), it is now measured in goldens, and it reverses client_rendering's "off in goldens". That is an owner decision §9 doesn't ask (S4).
- **Is the leak rule complete?** It is enforceable on the typed path. It is incomplete on site and placement (S1), and on untyped access (N2).
- **Does the RGBA8 texture solve half-float custom data?** Yes, verified (E-B1).
- **Are the owner questions honest?** Q2 and Q4 are honest. Missing: the step 7 / 6.0b order (S1), flames in goldens (S4) and the per-step cadence's cost (S3).

## 4. Rounds-stop note

B1 is a contract BLOCKER and must fold. It is small, and the fix is verified. Contract findings S1–S4 and S6 should also fold. Mechanism findings S5, S7, S8 and N3–N4 can move to step 8's checklist under the charter's procedure, once the owner accepts the move; I would record them `deferred` with step 8 as the trigger.
