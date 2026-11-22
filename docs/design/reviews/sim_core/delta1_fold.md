**The owner accepted the stop on 2026-11-21:** no design round follows this fold. Every status below is set by 5a's
code reviewers, reading the tree; the author sets none (O25).

# Fold of step 5a's delta round 1 into `sim_core.md`

**Inputs:** the four delta reports (`delta1_exec_physics.md`, `delta1_wire_det.md`, `delta1_arch_bio.md`,
`delta1_perf.md`), reviewing `3b5937b..99917fb`. New findings: 5 BLOCKER, 23 SHOULD-FIX, 19 NIT. The open round-1 rows
they name are listed too.

**The four contract blockers, as folded:**
1. **Where a strike's load resolves** (X-B1 delta, N-B2, DA-S1). `damage.loads` has cadence `per_record`, run right
   after each record's stage 2 in the apply phase (§5). `per_tick` is sem §4.1's step 3, for the body laws. A
   topology batch is one requester's one invocation, so a strike bumps `topology_version` once (§5.1).
2. **The per-tick source rule's state** (X-B2 delta, N-S1). `source_exposure` is a declared input (§2, §3, §6):
   each live value's effective tick, plus the interval's closed segments. Douse and replacement take effect per tick.
   It is digested (§9 member 3) and saved, and cleared each physics step.
3. **The digest's byte form** (N-B1, Perf S1). `sha256/raw-1` is two-level: member digests, then a combine over name,
   `dtype.str`, ndim, shape and member digest. Strings are a u64 length plus UTF-8, integers u64 little-endian, and
   record members have explicit row bytes. Source keys are hashed. Member digests are seeded at construction and on
   load (§9).
4. **"All heat input resolves in heat"** (DA-B1). It is now "one resolver per input kind", asserted over the
   registry. `temperature` has declared, ordered writers (heat, then the solid, contact, skin and bed laws as they
   land), and all damage resolving in damage is one instance of the rule (§5.1, §6). CLAUDE.md and B40 are reworded.

**Measured or verified by the author:** each contract fix was checked against the text it touches. Nothing was rerun:
no fix in this fold rests on a new measurement. Performance's corrected figures are quoted from its report.

**Also corrected:** two rows of `fold.md` claimed `boundaries.md` §4.2 had been amended; that edit was reverted in
1270564 (A-B3, Perf P6).

## Executor and Physics (`delta1_exec_physics.md`)

| Id | Where it went | Status |
|---|---|---|
| B1 | §5 `per_record` cadence; §5.1 strikes; checklist §5 (two strikes, one tick) | open (for the reviewer, on 5a's code PR) |
| B2 | §3 rule and `source_exposure`; §6 inputs; §9 member 3; checklist §3 (douse, re-ignite, save mid-interval) | open (for the reviewer, on 5a's code PR) |
| S1 | §7: region reductions keyed on `topology_version` and the write tick of each field read; checklist §7 | open (for the reviewer, on 5a's code PR) |
| S2 | §5.1: a batch is one requester's one invocation | open (for the reviewer, on 5a's code PR) |
| S3 | §13: a submit-and-step port the test or host owns; interim rules stated; marker reason rewritten; checklist §13 adds the membrane line | open (for the reviewer, on 5a's code PR) |
| S4 | §4 links tile §4 (refusal-only ticks publish); checklist §4 cites tile §4's cases; `fold.md` A-B3 corrected | open (for the reviewer, on 5a's code PR) |
| N1 | §5.1: `integrity`'s writers are `damage.loads`, `damage.thermal` and `Topology` | open (for the reviewer, on 5a's code PR) |
| N2 | §11 bar 3: reversal within each cadence group | open (for the reviewer, on 5a's code PR) |
| N3 | checklist: the deferral says owner-ruled, not "to confirm" | open (for the reviewer, on 5a's code PR) |
| N4 | checklist §13: `boundaries.md` §6.4's rows follow §6's writer roles in 5a's PR | open (for the reviewer, on 5a's code PR) |
| N5 | §11 bar 5: today's `heat.step` and damage callback, frozen as test fixtures | open (for the reviewer, on 5a's code PR) |
| X-S9 (round 1, open) | as N5 | open (for the reviewer, on 5a's code PR) |
| P-S2 (round 1, open) | as B2 | open (for the reviewer, on 5a's code PR) |

## Wire integrity and Determinism (`delta1_wire_det.md`)

| Id | Where it went | Status |
|---|---|---|
| N-B1 | §9 two-level scheme and byte form; checklist §9 golden bytes and key-only test | open (for the reviewer, on 5a's code PR) |
| N-B2 | §5 cadences and group order; §5.1 batch and per-record resolution | open (for the reviewer, on 5a's code PR) |
| N-S1 | §3 and `source_exposure` (see blocker 2) | open (for the reviewer, on 5a's code PR) |
| N-S2 | `tile_and_client.md` §3.1 amended: `ignite` (v0) ranks 3, host commands 4; checklist §14 | open (for the reviewer, on 5a's code PR) |
| N-S3 | §4 links tile §4; checklist §4; `boundaries.md` §4.2's copy is the docs-contracts line's to replace with a link | open (for the reviewer, on 5a's code PR) |
| N-S4 | §3: tick 0 is construction and the first step runs tick 1, so `physics_steps == N // physics_every` after N steps (§10, checklist §10) | open (for the reviewer, on 5a's code PR) |
| N-S5 | §14: a `tick_digest` line kind in `intent_log` v0, with a fixture | open (for the reviewer, on 5a's code PR) |
| N-N1 | §3 owns the phase rule; realtime §2.1 is a superseded record, not edited | open (for the reviewer, on 5a's code PR) |
| N-N2 | checklist §7: the box's coordinates use `sphere_overlap`'s expression | open (for the reviewer, on 5a's code PR) |
| N-N3 | §13: bridge-driven sessions aren't logged or replayable, said in the marker's reason | open (for the reviewer, on 5a's code PR) |
| N-N4 | §14: the header is `boundaries.md` §6.3's; only 5a's additions are listed | open (for the reviewer, on 5a's code PR) |
| N-N5 | §9: the cost is per written member per tick | open (for the reviewer, on 5a's code PR) |
| W-B2, D-B1 (round 1, open) | as N-B2 | open (for the reviewer, on 5a's code PR) |
| W-S2 (round 1, open) | `tile_and_client.md` §3.2 amended to the owner's v0 ruling | open (for the reviewer, on 5a's code PR) |
| W-S4 (round 1, open) | `fold.md` A-B3 and Perf P6 corrected | open (for the reviewer, on 5a's code PR) |
| W-S6, D-B2 (round 1, open) | §9; sem §5's per-lane digests named as their own, not members | open (for the reviewer, on 5a's code PR) |
| W-S7 (round 1, open) | §6 adds grid and phase; **proposed: deferred**, world_v2 §2.5's list stays, since a superseded record is not edited; trigger: the docs-contracts line's index of superseded records | open (for the reviewer, on 5a's code PR) |

## Architecture and Bio-faithful (`delta1_arch_bio.md`)

| Id | Where it went | Status |
|---|---|---|
| DA-B1 | §5.1 one resolver per input kind; §6 inputs name their resolver; checklist §5.1 test; CLAUDE.md and B40 | open (for the reviewer, on 5a's code PR) |
| DA-S1 | §5 cadences name their D10 step and position | open (for the reviewer, on 5a's code PR) |
| DA-S2 | §6 writer roles: laws, `Topology`, construction and the save's loader, input appenders; the column is the writers' owner | open (for the reviewer, on 5a's code PR) |
| DA-S3 | §5.1: keyed-table rows are topology requests; fire_solid §1.4 owns their timing; checklist §5.1 | open (for the reviewer, on 5a's code PR) |
| DA-S4 | §5.1 `integrity`'s writers; checklist §5.1 | open (for the reviewer, on 5a's code PR) |
| DA-S5 | §11 bar 3 within cadence groups; §5 group order | open (for the reviewer, on 5a's code PR) |
| DA-S6 | §5.1 `contact_exchange` (per coupling row, reset by the solid, saved, ledgered when the ledger lands); fire_solid §3.2 linked for how the transfer is computed | open (for the reviewer, on 5a's code PR) |
| DA-S7 | §5.1: a shared operator lives in a module that is not a law; checklist §5.1 edits sem §7.1's table by name | open (for the reviewer, on 5a's code PR) |
| DA-S8 | §4; checklist §4; `fold.md` A-B3 corrected | open (for the reviewer, on 5a's code PR) |
| DA-S9 | §5 `bound_reads`; §7 key; checklist §5 planted law | open (for the reviewer, on 5a's code PR) |
| DA-S10 | §13 interim rules and port | open (for the reviewer, on 5a's code PR) |
| DA-N1 | §5.1 batch defined | open (for the reviewer, on 5a's code PR) |
| DA-N2 | §5.1: readers sum `radiant_emitters`' rows | open (for the reviewer, on 5a's code PR) |
| DA-N3 | §5.1 and §13 say "the admin material edit"; `set_material` keeps world_v2 §2.2's meaning | open (for the reviewer, on 5a's code PR) |
| DA-N4 | §5: a ledger handle joins when the ledger lands | open (for the reviewer, on 5a's code PR) |
| DA-N5 | **proposed: rejected**, world_v2.md is a superseded record and is not edited; its §2.5 lead already says §6 supersedes it | open (for the reviewer, on 5a's code PR) |
| DA-N6 | §2: `Topology` and its request type live with the cells | open (for the reviewer, on 5a's code PR) |
| A-B1 (round 1, open) | as DA-B1 to DA-S4 | open (for the reviewer, on 5a's code PR) |
| A-B3 (round 1, open) | as DA-S8 | open (for the reviewer, on 5a's code PR) |
| A-S2, A-S3, A-S7, A-N4 (round 1, partly open) | §5.1, §5, checklist §13, §2 | open (for the reviewer, on 5a's code PR) |
| BF-5a-B2 (round 1, partly open) | §5.1, §6, checklist §5.1 | open (for the reviewer, on 5a's code PR) |
| BF-5a-S2 (round 1, partly open) | checklist SEM rows add delta 2's A-S10 | open (for the reviewer, on 5a's code PR) |
| BF-5a-S3 (round 1, partly open) | §5 `per_tick` at sem §4.1's step 3 | open (for the reviewer, on 5a's code PR) |
| BF-5a-S4 (round 1, partly open) | §2, §3: `from_scene` publishes frame 0; checklist §3 | open (for the reviewer, on 5a's code PR) |

## Performance (`delta1_perf.md`)

| Id | Where it went | Status |
|---|---|---|
| Correction | §7 quotes the re-measured figures (about 115 ms today at 0.1 m; uncached about 4.2×, cached about 0.7×; 0.2 m 1.4–1.6×) | open (for the reviewer, on 5a's code PR) |
| S1 | §9 two-level scheme and seeded member digests; B5's digest-cost item; checklist §9 | open (for the reviewer, on 5a's code PR) |
| S2 | §7 states the 0.2 m cost; bar 7 records both grids and gates 0.1 m | open (for the reviewer, on 5a's code PR) |
| S3 | §5 `bound_reads`; §7 key; checklist §5 | open (for the reviewer, on 5a's code PR) |
| S4 | §7: caches hold only the current state's entries; §5.1: one window per apply phase, opened only when needed; checklist §7 | open (for the reviewer, on 5a's code PR) |
| N1 | §7 figures replaced, cited to `delta1_perf.md` | open (for the reviewer, on 5a's code PR) |
| N2 | §9: c14n-1 of four fields at 10 Hz, or `temperature` at 0.05 m, is the slower-than-real-time case | open (for the reviewer, on 5a's code PR) |
| N3 | §5.1: one cell window per apply phase | open (for the reviewer, on 5a's code PR) |
| P4 (round 1, open) | as S3 | open (for the reviewer, on 5a's code PR) |
| P6 (round 1, open) | §5.1 window rule; checklist §7 quiet-tick test | open (for the reviewer, on 5a's code PR) |
| P7 (round 1, open) | B5 gains the memory item; checklist deferral points to it | open (for the reviewer, on 5a's code PR) |
| P8 (round 1, open) | §7 cache contents a function of state; §9 seeded member digests | open (for the reviewer, on 5a's code PR) |
| P12 (round 1, open) | B5 gains the per-record work item | open (for the reviewer, on 5a's code PR) |

## For the docs-contracts line

This fold amends, in place and without growth: `tile_and_client.md` §3.1's `kind_rank` line and §3.2's v0 sentence.
`boundaries.md` §4.2's cadence copy and §6.4's rows are that line's or 5a's PR's, as noted above.
