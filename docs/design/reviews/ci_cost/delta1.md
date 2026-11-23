# Delta 1, Executor and Wire integrity: phase1/ci-cost (f5e9619..5e21bb8)

Reviewer: independent, read-only. Diff read: `git diff f5e9619..5e21bb8`. Worktree HEAD 5e21bb8, clean apart from the
untracked round-1 reports. `tests/test_check_lock.py`: 21 passed at HEAD.

**Counts: 0 BLOCKER, 2 SHOULD-FIX, 4 NIT.**

## 1. Round-1 fold status (reviewer-set)

| Finding | Status | Reason, read from the tree |
|---|---|---|
| Executor B1 (setup-python on a self-hosted Mac) | rejected: moot under B | No job names a self-hosted label. macOS is `macos-latest`. |
| Executor S1 (`gh` on the mini), S2 (blast radius) | rejected: moot under B | Same reason. |
| Executor N1 (trigger test names two files) | **open** | Unchanged. The new loop also lists three named files, so a fourth workflow escapes both tests. |
| Executor N2 (24 h queue) | rejected: moot | There is no self-hosted job left to queue. |
| Executor N3 (stale comments) | rejected: moot | `install_godot.sh`'s "macos-latest" and prepush's "fresh clone" are true again. |
| Executor N4 (job names) | fixed | Matrix values are the runner labels again, as on origin/main. |
| Trust B1 (unpinned drift on the mini) | fixed | `git diff origin/main -- .github/workflows/drift.yml` is empty. |
| Trust B2 (removal rule is only a comment) | fixed | Owned by the roadmap section "Before the repository goes public", cited by B37. The test's guard is weaker than it reads (D1). |
| Trust SF1–SF4, N1, N3 | rejected: moot under B | Each is about a self-hosted runner, and none is configured. |
| Trust N2 (invert the test) | fixed, with D1 | The test now asserts no self-hosted runner, but it misses a lone custom label. |
| Wire S1 (no runner registered) | rejected: moot | |
| Wire S2 (B11 says "every push") | fixed | B11 is rewritten. Leftovers are in D5. |
| Wire S3 (exemption's "fresh clone") | rejected: moot | GitHub-hosted clones are fresh again. |
| Wire S4 (removal obligation has no owner) | fixed | The roadmap section owns it and B37 cites it. |
| Wire N1, N2, N5 | rejected: moot under B | |
| Wire N3 (workflow tests scattered) | **open** | Unchanged. |
| Wire N4 (CI PASS names only a merge sha; golden only on PRs) | half fixed | Pushes to main run test.yml again, so CI now prints a PASS for a real main commit. Golden still runs on a branch only once a PR exists, and nothing says so: open. |

## 2. The matrix expression

`os: ${{ fromJSON(github.event_name == 'push' && '["ubuntu-latest", "macos-latest"]' || '["ubuntu-latest"]') }}`

I read these in GitHub's docs source (`github/docs`) during this session:
- **Verified:** the `github` context is available in `jobs.<job_id>.strategy`. The contexts page's availability
  table lists "github, needs, vars, inputs".
- **Verified:** a single matrix key may be set from an expression. See "Using contexts to create matrices" in
  run-job-variations, where `version` comes from `github.event.client_payload.versions`.
- **Verified:** `fromJSON` returns arrays as well as objects.
- **Verified:** string literals inside `${{ }}` take single quotes. Double quotes inside them are just JSON
  characters, so the quoting is valid.
- **Unverified:** that `a && b || c` returns the value of an operand rather than a boolean. The current expressions
  page lists `&&` and `||` only as "And" and "Or" and documents no value semantics. Many workflows rely on this
  idiom, but I could not find it in the docs. If it held booleans, `fromJSON(true)` would not be a sequence, and the
  workflow would fail at evaluation on every event. The documented alternative is
  `fromJSON(case(github.event_name == 'push', '[...]', '[...]'))`. `case()` is on the same page.
- Not run on GitHub.

Events, assuming the operand-value semantics:
- `push`: the trigger is restricted to `main`, so this gives 4 jobs (2 OS × 2 Python).
- `pull_request`: 2 jobs, Linux only.
- `workflow_dispatch`: test.yml has no such trigger, and
  `test_ci_runs_on_pull_requests_and_pushes_to_main_only` pins the triggers to exactly those two, so it can't
  happen. If it were added later, it would get Linux only.
- The middle operand is a non-empty string, so it is truthy. The `||` branch is taken only for non-push events, so
  the classic `&&/||` pitfall doesn't apply here.

## 3. Proof by deletion

I planted each change in a `git archive HEAD` copy under `_durable/ci_review/plant/` (now removed) and ran
`tests/test_check_lock.py`. For the self-hosted plants I also ran `test_client_project.py` and
`test_tooling_config.py`.

| Plant | Result |
|---|---|
| PRs get macOS (ternary removed) | red |
| Static `[ubuntu-latest, macos-latest]` matrix | red |
| drift.yml drops macOS | red |
| golden.yml `runs-on: [self-hosted, macOS]` | red |
| golden.yml `runs-on: overdrive-mini` | red, but only through `test_client_project.py` (golden pinned to ubuntu-latest) |
| **drift.yml `runs-on: overdrive-mini`** | **green** |
| **test.yml: a new job with `runs-on: overdrive-mini`** | **green** |

In the copy, the three-file baseline had one failure. It was the same failure in every run and so unrelated: the
copy has no `.git`.

## 4. Going-public plan and B37

- Test name in step 2: it matches the test's name.
- "Seven files (three spike scripts and four documents)": verified. `git ls-files | xargs grep -l <home>`
  gives four documents and `spikes/physics/solid/{fds_driver.py,launch_fits.sh,launch_fits_rerun1.sh}`. Two more
  files hold elided `/Users/…` forms, which are not personal.
- "Runners lists none": round 1 measured `total_count: 0`. I did not re-measure.
- "202 commits": not reproduced (D3).
- B37 cites the roadmap section and doesn't restate the steps. One owner is kept, apart from D6.

## Findings

**D1 SHOULD-FIX `tests/test_check_lock.py::test_macos_runs_on_githubs_runners_only_for_pushes_to_main_and_the_weekly_drift`:
the "no self-hosted runner" loop cannot fail for a lone custom label, which is exactly round 1's form.**
`"self-hosted" not in str(job["runs-on"])` matches only the literal word. drift.yml's `runs-on` is not asserted at
all.

Failure scenario: someone sets drift.yml back to `runs-on: overdrive-mini`, the round-1 mapping, or adds a test.yml
job on that label. Every test stays green (planted, §3). Weekly unpinned releases, or PR code, then run on the
owner's machine, which is what option B and Trust B1 exist to prevent. The comment above the test claims a guarantee
that the test doesn't hold.

Fix (unverified): assert that every `runs-on` in every workflow is one of `{ubuntu-latest, macos-latest,
"${{ matrix.os }}"}`, and that every `matrix.os` value is one of the GitHub-hosted labels. Iterate over
`.github/workflows/*.yml` rather than three named files, which also closes Executor N1.

**D2 SHOULD-FIX `.github/workflows/test.yml::prepush` header comment and the test comment ("A PR's macOS check is the
prepush PASS from the owner's Mac mini that every hand-off carries"): this overstates what replaces the PR's macOS
jobs.**
- The hand-off gate runs one Python, whichever `.venv` or `PYTHON` it is given (`prepush.sh` line 43). CI's macOS
  legs ran both 3.12 and 3.14.
- Nothing in CLAUDE.md requires the hand-off PASS to come from the mini, or from a Mac at all.
- It runs on the branch head, not the PR's merge commit.

Failure scenario: a change breaks only macOS × 3.12, for example a py3.12 lock pin with no darwin-arm64 wheel, or
setup-python's 3.12.10 noted in round 1. It is handed over with a 3.14 PASS, merges green on Linux, and turns main red
on the push run. The comment says this was covered.

Fix (unverified): state the real coverage in one place (B11 is the natural owner): "PR macOS = the hand-off's one
Python. Other macOS Pythons are first seen on main." Or have the hand-off note name its Python and machine.

**D3 NIT `docs/roadmap.md`, "Before the repository goes public" step 1, "the mentions span 202 commits": I could not
reproduce the number, and the method is not stated.**
My counts:
- 15 commits on HEAD's history change an `OD-I5` line (`-G`).
- 158 commits on HEAD carry it in their tree.
- 169 on origin/main.
- 207 across all local refs.

Failure scenario: the owner weighs a history rewrite on a figure that matches none of these. Fix: name the measure,
or drop the number.

**D4 NIT Wire N4's golden half, still open:** `golden.yml` runs on a branch only once a PR exists, and nothing says
so (see §1).

**D5 NIT stale CI text:**
- `docs/plans/checklists.md:29` says CI's prepush "runs on every push". This has been stale since f5e9619, and round
  1's grep missed it. It holds for main, which is the case the sentence needs, but the wording is wrong.
- `docs/standards_backlog.md::B11` still says "It has not yet run on GitHub; the first push verifies it" next to its
  **done** status.
- B11's "all four jobs" now describes only main pushes.

Failure scenario: a reader expects CI on a pushed branch with no PR.

**D6 NIT, one owner (B36): the event → OS contract is stated four times.** The copies are in the test.yml comment,
the test comment, B11 and roadmap step 2. The roadmap step and B11 could cite test.yml rather than paraphrase it.
Failure scenario: going public flips test.yml and the test as step 2 says, and B11 keeps the old split.

## Wire contract row

| Contract | Producers | Consumers | Before → after |
|---|---|---|---|
| OS per CI event (test.yml) | `include` mapping linux→GitHub, macos→`overdrive-mini` → `fromJSON` ternary | the PR check list, hand-off practice, B11, checklists.md:29, roadmap go-public step 2 | PR: 4 jobs (2 queued forever) → 2 Linux; main push: 4 → 4 on GitHub. checklists.md wording is stale (D5). The PR's macOS coverage is overstated (D2). |
| drift runner | `overdrive-mini` → `macos-latest` (origin/main) | weekly drift issue step | restored; `gh` is present on hosted images |
