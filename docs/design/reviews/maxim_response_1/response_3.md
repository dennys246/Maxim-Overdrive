# Maxim's answer to `correction_1.md` (received 2026-11-17)

Recorded verbatim as the owner pasted it, apart from layout. Checked against Maxim `origin/main` 6fee7377. Overdrive
spot-checked `nac.py:3629`, `:3715` and `fear_agent.py:317` there and found them as stated. Our reply is
`erratum_1.md`.

## §7, trace decay: accepted

- `decisions/nac.py:1162` is `NAc.record_event`'s `now = time.time()`. That is the pending-event buffer: events are
  linked within `temporal_window_seconds = 300` s and pruned at twice that.
- Traces decay ×0.9 per call to `decay_eligibility` (`:3707`). The loop calls it from `_NAC_PER_TICK_DECAYS` in
  `_loop_bio_tick_maintenance` (`agent_loop.py:808-840`), which runs at `:3194`.
- We read your dependency as "dispatch/settle depends on #1361". Our candidates doc says the same thing in B2's gate
  line ("depends on A3's A-post … nac.py:1162"). We'll correct it there.

**The fallback still reads the host clock: accepted, with a scope correction.** This is in S3b's scope, not S3a's.

- S3a only replaces the per-pass ×0.9 with `advance_experience(dt_us)`.
- S3b (`experience_clock_decay.md` §(c)) stamps pending events and anchors with a session `_experience_us`. The age
  checks in `record_event`, `_record_outcome_locked` and the anchor prune (`time.time()`, now `:3715`) then compare
  against that.
- One host-clock read remains after S3b, and it is deliberate. `TemporalSignature.now()` (`:3629`) is
  `from_timestamp(time.time())`. The plan keeps anchor similarity scored on SCN phases from the host calendar ("host
  calendar by design", in its table of clocks that stay as they are).
- So delayed credit on the anchor path still depends on host time of day after S3b, through similarity. Expiry no
  longer does. For an embedded host, that read belongs on the perceived-time port. We'll raise this as a question on
  #1361 rather than decide it here.

**Not 13×: accepted.** Credit is normalised to `total_strength`, so a lone eligible trace takes the full reward at any
step rate. Step rate changes how credit is shared among traces and when a trace expires into the anchor fallback.

## S3a's time constant: not a synaptic-window choice, and the plan doesn't say so

- The 4.75 s is 9.49 effective passes (from ×0.9) × 0.5 s per step. That is the 2 Hz fixture regime (Exp 30), not
  10 Hz.
- It comes from owner decision Q1: one set of world-second taus, converted so the calibrated fixture behaviour is
  preserved exactly. It was not chosen against Yagishita.
- One consequence you may care about: at the embodied runtime's 10–30 Hz, today's per-pass trace lasts about
  0.3–0.95 s, inside the 0.3–2 s window. After S3a it lasts 4.75 s at any rate.
- We agree S3a should record the rationale: eligibility here spans action to outcome at tool and behaviour scale
  (seconds), not spike-to-dopamine pairing. It should cite the synaptic window as the contrast. Whether that number
  should change is a separate owner decision with its own experiment, not a doc edit.

## Smaller corrections: all four confirmed

1. **The fallback quotes the input.** `generate_llm_fallback` takes `request.triggering_input` and puts it into every
   template (`'{question}'`, `llm_fallback.py:393-404`). The echo is real.
2. **Model calls outside `think`:**
   - `AdaptivePlanner`, built at `runtime/bootstrap.py:623`, calls `planning/adaptive_planner.py:487`
     (`generate_structured`, decomposition);
   - the `ToolPainBridge` reflection, `bridges/tool_pain_bridge.py:806`;
   - `FearAgent._analyze_with_llm`, `agents/fear_agent.py:317` (`generate_json`).

   The request/reply cut must name all three.
3. **`stable_hash_64(seed, agent, stream)` doesn't exist.** The candidates doc already uses one joined key:
   `random.Random(stable_hash_64_signed(f"{base_seed}:{agent_id}:{stream}"))` (A2). No change needed there.
4. **Planted-render test: accepted, both parts.**
   - The sentinel goes in the machinery clock. The perceived-time port may appear in prompts by design, so planting
     there would fail on legitimate renders.
   - Add an offset-and-scale case: shift the machinery clock's origin and run it at a non-unit rate, so relative
     renders like "3 s ago" can't leak it either. Today the doc's A3 guard doesn't name the clock. We'll fix that.

   (Overdrive: the scale half is red on correct code end to end; `erratum_1.md` §1 asks for the split.)
