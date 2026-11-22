# Architecture review: step 5a PR 1, the `Simulation` shell (`origin/main...553abca`)

Reviewer: Architecture lens, read-only. I read CLAUDE.md, `docs/code_review.md`, `sim_core.md` §1–§5.1, §12–§14,
`boundaries.md` §2.2 and §6, the diff, `applier.py`, `world.py::advance`, `checks.py` and the import contracts. I
ran `lint-imports` in the worktree (9 kept, 0 broken). I ran no tests.

**Counts: 0 BLOCKER, 5 SHOULD-FIX, 4 NIT.**

The shell is small and its `step` is the short orchestration §2 asks for. No god object is forming: `Simulation` has
five public members, `Clock` and `SimConfig` each have one job, and validation sits apart from application. Where it
falls short is the record type, `LogRecord`. It sits in the wrong layer, and its shape covers only today's three
actions, so PR 4 (the log) will have to move it and reshape it. That rework is cheap now, while tests are its only
callers.

## SHOULD-FIX

**S1. `src/simcore/core/simulation.py::LogRecord` sits in the wrong layer, and the membrane will be unable to build
one.**
- `boundaries.md` §2.2 puts "the intent record" in layer 5b (`engine.intents`). `sim_core.md` §2 places only `Clock`,
  `SimConfig`, `TickReport` and `WorkCounters` with the simulation.
- This diff puts `LogRecord` and `WORLD_ACTION_RANK` in `simcore.core.simulation`, and in the same change adds that
  module to `membrane-reads-frames`'s forbidden list in `pyproject.toml`.
- Failure scenario: `sim_core.md` §13 has the bridge's `execute` "submit its record" to a submit-and-step port until
  `phase1/agents`. To submit a record, the bridge must import `LogRecord`, and the contract this PR adds refuses that
  import.
- PR 4 then has two choices: move the type, or weaken the membrane contract. The protocol's stage-1 decode
  (`boundaries.md` §6.1: decode → stage 1 → log) would also have to import the simulation module just to build the
  record it hands to the simulation.
- Fix: move `LogRecord` and the `kind_rank` constant into `simcore.core.intents`, which the membrane already
  imports, and keep `simulation` forbidden to the membrane. Unverified: I didn't make the move or run the contracts
  on it.

**S2. `LogRecord`'s shape covers world actions only, so PR 4's full record breaks its callers instead of extending
it.**
- Three things assume every record is a world action:
  - `action: Action` and `target: str` are required fields;
  - `kind_rank` returns 30 unconditionally;
  - `step` sends every record to `self._applier.apply(r.target, r.action)`.
- §6.1 and §14 require the log to carry more than world actions: host commands at rank 40 (advance, rig selection,
  save, load, admin `set_material`), controls at rank 10 (pause, the dial), and `imagine`. None of these is an
  `Action`, and most have no target.
- §6.2's full record also needs required fields with no sensible default: `schema_version`, `observed_tick` and
  `issued_tick`. Every construction site breaks when they arrive.
- §6.2 names the typed payload `params` and makes `kind` a field. Here `kind` is a derived property, and the payload
  is called `action`.
- Failure scenario: PR 4 adds a `pause` control. There's nowhere to put it. The type has to become a payload union
  with `kind_rank` looked up per kind, and `step`'s apply line has to dispatch by kind.
- Fix: rename now to §6.2's names (`params` typed as `Action`, with `kind_rank` read from a per-kind table rather
  than a constant), so PR 4 widens types instead of renaming fields. Unverified.

**S3. `src/simcore/core/simulation.py::Simulation.__init__(world, *, config)` is an unmarked band-aid, and its
removal moment is wrong.**
- The commit message calls the World seam "interim". CLAUDE.md requires a scheduled band-aid to carry a
  `TEMPORARY(phaseN/step): …` marker and a roadmap entry. This one has a docstring and nothing else, so the lint
  can't see it.
- Leak check:
  - The shell itself is clean. There is no public `world` accessor, and the membrane can't import `simulation` or
    `world`.
  - Any caller that uses `__init__` still holds the World. It can call `world.advance` or build a second
    `Applier(world)` and hand it to the bridge, as the shipped bridge path does today. Those writes bypass `step`'s
    key order and the clock, and `Simulation.tick` then drifts from `World.turn` and `grid.time_s`.
  - Nothing on the shipped path calls `Simulation` yet, so this is latent. No scan stops `__init__` from becoming the
    constructor the host uses.
- The removal moment is wrong. The docstring says construction moves into `from_scene` in PR 2. But every
  bit-identity test, and most of the others, need the World handle to compute `digest(world)`. `Simulation` exposes
  no digest until PR 4's per-tick digest.
  - Failure scenario: PR 2 can't drop the seam without losing the state comparison, so the seam silently survives
    into PR 4 with a docstring that has become false.
- Fix: mark it `TEMPORARY(phase1/<5a branch>)`, naming the PR that actually removes it, list `simulation.py` in the
  roadmap, and restrict `__init__` to tests until then (an ownership-scan rule, or a keyword-only private factory).
  Unverified.

**S4. `simulation.py::_whole` and `LogRecord.__post_init__` validate identity with a second, weaker rule than
`checks.py`'s.**
- CLAUDE.md says every untrusted number becomes a whole number in `checks.py`, and identity keys pass
  `checks.identity_key`. This diff adds `_whole` instead of using `checks.whole_number`, and the two differ:
  - `_whole` refuses `numpy.int64`, which `numbers.Integral` accepts;
  - it raises a bare `ValueError` with no `RefusalCode`.
- `actor_id` is checked only as a non-empty `str`, so it accepts `"a:b"`, `" npc"` and a 10 kB string.
  `identity_key` refuses all three.
- Failure scenario: PR 4 builds records from decoded wire input. An actor id containing `:` lands in the ordering key
  and the c14n log. Then `identity_key` refuses the same id at the agent seam, so one identity has two rules.
- `apply_us` has no upper bound. §6.2 defines it as an int64 offset within the tick, so it must stay below `tick_us`.
  `step` has the config and could check that, but doesn't.
- Fix: use `whole_number` and `identity_key`, and check `apply_us < tick_us` in `_check_batch`. Unverified.

**S5. The phase1/sim-clock markers this PR touches now give a false reason.**
- `world.py::World.advance`, `applier.py::Applier.apply` and `imagination.py::place` each carry
  `TEMPORARY(phase1/sim-clock): … until Simulation.step exists`. The roadmap (lines 48–52) still says
  "`phase1/sim-clock` moves both into `Simulation.step`".
- After this diff, `Simulation.step` exists and neither of those moves has happened. `phase1/sim-clock` is already
  merged (#36).
- Failure scenario: a reader or the marker lint takes the markers as describing pending work for a branch that has
  closed. The real removal moments are 5a's PRs 2–4, and no marker names them.
- Fix: in this PR, rewrite the three reasons and the roadmap bullet to name the 5a PR that removes each one. Not a
  code change. Unverified.

## NIT

- **N1. `simulation.py::TickReport.outcomes` correlates with records by position only.** The host's receipt id is
  `(actor_id, seq)` (§6.1), and PR 4's logger will have to zip outcomes back to records. Keying each outcome by its
  record's `key` puts that invariant into the type.
- **N2. `LogRecord.kind` returns `"extinguish"`, but §14's v0 log vocabulary spells it `douse`.** The comment admits
  it. Name the PR that renames it, or PR 4's golden fixtures will record the wrong word.
- **N3. Frames are still published at each write window's close, not once per tick.** A tick with two records and
  physics publishes three frames, and their stamps are `World` sequence numbers rather than ticks. This is
  behaviour-preserving and §12 lists it as a break owed to 5a. The commit's PR 2–4 list doesn't say which PR owns
  "publication cadence, frame stamps".
- **N4. `Simulation.step` checks the batch at runtime.** A validated `TickBatch` type, built by the host or log reader,
  would carry "one tick, strictly increasing keys" in its type and keep `step` to orchestration. This is optional:
  the runtime check is correct and tested.

## What holds up (checked, no finding)

- **Layering and classification.** `simulation` imports only core modules (applier, frames, intents, limits,
  materials, scene, world). It joins `CORE_PUBLIC_SURFACE` and is subtracted from `MEMBRANE_SURFACE`, consistent with
  `world`. The skip-layer contract lets adapters and protocol import it, matching §2.2's "only `engine.sim`'s public
  surface". `lint-imports`: 9 kept.
- **Shape of `step` for PRs 2–4.** Apply, then physics on physics ticks, then advance the clock maps onto D10 steps 1,
  6 and 8. Per-record laws (`damage.loads`) slot in after each apply. Replacing `self._world.advance(...)` with the
  law groups is local to one line. The phase rule `T % physics_every == 0`, with tick 0 as construction, matches §3.
- **`SimConfig`.** It is frozen, stores integers only, and derives `physics_seconds` (exact for T3) without storing
  it. `substep_refine` joins in PR 3 as a field with a default, so callers don't break.
- **Bit-identity.** The tests compare against a direct-World path, and the commit names their lifetime (until PR 3).
  That is the honest strangler pattern.
- **The applier stays private** (§4). `Applier` is not exposed from `Simulation`.

## Fold status

Every finding above is `open`. A reviewer sets each status after the fold, read from the tree.
