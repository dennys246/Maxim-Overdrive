# Delta round 1, step 5a design: Wire integrity and Determinism and replay

Diff: `git diff 3b5937b..99917fb` (`phase1/sim-clock`). I also read the owners the fold now links to:
`tile_and_client.md` §3.1, §3.2, §4 and §6.1; `sem_stimuli.md` §4.1, §5 and §7.1; `boundaries.md` §4.2 and §6.2–§6.4;
`realtime_lanes_coop.md` §2.1; and `world_v2.md` §2.5. The code I read is `world.py::sphere_overlap`, `HeatSource`
and `applier.py::_ignite`. `lint_standards.py` passes (0 findings), and so does `check_plan.py`.

**Counts.** Round-1 statuses: 24 fixed, 7 open, 1 deferred, 1 rejected. New findings: 2 BLOCKER, 5 SHOULD-FIX, 5 NIT.

## Status of round-1 findings (set from the tree)

| Id | Status | Basis |
|---|---|---|
| W-B1 | fixed | §5.1 declares ordered writers; `Topology` applies requests; §6's `writers` column; sem §7.1 edited |
| W-B2 | **open** | §5.1 answers the question, but §5's cadence definition contradicts it (N-B2) |
| W-B3 | fixed (author's ruling R3) | §13 keeps the marked synchronous path and drops the effect metadata. See N-N3 |
| W-S1 | fixed | §14 links tile §3.1. That table lacks 5a's kinds (N-S2) |
| W-S2 | **open** | The ruling is v0, but `tile_and_client.md` §3.2 still says "no v0 intent log ever exists and the v0-log refusal test is moot", and that kindle "ships with the first log writer". §14 cites that section as if it agreed. The owner was not amended |
| W-S3 | fixed | §14 gives the `Format`, the reader's refusal, the gate row and the fixtures. The digest chain is not covered (N-S5) |
| W-S4 | **open** | The fold says A-B3 amended `boundaries.md` §4.2. It didn't: the diff touches only §6.4. N-S3 |
| W-S5 | fixed | §4's effects are host-side, and a receipt is sem §6.2's |
| W-S6 | **open** | Members and scheme name are given in §9. The byte form admits incompatible implementations, the source key is not hashed, and the relation to sem §5's lanes is unstated (N-B1, N-S1) |
| W-S7 | **open** | `world_v2.md` §2.5 still holds its own column list under "Superseded by…", so there are two lists. §6 says it "carries" world_v2's columns but drops "grid (rig cell, fixed metres or zone) and phase" |
| W-S8 | fixed | `SimConfig` and the seed slot are placed, and the actor allocator goes to 5b. `day_length_ticks` and `epoch_us` are unplaced, but nothing reads them in 5a |
| W-S9 | fixed | The scene is recorded by digest and stays repo-only |
| W-S10 | fixed | Bar 3 compares the two orders directly, with a planted pair |
| W-N1 | fixed | |
| W-N2 | fixed | CLAUDE.md links §5.1 |
| W-N3 | fixed | §5: tuple order recorded, a reordered log refused |
| W-N4 | rejected (author; reason accepted) | `realtime_lanes_coop.md` is superseded wholesale (its banner), so it is not edited. But see N-N1 |
| W-N5 | fixed | `ValueError`; the phase is stated in §3 |
| W-N6 | deferred | The checklist says to "name the regeneration command, LF endings" but names neither. It is a mechanism. Trigger: the 5a build's `fields.md` byte-for-byte test |
| D-B1 | **open** | As W-B2 (N-B2) |
| D-B2 | **open** | §9 lists members. The byte form is incomplete (N-B1), and §3's overlap rule adds carried state that is not a member (N-S1) |
| D-S1 | fixed | §7 states the 1/64 condition. One more condition is needed (N-N2) |
| D-S2 | fixed | §7 keys the cache on the source's value; the checklist has the re-ignite test |
| D-S3 | fixed | The checklist has three sources and a planted loop; §12 narrows the break |
| D-S4 | fixed | §8 replans from counts |
| D-S5 | fixed | §3 gives tick semantics, `T > 0`, the interval and tick-overlap integration. New gaps: N-S1, N-S4 |
| D-S6 | fixed | `FrameFeed` is written only by `step`'s last step; frames carry the tick |
| D-S7 | fixed | §12 lists the breaks; the golden is committed in 5a |
| D-S8 | fixed | Linked to tile §3.1 (but N-S2) |
| D-N1–D-N4 | fixed | §5 sorted tuples; §5 header order; §7 code-point keys; §3 `apply_us` |

## BLOCKER

### N-B1. `sim_core.md::§9`: the `sha256/raw-1` byte form is self-contradictory and under-specified

The defects:

- **Flat or composed?** "Each member is written as … the C-order little-endian bytes" describes one SHA-256 over a
  flat byte stream. "A field's bytes are rehashed only on a tick whose window wrote it … an unchanged field reuses its
  last digest" can only work if the tick digest is a hash of per-member digests: SHA-256 state can't splice a cached
  sub-hash into a flat stream. The §9 cost figure (physics ticks only) assumes reuse. Both readings are valid
  implementations of the text, and they never agree on a single bit.
- **ndim is not written.** Without it, the shape words and the data bytes have no unambiguous boundary, so the stream
  is not uniquely decodable.
- **Encodings are unstated:**
  - the dtype's encoding (a string such as `<f8`? its length prefix?);
  - the name prefix's width and endianness;
  - how non-array members are written: string source keys, a region's footprint (a box or a mask?), refusal codes
    and effect values.
- **The source key is not hashed.** "`sources`, sorted by key (point, radius and power as f64)" hashes the values
  only. Two runs whose sources are equal in value but keyed `fire:crate` and `fire:wall` digest equal on that tick,
  and a later `douse` on `crate` diverges them.
- **Failure.** 5a commits the first replay golden under one reading (§12). `engine.host`'s replay reader, or 6.0a's
  regeneration, implements the other. Bar 4 then goes red on every tick with no physics change, or a key-only
  divergence passes. The scheme is versioned in a format held by others, so this is a contract defect.
- **Fix (unverified).** Tick digest = SHA-256 over: the scheme tag; tick and `topology_version` as u64 LE; then per
  member the u64-length-prefixed UTF-8 name, the u64-prefixed numpy `dtype.str`, u64 ndim, the shape as u64s, and the
  member's own SHA-256 (which makes reuse legal). Strings are u64 length plus UTF-8; refusals are their integer codes
  from `refusals.py`. Source keys are hashed.

### N-B2. `sim_core.md::§5` against `§5.1`: when loads resolve is stated twice, differently, and the topology batch is undefined

- §5 defines `per_tick` as "in the per-tick slot, D10 step 1, **after the records**", and puts `damage.loads` at that
  cadence. §5.1 (R2 as the owner confirmed it) says each load resolves "right after **its own** record applies, so
  the next record's stage 2 sees the crater".
- §5.1 has `Topology` bump `topology_version` "once per batch" without defining a batch. Per-record resolution
  needs each strike's destruction applied before the next record's stage 2, so one batch per record.
- §5 also places a "per-tick slot" inside D10 step 1. That is a tick-order contract: `sem_stimuli.md` §4.1, the owner,
  has no such slot. The body laws §5 says will be `per_tick` (tissue, contact) run in §4.1's step 3, not step 1.
- **Failure.** Two strikes on `crate` at tick 7.
  - Built per §5: both pass stage 2, there is no `REGION_GONE`, two loads resolve, and `topology_version` rises by 1.
  - Built per §5.1 with per-record batches: the second strike is refused `REGION_GONE`, and `topology_version` rises
    by 1 (or 2, depending on how batches are read).
  - Refusals and `topology_version` are §9 digest members, so the two conforming builds give different digests, and
    `test_sem_bridge`'s strike-then-read sees different worlds.
- **Fix (unverified).**
  - Give `damage.loads` its own cadence, `per_record`, invoked by the apply phase after each record.
  - Define a topology batch as one record's requests (construction is one batch).
  - Move the per-tick body-law slot's position into `sem_stimuli.md` §4.1, by amendment, or link to it there.

## SHOULD-FIX

### N-S1. `sim_core.md::§3` "A source's energy in a physics step": the overlap rule needs carried state that nothing declares

- The energy is "power times the number of ticks in the interval at whose end it existed". Applying that at the
  physics tick needs the history of the interval. Three cases are undefined:
  - a source doused mid-interval: it is gone from `sources` by tick 10 but owed its earlier ticks;
  - a source re-ignited under the same key with a different power: is it the last power times all its ticks, or the
    sum of each tick's power?
  - a source replaced at the same value.
- This state appears in none of §6's inputs, §9's members or the save, and §5.1 claims nothing is carried state.
- **Failure.** Ignite `fire:crate` at 1 kW at tick 6, then re-ignite at 3 kW at tick 8. One build deposits
  3 kW × 4 ticks; another deposits 1 kW × 2 + 3 kW × 2. Both read §3 correctly. A douse at tick 7 deposits either
  nothing or one tick's worth.
  - A save at tick 8 (step 9) would lose the pending energy.
  - The tick digest catches the divergence only indirectly, through `sources` on an earlier tick.
- **Fix (unverified).** Declare a per-interval accumulator: per key, the integer sum of power over tick ends (or a
  per-tick power row). It is digested input state, cleared after each physics step. Say explicitly that douse and
  replace take effect per tick.

### N-S2. `tile_and_client.md::§3.1` `kind_rank` has no rank for the kinds 5a logs

5a's v0 logs carry `ignite` (§14), and §5.1/§13 add admin `set_material` (a host command, `boundaries.md` §6.1's
table). Tile's table ranks `kindle`, `strike`, `douse` and `imagine`, but not `ignite`, and no host command. **Failure:** the 5a build
picks a rank for `ignite` and commits a golden. Tile's later table, or `phase1/agents`'s extension, picks another,
and same-tick `ignite`/`strike` records reorder under one log format version. **Fix:** amend tile §3.1 to rank
`ignite` (with its v0 retirement) and host commands.

### N-S3. Frame cadence: two owners still disagree, and the checklist restates a third version

- `boundaries.md` §4.2, unedited: a frame "after each physics step … and after each tick that applied an intent".
- Tile §4: a frame on every tick where an intent was "applied **or refused**", or an actor or pilot changed.
- The checklist §4 test: "none on a tick that changed nothing".
- §4's "5a publishes that tick's frame at the end of the tick" reads as every tick.
- **Failure:**
  - A tick with only a refused strike changes nothing. The checklist test passes a build that publishes no frame
    there, but tile §4 requires one ("so a receipt's after-frame always exists").
  - A physics-only tick publishes under boundaries §4.2 but is not listed in tile §4.
- **Fix:** make tile §4 the owner; amend boundaries §4.2 to link to it; and have the checklist test cite tile §4's
  cases (a refusal-only tick publishes; a tick with no record and no physics publishes nothing).

### N-S4. `sim_core.md::§10` and checklist §10: `physics_steps == ticks // physics_every` encodes the old tick-0 rule (verified by arithmetic)

Under §3, N steps from tick 0 run ticks 0 to N−1, with physics where `T % 5 == 0 and T > 0`. That gives
`(N − 1) // 5` physics steps. For N = 5 or N = 10 that is 0 or 1, while the formula gives 1 or 2. **Failure:** the
counter test fails on a correct build, or an implementer "fixes" it by running physics at tick 0, which reverses the
owner's ruling. **Fix:** `(N − 1) // physics_every` for N steps (verified for N = 1 to 15 by hand), or define "ticks".

### N-S5. `sim_core.md::§12/§14`: the per-tick digest chain has no declared format

§12 commits "a log and its per-tick digest chain" as a golden, and §2 says the host logs what `TickReport` carries.
§14's `intent_log` declares only a header line and record lines. **Failure:** the replay reader compares against an
unversioned chain file. A change to the `TickReport` shape or to raw-1's members isn't refused by version; it shows
up as a digest mismatch blamed on physics. **Fix (unverified):** either digests ride the log as a declared
`tick_digest` line kind in `intent_log` v0, or the chain is its own `Format` with fixtures and a gate row.

## NIT

- **N-N1. `sim_core.md::§3`:** the phase rule is cited as "`realtime_lanes_coop.md` §2.1's and `tile_and_client.md`
  §3.2's". It restates both, and overrides realtime with `T > 0`, against a document superseded wholesale. The fold
  says §3 "supersedes realtime §2.1 on this point", but the text doesn't. State that §3 owns the phase rule.
- **N-N2. `sim_core.md::§7`, the bounding-box claim:** the 1/64 condition covers the sum, not the sample test.
  `sphere_overlap` forms coordinates as `np.arange(n) * dx + off`. A box built as `x0 + np.arange(m) * dx` can flip a
  sample lying within an ulp of r², and a random-source test is unlikely to hit one. Require the same expression,
  `np.arange(i0, i1) * dx + off` (unverified). This is a mechanism; defer it to the checklist §7 test.
- **N-N3. `sim_core.md::§13`:** the bridge's synchronous `execute` steps `Simulation` with no host, so its records are
  never logged and a bridge-driven session can't be replayed before `phase1/agents`. Name this in the existing
  marker's reason.
- **N-N4. `sim_core.md::§14`, the header bullet:** it restates parts of `boundaries.md` §6.3 (the scene digest, the
  run seed, the truth constants). List only 5a's additions and link to the rest.
- **N-N5. `sim_core.md::§9`, the cost:** "on physics ticks only" is false for a strike tick, since the crater writes
  cells in the apply phase. The cost is per written field per tick.

## What I checked

| Contract | Owner | Result |
|---|---|---|
| Digest members and bytes | sim_core §9 | N-B1, N-N5 |
| Intent log, header | sim_core §14; boundaries §6.2/§6.3 | W-S3 fixed; N-S5, N-N4 |
| Load and record order | sim_core §5.1 | N-B2 |
| Tick 0, phase, interval | sim_core §3 | fixed; N-S4, N-N1 |
| Source integration | sim_core §3; tile §3.2 | N-S1 |
| Cadence | tile §4, boundaries §4.2 | N-S3 (two owners; fold overclaims A-B3) |
| Tick order | sem §4.1 | linked correctly in §3; §5's slot placement restates it (N-B2) |
| `kind_rank` | tile §3.1 | N-S2 |
| Vocabulary v0 | tile §3.2 | W-S2 open |
| Registry columns | sim_core §6, world_v2 §2.5 | W-S7 open |
