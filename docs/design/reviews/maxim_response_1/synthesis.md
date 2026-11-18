# Synthesis: Overdrive's review of Maxim's response (2026-11-16)

Four lenses read `response.md` independently against Maxim `origin/main` 7084f561 and Overdrive's design:
`executor.md` (fact-check), `architecture.md`, `bio_determinism.md` (BD-1 to BD-19), `trust_boundary.md` (TBR-1 to
TBR-14). The two findings with the largest consequences were re-checked by hand: the prompt renders the time
(`agents/prompt_builder.py:237`, `:1125-1127`; `agents/context_pool.py:468`), and prefetch runs on every input
(`runtime/agent_loop.py:1571`).

## Verdict

The response is good and mostly right. Its central correction holds: Maxim has no inner tool loop, so a tool call
is an intent the host validates, not a pending request. That deletes a layer of our design. Its structure (cut at
the router and at `execute_and_learn`, a host-called `think`, the gateway above the backend, one design with
`hybrid_arbitration.md` §A.1b) is the right shape. But it understates the work in four places, and one of its
proposals would break our time model as worded.

## Where it is wrong or incomplete

1. **AgentTime as worded breaks O4** (BD-12). Handing the host clock to the agent puts exact world time into every
   prompt, because the prompt renders the time. The planted wall-clock test still passes. It must be split into a
   machinery clock that can't be rendered as text and a perceived-time port, with a planted-render test.
2. **"One call returns one action" is partly true** (executor). PFC deliberation makes up to 3 sequential model
   calls in one tick, and `next_actions` chains run later actions with no further call. The resumable state must
   survive several requests, our latency table understates speech before PFC by up to 3×, and each chained action
   is validated when it dispatches.
3. **Leaks it missed** (executor, trust):
   - prefetch reads files under the working directory and runs `find` on every input, bypassing the roster;
   - a short-question shortcut answers without the model ("what time is it" gives host local time), triggered by
     the word "maxim";
   - a parse-failure template echoes the guest's text, which a cancelled reply would trigger on every barge-in;
   - cwd-relative `data/` files that collide with ours;
   - the root logger replaced with `force=True`;
   - a redaction defect, now a private advisory (OD-I5; details redacted 2026-11-17).
4. **Two dynamic tests aren't enough** (trust). The advisor uses three (`test_no_effect` is the one that catches
   writes), and dynamic tests miss lazy imports on paths they don't run.
5. **The offline latch is half right** (executor, trust). Inbound listening survives; loopback connect, DNS, spawn
   and fork die. Setting `MAXIM_OFFLINE` latches the whole process at `import maxim`.
6. **`make_agent_rng` is a single sequential `random.Random`** (executor, BD-13). We need keyed numpy substreams;
   `seed_all` must never run in an embedded host.
7. **Streaming can't wait for "later" in the reply type** (architecture). v1 needs a cancelled-or-truncated reply
   variant and a speech field the host can read before the JSON closes, or syllable stamps and barge-in are
   designed out.
8. **Paired replays are overstated** (architecture, BD-16). They help substrate claims; for LLM arms the pairing
   ends at the first diverging token.

## Where it is right and we should change ours

- Delete `request_thought`, the host service protocol, and the cancellable-`LLMBackend` gateway (our draft's PR 4).
  `AgentPort` becomes step, think (resume) and settle, all host-called.
- O11 gains an account before the yield: a filler, then "let me think" at about 600–700 ms, then a yield at about 1 s
  (Stivers & Robinson 2006). Thresholds are per-world parameters in world time.
- The first filler comes from the modelled predicted delay. What follows can track lateness, logged and tier 3,
  with a meter: slow hardware otherwise makes NPCs sound reluctant to listeners (BD-4, Roberts et al. 2006).
- Floor-holding is a fifth hybrid split-out plan, not `learned_hold_window`. The neural story is real (planning
  starts mid-turn: Bögels et al. 2015), so "not a neural mechanism" is too strong.
- Dispatch/settle is bio-faithful (Yagishita et al. 2014), but it depends strictly on the clock seam, because NAc's
  eligibility traces decay on the wall clock.

## What Overdrive should decide

- **A worker process per real agent** (TBR-3): the process boundary becomes the trust boundary, with a scrubbed
  environment, the agent's own home, no keys, the latch engaged and the gateway in the host. Pipe latency and memory
  are the costs, to be measured.
- **Guest sessions with real NPCs** wait for five gates, not one prompt test: the worker process, the effect test, a
  dialogue-level bypass test, the line-separator fix, and memory provenance with a purge path.
- **The gate coupling** (architecture): the seam and the dispatch/settle split are engineering, accepted by parity
  and regression guards. If they ride the hybrid line's experiment gate, Phase 4 waits on the arbiter's results
  after 1.4.0.
- **O7's condition is met:** Maxim answered, so the agent half can be revised once and reviewed.
