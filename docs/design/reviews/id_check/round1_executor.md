# lint_ids, round 1: Executor (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. The reader worked in a scratch copy and edited nothing in the worktree.

**Verdict:** the lint does its main job on the real tree. A duplicate lesson heading and a dangling citation, appended
to a scratch copy of the real lessons file, both fail through `scripts/lint_standards.py` end to end. The real tree is
clean: 36 headings, 221 citations, 117 decision ids. The ten ids defined twice (O3–O7, O7a, O31, T1, T2, D20) are all
cross-listed both ways. `main-protection` is strict, so the PR merged second reruns on the new base. No BLOCKER.

## SHOULD-FIX

1. **`scripts/lint_standards.py::main`: the wiring has no test.** Replacing `problems += check_ids(files)` with `pass`
   left all 165 tests green. Fix (verified): a `test_lint_standards.py` case where a duplicate lesson makes `main()`
   return 1.
2. **`scripts/lint_ids.py::_CITE`: three file-name citation forms are missed.**
   - `` `lessons_maxim_in_games.md` 30 `` (no §) at `docs/design/inference_placement.md:351` and
     `docs/design/reviews/sem_stimuli/bio_faithful.md:232`;
   - `` `lessons_maxim_in_games.md::24` `` (twice, in `reviews/fire_model/`);
   - `§1, §30` after the file name, where only §1 is read.

   Failure: lesson 30 is renumbered, the citation dangles, and the gate stays green. Fix (verified: the real tree stays
   clean, citations go from 221 to 225): make the second alternative
   `` lessons_maxim_in_games\.md`?(?:::|[ \t]*§?[ \t]*)(\d+(?:[ \t]*(?:,|and|–){_SEP_GAP}§[ \t]*\d+)*) ``.
3. **`scripts/lint_ids.py::_ID_CELL`: a decorated id cell is silently not a record.** `` `O58` ``, `**O58**`,
   `O58 (provisional)`, `O58,provisional` and `PH2-S2`, each put in two logs, give 0 problems. `PH2-S2, re-ruled`
   (`decisions/sem_stimuli.md:29`) is a real id skipped today. Failure: one branch writes `| **O58** |`, another
   writes `| O58 |`, and both merge green. Fix (unverified): refuse an id-like first cell that matches no known shape,
   or widen `_ID_CELL`.

## NIT

4. **`tests/test_lint_ids.py::test_every_citation_spelling_of_a_missing_lesson_fails`** can't fail on the line number:
   the second half of its `or` is always true. The mutation `line = 1` survived the file.
5. **`_cited`: a date after a citation is read as lessons.** `lesson 24, 2026-11-20` reports 2026, 11 and 20 as
   dangling; `lesson 2 to 2026` misfires too. A loud false red, not in the tree today.
6. **`_cross_listed`: the status-cell parse is untested.** The mutations `status = line` (an "also in" in the
   decision text would excuse a collision) and dropping `len(defs) != 2` survived.

Not a defect: no `reason=` string in `tests/` cites a lesson today, and a range checks only its two ends, as the
docstring says.

## Mutations

34 on `lint_ids.py` plus 1 on the wiring. Killed: 31, covering the decision family, cross-listing, the lesson
headings and every citation spelling, the `reason=` reader, frozen files and scope. Survived: `len(defs) != 2`
dropped, `status = line`, `line = 1`, and the wiring.
