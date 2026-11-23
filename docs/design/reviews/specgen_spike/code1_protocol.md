# Spec generator spike, code round 1: protocol fidelity (Wire integrity and Architecture) (2026-11-22)

A condensed record of one independent reader's hand-back on 1761097: the generator, scorer and errata against the
frozen `plan.md` and `arms.yaml`. The reader ran `test_spike.py` (17 passed) and a smoke script calling `burn.burn` and
`score.decision` on synthetic data.

**Verdict:** the generation protocol traces cleanly from the frozen text to the code. The scorer has one BLOCKER and
several missing or unguarded metrics.

## The trace, in brief

**Matched:**
- the arms;
- every pinned sampler;
- the seeds and `retry_seed`;
- thinking off (PyYAML reads `off` as `False`);
- `max_output_tokens`;
- the schema, sent unmodified with its key order;
- the exact instruction, user and feedback strings;
- compact example serialisation;
- cm to m by `v/100`;
- `drop_before_place`;
- A0's parse;
- the truncated and overflow classes;
- A3's order, end conditions, scored attempt and fresh scene;
- the scene and offset;
- M1, M2, M4 and M7;
- §6's rule logic;
- the bootstrap parameters;
- the template diagnostic;
- the run header.

**Partial:**
- M3: `_voxel_m3` returns 0.0 on any refusal;
- M6: label rates are never computed;
- M8: labels are never read;
- M9: completion tokens only;
- the §7 record: `weights_sha256` is copied from the manifest.

**The power statement's arithmetic checks:** 1.96·0.5/√120 = 0.089 and 1.96·0.5/√30 = 0.179.

**The errata:** E1, E3 and E5–E7 are true, and the E6 quotas reproduce (37/30/22/38 gives 9/7/5/9). E2 is true in
substance (empty content with `finish: "stop"` also ends the loop). E4's reading is fine, but its premise is half
wrong: `World` still defaults to 6 s. E8 describes ratios the code doesn't compute. Missing: the plan says "300
renders", the code emits up to 320 items (M8's 20 added), and only M1 passes are rendered.

## Findings

**BLOCKER 1, `score.py::decision` and `paired_delta`:** a missing sample or label counts as "not good" without a
warning. Verified: S-A3 samples only, all labelled yes, no R file, and `decision` returns rule 1 with L = 1.0 and
**H = 0.0 from n = 120**. R runs in windows, so a partial file gives a pre-registered decision from incomplete data.
Fix (unverified): refuse unless every (S and R, A3, paired prompt, seeds 0–3) sample exists exactly once and every
M1-passing key row has a label; test it.

**SHOULD-FIX:**
- **1, `score.py::score`:** the bootstrap stream depends on which runs are loaded and on the mode, because earlier
  metrics draw from the one generator first. L's interval changes when unrelated cells are included, and the emit and
  labels runs disagree. Fix (unverified): a fixed position in the stream per bootstrap, or one generator each (an
  erratum against §7's "one Generator"), with a test.
- **2, `score.py::load`:**
  - it ignores headers and splits, and counts duplicate rows, so dev and held-out files pool and a rerun counts twice;
  - nothing compares the run headers with the scoring tree.

  Fix (unverified): carry the split from the header, refuse duplicates, mixed splits and hash mismatches.
- **3:** M6's label rates per set, the `hard: shape` breakdown and M8's closest-fit fraction are computed nowhere.
- **4, `generate.py::header`:** `weights_sha256` is the manifest's value, asserted rather than measured; the model check
  matches the file name only.
- **5, `generate.py::check_server`:** the server's context size isn't checked, though the overflow class depends on it
  (`/props` exposes `default_generation_settings.n_ctx`, unverified).
- **6, `HEADER_KEYS_THAT_MUST_MATCH`:** it leaves out `data_sha256`, `lockfile`, `simcore_commit` and `runtime`. An
  edit to the material table between R's windows would change A3's refusal paths under the old header.
- **7:** `decision`, `paired_delta`, `m3` and `burn` have no tests. Deleting `and d["lo"] > 0` turns nothing red.

**NIT:**
1. the "every other sampler is pinned off" claim isn't enforced in the request;
2. any `thinking` value other than `False` silently sends nothing;
3. `grammar_hash` hashes the schema, so it should be named `schema_digest`;
4. the thin fraction is a mean of per-spec ratios;
5. `_voxel_m3` should count refusals apart;
6. the blind sheet shows each item's `set`;
7. M9 omits prompt tokens and E8's ratios;
8. `score.check` lets both processes write one labelling directory, and `done_samples` crashes on an empty file or a
   torn last line;
9. E4's premise.
