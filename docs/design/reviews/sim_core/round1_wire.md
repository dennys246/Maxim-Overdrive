# Wire integrity: step 5a design (`sim_core.md`, checklist "Step 5a"), at 3b5937b

Diff `origin/main...3b5937b`: sim_core.md (new), checklists 5a, CLAUDE.md flow rule, backlog B40.
`lint_standards.py`: PASS (0). `check_plan.py`: PASS (0).

**Counts: 3 BLOCKER, 9 SHOULD-FIX, 6 NIT.**

## BLOCKER

**W-B1. `sim_core.md::§5.1` "every field has exactly one writer" contradicts §12, `sem_stimuli.md` §7.1 and the code.**
- §12 moves `imagination.place` into the applier as `imagine`'s stage 2. `place` → `_voxelize` → `grid.paint` and
  `name_region` write `material`, integrity (paint) and region ownership. §5.1 says damage is "the only writer of
  `integrity` and of destruction", the write window "refuses a write to a field from anything but its declared
  writer", and the applier "writes no outcome field" (checklist B40 item: the ownership scan holds it).
- Failure: the first `imagine` record raises in the window, or the window exempts the applier and the rule is false. `topology_version` (§7) also counts `imagine` as a
  material/owner change, so §7 assumes a second writer that §5.1 forbids.
- `sem_stimuli.md` §7.1 (ruled, "the rounds stop") asks 5a for "a multi-writer `radiant_emitters` table" and lists
  six writers of the body store (load, motion, the applier, `tissue`, `irradiance`, `contact`). It also has
  `contact.py` write the object "through the solid law's exchange API", which is one law calling another, and §5.1
  forbids. §6's `FieldSpec` has "its writer laws" (plural).
- Fix (unverified): one writer per outcome field; construction and `imagine` declared as non-law writers of
  `material`/region; keyed tables one writer per row key; amend sem_stimuli §7.1 by name; `FieldSpec.writers` typed.

**W-B2. `sim_core.md::§5.1` and §4 put a strike's crater and receipt on a tick where damage doesn't run.**
- Damage is a law (§5). Laws run only in the physics phase "on physics ticks" (§3), which is every 5th tick (T3).
  §5.1 says loads are "the tick's `loads`, a list the applier appends to and damage consumes", and that "the frame
  shows it at the end of the same tick", with the receipt "carried in that tick's `TickReport`".
- Failure: a `strike` with `apply_tick` = 3. Step 1 appends a `Load`, and step 6 doesn't run. One of three things
  happens; the note doesn't say which. (a) The load is dropped, so the strike is silently lost. (b) It carries to
  tick 5, so the receipt lands in tick 5's report and the after-frame is not on the apply tick, breaking
  `boundaries.md` §4.2 ("a receipt's after-frame exists on its apply tick"). (c) Damage runs on every tick, which
  contradicts §3 and §8's planning of `n` per physics step.
-
- Fix (unverified): state whether loads persist and which report carries the receipt; amend boundaries §4.2, or
  resolve loads in sem_stimuli §7.1's "per-tick law slot".

**W-B3. The shipped membrane path, `bridge.StructureModulator.execute` → `Applier.apply`, has no defined behaviour between 5a and `phase1/agents`.**
- Today `execute` calls `Applier.apply` synchronously (`TEMPORARY(phase1/agents)` marker, bridge.py). It returns
  `metadata` with `destroyed_volume_m3` and `absorbed_j` from `damage.strike`.
  `region_parts(applier, frames, region)` takes an `Applier`.
- 5a: "the applier is not public", "every input reaches the world as a record through `step`", and a strike
  "appends a `Load` instead of calling `damage.strike`" (§4, §5.1, §12). The bridge's synchronous apply ends only in
  `phase1/agents` (boundaries §6.4; sem_stimuli §11.1 puts D10 in `phase1/agents`).
- Failure: after 5a, `test_strike_moves_the_integrity_sensor` calls `execute("strike", …)`. That returns before any
  `step`, so there is no destroyed volume to put in `metadata`, and the integrity sensor is unchanged. There is also
  no public `Applier` to pass to `region_parts`, `to_maxim_entity` or the three bridge tests. The checklist only says
  the test "reads the next tick's frame". It doesn't say who calls `step`, how `execute` turns into a record, or what
  `execute` returns (metadata keys removed is a `ModulatorResult` payload change Maxim sees).
- Fix (unverified): §4/§12 states the interim contract. One option: `execute` appends a record to a host-owned
  outbox and returns a pending result with no effect metadata, which pulls a slice of `phase1/agents` forward and
  moves the marker. The other: keep a marked synchronous path and name its `TEMPORARY(phase1/agents)` mechanics.

## SHOULD-FIX

**W-S1. `sim_core.md::§13` and checklist 5a: "Kinds are ranked 0, 10, 20 and 30" conflicts with the rank table's
owner and maps nothing.**
- `tile_and_client.md` §3.1 owns `kind_rank`: join/leave 0, `time` 1, moves 2, `kindle`/`strike`/`douse`/`imagine` 3.
- boundaries §6.1 and sem_stimuli §5 add `speak`, `control`, `thought_cancelled`, `thought_failed`, host commands,
  `agent_ready` and `agent_failed`, with no rank anywhere.
- Failure: two orderings of `(apply_tick, kind_rank, …)` across documents, so a log written from one is "out of order"
  under the other (§4 refuses it). Fix: one owner holds the full kind→rank table. Link it.

**W-S2. The first log is written with a vocabulary `tile_and_client.md` §3.2 says won't exist.** Tile §3.2: `kindle`
"ships with the first log writer (step 5), so no v0 intent log ever exists and the v0-log refusal test is moot". The
5a checklist builds the log writer. Action vocabulary v1 with `kindle` is a 5b item (checklist 5b). Failure: 5a's
logs carry `ignite`, so v0 logs exist and the refusal test is no longer moot. Fix: name 5a's vocabulary version; move v1
into 5a or restore the v0-log refusal test.

**W-S3. The log's own format is not declared.** §13 says 5a "writes" boundaries §6.2/§6.3's record and header. It
doesn't name:
- a `Format` (name, version 0, `held_by_others=True`: bug reports carry logs);
- the byte encoding (JSON lines? c14n-1?);
- the reader that refuses an unknown version;
- a `lint_gates` row for the replay reader, which reads input from outside the repo;
- the record and header golden fixtures boundaries §6.2 requires.

§11 defers "the first replay golden" to after 6.0a, and readers can take that as deferring format fixtures too.
Declared `Format`s are auto-enrolled by `test_formats._declared_formats` (verified by reading it). Failure: a v1 header read by a v0 replay is
undefined. Fix: add these items to §13 and the checklist.

**W-S4. `sim_core.md::§4` "Frames are published once per tick" restates and contradicts the cadence's owner.**
- `boundaries.md` §4.2 says frames are "published on change … not per tick", with the cost (64–80 MB per copy, about
  13–16 GB/s at 20×). `realtime_lanes_coop.md` §2.1 step 4: "a snapshot when cells' version changed". Neither is
  superseded by name.
- Failure: a full-grid copy every tick, four in five unchanged. Fix (unverified): "at most one frame per tick, at its end, when cells changed", and amend boundaries §4.2
  by name.

**W-S5. `sim_core.md::§5.1`: "the strike's receipt (the destroyed volume)" reuses a term whose one home is elsewhere.**
`sem_stimuli.md` §6.2 (D15) makes the receipt `(pid, kind)` in `stimuli.wire`, with kind decided by stage 1 alone,
and says effects like destroyed volume are "logged host-side only". It supersedes boundaries §7.2's measured effect.
Failure: `destroyed_volume_m3` reaches agents in a receipt, the oracle D15 removed. Fix: call `TickReport`'s items host-side "effects" (derived, boundaries §6.2), distinct from
`stimuli.wire.Receipt`.

**W-S6. The per-tick digest has no stated coverage or scheme.**
- §4 puts it in `TickReport`; §6 derives it from `FieldSpec.digested`. The current determinism digest
  (`tests/test_determinism.py::digest`) also covers regions with footprints, `sources`, the clock and the turn.
  None is a registry field; nor is `topology_version`.
- boundaries §6.2 says receipts and refusals are checked against the per-tick digest.
- `digest.py`'s `sha256/c14n-1` is for loaded values, not arrays. sem_stimuli §5's lanes define their own array
  hashing.
- Failure: a replay that diverges only in `sources`, for example in insertion order (§7 changes it), passes a
  field-only digest. Fix: list the digested state, name the prefix or scheme, and say how it relates to sem_stimuli's
  lanes.

**W-S7. `sim_core.md::§6` `FieldSpec` versus the documents it supersedes and serves.**
- It supersedes world_v2 §2.5's `fields.yaml`, but world_v2 §2.5 is unedited, so the two field lists disagree.
  world_v2's has conservation law and ledger, grid and phase, the `required` flag, and "how often".
- sem_stimuli §7.4 needs a `perceivable` flag (default false). sem_stimuli §5's producer closure needs law
  reads/writes, which are on laws, so that part is fine.
- The container vocabulary (cells, zone, pool, body) has no slot for fire_model §10 / fire_solid §0's object,
  segment and coupling tables, which "join this registry" in 6.0a on 5a's line.
- Failure: 6.0a can't declare its tables. Fix: one column list here; world_v2 §2.5 becomes a link.

**W-S8. The composition (§2) and config (§3/§4) omit what `realtime_lanes_coop.md` §2.1/§2.2 put in `Simulation`.**
- Missing: the RNG ("seeded from the log header"; boundaries §6.3 has the run seed slot), the actor-id allocator,
  `day_length_ticks` and `epoch_us`.
- `from_scene(…, config)` doesn't say where `config` comes from: a `data/world/` file (realtime §2.2) needs a
  `Format`, a loader and a gate row. The current `limits=` argument isn't placed.
- Failure: the header's seed slot has no owner type.

**W-S9. `sim_core.md::§13` ("the scene format becomes held by others … an old version migrates") contradicts
`fire_solid.md` §5.2.** fire_solid §5.2 says "scenes are repo-only, so the older version gets a bump and a refusal
test, not a migration", for 6.0b, which lands after 5a. Failure: 6.0b refuses scenes 5a-era bug reports carry. Fix: amend fire_solid §5.2.

**W-S10. `sim_core.md::§5`: the reversed-order test "asks `same_class_under_refinement`".** That function
(`verify/splitting.py`) compares one outcome at `run` refined in time by `factors`. It takes no law list and can't
compare orders. Its `Run.dt_s` is also not a knob `Simulation` exposes (P is a truth constant). Verified by reading
the source. Failure: the bar-3 test as written can't express the comparison. Fix: name the new harness call (for
example `same_class` over a law-order callable) and amend verify_harness §4.

## NIT

- **W-N1.** §2's table cites "`sem_stimuli.md` §11.1's `body_points` container". It is §7.1.
- **W-N2.** CLAUDE.md's new rule, the B40 row and the checklist's B40 item each restate §5.1's contract (B36). The
  verification rule's form, "stated in … its one owner; follow it there", avoids the stale copy.
- **W-N3.** §5: the header should record the law list in order, not as a set. sem_stimuli §5's producers are a sorted
  set, and a reversed-order log would pass a set comparison.
- **W-N4.** realtime_lanes_coop §2.1 says "`World.advance(seconds)` stays as the physics call". §2 deletes it, so
  supersede it by name.
- **W-N5.** §4: does "`step` refuses" mean an exception or a refusal code? Also unstated: the physics-tick phase
  (`tick % physics_every == 0`, the interval ending at T, realtime §2.1), so link it.
- **W-N6.** §6: name the regeneration command for `docs/generated/fields.md`, and the line-ending rule the
  byte-for-byte test assumes. Also, §8 restates splitting §6 rule 3 but drops its "safety 0.9".
  §2 links world_v2 §5 only for sensors; `Frame.time_s` and `snapshot()["time_s"]` follow it too (no client reader).

## What I checked

| Contract | Owner | Producers / consumers read | Result |
|---|---|---|---|
| `kind_rank` values | tile §3.1 | sim_core §13, checklist 5a | W-S1 conflict |
| Log header slots | boundaries §6.3, sem_stimuli §5 | sim_core §3/§5/§13, checklist 5a SEM item | W-N3; lanes and records reserved in checklist only (OK) |
| Log format version, reader, gate, fixtures | CLAUDE.md formats rule, boundaries §6.2 | `schema.Format`, `test_formats._declared_formats` | W-S3 |
| Action vocabulary version | tile §3.2 | checklist 5a/5b | W-S2 |
| `TickReport`, receipts | sim_core §4, sem_stimuli §6.2, boundaries §7.2 | `applier.Outcome`, `bridge._from`, `test_sem_bridge` | W-B2, W-B3, W-S5 |
| Strike resolution | sim_core §5.1 | `applier._strike`, `damage.strike`, heat `on_substep` | W-B2 |
| One writer per field | sim_core §5.1 | `imagination._voxelize`, `grid.paint/destroy`, sem_stimuli §7.1 | W-B1 |
| Frame cadence | boundaries §4.2 | `world._publish`, `frames`, realtime §2.1 | W-S4 |
| Per-tick digest | (none) | `test_determinism.digest`, `core/digest.py`, sem_stimuli §5 | W-S6 |
| Field registry columns, artifact | sim_core §6 | world_v2 §2.5, sem_stimuli §7.4, fire_solid §0, fire_model §10 | W-S7, W-N6 |
| #32 formats: `held_by_others`, migrations, refusals | `schema.Format`, `SCENE` | sim_core §13, fire_solid §5.2 | W-S9 |
| Refusal codes append-only, classification | `core/refusals.py` | sim_core §13, checklist 3b(b) item | consistent |
| Truth constants, config, RNG | tile §6.1, realtime §2.1–2.2 | sim_core §2–§4 | W-S8 |
| Harness calls | verify_harness §4 | `verify/splitting.py`, `agreement.py` | W-S10 |
| Time stamp after `grid.time_s` goes | world_v2 §5 | `frames.CellFrame.time_s`, `encoding.snapshot`, bridge timestamp, client `.gd` | W-N6 |
| Citations | — | splitting §6, verify_harness §4/§7, world_model §10, fire_solid §0 | W-N1 |
