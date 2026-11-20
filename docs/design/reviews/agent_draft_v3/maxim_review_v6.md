# Maxim's delta review of the embeddable-agent plan v6 (received 2026-11-19)

Recorded as the owner relayed it, with only the layout changed. It reviews
`docs/maxim_upstream/embeddable_agent_DRAFT.md` v6 (Overdrive `main`; PR #10 merged at ca403de1) against Maxim's
`origin/main`.

**Verdict: SOUND.** The folds carry no conditions. Q1 is answered below with one suggestion; Q2 needs no change.

## The folds, verified

- **Tense:** corrected everywhere (§1, §4).
- **Pid ownership:** the executor's uuid (`executor.py:512`) is excluded both as a pid and as a join key.
- **G17:** §5 names it. Until it lands, the field is reserved and null, with no stand-in.
- **OD-EA16:** covers refused, deferred, dropped and `agent_failed` intents, and books no physical event for a
  refusal.
- **O43:** `session_id` comes from the log root id plus the NPC key, and the high-water seq is saved in the agent
  home. One worker thread per agent is inside §5.5's scope.

## Q1: does the EventSequencer accept a host-supplied floor on restore?

**Today there is nothing to accept.** `EventSequencer` and `PhysicalEventId` are not in `src` on main.

- The autonomic plan's resume stage builds them (`autonomic_layer.md` §3.1.2 and the "After the fence, before GL4 S1"
  stage). That stage owns "the sequencer's own high-water mark, both load seams, and its gate through the real load
  paths".
- The resume rule it reuses is `Hippocampus._resume_capture_seq`: `next = max(next, max(saved) + 1)`. That is a floor
  taken from the agent's own saved state, not from a caller.

**A host-supplied floor is a new input to a seq authority.** That makes it a design question for that stage, asked at
the stage's start like the session-id source. Our position for that question:

- It composes safely only as a raise. The effective floor is `max(saved + 1, host_floor)`, applied at the load seam
  and logged, and it can never lower the floor.
- A host floor below the saved value is ignored, with a WARNING.
- It is a raise-only hint, never a source of seqs, so the "one seq authority per agent" invariant holds.

**An alternative that needs nothing from Maxim.**

- `PhysicalEventId` is `(agent_id, session_id, seq)`. v6 derives `session_id` from the log root plus the NPC key,
  which is constant across restores. That is why an older save can re-mint a logged id.
- If each restore opens a new segment, and the segment's number is part of `session_id` (recorded in the log header,
  so replay reproduces it), then restored pids can't collide with logged ones, whatever the seq.
- O44's floor then becomes a belt-and-braces check, not a requirement.

Pick whichever your replay model prefers. If you need the floor, say so and it goes on the resume stage's question
list.

## Q2: should GL3.B2's gate read "exactly one terminal outcome"?

**No.** The gate is over joined rows, not over every minted pid: "≥ 1 joined (context, action, consequence) row exists
per scripted consequence, every row's pid resolves to exactly one physical event" (`thalamic_relay.md` §6 GL3.B2).

Maxim's own plan already allows minted pids that produce no row:
- **On the loop path, a refused invocation mints nothing.** `Executor._run_started` mints only once the invocation
  will reach `tool.run`, after its refusal checks (`autonomic_layer.md` §3.1.2, "When a pid is minted").
- **The exception path consumes a minted pid with no record.** Seqs are "unique and monotonic, not dense", and
  lockstep tests assert the gaps.

An embedded refusal is the same shape as that exception-path gap: a minted pid with no physical event and no
forward-model row. So GL3.B2's gate holds unchanged, and OD-EA16 is the right place for the terminal-outcome
invariant, on your side, as you have it.

**One request:** OD-EA16's "refusals book no physical event" should also say that a refusal pid never appears in a
GL3.B2 row. Then the two gates can't disagree about a refused intent.

## No other new findings

§3, §4, §6's other rows and §8 are unchanged and stand as reviewed.

## Overdrive's decision on Q1 (owner, 2026-11-19, O45)

Each restore opens a new log segment, and the segment number is part of `session_id`. It is recorded in the log
header, so replay reproduces it, and ids from different segments can't collide whatever the seq. O44's floor is no
longer a requirement. It stays only as a host-side test that no new pid equals a logged one. Nothing is asked of
Maxim's resume stage.
