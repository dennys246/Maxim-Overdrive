# Step 5a design review, delta round 1: Performance lens

**Under review:** `git diff 3b5937b..99917fb` (`sim_core.md`, the checklist's Step 5a section, `fold.md`), worktree
`sim-clock`. **New findings:** 0 BLOCKER, 4 SHOULD-FIX, 3 NIT. Scripts: `perf_delta1/` beside this file, run with the
worktree's `.venv`.

**A correction of my round-1 numbers comes first.** P3's figures, now quoted in §7, don't reproduce. Rerun today
(`perf_scripts/step_shape.py`, unchanged), today's `advance(6.0)` on the T3 tile at 0.1 m is 112–118 ms, not 180 ms.
On the same model 5a uncached comes out about 4.2× today, not 2.6×, and cached about 0.75×, not 0.46×. A fuller
cached model (`perf_delta1/model.py`) adds the per-step power build from cached overlaps and the digest. It gives
0.67–0.74× at 0.1 m and **1.4–1.6× at 0.2 m**. The conclusion holds: the caches close the uncached slowdown at
0.1 m. The margin is smaller than §7 says, and 0.2 m regresses (S2).

## Status of round-1 findings (set from the tree)

| Id | Status | Reading |
|---|---|---|
| P1 | **fixed** | §7 keys the geometric overlap on `(point_m, radius_m)` and the weights on `(source value, topology_version)`. The checklist §7 has the re-ignite-at-a-new-radius test, which fails under the old key. |
| P2 | **fixed** (the blocker) | §9 now gives the members, their order, the byte form, a versioned scheme and the cadence. A residual contradiction between the scheme and the reuse rule is S1. The B5 cost row I asked for isn't in the tree; that part is folded into S1. |
| P3 | **fixed** | §7 says the caches are the precondition, and bar 7 requires 5a to be no worse than today at 0.1 m with the caches in. The figures it cites are stale (see the correction and N1). |
| P4 | **open** | §7 caches `stable_dt` per `topology_version`, but §5 defines it as "a function of the fields it reads, so it caches like them". The two disagree (S3). |
| P5 | **fixed** | §10 has the `stable_dt` evaluations, the windows and the cells they copied, frames, digest bytes, power-field builds, and rebuilds per cache. |
| P6 | **open** | Nothing says the cell window opens only on ticks that write cells, or copies only the fields it hands out. The checklist §4 counts frames, not windows (S4). |
| P7 | **open** | The deferral has its reason (the owner's ruling) and a trigger ("before step 9"), but it points at "B5's memory row", which doesn't exist. B5 (`standards_backlog.md`) has no temporaries or `memory_budget_mb` row, and the diff doesn't touch it. The checklist still says "owner to confirm" while the fold says the owner ruled. It becomes deferred once the row is written. |
| P8 | **open** (partly fixed) | The caches are built eagerly (§2), but the cache contents (S4) and the digest-reuse state (S1) still depend on the run's history, not only on its state, so the counters can still differ on a replay from a loaded state. |
| P9 | **fixed** | Bar 7 names the T3 tile, 0.1 m and B5's 20% gate. |
| P10 | **fixed** | §5 states the kernel contract. |
| P11 | **fixed** | §10: the cells the kernel iterates, times the substeps. |
| P12 | **open** | The fold says "checklist: B5 rows for per-record work (author adds with B5)". Neither the checklist nor B5 has them. |

## New findings

### SHOULD-FIX S1. `sim_core.md` §9: the scheme as written can't reuse a field's digest, and the history the reuse needs breaks bar 6

**What's wrong.** §9 defines `sha256/raw-1` as one stream: each member's name, dtype, shape and bytes are written in
order. It then says "an unchanged field reuses its last digest". A single SHA-256 stream can't splice in an earlier
digest; it has to be fed every byte again. Taken literally, then, every tick (10 Hz on T3, `tile_and_client.md`
§6.1) rehashes every field. Measured (`perf_delta1/digest.py`): 1.35 ms per tick at 0.1 m and 11.3 ms at 0.05 m. That
is 13.5 and 113 ms per world second, 4–5× the "about 3.4 ms per world second" §9 claims. An implementer who takes the
reuse sentence instead has to invent a two-level scheme, so two readings of one versioned format produce different
goldens.

The reuse state is also history. A replay from a loaded state has no "last digest", so its first tick hashes every
field, while the live run reused them. `digest bytes hashed` (§10) then differs, and bar 6 fails.

**Fix (cost verified, scheme unverified):** make the scheme two-level. Hash each member to its own digest, then hash
the ordered list of `(name, member digest)`. The combine costs about 0.7 µs (measured). Seed the member digests in
`from_scene` and on load, as the caches are. Add the digest's cost as a B5 row.

### SHOULD-FIX S2. `sim_core.md` §7 and §11 bar 7: 5a is slower than today at 0.2 m, and nothing records it

**What's wrong.** At `n = 1` the fixed step runs 12 heat substeps per 6 s, where today's floor runs 4 at 0.2 m. Kernel
work therefore triples whatever the caches do. Measured with the caches modelled in (`perf_delta1/model.py`), 5a costs
1.4–1.6× today's `advance(6.0)` at 0.2 m. Bar 7 names only 0.1 m, so this ships unrecorded. 0.2 m is the coarsest
verification grid and the default suite's. Every 0.2 m test that advances time slows by about that factor, and so does
any B5 baseline taken at 0.2 m.

**Failure scenario.** The 5a PR passes bar 7. The default `pytest` run gets slower, B5's first 0.2 m baseline is set
after the jump, and nobody has a number that says the slowdown was expected.

**Fix (measured, as above):** state the 0.2 m ratio in §7 as an expected cost of the fixed step, and have bar 7
record both grids, gating 0.1 m.

### SHOULD-FIX S3. `sim_core.md` §5 vs §7: what keys `stable_dt`'s cache is defined twice, differently

**What's wrong.** §5 says `stable_dt(state)` is "a function of the fields it reads, so it caches like them". §7 says
"each law's `stable_dt`, per `topology_version`". Heat's `reads` include `temperature`, so under §5 its key changes on
every substep and the cache never hits. That brings back P4's cost: 5.3 ms against a 6.6 ms substep at 0.1 m, about
2.3 ms of it after the conductance cache. Under §7, a law whose bound depends on temperature (temperature-dependent
conductivity, or 6.0a's fuel laws) gets a stale bound after heating, and the step can go unstable with no error.

**Fix (unverified):** each law declares the fields its `stable_dt` reads, a subset of its `reads`. The cache keys on
those fields' versions, which reduces to `topology_version` when they are all topology fields. Add a planted law
whose bound reads `temperature` and must miss the cache.

### SHOULD-FIX S4. `sim_core.md` §7: no rule for what a cache holds, so it grows without bound and replays count differently

**What's wrong.** Keyed by value with no eviction rule, the overlap and weight caches keep:
- an entry for every `(point, radius)` ever ignited;
- an entry for every `(source, topology_version)` pair.

Over a long burn with repeated destruction, the weight cache grows by one bounding box per source per topology bump.
The eager build at load holds only the current sources' entries, so the live run and a replay of the same ticks hold
different caches.

**Failure scenario.** Ignite the crate at 0.3 m, re-ignite it at 0.5 m, checkpoint, then re-ignite at 0.3 m. The live
run hits the stale 0.3 m entry; the replay from the checkpoint misses and rebuilds. `rebuilds` per cache differs, and
bar 6 fails. The same holds for the per-tick cell window (P6): today's `CellStore.writing` copies and mints every
channel even when nothing is written (0.17 ms at 0.1 m, 1.58 ms at 0.05 m, measured). A per-tick `damage.loads` that
takes its handles on a quiet tick therefore adds `cells copied` and defeats S1's reuse.

**Fix (unverified):**
- A cache holds entries only for the current sources at the current `topology_version`. Replacing, removing or
  bumping evicts, so its contents are a function of state and the eager build reproduces them.
- The cell window opens only when a law or request needs a handle, and copies only the fields it hands out.
- The checklist adds a quiet-tick test asserting `windows opened == 0`.

### NIT N1. `sim_core.md` §7: the cited ratios are stale

"About 2.6× … about 0.46×" don't reproduce (see the correction above). Cite the rerun ranges with their script and
date, or better, let bar 7's committed measurement be the number and drop the prose figures.

### NIT N2. `sim_core.md` §9: "76 ms … at 10 ticks a second would be slower than real time" is false as stated

76 ms × 10 = 0.76 s per world second, under real time. The claim is true for c14n-1 of all four fields, or at
0.05 m (594 ms). Restate it that way.

### NIT N3. `sim_core.md` §5 vs §5.1: one window per record or one per apply phase is unstated

§5 places `per_tick` laws "after the records"; §5.1 resolves each `Load` "right after its record applies". The
ordering contradiction belongs to the Executor and Architecture lenses. The cost question is mine: if each record
opens its own window, N strikes in a tick cost N full copies (1.58 ms each at 0.05 m) plus N Gaussians (P12). State
one window per apply phase.

## What else I checked and found sound

- **The law tuple's cost.** `heat` plus `damage.thermal` per substep is today's callback pair, at the same cost
  (thermal 0.7 ms at 0.1 m). `damage.loads` is O(1) on a tick with no loads, provided S4's window rule holds. Resolving
  loads every tick adds a Gaussian (1.3 / 10.5 ms) only on ticks that carry a strike.
- **The replan after a topology request.** Through a topology-keyed bound it recomputes once per destruction batch,
  which is acceptable.

## Fix verification summary

S1's combine cost and S2's ratios are measured (`perf_delta1/digest.py`, `perf_delta1/model.py`, run twice each).
No fix is verified on 5a code, because none exists yet.
