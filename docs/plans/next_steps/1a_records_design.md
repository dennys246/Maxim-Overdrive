# Step 1a: fold the records-layout design (`phase1/records-layout`)

You are the records-layout design session, the first step after `v0.1.0` (O79). Your one job: fold round 1's
BLOCKERs into `docs/design/records_layout.md`, get the owner's rulings on its open questions, run one delta round,
and hand the PR to the owner. This step is docs only. Building the design is step 4's (`phase1/records-build`),
not yours.

**Where to work.** The branch already exists: `phase1/records-layout`, pushed with no PR, with its worktree at
`.worktrees/records-layout`, parked at `35cec7b` by the torch-pilot session and assigned to this step by O79. Check
`git -C .worktrees/records-layout status` (clean) and `log -1` (`35cec7b`). If either differs, stop and ask the
owner. Work there. Its `.venv` (Python 3.14) was installed from the lock at `35cec7b`, and the lock has gained `websockets` since, so
reinstall it from the merged `constraints/py3.14.txt` after the merge. Merge `origin/main` in: the branch is about 172
commits behind. After the merge, diff the merged tree against `main` and read the design's untouched text against
`main`'s newer rulings and owners, not only the conflict hunks. #52 moved Known gaps to `docs/known_gaps.md`, #55
added `scripts/lint_ids.py`, and #70 added lesson 39 and B47. This session's planning PR added lesson 40, B48 and
O75–O80. The design's §1 counts and §8's branch list are stale, so recount them on the merged tree.

**Inputs.**
- The round-1 reports: `docs/design/reviews/records_layout/round1_architecture_bio.md`, `round1_concurrency.md` and
  `round1_wire_executor.md`. They hold eleven BLOCKERs: A-B1 to A-B4, C1 to C3, and W1 to W4 (C1 and W1 are one
  defect), plus their SHOULD-FIXes.
- The design's §10, five owner questions.
- Two questions the owner added to this step (2026-11-23):
  1. Do Known gaps get a `kind` (physics, performance or trust boundary)? With it, guest text's residual hidden
     channel (about 551 bits in "hi!" plus about 138 per further visible character, O73) and the selector and joiner
     channel (a bit or two per visible character) move from `checklists.md`'s step 7 and O73 into Known gaps, each
     with its numbers and the step that closes it. O73 is a ruling and is never edited, so the Known gap owns the
     open channel and cites O73 for the measured bound. The move itself happens at step 4.
  2. Do lessons beyond Maxim (general engineering and game engineering, today only in Claude's memory) get a lessons
     `section`, or nothing? The owner is learning game engineering, which argues for keeping them in the repo.
- C1 and W1 say a duplicate id merges because `main` is unprotected and PR checks don't rerun when `main` moves.
  Whether to turn on GitHub's "require branches to be up to date" rule is the owner's call, so ask it.

**Order.**
1. Ask the owner every question at the start, in AskUserQuestion calls of at most four questions each: the five §10
   questions, the two above (Q6 and Q7), the branch-protection question, and any BLOCKER whose fold is a choice
   between contracts. Lead each with your recommendation.
2. Record each ruling as a row in a new decision log, `docs/design/decisions/records_layout.md` (O79), headed like the
   other logs, with ids `RL1`, `RL2` and so on (check that `scripts/lint_ids.py` accepts the prefix). Each row cites
   its question in exactly one of these forms: `records_layout §10 Q1` to `records_layout §10 Q5`, `records_layout
   added Q6`, `records_layout added Q7`. Your reserved ids (O79): lesson number 43 and up, B55 and up.
3. Write the stop rule (above) into `docs/design/reviews/records_layout/fold.md`.
4. Fold the BLOCKERs and SHOULD-FIXes. Mechanism findings (a test plant, a script's behaviour) go to §9's build
   steps as tests to write, citing their finding. They are not contract text (CLAUDE.md, "A design document holds
   the contract").
5. Run one delta round on the fold's diff, with each lens's report saved as
   `docs/design/reviews/records_layout/delta_<lens>.md`, then stop.

**Files you may touch:** `docs/design/records_layout.md`; `docs/design/reviews/records_layout/`;
`docs/design/decisions/records_layout.md` (new); `docs/roadmap.md`'s step 1a and step 4 rows (state only); `docs/standards_backlog.md` (B55 and up, only for a rule waiting for a check);
`docs/lessons_maxim_in_games.md`. Nothing else, and no code.

**Review:** the delta round reads the fold's diff with Architecture with Bio-faithful integration, Concurrency, Wire
integrity and Executor, the same lenses as round 1.

**Exit test** (run from the worktree; it prints nothing and exits 0 when done):
```bash
set -e
test "$(wc -w < docs/design/records_layout.md)" -le 6000
D=$(ls docs/design/reviews/records_layout/delta*.md)      # the delta round's reports: the reviewers' statuses
for id in A-B1 A-B2 A-B3 A-B4 C1 C2 C3 W1 W2 W3 W4; do
  grep -qE "^\|[^|]*(^|[ ,*|])$id([ ,*]|\|)[^|]*\| *\**(fixed|deferred|rejected)" $D || { echo "no reviewer status: $id"; exit 1; }
  ! grep -qE "^\|[^|]*(^|[ ,*|])$id([ ,*]|\|)[^|]*\| *\**open" $D || { echo "a lens left $id open"; exit 1; }
done
for q in "§10 Q1" "§10 Q2" "§10 Q3" "§10 Q4" "§10 Q5" "added Q6" "added Q7"; do
  git grep -q "records_layout $q" -- docs/design/decisions || { echo "no ruling: $q"; exit 1; }
done
.venv/bin/python scripts/lint_standards.py >/dev/null
```
Then `prepush: PASS <sha>` on the pushed commit, and all five CI jobs green.

**Stop rule, specific to this step:** if the delta round finds a new BLOCKER in text the fold added, don't fold it.
Take it to the owner (CLAUDE.md, "Review finds; it doesn't design"; `docs/code_review.md`).

## Rules every step after `v0.1.0` follows

You are one short session with one step. You start after the planning PR (`phase1/planning`) has merged, because
its `docs/roadmap.md` ("Phase 1 at `v0.1.0`", "The next steps after `v0.1.0`") and rulings O75–O80
(`docs/design/decisions/boundaries.md`) are your base. Check with `git log origin/main --oneline | grep -i planning`.
If it hasn't merged, stop and tell the owner. Your session ends when your PR is handed to the owner. Don't start
another step.

- **Brutal honesty, corrections first** (CLAUDE.md, first principle). If this brief turns out wrong against the
  tree, say so first, and follow the tree.
- **Your own worktree and venv,** unless your brief says otherwise:
  `git worktree add .worktrees/<name> -b <branch> origin/main`, then
  `python3.12 -m venv .venv && .venv/bin/pip install -c constraints/py3.12.txt -e '.[dev,maxim]'`.
  - Never stash.
  - Never touch another session's worktree or branch, `.worktrees/specgen-spike` (session -18's live run chain,
    also on the Mac mini), `.worktrees/_tools`, or `.worktrees/_durable/sim_tick_review` and
    `_durable/sim-replay` (committed reviews cite them).
- **Scope:** touch only the files your brief lists. Anything else you find is an open item for the roadmap, with an
  owner and a trigger. It is not work for this session.
- **The stop rule,** written into your review record before the round it governs:
  - A BLOCKER or SHOULD-FIX is folded.
  - If a fold changes text or code, one delta round reads only that fold's diff, and no round follows it. A
    BLOCKER the delta round finds goes to the owner for a ruling, not to another round.
  - A NIT is your call: fix it in a fold or leave it. Either way it is recorded in the review record with its
    reviewer's trigger, and becomes a backlog row only if it is a rule waiting for a check (O80).
- **Review:** parallel independent readers with the lenses your brief names (`docs/code_review.md`).
  - Reviewers, not you, set each finding's status (O25).
  - Record their reports verbatim under `docs/design/reviews/<your step>/`.
  - A review report is at most 3,000 words.
- **Budgets:** an existing design document doesn't grow. A new one is at most 6,000 words, and a plan at most 2,500.
- **Gate:** `scripts/prepush.sh` must print `prepush: PASS <sha>` for the exact commit you push. On this Mac, run it
  in the background through the waiter, launched with plain `python3`:
  `python3 <Maxim checkout>/scripts/box_quiet.py wait --kind suite -- env PYTHON=.venv/bin/python bash scripts/prepush.sh`.
  Or gate on the mini with `scripts/remote_gate.py` (CLAUDE.md, Commands). Write logs to your scratchpad, never the
  worktree. Don't edit the tree while the gate runs.
- **Commits:** signed. If signing fails, try once more; if that fails too, stop and ask the owner.
- **Main moves:** if `main` moves under you, merge it in (never rebase), recheck budgets, and gate again. If the merge
  changed `constraints/` (step 2 moves the lock), reinstall your venv from the merged lock before the gate, or
  `check_lock` refuses it. Before each new commit on an open PR, check `gh pr view <n> --json state`: the owner may
  already have merged it. Your session ends at hand-off. If `main` moves after that, the owner resumes you, or starts
  a fresh session from this brief, to merge it in and gate again (O79).
- **Push and CI:** a push needs the owner's go-ahead in the turn. Push your own branch only. After pushing, wait until
  all five CI jobs exist, then read every one. Don't merge: the owner merges.
- **Public repo:** no home-directory or scratchpad paths, hostnames or private addresses in committed files or PR
  text (`scripts/lint_paths.py`, B45).
- **Lessons and ids:** record any lesson about Maxim in a game in `docs/lessons_maxim_in_games.md`, in the same PR.
  Steps 1a, 2 and 3 run together, so each takes only the ids O79 reserves for it, and releases an unused one in
  its PR. The reservations are for a step's first run. A rerun takes the ids the owner names when starting it, and
  without them writes no record id. After step 4 merges, the record files live where step 4 moved them.
- **Hand-off:**
  - The PR body carries the review summary, the last gate sha and this step's exit test output.
  - Update your memory. Re-read `MEMORY.md` before adding any pointer.
- **Teaching:** in each reply, teach the owner the game-engineering concepts the work touches (CLAUDE.md, B17).
