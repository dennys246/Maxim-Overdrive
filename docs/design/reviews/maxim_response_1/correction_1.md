# Correction 1 to Overdrive's reply (2026-11-17)

Written for: the Maxim design session that answered our embeddable-agent questions.

Our reviewers found things we told you that were wrong. `reply.md` stays as sent; this note corrects it. Citations
are to `origin/main` 7084f561; please re-check them on the fresh tree, as you will for the candidates doc.

## 1. NAc's eligibility traces don't decay on the wall clock (reply §7)

We wrote that dispatch/settle "depends strictly on the clock seam: NAc's eligibility traces decay on the wall clock
(`nac.py:1162`)", and you accepted the ordering "6 after 3" on that basis. It was wrong:
- `decisions/nac.py:1162` is the 300 s causal-link buffer, not the traces.
- The eligibility traces decay by ×0.9 **per loop tick** (`decisions/nac.py:3707`, `decay_eligibility`), run from
  `_loop_bio_tick_maintenance` (`runtime/agent_loop.py:800-840`) alongside five sibling decays.

So the dependency is real but different, and arguably worse: credit depends on **how often an agent ticks**, not on
which clock it reads. Two agents stepping at different rates credit the same 3 s-delayed outcome about 13× differently,
and a parity guard run at one step size can't see it. Swapping the clock doesn't fix it.

**The ask (our OD-A19):** step-size-invariant decay. The traces and their siblings decay as `exp(−Δt/τ)` with Δt from
the machinery clock, and an exit test credits one receipt delayed by the same world time equally at two rate
divisors. It argues against the per-tick decay contract in `_loop_bio_tick_maintenance`. On a robot at a fixed loop
rate nothing changes; it matters whenever the step size varies. Dispatch/settle then depends on this, not only on the
clock seam: "6 after 3" becomes "6 after 3 and this".

## 2. Smaller corrections

- **The settle horizon:** we cited Yagishita et al. 2014's 0.3–2 s dopamine window for credit. It supports immediate
  credit only. A horizon of seconds to minutes for slow effects is `[engineering]`, and its natural route is NAc's
  300 s causal-link buffer, not the traces.
- **Retrieval during `think`:** our draft called the think path read-only, and you accepted it. Recall strengthens a
  trace today (the testing effect), so a read-only `think` would silently drop it. We now propose that recalls return a
  `retrieval` write, applied by the host-called `apply`.
- **The parse-failure template does echo the input** (`'{question}'` from `triggering_input`, `agents/llm_fallback.py`
  near `:395-400`). You hadn't confirmed it. So the embedded path should never reach the template for **any** reply,
  not only cancelled ones: a complete reply that doesn't parse ends the thought as a failure.
- **Model calls outside `think`:** `AdaptivePlanner(llm=...)` (`runtime/bootstrap.py:623`, `adaptive_planner.py:487`),
  the `ToolPainBridge` reflection on the settle path (`tool_pain_bridge.py:806`) and `FearAgent(fear_llm)`. We propose
  that the embedded agent holds no model backend at all, so these fail closed until each returns a request.
- **The planted-render test:** we proposed planting the sentinel in the perceived-time port, which prompts are allowed
  to show. It belongs in the machinery clock, plus a test that two runs whose machinery clocks differ by an offset and
  a scale, with equal perceived-time bins, render byte-identical prompts; a sentinel instant can't catch a rendered
  duration.
- **Keyed substreams:** we named `stable_hash_64(seed, agent, stream)`, which doesn't exist (you have
  `stable_hash_32(text)` and `stable_hash_64_signed(text)`). We now propose that the host hands you one integer seed
  per `(npc_key, stream_key)`, and you seed a `random.Random` per stream, as you suggested.

Nothing here needs an answer before the candidates doc; fold what you accept into it.
