# Generation harness design, fold 2: the final fold under B33 (2026-11-22)

Delta 1 found new contract BLOCKERs in folded text, so the rounds stop (B33). Contract findings fold here, and mechanism
findings move to `docs/plans/checklists.md`'s "Generation harness" section, where a reviewer records each deferral
with its step as the trigger. Every status below is the author's claim.

## Contract, folded

| Finding | Change |
|---|---|
| NB1 (Arch/Trust/Exec) | §4's import surface lists frames and reductions, `schema`, `refusals`, `materials`, `checks` and `digest`. Verdicts read published frames, never `encoding`, which stays only for C and U7 |
| NB2 | §5.3 classes record fields as identity or informational. §3's generation identity is the byte equality of the identity projection, without `timed_out` and `transport_error` records |
| NB3, Wire F4 | a new §5.6: the harness's own versioned, per-user `generation_endpoints` file and gate, its directory proposed to `boundaries.md` §5.3, keys by reference to the OS credential store, and an IG §8 note. §2 points there |
| Phys/Det F1, Wire F3 | §5.2 classes keys per reader: a resume, a rescore, and the battery and its verdicts, which bind to their own commit, data, lockfile and pymaxim. §5.5's verdict key uses the battery's keys plus the job digest and SpecId, so a law change reruns only the battery |
| Phys/Det F2, Wire F2 | §7 gains a "A failure is" column for every check. §6 classes cross-grid misses as engine defects, `band_gate`'s no-flip as `world_outcome` and multiple flips as an engine defect, and object-only regions as `not_run: waits_on=S3`. U2 never yields `spec_fault`, and its post-S1 form is S1's µm rule |
| Phys/Det F3 | §6: an engine defect matching a filed gate's id records `engine_gap` and continues, while an unmatched one stops the batch and is filed first |
| Phys/Det F7 | §5.4: the cost bound is in turns, cells and tiles, derived from the `Budget`, and an oversized spec is refused before running as `not_run: waits_on=bound` |
| Phys/Det F9 | U2 never yields `spec_fault` (§7, §6) |
| Wire F1 | L5 is removed. Its no-pain and no-drive assertion is an engine property (`sem_stimuli.md` T1) run from `tests/` (§6). There's no lab builder or `maxim` exception, and `overdrive_tools` imports no `maxim` (§4) |
| Wire F8 (folded, though listed as mechanism) | N5 and N6 are classed as verification of our half, not perception and learning |
| Wire F5 (citation) | `player_text` is cited at `npcs_and_sem.md` §6.6 |
| Wire F6 (in part) | U8's "Until" names `sim_core.md` §9's `sha256/raw-1`, so there's no second scheme |
| Wire NIT, IP naming | U7 cites `ip_and_licensing.md` item 4 |
| Owner rulings | §11 records both. `owner_lan` is a Known gap in `docs/architecture.md` (PR #52 moves it) and in `long_term_features.md`'s Open row, with the peer-mesh trigger |
| NS3 | the roadmap's Phase 4 gains the removal row for `TEMPORARY(phase4/inference)`, naming its triggers |
| Wire F10 | the roadmap gains Phase 3 OD-I13 (seeds and samplers on the backends) with its Maxim search; the foundations plan lists it |
| NN1, Wire F11 | §10's H0 and the header list PR #52 and `phase1/protocol` |

## Mechanism, moved to the checklist

NS1, NS2 (moot after L5's removal), NS4, NS5, NS6, NS7, NN2–NN5; delta Physics F4, F5, F6, F8, F10, N2 and N3; Wire
F5's shipping surface, F7, F9, F11 and F12 and the NITs; Executor N2 (PR #50 cited at a commit). Each is under its step
in `checklists.md`, citing its finding.

## Not folded

- **Exec S4 (clock-free L5 fields):** moot, since L5 is removed and the battery imports no `maxim`.
- **Physics/Det F5** (the cost estimate): the arithmetic is replaced by H0's measurement of every check.

## After the reviewer's check (author's claims)

The deferral reviewer set the statuses: all twelve contract folds fixed, every listed mechanism item deferred to its
step, and no new blocker. Four one-sentence items, folded:
- **NS7, contract:** §5.5 decides `within_margin` per consumer. A data job (stage 2) keeps such specs, since dropping
  near-threshold shapes steers its data as excluding `engine_gap` would; a shipped-prop consumer refuses them. The
  author's decision, for the owner to confirm in review.
- **F2's no-flip rule:** a `world_outcome` only when both grids agree; a flip at one grid only is a cross-grid miss.
- **F3's "simcore commit":** the digest of the tree under `src/simcore/` and `data/`, not HEAD.
- **§4:** the address comes from §5.6's file for the placement id, and the endpoints reader joins the gate rows.

H0's checklist line now cites the owner's ruling instead of "§11's first question settled".
