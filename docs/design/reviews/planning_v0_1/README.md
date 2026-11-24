# Review of the planning session after `v0.1.0` (`phase1/planning`)

**Scope.** The roadmap diff and the rulings O75–O79 (`git diff 41036dc..<the reviewed commit> -- docs/`), and the five
step briefs. Round 1 read them in `.worktrees/_durable/next_steps_v0_1/`, a copy the fold deleted. That text is
rebuilt exactly, by reversing the fold's recorded replacements, at `round1_briefs/` (delta review ED10, WD3). The
folded briefs are at `docs/plans/next_steps/` (O79).

**Lenses:** Architecture, Wire integrity and Executor (`docs/code_review.md`), one round, run in parallel by
independent readers.

**The stop rule** (written before the round, as the planning brief requires):
- A BLOCKER or a SHOULD-FIX is folded.
- If a fold changes text, one delta round reads only that fold's diff, and no round follows it. A BLOCKER the delta
  round finds goes to the owner for a ruling, not to another round.
- A NIT becomes a backlog row in `docs/standards_backlog.md`, with no other change.
  *Amended after round 1 by the owner's ruling O80 (A10, AD6):* a NIT is the author's call; fixed or not, it is
  recorded with its reviewer's trigger, and becomes a backlog row only if it is a rule waiting for a check.
- The reviewers, not the author, set each finding's status (O25). Their reports are recorded verbatim beside this
  file.
