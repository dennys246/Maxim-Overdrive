# Wire integrity delta review

Scope: `git diff bf2b638..e7ca4a1 -- . ':!docs/design/reviews/planning_v0_1/round1_*'`, read against `fold.md`'s claims. Read-only: nothing in the tree was edited, and `git status` is clean after every run.

## Status of round-1 findings

| Id | Status | Reason (read from the tree) |
|---|---|---|
| W1 | fixed | Brief 1a now greps `docs/design/reviews/records_layout/delta*.md` (the reviewers' reports), not `fold.md`. It accepts `C1, W1` rows and `**fixed**`. The regex has a new defect of its own: see WD1. |
| W2 | fixed | Order step 2 fixes the forms (`records_layout §10 Q1`–`Q5`, `records_layout added Q6`/`Q7`), and the exit test greps exactly those strings. |
| W3 | fixed | The awk check now fails when `setprofile` appears outside a superseded heading. I ran it on today's draft: it exits 1, at lines 87–88 under `### 3.3 The tripwire`. Four new names are required (OD-H6, OD-A20, `perceived-time port`, `machinery clock`), and today the draft has 0 hits for each. Two supersessions are still unchecked: see WD2. |
| W4 | fixed | The decorator-spelling grep is gone. `strict=True` and `raises=AssertionError` are counted separately, ids are matched as `$id([^0-9]|$)`, and the XFAIL count is 3. Residual false reds: see WD4. |
| W5 | open | The queued-run half is fixed: `gh run watch "$RUN" --exit-status` waits for the run. The stale-run half is not. `RUN` is the newest `workflow_dispatch` run on the branch, read after `sleep 10`, and nothing ties it to the dispatched commit. Failure scenario: on the second dispatch after a fold, the new run hasn't registered within 10 s, so the script watches the previous run on the pre-fold commit and passes or fails on the wrong code. Fix (flag verified to exist in gh 2.89.0; the fix itself not run): add `--commit "$(git rev-parse HEAD)"` to `gh run list`. `gh workflow run --help` also says it "returns the created workflow run URL if available". |
| W6 | fixed | O78 now reads "OD-I7's fix and OD-I5's (private) fix". The OD-I5 row reads "Fixed in v1.3.4 (its release notes, Security)". `gh release view v1.3.4 -R dennys246/Maxim`: its Security section lists "Cloud redaction renders private prompt sections by identity", which matches the row's "cloud redaction". Brief 2 part 2 closes both rows and lists OD-I5 among its files. |
| W7 | fixed | The briefs are committed at `docs/plans/next_steps/`. O79 part 4 makes each brief the one owner of its exit test, and the roadmap table holds only a link per step. `git grep` finds no remaining `_durable/next_steps` path except `README.md:4`'s history (see WD3). |
| W8 | fixed | Brief 4 now counts open PRs whose `headRefName != "phase1/records-build"` and requires 0. |
| W9 | fixed | The test now needs three `replay MATCHES the recorded end` lines (the string is verified at `spikes/slice/slice_server/metrics.py:244`) and a coverage line with two percentages. Residuals: see WD5. |
| W10 | fixed | Brief 2's red proof and exit test run with `GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1`. I ran it: 2 failed, 19 passed, both `AssertionError: assert 0 == 1`. `check_lock.SKIP_EVENTS = {"schedule", "workflow_dispatch"}` (`scripts/check_lock.py:28`), and `drift.yml` has both triggers. |
| W11 | deferred | No change: 12 roadmap cells still say "read 2026-11-24", and the rulings say 2026-11-23. Trigger: step 3, which rereads and restamps every Phase 3 row it touches, should use one date convention. |
| W12 | deferred | No change: the row-6 text still says "W-N1" without its report. Trigger: 6.1b removing the `actions.yaml` marker, which closes that clause. Until then the citation should name `torch_pilot/merge_wire.md`. |
| W13 | fixed | O79 now reads "This replaces the roadmap's old trigger, which had records-layout run as the only active session". The amended source now resolves. |
| W14 | fixed | A4's cut removed the OD-A12 row's "has existed since v1.3.3 (`memory_hub.py:1918`)" sentence. `fold.md` lists W14 as "recorded with no change", which understates the fold. |
| W15 | deferred | No change: the item is stated in both the plan and the roadmap. Trigger: step 5 closing the coverage item. Brief 5's file list excludes `docs/plans/foundations_plan.md`, so the plan's copy can only be reconciled by the next planning session (O79 part 5). That session is the effective trigger. |

## New findings

| Id | Severity | file::symbol | Finding and failure scenario |
|---|---|---|---|
| WD1 | SHOULD-FIX | `docs/plans/next_steps/1a_records_design.md::Exit test` (the `grep -qE "^\|[^|]*(^|[ ,*|])$id([ ,*]|\|).*\| *\**(fixed|deferred|rejected)"` loop) | The greedy `.*\|` lets the status word match the start of **any** later cell, not the status cell. I ran it on samples. `| A-B2 | open | fixed in part, the rest is not |` passes. `| C3 | open | | deferred |` passes. The fold's sample claim ("A-B2 (open) fails") holds only when the reason cell doesn't begin with a status word. A reason that starts "deferred by the author without a trigger" sits naturally beside `open`. Failure scenario: a reviewer marks a BLOCKER `open`, with a reason beginning "fixed in §4, but §9…", and the exit test reports the step done. That is the O25 overstatement W1 was about. Fix (verified on the same samples: A-B2 and C3 then fail, and A-B1, A-B3 `**deferred**`, C1/W1 `C1, W1` and W2 still pass): anchor to the second cell by replacing `.*\|` with `[^|]*\|`. Also: grep runs over every delta report, so one lens's `fixed` passes an id that the owning lens marks `open`. |
| WD2 | SHOULD-FIX | `docs/plans/next_steps/3_upstream_sync.md::Exit test` (the five-supersessions loop) | Supersession 3 (OD-A7's RNG after the 1.4.0 cut, not in #1305) has no check. The draft still places "Randomness and ids outside the fence" in A-pre (`world_clock_release_DRAFT.md:130`, `:183` "OD-A7: PR 7", `:197`). Today it has 0 hits for `1.4.0` and for `#1305`. `M72` is vacuous: the draft already has 4 hits. The checks for supersessions 1, 4 and 5 test that the names are present, not that the old text is gone: the host-calendar text at `:47–54`, `:112`, `:124`, `:129` can stay beside an added "machinery clock" sentence. Failure scenario: the session marks §3.3 superseded and adds one sentence that names OD-H6, OD-A20, the machinery clock and the perceived-time port. The test passes, and the D9 session still plans RNG into A-pre PR 7. Suggested fix (unverified): require `1.4.0` and `#1305` in the draft, and give the RNG rows the same superseded-heading awk check. |
| WD3 | SHOULD-FIX | `docs/design/reviews/planning_v0_1/fold.md::A11, W7` ("the `_durable` copies were deleted"), `README.md:4` | The round-1 revision of the five briefs was never committed. Its only copy (`.worktrees/_durable/next_steps_v0_1/`) is deleted: `ls .worktrees/_durable` shows no such directory. In this diff the briefs appear only as new files, so no delta reviewer can see which brief text the fold changed. The text that W1–W5 and W8–W9 quote (for example `grep -c 'xfail(strict=True, raises=AssertionError'`) now exists only inside the round-1 reports. `README.md:4` points readers at a directory that is gone. This is the memory rule "committed reviews cite `_durable` evidence, so grep before deleting", broken. Failure scenario: a later dispute over whether a fold changed a brief, or whether a round-1 finding quoted it fairly, can't be settled from the tree. Fix: restore the round-1 briefs if any copy survives and commit them under `reviews/planning_v0_1/`, or say in the README that the reviewed revision is lost. |
| WD4 | NIT | `docs/plans/next_steps/2_drift_and_lock.md::Exit test` (`grep -c 'strict=True' $G` `-eq 3`, likewise `raises=AssertionError`) | These are exact line counts. A correct module that shares one marker (`PENDING = pytest.mark.xfail(strict=True, raises=AssertionError)` applied with `reason=` per test), or whose docstring mentions `strict=True`, fails. The XFAIL count is the real check. Trigger: step 2's first exit-test run. |
| WD5 | NIT | `docs/plans/next_steps/5_slice_week4.md::Exit test` | One log's report pasted three times passes, because the count doesn't check for distinct logs. On a sample I verified that `grep -oE '^[^ ]+: replay MATCHES the recorded end' | sort -u | wc -l` rejects it. The coverage check is line-based, so a correct note that wraps the two figures across a line (this repo wraps at 120) fails. It also passes "Coverage … not yet measured; fail_under stays at 100% and the slice adds 0%" (sample run). Trigger: step 5's verdict note. |
| WD6 | NIT | `docs/plans/next_steps/4_records_build.md::Exit test` (`records.py index && git diff --exit-code || …`); `1a_records_design.md::Exit test` (`git grep`) | `git diff --exit-code` doesn't see untracked files, so a newly generated index that was never committed passes as current. A failing `records.py index` is reported as "a generated index was stale". In 1a, `git grep` reads only tracked files, so it misses the new `decisions/records_layout.md` until it is added. That fails safe, but shows up as a false red before the commit. Trigger: the first exit-test run of each step. |

## References checked that hold

- **O78–O80** are each defined once in `decisions/boundaries.md`. The foundations key row now lists O80, and `check_plan`'s key table accepts it. `lint_standards` (which runs `lint_ids`) passes.
- **O80's claim** matches the charter: `docs/code_review.md:24` says "NITs are the author's call".
- **The RL prefix:** `lint_ids._ID_CELL` (`^((?:[A-Z]+\d*-)?[A-Z]+)(\d+)…`) accepts `RL1` as a record id. No `RL` row exists in any decision log. `check_plan.ID_SOURCES` doesn't read `decisions/records_layout.md`, as A2's fold says.
- **Reserved ids:** the newest backlog row is B48, so B49–B55 are free. The newest lesson is 40, so lesson numbers 41–43 are free. The briefs write them as "lesson number N", which `_CITE` doesn't match.
- **The brief paths:** all five files exist at `docs/plans/next_steps/`. Their shared-rules sections are byte-identical (same md5), and each brief is under 2,500 words (1,146–1,589).
- **The other fold claims hold in the tree:** A4's cut rows, B48's new trigger, lesson 40's mode sentence, and the roadmap's status lead and rows 5a and 6.

## Counts

0 BLOCKER, 3 SHOULD-FIX (WD1–WD3), 3 NIT (WD4–WD6). Round-1 statuses: 10 fixed (W1–W4, W6–W10, W13, W14), 1 open (W5), 3 deferred (W11, W12, W15). Under the stop rule, no BLOCKER goes to the owner. WD1–WD3 and the open W5 are SHOULD-FIXes; the stop rule allows no further round, so the owner decides how they are folded.

## What I ran

- `git diff --stat` and `--word-diff` of the scoped range, plus the full text of the five briefs, `fold.md` and `README.md`.
- Brief 3's word checks and awk on `world_clock_release_DRAFT.md`, as of `e7ca4a1`: OD-H6, OD-A20, `perceived-time port`, `machinery clock` 0 hits each; M72 4; `#1305` 0; `1.4.0` 0. The awk exits 1 at lines 87–88.
- Brief 1a's regex and a column-anchored variant, on sample delta reports under `mktemp -d`.
- Brief 5's greps and a distinct-log variant, on sample notes under `mktemp -d`.
- `GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1 .venv/bin/pytest -q -p no:cacheprovider tests/test_check_lock.py`: 2 failed (`assert 0 == 1`), 19 passed.
- `scripts/check_plan.py` (PASS) and `scripts/lint_standards.py` (exit 0).
- Reads with `gh`: `gh release view v1.3.4 -R dennys246/Maxim`, `gh run list --help`, `gh workflow run --help` (gh 2.89.0).
- `git ls-tree` and `git show` of `phase1/records-layout`'s review directory, to see how its ids are written; only the three round-1 reports exist there, and no `delta*` file yet.
- Greps over `scripts/check_lock.py`, `drift.yml`, `scripts/lint_ids.py`, `scripts/check_plan.py`, `spikes/slice/slice_server/metrics.py`, `docs/code_review.md`, `docs/standards_backlog.md` and the lessons headings.

No workflow was dispatched, and nothing was fetched.
