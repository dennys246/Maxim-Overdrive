# Maxim's delta review of the embeddable-agent plan v5 (received 2026-11-19)

Recorded as the owner relayed it; only the layout is changed. It reviews
`docs/maxim_upstream/embeddable_agent_DRAFT.md` v5, at Overdrive `main` cdc2f346 (PR #8), against Maxim's `origin/main`
95af47d2.

**Verdict: SOUND WITH CONDITIONS.** There are two SHOULD-FIX items, both on the pid. Nothing blocks the build.

## Folds: all verified

The citations hold at 95af47d2.

- **OD-EA15:** the fixture is named and the duration is in it. Accepted. That's the better choice of the two, for the
  reason you give.
- **OD-A20 (a)–(c):** accepted as a known divergence.
  - The threshold is at `nac.py:3638` (`temporal_strength > 0.01`).
  - `TemporalSignature.from_timestamp` uses `datetime.fromtimestamp(ts)`, which is local time.
  - Noted as information only: (c) is a cross-machine effect.
- **Forgetting on the wall clock:** verified.
  - `hippocampus_consolidation.py:117` sets `now = time.time()`.
  - `AccessBasedStrategy` with the hippocampus's 7-day `max_age_without_access` scores 0.5·(1 − t/7 d) + 0.2·(1/5)
    for a memory accessed once and unlinked. That falls below 0.3 at t > 3.36 d, so your figure is right.
  - It applies to `access_count` 1 and degree 0; a memory accessed 10 or more times is always kept. It stays with
    #1361 Q5.
- **The NITs and §7 answers** are folded as decided: `basis_seq`, `token_counter`, tracked rights, G2b, the `:` ban and
  bounded consolidate.

## NIT

Your cover note says the strict red gates "carry the evidence" (two for OD-A20, one for forgetting). Neither v5 nor
your tree has them yet: PR #8 is docs only, and `tests/` has no such files. Keep the future tense ("will carry") until
they land, so the divergences aren't recorded as evidenced before any run.

## Q1: who mints the embedded invocation pid?

Your assumption holds, with one refinement: **B2 owns the call site, the agent's `EventSequencer` owns the mint, and
GL3.B2 owns the contract.**

- **What exists today: no pid.** `PhysicalEventId` is not in `src` at 95af47d2.
  - The executor's `invocation_id` is `str(uuid.uuid4())`, drawn in `Executor.execute` (`executor.py:512`) before
    `_run_started`.
  - Never use it as the embedded pid or as a replay join key. It isn't deterministic, and GL3.B2's gate requires that
    "no row joins on an invocation id".
- **Who owns what** (`thalamic_relay.md` §5.2 and §6 GL3.B2):
  - The type `PhysicalEventId(agent_id, session_id, seq)` and the per-agent `EventSequencer` belong to the autonomic
    plan, built at its post-fence resume stage (G17).
  - GL3.B2 states only the contract:
    - one pid per invocation, drawn from that agent's `EventSequencer` under its lock;
    - minted before the tool runs, and reused by the H3t emits inside the invocation;
    - stamped on `ToolOutput` by `_stamp_invocation`, which mints nothing.

    "GL4 holds the producer."
  - On the loop path, the mint site is `Executor._run_started`.
- **So, embedded:** B2's dispatch is the `_run_started` equivalent. It draws from the agent's own sequencer inside the
  worker and puts the pid on the intent value, and the host copies it. The authority stays the sequencer, never B2 or
  the host.

## SHOULD-FIX 1: §5 step 4 depends on a stage that isn't built

- Step 4 lists "the invocation pid on each dispatched intent", but the type and sequencer come from the autonomic
  plan's post-fence resume stage, which isn't built at 95af47d2.
- Name that dependency in §5. Then either B2 waits on that stage for the pid, or it lands with the field reserved and
  unfilled.
- It must not fill the field with a stand-in like a uuid or the executor's `invocation_id`.

## SHOULD-FIX 2: every minted pid must end in exactly one receipt

- On the loop path, `Executor._run_started` can still refuse an invocation before `tool.run`.
- Embedded, the agent mints at `step()` time, and the host can then refuse, defer past a budget, or drop the intent.
- GL3.B2's gate requires every pid to resolve to exactly one physical event. A minted pid whose intent never runs
  would be an orphan.

Make it a settle invariant, and make it an exit test:

- each minted pid comes back in exactly one terminal receipt, either executed or a typed refusal;
- no receipt arrives without a minted pid;
- refusal receipts count as the pid's outcome, not as a physical event.

## New question, for replay

`PhysicalEventId` carries `session_id`, and replay is bit for bit.

- Is your NPC's `session_id` deterministic and supplied by the log, never wall-clock or uuid? It needs to be.
- Is the sequencer's high-water mark saved in the AgentHome, so a load continues the seq? Either works if it's
  decided. A reset per session needs `session_id` to change on every load.
- The relay plan scopes its determinism claim to single-threaded loop paths (§5.5). Your one-worker-per-agent step
  thread is inside that scope; a pool would not be.

## No other new findings

§3, §4's A3 rows, OD-A21 and §8 are unchanged from v4 and stand as reviewed.

## Overdrive's decision on the new question (owner, 2026-11-19, O43)

`session_id` is derived from the intent log's header (the log's root id plus the NPC key), never from the wall clock or
a uuid. The sequencer's high-water seq is saved in the NPC's agent home, so a loaded save continues the sequence.
