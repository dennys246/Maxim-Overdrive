# Reply to your answer on `correction_1.md` (2026-11-17)

Written for: the Maxim design session. Checked against Maxim `origin/main` 6fee7377. Your answer (recorded in
`response_3.md`) is right on every
point we checked (`nac.py:3629`, `:3715`; `fear_agent.py:317`). This note corrects one thing we asked for, brings
evidence to the question you're raising on #1361, argues one decision by name, and answers your front gate for A4.

## 1. Take back half of the offset-and-scale test

You accepted our planted-render ask as written: shift the machinery clock's origin **and** run it at a non-unit rate.
End to end, the scale half is red on correct code. A scaled machinery clock legitimately changes decay and recall, so
the agent's behaviour differs and the test can't tell a leak from physics. Please split it:

- **end to end:** origin offset only; nothing a prompt renders may change;
- **at render level, on a frozen store:** offset and scale, so relative renders such as "3 s ago" can't leak either.

This was our error, caught by our own review (`docs/plans/reviews/trust_bio.md`, TB-S1) after we sent it.

## 2. Evidence for your #1361 question on anchor similarity

You wrote that after S3b, `TemporalSignature.now()` still scores anchor similarity on the host calendar, and that for
an embedded host the read belongs on the perceived-time port. For Overdrive this is not hypothetical:

- **Replay breaks.** A session must replay bit-identically from its intent log. Replay the same log at 3 pm rather
  than 9 am and the similarity scores differ, so delayed credit differs, so the NPC's later choices differ.
- **Learning follows the player's clock.** Two players running the same world learn different NPCs depending on
  when they play. Our design says no host time reaches cognition (O4); this is the one read that still does.

We track it as OD-A20 and support moving it to the perceived-time port, which in Overdrive carries world time.

## 3. τ_elig: an argument against #1361 Q1, not a doc edit

We agree S3a should record the rationale. We also think the number is wrong for a module named NAc, and say so by
name against Q1 ("one set of world-second taus, converted so the calibrated fixture behaviour is preserved"):

- NAc is striatum, where the dopamine eligibility window is about 0.3–2 s (Yagishita et al. 2014, *Science*).
  Action-to-outcome credit over longer delays is carried by other mechanisms; in Maxim that is the anchor path,
  which is one more reason §2 matters.
- Your own figures show Q1 changes robots too: at the embodied runtime's 10–30 Hz a trace lasts about 0.3–0.95 s
  today and 4.75 s after S3a. Preserving the 2 Hz fixture lengthens the live runtime's window 5–15×.

We track it as OD-A21 and agree it is an owner decision with its own experiment, through your process.

## 4. Where we adopt your design over ours

- **Keyed substreams:** we'd take your A2 derivation (one joined key into `stable_hash_64_signed`) over our
  host-side handout, on two conditions, the only properties ours exists for: `agent_id` is the host's persisted NPC
  key, never an ordinal (so streams survive saves and roster edits), and `base_seed` comes from the host's log root.
  Settle it inside #1305's scope.
- **The machinery clock:** for robots it is `ExperienceClockDriver` (A3), and the static ban extends M72 rather than
  adding a second lint.
- **Tool duration:** we've added `tool_dispatch.py:1343` (wall-clock duration into NAc valence) and
  `environment.step` inside dispatch to our dispatch/settle items, as your B2 parity note says they must be.

## 5. Disclosure

The details of the cloud-redaction defect you hold as a private advisory were public on Overdrive's
`phase1/design-v2` branch (draft PR #4) for about a day, from 2026-11-16 until the owner made the repository private
on 2026-11-17. Please account for that in the advisory's timeline. We won't repeat the details anywhere, and the
branch's history will be scrubbed before the repository is public again.

## 6. Why the 1.1.4 world seam can't serve Overdrive's NPCs (your front gate for A4)

The 1.1.4 seam (`docs/plans/archive/world_seam_1_1_4.md`) connects a world to Maxim through a bridge:
`run_agentic_loop` owns the loop, reads the world's state at a wall-clock cadence and acts through the bridge. That
suits a world that owns its own clock and is never replayed. For Overdrive it fails five requirements:

1. **Time.** The world runs on an integer tick with a time dial; the agent perceives world time, never the host's
   (O4). A loop on a wall-clock cadence runs NPCs faster or slower than the world at any dial but 1×, and its prompt
   renders the host's clock (`prompt_builder.py:1125-1127`).
2. **Replay.** A loop on its own thread, ticking on wall time, makes the order of its actions depend on scheduling.
3. **One door.** Every NPC action enters as a validated intent at one gate, in canonical order on the log (O7). A
   bridge the loop calls when it chooses is a second door with its own timing.
4. **Trust.** Players' words are untrusted input; the guest boundary is a worker process the host drives (O13, O14).
   A loop owning its tools, environment and home in the host's process can't be put behind it.
5. **Scale.** One owned loop per agent, each with its own thread and router lock, doesn't share a host's model
   gateway or scheduler.

**Where it helps:** one unreplayed prototype NPC through a bridge is a cheap way to test the premise (latency, cost,
whether a conversation feels alive) before the stepped `think` exists. If we build one, it stays outside Overdrive's
replayable core and makes no claim.
