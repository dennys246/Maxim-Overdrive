# Generation harness design, delta 1: Wire integrity, Bio-faithful integration and Validation coverage (2026-11-22)

The reader's hand-back, condensed and saved by the author. The reader set every status, read from the tree at e55c079
against the owner sections it relies on:
- IP §1.3, §2.1–§2.6 and §4.1–§4.2, and IG §1–§9;
- `boundaries` §4.4 and §9.1, `sem_stimuli` §6, `npcs_and_sem` §6.6 and `ip_and_licensing` §6;
- `subcell` §11.2–§12, `sim_core` §9, `fire_model.md:243` and NS3;
- the spike's client.

It read Maxim at the fetched 16aaf664, without running it, since no finding needed Maxim's runtime.

## Statuses

**Wire integrity:**
- **Fixed:**
  - B1: the client, the IP and IG edits, and OD-I11 and OD-I12 cited;
  - B2, S2, S3, S4, S6 and S8;
  - S5, in text (F11);
  - N2.
- **Deferred:** S7, to `ip_and_licensing` §6.2. Trigger: before any shipped prop.
- **Open:**
  - S1: the weights digest has no channel (F12);
  - N1, in half: the harness version's encoding;
  - N3 (F6).

**Validation coverage:**
- **Fixed:**
  - B1: L5 and N5 split (but F1 and F8);
  - B2, in rule (undermined by F2);
  - S1 (U1c), S2, S3 and S5;
  - S4, held until S6 and the codec;
  - S6, with a wrong citation (F5);
  - N1–N4.
- **Open:**
  - S7 (F7);
  - `douse` (F9).

**Bio-faithful integration:**
- **Fixed:**
  - B1, as asked (it creates F1);
  - B2: N6 is on the designed path;
  - B3, for L5 (other object-only checks unstated, F2);
  - S1 (it duplicates T1, F1);
  - S3 (test 4 runs a path that doesn't ship, F5);
  - N1.
- **Partly fixed:** S2 (F5).
- **Deferred:** the pushback candidate. Trigger: Maxim's proximity plan revives. Recorded only in fold1.md.

**Consumers re-enumerated:** each now maps to a real-path check or a red gate with a trigger:
- `place` (U1, then `imagine` at 5a);
- reach, ownership and spawn names (U1c);
- the scene loader (§2);
- receptors (N5);
- acts (N6);
- LLM text (T7);
- the client (U7);
- the scorer's geometry (§9);
- statics (U10).

The gaps:
- `douse` has no check;
- C's bar can't fail;
- U8's digest has no owner;
- L5 sits on a path the battery can't legitimately import.

## New findings

**Contract blockers (B33):**
- **F1, §4 and L5: the surface imports "the lab builder at its new home", which the owners put in tests only**
  (`fire_model.md:243`; NS3 moves `region_parts`, `RegionInstrument` and the lab surface under `tests/`).
  - `tests-out` doesn't cover `overdrive_tools`, so nothing stops the import.
  - L5's "no pain published" is `sem_stimuli` T1, an engine invariant, which §6 says is never a spec verdict.
  - No consumer needs L5.
  - *Fix (unverified):* remove L5 from the battery and put its assertion in the engine-property suite, run from
    tests. Drop the lab builder and the `maxim` exception from the surface, so `overdrive_tools` imports no `maxim`.
- **F2, §6 and §7: no check states which class its failure takes.**
  - U2 declares a non-`place` `spec_fault`, against §6 and `subcell` §11.3.
  - U3, U3s and U10's out-of-band disagreements fit no class: a spec fault steers stage 2's data, an engine defect
    halts a 7-hour run, and an `engine_gap` has no gate id.
  - Object-only regions are unclassed for every check but L5.

  *Fix (unverified):* a failure-to-class column in §7.
- **F3, §5.2 against §5.5 and §9:** the simcore commit is `must_match` for rescoring and consumption, yet §9 rescores
  under the current engine and reruns only the battery on a law change. A docs-only commit would refuse every verdict
  file. *Fix (unverified):* classify each key per reader (resume, rescore, verdict consumption), with the commit
  informational for rescoring.

**SHOULD-FIX:**
- **F4, contract, §4:** placements have no address field, and IG §8 lets only the gateway read `endpoints.yaml`. An
  implementer might add the address to shipped `data/placements/`, publishing it, or write a second reader. Fix: an IG
  §8 edit naming the harness client as a reader from the per-user directory.
- **F5:** T7's tool-name rule and the foundry's test 4 run Maxim's tool generation on a region, the path N6 says NPCs
  never take. The name reaches the LLM as text (T13), and the citation should be `npcs_and_sem` §6.6 (`player_text`,
  line 824), not §7.
- **F6, U8:** the tick digest is owned by `sim_core` §9 (`sha256/raw-1`, not yet built). A proposal to `digest.py`
  would create a second scheme. Its build belongs in H0.
- **F7, C:** B5's budgets are unset and scene-wide, and the limits surface as world outcomes, so C can't fail.
- **F8, N5:** delivery at receptors is our membrane's half, a verification bar that never waits on Maxim. Class it as
  verification, `not_run` until the first body.
- **F9:** `douse` over objects (`subcell` §7.1) has no check.
- **F10, §4:** the F6 ask isn't a Phase 3 row and cites no Maxim search. At 16aaf664 `complete_with_usage` takes
  `temperature`, `stop` and `thinking`, with no seed or top-p, which confirms F6. Searched `docs/plans` for seed with
  backend and sampling terms: archived plans only.
- **F11, §5:** the strict decoder isn't built (it comes with `phase1/protocol`, which H0 doesn't list), and §9.1
  bounds size, not depth.
- **F12, §5.2:** the "measured" digest is an operator's `shasum`, which nothing can measure on `owner_lan`. Call it a
  declaration.

**NIT:**
- "IP" means two documents in places;
- §2's `owner_lan` gap restates IP §6.3;
- §5.3 doesn't place `failed(refused)`, `failed(empty)` and `failed(oversized)`, or say whether excluded classes leave
  the denominators;
- §4's surface omits `frames`;
- N6's `accepted` is target-independent, so only its stimuli half can fail;
- `owner_lan` over `http://` needs `cleartext: true`;
- the pushback candidate has no Phase 3 row.

**Verdict: not ready.** F1–F3 are new contract blockers in folded text, so B33's stop rule applies. F4 should fold
with them. F5–F12 and the NITs move to H0/H1 (F4, F10–F12) and H3 (F5–F9).
