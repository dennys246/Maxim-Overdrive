# Step 2: fix the drift job, move the lock to 1.3.4, gate the OD-I items (`phase1/drift-and-lock`)

You are the drift-and-lock session. You run beside step 1a, the only other session allowed then (O79), and you
take only the ids O79 reserves for you: lesson number 41 and B49 to B51. Your one job has three parts, in order:

1. **The drift job is red for our own bug.** Run 45238153656 (2026-11-23, on `5960606`) installed pymaxim 1.3.4
   unpinned and failed on all four jobs. Of the tests, 3,559 passed. Two failed, both in `tests/test_check_lock.py`:
   `test_a_python_without_a_lockfile_fails` and `test_main_compares_the_lock_with_what_is_installed`. The job sets
   `MAXIM_OVERDRIVE_UNLOCKED` (`.github/workflows/drift.yml`), those tests don't clear it, so `check_lock.main`
   returns 0 where they expect 1. The coverage miss on that run (99.69%) follows from it. Issues #60 to #63 are the
   job's own reports. Fix the root cause, which is that tests inherit the job's skip variable, so that no test of
   `check_lock` can see it, rather than patching the two tests one by one. Prove it red first, in the drift job's own
   mode: `GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1 .venv/bin/pytest -q
   tests/test_check_lock.py` fails twice with `assert 0 == 1`. With only the skip variable set they fail through a
   different path, the refusal (this PR's review, E2), so a fix proved only that way can leave the job red. Say so in the commit.
2. **Move the lock to `pymaxim==1.3.4`** (O78), in both `constraints/py3.12.txt` and `py3.14.txt`, without bumping
   other pins: compile into the existing file with `--upgrade-package pymaxim` (CLAUDE.md, "Dependencies are
   locked"). Restore the hand-written header lines `--no-header` drops. Both lockfiles must resolve one numerical
   stack. Diff the lockfiles and list every pin that moved. If numpy, scipy or anything else the simulation imports
   moves, stop and ask the owner: replay goldens are recorded on that stack. Reinstall your venv from the new lock.
   The gate is the replay check: if any replay golden or digest moves, stop and report it, because `simcore.core`
   imports no `maxim` and a moved golden means something reached the simulation. OD-I7's fix (`DamageRefused`, PR
   #1725) and OD-I5's (private) fix arrive with 1.3.4. Close both roadmap rows, citing your PR. Until you merge,
   you own the rows OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7, and step 3 leaves them alone (O79).
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
`constraints/py3.14.txt`, `docs/roadmap.md` (the OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7 rows only),
`docs/design/reviews/drift_and_lock/`, `docs/standards_backlog.md` (B49 to B51 only), `docs/lessons_maxim_in_games.md` (lesson number 41 only). No workflow edits: the job is right, the tests
are wrong.

**Review:** Executor, Architecture, Wire integrity, plus Determinism and replay (the lock moves the stack the goldens
are recorded on). One round. If a fold changes code, one delta round, then stop.

**Exit test:**
```bash
set -e
grep -qx 'pymaxim==1.3.4' constraints/py3.12.txt && grep -qx 'pymaxim==1.3.4' constraints/py3.14.txt
.venv/bin/python scripts/check_lock.py
GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1 .venv/bin/pytest -q tests/test_check_lock.py
G=tests/test_maxim_fixes_pending.py                     # the gates' module: use this name
for id in OD-I1 OD-I3 OD-I6; do grep -qE "$id([^0-9]|$)" $G || { echo "no gate names $id"; exit 1; }; done
test "$(grep -c 'strict=True' $G)" -eq 3 && test "$(grep -c 'raises=AssertionError' $G)" -eq 3
test "$(.venv/bin/pytest -q -rx $G | grep -c '^XFAIL')" -eq 3
# after a local prepush PASS and the owner's go-ahead for the push and the dispatch together:
gh workflow run drift.yml --ref phase1/drift-and-lock
sleep 10 && RUN=$(gh run list --workflow drift.yml --branch phase1/drift-and-lock --event workflow_dispatch --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch "$RUN" --exit-status
```
A red drift run files up to four public issues (`drift.yml`'s last step), so list any it opens for the owner. If
the run is red for a cause outside this step (a new numpy, ruff or mypy release, or 1.3.5 arriving and turning the
gates red), stop, record the cause, and ask the owner. The exit test then accepts a red run only if the owner has
accepted every one of its failures. Then `prepush: PASS <sha>` and all five PR jobs green. Only after that, close #60 to #63, each with a comment linking
the green drift run. Closing issues is outward-facing, so ask the owner first.

**Trigger for the repeat:** Maxim's 1.3.5 release. The upstream lane starts it when it reconciles at that release
(O78), not by reading the drift job, which O75's gates turn red then. A fresh session runs this brief's part 2 at
1.3.5 and removes the gates that flipped. It waits while step 4 is open (O79).

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
