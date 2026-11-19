# Maxim's answer to `erratum_1.md` (received 2026-11-19)

Recorded as the owner relayed it. Answers our §3a request (a date range for 1.4.0, O29) and §6 (why the 1.1.4 world
seam can't serve Overdrive's NPCs, Maxim's front gate for candidate A4).

## 1.4.0 timing

- Earliest February 2027; plan on March to May 2027. A planning range, not a commitment.
- 1.3.4 (robot and recall fixes) and 1.3.5 to 1.3.6 come first.
- 1.4.0's release gates must clear, including #1305's owned-RNG work, where candidate A2 (keyed substreams) now
  lives.

## The world-seam front gate: accepted

- Replay, one door and trust carry the case. Maxim considers scale the weakest of the five reasons, but not needed.
- Accepting the gate means Maxim agrees the case for a host-driven runtime mode.
- The embeddable-agent plan itself still gets a review round from Maxim before any Maxim `src/` lands for it.
- Until then, one unreplayed prototype NPC through a bridge is fine for latency, cost and feel, outside Overdrive's
  replayable core.

## What it changes here

- Roadmap Phase 3, tier A: the planning assumption is replaced by Maxim's range. The stepped `think` (candidate B1)
  comes after 1.4.0, in the 1.5 hybrid line's src phase, so Phase 4's first real NPC is after mid-2027 at the
  earliest; Maxim gave no range for B1.
- The host-driven mode is agreed in principle; the agent contract is not. `docs/maxim_upstream/embeddable_agent_DRAFT.md`
  goes to Maxim's review round, and its findings may change our port (`npcs_and_sem.md` §6, frozen by O19 until a
  reopen trigger: this is one).
- A bridge prototype NPC is allowed (O20's spike can grow into it), and makes no claim.
