# Step 4: build the records layout and migrate (`phase1/records-build`)

You are the records-build session. You run alone (O79): no other session may be open while you migrate, because
the migration touches every shared record file (lessons, decisions, Known gaps, backlog). Step 5's slice branch may be in flight beside you; under O81 it writes no record file and opens no PR until you
merge, so it doesn't count against running alone. Before you start, ask the
owner to confirm that no other Overdrive session is running. Check `gh pr list --state open` and `git worktree list`
yourself too.

**Your base** is the folded design `docs/design/records_layout.md` as step 1a merged it, with its rulings (read
`docs/design/decisions/records_layout.md`). Build its §9 steps R1 to R3. R4 (late
branches) applies only to branches open at your migration, and there should be none. Don't redesign. If the
design is wrong against the tree, stop and take it to the owner as a design finding.

**Scope and the scope stop.** R1 is the format and the checks on fixtures. R2 is the converter with its round-trip
tests. R3 is the migration commit, including the Known gaps `kind` and, if step 1a's ruling on added Q6 said so,
guest text's two O73 channels as Known gaps: each gap owns its open channel and cites O73 for the measured bound,
since a ruling is never edited, and `checklists.md`'s step 7 points at the gap, and the lessons `section`, if Q7 did. If R1 and R2 have taken the
session, stop after R2: open the PR as R1–R2, gate it, and hand it to the owner, with R3 as the next session. Don't
migrate under time pressure.

**Files you may touch:** what §9 names (`scripts/records.py`, `scripts/lint_records.py` or the names the fold chose),
their tests and fixtures, the record files and directories the design defines, the generated indexes,
`scripts/lint_ids.py`, `scripts/lint_guards.py`, `scripts/check_plan.py`, `scripts/lint_contracts.py` and
`scripts/lint_standards.py` (§7's changes), `src/simcore/adapters/loaders.py` (only §4's text-level entry point to the
strict YAML grammar, §7's one engine change) and its tests, `scripts/lint_gates.py` (the gate-registry rows for that
entry point and `read_record`, §4), the red-gate `reason=` strings in `tests/` (R3's rewrite to gap slugs, §5),
`CLAUDE.md` (only the wording below), `docs/plans/checklists.md` (step 7's two guest-text items, which then point at their gaps), `docs/design/reviews/records_build/`, `docs/roadmap.md` (step 4's row), and `docs/plans/next_steps/` (only the record
paths in briefs 2, 3 and 5, moved to where the migration puts them).

**CLAUDE.md** (owner's amendment of this brief, 2026-11-24). Step 4 makes two changes, both in R3's first commit, and
no other:
- §8's wording, as RL5 accepted it.
- "A record id names one record" goes stale at the migration (it names `also in` rows and hand renumbering), and §8
  doesn't touch it. Step 4 replaces that rule with this text, accepted when this amendment merged:

  > **A record id names one record** (owner, 2026-11-23; one file per record, `docs/design/records_layout.md`).
  > Sessions number decisions, lessons, backlog rows and roadmap items on their own branches, so two can take the
  > same next id. Each decision id is defined once across `docs/design/decisions/` (a decision in two logs is one
  > record with `also_in`), each lesson number and each `B` row once, and each `OD-` item once in
  > `docs/roadmap.md`. Two branches adding to one family conflict in its generated index on purpose: that conflict
  > is the detector, and `scripts/records.py index` resolves it, never a hand edit. When ids collide, the branch
  > merged second renumbers its own record and its citations with `scripts/records.py renumber`, which rewrites
  > only the lines the branch added or changed and lists the rest; a green check doesn't prove a listed citation
  > moved. Guard: …

  The Guard line names, as `file::function`, the checks R1 leaves holding each family's uniqueness (`lint_ids`'
  for decisions, lessons and `OD-`, `lint_guards`' for `B`) and `lint_records`' generated-file check. Step 4 writes
  only those names; if R1 changes what the rest of the text says (a command's name, say), stop and ask the owner.

This amendment overrides §7's "CLAUDE.md changes only by the wording of §8" for this one rule; the design and RL5 are
not edited, and the review record cites this paragraph.

**Review:** Executor, Architecture, Wire integrity, plus Concurrency and lanes (ids under concurrent branches). One
round over the PR before the migration commit, and one delta on the folds, then stop. The design asks for a round per
R step. That isn't possible in one short session, so the one round covers R1 and R2, and the delta covers R3's
commit. The first round also reads the lines RL14 folded unreviewed: `docs/design/records_layout.md` §4's
`qualifier` field and its second one-time exception (R3's presentation commit), §8's widened `legacy` list and
corrected stage 2, and §9 R3's one PR.

**Exit test** (use the commands §9 names; if the fold renamed them, use its names and say so in the PR):
```bash
set -e
.venv/bin/python scripts/lint_records.py
.venv/bin/python -m pytest -q tests/test_records.py      # includes the round trip over the four files' fixtures
.venv/bin/python scripts/records.py index && git diff --exit-code || { echo "a generated index was stale"; exit 1; }
test "$(gh pr list --state open --json headRefName -q '[.[] | select(.headRefName != "phase1/records-build")] | length')" -eq 0   # no other PR is open
.venv/bin/python scripts/lint_standards.py >/dev/null
```
Then `prepush: PASS <sha>` and all five CI jobs green. Tell the owner the next sessions may fan out once this merges, and list every recurring trigger that fell while
this step was open (an Overdrive tag or a Maxim release), since those run now (O79).

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
