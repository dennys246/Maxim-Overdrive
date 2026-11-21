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
   failure scenario: the input or state, and the wrong output or crash. A fix the reader proposes is marked
   *verified*, with what it ran, or *unverified*; the author verifies it before folding.
   - **BLOCKER:** wrong on the shipped path, breaks a standing rule, or a test that cannot fail.
   - **SHOULD-FIX:** a real defect or gap with a narrower trigger, or a rule kept by luck rather than by a check.
   - **NIT:** clarity, naming, small simplifications.
4. **Fold.** Every BLOCKER and SHOULD-FIX is fixed on the branch, or answered in writing with a reason. Deferring a
   code finding is allowed only as a `TEMPORARY(phaseN)` marker listed under that phase in `docs/roadmap.md` (the
   lint checks both). A finding with no code to mark (a missing check, a process gap) is deferred as a row in
   `docs/standards_backlog.md`, or as a known gap in `docs/architecture.md` for physics. NITs are the author's call.
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
| **Architecture** | the diff against `docs/architecture.md`, the roadmap and CLAUDE.md | Is this the root cause or a band-aid? Is it the right layer and owner (server vs client, protocol vs transport, world vs bridge)? Does it keep the standing rules? Are the docs and known gaps honest about what it does? Does each new or grown function, class and module keep one job and one reason to change, or is it becoming a god object? Was a size limit met by splitting along a responsibility, or by cutting at the line count? |
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
| **Call** | `World.advance`, `heat.step`, `damage.strike`, `imagination.place`; every caller, including tests and scripts |
| **Payload / field** | `snapshot()` keys and dtypes, `ModulatorResult.metadata` keys, `HeatSource` fields |
| **Wire format** | the protocol header, array order and dtypes, intent JSON; the Python server *and* the GDScript client |
| **Persisted state** | save files, scene YAML, rig and material YAML: the writer, the loader and every version check |
| **Vocabulary** | material names, region names, affordance names (`strike`, `ignite`, `extinguish`), intent types, rig names |
| **Gate** | rig profile fields, `MAXIM_OVERDRIVE_*` environment variables, defaults, thresholds such as `GLOW_START_C` |
| **Operator surface** | CLI flags (the rig flag), YAML fields, Godot project settings and input actions |
| **Lifecycle** | connect, handshake, disconnect, turn start and end, source added and removed: does every start have its end on every exit path? |
| **Mirror** | `simcore/adapters/sem/_compat.py` vs Maxim's SEM types; any Python/GDScript pair that decodes the same bytes |
| **Claims** | CLAUDE.md, `docs/`, docstrings and commit messages saying a thing works: is it true on the shipped path? |

An **empty table** is valid only when the diff changes function bodies alone: no signature, field, key, default,
dtype, vocabulary word or file format changes. State it as the list of changed functions, each with the search that
found no other reader.

## The situational lenses

Add each lens whose trigger the diff hits. More readers are cheap next to a defect that ships.

| Lens | Trigger | Asks |
|---|---|---|
| **Physics and resolution** | `simcore/core/`, `simcore/adapters/sem/`, materials, grid spacings, scenes | Is there a closed-form test, through `simcore.verify` with space and time refined apart, and a cross-grid test where the truth grid agrees with the reference and converges from the coarse grid? Is energy deposited by cell average or volume overlap? Are parameters per unit volume, and scenes in metres? Are thin features at least two coarse cells thick? Is it deterministic? Are new gaps recorded with numbers? Does any law apply a threshold or a non-linear rate to a cell's mean where the outcome depends on structure inside the cell (CLAUDE.md, "Reconstruct, decide at the point, integrate upward")? Does any consumer read raw cells instead of a reduction at its own scale? |
| **Trust boundary** | the protocol, intent handling, `simcore.core.imagination`, any file or YAML loader, anything that parses input | Can malformed, hostile or oversized input crash the server, change state partially, or reach the cells unvalidated? Is every rejection path tested? Is the localhost, Origin and token check intact? |
| **Performance** | hot loops, snapshot encoding, the turn loop, shaders, texture uploads | What does it cost at the max profile (about 5×10⁶ cells)? Is anything O(cells) done per message that could be done per turn? Does it stay inside the budgets in `docs/standards_backlog.md` B5? |
| **Client and rendering** | `client/` | Does the client only draw and send intents, computing nothing that feeds back into the world? Is GDScript typed? Do visuals come from the snapshot channels rather than art? Does it read the same at both profiles apart from detail? Is state shown by more than colour? |
| **Bio-faithful integration** | anything an NPC senses, acts through, or keeps time by: `simcore/adapters/sem/`, percepts built from world state, agent intents, the world clock and day, the thinking and substrate lanes, any call into Maxim; and every design review | Does each Maxim mechanism get to do its **real job**, not a caricature of it? (Maxim's own question, from its design-review charter.) Does the world produce every signal an NPC uses through play (a percept from cells, light or sound), or does the game hand the NPC a number it could never sense? Are Maxim's systems driven the way their briefs and `Bio-mapping:` tags say they work (the SCN entrained by time cues, a reflex under one-way suppression from deliberation, forgetting on experience time)? Is every divergence named, ideally as Maxim's EARN, ANALOG or OPEN intent (`docs/plans/bio_faithful_roadmap.md` in Maxim)? Does anything need a Maxim change, and is it listed under Phase 3 instead of patched around here? Does the game's evidence show that a Maxim plan, decision or default is wrong? If so, the finding names it and proposes the pushback (CLAUDE.md, "Push back on Maxim"). Does every proposal or ask to Maxim cite what Maxim's `origin/main` already has or plans on the topic, or say what was searched and found nothing (CLAUDE.md, "Search Maxim before proposing to it")? |
| **Determinism and replay** | the tick loop, intent ordering, the intent log, anything with threads, processes or queues, anything that could read a clock | Do the same scene, rig and intent log give bit-identical state, whatever the thread scheduling, the dial, the wall-clock latency or the hash seed? Can any wall-clock value, arrival order or non-deterministic result reach `World` without first being recorded in the log? Does a replay ever call something live (a model, a clock)? |
| **Concurrency and lanes** | threads, processes, channels, locks, the host's lifecycle | Does only the simulation lane touch `World`? Is every message crossing a lane frozen? Can a lane deadlock, starve or grow a queue without bound? Does every start have a stop on every exit path, including a crash in one lane? Is each lane metered against its own budget? |

## Design reviews

A design that changes the architecture (a new subsystem, a new contract, a reversed decision) is reviewed **before
code**, on the design document. The readers are Executor (are the design's claims about the existing code and its
numbers true?), Architecture and Wire integrity, plus each situational lens the design will trigger once it is
built, **always including Bio-faithful integration**. Findings use the same severities. A BLOCKER stops the build
until it is folded or overruled by the owner with a recorded reason. Each lens's findings are kept verbatim in
`docs/design/reviews/<design>/<lens>.md`, because they explain why the design is what it is. The author then folds
them into the design and presents one plan to the owner before building.

- **A delta round on a design reviews the fold's diff,** and Wire integrity also reads every section that uses a
  contract the diff changes. The fold table says how the author verified each fix (step 3).
- **When the rounds stop** (CLAUDE.md, "Review finds; it doesn't design"): the author proposes the move and the owner
  accepts it, which is the recorded overrule this section requires. Only findings about mechanisms move, each
  recorded `deferred` by a reviewer with its build step as the trigger. A contract BLOCKER still folds, or the owner
  overrules it with a recorded reason.

## When the reviewers are agents

The author spawns the readers as parallel subagents with these instructions and the diff range. A reader that
returns no findings must still show what it checked (for wire integrity, the table). The author does not decide on
a reader's behalf that a lens has nothing to say.
