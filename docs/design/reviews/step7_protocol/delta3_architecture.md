# Architecture lens, delta round 3: phase1/protocol (e97727d ... a532695, merged at 87ff10e)

Reader: Architecture. I read CLAUDE.md, docs/code_review.md, delta2_architecture.md, O63 to O67, and the fold's diff
(`git diff e97727d a532695`) of src/, scripts/, client/addons/engine/net/, pyproject.toml, the designs, the decision
record, checklists.md, foundations_plan.md and standards_backlog.md.

What I ran, in a copy of 87ff10e at <scratchpad>/delta3/architecture/tree:
- `replies.text` with its cap check removed: `test_host.py::test_the_server_writes_no_reply_past_the_client_s_text_cap`
  went red. With `>` changed to `>=`, it stayed green (see N-2).
- The merge check: for each of the 34 files that 87ff10e changes against a532695, its +/- lines equal main's own
  change (`d6dcbeb..06c2774`). Only checklists.md and foundations_plan.md were touched by both sides.
- `wc -w` at origin/main (06c2774), e97727d and 87ff10e.

Counts: fold table: 7 fixed, 3 open. New findings: 0 BLOCKER, 0 SHOULD-FIX, 5 NIT.

## Fold table

| # | Status | What I checked |
|---|---|---|
| SF-A | fixed | O67 is its own row, "author, 2026-11-22; awaiting the owner", and its owner section is §9.1. boundaries §9.1 now cites O67, not O63. Nothing on main or any local branch uses O67. One residue: N-1. |
| SF-B | fixed | The one owner is client_rendering §4.3 ("Server text messages are at most 64 KiB"). `replies.MAX_TEXT_BYTES` cites it, and so does `NetSession.MAX_TEXT_BYTES`. The manifest's `LIMITS["max_text_bytes"]` holds Godot's constant to it (test_wire_fixtures.gd:142). All four `send` sites in server.py go through `text()`. Removing the check turned the test red. Residues: N-2, N-3. |
| SF-4 / A6 | fixed | `time_decision` is now in step 7's Remaining list (checklists.md), so A6's trigger ("this step's `time_decision`") names something that will be built. |
| N4 / N-3 | fixed | grammar.py's step 2 now names `integers_only` and `not_int`. |
| N-6 | fixed | The refusal is always a code. The close code is kept separately in `close_code`, and net_client.gd ends with `"closed"`. Residue: N-4. |
| N-a | **open (partly fixed)** | The checklist's C3 line now says the contract fences only imports, and the "step 5a" wording is aligned. But the commit's claim that "pyproject and server.py say" this is false. pyproject's comment still reads as if the contract guards the hand-off, and server.py's docstring and `Dispatch` say nothing about the contract. |
| N-b | **open (partly fixed)** | Only the docstring was fixed ("Four sets"). There are still 13 `as _x` alias imports, `Fixture` is still in wire_texts.py, and the assembler is still 474 lines. |
| N-c | fixed | Renamed to `_check_encodable`. |
| N-d | **open** | `server_rules(read, protocol, versioned: bool)` is unchanged: the boolean is still there, and so are the typed-cast precondition and the versioned-type knowledge in NetSession. The commit message lists N-d nowhere, neither as folded nor as open. |
| N-e | fixed (answered) | Wire SF-1's line answers it: a float's value is not part of the contract, and only its class is. The hand-rolled code stays to keep the class (finite or not) equal at the largest double. The exact-halfway fixtures hold that, and both §9.1 and `_double`'s comment say so. I accept this. |

Unchanged and still accepted: N1, N5 (deferred), and A7, A8, C3.

## Requested checks

- **O67's row and citation:** sound, apart from the status column (N-1).
- **replies.text and the cap's one owner:** one contract statement (client_rendering §4.3), one Python constant and one
  Godot constant, with the manifest holding the two constants together. The server and the client use the same
  comparison (`>` the cap is refused).
- **Checklist triggers:** A6 now names `time_decision`, which the step builds. The three new deferrals each name
  something that exists in the plan:
  - U+1D159 → `phase1/agents`;
  - the 65th packet → step 8's live client;
  - the `index()` axis orders → step 8's `CellSnapshot`.

  I accept all three.
- **Word budgets against origin/main (06c2774):**

  | Document | origin/main | 87ff10e |
  |---|---|---|
  | boundaries.md | 10748 | 10748 |
  | client_rendering.md | 3740 | 3736 |
  | tile_and_client.md | 5408 | 5386 |
  | world_v2.md | 5452 | 5404 |
  | foundations_plan.md (plan, at most 2500) | 2498 | 2489 |

  None of them grew. The fold itself added 1 word to boundaries.md (10747 → 10748) and 9 to client_rendering.md
  (3727 → 3736), and both stay at or under main. Executor S3's rejection stands.
- **The 87ff10e merge's foundations_plan.md:** resolved correctly. Main's row 6 ("after 5a and `subcell_solids.md`
  S0"), OD-I13, the O57 and O46 relabels and D36–D37 are all present, and so is the branch's row 7 with O67. The
  merge changes nothing of this branch's: every merged file's diff equals main's own change.

## New findings (all NIT)

- **N-1** decisions/boundaries.md O67: the status column reads `live` while the ruling text says "awaiting the owner".
  A reader who filters the record by status sees a ratified ruling. Use a pending status until the owner rules.
- **N-2** `replies.text` and test_host.py's cap test:
  - The test's message is 65,536 characters of padding plus its envelope, well past the cap, so an off-by-one (`>=`)
    passes it. I ran that mutation and it stayed green. Add a reply of exactly `MAX_TEXT_BYTES` bytes, which must
    pass.
  - `len(out)` counts characters and equals bytes only because `encode` sets `ensure_ascii=True`. Say so, or measure
    `len(out.encode())`.
- **N-3** checklists.md step 7: the text cap is enforced only at run time. If a `tick` or a `welcome` at the world
  limits exceeds it, `text()` raises inside `_serve`, the session closes with 1011, and the client sees only
  `"closed"`. The frame side has its join-time bound at the world limits (3.5 MiB). The text side has no matching
  test-to-write, "tick and welcome at the world limits fit `MAX_TEXT_BYTES`", next to the `tick` and `regions` items.
- **N-4** Stale text:
  - server.py's docstring says the replies, `intent_result` among them, "join with this step's `intent_result`", which
    is circular.
  - test_net_session.gd:77 still ends a session with `"closed 1000"`, the retired form.
  - `"closed"` is a client-only code that isn't in `refusals.py`'s vocabulary, so the `CODE` shape is held by
    convention, not by `NetSession.end`.
- **N-5** Commit a532695's accounting overstates two items and omits one:
  - N-a, said to be fixed in pyproject and server.py;
  - N-b, listed as folded although one of its four parts was;
  - N-d, missing from the message entirely.

  The fold-table rule exists for exactly this.
