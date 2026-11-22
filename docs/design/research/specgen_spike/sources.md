# Spec generator spike: sources (2026-11-21, revised 2026-11-22)

What the plan (`plan.md`) rests on, condensed from four research passes on 2026-11-21. Each item is marked:

- **[read]:** the full text was read;
- **[abstract]:** checked against its abstract or a search snippet only;
- **[unverified]:** recalled, not checked.

Re-check fast-moving items (model releases, library flags) when the spike starts.

## Maxim (`origin/main` 688c4b02)

- `src/maxim/imagination/designer.py`: `ImaginationDesigner.imagine`. It infers an archetype from keywords, then calls
  `EntityDesigner.design`, and has 96 unit tests (`tests/unit/test_imagination.py`). It emits no geometry.
- `src/maxim/simulation/entity_designer.py`: `_design_with_llm` uses `llm_router.generate_json` with unconstrained JSON.
- `src/maxim/models/language/closed_local.py`: `LlamaGrammar.from_json_schema`, which only `maxim.advisor` may import.
- `README.md:28` and `docs/experiments/README.md:7`: the claim of learning without fine-tuning.
  `docs/plans/archive/substrate_plan.md:766` (archived) once made custom-trained models a non-goal.
- `docs/plans/archive/asset_foundry_plan.md` and `src/maxim/simulation/foundry.py`: offline generation scored by a
  rubric, with no training.
- `DECISIONS.md` G6 and G16, and `sem.py` `OUTCOME_PROVENANCE`: provenance labels body-consequence records
  (`apparatus` is never learned from). They are not object tags, so the spike doesn't use them.
- `docs/plans/overdrive_refactor_candidates.md:4-8`: game runs never go on Maxim's ledger.

## Generation with a verifier

- **BrickGPT**, ICCV 2025, [arXiv 2505.05469](https://arxiv.org/abs/2505.05469) [read].
- **CADCodeVerify**, ICLR 2025, [arXiv 2410.05340](https://arxiv.org/abs/2410.05340) [abstract].
- **CAD-Recode**, ICCV 2025, [arXiv 2412.14042](https://arxiv.org/abs/2412.14042) [abstract]: a 1.5B Qwen model
  trained on 1M procedural programs.
- **CAD-Coder**, NeurIPS 2025, [arXiv 2505.19713](https://arxiv.org/abs/2505.19713) [abstract]: supervised
  fine-tuning, then GRPO with Chamfer and format rewards.
- **cadrille**, ICLR 2026, [arXiv 2505.22914](https://arxiv.org/abs/2505.22914) [abstract]: online RL beat DPO.
- **DSO**, ICCV 2025, [arXiv 2503.22677](https://arxiv.org/abs/2503.22677) [abstract]: fine-tuning from simulator
  stability labels.
- **ShapeAssembly**, TOG 2020, [arXiv 2009.08026](https://arxiv.org/abs/2009.08026) [abstract]: a DSL of cuboid
  programs.
- **Yue et al. 2025**, [arXiv 2504.13837](https://arxiv.org/abs/2504.13837) [abstract]: RL with verifiable rewards
  narrows pass@k at large k. Disputed in [arXiv 2506.14245](https://arxiv.org/abs/2506.14245).
- **Vendi score**, TMLR 2023, [arXiv 2210.02410](https://arxiv.org/abs/2210.02410), and its orders,
  [arXiv 2310.12952](https://arxiv.org/abs/2310.12952) [abstract].
- **Tam et al.**, "Let Me Speak Freely?", EMNLP 2024 Industry,
  [ACL Anthology](https://aclanthology.org/2024.emnlp-industry.91) [abstract]. The rebuttal is
  [dottxt](https://blog.dottxt.ai/say-what-you-mean.html).

## Tooling and licences

- Anthropic structured outputs: no numeric `minimum`/`maximum`, `minItems` only 0 or 1, no `maxItems`.
  [Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) [read].
- llama.cpp JSON-schema grammars: integer bounds and `minItems`/`maxItems` are enforced, number bounds are not.
  [README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md) [abstract].
- Qwen3.5 small models are Apache-2.0: [model card](https://huggingface.co/Qwen/Qwen3.5-0.8B) [abstract]. Gemma 4 is
  Apache-2.0 as well, and Gemma 3 and earlier are not [abstract].
- Fine-tuning on Apple Silicon: [mlx-lm-lora](https://github.com/Goekdeniz-Guelmez/mlx-lm-lora) (SFT, DPO, GRPO)
  [abstract].
- Nondeterminism at temperature 0:
  [Thinking Machines, 2025](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) [abstract].

## Policy

- Steam's AI content disclosure, with pre-generated and live-generated content and the January 2026 rewrite.
  [Steamworks](https://partner.steamgames.com/doc/gettingstarted/contentsurvey) [abstract].
- US Copyright Office, *Copyright and AI, Part 2* (2025).
  [Announcement](https://copyright.gov/newsnet/2025/1060.html) [abstract].
- *Thaler v. Perlmutter*: the Supreme Court denied certiorari on 2026-03-02 [abstract].
- Prompt datasets: ShapeNet and PartNet are non-commercial [unverified]. StableText2Brick's card shows no licence
  [abstract]. That is why the prompts are written in-house.
