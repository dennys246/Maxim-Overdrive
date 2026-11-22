# Delta round 1: Wire integrity and Architecture, step 5a PR 1 (`phase1/sim-shell`, c9c0370)

Reviewer: Wire integrity and Architecture lenses, read-only. Diff `git diff 90dc9b2..c9c0370`. Ran in the worktree:
`lint_standards.py` PASS (0), `check_plan.py` PASS (0), `lint-imports` 9 kept / 0 broken, `pytest -p no:cacheprovider
tests/test_simulation.py tests/test_input_allowlist.py tests/test_tooling_config.py tests/test_ownership.py` 220
passed, 1 xfailed. I also ran two probes against `LogRecord` (shown below).

## Status table (set by this reviewer, from the tree)

| Id | Status | Basis |
|---|---|---|
| W-S1 | fixed | `actor_id` is an int in [0, 2^32); `test_actor_ids_order_as_integers_not_as_text`. Caveat: new SF-1 |
| W-S2 | fixed, verified | `KIND_RANK` is a closed table; `move`, `kindle`, `time`, `join`, `None` all refused `unknown_kind` (probe); the monkeypatch test kills a constant |
| W-S3 | fixed | `_check_batch` refuses `apply_us >= tick_us`; record bounds `apply_us` < 2^63, `seq` < 2^32; batch-refusal test covers it |
| W-S4 | fixed | departure named in `simulation.py`'s docstring; strict xfail, `raises=AssertionError`, precondition raises `RuntimeError`; it xfails today |
| W-S5 | open (for the owner) | contract conflict between tile §6.2's script and sim_core §3; not this fold's to settle |
| W-S6 | fixed | CLAUDE.md layout lists `simulation.py`, and `intents.py` holds the log record |
| W-S7 | fixed | boundaries §2.2 lists `simulation` as built; `Simulation` is gone from "Not built" |
| W-N1 | fixed | `RECORD_KIND_OF[Extinguish] == "douse"` |
| W-N2 | fixed | `SimConfig`'s docstring names `substep_refine` (PR 3) |
| W-N3 | fixed | the rank comment cites boundaries §6.2 alone |
| W-N4 | fixed | the pyproject comment names the simulation |
| W-N5 | deferred | reason: CLAUDE.md's "only `World.advance` moves time" stays true for `grid.time_s` until the laws' window leaves `advance`; trigger: step 5a's PR 2 (checklists §13 ties the rewrite to that move). Accepted |
| A-S1 | fixed, verified | `LogRecord`, `KIND_RANK`, `RECORD_KIND_OF` live in `simcore.core.intents`; `simulation` stays forbidden to the membrane; contracts 9 kept |
| A-S2 | fixed | `kind` is a field, `params` the typed payload, checked to match its kind |
| A-S3 | fixed (marker, roadmap, removal moment); residual deferred | `TEMPORARY(phase1/sim-clock)` on `Simulation.__init__` names PR 4; roadmap Phase 1 lists `simulation.py`. The proposed test-only restriction was not folded and the fold table doesn't say so. I defer it: reason, no caller outside `tests/` constructs `Simulation` and the marker lint keeps the seam visible; trigger, the first non-test caller (the stepped host, PR 2) |
| A-S4 | fixed, with a caveat | `whole_number`, `Refused`/`OUT_OF_RANGE`, `identity_key` on `target`; but the normalized int is discarded (SF-1) |
| A-S5 | fixed | the three window markers and the roadmap bullet name PR 2 / PR 4. The tag `phase1/sim-clock` is right: it is step 5a's branch name (foundations_plan row 5a, O34), not the closed #36 |
| A-N1 | deferred | receipt id joins PR 4's record; trigger PR 4. Accepted |
| A-N2 | fixed | as W-N1 |
| A-N3 | fixed | as W-S4 |
| A-N4 | deferred | a `TickBatch` type belongs with PR 4's log reader; trigger PR 4. Accepted |

Counts: 19 fixed (2 verified by my own probes), 4 deferred (one is A-S3's residual), 1 open for the owner. W-S5 is
not counted as fixed.

## The checks asked for

**`LogRecord` in `simcore.core.intents`.** The move fits the layering. `intents` is layer 5b (`engine.intents`,
boundaries §2.2). It imports only `checks`, `limits` and `refusals`, all below it. `simulation` imports it downward.
The membrane already imports `intents` (`bridge.py:25`), so the §13 submit port can build a record without touching
`simulation`. The import contracts and `test_tooling_config`'s surface-set equality pass. The gate registry rows for
`LogRecord`, `.key` and `.kind_rank` are present.

**KIND_RANK against §6.2.** `{"ignite": 30, "strike": 30, "douse": 30}`. §6.2 ranks `strike` and `douse` at 30, and
`ignite` (vocabulary v0 only) at 30. That is an exact match for the kinds listed, and leaving out `kindle`, `imagine`,
moves, controls and host commands is the fail-closed choice. Unknown or non-string kinds are refused with
`UNKNOWN_KIND` before `kind_rank` can raise a `KeyError`, and a kind or type mismatch is refused with `BAD_SHAPE`.
Either table missing a kind fails closed. Verified.

**The marker.** `TEMPORARY(phase1/sim-clock): <why>; <real fix>; Step 5a's PR 4 removes it` matches `TEMP_TARGET`,
cites a phase that is not done, and its file is listed in the Phase 1 roadmap bullet. `lint_standards` passes.
Well formed.

**Restatement.** `lint_contracts` passes, and the fold adds no copy to any design document. Two code-side echoes are
in NIT-1.

## New findings

**SF-1 (SHOULD-FIX) `src/simcore/core/intents.py::LogRecord.__post_init__` (and `simulation.py::SimConfig.__post_init__`)
check each integer but keep the caller's object.** `_bounded` and `_positive` return `int(value)`, and the result is
thrown away. Probe (verified):
`LogRecord(np.int64(1), np.uint32(0), np.int64(5), np.int16(0), "ignite", "crate", ig).key` gives
`(np.int64(1), 30, np.uint32(0), np.int64(5), np.int16(0))`, and `json.dumps(key)` raises
`TypeError: Object of type int64 is not JSON serializable`.
Failure scenario: PR 4 builds records from decoded frames or a numpy-backed batch. The log writer, the c14n digest
or the golden fixture then fails, or encodes the value differently from a plain int, on a record the type said was
`int`. That is a frozen wire type whose annotations lie, and the exact canonical-form drift §6.2's "typed canonical"
params forbid for the payload. This is also what A-S4's numpy point was about, so A-S4's fix is only partial. Fix
(unverified): store the normalized value with `object.__setattr__(self, name, _bounded(...))` in both
`__post_init__`s, and add a test that a numpy integer comes back as `type(...) is int`.

**NIT-1 `intents.py::KIND_RANK`'s comment and `LogRecord.key`'s docstring echo §6.2.** The comment writes "moves at
20", a rank for a kind the table doesn't hold. The docstring copies the key tuple, which §6.2 says is "stated here and
nowhere else". The `return` expression is the implementation, and a second copy in prose can go stale. Cite §6.2
alone in both.

**NIT-2 `docs/plans/checklists.md` §13 versus the rewritten markers.** §13 has "the three `TEMPORARY(phase1/sim-clock)`
window markers" going together, and the CLAUDE.md lines changing "in the same PR". The markers now split: PR 2
(`world.py`) and PR 4 (`applier.py`, `imagination.py`, the seam). The fold's W-N5 deferral picks PR 2. Failure: PR 2's
author follows §13, deletes all three markers, and leaves the applier opening its own window unmarked. Align §13 with
the markers.

**NIT-3 `docs/design/reviews/sim_shell/fold.md` A-S3 row** says "As Executor S3" and doesn't mention that the
test-only restriction A-S3 proposed was not taken. A declined part of a fix should be stated, so the reviewer doesn't
have to find it in the diff.

**NIT-4 `simulation.py::Simulation._check_batch`** refuses with a bare `ValueError` and no `RefusalCode`. That is fine
while only tests and the host build batches. When PR 4's log reader feeds batches from a file, those become untrusted
input and should carry codes, like the record's own refusals. Note it for PR 4, alongside A-N4.

## Verdict

0 BLOCKER, 1 SHOULD-FIX, 4 NIT. The fold's structural fixes (the record's layer, the closed rank table, integer
keys, the marked seam) hold up from the tree. SF-1 should fold before hand-off, because PR 4 will freeze this
type's encoding.
