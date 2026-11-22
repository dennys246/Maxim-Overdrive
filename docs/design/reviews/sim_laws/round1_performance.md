# Performance lens: step 5a PR 2 (law tuple, field registry, writer gate, Topology)

Reviewer: Performance lens, independent. Tree: `phase1/sim-laws` at 3b4c493 against `origin/main` e9cd87f (the merge
base). Both trees were extracted with `git archive` into `_durable/sim_laws_review/perf/{base,head}` and run on the
sim-laws `.venv`; each script asserts which `simcore` it imported. Scripts: `perf/bench.py` (both trees),
`perf/ablate.py` and `perf/micro2.py` (head, with the new indirection monkeypatched out in the same process),
`perf/ops.py`, `perf/summarize.py`. Raw runs: `perf/runs.jsonl`, `perf/scen.jsonl`.

**Caveat on noise.** The machine was shared, at load averages of 6 to 16 on 8 cores. Cross-process wall times for
whole runs vary by ±10 to 20% from one run to the next. I trust only three kinds of number: min-of-N tight loops,
paired in-process ablations with the order alternating, and tracemalloc peaks, which are deterministic. Cross-tree
scenario totals are given for context and are not evidence of a regression.

## Summary

- **Bit-identity holds on the scenario.** The determinism scenario at 0.1 m (crate fire, wall strike, 30 turns, 480
  substeps) gives digest `e9e5712288d60300…` on both trees in every run (26 runs).
- **Per-substep indirection costs about 5 µs, a constant.** Per substep, min-of-30×300 with the gate, the tuple loop,
  the batches and the views ablated: 0.2 m +5.4 µs (3.8%), 0.1 m +4.3 µs (0.7%), 0.05 m within noise (−156 µs). That
  is about 70 µs per 0.1 m turn (16 substeps) of about 11 ms.
- **Nothing new is O(cells) per substep.** The thermal law is now cheaper when nothing breaks: `gone.any()` replaces
  an unconditional `destroy`, which ran a full `material != AIR` pass and a count. Read-only views are O(1)
  `arr.view()`. `topology_version` is an integer compare.
- **New O(cells) work per record, and new O(primitives × cells) memory at construction.** Both are below.
- Findings: **0 BLOCKER, 1 SHOULD-FIX, 3 NIT.**

## Measurements (0.1 m unless stated)

| Quantity | origin/main | 3b4c493 | Note |
|---|---|---|---|
| Scenario digest | e9e57122… | e9e57122… | identical, 26/26 runs |
| Substep, the shipped loop's body (min) | 496.8 µs | 505.5 µs | cross-process; noise-limited |
| Substep, paired ablation within head | — | +4.3 µs (0.7%) | `micro2.py`, min-of-N |
| The indirection alone (3 × `as_writer` + 3 empty `topology.apply` + version compare) | 0.04 µs | 4.2 µs | `bench.py::per_substep` |
| One field read inside the orchestrator window | 0.08 µs | 0.41 µs | `CellStore._channel` makes a view |
| `check_laws` + `_group`, per `run_physics` / `resolve_loads` call | — | 2.3 µs | O(laws) |
| Stability bound (`min` over the group) | 390 µs | 407 µs | noise; damage's laws return inf |
| Turn, paired ablation within head, 0.2 m | — | +66 µs (3.5%) | 180 pairs, median |
| Turn, paired ablation within head, 0.1 m | — | +0.11 to +0.45 ms (0.6–2.4%) | noise-dominated |
| Strike via the applier (window copy included), 18,000 cells | 0.31 ms | 0.37 ms | min of 12 runs |
| Strike resolution only, 9.6×10⁶ cells | 79.0 ms | 75.4 ms | min of 5 per run; noise |
| Construction peak, 400 unnamed boxes, 1.54×10⁶ cells | 61.6 MB | **647.6 MB** | tracemalloc, deterministic |
| Construction peak, 400 named boxes, 1.54×10⁶ cells | 1233.8 MB | **1819.9 MB** | tracemalloc, deterministic |

## Findings

### SHOULD-FIX P1: construction and `imagine` now hold every primitive's full-grid mask at once

`src/simcore/core/scene.py::Scene.build` and `src/simcore/core/imagination.py::_voxelize`.

Both now build the whole request list before `topology.apply` runs. Each `Paint` holds a full-grid boolean mask
(`Box.mask` and `Cylinder.mask` broadcast `grid.mesh()` to the full shape). The base painted one primitive at a time
and dropped each mask. Peak memory therefore grows from O(cells) to O(primitives × cells). Measured: 400 unnamed boxes
at 1.54×10⁶ cells take **61.6 MB → 647.6 MB**, which is +586 MB, exactly 400 × 1.46 MB. With named boxes the peak rises
by the same +586 MB.

**Failure scenario.** A scene at the cap, `scene.MAX_PRIMITIVES = 4096` unnamed primitives, built at the max profile
(about 5×10⁶ cells) needs about **20 GB** of transient masks on top of the grid. On the base it needed about 5 MB.
On a 16 GB machine that is an OOM at load time, from a file the file gate accepted. For `imagine`, the default
`Budget.max_primitives = 32` costs about 160 MB per placement at 5×10⁶ cells. The configurable ceiling is 4096. The
comment at `imagination.py::Budget.max_primitives`, "each primitive costs a full-grid mask to voxelize, one at a
time", is now false.

**Fix.**
- For construction, feed `topology.apply` lazily. Make `requests` a generator, and widen `apply`'s parameter to
  `Iterable[Request]`.
- For `_voxelize`, the occupancy and too-small checks need every mask before the window opens. Either compute each
  mask twice (check and discard, then a lazy generator into `apply`), or go back to checking inside the window and
  rolling back, as the base did. The second keeps one mask live at a time and costs no extra voxelization.

**Status: verified for construction, unverified for `_voxelize`.** I prototyped the construction fix in
`perf/headfix` (`requests = (… for p in self.primitives)`). It restores the base peaks exactly, 61.59 MB unnamed and
1233.84 MB named, and the scenario digest is unchanged (`e9e57122…`). Under mypy the list-to-generator change needs
the `Iterable` signature.

Out of scope, pre-existing: the base already holds one full-grid mask per *named* region, which is 1.2 GB for 400
named boxes here. That is the region table's design, not this diff.

### NIT P2: each load adds about 5 full-grid passes and a full-grid allocation

`src/simcore/core/damage.py::LoadsLaw.step`.

For every load, `step` allocates `slated = np.zeros(grid.shape, bool)`. It also:
- recomputes `grid.solid`, which `_strike_loss` has just computed;
- builds `~slated` and `slated |= gone`;
- counts `gone.sum()`, which `MaterialGrid.destroy` counts again.

Measured as isolated ops (`perf/ops.py`): about 2.6 ms of new work per load at 5×10⁶ cells, and about 7 ms at
9.6×10⁶. That is roughly 6–9% of a strike, whose own full-grid Gaussian (about 75 ms at 9.6×10⁶ cells) dominates. The
whole-strike comparison at 9.6×10⁶ was within noise.

**Failure scenario.** A record with k loads (ballistic and chemical kinds join later) pays k allocations and k × 5
passes at full-grid size. At the max profile with 10 loads, that is about 25 ms per record, inside the window.

**Fix.**
- Allocate `slated` only when `len(inputs.loads) > 1`.
- Return `solid` from `_strike_loss`.
- Take the count from `topology.apply`'s return value rather than from `gone.sum()`.

**Status: unverified.**

### NIT P3: the writer gate adds a fixed ~5 µs per substep in Python

`src/simcore/core/physics.py::run_physics.once`, `src/simcore/core/writers.py::WriterGate.as_writer`,
`src/simcore/core/grid.py::CellStore._channel`.

The cost is three generator-based context managers per substep, plus a Topology `as_writer` per law even when the
batch is empty, plus a view per undeclared field read. That comes to 4.3–5.4 µs per substep: 3.8% at 0.2 m, 0.7% at
0.1 m, and nothing measurable at 0.05 m.

**Failure scenario.** None at today's spacings. It matters only if a future tick runs many tiny substeps, such as the
fixed physics step at small tiles or per-tick laws at 10 Hz on a 0.2 m tile.

**Fix, if B5's budget ever needs it.** Have `topology.apply` return early on an empty `requests`, which saves one
`as_writer` per law per substep. Optionally cache the read-only views per window.

**Status: unverified.** No action needed for PR 2.

### NIT P4: `check_laws` runs on every call

`src/simcore/core/physics.py::_group`.

It revalidates the registry on every `run_physics` call and every `resolve_loads` call (once per record), at 2.3 µs
each. The cost is negligible. It is mentioned only because `DEFAULT_LAWS` is a module constant that could be checked
once at import.

**Failure scenario.** None at today's cost; it scales with the number of laws and calls only.

**Status: unverified.**

## What was checked and found clean

- **No caches.** No cache keys on array identity (`heat`, `grid`, `world` and `frames` have none), so returning a
  fresh view per access defeats nothing.
- **The substep loop.** `stepping.substep_loop` is the old loop verbatim. Power and the stability bound are
  recomputed on the same triggers: the first substep, and after an edit. The trigger moved from "damage destroyed a
  cell" to "`topology_version` moved". These coincide today: a substep's only edit is a destruction, and an empty
  destruction does not bump the version (`_close_batch`).
- **The window.** It still copies every channel once per window (unchanged). `_begin` and `_end` are O(1).
- **Frame publication.** The frame published when a window closes is unchanged.
- **Construction time.** `from_scene` time is unchanged within noise (0.44 → 0.47 ms on the scenario).
- **Bit-identity.** It holds on every run of the scenario.
