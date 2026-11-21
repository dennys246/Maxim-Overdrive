# PR 24 delta round: Wire integrity

Reviewer: Wire integrity lens. Tree: `.worktrees/standards-bars-2` at af6f255 (= PR #24 head, pushed), read only.
Diff: `origin/main...af6f255` (32e1ce8, af6f255). Note: `origin/main` has moved to 755f5a2 (#22, #23 merged); the
branch still merges cleanly (`git merge-tree`), and #23 brings `docs/plans/long_term_features.md` to main.

## Status of the earlier findings (PR #21 Wire report)

| Finding | Status | From the tree |
|---|---|---|
| B1 dangling `long_term_features.md` citation | **fixed** | Parenthetical removed from "A design document holds the contract" |
| B2 7debd5c had no PR or branch | **fixed** | Recommitted as 32e1ce8 on `phase1/standards-bars-2`, PR #24 open, head af6f255. The gate's PASS line for af6f255 is claimed in the body; I did not rerun the gate |
| S1 lint counts partly checked rules as checked | **open (deferral incomplete)** | Recorded as B35 with a reason, but "Lands with" is `open`: no trigger. O25 requires a reason *and* a trigger for `deferred`. Name one (e.g. "the next branch that touches `scripts/lint_guards.py`, or before Phase 1 exit") and it becomes deferred |
| S2 verified/unverified only in design reviews | **fixed** | `code_review.md` step 3 now asks it of every reader; CLAUDE.md agrees |
| N1 B33 lacks section prefix | **fixed** | "Review: review finds; it doesn't design" |
| N2 "round stops" vs "rounds stop" | **fixed** | Both say "the rounds stop" |
| N3 ImportError reason imprecise | **fixed** | Reason now "any exception counts ... (a missing module, a renamed function)" |

## New findings

### BLOCKER

**D-B1. `tests/test_act_validation.py::_burn_every_turn` and `::_block_strike` break the precondition clause this PR
adds to `CLAUDE.md::"Known-broken behaviour gets a strict red gate"`.** The rule now says "a precondition the gate
needs raises something other than its `raises=` type". The fold fixed only the burnout gate. Two of the other three
strict gates reach their bar through helpers whose precondition is a bare `assert ...success`, i.e. an
`AssertionError`, which is exactly their `raises=` type:
- `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn` calls `_burn_every_turn`, which
  asserts `execute("ignite", {...LIMITS.max_power_w, LIMITS.min_radius_m}).success`.
- `test_a_strike_breaches_a_thin_wall_the_same_at_every_rig` calls `_block_strike`, which asserts `res.success`.

Failure scenario: a later change to `data/world/actions.yaml` or the applier makes the ignite or the 1.5x-threshold
strike refused. The helper raises `AssertionError`, the strict gate reports xfailed, and stays green without ever
reaching its bar: the very hole 32e1ce8's message says `raises=` closes. 32e1ce8 also says "three already passed
raises=AssertionError" as though they complied; under the rule as af6f255 words it, two do not. (The hollow-wall gate
is fine: a refused ignite skips the assert and XPASSes, which strict turns red.) Severity: the PR adds a standing
rule and ships the tree breaking it, with no backlog row or marker. Fix: give both helpers the burnout gate's
`RuntimeError` precondition (the non-gate callers of `_block_strike` would then fail with `RuntimeError`, which is
fine), with the same deletion proof; or narrow the rule's wording to what B34 can check and record the precondition
clause as review-held. Unverified.

### SHOULD-FIX

**D-S1. `docs/standards_backlog.md::B31` no longer matches the rule it holds.** The fold rewrote the future-bar rule:
the gate's reason names "the Phase 3 item (and its issue once filed)", and the evidence is "a separate, passing test
that what our membrane hands Maxim ... carries the stimulus, and a note that Maxim is driven as its brief says". B31
still reads "Every strict red gate whose reason names an **upstream issue** has a Phase 3 row ... with that issue",
and "the row cites the **world-side test** that passes". Failure scenario: someone builds B31's lint as written; it
keys on issue numbers, so a gate naming only a Phase 3 item (the rule's allowed form before an issue is filed) is
never matched, and it accepts a world-side-field test, which the PR body says explicitly "isn't enough". Fix: reword
B31 to "names a Phase 3 item", "cites the passing membrane test (bridge output, on its clock) and the driven-as-briefed
note". Unverified (text only).

### NIT

**D-N1. B35 is cited by no rule.** Every other new row (B30–B34) is a rule's `Guard:`. B35 holds the preamble
paragraph ("prints how many rules a check enforces and how many only review holds"), which has no `Guard:` line, so the
lint can't see that B35 belongs to anything. Harmless today (the lint doesn't require rows to be cited), but the row
can be closed without anything noticing. Add "Guard: `scripts/lint_guards.py::check_guards`, B35" to that paragraph,
if the lint's bullet parser tolerates it (unverified).

**D-N2. B35's "Rule it enforces" column** reads "Every rule names its guard (the counts don't hide)", which matches
the backlog header's own sentence, not a CLAUDE.md bullet. Acceptable, but "Engineering standards preamble: the counts
don't hide" would point a reader at the right paragraph.

**D-N3. PR body, "Review"**: "No delta round has run on the fold" is now stale; this round is running. Update after
it folds, with the delta counts.

**D-N4. The stop rule is split.** CLAUDE.md says "The charter holds the procedure", but the trigger (a second paper
round finding new blockers in fold text) lives only in CLAUDE.md; the charter's "When the rounds stop" points back to
CLAUDE.md for it. Readable, but the charter alone (which is what readers are handed) doesn't say when the rounds stop.

## What I checked

| Contract | How | Result |
|---|---|---|
| Lint parses revised rules | `scripts/lint_standards.py` at af6f255 | PASS, 0 findings, 19 checked / 27 review (matches commit message). Red-gate rule and future-bar rule still count as checked via the tooling test; "Review finds" rule now cites only B33 (path moved into body text), still review |
| `Guard:` placement | read `GUARD`, `PATH_REF`, `BACKLOG_REF` in `scripts/lint_guards.py`; each changed bullet | One `Guard:` per bullet; mid-line "Guard: B30, B10" parses; B31, B34 resolve |
| B30–B35 format | against header and B1–B29 | Four columns, unique ids, section prefixes present (B35 see D-N2); B30's cited symbols exist (`WOOD_FLAME_C` at two asserts, `<= 0.1` in `test_act_validation.py`) |
| CLAUDE.md vs charter vs backlog | read all three | Charter step 3, "Design reviews" bullets and CLAUDE.md agree on verified/unverified, owner acceptance, contract blockers. B31 disagrees (D-S1) |
| Every strict gate vs the new precondition clause | read all four `xfail` sites and their helpers | Burnout and hollow-wall comply; fiercest-fire and thin-wall do not (D-B1) |
| Body claim "422,126 °C against 2,000" | `pytest --runxfail -k burned` with `PYTHONPATH=src`, no cache | **Verified**: `AssertionError: (0.2, 422126.08)` |
| Body vs commits | `gh pr view 24` against both messages | Consistent: every listed change is in the diff; counts 2/2/3 match my earlier report; "folded except S1" holds apart from D-S1 and D-B1, which are new |
| Merge with moved main | `git merge-tree origin/main af6f255` | Clean |
| Tree left unchanged | `git status --short` | Clean |
