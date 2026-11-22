# Spec generator spike, freeze delta 1 (2026-11-22)

This is a condensed record of one reader covering both freeze lenses. The reader set each status, read from the tree.

**Verified by the reader, by running code:**
- the strict loader refuses duplicate keys;
- all 200 prompts pass, and i14 and i17 are whole;
- the split is 150/50, with the held-out `breaks` at 3/2/2, byte-identical across PYTHONHASHSEED 0, 1 and 7;
- ruff, format and `mypy --strict` are clean, and `lint_inputs` accepts `_StrictLoader`;
- the name pattern caps names at 64 characters;
- the examples' `too_small` table matches;
- the reachable refusals carry no field;
- plan.md is 2,481 tokens.

## The reader's statuses

**Content and Wire.**

| Finding | Status |
|---|---|
| B1, S1, S2, S6 (mass), S7 | fixed |
| S3 | fixed in mechanism, tags incomplete (SF-new-1) |
| S4 | the copies are fixed; the locker as a template is open |
| S5 | open: families still cross the splits (ladder, gate, door, booth) |
| NITs | fixed, except single-material furniture: open |

**Executor and Determinism.**

| Finding | Status |
|---|---|
| 1, 3, 4(a), 4(b), 4(c), 4(e), 4(f), 4(g), 4(h), 5, 6, 7, 9 | fixed |
| 2 | fixed, except empty `expect` and a `TypeError` on a null key (NIT) |
| 4(d) thinking mode | deferred to the mini check before the freeze; the mechanism is unnamed |
| 8 | fixed, but the rounding is unexplained |
| 10 | open (SF-new-1) |

**New defects.**
- **SF-new-1:** i16 and i17 lack `single_ok`.
- **SF-new-2:** the footstool is a template for tables, and m36 had become a near-copy of the aquarium.
- **SF-new-3:** b27 breaks the primitive budget at its stated size.
- **SF-new-4:** A3 leaves truncation, the scored attempt and the check order unstated.
- **SF-new-5:** the plan says "all but one" (it is all four), and its "accepted" metrics exclude specs that are
  `too_small` only.
- **SF-new-6:** `hard: shape` misses slopes (b33, g28), and f48 and g11 have correct square answers.
- **NITs:**
  - the retry seeds overlap the base seeds;
  - i22 and i29 also break extent;
  - nothing asserts the `HELD_OUT_BREAKS` sum;
  - §3 still says "code and field";
  - f31 and m22 are weak echoes of the birdbath.

## The author's folds after delta 1 (unreviewed claims)

- **SF-new-1:** i16 and i17 are tagged `single_ok`.
- **SF-new-2:** m36 becomes "a wooden sentry box with a steel roof". The footstool and locker templates are kept on
  purpose, since examples teach structure and that is what A2 measures; `arms.yaml` says so (the author's
  disposition, also covering S4's locker half).
- **SF-new-3:** b27 becomes solid blocks, 1 m × 1 m × 15 cm (about 360 kg).
- **SF-new-4:** each attempt is checked in this order: truncation, then the bounds check, then `place`. The loop ends
  at the first pass of M1, at truncation, at `too_small`, or after the third retry, and the last attempt is scored.
- **SF-new-5:** "all four". M2, M4, M6 and M7 now read "passing M1".
- **SF-new-6:** b33 and g28 are tagged, and f48 and g11 untagged.
- **NITs:**
  - the retry seed is 100 × attempt + seed;
  - an import-time assert checks the `HELD_OUT_BREAKS` sum;
  - the docstring explains the rounding;
  - errors stringify keys;
  - an empty `expect` is documented as allowed;
  - A0's parse is `raw_decode` at each `{`;
  - §3 says "the code";
  - the thinking mechanism is named (`enable_thinking=false` through llama-server), still to verify on the mini.
- **S5, the author's deferral:** stage 1 runs the held-out split once, for its final table. A held-out test of
  stage 2's generalisation needs its own family-dealt split, designed with stage 2. Trigger: stage 2's design.
- **Single-material furniture, the author's disposition:** intentional. The mixed stratum carries multi-material
  objects.

No further round was run. Before the freeze commit, a reviewer should set these statuses.
