# Step 5a design review: Determinism and replay

Reviewed: `docs/design/sim_core.md` and the Step 5a checklist additions, `phase1/sim-clock` at 3b5937b
(`git diff origin/main...3b5937b`). Read against: CLAUDE.md, `docs/code_review.md`, `boundaries.md` §6–§7,
`sem_stimuli.md` §4.1 and §5, `realtime_lanes_coop.md` §2.1–§2.2, `tile_and_client.md` §3.2 and §6.1,
`research/physics_spike/splitting.md` §6–§7, and the code the note changes (`core/world.py`, `heat.py`,
`damage.py`, `applier.py`, `frames.py`, `digest.py`, `tests/test_determinism.py`).

**Counts: 2 BLOCKER, 8 SHOULD-FIX, 4 NIT.**

---

## BLOCKER

### D-B1. `sim_core.md` §3, §4, §5.1: when a strike's load is resolved has no single answer

§3 runs physics (the law list) only on physics ticks: every 5th tick, step 6. §5.1 says damage is a law in that
list, and that a strike becomes a `Load` that damage consumes "at damage's place in the tick". §5.1 and §4 also
say the frame shows the crater "at the end of the same tick", and that the receipt comes from "that tick's
`TickReport`". All three can't hold together.

- **Failure scenario.** A strike is applied at tick 7. Damage next runs at tick 10. One implementation holds the
  load for three ticks: the crater appears at tick 10 and the receipt arrives in tick 10's report. Another runs
  damage's load resolution on every tick: the crater appears at tick 7. Both are deterministic, but they produce
  different digests, different receipts and different agent percepts. Whichever is built, the other reading of the
  note says it is wrong, so replay goldens and `test_sem_bridge.py`'s strike-then-read rest on nothing.
- **Related gaps.**
  - The note doesn't say which substep of a physics step consumes the loads (before heat's first substep, or after
    it), or whether a load comes before or after `thermal_degrade` in that substep. Each choice gives different bits.
  - If loads wait across ticks, the pending `loads` list is world state, but the registry's containers (cells, zone,
    pool, body) have no place for it. It would then sit outside the per-tick digest and the save, so a save taken
    at tick 8 and reloaded loses the strike.
- **Fix (unverified).** State one rule:
  - either damage resolves loads on every tick, and §3 names that as part of step 1 or a step of its own;
  - or loads wait for the next physics tick, and §4 and §5.1 say the crater and the receipt arrive then.
  Also name the substep and its order against thermal degradation. Then register `loads` as digested, saved state.

### D-B2. `sim_core.md` §4, §6, §10 bar 4: the per-tick digest has no stated contents and no byte form

§4 puts "the per-tick digest" in `TickReport`, and §6 has the registry declare which fields are "digested". Nothing
names the rest of the state that decides the next tick:
- the heat-source table;
- pending loads (D-B1);
- the region table and footprints, `region_id` and `topology_version`;
- the tick.

None of these is a registry field in a cells, zone, pool or body container. Today's hand-rolled digest
(`tests/test_determinism.py::digest`) hashes sources, regions and the clock for exactly this reason. Nothing says
either whether the digest covers the derived values that `boundaries.md` §6.2 says replay "checks against a
per-tick digest" (receipts, refusals), or `WorkCounters`.

There is no byte form either. `core/digest.py`'s c14n-1 refuses numpy values. `sem_stimuli.md` §5 defines a form
for its lanes (dtype, shape, little-endian bytes, length-prefixed), but not for the world digest. And "Regions in
insertion order", which today's test hashes, conflicts with §7's sorted-key rule.

- **Failure scenario.** `HeatSource` allows `power_w == 0`, so an ignite at 0 W adds a source and changes no cell.
  Suppose a replay drops that record: say a refusal is recomputed differently after a validator change.
  - The registry-based digest matches on every tick, because no cell differs.
  - Ten ticks later the log's `extinguish` is applied in one run and refused in the other.
  - Bar 4 passed on the ticks where the divergence began, so the first bad tick it names is wrong.
  This is `splitting.md` §7 hazard 5 (the digest must include the latches) again, one level up.
- **Fix (unverified).** In one owner (this note, or `boundaries.md` §6.2 with a link from here), name:
  - the digest's members: the digested registry fields, sources in sorted key order, loads in key order, regions in
    sorted name order, `topology_version`, the tick, the tick's receipts and refusals, and whether `WorkCounters`
    are in it;
  - its byte form: dtype, shape, C order, little-endian, length-prefixed, with a scheme prefix like
    `sha256/c14n-1`.

---

## SHOULD-FIX

### D-S1. `sim_core.md` §7, §11 ("They hold: … overlap caches"): computing over the bounding box is not bit-identical — verified

§7 computes each source's overlap over its bounding box instead of the grid. `World._power_field` then normalises
with `weights.sum()`. Numpy's pairwise summation groups terms by position, so summing a block embedded in zeros
does not give the same bits as summing the block alone.

- **Measured** (`.venv` in this worktree): a random 7³ block placed in a 40×40×30 grid of zeros gave
  `full.sum() != box.sum()` in 81 of 200 trials.
- **Consequence.** `power_w * weights / weights.sum()` changes bits. The checklist test ("the conductance and
  overlap caches equal the uncached path bit for bit") fails if the uncached path is today's whole-grid code, or
  passes only because the reference was changed too.
- **Fix (unverified).** Either list "overlap over the bounding box" among §11's breaks, or define the reference as
  the bounding-box computation without a cache. Then the cache claim holds and the bounding-box change is recorded
  as a break.

### D-S2. `sim_core.md` §7: the overlap cache key `(source id, topology_version)` goes stale

The applier keys fires as `f"fire:{region}"` (`applier.py::_ignite`), and a second ignite on one region replaces
the source under the same id, possibly with a different `radius_m`. Tile's `kindle` also varies the point. Neither
changes the topology, so the cache hit returns the old sphere.

- **Effect.** Replay still matches, because it is deterministic, but the cached path differs from the uncached
  path, and the physics is wrong.
- **Fix (unverified).** Key the cache on the source's value (point and radius) or on a revision number that every
  write to the source bumps. Add a test that re-ignites with a different radius.

### D-S3. `sim_core.md` §7, §11 and the checklist §7 line: the sorted-order guard can't fail with two sources — verified

IEEE addition is commutative. With `power` starting at zero, `0+a+b` equals `0+b+a` bit for bit.

- **Measured:** two sources gave identical arrays in both orders. Three sources gave two distinct results over the
  six orders.
- **Consequences.**
  - §11's "sorted-key power accumulation breaks digests wherever insertion order differed" is true only with three
    or more overlapping sources. No shipped scenario has more than one fire per region, and the determinism
    scenario has one fire.
  - The checklist's "sources accumulate in sorted key order" test, written the natural way (ignite the wall, then
    the crate), can't go red. A test that can't fail is a BLOCKER under the charter's Executor lens, so this must
    be fixed when the test is written.
- **Fix (verified for the arithmetic).** The test needs three or more overlapping sources inserted out of sorted
  order, and a planted insertion-order loop that turns it red. Move
  `test_runs_in_processes_with_different_hash_seeds_agree` onto the `Simulation.step` path with that scene.

### D-S4. `sim_core.md` §3 ("never accumulated") against §8's replan

§3 derives a law's `dt` from integer microseconds and says "never accumulated". §8's replan keeps
`heat.step`'s mechanism: `remaining = seconds - elapsed`, where `elapsed` is a float running sum, plus
`dt = min(dt, seconds - elapsed)`.

- **Why it matters.** The replanned count `ceil(remaining / bound)` depends on rounding in that sum. That is
  `splitting.md` §7 hazard 4, the one the integer clock was meant to remove. The count goes into `WorkCounters` and
  the digest.
- It is deterministic on one machine, so this is SHOULD-FIX, not BLOCKER. But the note claims a property it
  doesn't have.
- **Fix (unverified).** Compute what remains without a running sum: `remaining = (planned - taken) * dt`, one
  rounding from integers and the current `dt`. Or state the exception in §3 and record the hazard.

### D-S5. `sim_core.md` §3, §4: the tick's semantics and the physics interval are unstated

The note doesn't say:
- whether `step` runs tick `T` and then sets `tick = T + 1`, or increments first;
- whether tick 0 is a physics tick. Under `realtime_lanes_coop.md` §2.1's `tick % physics_every == 0` it is, and
  it covers (−5, 0], half a second before the world existed;
- what interval a physics step covers (`tile_and_client.md` §3.2 says (t − 5, t]);
- how a source applied partway through an interval is integrated. Today a source present at the physics tick heats
  for the whole P: an ignite at tick 66 and one at tick 69 give identical bits. Tile's pilot gets
  "P × 0.1 s per overlapping tick".

So the same kind of input has two integration rules in two documents. Each choice is an off-by-one that changes
every golden and the tile script's timings.

- **Fix (unverified).** State all four here, as contract, and make sources follow tile's per-tick overlap rule or
  say why they don't.

### D-S6. `sim_core.md` §4: frame identity and once-per-tick publication

- **Publication is tied to the window.** `World` publishes on every window close (`grid.on_close`), and
  `Frame.sequence` counts publications. §4's once-per-tick rule needs publication separated from the window: the
  apply phase and the physics phase would each close one, and a construction-time `imagine` would add another.
- **Frame ids depend on window count.** Otherwise frame ids depend on how many windows opened, and those ids are
  carried in receipts (`boundaries.md` §7.2, "before and after frame ids") and in `BodyFrame.fields_sequence`. A
  save that doesn't persist the counter then gives different ids on reload.
- **A float time remains.** `CellFrame.time_s` and `Observation.time_s` are floats, against §3's "nothing stores
  time as a float", and §2 doesn't list them.
- **Fix (unverified).**
  - Publish from `Simulation.step` only, as its step 8.
  - Make the frame's id the tick (or a stated function of it).
  - Replace `time_s` with the tick in the frame, with seconds derived where an observer asks for them.

### D-S7. `sim_core.md` §11: the list of breaks is incomplete, and nothing records the bits until 6.0a

- **Missing breaks.** §11 leaves out several changes that alter the arithmetic or the order:
  - the strike moving from immediate application (before the next `advance`) to a load resolved inside damage;
  - once-per-tick publication;
  - the overlap computed over the bounding box (D-S1);
  - the change in when an ignite takes effect (D-S5).
- **No golden before 6.0a.** 5a commits no golden digest, and records the first one "after 6.0a lands". Bar 4 is
  replay against run, which checks self-consistency, not regression. Between 5a and 6.0a any change to the physics
  bits is invisible, so `boundaries.md` §6.3's "goldens change only on a recorded change" has nothing to act on.
  Replacing `TURN_SUBSTEPS` pins counts, not bits.
- **Fix (unverified).** Commit a replay golden (a log and its per-tick digest chain) in 5a itself, and regenerate
  it in 6.0a with a commit that says so. List every break above.

### D-S8. `sim_core.md` §13: kind ranks without the kinds

"Kinds are ranked 0, 10, 20 and 30" doesn't say which kind holds which rank. `boundaries.md` §6.2 fixes only
"controls and joins rank before intents". `kind_rank` is the second field of the ordering key, so its assignment
decides the order records apply in within a tick.

- **Failure scenario.** One build ranks `imagine` before `intent`, another ranks it after. A strike and an imagined
  wall arriving in the same tick then give different worlds, and both logs claim the same format.
- **Fix (unverified).** Name the four kinds and their ranks in the ordering key's owner.

---

## NIT

### D-N1. `sim_core.md` §5, §6: the type of `reads` and `writes`

If `reads` and `writes` are a `frozenset` of strings, anything that iterates them depends on the hash seed:
generating `docs/generated/fields.md`, `sem_stimuli.md` §5's producer closure, and the header. Require sorted
tuples, or sorted iteration.

### D-N2. `sim_core.md` §5: the header should record the law order

The header should record the law tuple's order, not only each law's name and version. A log recorded under the
reversed tuple must then be refused by the default build, not replayed into a divergence.

### D-N3. `sim_core.md` §7: string source ids against integer ordering keys

Source ids are strings (`fire:crate`), sorted by code point, while `boundaries.md` §6.2 says "ordering keys are
integers (D-N2)". Say which rule governs collection order, or give sources integer ids.

### D-N4. `sim_core.md` §3, §4: what `apply_us` does in 5a

State that `apply_us` only orders records in 5a. Every record applies at step 1, and time below the tick reaches no
law.

---

## Checked and sound

- An integer tick, with world microseconds as `tick * tick_us` and `P_s = 0.5` exact. Hashing the truth constants is
  right.
- One owner of time (`Simulation.step`).
- The fixed law tuple, with no discovery.
- `step` refusing records for another tick and records out of key order.
- Exact integer `WorkCounters`, kept separate from wall time.
- Read-before-the-tick semantics for observers.
- No wall clock or RNG introduced.

The mid-step replan is a deterministic function of state: it is triggered by `Changes` and bounded by
`stable_dt(grid)` after the change. Its only defect is D-S4.
