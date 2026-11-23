# Sub-cell solids design, delta 1: Physics and resolution, Determinism and replay (2026-11-22)

The reader's report as handed back, saved by the author. The reader set every status below, read from the tree at
ed2c9ae; its scripts ran in the session scratchpad.

**What the numbers show:**
- **The µm rule holds.** `4.0−3.6` is 0.3999999999999999 in float64 and 400,000 µm as integers. All 261 centimetre
  edges of 40 cm give exactly 400,000 µm.
- **The world frame flips at half-µm origins.** On 200k random sub-µm origins the world-frame thickness never flipped,
  but at origins of exactly half a micrometre, 5,994 of 16,000 checks flipped by 1 µm (N-a).
- **The coupled contact solve conserves and stays monotone.** With backward Euler on round 1's cases, pine against
  steel moves 45,700.64 J/m² each way, and glass against pine 52,804.64 J/m².
- **τ for the 1 cm steel sheet:** 769 s at c = 490 and 785 s at c = 500, by convection on both faces. With linearized
  radiation (300 K, ε 0.9) it is 630–643 s.
- **Euler buckling of the 4 cm × 0.4 m pine leg (E = 10 GPa):** 132 kN at K = 1 and 33 kN at K = 2. K = 2.0 is right.
- **The 3 mm minimum against the 1 mm tolerance** stops containment, but not double counting inside the tolerance
  (N-c).

## Status of round-1 findings

| Finding | Status | Reason |
|---|---|---|
| B1, D-B1 | fixed | integer µm in the spec's own frame; residual in N-a |
| B2 | fixed | tiles per material with in-plane conduction; the layout has its own defect (S-b) |
| B3 | fixed | strength integrated over the remaining section, E(T) in I |
| B4 | **open** | the in-plane criterion is folded, but the band isn't shaded and is resolved only at tile size, so ΔT ≈ 0 (S-c) |
| B5 | fixed | coupled implicit solve per island; conservation measured above |
| B6 | fixed | 3 DOF, contact points in µm, active set; new defects B-1 and B-2 |
| B7 | fixed for objects and openings | cell-to-cell anchoring is still judged on cells (S-e) |
| B8 | fixed in form | §2.3's table exists, but two "same class" rows are false (S-d) |
| S1, S3, S5, S6, S7, N1, N2 | fixed | S1's numbers check (0.6, 0.5, 0.45 m; 1.5×; 2.25×) |
| S2 | fixed | 3,000 > 2 × 1,000; containment refused; NIT N-c |
| S4 | deferred | Trigger: S2's two-sided char test. A miss changes the node limit, which is contract, so S2 reports back here |
| S8 | fixed in intent | the union is clipped, but "exact integer µm²" is impossible as written (S-f) |
| S9 | fixed | boundary conditions stated; NIT N-d |
| N3 | **open (NIT)** | the author's rejection is not accepted: under the active set the idealization is contract (N-e) |
| N4 | deferred | Trigger: S3 defines lab readings |
| D-B2 | fixed | keyed on write ticks; loads derived and not digested; the added save rule is wrong (S-a) |
| D-B3 | fixed | state, `breached` and `support` are Topology requests that bump `topology_version` (§7.4) |
| D-S1 | fixed for statics | Cholesky per anchored island, fixed order, solver identity in the law version; the thermal island has no such rule (S-g) |
| D-S2 | **open** | fail-all-then-re-solve is stated, but failed members still carry load, so nothing cascades (B-1) |
| D-S3 | fixed for strike; **open for `kindle`** | §7.1's `kindle` row names no tie-break |
| D-S4 | fixed (moot) | `QUANTITIES` and today's expression are unchanged |
| D-S5 | partly fixed | union, int64, polygonal discs; exactness fails (S-f) |
| D-N1, D-N2, D-N3 | fixed | |

## New findings in the folded text

### BLOCKER (contract)

**B-1. `§8.1` (vertices) with §8.3 (failure): a failed member keeps carrying load.** Every `live` or `failed`
object is a vertex with bearing springs, and nothing removes a failed member's stiffness. A pine leg chars past
capacity and becomes `failed`; the re-solve keeps it carrying its share, so no load moves to the other legs and the
loop ends after one pass. D-S2's cascade and D31's falling table can't happen. Fix (unverified): a failed member
stays as weight only, its bearing points inactive and its capacity never checked again.

**B-2. `§8.1` (side contacts) with §8.2 (singular → `unstable`): an attached part makes its whole island
unstable.** A part held only by side contacts (D36 (1)'s wall shelf) has zero stiffness in all three DOFs, so the
island's matrix is singular. A cabinet with a side-attached shelf fails Cholesky, and every vertex in the island,
cabinet included, becomes `unstable`, which is digested and on the wire. Fix (unverified): build islands from
bearing contacts only; a vertex attached only at its sides stays outside the solve and keeps `attached`, with where
its weight goes stated as the Known gap.

**B33:** two new contract BLOCKERs, both in the new §8 statics text. Each is about a one-sentence fix.

### SHOULD-FIX

- **S-a, `§11.4`:** the save reader refuses a `state` that differs from recomputed statics, but `failed`, `burnt_out`
  and `removed` are history. A member that failed at 700 °C and cooled is refused on reload. Fix (unverified): check
  only `support`, recomputed from the saved state, and `state` for its enum values.
- **S-b, `§3.1` `tiles`, contract:** each face is cut into tiles with a full-thickness profile, so a slab's top and
  bottom faces count its heat capacity and mass about twice. Fix (unverified): a tile is a through-thickness column
  under a patch of the two largest faces (or an axial and angular patch of a rod), with the edge faces as boundary
  conditions.
- **S-c, `§3.3` and §7.2, the glass edge band:** the band is resolved at `tile_m` and isn't shaded from flux or gas,
  so band and interior heat alike and the pane still never cracks. A 15 mm band read through 100 mm tiles dilutes ΔT
  to about 0.15, because lateral diffusion in glass over 300 s reaches about 1.2 cm. Fix (unverified): a ring of tiles
  exactly `edge_band_um` wide, by area, whose contact-covered faces get no flame or gas exposure.
- **S-d, `§2.3`:** "Strike: same class" and "Gap blocking: same class" are false. A strike holes a 0.41 m wall of
  cells and joins the zones, but only lowers a 0.39 m object's `integrity`, which nothing turns into a hole. Fix: both
  rows become red gates, with D35 (2)'s fracture kind in the Until column.
- **S-e, `§8.1` anchors:** connectivity "through cells" is judged on voxels. A block authored 3 mm above a cell floor
  is connected at 0.2 m and disconnected at 0.05 m, while §8.4's authored check disagrees. Fix (unverified): use §4.1's
  authored µm contact test between primitives.
- **S-f, `§6`, "exact integer µm²":** polygon-edge crossings are rational (a 16-gon edge at r = 20,000 µm crosses
  x = 7,000 at y = 6,728,563/271), and exact intersection terms overflow int64 near 1e24. Fix: exact rational arithmetic
  floored once to µm², or a named sub-sampling (Fraction arithmetic verified exact).
- **S-g, `§5.1` and §3.3:** the thermal island's scheme and solver are unnamed. In-plane conduction plus contact makes
  a sparse system, and the ledger's closure and bit-identity depend on it. Fix: name the scheme, a direct solver, a
  fixed DOF order, and that an island solved alone is bit-identical, as §8.2 does for statics.

### NIT

- **N-a, `§2.1`:** form world µm as q(local) + q(origin); float q(local + origin) flips by 1 µm at half-µm origins
  (verified).
- **N-b, `§2.4`:** a tie at exactly ½ needs a tie-break between two primitives, such as primitive order.
- **N-c, `§3.1`:** "no volume counts twice" is false inside the tolerance; state the bound.
- **N-d, `§13` S2:** τ ≈ 770 s holds only with radiation off (about 630 s with it); say which.
- **N-e, `§8.2`:** bearing points within `contact_tolerance_um` start at zero gap, or a leg 0.5 mm short carries
  nothing and the split depends on an unstated idealization.

## Verdict

Most round-1 findings are genuinely fixed. B4, D-S2, D-S3 (`kindle`) and N3 remain open. Under B33, the folds
introduced two new contract BLOCKERs, B-1 and B-2. They set the digested `support` and `state`, so they fold or go to
the owner. S-a, S-b, S-d and S-f are contract text and should fold with them. S-c, S-e and S-g could move to S3, S4
and S2 as build-step tests, deferred by a reviewer with those steps as triggers, if the owner accepts.
