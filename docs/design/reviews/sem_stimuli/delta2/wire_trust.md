# SEM stimulus design, delta round 2: Wire integrity and Trust boundary

**Reviewed:** `docs/design/sem_stimuli.md` v3 at `77e24bb` (`phase1/sem-stimulus`), against my delta-1 report
(`reviews/sem_stimuli/delta1/wire_trust.md`) and the author's `delta1/fold.md`. Read from the tree:
`pyproject.toml` (import contracts), `tests/test_tooling_config.py` (`_core_modules`, `CORE_PUBLIC_SURFACE`),
`src/simcore/core/{applier,intents,limits,frames,readonly,checks}.py`, `boundaries.md` §4.2–§4.3, and
import-linter 2.6's `contracts/forbidden.py` in the fire-research venv. No Maxim claim needed re-checking for this lens.

**Correction of my own delta-1 advice, first.** My S4 fix said "state `allow_indirect_imports = false`". v3 did exactly
that, and as written it will break on landing: every existing `forbidden` contract here sets `true` precisely because
chains through allowed modules reach forbidden ones (`membrane-reads-frames` → `frames` → `grid`). I did not check that
`AGENTS_SURFACE` is closed under imports. Verified below on a toy package; S4 stays open, on my error as much as the
author's.

| Id | Status | Reason (read from v3) |
|---|---|---|
| S3 | deferred | unchanged; trigger stands: `phase1/agents`' strip-list schema test or the first `events` producer, whichever is first, must name `offset_us` as the second exemption |
| S4 | open | §7.3 sets `allow_indirect_imports = false`, but nothing makes `AGENTS_SURFACE` closed under core imports, so the contract goes red the day `stimuli.schema` imports the body or field-reader types (W9 below gives the measurement and the fix) |
| S5 | deferred | §6.1 hands the environment entity and the mapping of `StructureModulator.execute`'s refusals to `phase1/agents`. Trigger unchanged: the `phase1/agents` design, reviewed by this lens |
| W1 | fixed | §4.4: `execute` returns a fixed `pending`, no name, no metadata; §4.2 adds `receipts: (pid, kind)` to `BoundFrame`; §5 versions the receipt with a gate row in `phase1/agents`; §6.2 and T7 cover receipt bytes and the `pending` return. Delivery under D14's divisor is a new gap (W10), not a reopening |
| W2 | open | precedence is fixed and unperceived/out-of-reach merge into `unavailable`, which removes the ordering oracle. But `applied` against `unavailable` is still an existence and footprint oracle that no v1 stimulus grounds, and T11 sweeps only inside `unavailable`, so it can't see it. Details below. The proposed deferral of mapping `StructureModulator`'s refusal strings to `phase1/agents` is **accepted** under S5's trigger |
| W3 | fixed | §3.2: `Binding` is a frozen spec in `core/stimuli/schema.py`, validated when `join` is applied; an invalid table is `agent_failed(build)` before any reduction; replay reads `join` through the same gate; the worker keeps only Maxim-side checks |
| W4 | open | §3.2 and §4.2 add `bindings_digest` to `welcome` and every `BoundFrame`, and the worker refuses a mismatch. Missing: the worker-side plant I asked for. §5's reorder plant is inside `reduce.py` with `join` unchanged, which tests the host lane, not the worker's refusal. Without a plant that edits only the worker's copy, the refusal is a check nobody has seen fail |
| W5 | fixed | §6.3: one header row; "T2 merged into T1 in v2" |
| W6 | fixed | §2.2: `valid` range and rounding freeze with the tissue law's PR, the alternative I offered |
| W7 | fixed | §5: body instance (5b); binding table, `BoundFrame`, receipt (`phase1/agents`); the save's body state (the first law), each with a version and a gate row. Two channel messages are still unnamed (W13, NIT) |
| W8 | fixed | §3.1 names the skin's outer boundary as convection's one receiver; §6.1 cites `boundaries.md` §4.2 (line 252 holds the pinned-frame rule) and §4.3 |

Counts: 11 rows: 6 fixed, 2 deferred, 3 open, 0 rejected. New in v3: 0 BLOCKER, 4 SHOULD-FIX, 2 NIT.

## 1. W2, what is still open

v3's kinds are `malformed`, `limit`, `unavailable`, `applied`. The applier today checks limits (`action.check`), then
the region (`_check_region`: no such region, air, gone), then, inside `_strike`, whether `point_m` is on the region's
authored footprint (`applier.py:101-104`, "point_m is not on the {region}"). The first two are target-independent and
fine. Everything after them depends on the target, and v1 has no row that tells A anything about the target: no
vision, no touch, only `tissue_temperature`. So:

- **Footprint by bisection:** A strikes a region it was handed at a swept `point_m`. On the footprint it gets `applied`,
  off it `unavailable`. Twenty receipts bound an edge to 1 mm. §6.2 itself lists "footprint bounds by bisection" as a
  leak the receipt path carries today, and v3 keeps it.
- **Existence by name:** for any name the environment entity accepts, `applied` means "exists, not gone, in reach".
  Which names A can submit is S5's deferred design, but the receipt vocabulary is frozen now (§0, "receipt kinds").
- **The gate can't fail on it:** T11 "sweeping an unavailable target's position and existence" holds the kind constant
  among targets that are all `unavailable`. The leak is the boundary between `unavailable` and `applied`, which the sweep
  never crosses.
- **Unmapped outcome:** `_strike`'s footprint miss is an `Outcome(applied=False)`, not an `ActionRefused`. v3 doesn't say
  which kind it becomes. If an implementer maps "the applier returned an Outcome" to `applied`, the oracle flips sign but
  stays.

*Fix (design-level, not run):* the only rule consistent with §6.2's own principle (perception is defined from A's frame)
in a version with no perception row is a target-independent receipt: v1 kinds `malformed`, `limit`, `accepted`, with
every target-dependent result logged host-side only, and the effect arriving as stimuli. It costs something real: an
NPC can't tell whether a strike landed until a touch or vision row exists, and the receipt vocabulary changes when one
does (a version event; see W11). The alternative is to keep `applied` and enter it as a named ANALOG leak with T11
recording it, which the owner may prefer. Either way, extend T11 to sweep `point_m` across a footprint edge and hold the
kind constant, and state the kind of a non-refusal `Outcome(applied=False)`.

## 2. New findings in v3

### SHOULD-FIX

**W9. `sem_stimuli.md::§7.3 agents-reads-body-frames`: with `allow_indirect_imports = false`, the contract is red
as soon as any surface module imports a core module outside `AGENTS_SURFACE`, and v3 has no rule that prevents it.**
- Import-linter 2.6's `forbidden` contract defaults `allow_indirect_imports` to `False` and then reports any chain from
  source to forbidden module through any intermediate, allowed ones included (`forbidden.py:47`, `:96-107`).
- **Measured** on a toy package (`scratch_wire_trust/toy/`): `agents.worker → core.frame → core.readonly`, with
  `readonly` forbidden. `false` gives BROKEN, naming the two-link chain; `true` gives KEPT.
- In this repo `intents → {checks, limits}` and `limits → checks`, which are closed. But v3 gives `stimuli.schema`
  "`Binding` and its checks" ("sites lie in its site set and the body") and "the `StimulusModel` protocol", whose kernel
  takes a `FieldReader`. The natural imports are `core.body.spec` or `sites` and 5a's field-reader module, none of them
  in `AGENTS_SURFACE`. Grimp counts `TYPE_CHECKING` imports unless `exclude_type_checking_imports` is set, and
  `pyproject.toml` doesn't set it. `frame.py`'s "refuses writable arrays, as `CellFrame` does" may pull in `readonly`.

*Failure:* `phase1/agents` lands, `lint-imports` goes red on `adapters.agents → stimuli.schema → body.spec`. The cheap
way to green, and the one every sibling contract already uses, is `allow_indirect_imports = true`. That reopens round 1's
S4 exactly: `stimuli.frame`'s reduction path then reaches `core.body` with no contract objecting.

*Fix:*
- Put what crosses to the worker (`BoundFrame`, `StimulusEvent`, `Receipt`, the receipt kinds and the binding table's
  plain data) in a leaf module, say `core/stimuli/wire.py`, that imports only `checks` and numpy. Keep `Binding`'s
  validation against the body in `schema.py` or `reduce.py`, which the worker never imports.
- Add a closure test beside the list-equality test: every core module reachable from `AGENTS_SURFACE` is in
  `AGENTS_SURFACE`. **Verified** on the toy with grimp: `find_upstream_modules` over the surface reports
  `pkg.core.readonly` as outside it (`scratch_wire_trust/closure.py`). Plant: add one import from the leaf to
  `readonly`, and see both the closure test and the contract go red.

**W10. `sem_stimuli.md::§6.2`, `§4.2` and `§4.6`: under D14's cognition-rate delivery, receipts in an undelivered frame
are lost, and the frame's "since last delivered" events contradict T9.**
- §6.2 puts the receipt "in tick `T+L`'s `BoundFrame`". `L` is never defined in v3; I read it as the lane minimum of
  `npcs_and_sem.md` §9.
- §4.6: until a pain path exists, push and body step run at the cognition rate, "with that tick's values and the events
  since the last delivered frame". Receipts aren't mentioned, and §4.2 accumulates only events.
- At divisor 10, an intent observed at tick 0 applies at `L = 1`; tick 1's `BoundFrame` holds the receipt, is built and
  digested, and is never sent. The worker's next frame at tick 10 has no receipt. Credit through settle (§4.4, M18)
  never sees the outcome.
- The other direction: §4.2 makes `BodyFrame.events` "since this NPC's last delivered frame". T9 requires frames
  byte-identical across divisors 1–50. At divisor 1 a frame holds one tick's events; at divisor 10 it holds ten. Those
  can't both hold. v1 has no event producer, so T9 passes vacuously and the contradiction surfaces with sound.

*Fix (reasoned, not run):* make every frame per tick: events and receipts of that tick only, digested as now, so T9 and
the lanes are divisor-independent. Make the **delivered message** the concatenation of every undelivered frame's
events and receipts since the last delivery, plus that tick's values, assembled at send under the byte budget. That
message is what T12 scans and what gets the `phase1/agents` version and gate row. Define `L`. Gate: at divisor 10, an
intent's receipt reaches the worker in the next delivered message, planted red by delivering only the current frame's
receipts.

**W11. `sem_stimuli.md::§5 The digest` and `The header`: the per-NPC `BoundFrame` lane is keyed by nothing that
versions it, so a format change replays as a mismatch, not a refusal.**
- Row lanes are keyed by `(name, derivation_version)`, so replay skips a changed unbound lane and refuses a changed
  bound one. But "`BoundFrame` values and receipts are one lane per NPC", with no stated key beyond the NPC.
- The header lists rows, lanes, id maps and truth constants. It doesn't list `STIMULUS_SCHEMA_VERSION`, the receipt
  vocabulary's version or the `BoundFrame` format's version.
- §6.2 already schedules a vocabulary change: `unavailable` splits when a vision row lands. W2's fix would schedule
  another. Either one changes every NPC lane's bytes with the key unchanged.

*Failure:* after the split, every committed replay golden goes red at "the first bad interval" (§5 localisation), which
reads as a determinism bug. A reader that doesn't know an old format has to refuse it loudly (CLAUDE.md, "Every format is
versioned"). This one doesn't know it is reading a different format.

*Fix:* key each NPC lane by `(npc_key, BoundFrame version, receipt-vocabulary version)`, write all three versions plus
`STIMULUS_SCHEMA_VERSION` into the header, and have replay refuse an unknown version by name, or skip and report a
known older one exactly as it does row lanes. Plant: bump the receipt version and change a kind's encoding; replay must
report a version refusal, not a lane mismatch. Not run.

**W12. `sem_stimuli.md::§4.5`: posture, gaze and breathing become intent kinds with no gate.**
- §4.5 makes them intents applied next tick. Posture moves the body's sites in world metres, which feeds visibility,
  contact and tissue. Gaze feeds visibility. Breathing feeds gas.
- v3 gives them no stage-1 parsing, no limits, no format version and no gate-registry row. The intents that exist today
  get all four (`intents.py`'s `finite_vector` and `ActionRefused`, `limits.py`'s bounds).
- §4.3: "a non-finite value in the core is a world bug: the server stops loudly."

*Failure:* a worker, whether by bug or adversarial LLM output, emits a gaze of `[NaN, 0, 1]` or a posture placing a hand
40 m away inside a wall. If nothing validates it at the protocol layer, the NaN reaches the irradiance law and the world
server stops, on every replay of that log. The far hand produces a contact solve against a wall that no physical body
could touch. Either way, untrusted input decides the world's outcome, against "malformed input gets an error reply,
never a crash".

*Fix:* add the three kinds to the stage-1 parser with finite and unit-vector checks, ranges in `ActionLimits` (joint
ranges, a gaze rate, physiological breath bounds) loaded from `data/`, a gate-registry row each, every rejection path
tested, refusals reported as `malformed` or `limit` receipts, and a Hypothesis "never crashes" property over the parser.
Plant: NaN gaze, and the world advances with an error receipt. This follows the existing `Strike` pattern; I haven't
written it.

### NIT

- **W13. `§5` format list:** `welcome` (which carries both digests) and `step_output` (the worker-to-host direction, the
  untrusted one) have no version or gate row named. Both are `phase1/agents`' channel. Add them to the list with that
  owner.
- **W14. `§4.2` and `§6.2` loose ends:**
  - `pid` is never defined. Say who allocates it and that it is per NPC. A global counter would leak B's intent count;
    T11 would catch that only if its plants include B issuing intents.
  - v2's "checks `tick` rises, **then drops it**" lost its last clause. Under D4 cognition gets no time field, so restore
    it or say where `tick` goes.
  - On restart (§4.5), state that receipts for the previous life's pids are dropped and counted, like events.

## 3. Leak shapes, after v3

| Leak shape | Caught by | Remaining gap |
|---|---|---|
| Region instrument on the NPC | T13, T8, `agents-reads-body-frames` | the surface isn't closed, so the contract will be loosened (W9); environment entity deferred (S5) |
| Material constant | T5, T6, T12, fixed `pending` | none new |
| Another NPC's stimuli | T11, T12 | `pid` allocation unstated (W14) |
| Existence and position oracles | merged `unavailable` | `applied` vs `unavailable` across a footprint edge or a name (W2) |
| Outcome text | T7, `pending` | refusal strings mapped in `phase1/agents` (S5) |
| Time | T9, D3 named | strip exemption deferred (S3); `tick` drop unstated (W14) |
| Receipts lost or reformatted | none | divisor drops (W10); unversioned NPC lane (W11) |
| Malformed input | NaN, ±inf, `1e400`, `bool`; join gate | posture, gaze, breath ungated (W12) |
