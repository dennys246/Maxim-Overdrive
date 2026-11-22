# Executor review: phase1/sim-shell (553abca), step 5a PR 1, the `Simulation` shell

Diff read: `git diff origin/main...553abca` (simulation.py, test_simulation.py, pyproject.toml, test_tooling_config.py).
Contract read: sim_core.md §1–§4, §12–§14; boundaries.md §6.2's key. Plants ran in a copy at
`.worktrees/_durable/sim_shell_review/plant/` (`plant.py`, `probe.py` beside it); the worktree was not edited.
One side effect to own up to: my `--cov` run in the worktree overwrote its ignored `.coverage` file (23:32).

**Counts: 0 BLOCKER, 3 SHOULD-FIX, 5 NIT.**

## Commit-message claims, checked

| Claim | Result |
|---|---|
| 25 tests, 100% branch coverage of the module | true (ran: 25 passed; 101 stmts, 16 branches, 0 missed) |
| bit-identical digests at 0.2 and 0.1 m, plus a 120-step burn that destroys crate cells | true; the burn test asserts destruction happened |
| deletion: key-order check → 2 fail | true (2) |
| deletion: tick check → 1 | true (1) |
| deletion: cadence shift → 1 | true (1) |
| deletion: interval +1e-6 → 3, the bit-identity tests | partly: planted in `step` I get **4** (the three bit-identity tests plus `test_physics_runs_…`, whose `approx` is tighter than 1e-6 relative). Planted in `SimConfig.physics_seconds` instead, the bit-identity tests stay **green** (see N2) |
| deletion: validate after apply → 4 | true (4) |
| deletion: tick 0 as a step → 10 | true (10) |
| import contracts 9 kept; ruff, mypy | true for the contracts and for ruff/format/mypy on the changed files; the full 89-file mypy, `lint_standards` and `check_plan` I did not run (unverified) |
| tooling, allowlist, ownership, determinism, sem_bridge tests pass | true (186 + 91 passed) |
| "One interim departure" from §2 | understated, see N3 |
| no behaviour change | true, and trivially so on the shipped path: nothing outside tests constructs `Simulation` (N4) |

## SHOULD-FIX

**S1. `tests/test_simulation.py` (no test): the order inside a tick and physics on a tick that carries records are unguarded.**
Every test applies records only at tick 1, never on a physics tick. Two plants survive the whole file (25 passed each):
- physics before apply in `Simulation.step` (swap the `outcomes` line below the `advance` line), against §3's order
  (step 1 apply, step 6 physics);
- `physics = … and not records` (a physics tick that carries a record skips physics).
Failure scenario: an NPC ignites at tick 5 and the fire misses that physics step, or physics runs before the douse; every
test stays green. Fix (verified): a test that steps `physics_every - 1` empty ticks, then one tick carrying `IGNITE`, and
compares its digest with `Applier.apply` then `World.advance(0.5)` on a direct world, asserting `report.physics`. Added in
the copy, it passes on 553abca and fails under both plants.

**S2. `simulation.py::Simulation.step`: an iterator batch is silently dropped and the clock still advances.**
`_check_batch` consumes `records` with `for r in records`, then the `keys` list and the apply loop see nothing.
Probe: `sim.step(r for r in [ignite_record])` returns `outcomes=()`, the world digest is unchanged, and `sim.tick` moves
to 2. The annotation says `Sequence`, so mypy catches typed callers, but the method's promise ("a bad batch raises and
changes nothing") becomes a silent lost input, the worst case for a replay. Fix (verified): `records = tuple(records)`
first in `step`; the probe then applies the record and all 25 tests pass. A test that passes a generator should come
with it.

**S3. `simulation.py::Simulation.__init__`: the interim constructor is an unmarked scheduled band-aid.**
The commit and the docstring call it the strangler seam that PR 2 removes, but it carries no `TEMPORARY(...)` marker and
`docs/roadmap.md` doesn't list `simulation.py`, so `lint_markers` can't show it as open and nothing forces its removal.
Its failure mode is real while it lasts: `Simulation(world, config=…)` over a world that has already advanced starts a
fresh clock at tick 1 (the clock disagrees with `grid.time_s`/`turn`), two `Simulation`s can wrap one world with two
clocks, and the caller keeps the `World` and can drive it beside the shell, which §4 ("the applier is not public") rules
out. Fix (unverified): mark it `TEMPORARY(phase1/sim-clock): …` (the phase the other window markers use) and add the
file to that roadmap bullet, or name it under whichever phase PR 2 lands in.

## NIT

**N1. `simulation.py::LogRecord`: `apply_us` isn't held to the tick.** boundaries.md §6.2 defines it as "the integer
world-microsecond offset within the tick" (int64). `LogRecord(apply_us=10**12)` is accepted and applied. Harmless in 5a
(apply_us only orders), but the range belongs to the record or `_check_batch` (`apply_us < config.tick_us`) before PR 4's
log reader starts depending on it. Likewise `actor_id="a:b"` is accepted; if actor ids follow `checks.identity_key`
(no `:`), the record is where to apply it. Unverified as a contract requirement for PR 1.

**N2. `tests/test_simulation.py::_directly`: the reference path uses `T3.physics_seconds`, the value under test.**
So a wrong `physics_seconds` (plant: `+ 1e-6` in the property) leaves all three bit-identity tests green; only
`test_t3_…`'s exact `0.5` and the `approx` in `test_physics_runs_…` catch it. Guarded overall, but the bit-identity tests
aren't independent of the shell; a literal `0.5` in `_directly` would make them so. Also fix the commit's "3" to the
count the plant actually gives.

**N3. Commit message, "one interim departure":** §4's signature also has `laws=DEFAULT_LAWS`, which `from_scene`
lacks; `Simulation.config` is public surface §4 doesn't list; `TickReport` holds `outcomes`/`physics`/`substeps` instead
of refusals, effects, digest and counters. The commit names each as a later PR's elsewhere, so nothing is hidden, but the
"one departure" sentence should say "departures", or list them together.

**N4. Wire integrity, for the record:** nothing on the shipped path calls `Simulation` (grep: only tests). The "no
behaviour change" claim is true because the shell is capability until PR 2–4 put a caller on it; the bit-identity tests
prove the shell adds nothing to `World`, not that a host's path is unchanged.

**N5. Stale text:** `world.py:179`, `applier.py:79` and the roadmap bullet say "until `Simulation.step` exists" /
"before `Simulation` exists". It exists now; the reasons should read "until `Simulation.step` owns the window (§13)".
`lint_markers` passes, so this is wording only.

## Refused batch changes nothing

Holds for the cases the contract names: the batch is checked before any apply, and the test compares the full digest
(cells, regions, sources, clock), tick and frame sequence before and after. The tick-error case prepends a valid record,
so validating after applying fails it (4 fail, as claimed). The applier's only raise is `TypeError` for a non-action,
which `LogRecord.__post_init__` already excludes. A probe on a later tick (a stale tick-1 record at tick 5, after earlier
work) also left digest, tick and sequence unchanged. The exception is S2's iterator, which isn't refused at all.

## Scope

Nothing outside the stated scope slipped in: `pyproject.toml` adds only `simcore.core.simulation` to the membrane's
forbidden list, `test_tooling_config.py` adds it to the core surface and removes it from the membrane's. No change to
`world.py`, heat, damage, applier, frames or the bridge.
