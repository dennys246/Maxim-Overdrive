# Sub-cell solids design, round 1: Determinism and replay (2026-11-22)

This is the reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the
fold.

**Reviewed:** `docs/design/subcell_solids.md` at 1c701aa. The reader read it against these sources:
- `fire_solid.md` §1, §2, §5.4–§5.5;
- `sim_core.md` §5–§9;
- `world_model.md` §1.1, §5–§8;
- `boundaries.md` §6.3;
- D31–D35 and survey §2, on `phase6/specgen-spike` at 91ebd0d;
- today's `frames.py`, `damage.py` and `imagination.py`.

The probes ran with `-I` in the main checkout's venv (numpy 2.5.4); the scripts were kept in the session scratchpad.

**Summary:** 3 BLOCKER, 5 SHOULD-FIX, 3 NIT.

## BLOCKER

### D-B1. `subcell_solids.md::§2.1`: the threshold comparison on authored floats depends on placement

**Defect.** §2.1 computes t(p) = `min(max_m − min_m)` in float64 and compares it with `object_threshold_m`. §0 (1)
claims the part's offset never enters it.
- `imagination._read` places a spec by translating its primitives (`_offset`), so the subtraction runs on translated
  values.
- Even local values aren't exact: `0.7 − 0.3` is `0.39999999999999997`.

**Measured.** A 0.4 m part (local [0, 0.4]) was placed at 2,001 offsets, 1 mm apart, from 0 to 2 m:
- t < 0.4, so an object, at 682 offsets;
- t > 0.4, so cells, at 679;
- exactly 0.4 at the rest.

The same happens at `min_part_thickness_m`, where a part is refused or accepted by offset. It also happens in §4.2's
1 mm separation test for object-to-object contact: an authored 1 mm gap is a contact at 990 offsets and not at 1,003.

**Failure scenario.**
- The generator emits a plinth exactly 0.4 m thick, the kind of round number an LLM writes.
- Placed at x = 0.177 m, it becomes a structural object with a 1-D profile and a capacity. At x = 0.178 m it becomes
  cells.
- So two replays that differ only in `origin_m` reach different outcome classes under the same fire and load. That is
  D34's defect come back at the threshold.
- S1's red-first test (§13) can't catch it: its specs have 1–4 cm parts. §2.2's test of 0.38, 0.40 and 0.42 m blocks
  checks only one placement.

**Fix (verified for thickness).**
- Judge every metric threshold on authored geometry in whole micrometres: t_µm = rint(hi·10⁶) − rint(lo·10⁶), with
  each threshold stored as integer µm. In 800k random placements within ±50 m, using four local spans of 0.4 m, t_µm
  was always 400,000.
- Better still, take t in the spec's local frame before translation.
- Feed the same quantized t to the Biot number, the node count and the mass, so no float version of t survives
  downstream.
- Add a Hypothesis property over placement offsets, with parts sitting exactly at each threshold.

### D-B2. `subcell_solids.md::§8.2` (Cadence): the solve's skip rule keys on the wrong inputs

**Defect.** The solve reruns "only when a topology batch or a member's strength factor changed". But it reads more
than that:
- each vertex's weight, which falls continuously as fuel burns (node densities, `removed_kg`) and as structural wood
  chars (`burns_as`);
- each member's section, which for D31's charring leg must come from node thicknesses, because §3.1 keeps geometry
  immutable;
- possibly `integrity` after a strike; the design doesn't say whether capacity reads it.

This breaks `sim_core.md` §7's rule that a cache's key is the values its result reads. §11.4 also says that on load
the solve "must equal the stored digest", yet the solve's output isn't one of the members §11.4 digests.

**Failure scenario.**
- A crate of fuel burns on a cold steel shelf. No topology batch happens and the shelf's strength factor never
  changes, so the solve never reruns, and the shelf keeps carrying the crate's initial weight.
- Save at tick 4,000 and load it. The load recomputes the solve from current masses and gets a smaller load.
- Either the derived-state check refuses a valid save, or the continued run and the reloaded run gate member failure
  on different loads.
- Either way a replay from the save stops matching the continuous session, which breaks "replays are first-class".

**Fix (unverified).**
- Make the solve a pure function of declared, versioned reads. Either rerun whenever any read field's write tick
  changes, or key it on the versions of mass, section, integrity and strength factor.
- Say whether the per-member load is saved or derived, and give it a digest member.

### D-B3. `subcell_solids.md::§6`, `§8.1`, `§8.3`: object state changes are not topology batches

**Defect.** Gap areas and the member graph are rebuilt "per topology batch". §6 relies on "the next batch" to reopen
a breached pane's gap, and §8.1's vertices are objects whose state is `live`.

`sim_core.md` §5.1 lists the topology request kinds: `material`, `original_material`, `region_id`, a new cell's
`integrity`, and keyed-table rows (`pending` and the id counter). An object's state (breached, `failed`, `removed`)
and its `support` are not among them, and the design never adds them.

**Failure scenario.**
- A pane breaches at tick 1,200. Its gap stays closed until an unrelated topology request arrives, say a strike on a
  wall at tick 1,900.
- On the 0.2 m and 0.1 m grids that strike lands on different ticks. So the zones join at grid-dependent times, and
  the next room gets a different outcome class for a reason that isn't physics.
- A save made between ticks 1,200 and 1,900 reopens the gap as soon as it loads, so the loaded run diverges from the
  continuous one.
- §6's own Hypothesis property (incremental state equals a full recompute) fails at every tick in that window.
- For load: a failed member stays a vertex until the next batch, so load is still routed through it, and `support`
  `loose` is judged on a stale graph.

**Fix (unverified).**
- Declare object state transitions (breach, `failed`, `removed` and `support`) as topology requests, so each bumps
  `topology_version` in the step it happens.
- Add that request kind to §12's revision of `sim_core.md` §5.1.

## SHOULD-FIX

### D-S1. `§8.2` (the solve): determinism is asserted, not contracted

The design says the factorization is deterministic but leaves the solver to S4. These requirements are contract,
because other modules depend on them:
- **A direct solver, not an iterative one.** An iterative solver stops after a number of iterations that depends on
  the bits, and the count differs across machines.
- **BLAS and thread count recorded.** MKL without CNR mode is a known case of results that aren't deterministic on one
  machine.
- **Solve anchored components only.** A loose component's matrix is singular: depending on pivoting it raises
  `LinAlgError` or returns garbage. §8.3 decides looseness after failure, so the order of the two steps matters.
- **Solve each island on its own, ordered by its smallest key.** Then an unrelated object can't change the matrix
  that splits a table's load between its legs.
- **The solver's identity goes in the `load` law's version.**

Measured on one machine only: a dense n = 1,500 `np.linalg.solve` gave bit-identical results over 20 reruns, and a
4×4 block embedded in block-diagonal systems of n = 50, 200 and 800 solved bit-equal to the block alone. That is
evidence for splitting by island, not a guarantee.

### D-S2. `§8.3`: cascading failure has no ordering rule

When a member fails and the load it shed overloads others, the design doesn't say what happens next: re-solve to a
fixed point within the same step, fail the next one in the next step, or fail the most overloaded member first. Across
grids, two legs near capacity can swap which fails first, so the table falls left at 0.1 m and right at 0.05 m. Make
the rule contract. For example: every member over capacity fails at once, re-solve, and repeat until nothing more
fails, with an iteration cap counted as work.

### D-S3. `§7.1`: strike and `kindle` have no tie-break

- A strike point within 1 mm of a surface is often within 1 mm of two of them: a leg and the top it carries, or an
  object and a cell face.
- `kindle`'s nearest-surface query can tie exactly on axis-aligned boxes.

Without a rule, iteration order decides which part's integrity drops. State one, for example: smallest distance, then
cells or objects first (pick which), then smallest `object_id`.

### D-S4. `§7.3`: one formula can't meet the bit-identical pin for cell-only regions

- **Today:** `temperature_mean` is `np.mean` over a gathered subset.
- **The new formula:** a volume-weighted Σ(T·dx³)/(n·dx³), and its `bincount` form, differ from `np.mean` in 576 of
  1,200 cell-only cases across 0.2, 0.1 and 0.05 m.

So the pin holds only with a branch that keeps today's expression for cell-only regions, which is a special case.
Meanwhile `fire_solid.md` §5.4 forbids exactly today's gathered-subset form for objects (DP-S2). Either record a digest
break and pin the new expression, or make the branch contract. In both cases, fix the reduction order: cells by flat
index, then objects by key.

### D-S5. `§6`: blocked area is a sum, not a union, and its integers are undefined

- **The sum can exceed the face.** Panes 0.5 mm away on either side of the gap plane don't overlap in 3-D (§4.2 allows
  1 mm), but each blocks the whole face. Blocked area is then twice the face area and open area goes negative, and
  clamping it would hide a symptom. Use the area of the union.
- **Discs aren't integers.** An upright cylinder over a horizontal gap projects to a disc, whose area isn't an integer
  function of integer geometry. Computing it needs `asin` and `sqrt`, and libm's `asin` differs across machines. Name
  the rounding rule, or use a formula with only IEEE-exact operations, or a fixed sub-sampling.
- **Several terms are undefined:** "within 1 mm" when an object spans the plane; the rounding mode; the dtype, which
  should be i64, since 1 m² is 10¹² µm².
- **Wrong citation.** The micrometre edge rule is `tile_and_client.md` §1.3's; F13 is the scene loader.

## NIT

- **D-N1. `§3.1` `pose`: give it a canonical form now.** It is digested, and §8.3 promises no format change at D32, so
  fix the component order (w first or last), the sign (w ≥ 0) and +0.0 for zeros. Without that, D32's first write of
  the identity pose can change the digest when nothing physical changed.
- **D-N2. `§11.4`: name the digest break for existing fuel rows.** "5a's goldens unchanged" is true, but the new
  `objects` columns and the table rename (the member's name is hashed, `sim_core.md` §9) change every golden that has
  fuel objects in it. Record it as a break under `sim_core.md` §12, and give the new tables' place in registry order.
- **D-N3. `§3.1`, `§8.1`: id minting and anchor identity.** Say that ids are minted in primitive order within a spec
  and in entry order at scene build; the matrix and the digest both follow id order. "One anchor per cell region"
  breaks when a region splits: an object on the half that lost its anchor still reads as supported. Anchors per
  component need component identities with a metric key, because `ndimage.label` gives no persistent identities
  (`world_model.md` §6).

## Checked, nothing found

- **Bearing angle.** Every v1 face normal is axis-aligned (pose at identity), so the 30° test is never near its
  threshold.
- **Biot choice.** It is computed from data with IEEE operations only and fixed at insertion. Its one exposure is the
  float t of D-B1.
- **Glass cracking band.** The band gate lives in the tests, and the runtime check is a float comparison that is
  deterministic on one machine. One note for the Physics lens: the 1-D profile has no "edge nodes", so the criterion
  has nothing to read.
- **Object-to-object contact.** Each transfer is antisymmetric, keyed and sorted, apart from D-B1's separation
  threshold.
- **Zone-face areas.** They are cached per `topology_version` and summed in sorted order, subject to D-B3.
- **Header.** It covers `limits.yaml` and `mechanics.yaml`. The solver identity should ride in the law version
  (D-S1), and spec v1 rides in each `imagine` record.
- **Hidden nondeterminism.** The design introduces no randomness, wall clock or builtin `hash()`.
