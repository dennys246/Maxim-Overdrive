# Generation harness plan, round 1: Executor (2026-11-22)

The reader's hand-back, condensed and saved by the author; statuses are unset until a reviewer sets them after the
fold. Read at 620b7a0 against:
- `tests/test_sem_bridge.py`, `encoding.snapshot`, `digest.py`, `imagination.place` and `test_cross_tier.py`;
- the import contracts, `test_determinism.py`, `tests/_imports.py` and `scripts/lint_inputs.py`;
- the installed pymaxim's `maxim/embodiment/body.py`.

No tests were run, and no fix was verified.

**Summary:** sound in direction, but not executable as written:
- three existing gates would refuse the harness code it describes;
- one check (U5's `evaluate_failures`) cannot fail on today's bridge;
- several pass criteria have no bar;
- the red gates are named but not specified.

## BLOCKER

- **B1, §3: the repository's own gates refuse the harness in `src/maxim_overdrive/`.**
  - `test_determinism.py` bans `time` and `datetime` in every `src/` package (`NOT_SIMULATION = set()`), but windows,
    timeouts and run timing read the clock.
  - `ALLOWED["maxim_overdrive"] = {}` allows no externals.
  - `lint_inputs.py` refuses file reads outside its two gates, yet resuming JSONL, job files and placements are all
    input reads.

  Fix (unverified): §3 names each exemption H1 adds, each reviewed as a trust-boundary change.
- **B2, U5: "`evaluate_failures()` runs" cannot fail.** The bridge defines no failure modes, so it returns `[]` for
  every spec, with or without the call. The plan's own model, Maxim's smoke test, drives a durability failure to a
  `PainSignal`, which U5 leaves out. `test_sem_bridge.py` has a real `Entity`, `read_all_sensors()` and a strike that
  moves integrity, and nothing about `Embodiment`. Fix (unverified): assert a failure event that a breach drives
  through the bridge's own entity (a mirror and Maxim-type question), or drop `evaluate_failures` and say why.
- **B3, U2 and U3: no bars, and no outcome margin on the class check.**
  - "some turns", "temperatures bounded" and "the class the same" give no count, bound or source.
  - A spec near the breach threshold legitimately flips class between grids, so U3 rejects it.
  - U2's bar is in unmerged PR #51.
  - The cited pattern carries round bars B30 already lists.

  Fix: per physics check, the bar's kind, source and margin, with "measured at H3, before the first battery run"
  where it waits on a measurement.

## SHOULD-FIX

- **S1, the red gates:**
  - no `raises=`;
  - U11's trigger names no step;
  - U3's ledger and U4's `kindle` (unmerged torch-pilot) are waits the plan doesn't list.

  Fix: a row per waiting check, with its trigger, a battery-defined `raises=` type and the precondition.
- **S2, H3's planted specs:**
  - U8 can't be proven by a spec, because `place` is deterministic; it needs a mechanism mutation.
  - U5's planted strike energy is unfixed and material-dependent.

  Fix: say per check whether its proof is a planted spec or a mutation, and derive U5's strike from the spec's own
  material and mass.
- **S3, U8:** `digest.py`'s `canonical` refuses numpy arrays and scalars, and `snapshot` returns arrays; there is no
  grid-state digest. Fix: name what is digested (arrays by bytes, dtype and shape under a new versioned scheme). The
  same applies to H2's scorer digest (builtin floats, NaN refused).
- **S4, U5:** Maxim's `Embodiment.evaluate_failures` computes drive drift from the wall clock (`body.py:258`; also
  the roadmap's OD-I8). Fix: U5's record holds only clock-free fields, with a test that a drifted clock changes
  nothing.
- **S5, H1:** two tests depend on the open Q2. Name the fake inference server, its port 0 and its `ALLOWED_SPAWNS`
  site.
- **S6, H1 and H2:** committed records are persisted formats, so they need a version, refusal of unknown versions, a
  round trip and golden fixtures.
- **S7, H3 and H4:** the battery ships without a caller. No step builds the verdict filter, and H4's consumer is
  undecided. Fix: pick H4's consumer, with a test that a spec failing a needed check never reaches its output.
- **S8, U2:** U2 is `simcore.verify`'s job, which `verify-ships-nowhere` forbids the game to import.
- **S9:** no per-spec performance budget, though U2 runs at 0.05 m over thousands of specs. Fix: measure at H3,
  before H4.

## NIT

- **N1, H2:** "other inputs" should say "other statistics"; more samples do change an interval.
- **N2, §6:** the spike's code isn't on this branch; cite PR #50 at a commit.
- **N3, §3:** the harness's route to a grid through public surfaces isn't shown.
- **N4, U7:** the wire codec (`engine.protocol`) isn't built, so U7 waits on it too.
