# Spec generator spike, freeze delta 4 (2026-11-22)

One independent reader set the statuses of the author's folds after delta 3 (`freeze_delta3.md`), read from the
working tree on top of 11db101. This is a condensed record of the reader's hand-back.

**Verified by the reader, by running code:**
- the splits rerun byte for byte under PYTHONHASHSEED 0 and 1, and the ids per split equal 91ebd0d's;
- stripping the new tags gives the previous prompt body byte for byte;
- 33 targeted cases and 20,000 random mutations of `split.py`'s input raise only `ValueError`;
- ruff, format and `mypy --strict` are clean;
- `arms.yaml` loads;
- plan.md is 2,489 words.

## The reader's statuses

| Fold | Status |
|---|---|
| NEW-B, the template tags and §6's diagnostic | open: the tags miss prompts their own definition covers (NEW-D), and the change departs from an owner ruling (NEW-E) |
| NEW-A, `split.py`'s checks | fixed, with one remaining NIT (NEW-C) |
| The disclosure | fixed: 21 calls = 12 + 6 + 1 + 2, consistent with lesson 33 |
| Lesson 33 | fixed: "four to five minutes" (264 s and 305 s) and "about 8.6 minutes" hold |
| The plan's header | fixed |
| `arms.yaml` | fixed: the host is undisclosed, and the overflow class agrees with M1 and with A3's loop |

## New findings

- **NEW-D, SHOULD-FIX, `prompts_source.yaml::template`:** about 17 clear misses.
  - Glass-paned and hollow boxes: g04, g05, g16, g20, g27, m28, f30, m30, f27, m38 and m14.
  - Tops on four legs: f15, f06, f40, f41, i24 and f10.

  None is a clear false positive; f09, m25 and m24 are borderline. The counts can't be checked, because the tag
  records no category. If the misses stay, the "without template" set keeps template-shaped prompts, and the
  diagnostic understates the examples' effect.
- **NEW-E, SHOULD-FIX, `freeze_delta2.md`, the owner's rulings:** the ruling says "without furniture", while the plan
  now says "without prompts tagged `template`". The change needs the owner's ruling, recorded.
- **NEW-C, NIT, `split.py::_checked`:** two `breaks` labels swapped in opposite directions keep the sizes, so they pass
  and change the deal. Texts are compared case-sensitively.
- **NEW-F, NIT, the disclosure:** it doesn't say whether the two replies read were with or without the switch.
- **NEW-G, NIT, `arms.yaml::engine.server_flags`:** with a placeholder in it, the string no longer compares byte for
  byte with a run's command line.

**The reader's verdict:** `split.py`, `arms.yaml` and plan.md are ready to hash. The prompt files are not, until
NEW-D folds. NEW-E needs the owner. Nothing is a BLOCKER.

## The author's folds after delta 4 (unreviewed claims)

- **NEW-D:** every listed miss is tagged. The tag now records its category: `legs` (23), `sheets` (34; a hollow box of
  thin sheets or panes, the locker and the aquarium's tank), `post` (10) and `stand` (2). That is 69 of 200.
  `split.py` checks the value against `TEMPLATES`. The borderline f09, m25 and m24 keep their tags. The splits
  reproduce under PYTHONHASHSEED 0 and 1, and the deal is unchanged.
- **NEW-C:** `split.py`'s comment states the limit. Swapped labels are left to review, because the source is reviewed
  content. Case-sensitive text comparison is left as is.
- **NEW-F:** "with the switch".
- **NEW-G:** each run's header records the flags with the address replaced by the same placeholder.
- **NEW-E, the owner's ruling (2026-11-22):** accepted. Plan §6 reports L and H without the prompts tagged
  `template`, replacing "without furniture" in `freeze_delta2.md`'s rulings, because the tags isolate the examples'
  structure wherever it appears.
