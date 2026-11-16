# CLAUDE.md

Maxim Overdrive is a cyberpunk RPG set in **Maxim Prime**, where every NPC is a [Maxim](https://github.com/dennys246/Maxim)
agent (`pymaxim`) with a life it actually lived. This repo holds the **world server** (Python, authoritative) and,
from Phase 1, a **Godot 4 client** in `client/` that only draws snapshots and sends intents.

Read these first: `docs/architecture.md` (the design and why), `docs/roadmap.md` (phases, exit tests, standing rules)
and `docs/book_to_world.md` (the book-to-world plan).

## First principle: brutal honesty

This comes before every other rule in this file. The owner wants the truth, not comfort, and engineering this
serious depends on it.

- **No sycophancy, no sugar-coating.** Say what is true, including when it's unwelcome, when it contradicts the
  owner, and when it shows your own earlier work was wrong. Don't praise an idea to be agreeable: agree when you
  agree, and say why. Guard: B16
- **Raise a problem the moment you see it.** Tell the owner in plain words what's wrong, how bad it is, and what
  fixing it costs. Never sweep it under the rug: no silent deferral, no burying it at the end of a long message,
  no quietly choosing the smaller fix. Guard: B16
- **Report results exactly as they are.** Failing tests with their output, skipped steps, numbers that came out
  worse than claimed, claims that turned out false. "Done" means done and verified, and anything less is named for
  what it is. A correction of your own earlier claim goes first in a message, not last. Guard: B16
- **Disagree when you disagree.** Give the reasons and the evidence, then do what the owner decides, and record the
  decision. Guard: B16

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'   # Python >= 3.10; the gate needs both extras
.venv/bin/pytest                            # laptop + rig profiles, a few seconds; run the module you touched first
MAXIM_OVERDRIVE_ALL_TIERS=1 .venv/bin/pytest  # adds the 0.05 m max profile (about a minute)
scripts/prepush.sh                          # the full gate: lint, types, standards, every tier, coverage, diff coverage
```

`[maxim]` is optional for running the server, but the gate needs it: mypy checks the SEM bridge against Maxim's own
classes, and `tests/test_sem_compat.py` compares the mirror with whichever pymaxim is installed. A pymaxim release
that changes those classes turns the gate red with no local change; that is the drift check working, so update the
mirror rather than pinning it away. In a worktree without its own `.venv`, run `PYTHON=<venv>/bin/python
scripts/prepush.sh`.

Godot 4.7.2 is installed at `/Applications/Godot.app` (binary: `Contents/MacOS/Godot`).

## Layout

- `src/maxim_overdrive/config.py`: rig profiles and the material table (`data/rigs/`, `data/materials/`)
- `src/maxim_overdrive/world/`: `grid.py` (cells), `scene.py` (authoring in metres), `heat.py`, `damage.py`,
  `world.py` (turn loop, heat sources, `snapshot`)
- `src/maxim_overdrive/sem_env/bridge.py`: environment regions as Maxim SEM Entities
- `src/maxim_overdrive/imagination/spec.py`: imagined objects as validated specs that become cells
- `scripts/`: `prepush.sh` (the gate) and `lint_standards.py`
- `docs/code_review.md`: the pre-push review charter. `docs/standards_backlog.md`: rules waiting for a check
- `docs/maxim_upstream/`: drafts that belong in the Maxim repo (the Exp 64 pre-registration)
- `docs/lessons_maxim_in_games.md`: what building this game teaches about applying Maxim to games, kept current

## Rules that matter here

- **The resolution rule:** a rig profile may change precision, never the outcome class. Any new physics ships with a
  closed-form test and a cross-tier test (`tests/test_heat.py` and `tests/test_cross_tier.py` are the patterns). If
  a cross-tier test fails, fix the physics; never loosen the test to pass.
- Author scenes in metres. Keep physics parameters per unit volume. Deposit energy by exact cell average or volume
  overlap, never by whether the cell centre is inside.
- **Reconstruct, decide at the point, integrate upward.** Never apply a threshold or a non-linear law to a cell's
  mean when the outcome depends on structure inside the cell: averaging then thresholding is not thresholding then
  averaging, and the difference grows with the cell size. Reconstruct the sub-cell profile (from neighbours, or a
  surface model sized in metres), evaluate the law on it, and integrate over the cell. Every consumer reads at its
  own scale: NPC sensors as reductions over volumes in metres, zones as integrals, the client at its own level of
  detail; none of them reads "a cell". Fineness is spent where the gradients are. Binary outcomes (breached,
  ignited) keep a band near their threshold however fine the cells are, so they are gated with an outcome margin.
- Thin features must be at least two cells of the coarsest rig thick.
- The world server is authoritative. The client never computes anything that feeds back into the world; it may add
  purely visual effects.
- The SEM bridge uses Maxim's frozen types (`SensorReading`, `ModulatorResult`, `AffordanceSchema`, `Entity`).
  `sem_env/_compat.py` mirrors the three dataclasses field for field, with the same flags and slots
  (`tests/test_sem_compat.py` holds it to that); without pymaxim there is no `Entity`, and `to_maxim_entity` refuses.
  Don't add fields Maxim doesn't have.
- Imagined objects enter only through `imagination.spec.place`, which validates them. Never write cells directly
  from LLM output.
- Actions change cells; only `World.advance` moves time.
- Record known physics gaps in `docs/architecture.md` ("Known gaps"), with numbers, instead of hiding them.

## Engineering standards

Treat this as a serious engineering project from the first commit. Each rule ends with `Guard:`, naming the check
that enforces it, or, for a rule held only by review or attention today, a row in `docs/standards_backlog.md`, so
the gap is visible. A document is not a check: a rule guarded only by `docs/` must cite a backlog row too.
`scripts/lint_standards.py` fails if a rule loses its guard, and prints how many rules a check enforces and how many
only review holds.

### Fix root causes

- **No band-aids.** Fix the root cause, even when that means stepping back and refactoring. A band-aid is anything
  that hides a symptom: a special case, a swallowed exception, a flag that routes around broken behaviour, a
  loosened tolerance, a fix that has to be repeated at each call site. If the root fix is bigger than the task, stop,
  describe the root cause and the scope of the real fix, and ask. Never quietly pick the smaller fix.
  Guard: `docs/code_review.md` (the Architecture lens asks this of every diff), B1
- **The one exemption: a marked, scheduled band-aid.** Allowed only when the plan already has a moment that removes
  it. Mark it in the code as `TEMPORARY(phaseN[/step]): <why, and what the real fix is>`, and list its file under
  that phase in `docs/roadmap.md`. The lint fails on a marker with no reason, an unknown or finished phase, or a file
  the phase doesn't list, so every open band-aid shows in the roadmap. A finding with no code to mark is deferred as
  a backlog row or a known gap instead. Guard: `scripts/lint_standards.py::check_markers`
- **When debugging stalls, audit the layer beneath.** If two explanations for a bad result have died, stop
  generating a third. Check what else changed, and whether the action you commanded actually happened (did the fire
  actually get added, did the message actually arrive) before theorizing about the sensor. Guard: B1 (review asks how
  a fix was found)

### Testing

- **Every behaviour change ships with its tests in the same commit.** A bug fix starts with a test that reproduces the
  bug and fails. Guard: `scripts/prepush.sh::diff_cover` (changed lines must run under a test), B1 (same commit,
  red first)
- **Critical functionality is tested exhaustively, by kind.** Physics: a closed-form test and a cross-tier test.
  Trust boundaries (protocol, intents, `imagination.spec`, every loader): every rejection path, aiming at 100% branch
  coverage. Wire and save formats: a round trip plus committed golden fixtures. Determinism: a bit-identical rerun.
  Guard: `tests/test_cross_tier.py`, `tests/test_imagination.py`, `tests/test_determinism.py`, B3, B4
- **Coverage only ratchets up.** Branch coverage must stay above `fail_under` in `pyproject.toml`; raise the floor
  when coverage rises, never lower it. Coverage measures `src/` and `scripts/`. Lines changed on a branch must be at
  least 95% covered. A `pragma: no cover` must say why (`# pragma: no cover - <why>`), and reviewers question it.
  Guard: `pyproject.toml::fail_under`, `scripts/lint_standards.py::check_coverage_ratchet`,
  `scripts/lint_standards.py::check_markers`, `scripts/prepush.sh::diff_cover`,
  `tests/test_tooling_config.py::test_coverage_measures_branches_over_src_and_scripts`
- **Prove a guard by deleting what it guards.** Before claiming a test protects something, break the mechanism and
  watch the test go red, and say so in the commit message. A test that cannot fail is a BLOCKER.
  Guard: `docs/code_review.md` (Executor lens), B10
- **Known-broken behaviour gets a strict red gate,** `pytest.mark.xfail(strict=True)` with a reason, never `skip`.
  When the fix lands the gate flips and must be removed. Warnings are errors.
  Guard: `tests/test_tooling_config.py::test_red_gates_are_strict_and_warnings_are_errors`
- **Property tests for invariants over input spaces** (Hypothesis): physics conservation, protocol round trips,
  validators that never crash on any input. Guard: B9
- **Tests are deterministic and fast.** No sleeps, wall clock, real network beyond localhost, or LLM calls in tests.
  Mark anything over a few seconds `slow` and gate it behind a tier variable. Guard:
  `tests/test_determinism.py::test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism` (RNG, clock,
  sleep), B1 (network and LLM calls)

### Review before push

- **Every branch that changes code gets a pre-push review round:** parallel independent readers, always Executor,
  Architecture and Wire integrity, plus each situational lens the diff triggers (Physics and resolution, Trust
  boundary, Performance, Client and rendering, Bio-faithful integration, Determinism and replay, Concurrency and
  lanes). Findings are BLOCKER, SHOULD-FIX or NIT with a `file::symbol` and a failure scenario. They are folded into
  the same branch before hand-off, with delta rounds after code folds. The hand-off note carries the round summary.
  Charter: `docs/code_review.md`. Guard: B1
- **A design that changes the architecture is reviewed before code,** on its design document, and Bio-faithful
  integration is always one of its lenses. Each lens's findings are kept in `docs/design/reviews/`.
  Guard: `docs/code_review.md` ("Design reviews"), B1
- **`scripts/prepush.sh` must print `prepush: PASS <sha>` for the exact commit handed over.** It refuses a dirty
  tree (`ALLOW_DIRTY=1` checks work in progress but says the result doesn't count). Rerun it after every fold.
  Guard: `scripts/prepush.sh::HEAD_SHA`, B11

### Game engineering

- **Determinism.** The same scene, rig and intents give bit-identical state on one machine. Across machines only the
  outcome class is promised, as with rigs. Randomness, when it arrives, comes from one seeded `numpy.random.Generator`
  owned by `World`. Time comes from `World.advance`, never the wall clock. No builtin `hash()` in the simulation.
  Guard: `tests/test_determinism.py::test_runs_in_processes_with_different_hash_seeds_agree`,
  `tests/test_determinism.py::test_the_simulation_and_tests_have_no_hidden_sources_of_nondeterminism`
- **Replays are first-class.** The intent log plus the scene and rig reproduce any session. It is the bug report, the
  regression test and the save format's backbone. Guard: B2
- **Every format is versioned:** wire protocol, saves and scene files. Readers refuse versions they don't know, loudly.
  Old fixtures stay committed, and a format change that breaks one needs a migration or a version bump. Guard: B3, B4
- **The client is untrusted input.** Every intent is validated at the protocol layer. Malformed input gets an error
  reply, never a crash or a half-applied change. The server binds to 127.0.0.1, refuses any handshake carrying an
  `Origin` header, and requires the per-launch token. Imagined and authored geometry is validated where primitives
  are made. Guard: `tests/test_imagination.py::test_the_world_refuses_impossible_objects`, B3, B14
- **Performance has budgets, measured, not guessed:** turn time and snapshot size per profile, with a regression gate.
  Optimize only from a profile. Guard: B5
- **Client standards (Godot).** The engine version is pinned (4.7.2), and an upgrade is its own branch. GDScript is
  fully typed, with typed-GDScript warnings as errors. Visuals come from snapshot channels, not art. State is never
  shown by colour alone (cracks also change shape and shading, glow also changes brightness). Guard: B6, B7
- **Exit tests are automated where they can be:** a scripted scenario plus golden screenshots per profile, then a
  human playtest. Guard: B7
- **Data and assets.** Tunables live in `data/` YAML, not code, and every data file loads and validates in a test.
  Every non-code asset is listed with its source and licence before it is committed. Never commit the Steamworks SDK,
  licensed third-party assets or `.env` files. Guard: B8, B12

### Code

- **Lint, format and type-check clean:** ruff (rules in `pyproject.toml`), and mypy strict on `src/` and
  `scripts/` with test bodies checked too. Guard: `scripts/prepush.sh`,
  `tests/test_tooling_config.py::test_mypy_is_strict`
- **No silent exception swallows.** Catch the narrowest type, and handle it by reporting or re-raising. A handler
  that quietly returns a fallback is a swallow too.
  Guard: `tests/test_tooling_config.py::test_the_no_silent_swallow_rules_are_selected_and_not_ignored`, B13
- **Separation of concerns; no god functions.** Every module, class and function has one job and one reason to
  change. A function either decides or does; orchestration reads as a short list of named steps, and each step lives
  where its concern lives. Once the boundaries design lands, packages import only downward through its layers. No
  check can see a mixed concern, so review holds this and the size tripwires below only catch its symptoms.
  Guard: `docs/code_review.md` (the Architecture lens asks it of every diff), B19
- **Size tripwires.** Hard limits in `src/` and `scripts/`: a 40-line function body (code lines: the docstring,
  comments and blank lines don't count), a 500-line module and 12 public methods per class, properties included
  (`[tool.maxim_overdrive.size_limits]`). Ruff caps cyclomatic complexity at 10, plus branches, returns and
  statements, in `tests/` too (tests waive only the statement count). Code that reaches a limit is split along a
  responsibility, never cut at the line count, and never silenced with a `noqa` or a ruff config. The limits only
  tighten; the ratchet compares with the base branch, and until the base carries the table the lint says it has
  nothing to compare. Guard: `scripts/lint_standards.py::check_sizes`, `scripts/lint_standards.py::check_size_ratchet`,
  `tests/test_tooling_config.py::test_ruff_enforces_each_complexity_cap_at_its_threshold`,
  `tests/test_tooling_config.py::test_ruff_lints_every_tracked_python_file`
- **Push invariants into types.** A collaborator that must be passed is a required keyword-only parameter, so
  forgetting it is a `TypeError`, not a silent no-op. Prefer frozen dataclasses for anything that crosses a wire or
  is persisted. Guard: `docs/code_review.md` (Architecture lens), B1
- **A fix ships with a caller.** New code with no caller on the shipped path is capability, not a fix. A claim about
  what works is measured on the shipped path, and the commit says where. Guard: `docs/code_review.md` (Wire
  integrity lens), B1

### Working

- **Branches and commits.** Work on `phaseN/<step>` branches with clear, signed commits. Never bypass signing or
  hooks. Never push: the owner reviews and pushes. Concurrent sessions each use a worktree under `.worktrees/`.
  **When signing fails** (the passphrase prompt timed out or was cancelled), try once more: the first attempt often
  only raises the prompt. If the second fails too, stop and ask the owner to answer the prompt; they're probably in
  another window. Don't retry beyond that, and don't change the GPG cache settings. Keep working on anything that
  doesn't need a commit, and say what's waiting.
  Guard: B1 (the .gitignore entry for .worktrees/ is not a check)
- **Keep Maxim untouched from here.** Anything that needs a Maxim change goes under Phase 3 in `docs/roadmap.md` and
  follows Maxim's own process, which depends on the kind of change: a sub-plan or a change to Maxim's `src/` gets a
  three-lens review before its PR opens (Maxim `CONTRIBUTING.md`); a new experiment gets a pre-registration, a
  four-lens design review and a ledger entry (Maxim `CLAUDE.md`). Game runs never go on Maxim's results ledger.
  Guard: `docs/roadmap.md`, B1
- **Push back on Maxim where the game shows it's wrong.** Guiding Maxim through a real application is a pillar goal
  of this project. When the game's evidence contradicts a Maxim plan, decision, default or assumption (a clock, a
  deferred trigger, a recorded rationale), propose the change in Maxim. Name the decision you're arguing against,
  bring the evidence from here (numbers, a failing scenario, a review finding), and go through Maxim's own process.
  Never work around it in this repo, and never stay quiet because the decision was recorded. Each proposal is an
  item under Phase 3 in `docs/roadmap.md`, with its draft in `docs/maxim_upstream/` when it needs one.
  Guard: `docs/code_review.md` (the Bio-faithful integration lens asks it), B15
- **Record lessons as they're learned.** Whenever the work teaches something about putting Maxim into a game (a
  finding, a measurement, a pushback, a design reversal), add or update an entry in `docs/lessons_maxim_in_games.md`
  in the same commit as the work that taught it, with its evidence and its consequence. Don't save lessons for a
  session's wrap-up: a lesson that lives only in a conversation is lost. This file is the seed of an engine's
  documentation and the evidence base for pushbacks to Maxim. Guard: B18
- **Engine choices get a one-line why** in the code or the commit (scene tree, node types, shaders, GDScript vs C#),
  for a team learning Godot. Guard: B1
- **Teach game engineering as you go.** The owner is learning game development from the start, and knows software
  engineering and machine learning well. In every reply, explain the game-engineering concepts the work touches, in
  depth and from first principles, including the everyday ones a game developer takes for granted: the game loop
  and fixed timestep, level of detail, streaming, collision, rendering passes and shaders, netcode and
  authoritative servers, save systems, asset pipelines, simulation stability. Say what the concept is, why games
  do it that way, and what it costs or trades off, and tie it to what it means here. Don't explain general software
  or ML. Guard: B17

## Licensing

Code is Apache-2.0; story, characters, lore, art and audio are all rights reserved (`ASSETS_LICENSE.md`).
