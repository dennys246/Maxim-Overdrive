# Step 2: fix the drift job, move the lock to 1.3.4, gate the OD-I items (`phase1/drift-and-lock`)

You are the drift-and-lock session. You run beside step 1a, the only other session allowed then (O79), and you
touch no record family except one lesson, one roadmap edit and backlog NITs. Your one job has three parts, in order:

1. **The drift job is red for our own bug.** Run 45238153656 (2026-11-23, on `5960606`) installed pymaxim 1.3.4
   unpinned and failed on all four jobs. Of the tests, 3,559 passed. Two failed, both in `tests/test_check_lock.py`:
   `test_a_python_without_a_lockfile_fails` and `test_main_compares_the_lock_with_what_is_installed`. The job sets
   `MAXIM_OVERDRIVE_UNLOCKED` (`.github/workflows/drift.yml`), those tests don't clear it, so `check_lock.main`
   returns 0 where they expect 1. The coverage miss on that run (99.69%) follows from it. Issues #60 to #63 are the
   job's own reports. Fix the root cause, which is that tests inherit the job's skip variable, so that no test of
   `check_lock` can see it, rather than patching the two tests one by one. Prove it red first: run the two tests with
   `MAXIM_OVERDRIVE_UNLOCKED=1` set, watch them fail, then fix them. Say so in the commit.
2. **Move the lock to `pymaxim==1.3.4`** (O78), in both `constraints/py3.12.txt` and `py3.14.txt`, without bumping
   other pins: compile into the existing file with `--upgrade-package pymaxim` (CLAUDE.md, "Dependencies are
   locked"). Restore the hand-written header lines `--no-header` drops. Both lockfiles must resolve one numerical
   stack. Diff the lockfiles and list every pin that moved. If numpy, scipy or anything else the simulation imports
   moves, stop and ask the owner: replay goldens are recorded on that stack. Reinstall your venv from the new lock.
   The gate is the replay check: if any replay golden or digest moves, stop and report it, because `simcore.core`
   imports no `maxim` and a moved golden means something reached the simulation. OD-I7's fix (`DamageRefused`, PR
   #1725) arrives with 1.3.4. Close its roadmap row, citing your merge.
3. **O75's strict red gates** for OD-I1, OD-I3 and OD-I6, in one new module, `tests/test_maxim_fixes_pending.py`, each reason naming its OD id and Maxim issue. Each runs against the installed
   pymaxim and fails today with `raises=AssertionError`:
   - OD-I1: a world time of `0.0` passed to one of #1773's five sites comes back as `0.0`, not the wall clock. Pick
     a public call, and don't read the wall clock in the test itself.
   - OD-I3: the embedding store refuses a pickled file. Point it at `tmp_path`. If it can't be pointed away from the
     home directory, stop and ask: tests never write outside their worktree or `tmp_path`.
   - OD-I6: pymaxim's declared `rich` requirement admits `rich` 14 (read through `importlib.metadata` and
     `packaging`).

   None of the three is fixed in 1.3.4 (read at Maxim `2fb497a1`: `git tag --contains 1b2e60a9` is empty), so all
   three stay red under the drift job too, until 1.3.5. Prove each gate can fail: run it against a monkeypatched
   "fixed" behaviour, or say why that is impossible.

**Files you may touch:** `tests/test_check_lock.py`, `scripts/check_lock.py` (only if the root fix is there),
`tests/conftest.py` (only if the root fix is there), one new test module for the gates, `constraints/py3.12.txt`,
`constraints/py3.14.txt`, `docs/roadmap.md` (the OD-I1, OD-I3, OD-I6 and OD-I7 rows only),
`docs/standards_backlog.md` (NITs), `docs/lessons_maxim_in_games.md`. No workflow edits: the job is right, the tests
are wrong.

**Review:** Executor, Architecture, Wire integrity, plus Determinism and replay (the lock moves the stack the goldens
are recorded on). One round. If a fold changes code, one delta round, then stop.

**Exit test:**
```bash
set -e
grep -qx 'pymaxim==1.3.4' constraints/py3.12.txt && grep -qx 'pymaxim==1.3.4' constraints/py3.14.txt
.venv/bin/python scripts/check_lock.py
MAXIM_OVERDRIVE_UNLOCKED=1 .venv/bin/pytest -q tests/test_check_lock.py
G=tests/test_maxim_fixes_pending.py                     # the gates' module: use this name
for id in OD-I1 OD-I3 OD-I6; do grep -q "$id" $G || { echo "no gate names $id"; exit 1; }; done
test "$(grep -c 'xfail(strict=True, raises=AssertionError' $G)" -eq 3
test "$(.venv/bin/pytest -q -rx $G | grep -c '^XFAIL')" -eq 3
gh workflow run drift.yml --ref phase1/drift-and-lock   # then wait for the run to finish
test "$(gh run list --workflow drift.yml --branch phase1/drift-and-lock --limit 1 --json conclusion -q '.[0].conclusion')" = success
```
Then `prepush: PASS <sha>` and all five PR jobs green. Only after that, close #60 to #63, each with a comment linking
the green drift run. Closing issues is outward-facing, so ask the owner first.

**Trigger for the repeat:** when Maxim releases 1.3.5, the drift job turns O75's gates red (their XPASS). Then a fresh
session runs this brief's part 2 at 1.3.5 and removes the gates that flipped.

## Rules every step after `v0.1.0` follows

You are one short session with one step. You start after the planning PR (`phase1/planning`) has merged, because
its `docs/roadmap.md` ("Phase 1 at `v0.1.0`", "The next steps after `v0.1.0`") and rulings O75–O79
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
  - A NIT becomes a backlog row (`docs/standards_backlog.md`), with no other change.
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
- **Main moves:** if `main` moves under you, merge it in (never rebase), recheck budgets, and gate again. Before each
  new commit on an open PR, check `gh pr view <n> --json state`: the owner may already have merged it.
- **Push and CI:** a push needs the owner's go-ahead in the turn. Push your own branch only. After pushing, wait until
  all five CI jobs exist, then read every one. Don't merge: the owner merges.
- **Public repo:** no home-directory or scratchpad paths, hostnames or private addresses in committed files or PR
  text (`scripts/lint_paths.py`, B45).
- **Lessons:** record any lesson about Maxim in a game in `docs/lessons_maxim_in_games.md`, in the same PR.
- **Hand-off:**
  - The PR body carries the review summary, the last gate sha and this step's exit test output.
  - Update your memory. Re-read `MEMORY.md` before adding any pointer.
- **Teaching:** in each reply, teach the owner the game-engineering concepts the work touches (CLAUDE.md, B17).
