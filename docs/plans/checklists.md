# Checklists the foundations plan points at

For whoever runs the step. Each item names the review finding it comes from (`reviews/fold.md` has the key). The plan
(`foundations_plan.md`) keeps the order and the decisions; this file keeps the items, so the plan stays inside its
word budget. An item is done when its test exists and passes, or its text has landed.

## Step 1, the merge: this line's items

- Map act-validation's Phase 3 items 10 (malformed arguments booked as tool failures, against TF2) and 11 (affordance
  direction, against `scene_actor_affordances.md`) onto OD ids, or add new ids. Never resolve them mechanically
  (SEQ-S11).
- Keep design-v2's newer versions of the three documents it shares with PR #3 (SEQ-S11).
- Drop the marker-lint exemption for `docs/plans/reviews/` together with the rest of `MARKER_EXEMPT_DIRS`, once the
  Markdown-aware lint from PR #3 lands. Its seven hits are backticked, so that lint passes them (fidelity pass,
  2026-11-17).
- Write the lessons design-v2 owes to `docs/lessons_maxim_in_games.md`: a duplicate ask to Maxim (OD-A19); `-I`
  ignores `PYTHONHASHSEED`; Python falls back to the real home when `HOME` is unset; a pipe that unpickles; O15a
  (ST-S11).
- Flip the design documents' status lines from DRAFT to accepted, citing the owner's merge (CS-S6).
- The merge commit's `prepush: PASS` comes from CI's `prepush` workflow on `main` (it runs on every push and says
  that its isolation check is skipped). Locally: `git worktree add --detach .worktrees/merge-check <sha>` and run
  the gate there; a detached HEAD is neither `main` nor the main checkout (SEQ-S9).

## Terms the plan uses (CS-S4)

- **Tier A / B / C:** Maxim-side work in Phase 3, by what it enables: A, an agent a host can drive (Phase 4 waits on
  it); B, Maxim's 1.4 line; C, SEM additions after A (`docs/roadmap.md` Phase 3).
- **The 1.4.0 cut:** Maxim's next minor release; the stepped `think` comes after it, in the 1.5 hybrid src phase (O15a).
- **The scripted double:** a fake agent with Maxim's interface, scripted per test, run in a real worker process, so
  the agent line is tested before real Maxim can be.
- **B-numbers (B19, B20):** rows in `docs/standards_backlog.md`, rules held by review until a check exists.
- **OD- ids:** Overdrive's proposals to Maxim (`docs/roadmap.md` Phase 3). **O, OA, D:** owner decisions in the
  design docs' §0.
- **Strict red gate:** `pytest.mark.xfail(strict=True)`; it goes red the day the fix lands, so someone removes it.

## Machine assumptions for any session (CS-S8)

Python 3.10 or later; GPG signing configured, with someone present to answer its passphrase prompt; `gh`
authenticated for the private repository; Godot 4.7.2 at `/Applications/Godot.app` from step 2; a per-worktree
`.venv` (step 0a).

## Step 7, `phase1/protocol`

- The strict red gate that refuses guest joins while real-Maxim NPCs are live, as the roadmap's Phase 4 assigns
  this PR (TB-B2).
- The guest-text gate `engine.text.player_text`. Its Cf rule must let ZWNJ and ZWJ through for Persian, Indic
  spelling and emoji sequences, or say why not, and NFC runs before the length cap. This is an owner decision
  (TB-N5).

## The agent line's PR (after steps 5 and 7)

It needs step 7: the host's stage 1 for worker speech calls `engine.text.player_text` (TB-S9).

**Precedence.** For the agent half, a finding in `docs/design/reviews/npcs_v3_1/` overrides the frozen §6.6 text it
contradicts (TB-S5). Before the codec's fixtures freeze, each of these is a test or a fixed codec kind:
- ATR-S1 (worker stdio not inherited);
- ATR-S3 (a refused frame drops the frame, not the NPC);
- ATR-S6 (the `purge(actor, session)` kind, and a host-computed lower bound on provenance; TB-B3);
- ATR-S8 (snapshot save; cancel pending intents);
- ATR-S9 (a frame per perceiver, not the whole world);
- ATR-S10 (budgets for body, home and rlimits);
- ATR-N1;
- ATR-N2 (a `hello` kind).

**Real Maxim stays off the test process (TB-S4).**
- Every real-Maxim red gate builds its agent only inside a spawned worker, with the allowlist and `MAXIM_OFFLINE`.
- Tests 1–3 are green before the first such gate is written.
- A test asserts that `maxim.runtime` and `maxim.agents` are absent from pytest's `sys.modules` after the agent
  suite.

**Platform and latch (MS-S7, SEQ-S7).**
- Off POSIX, the host refuses to spawn a worker with a typed error, and a test covers it.
- A test pins that the pre-opened `socketpair` survives `engage()`. Tell Maxim that this residual is load-bearing.
- Tests that need `maxim._offline` are a strict red gate naming the pymaxim release that ships it. Raise
  `pymaxim>=` when it ships. A pymaxim release that turns `tests/test_sem_compat.py` red gets its own mirror-update
  PR from this line, never a fix inside a feature branch.
- Windows NPCs before Phase 8 need a Phase 3 item; the owner decides whether they are wanted. Until then, a Known
  gap: real NPCs on macOS and Linux only.

**The lane's model (MS-S8, O18).**
- Build the router with `models/download.py::consented_router`, with no cloud or peer tail when guests are present,
  the model provisioned before play, and stdin not a terminal.
- A gate test: a missing local model with guests present refuses (typed, and shown in the client). It never falls
  through to a remote tail.

**Coverage of the worker (ST-S2).** Coverage follows the child: `patch = ["subprocess"]`, or
`COVERAGE_PROCESS_START` with `parallel` and `combine`. Admit coverage's variables through test 2's allowlist, by
name, and test that the worker's main loop is measured.

**Determinism (ST-S3).**
- The hash probe calls the builtin `hash()`, so give its module a package-qualified exemption in
  `tests/test_determinism.py`, with a reason.
- Rewrite CLAUDE.md's rule of one `Generator` owned by `World`: per-NPC streams break it under either derivation.
  If MS-S6 keeps ours, admit Philox in `NUMPY_RANDOM_ALLOWED` in the same commit, for Overdrive's streams only.

**Formats and data (ST-S5).**
- The channel codec: a version that readers refuse when unknown, a round trip, committed golden fixtures, and a
  Hypothesis round-trip property.
- `data/agents/`: a `version`, closed schemas, and tunables in YAML. The continuation blob is versioned.

**Provenance of *to verify* values (TB-S6, option (b)).** Each value in `data/agents/` carries a tag: `verified`,
`to_verify` or `engineering`. A loader test fails on `to_verify` outside a fixture. The calibration ledger the source would have this block on
is out of the plan (S-S8), so this test is the whole mechanism.

**Reopening the frozen agent half (S-S2).** Edits are errata only until one of these fires:
- Maxim's stepped-`think` API lands (cand. B1);
- the LLM spike measures latency;
- Maxim answers a second candidates round (the first, #1688, is answered by errata).
