# Final round: SEM stimuli v4, Determinism, replay and performance lens

Scope: `git diff 0918685..aa6bd1b` on `phase1/sem-stimulus` (v4 `sem_stimuli.md`, `delta2/fold.md`, the checklist
items, §10's rulings). Inputs: my delta-2 report, the fold table, §10. Scripts: I reran
`_durable/sem_review_delta2/scratch_determinism_performance/refresh_cap2.py`. It reproduces: a shared K = 116 changes
A's refresh log when 9 others run, and a per-body k = 12 doesn't. I also wrote `scratch_determinism_performance/final_checks.py`
(pure Python, seeded). No Maxim claim falls in this lens's part of the diff, so I read nothing in Maxim.

## Status of my delta-2 findings (reviewer-set, read from the tree)

| Id | Status | Reason |
|---|---|---|
| DP3-B1 | **fixed** | §7.2: "No budget is shared across bodies: any cap … is per body and per emitter, from that body's own state." T11 adds the shared-budget plant. §8: D12 is measured on one body. §10 records the owner accepting the no-pooling trade. Rerun reproduces. The plant's fixture is underspecified: new **F-S4** |
| DP3-S1 | **fixed** | Checklist "Refresh schedule": one total order from saved state, and the starvation measurement recorded. One of its keys is vestigial: **F-N2** |
| DP3-S2 | **fixed** | The per-emitter cap removes the staleness doubling. Staleness per pair is now ⌈58/k⌉ whatever E is. §8 measures D12 at the maximum emitter count. Two leftovers: what happens above that maximum is undefined (new **F-S3**), and the "motion trigger is inert at the floor" sentence is missing (**F-N3**) |
| DP3-S3 | **fixed** | §7.2: a component is "the patches sharing object-side sub-mesh nodes within the tick, never an object, with its own termination and substeps". T11 adds "B on the same floor object". The same edit dropped v3's "canonical order": new **F-S1** |
| DP3-N1 | **fixed** | §4.1 now has host hooks, two fixed orders, no wall timing, a cell-writing intent, and the replay leg named. The checklist has the hook points and the toy result. The pass condition was lost in the cut: **F-N4** |
| DP3-N2 | **fixed** | §5 has an events lane per NPC over `BodyFrame.events`. The checklist 5a item reserves it |
| DP3-N3 | **fixed** | §4.3: the byte budget is a header truth constant, and start is refused unless it is below the measured buffer. §5's header lists it |
| DP3-N4 | **fixed** | The checklist cost table says "~11–14 ms on this basis" |
| DP3-N5 | **fixed** | §7.2: "A point's flux sums emitters in stable-key order." T11 adds the plant. The key is undefined, and the plant can be vacuous: **F-S4**, **F-N1** |

Counts: 9 fixed, 0 deferred, 0 rejected, 0 open. The fold proposed no deferral for this lens, so I have none to rule on.
Concurrency F2's deferral, which I accepted in delta 2, stands as §4.6 words it.

## New findings (diff only)

### F-S1 (SHOULD-FIX). v4 dropped "in canonical order" from the contact contract, and the component order now decides float sums into the solid

`sem_stimuli.md::7.2` ("A contact component is the patches sharing object-side sub-mesh nodes … with its own
termination and substeps"). v3 read "contact solves per connected component … in canonical order". `::7.1` says
contact writes "the object through the solid law's exchange API".

Components are now finer (by node, not by object). That makes it more likely that two components on one object
deposit into the same solid cell in one tick. Float accumulation into that cell depends on the order the components
are solved. The diff removed the only sentence that fixed that order, and the checklist ("Contact … `contact.py`
composes tissue's operator on one grid per component") doesn't restore it.

**Failure scenario.** A and B each rest a palm on one 0.1 m floor cell, 5 cm apart. Their sub-meshes are refined to
millimetres, so they share no node: two components. Both exchange heat into that cell in step 3. The live run
iterates components in contact-onset order. A save and load rebuilds the component map keyed by `npc_key` and
iterates B first. The cell's energy differs by an ulp, and so does every later bit. §5's "a save anywhere reloads
bit-identical" fails, and nothing in the contract says which order was right. The checklist doesn't hold it.

**Fix (unverified, no script):** restore a canonical order in §7.2, for example by each component's smallest
(object id, sub-mesh node id) or `npc_key`. Then cover it with the existing save–load test, with two components on one
cell.

### F-S2 (SHOULD-FIX). Coalescing at the per-frame byte budget is divisor-dependent, so §4.2's "nothing is lost at any divisor" is false and T9's multiset clause goes red on correct code

`sem_stimuli.md::4.2` ("concatenating the undelivered ticks' events and receipts under the byte budget, so nothing
is lost at any divisor"), against `::4.3` ("Events are capped per delivered frame … overflow coalesces by `(kind,
site)` into count and peak") and `::6.3` T9 ("`BoundFrame` event and receipt content equal as a multiset over a
common window", divisors 1–50). All three sentences are new or rewritten in this diff.

The budget applies per delivered frame. A frame at divisor 50 concatenates 50 ticks, so the same event stream
overflows at high divisors and not at low ones. Coalescing replaces events with `(count, peak)`, and that is a loss.

- **Measured** (`final_checks.py`): 3 events per tick of 40 B, a 400 B budget. Divisor 1 delivers 300 events, none
  coalesced. Divisor 50 delivers 4 coalesced records. The multisets are unequal (`False`).
- **Receipts.** §4.2 puts them "under the byte budget", but coalescing keys on `(kind, site)` and a receipt
  `(pid, kind)` has no site. Either receipts are exempt, which the contract doesn't say, or an overflow drops pids. A
  dropped pid is an agent never told its intent was refused. Receipts exist in v1, and so does D14's divisor 10.
- **Digest coverage.** §5's bound lane covers "`BoundFrame` values and receipts", not `BoundFrame.events`, and the
  events lane covers `BodyFrame.events`, which are pre-coalescing. So a coalescing bug in `events.py` changes what the
  agent receives, and no lane digests it.

**Failure scenario.** Sound lands. A crowd scene at a dilated dial runs divisor 20. T9, frozen as contract, goes red
on correct coalescing. The cheap response is to narrow T9's window or tolerance, which is the loosened-test pattern.

**Severity.** This is a contract contradiction. It is SHOULD-FIX rather than BLOCKER only because v1 has no event
producer, a gate holds `events` empty, and receipt overflow is unlikely at v1 rates. It must be settled before the
`phase1/agents` codec fixtures freeze. The checklist doesn't hold it.

**Fix options (unverified):** coalesce per tick against a per-tick budget, which is divisor-independent, and then
concatenate, stating the delivered frame's bound as divisor × budget; or keep a per-frame budget, delete "nothing is
lost", and make T9 compare pre-coalescing content. In either case say whether receipts count, and digest the
coalesced events (add them to the bound lane).

### F-S3 (SHOULD-FIX). "The scene's maximum emitter count" is a header constant for a quantity fire spread makes dynamic, with no defined behaviour when it is exceeded

`sem_stimuli.md::8` ("at the scene's maximum emitter count"); checklist "Refresh schedule" ("The header records the
maximum emitter count"); `::5`'s header list doesn't name it; `::7.2` ("emitters append to `radiant_emitters`").

Per-emitter caps make cost 10·N·E·k·c, linear in E. Emitters are appended by fire at runtime, so E isn't known at
start. The contract doesn't say whether exceeding the header's maximum refuses, clusters emitters down to it, or
proceeds. Two implementations can pick differently, and the first two change values, so this is part of the contract.

**Failure scenario.** The header declares 2 emitters. A market fire spreads to 6 burning surfaces. The visibility row
goes from ~73–90 to ~440–540 ms per world second against a ~140 ms target. D12 was re-ruled on a measurement at
E = 2, so the ruling's basis no longer holds, and no gate notices: the counter thresholds are per-emitter, or not set
yet. **Fix (unverified):** name the slot in §5's header list and in 5a's reservation, and state the rule above the
maximum in the contract. If the rule is clustering, it is a law parameter with its error stated.

### F-S4 (SHOULD-FIX). Two new T11 plants go green under natural fixtures, so as listed they can fail to fail

`sem_stimuli.md::6.3` T11 plants "a refresh budget shared across bodies (red when B runs, **D**)" and "emitters summed
in append order". The checklist gives neither a fixture.

- **Append order.** IEEE addition is commutative, so with two emitters every order gives the same bits.
  `final_checks.py`: two emitters, 0 of 100,000 draws differ; three emitters, 36,200 of 100,000 differ for some
  permutation. A plant fixture with one or two flames, which is the natural fire scene, cannot go red.
- **Shared budget.** My rerun of `refresh_cap2.py` at K = 116 shows that a *single* running B joining leaves A's log
  unchanged (`True`). It goes red only when 9 others run, or when K is below demand (K = 90). "Red when B runs", built
  with one B at the one-emitter floor, stays green.

**Fix (verified for the numbers above by the two scripts; the fixture wording is unverified):** in the checklist,
require ≥ 3 emitters with nonzero flux at A, and a crowd or K below demand for the budget plant. Each plant asserts
first that its permutation changes the planted computation's output, in the pattern of Y5's "asserting first that the
permuted values differ". The same applies to "B on the same floor object": B's patch must drive the merged
component's substep count above A's own. That one is unverified.

### F-N1 (NIT). The "stable key" for emitters is undefined

`sem_stimuli.md::7.2`, `::7.1` (`radiant_emitters`, a 5a seam). The table's rows (research L7: position, area,
temperature, emissivity) carry no id. If the key is the row index, "stable-key order" is append order, and DP3-N5's
rule does nothing. Name the key in the 5a seam, for example (writer law, source object id, primitive id). The same
key orders the refresh ranking.

### F-N2 (NIT). "Body sort position" in the refresh order key varies with B's membership

Checklist "Refresh schedule": (last refresh tick, body sort position, point id, emitter key). Under a cap per body and
per emitter, the body and the emitter are constant within each ranked set, so this is harmless today. But A's sort
position shifts when B joins, so the key carries exactly the cross-body dependency DP3-B1 removed, and it is waiting
to bite if the ranking is ever pooled. Drop it: (last refresh tick, point id) within a body and an emitter.

### F-N3 (NIT). k = 12 is the stationary floor, so the motion trigger buys a runner nothing

A body's stationary demand is 58 / 5 = 11.6 pairs per tick per emitter. At k = 12 a runner's 58 always-due pairs refresh
once every 5 ticks: once per physics step, the v2 behaviour. The checklist's "as a shared K = 116 did" implies this
but doesn't say it. Say it, so D12's re-ruling knows that any gain over v2 needs k > 12.

### F-N4 (NIT). The overlap gate's pass condition was cut

`sem_stimuli.md::4.1`. v3 said that "digests and record stream must match" across the live legs and replay. v4 names
only the red leg, and the checklist item is the same. State the green assertion: every leg's lanes and record stream
are equal. Without it, an implementation that compares only the replay leg passes a leak that only the on/off leg
sees.

## Checked, no finding

- **Delivery schedule.** The divisor is an integer per-actor rate with a phase, from data (`boundaries.md` §6, the
  rates rule), so the boundaries of delivered frames are deterministic.
- **Merge order.** The pump's arrival stamps don't order merges ("arrival never orders", `npcs_and_sem.md` §9 table).
  The new queue hand-off (§4.1) keeps that.
- **D12 on one body.** This is valid under a cap per body and per emitter: staleness is a function of the body's own
  state (rerun).
- **T16 and D14.** Tissue and frames still run every tick, so T9's `BodyFrame` identity holds under D14.
- **The byte-budget refusal at start** reads the host's socket only to refuse. It never changes a value, and replay
  opens no socket.

## Counts

Delta-2 findings: 9 fixed, 0 deferred, 0 rejected, 0 open. New: 0 BLOCKER, 4 SHOULD-FIX (F-S1 through F-S4), 4 NIT
(F-N1 through F-N4). The checklist holds none of the new ones. F-S2 must be settled before the agent line's codec
fixtures freeze.
