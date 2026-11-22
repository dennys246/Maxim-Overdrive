# Step 5a design review: Executor lens

Reviewed: `docs/design/sim_core.md` and `docs/plans/checklists.md` "Step 5a", worktree `sim-clock` at 3b5937b
(`git diff origin/main...3b5937b`). I read the cited sections of boundaries, world_model, world_v2, sem_stimuli,
verify_harness, splitting and tile_and_client, and the code in `src/simcore/core/{world,heat,damage,applier,
imagination,grid,frames}.py`, `src/simcore/verify/{splitting,runs}.py` and `src/simcore/adapters/sem/bridge.py`.

**Counts: 3 BLOCKER, 9 SHOULD-FIX, 5 NIT.**

Claims that checked out: four `TEMPORARY(phase1/sim-clock)` markers exist (world, applier, imagination = the three
window markers, plus heat's floor); `World._power_field` iterates `sources.values()` in insertion order; `tick_us` =
100,000 and physics every 5 ticks is tile §6.1; the mid-step replan is in `heat.step` since step 4 (29af1d8);
`same_class_under_refinement` exists; every §14 row id exists in `docs/design/reviews/sem_stimuli/`; 0.5 s is exact
in binary; the note is 2,263 words.

## BLOCKER

**X-B1. sim_core.md::§5.1 "Every field has exactly one writer" contradicts the writers 5a itself builds.**
- §12 moves `imagination.place` into the applier as `imagine`'s stage 2. `place` calls `grid.paint` (writes
  `material`, `original_material`) and `grid.name_region` (writes the region table, which becomes `region_id`).
  §5.1 says damage is the only writer of destruction and the applier "writes no outcome"; §7 says
  `topology_version` bumps on any material or owner change. So `material` has two writers (applier via imagine,
  damage via `destroy`), and the checklist's B40 test "the applier writes no outcome field (the ownership scan)"
  goes red on `imagine`, or gets an exemption that is exactly the special case the rule forbids.
- world_model §10 row 4 (sim-clock) and world_v2 §2.2 put admin `set_material`, "the topology choke point", in this
  step. sim_core.md never mentions it; it is a third writer of `material`.
- The 5a checklist's SEM bullet (unchanged by this diff) reserves `radiant_emitters` "keyed `(writer law, source
  object id, primitive id)`", and sem_stimuli §7.1 calls it "a multi-writer `radiant_emitters` table"; §7.1 also
  allowlists six writers of the body store. Under §5.1 as written, the window must refuse all but one.
- boundaries §6.4 (which §12 says "owns the classification") still says "the applier: strike | cells, through the
  strike law". After §5.1 it doesn't. One contract, two owners, disagreeing.
- **Failure scenario:** the engineer implements "the window refuses a write from anything but the field's declared
  writer" (B40's test); the first `imagine` record raises inside `Simulation.step`, or the engineer adds an
  applier exemption and the ownership scan is weakened to pass.
- Fix (unverified): state the rule per field *and* per kind of writer: either `material`/`region_id` have one
  writer, the `set_material` choke point that damage, imagine and admin all call, or the rule distinguishes outcome
  fields from declared-input fields; say how a multi-writer table (keyed rows) fits; update boundaries §6.4 in the
  same branch.

**X-B2. sim_core.md::§3, §5, §5.1: a strike's load has no defined resolution tick on 4 of every 5 ticks.**
- §3: step 6, physics, runs on physics ticks only (`physics_every` = 5). §5: damage is the second law of the
  physics tuple, "run after heat in each substep". §5.1: the strike is a `Load` "resolved at damage's place in the
  tick", "the frame shows it at the end of the same tick", and its receipt is "carried in that tick's
  `TickReport`".
- A strike applied on a non-physics tick (tick 3) is never resolved on tick 3: damage doesn't run. Either loads queue
  to the next physics tick (then the receipt is not in "that tick's" report, and boundaries §4.2's "a receipt's
  after-frame exists on its apply tick" breaks), or damage's load resolution runs every tick (then it is a
  per-tick law, and §5 has no per-tick slot; sem_stimuli §7.1 asks 5a for one, sim_core never defines it).
- Also unstated: which ticks are physics ticks (`tick % physics_every == 0`, or `== physics_every - 1`); that is
  replay-visible contract.
- **Failure scenario:** two engineers build it two ways; the receipt for an intent with `apply_tick` = 3 appears in
  tick 3's report in one and tick 5's in the other, and replay goldens differ.
- Fix (unverified): state when loads resolve, with what `dt` (thermal degradation needs one; a strike doesn't), and
  which tick's report carries the receipt; name the per-tick slot's interface if that is the answer.

**X-B3. sim_core.md::§4 "The applier is not public" and §12 (the applier's window moves into `step`) break the
SEM bridge, which applies synchronously until `phase1/agents`.**
- `bridge.py::StructureModulator.execute` calls `self._applier.apply(...)` directly under
  `TEMPORARY(phase1/agents)` and returns `destroyed_volume_m3` and `absorbed_j` in the `ModulatorResult` from the
  `Outcome`. sem_stimuli §11.1 puts the outbox (the record path) and D10's `region_parts` split in `phase1/agents`,
  after 5a.
- After 5a, `apply` outside `Simulation.step` has no window (its own marker is removed), and under §5.1 the
  destroyed volume doesn't exist until damage runs. `region_parts(Applier(w), ...)`/`Applier(` appears at 61 sites in
  `src/` and `tests/` (grep), including `tests/test_determinism.py::run`, whose digest test is a gate.
- §4's "`region_parts` hands the membrane an applier only through the record path" names a path that doesn't exist
  until `phase1/agents`.
- **Failure scenario:** 5a lands as written; every `execute("strike", ...)` raises `WindowClosed` (or writes
  nothing), and the determinism and bridge tests go red; or the engineer keeps a public synchronous `apply`,
  contradicting §4.
- Fix (unverified): say what `execute` does between 5a and `phase1/agents` (for example, append a record for the
  next tick and return a pending result, pulling that part of `phase1/agents` into 5a), what its result carries
  without the destroyed volume, and list the call-site migration in the checklist.

## SHOULD-FIX

**X-S1. sim_core.md::§5, §6: the law interface can't carry what §5.1 needs.**
`Changes` holds "the cells destroyed and whether topology changed", but §5.1 builds each strike's receipt (destroyed
volume, and today's `absorbed_j`) "from damage's resolution". With two strikes in one tick, per-load attribution must
come out of `step`; `Changes` has no field for it. `loads` and `sources` are applier-written inputs that laws read,
yet §6's registry declares only "its writer laws", so neither fits it, and `step(state, dt_s, ledger)` doesn't say
where `loads` live in `state`. And §5.1's "the write window refuses a write ... from anything but its declared
writer" names no mechanism: today `CellStore.writing()` yields every channel to whoever opens it, with no caller
identity; construction (`from_scene`) writes every field and isn't a law. Failure: the engineer invents a
per-law `writing(fields=...)` API and a receipt side channel that the next reviewer reads as unreviewed contract.

**X-S2. sim_core.md::§5.1, §11: stage 2 now judges a world the tick's earlier loads haven't touched, and §11's break
list misses the effects.**
Today strikes apply in sequence, so a second strike on a region the first destroyed is refused `REGION_GONE`
(`applier._check_region`). Under §5.1 both pass stage 2 at apply (the region still has cells) and the second
resolves on air as a success with 0 m³. Likewise `imagine` after a strike in the same tick is checked for occupancy
against the uncratered cells. And today the crater exists before the next heat substep; under §5 (damage after heat)
heat runs one step over intact geometry first. These are behaviour and digest changes that §11 doesn't list.

**X-S3. sim_core.md::§7, the overlap cache key `(source id, topology_version)` is both stale and over-invalidated.**
`Applier._ignite` writes `sources[f"fire:{region}"]`, so igniting the crate again with a new radius keeps the id;
with no destruction in between the cache returns the old radius's overlap. Meanwhile `sphere_overlap` depends only
on grid geometry and the source's point and radius; only the `* grid.solid` weighting depends on topology, and a
burning crate destroys cells on many steps, so keying the geometric overlap on `topology_version` recomputes it in
exactly the burning case the cache is meant for. Fix (verified by reading `world.py`, `applier.py`): key the overlap
on the source's value, and the solid weighting on `topology_version`.

**X-S4. sim_core.md::§11 "They hold: the conductance and overlap caches" is a prediction, and the bounding-box
overlap can break it.**
`_power_field` normalises by `weights.sum()` over the whole grid. Summing only the box changes numpy's pairwise
summation grouping. Verified: in 200 random 7×9×11 boxes embedded in 60×60×40 zeros, `box.sum() != full.sum()` in
60. Say the normalisation must sum the full-grid layout (or record the break), rather than asserting identity.

**X-S5. sim_core.md::§4, §5, §10 bar 1: the reversed-order test and bar 1 can't be built with the named API.**
`same_class_under_refinement(outcome, run, factors)` refines one `Run` in time; it takes no second law tuple, so "for
the same outcome class in both orders" needs a different function (`same_class` over orders, or a new one). Both it
and bar 1's time study need the physics step to vary, but `P` is a hashed truth constant and, measured on
`tests/test_determinism.py::SCENE`, `heat.stable_dt` is 239.6 s, 59.9 s and 15.0 s at 0.2, 0.1 and 0.05 m, so
`n = 1` at every grid and only `tick_us`/`physics_every` can change `dt`. The note doesn't say whether a test may
set them, and `from_scene`'s `config` has no type: `World` today requires `limits`, which §4's signature drops
(world_v2 §5 puts limits in hashed config; say so). It also means §8's replan never fires on a shipped scene at
0.5 s; only a constructed material exercises it.

**X-S6. sim_core.md::§2, §4: frame cadence and stamps have two owners and two clocks.**
boundaries §4.2 says frames are "published on change ... not per tick": after each physics step and after a tick
that applied an intent. §4 says "once per tick, at the end of the tick" without superseding §4.2. `CellFrame`
carries `sequence` (`FrameFeed` requires +1) and `time_s` (read by `encoding.snapshot`'s wire field and the bridge's
`SensorReading.timestamp`); the note removes `grid.time_s` but doesn't say what stamps a frame (tick? is sequence
== tick, given construction publishes sequence 0?). §2's "sensors take a required keyword-only clock" adds a second
time source: a sensor reading tick T−1's frame during tick T would stamp T. Fix (unverified): the frame carries its
tick, and readings take their time from the frame.

**X-S7. sim_core.md::§13 "Kinds are ranked 0, 10, 20 and 30" restates tile §3.1 with different numbers.**
tile_and_client §3.1 owns `kind_rank`: join/leave 0, `time` 1, moves 2, `kindle`/`strike`/`douse`/`imagine` 3. The
note gives no mapping, and boundaries §6.1 has more kinds (control, `thought_*`, host commands, `agent_ready`). The
rank is in the ordering key, so it is replay contract with two owners. Link tile §3.1 and amend it there.

**X-S8. sim_core.md::§8, §11, checklist: contradictory instructions for `TURN_SUBSTEPS` and goldens.**
§8: `TURN_SUBSTEPS` "goes". §11: 5a "replaces `TURN_SUBSTEPS` with the new per-physics-step counts". The checklist's
older bullet (not edited): "Replace it with an accuracy floor per step length, with new goldens and
`TURN_SUBSTEPS` updated"; its new §8 sub-bullet: "gone". §8 and §11 say no accuracy floor unless bar 1 fails and no
golden until after 6.0a. `docs/roadmap.md` line 46–47 repeats the accuracy-floor version. Pick one and edit the rest.

**X-S9. checklists.md::"Step 5a", the §4–§12 sub-bullets: most tests don't say how they fail.**
Only B40's import contract ("proven by a planted import") and second-writer test name a planted break. "`WorkCounters`
are identical on replay" passes with counters stuck at 0; it needs exact expected values (for example `physics_steps
== ticks / physics_every`). "Every reader takes its fields from the registry" needs a planted field that must appear
in storage, snapshot and digest. "`prepare` plus kernel equals the unsplit law" has no reference once the law is
split; say where the unsplit oracle lives. "Each digest break is named in the commit" is a review item, not a test.
world_model row 4's "preallocated buffers" and "memory budget with transients" are dropped without a deferral.

## NIT

- **X-N1. sim_core.md::§14:** bare ids are ambiguous: round 1's `fold.md` has an `S2` and an `N3` in each of five
  lens tables (lines 31, 81, 108, 151, 176). Prefix the lens.
- **X-N2. sim_core.md::§6:** "`engine.cells`" is boundaries §2.2's layer name, not a module; the code has
  `simcore/core/grid.py`. Name the file the `FieldSpec` tuple goes in.
- **X-N3. sim_core.md::§5 ↔ §11:** §5 says "§11 says which way it went", and §11 repeats the conditional. From
  `heat.step`, the callback runs after each substep with the same `dt` and its return drives the same recompute, so
  the split alone should be bit-identical (unverified); say so, apart from X-S2's strike reorder.
- **X-N4. sim_core.md::§7:** "measured at about half a burning tick's CPU" has no citation I could find; world_v2 §5
  and the states-of-matter research give 453 ms at max. Cite it.
- **X-N5. sim_core.md::§4:** "refuses records out of order" doesn't say whether it checks before applying any,
  so a bad batch half-applies a tick. Say it validates the whole batch first. Also `World.turn` and its counter are
  left unstated once `advance` goes.

## Verification run

- `heat.stable_dt` on the determinism scene at 0.2, 0.1 and 0.05 m: 239.58, 59.90 and 14.97 s (`.venv/bin/python`,
  `World.from_scene`).
- The pairwise-sum experiment for X-S4: 60 of 200 differ (numpy, seed 0).
- Everything else comes from reading the code and docs at 3b5937b.
