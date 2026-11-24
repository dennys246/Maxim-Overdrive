# Step 5a PR 3: Architecture and Wire integrity review

Reviewer: independent, Architecture and Wire integrity lenses. Tree: `.worktrees/sim-laws`. I read the unstaged diff on
HEAD 3b4c493 (PR 2's staged fold) plus the untracked `deposit.py`, `exposure.py`, `test_deposit.py` and
`test_exposure.py`, and the commit message `_durable/sim-step/pr3_msg.txt`. I edited nothing in the worktree.

**Counts: 0 BLOCKER, 5 SHOULD-FIX, 5 NIT.**

## What I checked

| Check | Result |
|---|---|
| `lint-imports` | 10 kept, 0 broken |
| `scripts/lint_standards.py` | PASS, 0 findings (21 checked, 27 backlog) |
| `scripts/check_plan.py` | PASS |
| ruff check and format, mypy on the new and changed core modules | clean |
| pytest: fields, deposit, exposure, simulation, ownership, tooling_config, input_allowlist, client_fixtures, lint_contracts, lint_standards, frames, determinism, laws | 669 passed, 1 xfailed (the expected strict gate) |
| New modules: one job each, layering | `deposit` imports only `grid`; `exposure` imports only `deposit`; `world` → `deposit`, `simulation` → `exposure`. Downward only. See N1 |
| Import contracts | both modules added to the adapters/protocol and SEM `forbidden` lists |
| `source_exposure` in the registry | `InputSpec("source_exposure", "simulation", "heat")`, and `docs/generated/fields.md` regenerated. See S2 |
| `World._power_field` marker | names PR 4, which matches the roadmap and `simulation.py`'s interim list. The commit message disagrees (S4) |
| Roadmap | the floor's entry is gone, `heat.py` has no marker left, and the `_power_field` sentence was rewritten for PR 4 |
| architecture.md Known gap | updated to 137/104. See N4 |
| CLAUDE.md | the time sentences were updated; the layout and the verification rule are stale (S3) |
| Checklist PR 3 / PR 4 | the PR leaves `checklists.md` unchanged (S5) |
| B36 restatements | no new restatement in a design document. See N3 |
| Band-aids | no new `TEMPORARY`. One cache-key defect (S1) and one identity special case (N5) |

## SHOULD-FIX

**S1. `src/simcore/core/deposit.py::Deposit.power`: the weights cache is keyed on `topology_version`, which a window
rollback rewinds, so after a rollback a different edit gets the same version and a stale cache hit.**
`CellStore._roll_back` (grid.py) restores `_topology_version`. `Deposit` lives outside the window, so it keeps the
entry it computed inside the rolled-back window. Failure scenario: an editing substep at version N+1, then
`power()` (on a refresh, reachable with `substep_refine` > 1 or a replan), then a law raises and the window rolls
back to N. A strike then destroys a *different* cell and the version moves to N+1 again. The next `advance` reuses
the rolled-back topology's weights and puts power into a cell that is now air. **Verified:** my scratch script
(`<scratchpad>/rollback.py`) got `equal: False`, with 75.47 W deposited into the destroyed cell against 0.0 from a
fresh `Deposit`. This breaks §7's "a cache's contents are a function of state" and "each cache equals its uncached
path", and a replay that doesn't raise diverges. It is the first cache keyed on `topology_version`, so it sets the
pattern for the conductance and `stable_dt` caches to come. Proposed fix (unverified): roll the deposit's dicts back
with the window (make it a window participant), or key on a counter that rollback never rewinds. Add a test with
this exact sequence.

**S2. `docs/design/sim_core.md` §6 vs `src/simcore/core/fields.py::INPUTS`: the appender disagrees.** §6 says the
inputs `sources`, `source_exposure` and `loads` each have "its appender (the applier)". The registry says
`simulation`. Separately, the appender is a bare string that nothing checks: it is not in `WRITERS`, has no token,
and no test holds it to a known owner. So "with its writer declared" is nominal only. `"applier"` was already in
the same state before this PR. Failure scenario: a typo (`"simulaton"`) passes every test, and the contract owner
(§6) and the registry describe different flows. Fix: amend §6 (without growing it) or the registry, and add an
appender vocabulary that `test_fields` asserts.

**S3. CLAUDE.md is stale against this PR.**
- (a) The layout lists `stepping.py`, `heat.py`, `damage/` and `reductions.py` but not `deposit.py` or `exposure.py`.
- (b) The verification rule still says the cross-grid scenarios "refine both together until step 5a's fixed physics
  step". PR 3 *is* that step: `test_cross_tier.py`'s new docstring says they now refine space alone. The checklist's
  §13 item names exactly this sentence as one to change.
- (c) Same drift in `docs/design/verify_harness.md` §4 ("until step 5a's fixed physics step, its substep floor
  scales as 1/dx², so these studies refine space and time together") and §6 ("The substep floor in `heat.py`
  stays").

Failure scenario: a reader trusts CLAUDE.md or verify_harness §4 and thinks the scenario studies still measure the
combined discretisation, so they misread bar 2.

**S4. Where heat's `prepare` and `bound_reads` are deferred to is stated three different ways.** The commit message
says "deferred there [§5] until a profile; bar 5 with it". `simulation.py`'s interim list says "(§5; PR 4)", and so
do the `_power_field` marker and the roadmap: "PR 4 hands the sources to heat's prepare". sim_core §5 defers only the
numba kernel. `bound_reads` is not deferred there, and §7 and the checklist's §5 item ("`prepare` reruns after a
topology change … with `substep_refine` > 1") make `prepare` a 5a item. Failure scenario: if the commit message is
right, PR 4 builds no `prepare`, and the `TEMPORARY(phase1/sim-clock)` on `_power_field` has a removal trigger that
never fires. Fix: pick PR 4 or a later trigger, and say the same thing in all three places and in the checklist.

**S5. `docs/plans/checklists.md`: PR 3's deferrals are not recorded with triggers.** The PR leaves the checklist
unchanged. PR 1 set the pattern ("Deferred from PR 1's review … each to the PR that owns it"). PR 3 defers these
only in the commit message and `simulation.py`:
- `source_exposure` in the digest (§9 member 3) and the save (X-B2's save-and-restore mid-interval);
- the exposure being cleared by a physics step that raises;
- moving the scenario tests off the 6 s turn;
- frames carrying their tick;
- bars 4–7;
- `prepare`/`bound_reads` (S4).

Several already exist as step-level items, but none names PR 4 as its trigger. The existing "PR 4: a tick an
exception interrupts…" line doesn't mention the exposure. Failure scenario: PR 4 closes the window item, and the
cleared-exposure half is never tested. Fix: add a "Deferred from PR 3, each to its PR" block.

## NIT

- **N1. `src/simcore/core/deposit.py::Share`, `Exposure`, `standing`:** `source_exposure`'s value types and its
  "standing the whole step" constructor sit in the deposit module, and `exposure.py` imports them from there. The
  dependency direction is fine, but deposit now has two jobs: the geometry and caches, and the exposure's data
  types. Consider moving the types to `exposure.py`, or to a small types module both import.
- **N2. `src/simcore/core/world.py::World.advance`, `simulation.py::Simulation._physics`:** the integer interval
  (`tick_us * physics_every`) is turned into float seconds and back with a round-trip check. Nothing ties
  `Exposure.of_ticks` to `seconds`, so an exposure of 5 ticks passed with a 6 s step mis-scales energy silently.
  Passing `interval_us: int` would push that into the type. `advance` also accepts negative seconds, which moves
  `time_us` backwards (this predates the PR). It is interim, since PR 4 retires `advance`.
- **N3. `src/simcore/core/exposure.py` (module docstring):** it restates §3's energy rule in full rather than
  linking to it. It is code, not a design document, so B36's lint doesn't apply, but a §3 edit would leave this
  copy stale. sim_core §7 also still says "Today `World._power_field` iterates `sources` in insertion order", which
  is no longer true (an existing design document may be edited without growing).
- **N4. `docs/architecture.md` Known gap:** the first clause still says "crate integrity 0.55 at 0.2 m". The commit's
  6 s-turn measurement is 0.539 at refine 1.
- **N5. `src/simcore/core/simulation.py::Simulation.__init__`:** `if laws is not DEFAULT_LAWS: check_laws(laws)` is an
  identity special case. An equal tuple built elsewhere is checked and the default is not. Calling `check_laws`
  unconditionally costs nothing. Also, `pyproject.toml`'s first forbidden list leaves `"simcore.core.heat",` alone
  on its own line (cosmetic).

## Wire integrity notes (no finding)

- The snapshot's `time_s` (`encoding.py`) and the SEM `timestamp` (`bridge.py`) now read exact derived seconds
  (0.3, not 0.30000000000000004). The field's type and the format version are unchanged, and the client-fixture
  tests pass.
- Between physics ticks, time still reads the last physics tick's value, as recorded in the interim list.
- The fixed step's shipped path is exercised: `Simulation._physics` → `World.advance(refine, exposure, laws)` →
  `run_physics`. `test_exposure.py` measures it through `Simulation.step`, which is on the shipped path.
