# Review of `foundations_plan.md` (72bf36c): standards and process

Lens: every step the plan prescribes, checked against CLAUDE.md as of `phase1/standards` (87593fe), its backlog,
`docs/code_review.md` and `scripts/prepush.sh`. Read-only; nothing in the repo was changed except this file.

**Counts:** 4 BLOCKER, 14 SHOULD-FIX, 5 NIT.

What I ran, so these claims can be checked:
- `docs/plans/check_plan.py` passes (`0 missing`). It also passes ruff under both design-v2's and standards'
  `pyproject.toml`, and `mypy --strict`, when run by hand.
- Proof by deletion, run on a copy: removing `O19` from the plan, or §5.1's item 4, makes it go red. Removing the
  `### 12.1` heading from the source crashes it with an `IndexError` instead of reporting the problem.
- `phase1/realtime-design`'s marker lint (`check_markers`), run over design-v2's tracked files, finds one problem
  (S12).
- `git ls-remote origin`: `phase1/design-v2` is at `72bf36c` and `phase1/standards` at `87593fe`.

## BLOCKER

**B-1. Steps 3 and 4 would need a force-push, which the pushing rule forbids.**
`foundations_plan.md::§3 rows 3–4`.
- PR #2 (`2f200b5`) and PR #4 (`72bf36c`) are both already on origin. Rebasing either one rewrites published
  commits. Bringing the PR up to date afterwards then needs `git push --force`.
- CLAUDE.md (standards, "Branches and commits") says a session "never force-pushes".
- Scenario: the session does step 4 and the push is refused. It either breaks the rule or leaves PR #4 showing the
  stale base.
- `boundaries.md` §11.3 (W1) also assumes rebases.
- Fix: choose one route and record the choice.
  - Merge `phase1/standards` into each branch. This rewrites nothing.
  - Or push the rebased branch under a new name and open a new PR.
  - Or have the owner record an exception to the force-push rule, or do the force-push themselves.

**B-2. Step 7's position contradicts every linked document, and its own red-first test 4 would have no caller.**
`foundations_plan.md::§3 row 7`.
- The plan puts `phase1/agents` right after `phase1/gates`. Three linked documents put it after `phase1/sim-clock`
  and before `phase1/lanes`:
  - `docs/roadmap.md` Phase 1: "after the clock and before the lanes";
  - `world_model.md` §10 row 9b;
  - `boundaries.md` §11.1.
- The plan also leaves out `world_model.md` §10 rows 3–4 (verify, sim-clock) altogether.
- Test 4 ("resume at the modelled landing tick") needs the integer tick that sim-clock introduces. Without
  `Simulation`, the agent port has no caller on the shipped path, which breaks "A fix ships with a caller".
- The linked documents also disagree with each other about the worker:
  - `world_model.md` row 9b puts "the worker channel and its codec… in a spawned worker" in `phase1/agents`;
  - `boundaries.md` §11.1 says "the worker processes… arrive with `phase1/lanes`".
- The plan's rule "the linked document wins" can't settle a disagreement between two linked documents.
- Fix: put sim-clock (and verify, or a stated reason to skip it) before step 7. Reconcile where the worker lands in
  `boundaries.md` §11.1 and `world_model.md` §10, then cite the reconciled text.

**B-3. Step 5's preconditions are incomplete, and they form a cycle with step 8.**
`foundations_plan.md::§3 rows 5 and 8`.
- (a) The plans contradict each other on part 3:
  - `world_model.md` §10 row 2 and `boundaries.md` §11.1 require parts 1, 2 and 3 to be accepted before 2b
    (`phase1/boundaries`).
  - Part 3 is the plan's step 8, and step 8 is blocked by step 5.
- (b) Step 5 needs owner answers that the plan never lists:
  - `boundaries.md` §12 Q1, the engine's package name. The rename touches about 70 references; a placeholder
    `engine` renamed later means doing it twice.
  - `boundaries.md` §12 Q2 (one PR or two), Q3 and Q5.
  - `world_model.md` §12 Q1–Q3.
  - The plan's §5.1 lists only `npcs_and_sem.md` §12.1, and `check_plan.py` checks only that list.
- (c) Step 5's base branch isn't stated.
  - Step 5 moves `parse_action`, `ActionLimits` and `checks`. That code exists only on `phase1/act-validation`
    (PR #2). The design it implements exists only on PR #4.
  - The plan blocks step 5 only on step 3, a hand-off, not on PRs #2 and #4 merging.
  - With `BASE=main` (still `d02c0a2`), the size ratchet "says it has nothing to compare", so the "limits only
    tighten" rule goes unenforced for the branch.
- Fix:
  - Block step 5 on the merges, in `boundaries.md` §11.3's order, or say exactly which branch it stacks on and
    which `BASE` the gate uses.
  - Add the boundaries and world-model questions to §5.
  - Either write and accept part 3 before step 5, or amend §10 row 2 with a recorded reason.

**B-4. "§2 Every owner decision" leaves out six owner decisions, and the checker can't notice.**
`foundations_plan.md::§2`, `check_plan.py::SOURCES`.
- `world_model.md` §0 records D20–D25 (owner, 2026-11-16). None of them appears in the plan.
- `SOURCES` leaves out `world_model.md`, so `check_plan` passes while the heading's claim is false.
- This breaks the first principle ("Report results exactly as they are"). It also meets the charter's BLOCKER
  definition: a check that cannot fail on the case it claims to cover.
- Fix: add a §2.0 listing D20–D25. Add `world_model.md` to `SOURCES`, with a `D\d+` pattern scoped to that file.

## SHOULD-FIX

**S1. `check_plan.py` is code that no gate sees, and it is called a check.**
`docs/plans/check_plan.py`.
- The gate doesn't touch it:
  - ruff runs only on `src tests scripts`;
  - mypy's `files` and coverage's `source` leave `docs/` out;
  - the size tripwires and the determinism and isolation scans don't reach `docs/`;
  - no test runs it, and neither `prepush.sh` nor CI calls it.
- `tests/test_tooling_config.py::test_ruff_lints_every_tracked_python_file` lists only `src tests scripts`. With a
  tracked `.py` file under `docs/`, the test's name is now a false claim.
- It crashes with an `IndexError` when the `### 12.1` heading is missing, instead of naming the problem.
- It counts a mention as coverage, so a stale status passes. Example: §5.2's OD-A19 text, which the plan itself
  flags.
- It overlaps backlog row B15, which asks for a lint over the Phase 3 items.
- Fix: choose one.
  - Move it to `scripts/`, as its own module (B19 (4)), with tests: proof by deletion and the missing heading. Wire
    it into `prepush.sh`, extend its sources (B-4) and note the partial B15 coverage.
  - Or call it a one-off helper and drop the "`check_plan.py` fails if…" sentence.
- Either way, widen the ruff test to `git ls-files '*.py'`.

**S2. Step 7 doesn't say how the spawned worker's code gets coverage.**
- `fail_under = 100` and diff-cover at 95%.
- pytest-cov doesn't measure child processes unless coverage is configured to follow them (for example
  `patch = ["subprocess"]`, or `COVERAGE_PROCESS_START` plus `parallel` and `combine`).
- Red-first test 2 rewrites the worker's environment, and any `-I` drops every environment variable. Either one
  silently removes the coverage hook.
- Scenario: the worker's main loop shows 0% covered, the gate goes red, and `pragma: no cover` comments start to
  appear.
- Fix: name the mechanism. Admit coverage's variables through test 2's environment allowlist explicitly, and test
  that they don't reach production launches. Mark tests that spawn a worker `slow` if they exceed a few seconds.

**S3. Step 7's determinism changes aren't in the plan.**
- The hash probe (test 1) calls the builtin `hash()`. `tests/test_determinism.py` flags `hash` anywhere it scans.
  The worker module needs a package-qualified non-simulation entry (W14), with a reason, or the probe must sit
  outside the scanned packages.
- The keyed Philox streams need two edits in the same commit, as `boundaries.md` §11.2 and `npcs_and_sem.md` §3.4
  require:
  - `NUMPY_RANDOM_ALLOWED` must admit Philox, for Overdrive's streams only (the scan matches names, not packages);
  - CLAUDE.md's determinism rule ("one seeded `numpy.random.Generator` owned by `World`") must be rewritten.

**S4. Red-first test 5 can't fail against the scripted double, and the real-Maxim gate needs fencing.**
- Credit shared among NAc traces, and trace expiry, are Maxim's mechanisms (OD-A1, #1361 S3a). Run against
  Overdrive's scripted double, the test exercises only the double, so it cannot fail: a BLOCKER under the testing
  standard.
- Its "wall-clock fallback" also can't run in a test without an injected clock.
- OD-EA12 is an exit test in Maxim's embeddable draft, so replacing it is an upstream amendment.
- Fix: send it through `docs/maxim_upstream/` and keep only a strict red gate against real Maxim.
- That red gate, and O10's, must fail closed before any model call, network use, or write under `~/.maxim`:
  - tests forbid LLM calls;
  - B20 says the scan must cover Maxim's shared paths once real Maxim runs in tests.
- Say that the gate is expected to XPASS, and so turn the build red, when a pymaxim release ships tier A, as the
  SEM mirror already does.

**S5. Step 7's formats and data are missing the standards that apply to them.**
- The worker channel codec is a wire format. It needs:
  - a version that readers refuse when unknown (test 3 covers this);
  - a round trip;
  - committed golden fixtures (the "Wire and save formats" rule; B3);
  - a Hypothesis round-trip property (B9).
- The `data/agents/` files need:
  - a `version` through `checks.format_version` (B21);
  - closed schemas;
  - a loader test, including a negative-range test (B12).
- These tunables must live in `data/` YAML, not code: O11a's thresholds, O12's speed-trait parameters, OA1's
  settings table and OA5's load weights.
- The continuation blob becomes save state at save v0, so give it a version now.

**S6. No step names its review lenses or its design review.**

| Step | Lenses its diff triggers (Executor, Architecture and Wire integrity always) |
|---|---|
| 5 boundaries | Physics and resolution (`world/`, `sem_env/` and materials move); Trust boundary (loaders, `parse_action`, `imagination`); Bio-faithful (the `adapters.sem` split, `StructureModulator`); Determinism and replay (the scan is rewritten) |
| 6 gates | Trust boundary (validating constructors, registry, bounded echo); Determinism and replay (write window); Physics (`World.advance` owns the window); Bio-faithful (sensors on frames, instruments); Performance (frame copies); Concurrency (frames as copies) |
| 7 agents | Trust boundary (codec, `data/agents/`, home); Bio-faithful; Determinism and replay (streams, hash seed, resume); Concurrency and lanes (spawned worker, channel); Performance (round trip per park) |
| 8 part 3 | A **design review before code**: Executor, Architecture, Wire integrity, Bio-faithful (always), Physics, Client and rendering, Performance; records kept in `docs/design/reviews/lab_and_core_loop/` |
| 10 ledger | Trust boundary (a new loader) |
| this branch | Executor, Architecture, Wire integrity, on `check_plan.py` |

Each code step also needs `prepush: PASS <sha>` for its hand-off commit, and the round summary in its hand-off note.

**S7. The backlog's "Lands with" pointers are stale, and the plan doesn't remap them.**
- B2, B3, B5, B9, B12 and B14 say "Phase 1 step N". The roadmap's Phase 1 list has no numbers, and the build order
  now lives in `world_model.md` §10.
- The plan should state which row closes each one.
- B5 must land before `phase1/sim-clock`. Sim-clock's cached conductances and preallocated buffers are
  optimizations, and the standard is "optimize only from a profile".

**S8. B19 (4) applies, and the plan doesn't mention it.**
- `scripts/lint_standards.py` (396 lines, several checks) must be split into one module per check "before the next
  check lands".
- Step 10's calibration lint is the next check, and so is `check_plan`, if it moves (S1).
- Step 5 also adds import-linter. Add `importlinter` to the gate's tool check in `prepush.sh`.

**S9. Step 9 is a precondition, not a step that can wait.**
- "Make your worktree its own `.venv`."
- Every new worktree (boundaries, gates, agents, part 3) needs its own `.venv`, created with the worktree, before it
  first runs the gate.
- Listing it ninth, "blocked by nothing", invites running on the shared `.venv` with `PYTHON=`. That `.venv`'s
  editable install points at `main`'s empty `src/`.

**S10. design-v2's older CLAUDE.md contradicts standards' in ways a session would trip on before step 4.**
- **Pushing:** it says "Never push". The plan says push your own branch, and the branch has been pushed.
- **Lessons:** it has no lessons file and no lessons rule.
- **Searching Maxim:** it has no "search Maxim first" rule.
- **Maxim's process:** it describes the process as "pre-registration, four-lens design review, ledger" for every
  change. design-v2's own roadmap Phase 3 says the process depends on the kind of change.
- **Missing standards:** it has no separation-of-concerns rule, no size tripwires and no isolation rule.
- **Its gate:** design-v2's `prepush.sh` lacks `refuse_main_branch` and the guard against installing into a shared
  venv.
- Fix: integrate standards into design-v2 now, by merge (B-1), rather than after PR #1 lands. Until then, state in
  §2.4 that design-v2 sessions follow standards' CLAUDE.md.

**S11. Lessons are owed for design-v2's work.**
- design-v2's commits taught several lessons:
  - OD-A19 was withdrawn as a duplicate of Maxim's own work;
  - `-I` ignores `PYTHONHASHSEED`;
  - Python falls back to the real home directory when `HOME` is unset;
  - the pipe unpickles;
  - O15a.
- Those commits also added Phase 3 items.
- Standards requires a lessons entry in the same commit; B18's proposed check would fire on these commits.
- Step 4 should add the missing entries to `docs/lessons_maxim_in_games.md`, each with its evidence.

**S12. A third CLAUDE.md variant, on PR #3, will turn the gate red on design-v2's records.**
- `phase1/realtime-design`'s marker lint says that Markdown holds no markers.
- It flags `docs/design/reviews/foundations_v1/delta1_wire_integrity.md:343`, where an unquoted
  `TEMPORARY(sim-clock)` sits in a table.
- Reviews are kept verbatim (W7, W11), and §11.3 merges PR #3 after design-v2.
- The plan has no step for PR #3. Decide whether to quote the marker in the record or exempt `docs/design/reviews/`.

**S13. §1's status table is wrong.**
- It calls PR #4 "Docs only; pushed at 73c0eb8". The branch holds `check_plan.py`, which is code needing a review
  round and a gate PASS, and origin is at `72bf36c`.
- It says PR #1 was pushed at `e5aa3e1`. Origin is at `87593fe`, which was pushed while its gate was still "in
  progress".
- No gate result is recorded for design-v2's head.

**S14. Two dependencies dangle.**
- Merge order: the plan rebases PR #2 onto standards, while `boundaries.md` §11.3 merges act-validation first.
- Roadmap OD-A18 says "After OD-A19", but OD-A19 is withdrawn. `check_plan` passes both.

## NIT

- **N1.** Before step 1 is sent, re-read Maxim's `origin/main` (B22). `correction_1.md` cites `7084f561`
  (2026-11-16), but Maxim answered on 2026-11-17.
- **N2.** Step 10 is a new standard. Route it through `phase1/standards`: a CLAUDE.md rule, a guard and a backlog
  row, plus a design note before code.
- **N3.** `phase1/agents` is larger than PR 7, which `world_model.md` split for its size (A-SF-5). Consider
  splitting it into two: the codec, the worker and `data/`, then the port and the double.
- **N4.** §5.3's "the delta reviewer sets the status" is still a floating proposal. Make it an owner decision or a
  B1/B16 row.
- **N5.** `check_plan`'s check of §5.1 counts any `N. ` line, not the items themselves.

## Backlog rows

| Row | Should a planned step close or advance it? | Does the plan say so? |
|---|---|---|
| B1 review | No step closes it. Every code step must record a round summary | No (S6) |
| B2 replay | Sim-clock and protocol, beyond the plan's horizon; step 7 scopes replay to the world (§11.2) | No (S7) |
| B3 wire | Protocol (row 6); step 7's codec should follow its pattern | No (S5) |
| B4 save v0 | Row 11, beyond the horizon | Listed only |
| B5 performance | Before sim-clock | No (S7) |
| B6/B7 Godot | Protocol (row 6) and lab; `prepush.sh` refuses a `client/` | No |
| B8 assets | No | — |
| B9 Hypothesis | Steps 6 (constructors never crash) and 7 (codec round trip) | No |
| B10 mutation | Open | — |
| B11 | Done | — |
| B12 data | Step 7 (`data/agents/`), material table v1 (ranges), step 10 | No |
| B13 swallows | Open | — |
| B14 server | Protocol | No |
| B15 Phase 3 lint | Partly, if `check_plan` moves to `scripts/` | No (S1) |
| B16–B18 | Held by review. B18 is owed now | No (S11) |
| B19 | (1) step 5, stated. (4) must precede step 10 | Half (S8) |
| B20 isolation | Step 7: the worker's home and environment test; scan Maxim's paths with the real-Maxim gate | No (S4) |
| B21 (act-validation) | Done there; step 7's data files must use it | No (S5) |
| B22 search Maxim | Held by review; step 1 | Listed |
