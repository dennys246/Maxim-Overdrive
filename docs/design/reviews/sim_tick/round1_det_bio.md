# PR 4a (336eee8) review, round 1: Determinism and replay; Bio-faithful integration

Diff: `git diff bfb12f8 336eee8`. pymaxim read: 1.3.3 (the sim-replay venv's site-packages). Experiments ran on a
`git archive` copy of each commit in the session scratchpad
(`/private/tmp/claude-501/-Users-dennyschaedig-Scripts-Maxim-Overdrive/74644a49-11ab-4a8e-8ab1-c2ccc9c3fbed/scratchpad/review_4a_det/`,
scripts in `scripts/`), with the worktree's `.venv/bin/python -I`.

**Counts: 0 BLOCKER, 2 SHOULD-FIX, 5 NIT.**

## Findings

### SF-1 (SHOULD-FIX, Determinism): no cache is built eagerly, so the work counters depend on what the caches went through, not on the state
`src/simcore/core/heat.py::HeatState.__init__`, `src/simcore/core/physics.py::Physics.__init__` (`_bounds = {}`),
`src/simcore/core/physics.py::Physics.forget`, `src/simcore/core/simulation.py::Simulation.from_scene` (docstring),
`src/simcore/core/work.py` (module docstring).

sim_core §2 says `from_scene` "builds every cache and member digest eagerly ... so a run from construction and a
replay from a loaded state start alike", and §10 says the counters "are identical on any replay, because the caches
... are built eagerly". `from_scene`'s docstring says "Every law's caches are built here, eagerly (§2)", and
`work.py` says the same. Neither is true. `HeatState` starts with `_faces = None` and an empty `Deposit`, and
`Physics._bounds` starts empty, so all three are built on the first physics tick that needs them. After a rollback
`forget()` empties them and nothing rebuilds them at rest. `tests/test_simulation.py::test_the_work_counters_hold_their_exact_values_and_repeat_on_a_rerun`
records the lazy build as the expected value ("The first physics step builds heat's caches": `rebuilds ==
(("heat/deposit", 2), ("heat/face_conductances", 1))`, `stable_dt_evaluations == 2`).

Failure scenarios:
- *Measured (scripts/rollback.py):* the same schedule run twice, once with tick 10 (or 15) raising inside
  `heat.substep` and then retried with the same records. The cells, sources and `source_exposure` afterwards are
  bit-identical, which is right. The retried tick's `WorkCounters` differ, though: with the raise injected at 10 it
  reads `rebuilds=(heat/deposit 2, heat/face_conductances 1), stable_dt_evaluations=2`, and without one it reads
  `(), 0`. With the raise at 15 it reads `(heat/face_conductances 1), 2` against `(), 0`. So the counters depend on
  a tick that left no trace in state.
- *By construction, for PR 4b and the save:* a session loaded at tick N rebuilds faces, the bound and the deposit on
  its first physics tick, where the live run had cache hits. Bar 6 ("identical on replay") then fails on that tick
  for any replay that starts from a loaded state, which is the case §2 names.

The bits are unaffected: every cache is a function of the versions it is keyed on, so it is the counters and the
false claims that are wrong. Fix: build the three caches in `new_state` and `Physics.__init__`, and again at rest
after `forget`, or else amend §2 and §10 and the two docstrings. Unverified. The bar-6 test will need its expected
values changed either way.

### SF-2 (SHOULD-FIX, Bio-faithful): lesson 34 claims something about the port that the port doesn't deliver for heat, and it files its Maxim ask beside the wrong item
`docs/lessons_maxim_in_games.md` §34; the `TEMPORARY(phase1/agents)` comment in
`src/simcore/adapters/sem/bridge.py::StructureModulator.execute`.

1. **The claim is true only for instant effects.** The lesson says Maxim's "read right after execute" holds in a
   stepped world "only if the port runs a tick for it", and that the port makes it hold. It holds for a strike:
   Topology changes cells within the record's own tick. It doesn't hold for fire. *Measured (scripts/cascade.py,
   through pymaxim 1.3.3's `ModulatorAffordanceTool` with the `SteppingPort`, alternating `crate_ignite` and
   `crate_extinguish`):* the `entity_state.temperature_max` read back after each call stays at 20.0 for calls 1–4,
   rises to 21.29 on call 5 (a physics tick), and rises again to 22.15 on call 10. Call 10 is an extinguish, so the
   post-execute read credits the douse with heating, because the physics that ran on its tick carried earlier
   ignites' exposure. In pymaxim 1.3.3 that read is not only logging: `tool_bridge.py` reads every sensor right
   after `self._modulator.execute` (about lines 576–588 of the installed file) and passes it as `actual=` to
   `Cerebellum.observe_from_action` (about lines 860–886), and it puts `entity_state` in the LLM's output. So the
   interim port gives an action's read-back whatever physics happened to run on that call, at a rate set by
   `call_index % physics_every`. Before this commit the bridge never ran physics, so this is new behaviour. §13
   forbids outcome bars on this path, so no bar is wrong today. The lesson is wrong, though, and it is the evidence
   base for a Maxim proposal.
2. **It points at the wrong existing item.** "Maxim's tool loop should read the response from the next observation,
   not from the tool's return" is lesson 6's point ("An action's effect may arrive after the call returns", proposal
   P3), and it is already Phase 3's **OD-A16** ("Credit for effects measured later: receipts, the cerebellum
   observing at settle", `docs/roadmap.md:197`). Lesson 34 names neither. It points at OD-A4 (a tool's duration in
   world time) and defers to `phase1/agents` the question of "whether it needs its own Maxim item, after searching
   Maxim's origin/main". The rule ("Search Maxim before proposing to it") says an ask that duplicates an existing
   item becomes a question on that item. Here the item is our own OD-A16, so the search the lesson defers would only
   rediscover it.
3. **Its consequence is already settled.** "phase1/agents must replace 'effect visible at once' with a pending
   result" is already `sem_stimuli.md` §6.2 and lesson 23's 2026-11-20 amendment. The lesson's new content is the
   port mechanism, which point 1 qualifies.

Fix (unverified): restrict the headline to instant effects; add the measured misattribution with its numbers; cite
`tool_bridge.py`'s readback and its `observe_from_action` call at 1.3.3; and point the Maxim line at OD-A16 and
lesson 6 instead of opening a question.

### N-1 (NIT, Determinism): `field_version`'s invariant has an unbumped writer
`src/simcore/core/grid.py::CellStore.field_version`, `CellStore._channel`.

The docstring says the count "moves whenever name's values may have changed, and never otherwise ... Equal versions
mean equal values". A field handed out writable in an un-narrowed window is not counted, because `_handed` records
only narrowed blocks, and construction's window (`scene.constructing`) is one. *Measured (scripts/ver.py):* on a
`Simulation`'s grid, `constructing(g)` writing `temperature[...] = 999` and `integrity[...] = 0.5` leaves both
versions unchanged, at `(0, 2)` before and after. The shipped path is safe only because construction runs before
any reader (heat's bound reads `material`, which moves only through `_set_cells`). Tests do call `constructing` on
a live simulation's grid (`tests/test_validation.py::test_a_region_that_lost_all_its_cells_reads_nan_and_cannot_burn`).
PR 4b's "a member is rehashed only on a tick whose window wrote it" (§9) will presumably key on these versions too.
Either bump in the un-narrowed case or state the precondition in the docstring.

### N-2 (NIT, Determinism): the cache key the code uses is not the one the contract states
`src/simcore/core/heat.py::HeatState.faces`, `HeatLaw.bound_reads`; sim_core §7.

§7 (and the checklist's PR 4a row) says face conductances and heat's `stable_dt` are cached "per
`topology_version`". The code keys both on `field_version("material")`, a new counter that §7 doesn't define.
It is finer and still sound: the material version moves only when Topology changes a material value, and a
rollback restores it. But it is a contract surface (PR 4b's digest will read it), so §7 should name it.

### N-3 (NIT, Bio-faithful): lesson 23 now cites a test that no longer exists, and a rule that no longer holds
`docs/lessons_maxim_in_games.md` §23 still cites
`tests/test_ownership.py::test_the_shipped_path_publishes_a_frame_after_each_application_and_each_advance`, which
this commit renamed to `test_the_shipped_path_publishes_one_frame_per_tick_with_a_record_or_physics`. Its
"every write window that closes publishes" is also no longer the rule. The commit edits this file but leaves §23
pointing at a missing guard.

### N-4 (NIT, Bio-faithful): "one tick per call" is not what the port does
The marker in `bridge.py::StructureModulator.execute`, `tests/_sim.py::SteppingPort`, and lesson 34 all say world time
advances one tick per call. A call refused at stage 1, or for its target, runs no tick (the test asserts this). A
stage-2 refusal (not burning, region gone, not on region) costs a tick, and on every fifth call a physics step. So an
agent's malformed call is free in world time and a well-formed refused one is not. This doesn't matter in the interim
under §13, but the text should say "one tick per call that reaches stage 2".

### N-5 (NIT, Determinism): the window and exposure commit before publication and the clock
`src/simcore/core/simulation.py::Simulation.step`: `_run` commits the cells, the sources and `self._exposure`, and
only then do `_publish` and `self._clock.advance()` run. If `_publish` raises (unlikely: `CellFrame.of` on a grid at
rest, then `FrameFeed.publish`'s order checks), tick T's effects are committed with the clock still on T, and a
caller retrying `step` for tick T applies its records twice. The docstring's "the clock, the exposure and the frames
move only after it commits" is true but doesn't cover this. Publishing inside the same guarantee, or advancing the
clock before publishing, would close it (unverified).

## Not findings (checked)

- **The bit-identity claim holds on an independent schedule.** I ran my own schedule (`scripts/bits.py`) on both
  commits: an ignite on the crate and a strike on the wall at tick 1, an ignite on the wall at 3, a douse at 12, a
  re-ignite at a new power at 13, a strike at 40 and a douse on the crate at 55, then 600 ticks. Every outcome and
  the digest of cells, regions and sources match bfb12f8 and 336eee8: `eb91fb44…` at 0.2 m and `499b3335…` at 0.1 m.
- **Rollback.** A raise inside physics leaves the cells, the sources and `source_exposure` (`_live` and `_closed`)
  bit-identical to a run without it, once the tick is retried (scripts/rollback.py, raising at ticks 5, 10 and 15).
  The exposure is worked on `copy()`, which is independent because `Source` and `Share` are frozen, and is kept only
  after the window commits. A fires-only (`holding`) tick touches no cache, so its rollback firing no listener is
  harmless.
- **Cache keys after a rollback.** `_roll_back` restores `_versions` and `topology_version`, and `on_roll_back`
  (registered at rest in `Simulation.__init__`) calls `Physics.forget`, so a version reached again by a different
  edit can't hit a stale entry. The bounds of `damage.thermal` and `damage.loads` (`bound_reads=()`) are constants,
  so caching them forever is right. Heat's bound and faces read only `material` plus fixed data (the material table
  and `dx`).
- **Iteration order.** `Physics._states` and `inputs` follow the tuple's order. `Work`'s Counters are read sorted.
  Exposure shares are sorted by key (stable, so a key's closed segments stay before its live one, in tick order),
  and the deposit accumulates in that order. Nothing new iterates a set or an unsorted dict into arithmetic.
- **Time.** No float time is stored. `SimConfig` holds integers, `physics_seconds` is derived per call, and frames
  carry `tick` and `time_us`, with `time_s` derived. A frame's stamp `tick * tick_us` is the tick's end, as §3 and
  §4 say. `FrameFeed.publish` refuses a tick that doesn't move forward.
- **Counters on a rerun from construction.** These are equal (the repo's bar-6 test, and scripts/rollback.py's
  baseline). SF-1 concerns only reruns that start from a load or that retry a rolled-back tick.
- **Nothing in this commit blocks PR 4b's digest.** `field_version` and `topology_version` give a cheap "this field
  was written this tick" signal (subject to N-1). The exposure's `closed` is already sorted for member 3.
  `TickReport` carries each outcome's `code` and `effects` for member 5.
- **The frame right after `execute` holds the action's effect for a strike.** `test_strike_moves_the_integrity_sensor`
  shows it, and scripts/cascade.py shows the frame's tick equal to the call count. Fire is qualified in SF-2.
- **The interim rule (§13) is respected.** No outcome bar runs through `submit`. `tests/test_cross_tier.py` and
  `tests/test_determinism.py` build a `SteppingPort` only to get `region_parts`' sensors, which read frames, and they
  drive their scenarios with records. The marker keeps its phase and roadmap row.
- **Taking `destroyed_volume_m3` and `absorbed_j` out of `ModulatorResult` is a bio-faithful gain.** pymaxim 1.3.3
  merges `**result.metadata` into the tool output the LLM reads (`tool_bridge.py`, `output_dict`), so these were
  exact oracle numbers shown to the model. They are now gone (measured: the output keys are `active_failures`,
  `affordance`, `entity`, `entity_state`, `success`). This matches `sem_stimuli.md` §6.2 (T12's `absorbed_j`
  sentinel).
- **The `REGION_GONE` fix and the douse exception** are consistent across spacings (they are judged on solid cells
  of the region the record names), and they keep a fire on a destroyed crate dousable.
- **Nothing in this commit works around Maxim.** The port is our membrane's write half, and `ModulatorResult` keeps
  Maxim's fields exactly (`test_sem_compat`).
