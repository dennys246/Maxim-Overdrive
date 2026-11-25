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

## After the delta round (RL11–RL13)

The delta round found two new BLOCKERs in text the fold added (Executor X-B1 with Wire B1, and Concurrency B1) and
left A-B4, W5, W6 and W11 open. Under the stop rule they went to the owner, who ruled RL11 and RL12 and amended the
stop rule (RL13): the contract findings fold, and the same four reviewers set statuses on those folds only, in their
delta reports. No other round follows.

| Delta finding | Fold (the author's account) |
|---|---|
| Executor X-B1, Wire B1 | RL11: the two-stage proof, `legacy` fields (§4, §8) |
| Concurrency B1, Executor S6, Wire N4 | RL12: the base is a fetched `origin/main`; no run mid-merge (§5) |
| A-B4, W5, Wire S1, Architecture N-S3 | §4: `confirms`, `corrects`, `amended_by_external`, `restates` takes paths |
| W6 | §4: `done_in` forms, one owner per fact after R3, `unknown` legal only at the migration |
| W11 | §4, §7: `read_record` splits the file; the loaders gain a text entry point; quoted dates |
| Architecture N-S1, Concurrency SF3, Executor S2 | §5: `renumber` never rewrites upstream files instead of refusing to run |
| Architecture N-S2, Executor S3, Wire S3 | §3, §5: slug ids are plain slugs within a log's directory; `slug` key |
| Wire S4 | §3: a cross-listed decision lives in the first of its logs by name |
| Wire S5 | §5: whole-token rewrites only, never in `docs/design/reviews/` |
| Concurrency SF1 | §6: `index` never discards text; §8: `migrate-branch` works after a clean merge |
| Concurrency SF2, Executor S5 | §5: `renumber --merged`; the owner starts the fix session |
| Executor S1 | §7: a lesson change without an `amended` entry is refused |
| Executor S4, Wire S2, the §2 counts NITs | §2: 18 gaps, counts at `1ed9caa`; hand titles for the five without a lead |
| A-N1 | §5: `B` duplicates stay `lint_guards`' |

Delta NITs, the author's call:

| NIT | Call | Trigger |
|---|---|---|
| Architecture: the restating-row example names the wrong log | fixed (§5) | — |
| Architecture: a lesson's `section` can't change | fixed (§4) | — |
| Architecture: lesson 11's heading tail | fixed (`legacy`, §8) | — |
| Architecture, Bio: an amended lesson cited upstream tells no one | left | step 4, R1: a note when an amended lesson is cited under `docs/maxim_upstream/` |
| Concurrency N1: `OD-` ids have no generated index | left: Phase 3 rows are out of scope (RL3) | when Phase 3 rows join |
| Concurrency N2: a hand-resolved line with both branches' citations | fixed: a test in §9 R1 | — |
| Concurrency N3: `migrate-branch` runs from `main` and commits on the branch | fixed (§8) | — |
| Concurrency N4: derived status lines conflict without a duplicate | left: resolved by regenerating | step 4, if such conflicts recur |
| Executor: "id order" undefined | fixed (§5) | — |
| Executor, Wire N2: `lint_contracts` has a scope regex, not an out-of-scope list | fixed (§3, §7) | — |
| Executor: CLAUDE.md's "A record id names one record" names the old logs after the migration | left: RL5 limits step 4's CLAUDE.md edits, so it goes to the owner | step 4, R3 |
| Executor: one id with one slug in two branches | left: the same file name is an add/add conflict, or the same record | — |
| Wire N5: retiring `check_plan`'s decision half drops its check of decision ids cited in designs | left | step 4, R1: decide whether `lint_ids` resolves decision ids cited in `docs/design/` |

## After the status check (RL14)

The status check of the RL13 fold found two new BLOCKERs in its text: Wire's (R3's presentation commit breaks §4's
change rules, and §8 said it changes no body text) and Executor's (X-B1's residue: `legacy` couldn't hold id-cell
qualifiers, slug-id rows' first cells or status-cell wording). The owner ruled RL14: a narrow fold with no further
check. Folded unreviewed, for step 4's first review round to read: §4's `qualifier` field and second exception, §8's
widened `legacy` list and corrected stage 2, and §9 R3's one PR. Executor's SF-A (nothing names "the migration
commit" for the lint) is deferred by its reviewer to step 4, R1 and R3.
