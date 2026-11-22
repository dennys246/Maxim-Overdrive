# Determinism and replay lens: phase1/sim-shell (553abca)

Reviewer: independent, read-only. Diff: `git diff origin/main...553abca` (`src/simcore/core/simulation.py`,
`tests/test_simulation.py`, two config lines). I ran every probe against a `git archive` copy of 553abca in my
scratchpad, with `PYTHONPATH` pointed at the copy and the worktree's `.venv`. Nothing in the worktree was edited.
`tests/test_simulation.py`: 25 passed, 0.95 s.

Counts: 1 BLOCKER, 2 SHOULD-FIX, 4 NIT.

## What holds (checked)

- **Physics interval.** `SimConfig.physics_seconds` is `physics_every * tick_us / 1_000_000`: an integer product
  and one correctly rounded division, computed fresh on every physics tick. Nothing accumulates. For T3 it is exactly
  0.5. The phase rule `tick % physics_every == 0` with the clock starting at 1 matches sim_core §3 (tick 0 is
  construction, and physics covers `(T - pe, T]`).
- **Key and ties.** `LogRecord.key` is `(apply_tick, kind_rank, apply_us, actor_id, seq)`, the order of
  boundaries.md §6.2. Strictly increasing keys refuse exact duplicates, so the order is total and no tie is left to
  insertion order. `str` comparison is by code point and does not depend on locale. The shell has no `hash()`, no
  clock and no RNG.
- **Refusing the whole batch.** `_check_batch` runs before any apply. The parametrized test puts a good record ahead
  of the bad one in the tick case and the key-order cases, so a check moved after the apply would change the digest
  (the commit's deletion proof says 4 tests fail). An unknown target comes back as an outcome from the applier
  (`_check_region`), not an exception, so a list batch cannot half-apply on a refusal.
- **Same calls.** `_through_simulation` and `_directly` issue the same applier calls in the same order, followed by
  the same number of `advance(0.5)` calls. The digest covers the cells, regions, sources, `time_s` and `turn`. The
  burn test asserts that crate cells were destroyed, so destruction happens on the compared path.

## BLOCKER

**B1. `tests/test_simulation.py` (the two bit-identity tests and the key-order test): two orderings inside a tick
have no test that can fail.** Both comparisons put records only on tick 1, which is not a physics tick. They also use
a pair that commutes (ignite the crate, strike the wall). I planted three mutations in
`simcore/core/simulation.py::Simulation.step` and ran the shipped suite:

| Plant | Shipped suite |
|---|---|
| A: run physics before applying the tick's records | 25 passed |
| C: silently drop every record that falls on a physics tick | 25 passed |
| B: apply records in reverse key order, then reverse the outcomes back into key order | 25 passed |

Failure scenario: an NPC douse lands on tick 30. Under C it is lost and the fire keeps burning. Under A the fire
burns 0.5 s longer before the douse takes effect. Under B, ignite-then-douse in one tick leaves a fire burning.
Every test stays green under all three. Step 1 (apply) followed by step 6 (physics) is sim_core §3's order within a
tick, and applying in key order is the shell's central contract. The commit's "bit-identity, proven" claim does not
cover records on physics ticks.

Proposed fix, **verified**. I added two tests in the copy:

- Records on tick 1 (ignite), tick 5 (strike on the crate, a physics tick) and tick 30 (douse, then re-ignite, in
  one physics tick), run to tick 60. The test compares the digest with the direct calls: apply that tick's records,
  then `advance` when `t % 5 == 0`.
- Ignite then douse on the crate in one tick (seq 0 at `apply_us` 0, seq 0 at `apply_us` 1), which must leave
  `w.sources` empty.

Both pass on 553abca. Plants A and C each fail the first test. Plant B fails both. A run of that shape could also
replace the 12-step scenario.

## SHOULD-FIX

**S1. `simcore/core/simulation.py::Simulation.step`: a one-shot iterable loses the whole batch without an error.**
`_check_batch` iterates `records`, and then the apply iterates it again. Passed an iterator,
`step(iter([ignite]))` returned `outcomes == ()`, left no source, moved the tick to 2 and raised nothing
(`probe_iter.py`). The annotation says `Sequence`, so mypy catches a typed caller that passes an `Iterator`. A
replay reader that yields its records, or any untyped path, would still lose inputs and give a different
world with no error, which is the worst kind of replay failure. Proposed fix, **verified**: begin `step` with
`tick, records = self._clock.tick, tuple(records)`. With it the probe applies the ignite, and the 27 tests (the
shipped 25 plus my 2) pass. Add a test that passes a generator.

**S2. `simcore/core/simulation.py::LogRecord` / `_check_batch`: two parts of §6.2's record contract are not
checked.**

- (a) `apply_us` has no upper bound. A record with `apply_us = 5_000_000` (50 ticks past its own tick at T3) is
  accepted. §6.2 defines it as "the integer world-microsecond offset within the tick" and an int64. A reader
  that accepts out-of-range offsets now makes the PR 4 log format inherit them.
- (b) `(actor_id, seq)` is the intent id that receipts carry (§6.1). Two records with the same `(host, 0)` and
  different `apply_us` both applied (`probe_iter.py`: `[True, True]`). Neither the batch nor the ticks (seq is never
  held to increase across ticks) enforce it. Ordering stays total, so replay is not broken today. But receipts keyed
  by `(actor, seq)` become ambiguous, and a replayed log with a duplicated id is accepted silently.

Fix (unverified): check `0 <= apply_us < config.tick_us` in `_check_batch`, which has the config, and refuse a
repeated `(actor_id, seq)` within a batch. If the cross-tick check belongs to PR 4's log, say so as a named
deferral.

## NIT

**N1. `simcore/core/heat.py::step` (`grid.time_s += seconds`), reached through the shell: published time is still a
float accumulator, not derived from the tick.** This PR adds `SimConfig`, which accepts non-dyadic intervals. With
`physics_every=3`, 300 ticks give `frames.latest.time_s == 30.00000000000005` against 30.0 from the tick
(`probe_time.py`). That explains why `test_physics_runs_on_every_physics_every_th_tick...` needs `pytest.approx`.
T3's 0.5 s is dyadic, so shipped play is exact up to 2^52 steps. sim_core §2 retires `grid.time_s`, but the
commit's list of what PRs 2 to 4 take on does not name that removal. Name the PR that removes it. Until then,
consider an assertion of exact equality with T3's derived seconds.

**N2. `simcore/core/simulation.py::Simulation.__init__`: the clock and the world's time can disagree.** It wraps
any `World`, including one that has already advanced (`turn > 0`, `time_s > 0`), and the clock still starts at tick
1. The caller also keeps the `World` and can call `advance` or another `Applier` alongside the shell. This is
accepted as the interim seam, but nothing asserts `world.turn == 0` at wrap. A one-line check would make the seam
harmless until PR 2 removes it.

**N3. `Simulation.step`: an exception during the apply or physics phase leaves the tick half done.** If
`World.advance` raises, the tick's records are already applied and the clock has not moved, so a caller that
retries `step` with the same batch applies them twice. Today the only exceptions are programming errors, so this
is a note for PR 3, which moves the window into the step.

**N4. `tests/test_simulation.py::test_from_scene_builds_the_same_world_as_world_from_scene`** compares only
`material`. Comparing `digest()` would cover regions, integrity and temperature at no cost. The shared `digest` also
leaves out frames (sequence and stamp), so if the shell published a frame of its own, or failed to, no test would
see it. Frame cadence is §4's contract. A `frames.latest.sequence` equality in the bit-identity tests would cover it.

## Fold status

Every finding is `open`. The B1 and S1 fixes are verified in a scratch copy. The S2 fix is unverified.
Probe scripts: `/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/74644a49-11ab-4a8e-8ab1-c2ccc9c3fbed/scratchpad/plant/`
(`probe_iter.py`, `probe_time.py`, `tests/test_sim_probe.py`). They are scratch and will not survive a reboot.
