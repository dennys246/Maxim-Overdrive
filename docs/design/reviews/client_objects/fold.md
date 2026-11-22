# client_objects.md round 1 fold: author's record

**The author's record, not a fold-status table** (O25): reviewers set each finding's status from the tree. Round 1
ran at 51c9660 with six lenses: `executor.md` (E), `architecture.md` (A), `wire_integrity.md` (W), `client_rendering.md`
(C), `performance.md` (P) and `bio_faithful.md` (Bio). Counts: 4 BLOCKER (A-B1, W F1, C B1 and E-B1 the same defect,
E-B2), 29 SHOULD-FIX and 24 NIT. The fold also merged origin/main 98e2342 (#37).

**Corrections to the author's own claims, first.**
- The design assumed fire_model §10.2's order, in which step 8 follows 6.4. The owner moved 6.2–6.4 to Phase 2 on
  2026-11-20, and the Phase 1 exit is the torch-lit slab (A-B1).
- "Exact below 2²⁴" for custom data was false: it is half float on Compatibility (E-B1, C B1, both ran it).
- "R3's sticks, 7.5–15 mm" was the gap between sticks, not their diameter (E-S1).
- The stability bar measured the probe's own sampler (E-B2).

## BLOCKERs

| Finding | Change | How verified |
|---|---|---|
| A-B1 (scoped to a superseded Phase 1) | §1 cites the roadmap's exit first. §2: Phase 1 has no flame object. §3.4: `flames` is Phase 2 and optional. §5.3: Phase 1 flames are client-drawn from `ignited_fraction`, so the flame-shape check runs in Phase 1. §7.3 and owner question 4: the beats' owner's trigger is dead, and nothing yet says how the torch lights the slab | read `docs/roadmap.md` (the exit; Phase 2's "moved from Phase 1" bullet) and `research/solid_spike/results_rerun1.md` §7 |
| W F1 (step 7's checklist orders the retired channels) | `checklists.md` step 7 replaces them with the fuel tables, fuel view, dtypes, non-default-scale `crack` fixtures, the join cap and the `glow` key's retirement. Step 8 gains the object pass. The design's §9 build list is gone; the checklist holds it | diffed the checklist |
| E-B1, C B1 (custom data is half float) | §2 records it [ran] by both reviewers. §4.1: no index in custom data; the first row and `state` live in a per-instance RGBA8 texture indexed by `INSTANCE_ID`; fixtures put rows past 2,048 | not rerun by the author: two independent runs agree, at 2,047 exact and 2,049 rounded |
| E-B2 (the stability measure aliases by itself) | §7.2: coverage integrated over 4 px axial bins, compared across 8 sub-pixel camera offsets, against an ideal anti-aliased line in the same fixture, with the margin taken from the ideal's own spread before the renderer is measured. The 25% bar is gone | the reviewer's numpy on an ideal line (0.22–0.25) and the binned measure (0.060 against 0.027); not rerun |

## SHOULD-FIX

| Finding | Change |
|---|---|
| A-S1 (a 6.0b requirement in a client doc; meanings with two owners) | The fuel view moves to `fire_solid.md` §5.6, built at step 7 with its caller, the encoder, so A-S7's fold stands. fire_solid owns the quantities; this document owns only the wire columns. F1–F3 go to step 8's checklist |
| A-S2, W F9 (stale copies) | Linked or edited: `client_rendering.md` §3.1, §4.1–§4.3, §5.1, §5.3, §5.4, §5.6, §6.1, §6.4 and §12; fire_model §9.2; tile §5.5; FIELDS.md; `architecture.md`; `roadmap.md` l.19; `foundations_plan.md` row 8. §3.5's restatement of §4.2 is cut to a link. Not done: §5.5's tier table (the flame-particle column still applies) and §8's rows (§7.4 states them) |
| A-S3, W F3 (`temperature_c` unmasked) | §5.1 masks by `material` ≠ air, with the filter blending solid neighbours only. The Known gap's steady bound is 36 K per kW/m² (derived). The encoder's constants and `glow` key are deleted at step 7 |
| A-S4 (B42 closed early) | B42 stays open; its trigger is now "step 8, when the provisional reads are deleted" |
| A-S5, C S4 (burning unguarded) | §7.2: a burning check at 600 °C, below the laptop's white band, ≥ 15 L*, failed by deleting the term |
| A-S6 (unsized) | §7.5: about one more #31-sized PR `[engineering]`; plan row 8 and the checklist say so |
| W F2 (collision with #37) | Merged; §3.1 states that a required table or a new kind is a protocol bump and an optional table a registry bump; the kind vocabulary joins `client_rendering.md` §4.1's `welcome` row; snapshot channels and fuel columns registered in `contracts.md` |
| W F4, E-S4 (k past the object) | §4.1 clamps k; §3.2's decoder checks `segment_count` = ⌈L/ℓ − 10⁻⁶⌉ in f64 |
| W F5, E-S5 (denominators) | fire_solid §5.6: residue ÷ remaining solid mass, 0 when none remains; Σ a_p is the segment's area, never 0 |
| W F6 (what step 7 freezes) | §3.1: `<table>.<column>` names; dtypes, with u32 and f32 named for v0; encodings `raw` and `linear`; units `id`, `celsius`, `m`, `ratio`; every column required |
| W F7 (non-default scale) | §7.1: the fire fixture writes `crack` at a non-default scale; the checklist carries it |
| W F8 (a second axis-mapping site) | §4.1: transforms stay in the server's frame and the object shaders include the raymarch's mapping |
| W F10 (send rule and view unspecified) | `client_rendering.md` §4.1 sends on `fuel_version`; fire_solid §5.6 defines the view, its cadence and leak rule |
| W F11 (G2 loses its subject) | §7.3: G2–G4's beats must be restated for the slab (owner question 4); §6.3 says when the slab's top face carries cracks (≥ 0.17 m) |
| E-S1 (stick sizes) | §2 restated: 20 mm stick 0.6–2.4 px, 3.2 mm dowel 0.10–0.38 px |
| E-S2, C S3 (the severity rule contradicts itself and decision 4) | §6.1: monotone by bands; additive; outlines on edges shared with uncracked cells instead of an edge in every cell; owner question 2 records the conflict between decisions 4 and 7 |
| E-S3, C S1 (burn-through per vertex) | §4.2: per-fragment lookup and discard at segment granularity; §7.2's footprint is shrunk by the projected radius. C S1's fix was verified by its reviewer (R2) |
| C S2 (laptop over the bar) | E-B2's measure replaces the bar, at every tier |
| C S5 (char on sticks unguarded) | §7.2: a char-darkening check, ≥ 8 L* |
| C S6 (tier deletion can't fail) | §7.2: fuel ID masks per kind, compared separately |
| C S7, E-N3 (the probe's row readout) | §2 no longer cites the probe for row mapping; E-N3's derivation explains the 0.259 and 0.882 |
| P-S1 (decoder loop) | §3.2: checks run only when key or geometry bytes differ (a 30 µs native compare) |
| P-S2 (rebuild cost and "rare") | §2 and §7.4 cite 3.6–3.8 ms; `state` leaves the rebuild trigger |
| P-S3 (vertex density) | gone with the per-fragment lookup: one ring, +0.24 ms at 2,000 instances |
| P-S4 (join cap) | `client_rendering.md` §4.3 counts the fuel tables at the limits; §3.5 gives 552,336 cells |
| P-S5 (reductions per publish) | fire_solid §5.6: once per physics step and insertion; a B5 row with the stand-in's 13.3 ms |
| P-S6 (flame fill) | §5.3 and §7.4: a frame-time row; 6.2 states a cluster bound |
| Bio S1 (no leak rule) | fire_solid §5.6's leak rule; step 7's checklist names its test |
| Bio S2 (parity) | §5.4 names the three divergences, OPEN against OD-C8 |
| Bio S3 (pick snap) | §4.3: the raw hit point, no snap; the floor's offset (33 mm at 30 px/m) is inside the server's 50 mm reach |
| Bio S4 (the lesson) | rewritten in the file's format as lesson 32 |

## NITs

Folded: A-N1 (exact only while one part has area, fire_solid §5.6), A-N2 and E-N4 (citations), A-N3 (§10 names an
owner for each item), W F12 and E-N1 (tier ID masks aren't built; §7.2 no longer says "kept"), W F13 (Phase 2's
flame needs width), W F14 (kind ids are the vocabulary's), Bio N1 and N2, C N1–N6, E-N2, E-N5, E-N6, P-N1–N3.

Not folded:
- **A-N1's alternative of sending both parts' temperatures.** In Phase 1 a segment flips whole, so this waits for
  6.2's partial transfer.
- **The probe itself** wasn't changed. It records what was measured, and the reviewers' variants live in their
  scratch copies. C S7's head-on row readout goes to step 8's build of the fuel fixture.
