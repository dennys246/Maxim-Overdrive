# D-B2 (`client_objects.md`): the owner's rulings

Moved out of the design's §9 on 2026-11-22 (decision records belong in `reviews/`, not in a design; CLAUDE.md, one
owner per contract). Each ruling's effect is stated in the design section it names; the design's §9 links here.

## The rulings (2026-11-22: all five as recommended)

1. **Thin fuel shows char by darkening and burn-away by gaps,** not by cracks (§6.3).
2. **Outlines rather than an edge in every cracked cell** (§6.1, rule 3). This narrows step 8 decision 7, which
   conflicts with decision 4 at a 7.2 px cell pitch. The 1/8 outline threshold, added after the ruling to stop
   scattered slight damage drawing a grid (`delta1_five_lenses.md` S6), was confirmed by the owner.
3. **Anti-aliasing:** prototype MSAA and analytic coverage at step 8, and choose by the stability check and frame
   time (§4.2).
4. **The exit's holes:** D-S2's trigger moves to "before step 8" (fire_solid §7), and checklist step 6 names the
   torch's Phase 1 pilot.
5. **Structural glow from the cell mean** until face skins exist, a Known gap (§5.1).

Also confirmed by the owner: Phase 1 flames are drawn in goldens, with flicker off (§5.3). `client_rendering.md` had
turned flames off in goldens, but §7.2's flame-shape check needs them drawn.

## Step 8 leftovers (2026-11-22)

Recorded by the author from the owner's answers in the session; the findings are in `../fuel_leftovers/`.

6. **Keep the shader's temperature clamp** (review E2-S3). Its golden check could not fail and was removed: with
   the clamp deleted, +∞ °C drew pixel-identical to 6,000 °C, measured on llvmpipe with the linear tonemapper and
   bloom on (6,000 °C's emission is already far past the white the frame saturates at). Other tonemappers, NaN and other
   drivers were not measured. Ruling 6 was asked without TB-S4's decoder option; ruling 9 adds it.
7. **Rods draw their colour in two passes, core then fade, instead of sorting** (fuel_leftovers A1, CR-1, E-S1: a sort
   by centre ordered crossing rods right only where their centres line up). Every rod's core draws before any rod's
   fade, so a front rod's outer fade lands on a rear rod at any crossing, yaw and instance order, with no camera call;
   where rods touch, their widened shells interpenetrate, and near the contact depth hides part of the front fade
   and the rear fade draws over the front core (fuel_leftovers N-1, from a model; numbers in step 8's checklist).
   Fade over fade still blends in instance order (N-5, step 8).
8. **The outer-fade bar is re-derived from the coverage model, on rig and max only** (A3, CR-2, E-S4, B30): in linear
   light, the band must add at least 1/14 of the stick's gain, half the model's 1/7. Laptop stays unchecked until a
   laptop measure is derived.
9. **The decoder also refuses a temperature outside [−273, 6000] °C, NaN or ±∞** (TB-S1, A4, W7): `FuelSnapshot`'s
   per-frame check, tested in GDScript on every renderer, where the shader's clamp can't be seen. It costs 1.5–1.8 ms
   per snapshot (2 Hz), not per rendered frame, at 2×10⁴ segments (headless, editor build, the owner's M2).
