# Sub-cell solids design, fold 2: delta 1 folded, the last fold (2026-11-22)

The owner accepted B33's stop (D37 (3)): delta 1 found three new contract BLOCKERs in folded text, so this fold takes
them and the contract SHOULD-FIXes, with no further paper round. Mechanism findings move to the build steps'
checklist (`docs/plans/checklists.md`, "Sub-cell solids"), and a reviewer, not the author, records each as deferred
with its step as the trigger. **Every status below is the author's claim.**

The design is 5,998 words (limit 6,000). To make room, §0's summary was cut (it restated §2–§8), two "Why" asides
went, and §13's test lists moved to the checklist, which O42 exempts from the budget. No contract value was cut.

## Contract findings folded

| Finding | What changed | How the author verified it |
|---|---|---|
| N-B1 (Arch) | §4.1: a cell region's **present geometry** is its `region_geometry` minus its `craters`, in µm; every overlap, contact and support rule reads it. A crater under a bearing removes the contact in its batch, and `imagine` into a gap sees the gap. Exchange lands on live cells only. §3.1 adds `region_geometry` and `craters`; §7.1's strike appends a crater; §7.4 makes a crater a Topology request; §11.4 saves and digests both | read §4.1, §3.1, §7.1, §7.4, §8.2's key and §11.4 together for the beam-on-a-cratered-wall scenario |
| B-1 (Phys) | §8.1: a failed member leaves the solve, with its bearing contacts removed and its capacity never checked again; §8.3 says the re-solve cascades within the step | read §8.1 against §8.3; the four-leg cascade is now a checklist test (S4) |
| B-2 (Phys) | §8.1 and §8.2: islands are built from bearing contacts only; a side-only vertex stays outside the solve, keeps `attached`, and its weight reaching no support is the stated Known gap | the cabinet-with-shelf case is a checklist test (S4) |
| N-S1, N-a, N1 | §2.1: |v| ≤ `coordinate_limit_um` / 10⁶ m before quantizing, else `out_of_range` (§11.1 proposes 10⁸ µm, so int64 products of µm stay below 10¹⁶); each coordinate and radius quantized once, then integers; a box edge is q(hi) − q(lo), a cylinder's diameter 2·q(r); world µm = q(origin) + q(local) | the readers' measurements (half-µm origins flip under q(o + l), never under q(o) + q(l)) |
| N-S2 | §3.1 adds `region_support`; §8.1 holds an unanchored cell region's outcome there; §8.3's hand-off has D22 read it | read |
| N-S3, A-S4's open point | §3.2: `inert` and `fuel` are rigid vertices that pass load and are never checked for capacity; a sheet on a fuel crate is attached through it. On a cell part a role changes nothing until D22, and every floor-connected cell region is an anchor whatever its role | read §3.2 against §8.1 |
| N-S4 | §11.2: the discriminator is the `recipe` key; a kind its form doesn't admit is `kind_not_admitted`, checked before any other key | the reader's two cases (`{kind: slab, material: steel}`, `{kind: box, recipe: crate}`) each get `kind_not_admitted` |
| N-S5, S-a | §11.4: only `support` is checked, recomputed from the saved `state`; `state` is history, checked for its enum values | the cooled-beam scenario loads |
| N-S6 | §8.4: the base is every part whose lowest point lies within the tolerance of the spec's lowest point | the reader's z = 0.002 m and downward-fixture cases connect |
| S-b | §3.1 `tiles`: a slab's tile is a through-thickness column under its two largest faces; a rod's an axial and angular patch; the last tile takes the remainder | read; no face carries a second profile |
| S-d | §2.3: the strike row and a new "gap blocking after a strike" row are red gates until D35 (2)'s fracture kind | read |
| S-f | §6: the union in exact rational arithmetic, floored once to µm² | the reader's Fraction check |
| NS1 (Wire) | §7.1: the strike target is the footprint plus σ, as `applier._on_region` judges cells, refused `not_on_region` off it; §9 and §11.3 updated | `applier.py:123` is `not_on_region` |
| NS3 (Wire) | §7.1 and §7.2: strike and removal act on `structure` and `inert` only; a fuel object takes no strike until 6.2, so fuel's `state` stays 0 or 1 | read against §10 |
| NS6 (Wire) | §11.2: v0 is the one spec form `Format` reads without a version key, a named exception in `schema.py`; §12 row added | `schema.read_version` refuses a missing version today, so the row is needed |
| NS7 (Wire) | §2.3's interim row: until S3 an act reaches a region's cell parts only, and a strike meeting none destroys nothing and is accepted. No code is reused for it, and `wrong_target` is untouched. A readings row was added | read; the S0 text in `fire_solid.md` §2 says the same |
| N-N1 | §11.3: one set of codes; fuel geometry out of range is `out_of_range`; the new `world_limit_tiles` and `world_limit_object_contact` and the loader's `bad_key` listed | `fire_solid.md` §5.3 revised in S0 to match |
| Wire N5 | §5.1: the body reads the tile at onset into its carried sub-mesh; `radiant_emitters` keyed by tile; §12 row for `sem_stimuli.md` §7.1 | read |
| Wire N4 | §8.3: `support_lost` is a host-side log record; §12 row for `sim_core.md` §4 | read |
| Wire N8 | §12 rows for `client_rendering.md` §4.1 and `schema.py`; the `applier.py` row added | read |
| Wire N6 (half) | §11.4: "the registry's order" | read |
| N-N2 | §7.2 and §11.1: `MaterialCatalogue` checks `breach_ligament_um` < `min_part_thickness_um` against the loaded limits | read |
| D37 (1) | §2.2: `min_part_thickness_um` = 3,000, the owner's | read |
| §14 | removed: both questions are answered by D37 | read |

## S0, applied in a separate commit

`fire_solid.md` §1.3, §2, §5.2, §5.3 and §7 now say what §12's S0 rows say:
- representation by §2.2's rule;
- overlap and contact on present geometry in µm;
- mixed regions with S1;
- acts on cell parts only until S3;
- one tagged spec v1, with v0 migrated;
- one set of codes. `fuel_only_region`, `overlaps_fuel` and `geometry_out_of_range` are gone from it.

Its word count fell from 5,964 to 5,963, since an existing design may not grow. `foundations_plan.md`'s row 6 makes
6.0a follow S0, and its index lists D37 (2,493 words; `check_plan` passes).

## Moved to the build steps' checklist (mechanism; a reviewer records each deferral)

| Finding | Step |
|---|---|
| S-c, Physics B4's remaining part: the glass edge band as a ring of exact width, shaded where framed | S3 |
| S-e: anchor connectivity by µm contact on present geometry | S4 |
| S-g: the thermal island's scheme, solver and DOF order | S2 |
| Wire NS2: the wire's tile mapping, never a client recount | S6 |
| Wire NS4: structure's wire tables against S1 | S1 |
| Wire NS5: a region that becomes object-only mid-life | S3 |
| N-N3: how much of an island goes `unstable`; requests only on a change (the latter also stated in §7.4) | S4 |
| N-b: §2.4's tie between two primitives | S1 |
| N-c: the double-counted volume bound (also stated in §3.1) | S1 |
| N-d: τ with radiation off or linearized | S2 |
| N-e: bearing points within the tolerance start at zero gap (also stated in §8.1) | S4 |
| Wire N2: slab axes on tied edges, tile handedness | S1 |
| Wire N3: naming the first act that reaches an object-only region | S3 |
| Wire N7: `recipe_id`'s sentinel for structure rows | S1 |
| Architecture A-S3 (statics' registry row) and A-S7 (the module plan), already deferred by delta 1 | S4, S1 |

## TP1, an owner ruling from `phase1/torch-pilot` (2026-11-22)

Applied before this commit, at the coordinator's request:
- **`kindle` is excepted** from the interim cell-only rule, both in §2.3's row and in S0's `fire_solid.md` §2 text,
  each linking `torch_pilot.md` §3. Phase 1's exit kindles a fuel slab, an object-only region.
- **§7.1's `kindle` row** links `torch_pilot.md` §3, which owns the whole target rule, and doesn't restate it. That
  settles D-S3 for `kindle`, so it is gone from the build steps.
- **A §12 row:** `torch_pilot.md` §2 follows §3.1's states and §4.3's "gone" after S1.
- **Strike keeps its own tie-break** on the shared ranked query. §10 adds nothing to the pilots row, so it doesn't
  contradict TP5.

**A merge-order dependency:** `torch_pilot.md` is on the unmerged `phase1/torch-pilot`, so these links resolve only
once that branch merges.

## Not folded

- **Wire N6's first half:** whether a reversed but unique `h_contact` pair is a `duplicate_key`. It now gets its own
  loader code, `bad_key`, so the question no longer arises.
- **Nothing else** is left open by the author. A reviewer reading this fold may still find that a claim above
  overstates the tree.
