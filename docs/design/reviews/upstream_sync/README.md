# Review of step 3, the upstream lane's first run (`phase3/upstream-sync`)

**Lenses** (the brief, `docs/plans/next_steps/3_upstream_sync.md`): Architecture, Wire integrity, Executor and
Bio-faithful integration. Bio-faithful integration asks of every upstream draft whether Maxim was searched first
(CLAUDE.md, B22). Round 1 reads commit `71bb320` against `origin/main` `1ed9caa`.

**The stop rule, written before round 1:**
- A BLOCKER or SHOULD-FIX is folded.
- If a fold changes text, one delta round reads only that fold's diff, and no round follows it. A BLOCKER the delta
  round finds goes to the owner for a ruling, not to another round.
- A NIT is the author's call: fixed in a fold or left. Either way it is recorded here with its reviewer's trigger, and
  it becomes a backlog row only if it is a rule waiting for a check (O80).
- Reviewers, not the author, set each finding's status (O25). The reports are kept verbatim beside this file.
