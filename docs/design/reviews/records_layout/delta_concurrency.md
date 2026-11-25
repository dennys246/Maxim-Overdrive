# Records layout design, delta round: Concurrency (2026-11-24)

Read: the fold's diff, `git diff 239f267 9d1e747` (the design, the rulings RL1–RL10, `fold.md`, two roadmap rows), with
round 1's `round1_concurrency.md`. Ran: scratch git repositories under `<scratchpad>` (merge-ort, `zdiff3`,
`git merge-tree`) for the index conflict and the migration window; `gh pr view` for #47, #48, #49, #52; `git
rev-parse` and `git merge-base` in this worktree for the base ref; grep over `scripts/lint_ids.py`,
`scripts/prepush.sh`, the decision logs and `docs/maxim_upstream/`. Nothing in the tree was edited but this report.

## Round-1 statuses

| Finding | Status | Evidence |
|---|---|---|
| C1 | fixed | §1 withdraws the PR-CI claim; §5 "Detection, before the second merge" and §6's id-ordered indexes (RL9), RL8 recorded. Verified by experiment: two branches inserting different lines after the same last index line conflict under merge-ort, under `merge.conflictstyle=zdiff3`, and in `git merge-tree` (exit 1), whether the index is mid-file (lessons head) or at EOF (backlog table). A duplicate id sorts to the same position, so it always lands in one hunk. GitHub's refusal itself was not exercised (no push); it follows from the server's merge reporting a conflict, with the caveat that GitHub's web conflict editor can still resolve it by hand, which §6 forbids. R1 has the test. Residuals are new findings SF1 (migration window) and N1 (`OD-`). |
| C2 | fixed | §5 "A duplicate on `main`": the rename of an existing record is allowed only while `main` holds two records with the id and the branch leaves one; the second-to-reach-`main` record is renamed; CLAUDE.md names the branch merged second. R1 tests "only in its case". The fix branch can't move the citations, though: new finding SF2. |
| C3 | fixed | §5 Resolution: `renumber` rewrites only lines the branch added or changed against its merge base, lists `main`'s citations without rewriting; R1 tests it on a shared file (C3, W2, A-S1). The contract names the wrong base ref for this repo's worktrees, which reopens C3 in practice: new finding B1. |
| C-S1 | fixed | §5 "A family": an id prefix across every log, as `lint_ids` holds; cross-listed rows one record with `also_in`; restating and id-less rows get log-qualified slug ids. Sub-ids (`O6a`, `O7a`, `O11a`, `O15a`, the only ones in the logs today) are covered: `lint_ids::_ID_CELL` accepts a `[a-z]?` suffix and §3's `<id>-<slug>.md` names them. No `D37 (1)` form exists in the logs. R2 tests it. |
| C-S2 | fixed | §8: `migrate-branch` maps each edit onto a change §4 allows or refuses it by name; R2 tests both. The PRs §8 listed are gone because they merged (`gh pr view`: #47, #48, #49, #52 all MERGED on 2026-11-23). |
| C-S3 | fixed | §8: `migrate-branch` runs before the branch merges `main`, then the branch merges and regenerates; R3 reruns `migrate` if `main` moves; R2 tests the order. Wording nit: N3. |
| C-S4 | fixed | §5: `renumber` refuses a file listed in any `freeze.sha256`; CLAUDE.md's "the branch merged second renumbers" gives the side. R1 tests it. |
| C-N1 | fixed | §6: deterministic generation, conflicts resolved by regenerating; R1 tests locales and time zones. |
| C-N2 | deferred | Not adopted: O79 and O81 reserve blocks for every planned step and RL9 now detects a collision before the second merge. Trigger: a collision at step 4 or later despite the reservations. |

## New findings

### BLOCKER

- **B1, §5 Resolution (and §7's `lint_records` "compared with the merge base"): "its merge base with `main`" resolves
  to the owner's stale local `main`, so `renumber` silently rewrites the other branch's citations, which is C3
  again.**
  - The evidence (verified): in this worktree `main` is `814dea9` and `origin/main` is `1ed9caa`, two merges ahead. The
    gate's base convention (`scripts/prepush.sh` header: "base: main if it exists, else origin/main"), which §7 tells
    `lint_records` to follow ("as `lint_sizes.py`'s ratchet compares"), picks the stale one. `git diff --stat
    $(git merge-base HEAD main) HEAD` reports 938 files changed; against `origin/main` it is 7. Sessions never update
    local `main` (the main checkout is the owner's), they merge `origin/main`, as 239f267 did.
  - The interleaving: A adds lesson number `47` and cites it on a roadmap row; A merges. B, branched earlier, also took 47 and
    cites it. GitHub refuses B (RL9 works). B's session merges `origin/main`, regenerates, sees the duplicate, runs
    `renumber 47=48`. `merge-base(HEAD, main)` is the stale `main`, older than A's merge, so A's roadmap line counts as
    a line B added: A's citation is rewritten to 48 and now names B's lesson. Nothing goes red, since every citation
    resolves. The same happens if `renumber` runs mid-merge, before the merge commit, against the working tree.
  - Why it's contract: §5's rule is defined by which lines are "the branch's", and that is set by the ref. Every
    consumer (`renumber`, `lint_records`' §4 comparison, the C2 case "while `main` holds two records") depends on it.
  - *Fix (unverified):* §5 names the base as the `main` commit the branch last merged (the merge commit's second
    parent, or `origin/main` fetched at the merge), and `renumber` refuses to run with `MERGE_HEAD` present or with a
    base older than the last merged `main`; R1 adds the stale-local-`main` fixture beside C3's test.

### SHOULD-FIX

- **SF1, §8 "When" with §6's round trip: an old-format edit merges cleanly into the migrated file, in either order,
  and lives only in a generated file.**
  - The evidence (verified, scratch repo): the old lessons file, a step-4 branch that adds the marker and the index at
    the head and keeps the body byte-identical (as §8's round trip requires), and a late branch that appends lesson number `41`
    to the old file. Merging step 4 then the late branch, and the late branch then step 4, are both clean: the
    generated file holds "### 41." with no record file and no index line. A mid-body edit (a lesson 20 correction)
    also merges cleanly. A decision log whose only change is the marker takes an appended row cleanly too.
  - The interleaving: O79 says step 4 runs alone, but sessions are resumed by the owner (O79 part 4) and a branch
    handed off before step 4 (step 2, 3, or the slice branch breaking O81) can still be merged after it. Both PRs'
    checks are green on their last push and GitHub shows no conflict, so RL9's detector never fires and §8's "runs
    `migrate-branch` at its next merge of `main`" never happens. `main` goes red on the generated-file check, and
    every session that merges `main` sees it; §6 says to resolve a generated file by regenerating, and §7's message
    names `migrate-branch`, which §8 defines only before the branch merges. The first session that regenerates to get
    green deletes lesson number `41` from the tree, with no conflict to show it.
  - *Fix (unverified):* a contract for the post-merge case (the check names the commit that brought the hand edit and
    a `migrate-branch` mode that runs on `main`'s result), or a generated form that never matches the old bytes; R3
    tests both orders with a late appending branch.

- **SF2, §5 "A duplicate on `main`" with §5 Resolution: the fix branch can rename the record but `renumber` can't
  move its citations.**
  - The interleaving: A and B both land lesson number `47` on `main` (the web conflict editor, or SF1's path for gaps). The fix
    branch, cut from `main`, runs `renumber 47=48` on B's record. Every citation of 47 is now on a line that came from
    `main`, so by §5's rule none is rewritten; all are only listed, and nothing says which are B's. After the rename
    B's citations silently resolve to A's lesson. The C2 exemption permits the rename, but the tool the design names
    for it can't finish it.
  - *Fix (unverified):* in the duplicate-on-`main` case, "the branch's lines" are the lines the second-merged PR's
    merge commit added against its first parent; R1's C2 test checks a citation moves.

- **SF3, §5 Resolution, the refusal "an old id cited anywhere under `docs/maxim_upstream/`": the refusal fires on the
  first record's citation and blocks the second record's renumber, with no other path.**
  - A collision always has the old id on `main`, and A-S10's rule ("a lesson is cited upstream only after it is on
    `main`") means any upstream citation of that id names the *first* record, which stays put. Today
    `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md` cites lesson 1.
  - The interleaving: lesson number `46` is on `main` and cited in an upstream draft. Another branch also took 46 and is
    refused by GitHub (RL9). Its session runs `renumber 46=47`, which refuses because 46 is cited under
    `docs/maxim_upstream/`. The branch can't merge, the first record can't be renamed (it's cited upstream, and §4
    forbids it), and the contract gives no third way, so a hand rename follows, which §5 exists to prevent.
  - *Fix (unverified):* refuse only when a line the branch added under `docs/maxim_upstream/` cites the old id; R1
    tests a collision whose first record is cited upstream.

### NIT

- **N1, §5 "A family" lists `OD-` ids, and "Detection" says "each id-bearing family has one generated index",
  but `OD-` has none (RL3 keeps it in the roadmap).** Two `OD-` rows with one id in different Phase 3 tables merge
  cleanly with stale green checks, which is C1's original interleaving. RL3 accepts this scope; the design should say
  that `OD-` duplicates are still caught only after the second merge.
- **N2, §5 Resolution's granularity is a line.** A roadmap line A edited to cite lesson number `47`, which B also edits for
  another reason, conflicts; resolved by hand it becomes a line "the branch changed", so both 47s on it are rewritten.
  R1's shared-file test could include a line both branches touch.
- **N3, §8: `migrate-branch` "runs from a checkout of `main`" and "commits the result on the branch".** One process
  can't do both in one worktree, and CLAUDE.md keeps sessions out of the main checkout. Presumably main's
  `records.py` run against the branch's worktree; R2's S3 test can fix the meaning.
- **N4, §6: `decisions_index.md` carries the derived status on each id line.** A new ruling that supersedes D10 rewrites
  D10's line, so two branches adding unrelated rulings that amend adjacent ids conflict without a duplicate. That
  costs a regeneration, not correctness, and is worth one line in §5 so a session doesn't read every index conflict as
  a duplicate.

## Status check after the RL13 fold (2026-11-24)

Read: `git diff 14c2e5d 01cbb25` (the design, RL11–RL13, fold.md's "After the delta round"), checked against the
tree. Ran: in the SF1 scratch repository under `<scratchpad>`, `git merge-base late main` after the late branch had
merged into `main`; `grep` of `.github/workflows/` for the base CI uses. No round-1 status changed.

| Finding | Status | Evidence |
|---|---|---|
| B1 | fixed | §5 "The base": the merge base with a freshly fetched `origin/main`, never local `main`; `renumber` and the change check refuse during an uncommitted merge (RL12); §4, §7 and §8 point at it; R1 tests a stale local `main` and the mid-merge refusal. CI already compares with `origin/main` at `fetch-depth: 0` (`test.yml`). Merging `origin/main` and fetching again later still gives the last merged `main` commit as the base, so lines `main` gained after that aren't in the branch at all. Residual NIT: §7 still says "as `lint_sizes.py`'s ratchet compares", and that ratchet's base is `prepush.sh`'s "main if it exists"; R1's stale-`main` test is what holds it. |
| SF1 | fixed | §6: regeneration never discards text; `index` refuses a generated file holding an entry no record holds and names it; R1 tests it. The loss I described can't happen now. Residual: my scenario had the late PR merged into `main` on GitHub. Then the merge base of that branch with `origin/main` is the branch's own tip (verified: `git merge-base late main` equals `late`, and the diff is empty), so `migrate-branch`'s "branch's own commits' diff against the base" finds nothing, and the tool §6 and §7 name can't do the repair. `main` stays red and every regeneration refuses until someone writes the record by hand. That is recoverable, with nothing lost, so it isn't a BLOCKER. R2's "after a clean merge" test should include the PR-already-on-`main` case. |
| SF2 | fixed | §5: `lint_ids` names the PR that brought the second record; the owner starts the fix session; `renumber --merged <PR>` rewrites citations in that merge commit's lines against its first parent; R1 tests it. A squash or rebase merge has no two-parent merge commit; R1 should cover the merge method the owner uses. |
| SF3 | fixed | §5: `renumber` never rewrites a file under `docs/maxim_upstream/` instead of refusing to run, and `check_records` refuses an added upstream citation of a lesson not on the base; R1 tests that the branch's record is still renumbered when `main`'s is cited upstream. |
| N1 | deferred | Left by the author: `OD-` rows are out of scope (RL3). Trigger: when Phase 3 rows join the records. §5's "Each id-bearing family has one generated index" still overstates it for `OD-`. |
| N2 | deferred | Moved to §9 R1 as a test: a hand-resolved line holding both branches' citations is listed, not rewritten. Trigger: R1. §5 still says `renumber` rewrites lines the branch "added or changed", which covers that line, so R1 must reconcile the text with the test. |
| N3 | fixed | §8: `migrate-branch` runs in a detached worktree of a fetched `origin/main`, writes into the branch's worktree, and leaves the commit to the branch's session. |
| N4 | deferred | Left: such a conflict costs a regeneration, not correctness. Trigger: step 4, if such conflicts recur. |

### New BLOCKER in the fold

None. The one gap I found is SF1's residual above: after a late PR has merged into `main`, `migrate-branch` finds no
diff. It is recoverable by hand and loses nothing.
