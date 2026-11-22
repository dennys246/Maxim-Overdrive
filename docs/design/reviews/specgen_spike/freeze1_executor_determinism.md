# Spec generator spike, freeze round 1: Executor, Determinism and replay (2026-11-22)

This is a condensed record of the reviewer's hand-back message. Everything was run from scratch copies, and nothing
in the repo was written.

## BLOCKER

1. **i14's and i17's texts are cut short in the generated files** (verified). Their unquoted commas inside YAML flow
   mappings split each text into a short `text` plus a null key. i17 then fits the budget: 432 kg, so it no longer
   breaks mass. Fix (verified): quote them. The deal is unchanged, because it goes by index.
2. **`split.py` doesn't hold prompts to their keys,** and `safe_load` keeps the last of two duplicate keys without a
   word. It also doesn't check:
   - the `breaks` values;
   - empty `expect` lists;
   - unique texts;
   - unknown keys.
3. **The bollard example nearly answers b01, b02, b03 and m19,** three of them in the dev split. Weaker overlaps: the
   aquarium with g25, and the locker with g19.

## SHOULD-FIX

4. **The plan can't run exactly from these files.**
   - (a) There's no block saying which arm gets the grammar, the examples and the retries.
   - (b) The cm-to-m arithmetic is unstated: `v*0.01` and `v/100` differ for 35 of the values 0–300, which changes
     masses, SpecIds and digests.
   - (c) A0's parsing: fences, prose, keys.
   - (d) The chat template, and Qwen's thinking mode against the grammar (unverified).
   - (e) Sampler settings beyond temperature.
   - (f) A3's protocol: multi-turn or not, retry seeds, a fresh scene, whether a lone `too_small` ends it, and what is
     fed back for an object accepted partly outside the world (a cylinder at centre (0, 0) with r 60 cm is accepted).
   - (g) How the example replies are serialised.
   - (h) How a truncated reply is classed.
5. **A3's feedback is about one bit, and `field_map` is dead under the grammar.**
   - `out_of_range` carries no field and no primitive index.
   - `over_budget` covers both mass and extent.
6. **The grammar** (llama-cpp-python 0.3.35's converter accepts the schema; the server's C++ converter is unverified).
   - With a `pattern`, `minLength` and `maxLength` are dropped, so names over 64 characters are possible.
   - Cylinder extent is unbounded (centre plus radius), while a box can't exceed 300 cm. So M8's extent prompts
     measure the grammar under A1–A3.
7. **Several possible prompts exceed 500 kg at natural size:** b38, b30, b15, b10, b40 and b06.

## NIT

8. The docstring's "rounded to the nearest" is inaccurate: the two halves are broken in opposite directions, and
   `HELD_OUT` is hard-coded. `MATERIALS` is a copy of the table.
9. Determinism holds only per NumPy and PyYAML version (numpy 2.5.5, PyYAML 6.0.3). Write both into the headers.
10. M2(a)'s exemption by stratum misses one-block impossible prompts.

## Verified

- The examples' placement table and masses (4.992, 260.212, 165.308 and 101.622 kg).
- `split.py` is byte-identical across three hash seeds, giving dev a724b0b7… and held-out 01dbfc00….
- Ruff, format and `mypy --strict` are clean, and `lint_inputs` finds nothing.
- The gate doesn't cover `spikes/`.
