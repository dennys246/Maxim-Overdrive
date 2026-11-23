# Executor delta-3 review: step 7 fold (e97727d..a532695, merged at 87ff10e)

Lens: Executor. I reviewed `git archive 87ff10e` copies under `<scratchpad>/delta3/executor/{t,py}`. Godot ran only
through `godot_check.run_godot`, with HOME in scratch. I wrote nothing to the worktree.

Baseline:
- Python (text, host, wire, formats, determinism): 1315 passed, 1 skipped.
- Client suite: 90 passed.
- `test_godot_net`: 7 passed.

The merge at 87ff10e touches two of this branch's files. In `checklists.md` it appends the generation-harness section.
In `foundations_plan.md` it changes other steps' rows and the index. Step 7's text is unchanged in both.

## 1. Fold table (my delta-2 findings)

| ID | Status | What I checked |
|---|---|---|
| X-N1 `_visible` ignorable clause | **fixed** | The clause is removed. Every character still passes through `_refused_at`, which refuses default-ignorables, so the outcome can't change. I checked this by reading, not by an exhaustive run. |
| X-N3 reconnect | **fixed** | Deleting `session = NetSession.new()` turns `test_a_reconnect_starts_a_fresh_session` red. The residual is new NIT N1. |
| X-N4 `_INT_DIGITS` | **open, regressed** | The guard was removed on a claim that is false. See B1. |
| E-N3b token early exit | **open** | The author marks it open. It has no backlog row. As a NIT it is the author's call. |
| S1 halfway rounding | **fixed** | With `elif false:`, `exact_halfway_past_the_largest_double` goes red (accepted, want bad_json). |
| S2 close-reason shape | **fixed** | With `not reason.is_empty()`, `test_a_close_reason_that_is_no_code_is_not_taken_as_one` goes red. |
| S3 boundaries words | **rejected, accepted** | boundaries.md is 10748 words at main (06c2774) and at a532695. My delta-2 count compared two commits inside the branch, not against main. O22 and O66 compare with main. |
| N1 `_double` comment | **fixed** | The comment and `value_tree` now promise the class only. Corrupting the tree's class turns the fixture-regeneration test red. |
| N2 `was_float` | **fixed** | The parameter is removed. Removing `not value is int` goes red in 3 tests. |
| N3 `_blank` in `_visible` | **fixed** | The clause is now load-bearing: deleting it turns "the braille blank alone" red. |
| N4 `MAX_TEXT_BYTES` | **fixed** | It is in the manifest's limits. Changing 64 to 256 KiB goes red. Dropping it from `LIMITS` goes red too. |
| N5 asyncio alias | **open** | The author marks it open. The scan's docstring doesn't name the limit. |
| N6 U+2800 | **fixed** | The rule is narrowed and braille passes. Mutating back to "any blank" goes red. |

Counts: **9 fixed, 3 open, 1 rejected (accepted), 0 deferred.**

### The commit's "proven by breaking" list

I broke each guard in a copy, and every one went red:
- close-reason shape;
- type is a String first: 4 failures, with "Invalid operands 'int' and 'String'", as claimed;
- halfway rounding;
- fresh session;
- MapOf walk: 2 failures;
- the network-lane contract: a planted applier import makes 1 contract break;
- MAX_QUEUE.

Also red:
- a planted `connection.latency` or `.time()` in server.py;
- `scan_hits` reduced to `findings`;
- the `text()` cap's raise.

One claim of fact is false: "String.to_int clamps" (B1).

## 2. New findings

### BLOCKER

**B1. `client/addons/engine/net/wire_json.gd::_integer`: removing the digit guard lets Godot accept integers Python
refuses, one of them with its sign flipped.**

Godot 4.7.2's `to_int` does not clamp consistently. I probed it on the unmutated tree:

| Literal | `to_int` reads | Godot | Python |
|---|---|---|---|
| `9223372036854775808` (2^63) | −2^63 | accepts, as −2^63 | bad_json |
| `-9223372036854775808` | −2^63 | accepts | bad_json |
| `-18446744073709551617` | −2^63 | accepts | bad_json |
| `-99999999999999999999999` | −2^63 | accepts | bad_json |

`absi(−2^63)` overflows to −2^63, which is below `INT_MAX`, so the magnitude check passes. The old 16-digit guard
refused all four.

Failure scenario: a hostile peer on the port sends `{"type":"welcome","protocol":0,...}` with a field of 2^63. The
client reads it as a negative int where the server's reader refuses it. Any signed field later read without a range
check takes it.

The fixture corpus has no such literal, so the removal was "green".

Fix, verified: `if text.to_int() > INT_MAX or text.to_int() < -INT_MAX:`.
- My probe refuses all 8 literals and accepts `-9007199254740991`.
- The client suite passes 90.

Add the four literals above as `bad_json` fixtures. The commit's sentence about clamping needs correcting too.

### SHOULD-FIX

**SF1. `src/simcore/core/text.py::_refused_at`, `zero_width_blank`: it decides an outcome, and no test holds it.**

Replacing it with `False` leaves `test_text.py` green (61 passed). With it gone, `a\U00016fe4\U00016fe4\U00016fe4b` is
accepted: Khitan fillers (Mn) carry hidden bits between letters. That is the smuggling route O61 names.

Under Unicode 15, U+16FE4 is the only code point this clause catches.

The HIDDEN cases (the filler alone, and fillers with a joiner) are refused by other rules.

Fix, verified: add `("a\U00016fe4b", ...)` to HIDDEN. It is refused on the tree and accepted under the mutation.

**SF2. `src/simcore/host/server.py`, the `text()` call sites: the claim "the server refuses to write a reply past it"
is held only at `replies.text`. The wiring is not held.**

I replaced each of the three `text(...)` sends with `encode(...)` (welcome, the stage-1 error, dispatch). Each leaves
`test_host.py` green (42 passed).

Failure scenario: a refactor sends through `encode` again. A dispatch reply that grows past 64 KiB is then sent, and
the client ends the session with bad_shape.

Fix, unverified: a host test whose dispatch returns an oversized reply, and which asserts that nothing past the cap
reaches the client.

### NIT

- **N1. `net_client.gd::open`:** deleting `_hello_sent = false` leaves 90 green. A reconnect after a sent hello would
  never send a new one. The test could assert that a hello goes out, or check the flag.
- **N2. `net_session.gd::close_code`:** it has no reader and no test. Deleting the assignment in `poll` leaves
  `test_godot_net` green. This is capability with no caller. Have `net_check` print it, or drop it.

Scripts and logs: `<scratchpad>/delta3/executor/tools/{gdmut.py,pymut.py,rungd.py}`, `<scratchpad>/delta3/executor/probe/probe.gd`,
`<scratchpad>/delta3/executor/gd/out.txt`.
