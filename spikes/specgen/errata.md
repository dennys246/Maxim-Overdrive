# Spec generator spike: errata to the frozen inputs (2026-11-22)

`plan.md` and the five files in `freeze.sha256` are frozen and never edited. Writing the generator and scorer found
places where the frozen text is wrong, vacuous or silent. This file records how the spike reads each one. It is
committed before any data exists, so no reading can be chosen to rescue a result.

The owner accepted this process on 2026-11-22. Each reading below is the author's, and the owner confirms or changes
it in PR review, before the first run. A changed reading means a changed line here, never a change to a frozen file.

| # | Frozen text | What is wrong or missing | The spike's reading |
|---|---|---|---|
| E1 | `arms.yaml` `protocol.a0_parse` comment: "A0 keys in metres, or floats, aren't converted: place refuses them as written" | `place` accepts `min_m`/`max_m` keys, so an A0 reply keyed in metres is accepted, not refused | Metre keys are passed to `place` as written, unconverted, as the comment's first half says; they are scored like any other reply. The comment's prediction is false |
| E2 | `arms.yaml` `protocol` (A3's loop) | No feedback text is defined for a reply that fails to parse | A3's loop ends at a parse failure, and that attempt is scored. Under the grammar, a parse failure can follow only a truncation, which already ends the loop |
| E3 | `arms.yaml` `a3_never_fed_back: [too_small]` | Vacuous: `place` raises `too_small` last, so a `too_small` reply already passes M1 and ends the loop before any feedback | No effect; kept as written |
| E4 | plan §5 M5, "turns 10, 20, 30" | No turn length is named, and T3 retired the 6 s turn for a 0.1 s tick | World time 60, 120 and 180 s: turns of 6 s, the length the plan was written against. M5 is reported only and decides nothing |
| E5 | plan §5 M5 | Silent on refused specs | M5 runs on accepted specs only: a spec refused as `too_small` has no region to ignite |
| E6 | plan §5 M6, the labelling set "drawn with seed 0 and stratified" | No allocation rule across strata | Proportional allocation by largest remainder, ties broken by the plan's stratum order |
| E7 | plan §5 M6 and M8: the 10 trend prompts and the 10 impossible prompts M8 labels | Which prompts are drawn is unstated | Both are drawn by the same `numpy.random.default_rng(0)`, in a fixed order: the labelling set, then the trend set from among the labelling set's 30 prompts, then M8's set from the impossible stratum |
| E8 | plan §5 M9, "per good spec" | "Good" needs owner labels, which exist only for the labelling set | M9 per good spec is computed on the labelled set only; elsewhere the run reports tokens and wall time per sample and per M1 pass |
| E9 | plan §7, "the runtime version" | The field is unnamed | llama-server's `/props` `build_info`, which reads `b10621-c1d0e7a00` on the mini (checked 2026-11-22). The run refuses any other value |
