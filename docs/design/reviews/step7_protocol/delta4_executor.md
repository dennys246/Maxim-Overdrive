# Executor delta-4 review: step 7 fold (87ff10e..5471454, merged at 0eba5e8)

Lens: Executor. I reviewed a `git archive 0eba5e8` copy under `<scratchpad>/delta4/executor/t`. I ran Godot only
through `godot_check.check`, the gate's full step: version, import, load, client tests, and the error scan of every
run. I gave it a scratch HOME. I wrote nothing to the worktree.

Baseline:
- `godot_check.check`: PASS, 0 findings.
- `test_text.py` and `test_host.py`: 105 passed.
- `test_wire.py` and `test_godot_net.py`, unset: 312 passed, 8 skipped.
- `test_godot_net.py` with `MAXIM_OVERDRIVE_GODOT=1`: 7 passed in each of 4 runs.

Merge 0eba5e8 overlaps the branch in CLAUDE.md, checklists.md, roadmap.md and standards_backlog.md. Every line it
removes is main's own text. Step 7's added lines survive, including the B5 row's "Measured in step 7" sentence.

## 1. Fold table (my delta-3 findings)

| ID | Status | What I checked |
|---|---|---|
| B1 `_integer` digit guard | **fixed** | The digit count runs before `to_int`. The four new fixtures are in the manifest, and so is the 400-digit negative. I ran 3 mutations in a copy, under the full check, and each went red. (a) With the guard neutralised (`digits < 0`): 5 "Godot printed an error" findings plus 3 test failures. (b) With `_INT_DIGITS` set to 19: 2 failures (`integer_at_2p63`, `negative_integer_at_2p63`). (c) Counting the sign as a digit: 2 failures. |
| SF1 `zero_width_blank` | **fixed** | `"a\U00016fe4b"` is in HIDDEN. Changing `or zero_width_blank` to `or False` makes it red (1 failed). |
| SF2 reply cap wiring | **fixed** (for the scenario I named) | I swapped the dispatch site to a plain `json.dumps` encode, and `test_a_reply_past_the_cap_ends_that_session_and_frees_its_token` went red. The welcome and both error sites are still unheld: swapping all three leaves 43 green. Their messages are bounded by construction. The welcome is covered by the checklist's new test-to-write, so I don't count this as a finding. |
| N1 `_hello_sent` reset | **open** | The commit marks it open, and it is untested. It has no checklist or backlog row. It is a NIT, so this is the author's call. |
| N2 `close_code` | **fixed** | The field and its assignment are gone. Nothing in `client/` reads it now. |
| E-N3b token early exit | **open** | It is listed open in the commit and has no row. NIT. |
| N5 asyncio alias | **open** | Same: listed open, no row. NIT. |

Counts: **4 fixed, 3 open, 0 deferred, 0 rejected.**

### Other claims in the commit, checked

- **The `loop.time()` and `connection.latency` scan cases hold.** Dropping `"latency"` from `LOOP_HANDLES` turns its
  case red, and so does dropping `"time"`.
- **The engine-fact socket test is now `0 or 1` packets.** It stayed green in 4 of 4 runs. It can still fail: if the
  reason is lost, it goes red. See N2 below for what it gave up.
- **The docs match the commit.** O68 is marked "awaiting the owner", and boundaries §9.1 cites it.
  client_rendering §4.3 says "can drop". The checklist carries both new rows with their triggers. The roadmap
  points at the pre-hello cap's deferral.
- **"a532695 could not pass the gate"**: I accept this. It held `integer_past_u64`, and that literal makes Godot
  print "Cannot represent 18446744073709551617". The error scan turns that into a finding. Mutation (a) reproduces
  it.
- **"Widening the guard … two 'Godot printed an error' findings and two client test failures"**: I could not
  reproduce this as worded, though the guard holds either way.
  - Widened to 19 digits: 0 error findings and 2 failures.
  - Widened to 20 digits: 1 error finding and 2 failures.
  - The count depends on how far the guard is widened. At 2^63 exactly, Godot prints no ERROR (N1 below).

## 2. New findings

No BLOCKER or SHOULD-FIX.

### NIT

- **N1. `client/addons/engine/net/wire_json.gd::_integer`, the comment.** It says "String.to_int prints an engine
  ERROR on overflow and returns -2^63". I measured something narrower under the 19-digit mutation:
  - Godot reads `9223372036854775808` (2^63) as -2^63 and prints nothing.
  - `-9223372036854775808` is not an overflow at all: it is representable, and only `absi` wraps.

  So the fixtures are what catch these two literals, not the error scan. Suggested wording: "may print an engine
  ERROR". Better, name that 2^63 reads silently.
- **N2. `tests/test_godot_net.py::test_godot_may_drop_the_error_that_arrives_with_the_close_and_the_reason_still_says_why`.**
  Before the fold, this test watched the engine fact (B26): it flipped if an upgrade made Godot hold the packet.
  Accepting 0 or 1 removes that tripwire. An engine that always holds the packet stays green. The old docstring's
  promise "if an engine upgrade makes it hold the packet, this flips" is gone, and no other test replaces it. That
  is acceptable while the behaviour is nondeterministic. B26's upgrade checklist should then name the measurement
  (14/16 runs held 0 packets) as something to re-measure on an upgrade.
- **N3. `client/addons/engine/net/net_client.gd`, line 16.** The reflowed doc comment is 124 characters, past the
  120 that the rest of the file keeps. No GDScript lint enforces this, and two older lines in `wire_json.gd` exceed
  it too.

Scripts:
- `<scratchpad>/delta4/executor/tools/gcheck.py`: the full `godot_check.check` on a mutated copy.
- `<scratchpad>/delta4/executor/tools/lines.py`.
- Run directories: `<scratchpad>/delta4/executor/runs/`.
