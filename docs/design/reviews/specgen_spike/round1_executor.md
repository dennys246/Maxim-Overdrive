# Spec generator spike, round 1: Executor (2026-11-22)

This is a condensed record of the reviewer's hand-back message; review agents can't write files. Scope: the branch's
diff against `origin/main` 98e2342, plus the untracked `research/specgen_spike/plan.md` and `sources.md`.

**What the reviewer checked and found sound.**
- `Ignite(100 kW, 0.3 m)` lies inside `actions.yaml`.
- `region_integrity` and `region_breached` exist, and `SpecRejected` carries `.code` and `.field`.
- 4 m is a whole multiple of 0.2 m.
- The strata sum to 200, and 200 × 8 × 4 × 2 = 12,800.
- `check_plan: PASS`, and plan.md is 2,459 words.

**No proposed fix is verified.** The reviewer read every cited code path: `place` and `_read`, `Box.mask` and
`Cylinder.mask`, `_check_alignment`, `footprint_of`, `Applier._ignite`, `World._power_field`, `region_breached`,
`region_integrity`, `refusals.agent_text`, `actions.yaml`, and the crate in `test_cross_tier.py`.

## BLOCKER

- **B1, plan §5 M5(b) and the composite: there is no "breach threshold".** `damage.region_breached` is topological:
  a connected hole of destroyed cells across the region's thinnest axis. No integrity value marks a breach, so the
  0.1 band can't be computed, and the headline good-spec rate is undefined. The 0.1 is also a round-number band on a
  physics outcome.
- **B2, plan §6: the decision rules can conflict, and "stop" passes vacuously.**
  - "Go" rule 1 compares the best arms, while "stop" compares the A3 arms, so both can hold at once, with no
    precedence.
  - "Stop" has no absolute floor: two models that both fail overlap, and the rule then says no training is needed.
  - The rule doesn't say which interval it uses.
  - Rule 2's "failures concentrate" has no threshold.
- **B3, plan §5 M6 and the composite: no headline if the judge fails κ.**
  - Without a judge, only the owner's 300 labels exist, about 7 per arm, backend and stratum cell, so the composite
    can't be computed for the other samples.
  - A stratified random 300 can't support §6's paired bootstrap over prompts.

## SHOULD-FIX

- **S1, plan §5 M5.**
  - 60 turns isn't clear of the air runaway: `actions.yaml` warns of it past about 30 turns, and thin parts hold far
    less fuel than the 0.6 m crate.
  - Specs with fire on air are in the runaway from turn 1.
  - Unbreached specs agree vacuously: those with fire on air, and concrete or steel ones.
  - The breach base rate isn't reported.
  - The composite charges the generator with the known 0.2 m lag.
- **S2, plan §5 M1 and M3: a spec partly outside the world is accepted and silently clipped.** `place` doesn't check
  the grid's extent, and the plan sets no coordinate convention.
- **S3, plan §3 A3: the feedback text is ambiguous.** The exception message and `agent_text` (code plus field) are
  different things, and the messages quote metres while the local arms decode centimetres.
- **S4, plan §4: the hosted API takes no seed.** The reviewer marks this unverified.
- **S5, plan §2 and §3.** The units differ between backends (cm integers against metre floats), which confounds every
  comparison between them. Local A0's units are unstated, and "2B or 4B" is left open.
- **S6, plan §3 and §4: the frozen inputs don't exist, so they can't be hashed.** `arms.yaml` and `prompts.yaml` are
  missing, one file can't freeze the split on its own, and nothing orders writing them before the freeze.
- **S7, plan §6:** which split the rules read is unnamed.
- **S8, plan §4:** the impossible stratum's right answer isn't scored, and it lowers the composite.
- **S9, plan §5 M6:** κ's weighting, its interval method and the label strata are unstated, and 0.6 gates §6.
- **S10, plan §5 M5(c):** fragility is undefined for specs with more than one material, which is 80 prompts.

## NIT

- "Rejection 13" is defined nowhere.
- The spacing for M1 and M5(a) is unstated.
- M2(c) misses a single floating leg, and §8 overstates what it catches.
- M7's denominator is ambiguous.
- §6 rule 1 picks the best arm after the fact.
