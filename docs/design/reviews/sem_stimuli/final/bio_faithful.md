# SEM stimulus interface v4: Bio-faithful integration, final round

**Read:** `git diff 0918685..aa6bd1b` on `phase1/sem-stimulus` (v4, `delta2/fold.md`, `checklists.md`,
`embeddable_agent_DRAFT.md` §7, lesson 27, `roadmap.md`, `tile_and_client.md`), plus the drafted standards at
`phase1/standards-bars` `c72fbe2` (B30–B33). I read Maxim only through `git show` and `git grep` at local
`origin/main` **`043eab8f`**, and did not fetch. I ran no new scripts. My numbers come from L3's committed measurement
(`_durable/sem_research/scratch/contact.json`).

## Status of my delta-2 findings (reviewer-set, read from the tree)

| Id | Status | Reason |
|---|---|---|
| SF-3 | fixed | Draft §7: `percepts.py:122` is gone, and so is the false "searched, nothing found" for M4. The three production callers are cited, and I checked them at `043eab8f`: `substrate_proposal.py:837`, `loop_gates.py:309`, `tool_bridge.py:776`. M4 is now a Question, and the between-pass keying question has been added. The routing is still wrong, and that is new finding F-S1 below. |
| D2-B1 | fixed | T16a asserts what only per-tick delivery produces: the stub's push log holds every tick's value inside the contact. It is red under D14, turns green with per-tick delivery, and carries `raises=AssertionError`. The gap now has a guard that can fail. T16b, the other half, is ill-posed (F-B1). |
| D2-S1 | fixed | §4.6 defines the term: a PainBus publish driven by a bound skin sensor, with onset before Ω = 1, and failure-mode pain excluded. `roadmap.md:293` points at it. Two well-posedness gaps remain (F-S2, F-N1). |
| D2-S2 | fixed | §4.4: on a cognition tick the host pushes but doesn't step the body, and between cognition ticks the host steps it. The between-pass key is tagged ANALOG and asked in M4. The checklist has the one-call gate, but the gate has no plant (F-N4). |
| D2-S3 | fixed | §6.4 lists all three routes. Citations checked: `body.py:806` `WARN:`, and `memory_hub.py:58-77` (in `integration/`). M19 is widened, T13's golden adds both prompt sections, the worker refuses the flag, and §3.3 says no failure mode triggers on a bound sensor field. |
| D2-N1 | fixed | The checklist's first-body item has the apparatus check of measured rest per depth and ambient (28.5–35.1 °C). |
| D2-N2 | fixed | M10's evidence is now a harness scenario under `tests/` on a fixture body, outside Phase 4's scenes. |
| D2-N3 | fixed | `spec.py:1034-1036`. |
| SF-2 (delta 1) | deferred, unchanged | The trigger still stands: the checklist's first-body item ("SF-2, trigger this PR"). |

**Counts:** 8 fixed, 1 deferred (carried over), 0 rejected, 0 open. The author proposed no deferral on my lens's
rows. PH2-S2's proposed deferral is moot, because the owner ruled (a). I rule below only on the bio-faithful side of
(a) (F-S3).

## New findings in the diff

### F-B1 (BLOCKER). T16b is not a well-posed future bar: its world-side evidence is red by design, its flip doesn't need the upstream items it names, and it has no Phase 3 row

**Where:** `sem_stimuli.md::§4.6` (T16b), `checklists.md::The SEM stimulus laws` (last item), `roadmap.md` Phase 3.

B31 (`c72fbe2`) requires three things of a future bar. T16b fails all three.
1. **"The world-side half is T16a."** T16a is strict red under D14 by design: delivery runs at the cognition rate.
   So the evidence that "the world-side half passes" is a gate that is defined to fail. Under B31, "without that
   evidence it is our bug."
2. **What actually flips it is our own interim.** The drive latch publishes on band entry at whichever
   `evaluate_failures` call sees the entry (`body.py`, `breach_latch = ent.drive_breach_severity`, "pain fires on
   band ENTRY only"). Once D14 lifts, §4.4 has the host push every tick and step the body between cognition ticks.
   On today's pymaxim, the host's call on the peak tick then publishes between steps, and T16b goes green, with
   neither M4 nor #1176 landed.
   - #1176 (L1) is per-pass transduction *inside* an agent pass, "a per-pass transduction also encodes that pass,
     then `note_active_clusters`, then pain, in one tick" (`thalamic_relay.md` §L1 and GL3.B4, about `:478-483`).
     It produces no publish between passes.
   - So the gate names an upstream issue whose fix doesn't flip it. It also doesn't assert the one Maxim-owned
     thing M4 asks: how a between-pass publish is *keyed*.
3. **No Phase 3 row.** `grep -n 'M4\|1176\|T16b' docs/roadmap.md` matches nothing. OD-A10's row doesn't mention
   the body step.

**Failure scenario.** D14 lifts once a pain path exists. T16b XPASSes and the strict gate turns red. The author
removes the xfail. A Phase 3 ask to Maxim (#1176) has stood on evidence that never isolated Maxim. Meanwhile the real
defect goes unguarded: the publish is keyed to the previous pass's stash, fear goes to the wrong place, and the
ANALOG tag in §4.4 has nothing to hold it.

**Fix (unverified; I reasoned from the cited sources and ran nothing):**
- **World-side half:** the delivered value crosses the fixture drive's band edge on a between-step tick. That is a
  `BoundFrame` value check, and it passes once the contact law exists, whatever D14 says.
- **Maxim half:** a between-pass publish is joined to the situation in which it occurred, not to the last stash. See
  the `CauseRef` path in F-S1.
- **Classification:** if only D14 stands between T16b and green, T16b is a verification bar of ours, not a future bar.
- **Roadmap:** add the Phase 3 row with its trigger, citing the world-side test.

### F-S1 (SHOULD-FIX). M4 is routed to a merged stage and a census; the plan that owns between-pass keying isn't cited

**Where:** `sem_stimuli.md::§9 M4`, `embeddable_agent_DRAFT.md::§7`, lesson 27.

- **GL3.B0 is merged** (#1201, `grounding.md:14`, "status 2026-10-18"). It was a census and a set of red gates, and
  it has no open scope to answer a question.
- **`autonomic_layer.md` §1.2a is a state description, not a plan.** The plan that answers "how is a publish between
  passes keyed" is the same file's **out-of-band producer**: `autonomic_layer.md` §3.1.4, owner decision **G9**,
  "after the fence". In it:
  - `evaluate_failures` compares against a per-entity snapshot and queues a record, drained by
    `Embodiment.drain_outcomes()`;
  - emission is "latched like channel 2: band entry/exit … never per tick";
  - a delayed consequence joins its cause through `CauseRef.cause_pid`;
  - the record carries the bridge's `state_age_s`, which is exactly the Minecraft-pump analogue of our host step;
  - the cross-thread lock on `drive_breach_severity` lands with this producer (§1.2a, last paragraph).

**Failure scenario.** Maxim reads M4 as a question to a finished stage, or answers it from the census ("yes, callers
exist"). The keying question then gets no owner, and our ANALOG stale key has no trigger to close.

**Fix (verified by reading):** route M4 as a Question to `autonomic_layer.md` §3.1.4's out-of-band producer (G9),
plus #1176 for the in-pass half. Cite GL3.B0's census as evidence, not as owner. Same change in the draft's §7 and
lesson 27.

### F-S2 (SHOULD-FIX). The pain-path test fixes neither the divisor nor a margin, so "a pain path exists" depends on the dial

**Where:** `sem_stimuli.md::§4.6` (definition), `::§6.3` (fingertip sentence), `roadmap.md:293`.

The definition only says onset "precedes Ω = 1". L3's measurement for 70 °C steel in perfect contact
(`contact.json`, **D**) gives pain at 0.25 s and Ω = 1 at 2.92 s.
- Under D14, a skin-driven publish arrives at the next cognition tick, up to 0.1·d s later.
- At divisor d ≥ 27, a worst-phase contact publishes after Ω = 1. T9 runs the dial to 50.
- So one body has a pain path at divisor 10 and none at divisor 30, and Phase 4's gate doesn't say which.
- At d = 25 the onset precedes Ω = 1 by about 0.2 s. That meets the words but gives no time to withdraw.
- CLAUDE.md requires binary outcomes to be gated with an outcome margin, and this one has none.

**Fix (unverified):**
- Run the test at the dial's maximum and over every cognition phase. Measure the delivery delay in ticks, not
  seconds.
- Require a lead of at least a sourced withdrawal latency plus one cognition interval.
- Record the lead.

### F-S3 (SHOULD-FIX). Core law (a) puts the hypothalamic set point in the world; a bound `core_temperature` would be a constant that does Maxim's homeostasis for it

**Where:** `checklists.md::The core`, `sem_stimuli.md::§10` (PH2-S2), `::§2.2` ("`core_temperature` joins when
bound"), `::§3.1` (the `bodies` ledger line), `::§1` ("Maxim owns … set points, drives").

(a) holds the core at 37 °C and books the supplied power as "basal thermoregulation, ANALOG". The ANALOG tag is honest
about the physics, but four things are missing:
1. **§1 assigns set points to Maxim.** Maxim's own plan claims the regulator: "Hypothalamic thermoregulation is
   two-sided" (`autonomic_layer.md` R-2), and §3.3 adds the "above → heat" corrective need. No §9 row asks
   `autonomic_layer` §3.3. That breaks the search rule for a design that depends on what Maxim plans.
2. **A bound core sensor becomes an oracle of perfect regulation.** §2.2 lets `core_temperature` be bound. Under (a)
   it reads 37.000 forever. A body with a homeostatic core drive then never breaches in fire or in a cold street, and
   R-2's two-sided need can never be exercised or learned: the world has regulated perfectly on the agent's behalf.
   *Scenario:* a cradled NPC with a `core` drive stands in a 20 kW/m² plume for minutes, and its core drive stays
   silent.
3. **§3.1's ledger line lists radiant, contact, ambient, perfusion and metabolism, but not the held-core power.** A
   conservation audit of `bodies` would show (a)'s source or sink as an unexplained residual.
4. **"An idle NPC for one world hour" has no pass rule.** Under (a) the core can't move, so a core check can't fail.

**Fix (unverified):**
- A build check refuses binding `core_temperature` while (a) is the law, planted.
- Add the held power to §3.1's ledger line.
- Add an M-row: a Question to `autonomic_layer.md` §3.3 and R-2 on who owns core regulation.
- Give the idle test a pass rule: the supplied power matches its closed form, and skin rest drifts less than the
  kelvin tolerance in one hour.

### F-N1 (NIT). The fingertip sentence is conditioned on the term it defines, and asserts a different thing

`sem_stimuli.md::§6.3`: "With a pain path: … under `noci_heat` exceeds threshold before … Ω reaches 1". §4.6 says a
pain path is *shown by* this test, and defines it as a PainBus publish, not a receptor threshold. `noci_heat` is
M9/GL2b's `NociceptorSpec`, which doesn't exist at `043eab8f`. A builder can't tell whether the test asserts a
threshold crossing or a publish, or when it runs.

**Fix:** a single unconditioned test that asserts a PainBus publish, observed by a subscriber.

### F-N2 (NIT). "Stamped between cognition steps" has no meaning in Maxim

`§4.6` T16b. `PainSignal` carries no world tick. `PainBus.publish` gates on `time.monotonic()` (`pain_bus.py:196`).

**Fix:** define the stamp as the host tick of the `evaluate_failures` call whose subscriber saw the publish. Note that
the refractory runs on the wall clock (M6) and can't decide a single-entry test.

### F-N3 (NIT). The checklist still offers (b)

`checklists.md::The core` says "the owner ruled (a)", then still offers "(a) … or (b) free, with the 3.5–4.7 K/h drift
as a Known gap". A builder reading only the checklist could pick (b).

**Fix:** delete (b), or keep it as history.

### F-N4 (NIT). The one-call gate has no plant

`checklists.md` (agent line): "one `evaluate_failures` per agent step on a cognition tick (D2-S2)". Unlike its
neighbours, it names no plant, and §0's "Bars" paragraph says every gate's plant is in the checklist.

**Fix:** plant a host step on a cognition tick, and the count must read 2.

## Answers to the lens questions

- **Stimuli, never labels?** The world side is clean. One exception: under core law (a), a bound `core_temperature`
  would report a regulated variable as perfectly regulated (F-S3).
- **What may be claimed as learned?** §6.4 is sound and its audit is complete. Credit from between-pass pain stays
  ANALOG, with no owner to close it until M4 is routed to G9's out-of-band producer (F-S1).
- **T16b as a future bar?** It is not well posed (F-B1).
- **M4 searched properly?** Better than v3: the callers are right and the false "nothing found" is gone. But it still
  misses the plan that owns the answer (F-S1).
- **Core law (a) as ANALOG?** Acceptable as physics, but not as bio-faithful integration until the core sensor is
  refused and the question goes to `autonomic_layer` (F-S3).
