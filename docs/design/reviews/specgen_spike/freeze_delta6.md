# Spec generator spike, freeze delta 6 (2026-11-22)

The last pass before the pre-registration. One independent reader set the statuses of the author's folds after
delta 5 (`freeze_delta5.md`), reviewing `git diff 87ed4f5 656421d`. This is a condensed record of the reader's
hand-back.

**Verified by the reader, by running code:**
- the splits rerun byte for byte under PYTHONHASHSEED 0 and 1, and the ids per split equal 91ebd0d's;
- `check_plan` passes at 2,498 words;
- OD-I11 and lesson 36 match Maxim's `origin/main` b98954f7 at every cited line;
- the diff carries no hostname, IP address or email.

## The reader's statuses

| Fold | Status |
|---|---|
| NEW-H, the template tags | fixed: 79 of 200, and each new tag fits the definition; two sibling misses remain (NEW-J) |
| NEW-I, OD-I11 and lesson 36 | fixed: they say what the code shows, and no more |
| OD-I12's citations | fixed for `:62`; the `:156` paraphrase is loose (NEW-K) |
| The foundations plan | fixed, with a placement NIT (NEW-L) |
| The breach gate's port (87ed4f5) | not reviewed: outside the range |

## New findings

- **NEW-J, NIT, `prompts_source.yaml::template`:** two prompts are untagged although their siblings are tagged.
  - m44, a concrete fire pit, has b38's structure (`sheets`).
  - m41, a steel grill on a concrete base, has m24's (`post`).
- **NEW-K, NIT, `roadmap.md::OD-I12`:** the deferred plan prescribes `--reasoning-parser` at `:155-156`, so it treats
  thinking as a parsing problem. It doesn't put `<think>` text in `content`.
- **NEW-L, NIT, `foundations_plan.md` §4:** the compaction moved O57 under npcs §0, but its record is in
  `decisions/boundaries.md`.

**The reader's verdict:** all six files are ready to hash. The one decision left is whether to fold NEW-J first,
because the source can't change after the hash.

## The author's folds after delta 6 (author's claims; no further round)

- **NEW-J:** m44 is tagged `sheets` and m41 `post`, so 81 of 200 are tagged. The splits reproduce under PYTHONHASHSEED
  0 and 1, and the deal is unchanged.
- **NEW-K:** OD-I12 says the plan treats thinking as a parsing problem: `--reasoning-parser` keeps `<think>` text out
  of `content`, but nothing bounds the tokens it spends.
- **NEW-L:** O57 is back under boundaries §0. O56 joins the inference row with O58. `check_plan` passes at 2,500 words.

**Why the rounds stop here.** Delta 6 found two tags and two text NITs. Each pass over the tags has found fewer
misses than the last (17, then 10, then 2), and the tags feed only a diagnostic that no decision rule reads. These
last folds go into the freeze unreviewed. The pre-registration records that the template tags are the author's
judgement, checked by three readers, with any remaining misses accepted as a known limit of the diagnostic.
