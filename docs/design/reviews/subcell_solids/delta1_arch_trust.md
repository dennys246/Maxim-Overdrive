# Sub-cell solids design, delta 1: Architecture and Trust boundary (2026-11-22)

The reader's report as handed back, saved by the author. The reader set every status below, read from the tree at
ed2c9ae.

**What the reader read:**
- the diff from e37eb3e to ed2c9ae on the three files;
- the full folded `subcell_solids.md` (5,986 words), both round-1 reports, fold1.md and D36;
- `refusals.py`, `imagination.py`, `fire_solid.md` §4, §5.2 and §5.3, `world_model.md` §2 and §6, `sim_core.md`
  (craters) and `contracts.md`.

The D36 row matches the owner's seven rulings.

## Status of round-1 findings

| Finding | Status | Note |
|---|---|---|
| A-B1, T-B1 | fixed | §2.1 works in integer µm in the spec's own frame; see N-S1 on the quantum's domain |
| A-B2 | fixed | §6 defines an opening as an authored interface in µm; a full pane gives 0 at every grid |
| A-B3 | fixed | cell regions are loads and supports (§8.1), handed to D22 (§8.3); see N-S2 |
| A-B4 | fixed | state changes are Topology requests (§7.4); §6 excludes breached objects |
| A-B5 | fixed | the object resolver sits in `damage.loads`'s tuple, `per_record` |
| A-B6 | fixed | `ignite` has no row; `kindle` covers objects |
| A-B7 | fixed | tiles, in-plane conduction and a glass edge band (§3.3) |
| A-B8, T-S8 | fixed (contract) | one tagged v1 (§11.2), applied at S0, triggered by S0 landing before 6.0b; see N-S4 |
| A-S1, A-S2, A-S5, A-S6, A-S8, A-S9, A-S10, A-S11 | fixed | |
| A-S3 | deferred, in part | cadence, key, writers and `contact_exchange` fixed; statics' registry row (name, version, reads, writes) deferred. Trigger: S4's review must see that row |
| A-S4 | open, in part | `anchored` is gone and D36 (1) settles D33. Still unanswered: §3.2 says inert and fuel parts "carry nothing", but §8.1 makes them rigid vertices; whether a sheet on a fuel crate is attached, and whether the crate passes its load down, is unsaid |
| A-S7 | deferred | Trigger: S1's branch carries the placement table in its module plan, with one shared home for §2.1's rule used by `scene`, `place` and the scorer |
| A-N1, A-N2, A-N4, A-N5 | fixed | |
| A-N3 | rejected, reason accepted | thermal exposure values stay in `mechanics.yaml`; `MaterialCatalogue` is fixed |
| T-B2 | fixed | the floor is an anchor, no snapping, and §12 has the spike place its scene at z = 0 |
| T-B3 | fixed | by D36 (1); side contacts carrying no load is a Known gap |
| T-B4 | fixed | three degrees of freedom, SPD per anchored island, singular or non-finite is `unstable`; see N-N3 |
| T-S1 | fixed | codes classed and reused; see N-N1 |
| T-S2, T-S4, T-S5, T-S6, T-N1, T-N2, T-N4 | fixed | |
| T-S3 | fixed | see N-N2 |
| T-S7 | fixed as written | the fix created N-B1 |
| T-S9 | fixed | scenes take `structure` by default, `inert` when authored, fuel only through fuel entries; see N-S3 |
| T-S10 | fixed, NIT left | S1 still says "every §11.3 code at its gate", but `not_on_surface` and the §8.4 codes arrive at S3 and S4 |
| T-N3 | fixed as written | the fix created N-S5 |

## New findings in the folded text

### BLOCKER (contract)

**N-B1. `§4.1`, with §4.3 and §8.1: contact, overlap and support are judged on a cell region's authored primitives,
which go stale as soon as cells are destroyed.** Strikes destroy cells (`sim_core.md`'s crater; mass to fines,
`world_model.md` §2), and Phase 2's rubble does the same, but §4.1 judges against authored primitives "never against
cell faces", and §4.3 keeps a region until its last live cell is gone.

*Failure scenario:*
1. A steel beam bears on the alley's wall top, and a strike craters the wall under the bearing.
2. The beam stays `attached`, bearing on authored concrete that is now air, and statics carries its load into the
   void.
3. §4.1's exchange "lands on the cells under the authored patch" and now targets air cells. Either a law heats air,
   which §5.2 forbids, or the transfer has no recipient, which breaks §5.3's ledger.
4. In reverse, `imagine` into the blasted gap is refused `space_taken` against concrete that is gone.

The round-1 text, which judged on cell faces, didn't have this; Physics B7's fold introduced it.

A second gap in the same contract: an imagined region's primitives are now load-bearing state, but §11.4's save and
digest don't carry them.

*Fix:* no mechanism proposed. The contract must say what geometry a damaged cell region presents in µm. Two options,
both unverified:
- authored primitives minus metric crater volumes, kept as µm records;
- primitives clipped by cell liveness, with the dx dependence declared as a §2.3 gap.

**B33:** a new contract BLOCKER in folded text, so the stop rule's condition is met. N-B1 folds or the owner
overrules it.

### SHOULD-FIX

- **N-S1, `§2.1`: the quantum q(v) = rint(v·10⁶) has no domain and no stated application point.**
  - Domain: `_read` checks finiteness only, and §2.1 quantizes before `outside_extent`. x = 1e15 m gives
    `np.rint(1e21).astype(np.int64)` = 9223372036854775807 with "invalid value encountered in cast" (verified): a raw
    RuntimeWarning under warnings-as-errors, not `SpecRejected`, or a garbage thickness.
  - Application point: q(hi) − q(lo) or q(hi − lo); 2·q(r) or q(2r). At half-µm radii, 42,824 of 200,000 differ
    (verified).
  - It is an interface every implementer computes. Fix (unverified): bound |v| before q, refused `out_of_range`;
    quantize coordinates and the radius, then use integers.
- **N-S2, `§8.1` and §8.2:** an unanchored cell region is a statics vertex, but no region column or §7.4 request kind
  holds its `unstable` or `loose` outcome. A slab on posts loses a post, and D22's hand-off can't tell which cells
  lost support.
- **N-S3, `§3.2` against §8.1:** an inert cell part is "a load and never a support", but every floor-connected cell
  region is an anchor. An inert plinth on the floor is both, so a part on it is `attached` or `unsupported` by which
  sentence is read, and that changes refusals.
- **N-S4, `§11.2`:** "tagged" v1 names no tag. Fuel entries also carry `kind` and `geometry`, so
  `{kind: slab, material: steel}` or `{kind: box, recipe: crate}` gets `kind_not_admitted`, `missing_field` or
  `unknown_field` by dispatch order, codes of different classes.
- **N-S5, `§11.4`:** refusing a save whose `support` or `state` differs from recomputed statics refuses legitimate
  saves. `state` is history: `failed` is sticky while σ(T) recovers on cooling, and `burnt_out` and `removed` aren't
  statics outputs. Fix (unverified): check only `support`, recomputed given the saved `state`.
- **N-S6, `§8.4`:** "the base" in `parts_disconnected` is undefined. A valid spec whose lowest part sits at
  z = 0.002 m, or a fixture authored downward, reads disconnected, and the generator is taught a false fault.

### NIT

- **N-N1:** fuel geometry keeps `geometry_out_of_range` while structural parts get `out_of_range`, against D36 (4)'s
  one set of codes. The new `world_limit_*` members aren't listed in §11.3.
- **N-N2:** `breach_ligament_um` < `min_part_thickness_um` crosses two files, and no loader is named for the check.
- **N-N3, `§8.2`:**
  - one singular sub-part, or the iteration cap, marks a whole island `unstable`;
  - statics' `support` requests bump `topology_version`, which is in its own key, so it must emit only on a change, or
    it reruns every step.

## Verdict

The fold resolves almost every Architecture and Trust finding. A-S3 and A-S7 are deferred, A-N3 is rejected with a
reason accepted, and part of A-S4 is open. One new contract BLOCKER (N-B1) triggers B33's stop rule. N-S2 to N-S5 are
one- or two-sentence contract defects, and N-S1 is contract because every implementer must quantize the same way. The
NITs can move to S1 and S4 as tests.
