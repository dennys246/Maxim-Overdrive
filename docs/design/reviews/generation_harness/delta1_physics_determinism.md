# Generation harness design, delta 1: Physics and resolution, Determinism and replay (2026-11-22)

The reader's hand-back, condensed and saved by the author. The reader set every status, read from the tree at e55c079
against `world_model.md` §1.1 and §4, `verify_harness.md` §4–§5, `simcore/verify/bands.py`, `test_cross_tier.py`, B30
and `subcell_solids.md` (05e9738).

**Probe** (a 100 kW, 0.3 m ignite for 30 turns of 6 s, in the spike's venv):
- **A table** (a 0.04 m top on 0.05 m legs):
  - at 0.1 m the hottest cell anywhere reaches 130,433 °C, in air, while the table's own cells peak at 20.6 °C, at
    integrity 1.000;
  - at 0.05 m the object peaks at 31,142 °C with a mean of 10,439 °C, at integrity 0.584.
- **A crate:** 175.6 and 176.0 °C peaks, a 101.7 °C mean at both grids, integrity 1.000.
- **Cost:** 0.20 s at 0.1 m and 0.93 s at 0.05 m per 30 turns.

## Statuses

| Finding | Status |
|---|---|
| Phys B1 | open, partly fixed: U2 records fidelity, but U3 and U3s still run cross-grid on the cell-centre representation before S1, and the table flips class (1.000 against 0.584) |
| Phys B2 | open, partly fixed: 0.1 m against 0.05 m, and the scenario lives in the battery file. U3's bar cites a closed form no arbitrary spec has and B30's round-number 10%; U3s's bar is unstated, and the band checks name no control variable |
| Phys B3 | fixed, with a new hole (F3) |
| Phys B4 | fixed in structure (`not_run`, `waits_on`, `raises=CheckUnavailable`); which ledger closes is unnamed (N2) |
| Phys S1, S2, N2 | fixed |
| Phys S3 | deferred to H0's measurement; the stated number understates it (F5) |
| Phys N1 | partly fixed: "the material's bound" is unsourced, and air has none |
| Det D1, D4, D9, D10, D11 | fixed |
| Det D2 | fixed in shape; the `rng_for` cross-machine claim is unproven (F6) |
| Det D3 | open: the verdict key contradicts §9 (F1) |
| Det D5 | partly fixed: "regressions refuse non-reproducible runs" appears nowhere |
| Det D6 | fixed in text; the cause is asserted, not measured (F4) |
| Det D7 | open, partly fixed: "budgets in turns, never seconds" is missing (F7) |
| Det D8 | fixed in §9, contradicted by §5.2 and §5.5 (F1) |

## New findings

**Contract blockers (B33):**
- **F1, §5.2, §5.5 and §9: the `must_match` key mixes generation pins with the battery's and the scorer's.** A
  heat-law change moves the simcore commit, so rerun verdicts still carry the generation header's old commit, and
  H4's consumer refuses them all until regeneration. That contradicts "a law change reruns only the battery". The key
  also holds values the consumer can't compare (the engine build, the machine label, `cache_prompt`). *Fix
  (unverified):* split resume keys (generation inputs, including the simcore commit, since `agent_text` is fed back)
  from each run's own keys. The battery and scorer bind to their own commit, data, lockfile and pymaxim, and verdicts
  are keyed on those plus the job digest and SpecId.
- **F2, §6 and §7: a cross-grid verification miss has no verdict class.** `spec_fault` is limited to `place`'s and
  the name checks; `engine_gap` needs a matching Known gap; the engine-property suite covers only finiteness, bounds,
  integrity and the ledger. The probe's table needs a verdict. `band_gate` also raises `ValueError` when a sweep
  doesn't bracket the outcome or flips more than once, which happens for any thick spec that never breaches. *Fix
  (unverified):* a verification miss is an engine defect under the engine-property rule; name each band check's
  control variable and sweep; map "not bracketed" to a stated class.

**SHOULD-FIX:**
- **F3, §6:** no rule covers an already-filed defect. Fire-on-air is a filed gap with a strict red gate, yet it heats
  air to 130,433 °C on the table, so the battery would stop at the first thin-topped spec. Fix: a failure matching a
  filed gate's id records `engine_gap` and continues; an unmatched one stops the batch.
- **F4:** "a prompt-cache hit changes the floating-point path" is asserted without measurement; run H1 with
  `cache_prompt` true too. Server launch flags (batch sizes, threads, GPU layers, flash attention) are pinned nowhere.
- **F5, §11 Q1:** "about 5 s a spec, 7 hours for 5,000" covers U3 alone at an unstated 150 turns, leaving out U3s's
  band sweep, U10, U8 and the 0.1 m runs. Round 1 estimated about 30 s a spec, about 6 times higher.
- **F6, §3:** the cross-machine promises have only one-machine proofs. Quantile interpolation of interval endpoints
  may differ under arm64 FMA contraction and per-CPU numpy dispatch. Fix: run the H2 digest and an H3 fixture on Linux
  CI too, digesting counts and indices only.
- **F7, §5.4:** the per-spec cost bound has no unit and no outcome. Fix: state it in turns, cells and tiles, and
  refuse oversized specs before running.
- **F8, U3:** "the peak temperature" is a cell maximum, which no consumer may read; at 0.1 m it's an air cell, not
  the object. Fix: a reduction in metres over the object.
- **F9, U2:** its `spec_fault` branch can never fire, since a part of 0.4 m or more always has cells at 0.1 m (a
  geometric argument, not run). It contradicts `subcell` §11.3, and its post-S1 form is unstated.

**NIT:**
- F10: say why 0.2 m's convergence half is waived per spec, or judge it where 0.2 m places the spec.
- N2: name the ledger and source the temperature bound, air included.
- N3: "inside the band widened by its margin"; derive the margins before measurement, not "measured at H3".

**Verdict: not ready.** Of 20 round-1 findings in these lenses:
- 12 fixed;
- 4 partly fixed;
- 1 deferred;
- 3 open;
- 1 overturned (D3, by F1).

Two new contract BLOCKERs (F1, F2) fold or go to the owner under B33. F3, F7 and F9 touch contract and are short to
fold. F4, F5, F6, F8 and F10 can move to H0–H3.
