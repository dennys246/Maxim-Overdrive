# Architecture lens: `phase1/drift-and-lock`, `1ed9caa..38383fc`

**Summary.** 0 BLOCKER, 3 SHOULD-FIX, 3 NIT. The drift-job fix is a root fix, not a band-aid. The branch stays inside
the brief's file list. One roadmap statement is false against the tree (OD-I6, A1), and lesson 41 contradicts it. The
three red gates can silently disappear rather than flip if Maxim moves a module (A2). The lock move made one design
claim about Maxim's behaviour stale (A3). That claim sits outside this branch's scope, so it needs an open item, not an
edit.

## What I checked

- **The root fix.** `scripts/check_lock.py::main` now takes `env: Mapping[str, str]` as a required keyword-only
  parameter. Only `__main__` passes `os.environ`. I grepped `scripts/`, `tests/`, `.github/` and `prepush.sh` for
  every caller of `check_lock` and every reader of `MAXIM_OVERDRIVE_UNLOCKED`:
  - The only Python callers of `main` are in `tests/test_check_lock.py`, and every call passes `env`.
  - `prepush.sh` runs the script as a process, so it goes through `__main__` and is correct.
  - `prepush.sh:70` reads the variable only for the PASS line's note.
  - `tests/test_prepush.py::_gate` builds its subprocess environment from `isolated_env()` with explicit overrides.
  - `tests/test_remote_gate.py` plants the variable on purpose and checks that it does not leak.

  No other test can inherit the skip through `check_lock`. The design follows CLAUDE.md "Push invariants into types":
  forgetting `env` raises `TypeError`, and `test_the_environment_is_a_required_keyword` holds that. It also matches the
  repo's existing pattern of a passed environment (`godot_check.find_godot(os.environ, ...)`). The alternative, an
  autouse conftest fixture that clears the variable, would hide the dependency rather than remove it. This is the
  better fix.
- **The brief's red-first mode.** I ran `GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1
  .venv/bin/pytest -q tests/test_check_lock.py tests/test_maxim_fixes_pending.py -rx`. Result: 26 passed, 3 xfailed,
  and each XFAIL reason names its OD id and Maxim issue. `test_the_check_never_reads_the_process_environment` sets the
  drift job's three variables in the process and passes `env={}`. It therefore holds the property in the exact mode
  the brief names, not only in the skip-variable-only mode (E2).
- **Scope.** The diff touches eight files:
  - `constraints/py3.12.txt` and `constraints/py3.14.txt`
  - `scripts/check_lock.py`
  - `tests/test_check_lock.py`
  - the new `tests/test_maxim_fixes_pending.py`
  - the OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7 rows of `docs/roadmap.md` (the hunk changes exactly those five rows)
  - `docs/design/reviews/drift_and_lock/README.md`
  - lesson 41

  All are on the brief's list. No workflow edits. No ids outside O79's reservation are used.
- **The lockfiles.** Each file has a one-line diff, `pymaxim==1.3.3` to `==1.3.4`. No numerical pin moved.
- **The roadmap rows against the installed pymaxim** (`.venv/.../maxim`, `metadata.version("pymaxim") == "1.3.4"`):
  - OD-I1: the five `x or time.time()` sites are still at `salience_map.py:227`, `salience_network.py:222` and
    `cost_tracker.py:376`, `:469`, `:480`. True.
  - OD-I3: `semantic.py:662` still has `np.load(path, allow_pickle=True)`. True.
  - OD-I6: `requires("pymaxim")` gives `rich<14.0,>=13.0.0`. True.
  - OD-I7: `spec.py:1040` raises `DamageRefused`. True.
  - Maxim's clone: `git tag --contains 1b2e60a9` is empty, so #1773 is in no release.
  - Diffing `1b2e60a9^1..1b2e60a9`: `pyproject.toml` widens the cap to `rich>=13.0.0,<16.0`, `cost_tracker` switches
    to `is not None`, and `EmbeddingStore.load` refuses version 1 with `allow_pickle=False`. That agrees with what the
    gates and their stand-ins assume.
  - I did not re-run the gates on #1773's source. `git archive` is outside the read-only commands I was allowed.
- **Facts stated in two places.** I grepped `docs/` and `CLAUDE.md` for `1.3.3`, `1.3.4`, `OD-I[13567]` and the new
  module's name. Results are A1, A3 and A4.

## Findings

### A1. SHOULD-FIX: `docs/roadmap.md::OD-I6` claims a proof that was never run, and lesson 41 says so

**Defect.** The OD-I6 row ends: "it fails on 1.3.4 and passes on #1773's source (`phase1/drift-and-lock`)". The gate
`test_pymaxim_admits_rich_14` reads `metadata.requires("pymaxim")`, which is the *installed distribution's* metadata.
Putting #1773's `src/maxim` first on `sys.path` cannot change that, so the gate cannot have passed "on #1773's source".
Lesson 41 in the same commit says the opposite: "OD-I6 reads the installed distribution's metadata, so only its
stand-in, #1773's own `rich>=13.0.0,<16.0`, can show it."

So the same fact is stated in two places, and the two disagree. The roadmap row, the one a future session reads to
decide whether a gate is trustworthy, carries the wrong version. Under CLAUDE.md's brutal-honesty rule this is a claim
that overstates verification.

**Failure scenario.** At 1.3.5 the repeat session reads the row and treats OD-I6's flip as proven against the real
fix. Suppose Maxim's released metadata spells the requirement differently, for example under an extra or with an
environment marker so `Requirement(r).name == "rich"` matches a different entry. Or suppose `next(...)` raises
`StopIteration` because no `rich` entry exists. The gate then fails with something other than `AssertionError`, or
stays red. The row told the session this had been checked.

**Fix (verified by reading):** reword the row's tail for OD-I6, for example "it fails on 1.3.4; its stand-in,
#1773's own requirement string, passes (lesson 41)". The OD-I1 and OD-I3 rows could cite lesson 41 for the evidence
instead of restating it, so it lives in one place. I read the test body and lesson 41 to confirm that the metadata
path is the only input. No run was needed.

### A2. SHOULD-FIX: `tests/test_maxim_fixes_pending.py` (module level, `pytest.importorskip`) lets the three red gates vanish instead of flip

**Defect.** The module starts with `cost_tracker = pytest.importorskip("maxim.models.language.cost_tracker")` and
`semantic = pytest.importorskip("maxim.similarity.semantic")`. If either import fails, all six tests are skipped and
pytest exits 0. That includes `test_pymaxim_admits_rich_14`, which needs neither module.

CLAUDE.md's red-gate rule exists so that a gate "can't stay green without ever reaching the bar it names", and it
calls out "a missing module, a renamed function" as the case to fear. A skip is that case in a quieter form. The gate
environment always has pymaxim, because `check_lock` refuses an environment without the locked `pymaxim==1.3.4`. So the
skip protects nothing in the gate. It only hides a move upstream. `test_sem_compat.py` uses `importorskip` too, but
that is a mirror test, not a strict red gate whose job is to flip.

**Failure scenario.** 1.3.5 ships #1773 and in the same release moves `EmbeddingStore` to
`maxim.memory.embeddings`, which is plausible given that #1773 already rewrote the file. The drift job installs 1.3.5,
and the module skips at collection. Nothing turns red, so nobody learns that OD-I1, OD-I3 and OD-I6 are fixed. The
brief's own trigger for the repeat ("O75's gates turn red then") never fires. The rows stay open past their fix.

**Fix (the skip behaviour verified, the fix unverified):** I copied the module to `<scratchpad>/review_arch/` with
the import path changed to `maxim.similarity.semantic_moved` and ran it. pytest reported `1 skipped` and exited
cleanly. A plain `import` (or `importlib.import_module` inside each helper, so one move does not hide the other two
gates) would make a move a collection error, which is red. I did not run that variant.

### A3. SHOULD-FIX: the lock move falsifies `docs/design/sem_stimuli.md`'s claim about `apply_damage`, and nothing records it

**Defect.** `sem_stimuli.md:133-135` reads: "`apply_damage` silently returns 1.0 without sub-sensors
(`spec.py:1034-1036`, OD-I7), so a build test requires a planted burn to lower integrity." On the locked release that
is no longer true: 1.3.4 raises `DamageRefused`, at `spec.py:1040` in the installed copy.

This is contract text: the region-modulator build depends on it. The future bridge must now handle a raised exception
where the design expected a silent no-op. The fact now lives in two places that disagree: the roadmap row (closed,
"raises `DamageRefused`") and the design (silent 1.0). The design doc is outside this brief's file list, and existing
design documents don't grow. So the right move is an open item, not an edit here. But the branch closes OD-I7 without
pointing at the dependent text, which is the "stale fact left behind" this lens exists to catch.

The commit message says "Nothing in this repo calls apply_damage, so no gate here flips". I confirmed that with
`grep -rn apply_damage src/`, which found nothing. So nothing breaks today. The risk is to the build step that reads
the design.

**Failure scenario.** The session that builds region modulators reads §4 of `sem_stimuli.md` and writes the planted
burn test expecting a silent 1.0 on a flat body. On 1.3.4 it gets `DamageRefused`. It may then catch and swallow the
exception to match the design, which is a band-aid the no-silent-swallow rule forbids. Or it may lose time on an
apparent regression.

**Fix (unverified):** add one clause to the OD-I7 row (in scope), for example "`sem_stimuli.md` §4's 'silently
returns 1.0' describes 1.3.3; the region-modulator build step reads `DamageRefused` instead". Or record it as an open
item in the review record with that build step as the trigger. Either way the design itself stays untouched until its
owner's step.

### A4. NIT: `docs/design/inference_placement.md:22` says "The locked release is pymaxim 1.3.3"

**Defect.** The sentence is present tense and now false. It sits in a dated "Sources" paragraph (Maxim at
`043eab8f`), so a careful reader takes it as a snapshot. It is still a second, unowned statement of what
`constraints/` owns.

**Scenario.** A reader cites the design for the locked version in a Maxim proposal and quotes the wrong release.

**Fix (unverified):** out of scope here. Record it as an open item with the trigger "next edit of
`inference_placement.md`", rewording it to "read against pymaxim 1.3.3". The same applies to
`docs/design/research/time/*`'s "installed pymaxim 1.3.3", which already reads as a snapshot and needs nothing.

### A5. NIT: `scripts/check_lock.py::main` still reads `argv` and `version` from the process

**Defect.** The fix removes ambient reads for `env` only. `argv=None` falls back to `sys.argv[1:]`, and `version=None`
falls back to `sys.version_info`. These are the same class of inherited-runner-state hazard. The docstring is accurate
because it claims this only for `env`. But a test that omits `argv` reads pytest's own command line. That is harmless
today: no pytest flag spells `--report`, and every test passes `argv=[]`. It is the same shape as the bug just fixed.

**Fix (unverified):** when `main` is next touched, make `argv` required keyword-only too, with `__main__` passing
`sys.argv[1:]`. Not worth a fold now.

### A6. NIT: `docs/roadmap.md` rows OD-I1, OD-I3, OD-I5, OD-I6, OD-I7 cite the branch, not the PR

**Defect.** The brief says "Close both roadmap rows, citing your PR". The rows cite `phase1/drift-and-lock`. A branch
name stops resolving once the owner merges and deletes it. A PR number does not.

**Fix:** swap in `#<n>` once the PR exists. That is a text-only change, and the stop rule decides whether it needs a
delta round.

## Status

All six findings are `open` as of `38383fc` (reviewer-set, O25).
