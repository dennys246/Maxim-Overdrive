# Records layout design: the fold of round 1 (step 1a, 2026-11-24)

## Stop rule (written before the delta round)

- Every BLOCKER and SHOULD-FIX of round 1 is folded into `docs/design/records_layout.md`. A mechanism finding (a test
  plant, a script's behaviour) is folded as a test to write in §9's build steps, citing its finding, not as contract
  text.
- One delta round reads only the fold's diff, with the round-1 lenses: Architecture with Bio-faithful integration,
  Concurrency, Wire integrity and Executor. No round follows it.
- If the delta round finds a new BLOCKER in text the fold added, it is not folded. It goes to the owner for a ruling
  (CLAUDE.md, "Review finds; it doesn't design"; `docs/code_review.md`).
- A NIT is the author's call, fixed or left, and is recorded below with its reviewer's trigger. It becomes a backlog
  row only if it is a rule waiting for a check (O80).

## Base

The design at `35cec7b`, merged with `origin/main` at `1ed9caa`. The owner's rulings are RL1–RL10
(`docs/design/decisions/records_layout.md`). The fold also follows what `main` decided after round 1: #55's
`scripts/lint_ids.py` and the CLAUDE.md rule "A record id names one record".

## Where each finding went (the author's account; reviewers set the statuses in the delta reports)

| Finding | Fold |
|---|---|
| A-B1, C1, W1, A-S3 | RL8, RL9: id-ordered generated indexes conflict on purpose (§5, §6); §1's claim withdrawn |
| A-B2, W8 | RL10: mutable lesson bodies with an `amended` trail (§4); comparison against the merge base, deletion rules (§4) |
| A-B3, W4, S1 | §5: a family is an id prefix across every decision log, as `lint_ids` holds; cross-listed rows are one record with `also_in`; restating and id-less rows get slug ids |
| A-B4, W5 | §4: `amends` and `supersedes` may name an external ruling; status is derived from four fields; the title is the bold lead |
| C2 | §5: a rename that fixes a duplicate on the base is the one permitted change of an existing record's name |
| C3, W2, A-S1 | §5: `renumber` rewrites only lines the branch added against its merge base; R1 tests both errors on a shared file |
| W3, A-S2 | §5: the citation grammar is `lint_ids`'; decision citations are not resolved |
| A-S4, S2, S3, W9 | §8 rewritten: the PRs it listed have merged; `migrate-branch` runs before the merge and maps or refuses edits |
| A-S5, W7 | RL4 (§6) |
| A-S6, W10 | §7: `missing_ids` keeps its OD half |
| A-S7, W-N3 | §5, §9 R3: the `reason=` rewrite is scheduled; the generated file shows each slug |
| A-S8 | §6: authored header text lives in a hand-written header file per family |
| A-S9, W11 | §4: one reader, its delimiter grammar, versions per family, a gate-registry row |
| A-S10 | §5: an unmerged lesson is never cited upstream; `renumber` refuses ids cited under `docs/maxim_upstream/` |
| S4 | §5: `renumber` refuses frozen files |
| W6 | §4: gap and backlog fields; a fixed gap's record is deleted, as #52 rules |

## NITs (the author's call)

| NIT | Call | Trigger |
|---|---|---|
| A-N1 (two owners of backlog duplicates) | fixed: `lint_guards` keeps it (§7) | — |
| A-N2 (a gap's whole body is mutable) | fixed (§4) | — |
| A-N3 (findings in generated files name the record) | fixed (§7) | — |
| C-N1 (deterministic generation) | fixed (§6) | — |
| C-N2 (read open PR heads before taking an id) | left: O79's reserved blocks do this job | step 4, if a collision happens despite reservations |
| W-N1 (a lesson heading's date tail) | fixed: the heading is generated from `date` (§6) | — |
| W-N2 (`owner_section` values like "cites §8") | left: a converter detail | step 4, R2 |
| W-N4 (a range renumber collides one at a time) | fixed: `renumber` takes a whole mapping (§5) | — |
