# Determinism and replay, Concurrency and lanes, Performance: world_v2.md (at d596418)

Reader brief: `docs/code_review.md`, the **Determinism and replay**, **Concurrency and lanes** and **Performance**
rows, and "Design reviews". Read: `docs/design/world_v2.md`, v1 §2 and §4 (`realtime_lanes_coop.md`), the v1
reviews `determinism.md`, `concurrency_performance.md` and `delta1_determinism.md` (DD1 to DD10),
`research/states_of_matter/architecture.md` (the source of the 91 B/cell and relabel figures), and the code in
`.worktrees/act-validation` at 02cd9e3 (`world/heat.py`, `world/grid.py`, `world/world.py`,
`tests/test_determinism.py`), plus the installed pymaxim 1.3.3.

Measurements were run here (numpy 2.5.4, scipy 1.18.1, Python 3.14.6, Accelerate BLAS/LAPACK), best of 3 to 5, on a
synthetic 16×10×4 m tile (floor, outer and interior 0.4 m walls, 40 crates; 24% solid). Scripts are in the session
scratchpad, not committed. Every run took under 30 s.

Counts: **2 BLOCKER, 12 SHOULD-FIX, 4 NIT.**

---

## B-1. BLOCKER: incremental float topology can't match the recompute-on-load that §8 requires, so the heavy-mode save test can't pass

**Location:** §2.2 ("Zone volumes, gaps and the volume profile update incrementally"), research §1.6 ("zone open
volume ± dx³ … gap area ± dx² (also binned by z)"), §8 ("Derived fields are recomputed on load and checked against a
stored digest. A 'heavy mode' test saves, loads and continues, and must match an uninterrupted run bit for bit").

The design keeps derived topology as running float sums, updated by ± dx³ and ± dx² per changed cell, and then
requires that recomputing it from scratch gives the same bits. Float addition doesn't round-trip: +v then −v doesn't
return to the start.

**Measured:** at dx = 0.05, 20,000 random ±dx³ updates to a zone volume end at 0.10825000000000001, against
`n·dx³` = 0.10825000000000003. They aren't bit-equal. So after any fire that removes cells:
- the stored digest of derived fields fails on load, or, if the digest excludes them, the loaded world holds
  different volumes and gap areas from the live one;
- the gap conductances feeding the implicit zone step differ in the last bits, and the continued run diverges from
  the uninterrupted one at the next physics step;
- the same split happens between a live run and a replay that starts from a checkpoint.

There is a second form of the same bug. If gaps live in a dict keyed by zone pair and are inserted as events create
them, the Laplacian is assembled in event-history order live but in scan order after a load. The summation order
differs, so the bits do too, even with exact areas.

**Fix:** make every derived topology quantity a pure function of the cells, by construction:
- Store **integer counts**, not areas or volumes: open cells per zone, open faces per (zone, zone, z-bin), cells per
  region. Convert to m³ or m² (`count × dx³`) only where they're used. Integer ± is exact and order-independent, so
  incremental and from-scratch always agree.
- Compute each event's delta as `f(after) − f(before)` over the changed cells dilated by one. Don't apply it cell by
  cell in sequence: two adjacent changed cells would count their shared face twice.
- Assemble the zone graph in sorted `(i, j)` order every time, never in insertion order.
- Add a property test (Hypothesis): random `set_material` sequences, then check that the incremental state equals a
  full recompute **bit for bit**. Prove the test by switching one counter back to a float.

## B-2. BLOCKER: the world-time latency mode brings back v1's blocking hold without v1's fix (CP BLOCKER 3)

**Location:** §6 ("The host may block in *wall* time so that a thought lands at exactly T + d in *world* time").

As written, this is the literal `results.get(timeout=…)` that `concurrency_performance.md` BLOCKER 3 rejected. That
blocker's failure scenarios all apply to a headless cradle or experiment:
- Ctrl-C or a test teardown waits out the timeout;
- a crash in the thinking lane leaves the simulation lane blocked on a result that will never come (v1 §4.1 says a
  crash stops every lane and joins every thread, but a blocked thread can't be joined);
- a `stop` sits in the inbox unread.

Four further problems are new in v2:
1. **Who blocks, and where.** "The host may block" doesn't say the model call stays in the thinking lane. If an
   implementer makes the cradle simpler by calling the model synchronously inside `Simulation.step`, the call reads
   clocks and entropy (pymaxim: `from uuid import uuid4` in `memory/hippocampus.py`, `from datetime import datetime`
   in `agents/prompt_builder.py`). The tripwire then fires, or the scan exemption grows to let it through.
2. **Dispatch order.** v1 §4.3 orders the queue by priority, then age. In this mode the host waits for the request
   whose T + d comes first, but that request may be queued behind higher-priority ones that are due later. The host
   then waits for the whole queue, which is the inversion CP-4 described, now on the critical path. In this mode the
   queue must dispatch by deadline.
3. **Effective speed.** The mode makes the cradle's speed min(dial, d·tick_us / wall latency of the slowest thought
   in flight). With d = 30 ticks (3 s) and a 2 s model call, a cradle "at 300×" runs at about 1.5× while any thought
   is out. The claim that the mode lets cradles keep their thoughts is right, but the design should say what it costs
   in speed, so cradle budgets (Phase 4) are planned from it.
4. **No guard against a live session.** Nothing stops the mode from being enabled with the network lane up, which
   would freeze every player's world each time an NPC thinks.

**Fix:**
- A wait is a state of the simulation lane, as CP-3's fix said: it waits on the one multiplexed inbox, which carries
  `stop` and lane-crash messages, with a wall timeout. A timeout becomes a logged `thought_worker_failed` input at
  T + d. `stop` ends the wait at once and joins every thread.
- State that the model call is always in the thinking lane, and that `Simulation.step` never calls a model.
- Dispatch by deadline in this mode.
- Refuse the mode at load when any network session can attach.
- The mode and every per-kind d are hashed world config (see S-7).
- Tests, using a stub thinking lane that never answers: `stop` during a wait joins every thread within a bound; a
  thinking-lane crash during a wait fails the host loudly and doesn't hang it.
- Place it in the tiers: apply ticks are deterministic and content is live, so it is tier 3 with timing fixed (DD6's
  H2-live arm).

## S-1. SHOULD-FIX: the live thought source's `max(T + d_min, …)` needs a buffer, a log position and a lower bound, none of which are written

**Location:** §1, §6 ("A result applies at `max(T + d_min, first tick after arrival)`"; "Stub: … releases it … at
exactly T + L").

- **An early arrival must be held.** A result that arrives at tick k < T + d_min has to be held by the `Simulation`
  until T + d_min. The design doesn't say where it is held, whether that buffer is checkpointed state (it must be: a
  save at a tick between k and T + d_min would otherwise lose the result), or what the log records. If the log
  records the result at its arrival tick k, the apply at T + d_min is derived. If it records the result at the apply
  tick, the replay never sees k. Either can work, but only one of them can be the rule, and B2 and the save depend
  on which.
- **d_min = 0 is ill-defined.** In v1 §2.1's order, a tick applies records (1) before agents step (2). A request
  made at tick T therefore can't apply at T. With d_min = 0 the live source gives T + 1 (first tick after arrival),
  while a stub with L = 0 would try to apply at T, which is impossible. That is DD1's off-by-one, still unstated in
  v2. Require d_min ≥ 1 and L ≥ 1 at load, and say that "apply at tick k" means phase (1) of tick k.
- **The stub and live sources have different floors.** The stub applies at T + L; the live source at
  max(T + d_min, …). If L < d_min, a stub thought lands faster than a live one can, which skews H2's latency
  sweep. Apply the same floor to all three sources inside the one apply path: stub at max(T + d_min, T + L), replay
  at the logged tick, which is checked to be ≥ T + d_min.
- **d_min isn't in the hashed config list** of §5. It decides apply ticks, so it is world config (DD4).

**Failure:** a save at tick 105 holds a request made at 100 with d_min = 10, whose result came back at 103. The save
doesn't include the result, because it isn't "in flight" (the worker is done) and isn't applied. After a load, the
NPC never gets its thought, while the uninterrupted run applies it at 110. The heavy-mode test fails, or passes only
because its scenario has no NPCs.

## S-2. SHOULD-FIX: the total order's key is still not written, and released results have no place in it

**Location:** §6 ("sorts them by one total key, then assigns `host_seq`").

DD3 asked for the key to be written down, and for an explicit decision on whether a player intent and a thought in
the same drain are ordered by kind or by arrival. v2 says "one total key" and stops there. There is also a new
case: at tick k the records to apply come from three places:
- this drain's arrivals;
- live results buffered since an earlier tick (S-1);
- stub results due now.

The last two weren't in the inbox at k, so "inbox order" doesn't cover them.

**Fix:** write the key in one place, for example `(kind rank, session actor id, per-session arrival index)` for
client records, and `(kind rank, request id)` for every thought result whatever its source. Released and buffered
results sort by request id with the newly arrived ones. Then add a test in which a buffered live result, a stub
release and a fresh intent all land on one tick.

## S-3. SHOULD-FIX: the ledger's 1e-10 is unachievable as an absolute bound, and the implicit zone step isn't exactly conservative

**Location:** §2.6 ("cells plus zones plus pools change by sources minus outflow, to 1e-10"), §2.2 ("Zone exchange
is one implicit step … conservative"), research §3.3 ("(I + dt·V⁻¹L) m′ = m … conserves total mass to round-off
because L is symmetric").

- **Absolute or relative.** The tile's heat content is about 10¹¹ J (640 m³ of mostly concrete, ρc ≈ 2×10⁶ J/m³K,
  at about 300 K), so one ulp of the total is about 10⁻⁵ J. A 1e-10 J absolute bound can't hold; a relative 1e-10
  can. Say which, per conserved quantity.
- **The research's formula is wrong.** With m extensive (moles) and L the gap-conductance Laplacian (m³/s), the
  flux is L·V⁻¹·m. The research writes V⁻¹·L. **Measured** on 100 zones with one fully open gap (Q = 10⁶):
  - (I + dt·V⁻¹L) changes total mass by −85 of 4.7×10⁴, a 0.18% loss;
  - (I + dt·L·V⁻¹) changes it by −1.6×10⁻¹⁰, which is 3×10⁻¹⁵ relative. That is round-off, but it already fails an
    absolute 1e-10 on moles.

  v2 says only "conservative", so an implementer who follows the research will build the wrong form.
- **"One transfer, antisymmetric" (§2.6) isn't what an LU solve does.** Applying the solve's output directly
  conserves only to the solver's round-off, which grows with the conditioning (a huge gap makes the matrix
  ill-conditioned).

**Fix:** solve for the new concentrations, then turn them into per-gap transfers, F_ij = dt·Q_ij·(c′_i − c′_j), and
apply each with `np.subtract.at` and `np.add.at` (one donor, one receiver). That makes the zone step obey §2.6's
transfer rule. **Measured:** total change 0.0, and the result differs from the direct solve by 3.6×10⁻¹³
relative. Limit each transfer by what the donor holds, as §2.6 requires. Correct the research formula, or cite the
right form in v2.

## S-4. SHOULD-FIX: `ndimage.label` numbering isn't an identity, and its order isn't rig-independent

**Location:** §4 (connectivity, "settling … per cluster"), §7 N1 (`matter` entities: "rubble clusters"), §4 ("a
chunk is a real thing, an entity an NPC can perceive").

`ndimage.label` is deterministic: the same input gives the same labels (sound, see below). But the numbers come from
raster order over (x, y, z). Any change to a cell earlier in raster order renumbers every cluster after it.
- **As identity:** if a rubble cluster's SEM entity name, a client mesh id or a save key comes from its label,
  every relabel reassigns names. N7 notes that NPC memories key on names exactly, so an NPC's "the pile by the door"
  silently becomes another pile. The design has no identity rule for clusters.
- **As an iteration order:** the order of clusters depends on which coarse or fine cell is first in raster order.
  Two clusters whose lowest cells share a coarse cell can swap order between rigs. That matters as soon as order
  changes the result (S-5).
- **Rig-dependent count as an NPC input:** "outcomes are judged by volume, never by fragment count", but N1 makes
  each cluster an entity. Then an NPC perceives about 3 chunks at laptop and about 40 at max, and its choices can
  differ by rig. That's an outcome class reached through the agent rather than the physics.

**Fix:**
- Give a cluster an identity at creation, keyed in metres or by its lowest linear cell index at that moment, and
  persist it. On a relabel, match new labels to old identities by overlap, with a written tie-break (largest
  overlap, then lowest old id). A cluster that splits keeps its id on the larger part, and the smaller gets a new id
  from a counter in the `Simulation`.
- Never iterate in label order. Sort by a key in metres: lowest z, then the centroid's x and y rounded to the
  coarsest rig's grid, then id.
- When `matter` entities are built, expose clusters merged to a metre scale, not raw labels.

## S-5. SHOULD-FIX: settling per cluster needs an order-independent rule and a defined fixed point

**Location:** §4 ("Settling under gravity follows a rule written in metres … Settling is per cluster, on events").

- **Order.** Two clusters that fall onto the same footprint get different piles depending on which settles first:
  the first takes the bottom cells. With label order (S-4), that order is set by raster position and can differ
  between rigs.
- **Fixed point.** Settling moves cells, so it calls `set_material`, which is a topology event, which triggers a
  relabel. A settled pile now touches the floor. If "loose" is recomputed from connectivity to anchored support,
  the pile is no longer loose, which is wrong. If an intact cluster resting on rubble counts as supported, the
  answer depends on whether loose cells are support. The design doesn't say whether `loose` is sticky, or whether
  loose cells carry load. Settling can also free more clusters, so the event loop needs a bound and an order.

**Fix:**
- `loose` is sticky (only a later "fuse" process could clear it). Connectivity only ever turns intact cells loose,
  and support counts intact, anchored cells only (or say otherwise, explicitly).
- Settle every cluster freed in one event together, as one deposit: sum the volume per footprint column in metres,
  then place it. Or sort by S-4's metre key and settle in that order. Either way, the result must not depend on
  label numbers.
- One relabel and settle pass per physics step, iterated to a fixed point with a declared iteration cap. Hitting
  the cap is logged and fails the step loudly in tests.
- A cross-tier test: two crates collapse onto one spot, with pile volume and height in metres compared across
  rigs; and a determinism test with the clusters' raster order permuted (mirror the scene in x).

## S-6. SHOULD-FIX: "O(changed region)" isn't true for connectivity, and per-event relabels would rival the heat solve during a fire

**Location:** §4 ("Cost is O(changed region); a full relabel takes 0.6 / 3.8 / 28.8 ms").

- **Not local.** Whether a cluster is still anchored is a global property: cutting one cell can disconnect a beam
  whose other end is metres away. A local relabel of the changed neighbourhood can't tell whether its pieces join up
  again outside the window. The honest bound is O(the component touched), which can be the whole tile.
- **The figure is for a different labelling.** 28.8 ms is the research's label of *open* cells. The design's
  operation is a label of solids followed by an anchored-support test. **Measured** (24% solid tile, label plus a
  label lookup table against the floor):

  | | laptop | rig | max |
  |---|---|---|---|
  | label, 6-connected | 0.4 ms | 2.9 ms | 21.0 ms |
  | label, 26-connected | 0.7 ms | 4.7 ms | 36.4 ms |
  | anchored test (`unique` on anchor cells, LUT gather) | 0.2 ms | 1.0 ms | 10.4 ms |
  | **total** | 0.6–0.9 ms | 3.9–5.7 ms | **31–47 ms** |

  The research figure is the right order, but it's 1.1–1.6× low at max, and the design doesn't choose a
  connectivity. 26-connectivity makes diagonal corner contact count as support, and corner contact is a
  sub-cell feature that differs between rigs. Use 6-connectivity, and say so.
- **Frequency.** During a fire, cells reach zero mass or come loose in most substeps. If each `set_material` is an
  event, max relabels up to 6 times per physics step: about 190–280 ms, against about 210 ms for the six heat
  substeps (P-1). The cache rebuild that `topology_version` also triggers costs about 100 ms per call at max today
  (`stable_dt` measured at 104 ms), unless it is limited to the affected chunks.

**Fix:** batch topology work. Every process collects its changes for a substep into one `set_material` call, and
the label and settle pass runs once per physics step on a dirty flag. Rebuilding the caches (conductances, ρc,
stability bound) is done per affected chunk. Record the relabel cost per physics step as a B5 row.

## S-7. SHOULD-FIX: the hashed config list is missing the new outcome-deciding values, and library versions

**Location:** §5 ("Everything `Simulation.step` reads is hashed world config: …"), §8 (the header hashes the registry
and the material table).

The following decide outcomes, but aren't named in §5's list:
- `d_min`;
- each request kind's latency-mode d, and whether the mode is on (B-2);
- the connectivity structure (S-6);
- the settle iteration cap (S-5);
- the zone exchange coefficient and the gap aperture rules (unless they're in material table v1);
- `max_age_ticks` relative to d (DD6 point 2).

The bits also depend on numpy, scipy and the BLAS/LAPACK build, as well as the code. Tier 1 is "on one machine", but
committed replay fixtures (B2, B7 as log replays) outlive a `pip install -U`. Today a numpy upgrade would show up
only as an unexplained digest mismatch.

**Fix:** add those values to world config. Record `numpy.__version__`, `scipy.__version__`, the BLAS name
(`np.show_config(mode="dicts")`), Python's version and the platform in the log header (D2's code SHA and dirty flag
too, still missing; DD8). A replay that finds any of them different warns and labels a mismatch "environment
changed" instead of "bug". Committed golden logs are regenerated on an environment bump, as their own commit.

## S-8. SHOULD-FIX: a patch-based tripwire can't cover what §5 lists; use a per-thread profile hook and RNG state checks

**Location:** §5 ("The tripwire is thread-scoped … covers `os.urandom`, `secrets`, `datetime`, the monotonic clocks
and the numpy random globals, and is proven with a planted `time.time()`").

The design doesn't say how the tripwire intercepts calls. If it patches module attributes (the obvious reading of
v1's "makes `time` … raise"), two things defeat it, both measured here:
- **`datetime.datetime.now` can't be patched:** `TypeError: cannot set 'now' attribute of immutable type
  'datetime.datetime'`.
- **Names bound at import escape a patch.** pymaxim 1.3.3 has 18 modules with `from uuid import uuid4` or `from
  datetime import datetime` (for example `memory/hippocampus.py`, `memory/atl.py`, `agents/prompt_builder.py`).
  Patching `uuid.uuid4` doesn't reach hippocampus's own `uuid4`.

A planted `time.time()` in a stub would pass the proof while Maxim's real calls go through unseen.

**Fix (measured to work here):**
- On the simulation thread only, install a `sys.setprofile` hook for the duration of `step`. It sees `c_call`
  events for built-in functions by object identity, however they were imported. In a test it caught an aliased
  `from time import time as now`, `uuid4()` (as `posix.urandom`) and `datetime.datetime.now()`. `sys.setprofile` is
  per-thread, so it is thread-scoped by construction and doesn't touch the thinking or network lanes.
- The profile hook does **not** see numpy's Cython functions: `np.random.random()` wasn't caught. Cover the numpy
  and stdlib global RNGs by comparing `np.random.get_state()` and `random.getstate()` before and after `step`. Any
  draw changes the state, whoever drew it.
- Prove it three ways: a planted aliased `from time import monotonic`, a planted `datetime.now()`, and a planted
  `np.random.random()`, each turning the test red.

## S-9. SHOULD-FIX: float32 caches break the "match the old tests to 1e-12" regression claim

**Location:** §2.3 ("with no transitions, results match the old tests to 1e-12"), research §3.1 ("Caches … f32").

The 91 B/cell budget assumes the k, ρc and face-conductance caches are float32. Conservation survives that
(the flux is antisymmetric), but bit-level agreement with today's f64 path doesn't. **Measured:** 50 substeps on a
40×25×10 grid with T up to 500 °C give a maximum difference of 2.5×10⁻⁶ °C between f32 and f64 conductances. That's
about 10⁶ times the claimed 1e-12.

**Fix:** pick one of these and write it down:
- f64 caches, at +24 B/cell (115 B/cell, about 590 MB at max, still within 2048 MB);
- or f32 caches, with the L1 regression restated as "within 1e-5 °C", re-deriving the old tests' error figures
  instead of claiming they carry over.

The first keeps the regression meaningful.

## S-10. SHOULD-FIX: the memory figures undercount, and the budget check can't see the peak that actually hurts

**Location:** §2.5 ("about 91 B/cell: 7 / 58 / 466 MB"), research §3.1.

The arithmetic is right (91 × 5.12 M = 466 MB). It leaves out:
- v2's own rubble fields (§2.1: a `loose` flag and a packing fraction, +5 B);
- the label array (`ndimage.label` returns int32, +4 B, plus the bool solid mask, +1 B);
- the surface-skin state per exposed fuel face (§3.1), which has no container (S-11);
- f64 caches if S-9 goes that way (+24 B).

That gives about 100 to 125 B/cell: about 510 to 640 MB at max. The proposed budgets (128 / 512 / 2048 MB) still
hold, so this isn't a blocker for the numbers.

The real gap is the check itself. §2.5 checks `memory_budget_mb` "against the registry", but the registry lists
fields, not transients. **Measured:** today's `heat.substep` at max allocates a peak of **412 MB** of temporaries
(tracemalloc), on top of 72 MB of state. That's about 80 B/cell that no registry row declares. The 466 MB figure is
true only once PR 3's preallocation lands, and the load-time check would pass either way.

**Fix:** declare caches, temporaries and label buffers as registry rows of kind `scratch`, so the load-time sum
covers them. Add a B5 measurement: the tracemalloc peak across one physics step at each rig, gated against the
budget. Then a regression that brings back per-substep allocation fails a test.

## S-11. SHOULD-FIX: surface-skin state per face is saved state with no container in the registry or the frame grammar

**Location:** §3.1 ("Surface ignition: a heat-balance skin per exposed fuel face, depth in metres"), §2.5 (registry
grids: "rig cell, fixed metres or zone"), §11 (the protocol freezes at PR 5; the fuel model is PR 7).

A skin temperature per exposed fuel face is state: it has to be saved, digested and replayed. It isn't per cell (a
cell has up to six faces), it isn't per zone, and it's sparse. The registry's grid kinds don't cover it, and the
frame grammar freezes two PRs before it exists. A sparse set is also a determinism hazard of its own: a dict of face
index to state iterates in insertion order, which differs between a live run and a load.

**Fix:** add a `faces` (or sparse-index) container kind to the registry and the grammar before the freeze in PR 5,
stored as sorted index arrays plus value columns. Give its iteration order a rule (sorted by linear face index).
Count its bytes against the budget, as a function of exposed area.

## S-12. SHOULD-FIX: cached region reductions must be one pass and must be published frozen; DD6, DD8 and DD9 aren't folded

**Location:** §2.4 ("Region reductions … cached once per physics step"); the intro's claim that the four
`delta1_*.md` files are "folded here for the first time".

- **Cost.** Caching per region with a mask still costs O(regions × cells). **Measured** at max with 50 regions: one
  region by mask takes 1.8 ms, so 88 ms per physics step for all of them. One `np.bincount(region_id, weights=…)`
  pass takes 22.9 ms for all 50. Say "one bincount pass per reduced field".
- **Concurrency.** If the cache is read anywhere other than the simulation lane (a thinking-lane context builder,
  the network lane's debug view), a dict mutated in place each step is shared mutable state. Publish each step's
  reductions as a new frozen object and swap the reference, as with snapshots.
- **Folds missing.** v2 cites DD1 to DD5, DD7 and DD10, but not:
  - DD6: the H2/H6 prerequisites, `max_age_ticks` against the sweep, H2's 0 s arm (now S-1's d_min ≥ 1);
  - DD8: tick-0 physics, D12's digest-equality test, the dirty flag, the save rule for in-flight thoughts on load;
  - DD9: where the wall/world boundary sits in code.

  DD9 matters more now. B-2's latency-mode wait and S-1's buffer both sit exactly on that boundary, so the design
  should say that only "this tick's arrivals, in inbox order, as validated frozen values" cross into
  `Simulation.step`, and that the buffer and the release decision are inside it.

## N-1. NIT: the log's input list dropped joins, leaves and time decisions, and the context hash needs a canonical form

§6 lists the inputs as "intents, thought results and worker failures". v1 §7 and DD2 also had join, leave and the
time request with its decision. These are presumably only left out of the summary, but this list is the normative
one. "A hash of its context" should name its function and serialization: SHA-256 over a canonical encoding (sorted
keys, floats as their IEEE bytes), never pickle or `hash()`. Otherwise the derived check fails on a dict-order
change or on a hash seed.

## N-2. NIT: tier 2's wording lost "with the stub", and the latency mode has no tier

§5 tier 2 reads "Scripted runs whose inputs carry their ticks are bit-identical at any dial". It should add "with the
stub thought source". Place the latency mode explicitly (B-2: tier 3, with apply ticks deterministic).

## N-3. NIT: the research benchmark scripts aren't committed

`research/states_of_matter/architecture.md` cites `bench.py`, `bench2.py` and `bench3.py` "beside this file". They
aren't there, so the 91 B/cell, relabel and 5.1 ms figures can't be re-run. Commit them (or the harness PR 2 builds
replaces them) before the numbers go into `docs/` or B5.

## N-4. NIT: "what the storage actually lost" is exact only for values of similar magnitude

`float64(old_f32) − float64(new_f32)` is exact when the two exponents differ by at most 29, which covers every
ordinary burn step. A cell whose fuel goes from 1.0 to a denormal in one step loses that guarantee. Clamp to zero
from a declared floor (still a transfer of what was there), or note the bound in the ledger test's docstring.

---

## Performance: what dominates a physics step after v2, and the max profile

Measured per heat substep on the 16×10×4 m tile:

| | laptop | rig | max |
|---|---|---|---|
| today's `heat.substep` (rebuilds conductances, allocates) | 2 ms | 14 ms | 113 ms |
| today's `stable_dt` | 1 ms | 12 ms | 104 ms |
| cached f32 conductances, preallocated `out=` buffers | 0.6 ms | 3.9 ms | 34.6 ms |

Per physics step (0.5 s of world) at max, after PR 3's caching and preallocation:

| Work | Cost |
|---|---|
| 6 heat substeps over the full grid | about 210 ms |
| latent correction (research) | about 30 ms |
| solid-zone surface exchange per substep (not measured; a face pass, about one stencil axis) | about 60 ms (estimate) |
| region reductions, one bincount pass per field | about 23 ms |
| label and settle (S-6), if batched to once per step and only on change | 0 to 47 ms |

- **Quiet room:** about 0.3 s per 0.5 s step, roughly 1.6× real time.
- **During a fire with unbatched relabels:** about 0.55 s, slower than real time.

**Verdict:**
- The max profile gets **better** than v1's 0.75× estimate, but only through PR 3's caching and preallocation (113
  to 35 ms per substep is the root of it), and only if topology work is batched (S-6).
- v2's 12.5% more substeps at max cost less than the caching recovers.
- "Air out of the conduction solve" doesn't by itself cut cost: a full-grid stencil with air masked out costs the
  same. The research's speed-up needs a solve restricted to solid bounding boxes or active chunks, and no PR in §11
  schedules it. The design should state the expected dial per profile with and without that solve, and say which PR
  builds it, or record that it is Phase 2 "Scale".
- At laptop and rig, physics is a few ms per step, and the dial is bounded elsewhere: frames, Python overhead per
  tick, and the thinking lane.

## Checked and found sound

- **`ndimage.label` is deterministic.** It is single-threaded C, two-pass, and gives the same labels for the same
  input. The hazards are only in using its numbers as identity or order (S-4).
- **`np.linalg.solve` is repeatable on this machine** (Accelerate). A 300×300 system with 12 right-hand sides gave
  one distinct result over 200 repeats and under 4 concurrent threads. A 100-zone solve costs microseconds, as
  claimed.
- **numpy reductions don't depend on alignment here.** `sum` of 10⁶ float32 and float64 values placed at 16 and 8
  different byte offsets gave one result each.
- **The zone model's rig-independence** (integrals over cells, fluxes per m²) is sound for determinism and
  cross-tier, once topology is held as integer counts (B-1).
- **"Transfer what the storage lost" (float32 storage, float64 transfers)** closes the ledger to round-off for
  ordinary steps (N-4 for the edge).
- **The stub thought source with no thread** answers DD1: tier 2 rests on nothing that touches wall time.
- **Matching by request id `(tick, actor, n)`**, the input vs derived split with derived decisions asserted on
  replay, and log order as apply order with a replay that never sorts, are sound in principle, given S-1, S-2 and
  N-1.
- **"The simulation can't read server config", as a test**, answers DD4's mechanism.
- **The wall timeout stopping while paused** answers DD10.
- **The arithmetic and the substep ratios hold:**
  - 91 B/cell is 7 / 58 / 466 MB;
  - 8 B/cell is 41 MB per full frame at max;
  - the substep ratios 3 / 1.5 / 1.125 follow from today's 4 / 16 / 64 substeps per 6 s turn against 1 / 2 / 6 per
    0.5 s;
  - the research's 5.1 ms latent correction is consistent with the 35 ms cached substep measured here.
- **The proposed `memory_budget_mb` values (128 / 512 / 2048)** still fit the corrected 100–125 B/cell estimate.
- **Today's AST scan** (`tests/test_determinism.py`) covers this repo's simulation code well. The tripwire's job is
  Maxim's code, which the scan can't reach (S-8).
