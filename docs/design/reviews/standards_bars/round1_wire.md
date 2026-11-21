# PR 21 / 7debd5c: Wire integrity review

Reviewer: Wire integrity lens. Tree: `.worktrees/standards-bars` at 7debd5c, read only.

## The base moved: read this first

PR #21 is already **MERGED** (2026-11-21T17:32Z, merge commit 78a914a). Its only commit was c72fbe2. `origin/main` is
now 78a914a, so `git diff origin/main...7debd5c` today shows only 7debd5c (merge base c72fbe2). The remote branch
`phase1/standards-bars` is gone (`git ls-remote origin phase1/standards-bars` is empty), and 7debd5c is on no remote.
I reviewed both commits: c72fbe2 as merged, and 7debd5c as the unmerged follow-up.

## What I checked

| Contract | How | Result |
|---|---|---|
| PR count "19 enforced, 27 review" | `scripts/lint_standards.py` at HEAD; `check_guards` on `git show <rev>:` text for 35a1702, c72fbe2, 7debd5c | 35a1702: 18/24. c72fbe2: 19/27. 7debd5c: 19/27, PASS, 0 findings. **The claim matches** both commits |
| Delta of counts | per-bullet classification at 7debd5c | +1 checked (future bar, through its strict-half path), +3 review (three kinds, contract, review finds). Red-gate rule stays checked after B34 is added |
| Each new Guard parses as meant | `GUARD`, `PATH_REF`, `BACKLOG_REF` on each new bullet | All four rules end in `Guard:`, every B id resolves, every path exists. "(strict)" and "(the issue, the row, the evidence)" annotations are ignored as intended |
| Backlog ids unique, B30 to B34 present | lint duplicate check; read the table | Unique, all present |
| B30 to B34 format | against the header `ID / Rule it enforces / The check / Lands with` and rows B1 to B29 | Four columns, "open" in Lands with, as B10, B13, B15 do. One naming NIT (N1) |
| CLAUDE.md vs charter vs backlog wording | read all three | One scope mismatch (S2), one wording NIT (N2) |
| Cited guard test actually checks the cited half | read `tests/test_tooling_config.py::test_red_gates_are_strict_and_warnings_are_errors` | It asserts `xfail_strict`, `filterwarnings == ["error"]`, `--strict-markers`. It holds "strict"; it does not hold `raises=`, a reason, "never skip" or the upstream issue (S1) |
| Every strict gate has `raises=` | grep `xfail` in `tests/` | 4 gates, all `raises=AssertionError` at 7debd5c (3 in `test_act_validation.py`, 1 in `test_cross_tier.py`) |
| Paths named in rule text | `ls` | `docs/plans/long_term_features.md` does not exist on this branch or main (B1) |
| PR body vs the commits | `gh pr view 21` against `git log` | Body describes c72fbe2 correctly; says nothing of 7debd5c (B2) |

## Findings

### BLOCKER

**B1. `CLAUDE.md::"A design document holds the contract"` cites a file that doesn't exist.**
The rule says "Laws stay simple and swappable behind the contract (`docs/plans/long_term_features.md`)". That file
isn't on this branch or on main; `git log --all` finds it only on the SEM stimulus branch (41bd42a, 86950ad, e381295).
It is merged into main as of 78a914a. Failure scenario: a session on main follows the rule to read where laws stay
swappable, and the path leads nowhere. If the SEM branch renames or drops the file, it stays dangling for good. The
lint misses it because the path sits in the rule text, not after `Guard:`; `lint_guards` resolves only Guard paths.
Calling it a BLOCKER because it ships in a binding rule file and points at a branch's work in progress, against
"Assume other agents are working", which keeps sessions' files apart. Fix: drop the parenthetical, or land it with
the SEM branch that adds the file. Unverified. A lint that resolves every backticked repo path in CLAUDE.md would
catch the class: unverified, a backlog candidate.

**B2. 7debd5c has no PR and no pushed branch, and the PR it was written for is merged.**
The rule change it makes (`raises=` required), B34 and the change to `tests/test_cross_tier.py` are not in main. PR
#21's body ("B30–B33", "with no code", the gate at c72fbe2) describes what merged, so the body is accurate for 21. But
any hand-off that presents 7debd5c as "PR 21" is false. Failure scenario: the owner reads PR 21 as covering the
`raises=` rule and believes main requires it. Main's CLAUDE.md still has the old red-gate wording, and main's burnout
gate still lacks `raises=`. 7debd5c also needs its own `prepush: PASS 7debd5c...`: I found none, and the only PASS
line on record is for c72fbe2. Fix: the owner decides, on a new branch from main per CLAUDE.md (a rebase onto
78a914a is an empty change apart from 7debd5c), a new PR, and a gate run on that sha. Unverified.

### SHOULD-FIX

**S1. `scripts/lint_guards.py::check_guards` counts a partly checked rule as "enforced by a check", and this PR adds
one more.** A rule counts as checked if any non-`docs/` path appears after `Guard:`. The future-bar rule's new
"checked" count comes from `test_red_gates_are_strict_and_warnings_are_errors`, which holds only `xfail_strict = true`.
The issue, the Phase 3 row and the evidence (B31) are the substance, and review holds them. At 7debd5c the red-gate
rule's new `raises=` half is likewise unchecked (B34) and still counted as checked. The PR body itself says "only one
rule has a real check: the future-bar rule's strict-gate half", which concedes the point. The printed "19" goes
against the module docstring's "so neither number hides". Failure scenario: a later rule cites any test for one clause
and the gate reports it enforced, while the clause that matters is unguarded. Fix: count a rule that cites both a check
path and a B row as "partly checked", a third number, so the output reads e.g. 17 checked, 2 partly, 27 review.
Unverified. Arguably pre-existing, but this PR is the first to lean on it deliberately.

**S2. `CLAUDE.md::"Review finds; it doesn't design"` covers every review; the charter writes it only for designs.**
CLAUDE.md puts the rule under "Review before push", unqualified: proposed fixes are marked verified or unverified,
"a delta round reviews the diff", and so on. `docs/code_review.md` states it only under "## Design reviews" ("A
delta round on a design reviews the fold's diff"). "How a round runs", step 3 (what a finding is), doesn't ask for
verified or unverified marks on code-review findings. Failure scenario: a code-review reader briefed with the charter,
as the charter directs ("Each gets ... this charter"), never learns to mark fixes. The rule then holds only where the
author's brief adds it, as this brief did. Fix: add the verified/unverified clause to step 3 of "How a round runs",
or scope the CLAUDE.md rule to design reviews. Unverified.

### NIT

**N1. `docs/standards_backlog.md::B33`, "Rule it enforces"**: "Review finds; it doesn't design" lacks the section
prefix that B30, B31, B32 and B34 carry ("Testing: ...", "Review: ..."). It should read "Review: review finds; it
doesn't design".

**N2. Wording drifts between CLAUDE.md and the charter.** On stopping, CLAUDE.md says "the round stops" and
`code_review.md` says "the rounds stop". The charter's is the intended meaning (no more paper rounds).

**N3. `CLAUDE.md::"Known-broken behaviour"`**: "a gate whose module doesn't exist yet passes on the `ImportError`"
holds only for an import inside the test body. A module-level import fails collection whatever the marker says.
Saying "an import inside the test" would make the reason precise.

## Not findings (checked and fine)

- `raises=AssertionError` on the burnout gate fits the rule's "narrowest" (narrower than `Exception`). The commit
  message names its deletion proof. I did not rerun it.
- The B34 row's proposed check (read marker keywords from the AST) is sound in principle. Unverified.
- No `pytest.skip` or `mark.skip` in `tests/`. The only `skipif` is the Godot tier switch, which is allowed.
