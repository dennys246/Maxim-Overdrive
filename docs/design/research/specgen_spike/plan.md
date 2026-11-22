# Spec generator spike, stage 1: plan (draft, 2026-11-22; reviews folded through freeze delta 3)

**This is a draft, not yet the pre-registration.** It becomes the pre-registration when these are committed
together, before any spike code runs:
- `spikes/specgen/arms.yaml`, holding the schema text, the examples and the feedback wording;
- `prompts_dev.yaml` and `prompts_heldout.yaml`, holding the prompts, dealt from `prompts_source.yaml` by `split.py`;
- `spikes/specgen/freeze.sha256`: the SHA-256 of those five files and of both models' weights;
- this plan.

Those files are reviewed before that commit. After it, no metric, threshold or prompt changes to rescue a result, and
none is reinterpreted.

**The question.** How well does a local model turn a text prompt into an imagined-object spec, the JSON that
`simcore.core.imagination.place` accepts? A good spec is accepted, in the world, not degenerate, and recognisably the
thing asked for. We test four generation regimes, from a bare prompt to a validator feedback loop, on a small model
and on a large reference model. The answer decides whether stage 2 is worth doing: fine-tuning the small model with
the scorer as its reward, toward the reference model's level.

**What it is not.** It is throwaway, like the physics and LLM spikes: code in `spikes/specgen/`, never imported by
`src/`, and no change to `src/`. It claims nothing about Maxim or NPCs and never goes on Maxim's ledger.

## 1. What we found before planning

**Maxim** (`origin/main` 688c4b02). `ImaginationDesigner.imagine` calls `EntityDesigner.design()`, which asks an LLM
for a SEM entity (sensors, modulators, affordances). It emits no geometry, and no plan adds any. Maxim's claim is
learning without fine-tuning (`README.md:28`). So the spec author is a generator on the world's side (O57), never the
agent's imagination. Search terms and citations are in `sources.md`.

**This repo** (`main` 98e2342).
- **The spec is v0:** a `name` and up to 32 boxes or upright cylinders, made of concrete, steel, glass, wood or
  drywall, within 3 m and 500 kg. `place` returns the mass, and each refusal carries a `RefusalCode`.
- **No support or motion:** there is no gravity, support, collision or rotation, and mass feeds no law.
- **Today's physics can't score everyday objects.** Round 1 measured it:
  - **Thin parts vanish or inflate.** Voxelization goes by cell centre, and the result depends on the sub-cell phase.
    A table with a 4 cm top and 5 cm legs (0.0455 m³) keeps 0.007 m³ at 0.1 m when placed at (0.5, 0.5, 0), but
    0.103 m³ at this spike's offset, where its top inflates to a full cell.
  - **Fires on air.** Ignite lands at the authored centroid, under a table's top, where the fire heats air.
  - **The breach test can change axis.** `region_breached` picks its axis from cell extents.

  These are now Known gaps with strict red gates (`architecture.md`). Spec v1's fuel objects (`fire_model.md`) let
  fire judge thin fuel. Load on thin structural members needs a contract `world_model.md` §1.1 doesn't have yet (D31).
  Every result here is tied to v0.

**The literature** (`sources.md`). BrickGPT (ICCV 2025) gets 100% valid output by checking and resampling, against
2.4% for 5-shot prompting alone, so verify-and-resample is the baseline to beat. Reinforcement learning against a
checker narrows diversity (Yue et al. 2025), and a physics reward invites degenerate answers, so both are measured
from the start.

## 2. Owner decisions (2026-11-22, O56, O58, D34)

1. **Scope.** O56 allows the spike outside the core.
2. **Both models run locally, on the owner's Mac mini** (M4 Pro, 48 GB) over Tailscale. That follows O58: local
   models first, with hosted models only ever the player's opt-in. The model server binds to the mini's Tailscale
   address only.
   - **Small model S:** Qwen3.5 4B at 8 bits (Apache-2.0), the model stage 2 would train.
   - **Reference model R:** Qwen3.5 27B at 8 bits (Apache-2.0), S's family, so Δ measures scale (owner, 2026-11-22).
   - **No Llama-family or hosted model:** nothing is spent, and no prompt leaves the owner's machines.
   - **Decoding:** llama.cpp (build 10621) with a JSON-schema grammar. Every arm emits whole centimetres as bounded
     integers, which the scorer converts to metres.
3. **Product bar P = 0.8.** This is the good-spec rate an imagination feature would need to ship, used by §6. It may
   be tuned before the freeze. A change after the run is a recorded owner decision, and the report still gives the
   result at 0.8.
4. **Labels.** The owner labels §5's labelling set blind, about 2 hours.

## 3. Arms

Each arm runs on S and on R.

| Arm | Decoding | Prompt | Feedback |
|---|---|---|---|
| A0 | unconstrained, parsed after | the schema described in words | none |
| A1 | grammar-constrained | same | none |
| A2 | grammar-constrained | plus 4 hand-authored examples | none |
| A3 | as A2 | as A2 | up to 3 retries |

- **A3's feedback** is each refusal's `agent_text`, the code an NPC would read, with no echo of the
  model's own values. A3 is the BrickGPT analogue at whole-spec grain, and it tests whether refusals steer.
  `too_small` is never fed back (D34): it would teach the model to thicken parts to suit the grid. The refusals a
  grammar-constrained reply can reach carry no field, so A3 tests steering by the code alone. The protocol (retries,
  seeds, parsing, serialisation) is `arms.yaml`'s.
- **Coordinates.** The prompt states the convention: the object's minimum corner is at its origin, so every
  coordinate is at least 0. A free-text `intent` field comes before the geometry and is dropped before `place`.

## 4. Prompts and sampling

- **200 prompts**, written in-house, with category names only borrowed from public sets (ShapeNet and PartNet are
  non-commercial).
  - 150 are the development split, in `prompts_dev.yaml`; §6 reads only this split.
  - 50 are the held-out split, which runs once for the final table after §6 is decided.
- **Strata:**
  - wooden furniture, 50;
  - barriers and structural pieces, 40;
  - objects with glass, 30;
  - mixed-material objects, 50;
  - **impossible objects, 30:** each breaks a budget. They are scored apart (M8) and left out of the composite.
- **Expected materials.** Each prompt lists the materials it must contain where the object leaves no doubt.
- **Sampling.** 8 samples per prompt, arm and model, at temperature 0.7 with seeds 0–7. That gives 12,800
  generations plus A3's retries, all on the mini.

## 5. Metrics (fixed here, before any measurement)

Every object is placed in an empty 4 × 4 × 4 m air scene at the offset (0.503, 0.503, 0.003) m.
- **No knife edges.** Faces given in whole centimetres then miss every cell centre at 0.2, 0.1 and 0.05 m. A cylinder
  can't tie either: delta 1 found the nearest miss to be 0.7 µm.
- **The truth grid is 0.1 m** (`world_model.md` §1.1), and every metric below uses it unless it says otherwise.
- **Rates** come with prompt-clustered bootstrap intervals: 95%, percentile, 10,000 resamples, seed 0. They are
  reported per arm, model and stratum.

The metrics:
- **M1, acceptance.** The fraction that `place` accepts and whose placed bounds lie inside the world. The scorer checks
  the bounds, since `place` doesn't (a Known gap). Rejections are broken down by `RefusalCode` and field.
  "Outside the world", truncated replies and A0's parse failures are their own classes.
  - **`too_small` is a world outcome, not a generator failure** (D34). `place` refuses objects of thin parts depending
    only on where they land on the grid: two of the four examples are refused at 0.1 m, and all four at some
    spacing. M1 reports it apart. A spec
    refused only as `too_small` passes M1 if every other check holds, judged in metres by the scorer: the materials,
    the 3 m extent, the 500 kg mass from authored volume, the 32-primitive count and the bounds.
- **M2, degeneracy.** A spec that passes M1 is degenerate if any of these holds:
  - (a) it has one primitive and its prompt isn't marked `single_ok` (one primitive is a correct answer);
  - (b) it uses one material where two or more are expected;
  - (c) its primitives' contact graph, judged in metres from authored shapes (touching or overlapping), with the
    floor (z = 0) as one more node, has more than one component: a floating part.

  Also reported: the fraction of authored volume in primitives whose smallest side is under 0.4 m, the thin-feature
  rule.
- **M3, voxel fidelity.** The voxelized volume over the authored volume, at two offsets: the scene offset and that
  offset plus half a cell. Also whether `place` accepts the spec at 0.2 m (`TOO_SMALL` depends on the spacing). This
  is reported only: it measures the world, not the generator.
- **M4, material fit.** Over prompts with expected materials, the fraction of specs passing M1 that contain all of them.
- **M5, burn diagnostic.** This is reported only, never part of the composite or a stage-2 reward until spec v1,
  because it measures known gaps. On the shipped path: run `place`, then `Applier.apply(name, Ignite(100 kW,
  0.3 m))`, then record:
  - (a) **fire on air:** the fraction of specs with no solid cell inside the fire's sphere at turn 0;
  - (b) for the rest, the turn at which the sphere's solid fraction reaches zero, and region integrity at turns 10,
    20 and 30, censored from that turn on. Past it, the fuel gap heats air.
- **M6, semantic fit.** Each spec passing M1 is rendered from its authored primitives (three orthographic views and one
  isometric view, coloured by `color_rgb`), not from voxels, so M6 judges the generator. The owner labels 300
  renders blind: "yes / partly / no".
  - **Paired, 240.** 30 dev prompts, drawn with seed 0 and stratified over the four possible strata, × samples 0–3 ×
    S-A3 and R-A3.
  - **Trend, 60.** Samples 0–1 of 10 of those prompts × S's A0–A2, as descriptive context only.
  - There is no LLM judge, so only owner labels decide.
  - Prompts marked `hard: shape` need a shape the primitives can't make; their labels are reported apart.
- **M7, diversity.**
  - Among each prompt's samples passing M1, the number of distinct `SpecId`s (`ip_and_licensing.md` §6).
  - The Vendi score at orders 0.5 and ∞, with a kernel of volume IoU between authored shapes. The IoU is computed on a
    1 cm analysis raster, not a world grid, after each spec's minimum is moved to the origin.
  - The denominator is the samples passing M1. Prompts with fewer than 2 are counted, not scored.
- **M8, impossible prompts.** The fraction accepted, and whether each accepted spec is the closest object that fits,
  scaled down only as far as the limits require, labelled by the owner on samples 0–1 of 10 such prompts for S-A3.
  The grammar bounds a box at 300 cm, so for extent prompts under A1–A3 acceptance partly measures the grammar; A0
  is reported beside it.
- **M9, cost.** Tokens and wall time on the mini per good spec.

**The composite, defined now.** A sample is a *good spec* if it passes M1 (accepted, or refused only as `too_small`) and
is in the world, not degenerate (M2), and labelled "yes". Physics and cross-grid agreement stay out until spec v1: a
generator rewarded for avoiding simcore's known gaps would learn the gaps, not objects.

## 6. Decision rules for stage 2

These apply to the paired labelling set only. L and H are the good-spec rates of S-A3 and R-A3, each with its
prompt-clustered interval. Δ is H − L, with a paired bootstrap over the 30 prompts. The rules are checked in order,
and the first that holds decides:

1. **Stop, the small model suffices:** L's lower bound is at least P. S-A3 becomes the Phase 6 caller candidate.
2. **Stage 2 goes ahead:** H's lower bound is at least P, and Δ's interval excludes zero, with H higher. The reference
   model shows a level worth having, and fine-tuning S could close the gap. Its reward waits for the sub-cell solids
   contract (D34), so the world can judge thin parts itself.
3. **Neither:** in every other case, this data doesn't justify training. The report says which failure classes
   dominate, and the owner decides. A larger model or spec v1 may need to come first.

L and H are also reported without prompts tagged `template` (sharing an example's structure), as a diagnostic only.

**Power.** The 120 samples per arm are 30 prompts of 4 correlated samples each. With within-prompt correlation ρ, the
design effect is 1 + 3ρ, so near a rate of 0.5 a half-width is about ±0.09 when ρ = 0 and ±0.18 when ρ = 1. A Δ under
roughly 0.25 can therefore fall under rule 3.

Known gaps that M3 and M5 measure go to `docs/architecture.md` with their numbers, whatever the decision.

## 7. Determinism, records and isolation

- **Generation isn't reproducible,** so the committed JSONL is the truth and is never regenerated. Each sample
  records:
  - prompt id, arm, model and the weights' SHA-256;
  - runtime version and machine;
  - sampler settings and seed;
  - grammar hash;
  - the raw reply and each retry's refusal.
- **Each run's header** records the simcore commit, the lockfile hash, the digests of `data/materials/core.yaml` and
  `data/world/actions.yaml`, the scene, the offsets, and the hashes of the arm and prompt files. The owner's labels
  are committed as their own file.
- **Scoring is deterministic** over those files on one machine. Every bootstrap and draw uses one seeded
  `numpy.random.Generator`. `score.py --check` scores in two processes with different `PYTHONHASHSEED` and compares
  digests. Across machines only the outcome class is promised: cylinder masks use `pow` (B28), and Vendi's
  eigenvalues use BLAS.
- **Where it lives.**
  - Code in `spikes/specgen/`; the write-up in `docs/design/research/specgen_spike/results.md`.
  - It imports only simcore's public API, plus `yaml.safe_load` and `json`, and runs in its own `.venv` on each
    machine.
  - Only `generate.py`, run by hand, calls a model; `tests/` never does.
- **Scope guard.** If scoring needs a change in `src/`, the spike stops and asks.

## 8. What stage 1 cannot tell us

- physical plausibility of furniture-scale objects, which waits on spec v1, D31 and D33;
- combustion realism;
- whether hosted models do better (O58 makes them an opt-in, not the target);
- how NPCs would use generated objects;
- whether players like them.

## 9. Follow-ups raised now

1. **Steam and copyright.** Shipped generated specs are pre-generated AI content under Steam's disclosure. Runtime
   imagination is live-generated, and `place` and the IP gate are its guardrails. Raw outputs are likely not
   copyrightable (US Copyright Office, Part 2, 2025). This goes into `ip_and_licensing.md` when it is reviewed.
2. **Weights are assets.** A stage 2 model needs a licence and source entry, and provenance for its training data.
3. **The minimum hardware (O58).** The mini's measured cost per good spec (M9) is that budget's first data point.
4. **Stage 2's held-out split is dealt by family:** doors, ladders and booths cross today's split (freeze delta 1, S5).

Reviews: `../../reviews/specgen_spike/`. Sources: `sources.md`.
