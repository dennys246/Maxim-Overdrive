# Records layout design, round 1: Concurrency (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. The reader read `records_layout.md` at c7cbc24, with evidence from `gh api`, `gh pr diff`, the workflows and
grep. Nothing was edited or run.

**Summary:** the design solves the merge conflict, not the merge collision. §5's claim that a duplicate is caught
before the second merge is false here. A duplicate that reaches `main` can't be fixed under the design's own
immutability rule, `renumber` can silently move another branch's citation, "family" is undefined across directories,
and §8 misses an open PR and loses edits to existing rows.

## BLOCKER

- **C1, §5: a stale green CI lets the second duplicate merge.**
  - The evidence (verified): CI runs on `pull_request` and `push: main`; `main` is not protected and has no rulesets,
    so there's no "require up to date" and no merge queue; and a PR's run checks its merge ref only as of its last
    push.
  - The interleaving: A and B each add lesson 37 in different files, both green, and the owner merges both. They merge
    cleanly, and the duplicate is caught only by the push to `main`. Every session's next merge of `main` then brings
    in a red check it didn't cause.
  - *Fix options (unverified):*
    - (a) the owner requires branches to be up to date, or a merge queue, at a cost per merge;
    - (b) a per-family sentinel line in each generated file (`next id: 38`), so any two branches adding to a family
      conflict textually;
    - (c) collision-free ids.

    §5 must stop claiming the PR-CI catch.
- **C2, §4 against §5: a duplicate on `main` can't be fixed.** Fixing it means renaming a record that exists on the
  base, which §4 and §7 refuse, and once both branches have merged no session owns the fix. *Fix (unverified):* an
  owner-approved `renumber` exemption that the lint recognises for duplicates present on the base, with a rule that
  the session whose PR merged second opens the fix branch.
- **C3, §5: `renumber`'s "files the branch changed" catches the other branch's citations.** A cites lesson 37 in the
  roadmap and merges; B cites its own lesson 37 there, merges `main` and renumbers, and A's citation silently becomes
  38, resolving to B's lesson. *Fix (unverified):* rewrite only the branch's own added lines, refuse ids on lines from
  `main`, and let citations carry the slug (``lesson 37 (`thinking-off`)``) so a mis-citation goes red.

## SHOULD-FIX

- **S1:** "family" is undefined. Ids are global across directories (verified): O1–O58 across three logs, D across four,
  T across two, and restating rows repeat ids (O3, O6, O7, T1, T2, D20, O31; O7 twice in one file). Per-directory
  uniqueness allows two O59s; per-prefix uniqueness makes the migration of restate rows red. Fix: a family is an id
  prefix across all logs; restate rows become links; sub-ids (`O6a`, `D37 (1)`) get filenames.
- **S2:** `migrate-branch` keeps only added rows and reverts edits to existing ones (verified by diff):
  - #48 modifies B11 and B37;
  - PR #49, missing from §8, renumbers existing Known gaps in `architecture.md`, touches the lessons and conflicts
    with #52;
  - #47 edits the backlog.

  Fix: map edits onto mutable fields or refuse by name, and add #49.
- **S3:** the order of `migrate-branch` can't work. Mid-merge the old files are in conflict, and afterwards the merge
  base has moved. Fix: run it before merging, then merge and regenerate; R3 reruns `migrate` each time `main` moves.
- **S4:** `renumber` could be forced into a frozen file. `spikes/specgen/arms.yaml` cites lesson 36 and D34 in a
  frozen comment. Fix: refuse files listed in any `freeze.sha256`, and give a rule for which side renumbers.

## NIT

- **N1:** require deterministic generation (fixed order, no dates, SHAs or locale), and resolve generated conflicts
  by regenerating.
- **N2:** a cheap reservation: read the open PRs' heads before taking an id.

**What holds:**
- a gap's slug collision is an add/add conflict git catches;
- two status changes conflict inside one file;
- a third branch citing an unmerged id goes red.

The exception is a branch stacked on B, after C3's renumber, which the slug citation covers.
