# Spec generator spike, freeze delta 2 (2026-11-22)

One independent reader set the statuses of the author's folds after freeze delta 1 (`freeze_delta1.md`, last
section), read from the tree at 91ebd0d. This is a condensed record of the reader's hand-back.

**Verified by the reader, by running code:**
- `split.py`, rerun from a copy under PYTHONHASHSEED 0 and 1, matches the committed splits byte for byte: 150/50,
  held-out strata 13/10/8/12/7 and `breaks` 3/2/2;
- b27's mass is 360 kg;
- a null key gives `ValueError`;
- `place` raises `too_small` after every budget check (`imagination.py:156`), so ending A3's loop at `too_small` can't
  hide a fixable refusal;
- plan.md is 2,485 words.

## The reader's statuses

| Finding | Status |
|---|---|
| SF-new-1, SF-new-3, SF-new-4, SF-new-5, SF-new-6 | fixed |
| SF-new-2 (m36) | fixed: no prompt nearly copies an example; g19 and m34 are structural echoes |
| SF-new-2 and S4 (templates kept on purpose) | the author's disposition, accepted: deployed imagination ships the same examples, and S-A3 and R-A3 share the bias, so Δ is unaffected. Residual risk: L's absolute level may read high on table- and cabinet-shaped prompts, and only `arms.yaml` says so |
| The NITs: retry seed, the breaks assert, the rounding docstring, stringified keys, empty `expect`, A0's parse, §3's wording | fixed |
| 4(d), the thinking switch | deferred, accepted. Reason: only the mini can check it. Trigger: the mini check, before `arms.yaml` is hashed. R may need a different switch |
| S5, families across the splits | deferred, accepted. Reason: stage 1 tunes nothing on dev and claims no family generalisation. Trigger: stage 2's design. Recorded only in this folder |
| Single-material furniture | the author's disposition, accepted: the mixed and glass strata carry multi-material objects |
| i22 and i29 also break extent | open |
| f31 and m22 echo the birdbath | open, unless the templates disposition covers it |

## New findings

- **NEW-1, SHOULD-FIX, `plan.md`:** 15 words of headroom can't hold the freeze's hashes, R's name and the weights
  hashes, so the pre-registration commit would break the budget.
- **NEW-2, NIT, `split.py::_check_prompt`:** nested lists in `expect`, `breaks` or `hard`, a bare-string prompt and
  repeated list keys raise `TypeError` or `AttributeError`. `version: false` and `version: 0.0` pass.
- **NEW-3, NIT, `prompts_source.yaml`:** b26, b39 and f38 plausibly need diagonals, but aren't tagged `hard: shape`.
- **NEW-4, NIT, `plan.md` §5 M1:** M1 doesn't list `truncated` as its own class.

**The reader's verdict.** The splits are ready to hash. The plan and `arms.yaml` aren't: the plan's budget (NEW-1),
the S5 record, the unverified thinking line, and R isn't fixed.

## The author's folds after delta 2 (unreviewed claims)

- **NEW-1:** the hashes move to `spikes/specgen/freeze.sha256`, which the plan names. The plan was trimmed to 2,497
  words.
- **S5's record:** plan §9 item 4.
- **NEW-2:**
  - every key must be a string;
  - a prompt must be a mapping;
  - each material must be a string;
  - `breaks` and `hard` are looked up in lists;
  - the version must be the integer 0.

  Each of the reader's cases now raises `ValueError`, run by the author.
- **NEW-3:** b26, b39 and f38 are tagged.
- **NEW-4:** M1 lists truncated replies.
- **i22 and i29:** reworded to a 2 m panel of fifty bars and a 2.5 m fence of forty pickets, so each breaks only the
  primitive count.
- **f31 and m22:** the author's disposition is that the templates disposition covers them. An object on a post is a
  structure, not a copy of the birdbath.

The splits were regenerated, and the deal is unchanged (the same ids in each split).

## The owner's rulings (2026-11-22)

The owner accepted each of the author's recommendations:
- **f31 and m22:** covered by the templates disposition.
- **The templates' residual risk:** plan §6 reports L and H without furniture, as a diagnostic only. Superseded by
  the owner's ruling in `freeze_delta4.md` (NEW-E): without the prompts tagged `template`.
- **R:** Qwen3.5 27B at 8 bits, S's family and quantization, so Δ measures scale. Gemma 4 31B was probed and set
  aside.
- **llama.cpp:** frozen at the mini's installed build 10621 (c1d0e7a00), with no upgrade during the spike.
- **P:** stays 0.8.

## A disclosure before the freeze

The mini probe ran the same 21 calls on each of three models, S (Qwen3.5 4B), Gemma 4 31B and R (Qwen3.5 27B), on
six development prompts: f01, b03, g02, m05, m30 and i02.
- **With the thinking switch, 19 calls:** A2 at seeds 0 and 1 for each prompt (12), A0 at seed 0 for each (6), and
  f01's A2 seed 0 again, as a same-seed repeat (1).
- **Without the switch, 2 calls:** f01 at seed 0, under A0 and under A2.

What the author saw:
- **Every call:** mechanics fields only (finish reason, reasoning length, parse, name check, primitive count, token
  counts, speed).
- **Content, two replies only:** S's f01 under A2 and under A0, both at seed 0 and with the switch, printed in part.

Nothing in any arm, prompt or bar was changed because of a reply's content. The six prompts stay in the development
split.

**Measured on the mini (the frozen engine, build 10621):** S runs at about 40 tokens/s (about 5 s per spec), R at
about 8 tokens/s (about 35 s per spec). At those speeds the plan's 12,800 generations take about 9 hours for S
and about 62 hours for R, before A3's retries: three to four days of the mini.
