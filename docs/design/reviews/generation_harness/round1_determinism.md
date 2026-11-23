# Generation harness plan, round 1: Determinism and replay (2026-11-22)

The reader's hand-back, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. The reader read `generation_harness_plan.md` at 620b7a0, the Determinism row of `docs/code_review.md`, and the
spike's `generate.py`, `score.py` and `plan.md` §7. No fix was verified.

**A correction to the review brief:** the brief said scoring is reproducible "everywhere". The spike's plan §7 says
only per machine: across machines only the outcome class holds, because cylinder masks use `pow` (B28) and Vendi uses
BLAS. The harness moves `score.py` and `geometry.py` as they are, so it inherits that limit (D2).

## BLOCKER

- **D1, §2 and §7: the plan never says what is reproducible, or how each claim is proven.** Generation on one machine
  and build, scoring, and the battery each need a promise (bit-identical per machine, or outcome class across machines
  and grids), the pins it needs, and the test that proves it. *Failure:* a regression rerun shows a difference, and no
  one can say whether it is the model, float drift across machines, or a rerun that was never bit-identical. *Fix
  (unverified):* a three-row table in §2.
- **D2, §7 H2: one pinned scorer digest fails across machines, or forces the bar to loosen.** The gate runs on the
  Mac, the mini and Linux CI. *Fix (unverified):* a bit-identical digest for the integer and boolean statistics, and
  an outcome-class comparison with a derived band for the `pow` and BLAS ones; optionally per-platform digests from CI.
- **D3, §5: battery verdicts carry no inputs header, so verdicts from different laws or battery versions can mix.** A
  verdict depends on the engine commit, the data, the law versions, the grids, the lockfile, and for U5 the pymaxim
  version. *Failure:* after a fire-law change, stage 2 trains on specs that passed U4 under two different laws. *Fix
  (unverified):* versioned battery output with a pinned header, refused by consumers on a mismatch, as
  `score.py::read_run` refuses frozen-file drift.

## SHOULD-FIX

- **D4, §6 and H1:** nothing forces each header key to be classified. The spike writes `machine` but doesn't make it
  must-match, so a run could resume on another host. Fix: every key is `must_match` or `informational` with a reason,
  and a test fails on an unclassified key.
- **D5, §4:** the slot count, and whether a run is reproducible, aren't recorded or refused at resume, so a
  regression set could mix `max_in_flight` 1 and 4, and batching noise reads as a model change. Fix: both in the
  must-match keys; regressions refuse non-reproducible runs; a property test that shuffles records.
- **D6, §2 and §4:** llama-server reuses the KV prefix by default (`cache_prompt`), even with one slot, so a reply can
  depend on the previous request, and a resumed run can differ from an uninterrupted one. Under the gateway, a
  timeout also becomes an outcome that depends on load. Fix (unverified): pin `cache_prompt: false` for reproducible
  jobs; record timeouts and retries; exclude timed-out records from identity claims. Unmeasured on Metal; it is H1's
  test.
- **D7, H3:** the battery's independence test covers only the hash seed. Fix: a spec's verdict alone equals its
  verdict in a shuffled batch, the same under 1 and N BLAS threads, and budgets in turns, never seconds.
- **D8, §1:** a regression rerun must differ from its baseline in exactly the variable under test. A model change, an
  engine-build change and a format change each regenerate (or re-parse for a format), and a law change reruns only the
  battery. Fix: compare two headers and refuse unless they differ only in the declared variable.
- **D9, U2, U3 and U10:** binary verdicts compared across machines need the outcome margin, or float drift reads as
  flip-flops. Fix: a third value, "within margin".

## NIT

- **D10, U6:** say whether U6 is bit-identical, or a perception and learning bar.
- **D11, §2:** add `scorer_version` to the scoring output, so a rescoring of the spike can't pass for its
  pre-registered numbers.
