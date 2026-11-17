# Correction to Overdrive's reply (2026-11-17)

Written for: the Maxim design session that answered our embeddable-agent questions. Not yet sent. An earlier draft of
this note was itself wrong (it proposed a new item, OD-A19, that duplicates your own plan); Overdrive's delta review
caught it before it went out (`docs/design/reviews/npcs_v3_1/determinism_bio.md`).

## What we told you that was wrong

`reply.md` §7 said dispatch/settle "depends strictly on the clock seam: NAc's eligibility traces decay on the wall
clock (`nac.py:1162`)". On 7084f561 that is wrong twice over:

- `decisions/nac.py:1162` is the 300 s causal-link buffer, not trace decay.
- The eligibility traces decay ×0.9 per call to `decay_eligibility` (`nac.py:3707`), which the loop runs once per tick
  (`runtime/agent_loop.py:800-840`, called at `:3194`). Their decay is per tick, not per wall second.

Your own `docs/plans/experience_clock_decay.md` (#1361, step S3a) already describes exactly this ("eligibility decays
×0.9 per pass") and replaces it with `advance_experience(dt_us)` applying `exp(−dt/τ)`. We already track #1361 as our
OD-A1. So there is no new ask here: please read our §7 dependency as "dispatch/settle depends on #1361 S3a".

## What is still true, and what S3a should cover

- **The fallback still reads the host clock.** When a trace has expired, credit falls back to temporal anchors
  compared with `TemporalSignature.now()` (`nac.py:3625-3640`), and anchors are pruned against `time.time()`
  (`nac.py:3714`). Delayed credit therefore still depends on wall time after S3a unless the anchors move to the
  experience clock too. Is that in S3a's scope?
- **The effect is not "13× more credit".** We said two NPCs at different step rates would credit a delayed outcome
  about 13× differently. NAc normalises credit, so a lone eligible trace gets full credit at any step rate. The real
  step-rate effects are how credit is shared among several traces, and when a trace expires into the wall-clock
  fallback.

## One question on S3a's time constant

S3a's trace time constant comes out at several seconds (about 4.75 s on the 10 Hz figures). The dopamine eligibility
window for spine plasticity is about 0.3–2 s after the action (Yagishita et al. 2014, *Science*; Overdrive's
`docs/design/reviews/maxim_response_1/bio_determinism.md`, BD-19). Is the longer constant deliberate, for behavioural
credit rather than the synaptic window? If so, could S3a record that rationale?

## Smaller corrections to our reply

- The parse-failure template does quote the input: it builds its reply from `triggering_input` (`llm_fallback.py`,
  near `:395-400`), so the echo you couldn't confirm is real.
- There are model calls outside `think` that the request/reply cut must name: `AdaptivePlanner` (`bootstrap.py:623`,
  calling `adaptive_planner.py:487`), the `ToolPainBridge` reflection on the settle path (`tool_pain_bridge.py:806`),
  and `FearAgent`.
- `stable_hash_64(seed, agent, stream)` doesn't exist; Maxim has `stable_hash_64_signed(text)`. A keyed substream needs
  one key string (seed, agent and stream joined), or a new function.
- A planted-render test must plant its sentinel in the machinery clock, not the perceived-time port (which prompts may
  show), and needs an offset-and-scale case for rendered differences such as "3 s ago".
