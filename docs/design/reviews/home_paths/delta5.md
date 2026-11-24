# Home paths, delta round 5 (Executor, Trust boundary, Architecture, Wire integrity)

Scope: `git diff 61a8a9b c30c726` (without `delta4.md`), and fold.md's "Delta round 4 folds". No gate and no full suite.

What I ran in the worktree:
- `scripts/lint_standards.py`: PASS, 0 findings, 24 rules enforced by a check and 27 held only by review.
- `tests/test_lint_paths.py` and `tests/test_isolation.py`: 141 passed. c30c726 fixes the port false positive.

## Statuses

| Finding | Status | Evidence from the tree |
|---|---|---|
| D4-S1 | **fixed**, for the shapes it named | `NOT_A_DISK` now ends at `:` `=` `|` `@` `\` `{` `}` and before `..`. All nine glued spellings are in `SPELLINGS` and are refused. 9 of delta 4's 10 probes are refused. The tenth, `{res://x}`, is refused too. B45 and the docstring record the four ambiguous shapes. The same class of hole is still open through other characters, reported as D5-S1. |
| D4-N1 | **fixed** | The case's id is `elisions`. `--collect-only` shows no `u2026` in any id. |

## Deletion proofs re-run

On a copy (`git archive c30c726`, then `git init`), with `tests/test_lint_paths.py` run after each change and the file
restored between runs:

- Old token restored: 9 failed, exactly the nine D4-S1 spellings. This matches the commit message.
- Lookahead removed: 2 failed (`client/../../Users/` and `res://../Users/`).
- Each terminator dropped alone: `:` gives 2 failed, and `=`, `|`, `@` and `\` give 1 each.
- `{` alone or `}` alone: 0 failed. Only dropping both turns `res://{x}/Users/` red. See D5-N1.

## Refusals of legitimate text

The narrowed token refuses nothing legitimate. I compared `_private` under the old and the new token on every line of
the tracked tree (which includes every `res://` line under `client/`), and on every added line of open PRs #53, #56 and
#57. #57's diff is too large for `gh pr diff`, so I diffed its head commit against the merge base instead.
- The token is shorter on 126 lines: `client/x.gd::symbol` references, `res://{rel}` f-strings, `client/addons/.../{a,b}`
  brace lists and the new samples.
- 0 lines are newly refused. None of these lines has a home after the point where the token now ends.

## B45 and docstring accuracy

B45 is accurate. Delta 4 named four ambiguous shapes. B45 gives two of them as examples of a class ("no separator the
check can tell from the project's own"), and the class covers the other two (`?f=client/Users/<name>` and
`USER://home/<name>`). All four still pass, as B45 says.

## New findings

### D5-S1 SHOULD-FIX: `scripts/lint_paths.py::NOT_A_DISK`: the terminators are a denylist, so other glue characters still hide a home

This is the third round in which this token's span has been too wide (D3-S1, D4-S1). With a fictional name, `_private`
at c30c726 finds nothing in:
- `res://x#/Users/<name>`, `res://x?/Users/<name>`, `res://x&/Users/<name>`
- `res://x+…`, `res://x!…`, `res://x*…`, `res://x$…`, `res://x~…`, each followed by `/Users/<name>`
- `res://x%3A/Users/<name>` (an encoded `:`)
- `res://x/.%2E/Users/<name>` (an encoded `..`)
- `res://x…/Users/<name>`

The comment says the token ends at "anything that glues another path on". That is false for these.

Failure scenario: a review file quotes a dev-server URL whose query joins a project path and an absolute one, such as
`?root=client/game&src=/Users/<name>/repo`. The token runs through the `&`, the gate passes, and the account is
published.

Fix, marked verified: replace the denylist with an allowlist of the characters a Godot path in this project uses,
`(?:(?!\.\.)[\w./-])*`. I applied it on the copy:
- `tests/test_lint_paths.py`: 72 passed.
- Every probe above is refused, plus the nine D4-S1 spellings.
- The four documented ambiguous shapes still pass, as B45 states.
- Compared with c30c726, the allowlist changes the refusals on 0 lines of the tree or of the three PRs' added lines.

Add some of these probes to `SPELLINGS` and fix the comment.

### D5-N1 NIT: `tests/test_lint_paths.py::SPELLINGS`: `{` and `}` are proven only as a pair

`res://{x}/Users/` stays refused when either brace alone is dropped from the class. So neither terminator has its own
proof, and either one could be deleted with the suite staying green. With the allowlist from D5-S1, this finding goes
away. Otherwise, add `res://x}/Users/` and `res://x{/Users/`. Unverified.

### D5-N2 NIT: `scripts/lint_paths.py` module docstring: the blind spot is attached to the wrong form

The docstring reads "a dash-encoded home after an encoded prefix (...) or glued onto a Godot path
(`res://game/x.gd/Users/<name>`...)". Grammatically, "glued onto a Godot path" attaches to "a dash-encoded home". But
`DASH_HOME` is never filtered by the token, and the example is the exact `/Users/` spelling. B45's wording is right.

Failure scenario: a maintainer reads the docstring and concludes that dash-encoded scratchpads under `res://` are
skipped.

Fix (unverified): make it its own list item, "an exact-spelling home glued onto a Godot path (...)".
