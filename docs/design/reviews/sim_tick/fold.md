# Step 5a PR 4a (`phase1/sim-replay`): round 1 fold

Round 1 ran three readers, eight lenses, on 336eee8 against bfb12f8: `round1_exec_phys_perf.md` (Executor, Physics
and resolution, Performance), `round1_arch_wire_trust.md` (Architecture, Wire integrity, Trust boundary) and
`round1_det_bio.md` (Determinism and replay, Bio-faithful integration), each copied verbatim. 0 BLOCKER,
11 SHOULD-FIX (the eager caches reported twice), 18 NIT. This table is the author's account. **Every status is "open
(for the reviewer)"** until a reviewer reads it from the tree (O25). Items marked **for the owner** change a contract
or need a design call, and the owner rules on each.

**Correction first.** 336eee8's message says "the interim Simulation(world) seam is gone" (false: the constructor for a
built world stayed public and checked nothing, Arch S5) and "Lesson 34" (it is 37: 35 after the first merge with main,
37 after main added its own lessons 35 and 36; "lesson 35" in the rows below and in the reviewers' reports is this
lesson). `from_scene`'s docstring and `work.py` said the caches were built eagerly (false: they were lazy, Det SF-1,
Arch S3).

## How the main fix works (Det SF-1, Arch S2, S3, Exec S1)

- **Cache contents follow the state.** Each law's state has `warm(grid, sources)`, and `Physics.warm` runs it for
  every law and evaluates every per-substep bound. `Simulation` calls it at construction and after a rolled-back
  tick, at rest, counted in no tick, and at the end of every tick that opened a window, counted in that tick. The
  deposit's `keep` holds exactly the entries the live and closed source values need. A retried tick then counts what
  an uninterrupted run counts, and PR 4b's replay from a loaded state can too.
- **Eviction is the type's.** `CellStore.field_version` is now `(rollbacks, count)`: a rollback restores the count
  but never the rollbacks, so no key a rolled-back window reached is reached again, whoever owns the cache. That made
  the rollback listener and `forget` redundant (deleting them changed no result), so both are gone rather than kept
  as a mechanism no test could fail. Every cache (the faces, the bounds, the deposit's weights) keys on these
  versions.
- **Proofs.** Deleting the rollback count turns three tests red (the version test, a bare orchestrator over a rolled
  back grid, the deposit's PR 3 S1 test); deleting each `warm` call (construction, a tick's end, after a rollback)
  turns the counter or retry tests red.

## Rows

| # | Finding | Fold | Status |
|---|---|---|---|
| Det SF-1, Arch S3 | caches lazy, counters depend on history | as above; `test_a_retried_tick_counts_the_same_work_as_one_that_never_failed`; the counter test's values now show construction's builds in no tick | open (for the reviewer) |
| Arch S2, Exec S1 | rollback eviction at one call site; heat's eviction untested | as above; `test_a_bare_orchestrator_on_a_rolled_back_grid_serves_no_stale_cache`, `test_no_version_a_rolled_back_window_reached_is_reached_again` | open (for the reviewer) |
| Arch S1 | `bound_reads` and `prepare`'s reads not enforced | `CellStore.reading(reads=...)` narrows a writer-less reader in a window or at rest; the bound, `prepare` and `warm` run narrowed; `test_a_bound_or_a_prepare_reading_an_undeclared_field_raises`, red when either runs unnarrowed | open (for the reviewer) |
| Exec S3 | `cells_copied` undercounts 2.75× | the grid counts every field copy where it is made (`CellStore.cells_copied`): open, views, revocations, commit. A 0.2 m physics tick is 11 fields' worth; red when the revocation isn't counted | open (for the reviewer) |
| Exec S2 | `REGION_GONE` flips with grid spacing | owner ruled (a), below: reverted to main's rule, §5.1 amended, the destruction-based rule a Step 6 checklist row; `test_a_strike_on_a_region_destroyed_earlier_in_the_tick_applies_and_destroys_nothing` at 0.2 and 0.1 m | fixed (author's, after the owner's ruling) |
| Det SF-2 | lesson 34 wrong for slow effects; Maxim ask misfiled | lesson 35 rewritten on the measured misattribution, with `tool_bridge.py:584` and `:885` read at 1.3.3; pointed at lesson 6 and OD-A16, whose roadmap row now cites it | open (for the reviewer) |
| Arch S4 | README quick start and the slice spike run on the retired API | README rewritten and run by `tests/test_readme.py` (its own interpreter, an `ALLOWED_SPAWNS` row); the spike stays pinned to `bfb12f8` in its README (owner, 2026-11-22) | open (for the reviewer) |
| Arch S5 | the constructor for a built world checks nothing | `Simulation(world, *, config, laws)` builds its orchestrator over `world.grid`, so two grids can't meet | open (for the reviewer) |
| Arch S6 | sim_core §2 puts `source_exposure` in `World` | §2 amended: `Simulation` holds it; owner accepted, 2026-11-22 | fixed (author's, after the owner's ruling) |
| Det N-1 | construction's writes don't move a version | fields handed writable in an un-narrowed window bump at commit; test red without it | open (for the reviewer) |
| Det N-2, Exec N4, Arch NIT | §7 keys on `topology_version`, the code on material's version | §7 amended: keys are `field_version`s, which count rollbacks; owner accepted, 2026-11-22 | fixed (author's, after the owner's ruling) |
| Det N-3 | lesson 23 cites a renamed test | fixed | open (for the reviewer) |
| Det N-4 | "one tick per call" is wrong for stage-1 refusals | the marker, `SteppingPort` and lesson 35 say "per call that reaches stage 2" | open (for the reviewer) |
| Det N-5 | commit before publication and the clock | the clock moves before the frame is published, so a publication that raised can't make a retry apply records twice | open (for the reviewer) |
| Arch NIT | stale names | the membrane contract says "its port"; boundaries §6.2 names the deposit; `on_close` was deleted in c721850 | open (for the reviewer) |
| Arch NIT | `_run` tests `Strike` itself | each action declares `edits_cells`; red when a strike's is false | open (for the reviewer) |
| Arch NIT | `Simulation.step` replaces `Physics.work` | `Physics.start_tick()` hands out the tally | open (for the reviewer) |
| Arch NIT | roadmap's membrane line, §13's "a callable" | the roadmap line is current; §13's "a callable its test or host owns" is a Protocol with one call, left as worded | open (for the reviewer) |
| Arch NIT | the fierce-fire gap mixes units | its old figures are labelled "in 6 s turns" | open (for the reviewer) |
| Arch NIT | `place` no longer publishes a frame | stated in its marker: the next tick's frame shows the object | open (for the reviewer) |
| Arch NIT | `Simulation.step` has no gate row | not folded: `LogRecord`'s rows and `test_simulation.py`'s batch tests hold the records it takes; predates PR 4a | open (for the reviewer) |
| Arch NIT | `field_version`'s docstring overclaims | it now says a key may move when values didn't | open (for the reviewer) |
| Exec N1 | the 0.2 m bar 7 figure is noise | recorded as a range: 0.72–0.98× at 0.2 m (the reviewer's runs and mine); 0.32–0.35× at 0.1 m, the gated grid | open (for the reviewer) |
| Exec N2 | `rho_cp` recomputed every substep | deferred to B5's profile pass (a cache beside the faces), not folded here | open (for the reviewer) |
| Exec N3 | the douse exemption isn't in §5.1 | moot: the revert removed the exemption with the rule that needed it | open (for the reviewer) |
| Arch NIT | fire_solid's `_check_region` row | true again after the revert ("not cells.any()") | open (for the reviewer) |

## What "gone" means (Exec S2; owner, 2026-11-22: option (a))

On main, `REGION_GONE` came only from a later paint emptying a region: authored, so it can't depend on the grid.
336eee8 made it "no solid cell left", to meet sim_core §5.1 ("REGION_GONE still refuses a second strike on a
destroyed region"). The reviewer measured that this flips with spacing: a 1.2 m wood cube struck repeatedly at 2e7 J
is first refused at strike 29 at 0.2 m but strike 30 at 0.1 and 0.05 m. Options:

- **(a) Revert to main's rule, and amend §5.1** (recommended for this PR; **the owner's ruling**): gone only when
  authored geometry empties the region. A strike on a destroyed region succeeds with zero effect, as on main, and no
  outcome depends on the grid. The douse exemption is then not needed. Destruction-based "gone" returns with a
  margin-gated rule in the fuel and structure work, as a checklist row.
- **(b) Keep the cell rule, and record it as a Known gap with a strict red gate** on the measured flip, fixed in a
  named later step.
- **(c) Define gone in metres now** (say, solid volume below a fraction of the authored footprint, gated with a
  margin band), which is new design for this PR.

## Delta 1 (`delta1.md`): 0 BLOCKER, 3 SHOULD-FIX, 6 NIT; round 1 read from the tree as 22 fixed, 5 open, 1 deferred, 1 rejected

**Correction first.** The fold and its message claimed that deleting the rebuild after a raised tick turns a test red.
It didn't: that proof was run before `forget` was removed, and not rerun after. Delta 1's D-S1 caught it.

| # | Finding | Fold | Status |
|---|---|---|---|
| D-S1 | the rebuild after a raised tick has no test | the retry test also retries a quiet physics tick, the case that needs it; deleting the rebuild turns it red | open (for the reviewer) |
| D-S2 | the end-of-tick rebuild costs 2.1× on a strike every tick | reproduced at 0.1 m on the T3 tile: 20 face builds and 363 ms per 20 ticks against 4 and 183 ms on 336eee8; bar 7's burn is unchanged. Owner ruled (2): accepted and tracked as a Step 5a checklist row, triggered by B5's turn-time budget | deferred (author's, after the owner's ruling; trigger B5's budget) |
| D-S3 | `tests/_imports.py` over 120 columns | rewrapped; ruff clean | open (for the reviewer) |
| D-N | `Physics.warm`'s narrowing untested | `test_a_law_state_warming_up_reads_only_what_its_law_declares`, red when warm runs unnarrowed | open (for the reviewer) |
| D-N | Det N-5's order untested | `test_a_publication_that_raises_leaves_the_tick_counted_so_no_retry_applies_it_twice`, red when the clock moves after publication | open (for the reviewer) |
| D-N | a refused `place` changes the next tick's counters | a PR 4b checklist row: it ends when `place` runs inside the step's window | open (for the reviewer) |
| D-N | stale text | the checklist's cache row, `scene.py`'s `geometry.MAX_LENGTH_M`, the retry test's comment, CLAUDE.md's layout (`geometry.py`), §7's credit (the new rule proposed, the rollback rule the owner's), §7's measured bar 7 range | open (for the reviewer) |
| D-N | `test_readme.py` takes 5.7 s | marked slow behind the tier variable | open (for the reviewer) |
| D-N | lesson 35 omits that the credit needs a cerebellum | it says so (line 860) | open (for the reviewer) |
| Arch N4 (open) | the fold's reason for §13's "a callable" is wrong: `Port` has `limits` too | §13 now says "an object its test or host owns"; owner accepted, 2026-11-22 | fixed (author's, after the owner's ruling) |

### The end-of-tick rebuild's cost (D-S2; owner, 2026-11-22: option (2))

Every cache is rebuilt for the state at each windowed tick's end, so the counters are a function of state (Det SF-1).
A strike changes `material`, so heat's face conductances and its bound are rebuilt over the whole grid on every
strike tick, not once per physics step. Options:
- **(1) Make both rebuilds incremental:** keep the per-cell conductivity and stability arrays, and recompute only the
  faces and cells around what Topology changed. Each face depends on its two cells, so the result is bit-identical;
  the cost follows the edit, not the grid. Real work in this PR, and its own tests.
- **(2) Accept the cost now and track it:** record the measured 2× on strike-dense ticks, with (1) as a checklist row
  triggered by B5's turn-time budget. No budget exists yet to say 363 ms per 20 ticks at 0.1 m is too slow.
- **(3) Rebuild lazily again** and amend §10 so counters match only on replays that start at a physics tick. This
  gives up what Det SF-1 asked for.

## Delta 2: 0 BLOCKER, 3 SHOULD-FIX, 8 NIT, on 82447d3

Two readers, on the whole fold commit (no snapshot of delta 1's tree survived): `delta2_exec_det_perf_phys.md`
(Executor, Determinism, Performance, Physics: 0 SHOULD-FIX, 3 NIT; 20 fixed, 3 deferred, 1 open of its 24 rows) and
`delta2_arch_wire_trust_bio.md` (Architecture, Wire integrity, Trust boundary, Bio-faithful: 3 SHOULD-FIX, 5 NIT;
28 fixed, 1 open, 2 deferred, 1 rejected of its 32 rows). Each copied verbatim. Their statuses stand as read; each
reopened row (Arch S5, Exec N2) is folded below. Every deletion claim they tried went red.

| # | Finding | Fold | Status |
|---|---|---|---|
| D2-S1, Arch S5 (reopened) | the built-world constructor accepts a world another simulation owns; §2 and §4 say there is one constructor | `World.adopt()`: the constructor adopts its world, and a second adoption raises. §2 names both constructors, §4 lists the second. `test_a_world_another_simulation_owns_is_refused_so_time_has_one_owner`, red when `adopt` is deleted | open (for the reviewer) |
| D2-S2 | §13 and the bridge test's comment still say "one tick per call" | both say "each `execute` that reaches stage 2" | open (for the reviewer) |
| D2-S3 | `sim_core.md` grew from 3,770 to 3,773 words | 3,770 words (`wc -w`) after this fold's own additions, by tightening §7's cost and cache text and §13 | open (for the reviewer) |
| D2-N1 | `Deposit.keep`'s docstring says "topology version" | "`material`'s current version" | open (for the reviewer) |
| D2-N2 | lesson 37 calls the cerebellum's update "credit"; it omits the LLM's read | checked at 1.3.3 (`cerebellum.py`'s docstring, `tool_bridge.py:908`); lesson 37 and OD-A16 now say the forward model learns from the read-back and the LLM reads it, and that NAc's reward credit doesn't come from it | open (for the reviewer) |
| D2-N3 | the cadence row lost its precondition | "the first destroying it and the second applying and destroying nothing" | open (for the reviewer) |
| D2-N4 | Exec S2's Step 6 row sits in the superseded record | moved out, as an "Added by" paragraph like D-B2's | open (for the reviewer) |
| D2-N5 | unwrapped lines and a stray capital | every line this branch added past 120 columns outside tables and headings is rewrapped, word for word; "it" | open (for the reviewer) |
| A N1 | `step`'s docstring says a raising tick changes nothing, but a raising publication leaves it committed | the docstring says so, and the rollback branch's comment no longer says keys recur; a PR 4b checklist row covers a log that would drop that tick | open (for the reviewer) |
| A N2, Exec N2 (reopened) | the D-S2 row lacks the max-profile figure and the deposit's 40 against 10; `rho_cp`'s deferral is only in this file | the row gives both; `rho_cp` has its own Step 5a checklist row, triggered by B5's profile pass | open (for the reviewer) |
| A N3 | the marker's "an instant effect at once" | "an instant effect" | open (for the reviewer) |

## Delta 3 (`delta3.md`, verbatim): 0 BLOCKER, 1 SHOULD-FIX, 6 NIT, on afda61c

One reader (Executor, Architecture, Wire integrity, Determinism) on the delta-2 fold. Of delta 2's 12 rows: 10
fixed, 1 open (D2-S1 with Arch S5, folded below as D3-S1), 1 deferred.

**Correction first.** The delta-2 fold said `World.adopt()` closed D2-S1. It didn't: the flag sat on the `World`, so a
new `World` over a live simulation's grid gave a second owner (D3-S1). It also said every added line past 120 columns
was rewrapped, and `fold.md:70` wasn't.

| # | Finding | Fold | Status |
|---|---|---|---|
| D3-S1, D2-S1, Arch S5 | adoption on the `World`, not the cells; §2 calls the constructor the save loader's, which it can't be | `CellStore.adopt()`: the cells carry the adoption, so no world over them can take a second simulation; `World.adopt` is gone. §2 says `Simulation(world)` adopts a world's cells at tick 0 and a loaded tick is PR 4b's. `test_cells_another_simulation_owns_are_refused_in_any_world_so_time_has_one_owner` covers both worlds, red with adoption deleted | open (for the reviewer) |
| D3-N1 | adoption before `Physics(...)` leaves a failed construction's world owned | adopted last, after the caches are warmed; `test_a_construction_that_raised_leaves_the_cells_free_for_a_retry`, red with adoption first | open (for the reviewer) |
| D3-N2 | the rollback comment says no key can recur; a tick of fires alone counts no rollback | it says a cell window's rollback is counted and a tick of fires alone moves no version | open (for the reviewer) |
| D3-N3 | the module docstring keeps "a tick that raises changes nothing" | "before the window commits" | open (for the reviewer) |
| D3-N4 | the churn row misstates the condition | 20 ticks cycling through 5 radii; a radius the previous step used rebuilds | open (for the reviewer) |
| D3-N5 | `fold.md:70` past 120 columns | rewrapped | open (for the reviewer) |
| D3-N6 | the bridge test's name states the corrected rule | `..._one_tick_per_call_that_reaches_stage_2`, and lesson 37's citation | open (for the reviewer) |
| D3-N7 | §7's cost line lost "measured" and the grid labels | both back, at the same word count | open (for the reviewer) |

## Delta 4 (`delta4.md`, verbatim): 0 BLOCKER, 0 SHOULD-FIX, 4 NIT, on 94ca301

One reader (Executor, Architecture, Wire integrity, Determinism) on the delta-3 fold and the merge of #48. Of the
Delta 3 table's rows: 9 fixed and 1 open. D3-S1 and D2-S1 are fixed, and Arch S5's residual is open, as D4-N2. It
found no route to two simulations over one cell store, other than the copy below.

| # | Finding | Fold | Status |
|---|---|---|---|
| D4-N1 | the retry test covers only the law-tuple refusal; adoption just after `Physics(...)` passes it | parametrized over a refusal in `warm` too (a fire outside the grid); red with adoption moved there | open (for the reviewer) |
| D4-N2, Arch S5 (residual) | a grid rebuilt from a stepped state is published as frame 0 | a PR 4b checklist row: the loader states its tick and what frame 0 is for a loaded state, with a test | deferred (author's; trigger PR 4b's loader) |
| D4-N3 | `copy.copy` of a grid shares its versions and gate with a second simulation | `CellStore.__copy__` and `__deepcopy__` raise; `test_cells_are_never_copied_so_no_two_simulations_share_their_versions`, red without them | open (for the reviewer) |
| D4-N4 | no scan holds `adopt` to `simulation.py` | an `OWNED_CALLS` entry, and a planted case in the scan's test, which goes red without the entry | open (for the reviewer) |

## Delta 5 (`delta5.md`, verbatim): 0 BLOCKER, 0 SHOULD-FIX, 3 NIT, on a1d22ff

One reader (Executor, Architecture, Wire integrity, Determinism). The Delta 4 table read as 3 fixed and D4-N2
deferred, all as the author claimed. The reader notes that the charter's step 4, read literally, defers a code
finding only through a `TEMPORARY` marker, and Arch S5 was a SHOULD-FIX: **for the owner**, whether its PR 4b
checklist row suffices or `Simulation.__init__` needs a marker too.

| # | Finding | Fold | Status |
|---|---|---|---|
| D5-N1 | nothing checks that an `OWNED_CALLS` entry names a call that is made | `test_each_owned_call_is_made_by_one_of_its_owners`, for every entry; red when `adopt`'s one call is renamed | open (for the reviewer) |
| D5-N2 | three PR 4a deferrals sit under the PR 3 group | their own group, "Deferred from PR 4a's review" | open (for the reviewer) |
| D5-N3 | `__deepcopy__`'s docstring gives the shallow copy's reason | it names a deep copy's hazard, D4-N2's | open (for the reviewer) |

**The owner's rulings on delta 5 (2026-11-22).** Arch S5's residual also gets a `TEMPORARY(phase1/sim-clock)` marker
on `Simulation.__init__`, listed under Phase 1 in the roadmap beside its PR 4b checklist row; the lint fails with the
listing removed. A delta 6 reviews the delta-5 fold, the merge with #50's spike pin and this marker.
