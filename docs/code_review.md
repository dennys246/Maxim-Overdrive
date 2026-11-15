# The pre-push review

Every branch that changes code gets a review round **before it is handed over for push**. A round is several
independent readers, run in parallel, each holding one lens. Their findings are folded into the same branch before
anyone pushes it, never merged first and fixed after. Adapted from Maxim's three-lens review (`docs/CODE_REVIEW.md` in
the Maxim repo), where the record shows that the catches came from a *different* reader, not a more careful one.

## How a round runs

1. **Freeze the diff.** The round covers `git diff main...HEAD` as it is when the round starts. Run
   `scripts/prepush.sh` first; a round is not spent on code that fails its own gate.
2. **Spawn the readers in parallel.** Each gets the diff range, this charter, CLAUDE.md and its lens brief. They do
   **not** get the author's explanation of why the change is right: an agent handed a hypothesis tends to confirm
   it. Commit messages are part of the diff and are fair game, as claims to check.
3. **Each finding is** a severity, a location (`file::symbol`, not a line number, which drifts), and a concrete
   failure scenario: the input or state, and the wrong output or crash.
   - **BLOCKER:** wrong on the shipped path, breaks a standing rule, or a test that cannot fail.
   - **SHOULD-FIX:** a real defect or gap with a narrower trigger, or a rule kept by luck rather than by a check.
   - **NIT:** clarity, naming, small simplifications.
4. **Fold.** Every BLOCKER and SHOULD-FIX is fixed on the branch, or answered in writing with a reason. Fixing it in
   a later PR is allowed only as a `TEMPORARY(phaseN)` marker plus a roadmap or backlog row. NITs are the author's
   call.
5. **Delta round.** After a fold that touches `src/`, `scripts/` or `client/`, rerun the lens whose finding was
   folded, plus wire integrity, on the fold's diff only. Repeat until a round folds nothing in code.
6. **Record.** The fold commit's message lists each finding and what was done. The hand-off note (and the PR
   description) carries the round summary: the lenses run, the counts by severity, and anything deferred.

A docs-only change that makes no new claim about the code needs no round. A docs change that says something works
gets a round, because a claim is a contract.

## The always-on lenses

| Lens | Reads | Asks |
|---|---|---|
| **Executor** | the code in the diff's hunks and its path from a real entry point (server endpoint, `World.advance`, a test) | Does it work on the path that ships? Does every new branch, error path and return value run under a test? Would each test fail if the mechanism were deleted? Does it refuse bad input when it should? |
| **Architecture** | the diff against `docs/architecture.md`, the roadmap and CLAUDE.md | Is this the root cause or a band-aid? Is it the right layer and owner (server vs client, protocol vs transport, world vs bridge)? Does it keep the standing rules? Are the docs and known gaps honest about what it does? |
| **Wire integrity** | every line **outside** the hunks that produces or consumes a contract the diff touches | What does each neighbouring producer and consumer get, before and after? |

**Boundaries.** Executor owns the code inside the hunks. Wire integrity owns everything outside them that touches a
changed contract. Architecture decides whether a contract should exist and where it lives. A lens never drops a
finding because another lens might cover it: two lenses finding the same thing is signal.

### Wire integrity: contracts in this codebase

For every contract the diff adds, removes, renames, re-types, re-defaults or newly reads, one row:

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|

The contract types, with this codebase's examples:

| Type | Examples |
|---|---|
| **Call** | `World.advance`, `heat.step`, `damage.strike`, `imagination.spec.place`; every caller, including tests and scripts |
| **Payload / field** | `snapshot()` keys and dtypes, `ModulatorResult.metadata` keys, `HeatSource` fields |
| **Wire format** | the protocol header, array order and dtypes, intent JSON; the Python server *and* the GDScript client |
| **Persisted state** | save files, scene YAML, rig and material YAML: the writer, the loader and every version check |
| **Vocabulary** | material names, region names, affordance names (`strike`, `ignite`, `extinguish`), intent types, rig names |
| **Gate** | rig profile fields, `MAXIM_OVERDRIVE_*` environment variables, defaults, thresholds such as `GLOW_START_C` |
| **Operator surface** | CLI flags (the rig flag), YAML fields, Godot project settings and input actions |
| **Lifecycle** | connect, handshake, disconnect, turn start and end, source added and removed: does every start have its end on every exit path? |
| **Mirror** | `sem_env/_compat.py` vs Maxim's SEM types; any Python/GDScript pair that decodes the same bytes |
| **Claims** | CLAUDE.md, `docs/`, docstrings and commit messages saying a thing works: is it true on the shipped path? |

An **empty table** is valid only when the diff changes function bodies alone: no signature, field, key, default,
dtype, vocabulary word or file format changes. State it as the list of changed functions, each with the search that
found no other reader.

## The situational lenses

Add each lens whose trigger the diff hits. More readers are cheap next to a defect that ships.

| Lens | Trigger | Asks |
|---|---|---|
| **Physics and resolution** | `world/`, `sem_env/`, materials, rig profiles, scenes | Is there a closed-form test and a cross-tier test? Is energy deposited by cell average or volume overlap? Are parameters per unit volume, and scenes in metres? Are thin features at least two coarse cells thick? Is it deterministic? Are new gaps recorded with numbers? |
| **Trust boundary** | the protocol, intent handling, `imagination.spec`, any file or YAML loader, anything that parses input | Can malformed, hostile or oversized input crash the server, change state partially, or reach the cells unvalidated? Is every rejection path tested? Is the localhost, Origin and token check intact? |
| **Performance** | hot loops, snapshot encoding, the turn loop, shaders, texture uploads | What does it cost at the max profile (about 5×10⁶ cells)? Is anything O(cells) done per message that could be done per turn? Does it stay inside the budgets in `docs/standards_backlog.md` B5? |
| **Client and rendering** | `client/` | Does the client only draw and send intents, computing nothing that feeds back into the world? Is GDScript typed? Do visuals come from the snapshot channels rather than art? Does it read the same at both profiles apart from detail? Is state shown by more than colour? |

## When the reviewers are agents

The author spawns the readers as parallel subagents with these instructions and the diff range. A reader that
returns no findings must still show what it checked (for wire integrity, the table). The author does not decide on
a reader's behalf that a lens has nothing to say.
