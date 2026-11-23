# Trust boundary, delta round 4: phase1/protocol (87ff10e ... 5471454, merged at 0eba5e8)

Lens: Trust boundary. I reviewed the committed tree at 0eba5e8, unpacked with `git archive` into
`<scratchpad>/delta4/trust/wt`. The merge (`git diff 5471454 0eba5e8`) only repoints Known-gap links to
`docs/known_gaps.md` and touches none of this branch's protocol, text, host or client files. Probe:
`<scratchpad>/delta4/trust/run.py`. With the committed code, `tests/test_text.py` and `tests/test_host.py` give 105 passed.

Counts: fold table **3 fixed, 2 deferred (accepted), 4 open, 0 rejected**. New: **0 BLOCKER, 1 SHOULD-FIX, 1 NIT.**

## Fold table (status read from the tree)

| Id | Status | What I checked |
|---|---|---|
| T3-S1 zero-width blank untested | **fixed** | `HIDDEN` holds `"a\U00016fe4b"`. Mutation `zero_width_blank = False` in the scratch copy: **1 failed, 61 passed**, and the failure is the new case. Restored: it passes. |
| T3-N1 `close_code` unread | **fixed** | The field and its write are gone. `grep close_code client/` finds nothing, and the unit test now ends with `"closed"`. This is a removal, so there was nothing to mutate. |
| T3-N2 alternating spacing channel | **deferred, accepted (reason and trigger)** | `checklists.md` step 7 lists it "for the owner" with the trigger "the first guest text an NPC reads". The row misstates the channel's size, though: see T4-S1. |
| N-N2 U+1D159 | **deferred, accepted** | Unchanged from delta 3. |
| T3-N3 blank symbols refused alone | **open** | Not addressed and not mentioned in the commit. `text.py::_blank`'s docstring still says the gap fillers "keep working". That holds only inside other text. |
| N-N3 code shape vs `RefusalCode` | **open** | Not addressed. It is missing from the commit's "Open" list for the second round running, so it is not tracked anywhere. |
| D-N5 fuzz reach | **open** | Listed open in the commit. No checklist or backlog row records it. |
| D-N6 `bad_version` field | **open** | Listed open in the commit. `_check_protocol` is unchanged. |

### The oversized-reply host test (Executor SF2, delta-3 caveat of mine)
`test_a_reply_past_the_cap_ends_that_session_and_frees_its_token` is real. I swapped `server.py::_answer`'s send site
from `text(...)` to `strict_json.encode(...)` in the scratch copy: the test went **red** (1 failed), and the restored
copy passes. The 1011 path does not leak content. The `ValueError` names only the type and the size, and an
exception in the handler cannot reach another session. The at-the-cap and one-past-the-cap assertions in
`test_the_server_writes_no_reply_past_the_client_s_text_cap` are byte-exact under `ensure_ascii`.

## New findings

### T4-S1 (SHOULD-FIX). The owner's record understates the spacing channel by orders of magnitude
`docs/plans/checklists.md`, step 7 deferrals, the row "Guest text's hidden channels the rulings leave open, for the
owner".

The row says each channel carries "a bit or two per visible character". For the variation-selector and joiner
channel that holds, because each needs its own visible neighbour. The spacing channel has no such bound.
`run.py` sweeps every code point and finds **28** characters that `player_text` refuses alone ("draws nothing") but
accepts in a run of any length between two visible characters. They are U+0020, U+00A0, U+1680, U+2000–U+200A,
U+202F, U+205F, U+3000, U+2422, U+2800, U+A8F9, U+10AF6, U+1144E, U+11945, U+11C44, U+11C45, U+11F48, U+13441 and
U+13442. `"hi"` + 496 characters alternating U+2009/U+200A + `"!"` is accepted at `max_chars=500`. Drawing from all
28 gives about log2(28) ≈ 4.8 bits per character, so about 2,390 hidden bits ride on three visible characters. That
is roughly 800 bits per visible character, not "a bit or two". Even U+0020 against U+00A0 alone gives one bit per
character in a run.

Failure scenario: the owner reads the row to decide whether this residual can wait until NPCs read guest text. Sized
as "a bit or two per visible character", it looks negligible. Sized truthfully, one guest line can carry a ~300-byte
covert payload into an NPC's prompt, and the ruling (for example, folding every run of spacing characters to one
U+0020) may be made on the wrong number.

Fix (unverified as wording; the numbers are verified by `run.py`): restate the row with the bound per spacing
character (the 28 characters, about 4.8 bits each, unlimited run length within `max_chars`), and keep the selector
and joiner channel's per-visible-character bound separate.

### NIT
- **T4-N1** `tests/test_host.py::test_a_reply_past_the_cap_ends_that_session_and_frees_its_token`: on the mutant
  it fails by an asyncio `TimeoutError` after about 10 s (`WAIT_S`), not by an assertion. Red is red, but the
  failure doesn't name the broken guard. Bounding `_closed` (or the oversized `recv`) with its own short wait and an
  assertion message would make the failure say what broke.
