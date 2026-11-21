# Fold of delta round 2 into `sem_stimuli.md` v4

**Author's table, 2026-11-21.** One row per finding that delta round 2 left open or raised new. "Where" names the v4
section, or the checklist item (`docs/plans/checklists.md`: **5a**, **5b**, **agents** for the agent line's SEM block,
**laws** for "The SEM stimulus laws"). Every status is **open (for the reviewer)** (O25); a deferral or rejection the
author proposes says so. Physics' delta-2 ids are prefixed PH2- to keep them apart from other lenses' S and N ids.

**The owner's split shaped the fold** (2026-11-21): v4 keeps the contract; law text, numbers and test mechanics moved
to the checklist once, deleted from the design. About 1,600 words left the design and about as many came in as
contract fixes, so v4 is 5,993 words, at the cap, not under it as the split hoped. The checklist grew to 5,659 words
(it is exempt from O22 by O42).

**Verified before folding (scratch: `scratchpad/v4/`, plus reruns of the reviewers' scripts):**
- Y1/D2-B1: T16's measurement reproduces (basal 5.71, 7.55 and 10.80 K above rest at the next step).
- PH2-B1: the sub-mesh table reproduces (wood 90 °C: rebuilt 2.35 s, stale 0.40 s; persistent painless).
- DP3-B1, DP3-S1: the shared cap changes A's refresh log when others run, and a per-body cap of 12 doesn't; literal
  "moved first" starves stationary pairs for 100 of 100 ticks; pure oldest-first gives 6.
- F1: the overlap toy reproduces (an `ignite` plant red on both legs; a posture plant green on the on/off leg).
- W9/Y4/A3-S1: the closure test reports `pkg.core.readonly` outside the surface; A3-S2's `layers` contract with
  `containers` breaks `spec → store` and a sibling `tissue → contact`, and keeps the clean package.
- Y1(b): a strict xfail without `raises=` reports a missing module as "xfailed"; with `raises=AssertionError` it fails.
- D2-S2, D2-S3, SF-3: Maxim citations read at `origin/main` 043eab8f. One was off: the "without choosing to call
  tools" text is at `loop_perception.py:274`, not `prompt_builder.py:1909-1915`; v4 cites `loop_perception.py`.

**Not verified by the author:** the rest temperatures by ambient (D2-N1, the reviewer's measurement); PH2-S1's
34.7 °C and linearisation errors; PH2-S2's 3.5–4.7 K/h; Henriques' **M** constants (PH2-N1); A3-S5's producer key as
built; every fix that needs code that doesn't exist (marked "design").

## Executor

| Id | What v4 did | Where | Status |
|---|---|---|---|
| X1 | the value check moves to before each push, against the recorded value; plant: a stub writing during cognition | §4.4; agents | open (for the reviewer) |
| X5 | the contract sets `L_us ≥ 1`, refused at 0, planted; the false §9 citation removed | §4.1; agents | open (for the reviewer) |
| Y1 | T16 split: T16a asserts per-tick delivery from a stub push log (red under D14), T16b a future bar on a fixture body; both land with the contact law with `raises=AssertionError`; the Known gap reworded with the measurement | §4.6, §6.3; agents, laws | open (for the reviewer) |
| Y2 | the recorded value is the pushed value clamped to the declared range; a bite is counted, not a failure | §4.4 | open (for the reviewer) |
| Y3 | `wire.py` (the `BoundFrame` types and binding data) and binding validation land in `phase1/agents`, before the codec; `frame.py`'s host-only `BodyFrame` stays with the tissue row | §7.1, §11.1; agents | open (for the reviewer) |
| Y4 | the `wire.py` leaf plus a closure test (with W9) | §7.3; agents | open (for the reviewer) |
| Y5 | the order plant runs on one-sided exposure and first asserts the permuted values differ | 5a | open (for the reviewer) |
| Y6 | the overlap gate releases stub replies at host hooks in two fixed orders, no wall timing | §4.1; agents | open (for the reviewer) |
| Y7 | lanes hash after rounding; the plant moves a digested value by at least one quantum, sized when rounding freezes | §5; 5a | open (for the reviewer) |
| Y8 | `world_owned_sensors` is the bound set; build test and empty-tuple plant | §3.3, §4.4; agents | open (for the reviewer) |
| Y9 | the 5–9% sentence left the design; the checklist states 5.1–5.5% under L3's constant, conditional on the trace | laws | open (for the reviewer) |

## Architecture

| Id | What v4 did | Where | Status |
|---|---|---|---|
| A-S10 | the 5a checklist item says the composition note cites §11.1; the plan row is unchanged (at its budget) | 5a | open (for the reviewer) |
| A3-S1 | kept `allow_indirect_imports = false` with a leaf `wire.py` and a closure test (Wire W9's fix), not `true` plus `PLAIN_DATA`: the leaf makes the surface closed by construction, so no plain-data list has to be kept | §7.3; agents | open (for the reviewer) |
| A3-S2 | `body-layers` and `stimuli-layers` contracts with `containers`; stimuli restated as 5c, above intents | §7.1, §7.3; 5b | open (for the reviewer) |
| A3-S3 | `tissue.py` exports the column operator and steps untouched sub-columns; `contact.py` steps touched components on one grid it owns, first in step 3; §7.2's substep sentence restated | §7.1, §7.2; laws | open (for the reviewer) |
| A3-S4 | one home: `store.py` implements the registry's `body_points` container, the `FieldReader` views it without a copy | §3.1; 5a, 5b | open (for the reviewer) |
| A3-S5 | row lane keys add derived `producers`; the bound lane key adds bindings digest, reduce version and bound row keys; D13 records them; a producer-bump plant | §2.1, §5, §7.4; 5a | open (for the reviewer) |
| A3-S6 | `body-protected` lands in 5b, allowed layer 6's modules; the store's writer allowlist and scan | §7.1, §7.3; 5b | open (for the reviewer) |
| A3-N1 | `MEMBRANE_SURFACE` subtracts the new surface modules | §7.3; 5b | open (for the reviewer) |
| A3-N2 | `core/stimuli/events.py` owns pending events and coalescing, saved by layer 6 | §7.1 | open (for the reviewer) |
| A3-N3 | `site_id` is the index within the row's site set for that body | §4.2, §5 | open (for the reviewer) |

## Wire integrity and trust

| Id | What v4 did | Where | Status |
|---|---|---|---|
| S4 | with W9 | §7.3 | open (for the reviewer) |
| W2 | recommended target-independent v1 kinds (`malformed`, `limit`, `accepted`), with the ANALOG alternative as **D15 for the owner**; T11 sweeps a strike point across a footprint edge | §6.2, §10; agents | open (for the reviewer) |
| W4 | the bindings-digest refusal is planted by editing only the worker's copy | §3.2; agents | open (for the reviewer) |
| W9 | `wire.py` leaf importing only `checks` and numpy; grimp closure test over `AGENTS_SURFACE` | §7.1, §7.3; agents | open (for the reviewer) |
| W10 | `BodyFrame` holds one tick's events; a `BoundFrame` concatenates undelivered ticks' events and receipts; receipt timing defined; divisor-10 plant | §4.2, §6.2; agents | open (for the reviewer) |
| W11 | the bound lane is keyed by format and vocabulary versions; header carries them; replay refuses unknown versions by name | §5; agents | open (for the reviewer) |
| W12 | posture, gaze and breath go through stage 1 with limits and gate rows; NaN-gaze plant | §4.5; 5b | open (for the reviewer) |
| W13 | `welcome` and `step_output` get versions and gate rows | §5; agents | open (for the reviewer) |
| W14 | `pid` per NPC; `tick` dropped after its check; restart drops the previous life's receipts, counted | §4.2, §4.5; agents | open (for the reviewer) |

## Physics and resolution

| Id | What v4 did | Where | Status |
|---|---|---|---|
| S5 (r1) | with PH2-B1 | §7.1; laws | open (for the reviewer) |
| PH2-B1 | the contract: contact runs against its own carried sub-mesh, saved, never rebuilt from published state; the law, outcome gate and planted rebuild in the checklist | §2.3, §5, §7.1; laws | open (for the reviewer) |
| PH2-S1 | the contract: sinks per point through field interfaces, never a body-wide mean; the sink choices and test in the checklist | §2.3; laws | open (for the reviewer) |
| PH2-S2 | **proposed: deferred to the tissue law's PR** (trigger: that PR chooses (a) or (b) and adds the one-hour idle test); a law choice under the split | laws | open (for the reviewer) |
| PH2-S3 | **proposed: deferred to the tissue law's PR** (trigger: the gas-temperature field or the Known gap lands with it); immersion added to the cross-tier list | laws | open (for the reviewer) |
| PH2-N1 | with Y9 | laws | open (for the reviewer) |
| PH2-N2 | transmittance per path length and a grazing ray | laws | open (for the reviewer) |
| PH2-N3 | the first-second no-drift test | laws | open (for the reviewer) |

## Determinism, replay and performance

| Id | What v4 did | Where | Status |
|---|---|---|---|
| DP3-B1 | the contract: no budget shared across bodies, caps per body and per emitter; a T11 plant; D12's measurement on one body; the pooling trade named for the owner | §7.2, §8, §6.3, §10; laws | open (for the reviewer) |
| DP3-S1 | one total order from saved state | laws | open (for the reviewer) |
| DP3-S2 | per-emitter caps, the maximum emitter count in the header, D12 measured at it | §8, §5; laws | open (for the reviewer) |
| DP3-S3 | a component is the patches sharing sub-mesh nodes; a T11 plant with B on the same floor | §7.2, §6.3; laws | open (for the reviewer) |
| DP3-N1 | with Y6 | §4.1; agents | open (for the reviewer) |
| DP3-N2 | an events lane per NPC, reserved in 5a | §5; 5a | open (for the reviewer) |
| DP3-N3 | the byte budget is a header constant, refused at start unless below the socket buffer | §4.3, §5 | open (for the reviewer) |
| DP3-N4 | the substep row restated on the table's basis (~11–14 ms) | laws | open (for the reviewer) |
| DP3-N5 | flux sums emitters in stable-key order; a T11 plant | §7.2, §6.3 | open (for the reviewer) |

## Bio-faithful integration

| Id | What v4 did | Where | Status |
|---|---|---|---|
| SF-3 | M4 rerouted as a question to GL3.B0, #1176 and `autonomic_layer.md` §1.2a (OD-A10 for the host-driven build); the dormant `percepts.py` citation and the false "nothing found" removed; the three production callers cited; the between-pass keying question added | §9; `embeddable_agent_DRAFT.md` §7 | open (for the reviewer) |
| D2-B1 | with Y1; T16b is this lens's fixture-body test, as a future bar | §4.6 | open (for the reviewer) |
| D2-S1 | "pain path" defined as a sensor-driven PainBus publish preceding Ω = 1, shown by the fingertip test; failure-mode pain excluded | §4.6, §10 | open (for the reviewer) |
| D2-S2 | on a cognition tick the host pushes and doesn't step; one `evaluate_failures` per agent step; the between-pass key tagged ANALOG and asked in M4 | §4.4, §9; agents | open (for the reviewer) |
| D2-S3 | §6.4 lists the three routes; M19 widened; T13's golden adds auto-sense and `body_state`; the worker refuses the flag; no failure mode on a bound sensor field | §3.3, §6.3, §6.4, §9; agents | open (for the reviewer) |
| D2-N1 | the apparatus check of measured rest per depth and ambient | laws | open (for the reviewer) |
| D2-N2 | M10's evidence is a harness scenario on a fixture body, outside Phase 4's scenes | §9 | open (for the reviewer) |
| D2-N3 | `spec.py:1034-1036` | §3.3 | open (for the reviewer) |

## Concurrency and lanes

| Id | What v4 did | Where | Status |
|---|---|---|---|
| F1 | the stub stream includes a cell-writing intent; the replay leg must go red | §4.1; agents | open (for the reviewer) |
| F2 | the condition is stated: T16a flips only once the barrier's B5 row exists | §4.6; agents | open (for the reviewer) |
| C1 | with W10: `BodyFrame` events per tick, delivery concatenates; T9 compares `BodyFrame`s byte for byte and `BoundFrame` content as a multiset | §4.2, §6.3 | open (for the reviewer) |
| C2 | the baseline at `agent_ready`, compared by name multiset, re-baselined at session boundaries; OD-EA7 named as unmet, its real-Maxim test strict red; Q7 records the session-open assumption | §4.4, §11.2; agents | open (for the reviewer) |
| C3 | with X5 | §4.1 | open (for the reviewer) |
| C4 | inbound `step_output` merges only whole; half-sent plant | §4.3; agents | open (for the reviewer) |
| C5 | the pump is a thread handing off through a queue step 7 drains; its cost and GIL share go in the B5 row | §4.1; agents | open (for the reviewer) |
| C6 | under D14 the parks divide by the cognition divisor | laws | open (for the reviewer) |

## Needs the owner

- **D15:** v1's receipt kinds (W2). Recommended: target-independent. Its cost: an NPC can't tell whether a strike
  landed until a touch or vision row exists.
- **D12's trade:** a per-body budget gives up pooling (DP3-B1); confirm with D12's re-ruling.
- **PH2-S2's core law** is a law choice deferred to the tissue PR, but option (a) supersedes tile §2.1's free
  relaxation test by name, which touches an accepted design.
