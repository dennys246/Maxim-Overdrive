# Step 5: the vertical slice, week 4 (`phase1/slice-week4`)

You are the first slice session after `v0.1.0`. You start after step 4 (the records migration) merges (O79). Your
one job: help the owner tune and playtest the heat-debt slice, record three playtests' numbers, write the verdict
note, and measure step 10's coverage item. The plan is `docs/plans/vertical_slice.md` (step 10, VS5, D28). The
verdict is due **2026-12-18**. If step 4 hasn't merged by 2026-12-08, tell the owner at once: the order puts the
date at risk, and the owner may move this step earlier.

**State** (after #68, `c95ab24`):
- The slice runs on step 5a's `Simulation`. Weeks 1 to 3 are built, and tuning hasn't started.
- The tuned numbers didn't move in the port (`spikes/slice/README.md`).
- The slice's tests and a committed replay golden are in `main`'s gate. An engine change that moves the slice's
  replay turns `main` red, and the fix is to rebuild the golden on purpose (`tests/test_metrics.py::FIXTURE`'s
  comment) or fix the engine, never to drop the test.

**More than one session.** The playtests run on the owner's time, over up to three weeks. If your session ends
before the exit test passes, commit what you have (logs, notes, tuning) on the branch and hand back. A fresh session
started from this brief continues on the same branch. The PR opens when the exit test passes.

**How to run it.**
- Playtests run on the Mac mini, which has no slice worktree. Get your branch there by a push (the owner's go-ahead)
  or a branch-only bundle, make a worktree with its own venv, and import the Godot project once (CLAUDE.md,
  Commands, for the remote gate).
- Never commit the mini's hostname or address.
- Each session log (`slice-log-2`) carries the data it was played on, so a retune keeps old logs replayable.
- `python -m slice_server metrics <log>` gives the numbers.
- Tune **one YAML value per play session**, and record which one and why.

**The three open items** (`docs/design/reviews/vertical_slice/port_fold.md`; the roadmap's step 10 row):
1. **Coverage:** measure branch coverage of `src` with and without `spikes/slice/tests` (two pytest runs with
   `--cov=src`, the slice's tests deselected in the second). Record both numbers in the verdict note. If `src`
   coverage drops without them, below `fail_under` or at all, say which lines, and write the `src` tests first
   (step 10's row in `docs/plans/foundations_plan.md`). Deleting the slice at step 10's close is not this step's.
2. **`Voice.ready()` after `close()`** can lose lines. It is latent: the shipped path never calls it after
   `close()`. Leave it unless your work adds such a caller or moves the voice out of the spike. Those are its
   triggers.
3. **Two server tests on the wall clock** (B47): the vendor-line test (2.95 s) and the hello deadline (0.9 s). If
   either passes 3 s or flakes in your runs, that is B47's trigger: fix it as B47 says, with a red-first test.
   Otherwise leave it.

**Files you may touch:** `spikes/slice/` (data YAML and the code the tuning needs), `docs/plans/vertical_slice_verdict.md`
(new, at most 1,000 words), `docs/plans/vertical_slice.md` (state only), `docs/roadmap.md` (step 10's row),
`docs/design/reviews/slice_week4/`, `docs/standards_backlog.md` (NITs and B47's row),
`docs/lessons_maxim_in_games.md`. No `src/` change unless item 1 requires `src` tests, which go in `tests/`.

**Review:** Executor, Architecture, Wire integrity, plus Client and rendering if the client changes. One round, one
delta, then stop.

**Exit test:**
```bash
set -e
V=docs/plans/vertical_slice_verdict.md
test -f $V && test "$(wc -w < $V)" -le 1000
test "$(grep -c 'replay MATCHES the recorded end' $V)" -ge 3   # three trusted replays, each report quoted
grep -iE 'coverage' $V | grep -qE '[0-9]+(\.[0-9]+)?%.*[0-9]+(\.[0-9]+)?%'   # with and without, both numbers
.venv/bin/python scripts/lint_standards.py >/dev/null
```
Then `prepush: PASS <sha>` and all five CI jobs green. The verdict is the owner's: fun or not, and why. Write down
what the owner says. Don't write it for them.

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
  - A NIT stays in the review record with its reviewer's trigger, and changes nothing. It becomes a backlog row only
    if it is a rule waiting for a check (O80).
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
  its PR.
- **Hand-off:**
  - The PR body carries the review summary, the last gate sha and this step's exit test output.
  - Update your memory. Re-read `MEMORY.md` before adding any pointer.
- **Teaching:** in each reply, teach the owner the game-engineering concepts the work touches (CLAUDE.md, B17).
