# Wire integrity review: phase1/sim-shell (step 5a PR 1), 553abca

Reviewer: Wire integrity lens. Diff: `git diff origin/main...553abca` (merge base 2e67af2). Read-only.

**First, a precondition.** The branch's base is 2e67af2 (#36). origin/main is now 98e2342: #37 (docs-contracts) has
merged. So the worktree's docs are older than what this PR will land on. I checked the contracts against
**origin/main's** `boundaries.md` §6.2, `sim_core.md` and `tile_and_client.md`. #37 changes no file this diff touches
(`git diff 2e67af2 origin/main` on `pyproject.toml`, `tests/test_tooling_config.py` and `src/` is empty), so a merge
should be clean. But the gate has to run on the merged tree, because #37 adds `scripts/lint_contracts.py`.

## What I checked

| Contract | Against | Result |
|---|---|---|
| `LogRecord.key` order | boundaries §6.2 (main): `(apply_tick, kind_rank, apply_us, actor_id, seq)` | matches |
| `kind_rank` value for v0 world actions | boundaries §6.2 (main): `strike`, `douse` 30, `ignite` (v0) 30, host 40 | 30 matches; derivation is not fail-closed (W-S2) |
| `LogRecord` field types | §6.2 "ordering keys are integers"; tile §2 `actor_id` u32 | `actor_id: str` conflicts (W-S1) |
| `apply_us` range | §6.2 "the integer world-microsecond offset within the tick" | unbounded above (W-S3) |
| `apply_tick` minimum 1 | sim_core §3 (tick 0 is construction); tile §6.2 script | the script's tick-0 `join` conflicts (W-S5) |
| `LogRecord.kind` spelling | sim_core §14, vocabulary v0 `douse` | yields `extinguish` (W-N1) |
| `SimConfig` | tile §6.1 T3: `tick_us` 100,000, physics every 5 | matches; `substep_refine` deferred without a mention (W-N2) |
| `TickReport` | sim_core §4 | subset plus `physics`, `substeps`; the deferrals are named in the docstring. OK |
| `Simulation` interface | sim_core §4 | `from_scene` lacks `laws=` (PR 2, named); `frames` cadence departs without saying so (W-S4) |
| Batch validation | sim_core §4 | whole batch first, ValueError, no change. Verified by the tests and by reading the code |
| Import contracts | `pyproject.toml` skip-layer and membrane lists, `tests/test_tooling_config.py` surface sets | agree; `lint-imports` 9 kept, 0 broken |
| `tests/_imports.py` | the core allowlist | it has no per-module core list. `simulation.py`'s externals (`__future__`, `collections.abc.Sequence`, `dataclasses.dataclass`) are in `_NAMES_CORE`; `test_input_allowlist.py` passes |
| Determinism scan reach | `tests/test_determinism.py` | `NOT_SIMULATION` is empty, so `simulation.py` is scanned |
| Docs | CLAUDE.md layout, boundaries §2.2 (main), checklist 5a | stale (W-S6, W-S7) |
| Tools | `lint_standards.py`, `check_plan.py`, `lint-imports`, `pytest tests/test_simulation.py tests/test_input_allowlist.py` | all PASS on 553abca (110 passed) |

## SHOULD-FIX

**W-S1 `src/simcore/core/simulation.py::LogRecord.actor_id`: a string in an integer ordering key.**
On origin/main, boundaries §6.2 says "Ordering keys are integers (D-N2)", and tile §2's actor table has
`actor_id` as a u32. `LogRecord` takes a non-empty `str`, and `key` sorts on it as text. Failure: once actors are
numbered, actors 9 and 10 written as `"9"` and `"10"` order `"10" < "9"`. A host that orders a batch numerically
then fails `_check_batch`, and a log written in text order disagrees with every other reader of the key. The tests
build this in with `"host"` and `"npc"`. Fix (unverified): make `actor_id` an `int` of at least 0, checked by
`_whole`. If the host's own actor needs a name, give it a reserved integer and record that in the §6.2 owner. The
alternative is to change the contract, which is the owner's call.

**W-S2 `simulation.py::LogRecord.kind_rank`: returns 30 for every kind.** The rank is a constant, not a lookup
by `kind`. It is correct only while `AFFORDANCE_OF` holds `strike`, `ignite` and `extinguish`. Failure: 5b adds
`move` (rank 20 in §6.2), or a host command (40), to the typed actions. `kind_rank` then silently ranks it 30, and
records in a tick apply in an order §6.2 forbids. No test fails, because the test asserts every kind is 30. Fix
(unverified): a closed `kind -> rank` mapping that raises on a kind it doesn't list, so a new kind cannot get a rank
without someone writing one.

**W-S3 `simulation.py::Simulation._check_batch` / `LogRecord.apply_us`: no upper bound.** §6.2 defines `apply_us`
as an offset *within* the tick. Today any non-negative int passes. I verified this: `apply_us=10**12` is accepted,
with key `(1, 30, 1000000000000, 'host', 0)`. Failure: a host computes `apply_us` from the wrong origin (absolute
µs, say) and the record is still accepted. In 5a it only reorders records within the tick. In PR 4 it gets frozen
into a log golden that a fixed reader then refuses. Fix (unverified): `_check_batch` refuses
`apply_us >= config.tick_us`. Also bound `apply_us` and `seq` to int64 / u32 as the format will, so the record
cannot hold a value the log cannot write.

**W-S4 `simulation.py::Simulation.frames`: the frame cadence departs from sim_core §4 without saying so.** Publishing
still happens when `World.writing` closes, not at the end of the tick. I verified this: one tick with ignite plus
strike leaves `frames.latest.sequence == 2`; a refusal-only tick publishes nothing (sequence stays 0); frames carry
no `tick` attribute. sim_core §4 says "a published frame is its tick's" and "a refusal-only tick publishes". The
checklist (§3, §4) schedules both fixes. But the commit names only one interim departure (the `__init__` seam), and
the module docstring says the cadence is "exactly as before" without saying this differs from the contract
`Simulation.frames` claims to follow. Failure: a PR 2 or PR 3 consumer, such as the stepped host or the bridge port,
treats `sequence` as the tick. Fix (unverified): name this as a second interim departure in the docstring and the
commit. Per CLAUDE.md's red-gate rule, add a strict `xfail` (`raises=AssertionError`) for "a refusal-only tick
publishes one frame stamped with its tick", which flips when publication moves.

**W-S5 Contract conflict: tile §6.2's exit script versus sim_core §3 and `LogRecord.apply_tick >= 1`.** The
exit script on origin/main (line 378) puts `join` (host) at tick 0. sim_core §3 makes tick 0 construction, and
`LogRecord` refuses `apply_tick=0`. The two documents can't both hold. This is not this PR's code bug, but this PR
is where the rule became executable. Fix: raise it with the owner, then move the join to tick 1 or allow tick-0
records into construction. One owner decides, and the other document links to it.

**W-S6 `CLAUDE.md` Layout: `simulation.py` is missing.** The `src/simcore/core/` list names every core module,
`world.py`, `applier.py` and `frames.py` included, but not the new one. Fix: add
`simulation.py` (`Simulation`, the integer clock and `step`; `SimConfig`, `LogRecord`, `TickReport`) beside `world.py`.

**W-S7 `docs/design/boundaries.md` §2.2 (origin/main): it says `Simulation` is "Not built".** After the merge,
§2.2's "Built today" list for `engine.sim` reads "`world`, `applier` and `frames`", and `Simulation` appears under
"Not built". Both are false once this PR lands. Fix: move `simulation` into the built list and drop it from
"Not built", in this PR.

## NIT

- **W-N1 `simulation.py::LogRecord.kind`** returns `extinguish`. The v0 vocabulary (sim_core §14) and §6.2's rank
  table call it `douse`. It is harmless while `kind` is not serialized. It becomes a wire-name mismatch in PR 4.
  Record the mapping now, or note it for PR 4.
- **W-N2 `simulation.py::SimConfig`'s docstring** doesn't say that `substep_refine` (sim_core §3, part of `SimConfig`)
  joins in PR 3. A reader comparing it with §3 sees a missing field.
- **W-N3 `simulation.py::WORLD_ACTION_RANK`'s comment** cites "sim_core.md §14". On origin/main, §14 only links to
  boundaries §6.2. Cite the owner alone. The commit message's "(sim_core section 14)" has the same issue.
- **W-N4 `pyproject.toml`'s membrane-reads-frames comment** still lists what the membrane gives up as "the material
  types, the file gates and the world itself". Add the simulation, or point to the test that holds the list.
- **W-N5 `CLAUDE.md`'s "only `World.advance` moves time" and the determinism rule's "Time comes from
  `World.advance`"** are now half true: `Simulation.step` moves the clock, and `World.advance` moves `grid.time_s`.
  The checklist schedules the rewrite (§13, X-S3) for the PR that removes `advance`. That is acceptable if the commit
  or the checklist says which PR does it.

## Not findings

- Skip-layer: `simulation` joining `CORE_PUBLIC_SURFACE` matches boundaries §2.2's rule that adapters and protocol
  import `engine.sim`'s public surface.
- Membrane: excluding `simulation` matches sim_core §13, where the bridge steps through a port its test or host owns.
- `pyproject.toml`'s forbidden list and `tests/test_tooling_config.py`'s sets agree. The tests compare the two sets
  for equality, and they pass.
- The bit-identity tests compare `tests/test_determinism.py::digest` for a wrapped run and a direct run. A real
  `apply` and `advance` sit on both paths.

## Counts

BLOCKER 0, SHOULD-FIX 7 (W-S1 to W-S7), NIT 5. I verified the behaviour behind W-S3 and W-S4 by running it; every
proposed fix is unverified.
