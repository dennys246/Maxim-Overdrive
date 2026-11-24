# Review: phase1/home-paths, delta round 3 (Executor, Trust boundary, Architecture, Wire integrity)

Tree: `git diff bb4c075 947d90e` (without `delta2.md`), `fold.md` ("Delta round 2 folds") and 947d90e's commit
message. Read-only: nothing in the worktree was edited, committed or stashed, and the gate was not run.

What I ran:

- `git archive 947d90e` into `<scratchpad>/review_home/copy3` (its own git repo), with the worktree's venv.
  `tests/test_lint_paths.py` there: 59 passed. Four deletion proofs (table below), each run with
  `tests/test_lint_paths.py tests/test_lint_standards.py` and restored with `git checkout` before the next.
- About 45 probe strings through `check_paths`, `_private` and `masked` at 947d90e, and some through bb4c075's
  `lint_paths.py` too.
- `scripts/lint_standards.py` in the worktree at 947d90e: PASS, 0 findings (22 rules held by a check, 28 by review).
- `origin/main` has moved to 7e85d84 (#52). `git merge-tree --write-tree 947d90e origin/main` is clean, and
  `check_paths` over the merged tree's 1,297 text files returns 0 findings.
- `gh pr diff` for the open PRs #49, #53 and #55, with both the new and the bb4c075 `_private` run over every added
  line and every file path. The one hit is #49's known `docs/design/reviews/sim_tick/round1_det_bio.md` (AW-S3).
  Both versions agree, so no PR line has a false positive or a new miss.
- Privacy: `git grep -a -i` at 947d90e for the local account name, `ts.net` and private IPv4 ranges. The same search
  ran over `git log -p origin/main..947d90e` and over the collected test ids. The tree and the ids are clean. The log
  has the account only on `-` lines, which are the scrub removing paths that `main` already carries.

## Deletion proofs re-run (on the copy)

| Mechanism deleted | Red | Matches the message |
|---|---|---|
| the cut: masking only the matched name, each name replaced by `<name>` | the file-path test, `ana-élise`, `Ana Maria`, the overlap test and the line-finding test | **in part**: the three combining-mark cases (`élodie`, `aña`, Devanagari) stay **green** (D3-N3) |
| `%` dropped from both name start sets | `%C3%A9lodie` | yes |
| `NOT_A_DISK` blanking removed | the `res://` pass case, `test_the_repository_holds_no_home_directory`, `test_the_repository_itself_passes` | yes |
| the `rstrip("-.")` in `_account` | the `runner-<name>` placeholder, the `/home/runner.` case and both whole-tree tests | yes |

## Status of delta-2 findings (read from the tree)

| Finding | Status | Basis |
|---|---|---|
| E1 SHOULD-FIX | **fixed** | `masked` prints only the text before the first private name's start, so no character of a found name reaches a finding: none of the eight tested names does, in either form. The percent-encoded name is found in both forms (proof 2). A name whose first character is outside `[\w%]` is still not found (D3-N2), but that is a different gap from E1's. |
| E2 NIT | **fixed** | `\/Users\/` and `%5CUsers%5C` are in `SPELLINGS` and are refused. |
| E3 NIT | **fixed in part** | The docstring now says that any directory spelled exactly `Users` or `home` is refused, and what to do. `res://` references pass. E3's own failure scenario still happens word for word, though. A tree directory `client/game/home/` is refused through its file path, as `client/game/home/<name>…`, and the printed `ADVICE` still says "write <home>, <scratchpad> or a path relative to the repository". `res://` doesn't help a directory that is in the tree. |
| E4 NIT | **fixed** | The module docstring cites B45. |
| AW-N5 | **fixed** for 06c2774 (4b09fbb) | `main` has since moved to 7e85d84 (#52). The merge is clean with 0 findings, but the branch must merge main again before hand-off. |

## New findings

### D3-S1 SHOULD-FIX: `scripts/lint_paths.py::NOT_A_DISK`: `\S*` exempts everything after a URL up to the next whitespace, and `http://` URLs do reach disks

`NOT_A_DISK` blanks the whole whitespace-delimited token from a `res://`, `user://`, `http://` or `https://` onward.
A token isn't a URL, though, and a web URL isn't always off-disk. Each case below is measured: refused at bb4c075 and
**passed** at 947d90e. This is a regression the fold introduced, and the check exists to protect privacy.

1. Minified JSON or JSONL, with a URL before a home in the same line:
   `{"url":"https://x.com/a","path":"/Users/<name>/x"}`. The spaced form of the same object is still refused.
2. A local file server or notebook URL, which carries a disk path: `http://localhost:8000/Users/<name>/x` and
   `http://127.0.0.1:8888/tree/Users/<name>`.
3. A disk path in a web URL's query, plain or URL-encoded: `https://x.com/?p=/Users/<name>/x`, and the same with
   `%2FUsers%2F`.
4. Markdown with no space after a link or a table cell: `[a](https://x.com)/Users/<name>` and
   `|https://x|/Users/<name>/x|`. The same applies to a `user://` in prose followed by `,/Users/<name>/x`.

Cases 1 and 2 are the realistic ones. A pasted tool log or a `.jsonl` excerpt is one token per record, and a dev
server or Jupyter link started from `/` names the account. The docstring's claim that web URLs are "paths on no one's
disk" is false for both. The `https` part of the exemption was added because of a hypothetical route
(`https://example.com/home/<page>`), and nothing in the tree or in any open PR's added lines needs it. With only `res` and
`user` exempt, the one whole-tree finding is the test module's own planted `https` sample (measured).

Failure scenario: a contributor commits a minified JSON log whose record holds a fetch URL and then a `cwd`. The gate
passes, and the account name is published.

Proposed fix (unverified): end the exempt span where a URL ends, at a quote, a backtick, `|`, `)`, `]` or `,`, and
drop `http(s)` from the exemption or keep it only for the path, not the query.

### D3-N1 NIT: `scripts/lint_paths.py::check_paths`: a line finding prints a file path that holds a home `_private` misses

A line finding prefixes `masked(rel)`, and that text is unmasked when the path's home is one of B45's blind spots.
Measured: a file at `docs/-Volumes-Data-Users-<name>-repo/r.md`, holding `/Volumes/Data/Users/<name>/repo`, gives one
finding, and that finding contains the real name. Without the line finding, nothing would print. A scratchpad copied
from a repository on an external volume is exactly this shape, since its files name their own full paths. The
detection gap is already deferred to B45, but this exposure, where the detection of a line pushes an undetected path
into the public log, isn't listed there.

Failure scenario: such a folder is committed, and CI prints the account once per offending line.

### D3-N2 NIT: `scripts/lint_paths.py::_NAME` and `DASH_HOME`: a name starting outside `[\w%]` is not found

`/Users/.x`, `/Users/-x`, `/Users/@x`, `/Users/+x`, `/Users/(x)`, `/Users/~x` and an emoji first character all pass.
macOS and Linux short names start with a letter, a digit or `_`, so the realistic exposure is Windows profile folders,
which allow most of these. This is low risk. The docstring doesn't say it, and B45 doesn't list it.

Failure scenario: a Windows profile named with a leading `.` or emoji passes.

### D3-N3 NIT: 947d90e's commit message: the deletion proof for the cut overstates what it reddens

The message says that masking only the matched name turns "the combining-mark, spaced and overlap cases" red.
Re-run on the copy, the three combining-mark cases stay green, because `_NAME`'s widened class now carries marks on
its own. The cut and the widened class each cover marks, so the cases hold only while both are present, and neither
one is proven alone. CLAUDE.md asks for the proof to be stated, and this one is stated wrongly. Record it in the fold
note, and either accept the redundancy or add a proof for the class (narrow `_NAME` back to `\w[\w.-]*` with the cut
kept, and the combining cases stay green, which is the expected result).

Failure scenario: a later refactor narrows `_NAME`, trusting that the combining-mark cases guard it. They still pass,
and the reader concludes the class is guarded.

### D3-N4 NIT: `tests/test_lint_paths.py::SPELLINGS`: `ssh://host/home/` appears twice

The second copy sits under the "Delta 2, E2" comment, but it is E3's `ssh://` case, which was already listed under
D1. pytest collects it twice, with ids ending `…/0]` and `…/1]`. The cost is a duplicate run and a misfiled
comment. The coverage E3 claims for `ssh://` is real either way.

### Checked and found sound

- **The cut.** `masked` takes the minimum name start over both forms. Overlaps, a dash form inside a path name, and a
  name followed by anything at all print nothing past that start. `shown != rel` is still equivalent to `_private(rel)`
  being non-empty, because the name start is `[\w%]`, so a literal `<name>…` can't already be in place.
- **Line findings** print only the masked path and the line number, never the line.
- **`_account`.** `runner.<x>`, `runner%20<x>`, `Shared-<x>` and a dash-form `runner.<x>` are private. `Shared/<x>`
  and `runner%2F<x>` are public, but those are subfolders of public homes. `runner` followed by a space, `<`, `[`, `"`,
  `,` or `|` reads as `runner`, which is only a gap for a Windows profile literally named "runner <x>", so it is
  negligible.
- **`NOT_A_DISK`'s `\b`** keeps `xuser://` and `myres://` from being exempt. `ssh://`, `file://`, `vscode://` and
  `ws://` homes are refused.
- This report passes `check_paths` (checked before hand-off).
