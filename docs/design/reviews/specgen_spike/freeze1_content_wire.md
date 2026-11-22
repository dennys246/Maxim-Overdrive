# Spec generator spike, freeze round 1: content validity and Wire integrity (2026-11-22)

This is a condensed record of the reviewer's hand-back message. It covers `spikes/specgen/arms.yaml`,
`prompts_source.yaml`, the generated splits and `split.py`.

**Verified by running code.**
- The split reproduces exactly.
- The examples are connected and within budget, at 5, 260, 165 and 102 kg.
- The `too_small` comment is exact.
- The instructions' densities and budgets match `core.yaml` and `Budget`.
- Every `expect` names only materials the prompt names.
- No brands or IP appear.

## BLOCKER

- **B1, `arms.yaml::instructions`:** "make the smallest object that keeps its intent" literally asks for a miniature,
  so a 20 cm beam answers i01. The plan's M8 shares the ambiguity, so its label has no criterion. Fix: "the closest
  object that fits, scaled down only as far as the limits require", in both places.

## SHOULD-FIX

- **S1, the `arms.yaml` header and `field_map`: the claim that the feedback names the field is false on the reachable
  path.**
  - `out_of_range` (max ≤ min) and `over_budget` (mass or extent) carry no field. The refusals that do carry one
    (name, primitives, vector length) are grammar-prevented.
  - A3 therefore tests steering by code alone, and `over_budget` doesn't say whether mass or extent is at fault.
  - A cylinder at centre 300 with radius 150 reaches 450 cm, inside the grammar's bounds.
- **S2, M2(c) against "z = 0 is the floor it stands on":** the scene has no floor solid, so parts that each stand on
  the floor count as floating (b22, b30, m17, m49).
- **S3, M2(a):** a correct one-pane g08 counts as degenerate. Several impossible prompts are naturally one primitive.
- **S4, near-copies of the examples:** b01, m19, g25 and b02 are copies of the bollard or aquarium examples, and the
  locker is a template for six prompts.
- **S5, near-duplicates across splits:**
  - door: f34 and m08;
  - ladder: i06 and b14, m15 and i21;
  - safe: i11 and m34;
  - bunk bed: m50 and f21;
  - gate: f33 and m16;
  - booths and counters within dev.

  Harmless for stage 1, but it matters for stage 2's held-out generalisation. Fix: deal by family.
- **S6, "every possible prompt fits" fails at realistic sizes:** b38, b30, m27, g22, b10, m36, b27, b40, g07 and
  g29. Shapes the primitives can't make: g11, g23, f48, m36, m23, m09, f11 and i10. Reword them or record them as hard
  cases.
- **S7, i03 has a reading that fits:** 20 seats around a 3 × 3 m table.

## NIT

- i09 breaks extent and mass both.
- The held-out impossible prompts aren't balanced by `breaks`.
- The rule "cylinder centre minus radius ≥ 0" is unstated.
- How the examples are serialised isn't frozen.
- Overlapping primitives count twice in mass.
- The examples' thin parts raise `too_small` under A2 and A3.
- Furniture is single-material only.
