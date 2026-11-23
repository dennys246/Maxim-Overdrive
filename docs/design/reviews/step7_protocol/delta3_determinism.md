# Determinism and replay: delta round 3 on phase1/protocol (e97727d .. a532695, merged at 87ff10e)

Fold table: fixed 2, deferred 1 (accepted), rejected 0, open 0. New findings: BLOCKER 0, SHOULD-FIX 0, NIT 1.

Everything was run against `git archive 87ff10e` in `<scratchpad>/delta3/determinism/tree`, with that tree's `src/` and `scripts/` first on the path (checked by printing `__file__`). Mutations were made in that copy and restored by byte comparison afterwards. No worktree was modified. The merge 87ff10e changes only `docs/` files from main (`git diff --name-only a532695 87ff10e`). It touches nothing of this branch's code, tests, scripts or client, and step 7's N3 deferral in `docs/plans/checklists.md` survives it.

## Fold table

| Finding (delta 2) | Status | What I read and ran |
|---|---|---|
| NIT N2 (nothing holds the main test to the asyncio half) | **fixed** | `tests/test_determinism.py::scan_hits` is now the main test's own scan (`hits = scan_hits({p: p.read_text() ...})`), and `test_the_main_scan_holds_src_to_the_asyncio_half` runs it on a planted `src/` file. I broke it by changing `scan_hits` to call `findings` for every file, and that test went red (1 failed). Residual, accepted: the main test could stop calling `scan_hits` and inline its own scan again. Nothing can test that short of a meta-test, and review sees it. |
| NIT N4 (`LOOP_HANDLES` misses `loop.time()`, the policy route and `connection.latency`) | **fixed** | `LOOP_HANDLES` now includes `time` and `latency`. I planted `def _pace(loop): return loop.time()` and `def _lag(connection): return connection.latency` in the copy's `server.py`, and the main scan went red. The policy route (`get_event_loop_policy().get_event_loop().time()`) is caught through `.time`. `.time` has zero hits in `src/`, where the simulation's time is `time_s`, so the handle won't collide with step 5a's clock as it is named today. The B14 row now names websockets' `ping()` round trip as review-held, "which the scan can't see". That is accurate: `.ping` isn't a handle, and the awaited waiter's result is the latency. See new NIT D3-N1 for the missing unit cases. |
| NIT N3 (`player_text` acceptance differs between 3.12 and 3.14) | **deferred; I accept the deferral** | No change in this fold. Step 7's checklist row (line 348) still gives the reason and the trigger (the first logged speech, `phase1/agents`). |
| N1's residual (a helper wrapping the one allowed `wait_for`) | not a finding | My delta-2 report wrote this as a residual I didn't hold the fold to. The author lists it as open, which is the right place for it. |

## New finding in the fold's diff

### NIT D3-N1: `tests/test_determinism.py::LOOP_HANDLES`: the two new handles have no unit case, so reverting them stays green

I reverted the set to its delta-2 contents (dropped `"time", "latency"`). All 91 scan-related tests stayed green on a clean tree. With my two plants added to `server.py`, everything still stayed green. The only thing that holds these handles is a plant that nobody commits. N4's fix was mine, and my delta-2 proposal didn't include a test either. The miss is shared.

Fix, **verified** in the copy: add these two cases to `test_the_src_scan_sees_asyncio_s_clock`'s parametrize list.

- `"def f(loop):\n    return loop.time()"`
- `"def f(connection):\n    return connection.latency"`

With them added, the test gives 12 passed. With the handles then dropped, 2 failed.

## Checked, sound

- **Fixture bytes after the value-tree change.** `wire_texts.value_tree` now writes a float as `{"f": "finite"}`, a constant, and no longer imports `struct`. That removes the one platform-sensitive encoding the trees had. `wire_fixtures.files()` gives 188 files (183 plus the five new `json/` edges). One sha256 over the sorted names and bytes gives `96090e788621da86` on 3.12.12 (Unicode 15.0.0) and on 3.14.6 (16.0.0), each with `PYTHONHASHSEED` 0, 3 and random, and `stale(OUT) == []` on all six runs (`<scratchpad>/delta3/determinism/hashall.py`, `-I`).
  - `LIMITS` gained `max_text_bytes`, a literal written with `sort_keys`.
  - The new fixtures are byte literals in a dict, so their order comes from the sorted manifest.
- **Replay.** The float's digits were never part of anything a replay reads. The server emits no float (O62), and the client only classifies one, so dropping the bits loses no replayed state.
- **Server and client changes** (the text cap, the close reason, the String type check, the reconnect reset) add no clock, entropy or ordering source. `server.py` still has exactly one `wait_for`, which matches the allowance's count of 1.
- **Tests run.** 3.12, against the copy: `tests/test_determinism.py tests/test_wire.py tests/test_text.py`, 474 passed and 1 skipped.

## Outside my lens, for the Executor reader

The fixture `exact_halfway_past_the_largest_double` (`[1.79769313486231581e308]`) is not the exact halfway. The halfway, 2^1024 − 2^970, is 1.797693134862315807937…e308, and the fixture's value is above it (checked with `fractions.Fraction`). So the fixture rounds to infinity under any tie rule. It doesn't test the tie that Executor S1 asked about, and the commit's "the exact halfway … is a fixture" overstates it. That is not a determinism defect. I'm passing it on unverified against S1's original wording.
