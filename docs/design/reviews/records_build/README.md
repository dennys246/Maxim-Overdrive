# Review record: step 4, the records build (`phase1/records-build`)

The step's brief is `docs/plans/next_steps/4_records_build.md`; the design is `docs/design/records_layout.md` with its
rulings RL1–RL14 (`docs/design/decisions/records_layout.md`).

## Scope reviewed

R1 (the format and the checks, on fixtures) and R2 (the converter, stage 1 of §8). R3, the migration commit, is not
in this branch: the brief's scope stop applies, and R3 is the next session's.

## Lenses

Executor, Architecture, Wire integrity, and Concurrency and lanes (ids under concurrent branches), as the brief names.
The first round also reads the lines RL14 folded unreviewed: `records_layout.md` §4's `qualifier` field and its second
one-time exception (R3's presentation commit), §8's widened `legacy` list and corrected stage 2, and §9 R3's one PR.

## The stop rule (written before round 1)

- One round over the branch, then one delta round, then stop (the brief's review plan; the design's round per R step
  is not possible in one session).
- A BLOCKER or SHOULD-FIX is folded.
- If a fold changes text or code, one delta round reads only that fold's diff, and no round follows it. A BLOCKER the
  delta round finds goes to the owner for a ruling, not to another round.
- A NIT is the author's call, fixed or left; either way it is recorded here with its reviewer's trigger, and becomes a
  backlog row only if it is a rule waiting for a check (O80).
- Reviewers, not the author, set each finding's status (O25). Reports are kept verbatim in this directory, each at
  most 3,000 words.

## Reports

Added below as each round lands.
