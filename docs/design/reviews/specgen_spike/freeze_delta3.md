# Spec generator spike, freeze delta 3 (2026-11-22)

One independent reader set the statuses of the author's folds after delta 2 (`freeze_delta2.md`), read from the
tree at 11db101, and read the diff from 91ebd0d. This is a condensed record of the reader's hand-back.

**Verified by the reader, by running code:**
- `split.py`, rerun from a copy under PYTHONHASHSEED 0 and 1, matches the committed splits byte for byte, and the
  deal (the ids per split) equals 91ebd0d's;
- a scripted fuzz of `split.py`'s inputs;
- ruff, format and `mypy --strict` are clean;
- `arms.yaml` loads;
- plan.md is 2,496 words;
- the run-time arithmetic: 6,400 generations per model, about 8.9 h for S and 62.2 h for R before retries.

## The reader's statuses

| Finding | Status |
|---|---|
| NEW-1, the S5 record, NEW-3, NEW-4 | fixed |
| NEW-2 | fixed for the earlier cases; other cases remain (NEW-A) |
| i22 and i29 | fixed: each now breaks only the primitive count at a natural build (about 340 kg and 20 kg) |
| f31 and m22 | rejected as a defect, by the owner's ruling |
| 4(d), the thinking switch | fixed, on the recorded evidence; it needs the mini to rerun |
| The templates' residual risk | fixed as wording, but see NEW-B |

## New findings

- **NEW-A, NIT, `split.py`:** some inputs still raise other errors:
  - a list or mapping `id`, or a null or integer stratum, raises `TypeError`;
  - an integer `id` passes;
  - a relabelled `breaks` changes the deal silently.
- **NEW-B, SHOULD-FIX, plan §6:** "without furniture" doesn't isolate the template bias. Template-shaped prompts sit in
  other strata: glass and mixed tables, counter cabinets, a safe on a stand, objects on posts.
- **SHOULD-FIX, the disclosure against lesson 33:** the two disagree on how many calls ran without the switch, and on
  what the lesson's "19 replies" are.
- **NIT, lesson 33:** Gemma's reasoning stayed under the budget, so "spends the whole budget" overstates it for Gemma.
- **NIT, the plan's header:** four problems:
  - the freeze list leaves out `prompts_source.yaml` and `split.py`;
  - R's line duplicates §2;
  - the title is stale;
  - R's licence is unstated.
- **NIT, `arms.yaml`:** the server flags don't bind the server to the Tailscale address, and a context overflow has
  no class.

**The reader's verdict:** `split.py` and the splits are ready to hash. `arms.yaml` is ready apart from `--host`. The
plan and the prompt files need NEW-B's fold first, and the disclosure must be exact before the freeze. None is a
BLOCKER.

## The author's folds after delta 3 (unreviewed claims)

- **NEW-B:** 52 prompts are tagged `template: true`, defined in `prompts_source.yaml`'s header. The tag means the
  object shares an example's structure:
  - a top on four legs (17);
  - a hollow box of thin sheets (23);
  - a part on one post or pedestal (10);
  - a box on a stand (2).

  Plan §6 reports L and H without the tagged prompts. The deal is unchanged.
- **NEW-A:** `split.py` requires a string id, list strata, `template` true when present, and the `breaks` group sizes
  in `BREAKS_SIZES` (10, 10, 10). Each of the reader's cases now raises `ValueError`, run by the author.
- **The disclosure:** it lists all 21 calls per model, and names the two replies whose content the author saw.
- **Lesson 33:** "can spend". The 19 replies are itemised. Gemma thought within the budget, for four to five minutes a
  call, then answered.
- **The plan's header:** a new title; the freeze list names all five files; the duplicated R line is gone; R is
  Apache-2.0.
- **`arms.yaml`:** `--host` is the mini's Tailscale address, named but never written. A context overflow is the
  class `truncated`.
