# Sub-cell solids design, fold of round 1 (2026-11-22)

The author's fold of the six round-1 reports (`round1_*.md`) into `subcell_solids.md`, under the owner's rulings, D36.
**Every status below is the author's claim.** A reviewer sets the statuses in the delta round.

**How the fold was checked:**
- **"text":** the new text says it, as read back.
- **"computed":** the author ran it. Every primitive of `tests/fixtures/scenes/alley_box.yaml` and every 40 cm
  centimetre edge in 0–300 cm (261 of them) gives exactly 400,000 µm under q(v) = rint(v·10⁶). In float64 the alley's
  `wall_north` is 0.3999999999999999 and `wall_end` 0.40000000000000036.
- **"reviewer's":** the reviewer's own verified fix, adopted as given.

The design is 5,986 words (limit 6,000). `lint_standards` passes.

## Architecture

| Finding | Change | Check |
|---|---|---|
| A-B1 | §2.1: every threshold and geometry decision in integer µm, specs in their own frame; §2.2 notes the alley's walls sit on the threshold | computed |
| A-B2 | §6: openings are the authored interfaces between zone volumes in µm; a tile's zone is judged on authored zones (§5.2) | text |
| A-B3 | §8.1: unanchored cell regions are vertices with their authored weight, and anchored ones are supports | text |
| A-B4 | §7.4: object state, `breached` and `support` transitions are Topology requests that bump `topology_version`; §6 excludes breached objects | text |
| A-B5 | §7.1: strike on objects is a resolver module inside `damage.loads`'s tuple, `per_record` | text |
| A-B6 | §7.1: `ignite` has no row; `kindle` covers objects with no new code; `not_flammable` dropped | text |
| A-B7 | §3.1, §3.3: structural faces are tiled in metres (`tile_m` per material) with in-plane conduction; glass gets an edge band | text |
| A-B8 | §11.2: one tagged spec v1 shared with fuel, settled in S0 before 6.0b | text |
| A-S1 | §12: rows for `fire_solid.md` §7's owner table, §1.3 and §2, `douse` (fire_model's revision), `tile_and_client.md` §3.4, `world_model.md` §2, and `sim_core.md` §5.1 | text |
| A-S2 | §10: fuel tables unchanged; structural tables separate (`structures`, `structure_rods`, `structure_slabs`, `tiles`); `ObjectFrame` with fire_solid §5.6's leak rule; fuel's contract markers untouched | text |
| A-S3 | §7.4, §8.2: Topology is the one writer of the state columns, from named emitters; statics declared `per_physics_step` after the solid law with its read key; object–object contact is inside the solid law's solve, so it has no `contact_exchange` writer. **Partial:** statics' full law entry (name, version, reads, writes) is S4's registry row | text |
| A-S4 | §3.1, §8.3: `support` is `attached`, `loose` or `unstable`, and `anchored` is gone; "loose" is only "no contact path to an anchor" (D33, D36 (1)); a wall shelf is authorable by a side contact | text |
| A-S5 | §2.4: the ½ rule is stated as a Known gap with its numbers, closing with B28 | text |
| A-S6 | §1 and §13: S0 before 6.0a, then S1–S6 after 6.0b on the Phase 2 line; footprints are authored primitives; the anchor is defined in §8.1 | text |
| A-S7 | **Not folded:** no placement table (layers and modules). The word budget is spent. Proposed to move to S1's build step as the module plan its review checks | — |
| A-S8 | §3.1: the kinds stay `rod` and `slab`, with one `object_contact` key form | text |
| A-S9 | §6: blocked area is the union, clipped to the opening, in int64 µm² | text |
| A-S10 | §7.1, §11.3: `not_on_object` becomes `not_on_surface` and `overlaps_object` becomes `space_taken`; `overlaps_fuel` is dropped in S0 | text |
| A-S11 | §9: the NPC fire note's trigger moves ahead of S3 | text |
| A-N1 | "accepted" removed; #40 is merged | text |
| A-N2 | the law is named `statics` | text |
| A-N3 | `MaterialCatalogue` (§11.1). `mechanics.yaml` keeps its name and holds the exposure values beside the mechanical ones | text, partial |
| A-N4 | §3.1: `pose`'s canonical form; the "no format change at D32" promise removed | text |
| A-N5 | §10: the protocol bumps | text |

## Physics and resolution

| Finding | Change | Check |
|---|---|---|
| B1 | §2.1, as A-B1 | reviewer's (200,000 offsets, 0 flips); computed |
| B2 | §3.3: tiles give lateral resolution | text |
| B3 | §7.2: capacity integrates σ(T(x)) over the remaining section, with E(T) in I; a minimum-node read only for breach | text |
| B4 | §3.3, §7.2: an edge band, and an in-plane ΔT criterion | text |
| B5 | §5.1: one coupled implicit solve per contact island, booked once antisymmetrically | text |
| B6 | §8.1–§8.2: three degrees of freedom, contact points in µm, compression only by an active set | text |
| B7 | §4.1, §6: contact, support and blocking judged on authored geometry; exchange mapped by area | text |
| B8 | §2.3: each law's outcome on both sides, with differences as red gates and Known gaps in named steps | text |
| S1 | §2.4's Known gap with these numbers | text |
| S2 | §2.2: `min_part_thickness_um` 3,000 > 2 × the tolerance; exact overlap per kind with containment refused (§4.2) | text |
| S3 | §3.3: `h_ref` from convection plus radiation linearized at `t_ref_k`, with its source cited | text |
| S4 | **Moved to S2** as a test: the square section against a two-sided char closed form; a miss is a Known gap whose fix changes the node limit | — |
| S5 | §8.2: `buckling_k`, 2.0 in v1 | text |
| S6 | §8.2: the remaining section, with node thickness in the solve's key | text |
| S7 | §5.2: `epsilon_gas` | text |
| S8 | §6, as A-S9 | text |
| S9 | §13 S2: boundary conditions stated (all faces, τ ≈ 770 s); cross-grid scenarios named for every step | text |
| N1 | §3.3: L_c = V/A, radial metrics for rods | text |
| N2 | §3.3: 1/h_node = 0 for a lumped node | text |
| N3 | **Not folded:** the 1 mm bearing idealization is unstated. Proposed rejected as text, since the reviewer accepted the idealization | — |
| N4 | **No change:** object readings are lab-only now (§7.3), and their definitions are S3's | — |

## Wire integrity

| Finding | Change | Check |
|---|---|---|
| B1 | §10, as A-S2; the join cap and bytes re-derived at S6 | text |
| B2 | §7.3: object-only regions refused by `Frame.reading` and `region_parts`, never 0.0 or NaN | text |
| B3 | §2.1, as A-B1 | computed |
| S1 | §3.1: numbered enums; `tiles` and `object_contact` are their own tables; §11.4: every vocabulary in the save | text |
| S2 | §7.4, as A-B4 | text |
| S3 | §11.3: `too_small`'s producers recoded; the replay break recorded at S1 | text |
| S4 | §1, §12 S0: fire's codes revised before 6.0a | text |
| S5 | §2.4 and §11.4: voxelization is a `derivation_version` bump and a break; new digest members are a break | text |
| S6 | §11.2: the `version` key, the v0 migration, and `SpecId` hashing the migrated form | text |
| S7 | §7.1, §11.3, as A-B6 and A-S10 | text |
| S8 | §2.2, §11.1: the threshold ≥ 400,000; sorted pair keys refused when reversed or repeated; law parameters moved to `mechanics.yaml` | text |
| S9 | §12: rows for `fire_solid.md` §5.1, §5.4–§5.6, `sim_core.md` §5.1 and §9, `scene.py`, `SPEC_KEYS`, `ip_and_licensing.md` §6.1 and `client_objects.md` §3 | text |
| N1–N5 | `statics`; save compares `support` and `state`; `dangling_reference` dropped; the key is write ticks; the D32 promise removed | text |

## Bio-faithful integration

| Finding | Change | Check |
|---|---|---|
| B1 | §7.3, §9: `QUANTITIES` and the bridge unchanged; object readings on a lab surface; the NPC fire note before S3 | text |
| S1 | §9: stage-2 refusals through `sem_stimuli.md` §6.2's receipts; T11 gains material and support (§12) | text |
| S2 | §9: weight, contact force and motion are a future row with its trigger, and a named gap meanwhile | text |
| S3 | §9: the never-perceivable list; `support_lost` in the `TickReport`'s lab section and the log only | text |
| S4 | §5.1: body–object coupling owned by `sem_stimuli.md` §7.1; tiles as emitters; §2.3's body-contact row | text |
| N1 | §5.2: the ambient gap must close before an NPC contact row reads an object | text |
| N2 | §8.3: ANALOG, earned at D32; no NPC bar depends on it | text |
| N3 | **No change:** for when the contact row lands | — |

## Determinism and replay

| Finding | Change | Check |
|---|---|---|
| D-B1 | §2.1, as A-B1 | reviewer's (800k placements); computed |
| D-B2 | §8.2: the solve keys on the write ticks of every field it reads; per-member loads are derived and never digested | text |
| D-B3 | §7.4, as A-B4 | text |
| D-S1 | §8.2: a direct Cholesky per island in a fixed order; the solver and BLAS identity in the law version and header | text |
| D-S2 | §8.3: everything over capacity fails at once, then a re-solve, until none fails, counted as work | text |
| D-S3 | §7.1: distance, then cells before objects, then the smallest id | text |
| D-S4 | **No change:** `QUANTITIES` stays cell-only and unchanged; lab readings state their order (§7.3) | — |
| D-S5 | §6: the union, polygonal discs at µm vertices, int64 | text |
| D-N1 | §3.1: `pose`'s canonical form | text |
| D-N2 | §11.4: the break and the tables' place in name order | text |
| D-N3 | §3.1 id minting; §8.1 anchors per component | text |

## Trust boundary

| Finding | Change | Check |
|---|---|---|
| T-B1 | §2.1, as A-B1 | reviewer's; computed |
| T-B2 | §8.1: the domain floor is an anchor; §8.4: no snapping; §12: stage 2 places at z = 0 | text |
| T-B3 | §8.1 and D36 (1): any-face attachment; side contacts carry no load (a Known gap) | text |
| T-B4 | §8.2: SPD per anchored island; a singular, non-finite or uncapped result is `unstable`, never an exception | text |
| T-S1 | §11.3: classes, with world outcomes never fed back; reused codes so the representation doesn't leak | text |
| T-S2 | §4.2: exact per-kind overlap, containment refused; the minimum > 2 × the tolerance | text |
| T-S3, T-S4 | §11.1: the loader's cross-checks and value checks, each with its test and gate row | text |
| T-S5 | §3.1: per-role limits and an `object_contact` limit; §13 S4: a B5 budget for re-solves | text |
| T-S6 | §11.3, as Wire S3 | text |
| T-S7 | §4.3: the whole region enters in one batch at the drain; cell parts' occupancy in µm | text |
| T-S8 | §11.2, as A-B8 | text |
| T-S9 | §3.2: `inert` on a cell part is defined (load only); `role: fuel` is `kind_not_admitted`; `air` exempt (§2.2). **Partial:** why scenes admit only `inert` isn't stated | text |
| T-S10 | §13 S1: the never-crash property | text |
| T-N1 | §7.1, as D-S3 | text |
| T-N2 | §6, as A-S9 | text |
| T-N3 | §11.4: the save reader's refusals | text |
| T-N4 | §12: the spike's stage-2 row | text |

## Not folded, and why

- **A-S7, the placement table:** the word budget is spent. It is proposed to move to S1's module plan.
- **Physics S4:** moved to S2 as a test with its closed form.
- **Physics N3, N4; Bio N3; Determinism D-S4:** no change, with the reason in each row.

## The owner's questions this fold leaves

1. **The minimum part thickness** rises to 3 mm (§14 item 1), so a 1 mm steel sheet is refused.
2. **Who carries S0's edits to `fire_solid.md`** before 6.0a (§14 item 2). No branch for 6.0a exists yet. The
   worktree `.worktrees/fuel-leftovers` (`phase1/fuel-leftovers`, another session's, at `main` with no commits) is the
   nearest fire-line branch.
