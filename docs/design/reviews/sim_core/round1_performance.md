# Step 5a design review: Performance lens

**Under review:** `docs/design/sim_core.md` and the Step 5a checklist, branch `phase1/sim-clock` at 3b5937b.
**Counts:** 2 BLOCKER, 6 SHOULD-FIX, 4 NIT.

**Measurements:** today's code (no 5a code exists), worktree `.venv`, best of 3–7; scripts in `perf_scripts/`. T3 tile:
12 × 4 × 4.8 m, concrete floor and wall, 0.8 m wood crate, 60 kW r = 0.3 m fire; 230 k cells at 0.1 m, 1.84 M at
0.05 m. CP-1 tile: 16 × 10 × 4 m, 640 k cells at 0.1 m.

| Per call, T3 tile | 0.1 m | 0.05 m |
|---|---|---|
| `heat.substep` (no power build) | 6.1 ms | ~60–100 ms |
| `heat.stable_dt` | 5.2 ms (2.9 of it `_face_conductances`) | 55 ms |
| `sphere_overlap`, whole grid | 27 ms | 255 ms |
| `sphere_overlap`, padded bounding box | 0.54 ms | 0.75 ms |
| `thermal_degrade` (+ window) | 0.7 ms | 6.1 ms |
| empty cell window (4 copies, freeze, publish) | 0.22 ms | 1.84 ms |
| SHA-256 of the 4 cell fields' bytes | 1.9 ms (3.2 MB) | 13 ms (25.8 MB) |
| c14n-1 `canonical` of `temperature` alone | 232 ms | 866 ms |
| `stable_dt` value | 52.6 s | 13.1 s |

---

## BLOCKER P1. The overlap cache's key, `(source id, topology_version)`, returns a stale overlap after a re-ignite

**Where:** `sim_core.md` §7, the cache bullet. The checklist §7 row tests the cache only against the uncached path.

**Failure scenario.** `Applier._ignite` writes `sources[f"fire:{region}"] = source`, so a second `ignite` on the crate
replaces the source under the same id. A re-ignite at a larger radius changes no material and no owner, so
`topology_version` doesn't move. The key `("fire:crate", v)` hits, and the new 0.5 m fire deposits through the old
0.3 m overlap. The heat goes to the wrong cells, at a different power density, with no error.
`perf_scripts/reignite.py` shows this: the same id, radius 0.3 → 0.5, the materials unchanged and the overlaps different.
An uncached-equality test misses it unless it re-ignites.

It also over-invalidates: `sphere_overlap` is pure geometry (point, radius, `dx`, shape), so keying it on
`topology_version` recomputes every overlap on any destruction anywhere, and `overlap_recomputes` counts churn.

**Fix (unverified):** key the geometric overlap on the source's value `(point_m, radius_m)` with the grid geometry.
Key only the solid weighting and normalisation (`frac * solid`, and the sum) on `topology_version`. The checklist then
gets a re-ignite-at-a-new-radius case.

## BLOCKER P2. The "per-tick digest" in `TickReport` is a contract with no content, scheme or cadence, and the plausible readings range from cheap to slower than real time

**Where:** §4 (`TickReport` "holds … the per-tick digest"), §6 ("whether it is digested"), §10 bar 4, §11.

**Failure scenario.** §6 implies the registry's digested fields go into it. The core's only digest scheme is
`digest.py`'s c14n-1 JSON. Implemented that way, the temperature field alone costs 232 ms per tick at 0.1 m. That is
2.3 s of CPU per world second at 10 Hz, 2.3× slower than real time, before any physics runs.

Even raw SHA-256 over the cell fields costs 1.9 ms per tick, or 19 ms per world second. 5a's physics with its caches
costs about 14 ms per world second on the same tile (P3), so the digest would cost more than the physics it guards.
At 0.05 m it is 13 ms per tick, 130 ms per world second.

On 4 of every 5 ticks no cell changes, so it rehashes unchanged arrays. `boundaries.md` §6.2 means derived values
(receipts, refusals), which are cheap; bar 4 reads as the world. The note doesn't say which.

**Fix (unverified):**
- State what the per-tick digest covers: the derived values every tick, and the cells only on ticks whose window wrote
  them. The owners are immutable at rest, so an unchanged owner can reuse its last digest.
- Give it a versioned raw-bytes scheme, not c14n-1: registry order, dtype, shape, C order, little-endian.
- Add its cost as a B5 row.

## SHOULD-FIX P3. The caches are 5a's precondition, not an optimisation, and §7's "about half a burning tick's CPU" doesn't match the code

**Where:** §7 (the measured claim), §8, §10 bar 7, §11.

**The measurements.** At 0.1 m and 0.05 m `stable_dt` is far above P = 0.5 s (52.6 s and 13.1 s), so `n = 1` on every
physics step at every shipped grid. The fixed step gives 12 heat substeps per 6 s of world time, against today's
4 / 16 / 64. That is 3×, 0.75× and 0.19× the kernel work at 0.2 / 0.1 / 0.05 m. The per-step overhead now runs 12 times
per 6 s instead of once (`perf_scripts/step_shape.py`):

| Per 6 s of world time | T3 0.1 m | T3 0.2 m | CP-1 0.1 m |
|---|---|---|---|
| today, `advance(6.0)` | 180 ms | 9 ms | 521 ms |
| 5a, 12 × 0.5 s, nothing cached | ~474 ms (2.6×) | ~103 ms (11×) | ~1,614 ms (3.1×) |
| 5a, power field and stable bound cached | ~82 ms (0.46×) | ~22 ms | ~282 ms |

The whole-grid overlap is about 70% of each uncached 0.5 s physics step. In today's code it is 15% of an idle-burning
6 s turn. Over a 40-turn, 500 kW burn that destroys cells (`perf_scripts/burn.py`), it is 20% of CPU at 0.1 m and 46%
at 0.2 m. "About half a burning tick" is therefore not what today's code shows at the truth grid. The note doesn't
cite a source for it. The figure comes from CP-1 (`reviews/realtime_lanes_coop/concurrency_performance.md`: 453 ms
at 0.05 m on the 16 × 10 × 4 m tile), not from "the vertical slice".

The mechanism claim holds: 64 whole-grid passes, once per `advance` and again after each destroying substep.

**Failure scenario.** §11 treats the caches only as bit-identity holders. If the clock lands before them, or the
bound cache is dropped (P4), the 0.1 m grid runs 2.6–3.1× slower than today, 11× at 0.2 m.

**Fix (verified as arithmetic from the measured components, not run on 5a code):**
- Replace the claim with the measured numbers and cite CP-1.
- Make bar 7 require that 5a's per-world-second CPU on the T3 tile at 0.1 m is no worse than today's `advance(6.0)`,
  with both caches in.

## SHOULD-FIX P4. The stability bound isn't cached, and at `n = 1` it costs almost as much as the physics

**Where:** §5 (`stable_dt(state)`), §7 (the cache list), §8.

**The measurements.** `stable_dt` costs 5.2 ms against a 6.1 ms substep at 0.1 m. The conductance cache removes about
2.9 ms of it, which leaves about 2.3 ms: the per-cell sum, the divide and the min. That is still about 38% of the step
it plans. The bound depends only on the material array, the table and `dx`, so it is a pure function of
`topology_version`.

§8's replan re-evaluates it after every destroying substep, yet with today's table it can't fire (air, the most
diffusive, bounds at 13–53 s against P = 0.5 s): 55 ms of pure overhead each at 0.05 m.

**Failure scenario.** Every physics step pays O(cells) for a value that changes only on destruction.

**Fix (unverified):** make each law's `stable_dt` cacheable by `topology_version` (the contract says what it may
depend on), and add the stable bound to §7's cache list.

## SHOULD-FIX P5. The counters can't see the regression class CP-1 found

**Where:** §9.

**What's missing.** The counters are `physics_steps`, `substeps`, `cell_substeps`, `overlap_recomputes` and
`cache_rebuilds`. Every cost in P2–P4 and P6 falls outside them:
- `stable_dt` evaluations;
- cell windows opened, and the cells they copied;
- frames published;
- digest bytes;
- power-field builds.

`sem_stimuli.md` §8 already lists frames and bytes. `cache_rebuilds` lumps three caches together.

**Failure scenario.** A change that opens a cell window every tick, or loses the bound cache, leaves every counter
identical. B5's gate, which reads them, stays green while CPU per world second doubles.

**Fix (unverified):** add those counters, and count rebuilds per cache.

## SHOULD-FIX P6. A cell window every tick copies the grid even when nothing changes

**Where:** §4 ("publishes one frame"), §3 (steps 1, 6, 8), §12.

**What happens.** `CellStore.writing` copies every channel at open and freezes it at close. That costs 0.22 ms at
0.1 m and 1.84 ms at 0.05 m for an empty window, or 18 ms per world second at 10 Hz at 0.05 m. Each window also mints
new owner arrays. That defeats identity-based digest reuse (P2), and a frame an agent pins on a no-op tick holds its own
full copy.

The note doesn't say whether `step` opens the cell window on a tick with no physics and no cell-writing record. §5.1
also leaves open whether a strike on tick 3 resolves at once, with damage running off a physics tick, or waits for
tick 5. That decides which ticks need a window.

**Fix (unverified):**
- Open the cell window only on ticks that write cells.
- Hold the sources-only window otherwise. It costs 0.005 ms and copies nothing.
- Publish a no-op tick's frame over the unchanged owners.

(Publishing once per tick, not per application, is itself a saving.)

## SHOULD-FIX P7. The memory half of world_v2's row 3 scope is dropped without a word

**Where:** §1 ("Builds"), §10 bar 7. Compare `world_v2.md` row 3: "preallocated temporaries, `memory_budget_mb`".

**The measurement.** One window plus a substep peaks at 6.7× the cell state: 21.6 MB at 0.1 m and 174 MB at 0.05 m
(`perf_scripts/alloc.py`). CP-1 measured 412 MB at 5.12 M cells.

**Failure scenario.** §6 lists the memory budget as a registry reader, but nothing sets it, and the temporaries stay
per-call. The 0.05 m verification run and agent-pinned frames (B5's owed row) share an unbudgeted peak.

**Fix:** either build the temporaries and the budget, or record their deferral with its trigger.

## SHOULD-FIX P8. The cache counters differ between a run and a replay from a checkpoint

**Where:** §9 ("identical on a replay"), §10 bar 6.

**What happens.** `overlap_recomputes` and `cache_rebuilds` depend on how warm the cache is, not only on the state
plus the log. A replay from step 9's checkpoint starts cold, so on its first physics step it counts rebuilds the live
run didn't.

**Failure scenario.** Bar 6 fails on every checkpointed replay.

**Fix (unverified):** either build the caches eagerly in `from_scene` and on load, so the first tick is the same
whichever way the run began, or scope bar 6 to replays from tick 0 and exclude the cache counters from the digest.

---

## NIT P9. Bar 7 names no scene, grid or gate

**Where:** §10 bar 7.

"CPU per physics step and memory, measured" names no tile, no grid and no threshold. B5 asks for a committed baseline
and a 20% regression gate. Fix: name the T3 tile at 0.1 m (and 0.05 m for the verification run) and B5's 20% rule.

## NIT P10. The kernel's side of the numba seam is unstated

**Where:** §5, the `prepare` and kernel bullet.

Bar 5 compares numpy with numpy, so it can't tell whether the seam suits numba. Fix: state the kernel contract (arrays
and scalars in, preallocated outputs, order-sensitive reductions in `prepare`), or a numba kernel can silently break
bar 5 or §11's goldens.

**Supporting measurement:** the bounding-box restriction is bit-identical. The normalising sums are exact, since the
weights are multiples of 1/64. Over 300 random sources, a one-cell-padded box matched the full-grid power field bit for
bit (`perf_scripts/bbox_bits.py`, verified). Without the padding I didn't test it, so the checklist should require
the padding or the same index arithmetic.

## NIT P11. `cell_substeps` has no definition for a sparse solve

**Where:** §9.

"Cells × substeps" means the grid's cell count today. Once air leaves the solve or the solve runs over active boxes
(`world_v2.md`), the counter stops measuring work unless it is defined as the cells the kernel iterates.

## NIT P12. Per-record O(cells) work is unrecorded

**Where:** §5.1, §7.

A strike's whole-grid Gaussian costs 1.3 / 10.5 ms per load at 0.1 / 0.05 m; a `region_id` mask per check 0.01–0.07 ms
(`perf_scripts/per_record.py`). Acceptable, but they belong in B5's rows.

---

## Fold status

All `open`. Failure scenarios verified for P1 (reignite script) and P2–P4, P6, P7 (measurements); no fix verified on 5a
code.
