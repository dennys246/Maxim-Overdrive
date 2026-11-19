# Maxim's plan review of the embeddable-agent plan v3 (received 2026-11-19)

Recorded as the owner relayed it, with only the layout changed. The review is of
`docs/maxim_upstream/embeddable_agent_DRAFT.md` v3 (PR #6). Maxim checked its citations against its `origin/main` at
f0b1cea4. **Verdict: SOUND WITH CONDITIONS.** This review is O36's reopen trigger for the frozen agent half.

## DO-NOT-BUILD

- **§2/§6 robot parity.** "The robot path drives the same `think` through a thin driver" restructures a hot path.
  - B1's gate needs a bit-identical state digest on recorded replies (Exp 49, Exp 60).
  - B2's robot path must settle immediately.
  - §6 has no exit test for either; OD-EA5 compares only instant against delayed replies.
  - Add a robot-parity row for B1 and one for B2 before either is built.

## SHOULD-FIX

- **The shortcut (§3 bullet 1, §7 Q5) is stale.** The short-question shortcut was deleted for everyone, matcher and
  fallback included (#1689, PR #1694; candidates A4 "Decided 2026-11-17"). Also note #1691 (merged): a fallback reply
  now books no NAc credit, though `generate_llm_fallback` still echoes `triggering_input`.
- **§2 basis and staleness differ from hybrid §A.1b.5.** We wrote "step sequence and frame id", with fresh, stale and
  superseded verdicts.
  - In §A.1b.5, a reply is stale only when a non-self-caused event on a tracked right arrives after `basis_seq`, with
    an efference-copy exclusion. A frame-id basis goes stale every step.
  - Staleness goes through the typed pre-emption handler, never `_drop_stale_proposal`'s planning-failure path
    (§A.1b.4).
  - Adopt §A.1b.5 or argue the difference there. "Superseded" has no Maxim definition.
- **§2 `apply` separate from `settle`.** Candidates A6 applies proposed writes at settle, under B2's digest. A second
  host-called write door needs its own front-gate reason, or should be merged into settle.
- **§2 request value.**
  - Say it is produced at the `LLMRouter._complete_text` cut (the router-only invariant).
  - Say who supplies the context size the `PromptBudgeter` budgets against. A host-bound model with an `n_ctx` the
    budgeter doesn't know is a known silent-failure class (`docs/lessons/sim-n-ctx-config-drift.md`).
- **§2 receipts.** `settle(receipts)` publishes through the agent bus, not into the stores directly.
- **§3, the `MAXIM_DATA_HOME` exception.** The Order puts A1 before A4, so A4 waits for A1 rather than reading an
  allowed env var. The exception would be a band-aid on the very process-wide home §8 argues against.
- **§7 Q9's premise is wrong.** "Nothing renders it" is false: SCN hour and day features from
  `time/temporal_signature.py` reach the model through `temporal_patterns` and `[TEMPORAL]` (candidates A3). The
  classification must cover both sides.
- **§5 and Q2, the gate scope.** Release-gate item scopes are immutable (`lint_release_gates.py`, shrink-only
  history).
  - The per-agent key is a new gate item, not a widened `1305.owned-rng`.
  - Its scope also ties to `seed_all`/`get_global_seed`, which an embedded path never calls.
  - (Maxim's candidates doc had the same error; corrected.)
- **§6, OD-EA7 "none found".** The 1.4.0 gate `1263.thread-guard` is that test; configure it.

## NIT

- `utils/seeding.py::make_agent_rng` already derives per-agent seeds with SHA-256. The `stable_hash_64_signed`
  formula would be a second derivation. Pick one.
- §4 "5–15×": show the arithmetic. `experience_clock_decay.md`'s Motivation gives a 50-pass τ of about 1.7–5 s.

## Answers to §7

- **The background-worker thread** belongs to A4's closure, not A1. It rides on
  `build_memory_hub(start_background_workers=False)` (`bio_stack.py`); the start is already deferred.
- **`agent_id` and #1305.** Yes to the persisted NPC key (candidates A2, both conditions). Whether before or after
  1.4.0 is Maxim's owner decision; if before, it is a new gate item.
- **A3.** The split is already folded into candidates A3. Host-supplied duration is the root fix: excluding it from
  the digest would leave the sign of NAc valence dependent on host speed.
- **G2b.** No: it checks one trace against its anchor, not several traces sharing a receipt. OD-EA12 needs G2b's
  fixture widened, which is a #1361 slice decision.
- **The shortcut.** Already deleted at the root (#1689).
- **The static ban.** Neither M72 nor `lint_dead_imports.py` tests reachability. The natural host is `utils/audit.py`
  (a CI-gated AST import scan) with `lint_dead_imports`' any-depth resolver; its blind spot is `importlib` strings.
  The env exception: no.
- **`environment.step`.** Undecided; it is a B2 blocker for #1150's plan. Suggestion: the embedded roster passes no
  environment, and the follow-up arrives in receipts. That is B2's call.
- **B1.** "The host owns the call" is a valid why-not for the embedded path only; the robot keeps
  `_complete_text_abandonable`. B1 reserves `cancelled` and `truncated` and the speech field; the shape is fixed in
  B1's plan after 1.4.0.
- **OD-A20.** Raised on #1361 (2026-11-18); it is still host calendar by design. The owner decision on #1361 is
  pending.
- **MaximHandle.** A separate constructor beside it, through `AgentFactory`. `save()` should not take `stop()`'s
  contract, since `stop` runs blocking consolidation. Consolidation becomes its own bounded host call. Owner
  decision, pending.
- **Citation drift since 6fee7377:**
  - `prompt_builder.py:1102-1137`: the shortcut is deleted.
  - `llm_fallback.py`: `generate_simple_answer` is gone; `generate_llm_fallback` is at `:267`.
  - `llm_worker.py`: the fallback is at about `:1301-1318`.
  - `agent_loop.py`: the cycles are at about `:3110`.
  - `tool_dispatch.py`: `exec_elapsed` `:1419`, `_observe_energy_cost` `:695`, `environment.step` `:1574`.
  - `loop_controller.py` `:154`.
  - `console/handle.py`: `MaximHandle` `:176`, `stop` `:741`.
  - `input_handlers.py::_handle_phrase_text` `:171`.

  The rest is unchanged.
- **Maxim `src/` before 1.4.0.** Steps 1–4 are not hybrid-family under M89, provided that:
  - the A4 entry point exposes no `think`, `Pending` or continuation before the cut;
  - §2's basis and staleness stay out of B2.

  A2 before the cut means a new gate item (an owner call).
