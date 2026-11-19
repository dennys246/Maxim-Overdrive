# DRAFT for Maxim: Overdrive's contribution to the hybrid arbitration line

**Status:** rewritten in Maxim Overdrive on 2026-11-16. The first version (2026-11-15) proposed a new 1.5 line for a
hybrid runtime. Since then Maxim's owner has decided one: `DECISIONS.md` 2026-11-11, "Hybrid arbitration is a 1.5
candidate line". Its design is `docs/plans/hybrid_arbitration.md` (HA-O1 to HA-O16), split into four plans:
- `idle_dmn_coordinator.md`;
- `sem_interruptibility.md`;
- `learned_hold_window.md`;
- `foreign_advice_layer.md`.

So this draft no longer proposes a line. It proposes what an embedded world adds to that one. Read against
`origin/main` `7084f561`.

- **The line's rules, which this respects:**
  - It is a parallel paper line, not a 1.4 rung, with no `src/` before the 1.4.0 cut (M89).
  - Its first evidence slice is an Exp 49 re-run, boundary-only, with one hybrid cell (HA-O14).
  - Claims are exploratory under BF2.
- **Overdrive ids:** OD-H1 to OD-H4 (tier C).

## OD-H1. The game as a test bed for the hybrid's questions

The line has **no** experiment yet that tested a hybrid ("Everything above is motivation, not evidence",
`hybrid_arbitration.md` §Why). An embedded world gives it what a robot can't:
- deliberation latency set exactly, in world time;
- swept;
- replayed bit for bit (after tier A).

The robots stay the ground truth for transfer. Candidate questions, for the line to adopt, amend or refuse:

| Id | Question | What a world adds | Earns? |
|---|---|---|---|
| OD-HX1 | **The substrate floor:** how much of an agent's competence does the substrate carry with no deliberation? | controlled tasks (keep away from fire, find food and rest) with identical replays | an experiment, with BF2 floors |
| OD-HX2 | **The latency curve:** does competence degrade gracefully as deliberation gets slower? | latency swept in world time (0, 1, 3, 10 and 30 s) | **calibration only.** It sets the hold's starting values and can't earn anything (MP-S9). |
| OD-HX3 | **Interruption:** can pain or salience cancel a thought in flight, as fast as a reflex? | a hazard timed exactly against a thought in flight | an experiment; needs OD-A14's `cancelled(prefix)` reply and `sem_interruptibility.md`'s vocabulary |
| OD-HX4 | **Acting while talking:** does an agent in conversation keep its reflexes, and stay coherent with what its body did? | a hazard during a dialogue thought | an experiment |
| OD-HX5 | **Game to robot:** does the latency curve transfer to a physical body? | the same sweep on Reachy | an experiment, the transfer check |

**Where these run.** Game runs never go on Maxim's ledger. An experiment from this list runs in a Maxim-owned harness,
either against a scripted world or against an Overdrive world exposed through a Maxim simulation bridge (as
`simulation/minecraft.py` exposes Minecraft). It is pre-registered and frozen on Maxim's `main` before data. Which of
the two is acceptable is a question for the line's owner.

## OD-H2. Pushback: in an embedded world, the hold's waiting cost must be modelled latency, not observed latency

- **The decision argued against:** `learned_hold_window.md` §"The rule to start from": "**Waiting cost:** the
  world's hazard and reward rate, the backend's action duration, and the observed LLM latency."
- **Why it's right for a robot:** on a robot, wall time is world time. The observed latency is the cost the world
  actually charges.
- **Why it's wrong for an embedded world:** there the observed latency is a property of the host machine and the
  time dial, not of the world.
  - The same agent on a faster GPU, or at a slower dial, would learn a different hold. Its behaviour would then
    depend on the hardware: the class of bug Overdrive's resolution rule forbids for physics (Overdrive lesson 1).
  - At 20×, a 0.4 s wall answer is 8 world seconds; at 0.25× it is 0.1 world second.
- **Overdrive's evidence:**
  - its design reviews (`docs/design/reviews/foundations_v1/determinism.md` DR-B5, `bio_faithful.md` BF2-8);
  - the engine mapping (`docs/design/research/time/engine_mapping.md` §3).
- **Maxim's own precedent:** `foreign_advice_layer.md` already decays advice "on the experience clock … not on loop
  passes. That way advice influence lasts the same in every arm, whatever the LLM latency or host load." The hold
  should follow the same rule.
- **Proposed:** when the agent is embedded, the waiting cost reads the host's **modelled world-time latency** for the
  thought kind, which the host reports on the request/reply cut (OD-A14). On a robot it keeps the observed latency, which there is
  the same thing. It is a declaration on the embedded entry point, so no robot changes.

## OD-H3. Re-key the deferred reflex runtime's trigger, argued against G4, at GL3's start

- **The decision argued against:** owner decision G4 (2026-10-07), recorded on
  `deferred/hybrid_substrate_reflex_runtime.md`: "this trigger is NOT re-keyed; it is the robot half of the
  second-body gate … Whether to re-read the 'second robot body' gate is a question at GL3's start."
  - The first draft cited M76. That was the wrong record: M76 is the mechanization row for the second-body plans'
    tripwire.
- **The argument, for GL3's start:** an embedded world is a second body in every respect the reflex runtime needs:
  - a body grammar;
  - drives;
  - sensors and timing;
  - a world it can't pause.

  It isn't a robot. G4 splits the gate into a perception half, re-keyed to a capability trigger, and a robot half.
  The reflex runtime's need is closer to the perception half's.
- **The ask:** when GL3 starts, consider re-reading the trigger as "a second body, physical or embedded". The
  Microduck's arrival would meet the robot half anyway.

## OD-H4. Conversation: deliberation starts while the other person is still speaking

- **The evidence:** people leave about 200 ms between turns (Stivers et al. 2009: the mode is 0–200 ms, and the
  language means run from about 7 to about 470 ms; verified in Overdrive's bio-faithful review). Producing a reply
  takes over 600 ms (Levinson & Torreira 2015), so people plan during the other person's turn. Gaps over about 700 ms
  read as reluctance (Kendrick & Torreira 2015).
- **What it means for the hybrid:**
  - the substrate carries the turn's fast parts: gaze, backchannels, and fillers chosen from the modelled delay
    (Clark & Fox Tree 2002);
  - deliberation is triggered by the incoming speech stream, not by its end.
- **What it needs:** streamed input to the agent, and OD-A14's speech-first reply and `cancelled(prefix)` variant. Now folded into OD-H5 (Maxim's answer).
- **The ask:** that the line consider "deliberation triggered during the other's turn" as a candidate for its
  escalation rule (`hybrid_arbitration.md` §A.1, "The arbiter escalates if ANY of the following holds"). Overdrive
  would bring a pre-registered comparison of onset-from-end against onset-during-turn.

## Open for the line's owner

- Whether an Overdrive world through a Maxim simulation bridge is an acceptable venue for OD-HX1, OD-HX3 and
  OD-HX4.
- Whether OD-H2 belongs in `learned_hold_window.md` v1's frozen hold, or only in v2.
