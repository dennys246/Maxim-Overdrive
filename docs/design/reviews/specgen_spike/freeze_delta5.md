# Spec generator spike, freeze delta 5 (2026-11-22)

One independent reader set the statuses of the author's folds after delta 4 (`freeze_delta4.md`), read from the
tree at d0bb15e. It also checked the lesson renumbering and the new Phase 3 rows against Maxim's `origin/main`
b98954f7. This is a condensed record of the reader's hand-back.

**Verified by the reader, by running code:**
- the splits rerun byte for byte under PYTHONHASHSEED 0 and 1, and the ids per split equal 91ebd0d's;
- 3,000 mutations weighted to `template` raise only `ValueError`, and only the exact category strings are accepted;
- ruff, format and `mypy --strict` are clean;
- plan.md is 2,489 words;
- the lessons run 1 to 36 with no gaps or duplicates;
- the diff carries no hostname, IP address or email.

## The reader's statuses

| Fold | Status |
|---|---|
| NEW-D, the category tags | fixed for all 17 listed misses; counts 23/34/10/2 check. Consistency misses remain (NEW-H) |
| NEW-C, NEW-F, NEW-G | fixed |
| NEW-E | fixed: plan §6 and the superseded ruling's pointer agree (the ruling is the author's record of the owner) |
| The renumbering to lessons 35 and 36 | fixed: every live citation points at the right lesson |

## New findings

- **NEW-H, SHOULD-FIX, `prompts_source.yaml::template`:** tags that contradict the file's own tagging. f25 and f42
  (counters) and b38 (a hollow concrete wall) are untagged, while their siblings are `sheets`. f37 and f39 (on legs)
  and m31 and m45 (on a post) are untagged. The bookshelves f04, i08 and i27 are arguably `sheets`.
- **NEW-I, SHOULD-FIX, `roadmap.md::OD-I11`:** the claim is too broad. `_ensure_client` (`openai_backend.py:273-275`)
  does refuse a blocked URL, but only for providers keyed `openai_compatible` or `openai_compat`, while the router
  dispatches on type (`router.py:467-474`). The defect is a guard keyed on the name. Lesson 36 has the same sentence.
- **NIT, `roadmap.md::OD-I12`:** `chat_template_kwargs` is named at the deferred plan's `:62` ("vLLM-only payload
  fields"), not in its "Not in scope". The rest of OD-I12 and the "no thinking control" claim hold Maxim-wide.

**The reader's verdict:** `split.py`, `arms.yaml`, the split files and plan.md are ready to hash. `prompts_source.yaml`
is not until NEW-H folds. NEW-I and the NIT don't block the freeze, but must be fixed before OD-I11 goes to Maxim.

## The author's folds after delta 5 (unreviewed claims)

- **NEW-H:** ten prompts are tagged: f25, f42, b38, f04, i08 and i27 as `sheets`; f37 and f39 as `legs`; m31 and m45
  as `post`. That is 79 of 200 (sheets 40, legs 25, post 12, stand 2). The splits reproduce under PYTHONHASHSEED 0 and
  1, and the deal is unchanged.
- **NEW-I:** OD-I11 and lesson 36 say the refusal is keyed on the provider's name, not its type, with `:273-275` and
  `router.py:467-474`. The author read both at b98954f7. The run's provider was keyed `local`, type `openai`.
- **NIT:** OD-I12 cites `:62` and `:156`, and notes that llama-server takes the same field.
- **Also folded:** the foundations plan lists OD-I11 and OD-I12, with the author's rows compacted to fit 2,500 words
  (2,498; `check_plan` passes). The merge of `origin/main` 2586ed7 needed the breach red gate ported to `main`'s
  Topology and `reductions` APIs (87ed4f5).
