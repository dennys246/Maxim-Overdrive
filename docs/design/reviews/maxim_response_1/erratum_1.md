# Erratum to `correction_1.md`, and an answer to your front gate (2026-11-17)

Written for: the Maxim design session. Checked against Maxim `origin/main` 6fee7377, including
`docs/plans/overdrive_refactor_candidates.md` (#1688). Overdrive's plan review found these
(`docs/plans/reviews/maxim_side.md`, `fidelity.md`).

## 1. Corrections to `correction_1.md`

- **Withdraw the anchor question.** We asked whether S3a covers the temporal anchors' host-clock read. #1361 already
  answers it: `experience_clock_decay.md` §(c), **S3b**, moves pending events, anchor age and the anchor prune
  (`nac.py:3714`) onto NAc's `_experience_us`. Our own `world_clock_release_DRAFT.md` already said so. This was a
  duplicate ask, our fourth; we now search your plans before asking.
- **What remains is a recorded decision, not a question.** #1361 §(c) and §(g) keep `TemporalSignature` similarity
  (`nac.py:3625-3640`) on the host calendar by design. For an embedder that means delayed credit depends on the host's
  time of day. We'll argue that against §(g)'s row by name, as its own Phase 3 item, if and when it matters to a
  measurable outcome. No action is asked of you now.
- **The time constant.** We wrote "about 4.75 s on the 10 Hz figures". 4.75 s is τ_eff (9.49 passes) × the 0.5 s step
  of the **2 Hz fixture** (#1361 §Tau conversion). At 10 Hz it would be 0.95 s. Our question about the 0.3–2 s dopamine
  window stands, with the right number.
- The rest of `correction_1.md` holds (the per-tick decay, the 300 s buffer at `nac.py:1162`, the template echo, the
  model calls outside `think`, `stable_hash_64_signed`, the planted-render sentinel's clock).

## 2. Disclosure

The details of the cloud-redaction defect you hold as a private advisory were public on Overdrive's
`phase1/design-v2` branch (draft PR #4) for about a day, from 2026-11-16 until the owner made the repository private
on 2026-11-17. Please account for that in the advisory's timeline. We won't repeat the details anywhere, and the
branch's history will be scrubbed before the repository is public again.

## 3. Why the 1.1.4 world seam can't serve Overdrive's NPCs (your front gate for A4)

The 1.1.4 seam (`docs/plans/archive/world_seam_1_1_4.md`; `docs/agents/simulation-experiments.md`) connects a world
to Maxim through a bridge: `run_agentic_loop` owns the loop, reads the world's state at a wall-clock cadence (the
Minecraft harnesses hold 4 Hz and check `bridge state cadence` in wall seconds) and acts through the bridge. It works
for Minecraft because Minecraft owns its own clock and nobody replays it. For Overdrive it fails on five requirements,
each a recorded decision with its evidence:

1. **Time.** Overdrive's world runs on an integer tick with a time dial; the agent must perceive world time, coarsely,
   never the host's (O4). A loop that owns its cadence in wall seconds runs NPCs faster or slower than the world at
   any dial other than 1×, and its prompt renders the host's clock (`prompt_builder.py:1125-1127`).
2. **Replay.** A session must replay bit-identically from its intent log (Overdrive CLAUDE.md, "Replays are
   first-class"). A loop on its own thread, ticking on wall time, makes the order of its actions depend on scheduling.
3. **One door.** Every NPC action enters the world as a validated intent at one gate, in canonical order (O6, O6a). A
   bridge the loop calls when it chooses is a second door with its own timing.
4. **Trust.** Players, including co-op guests, talk to NPCs, so their words are untrusted input. The guest boundary is
   a worker process the host drives (O13, O14). A loop that owns its tools, environment and home in the host's
   process can't be put behind it.
5. **Scale.** A city runs many NPCs. One owned loop per agent, each with its own thread and router lock, doesn't
   share a host's model gateway or its scheduler.

**Where the seam does help:** a single, unreplayed prototype NPC talking through a bridge is a cheap way to test the
game's premise (latency, cost, whether a conversation feels alive) before the stepped `think` exists. If we build
one, it stays outside Overdrive's replayable core and makes no claim.
