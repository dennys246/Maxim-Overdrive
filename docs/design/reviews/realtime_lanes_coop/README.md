# Design review: real time, lanes and co-op (round 1, on v0 at 52e64f0)

Seven readers ran in parallel on 2026-11-15, each given the design, the charter and its lens brief, but not the
author's reasoning. Their files here are verbatim. The fold is design v1 (`../../realtime_lanes_coop.md`).

| Lens | File | BLOCKER | SHOULD-FIX | NIT |
|---|---|---|---|---|
| Executor | `executor.md` | 1 | 7 | 4 |
| Architecture | `architecture.md` | 3 | 9 | 4 |
| Wire integrity | `wire_integrity.md` | 3 | 11 | 4 |
| Bio-faithful integration | `bio_faithful.md` | 4 | 8 | 4 |
| Determinism and replay | `determinism.md` | 2 | 7 | 3 |
| Concurrency and performance | `concurrency_performance.md` | 3 | 9 | 3 |
| Trust boundary | `trust_boundary.md` | 6 | 10 | 2 |
| **Total** | | **22** | **61** | **24** |

## Cross-confirmed (found independently by two or more lenses; folded first)

| Finding | Lenses | Where v1 folds it |
|---|---|---|
| The cost table measured one 6 s advance, not the design's loop; the substep rounding gives 12/24/72, not 4/16/64 | X1, CP-1, A4, W-F7, X2 | §2.3 (the rig field becomes an integer per physics step; caching is the root fix; cost re-measured in PR 2) |
| Time split across the host's tick, `World.turn` and `grid.time_s`; the clock in floats | A1, A5, W-F3, W-F8, D7, X3, X-N3 | §2.1 and §2.2 (`Simulation` owns one integer clock) |
| The intent log has no format or version | A2, D2, W-F2 | §7 (intent log v0) |
| Ordering by the client's `seq` isn't total | A6, D3, TB-12, W-F5 | §4.2 (host-assigned `host_seq`) |
| LLM results must pass the same validation as client intents | A7, TB-15 | §4.3 and §7 (one validator) |
| Host role and host departure undefined | A8, TB-4, W-F13 | §5 |
| Agent state written outside the simulation lane during LLM calls | A3, CP-2 | §4.3 and §6 item 16 |
| Maxim agents read the wall clock and OS entropy far beyond the three clocks listed | D1, Bio-1, Bio-2, X5, X6 | §4.4 (three tiers, tripwire), §6 items 10, 11, 15 and the #1361 prerequisite |
| The existing SEM modulator accepts NaN, infinite and negative values, and a short `point_m` raises | TB-1, X7 | §8 PR 1, before any other work |
| Holding the world buys less than v0 claimed, and blocks control | A9, D5, CP-3, Bio-5 | §4.3 (a held state that serves control, a budget, the simulation lane decides failure) and §9 Q1 |
| Stale docs not listed | A11, W-F14, X-N4 | §8 "Supersedes" |
| Axis order, frame and `shape` order unstated | W-F4, X-N2 | §7 (z, y, x; z-up; an asymmetric golden fixture) |

## Every other BLOCKER and SHOULD-FIX

- **Trust boundary:** TB-2 lane crash → §4.1. TB-3 closed schemas → §7. TB-5 token handling, TB-6 handshake
  lifecycle → §5. TB-7 inbound `max_size` small, `compression=None` → §4.1. TB-8 slow readers → §4.1 latest-wins
  slots. TB-9 snapshot amplification → §7. TB-10 cost of valid intents → §7 rate limits and source cap. TB-11 time
  validation → §3.1 and §7. TB-13 two-stage validation → §7. TB-14 disconnect with intents in flight → §5. TB-16
  bind, Origin variants, HTTP 400 → §5. The 41 rejection paths are PR 3's test list (§8).
- **Architecture:** A10 lanes to processes, world-seeded RNG → §4.1 and §6 item 15. A12 save with in-flight state →
  §2.1.
- **Wire integrity:** W-F1 `act_result` and one final reply per message → §7. W-F6 header dtype vocabulary, offset
  base, `kind`, refusal → §7. W-F9 pause separate from scale, unpaced not a value → §3.1. W-F10 epoch type, local
  time zone → §2.2 and §3.2. W-F11 experience clock via turns → §3.3. W-F12 `welcome` contents → §7.
- **Executor:** X4 the experience driver only runs in Maxim's full loop → §3.3 and §6 item 12. X8 live tick
  assignment depends on arrival → §4.2.
- **Bio-faithful:** Bio-3 per-tick substrate step is the hybrid Maxim rejects → §6 items 11, 12 and the owner
  decision. Bio-4 sleep and consolidation → §6 item 14. Bio-6 oscillator per event → §6 item 10. Bio-7 day-length
  entrainment, Bio-8 a day at 1× → §3.4 and §9 Q2. Bio-9 experience clock → §3.3. Bio-10 efference copy,
  per-behaviour suppression → §6 item 11. Bio-11 no synthetic signals → §3.1; the missing food and rest affordances
  are a Phase 4 tile requirement. Bio-12 Exp 64 → §6 (the pre-registration update).
- **Determinism:** D4 actor allocation → §4.2. D6 same-tick thoughts → §4.2. D8 the `server/` exemption → §4.4. D9
  the promise in tiers → §4.4.
- **Concurrency and performance:** CP-4 the thinking queue → §4.3. CP-5 backpressure → §4.1. CP-6 lifecycle, the log
  written synchronously → §4.1. CP-7 the network lane → §4.1. CP-8 snapshot publishing → §7. CP-9 lumpy ticks,
  CP-11 GIL, CP-12 meters → §2.3 and §4.1. CP-10 fast-forward ceiling → §3.4.

## NITs

All taken into v1 except where noted: A13 to A16, W-N1 to W-N4, X-N1 (the max snapshot rate is 51.2 MB/s; v1 no
longer quotes it), D10 to D12, CP's three NITs, TB-17 and TB-18, and the Bio-faithful NITs (10 Hz is fine for DN on
world time; sensors sample cells every tick; Phase 2 visibility must not be shaped as a synthetic camera; DN's
NAME-ONLY tag noted). W-N1's naming (`dx` vs `cell_size_m`) is settled in PR 2 when `grid.time_s` goes.

## Not settled by the fold (owner decisions, design §9)

Q1 holding the world, Q2 play against a 24-hour day, Q3 and Q4 the two Maxim decisions.

A delta round on v1 runs once the owner has answered §9, because the answers change §4.3 and §3.4.
