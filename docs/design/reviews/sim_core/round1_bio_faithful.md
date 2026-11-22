# Step 5a design review: Bio-faithful integration

**Under review:** `docs/design/sim_core.md` and the Step 5a checklist, `phase1/sim-clock` at `3b5937b`
(`git diff origin/main...3b5937b`). **Maxim** read only at `origin/main` `4b9641d9` (no fetch, no working tree).

**Counts:** 2 BLOCKER, 4 SHOULD-FIX, 3 NIT.

**The short version.** The clock itself is right for NPCs: an integer tick, no float accumulation, no wall time in
`WorkCounters` or the digest. One frame per tick at step 8 fits `sem_stimuli.md` §4.1, where step 4 builds body frames
from the held fields of the previous tick's frame. Two things break. First, §5.1 (added in `3b5937b`) has strikes
resolve inside a law that runs only on physics ticks. Second, §5.1's one-writer rule contradicts seams that the same
checklist item tells 5a to build. The fold-row list in §14 also has an id that doesn't exist.

---

## BLOCKER

### BF-5a-B1. `sim_core.md::§5.1` vs `::§3`: a strike's load waits for a physics tick that the contract doesn't wait for

**What is true.** §3 runs step 6 (physics) "on physics ticks", with `physics_every` = 5 (T3). §5 puts damage in the
law tuple `(heat, damage)`, run "after heat in each substep", so it runs only in step 6. §5.1 says a strike is a
`Load` that the applier appends to "the tick's `loads`" in step 1, and that damage consumes it. It also says "the
frame shows it at the end of the same tick", and that the receipt is "carried in that tick's `TickReport`".

**Failure scenario.** An NPC's strike applies at tick 101. That is not a physics tick, since 100 and 105 are. Damage
doesn't run at 101, so the contract allows two readings, and both are wrong:
- **The load is dropped** at the end of tick 101 ("the tick's loads"). The strike is lost silently. Stage 1 still
  gives an `accepted` receipt (D15), so the NPC is told its strike went through, and the world never shows it.
- **The load is carried to tick 105.** Then "the end of the same tick" and "that tick's `TickReport`" are false on
  four ticks in five. A strike's effect lags by up to 0.4 s. A pending-load list then exists that §2's part table
  has no home for. A save at tick 103 (step 9) loses it, or reloads without it, and a save anywhere no longer reloads
  bit-identical (`sem_stimuli.md` §5's save rule).

Two more things are unstated. Which substep consumes the load: the first, with §8's replan afterwards? And what is
the order key across carried ticks: `(apply_tick, record key)`?

An NPC learns from cause and effect. A strike whose effect lands 0 to 4 ticks late, depending on the tick's phase
against `physics_every`, gives the effect a timing that varies with no cause the NPC could sense.

**Fix (unverified), the owner's choice:**
- (a) damage's load resolution runs every tick. This is the "per-tick law slot" `sem_stimuli.md` §7.1 already asks
  this note for. Thermal degradation keeps running on physics substeps.
- (b) loads are world state in a named part with a save entry, resolved at the next physics step. §5.1 then states
  the latency and the order key, and the receipt tick is the resolving tick.

Either way, delete "the end of the same tick" unless it holds.

### BF-5a-B2. `sim_core.md::§5.1` "every field has exactly one writer" vs the seams 5a must build (`sem_stimuli.md` §7.1)

**What is true.**
- §5.1 says a law's `writes` is exclusive, and that the window "refuses a write to a field from anything but its
  declared writer". B40's checklist line builds the check that refuses a second writer.
- The same Step 5a checklist item (the SEM 5a half, DP-F-N1) tells 5a to build "a multi-writer `radiant_emitters`
  table, each row keyed `(writer law, …)`" (`sem_stimuli.md:388-391`).
- `sem_stimuli.md` §7.1 also has `contact.py` write "the object through the solid law's exchange API". That is a
  second path into `temperature`, which §5.1 gives to heat alone. And the store's writers are "load, motion, the
  applier, `tissue.py`, `irradiance.py`, `contact.py`", several writers of `body_points` fields, the applier among them.
- `sim_core.md` §6's `FieldSpec` declares "its writer laws", plural, which contradicts §5.1 in the same note.

**Failure scenario.** 5a builds the single-writer window check (B40) and the multi-writer `radiant_emitters` seam in
one PR. One of them has to give, and the likely result is an exemption, a band-aid. Later, when contact lands, the
B40 test refuses `contact.py`'s exchange write to object temperature. Then either the test is loosened, or contact is
redesigned under time pressure. Contact is the mechanism T16 and the pain path (D14) depend on. Two documents now
state contradicting contracts for the same writes, against one owner per contract (B36).

**Fix (unverified).** Pick one owner and supersede the other by name. §5.1's own pattern works: contact and emitters
declare inputs (an exchange flux heat consumes, an emitter row irradiance consumes), and heat stays the one writer of
`temperature`. Then `radiant_emitters` is an input table appended by sources, not written by laws, and §5.1 says so
explicitly, along with which body-store fields the applier may set (pose is an input; tissue is an outcome). §6's
"writer laws" becomes "writer law".

---

## SHOULD-FIX

### BF-5a-S1. `sim_core.md::§5.1`, `::§4` (`TickReport`): the strike's "receipt" is named like `sem_stimuli` §6.2's `Receipt` and carries the oracle D15 removes

**What is true.** §5.1 says "the strike's receipt (the destroyed volume) is built from damage's resolution and carried
in that tick's `TickReport`". §4 lists `TickReport`'s "receipts and refusals". `sem_stimuli.md` §6.2 defines the
receipt as `(pid, kind)`, with v1 kinds decided by stage 1 alone (D15). Whether the target was hit "is logged
host-side only". Today `applier.py:126` returns `destroyed_volume_m3` and `absorbed_j`, and the bridge
(`bridge.py:182-186`) hands them to Maxim. That is the measured-effect path D15 supersedes.

**Failure scenario.** `phase1/agents` builds `BoundFrame.receipts` from `TickReport.receipts`, because that is what
the field is called. A destroyed volume of zero then tells the NPC "missed". That is the existence and footprint
oracle D15 removes, and T11 only catches it if its sweep reaches this path. In 5a itself, `tests/test_sem_bridge.py`
"moves to reading the next tick's frame". If the bridge's `execute` keeps returning a destroyed volume, now read from
`TickReport`, the oracle survives the refactor.

**Fix (unverified).** Call it the strike's *resolution* (a host-side log value), not a receipt. Say that `TickReport`
is host-only, that no stimulus or wire path reads it, and that `Receipt` stays `sem_stimuli.md` §6.2's. Have 5a's
bridge stop returning the destroyed volume or `absorbed_j`, or say why it still may until D10 moves the bridge.

### BF-5a-S2. `sim_core.md::§14`: the fold-row list is wrong in one row and incomplete in another

I checked every id against `docs/design/reviews/sem_stimuli/{,delta1/,delta2/,final/}fold.md`:
- **"N3" under Final doesn't exist.** `final/fold.md` has no N3 row. The id comes from the checklist's lane list
  ("A3-S5, W11, DP3-N2, S-F3, N3"). From its context (lane bytes `(npc_key, site index, value)`) it is delta 2's
  **A3-N3** ("`site_id` is the index within the row's site set", §4.2, §5). A reviewer can't set a status on a row
  that isn't there, so it stays open forever, or gets marked against the wrong N3. Round 1 has five N3 rows and delta
  1 has one, none of them about 5a.
- **"S2" is ambiguous.** Round 1 has five S2 rows. The 5a one is Executor S2 (`fold.md:31`). Qualify it by lens.
- **Missing: Final Architecture N-S2.** 5a's `imagine` kind makes `intents` import `imagination`, which opens
  `AGENTS_SURFACE`. Its fix says "record the choice in the 5a and agents checklist items". The owner accepted
  `AGENTS_SURFACE` = `stimuli.wire`, `checks`, `readonly`, and §12 moves `place` under the applier. That is exactly
  the change N-S2 is about, and the 5a reviewer should set its status.
- **A3-S5 has rows in both delta 2 and Final** (both tagged 5a), but §14 lists only delta 2. A-S10 has rows in
  round 1, delta 1 and delta 2, and §14 lists only delta 1.
- **The count is 19 ids, not 20.** With the corrections it is 20 (N3 → A3-N3, plus N-S2), with duplicates named.

**Fix (verified by reading the fold tables):** Delta 2 gets A3-N3 instead of Final's N3, Final gets N-S2, and each id
is qualified by its lens where it repeats. Fix the checklist's "N3" too.

### BF-5a-S3. `sim_core.md::§5`, `::§13`: the per-tick law slot that `sem_stimuli.md` §7.1 hands this note is missing, so lane producers can miss body laws

**What is true.** `sem_stimuli.md` §7.1 says "5a's composition note gets three seams: a per-tick law slot; the
two-rate contact exchange …; the `body_points` container and … `radiant_emitters`". `sim_core.md` doesn't define
them. §2 reserves a body-state slot (and cites §11.1, where §7.1 is meant). §3 reserves D10 steps 2–5 and 7 as no-op
seams. §5's law object has no cadence: every law runs in step 6. `sem_stimuli.md` §5 keys row lanes by `producers`,
"the transitive closure over every law's declared reads and writes", and the header records "each law's version".

**Failure scenario.** Tissue, contact and irradiance run every tick at step 3, outside §5's list, because the list
has no per-tick cadence. A3-S5's closure is computed over §5's list, so it never sees `irradiance.py`. That is A3-S5's
own scenario: an occluder fix loads an agent home silently under D13. The header also omits those laws' versions.

**Fix (unverified).** Give the law contract a cadence (`per_tick` or `per_physics_step`) and a D10 step, keep one
tuple with one registry, and compute the closure and header versions over all of it. Name the three seams in §2 or
§5 as reserved, even if empty in 5a.

### BF-5a-S4. `sim_core.md::§2`, `::§3`, `::§4`: what a frame says about time is unstated

**What is true.** `frames.py:39-40,69`: `CellFrame` stores `sequence` and a float `time_s` copied from `grid.time_s`.
§2 removes `grid.time_s` and §3 says "nothing stores time as a float", but neither says what a frame carries.
`BodyFrame.fields_sequence` (sem_stimuli §4.2) names "the published Frame its held fields came from". The bridge
stamps `SensorReading.timestamp=frame.time_s` (`bridge.py:89`).

**Failure scenario.** Construction publishes frame 0 (`World` does today), so tick T's end-of-tick frame is sequence
T+1. One lane implementer writes `fields_sequence = tick - 1` and another `= tick`. Body frames are then digested
against different frames on live and replay, a red lane whose cause is bookkeeping. Or `CellFrame.time_s` stays a
stored float, which is the accumulation §3 forbids, at the one place an NPC's timestamp comes from.

**Fix (unverified).** A frame carries `tick: int`. `time_s` is a derived property from `tick * tick_us`. The note
states the relation between `sequence` and `tick`, or replaces `sequence` with `tick`.

---

## NIT

- **BF-5a-N1, `sim_core.md::§3`: the clock's origin and Maxim.** World time at tick 0 is 0.0 s. At Maxim `origin/main`
  `4b9641d9`, `attention/salience_map.py:227` (`current_time or time.time()`) and `salience/salience_network.py:222`
  still turn 0.0 into the wall clock. That is OD-I1 (#1684), already a Phase 3 row (`roadmap.md:128`), so nothing new
  needs filing. §3 should state the origin and cite OD-I1 and OD-A2 (machinery clock), so `phase1/agents` doesn't
  "fix" it with a host-side epoch offset, which would be a workaround in this repo. (Verified: read at `origin/main`.)
- **BF-5a-N2, `sim_core.md::§2` table:** "`sem_stimuli.md` §11.1's `body_points` container" should cite §7.1, where the
  container is defined. §11.1 only assigns it to a step.
- **BF-5a-N3, `sim_core.md::§4`:** "a strike and a read inside one tick see the frame from before the tick" is right,
  and matches D10. State what follows from it for agents: with `L_us ≥ 1` (sem_stimuli §4.1), an NPC's intent
  observed at T applies at T+1 or later, and its effect is first in the frame of tick T+1 at the earliest. Under B1's
  option (b), the earliest is the next physics tick. T9 and T16 timing tests need that number.

---

## Checked and found sound

- **The world-time machinery:** an integer tick, `dt` derived per physics step from integer µs, no wall time in
  `TickReport`, `WorkCounters` "never wall time", and the clock owned only by `Simulation.step`. Nothing in 5a reads
  a wall clock.
- **Frames per tick against cognition cadence:** frames are per tick whatever the cognition divisor. That fits
  `sem_stimuli.md` §4.2 (BodyFrame per tick, independent of delivery) and T9. The 0.5 s physics step makes cell
  fields a staircase at 10 Hz. Rows read tissue, which integrates against held fields (§4.1 step 3), so no receptor
  sees the steps directly. That is fine as long as no row differentiates a raw cell field.
- **Reservations (§5's header slots and `join`/`leave`/`agent_ready`/`agent_failed`; recursive `_core_modules` with
  `as_packages = false`):** carried by the checklist item, which cites `sem_stimuli.md` §11.1 as A-S10 required. Apart
  from S3 above, linking rather than restating is correct under B36.
- **Maxim changes:** none new from 5a. The clock items (OD-A2, OD-A4, OD-I1; M5–M8) are already under Phase 3.
