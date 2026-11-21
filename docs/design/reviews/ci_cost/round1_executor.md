# Executor review: phase1/ci-cost (f5e9619)

Diff read: `git diff origin/main...f5e9619` (test.yml, drift.yml, golden.yml, tests/test_check_lock.py).
Counts: 1 BLOCKER, 2 SHOULD-FIX, 4 NIT.

## What I verified

- `tests/test_check_lock.py`: 21 passed on the branch.
- Proof by deletion, planted in a `git archive` copy (since removed). Each plant fails exactly one new test, and
  restoring the files makes both pass again:
  - golden.yml with `branches: [main]` removed (every push): red.
  - test.yml with `pull_request:` removed: red.
  - drift.yml with `runner: macos-latest`: red. This plant is the one the commit message names.
  - test.yml with the include misspelt `os: macOS`, which would add an orphan combination with no runner: red.
  - test.yml with `runs-on: ${{ matrix.os }}`: red.
- Matrix shape: GitHub's "Running variations of jobs" page says an include entry is added to every original
  combination it can join without overwriting an original value. `{os: linux, runner: ubuntu-latest}` matches both
  linux combinations, the macos entry matches both macos combinations, and `runner` is a new key. Every one of the
  four jobs gets a runner. Verified against the docs; not run on GitHub.
- `runs-on:` with a single custom label sends the job to a self-hosted runner that carries that label. This is
  documented and I have not run it. The repo has no runners registered yet (`gh api .../actions/runners`:
  `total_count: 0`).
- Every use of `matrix.os`: before this branch the only one was `runs-on`. Now the only one is drift.yml's issue
  title, which reads "Dependency drift: the gate fails unpinned (macos, Python 3.14)". That still makes sense, and it
  reads better than "macos-latest", which is no longer true there. `matrix.python-version` is untouched.
- Commit message claims:
  - "each PR push ran it twice": true, because `push:` and `pull_request:` both fired for in-repo branches.
  - "half its matrix was macos-latest": true. Run 44960494531 has two macos-latest jobs out of four.
  - "the mini already runs the gate in about two minutes": consistent with the session's notes on the mini. I did
    not measure it.
  - "Proven by deletion": reproduced above.
  - "Until the runner is registered … the macOS jobs wait in the queue": incomplete. See B1 and N2.
- Branch protection and rulesets: the API returns 403 because the plan doesn't include them, so renamed matrix job
  names can't strand a required check.
- `prepush.sh::refuse_main_branch` keys its skip on `GITHUB_ACTIONS=true`. A self-hosted runner sets that too, so the
  exemption still applies. See N3 for the comment that justifies it.
- Python builds for darwin arm64 in actions/python-versions: 3.14.10 is available (arm64). The newest 3.12 with a
  darwin build is 3.12.10; 3.12.11 to 3.12.16 are source-only releases with no macOS binaries. "3.12" therefore
  resolves to 3.12.10 on the mini, as it did on macos-latest. That is not a regression.

## BLOCKER

**B1. test.yml::prepush / drift.yml::drift, step `actions/setup-python@v5`: it fails on a self-hosted macOS
runner unless the machine is prepared first, and neither the workflows nor the commit say so.**
The setup-python advanced-usage doc (self-hosted runners, macOS) says: "Due to the fixed shared library path, these
Python packages are non-relocatable and require to be installed only in `/Users/runner/hostedtoolcache`." It also
says to create that directory and give the runner user write access, with `sudo chown` if needed.

The mini's user is not `runner`; per the setup notes, its Pythons are Homebrew's in `/opt/homebrew/bin`.

Failure scenario: the owner registers the runner with the `overdrive-mini` label, as the commit message says is all
that remains. The first PR's two macOS jobs then fail at setup-python because they can't install into
`/Users/runner/hostedtoolcache`, so every PR carries two red macOS checks. The commit presents registration as the
only missing step, so the owner has nothing pointing at this cause.

Proposed fixes, all unverified because I did not touch the mini:
- (a) Run the runner as a dedicated macOS user named `runner`. That gives the path setup-python expects and also
  isolates PR code from the owner's home (S2).
- (b) Create `/Users/runner/hostedtoolcache` and make it writable by the runner user. Write the step into the
  workflow comment, and into a runbook if there is one.
- (c) On macOS, skip setup-python and build the venv from `python${{ matrix.python-version }}` on PATH, with a step
  that checks the version.

Whichever is chosen, the setup should be written down in the workflow header next to the "remove before public"
note.

## SHOULD-FIX

**S1. drift.yml::drift, step "Open an issue when the gate fails unpinned": it depends on `gh`, which GitHub-hosted
images ship and the mini may not have.**
Failure scenario: the macOS drift run goes red on Monday, the issue step fails with `gh: command not found`, and no
issue opens. The weekly drift signal (O32) is lost silently for macOS; only the run's red X is left, in a scheduled
workflow nobody watches.
- Unverified: I did not check whether `gh` is installed on the mini.
- Fix, unverified: confirm `gh` is on the runner service's PATH (a launchd service's PATH is minimal, so
  `/opt/homebrew/bin` may be missing even if `gh` is installed), or open the issue with `actions/github-script`,
  which needs no `gh`.

**S2. test.yml / drift.yml header comment: it names only the public-repo risk, not the local blast radius.**
A self-hosted runner runs as whichever user registered it. If that is the owner's account, every PR job can read the
owner's home: SSH keys, the `gh` token, `~/overdrive-gate`, and Tailscale access.

Failure scenario: a PR that a collaborator (or an agent) pushes runs a test that reads `~/.ssh` or `~/.config/gh` on
the mini. This is today's risk, not only after the repo goes public.

Fix, unverified: a dedicated, unprivileged runner user. It is the same step as B1(a).

## NIT

**N1. tests/test_check_lock.py::test_ci_runs_on_pull_requests_and_pushes_to_main_only: it names two files, so a new
workflow added with a bare `on: push` escapes it.**
Fix, unverified: assert over every `.github/workflows/*.yml` except a named allowlist (drift.yml).

**N2. Commit message, "wait in the queue": GitHub ends a self-hosted job that no runner picks up within 24 hours.**
Each PR therefore shows two pending macOS checks that later turn into failures. This is GitHub's documented
queue-time limit as I remember it; I did not re-read it. Harmless while there is no branch protection, but the
message overstates how benign the wait is.

**N3. Stale comments.**
- `ci/install_godot.sh` header, line 8: still says "macos-universal (macos-latest, either CPU)".
- `scripts/prepush.sh::refuse_main_branch`: says "GitHub Actions runs in a fresh clone". A self-hosted runner reuses
  its `_work` checkout. The exemption stays safe only if the runner's work directory is not inside a repository that
  sessions use (for example `~/overdrive-gate/repo`). Worth one line in the runner setup notes.

**N4. Default matrix job names change, probably to `prepush (linux, 3.12, ubuntu-latest)`.**
Unverified: GitHub's page doesn't document the naming of keys that include entries add. There is no required-check
impact (no branch protection), but run history no longer lines up by name. Optional:
`name: prepush (${{ matrix.os }}, ${{ matrix.python-version }})`.

## Not findings

golden.yml has no matrix and stays on ubuntu-latest. The `[True]` key in the new tests is PyYAML 1.1 parsing `on`
as a boolean; it matches the existing tests' convention.
