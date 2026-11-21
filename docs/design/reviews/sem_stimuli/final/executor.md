# Executor, final round: `docs/design/sem_stimuli.md` v4 (diff `0918685..aa6bd1b`)

**Read at:** Overdrive `phase1/sem-stimulus` **aa6bd1b** (the diff only, plus the files it cites); Maxim by
`git show origin/main:` at **043eab8f**, not fetched, no working tree read. Inputs: my delta-2 report, `delta2/fold.md`,
v4 §10. Nothing was run except reads. Every fix proposed below is **unverified** unless it says otherwise.

## Status of my delta-2 findings

| Id | Status | Reason (read from the tree) |
|---|---|---|
| X1 | fixed | §4.4: the expected value is recorded at each push and compared **before the next push**, a window covering the body step and cognition. Checklist (agents): the plant is a stub modulator writing during cognition |
| X5 | fixed | §4.1: the false §9 citation is gone, the contract sets `L_us ≥ 1`, refused at 0; checklist (agents) plants `L_us = 0` |
| Y1 | fixed | §4.6: T16a asserts per-tick values in the stub push log (red under D14, since no push happens off cognition ticks); T16b is a future bar; both land with the contact law as `xfail(strict=True, raises=AssertionError)`; the Known gap restates the measurement (5.7–10.8 K, 43.2 °C peak). §11.1 still lists T16a in the agents row (N-F3) |
| Y2 | fixed | §4.4: the record is the pushed value clamped to the declared range; a bite is counted, not a failure |
| Y3 | fixed | §7.1, §11.1: `wire.py` holds `BoundFrame`, `StimulusEvent`, `Receipt` and the binding-table data, and lands in `phase1/agents` before the codec. The fold introduced a new ordering defect for binding validation (S-F2) |
| Y4 | fixed | §7.3: `wire.py` imports only `checks` and numpy; a grimp closure test over `AGENTS_SURFACE`, planted with `readonly`. I checked the surface today: `intents` imports `checks` and `limits`, `limits` imports `checks`, `checks` imports numpy and stdlib, so the surface is closed as stated |
| Y5 | fixed | checklist 5a: the order plant runs on one-sided exposure and first asserts the permuted values differ. Placed in the wrong step (S-F4) |
| Y6 | fixed | §4.1 and checklist (agents): replies held and released at host hooks (before step 6, a test-only hook inside it, after the join) in two fixed orders; no wall timing |
| Y7 | fixed | §5: lanes hash after the row's rounding; the plant moves a digested value by at least one quantum. The checklist's parenthetical numbers are pre-rounding (N-F5) |
| Y8 | fixed | §3.3, §4.4: `world_owned_sensors` is the bound set; checklist: `live_world_set_sensors` equals it, an anonymous write returns `False`, planted with an empty tuple. `bootstrap.py:552-561` read at origin/main: the set is filled only under `if modulator_factory is not None`, which M18 already asks |
| Y9 | fixed | the sentence left the design; the checklist states 5.1–5.5% per 0.1 K under L3's constant |
| N3 | deferred (carried) | trigger Q1, still in §11.2 |

**Counts:** 11 fixed, 1 deferred (carried), 0 rejected, 0 open. The fold proposes no deferral or rejection in the
Executor rows, so I have nothing to rule on.

## New findings in the diff

**0 BLOCKER, 6 SHOULD-FIX, 5 NIT.**

### S-F1 (SHOULD-FIX). `sem_stimuli.md::"Bars"` and `§6.3`: "each gate's plant is in the checklist" is false for eleven gates

**What is true.** v4 adds: "Each gate's plant is in the checklist", and §6.3 still says "Each is first shown red on a
planted leak". The checklist names T11 once and T13 once, and no other gate. The design table gives plants or controls
only for T3 (a control), T9, T11 and T12. T1, T4, T5, T6, T7, T8, T10, T14 and T15 have no plant anywhere. v3 had the
same table, but v3 didn't claim the checklist held the plants, and v4's split moved test mechanics out of the design on
the basis that the checklist holds them.
**Failure scenario.** The tissue-PR engineer writes T5 ("identical streams before any thermal event") on a scene where
no model reads any material field. It is green whether or not the leak exists, and nothing tells them otherwise. T4
on a wall with no hazard behind it is the same. These are tests that can't fail, waiting to be written.
**Fix.** A checklist item, with the tissue row, giving each gate's plant: for example, T5 with a model that reads
the combustion constant, T4 with a march that ignores the wall, T8 with a sensor range computed from the scene. A
law-level detail, so the checklist is the right home. **The checklist doesn't hold it today.**

### S-F2 (SHOULD-FIX). `sem_stimuli.md::§3.2, §11.1, §7.3`: binding validation lands before the module that holds it

**What is true.** §3.2: the table's data is in `wire.py`; "its validation against the body is in `schema.py`" (the row
exists; sites lie in its site set). §11.1 puts "`stimuli/wire.py` and binding validation" in `phase1/agents`, and
`schema.py` in the tissue row. The checklist's agent half repeats "binding validation land[s] here". The order is
5a → 5b → 7 → the agent line (`foundations_plan.md:31-42`) → the tissue row, so in `phase1/agents` there is no
`schema.py` and no row registry to check "the row exists" against. Separately, §7.3's "adapters' reach" row adds
`stimuli.wire` and `stimuli.schema` to `CORE_PUBLIC_SURFACE` "at 5b", before either module exists. The checklist's 5b item
adds only `body.spec`.
**Failure scenario.** The agents engineer has to put validation somewhere: in `wire.py` (breaking its leaf rule and
the closure test), in the adapter (outside the core, so replay's "same gate" isn't the same gate), or in an early
`schema.py` that the tissue PR then rewrites. At 5b, a surface entry naming a nonexistent module either fails "every
allowed importer exists" or is silently skipped, depending on which test is extended.
**Fix.** Either move `schema.py`'s row and site-set vocabulary, with binding validation, into `phase1/agents` and leave
only the `StimulusModel` protocol to the tissue row, or move binding validation and its refusal test to the tissue
row and say what `phase1/agents` validates against (a stub registry is a band-aid unless it's marked). Make §7.3's
"Lands" column match: each surface module joins with its module's step.

### S-F3 (SHOULD-FIX). `sem_stimuli.md::§5 bound lane` vs `§4.1 step 4`, `§4.2`: what the bound lane hashes per tick is undefined

**What is true.** Step 4 builds, reduces and digests "every body's frames" every tick. §4.2 says a `BoundFrame` "is
assembled at delivery", concatenating undelivered ticks' events and receipts. §6.2 puts a receipt "in the first
`BoundFrame` delivered after its intent applies". §5's bound lane chains "per tick" over "`BoundFrame` values and
receipts". Under D14, delivery happens at the cognition rate, so on most ticks there is no delivered `BoundFrame`.
**Failure scenario.** Engineer A hashes the delivered frame: on non-delivery ticks the lane has no entry, the
lane depends on the cognition divisor (which nothing says is in the lane key or the header), and replay, which runs no
agents, must reconstruct delivery ticks it may not know. Engineer B hashes a per-tick frame with that tick's
receipts: the lane no longer covers what crosses the channel. The 5a order plant ("first differing tick named by the
lanes") behaves differently under A and B. T16a's reference, "that tick's `BoundFrame` value", has the same
ambiguity.
**Fix.** State it in the contract: the bound lane hashes, every tick, the reduced values in binding order plus the
receipts produced that tick, independent of delivery, and T9 holds delivery to it. Or key the lane by the delivery
divisor and put the divisor in the header.

### S-F4 (SHOULD-FIX). `checklists.md::Step 5a "Digest plants"`: plants that need later code are listed in 5a

**What is true.** The 5a item lists "a surface-conductance change …", "an order reversal in `reduce.py` … on one-sided
exposure" and "a producer's version bumped alone, a bound home refused". By §11.1, `reduce.py`, the tissue law and the
bound home (an agent home with bound lane keys) land in the tissue row and the agent line. 5a only reserves the lanes.
**Failure scenario.** The 5a reviewer marks the item undone, or the 5a engineer writes the plants against a stub
`reduce.py` and a fake law. Those plants then prove the stub's lanes, not the real reduction's, and nobody rewrites
them when the real code lands.
**Fix.** Keep in 5a what 5a can plant: lane chaining, the per-tick first-differing-tick report and the producer
key, all planted on a toy row. Move the three listed plants to the tissue row (and the bound-home refusal to the
agent line or the save item).

### S-F5 (SHOULD-FIX). `sem_stimuli.md::§4.4 threads`, `§6.3 T9`, `§2.3 S4 gates`: Y1(b)'s lesson applied to T16 only

**What is true.** The author verified (fold, "Y1(b)") that a strict xfail without `raises=` reports a missing module as
"xfailed". `tests/test_tooling_config.py::test_red_gates_are_strict_and_warnings_are_errors` checks only
`xfail_strict`. v4 adds `raises=AssertionError` to T16a and T16b, but the other strict red gates the diff names don't
have it: the real-Maxim thread test "strict red until [OD-EA7] lands", T9's worker half "strict red until M6, M8", and the
face-contact and face-emission gates (§2.3, S4).
**Failure scenario.** The real-Maxim thread test imports an embedded-build entry point that a pymaxim release renames.
The test raises `ImportError`, reports "xfailed", stays green, and stays green after OD-EA7 lands, because it never
reaches the assertion. The gate meant to flip never flips.
**Fix.** The contract's rule: every strict red gate states `raises=` (the narrowest expected type). A tooling test
should require `raises=` on every `xfail` marker: an AST scan that fails on an `xfail` with no `raises=`. Unverified.
This is a standards-level rule, so it may belong in `docs/standards_backlog.md`. Nothing holds it today.

### S-F6 (SHOULD-FIX). `sem_stimuli.md::§4.2, §4.3` vs `§6.3 T9`: "nothing is lost at any divisor" contradicts coalescing, and T9 goes red on it

**What is true.** §4.2: delivery concatenates undelivered ticks' events and receipts "under the byte budget, so nothing
is lost at any divisor". §4.3: overflow "coalesces by `(kind, site)` into count and peak", which loses events. T9
requires event and receipt content "equal as a multiset over a common window" at divisors 1–50. At divisor 50 a frame
carries 50 ticks of events against the same budget, so it coalesces where divisor 1 doesn't. Nothing says what
happens to receipts over budget: they have no `(kind, site)` to coalesce by.
**Failure scenario.** Sound lands and a scene has a steady stream of footsteps. T9 at divisor 50 coalesces, and the
multisets differ. T9 goes red for no defect, and the obvious "fix" is to drop the high divisors or loosen the
comparison. v1 is safe only because `events` is empty.
**Fix.** Pick one: the budget applies per tick (so concatenation never coalesces more than divisor 1 does), or T9's
event comparison carries a precondition that no frame in the window coalesced, with coalescing tested on its own.
State receipts' overflow rule (refused at start by sizing, or never coalesced). Delete "nothing is lost".

### NITs

- **N-F1. `sem_stimuli.md::§4.4 "The body step"` vs `§4.6`.** §4.4 says the host steps the body "on other ticks"; D14
  says the body step runs at the cognition rate. The `phase1/agents` engineer works under D14, so they have to infer
  that the host never steps the body. Say "(under D14, never; §4.6)".
- **N-F2. `checklists.md::"The core"` and `tile_and_client.md:140`.** The owner ruled (a), but the item still offers
  "(a) … or (b) free …". Its test, "an idle NPC for one world hour", gives no assertion and no plant, and under (a)
  a held core is trivially at 37 °C. Say what it asserts (for example, the `bodies` ledger closes with the booked basal power)
  and plant it (drop the booked power, and the ledger residual goes red). Also, 5b builds "the core node" (§11.1), but tile's
  relaxation test is now superseded for the core, so 5b has no core test until the tissue row. Name the test 5b
  writes.
- **N-F3. `sem_stimuli.md::§11.1` agents row, `§4.6`.** The row lists "T16a and D14's Known gap", but T16a lands with the
  contact law (the tissue row). The Known gap is entered with `phase1/agents`' code, so between the two steps it
  has no gate (no stimulus exists yet either, so the gap is harmless then). Move T16a to the tissue row.
- **N-F4. `long_term_features.md` SEM Status/Next.** It says "D15 (receipt kinds) open", "Ruled D1–D14 and S4" and
  "Next: The owner's D15". §10 records D15, D12's trade and PH2-S2 as ruled.
- **N-F5. `checklists.md::Step 5a "Digest plants"`.** "(measured: 10⁻¹² relative moves a node at tick 0 …)" was measured
  before rounding. With lanes hashed after rounding (Y7's fix), those numbers don't describe the plant. Mark them
  pre-rounding, or drop them.

## Checked and true

- Design 5,982 words (v3 5,997): it didn't grow. `tile_and_client.md` 5,977 (was 5,985).
- Maxim at origin/main 043eab8f: `tool_bridge.py:548-560` (the live, self-effect and drive sets);
  `bootstrap.py:552-561` (`world_owned_sensors` fills `live_world_set_sensors`, only with a `modulator_factory`);
  `memory_hub.py:58-77` (the `MAXIM_ENABLE_BODY_STATE_PROMPT` gate); `loop_perception.py:265-276` (auto-sense, the
  "without choosing to call tools" text the fold re-cited).
- `AGENTS_SURFACE` closure on today's tree (Y4 row).
