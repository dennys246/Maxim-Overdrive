# Home paths, delta round 4 (Executor, Trust boundary, Architecture, Wire integrity)

Scope: `git diff 947d90e eeb6ce8` (without `delta3.md`) and the merge resolution in 61a8a9b (`CLAUDE.md`,
`scripts/lint_standards.py`, `tests/test_lint_standards.py`, `scripts/lint_paths.py`).
No gate and no full suite.

What I ran in the worktree:
- `scripts/lint_standards.py`: PASS, 0 findings, 24 rules enforced by a check and 27 held only by review.
- `tests/test_lint_paths.py`, `tests/test_lint_ids.py` and `tests/test_lint_standards.py`: 279 passed.

## Statuses

| Finding | Status | Evidence from the tree |
|---|---|---|
| D3-S1 | **fixed** | Web URLs are no longer exempt. `NOT_A_DISK` is now limited to `res://`, `user://` and `client/` tokens, and a token ends at whitespace, a quote, a backtick, `,`, `;`, a bracket or `<>`. `SPELLINGS` holds the four D3-S1 shapes (a dev-server link, a query, a JSON line after a URL, and a JSON line after a `res://` string). All four are refused. Proof 1 (below) turns them red. A related hole in the new token is reported as D4-S1. |
| E3 (rest) | **fixed** | A file at `client/game/home/kitchen.tscn` passes, both as a file path and as text. A dash-encoded scratchpad under `client/` or `res://` is still refused. Proofs 2 and 3 turn this red. |
| D3-N1 | **deferred**: B45 now lists it ("a file path holding a home the check can't see is printed as it stands on its lines' findings"), and so does the docstring. Trigger: B45's own ("a leak found in review gets a pattern here if one can see it"). | `docs/standards_backlog.md` B45 |
| D3-N2 | **deferred**: B45 and the docstring list the names that start with `.`, `@`, `+` or an emoji. Same trigger as D3-N1. | B45, `lint_paths.py` docstring |
| D3-N3 | **fixed** | The fold table records the correction: the cut and `_NAME`'s Unicode class each hold the combining-mark cases, so neither is proven alone. This matches what delta 3 measured. |
| D3-N4 | **fixed** | `ssh://host/home/` now appears once in `SPELLINGS`. |
| (author) the `client/` flag in `masked` | **fixed** (the removal is correct) | `masked` has no flag. A `client/` file path goes through `_private` and is covered by the token. With the flag gone, the Godot test still passes. |
| AW-S2 | **fixed** | `lint_standards.py` lists `lint_ids` as 8 and `lint_paths` as 9, and `main` calls both `check_paths(files)` and `check_ids(files)`. `lint_paths.py`'s docstring says "Standards check 9". No "check 8" is left for the paths check outside the review files. `test_lint_standards.py` loads both siblings. `CLAUDE.md` carries #55's "A record id names one record" and this branch's "No personal details in the tree" once each, and both rules keep their guards. The lint run above passing shows that the guard citations resolve. |

## Deletion proofs re-run

On a copy (`git archive eeb6ce8`, then `git init`), I ran `tests/test_lint_paths.py` after each change, restoring the
file between runs:

1. Old exemption restored (`(?i)\b(?:res|user|https?)://\S*`): 6 failed. These were the 4 D3-S1 spellings, the Godot
   test and the whole-tree test. The whole-tree test fails because the test module's own `client/game/home` lines are
   no longer exempt.
2. `client/` taken out of `NOT_A_DISK`: 2 failed, the Godot test and the whole-tree test. This matches the commit
   message.
3. The exemption also applied to `DASH_HOME`: 1 failed, the Godot test (its `client/` and `res://` scratchpad
   cases). This matches.

All three proofs hold as the commit states them.

## New findings

### D4-S1 SHOULD-FIX: `scripts/lint_paths.py::NOT_A_DISK`: the token runs through `..`, `:`, `=`, `\`, `|`, `{`, `}` and `@`, so a disk home glued to a Godot token is skipped

`_private` drops every `PATH_HOME` match that starts inside a token. A token only ends at whitespace, a quote, a
backtick, `,`, `;`, `()`, `<>` or `[]`. I probed it with a fictional name (`_private` on each string):

- Not found: `client/../../Users/<name>/x`, `res://../Users/<name>/x`, `res://=/Users/<name>/repo/client` (a
  globalized-path listing), `user://=/Users/<name>/Library`, `res://x.gd:12:/Users/<name>/x`,
  `GODOT_PATH=client/bin:/Users/<name>/bin` (a colon path list), `client/x\Users\<name>\y`,
  `| res://x|/Users/<name>/x |`, `{res://x}/Users/<name>/x`, `res://x@/Users/<name>`.
- Found, correctly: the same homes after a space, an absolute `/Users/<name>/repo/client/x`, a Windows path with
  `\client/`, `file://` and `ssh://` homes, and any dash form.

The docstring says a `client/` or `res://` path is "on no one's disk". That is false once the token climbs out with
`..`, or once it is followed by a separator that isn't a path character (`:` in a path list or after a line number,
`=` in a `key=value` dump). The most plausible route is `client/../..` from a tool that prints paths relative to the
repository, or a `res://=<absolute>` mapping pasted while debugging Godot's path globalization. Same class
as D3-S1 (an exempt span wider than its path), narrower in reach.

Failure scenario: a review file quotes a Godot debug line that maps `res://` to the project's absolute path with no
space between them (`res://=/Users/<name>/...`). The gate passes, and the account is published.

Fix tried, marked verified: on the copy, the token's class took `:` `=` `\` `|` `{` `}` `@` as extra terminators, and
the token stopped before `..`:
`(?:(?!\.\.)[^\s"'`,;()<>\[\]:=\\|{}@])*`. With that change, `tests/test_lint_paths.py` gave 63 passed, and 9 of the
10 probes above were refused.

Four glued shapes still passed:
- `res://game/x.gd/Users/<name>/x`
- `--path=client/x/Users/<name>`
- `?f=client/Users/<name>`
- `USER://home/<name>`

Each of these reads the same as a game directory named `Users` or `home` under the project. That ambiguity is the one
the docstring already accepts. If the author keeps it, it belongs in B45 and the docstring as a blind spot. I did not
check whether the narrower token rejects any real Godot path in the tree. The whole-tree test passing on the copy is
the only evidence that it doesn't.

### D4-N1 NIT: `tests/test_lint_paths.py::test_placeholders_elisions_and_public_accounts_pass`: a test id that the check itself refuses

pytest escapes the elision `…` in this case's id as `…`. The id then reads as a home behind a backslash
separator, whose "account" is `u2026`. `check_paths` over `--collect-only` output gives one finding, and that finding
is this id. No real name is involved, and nothing scans test ids today. But a pasted `pytest -v` log in a review file
would be refused for a placeholder.

Failure scenario: a reviewer pastes a verbose test run into `docs/design/reviews/` and the gate goes red on a
false positive.

Fix (unverified): give the case an ASCII `id=`.

## Privacy

- `git log --format=%B origin/main..61a8a9b`, through `check_paths`: one line found, the commit text's
  fictional `runner-x` sample, which is intended. The local account name appears in no commit text.
- Test ids for `test_lint_paths.py`: no account name. The one finding is D4-N1.
- `git grep` for the local account name at 61a8a9b: no hit apart from the public GitHub handle.
- Exemptions that `NOT_A_DISK` actually grants in the tracked tree: 4 lines, all in `tests/test_lint_paths.py`'s
  `res://`, `user://` and `client/game/home` samples.

## Checked and found sound

- The anchor `(?<![\w./-])client/` rejects `myclient/`, `old-client/`, `.client/` and `<path>/client/`, so an
  absolute path's `client/` never opens a token. Where a home comes first, it starts before the token and is still
  found.
- Only `PATH_HOME` is filtered by span, and `DASH_HOME` is never filtered. `masked` uses the same `_private`, so a
  masked path and a finding agree.
- In the merge, `check_ids` runs unconditionally after `check_contracts`, and `check_paths` runs unconditionally
  after `check_inputs`. Neither one shadows the other.
