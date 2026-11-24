# Executor delta-5 review: the delta-4 fold (0eba5e8..70d8834, merged at 5e43010)

Lens: Executor. I reviewed a `git archive 5e43010` copy under `<scratchpad>/delta5/executor/t`. I ran Godot only
through `godot_check.check`, the gate's full step, with a scratch HOME. I wrote nothing to the worktree.

Baseline on the committed tree:
- `godot_check.check`: PASS, 0 findings.
- `test_wire.py` and `test_text.py`: 375 passed, 1 skipped.
- `wire_fixtures.stale(OUT)` on the copy: `[]`. The committed fixtures are exactly what the split generator makes.
- `lint_sizes.check_sizes` over `src/` and `scripts/`: no findings. `ruff` is clean on the two changed Python files.
- `lint_ids` (from main) over every `.md` file in the merged tree: `check_decisions`, `check_roadmap_ids` and
  `check_lessons` all return nothing, so O63 to O68 don't collide with main's ids.

The merge 5e43010 changes nothing of the branch's. Every file it touches has main's blob (868e160), except
CLAUDE.md, and in CLAUDE.md its hunk is exactly main's hunk. No branch-changed file differs from 70d8834.

## 1. Fold table (my delta-4 findings and the NITs still open)

| ID | Status | What I checked |
|---|---|---|
| D4 N1 `_integer` comment | **fixed** | It now says to_int returns -2^63 past int64, "with an engine ERROR above 2^63, silently at it", and that the fixtures hold it. That matches what I measured in delta 4. |
| D4 N2 close-packet tripwire | **fixed**, with the NIT N2 below | The checklist row exists, with a trigger ("the upgrade branch"). Where it lives is the problem: see N2. |
| D4 N3 GDScript over 120 characters | **fixed** | `awk 'length>120'` over `client/addons/engine/net/*.gd` and `client/tests/unit/net/*.gd` finds nothing. The `_utf8_sequence` rewrite has the same branches, and the full check passes. |
| D3 N1 `_hello_sent` reset | **open** | It has no row and no test. NIT, the author's call. |
| E-N3b token early exit | **open** | Same: no row. NIT. |
| N5 asyncio alias | **open** | Same: no row. NIT. |

Counts: **3 fixed, 3 open, 0 deferred, 0 rejected.**

### The commit's other claims, checked

- **"Changing the tie rule's >= to > turns 2 client tests red": confirmed.** In a copy I changed
  `_past_largest`'s `>=` to `>` and ran the full check. It went FAIL with one finding:
  "client-tests: FAIL 2 failure(s) in 90 tests". The unmutated copy passes.
- **"Every fixture's bytes are unchanged apart from the two halfway fixtures and the manifest's order": confirmed.**
  - `git diff --name-only 0eba5e8 70d8834 -- client/tests/fixtures` lists only the two halfway files and
    `manifest.json`.
  - In the manifest, the only change apart from order is one added entry (`exact_halfway_in_exponent_form`,
    bad_json, refused), in `json.fixtures`. The three integer entries only moved. The other top-level keys and
    `json.readers` are identical.
  - The existing halfway entry keeps its code and outcome. Only its bytes changed (`.0` appended).
- **"wire_texts.py's float edges are their own function (the 40-line limit)": true.** The size lint is clean. See
  N1 on what ended up in which function.
- **The other NIT folds** (the W4-N1 comment, the T3-N3 docstring, `CLOSE_WAIT_S`, the NT-1/NT-2/D-N5/D-N6/N-N3/N-N2
  row): each is present in the tree as described. I didn't run `test_godot_net.py` under Godot. The only change
  there is a named constant with the same 5.0 s value.
- **The correction to 5471454's message** matches my delta-4 measurement: 19 digits gives 0 error findings and
  2 failures.
- **The delta-4 reports** in the tree contain no machine path (`git grep` for `/Users/` and `/private/tmp`).

## 2. New findings

No BLOCKER or SHOULD-FIX.

### NIT

- **N1. `scripts/wire_texts.py::_float_edges`.** The docstring says "Floats at a double's edges: both readers agree
  on each one's class (O68)". Two of its entries are integers, not floats:
  - `minus_zero` (`[-0]`)
  - `long_negative_integer` (400 nines)

  Meanwhile the three 2^63 and u64 integers moved to `_number_and_structure_edges`. The split follows line count
  more than responsibility, which CLAUDE.md's size rule forbids ("split along a responsibility, never cut at the
  line count"). The fix is to move both integer entries next to `integer_at_2p63`. The bytes stay the same; only
  the manifest's order changes.
- **N2. `docs/plans/checklists.md`, step 7: the Godot-upgrade re-measure row.** Its trigger is "the upgrade
  branch". But an upgrade branch follows B26's procedure in `docs/standards_backlog.md`, which doesn't mention this
  measurement. Step 7's checklist closes when step 7 ships. So on an upgrade where Godot always holds the packet,
  `test_godot_net.py` stays green and nobody re-measures. `net_client.gd`'s "may drop … (most runs)" would then go
  stale. This is what I asked for in delta 4 ("B26's upgrade checklist should then name the measurement"). It
  belongs in B26's procedure text.

  The row's numbers are also garbled: "0 held in 14 of 16 runs on 4.7.2, 1 in 2". The commit message also cites
  Client's 2 held in 252, which the row omits.
- **N3. `docs/plans/checklists.md`, line 368 of the new "Open NITs" row.** It is 178 characters: the
  NT-2/N-N2 clause wasn't reflowed. Other lines in that file already exceed 120, and no check covers it.

Tools: `<scratchpad>/delta5/executor/tools/gcheck.py` (the full `godot_check.check` on a mutated copy). Runs are in
`<scratchpad>/delta5/executor/runs/` (`base`, `tie`).
