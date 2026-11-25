# Executor review: `phase1/drift-and-lock` (`1ed9caa..38383fc`)

**Reviewer lens:** Executor. **Diff:** three commits (`aee5ca1`, `2a09f5d`, `38383fc`). I ran everything read-only. Every
mutation ran on copies under `<scratchpad>/review_exec/`, using the worktree's venv, and never touched the tree.

## Summary

**Counts:** 0 BLOCKER, 3 SHOULD-FIX, 3 NIT.

What holds:
- **Exit test, local lines: all pass.** Both lockfiles carry `pymaxim==1.3.4`, and `check_lock.py` prints `PASS (py3.12.txt, 0 difference(s))`. In drift mode, `test_check_lock.py` passes 23 of 23. The gate module names OD-I1, OD-I3 and OD-I6, and it holds 3 `strict=True`, 3 `raises=AssertionError` and 3 `XFAIL`.
- **Red first, reproduced.** I ran the old `test_check_lock.py` and old `check_lock.py` (from `1ed9caa`) in drift mode (`GITHUB_ACTIONS=true GITHUB_EVENT_NAME=schedule MAXIM_OVERDRIVE_UNLOCKED=1`). The result was 2 failed, `test_a_python_without_a_lockfile_fails` and `test_main_compares_the_lock_with_what_is_installed`, both `AssertionError: assert 0 == 1`.
- **The guard was proved by deletion, reproduced.** I put `env = os.environ` back at the top of `main`. Drift mode gives 6 failed, and `test_the_check_never_reads_the_process_environment` is among them. I also gave `env` a default of `os.environ`, and `test_the_environment_is_a_required_keyword` failed.
- **All three gates fail today for the stated reason.** Under `--runxfail` I got:
  - OD-I1: `assert 0.0 == 1.0`. The hourly total was pruned at the wall clock.
  - OD-I3: `assert 1 == 0`. The version 1 object-array file loaded one entry.
  - OD-I6: `SpecifierSet('<14.0,>=13.0.0').contains('14.2.0')` is False.
- **All three flip on the real fix.** I copied the installed `maxim` package and replaced `cost_tracker.py` and `semantic.py` with Maxim `1b2e60a9`'s, via `git -C <Maxim> show`. I copied `pymaxim-1.3.4.dist-info` and set its rich line to #1773's `rich<16.0,>=13.0.0`. With that copy first on `PYTHONPATH`, all three gates report `XPASS(strict)` and fail. That includes OD-I6, which the author said could not be shown this way (E4).
- **No home-directory writes.** I ran the gate module with `HOME` and the four XDG variables pointed at an empty scratch directory, and the directory stayed empty. `CostTrackerConfig(state_path=...)` keeps `resolve_user_state` (which would `mkdir ~/.maxim/util`) off the path. Every file the tests write lands under `--basetemp`.
- **No wall clock in the tests.** No test reads the clock. The code under test does (`CostTracker.__init__`, `_maybe_persist`, and the gate's own subject `get_totals`). The outcome holds for any wall clock after 3,601 s past the epoch, so it is deterministic. The targeted scans pass: `test_determinism.py` `hidden_sources`, `test_isolation.py`, and `test_tooling_config.py` red-gate and isolation (76 passed).
- **Lockfiles.** Only the pymaxim line moved in each. The 3.12 and 3.14 files are identical below their headers, and the header lines are unchanged from `1ed9caa`.
- **OD-I7 closure checked.** The installed 1.3.4 `embodiment/spec.py` imports and raises `DamageRefused` at `:1040`. Nothing in `src`, `tests` or `scripts` calls `apply_damage`.

## Findings

### E1, SHOULD-FIX: `scripts/check_lock.py::__main__` (the entry point's `main(env=os.environ)`)

**Defect.** The fix moves the only read of the process environment into `if __name__ == "__main__": sys.exit(main(env=os.environ))`. Coverage leaves that line out (`exclude_also = ["if __name__ == .__main__.:"]`), and no test runs it. Before this branch, `test_only_the_scheduled_drift_job_may_skip` set real environment variables, so it exercised the process-environment path from end to end. Now it passes `env` directly. The one line that connects the drift job's variables to the skip decision has lost its guard.

**Failure scenario.** A later edit "hardens" the entry to `main(env={})`, or passes a filtered mapping that drops `GITHUB_EVENT_NAME`. The drift job installs unpinned, `check_lock` no longer skips, and it reports `FAIL` on the unpinned stack. The weekly job then goes red forever. Locally everything stays green, and diff coverage can't see the excluded line. This is the failure class this branch exists to fix (a red drift job for our own bug).

**What I ran.** I changed the entry to `sys.exit(main(env={}))` on a copy. `test_check_lock.py` then passed 23 of 23 in drift mode and 23 of 23 in a clean shell.

**Proposed fix (verified).** Give the entry a tested function, and test it with the process environment patched:
```python
def entry() -> int:
    """The command line: the one caller that hands main the process environment."""
    return main(env=os.environ)

if __name__ == "__main__":
    sys.exit(entry())
```
```python
def test_the_command_line_decides_the_skip_from_the_process_environment(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_lock.py"])
    for k, v in DRIFT_JOB.items():
        monkeypatch.setenv(k, v)
    assert check.entry() == 0
    assert "SKIPPED" in capsys.readouterr().out
    monkeypatch.delenv("GITHUB_EVENT_NAME")
    assert check.entry() == 1
```
On a copy, this passed 24 of 24. Changing `entry` to `main(env={})` then turned the new test red (1 failed). I did not run ruff or mypy on it.

### E2, SHOULD-FIX: `tests/test_maxim_fixes_pending.py::_assert_a_pickled_embedding_file_is_refused`

**Defect.** The gate's bar is `store.load(path) == 0 and len(store) == 0`. In 1.3.4, `EmbeddingStore.load` wraps its whole body in `except Exception: logger.error(...); return 0`. It also returns 0 for any version it does not accept. So the gate turns green for any change that makes this file fail to load, not only for "pickle is off". The committed proof, `test_the_pickle_gate_passes_once_pickle_is_off`, passes through that same swallow: with `np.load(allow_pickle=False)`, `data["memory_ids"]` raises `ValueError`, the handler swallows it, and load returns 0. The proof therefore shows that the helper can pass. It does not show that the helper tells a pickle-off loader from any other failure. The security property, that no code runs from the file, is never checked.

**Failure scenario.** A release bumps the embedding format to version 2 and leaves `allow_pickle=True` in place. Or it renames a key, or tightens a shape check. The gate goes `XPASS(strict)`, and the lock-moving session reads that as "OD-I3 fixed". It removes the gate and closes the row, while `~/.maxim/util/semantic_embeddings.npz` is still unpickled. OD-I3 must land before `AgentHome` makes this path reachable from saves.

**What I ran.** On a copy of 1.3.4's `semantic.py`, I changed only `if version != 1` to `if version != 2`, so pickle stays on. The committed gate went `XPASS(strict)`.

**Proposed fix (verified).** Make the bar "nothing was unpickled". Put a payload with an observable side effect in the `version` field, which every loader reads first, and assert that the side effect never happened:
```python
class _Payload:
    def __init__(self, marker: Path) -> None:
        self.marker = marker
    def __reduce__(self):
        return (os.mkdir, (str(self.marker),))
# np.savez(path, memory_ids=np.array(["mem-1"], dtype=object), embeddings=..., hashes_json=...,
#          version=np.array([_Payload(tmp_path / "unpickled")], dtype=object))
# EmbeddingStore(embedder=None).load(str(path)); assert not (tmp_path / "unpickled").exists()
```
Results: XFAIL on installed 1.3.4, XFAIL on the version-bump-only mutation, and `XPASS(strict)` on #1773's `semantic.py`. A payload in `memory_ids` would not work, because #1773 refuses version 1 before it reads `memory_ids`; I tried it, and it false-flipped on the version-bump mutation too. I did not check the variant against `scripts/lint_inputs.py` or `tests/test_input_allowlist.py`. The current gate already hands Maxim a pickled array, so the exposure is the same. The stand-in proof would become a monkeypatched `np.load(allow_pickle=False)`, under which the marker stays absent.

### E3, SHOULD-FIX: `tests/test_maxim_fixes_pending.py` (module level, the two `pytest.importorskip` calls)

**Defect.** The module skips as a whole if `maxim.models.language.cost_tracker` or `maxim.similarity.semantic` can't be imported. A gate whose precondition breaks must fail loudly ("a precondition the gate needs raises something other than its `raises=` type", and "never `skip`"). Here a broken precondition turns into a silent skip of all six tests. That includes OD-I6, which needs neither submodule. pytest does not fail on skips, and the gate environment always has pymaxim (`check_lock` refuses one without it). So inside the gate, a skip can only mean that Maxim moved a module.

**Failure scenario.** 1.3.5 moves `semantic.py`, for example to `similarity/embedding_store.py`. The drift job and the 1.3.5 lock move show "1 skipped" and no red. The three gates disappear without a sign, so OD-I1, OD-I3 and OD-I6 stay open with nothing holding them. Or the opposite happens: they get closed on the strength of a green run that never executed them.

**What I ran.** I copied the package with `similarity/semantic.py` renamed and put it first on `PYTHONPATH`. The module, as written, reported `SKIPPED [1] ... could not import 'maxim.similarity.semantic'` and `1 skipped`.

**Proposed fix (verified for behaviour).** Skip only on the distribution's absence, then import plainly: `pytest.importorskip("maxim")`, followed by `from maxim.models.language import cost_tracker` and `from maxim.similarity import semantic`, or `importlib.import_module(...)` to avoid an E402 `noqa`. With the moved module, this gave a collection error (`1 error`). With the installed package, it gave `3 passed, 3 xfailed`. I did not check the exact spelling against ruff or mypy.

### E4, NIT: `docs/lessons_maxim_in_games.md` (lesson 41), `docs/roadmap.md` (OD-I6 row)

**Defect.** Lesson 41 and the commit message say that OD-I6 "reads the installed distribution's metadata, so only its stand-in ... can show it". That is false: a copied `dist-info` with #1773's requirement, first on the path, shows the flip. The roadmap's OD-I6 row also claims that the gate "passes on #1773's source", which the author's own text says was never run. The claim turns out true, but it was written before anyone measured it.

**Failure scenario.** A later gate on metadata is "proved" only by a hand-typed string. If the string was typed wrong, the gate never flips, and the lesson has taught that nothing better is possible.

**What I ran.** I copied `pymaxim-1.3.4.dist-info` and changed its `Requires-Dist: rich` line to `rich<16.0,>=13.0.0`. `test_pymaxim_admits_rich_14` went `XPASS(strict)`.

**Proposed fix (verified as above).** Correct the sentence in lesson 41 to name the `dist-info` overlay. The row's claim can then cite that run.

### E5, NIT: `tests/test_maxim_fixes_pending.py::test_a_world_time_of_zero_is_a_time`

**Defect.** OD-I1 names five sites (`salience_map.py:227`, `salience_network.py:222`, `cost_tracker.py:376`, `:469`, `:480`), and the gate holds one of them, `get_totals` at `:469`. The brief allows a single public call. But the row closes when this one gate flips.

**Failure scenario.** A release fixes `cost_tracker` and leaves `salience_*` on `or time.time()`. The gate flips, the row closes, and the salience sites still turn world time 0.0 into the wall clock. #1773 does fix all five, so this is unlikely for 1.3.5.

**What I ran.** I read #1773's diff (`salience_map.py` and `salience_network.py` are in it). I did not write a second gate.

**Trigger:** the 1.3.5 lock move. Before closing OD-I1, read the release for all five sites, or add a gate on a public salience call.

### E6, NIT: `docs/roadmap.md` (OD-I5 and OD-I7 rows)

**Defect.** The brief says "Close both roadmap rows, citing your PR". The rows cite the branch name (`phase1/drift-and-lock`), not a PR number.

**Failure scenario.** After the merge and branch deletion, the citation no longer resolves to a review record.

**What I ran.** I read the diff.

**Trigger:** when the PR opens, put its number in the rows, before hand-off.

## Not findings (checked)

- **`raises=AssertionError` is narrow enough.** A `StopIteration` in OD-I6 (rich dropped from the requirements) would error, not xfail. So would a `TypeError` in the constructors.
- **The OD-I1 stand-in.** `monkeypatch.setattr(cost_tracker, "time", _Clock)` swaps a module global and restores it. It models a clock at 0.0, not the fix, but the real fix was verified separately.
- **`semantic.np.load` is the global `numpy.load`.** Monkeypatch scopes and restores it.
- **Commit signatures.** `git log --format=%G?` shows `G` on all three commits.
