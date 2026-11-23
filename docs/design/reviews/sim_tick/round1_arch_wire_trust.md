# PR 4a round 1: Architecture, Wire integrity, Trust boundary

Diff: `bfb12f8..336eee8` (commit 336eee8). Reviewer read the diff, sim_core.md §2/§4/§5/§5.1/§7/§13, boundaries §4.1/§6.4,
the Step 5a checklist, and ran hypotheses on a copy of the tree at 336eee8
(`.../scratchpad/review_4a_arch/tree`, `tree2` for proposed fixes) with the worktree's venv, `-I`, the copy's `src`
and root first on `sys.path`.

**Counts: BLOCKER 0 / SHOULD-FIX 6 / NIT 9**

The shipped path (`Simulation.step` → applier → `Physics`) holds up: one window per tick, rollback covers the
records, the exposure and the caches, the REGION_GONE change is correct, and no rejection path was lost. The six
SHOULD-FIX findings are guards that live at a call site or in a docstring instead of a type, and docs that are now
false.

## SHOULD-FIX

### S1. `bound_reads` (and `prepare`'s reads) are declared but never enforced, so a wrong declaration serves a stale bound with no error
`src/simcore/core/physics.py::Physics._law_bound`, `Physics._prepare`; `src/simcore/core/law.py::Law.bound_reads`

`check_laws` checks only `bound_reads ⊆ reads`. `_law_bound` calls `law.stable_dt` with the window unnarrowed, so a
`stable_dt` that reads a field outside `bound_reads` is evaluated once and then cached forever on the versions of
fields it doesn't depend on. `Law.bound_reads`' own docstring names the failure ("a bound that reads anything else
would be served stale"), and the protocol is the seam 5b's body laws and 6.x's solid will implement.

*Failure scenario (verified, `h1.py`):* a per-substep test law with `reads=("material","temperature")`,
`bound_reads=("material",)` and `stable_dt` = 0.5 s once max T > 100 °C, else ∞, added to the default tuple. Lit at
max power, run 40 physics steps: max T reaches 106 °C, but `stable_dt` was evaluated **once** (at 20 °C), so the
0.5 s bound never applies. An explicit scheme then runs past its stability limit with no error. `prepare` runs
unnarrowed too: heat's deposit reads `material` (declared), but nothing stops a law's `prepare` from reading an
undeclared field, which breaks the §5.1 rule that a law reads only its `reads`.

*Fix (verified):* the gate already has the mechanism. In `tree2`, wrapping `_law_bound`'s call in
`self._grid.as_writer(None, reads=law.bound_reads)` and `_prepare`'s in `as_writer(None, reads=law.reads)` makes
`h1.py` raise `UndeclaredRead: None doesn't declare 'temperature'`, and `tests/test_laws.py`, `test_heat.py`,
`test_simulation.py`, `test_cross_tier.py`, `test_exposure.py` and `test_deposit.py` pass (130 + 150 passed; the full
suite and the bit-identity schedule were not run).

### S2. Rollback eviction moved out of the type and into one call site; a `Physics` not built by `Simulation` keeps its caches across a rollback
`src/simcore/core/simulation.py::Simulation.__init__` (`world.grid.on_roll_back(physics.forget)`);
`src/simcore/core/deposit.py::Deposit.__init__`; `src/simcore/core/physics.py::Physics.__init__`

On `bfb12f8`, `Deposit.__init__` registered its own `grid.on_roll_back(self._forget)`, so any deposit evicted its
cache when a window rolled back. Now only `Simulation.__init__` registers `Physics.forget`. Every other owner of a
`Physics` gets no eviction: `physics.strike`, `tests/_cells.py`'s run helper, the direct `Physics(...)` tests, and in
PR 4b the save loader's construction half (§2: "builds every cache … on load"). CLAUDE.md asks for invariants in
types, and this moves one from a type to a call site.

*Failure scenario (verified, `h2.py`):* `Physics(g).run(0.5, …)` inside `g.writing(writer=None)` that then raises.
After the rollback, `deposit._weights` still holds 1 entry, `_faces` is still cached and `_bounds` holds 2. The
rollback restored `topology_version` and the material version, so a different later edit that reaches the same
versions is served those entries. That is the exact bug §7's eviction rule (`reviews/sim_step/fold.md` S1) exists to
prevent. `CellStore.field_version`'s docstring ("Equal versions mean equal values, so a cache keyed on them is a
function of state") is also false across a rollback unless someone registered a listener (see N9).

*Fix (unverified):* register in `Physics.__init__` (grid at rest), as `Deposit` did.

### S3. The caches are built lazily, not eagerly as §2 requires; `work.py` and the commit claim otherwise
`src/simcore/core/heat.py::HeatState`, `src/simcore/core/physics.py::Physics.__init__`, `src/simcore/core/work.py`
(module docstring)

sim_core §2: `from_scene` "builds every cache … eagerly … so a run from construction and a replay from a loaded state
start alike". §10 makes bar 6's "identical on replay" depend on that. The commit says "each law's state built eagerly
at construction", and `work.py` says "Because every cache … is built eagerly (§2), a replay counts exactly what the
live run counted". In fact only the state *objects* are built. `HeatState._faces` is `None`, the deposit is empty and
`Physics._bounds` is `{}` until the first physics tick.

*Failure scenario (verified, `h4.py`):* after `from_scene`, faces are `None`, bounds `{}`, deposit 0. The first
physics tick (5) reports `rebuilds (('heat/deposit', 2), ('heat/face_conductances', 1))` and
`stable_dt_evaluations 2`; tick 10 reports none. A run resumed from a save taken at tick 7 (PR 4b) builds those
caches on *its* first physics tick (10), so tick 10's `WorkCounters` differ from the live run's, and bar 6 fails for
replay-from-load. Replay from construction agrees today only because both runs are lazy in the same way. Either build
eagerly or correct §2/§10/`work.py`; at present the code, the contract and the docstring disagree.

### S4. The README quickstart and the slice spike no longer run: both call API this commit removed, and the commit doesn't say so
`README.md` (lines 30–41), `spikes/slice/slice_server/sim.py` (lines 40, 41, 70, 85, 162)

The README's example calls `World.from_scene`, `Applier(world)`, `world.frames` and `world.advance()`. All four are
gone or have changed signature (verified: `hasattr(World, "from_scene")` and `hasattr(World, "advance")` are both
False; `Applier.apply` now requires `sources=` and `resolve=`). The slice server (`Sim.__init__`, `frame`, the advance
call and `outcome.metadata.get("destroyed_volume_m3")`) breaks the same way. Neither is covered by mypy or pytest
(spike tests run from `spikes/slice` only), so the gate stays green. The README is the repo's front door, and the
spike is the owner's playable prototype.

There is also no shipped `Port`: the only implementation is `tests/_sim.py::SteppingPort`. §13 allows a test-owned
port, but the README can't be fixed without one or without rewriting it around records. Correct the README, and
either fix the spike or say in the commit and PR that it is left broken.

### S5. The "seam is gone" claim is false: `Simulation.__init__` is still a public two-part constructor with no invariant, and a test uses it
`src/simcore/core/simulation.py::Simulation.__init__`; `tests/test_exposure.py::_run`; `docs/roadmap.md` (entry removed)

The commit says "Simulation.from_scene is the one constructor; the interim Simulation(world) seam is gone", and the
roadmap entry for the seam was deleted. Yet `Simulation(world, physics, *, config)` is still public, called only by a
comment saying it's private. `tests/test_exposure.py` uses it to give a world construction-time sources, which
`from_scene` can't take. The old seam at least refused a world that had advanced. The new one checks nothing: not that
`physics` was built on `world.grid`, not that the grid is still at construction.

*Failure scenario (verified, `h3.py`):* `Simulation(World(ga), Physics(gb), config=T3)` with two grids built from one
scene. An ignite at tick 1 succeeds, quiet ticks run, and a strike at tick 2 raises `WindowClosed`. The simulation
stays wedged at that tick until a physics tick also raises. It fails loudly, but late and far from the cause, and §2's
"one constructor" is a comment, not a type. Either make the seam private, or have `from_scene` take the
construction-time sources, or keep the roadmap entry and say the seam remains. As it stands, the claim is false.

### S6. sim_core §2's composition table now contradicts the code on who holds `source_exposure`
`docs/design/sim_core.md` §2 (the "Cell state | World" row), `src/simcore/core/simulation.py::Simulation._run`

§2 says `World` holds `source_exposure` and changes it through declared writers inside the window. The code keeps it
on `Simulation` and makes the tick's rollback safe by working on a `copy()` committed after the window. That is a
reasonable design, but it is a contract change, and §2 (which owns the composition) wasn't amended. PR 4b's digest
member 3 and the save's reader will follow §2 and look for it on the world. Amend §2, or move it.

## NIT

- **N1. Stale names left by the move.** `pyproject.toml` contract `membrane-reads-frames` is still named "writes
  through the applier only", though its comment now says port. boundaries.md:458 says "today `World._power_field` over
  `sources`". `fire_solid.md`'s consumer table still lists `applier._check_region` as `not cells.any()` ("is gone"),
  which this commit changed (the row is dated "read at 396ae10", but the deposit rows beside it were updated).
  `window.py::WindowOwner.on_close` now has no caller in `src/`, and its docstring says "the world publishes a frame
  there", which is no longer true.
- **N2. `Simulation._run` decides the window kind by the applier's action types**
  (`any(isinstance(r.params, Strike) …)`), so the orchestrator knows which actions need cells. When imagine becomes
  an intent kind (4b), this line has to change too. It fails loudly if forgotten (the cell write raises), so this is
  a NIT.
- **N3. `Physics.work` is a public attribute that `Simulation.step` replaces every tick**
  (`self._physics.work = work = Work()`). Two owners of one tally, coupled through attribute assignment.
- **N4. §13 says the port is "a callable"; it is a `Protocol` with `limits` and `submit`.** That is fine and needed
  (stage 1 parses against the limits), but the contract text differs. roadmap.md:51 still says "the SEM membrane
  applies synchronously with no log"; it now submits and steps, which is close but not the marker's wording.
- **N5. Cache keys differ from the contract's wording.** §7 and the checklist say face conductances and heat's bound
  are cached "per `topology_version`"; the code keys them on `field_version("material")`. That is a finer and valid
  key (material changes only through Topology), but the docs should say which key is used.
- **N6. `docs/architecture.md`'s fierce-fire gap mixes new figures in seconds with "Older three-rig figures"** in
  turns ("…peaks at 0.259 … Older three-rig figures: It narrows near turn 30 …", with a capital I mid-sentence, and
  `temperature_max` 540/614/978 at turn 27). A reader can't tell which numbers are current.
- **N7. `imagination.place` on a simulation's grid no longer publishes a frame.** World's `on_close` publish is gone,
  so an imagined object is invisible to observers until the next tick that has a record or runs physics. It sits under
  its `TEMPORARY(phase1/sim-clock)` marker for 4b, but neither the marker nor boundaries §4.1 says so.
- **N8. `Simulation.step` has no gate-registry row**, though it is now the membrane's only write path (through the
  port) and holds the batch check the new `Port` rows cite ("Simulation.step's batch check … judge it"). This predates
  PR 4a (`simulation.py` isn't a gate module).
- **N9. `CellStore.field_version`'s docstring overclaims** ("Equal versions mean equal values"). Across a rollback,
  equal versions can mean different values. The claim holds only for a cache with a rollback listener (see S2).

## Not findings (checked)

- **Rollback of a raising tick:** records, sources, cells, versions, `topology_version`, the exposure (copy kept only
  on commit), the clock and the frames all stay unchanged; `Physics.forget` clears every cache on the shipped path. A
  sources-only (`holding`) tick that raises discards its dict and exposure copy. Skipping `end_tick` on a quiet tick
  is correct: only records change sources, and `end_tick` records only changes.
- **Applier stage 2 inside the window:** every refusal path survives (NO_REGION, NOT_SOLID, REGION_GONE,
  NOT_ON_REGION, NOT_BURNING, `action.check`'s limits, and TypeError for a non-action). A refusal writes nothing to
  the window's table. A raising record (TypeError, the `resolve_loads` count mismatch) rolls back the whole tick, so
  nothing is left half-applied; that is stronger than before. `HeatSource` and `Load` validation can't raise after
  `action.check` passes.
- **REGION_GONE:** `cells & grid.solid` is correct for "no solid cell left". The douse exemption needs
  `fire:<region>` in the window's table, so it can't be used to act on a gone region in any other way. An ignite on a
  destroyed crate is now refused, as §5.1 intends.
- **Bridge (§13):** stage 1 and the target check refuse before `submit`, so no record and no tick (test holds
  `sim.tick == 2`). The marker text matches §13 point for point (one tick per call, every `physics_every`-th call runs
  physics, not logged, no outcome bar). `_from` drops the effects. Outcome bars run through records, not the port
  (`_block_strike`'s comment, cross-tier); the port is used only to read instruments and for validation tests.
- **Wire:** every `Outcome.metadata` consumer in `src/` and `tests/` moved to `.effects` (only the spike is left,
  S4). `CellFrame.of` callers pass `tick` and `time_us`. `Observation.tick` has no other implementer. The snapshot's
  `time_s` key and dtype are unchanged; its value is now the tick's end, which `test_snapshot` holds.
  `TickReport.work` is built on every path.
- **Guards:** the writer-scan change (a `sources` parameter is an alias of the window's table) makes the scan
  stricter, not weaker. Writes through it count as writes, and the two new positive cases hold it. Renaming the
  parameter is a blind spot by name, the same kind the scan already states. WINDOW_OWNERS matches the code
  (`Simulation._run`, `World.writing`, `constructing`, `_voxelize`). The import contracts add `work` to the core's
  public surface and to the membrane's forbidden list, consistent with `CORE_PUBLIC_SURFACE` and `MEMBRANE_SURFACE`.
  The re-export scan cases follow `Physics`.
- **Markers:** the three `TEMPORARY(phase1/sim-clock)` markers for `World.advance`, the applier's window and
  `_power_field` are gone, along with the code they marked. `imagination.place`'s marker and the bridge's
  `phase1/agents` marker remain, and `lint_markers.check_markers` returns `[]` against roadmap.md on the copy.
- **Laws:** no law imports another. `HeatState` holds the deposit and the faces, the stateless laws share
  `STATELESS`, and `check_laws` runs in `Physics.__init__`. Within-call overlap reuse in `Deposit.power` is
  bit-neutral (a frozen tuple reused). `_CELL_FIELDS` (4) matches the channels the window copies.
- **Docs numbers:** architecture.md's late-burn and fuel-past figures match the commit's measurements (0.550/0.370
  at 900 s, 830/629.5 s, 31.9%, 243/201.5 s, 423,810/578,046 °C), and the red-gate test names exist.
