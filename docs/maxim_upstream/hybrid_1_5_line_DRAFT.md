# DRAFT for Maxim: a 1.5 line that builds the hybrid runtime and tunes it by experiment

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-15, for Maxim's own process: an issue, a plan, a
four-lens design review, and a pre-registration per experiment. Nothing here is run or claimed. It moves to Maxim's
`docs/plans/` if Maxim accepts it. Game runs stay off Maxim's results ledger; only the pre-registered experiments
below would go on it.

## The claim the line would test

A Maxim agent in hybrid mode never has to wait for its own deliberation. Its substrate (reflexes, NAc's learned
action selection, drives) carries it through the world while an LLM thought is in flight. The thought arrives
later, gets checked against the world as it is then, and then steers the agent.

The design that prompted this (Overdrive's `docs/design/realtime_lanes_coop.md`, §4.3) takes the claim as its
operating rule: neither the world nor the NPC ever waits for a thought. **If an agent would need to wait, the hybrid
isn't working as intended.** That's a finding for this line, not something the game should build around.

## Why now, and why the game

- **The game is a controllable, replayable real-time world.** Deliberation latency can be set exactly (a stub with a
  fixed latency in ticks), swept, and replayed bit for bit. A physical robot can't do that.
- **The robots are the ground truth.** On Reachy and the Microduck, the world truly can't wait. The same latency
  sweep run on a robot tests whether the game's curves transfer.
- **Its prerequisites are on Overdrive's Phase 3 list already:** an externally stepped Default Network on a world
  clock (item 11), an agent live tick (12), cancellable deliberation with a world-time deadline (13), deterministic
  agents (15), and generate vs apply (16). The hybrid plan
  (`docs/plans/deferred/hybrid_substrate_reflex_runtime.md`) and its BL-1 to BL-5 are the reflex half. This line
  would revive that plan, on a simulated body or on the Microduck (Phase 3 item 17).

## Candidate experiments (each needs its own pre-registration and four-lens design review)

| # | Question | Manipulation | Measures |
|---|---|---|---|
| H1 | **The substrate floor:** how much of an NPC's competence does the substrate carry with no deliberation at all? | deliberation off; then on with zero latency; then on with **the world paused for each thought**, which exists only as an upper-bound control arm and never as the shipped mechanism | task outcomes on the tile (keep away from fire, find food and rest, respond to a strike), pain, drive satisfaction |
| H2 | **The latency curve:** does competence degrade gracefully as thinking gets slower, or collapse? | stub deliberation latency swept over world time (for example 0, 1, 3, 10 and 30 s) | outcomes, the stale-refusal rate, the fraction of in-flight time spent on substrate actions and what they were, reflex-against-deliberation conflicts, dithering |
| H3 | **When to think:** is "the substrate has no opinion" (`NAc.recommend_action` returns `None`) the right trigger to deliberate, compared with fixed-interval deliberation? | the trigger policy | LLM calls per NPC-hour against outcomes |
| H4 | **Interruption:** can pain or salience cancel a thought in flight, as fast as a reflex? | a hazard appears while a thought is in flight, with cancellation on and off | time to a protective action, outcomes |
| H5 | **Acting while talking:** does an NPC in dialogue keep its reflexes? | a hazard during a dialogue thought | protective action while the reply continues; whether the reply stays coherent with what the body did (efference copy) |
| H6 | **Dial sensitivity:** with a live model, how much does behaviour change with the world's speed? | the same scenario at 0.25×, 1× and 4× | the H2 measures, compared across dial values |
| H7 | **Game to robot:** does H2's curve transfer to a physical body? | the latency sweep on Reachy or the Microduck orienting task | the same curve, game against robot |

**What the line tunes from these:** the deliberation budget for each kind of request, the trigger to deliberate,
cancellation thresholds, and how a late thought is reconciled with what the body did meanwhile.

**Kill criterion (to be pre-registered):** if H1's substrate floor is near zero on every task, and H2's curve
collapses at small latencies, the substrate can't carry an agent through deliberation. The hybrid claim fails, and
the line reports an honest null.

## Open for Maxim's review

- Whether this belongs in 1.5, or extends 1.4's grounding line.
- How H1's "world waits" control arm is reported, so it can never be read as a shipped mechanism.
- Which tasks on the Overdrive tile count as the battery, which drives the tile must satisfy (Overdrive design,
  Bio-11: the tile needs food and rest affordances), and how they map to Maxim's existing survival rig.
