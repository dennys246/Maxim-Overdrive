# Review: phase1/home-paths (09e3449 on 53cd42c), lenses Executor and Trust boundary

Read-only. Probes ran on a `git archive` copy of 09e3449 under `<scratchpad>/review_home/copy` (its own git repo),
with the worktree's venv. The probe samples use the name `<name>`. The owner's username is written `<name>` here.

## What I checked and what held

- **The deletion proofs are real.** I reran four of the five on the scratch copy, and each turned red as the commit
  message says:
  - unwiring `check_paths` from `lint_standards.main` turns `test_main_refuses_a_home_directory_in_an_untracked_file` red;
  - dropping `-Users-|-home-` from `HOME` turns `[-Users-]`, `[-home-]` and `test_a_session_scratchpad_path_is_refused` red;
  - echoing `line` in the finding turns `test_a_finding_names_the_line_but_never_the_name` red, and also the
    lint_standards test, whose message assertion it breaks;
  - treating every account as public turns 10 tests red, including all six spellings.
  The baseline is 182 passed for `tests/test_lint_paths.py` plus `tests/test_lint_standards.py`.
- **The scrub changes only what it says.** The word diff over `docs/design/reviews/` removes 21 `<scratchpad>…/scratchpad/…`
  paths and one bare `<name>`, and nothing else.
- **No echo of the name in output.** A finding carries `rel:line` and fixed text. The parametrize ids are the roots
  only, and the samples are `<name>`.
- **The tree is clean of the home basename.** `git grep -a -i` over every tracked file at 09e3449, binaries included,
  finds nothing, and neither do the branch's commit messages. The decompressed `.gz` fixtures and the strings in the
  six PNGs hold no home path.
- **Other personal details:**
  - hostnames: no `*.ts.net`, `.local` or `.lan`, and not the mini's hostname;
  - private IPv4 (10/8, 172.16/12, 192.168/16, 100.64/10): none, apart from a CIDR range named in prose;
  - emails: only `numpy-discussion@python.org` and `t@example.invalid`;
  - `claude-501` appears once, at `tests/test_lint_paths.py:31`, as the default macOS uid inside a sample. It names
    nobody.
- **The owner's real name, the GitHub handle and `RMDig LLC` appear** in `ASSETS_LICENSE.md`, `pyproject.toml`,
  `README.md` and the roadmap. They are public on purpose, so I don't count them as findings.

## Findings

### F1 BLOCKER: `docs/design/reviews/ci_cost/round1_trust.md` line 42 holds an account name the scrub missed

**Where.** `docs/design/reviews/ci_cost/round1_trust.md` (line 42: "If that account is `` `<short-name>` ``, every
job can reach…").

**What it is.** `<short-name>` is the login of the owner's Mac mini. The session memory records it as the mini's SSH
user, and the hostname beside it as private.

**Why it blocks.** The branch adds the CLAUDE.md rule "No file holds … a username". B44 says the only name outside a
path was the `ls -l` owner column in this same file. So the tree handed over breaks the rule the branch adds, and the
backlog row understates what was found. The check can't see it, and that is B44's documented limit.

**How bad.** Low on its own. It is a prefix of the public GitHub handle and the local part of the commit-author email.
But with any leak of the mini's hostname it is half of an SSH target.

**Failure scenario.** The owner reads B44, believes the bare-name hunt is complete, and the account name stays public
on `main`.

**Fix (unverified).** Make it `<owner>` as on line 121, and correct B44's sentence.

### F2 SHOULD-FIX: `scripts/lint_paths.py::HOME` misses the escaped and lowercase spellings of a home

**Probed with `check_paths`, all return `[]`:**

| Input | What it is |
|---|---|
| `"C:\\Users\\<name>\\x"` | the Python repr or JSON spelling, exactly what a pasted pytest or traceback line shows |
| `C:\users\<name>\x` | Windows lowercase, common in tool output |
| `/users/<name>/x` | macOS paths are case-insensitive, so this resolves to the same home |
| `/USERS/<name>` | uppercase |
| `file:%2FUsers%2F<name>` | URL-encoded |

**What it does catch.** `C:/Users/<name>`, `file:///Users/<name>` and `/mnt/c/Users/<name>`, through the `/Users/`
substring.

**Failure scenario.** A review record quotes a Windows contributor's pytest failure (`'C:\\Users\\<name>\\repo\\…'`),
and the gate passes it into a public tree.

**Why it matters.** The module docstring promises "every spelling", and CLAUDE.md says "in any spelling". The tests
cover only the six literal roots.

**Fix (unverified).** Match the roots case-insensitively and accept `\\+`, with a parametrized case for each.

### F3 SHOULD-FIX: `scripts/lint_paths.py::check_paths` and `scripts/lint_repo.py::tracked_text_files` skip three places a name can hide

Probed on the scratch copy with `tracked_text_files` and then `check_paths`, which returned `[]` for all three:

1. **Path names.** A directory named `docs/-Users-<name>-Repo/` with clean content passes. Only file contents are
   scanned, never `rel`.
   - Failure scenario: a session copies a scratchpad folder into the tree, named in the very form this branch exists
     to catch.
   - Note: once the path is scanned, a finding that prints `rel` would echo the name, so the finding needs a redacted
     path.
2. **Non-ASCII file names.** `docs/café.md` holding `/Users/<name>/y` is silently dropped.
   - Cause: `git ls-files` quotes non-ASCII paths under the default `core.quotepath`, so `p.is_file()` is false and
     the file is skipped without a word.
   - Scope: this hole affects every standards check, not only this one.
3. **Non-UTF-8 text.** A UTF-16 log holding the same line is skipped as "binary" (`except UnicodeDecodeError:
   continue`).
   - Failure scenario: a Windows tool log in UTF-16 is committed as evidence.
   - The comment "binary file: no markers to find" was true for markers, but not for this check.
   - Today only the 6 `.png` and 4 `.gz` files are skipped, and I found them clean.

**Fix (unverified).** Scan `rel` too. Read the listing with `-z`. Make an undecodable file a finding, or an explicit
allowlist by extension, rather than a silent skip.

### F4 SHOULD-FIX: the history claim is honest but incomplete

**Where it is stated.** "git history keeps them; the owner decides any rewrite" appears in the commit message and in
B44. It does not appear in the CLAUDE.md rule, which is the right split.

**What it leaves out:**

- **A rewrite can't fully clean GitHub.** From GitHub's "Removing sensitive data from a repository" docs (recalled,
  not verified here), rewriting `main` does not remove the commits from the `refs/pull/<n>/head` refs of merged PRs.
  This repo merged PRs whose commits hold the paths, #48 among them, and those refs are read-only to the owner.
  Forks and cached views keep them too, and purging them needs GitHub Support. As worded, "the owner decides any
  rewrite" reads as though a rewrite would finish the job.
- **Commit messages, PR titles and PR bodies are public too,** and nothing covers them. The check reads only the
  working tree, and B44 doesn't name them. I found none holding `<name>` on `main` or on this branch, so this is a
  gap in scope, not a live leak.

**Failure scenario.** The owner rewrites `main`, believes the paths are gone, and they stay reachable through
`refs/pull/*` URLs.

**Fix (unverified).** One sentence in B44 naming PR refs, forks and caches, and commit and PR text.

### F5 NIT: `scripts/lint_paths.py::PUBLIC_ACCOUNTS` lets a name through when it starts with a public one

`/Users/runner-<name>/x` and `-Users-Shared-<name>-` pass, because `name` stops at `-`, so they compare as `runner`
and `Shared`. `/Users//<name>/x` also passes, because the regex wants a name character straight after the slash.

**Failure scenario.** A username like `runner-<x>`. It is unlikely, but the test
`test_a_public_account_beside_a_private_one_is_still_a_finding` suggests the author meant to close the
public-account loophole.

### F6 NIT: `scripts/lint_paths.py::HOME` refuses ordinary prose and URLs, with no way to keep them

Each of these is flagged with the message "a path under someone's home directory":

- `https://example.com/home/index.html`
- `GET /home/<route>`
- `Power-Users-guide`
- `multi-home-setup`

The tree has none today, since the whole-repo test passes. The first doc that cites a `/home/` URL fails the gate, and
the author's only remedy is to reword it.

This is the safe direction. I record it so the next person doesn't "fix" it by narrowing the dash forms, which would
reopen the hole this branch exists to close.

### F7 NIT: `docs/standards_backlog.md` B44 gives the wrong count

B44 says the scrub missed the dash-encoded paths in "17 review files". The commit message says 16 records, and the
diff agrees: 16 files carry the 21 paths, and the 17th, `ci_cost/round1_trust.md`, carried only the `ls -l` owner.
Two records disagree on the number.

## Questions answered

- **Can each test fail?** Yes, all of them; see the proofs above.
  - `test_the_repository_holds_no_home_directory` goes red under the empty public-account set (the `/Users/runner`
    mentions in the tree) and would go red on any planted path.
  - `test_placeholders_elisions_and_public_accounts_pass` goes red under the empty set, as the commit message says.
- **Does any output echo the name?** No: not the findings, the test ids or the samples. F3's fix (scanning `rel`)
  needs care so that it doesn't start to.
- **Personal details left in the tree:** F1 only.
