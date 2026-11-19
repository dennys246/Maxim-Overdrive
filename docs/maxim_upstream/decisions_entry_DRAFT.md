# DRAFT for Maxim: a `DECISIONS.md` entry

Overdrive's plans cite an owner decision recorded only in Overdrive (`docs/roadmap.md` Phase 3, 2026-11-16). A
decision in another repo doesn't bind Maxim, and it doesn't override CC3's text (Overdrive's Maxim process review,
MP-S13). So the first Overdrive plan PR in Maxim records the decision in Maxim's own `DECISIONS.md`, in its house
format, worded for Maxim's owner to accept, amend or refuse. The text below is a proposal, not a record.

---

## 2026-11-16 — An embedding host is a first-class user: Overdrive may propose SEM and agent-loop changes, through this process

### Decision (owner, 2026-11-16; proposed from Maxim Overdrive)

1. **Embedding is a supported use of Maxim.** A host that owns time, randomness, ids, the model call, the tool roster
   and storage (a game world, a deterministic simulator) is a user Maxim designs for, alongside robots, the console
   and pulse.
2. **Overdrive may propose changes to SEM, including types marked `SHAPE-FROZEN at 1.0 (CC3)`, and to the agent
   loop.** Every change follows this repo's process: an issue or a plan, the plan review, the code review, and an
   experiment where a behavioural claim is made. CC3's rules apply unchanged: a trailing defaulted field is additive
   and review-gated; a required field or a `Protocol` signature change is a major-version question.
3. **Robots, the console and pulse keep today's behaviour** under every embedding change. Embedding enters through
   new collaborators with defaults equal to today's behaviour, or through opt-in declarations.
4. **Game runs never go on the results ledger.** Overdrive's evidence enters Maxim as strict red gates in Maxim's own
   tests, or as pre-registered experiments run as Maxim cradles.

### Reason

A real application with a world that can pause, run fast and replay exposed assumptions that a wall-clock robot never
does: wall time in prompts and stamps, an agent that owns its own loop and model calls, a default tool roster that
reaches the host's shell, and one shared data home. Guiding Maxim through that application is a goal of both
projects.

### Tradeoffs

- More review load: each embedding change is a plan with its own review.
- Some fenced work waits for 1.3.6.
- The embedder's evidence is a game, so it is never ledger evidence by itself.
