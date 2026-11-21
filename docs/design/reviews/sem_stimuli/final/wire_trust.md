# SEM stimulus design, final round: Wire integrity and Trust boundary

**Reviewed:** `git diff 0918685..aa6bd1b` on `phase1/sem-stimulus` (v4 `sem_stimuli.md`, `checklists.md`'s three
SEM items and the laws section, `delta2/fold.md`, §10's rulings, the side edits). I also read, at `aa6bd1b`,
`src/simcore/core/{applier,intents,limits,readonly,frames,__init__}.py`. This lens needed no Maxim claim. The script
is in `scratch_wire_trust/toy/` beside this report.

**My own error first.** W10's fix, as I wrote it in delta 2, said to concatenate undelivered ticks "under the byte
budget". v4 does that. Because coalescing is lossy and is applied to each delivered message, that wording brings back
the divisor dependence W10 was meant to remove (N1 below). The author followed my wording; the hole is mine.

| Id | Status | Reason (read from the tree at `aa6bd1b`) |
|---|---|---|
| S3 | deferred | v4 doesn't touch it. The reason and trigger stand: `phase1/agents`' strip-list schema test, or the first `events` producer, must name `offset_us` as the second exemption beside `SensorReading.timestamp` (`boundaries.md:572`). The trigger is written down only in review reports, so the agent-half checklist should carry it (N6) |
| S4 | fixed | as W9 |
| S5 | deferred | §6.1 and §11.1 give the environment entity, and the mapping of `StructureModulator.execute`'s refusals, to `phase1/agents`. Under D15 that mapping reduces to "every stage-2 result is `accepted`". Trigger unchanged: the `phase1/agents` design, reviewed by this lens |
| W2 | fixed | D15 (owner, §10): v1's kinds are `malformed`, `limit` and `accepted`, target-dependent results are logged host-side only, and T11 sweeps a strike point across a footprint edge (§6.2, agent checklist). The sweep still misses the applier's other target-dependent refusals (N2) |
| W4 | fixed | §3.2 and the agent checklist plant the refusal by editing only the worker's copy |
| W9 | fixed | §7.1 makes `wire.py` a leaf (only `checks` and numpy). §7.3 sets `AGENTS_SURFACE` = `wire`, `intents`, `limits`, `checks`, which is closed in today's tree (`intents → checks, limits`; `limits → checks`), and adds a grimp closure test with a `readonly` plant. A package-`__init__` path remains that neither the contract nor the closure test sees (N5, NIT) |
| W10 | fixed | §4.2: `BodyFrame` is per tick, `BoundFrame` concatenates the undelivered ticks, §6.2 defines the receipt's timing, and the agent checklist has the divisor-10 plant. The budget clause I supplied contradicts T9 (N1) |
| W11 | fixed | §5 keys the bound lane by the `BoundFrame` and receipt-vocabulary versions, the header carries them, replay refuses an unknown version by name, and the plant bumps the receipt version. The key still leaves out the delivery schedule (N3) |
| W12 | fixed | §4.5 and the 5b checklist: stage-1 finite and unit-vector checks, `ActionLimits` from `data/`, a gate row for each kind, every rejection path, Hypothesis, and a NaN-gaze plant. One wording slip (N4) |
| W13 | fixed | §5's format list now names `welcome` and `step_output` with `phase1/agents` |
| W14 | fixed | §4.2: `pid` is allocated per NPC, and `tick` is checked and then dropped. §4.5's restart row drops the previous life's receipts and counts them |

Counts: 11 rows: 9 fixed, 2 deferred, 0 open, 0 rejected. New in the diff: 0 BLOCKER, 3 SHOULD-FIX, 3 NIT.

## New findings

### SHOULD-FIX

**N1. `sem_stimuli.md::§4.2` ("nothing is lost at any divisor") and `§4.3` ("capped per delivered frame") against
`§6.3::T9`: coalescing is applied per delivery, so the delivered content depends on the divisor.**
- §4.3 caps events per *delivered* frame. Overflow coalesces by `(kind, site)` into a count and a peak, which loses
  data.
- §4.2 makes a delivery the concatenation of every undelivered tick. T9 requires `BoundFrame` event and receipt
  content to be "equal as a multiset over a common window" for divisors 1 to 50.
- *Scenario (reasoned, not run):* a 1 s burst with 60% of the budget in each tick. At divisor 1, no tick overflows
  and every event arrives intact. At divisor 10, ten ticks are concatenated, the message holds 600% of the budget,
  and the events arrive coalesced. The multisets differ, so T9 is red, or else T9 is written over a stream with no
  burst and never exercises coalescing. "Nothing is lost at any divisor" is false whenever coalescing fires.
- Receipts have no `site`, so §4.3's coalescing key doesn't say what happens to them. Coalescing them would drop the
  `pid` that settle (M18) needs. Not coalescing them means the budget doesn't bound the message.
- v1 has no event producer, so T9 passes vacuously until sound lands. That was W10's original failure shape, and the
  checklist doesn't hold this case (its bounds item, "a burst keeps the agent alive", runs at one divisor).
- *Fix (unverified):* coalesce per tick, in `BodyFrame`, where it is divisor-independent and the events lane already
  digests it. Size the per-delivery budget as the per-tick budget × the largest divisor (a header constant) and
  refuse a configuration that exceeds the socket buffer at start. Exempt receipts from coalescing and bound them with
  a per-step intent cap in `ActionLimits`. Plant: the burst above at divisors 1 and 10, with T9 required to compare
  event content.

**N2. `sem_stimuli.md::§6.2` Gates and `checklists.md` (agent half, "T11 sweeps a strike point across a footprint
edge"): T11 sweeps one of the applier's target-dependent paths and leaves out the rest.**
- At `aa6bd1b`, `Applier.apply` gives a refused intent `Outcome(applied=False, reason)` on five target-dependent
  paths:
  - no such region (`applier.py:76`);
  - the region is air (`:78`);
  - the region is gone (`:80`);
  - the strike point is off the footprint (`:104`);
  - `extinguish` with "nothing is burning on the {region}" (`:122`).
- It also re-checks limits at stage 2, inside the same `try` (`:57-60`), so a limit refusal and a target refusal
  reach the caller in the same shape.
- §6.2 names sweeps of existence, position and the footprint edge. Nothing sweeps fire presence.
- *Scenario:* `phase1/agents` maps receipts per action. `extinguish` maps `Outcome.applied` to the kind, so a refusal
  becomes `limit`, while strike is mapped correctly. T11's strike sweep stays green. A now has a fire detector that
  works through walls, one `extinguish` per region per cognition step. That is T4's "hazard behind a wall" leak
  arriving through the receipt path, with no physical crossing.
- *Fix (unverified):* T11's receipt sweep covers every target-dependent refusal the applier can return, once for each
  affordance: existence, air, gone, footprint and burning state. Each is planted by mapping that path's
  `Outcome.applied` to the kind. Add one contract sentence: the kind is decided by stage 1 alone, and any stage-2
  result is `accepted`. The sweep belongs in the checklist; the sentence belongs in §6.2.

**N3. `sem_stimuli.md::§5` (bound lane key, header) with `§4.2` and `§0`: the bound lane digests receipts whose
placement depends on the delivery schedule, and nothing keys or records that schedule.**
- §4.2 assembles `BoundFrame` at delivery and puts each receipt "in the first `BoundFrame` delivered after its intent
  applies" (§6.2). Which digested frame holds a receipt therefore depends on the actor's rate divisor and phase
  (`boundaries.md:582`, `data/agents/`) and on whether D14's interim is in force.
- The bound lane's key is `(npc_key, BoundFrame version, receipt-vocabulary version, bindings_digest, reduce version,
  bound row keys)`. The header lists no divisor, phase or D14 flag.
- The text also contradicts itself on when a `BoundFrame` exists. §0 and §4.5 build and digest one every tick ("built
  and digested, not sent"). §4.2 assembles it only at delivery.
- *Scenario:* D14 ends when a pain path lands, and delivery becomes every tick. Every NPC's bound lane changes bytes
  while its key is unchanged, so every committed replay golden goes red "at the first bad interval", which reads as a
  determinism bug. The same happens when an actor's divisor changes in `data/agents/`. This is W11's failure, moved
  from formats to schedules. D13 makes it worse: the agent home's recorded keys still match, so the load accepts it.
- *Fix (unverified):* one of two.
  - Digest receipts per tick in their own lane, as `BodyFrame.events` already are. Keep the per-delivery
    concatenation out of every digest, and say so in §0 and §4.2.
  - Add the delivery schedule (divisor, phase, the D14 flag) to the bound lane key and the header.

  The first is the one that matches §4.2's own "per tick and divisor-independent" principle. Plant: change one
  actor's divisor. Replay must either still compare green (the first option) or report a changed key (the second).

### NIT

**N4. `checklists.md` 5b, "Posture, gaze and breath intents": the plant says "the world advances with an error
receipt".** There is no `error` kind. Under D15 a NaN is `malformed`. Name the kind, or an implementer may add a
fourth one.

**N5. `sem_stimuli.md::§7.3 agents-reads-body-frames` and its closure test don't see package `__init__` imports,
and §7.4's "`__all__` allowlist on `core/stimuli`" invites re-exports there.** I checked this with import-linter in the
fire-research venv on a toy (`scratch_wire_trust/toy/`):
- `agents.worker` imports `core.stimuli.wire`, a leaf, and `core/stimuli/__init__.py` re-exports from `registry`,
  which imports `body.store`.
- The `forbidden` contract with `allow_indirect_imports = false` is KEPT, but at runtime `body.store` is loaded in the
  worker (`True`). Grimp doesn't add an edge from a submodule to its parent package.

No world data crosses this way, because the worker is a separate process, so this is a NIT. The contract's
guarantee is narrower than §7.3 implies. *Fix (verified only to the extent of the toy's KEPT result):* the closure
test adds each surface module's parent packages to the set it closes over, or §7.4 requires `core/stimuli/__init__.py`
to import nothing (`__all__` lists names only).

**N6. Stale and missing traces:**
- `long_term_features.md`'s SEM Status still says "D15 (receipt kinds) open", and Next says "The owner's D15", but
  §10 records D15 as ruled in the same commit.
- §11.3 still calls D15's kinds "recommended".
- S3's trigger (`offset_us` as a strip exemption) appears in no checklist item, now that the checklist owns the
  tests.
- §6.2 times a receipt "after its intent applies", but a `malformed` or `limit` intent never applies. State when it
  is delivered: in the first delivery after the merge that refused it.

## Leak shapes after v4

| Leak shape | Caught by | Remaining gap |
|---|---|---|
| Region instrument on the NPC | `agents-reads-body-frames` (false) + closure test, T13, T8 | package `__init__` re-export (N5); environment entity (S5) |
| Existence, footprint, fire-state oracles | D15's kinds, T11 sweeps | extinguish and air/gone paths not swept (N2) |
| Another NPC's stimuli | T11, T12, per-NPC `pid` | none new |
| Outcome text | T7, fixed `pending` | none new |
| Time | T9, `tick` dropped, D3 | strip exemption (S3) |
| Receipts lost or reformatted | divisor-10 plant, versioned key | coalescing per delivery (N1); schedule not in the key (N3) |
| Malformed input | stage 1 for all six kinds, NaN plants | none new |
