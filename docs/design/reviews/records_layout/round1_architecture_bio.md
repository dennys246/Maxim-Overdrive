# Records layout design, round 1: Architecture and Bio-faithful (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. The reader read `records_layout.md` at c7cbc24 against:
- the tooling: `check_plan`, `lint_contracts`, `lint_guards`, `lint_standards` and `test_fields`;
- every decision log, the lessons file and the backlog;
- the diffs of #47–#52 and of torch-pilot.

## BLOCKER

- **A-B1, §3 and §6: committed generated indexes bring the merge conflicts back.** Two branches adding different ids
  both regenerate the same index and append at the same spot. Tested in a scratch repository: `CONFLICT (content):
  Merge conflict in idx.md`. GitHub can't merge a conflicted PR, so §1's cost stays. *Fix options (unverified):*
  - don't commit the indexes, though upstream links need a stable target;
  - a merge driver, though GitHub ignores custom drivers, and whether its merge button honours built-in
    `merge=union` is unchecked;
  - keep the conflicts, make the resolution `records.py index`, and withdraw §1's claim.
- **A-B2, §4: immutable lessons contradict CLAUDE.md** ("add or update an entry"; "kept current") and current
  practice. Lesson 11 was reworded, lesson 23 amended in place, and #49 rewrites lesson 23's Consequence for a renamed
  test. Under the design that edit is refused, and the stale name stays. Bio: lesson 29's false claim, corrected by
  `delta_executor` D-N1, is the evidence base for OD-A24, and errata as new lessons would leave it unmarked in the
  generated file. *An owner question §10 omits:* mutable lesson bodies with a dated amendment trail, or `corrects`
  and `amends` with a derived status.
- **A-B3, §5 and §2: decisions have no single id namespace.**
  - "D" is two sequences (D1–D15 in `sem_stimuli`, D20–D37 in `world_model`).
  - "Also in" rows duplicate O3–O7, O7a, O31, T1, T2 and D20.
  - Restating rows (D26–D28, RT1–4…) aren't records, four rows have no id, and some ids aren't ids ("ruled 1", "the
    split", "S4", "PH2-S2, re-ruled", "CLAUDE.md").
  - The migration writes two O3 files, and CLAUDE.md's "(A1 and D1)" means review findings yet resolves to
    `sem_stimuli`'s D1.

  *Fix (unverified):* define the namespace (design-qualified ids or a prefix registry with one owner); restating rows
  become links; say how id-less rows are named.
- **A-B4, §4: derived status loses recorded information.** Eight statuses read "amended by docs-contracts ruling
  41/45/…", from `reviews/docs_contracts/rulings.md`, not from decision records. Others read "restates" or "also in".
  §8 lets round-trip differences pass as "a named, reviewed change", so they could be dropped. *Fix (unverified):*
  `amends` may name an external ruling record, or those rulings migrate as records.

## SHOULD-FIX

- **A-S1:** a missed renumber resolves silently to the other branch's record, so R1's test "a missed citation goes
  red" can't fail in its real case. "Files the branch changed" also catches `main`'s citations after a merge. Fix:
  rewrite by hunk, and flag renumbered ids in those lines.
- **A-S2:** citation forms beyond `lesson N` exist: "Lesson N" (11), "lessons N and N" (9), "lessons N" (4), "lesson
  §N" (3), and "`lessons_maxim_in_games.md` §N". Enumerate them at R1, or lint one canonical form.
- **A-S3:** detection "before the owner merges" doesn't hold, since `main` is unprotected and PR checks don't rerun.
  Name the owner setting, or the real detector.
- **A-S4:** §8 omits #49 and edits that aren't additions (lesson 23, the Known gaps, CLAUDE.md, torch-pilot's backlog
  edit).
- **A-S5:** the backlog cap (200) is below existing rows: B5 about 447, B7 about 408, B19 about 366. Lessons and
  decisions fit. State caps as "measured at R1".
- **A-S6:** retiring `missing_ids` also drops the check that 84 `OD-` ids appear in the plan. Keep that half, or have
  the owner rule it out.
- **A-S7:** "reason= strings name the gap's slug" is unscheduled work, and the generated file needs a visible slug.
- **A-S8:** authored prose (headers, intros) moves into generator code, outside `lint_contracts` and the budgets. Fix:
  an authored header file per family.
- **A-S9:** "the loaders' strict reader, or the scripts' equivalent" gives the format two owners.
- **A-S10, Bio:** if an unmerged lesson is cited in a Maxim issue or draft and later renumbered, Maxim's copy goes
  stale for good. Fix: never cite an unmerged lesson upstream, or refuse a renumber cited under
  `docs/maxim_upstream/`.

## NIT

- A-N1: `lint_guards` already refuses duplicate backlog ids, so two owners.
- A-N2: say a Known gap's whole body is mutable.
- A-N3: `lint_contracts` scans text, so findings in generated files must name the record to edit, with stable
  section numbering.

**Bio-faithful:** nothing touches what NPCs sense, act through or keep time by. Lessons stay citable by path and
heading. The risks are A-B2 and A-S10.
