# Executor delta review: `phase1/drift-and-lock` fold (`38383fc..d1c105b`)

**Lens:** Executor. **Scope:** the fold's diff only. Per the stop rule, this is the last round. I worked read-only in the worktree. Every mutation ran on copies under `<scratchpad>/delta_exec/`: overlays of the installed `maxim` package, and a `git archive` of `d1c105b`. Each mutation was put first on `PYTHONPATH`, with `--basetemp` in the scratchpad.

## Status of the round-1 findings (set by this reviewer, read from the tree)

| Finding | Status | Evidence |
|---|---|---|
| E1 (SHOULD-FIX) | **fixed** | `check_lock.entry` exists, and `test_the_command_line_decides_the_skip_from_the_process_environment` calls it. I changed `entry` to `main(env={})`: 1 failed, 23 passed. I changed it to drop `GITHUB_EVENT_NAME`: 1 failed. Unmutated: 24 of 24 pass, in a clean shell and in drift mode. One untested line remains; see N2. |
| E2 (SHOULD-FIX) | **fixed** | Results by setup (the full matrix is below). On installed 1.3.4, XFAIL. On 1.3.4 with only `version != 2`, XFAIL. On #1773 with `allow_pickle=True` restored, XFAIL. On #1773 (`1b2e60a9`, both files), XPASS(strict). So the gate now tells "pickle off" from a version bump, and from #1773 with the defect restored. It flips on the real fix. One residual gap remains in a refusal order nobody has written yet; see N1. |
| E3 (SHOULD-FIX) | **fixed** | With `similarity/semantic.py` renamed in an overlay, the module gives `ModuleNotFoundError ... 1 error during collection`. It does not skip. Only `pytest.importorskip("maxim")` remains as a skip. |
| E4 (NIT) | **fixed** | Lesson 41 now names the `dist-info` overlay. I reproduced it by copying `pymaxim-1.3.4.dist-info` and setting `Requires-Dist: rich<16.0,>=13.0.0`, which is #1773's `pyproject.toml:52`. `test_pymaxim_admits_rich_14` went XPASS(strict). The OD-I6 row no longer claims an unrun result; it cites lesson 41. |
| E5 (NIT) | **fixed** | The OD-I1 row now says the gate holds one of the five sites (`get_totals`), and that the release must be read for all five before the row closes. |
| E6 (NIT) | **deferred** | The OD-I5 and OD-I7 rows still cite `phase1/drift-and-lock`, not a PR number. The PR does not exist yet. Reason: the number is unknown until the PR opens. Trigger: the PR opens. The number goes into the rows before hand-off. This is the author's stated plan, and nothing in the tree carries it yet. |
| D1 (NIT) | **fixed** | The `_assert_a_world_time_of_zero_is_a_time` docstring states the bound: Maxim's clock must read later than 3,601 s after the epoch. |
| D2 (NIT) | **deferred** | The stand-in still patches `numpy.load` process-wide (`semantic.np` is numpy). It is harmless serially, and monkeypatch restores it. Reason: no parallel runner exists. Trigger: tests run concurrently in one process. This matches the README. |

## OD-I3 gate matrix (the fold's gate, unmodified)

| Setup | OD-I1 | OD-I3 | OD-I6 |
|---|---|---|---|
| installed 1.3.4 | XFAIL | XFAIL | XFAIL |
| 1.3.4 with `version != 2` (pickle on) | XFAIL | XFAIL | XFAIL |
| #1773 with `allow_pickle=True` restored | XPASS(strict) | **XFAIL** | XFAIL |
| #1773 `semantic.py` and `cost_tracker.py` | XPASS(strict) | **XPASS(strict)** | XFAIL |
| #1773 plus its `rich` line in a `dist-info` copy | XPASS(strict) | XPASS(strict) | XPASS(strict) |
| 1.3.4 plus a new-key check before `version` (pickle on) | XFAIL | **XPASS(strict): false flip** | XFAIL |

On #1773 the log shows `Failed to load embeddings: Object arrays cannot be loaded when allow_pickle=False`. So the gate passes because the pickled `version` is refused, which is the defect's own effect, and not because a refused format happens to return 0.

## New findings

### N1, SHOULD-FIX: `tests/test_maxim_fixes_pending.py::_assert_a_pickled_embedding_file_is_refused` (docstring), and `docs/lessons_maxim_in_games.md` lesson 41

**Defect.** Both texts justify the bar with "the pickled value sits in `version`, which every loader reads first". That is a universal claim about future loaders. It holds for the two that exist, 1.3.4 and #1773 (#1773 checks `"version" in data.files`, then reads it). Nothing enforces it. The marker stays absent for any loader that refuses the file before it touches `version`, whether or not pickle is still on. So the gate keeps a narrower form of the E2 false flip. Lesson 41's own consequence says to assert "the defect's own effect … never a return value that every failure shares". An absent marker is still shared by every refusal that comes before the read.

**Failure scenario.** 1.3.5's loader hardens the save format before `AgentHome`, for example with a required `schema` or digest key checked first, and keeps `allow_pickle=True`. The gate goes XPASS(strict). The lock-moving session removes it and closes OD-I3, and `np.load(allow_pickle=True)` is still in the release.

**What I ran.** I copied installed 1.3.4 and added `if "schema" not in data.files: return 0` right after its `np.load(path, allow_pickle=True)`. The committed gate went XPASS(strict).

**Proposed fix (verified).** The cheapest fix is to the text: write "which both loaders we have read (1.3.4, #1773) read first", so the assumption is named and not presented as a law. The stronger fix holds the defect itself. Keep the marker, and also spy on the `allow_pickle` argument:
```python
calls: list[object] = []
real = np.load
def spy(*a, **k): calls.append(k.get("allow_pickle", False)); return real(*a, **k)
monkeypatch.setattr(semantic.np, "load", spy)
...; assert not marker.exists(); assert True not in calls
```
I ran this variant as a standalone file. It gave XFAIL on 1.3.4, on the version bump, on #1773 with pickle restored and on the key-first mutation. It gave strict XPASS (reported as failed) on #1773. The variant needs the helper to take `monkeypatch`, and it widens D2's process-wide patch to the gate itself. I did not run ruff or mypy on it. Note: a loader that moved to `pickle.load` would bypass the spy, so the marker is still needed.

### N2, NIT: `scripts/check_lock.py` (the `if __name__ == "__main__":` block)

**Defect.** E1's guard covers `entry`, but the line that calls it, `sys.exit(entry())`, is still excluded from coverage and run by no test. On the archived tree I changed it to `sys.exit(main(env={}))`, and `test_check_lock.py` passed 24 of 24. The unguarded surface has shrunk from an expression to a bare call. It is the same one-line idiom every script here uses, and editing it to bypass `entry` would be deliberate.

**Failure scenario.** Someone edits that line to bypass `entry`. The drift job's `check_lock` then refuses the unpinned stack, and the job goes red for our own bug. That is lesson 40 again.

**What I ran.** The mutation above. **Trigger:** none needed now. If wanted, a subprocess test would close it, but subprocess sites are gated by `ALLOWED_SPAWNS`. I did not propose or verify one.

## Checked, no finding

- **The pickled payload is safe and contained.** On 1.3.4, `__reduce__` runs `os.mkdir(<tmp_path>/unpickled)` and nothing else. I ran the module with `HOME` and the four XDG variables pointed at an empty scratch directory, and it stayed empty. Every artefact landed under `--basetemp` (`embeddings.npz`, `unpickled`, `cost_state.json`). The 1.3.4 loader swallows the resulting `int(None)` `TypeError` and returns 0, so the gate fails on `assert not marker.exists()` as an `AssertionError`. That matches `raises=`.
- **The `entry` test can fail** (E1 row), and it is deterministic under drift-mode inheritance: `monkeypatch.setenv` and `delenv` override the runner and restore it afterwards.
- **The stand-in proof still passes.** `test_the_pickle_gate_passes_once_pickle_is_off`: the marker is absent and the store is empty.
- **Scans.** I ran `tests/test_isolation.py`, `tests/test_input_allowlist.py`, `tests/test_tooling_config.py` and the determinism hidden-sources scan: 198 passed. `ruff check` and `mypy` on the three changed Python files are clean.
- **The fold table's claims are reproduced:** `entry` red under `main(env={})`, the moved module a collection error, OD-I3 red on #1773 with pickle restored, and OD-I6 flipping on the `dist-info` overlay. The `docs/design/reviews/drift_and_lock/` reports contain no home paths (grep).

**Counts:** 0 BLOCKER, 1 SHOULD-FIX (N1), 1 NIT (N2).
