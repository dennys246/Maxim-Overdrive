# SEM stimulus design, final round: Physics and resolution

Reader: Physics and resolution lens. Diff `0918685..aa6bd1b` only (`sem_stimuli.md` v4, `checklists.md` "The SEM
stimulus laws" and the 5a/5b/agent items, `tile_and_client.md` §2.1's supersession, `delta2/fold.md`, §10's rulings).
Statuses are read from the tree, not from the fold table. Tags: **V** read here, **M** memory, **D** derivation or
measurement. Scratch: `_durable/sem_review_final/scratch_physics/wood_horizon.py` (fire-research venv), which reuses
delta-2's `submesh.py` model unchanged.

**Correction first.** My delta-2 fix for PH2-S2 option (a), "hold the core node at 37 °C as a boundary", left out
what a held core does under a heat load: it becomes an unbounded whole-body sink. The owner ruled (a) on my text, so
that omission is now in the plan. New S1 below states it; it is my error, not the author's.

**Counts: 5 fixed, 1 deferred, 0 rejected, 2 open. New: 0 BLOCKER, 2 SHOULD-FIX, 3 NIT.**

## Status of delta-2 findings

| Id | Status | Reason |
|---|---|---|
| S5 (r1) | fixed | Closed with PH2-B1: the carried sub-mesh replaces both the coarse mesh and the per-tick rebuild. |
| PH2-B1 | fixed | §2.3 makes "carried state is declared and saved, never rebuilt from a coarser published state" a contract rule. §7.1 has contact run "against its own carried sub-mesh, kept from onset to release". §5's save names contact sub-meshes. The checklist's contact item has the persistent sub-mesh, the conservative remap, the single remap at release, the convergence axis, the planted per-tick rebuild, and "two-way coupling unmeasured" stated. The outcome gate as written has a defect (new S2). |
| PH2-S1 | **open** | §2.3's per-point rule ("sinks … per skin point … read through field interfaces over volumes in metres") is in the contract, and the checklist holds the sink choices, the secant form and the two-region test. What's missing: **tile §2.1 still prescribes the opposite sink**, "T_env is the volume-overlap weighted mean of the exchange volume's cells … the same weights debit them" (**V**, `tile_and_client.md` lines 128–131). That is one body-wide mean, debited from cells. The diff's only tile edit touches the relaxation test. v3's §3.1 sentence linking the two ("tile §2.1's exchange volume now meets the skin") was deleted, and nothing replaced it. So two accepted designs now give contradictory sinks, and §3.1 says v4 "extends" tile §2.1's body. §3.1 also no longer says the ambient is a reservoir, which the checklist's "fixed reservoir in Phase 1's still air" depends on for ledger closure. Needed: supersede tile §2.1's exchange-volume convection by name (the same way the diff superseded its relaxation test), and say in §3.1 where `bodies` books convective loss in Phase 1. |
| PH2-S2 | **open** | The fold proposed deferral. The owner then ruled (a) (§10), so the deferral is moot, and the ruling isn't carried into the contract or the checklist. (1) §3.1 is the contract's ledger list. It still books "perfusion (skin–core) and metabolism" and still calls the 245 kJ/K store "the core node". The held core's supplied power, "basal thermoregulation, ANALOG", isn't a named `bodies` term. A conservation test on `bodies` then sees an unbooked ~319 W per idle body (delta-2, **D**). Either it goes red or someone books the term ad hoc. (2) The checklist's core item still reads "(a) … or (b) …" with the ruling bolted onto its heading. (3) Tile §2.1's supersession is partial (new S1). |
| PH2-S3 | **deferred (accepted)** | Reason: immersion and plume are law content. The contract already binds them through §2.3's "every body–world coupling gets a cross-tier test with an outcome margin". The checklist holds the continuous gas-temperature field, the cross-tier test with an outcome margin at the flame edge, and the interim Known gap. Immersion is now in the checklist's cross-tier coupling list. Trigger: the tissue law's PR, which brings in the outer boundary. That PR must either ship the field or enter "plume gas doesn't heat" in `docs/architecture.md` with its number; with neither, the deferral lapses to open. |
| PH2-N1 | fixed | The checklist gives 5.1–5.5% per 0.1 K, conditional on L3's ΔE/R and on the constant trace. The 9% is gone. Units NIT below. |
| PH2-N2 | fixed | The checklist's flux item defines transmittance per path length (fraction/λ along the chord) or by sub-cell reconstruction, with a grazing ray in the wall-edge test. |
| PH2-N3 | fixed | The checklist's tissue item has the first-second no-drift test. Under (a) it still has teeth: a join solved on a different mesh or sink than the law runs on still drifts. |

## New findings

### SHOULD-FIX

**S1. Under the ruled core law (a), a held 37 °C core absorbs every watt a fire puts into the body. Whole-body heat
storage is gone, `core_temperature` would be a constant, and tile §2.1's second closed form now contradicts the
plan. Nothing records this as a gap.**
`sem_stimuli.md::§10` (PH2-S2 ruling), `::§3.1`, `::§2.2` ("`core_temperature` joins when bound");
`tile_and_client.md::§2.1` (Tests, the edited line); `checklists.md::The SEM stimulus laws` ("The core").

- **The heat sink.** The tile's own figures say a body 1 m from the flaming fire absorbs 9.3 kW (+2.3 K/min on
  245 kJ/K), and 1.0 kW at 3 m (+0.25 K/min) (**V**, tile §2.1). With the core held, that heat goes into the held
  boundary once the columns approach steady state.
- **Failure scenario.** An NPC stands 3 m from the fire for 20 world minutes. A free core rises about 5 K, into
  heat-stroke territory (**D**, tile's arithmetic). The held core reads 37.0 °C. That is an outcome-class difference
  (heat stress or none) decided by a modelling choice and recorded nowhere. Once `core_temperature` is bound (§2.2),
  it delivers a constant to Maxim.
- **The sign.** "Supplied power" must be signed: about +319 W idle and about −9 kW near the fire. Nothing in the
  checklist says so, and a source booked as non-negative would break the ledger by kilowatts.
- **The tile's closed forms.** The edited tile line keeps "a body facing a fixed point source heats at α·q''·A/(m·c)".
  Under (a) the core doesn't heat at that rate; it doesn't heat at all. The edit also supersedes "for the core by
  `sem_stimuli.md` PH2-S2", citing a review id rather than §10, which is the ruling's home.
- **Checklist coverage.** It doesn't hold this. Its "one world hour" idle test asserts only the idle case. Under (a)
  it can pass with the source unbooked, since nothing in the item asks for a ledger closed form (supplied power equal
  to surface loss, about 319 W).
- **What the fix needs** (not a design): a Known gap with the numbers above, a signed source with a ledger closed
  form, a statement of whether `core_temperature` may bind while the core is held, and the tile's second closed form
  superseded or restated. **Verified:** only the arithmetic, from the tile's own figures. No coupled run.

**S2. The contact outcome gate "wood at 90 °C stays painless" has no horizon, and the persistent reference itself
hurts at 54 s. "Hurts at 0.76 s" has no tolerance.**
`checklists.md::The SEM stimulus laws` ("Contact": "Outcome gate: wood at 90 °C stays painless and wood at 120 °C
hurts at 0.76 s against the persistent reference").

- **The run.** delta-2's `submesh.py` (persistent fine sub-mesh, held 37 °C core, L3's layers, 20 mm and 200 mm
  wood), run to 60 s at dt = 10 ms (`wood_horizon.py`; at 10 s it matches the 2 ms run, 42.87 against 42.9 °C).
- **Results:**
  - 90 °C wood: pain at **54.2 s**;
  - 100 °C wood: pain at 12.5 s;
  - 80 °C wood: no pain in 60 s.
  - Thickness doesn't matter at these times.
- **Failure scenario.** "Painless" is true only within a horizon, and delta-2 measured it at 10 s. Read without one
  (contact held until release, say 60 s), a correct law fails the gate. With any horizon past 54 s, the gate is
  wrong by construction.
- **Margin.** Within 10 s the gate's margin is 1.9 K at basal (42.9 against 44.8 °C), so the horizon and the margin
  belong in the item.
- **The 120 °C case.** "Hurts at 0.76 s" names a point value from one reviewer's toy model. With no tolerance, the
  gate either can't be met by a different correct discretisation or will be loosened to fit.
- **Checklist coverage.** It holds the gate, defectively. **Verified** by `wood_horizon.py`.

### NIT

- **N1.** `sem_stimuli.md::§2.3`: "a body-wide shade or ambient makes burns 3× late (**D**)". The 3× is the shared
  visible fraction's measurement (v1 B1, delta-1). No measurement in the record gives 3× for a body-wide ambient.
  delta-2 S1 measured a rest shift (2.3 K) and argued the head-burn case without a number. Limit the 3× to shade.
- **N2.** `checklists.md::Accuracy`: "5.1–5.5% per 0.1 K under L3's … and 0.68–0.75 per K if Henriques" puts two
  units side by side, inviting a 5% against 0.7 comparison. Per 0.1 K under Henriques it is 7.0–7.8%
  (exp(0.068–0.075) − 1, **D**, checked by hand).
- **N3.** `checklists.md::Sinks`: in Phase 1 the sink is a fixed reservoir, so the "two-region body, one region in a
  hot zone" test can't be built on the shipped path until zones exist. Name a fixture gas field for it, or name its
  trigger (the zone design), so it isn't written as a test that can't fail.

## Notes on the diff that need no action

- §2.3's five rules carry the resolution rule into the contract correctly: per point, kelvin tolerance as a truth
  constant (D20), carried state saved, face exchange a strict red gate (S4), and cross-tier with outcome margins for
  every coupling.
- §2.2's zero-order hold is unchanged and sound.
- The PH2-B1 contract text is right as it stands. My own toy holds the core at 37 °C, which matches the ruling, so
  its contact numbers stand under (a).
