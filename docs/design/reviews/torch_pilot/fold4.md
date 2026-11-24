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
