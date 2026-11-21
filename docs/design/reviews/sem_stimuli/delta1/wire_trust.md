# SEM stimulus design, delta round 1: Wire integrity and Trust boundary

**Reviewed:** `docs/design/sem_stimuli.md` v2 at `3e97ac9` (`phase1/sem-stimulus`), against my round-1 report
(`reviews/sem_stimuli/wire_trust.md`) and the author's `fold.md`. I read from the tree:
- `src/simcore/core/applier.py`: `apply`, `_check_region`, `_strike`, `_extinguish`.
- `src/simcore/adapters/sem/bridge.py`: `StructureModulator.execute`, `_from`, `region_parts`, `to_maxim_entity`.
- `pyproject.toml`'s import contracts.
- `boundaries.md` §4.2 and §4.3, and `tile_and_client.md` §2.1.

Maxim was read by `git show origin/main` at `043eab8f`, not fetched:
- `src/maxim/embodiment/spec.py`, where `execute` delegates to `self._backend.execute` and returns its result
  (around line 1136).
- `src/maxim/runtime/bootstrap.py`, the `modulator_factory` backend hookup (around lines 552–561).

**Counts:** 23 findings from round 1. 20 are `fixed`, 2 `deferred` and 1 `open`; none is `rejected`. New in v2:
0 BLOCKER, 4 SHOULD-FIX, 4 NIT.

## 1. Status of round-1 findings

| Id | Status | Reason, read from v2 |
|---|---|---|
| B1 | fixed | §6.2: receipts are a closed vocabulary, unknown, destroyed and unperceived targets collapse to `not_perceived`, the effect arrives as stimuli, and T4/T5/T11 run over receipt bytes with intents issued, T12's sentinel in `absorbed_j`. The channel those bytes travel on and the refusal predicate are new gaps (W1, W2), not a reopening |
| B2 | fixed | §4.1 states steps 3–4 as an insertion into D10 before agents, and says an agent at a physics tick sees the previous physics step's fields; the overlap gets an on/off digest gate |
| B3 | fixed | §3.1: tile §2.1's store is the core node and sole producer of `core_temperature`; one `bodies` ledger line; `npc_key` is `body_key`. Residue on convection is W8 |
| S1 | fixed | §6.1 lists the three superseded contracts by name; the pinned actor table leaves the NPC path. (It cites `boundaries.md` §4.3; the "pinned per agent" sentence is §4.2 line 252, §4.3 only uses it; W8) |
| S2 | fixed | §4.2: `caused_by` is A's own pid or null; one name |
| S3 | deferred | §4.2 fixes the ordering (offsets within one tick, one frame per tick) and makes `local_id` per NPC. I accept the deferral of the strip-list exemption: `events` is held empty by a gate until sound lands, so no offset crosses before then. **Trigger:** `phase1/agents`' strip-list schema test, or the first `events` producer, whichever is first; that PR must name `offset_us` as the second exemption |
| S4 | open | `agents-reads-body-frames` now forbids the right modules, `adapters.sem.bridge` included, but v2 doesn't say `allow_indirect_imports`. Every existing `forbidden` contract sets it `true` (`pyproject.toml` lines 143, 158), so a copy bans direct imports only, and `stimuli-protected` lets adapters import `stimuli.schema` and `frame`, whose reduction needs sites (`core.body`). Missing: state `allow_indirect_imports = false` for this contract, or name the chain the models allowlist cuts and plant an indirect import red |
| S5 | deferred | §6.1 rescopes D10 (modulators stay; the instrument builder becomes a lab builder), which removes the `tests-out` break. Accepted, because the environment entity can't be designed before the `phase1/agents` channel exists. **Trigger:** the `phase1/agents` design; it gets this lens's review and must apply W2's refusal rule to `StructureModulator.execute`'s own refusals (below) |
| S6 | fixed | §5 rule 5: an agent home records only its bound rows; D13 rules refusal unless named |
| S7 | fixed | §5: canonical values through `checks`, codec bytes out, deltas ruled out, codec goldens |
| S8 | fixed | §4.3: the raise is a world bug that stops loudly with tick and NPC; NaN, ±Infinity, `1e400` and `bool` are planted; §2.1 gives each row validity, a rounding policy and an empty-patch rule. The v1 row's actual values are missing (W6) |
| S9 | fixed | §3.2 lists all four checks, and no unit transform, so `celsius` can't bind `celsius_norm`. Where they run is a new gap (W3); the gate row is folded into W7 |
| S10 | fixed | §4.4 specifies the backend as the outbox and cites `spec.py`'s delegation (verified: `execute` returns `self._backend.execute(...)`); M18 asks the embedded path; §2.1 has the worker count clamps. What `execute` returns is W1 |
| S11 | fixed | §4.2 has the worker check `npc_key` against its channel's actor and `tick` rising; `registry_digest` is checked against `welcome`; §5 has a round trip plus goldens. Binding order isn't covered (W4) |
| S12 | fixed | §6.3: T12's plants are a core misroute and a channel misroute; host load is named as a known leak until D3, with T9's worker half strict red |
| N1 | fixed | §1's tests are named (instrument, transduction); the gates are T-numbers. The table itself is malformed (W5) |
| N2 | fixed | `fields_sequence` |
| N3 | fixed | §4.2: the worker checks `tick` rises, then drops it |
| N4 | fixed | §4.2: a gate holds `events` empty until sound lands |
| N5 | fixed | the sentence is gone from §6.1 |
| N6 | fixed | §7.3: every new module, `__init__` included, is classified |
| N7 | fixed | §11.1 5b: a body-instance format with a strict loader, version, gate row and fixtures; §3.3's Maxim YAML holds sensors only |
| N8 | fixed | §4.3: everything is validated before any write |

## 2. New findings in v2

### SHOULD-FIX

**W1. `sem_stimuli.md::§4.4 The push` and `§6.2` give the receipt no channel and no defined interim result. B1's
gates therefore have no bytes to scan.**
- §4.4 says the backend's `execute` "*is* the outbox path: append an intent, return". At `origin/main`,
  `SpecModulator.execute` returns whatever the backend returns, so that return value is the tool result the LLM reads.
  v2 doesn't say what it holds.
- The code's own marker (`bridge.py`, `TEMPORARY(phase1/agents)` in `StructureModulator.execute`) promises "a
  pending, neutral result", but v2 never states it. Today's `_result` copies `entity_name`, the region's name, and
  `_from` spreads `Outcome.metadata`, which holds `absorbed_j`, into `ModulatorResult.metadata`.
- The closed-vocabulary receipt that §6.2 defines (applied, or a refusal kind) has no field. `BoundFrame` carries
  `value` and `events` only (§4.2), and `StimulusEvent` has no kind for it.
- §4.4's "credit flows through settle" therefore has no defined settle input on the wire.
- T4, T5 and T11 "over receipt bytes" can't be written, because there are no receipt bytes. T12's `absorbed_j`
  sentinel would pass vacuously if receipts never cross.

*Failure:* `phase1/agents` keeps `_from` for the return value, because the design is silent. `absorbed_j` reaches the
LLM in the synchronous tool result. T12's scan stays green if it reads only `BoundFrame` bytes.

*Fix:*
- State that `execute`'s return is a fixed `pending` result: no name, no metadata, constant over targets.
- Add the receipt to the wire as a versioned field or a message: `(pid, kind)` from the closed vocabulary, in the
  tick-`T+L` frame.
- Put it under `STIMULUS_SCHEMA_VERSION` or its own version, and point T12's scan at it and at the return value.

**W2. `sem_stimuli.md::§6.2 A receipt is a closed vocabulary` leaves "perceived" undefined and refusal precedence
unstated. The vocabulary is then an oracle in itself.**
- `not_perceived` needs a world-side predicate, "does A perceive target X", and v2 never defines it.
- If the predicate is geometric line of sight, it disagrees with A's stimuli: a crate in a dark room is "perceived"
  while A's frame carries nothing from it. An intent at a dark corner then returns `out_of_reach` or `applied`
  instead of `not_perceived`, which reveals that the thing exists.
- v2 also gives no order among the kinds. Today the order is `parse_action` (stage 1), then target judgement, then
  `action.check(limits)`, then `_check_region` (`applier.apply`).
- `malformed` and `limit` don't depend on the target, so they may come first. `out_of_reach` is a function of the
  target's position. If it is evaluated before perception, an unperceived target in reach and one out of reach give
  different kinds: a distance oracle by bisection, the same shape as round 1's `point_m` finding.
- `StructureModulator.execute`'s own refusals ("that is another thing called …", "acted on directly, not on …") aren't
  mapped to any kind.

*Fix:*
- Define perception from A's own stimuli. A target is perceived only if some value in A's `BodyFrame` at tick T
  depends on it (or name an ANALOG predicate with its leak stated).
- Fix the order: `malformed` and `limit`, then `not_perceived`, then `out_of_reach`.
- Map every existing refusal string to a kind.
- Add a T11 variation that sweeps an unperceived target's position and existence, holding the receipt kind constant.

**W3. `sem_stimuli.md::§3.2 Build checks`, `§4.5` and `§7.1` check bindings in the worker, while the core consumes
them first.**
- §7.1 places "Binding check" in `adapters/agents` (the worker).
- §4.5 has bindings ride the `join` record, with frames "built and digested from the join tick".
- §3.2 has the core reduce by them. The core therefore runs a binding before any worker has checked it.
- "Build refused" logs `agent_failed(build)` while the core keeps building and digesting with that binding.
- A binding that names a site outside the body, or a `single` binding with two sites, is then an index error or a
  non-finite reduction in the core. §4.3 makes that "a world bug: the server stops loudly".

*Failure:* one malformed per-NPC data file stops the world server, and does so again on every replay of that log.
Malformed input must get an error reply, never a crash (CLAUDE.md, "The client is untrusted input").

*Fix:*
- Run §3.2's checks in the core's binding constructor, behind the `phase1/agents` binding loader's gate, before the
  `join` record is accepted, and refuse the join with a logged reason.
- The worker re-checks only what it alone can see: Maxim sensor names, units and ranges.
- Replay reads `join` through the same gate, so a hand-edited log is refused, not crashed on.

**W4. `sem_stimuli.md::§4.2 BoundFrame` sends positional values, and nothing on the wire checks binding order.**
- `value` is "one per binding, in binding order", with no names.
- `registry_digest` covers "the bound rows": name, unit, site set, `derivation_version`. It doesn't cover the binding
  table, meaning which sensor, which sites, which pooling, in what order.
- The binding table exists twice: in the host's `join` record, and in the worker's own binding data checked at build
  (§3.2, §7.1).
- §4.5's restart "re-sends maps", but nothing compares the two copies. §5's second plant, reversed binding order,
  is caught only on the host, where both digests use the host's copy.

*Failure:* an agent home's binding file is reordered, or edited for a new body. Each tick the worker pushes the hand's
temperature into the foot's sensor. Every digest, replay and handshake check stays green. This is round 1's
"stale name map decodes silently to the wrong rows" again, one level down.

*Fix:*
- Put a `bindings_digest` (canonical binding table) in `welcome` and in each `BoundFrame`, or fold it into
  `registry_digest`, so the worker refuses a mismatch.
- Plant the reorder on the worker side as well.

### NIT

- **W5.** `§6.3`'s table has two header rows, the first with an empty "Catches" column, so it renders broken. T2 is
  missing with no note, which reads as a deleted gate. Fix the header, and say T2 was retired or renumber.
- **W6.** `§2.2`: `tissue_temperature` is "frozen now", and `valid` is an identity field (§2.1), yet the row states
  neither its validity range nor its rounding policy. The decoder's refusals in §4.3 need that value. State it, or say
  that it freezes with the tissue law's PR.
- **W7.** `§11.1`: the body-instance format gets "strict loader, version, gate row, fixtures". The binding format
  and the `BoundFrame` decoder get no gate-registry row, and the receipt (W1) gets no format at all. §5's save
  ("tissue, visibility and pending events") has no version. Name each one's version and gate row, as `fold.md` A-S10
  claims was done.
- **W8.** Two citation residues:
  - `tile_and_client.md` §2.1 also books convection over an exchange volume into `bodies`. §3.1's ledger list leaves
    it out, so it doesn't say whether convection now acts on the skin columns or stays on the core node. Name its one
    receiver, so it isn't booked twice.
  - §6.1's pinned-frame supersession should cite `boundaries.md` §4.2, where the rule is stated, as well as §4.3.

## 3. Leak shapes, after v2

| Leak shape | Caught by | Remaining gap |
|---|---|---|
| Region instrument on the NPC | T13, T8, `agents-reads-body-frames` | indirect imports (S4); environment entity deferred (S5) |
| Material constant | T5, T6, T12 sentinel | the synchronous `execute` return (W1) |
| Another NPC's stimuli | T11, T12 with core and channel plants | none new |
| Entity identity | T11, `caused_by` null, per-NPC `local_id` | none new |
| Existence and position oracles | §6.2's closed vocabulary | the perception predicate and precedence (W2) |
| Outcome text | T7, closed vocabulary | unmapped modulator refusals (W2) |
| Time | T9, host load named | the strip exemption deferred (S3) |
| Malformed values | NaN, ±inf, `1e400`, `bool` planted | malformed bindings crash the core (W3); misordered bindings pass silently (W4) |
