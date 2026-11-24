# Step 3: the upstream lane's first reconciliation (`phase3/upstream-sync`)

You are the upstream lane (O77). You own `docs/maxim_upstream/` and the roadmap's Phase 3, and you are the
"Overdrive session that owns `maxim_upstream`" that Maxim's 1.3.5 world-clock session (D9 in Maxim's
`docs/plans/release_1_3_5.md`) reports its OD-A ids to. You run beside step 1a (O79), on the ids it reserves for you:
lesson number 42 and B52 to B54. Record any owner ruling in `docs/design/decisions/upstream_sync.md` (new; ids
`UP1`, `UP2` and so on). This step is docs only.

**Why now.** Maxim's D9 session writes the A-pre world-clock plan, which isn't on Maxim's `origin/main` yet (read at
`2fb497a1`). It starts from `docs/maxim_upstream/world_clock_release_DRAFT.md`, last changed 2026-11-16, which the
roadmap's tier A table supersedes in five places:
1. OD-A2's split clock (a machinery clock plus a perceived-time port).
2. The static AST ban extending Maxim's M72, instead of the draft's `sys.setprofile` tripwire.
3. OD-A7's RNG ruling: after the 1.4.0 cut, not in #1305.
4. OD-H6 withdrawing the loop-interval argument.
5. OD-A20 declined, with the calendar recast as perceived time.

It also lacks OD-A4's world-time tool duration (`runtime/tool_dispatch.py`, a fenced file) and OD-I8. Maxim's #1769
(`CostTracker`'s month from the wall clock against a host clock from 0) is routed by Maxim to this plan, and the
roadmap's OD-A4 row now cites it. The authoritative sources are the roadmap's tier A table and
`docs/design/reviews/maxim_response_2/response.md`.

**Order.**
1. Fetch Maxim and read its `origin/main` (never its working tree): `release_1_3_5.md` (D9, line 2's rows from about
   `:155` to `:168`, and line 6), `overdrive_refactor_candidates.md`, `experience_clock_decay.md`, and the issues the
   rows cite (`gh issue view <n> -R dennys246/Maxim`). Cite the sha you read.
2. Bring the draft in line:
   - Where tier A rules, replace the draft's text with the ruling, or mark the section superseded and point at the
     row.
   - The draft must not grow (an existing document), so cut as you replace.
   - Add a line "read at Maxim `origin/main` `<sha>`".
   - Never write the lock's current version into a draft: `constraints/` owns it, and step 2 moves it. Write the
     release a fix needs ("closes when the lock reaches the release holding #1773").
3. Read `docs/maxim_upstream/README.md` and `issues_now_DRAFT.md` against that sha. Restate each status in O76's form
   (the issue or PR number, the release that holds the fix, where the lock is), and nothing more.
4. Reconcile every Phase 3 row you touch the same way, except OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7, which step 2 owns
   until it merges (O79). Every other open row is the lane's. Give each row that states no
   trigger of its own the trigger "each Overdrive tag and each Maxim release".
5. Ask the owner, in one AskUserQuestion:
   - whether to file OD-I13 (seeds and samplers on backends; nothing filed in Maxim) and OD-I11 (searched, nothing
     found) as Maxim issues;
   - whether to tell Maxim's D9 session, or its coordinator maxim-eb, that the draft is current (both are
     outward-facing).

   Do only what the owner says.

**Files you may touch:** `docs/maxim_upstream/` (any file), `docs/roadmap.md` (Phase 3 only), `docs/plans/foundations_plan.md`
§3 (only if `scripts/check_plan.py` needs an id, and within its 2,500-word budget), `docs/design/reviews/upstream_sync/`, `docs/design/decisions/upstream_sync.md`,
`docs/standards_backlog.md` (B52 to B54 only), `docs/lessons_maxim_in_games.md` (lesson number 42 only). No code.

**Review:** Architecture, Wire integrity, Executor, plus Bio-faithful integration, which asks of every upstream draft
whether Maxim was searched first (CLAUDE.md, B22). One round, one delta, then stop.

**Exit test:**
```bash
set -e
F=docs/maxim_upstream/world_clock_release_DRAFT.md
test "$(wc -w < $F)" -le "$(git show origin/main:$F | wc -w)"
for id in OD-A2 OD-A3 OD-A4 OD-A5 OD-A6 OD-A7 OD-A8 OD-I8 '#1769'; do
  grep -qE -- "$id([^0-9]|$)" "$F" || { echo "missing $id"; exit 1; }
done
grep -qE 'read at Maxim `origin/main` `[0-9a-f]{8,}`' "$F"
# the five supersessions: each is applied or marked, and the tripwire survives only under a superseded heading
for w in OD-H6 OD-A20 'perceived-time port' 'machinery clock' '1.4.0' '#1305'; do grep -q -- "$w" "$F" || { echo "missing $w"; exit 1; }; done
awk '/^#/{h=$0} /setprofile/ && h !~ /[Ss]uperseded/ {print "setprofile outside a superseded section: " NR; bad=1} END{exit bad}' "$F"
.venv/bin/python scripts/check_plan.py && .venv/bin/python scripts/lint_standards.py >/dev/null
```
Then `prepush: PASS <sha>` and all five CI jobs green.

**After this step,** the lane reruns from this brief at each Overdrive tag and each Maxim release (O77), each time as
a fresh session, and never while step 4 is open (O79). At Maxim's 1.3.5 release it also starts step 2's repeat
(O78).

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
