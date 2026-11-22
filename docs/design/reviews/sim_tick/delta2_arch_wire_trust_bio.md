# PR 4a (`phase1/sim-replay`) delta round 2, Architecture, Wire integrity, Trust boundary, Bio-faithful: the delta-1 fold, read from the tree

**Reviewed:** `git diff c721850 8a8fecb` (the round-1 and delta-1 fold), `git show 82447d3` and
`git diff 8a8fecb 82447d3` on the lessons, the roadmap and `fold.md` (the merge's renumbering), every `fold.md` row
in these lenses, and the round-1 and delta-1 reports. The tree is the pushed `82447d3`.

**How it was run:** on my copy at `.../scratchpad/delta2_b/tree`, which matched the worktree (`diff -rq`, caches
aside), with the worktree's venv under `-I` and the copy's `src` and root first on `sys.path`. `simcore.__file__`
resolved into the copy. I ran `test_simulation`, `test_laws`, `test_sem_bridge`, `test_ownership`, `test_lint_gates`,
`test_isolation`, `test_exposure` and `test_deposit`: 323 passed. `test_readme.py` under `MAXIM_OVERDRIVE_ALL_TIERS=1`:
1 passed in 2.0 s. The example prints 0.7918. Ruff check and format on `src scripts tests` are clean. After a local
`git init` in the copy, `scripts/lint_standards.py` reports PASS with 0 findings. Deletion proofs
(`b_mutate.py`) broke each mechanism in place, ran its module and restored the file byte for byte (asserted). The
copy is clean afterwards. pymaxim 1.3.3, the locked version, was read in the venv's site-packages. Scripts are in
`_durable/sim_tick_review/delta2_scripts/` (`b_mutate.py`, `b_two_owners.py`). Not run: the full suite, the 0.05 m
tier, mypy, import-linter, the gate.

## Counts

**New findings: 0 BLOCKER, 3 SHOULD-FIX, 5 NIT.**

**Statuses I set (32 rows in or touching these lenses):** 28 fixed, 1 open, 2 deferred, 1 rejected. Six
rows carry the author's status after the owner's ruling (Exec S2, Arch S6, Det N-2, D-S2 and Arch N4 twice). I
confirm each against the tree, with notes in the table. One status differs from an earlier claim: **Arch S5**. Delta 1 marked it fixed. I set it **open**, with
D2-S1 as the evidence.

## New SHOULD-FIX

### D2-S1. The public built-world constructor contradicts §2 and §4 and still checks nothing about the world it takes
`src/simcore/core/simulation.py::Simulation.__init__`; `docs/design/sim_core.md` §2 ("One constructor,
`Simulation.from_scene`"; "One owner of time") and §4 (the public interface lists `from_scene` only).

The fold resolved Arch S5 by making `Simulation(world, *, config, laws=DEFAULT_LAWS)` a documented public
constructor ("what `from_scene` builds, and what the save's loader will (PR 4b)"). It now builds its own `Physics`
over `world.grid`, so round 1's two-grid case can't happen. That part is fixed. Two problems remain:
- §2 still says there is one constructor, and §4 still lists only `from_scene`. The contract owner says the seam
  doesn't exist, and the code ships it public. That is the false claim round 1's S5 was about. Round 1 asked for one
  of three things: make the seam private, have `from_scene` take construction-time sources, or say that the seam
  remains. The fold did none of the three in the contract.
- The constructor checks nothing about the world, and round 1 named that as well ("not that the grid is still at
  construction"; the old seam refused an advanced world). *Failure scenario (verified,
  `b_two_owners.py`):* build a simulation, light the slab and run 13 ticks. Then
  `Simulation(world_of(sim), config=T3)` gives a second owner of the same world, at tick 1. It publishes frame 0 at
  `tick=0, time_us=0` of a world that has burned for 1.3 s. Both simulations then step. A strike through the second
  one applies to the world that the first one's next physics tick (15) integrates, and no window or clock refuses
  it. That breaks §2's "One owner of time". The only callers today are `from_scene` and `tests/test_exposure.py::_run`.
  PR 4b's loader will be the first real caller, and it needs a tick other than 0, which this signature can't take.

The contract and the code disagree on a public interface, and the shipped constructor lets two owners hold one world
with no error.

### D2-S2. sim_core §13, the contract owner, still says "one tick per call"; the code, the marker and the lesson say "per call that reaches stage 2"
`docs/design/sim_core.md` §13 ("In the interim, world time advances one tick per call, every
`physics_every`-th call runs physics"); also the comment in
`tests/test_sem_bridge.py::test_the_membrane_steps_only_through_its_port_one_tick_per_call` ("world time moves one
tick per call").

Det N-4 was folded at the three sites it named: `bridge.py::StructureModulator.execute`'s marker,
`tests/_sim.py::SteppingPort` and lesson 37. Each now says that a stage-1 or target refusal runs no tick. §13 owns
this rule (the marker cites it), and it was left saying one tick per call. Under the one-owner rule the marker
restates §13, and the two now disagree. *Failure scenario:* PR 4b or `phase1/agents` implements the host's port from
§13 and advances the clock for every `execute`, including stage-1 refusals. Then a malformed agent call costs world
time, and every fifth one runs physics. That differs from the shipped `SteppingPort`. The test asserts the code's
rule (`sim.tick == 2` after a stage-1 refusal), so the code is right and the contract is stale. Fixing it has to cut
words elsewhere in sim_core (D2-S3).

### D2-S3. sim_core.md grew, against the word budget for existing design documents
`docs/design/sim_core.md`. Word counts (`git show <rev>:docs/design/sim_core.md | wc -w`): `bfb12f8` 3,770;
`c721850` 3,770; `8a8fecb` 3,773; `82447d3` 3,773. The fold's amendments to §2, §5.1, §7 and §13 add 3 words net.
CLAUDE.md: "an existing design document doesn't grow ... Cut or move text rather than raise a limit" (B24). The
excess is small. The rule is absolute, though, and D2-S1 and D2-S2 need more text unless something is cut. Its only
guard is a backlog row, and the gate stays green.

## New NIT

- **D2-N1. `Deposit.keep`'s docstring still says "at the current topology version".**
  `src/simcore/core/deposit.py::Deposit.keep`. The code keys on `field_version("material")`, and the class docstring
  and §7 say so. A reader following `keep`'s docstring would key the weights on `topology_version`, which no rollback
  moves past. That is the stale-cache hole PR 3's S1 closed.
- **D2-N2. Lesson 37 calls the cerebellum's update "credit", and it omits the read-back's second consumer.**
  `docs/lessons_maxim_in_games.md` §37; the OD-A16 row in `docs/roadmap.md` ("pymaxim 1.3.3 credits the read-back").
  The lines it cites are right at 1.3.3. Line 584 is `reading = sensor.read()` after `execute`. Line 860 is
  `if self._cerebellum is not None and entity_state:`. Line 885 is `actual=entity_state` in `observe_from_action`.
  But `maxim/embodiment/cerebellum.py`'s module docstring calls the update a Rescorla–Wagner forward model "for
  sensory prediction instead of reward". `observe` learns the post-action sensor values, and NAc's credit at 1.3.3
  comes from interoceptive drives (`_intero_before`, `_measured_credit_total`), not from `entity_state`. So "the
  douse is credited with heating" is really this: the forward model for `extinguish` learns to predict the heated
  reading. The lesson also leaves out that `entity_state` goes into the tool's output for the LLM
  (`tool_bridge.py:908`), which round 1's SF-2 named. "Lesson 23's amendment is the planned design, not 1.3.3's
  behaviour" is half right: at 1.3.3 the read is more than logging (it trains a predictor and reaches the prompt),
  but it is not reward credit. Pointing at OD-A16 is still right, because OD-A16 includes "the cerebellum observing
  at settle". The wording matters because this lesson is the evidence for a Maxim ask. I didn't check whether 1.3.4
  (lesson 36's version) changed these lines, because no venv here has it.
- **D2-N3. The checklist's cadence row lost its precondition.** `docs/plans/checklists.md`, Step 5a: "two strikes on
  one region in one tick, the second destroying nothing". That holds only when the first strike destroyed the
  region. The test it describes
  (`test_a_strike_on_a_region_destroyed_earlier_in_the_tick_applies_and_destroys_nothing`) sets that up. As written,
  the row describes a test that would be false for a large region.
- **D2-N4. Exec S2's tracked row sits in a section marked superseded.** `docs/plans/checklists.md`, "Step 6, fire":
  the section opens "**Superseded (owner, 2026-11-20).** ... The list below is kept as the record of what the tile
  spec asked". The new destruction-based `REGION_GONE` row is appended to that list. A reader working through the
  live rung designs can take it for a historical item. Other live additions in that section carry a bold "Added by"
  lead, and this row doesn't.
- **D2-N5. Unwrapped lines from the fold's edits.** These lines exceed the 120-column wrap the documents otherwise
  keep: sim_core §5.1 and §7 (182, 153 and 126 columns), CLAUDE.md's Layout entry for `geometry.py` (178),
  `architecture.md`'s fierce-fire line (159, with the stray capital "It" delta 1 noted), the roadmap's membrane line
  (128) and `fold.md`'s merge note (167). No lint catches them.

## Merge resolution (82447d3)

Main added lesson 35 (imagination designs behaviour) and lesson 36 (reasoning models' thinking). The branch's lesson
became 37. Checked:
- The roadmap's OD-A16 row cites §37.
- OD-I11's "(lesson 36)" and `spikes/specgen/arms.yaml`'s "lesson 36" point at main's lesson 36, which is right.
- `client_objects.md:393`'s "lesson 34" is main's renderer lesson, which is right.
- No citation of 34 to 37 remains in `src/`, `tests/`, `docs/design/decisions/`, `research/`, `plans/`, the backlog
  or `maxim_upstream/`.
- `fold.md`'s note maps the reviewers' "lesson 35" (delta 1, and the fold rows) and the original "Lesson 34" (round
  1) to this lesson. The verbatim reports keep their old numbers, as they should.
- `8a8fecb`'s message says "Lesson 35". The merge message corrects it, since a signed commit can't change.

No wrong lesson citation is left.

## Status table

Rows outside these four lenses (Det N-1, Exec N1, Exec N2, Exec N3) aren't set here. I did run the deletion proofs
for the Delta-1 rows from other lenses, since they are the fold's changes.

| id | status | evidence |
|---|---|---|
| Det SF-1 / Arch S3 (lazy caches, history-dependent counters) | fixed | Deleting construction's warm turns `test_the_work_counters_hold_their_exact_values_and_repeat_on_a_rerun` red. Deleting the tick-end warm turns `test_a_rolled_back_tick_leaves_no_cache_a_later_state_reuses` red. `from_scene`'s and `work.py`'s "eagerly" are now true. |
| Arch S2 / Exec S1 (eviction at one call site) | fixed | `field_version` is `(rollbacks, count)` (`grid.py:174-180`). Deleting `_rollbacks += 1` turns `test_no_version_a_rolled_back_window_reached_is_reached_again` red. No `on_roll_back` and no `forget` are left in `src/`. |
| Arch S1 (`bound_reads`, `prepare` unenforced) | fixed | `CellStore.reading(reads=)` wraps the bound, `prepare` and `warm`. Unnarrowing the bound turns `[bound]` red. Narrowing only tightens, with writer `None`, so nothing is handed out writable. |
| Exec S2 (`REGION_GONE` flips with spacing; owner ruled (a)) | fixed (author's, after the owner's ruling; confirmed) | `_check_region` is `not regions[region].cells.any()`. Putting the cell rule back turns the test red at 0.2 m. §5.1 says "gone is authored geometry only". The Step 5a rows and the Step 6 row are there (D2-N3, D2-N4). `fire_solid.md:150` is true again. |
| Det SF-2 (lesson wrong for slow effects; ask misfiled) | fixed | Lesson 37 restricts the headline to instant effects, gives round 1's measured 20.0 / 21.29 / 22.15, and cites lines 584, 860 and 885, which match 1.3.3. It points at lesson 6 and OD-A16, and the row cites §37. The wording is D2-N2. |
| Arch S4 (README, spike on the retired API) | fixed | `test_readme.py` runs the README's one Python block in a fresh interpreter: it passes and prints 0.7918. It is marked `slow`, skipped without the tier variable, and its spawn is an `ALLOWED_SPAWNS` row with an explicit `env` and `cwd=tmp_path`. `spikes/slice/README.md` pins `bfb12f8` (owner). |
| Arch S5 (unchecked built-world constructor) | **open** | The two-grid case can't be built any more. But §2 and §4 still say `from_scene` is the one constructor, and the public `__init__` accepts a world another simulation owns, with no error (D2-S1, verified). |
| Arch S6 (§2 `source_exposure`; owner) | fixed (author's, after the owner's ruling; confirmed) | §2 says `Simulation` holds it. `world.py` has no exposure, and `Simulation._exposure` is committed only after the window. |
| Det N-2 / Exec N4 / Arch N5 (§7's keys; owner) | fixed (author's, after the owner's ruling; confirmed) | §7: faces and weights per `material`'s version, bounds per `bound_reads`' versions, `field_version` counting rollbacks. This matches `heat.py:99`, `deposit.py:87,101` and `physics.py:135`. The checklist's cache row is current. The one stale text is `Deposit.keep`'s docstring (D2-N1). |
| Det N-3 (lesson 23's missing test) | fixed | `tests/test_ownership.py:481` exists under the cited name. |
| Det N-4 ("one tick per call") | fixed at its three sites | The marker, `SteppingPort` and lesson 37 say "reaches stage 2". §13 and the bridge test's comment don't (D2-S2). |
| Arch N1 (stale names) | fixed | The `membrane-reads-frames` name is "writes through its port only". `boundaries.md:458` says "the deposit". `on_close` has no hits in `src/`. |
| Arch N2 (`_run` tests `Strike`) | fixed | `edits_cells` is a `ClassVar` on each action, outside `asdict`. Setting a strike's to False turns `test_a_tick_applies_its_records_in_key_order_and_reports_each_outcome` red. A future action without it fails with an `AttributeError`, loudly. |
| Arch N3 (`Physics.work` replaced by `Simulation`) | fixed | `Physics.start_tick()` makes and returns the tally. Making it return the old tally turns `test_a_rolled_back_tick_leaves_no_cache_a_later_state_reuses` red. |
| Arch N4 (§13's "a callable"; roadmap line) | fixed (author's, after the owner's ruling; confirmed) | §13 says "an object its test or host owns", and `bridge.py::Port` has `limits` and `submit`. The roadmap's membrane line says "submits through a submit-and-step port". |
| Arch N6 (fierce-fire units) | fixed | "Older three-rig figures, in 6 s turns". The stray capital "It" is still there (D2-N5). |
| Arch N7 (`place` publishes no frame) | fixed | The `imagination.py:159-162` marker says "the next tick's frame shows the object". |
| Arch N8 (`Simulation.step` has no gate row) | rejected | The reason holds. `LogRecord`'s rows and the batch tests (`_check_batch`'s five `ValueError`s) hold what `step` takes, and `simulation.py` isn't a gate module. `lint_gates` passes. |
| Arch N9 (`field_version` overclaims) | fixed | The docstring says the key "may move when they didn't" and can't recur after a rollback. That is true as built. |
| Arch NIT, fire_solid's `_check_region` row | fixed | True again after the revert. |
| Arch NIT, roadmap and §13 (round-1 fold row) | fixed | As Arch N4 above. |
| Det N-5 (commit before publication) | fixed | The clock advances before `_publish`. Moving it back turns `test_a_publication_that_raises_leaves_the_tick_counted_so_no_retry_applies_it_twice` red. |
| D-S1 (the rebuild after a raised tick is untested) | fixed | Deleting the `except` branch's warm turns `test_a_retried_tick_counts_the_same_work_as_one_that_never_failed[quiet]` red, and the `[a strike]` case passes. The fold's correction is right. |
| D-S2 (end-of-tick rebuild costs 2.1×; owner ruled (2)) | deferred (author's, after the owner's ruling; confirmed) | Reason: no turn-time budget exists yet. Trigger: B5's budget. The Step 5a checklist row names incremental rebuilds, a bit-identity test and the measured 363 against 183 ms. I didn't remeasure. |
| D-S3 (`tests/_imports.py` over 120 columns) | fixed | `ruff check --no-cache src scripts tests` passes. |
| D-N1 (warm's narrowing unguarded) | fixed | Unnarrowing `Physics.warm` turns `test_a_law_state_warming_up_reads_only_what_its_law_declares` red. |
| D-N2 (Det N-5's order untested) | fixed | As Det N-5. |
| D-N3 (a refused `place` moves the next tick's counters) | deferred | Reason: `place` has no `src/` caller and sits under its `TEMPORARY(phase1/sim-clock)` marker. Trigger: PR 4b, when `imagine` joins the tick. The checklist row is under Step 5a. |
| D-N4 (stale text) | fixed | The checklist cache row, `scene.py:48`'s `geometry.MAX_LENGTH_M`, the retry test's comment (no "forgets"), CLAUDE.md's `geometry.py`, §7's credit (split between the new rule and S1's rollback rule) and §7's measured 0.32–0.35× and 0.72–0.98×. |
| D-N6 (`test_readme.py` 5.7 s, not slow) | fixed | `@pytest.mark.slow` plus `skipif(not ALL_TIERS)`, the conftest pattern. |
| D-N (lesson omits the cerebellum condition) | fixed | Lesson 37 cites line 860. The remaining wording issue is D2-N2. |
| Arch N4 (open; delta 1's D-N5) | fixed (author's, after the owner's ruling; confirmed) | As Arch N4 above. |

## Not findings (checked)

- **Trust boundary.** `scripts/lint_gates.py`'s `Port`, `Port.limits` and `Port.submit` rows are unchanged and still
  true: stage 1 and the target check refuse before `submit`, and `SteppingPort` builds one record at the current
  tick. The applier's `sources=` and `resolve=` are unchanged. Removing the douse exemption narrows stage 2 back to
  main's rule, and every refusal path is still there (`_check_region`'s three, `action.check`). `CellStore.reading`
  narrows with writer `None` and can't widen. `Gate.narrow` refuses nesting, so a law's block can't be re-narrowed
  from inside.
- **Architecture.** `Simulation.step`'s `except BaseException` rebuilds and re-raises, so nothing is swallowed. The
  geometry split follows a responsibility. Sizes pass `lint_standards`. The warm at a tick's end runs inside the
  window at the state the commit installs, because no version moves at a tick's commit.
- **Merge.** The only changes the merge makes to the reviewed files are the lessons renumbering, the OD-A16 citation
  and the `fold.md` note. Main's other additions in those files (OD-I11, OD-I12, Phase 6 text) cite their own lessons
  correctly.
