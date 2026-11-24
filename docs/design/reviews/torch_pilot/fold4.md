# The merge round: `phase1/torch-pilot` onto main (2026-11-23)

**Why.** The branch was last merged with main at PR #42. Main then took about fifteen PRs, among them
`subcell_solids.md` (which applied TP1 into `fire_solid.md` §2 in its own words), the move of Known gaps to
`docs/known_gaps.md`, lesson 37 (#49) and #59. The torch pilot must land before the first base tag: main already
links to `torch_pilot.md` §3 from `fire_solid.md` §2, `generation_harness.md` and `reviews/subcell_solids/fold2.md`.

**What changed (author's account; the reviewers read the tree):**
- 88a410a merges main at 7500a85, with three conflicts:
  - `fire_solid.md` §1.3's contact paragraph: main's text, with the branch's ending ("6.1b's `kindle` uses
    geometry");
  - `fire_solid.md` §2: main's text, which already carries TP1's exception and drops `fuel_only_region`, plus the
    branch's "from 6.1b";
  - the lessons file: main's 37 keeps its number; the branch's becomes 38;
  - `roadmap.md`: the branch's TP6 sentence with main's write-window and port bullets; main's `known_gaps.md` link
    with the branch's TP6 sentence; both sides' evidence in OD-A16.
- The same commit moves the branch's two citations of its lesson (`torch_pilot.md` §12, the OD-A16 row) to 38, and
  points `torch_pilot.md` §7 and §10 at `docs/known_gaps.md`.
- 2728425 merges main at b578761 (#59), with no conflict.
- This commit parks the records layout: a Phase 1 row in `roadmap.md`.

**Scope of the round.** The merges' resolutions, including the files that merged without a conflict, the
renumbering, and the parked row. The design itself is not re-reviewed: rounds 1 and 2 and the status check ran.

**Readers.** Architecture, Wire integrity and Executor (`docs/code_review.md`), in parallel and independent.

**The stop rule, written before the round:**
- A BLOCKER or SHOULD-FIX is folded.
- If that fold changes text, one more round reads only that fold's diff. No round runs after it.
- A NIT goes to a backlog row or a Known gap, with no change to the text.
- The reviewers set each finding's status, not the author.

**Reports:** `merge_architecture.md`, `merge_wire.md` and `merge_executor.md`, verbatim.

## The round (head afdb849)

| Reader | BLOCKER | SHOULD-FIX | NIT |
|---|---|---|---|
| Architecture (`merge_architecture.md`) | A-B1 | A-S1, A-S2, A-S3 | A-N1, A-N2 |
| Wire (`merge_wire.md`) | — | W-S1, W-S2, W-S3 | W-N1, W-N2 |
| Executor (`merge_executor.md`) | E-B1 | E-S1 | E-N1, E-N2 |

The same defect, found by more than one reader: A-B1 = E-B1; A-S1 = W-S1; A-S2 = W-S3 = E-S1; A-N2 = E-N2.

**The author's correction, first.** The parked row said the records-layout review found three BLOCKERs. It found
eleven. The author took the count from the session's brief, and the author's own check read only each report's first lines.

**The owner's rulings (2026-11-23):**
- TP10, on A-B1: a cell region is a candidate by authored geometry, as the applier's "gone" is.
- TP11, on W-S2, option (a): TP5's layout stands, and the pilots table ships with 5b, with an `i32` dtype and a
  protocol bump.

**The fold (author's claims; the delta round sets their statuses):**

| Id | Change | Commit |
|---|---|---|
| A-B1, E-B1 | `torch_pilot.md` §3's candidacy and §7's gap follow TP10 | 4a9e5e8 |
| A-S1, W-S1 | §9.4: `..._same_time_...`; `core/deposit.py::Deposit` for `World._power_field` | 4a9e5e8 |
| A-S2, W-S3, E-S1 | the parked row: eleven BLOCKERs, named | 4a9e5e8 |
| A-S3 | checklist 6.1b: a destroyed region stays a candidate at every grid; U4 judges with §5's pilot condition | 4a9e5e8 |
| W-S2 | tile §2.2 and checklist 5b follow TP11 | 8710f4c |

**NITs, with no change to the text (the stop rule).** None fits a backlog row (a rule waiting for a check) or a
Known gap (a physics gap), as E-N1 says, so each is recorded here, with its trigger:
- A-N1 (the trigger's "tag" and "fan-out"): the planning session after the tag, which restates the roadmap.
- A-N2, E-N2 ("three conflicts" over four resolutions): three files, four hunks. Left as written.
- W-N1 (`data/world/actions.yaml:7`'s marker reason cites `docs/architecture.md`): main's text; 6.1b removes the
  marker.
- W-N2 (`OD-C11` cited in tile §2.3, §3.1, §8 and §10, defined nowhere): main's text; the planning session.
- E-N1 (the stop rule's gaps): this record. A BLOCKER found by the one delta round goes to the owner for a ruling, not
  to another round.

**The delta round** reads `git diff afdb849 8710f4c`, and only that, with the three lenses. It sets every status above.

## The delta round, and the stop

`merge_delta.md` read `afdb849..8710f4c` with the three lenses and set the statuses: 9 fixed, 4 deferred (A-S3,
A-N1, W-N1, W-N2), 2 rejected (A-N2, E-N2), none open. It found no BLOCKER and no SHOULD-FIX. Its four NITs change
no text, by the stop rule, and are deferred with the reviewer's triggers:
- D-N1 (`fire_solid.md` §2's `Deposit` row and §3.1's guard against §9.4's deletion): 6.1b;
- D-N2 (TP5 not marked as partly superseded by TP11): the decision log's next edit;
- D-N3 (which act refuses a tick past 2³² − 1, under which code): 5b, as a test to write;
- D-N4 (`subcell_solids.md` §4.3's planned "gone" against TP10): the step that makes `_check_region` follow §4.3.

No round runs after this one.
