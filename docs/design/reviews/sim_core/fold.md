# Fold of round 1 into `sim_core.md` (2026-11-21)

Seven lenses reviewed the note at 3b5937b: 18 BLOCKER, 47 SHOULD-FIX, 33 NIT (reports verbatim beside this file).
Every status below is **open (for the reviewer)**: the delta round's readers set them from the tree (O25).

## The owner's rulings (2026-11-21)

| Ruling | Where it is written |
|---|---|
| Decisions 1–5 of the first draft: replan mid-step; code-primary registry; accuracy floor only if bar 1 fails; one frame per tick (cadence owned by `tile_and_client.md` §4); damage a law | §8, §6, §8, §4, §5 |
| The flow is a standard (first written as "one writer per field") | §5.1, CLAUDE.md "Flow runs one way", B43 |
| R1: rework it as declared, ordered writers, and one resolver per kind of effect, with accumulated fields and a topology owner | §5.1; §2's `Topology`; §6's `writers` column; CLAUDE.md shortened to link §5.1; B43 |
| R2: damage resolves loads every tick in the apply phase; thermal damage on physics ticks | §5.1 (last bullet), §5's tuple `(damage.loads, heat, damage.thermal)` |
| R3: the bridge keeps its marked synchronous path until `phase1/agents` | §13 |

**R2's reading, confirmed by the owner (2026-11-21):** each load resolves right after *its own* record applies, not
after all of the tick's records, so a later record's stage 2 sees the crater (X-S2). That keeps today's
`REGION_GONE` refusal of a second strike on a destroyed region.

## Measured or verified by the author

- **Bounding-box overlap: bit-identical, conditionally.** Physics' `bbox.py` rerun: 0 of 600 mismatches;
  Performance's `bbox_bits.py`: 0 of 300 power fields. Determinism's and Executor's mismatches used random floats.
  `scratchpad/sim/random_sum.py`: random floats differ in 75 of 200 embedded sums, k/64 values in 0 of 200.
  `sphere_overlap`'s 4³ sub-sample makes every weight a multiple of 1/64, so the sums are exact. Folded as §7's
  condition.
- **Digest cost** (`scratchpad/sim/digest_cost.py`, T3 tile): raw SHA-256 of four cell fields 1.68 ms at 0.1 m,
  18.9 ms at 0.05 m; c14n-1 of `temperature` alone 76 ms and 594 ms. Folded as §9's scheme.
- **Unverified, taken from the reviewers:** the 2.6× and 0.46× CPU figures (Perf P3); `n = 1` at every grid
  (Physics, Executor, measured by them); the 29.1 kJ energy effect (Physics).

## Ruled by the owner, 2026-11-21 (each accepted as proposed)

- **Deferral, the memory budget and preallocated temporaries** (Perf P7, X-S9): to B5's memory row, before step 9.
- **Tick 0 runs no physics** (D-S5): `realtime_lanes_coop.md` §2.1's phase rule (`tick % physics_every == 0`) includes
  tick 0, whose interval lies before the world existed. §3 adds `T > 0`, and supersedes realtime §2.1's phase rule on this
  point; realtime is a superseded record and is not edited.
- **5a's logs use action vocabulary v0** (W-S2), so v0 logs exist and 5b restores the v0-log refusal test, instead of
  moving `kindle` into 5a.

## Rows

### Architecture

| Id | Where it went |
|---|---|
| A-B1 | R1: §5.1 declared ordered writers; splitting and contact (`fire_solid.md` §3.2) as declared writers; `radiant_emitters` keyed rows; `Topology` for `imagine`, `set_material`, construction and destruction |
| A-B2 | R2: §5.1, loads resolve on their own tick in the apply phase; no carried state |
| A-B3 | §4 links `tile_and_client.md` §4, the cadence owner. *Corrected in the delta fold:* this row first said `boundaries.md` §4.2 was amended; that edit was reverted in 1270564, and §4.2's copy is the docs-contracts line's to replace with a link |
| A-S1 | §5 `cadence`: per tick, per physics step, per substep |
| A-S2 | §5: a law is anything in the tuple at any cadence; sem §7.1's exchange API becomes an exchange field (sem edited) |
| A-S3 | §5: views of `reads`, handles for `writes` only |
| A-S4 | §2: `Simulation` is pure; the host owns the log writer |
| A-S5 | §2's table: `World` loses `advance`, `_power_field`, publication and construction |
| A-S6 | §5.1: one resolver module per load kind, in a declared tuple inside damage |
| A-S7 | world_v2 §2.5 marked superseded; boundaries §6.4 rows amended; the checklist's old 5a bullets rewritten |
| A-N1 | numba seam kept as contract (kernel interface, Perf P10); the "half a tick" claim replaced by measurements |
| A-N2 | §14's row index moved to the checklist |
| A-N3 | §6 `writers` plural is now consistent; `simcore/core/fields.py` named |
| A-N4 | §2: where `FieldSpec`, `Changes`, `Load`, `Clock`, `SimConfig`, `TickReport`, `WorkCounters` live |

### Bio-faithful

| Id | Where it went |
|---|---|
| BF-5a-B1 | R2 (§5.1) |
| BF-5a-B2 | R1 (§5.1); the exchange field (sem §7.1 edited) |
| BF-5a-S1 | §4: `TickReport` host-side, effects not receipts; §13: the bridge's `ModulatorResult` drops the destroyed volume and absorbed energy |
| BF-5a-S2 | checklist's 5a row list: A3-N3 for "N3", N-S2 added, ids qualified, A3-S5 (final) listed |
| BF-5a-S3 | §5 cadence; §6 producer closure over every law at any cadence; §1 names the three seams |
| BF-5a-S4 | §3: a frame carries its tick; seconds derived |
| BF-5a-N1 | §3: tick 0 is 0 s, OD-I1 cited |
| BF-5a-N2 | §2 cites sem §7.1 |
| BF-5a-N3 | §4: an intent observed at T applies at T + 1 or later |

### Determinism

| Id | Where it went |
|---|---|
| D-B1 | R2 (§5.1) |
| D-B2 | §9: the digest's members, order, byte form and scheme |
| D-S1 | settled: bit-identical while weights are multiples of 1/64 (measured above); §7 |
| D-S2 | §7: geometric overlap keyed on the source's value; checklist's re-ignite test |
| D-S3 | checklist: three overlapping sources and a planted insertion-order loop; §12 narrows the break |
| D-S4 | §8: remaining time from counts |
| D-S5 | §3: tick semantics, physics phase, interval, per-tick source integration; tick 0 proposed above |
| D-S6 | §3, §4: publication from `Simulation.step` only; frames carry the tick |
| D-S7 | §12: breaks listed; the first replay golden committed in 5a |
| D-S8 | §14: `kind_rank` links `tile_and_client.md` §3.1 |
| D-N1 | §5: `reads` and `writes` are sorted tuples |
| D-N2 | §5: the header records the tuple in order; a reordered log is refused |
| D-N3 | §7: string keys sorted by code point |
| D-N4 | §3: `apply_us` only orders |

### Executor

| Id | Where it went |
|---|---|
| X-B1 | R1 (§5.1, `Topology`; `set_material` named) |
| X-B2 | R2 (§5.1); §3 states the physics phase |
| X-B3 | R3 (§13); checklist: the 61 call sites |
| X-S1 | §5: `Changes` carries per-load effects; §6 declares inputs; §5 handles name the window interface |
| X-S2 | §5.1: per-record resolution keeps `REGION_GONE` (author's reading above) |
| X-S3 | §7 cache keys |
| X-S4 | as D-S1 |
| X-S5 | §8 `substep_refine`; §11 bar 3 compares orders directly; §4 takes `limits` |
| X-S6 | §3, §4 frame stamps |
| X-S7 | as D-S8 |
| X-S8 | §8: `TURN_SUBSTEPS` goes; the checklist and the roadmap's floor line now agree |
| X-S9 | checklist: each test says how it fails; counters hold exact values; memory deferral proposed |
| X-N1 | checklist row ids qualified |
| X-N2 | §6 names `simcore/core/fields.py` |
| X-N3 | §12: the split is expected bit-identical, shown by a test |
| X-N4 | §7: measured figures cited (Perf P3) |
| X-N5 | §4: the batch is validated first; §2: `World.turn` goes |

### Performance

| Id | Where it went |
|---|---|
| Perf P1 | §7 cache keys |
| Perf P2 | §9 |
| Perf P3 | §7 (caches are the precondition), §11 bar 7 |
| Perf P4 | §5, §7: `stable_dt` cached per `topology_version` |
| Perf P5 | §10 counters added |
| Perf P6 | §4 links tile §4's cadence (*corrected in the delta fold:* a refusal-only tick publishes); §10 counts windows and copies |
| Perf P7 | proposed deferral above |
| Perf P8 | §2, §10: caches built eagerly |
| Perf P9 | §11 bar 7 names the tile, grid and gate |
| Perf P10 | §5 kernel contract |
| Perf P11 | §10: `cell_substeps` counts the cells the kernel iterates |
| Perf P12 | checklist: B5 rows for per-record work (author adds with B5) |

### Physics

| Id | Where it went |
|---|---|
| P-B1 | §8 `substep_refine`; §11 bar 3 with a planted order-sensitive pair |
| P-B2 | §7 cache keys |
| P-B3 | R2 (§5.1) |
| P-S1 | R2 removes the heat-before-strike order: the crater is resolved at apply, before the tick's physics, as today; the destroyed-cell heat loss stays the existing Known gap |
| P-S2 | §3 per-tick source integration; the checklist's closed form |
| P-S3 | §5: `prepare` reruns after any topology request; the guard runs with `substep_refine` > 1 |
| P-S4 | §11 bar 2b |
| P-N1 | §8: n = 1 on shipped data, the replan reachable only from a constructed table, the coarser substep |
| P-N2 | as D-S4 |
| P-N3 | §7 states the 4³ sub-sample and its condition |
| P-N4 | §7: a cache's key is the values it reads |
| P-N5 | §7: region reductions per `topology_version` |
| P-N6 | §11 bar 2: observables restated in seconds |
| P-N7 | checklist §13: the CLAUDE.md lines that change in 5a's PR |

### Wire integrity

| Id | Where it went |
|---|---|
| W-B1 | R1 (§5.1) |
| W-B2 | R2 (§5.1) |
| W-B3 | R3 (§13) |
| W-S1 | §14 links `tile_and_client.md` §3.1; `phase1/agents` extends it |
| W-S2 | §14: vocabulary v0, proposed above |
| W-S3 | §14: the log's `Format`, reader, gate row, fixtures |
| W-S4 | as A-B3 |
| W-S5 | §4: effects, not receipts |
| W-S6 | as D-B2 |
| W-S7 | §6 carries world_v2's columns, keyed tables and `perceivable`; world_v2 §2.5 links |
| W-S8 | §3 `SimConfig` in code; §14 a reserved run-seed slot; the actor-id allocator is 5b's |
| W-S9 | §14: the header records the scene by digest, so scenes stay repo-only (`fire_solid.md` §5.2 holds) |
| W-S10 | as P-B1 |
| W-N1 | as BF-5a-N2 |
| W-N2 | CLAUDE.md and B43 now link §5.1 instead of restating it |
| W-N3 | as D-N2 |
| W-N4 | `realtime_lanes_coop.md` §2.1's `World.advance` line is superseded by §2 (not edited; the docs-contracts line's) |
| W-N5 | §4: a bad batch raises `ValueError`; §3 links the physics phase |
| W-N6 | checklist: the regeneration command and LF endings; §8 carries the safety factor by link |
