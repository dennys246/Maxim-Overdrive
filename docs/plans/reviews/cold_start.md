# Review: the foundations plan, cold-start reader lens

- **Plan:** `docs/plans/foundations_plan.md` at `72bf36c` (`phase1/design-v2`)
- **Lens:** a new engineer or fresh session told only "read the plan and start the next step"
- **Read against:** `git show phase1/standards:CLAUDE.md`, `docs/roadmap.md`, `docs/design/boundaries.md`,
  `docs/design/world_model.md`, `docs/design/npcs_and_sem.md`, `docs/design/reviews/npcs_v3_1/*`,
  `docs/plans/check_plan.py`, the git state of every branch and worktree (read only)
- **Counts:** 6 BLOCKER, 10 SHOULD-FIX, 7 NIT

## Summary

The plan is a good index of what has been decided about the agent half and the Maxim side. As a starting point for
building, it fails. A newcomer can't tell which step is theirs, can't find the base branch for the first code step,
and runs into an ordering that the documents it defers to contradict three ways. It omits the world half's decisions
and open questions, including one (the engine package name) that blocks step 5 outright. Nothing in it says when
anything becomes visible or playable. Two of its "still open" claims were fixed by the very next commit on the
same branch.

## BLOCKER

### CS-B1: the plan's order contradicts world_model §10, boundaries §11.1 and the roadmap

**Plan lines 89–94.** Step 7 (`phase1/agents`) is blocked only by step 6 (`phase1/gates`). Step 8 (Part 3) comes after
step 5.
- `world_model.md` §10 row 2 makes "Parts 1, 2 and 3 of this design accepted" a precondition of row 2b
  (`phase1/boundaries`), and `boundaries.md` §11.1 says the same ("after #2 (designs accepted)"). Part 3
  (`lab_and_core_loop.md`) doesn't exist yet. The plan puts it after boundaries.
- `world_model.md` §10 puts row 9b (`phase1/agents`) after rows 3–9 (`verify`, `sim-clock`, material table, `protocol`,
  `zones`, both fuel PRs, phase change). `boundaries.md` §11.1 says "after sim-clock and before lanes", and
  `roadmap.md` Phase 1 says "after the clock and before the lanes". The plan skips straight from gates to agents,
  and rows 3, 4, 5, 6, 7, 8a, 8b, 9, 10, 11 and 12 don't appear in it at all.
- Scope conflict: the plan (line 91) and `world_model.md` row 9b put "the scripted double behind the real worker
  channel" (a spawned worker) in `phase1/agents`. `boundaries.md` §11.1 says "the worker processes … arrive with
  `phase1/lanes`". Red-first tests 1–2 (lines 100–105) only make sense if the worker process exists in `agents`.

**Failure scenario.** A fresh session finishes gates and starts `phase1/agents`. It has no integer clock (row 4), and
`AgentPort.step` takes world time, so it builds against a clock that doesn't exist yet. Or it reads boundaries
§11.1, leaves the worker out, and the plan's red-first tests 1–2 have nothing to run against. The line-5 rule ("the
linked document wins") doesn't help, because the linked documents disagree with each other.

**Fix.** Either (a) say the plan deliberately reorders agents ahead of the world rows, record that as an owner
decision, and update `world_model.md` §10, `boundaries.md` §11.1 and the roadmap in the same commit, or (b) restore
the world_model order. Either way, list every row 3–12 in §3 so the plan is the whole Phase 1 path. Decide where
Part 3 sits relative to row 2's "accepted" gate.

### CS-B2: step 5 has no base branch, and its code lives on another session's branch

**Plan lines 87–89.** Step 5 is "blocked by steps 2–3", where step 3 is "rebase PR #2 onto standards and hand off".
`boundaries.md` §11.1 has 2b move `parse_action`, the typed actions and `ActionLimits` into `engine.intents`. Those
exist only on `phase1/act-validation` (`config.py:218`, `sem_env/bridge.py:207`), not on standards or design-v2.
"Hand off" isn't "merged". So the newcomer has to choose between branching from `main` (doesn't have the code),
from standards (doesn't have the code) or from `phase1/act-validation` (another session's branch, which the plan
says not to touch).

The merge order also contradicts: `boundaries.md` §11.3 proposes act-validation, then standards, then design-v2.
The plan lands standards first (step 2) and rebases PR #2 onto it (step 3).

**Fix.** State the base exactly, for example "`git worktree add .worktrees/boundaries -b phase1/boundaries
origin/main` after PRs #1, #2 and #4 are merged into `main`". Make step 5 blocked by those merges (owner actions),
not by a rebase. Reconcile §11.3's order with steps 2–4, or supersede it explicitly.

### CS-B3: the plan omits the world half's decisions and open owner questions; one blocks step 5

**Plan §2 (lines 24–79)** claims "every decision made so far". It doesn't record D20–D25 (`world_model.md` §0: the
one simulation truth, resolution follows the world, rubble to Phase 2, the lab as a benchmark tile, the three-part
split, the physics standard). §5.1 lists only `npcs_and_sem.md` §12.1. It leaves out:
- `boundaries.md` §12: **Q1, the engine's package name** ("`engine` is a working placeholder"). Step 5 is a rename
  into that package, so it can't start without an answer. Also Q2 (two PRs or one), Q3 (abandon `phase1/transport`
  and `foundations/world-server-v0`, both still present), Q4 and Q5.
- `world_model.md` §12: the truth resolution (0.1 m?), the band gate, and when the CSG footprints land.

`check_plan.py` scans only `boundaries.md`, `npcs_and_sem.md` and the roadmap, and only matches `O`/`OA`/`OD-` ids,
so its PASS can't see any of this.

**Fix.** Add §2.x for D20–D25 and §5.x for the boundaries and world_model owner questions. Mark the package name as
blocking step 5. Extend `check_plan.py`'s `SOURCES` to `world_model.md`, its regex to `D\d+`, and its question
check to every design's "Open questions for the owner" section.

### CS-B4: "start the next step" has no answer; ownership is unnamed

**Plan lines 83–95.** The "Owner" column says "owner", "other session", "this line" and "both".
- A newcomer doesn't know whether they are "this line". Nothing names the session, its worktree set, or how to tell
  "this line" from "the other session" apart from the branch name.
- Steps 1–4 belong to someone else or are blocked. The only step a newcomer can actually start is step 9, and the
  plan doesn't say so.
- No step has a done-criterion. Step 3's precondition ("the other session finishing its delta round") can't be
  observed, because nothing says where a hand-off is recorded.

**Fix.** Open §3 with "If you are a new session: your first step is N; run these commands". Define "this line"
(the design-v2 line: the worktrees `design-v2` and, after step 2, the new `phase1/*` code worktrees). For each
blocker, give an observable signal, for example "`gh pr view 2 --json isDraft,mergedAt` shows it merged" or "the
PR description carries a hand-off note with `prepush: PASS <sha>`". Give each step a done line, for example "PR
open, prepush PASS at its head, a review round folded, owner merges".

### CS-B5: nothing says what becomes visible or playable, or when

The owner is learning game development, and asked to see the path to something playable. The plan's 11 steps
produce documents, contracts, gates and an agent port. None of them produces a pixel. The Phase 1 exit ("walk into
the alley, set a crate on fire, watch it crack, glow and burn away", `roadmap.md`) and the Godot client
(`world_model.md` row 12, `phase1/lab`) are absent. So is the first Godot code (row 6's minimal fixture reader in
`phase1/protocol`).

From the documents, the honest answer is that nothing is on screen until about the 10th code PR, and nothing is
playable until row 12. The owner should see that stated, with the reason: the engine-first ordering is a deliberate
trade, cheaper refactors now for a later first pixel.

**Fix.** Add a column "What you can see or run afterwards" to §3 ("nothing new on screen; `pytest` proves X";
"first Godot window: a fixture reader draws a recorded frame"; "Phase 1 exit: the burning crate"), and a one-paragraph
"When will I see something?" near the top. Explain the handful of game terms the steps rely on (tick, lane, frame or
snapshot, worker, test double, dilation) in a short glossary, per the teach-game-engineering standard.

### CS-B6: the plan was stale on the commit after it, and its snapshot facts can't be checked

- Line 164 says §12.1 items 2, 6 and 7 "still read as open". Line 171 says "§12.2 still says this closes with
  OD-A19". Commit `72bf36c` (the current head, "Fix the contradictions the plan surfaced") fixed both. The plan now
  sends a reader to fix something already fixed.
- Line 19 says "pushed at `73c0eb8`"; the branch and its remote are at `72bf36c`.
- Line 16 says "gate run in progress" for `87593fe`, which is now on `origin/phase1/standards`. A newcomer can't tell
  whether step 2's precondition is met.

Because step 2 depends on that status, a stale snapshot misroutes the first action.

**Fix.** Replace the SHAs and states in §1 with the commands that give them now (`git log -1 --format=%h
origin/<branch>`, `gh pr view <n> --json isDraft,mergedAt,headRefOid`, "the PASS line is in the PR description").
Delete lines 164 and 171's "still" claims. Add a line: "when you change a source this plan summarises, update the
plan in the same commit".

## SHOULD-FIX

### CS-S1: the CLAUDE.md a newcomer reads in this worktree contradicts the plan

**Line 64, §2.4.** In `.worktrees/design-v2`, `CLAUDE.md` is the old one: "Never push: the owner reviews and pushes".
It has no "assume other agents" rule, no size tripwires and no "search Maxim first". The plan's push rule and §2.3
live only on `phase1/standards`. A newcomer opens the obvious file and gets the wrong rules. **Fix:** at the top of
the plan, say "until step 4, the rules are `git show phase1/standards:CLAUDE.md`, not this worktree's copy". Same for
`docs/standards_backlog.md`: B19, B20 and B22 (lines 68–71, 89, 188–190) don't exist on this branch.

### CS-S2: step 9 has no command, no worktree list, and a hidden ordering with step 5

**Line 93.** Step 9 doesn't say which worktrees "this line's" are, or give the command, which is in CLAUDE.md:
`python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'`. Step 5 needs import-linter (B19 (1)), which isn't
in `pyproject.toml` on any branch. Adding a dev dependency means installing it, and the shared venv may not be
installed into (`prepush.sh:43–47`). So step 9 blocks step 5, and the table says it doesn't. The install also pulls
`pymaxim>=1.3` from PyPI. The shared venv has 1.3.3, and a newer release can turn `test_sem_compat.py` red on day
one. Say that this is expected (CLAUDE.md, "drift check"), not an environment fault.

### CS-S3: step 1 is unrunnable as written

**Line 85.** "Send Maxim `correction_1.md` … owner (paste)": paste where? A Maxim issue, the thread where `reply.md`
went, or #1361? `correction_1.md` doesn't say either. Name the destination and how the plan learns it was sent.

### CS-S4: undefined ids and terms on the main path

These are unexplained at first use, and some can't be found without searching the repository:
- "PR 1" (line 17), which is PR **#2**, while "PR #1" is standards;
- "B19 (1)", "B21", "row 2b", "row 2c", "row 9b" (the rows of `world_model.md` §10, which the plan never names);
- "Part 3";
- "tier A";
- "the 1.4.0 cut" (Maxim's release);
- "#1361 S3a" (which repository? a plan slice of Maxim's `docs/plans/experience_clock_decay.md`);
- "the embeddable draft" (`docs/maxim_upstream/embeddable_agent_DRAFT.md`);
- "the scripted double";
- "the generator" (line 179: `reviews/npcs_v3/foldtable.py`?);
- "ANALOG", "the SCN phase", "oracles";
- "delta round", "fold table".

A five-line key at the top would fix most of these.

### CS-S5: review-finding ids collide with backlog ids

Line 102 cites "`executor_wire.md` B1", and line 190 cites backlog "B1"-style rows. The same "B1" means a backlog
row in CLAUDE.md and a review BLOCKER in `npcs_v3_1/`. Line 191 adds unkeyed ids (BD-1, TBR-11, TB3-S8, Arch 1.2,
Exec3 N8). **Fix:** cite review findings by their file's own prefix (the review files use DB-B1, DB-B2 and so on),
and give the file for each partial-fold id.

### CS-S6: the design documents' status lines contradict "converged" and "frozen"

Line 78 says "the world half is converged", and O19 freezes the agent half. Yet:
- `boundaries.md`'s status line says "DRAFT v3, for a delta design review before any code";
- `npcs_and_sem.md` says "A delta round follows before any code";
- `world_model.md` says "DRAFT, for a design review before any code".

The newcomer is told by the design documents themselves not to code. Nothing records the designs as accepted
(world_model row 2). **Fix:** an owner acceptance line per document (a decision id), and status lines updated to
match.

### CS-S7: PR #3 has no next step

`phase1/realtime-design`'s merge base is `9bad3bd`, older than standards' `15bd3aa`. It carries the other session's
marker-lint changes to `scripts/lint_standards.py`, which standards also changes. The plan gives it no rebase, merge
or abandonment step, though `boundaries.md` §11.3 slots it before `phase1/boundaries`.

### CS-S8: machine assumptions aren't stated

- Commits must be signed (`commit.gpgsign=true`), and a non-interactive session can hang on pinentry; the owner's
  standing rule is "try twice, then ask".
- `gh` must be authenticated for the PR-state checks.
- Python is Homebrew 3.14.
- Godot 4.7.2 is at `/Applications/Godot.app`; it's needed from row 6.
- The gate takes about 4 minutes under current load.

None of this is in the plan.

### CS-S9: "the linked document wins" can't resolve document-versus-document conflicts

**Line 5.** Add a precedence order: the owner's decision ids, then the newest design, then `world_model.md` §10,
then this plan. Or say which document owns the order of work.

### CS-S10: `check_plan.py` is described as a check, but nothing runs it

**Line 6.** It isn't in `prepush.sh`. Under CLAUDE.md ("a document is not a check"), it guards nothing until the gate
calls it. It also only proves an id string appears somewhere in the plan, not that the plan's row about it is
current (see CS-B6).

## NIT

- **CS-N1:** Line 22 cites "§5.6", which doesn't exist; it means §5.3.
- **CS-N2:** Line 11 says "Four draft PRs", but branches `phase1/transport` (local) and `foundations/world-server-v0`
  (on origin) also exist, unmentioned (see CS-B3, boundaries Q3).
- **CS-N3:** Line 95 says step 11's owner is "both": both of whom?
- **CS-N4:** Line 94: step 10 is "proposed, not designed" but sits in the ordered plan with a blocker. Mark it as
  awaiting an owner decision, as line 160 does for the speed trait.
- **CS-N5:** Lines 97–110: test 3 cites O13 and §6.6 while the others cite review findings. State that test 3 isn't
  from the open BLOCKERs, or cite the BLOCKER it comes from.
- **CS-N6:** Line 1: dated, but has no "last verified at <sha>" line. A reader can't tell how stale it is (see CS-B6).
- **CS-N7:** Line 148 lists OD-EA4 to OD-EA12 as "exit tests named in the roadmap". Say which file defines them
  (`embeddable_agent_DRAFT.md`).

## The first step, attempted on paper

Being "a new session" doesn't map to a step. Steps 1–3 belong to others, and 4–8 are blocked. The only unblocked step
for this line is **step 9**. What I would run:

```bash
# orient (read only)
git -C <home>/Scripts/Maxim-Overdrive worktree list
git -C .worktrees/design-v2 status --short
gh pr view 1 --json isDraft,mergedAt,headRefOid   # is step 2 done? the plan can't tell me
gh pr view 2 --json isDraft,mergedAt,headRefOid   # is step 3 done?
python3 docs/plans/check_plan.py                  # PASS today, but blind to CS-B3

# step 9, in this worktree only (writes only the ignored .venv/)
cd <home>/Scripts/Maxim-Overdrive/.worktrees/design-v2
python3 -m venv .venv && .venv/bin/pip install -e '.[dev,maxim]'
.venv/bin/pytest
```

**Safe given other sessions?** Only in `design-v2`. `.venv/` is gitignored there, it's this line's own worktree, and
the install only touches the new venv. The plan doesn't say whether `.worktrees/standards` is "this line's" (§1
says a gate run is in progress there), so I would not touch it.

**Step 5** I could not start safely:
- no base branch (CS-B2);
- no package name (CS-B3);
- a contradicting order (CS-B1);
- designs still marked DRAFT (CS-S6).

`git fetch` also isn't mentioned. It updates refs every worktree shares; that's benign, but a cautious newcomer would
want to be told it's allowed.

## Readability for the owner

The prose is tight, and the Maxim side (§4) reads well to an ML engineer. But §2 and §3 are dense with ids, and
nothing translates them into "what changes for me". The plan never says what the owner will see after a step, or that
the first window opens only after roughly ten code PRs (CS-B5). Add the "what you can see" column and a short
glossary, and the plan becomes a document the owner can steer by, rather than one he has to trust.
