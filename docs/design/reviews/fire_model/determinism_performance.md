# Fire model v1 design review: Determinism, replay and Performance

Lens: Determinism and replay, plus Performance. Reviewed: `fire_model.md` at 54358fd, against CLAUDE.md,
`world_model.md` §1.2, §6, §8–§9, `splitting.md`, backlog B2 and B5, L5, and on the membrane branch (`gates`, 396ae10)
`architecture.md` Known gaps, `boundaries.md`, `realtime_lanes_coop.md` and `heat.py`.

**Measurements** (mine, D): scripts and output in `_durable/fire_model_review/scratch/` (`p1_*`, `p2_*`). numpy
2.5.5, scipy 1.18.1, Python 3.14.6, arm64, thread variables at 1, `process_time`, best of 3–5. **Load 3.6–4.9**
(L5's was 2.6): absolute times are upper-ish; the ratios are the finding.

**Counts:** 3 BLOCKER, 7 SHOULD-FIX, 3 NIT.

---

## BLOCKERS

### DP-B1. A substep cap that "dilates world time" has no defined behaviour, and the mechanism it cites can't bound a loop

**Location:** `fire_model.md::§8.1` ("in play, world time dilates (D21) and the dilation is reported"), and §6's
n-cap test.

**The problem.** In this architecture, dilation belongs to the host. "Dilation is measured in the host and enters the
`Simulation` only as recorded data" (`boundaries.md`, Arch N7), and it is "log metadata the `Simulation` never reads" (Wire S7). It slows the wall clock
against world time and never changes what a step computes. A cap that binds *inside* `World.advance` therefore has only three possible meanings, and
the note picks none of them:

1. **Keep taking substeps past the cap and let the host report dilation.** Then the cap isn't a cap. K2_005's
   n = 2.8×10³⁹ (L5 §0) is still an endless loop, and the host can't interrupt a step it is waiting on.
2. **Clamp n at 16 with dt above the stability bound.** The explicit law overshoots (K2_005's NaN path) or errs
   silently, changing the outcome only where the cap binds.
3. **Advance less world time per step.** This breaks the fixed 0.5 s step and integer ticks, and puts a 0.05 m run
   whose cap binds on a different clock from 0.1 m, so R4's "time to peak ±40%" compares different clocks.

**Failure scenario.** A play session hits a sliver patch and "dilates". Its replay, filed as a bug report (B2), hits
the same cap in the harness, which "fails loudly". The session can't be reproduced, and the play path after the cap
is the one nobody tests.

Across machines, n = ⌈0.5/stable_dt⌉ comes from state that may differ by an ulp (`np.exp`, L5 §2), so a cap can
bind on one machine and not the other: a precision difference becomes a code-path difference.

**Fix.** Define the cap as physics, the same in play and in test.
- The stiff laws are implicit, as §8.1 already plans for conduction, so they need no cap.
- Any law that stays explicit substeps **locally, per patch or element**. L5's subset-independence result makes
  that safe, and one sliver can then no longer set n for the whole grid.
- A binding local cap is a **cap event** with a defined fallback (that patch steps implicitly), counted in the
  digest and tick status, identical in play and test. World time never shortens.
- Graded scenarios require zero cap events; one test forces one and checks rerun and replay bits.

### DP-B2. The visibility cache, as described, breaks save/load and replay-from-save bit-identity

**Location:** `fire_model.md::§8.3`, row 3 ("a visibility cache"); L5 §4 (iii): the cache is "keyed on topology
version … or when a flame's bounding box changes bin".

**The problem.** A cache that is recomputed only when its key changes returns whatever was computed **when the key
last changed**. Here that is the visibility for the flame geometry at that moment. Flame height changes every step
(it follows Q), so the cached value depends on the run's history and not on its current state.

**Failure scenario.** A flame grows inside one bounding-box bin from t₀ to t₁.
- A continuous run uses the visibility computed at t₀ for the whole interval.
- A save at t (t₀ < t < t₁), loaded later, starts with an empty cache and computes visibility from the geometry at t.
- From that point the two runs diverge.

The saved game no longer reproduces the session. `world_model.md` §6's property ("incremental state equals a full
recompute bit for bit", which is what lets the save's derived-state check work) fails on the first fire. The digest
can't catch this: the cache isn't state, yet it changes state.

**Fix.** Either:
- make each cache entry a **pure function of its key**, computed from bin-snapped geometry, never from the geometry
  current at the moment of the miss; or
- put the cache in the save and the digest.

Snapping makes occlusion step between bins, so bins are sized in metres and R2.5's offset test covers them. Add a test: in a fire scenario, save and load at every physics step, and
require the same digests as one continuous run.

### DP-B3. K = 2 element slots can't hold the exit scene, and slot overflow depends on the grid

**Location:** `fire_model.md::§2.1` ("key (cell, slot), K = 2 slots, reserved in the format") and §7. This overlaps
the Physics lens, but the failure is a format and determinism one.

**Failure scenario.** In §7's exit scene, a starter sits under kindling that leans on a crate packed with cardboard.
- A cell at the crate's base holds the crate's bed element and its cardboard, and touches the kindling stick and the
  starter. That is 3–4 elements in one 0.1 m cell.
- A 0.2 m verification cell has 8× the volume, so more objects coincide there.
- Either authoring refuses the scene at 0.2 m but not at 0.1 m (an outcome that depends on dx, so the cross-tier
  test can't even run), or something merges or drops an element.

"Reserved in the format" means that fixing this after save v0 is a format break.

**Fix.** Key elements by (cell, persisted object id), any count per cell (CSR row offsets), sorted by that key;
patches by (cell, object, patch). The cost is unchanged.

---

## SHOULD-FIX

### DP-S1. "Exact sleep" isn't established: subset independence isn't step exactness, and Arrhenius kinetics forbid sleep

**Location:** `fire_model.md::§8.3` (last paragraph), and the inference it relies on in L5 §4 ("So sleeping or
waking surfaces can't change results").

L5 showed a surface solved **alone** matches the batch; exact sleep needs **skipping** a step to match **taking** it.
Measured on a backward-Euler 20-node patch with FDS's linearised front, at exact ambient equilibrium, no flux (`p1` (a)):
- **The note's full form** (solve for T_new; rhs carrying 3εσT⁴ + εσT∞⁴) changed the bits on **200 of 200 steps**,
  drifting 9.8×10⁻¹² K, and it did so at every ambient value tried.
- **The delta form** (solve for ΔT, with rhs equal to the explicit residual, which is exactly 0 at bitwise
  equilibrium) changed the bits on **0 of 200** steps.

So under the full form, sleep changes the digest, and world_model §1.2's sleep on/off test goes red.

**Kinetics.** L5 §2's illustrative one-step Arrhenius (A = 10⁸ s⁻¹, E = 125 kJ/mol) at 20 °C removes **18 ulp** of
380 kg/m³ per 0.5 s step (472 at 40 °C; probe (b)). **No fuel patch under Arrhenius is ever exactly quiescent**, so
all fuel stays awake and cost scales with the district's fuel, not the fire.

**Fix.**
- Require the delta form.
- Make "is exactly zero below a stated temperature" a criterion in R0's rate-law choice (§3), so the choice is
  graded on cost as well as fit. The threshold law has it; Arrhenius needs a cutoff that is written as part of the
  law.
- Sleep predicate: bitwise equilibrium, zero forcing; each rung tests sleep on/off for identical bits.

### DP-S2. A "fire bounding box" isn't an exact sleep region, and cropped reductions change bits

**Location:** `fire_model.md::§8.3` ("exact sleep plus a fire bounding box"). The note's own §5.2 conflicts with it.

Flame radiation has unbounded range: view factor falls off as 1/r², so it never reaches zero. §5.2's whole case is
that radiation reaches an NPC **before** contact, which means outside any compact box around the fire. Sleeping
receivers outside the box drops real flux, and R2.5 requires "radiated power = χ_r·Q to round-off", which then
fails.

**Cropped reductions.** Measured in `p1c_sum_mask.py`: a pairwise `np.sum` over the awake rows gathered out differed
from the same sum over the full table with zeros for sleepers in **56 of 200** random masks. A sequential
`np.bincount` differed in **0 of 200**. So any ledger, zone or region reduction written as `np.sum` over a cropped
array changes bits whenever the crop changes.

**Fix.**
- Sleep only laws whose support is compact, under DP-S1's exact predicate.
- If radiation gets a cutoff, it is a law in metres and W/m², the same in every mode, with the dropped power booked
  on the ledger. It is not a sleep optimisation.
- Reductions are `bincount` or fixed-order sums over the full table, never `np.sum` over a gathered subset.

### DP-S3. Clustering and flame identity: order, labels, thresholds and RNG

**Location:** `fire_model.md::§4.1` (Clustering), §2.1, and §5.1 (Sight: flicker).

Measured in `p2_cost.py` §4: `connected_components` on the same patches in a permuted row order gives **the same
partition but different label numbers**. In `p1_sleep_and_sums.py` (c), a `bincount` over the same values in
permuted row order gives **different bits**. The note sorts element rows but says nothing about patches, flames,
cluster ids, or when rows are inserted. Four failure scenarios:

1. **Insertion order.** A patch appended on ignition, not inserted at its key, changes Q's summation order; a save
   rewrites the table sorted and loads with different bits.
2. **Label identity.** If flames carry state (flicker phase, tilt), a scan-order label that renumbers when another
   cluster appears hands one flame's state to another.
3. **A threshold in metres.** "Connected burning area in metres" needs a contact distance. Whether two patches
   merge is binary, and a merge changes the flame: Heskestad's L(2Q) = 1.32·L(Q). Patches are also cut per cell (an
   object straddling cells is one element per cell), so connectivity by cell adjacency would make a stick's flame
   count depend on dx.
4. **RNG.** If flicker or anything else draws from `World`'s sequential Generator, a merge changes how many draws a
   step makes, and every later draw shifts.

**Fix.**
- All tables (elements, patches, flames) stay sorted by canonical integer keys. Inserts and removals happen only in
  the per-physics-step topology batch (`world_model.md` §6), never mid-substep.
- Cluster id is the minimum member key. If flames are stateful, give them a persisted id with a written merge and
  split rule (the survivor is the minimum id).
- Connectivity comes from object geometry in metres, not from cell adjacency. The R2.5 and R3 offset tests run with
  bases at dx/3 and 2dx/3.
- Any randomness is counter-based, keyed by (flame id, tick) (numpy `Philox` with a key), not drawn from a
  sequential stream.
- State whether flames are stateless; the save format depends on it.

### DP-S4. Area retirement is an outcome threshold that can erase slow spread, and it loses more than energy

**Location:** `fire_model.md::§8.2`.

"A part below a minimum size … is retired and its energy merged" says nothing about its **area, inventories or
latch**.

**Failure scenario.** At 0.1 m, a patch about 0.01 m² starts slow spread at 0.1 mm/s across a 2 cm front, in the
preheated R2(a) regime near its band. The newly ignited part grows by about 10⁻⁶ m² per 0.5 s step, which is right
at the (1 mm)² floor.
- If the new ignited part is retired each step before it grows past the floor, spread never nucleates.
- The front's width inside a patch depends on how cells cut the object, so whether it nucleates can differ between
  0.1 and 0.05 m.

That is a class flip produced by a hygiene rule.

**Fix.**
- Retirement merges the part into its sibling part of the same patch, conserving area, every inventory and energy.
  Its latch merges by a written rule.
- An ignited part never vanishes; it folds into the patch's ignited-area fraction.
- Test: sweep the floor ×0.1 and ×10 and require the same outcome class. Where no part comes near the floor,
  require the same bits.

### DP-S5. The cost table understates realistic cost several-fold, and its flame count is the unmeasured crux

**Location:** `fire_model.md::§8.3`.

**1D solids.** The table quotes the bare Thomas solve at about 8 ns/node. A full step costs far more. My full step
covered k(T) and c(T), a per-node Arrhenius `exp`/`expm1`, the mass and energy sink, the linearised front,
backward-Euler Thomas and a ledger `bincount`. It took **21–23 ns/node**, 7.5–8× the bare Thomas solve (2.7–3.1
ns/node here):

| Surfaces, 20 nodes each | Time per step |
|---|---|
| 20,000 | 9.3 ms |
| 52,000 (the ~5×10⁶-cell scale) | 22 ms |
| 100,000 | 43 ms |

The note doesn't say **how often** the solid couples to the gas.
- Once per physics step, 9–22 ms is affordable.
- Inside every Lie substep, at heat's current floor of 16 substeps at 0.1 m and 64 at 0.05 m (`heat.py`
  `min_substeps`), it costs **150 ms at 0.1 m and about 600 ms at 0.05 m**, the verification grid the gate runs
  (before counting the extra patches that finer cells create).

**Radiation** (`p2_cost.py` §2–3):
- **View factors.** The analytic cylinder view factor costs about 39–41 ns per (flame, quadrature point) pair. For
  10 flames and 20,000 patches, that is 7.7 ms at 1 quadrature point and **31 ms at 4**. §4.1 asks for "quadrature
  points fixed in metres on each receiving patch", so 4 points is the realistic case.
- **Occlusion.** A ray march on a 1.92×10⁶-cell grid costs 9–9.5 ns per sample. 800,000 rays × 32 samples is
  **243 ms**. That puts an uncached evaluation with occlusion at about **275 ms**, against the note's "~5 ms".
- **The cache doesn't help during growth.** Flame geometry changes every step (DP-B2), so the cache misses on every
  step that matters.
- **Undersampling.** 32 samples over 10 m step over a 0.2 m wall; voxel traversal needs path/dx samples, 3–6× more.
- **Flame count.** The table assumes 10 flames. With no merging model (§4.1) and gaps between slats, a burning crib
  is one cluster per disconnected burning face, which could be **hundreds**. At 200 flames the view factors alone,
  unoccluded, take **656 ms** per evaluation.

**Clustering:** 10 ms at 20,000 patches, 29 ms at 52,000. **Baseline:** the table's tile is 640k cells; the
over-real-time figure it cites is the 1.92×10⁶-cell tile.

**Fix.**
- Re-derive the table with full kernels and a stated coupling frequency.
- Count flames in TN 2102's crib from its geometry before R2.5.
- Name the radiation scheme whose cost is bounded in the **flame count**: either merging, or a per-element
  emitter that receivers sum by `bincount`.

### DP-S6. No budget is set, and a 20% wall-time gate on a loaded machine doesn't guard this

**Location:** `fire_model.md::§8.3` ("every rung carries a cost-regression gate") and §6 ("a cost-regression gate
from R4"). The two sections disagree about when the gate starts.

The server already takes 0.7–1.45 s per 0.5 s step (Known gaps), and timings here moved 2× with load, so a 20%
wall-time gate (B5) alone is flaky or gets loosened.

**Fix.**
- Write a **fire budget** before R2.5, for example "fire kernels ≤ X ms per physics step at the 1.92×10⁶-cell tile
  with the crate at peak", and record it in Known gaps.
- Make the **primary gate deterministic work counters** (node solves, view-factor pairs, ray samples, cluster
  edges, cap events per step): exact, load-independent, and any increase is a reviewed diff.
- Keep B5's `process_time` (min of N, 20%) as the secondary gate.
- Gate the **worst-case** scene (maximum flame count), not the mean, from R2.5, which is where radiation enters.

### DP-S7. New state isn't enumerated for the digest and the save, and the 1D profile is created lazily

**Location:** `fire_model.md::§2.3` item 4 (only "latches" are named), §3 ("each **burning** surface patch carries a
1D in-depth grid") and §9.

**Failure scenario.** R0 *is* heating before ignition. If the 1D profile is allocated when a patch starts burning,
the preheat history is lost, and "this patch has a profile" becomes a threshold decision that changes outcomes.

**Format gaps:**
- Node arrays are ragged, shaped by the material table, so a table edit makes old saves unreadable.
- Recipe ids are integers in element rows. `world_model.md` §8 F8 keys species by name, never by position, and the
  same must hold for recipes.
- Flame objects, if derived, need a `derivation_version` (F15).
- The new acts (`light`, `apply`, `carry`, `drop`, `place`) are an intent-vocabulary bump.

**Fix.** Every fuel patch carries its profile from authoring (sleep makes it cheap). §2.3 lists everything in the
digest and save: element and patch rows with object ids and node arrays, inventories, latches, flame state if any,
cap and retirement counters, the material-table hash in the header (refuse or migrate), a recipe name map, and the
declared memory budget from patch count × N per class (F14).

---

## NIT

### DP-N1. A cap of "e.g. 16" collides with heat's current substep counts

**Location:** `fire_model.md::§8.1`.

The `TEMPORARY(phase1/sim-clock)` floor in `heat.py` already takes 64 substeps at 0.05 m. A global cap of 16 binds
at the verification grid on every step, unless the cap is per law. Say that it is.

### DP-N2. Subset independence of `np.exp` is shown only on arm64

**Location:** `fire_model.md::§8.3`, final sentence.

0 mismatches in 170 offset/length slices on arm64 (`p1` (d)); x86 SIMD body/tail paths are untested. Add the
offset test to CI at threads 1 and N.

### DP-N3. The cost table cites one load and one stack

**Location:** `fire_model.md::§8.3`.

Report load range, stack and CPU-dispatch features beside each figure (F16).

---

## What is sound

A hand-written Thomas solve with no BLAS, an exponential update at frozen T, `bincount` reductions over rows sorted
by integer key, and single-threaded clustering are all deterministic. Backward Euler needs no cap, and extending it
to the other stiff laws is DP-B1's root fix.
