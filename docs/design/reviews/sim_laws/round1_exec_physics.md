# Step 5a PR 2 (phase1/sim-laws @ 3b4c493): Executor and Physics review

Reviewer: independent, read-only. Every plant was made in an archive copy under
`.worktrees/_durable/sim_laws_review/exec_work/` (`base` = f72817a, `head` = 3b4c493, `plant` = head with plants
reverted after each one). The worktree was not touched.

**Counts: 0 BLOCKER, 2 SHOULD-FIX, 4 NIT.**

## What I verified

**Bit-identity holds.** I extracted f72817a and 3b4c493 and ran one script (`exec_work/digest.py`, `digest2.py`)
against each tree's own `src/`, with `simcore.__file__` printed to confirm which tree was imported. Every digest
is byte-identical between the two trees:

- the determinism scenario (`tests/test_determinism.py::run`) at 0.2 m and 0.1 m (`f7429cba…`, `e9e57122…`);
- a 120-turn fire-only burn at 0.2 m (state digest, plus a hash of every turn's substep count);
- four strikes in a row on the wall at 0.2 m and 0.1 m (1e6, 2e7, 5e7, 2e7 J), with every outcome's
  `destroyed_volume_m3` and `absorbed_j` equal to the last bit;
- an imagined crate placed through `place`, then 10 turns of fire, at 0.2 m and 0.1 m.

**The tightening replan holds too, on a path the shipped scenario never reaches.** I instrumented `substep_loop`:
the determinism scenario has 1 (0.2 m) and 5 (0.1 m) substeps that change the world, and **none of them tightens
stability**, so the digests above never run the `limit < dt` branch. I compared it directly (`exec_work/replan.py`):
base `heat.step(..., on_substep=wood→steel)` against head `run_physics(laws=(HEAT, _EditOnce))`, with a nonzero
power field and an uneven interval, for k = 3, 7 and 10. The substep counts (456, 1156, 1685), the temperature
bytes and `time_s` are identical.

**Law order.** `(damage.loads, heat, damage.thermal)` reproduces the old arithmetic exactly. Per substep, heat's
`substep` runs first, then thermal's integrity decrement (the same expression and dtype cast), then Topology's
destroy of `hot & integrity <= 0`, the mask the old `grid.destroy` got. `bound()` is
`min(heat.stable_dt, inf, inf)`, the same float. The power refresh moved from the top of the loop into `once`, which
is equivalent: `_power_field` is a pure read, and it is evaluated against the same cells. The replan trigger moved
from "destroy returned > 0" to "`topology_version` moved". These are equivalent, because a Destroy is emitted only
when `gone.any()`, `gone` is a subset of `solid`, and `destroy` marks an edit only when n > 0.

**Strikes as loads.** A strike still resolves inside the applier's own window, right after validation, as before
(`Applier._strike` → `physics.strike` → `resolve_loads`). For a single load, `n = gone.sum()` equals the old
`destroy` count (gone ⊆ solid = non-air), and `absorbed` uses the pre-strike `solid`, as before. The four-strike
sequence shows that each strike sees the previous one's crater.

**Mutation plants, each red as claimed:**

| Plant | Red test |
|---|---|
| swap heat and thermal in `DEFAULT_LAWS` | `test_the_law_tuple_is_bit_identical…` |
| `once` always returns False (no refresh after an edit) | `test_heat` replan and power tests |
| drop `& ~slated` | `test_two_loads_in_one_record_count_each_broken_cell_once` |
| `if limit < dt` → `if False` | `test_a_step_replans_at_the_shorter_step…` |
| refresh only on the first substep | `test_heat` |
| rollback doesn't restore `topology_version` | `test_a_window_that_rolls_back_restores…` |
| bump the version per request, not per batch | `test_topology_bumps_the_version_once_per_batch…` |
| `_channel` always returns the writable array | `test_a_law_cannot_write_a_field…` |
| `_require_writer` always passes | `test_a_law_cannot_write_a_field…` |

I did not re-run the import-contract plant (lint-imports) or the applier-scan plant. The applier scan's own
parametrized catches pass.

**Suites run on the worktree:** `test_laws`, `test_fields`, `test_ownership`, `test_heat`, `test_damage`,
`test_determinism`, `test_imagination`, `test_act_validation`, `test_tooling_config`: 492 passed, 1 skipped,
3 xfailed. `test_simulation`, `test_cross_tier`, `test_scene_v1`, `test_validation`, `test_frames`: 340 passed,
3 xfailed.

## Findings

### SHOULD-FIX 1: `src/simcore/core/writers.py::WriterGate.as_writer`: any caller can name any writer, so the B43 guards hold only for honest callers

`as_writer(name)` checks only that `name` is in `WRITERS`. Nothing ties the name to the caller. Two plants pass
every relevant test:

- **G3.** In `ThermalLaw.step`, I replaced the `Destroy` request with
  `with grid.as_writer('topology'): grid.material[gone] = AIR_ID; grid.integrity[gone] = 0.0; grid._mark_edited()`.
  `test_laws`, `test_ownership`, `test_fields` and `test_damage` all pass (105 passed). Damage edits the world without
  going through Topology.
- **G4.** In `HeatLaw.step`, I replaced `as_writer(self.name)` with `as_writer('construction')`. The entire suite
  passes, except two git-dependent tooling tests that fail only because the archive copy is not a repository. Heat
  then holds write access to `material`, `integrity` and `regions`.

`test_only_topology_edits_the_world` scans only `.paint`, `.destroy` and `.name_region` calls, not subscript writes
to the topology fields. `test_a_law_cannot_write_a_field…` proves that the window refuses a writer who names itself
honestly, not that a law cannot write an undeclared field.

The commit lists "laws narrow at runtime with as_writer rather than through typed handles" as a departure. That
departure is sound only if the call sites are held, and nothing holds them. The commit's sentence "a field's array
is writable only for a declared writer" overstates what the guard does.

**Failure scenario:** PR 3's solid law, or a hurried fix, writes `material` "as topology" to skip a request. It lands
green, and `topology_version` and the per-batch contract silently stop meaning anything.

**Fix (unverified):** add an AST scan over `src/`:
- `as_writer(` takes only `self.name` inside a class in a law module;
- `TOPOLOGY` and `CONSTRUCTION` (or their literals) appear only in `topology.py`, and in `scene.py` for
  `writing(writer=CONSTRUCTION)`;
- extend the world-edit scan to subscript and augmented assignment on `.material`, `.original_material` and
  `.integrity` outside `grid.py`, `topology.py` and the integrity writers;
- prove it with G3 and G4.

### SHOULD-FIX 2: `src/simcore/core/grid.py::CellStore._channel`: the read-only view can be unlocked, and writable handles outlive their `as_writer` block

`_channel` returns `arr.view()` with `flags.writeable = False`. The base is the window's writable copy, so one line
makes it writable again. This is exactly the weakness `readonly.frozen`'s docstring names and avoids at rest. Also,
an array taken inside a writer's block stays writable after the block ends.

Demonstrated on head (`exec_work/head`). Inside `as_writer("heat")`, `g.integrity` was unlocked with
`v.flags.writeable = True` and set to 0.25, which committed. A `T = g.temperature` taken in heat's block was then
written outside any block (999.0) and inside `as_writer("damage.thermal")` (777.0), and both values committed.

**Failure scenario:** a law caches a field array across substeps, which is the natural numba-seam pattern §5's
`prepare` invites, and writes it later as another writer or as nobody. No check sees it.

**Fix (unverified):** either hand a writer a lease that is revoked when the block ends (a per-block writable copy
committed at exit, which costs a copy per law per substep and must be profiled first, B5), or state the limit
plainly in `writers.py` and in the B43 backlog row: the gate catches mistakes, not handles kept past their block.
The second option still needs SHOULD-FIX 1's scan to forbid keeping field arrays on law objects.

### NIT 3: `src/simcore/core/writers.py::WriterGate.as_writer`: an exception leaves `_edited` set

On a raise, `_close_batch` is skipped, but `_edited` stays True. If a caller catches inside the still-open window,
the next batch, or the window's `_end`, bumps the version for an edit that belonged to the failed batch. No shipped
path catches inside a window today.

**Trigger:** PR 4, when refusals happen inside `Simulation.step`'s window.

**Fix (unverified):** reset `_edited` in a `finally`, or decide in `except` whether a partial batch counts.

### NIT 4: `tests/test_tooling_config.py::test_the_laws_independent_contract_covers_every_law_in_the_tuple`: a set of modules collapses the two damage laws into one

The test passes with 3 laws in 2 modules. Because both damage laws live in one module, nothing holds
`damage.loads` and `damage.thermal` apart (shared module state, one calling the other). That is sound today, since
they share only `_axis_fraction`-free imports, and the departure is declared.

**Trigger:** when damage becomes the package of one module per resolver that sim_core §5.1 describes.

### NIT 5: `src/simcore/core/physics.py::run_physics` and `resolve_loads`: the code departs from sim_core §5 and §5.1 wording without listing it

- **The replan trigger.** §5 says to replan "after any Changes with a topology request". The code replans on a
  version change, so a no-op Destroy does not trigger one. The code's behaviour matches the old behaviour and is
  arguably better, but it is not in the commit's departure list.
- **The batch boundary.** §5.1 makes "one record's apply (its stage 2 and its loads)" one batch.
  `resolve_loads` makes one batch per per-record law. These are identical today with one such law.

### NIT 6: `tests/test_laws.py::_reference_advance` and `_reference_strike`: the reference shares the code under test

The reference uses the current `heat.substep`, `grid.destroy` and window, and the scenario never reaches the
tightening replan (see above). That makes the test a regression check of the orchestration, not of the arithmetic.
The claim of bit-identity against f72817a rests on an uncommitted script. I reproduced that claim independently, so
it is **true**. A one-line note in the test's docstring saying what the test does not cover would keep a future
reader from over-trusting it.

## Commit-message claims

| Claim | Verdict |
|---|---|
| bit-identical (determinism scenario, burn, strikes, 0.2 and 0.1 m) | **true** (independently reproduced) |
| swapping heat and thermal turns `test_laws` red | **true** |
| strike resolved right after its record's stage 2 | **true** |
| the substep loop is shared with `heat.step` | **true** |
| the replan on a version change matches the old replan | **true**, including the tightening branch with power |
| `_channel` and `_require_writer` plants turn `test_a_law_cannot_write…` red | **true** |
| "a field's array is writable only for a declared writer" | **overstated** (SHOULD-FIX 1, 2) |
| "Scene.build, imagination and both damage laws … no longer edit cells themselves" | **true of the code**; no test would catch a regression that writes cells by subscript (G3) |
| laws-independent contract and applier-scan plants | not re-run, accepted on the commit's word |
