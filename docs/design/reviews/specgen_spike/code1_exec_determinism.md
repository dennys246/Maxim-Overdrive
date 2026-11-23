# Spec generator spike, code round 1: Executor and Determinism (2026-11-22)

A condensed record of one independent reader's hand-back on 1761097. The reader ran the 17 spike tests (they pass)
and `mypy --strict` (clean). Each mechanism was broken in a scratch copy, one mutation at a time.

**Mutation results:**
- **Red (guarded):**
  - the resume skip;
  - `retry_seed`;
  - truncation moved after the parse;
  - bounds moved after `place`;
  - a weakened model-path check;
  - SpecId including the name.
- **Green (unguarded):** listed under the findings below.

**Clean, verified:**
- `score --check` under PYTHONHASHSEED 1 and 2 gives one digest;
- sets are used only for `len` and membership, and the output is key-sorted;
- no wall clock or unseeded RNG reaches a scored value (`wall_s`, monotonic, feeds M9 only);
- the endpoint, loopback and `model_path` appear in no record;
- writes go only to `--out`, `--labelling-dir` and a temporary directory beside `--out`.

## BLOCKER

**B1, `score.py::score` and `decision`:** one generator is shared by blinding and every earlier `rates()` call, so
L, H and Δ are bootstrapped from a stream position that depends on which other files and flags are scored. Measured:
adding one arm's records moves Δ's hi from 0.050000000000000044 to 0.04999999999999993. A Δ near 0 could flip rule 2
on whether the analyst passes the held-out or A0 files: a forking path in a pre-registered decision. Fix (unverified):
one generator per statistic, `default_rng([SEED, *stable_ints(name)])`, recorded as an erratum against §7's "one seeded
Generator".

## SHOULD-FIX

- **S1, `generate.py::done_samples`:** a torn last line gives `JSONDecodeError` on restart, and an empty file
  `IndexError`, both verified. Skipping the fragment isn't enough, because appending would glue onto it. Fix
  (unverified): truncate to the last newline before appending, and treat an empty file as new. No test covers either
  case.
- **S2, `Server.chat`:** any 400 whose body mentions "context" is classed overflow; a 400 "invalid chat template
  context" is recorded `truncated` (verified). Fix (unverified): match `error.type == "exceed_context_size_error"`,
  with a negative test.
- **S3:** a sample that always fails with a 5xx or a timeout never gets a record. `score.load` checks neither
  completeness (150 × 8 per cell) nor duplicates nor the split, and `decision` counts a missing sample or label as
  "not good". Fix (unverified): refuse a cell missing or duplicating a (prompt, seed), and a paired item without a
  label.
- **S4, `score.py::load`:** it never reads headers or compares the frozen and data hashes with the tree. A resume in
  `generate.done_samples` doesn't compare `data_sha256`, `lockfile` or `simcore_commit` either.
- **S5:** guards tested only in their functions. Replacing `check_frozen()` in `header`, or `check_server` in `run`,
  with a bare read stays green, and so does cutting `HEADER_KEYS_THAT_MUST_MATCH` to `("arm",)`. Fix (unverified): one
  `run_cell` test each, with a mutated frozen copy, a wrong `/props`, and a differing header.
- **S6, the build near-miss test:** it can't catch a substring check on the full string, because the case
  `"b106210-c1d0e7a00"` doesn't contain `"b10621-c1d0e7a00"`. Fix (unverified): `"b10621-c1d0e7a00-dirty"`.
- **S7, M1's interval test:** `SEED = 1`, `SEED + 1` and percentiles 5/95 all stay green, because two prompts give
  three bootstrap values. Dropping the impossible-stratum exclusion stays green too. Fix (unverified): pin a digest of
  `score()` on a committed fixture.
- **S8, `spec_id`'s test:** dropping `material` stays green. Fix: a pair differing only in material, and one only in a
  coordinate.
- **S9, `labelling.write_sets`:** it overwrites the sheet and key unconditionally, so a rerun with a partial file set
  drops renders from the sheet the owner is labelling. Fix: refuse when the files exist.

## NIT

- **N1:** the parse-failure end of A3's loop is unguarded and unreachable under the grammar (E2); if reached, its
  feedback would read "refused that object: None".
- **N2:** the `a3_never_fed_back` branch is dead (E3).
- **N3:** `weights_sha256` is copied from the manifest, never measured against the served file.
- **N4:** `score.check` finds `--out` by exact token, so `--out=x` raises.
- **N5:** an empty paired set raises in `paired_delta` and `decision`, which at least fails loudly.
