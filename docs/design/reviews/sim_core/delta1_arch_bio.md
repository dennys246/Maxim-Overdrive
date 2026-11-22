# Step 5a delta round 1: Architecture and Bio-faithful integration

Reviewed: `git diff 3b5937b..99917fb` on `phase1/sim-clock`, read against `fire_solid.md` §1.4, §3.2, §4.4;
`research/physics_spike/splitting.md` §2.1, §6; `sem_stimuli.md` §4.1, §7.1; `boundaries.md` §2.2, §4.2, §6.4;
`tile_and_client.md` §4; `world_v2.md` §2.2; `src/simcore/core/{grid,damage}.py`; `adapters/sem/bridge.py`. Nothing
was run. Every proposed fix is **unverified**. No new Maxim claim needed checking (OD-I1 is still roadmap row 129).

**Counts: 1 BLOCKER, 10 SHOULD-FIX, 6 NIT.**

## Round-1 status (set by this reviewer, from the tree)

| Id | Status | Why |
|---|---|---|
| A-B1 | **open** | Declared ordered writers handle splitting, the cell side of contact and `radiant_emitters`. But the new "one resolver per kind of effect" clause brings the conflict back for heat (DA-B1), and construction, `pending` and integrity have no declared path (DA-S2–S4) |
| A-B2 | fixed | R2: loads resolve on their own tick, and nothing is carried. §5's cadence text contradicts it (DA-S1) |
| A-B3 | **open** | The fold row says `boundaries.md` §4.2 was amended. It wasn't: §4.2 still says "published … after each physics step and after each tick that applied an intent". `tile_and_client.md` §4 says something else, so two owners disagree (DA-S8) |
| A-S1 | fixed | `cadence` added. What remains is in DA-S1 and DA-S5 |
| A-S2 | **open (in part)** | "Law" is defined, and sem §7.1 now uses an exchange field. `contact.py` still builds on tissue's operator (DA-S7) |
| A-S3 | fixed for `step` | `stable_dt(state)` still takes the whole state (DA-S9) |
| A-S4 | fixed | §2 |
| A-S5 | fixed | §2's table |
| A-S6 | fixed | A resolver tuple inside damage |
| A-S7 | **open (in part)** | The strike and `imagine` rows in boundaries §6.4 are amended. Its "the laws in `advance`" row is stale, and it has no `Topology` or `set_material` row. world_v2 §2.5 is marked superseded but keeps the list (DA-N5). The checklist and the roadmap's floor line are fixed |
| A-N1 | rejected, accepted | The kernel interface is depended on (Perf P10), so it is contract. The "half a tick" claim is gone |
| A-N2 | fixed | |
| A-N3 | fixed | |
| A-N4 | **open (in part)** | `Topology` and its request type have no layer (DA-N6) |
| BF-5a-B1 | fixed | R2. The crater is in that tick's frame and no load is carried |
| BF-5a-B2 | **open (in part)** | `radiant_emitters` and the exchange field are folded. Still open: who owns the store's writer list, which writers aren't laws (DA-S2), and the contact-to-tissue import (DA-S7) |
| BF-5a-S1 | fixed | §4: `TickReport` is host-only and holds effects. §13: `ModulatorResult` drops the volume and the energy |
| BF-5a-S2 | **open (in part)** | Delta 2's **A-S10** is tagged 5a in `reviews/sem_stimuli/delta2/fold.md:49` and is missing from the checklist's row list. Everything else is corrected |
| BF-5a-S3 | **open (in part)** | The cadence and the closure are there. The cadence has no D10 step, and `per_tick` is pinned to step 1, so sem §4.1's step-3 body laws have no slot (DA-S1) |
| BF-5a-S4 | **open (in part)** | Frames now carry the tick. But §2 says frames change only in `Simulation.step`'s last step, so `from_scene` publishes none, and nothing exists for an observer before tick 0's step. Today `World` publishes frame 0 at construction. Fix (unverified): construction publishes a frame stamped tick 0, and the note says what tick 0's own frame is stamped |
| BF-5a-N1 | fixed | §3 |
| BF-5a-N2 | fixed | §2 |
| BF-5a-N3 | fixed | §4 |

## Does §5.1 fit the four conflicts?

| Conflict | Fits? |
|---|---|
| Splitting (splitting.md §2.1: four laws write skin and bulk temperature) | The multi-writer half fits. **"All heat input from sources resolves in heat" doesn't** (DA-B1) |
| fire_solid §3.2 contact | The cell-side write fits. The exactness contract is restated, and may be restated wrongly (DA-S6) |
| sem §7.1 store | `radiant_emitters` fits. The exchange field is underspecified (DA-S6). The store's non-law writers and its second writer list don't fit (DA-S2). contact→tissue breaks the import contract (DA-S7) |
| imagine/set_material | Cell topology fits. Integrity (DA-S4), fuel `pending` and the counter (DA-S3), and construction's non-topology fields (DA-S2) don't |

## BLOCKER

### DA-B1. `sim_core.md::§5.1` "All heat input from sources resolves in heat" contradicts the laws 5a lands on

Splitting.md §2.1, which is step 6's law list and the reference for §5's order:
- the pilot "deposits on the skins behind its disc" inside the **skin** law;
- the flame feedback q''_f is deposited by the **bed** law.

fire_solid §4.4 has the solid law take the prescribed flame flux q''_fl.

None of these is heat. "Kind of effect" is undefined, and B40 lists no check for it. CLAUDE.md says the rule is
guarded by B40, so the rule has no guard at all.

**Failure scenario.** 6.0b or step 6 either moves the pilot, the feedback and the flame flux into `heat`, which is
round 1's god law, or violates a rule the owner made a standard. A reviewer can't tell which is right, because the
rule doesn't say what a "kind" is.

**Fix (unverified).** Make it one resolver per *input kind*. Each declared input (a `Load` kind, a source kind, a
pilot, a flame flux) names exactly one resolving law in §6, and a test asserts that every input kind has exactly
one. Keep "all damage in damage" as one instance of the rule.

## SHOULD-FIX

### DA-S1. `sim_core.md::§5` "Cadence" contradicts §5.1 and sem §4.1

- §5 says `per_tick` runs "in the per-tick slot, D10 step 1, after the records".
- §5.1, which records the owner's confirmed reading, says each load resolves "right after its record applies".
- sem §4.1 runs contact and tissue in D10 step 3.

**Failure scenario.** A builder following §5 resolves the loads after all the records. A second strike in the same
tick then passes stage 2 against the state before the crater. The `REGION_GONE` test catches this one, but there is
still nowhere to put tissue and contact.

**Fix (unverified).** A cadence names its D10 step and its position: per record, or after the records.

### DA-S2. `sim_core.md::§6` "writers" can't express construction, the save or the store's non-law writers

§6 types writers as "laws … plus `Topology`", and `Topology` covers only `material`, `original_material`,
`region_id` and a new cell's `integrity`. But:
- `from_scene` writes `temperature` (`grid.py:360`) and `sources`;
- the save's construction half writes every saved field;
- sem §7.1's store writers include load, motion and the applier;
- sem §7.1 keeps that store-writer list in `boundaries.md` §6.4, a second owner beside §6's column.

**Failure scenario.** B40's test ("refuses an undeclared one") refuses `from_scene`'s temperature write on day one,
and the PR adds a construction carve-out. That is round 1's item 4, moved from `imagine` to construction.

**Fix (unverified).** Writers are roles: a law, `Topology`, construction, or an input appender. §6 is the one owner,
and boundaries §6.4 links to it.

### DA-S3. `sim_core.md::§5.1` "World edits are requests" leaves out fire_solid §1.4

fire_solid §1.4 says an accepted `imagine` goes into `pending`, and the id counter is minted at acceptance. Both are
digested, saved state, drained "between physics steps".

Against that:
- they are neither topology fields nor §6's declared inputs (`sources`, `loads`);
- `Topology` "applies them … once per batch", with no stated batch;
- two documents now own when an imagine takes effect.

**Failure scenario.** The ownership scan ("the applier writes inputs only") refuses 6.0b's write to `pending`, or
`Topology` applies an imagine immediately while fire_solid defers it.

**Fix (unverified).** `Topology`'s requests cover keyed-table rows, and one document owns when an insertion takes
effect.

### DA-S4. `sim_core.md::§5.1` "No second module writes `integrity`" is false in the same section

- `Topology` writes "a new cell's integrity".
- Destruction writes integrity too (`grid.destroy` sets it to 0).
- `damage.loads` and `damage.thermal` are two tuple entries.
- The checklist's `Topology` test lists only `material`, `original_material` and `region_id`.

**Failure scenario.** The writer test enforces "damage only", so imagined cells can't get integrity 1.0, or the
test gets an exemption.

**Fix (unverified).** Integrity's writers are `(damage.loads, damage.thermal, Topology)`, and the rule reads "no
law outside damage".

### DA-S5. `sim_core.md::§11` bar 3 reverses a mixed-cadence tuple

Reversing `(damage.loads, heat, damage.thermal)` would put load resolution after heat, which the apply phase can't
do. §5 also refuses a log recorded "under another order". Nothing says how laws of different cadences are ordered
in one tuple.

**Failure scenario.** Bar 3's reversed run either can't execute or silently reorders only part of the tuple.

**Fix (unverified).** Reverse within each cadence group, and state the order across groups.

### DA-S6. `sim_core.md::§5.1` The two-rate exchange is not defined, and fire_solid §3.2 is restated

§1 says §5 and §6 define sem's three seams. The two-rate exchange is only "a declared exchange field that the solid
law reads". Contact writes it every tick (step 3) and the solid reads it once per physics step, so it accumulates
across up to five ticks. That makes it carried state with no save entry, no ledger and no named resetter: round 1's
`loads` problem in a new place.

Separately, §5.1 says fire_solid's contact "writes cell temperature … as one antisymmetric transfer". fire_solid
§3.2 puts the Robin term inside both implicit solves and gives the cell "exactly the node's negated gain, as the
same f64 expression", so which law computes the gain is fire_solid's to say (B36).

**Fix (unverified).**
- Specify the exchange field: container, reset, saved, ledger.
- Link fire_solid §3.2 instead of restating it.

### DA-S7. sem §7.1's `contact.py` "from tissue's operator" breaks §5.1's import contract

Body laws are laws (§5), and laws may not import each other. sem §7.1's module table builds contact from tissue's
column operator, with contact layered "above tissue".

**Failure scenario.** When the tissue row lands, the planted-import contract refuses contact, or it gets narrowed.

**Fix (unverified).** Move the operator into a shared module that isn't a law, and edit sem §7.1 by name.

### DA-S8. Frame cadence has three statements (A-B3, still open)

| Where | What it says |
|---|---|
| `boundaries.md` §4.2 | after each physics step and each tick that applied an intent |
| `tile_and_client.md` §4 | every tick that applied or refused an intent, or changed an actor |
| the checklist | none on a tick that changed nothing |

A refused-only tick publishes under tile and not under boundaries.

**Fix.** Replace boundaries §4.2's copy with a link, and correct the fold row. Verified by reading.

### DA-S9. `sim_core.md::§5, §7` `stable_dt` caching contradicts itself

- §5 says `stable_dt(state)` takes the whole state and "caches like" the fields it reads.
- §7 caches it "per `topology_version`".
- splitting.md §2.1's conduction is nonlinear: its bound "tightens as the bed heats".

**Failure scenario.** Step 6's bound stays at its cold, cached value, so `n` is too small and the explicit scheme
goes unstable.

**Fix (unverified).** `stable_dt(views)`, cached by the values it reads.

### DA-S10. `sim_core.md::§13` (R3, Bio-faithful) The interim bridge advances world time once per NPC call

The owner's ruling stands. Its consequences aren't written down:
- `execute` now steps a tick, so world time is set by how many calls agents make;
- every fifth call also runs 0.5 s of physics;
- the bridge needs a step capability, which goes beyond CLAUDE.md's "an applier and a frame view";
- the marker's text ("applies synchronously and logs nothing") no longer describes what it does, so "no new
  deferral" understates the change.

**Failure scenario.** A strike-then-read result depends on the call's phase against `physics_every`. A run with
more NPCs heats faster per action, a cause no NPC could sense.

**Fix (unverified).**
- Name the port the bridge gets.
- Update the marker and the roadmap entry.
- State the interim's time rule, and that no outcome bar may be measured through this path.

## NIT

- **DA-N1** `§5.1` `Topology`'s "key order" and "batch" are undefined. A crater visible per record needs the batch
  to be one record, so `topology_version`, and every cache keyed on it, rebuilds once per strike.
- **DA-N2** `§5.1` The owner who sums `radiant_emitters` is unnamed.
- **DA-N3** `§5.1` `set_material` means two things. world_v2 §2.2 uses it for the topology choke point itself, and
  §5.1 uses it for an admin intent.
- **DA-N4** `§5` `step(views, handles, dt_s)` has no ledger handle, while §5.1 relies on ledgered antisymmetric
  transfers. Say the ledger is a registry field, or reserve the parameter.
- **DA-N5** `world_v2.md::§2.5` keeps the superseded list under its "Superseded" line. That stale copy is what B36
  forbids.
- **DA-N6** `§2` "Where the new types live" leaves out `Topology` and its request type. Laws (layer 4) emit
  requests, so the type must sit at layer 3 or 4.
