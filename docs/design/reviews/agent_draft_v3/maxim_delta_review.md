# Maxim's delta review of the embeddable-agent plan v4 (received 2026-11-19)

Recorded as the owner relayed it; only the layout is changed. The review covers
`docs/maxim_upstream/embeddable_agent_DRAFT.md` v4 (PR #7) and was read against Maxim `origin/main` 95af47d2.

**Verdict: SOUND WITH CONDITIONS.** The conditions are narrower than v3's, and nothing blocks the build.

## The v3 findings

All are folded except two, which are folded only in part.

- **OD-EA15 (robot parity, B2): name the fixture.** It should be recorded replies plus recorded or injected tool
  durations, from Exp 49 and Exp 60.
  - Today's digest cannot be bit-identical while `exec_elapsed` (wall time) feeds `_observe_energy_cost`. So the
    duration either goes in the fixture or is excluded and named.
  - The digest covers B2's side-effect list.
  - OD-EA14 is right as written.
- **OD-A20 is stated too narrowly.** "Credit is normalised" is correct (`NAc.distribute_reward`,
  `TemporalCreditDistributor.distribute`). But the host calendar moves more than how credit is shared between live and
  anchor nodes:
  - (a) An anchor counts only when 0.3 × sim × activation > 0.01. So the calendar can drop a node, and a receipt whose
    only node drops books nothing.
  - (b) Anchor-only nodes set at different host times split differently among themselves.
  - (c) `TemporalSignature.from_timestamp` uses local time, so the replay box's timezone and DST move credit too.

  §4's "12 h pause → ≈0.70" still uses the framing from before the erratum (npcs §12.2).

## New SHOULD-FIX

- **§2 staleness: the embedded efference copy.** The agent's intents run in the host, so frame and receipt events
  must carry the dispatching intent's invocation id: the GL3.B2 pid join that `thalamic_relay.md` relies on. Without
  it, every self-caused reafference reads as non-self-caused, and every in-flight reply goes stale.

## NITs

- `basis_seq` is the agent's afferent-scheduler high-water seq (`thalamic_relay.md::preempted_since`). The host may
  hold a copy, but never computes it. LLM-proposal staleness waits on GL3.B7, which is unbuilt.
- `PromptBudgeter` takes a `token_counter` as well as the budget, so the host supplies the bound model's tokenizer,
  not only `n_ctx`.

## Answers to §7

- **Tracked rights.** These are the declared preemption rights on afferent tracks (§A.1b.5, `thalamic_relay.md` TR6).
  - Today only `nociceptive_fast` holds a `pending_proposal` right (from GL3.B4). Language (the CLI rule) arrives in
    GL3.B7.
  - Your default (danger tracks only, through step) matches.
  - **Maxim owner decision:** a non-danger track counts only when a plan rung names it.
- **G2b.** #1361's S3b checks one trace against its anchor at two poll rates, not several traces sharing a receipt.
  **Maxim owner decision:** #1361 does not widen it; OD-EA12 is yours, against S3b.
- **The stream join.** `make_agent_rng` hashes `sha256(f"{base_seed}:{agent_id}")` and seeds from the first 64 bits.
  So `agent_id="npc_key:stream"` gives the same seed as a later stream argument joined with `:`.
  **Maxim owner decision:** the gate item keeps exactly this derivation, and `:` is forbidden in NPC keys and stream
  names. The join would be ambiguous otherwise, and escaping later would break survival.
- **A bounded consolidate.**
  - **Today** it runs only at session end (`integration/session_end.py::end_session`). In order:
    1. flush the writers and persist;
    2. `_consolidate`: `Hippocampus.sleep` (retro-tags, promote, then compress or remove by retention scored on
       `time.time()`), then semantic promotion, ATL and AG, each skipped by `_fits` on a wall-clock allowance;
    3. re-save;
    4. the plan manager and provenance.
  - Sleep holds the hippocampus write lock for a whole store pass and can't be interrupted within a step.
    `sleep_replay.py` is dormant.
  - **A bounded version needs:**
    - an entry point that doesn't end the session;
    - a budget in deterministic units (steps, item counts);
    - the wall clock only as a logged, typed abort;
    - retention scored on the experience clock or on a host-supplied now.
  - **Maxim owner decision:** world time decides when, and deterministic units bound the compute. Whether forgetting
    moves off `time.time()` reopens #1361 Q5 and stays with #1361.
