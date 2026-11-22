# Step 5a design review: Architecture, compartmentalization and modularity

Reviewed: `docs/design/sim_core.md` and `docs/plans/checklists.md` "Step 5a", `phase1/sim-clock` at 3b5937b
(`git diff origin/main...3b5937b`). I read the cited sections: boundaries §2.2, §4.1–4.2, §6.1–6.4, §7.2–7.3;
sem_stimuli §2.3, §4.1, §5, §7.1, §11.1; fire_solid §0, §3; world_v2 §2.1–2.6, §3.1–3.2, §5;
splitting.md §2.1, §6; tile §6.1; and `src/simcore/core/{world,grid,damage}.py`. Nothing was run. Every proposed
fix below is **unverified**.

**Counts: 3 BLOCKER, 7 SHOULD-FIX, 4 NIT.**

The composition in §2–§4 (five parts, `step` as orchestrator, integer clock) is sound. The problems are in §5.1. The
owner has ruled it, but as written it can't be implemented alongside the documents 5a lands on, and the ways out are
a god law or exemptions. I'm raising that despite the ruling, because the evidence is in the cited documents.

---

## BLOCKER

### A-B1. sim_core::§5.1 "Every field has exactly one writer" contradicts the designs it lands on and the note itself

Exclusive single-writer fields rule out four things the cited contracts require:

1. **Operator splitting on one field.** §5 orders the law list by splitting.md §6 rule 1 ("a law that enforces an
   invariant runs after every law that can break it"). That rule only means something when several laws write the
   same field. In the spike, which is step 6's law list, conduction, skin, bed (whose pyrolysis *projection* resets
   skin temperature to T_p) and open-air loss all write skin and bulk temperature (splitting.md §2.1).
2. **Two-sided exchange.** fire_solid §3.2: the contact law runs "as a law in 5a's list before heat", and "the cell
   side gets exactly the node's negated gain, as the same f64 expression". That is a second writer of cell
   `temperature`. world_v2 §2.6 says "every process is one transfer … applied antisymmetrically", so one process
   writes the donor and the recipient. world_v2 §3.1's transition kernel writes temperature and progress together.
3. **Multi-writer containers that 5a must reserve.** sem_stimuli §7.1 names six writers of the body store (load,
   motion, the applier, `tissue.py`, `irradiance.py`, `contact.py`). Contact writes skin on touched points while
   tissue steps the rest, so one field has two writers split by space. It also names "a multi-writer
   `radiant_emitters` table, each row keyed `(writer law, …)`". The 5a checklist repeats that seam, which §5.1
   forbids.
4. **The note's own §12.** `imagine` moves into the applier, and `grid.paint` writes `material`,
   `original_material` and `integrity` (= 1.0) (`grid.py::paint`). Construction writes everything, and
   boundaries §6.1 lists an admin `set_material`. So `integrity` and `material` have writers other than damage.

**Failure scenario.** In 6.0b the contact law has to change cell temperature, and the window refuses it (checklist:
"tested with a second writer"). The PR then either moves contact, skin, the projection and open-air loss into
`heat` (a god law that every fire, gas and body PR edits, against B32's "laws simple and swappable") or adds an
exemption (a band-aid). The same happens to zones: zone exchange and combustion both write species moles
(world_v2 §2.2, §3.1), and later plasma will too. In 5a itself, `imagine` is refused by the writer check, or the
check gets an applier carve-out.

**What the standard is protecting, and a contract that keeps it.** The protection the owner wants is this: no
hidden writers, inputs never write outcomes, and the order is deterministic. Exclusivity doesn't buy that.
Declaration does. One option, **unverified**:
- Each field's writers are **declared** in the registry, and the window enforces the declaration.
- A field's writers run in the tuple's static order.
- Transfers are antisymmetric and ledgered.
- Inputs (the applier) may *create* matter (initialise cells or bodies) but never change outcome fields of existing
  matter.

If exclusivity is kept, the alternative is a field *owner* that applies every change, with other laws writing typed
contribution arrays (source terms, fluxes, loads). That makes projections the owner's job, and the rule has to say
so. Either version must say how fire_solid §3.2's exactness and sem_stimuli's partitioned skin writes survive.

### A-B2. sim_core::§5.1 "What it changes": a strike's resolution time contradicts the clock, the receipt contract and frame cadence

§3: physics runs only on physics ticks, which is 1 tick in 5 (tile §6.1). §5: damage is the second law of that list,
run in each substep. §5.1 then says the strike's crater "is applied when damage runs", "the frame shows it at the end
of the same tick", and the receipt rides "that tick's `TickReport`".

**Failure scenario.** A strike applied at tick 11 appends a `Load`. Damage next runs at tick 15. The tick-11 report
has no receipt. boundaries §7.2's receipt (with `apply_tick` and "the before and after frame ids") and §4.2's "a
receipt's after-frame exists on its apply tick" both fail, as does the checklist's "receipt comes from that tick's
`TickReport`". The NPC's settle path gets its credit up to 0.4 s late, against a different frame.

Three things are also unspecified:
- **Pending loads are carried state across ticks.** A save at tick 13 must hold them (sem_stimuli §2.3: carried state
  is declared and saved), and they aren't in §6's registry.
- **The writers of `loads`.** The applier appends and damage consumes, which is two writers of one container by
  §5.1's own rule.
- **Which substep consumes a load,** so that it isn't applied n times.

**Fix options (unverified):**
- (a) Damage resolves loads in a per-tick slot, which is the slot sem_stimuli §7.1 already requires (A-S1), after
  apply and before outputs.
- (b) Receipts become deferred to the resolving tick. That changes boundaries §7.2's contract, so boundaries has to
  be amended in this branch.

### A-B3. sim_core::§4 "Frames are published once per tick" contradicts boundaries §4.2, its owner, with a measured cost

boundaries §4.2 owns frame cadence. It says frames are "published on change … not per tick", after each physics step
and each tick that applied an intent, because a full copy is "64–80 MB per tile at 0.1 m, about 13–16 GB/s … if
published per tick at 20×". The diff doesn't amend boundaries §4.2, so two contracts now give opposite answers
(B36). Per tick at 20× brings back exactly the cost boundaries rejected.

**Fix (unverified):** "at most one frame per tick, at its end, when any cell or source changed that tick". State it
once, in boundaries §4.2 or here, and replace the other copy with a link.

---

## SHOULD-FIX

### A-S1. sim_core::§5 The law interface has no cadence, so the sem_stimuli §7.1 seams it owes are missing

§5's law has one `step(state, dt_s, ledger)`, and §8 runs the whole tuple every substep. But:
- fire_solid §3.2: "the solid and contact run once per 0.5 s physics step", with Robin coupling frozen at the step's
  start;
- sem_stimuli §7.1 requires "a per-tick law slot" and "the two-rate contact exchange, ledgered antisymmetrically";
- world_v2 §2.5's registry declared "the process that steps it, and how often".

§1 claims "the SEM contract's 5a half (§11.1)", but none of these seams is in the note. Only the checklist lists them,
and they are contract, not mechanism, because 6.0b and 5b depend on them (B32).

**Failure scenario.** 6.0b's solid law, placed in the tuple, runs n times per physics step at dt = P/n. That changes
its implicit arithmetic and multiplies its cost by n.

**Fix (unverified):** each law declares its cadence (per tick, per physics step, per substep). The orchestrator's
named steps follow from it, and two-rate exchange is defined across cadences.

### A-S2. sim_core::§5.1 "Laws couple only through fields" contradicts sem_stimuli §7.1, and "law" is undefined

sem_stimuli §7.1 says contact writes "the object through the solid law's exchange API", which is a law calling a law.
The note doesn't say whether body laws (tissue, irradiance, contact, which run in tick step 3, outside the list) and
stimulus models are "laws" under §5.1. The import contract the checklist plans can't be scoped until that is defined.

**Failure scenario.** The planted-import contract over a `laws` package misses `core/body/contact.py`, or it catches
it and blocks sem_stimuli's design.

**Fix (unverified):** define a law as anything in a declared tuple at any cadence. Then either amend sem_stimuli's
exchange API into a declared exchange field, or record it as the rule's one named exception.

### A-S3. sim_core::§5 `step(state, …)` gets the whole state, so one-writer can't be expressed in types

`reads` and `writes` are declared, but the signature hands every law all of `state`. The window then has to decide
at run time who is writing, and "refuses a write to a field from anything but its declared writer" has no stated
interface (boundaries §4.1's `writing()` takes no writer).

**Failure scenario.** A law reads an undeclared field. Nothing refuses it, and sem_stimuli §5's lane `producers`
(computed from declared reads) silently misses a dependency, so a digest lane stays green across a real change.

**Fix (unverified):** a law receives read-only views of its `reads` and window handles for its `writes` only.
That is a typed interface, in line with CLAUDE.md "push invariants into types".

### A-S4. sim_core::§2 The intent log's owner is split between `Simulation` and the host

§2: the intent log "changes through `Simulation.step` only". §4: `step` takes records "already in the log's key
order". boundaries §2.2 places the log writer in `engine.host` (layer 8), above `engine.sim` (6).

**Failure scenario.** On replay, `Simulation.step` writes a second log while it reads the first. Or the host and
`Simulation` both append, and the key-order check runs on two copies.

**Fix (unverified):** `Simulation` is a pure function of the records it's given. The host owns the writer, and
`TickReport` carries what the host logs as derived values.

### A-S5. sim_core::§2 World's remaining jobs are unstated, and two keep it a god object

`World` today has `from_scene`, `limits`, `frames`/`_publish`, `writing`, `_power_field` and `advance`
(`world.py`). The note removes `advance` and `turn_seconds` only.
- `_power_field` turns declared sources into power. Under "sources declare, laws resolve" that is heat's job, but
  §7 leaves it on `World`.
- `World.frames` and §4's `Simulation.frames` are two publishers.
- `World.from_scene` and `Simulation.from_scene` both construct.

**Failure scenario.** Fire's sources land in `World._power_field` as well as in a law.

**Fix (unverified):** §2's row states that `World` holds cell state only, and names where each of these goes.

### A-S6. sim_core::§5.1 Damage as the resolver of every load kind grows into a god law

"A later source (ballistic, chemical, electrical) adds a load kind and its law of resolution inside damage." That is
one module with a switch over kinds, and every phenomenon PR edits it.

**Fix (unverified):** keep one integrator of `integrity`, with each kind's resolver as its own module in a fixed,
declared tuple inside the damage package. Each resolver returns increments, and damage applies them in key order.

### A-S7. One owner per contract (B36): stale copies the diff leaves

- **world_v2 §2.5** (`fields.yaml`) is "superseded" by §6 but not edited. §6's list also drops three things world_v2
  §2.5 had: "how often", conservation and ledger, and the `required` flag. The cadence and conservation entries are
  what A-S1 and A-B1 need.
- **boundaries §6.4's row** "the applier: strike | cells, through the strike law" is now false (§5.1, §12). §12 says
  boundaries owns the classification but doesn't change it.
- **boundaries §4.2** (A-B3).
- **The checklist's older 5a bullets** restate §5 and §6 beside the new "Written:" sub-list. The floor bullet says
  "Replace it with an accuracy floor per step length", while §8 adds one only if bar 1 fails. A builder following
  the checklist builds a floor §8 doesn't want.

---

## NIT

- **A-N1. sim_core::§5, §7 Mechanism in prose.** The `prepare`/kernel split, "the numba seam", the overlap's
  bounding box and "measured at about half a burning tick's CPU" are mechanism that nothing else depends on. They
  are already checklist items, so they can be cut from the note (B32).
- **A-N2. sim_core::§14** is a fold-row index inside a design document. CLAUDE.md B36 keeps fold and decision
  tables in `docs/design/reviews/`.
- **A-N3. sim_core::§6** says "its writer laws" (plural) while §5.1 says exactly one. The note also mixes package
  names (`engine.cells`, `core/refusals.py`) without saying which name it means after the rename.
- **A-N4. Layer of the new types.** The note doesn't place `Load`, `Changes`, `FieldSpec`, `TickReport`,
  `WorkCounters` or `Clock` in boundaries §2.2's layers. `Load` next to `Strike` in `intents` (5b) is the natural
  spot, and damage (layer 4) can't import it. The lint would catch that, but the note should say where each type
  lives.

---

## Will §5.1 hold for the phenomena ahead?

| Phenomenon | As written | With A-B1's declared-writer form |
|---|---|---|
| Fire 6.0b/6.1 (contact, solid, projection) | no: second writer of cell temperature, and a per-step cadence | yes, with cadence (A-S1) |
| 5b bodies (six store writers, partitioned skin) | no | yes, with a declared writer allowlist per field |
| SEM stimuli (models write nothing, read frames) | yes | yes |
| Gas zones and combustion (world_v2 §2.2, §3.1) | no: exchange and combustion share species | yes, with transfers ledgered |
| Plasma and electrical damage | only by growing damage (A-S6) | yes |

The parts of §5.1 that are sound and should stay: inputs never write outcomes, observers read only frames, laws
never import one another, and the law order is static.
