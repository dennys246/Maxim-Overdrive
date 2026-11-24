# Sub-cell solids design, the check of fold 2 (2026-11-22)

After B33's stop (D37), one independent reader set the statuses of the final fold, read from the working tree on top
of 7fcf9af: the deferrals to build steps, and delta 1's contract findings. This is a condensed record of its
hand-back. The budgets passed: the design at 5,998 words, `fire_solid.md` at 5,963 (base 5,964), and the
foundations plan at 2,493, with `check_plan` passing.

## Deferrals to build steps (the reviewer's)

| Finding | Step | Status |
|---|---|---|
| Wire NS4, N-b, N-c, Wire N2, A-S7 | S1 | deferred, trigger S1. Wire N2 holds only while S6 takes NS2's "no recount" |
| Wire N7 | S1 | **open, contract**: `recipe_id`'s sentinel is read by step 9's save reader, so it belongs in §3.1 |
| S-g, N-d | S2 | deferred, trigger S2. If S2's solver depends on the BLAS, its identity joins the log header, as statics' does |
| S-c with Physics B4's remainder | S3 | shading and the closed-form test deferred, trigger S3. **The band's tiling is open, contract** (§3.1's tiling rule is keyed on the wire and saved) |
| Wire NS5, Wire N3 | S3 | deferred, trigger S3 |
| S-e, N-N3, N-e, A-S3 | S4 | deferred, trigger S4 |
| Wire NS2 | S6 | **open, contract**: §10 still sends `tile_m` for a client recount that the checklist forbids |

## Delta 1's contract findings (the reviewer's)

**N-B1 is open in part.** It is fixed in the design, but `fire_solid.md` §1.3's body still defines contact against a
"solid cell face" and overlap against a "footprint", contradicting its own first line. The present geometry also
needs a holding before S1's `region_geometry` exists.

**Fixed:**
- B-1: a failed member leaves the solve, and §8.3 cascades within the step;
- B-2;
- N-S1, N-a, N1;
- N-S2, N-S3 and A-S4's open part;
- N-S4: both of the reader's cases give `kind_not_admitted`;
- N-S5, S-a;
- N-S6;
- S-b, S-d, S-f;
- NS1: checked against `applier.py:101–121`;
- NS3, NS6, NS7;
- N-N1: the retired codes appear only in §12's descriptions;
- TP1: the links resolve once `phase1/torch-pilot` merges.

**No new contract BLOCKER.** The verdict: not ready until N-B1's S0 text and the three contract items fold.

## The author's folds after this check (author's claims)

- **N-B1, S0 side:** `fire_solid.md` §1.3's overlap bullet reads "any solid region's present geometry". Its contact
  paragraph reads "a solid region's present face (`subcell_solids.md` §4.1; before S1, its authored primitives)",
  in integer micrometres, keeping F13's sliver rationale. `fire_solid.md` stays at 5,964 words, its base.
- **Wire N7:** §3.1 gives `recipe_id` the sentinel 0xFFFF for `structure` and `inert`.
- **The band's tiling:** §3.1 has glass cut its edge band first, as a ring of tiles exactly `edge_band_um` wide. The
  shading and the closed-form test stay at S3.
- **Wire NS2:** each `structures` row carries its tile counts along length and width, so the client never recounts.
  `welcome` no longer carries `tile_m`, and §12's `client_rendering.md` row now names only the material map.
- **Budgets:** the opening prose was trimmed, so the design is at 6,000 words. `lint_standards` and `check_plan` pass.
