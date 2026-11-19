# DRAFT for Maxim: an embeddable agent, which a host drives (v3)

**Status:** v3 (2026-11-19), sent for Maxim's **plan review** (three lenses, then a code review per PR) under
Overdrive's owner decision O35. Your answer of 2026-11-19 accepted the world-seam front gate, so the case for a
host-driven runtime mode is agreed; this contract is not, and no Maxim `src/` lands for it before this review. v3
folds your candidates doc (`docs/plans/overdrive_refactor_candidates.md`), your 1.4.0 range, our erratum, OD-A20,
OD-A21, recorded replies (O26) and our first NPC's tier-A subset (O29).
Everything here is `[engineering]`; it claims no behaviour. Citations are `file::symbol` with a line hint on Maxim
`origin/main` **6fee7377** (2026-11-17); the symbol is the citation. Where this draft and your candidates doc
differ, the doc wins and §7 asks.

**For a reader who hasn't read Overdrive.** Overdrive is a game world server whose NPCs are Maxim agents. It runs on
an integer tick, replays bit for bit from an intent log, and takes every action through one validated door. Each real
agent runs in its own spawned worker process (pickle-free framed JSON over a socket pair, an allowlisted environment,
no keys, the offline latch engaged); the model gateway stays in the host. Optional context: Overdrive's
`docs/design/npcs_and_sem.md` §6 (the port, frozen at v3.1; your review is a trigger to reopen it, O36),
`docs/roadmap.md` Phase 3 (the ids) and `docs/design/reviews/maxim_response_1/`.

**Ids.** This draft covers OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17, OD-A18, OD-I3 and OD-H6. It depends on
OD-A2 to OD-A8, OD-A20, OD-A21 (§4) and OD-A16 (an amendment to `tool_failure_credit.md`, #1200).

| Ours | Yours | Venue (yours) |
|---|---|---|
| OD-A12 `AgentHome` | cand. A1 | a plan merged with #984 |
| OD-A7 keyed substreams | cand. A2 | #1305 (`1305.owned-rng`) |
| OD-A2, OD-A3 clock and port; OD-A4 duration | cand. A3 (A-pre, A-post) | with #1361, M72 |
| OD-A10, OD-A11, OD-A17 entry point, roster, leak closure | cand. A4 | a section of this plan |
| OD-I3 pickle load | cand. A5, #1685 | issue |
| OD-I1 `x or time.time()` | #1684 | issue |
| OD-A18 dispatch/settle, generate vs apply | cand. B2 (#1150) with A6 | #1150 |
| OD-A14, OD-A15 the cut and stepped `think` | cand. B1 (with B3) | hybrid §A.1b, after 1.4.0 |
| inner tool loop | cand. C1 | prereg |

OD-I5 is your private advisory; this draft names it only.

## 1. Since v1

v1's errors about Maxim (an inner tool loop, a cancellable `LLMBackend`, the advisor as the base) are recorded in
Overdrive's `docs/design/reviews/maxim_response_1/`. One fact still shapes §2: a thought can be up to 3 model calls
with a percept source, 2 without (`runtime/agent_loop.py:3089-3093`; `llm.deliberation_max_cycles` overrides it).

## 2. The contract

Construction goes through `AgentFactory` (one construction point, OD-A10); deliberation is its own module.

| Call | Does | Returns |
|---|---|---|
| `step(agent, world_dt_us, frame)` (the host's port is in ticks; its adapter converts) | advances drives, the experience clock and the substrate; reads percepts | a `StepOutput` value: intents, memory writes, thought requests |
| `think(agent, handle, reply \| None)` | runs deliberation to its next model call; may read, never write | `Pending(request) \| ThoughtOutput`, with writes (retrieval strengthening included) as values |
| `apply(agent, writes)` | the only path by which memory writes reach the stores, host-called after its gate | an ack |
| `settle(agent, receipts)` | the only path by which credit reaches the stores, host-called | an ack |
| `save()` / `load(home)` | persist and restore under the home only, pickle-free | an ack, or a typed refusal |

The four calls are Overdrive's whole `AgentPort`; `save`/`load` are persistence.

- **The continuation is split by owner, and is not the whole agent.** The **host** keeps a header: thought id and
  kind, the triggering-input id, budget counters, the PFC cycle index and `max_cycles`, the basis (step sequence and
  frame id, §A.1b.5's `basis_seq`), each segment's landing time, cancel status and the delivered prefix. The
  **agent** keeps a body: the partial proposal, the transcript, enrichment results, and the loop locals that aren't
  values yet (the same-tool counter, `rejection_followups`), saved in its home, opaque to the host. The host enforces
  budgets from its header, so the agent can't reset them. A census of today's think-path writes is the plan's first
  step.
- **The body is versioned:** `load` refuses an unknown version with a typed error, which the host logs as
  `thought_failed(reloaded)` rather than refusing the save.
- **Staleness has one vocabulary,** `fresh`, `stale`, `superseded`: on a stale basis `think` returns a re-plan
  `Pending` (counted) or `ThoughtOutput(abandoned)`.
- **The request** is a value: rendered system and user text, sampling parameters, a model **role** (speech or plan,
  which the host binds to its model profile), the template version, and `tools is None`. Priority and deadline are
  stamped by the host from the thought's kind (your B3), outside any cache key.
- **The reply** is a value: `complete(text)`, with reserved `cancelled(prefix)` and `truncated(prefix, reason)`,
  where the prefix is the speech the host delivered and validated. Speech is a top-level field emitted first. Cancel
  is resuming with `cancelled(prefix)`.
- **Replies are recorded, and the record is the host's.** Replay uses the recorded model replies, never a model.
  The logged reply record is a versioned host type the adapter maps your reply values into, so B1's shape can change without breaking our saves.
  A purge of a guest's words leaves a redaction record, and replay is bit-identical up to the first redacted reply;
  that is ours. Guests and co-op are our Phase 5 or later (O28); nothing here waits on them.
- **No reply reaches the parse-failure template** (A4's bypass, with B1): an unparseable reply ends the thought as
  `thought_failed(reason=parse)`, since the template echoes the input (`agents/llm_worker.py:1322-1339`;
  `agents/llm_fallback.py:395-400`).
- **Cognition tools go through follow-ups** like world tools until your C1 decides otherwise.
- **The robot path drives the same `think`** through a thin driver.
- **Budgets per triggering input and per agent per world minute** across follow-up chains (so thoughts with no
  speech trigger are budgeted too): PFC cycles per thought, `parallel_actions` per reply (a grammar `maxItems`),
  `next_actions` chain length, tokens per call, memory writes and bytes.
- **Submit cadence (OD-H6):** a host-called `think` never consults `llm_submit_interval`
  (`runtime/loop_controller.py:157`), so it needs no change; part of B1.

## 3. The embedded-path leak closure (OD-A17; your cand. A4)

We take A4's list and guards as written. Ours adds or differs only here:
- **The short-question shortcut.** Our position: it answers any `triggering_input` without the model
  (`agents/prompt_builder.py:1102-1137`, via `llm_fallback.py::generate_simple_answer`, `:290`), rendering the host
  clock (`:1125-1127`), so it is a defect on a robot too and should be fixed at the root, not bypassed for
  embedders. A4 leaves this to your owner ("Not decided"); §7 Q5 asks.
- **No model backend in the embedded agent at all,** so the model calls outside `think` fail closed, each named:
  `AdaptivePlanner(llm=...)` (`runtime/bootstrap.py:623` → `planning/adaptive_planner.py:487`), the
  `ToolPainBridge` reflection on the settle path (`bridges/tool_pain_bridge.py:806`, its error dropped) and
  `FearAgent._analyze_with_llm` (`agents/fear_agent.py:303`, the call at `:317`). Each becomes a request through the
  cut, or is off when embedded.
- **The static ban** names at least `maxim.embodied_runtime` (the phrase commands,
  `embodied_runtime/input_handlers.py:202`, `:274-312`), the internet tools, `build_tool_registry`'s module,
  `runtime.prefetch` and `time.sleep`. Until `AgentHome` lands, the env-read test expects exactly one read,
  `MAXIM_DATA_HOME`. Our workers also start in the empty agent home: defence in depth, not the guard.

## 4. Clock, randomness and duration: yours, with our conditions

- **The machinery clock and perceived-time port** are A3's (`ExperienceClockDriver`, `runtime/experience_time.py:36`;
  the ban extends M72). Our port carries coarse world time.
- **The planted-render test, split** (our erratum to your accepted ask): end to end, shift the machinery clock's
  **origin only**, and nothing a prompt renders may change; at render level on a frozen store, shift origin **and**
  scale, so relative renders ("3 s ago") can't leak either. End to end, scale legitimately changes decay and recall,
  so the unsplit test is red on correct code.
- **Keyed substreams** are your A2 derivation, `random.Random(stable_hash_64_signed(f"{base_seed}:{agent_id}:{stream}"))`
  (`utils/seeding.py:121`), on two conditions, the only properties our host-side handout existed for: `agent_id` is
  the host's persisted NPC key, never an ordinal (streams survive saves and roster edits), and `base_seed` comes from
  the host's log root.
- **Tool duration (OD-A4):** `execute_and_learn` measures `exec_elapsed` on the wall clock
  (`runtime/tool_dispatch.py:1343`), and `_observe_energy_cost` books a NEGATIVE NAc valence above 2.0 s (`:626`).
  Embedded, the host supplies it in world time (a blocker B2 names).
- **Anchor similarity (OD-A20):** after #1361 S3b, `TemporalSignature.now()` (`decisions/nac.py:3629`) still scores
  anchor similarity on the host calendar (#1361 §(c); §(g): "host calendar by design"). A replay at 3 pm rather than
  9 am credits differently, and learning follows the player's clock. Read it from the perceived-time port; in O29's
  subset.
- **τ_elig (OD-A21):** an argument against #1361's decided Q1, "taus in world-seconds, anchored on Exp 30's fixture
  regime; tune the turn quantum, never per-runtime taus". The striatal dopamine eligibility window is about 0.3–2 s
  (Yagishita et al. 2014); S3a under Q1 lengthens a 10–30 Hz robot's window 5–15×. Reopening Q1 is your owner's
  decision, with its own experiment; **not** blocking for us.

## 5. The build, in your order

Your §Order governs: entry point and sealed roster (OD-A10, OD-A11) and the leak closure with A4, after this review;
`AgentHome` with A1 and #984, after #1685, including `MemoryHub.start_background_workers` (`runtime/bio_stack.py:654`)
made host-driven; dispatch/settle with B2 (#1150) and A6, carrying provenance by source actor, D53 `outcome_valence`,
OD-A16's keys and `environment.step` (`tool_dispatch.py:1516`) out of dispatch for a host that owns the step; the
stepped `think` with B1 and B3 after the 1.4.0 cut. Red gates for §6 come first, against a stub host.

**Timing, as you gave it** (not a commitment): 1.4.0 earliest February 2027, planned March to May 2027; B1 follows with
no range, so our first real NPC is after mid-2027. Meanwhile one unreplayed bridge NPC measures latency, cost and
feel, claiming nothing.

**What our first NPC needs (O29):** #1361 S3a, S3b and S4; OD-A2 to OD-A11; OD-A12's host-driven thread; OD-A14 to
OD-A18; OD-A20; #1684 and #1685. Not blocking: #1361 S5 and S6, OD-A21, and OD-A12's store routing.

## 6. Exit tests

Where you have the test, ours is a configuration of it.

| # | Passes when | Yours |
|---|---|---|
| OD-EA1 | a planted `BashTool` in the roster makes construction refuse, naming it | A4 |
| OD-EA2 | two embedded agents in one process never open the same file | A1's filesystem trace |
| OD-EA4 | no store changes until `apply`/`settle`; then exactly the returned writes; a memory write planted in the parallel dispatch path is refused | B2/A6 |
| OD-EA5 | the state digest is identical whether each reply returns instantly or after a seeded random delay | B1's gate |
| OD-EA6 | agent A's digest is identical alone, beside B, reversed and concurrent (proven by a planted global `random`) | A2 (partly) |
| OD-EA7 | the thread count is unchanged by building and stepping | none found |
| OD-EA8 | `cancelled(prefix)` records the host-delivered prefix as said and the thought as cancelled; no reply, cancelled or unparseable, reaches the parse-failure template | A4/B1 |
| OD-EA9 | stubs that request a follow-up on every reply, ask for 3 PFC cycles forever, or return 100,000 tokens all stop at the host's budget | none found |
| OD-EA10 | §3's four closure tests pass, and a planted read in a lazy path fails the static ban | A4 |
| OD-EA11 | a sentinel in the **machinery** clock never appears in a prompt in raw, clock or date form; an origin offset changes no prompt end to end; offset and scale change no render on a frozen store | A3's planted-render test, split (§4) |
| OD-EA12 | several traces credited by one receipt share it identically between agents stepping at two rate divisors | #1361 S3b's G2b (§7, Q4) |
| OD-EA13 | a stub that calls a model outside `think` fails closed, naming the call | none found |

OD-EA3 (no pickle) is #1685.

## 7. Questions to your existing plans

Each replaces an ask v2.1 made as new.

1. **A1 (with #984):** is `_GLOBAL_PATHS` the checked registry our OD-EA2 should run over, and does making
   `start_background_workers`' ConceptExtractor thread host-driven belong to A1 or to A4?
2. **A2 (#1305):** can A2's `agent_id` be a host-supplied persisted key and `base_seed` a host-supplied root, and does
   the per-agent key widen #1305 before 1.4.0 or follow it (your "Not decided")?
3. **A3:** will its planted-render guard take the split in §4, and is the host-supplied duration (OD-A4) A3's route,
   rather than excluding duration from B2's digest?
4. **#1361 S3b's G2b:** it checks one credit sequence at two poll rates; does it already cover several traces sharing
   one receipt, so OD-EA12 needs only an embedded host's configuration of it?
5. **A4's "Not decided":** the shortcut answers any `triggering_input` (a relayed stranger's line included) with a
   canned reply rendering the host's clock, past the model. We'd call that a robot-path defect, fixed at the root. Is
   that the owner decision you'd take?
6. **A4's static ban:** should it ride on an existing lint (M72's, or `scripts/lint_dead_imports.py` from #1436),
   as A3 rides on M72?
7. **B2 (#1150):** how does it resolve `environment.step` inside dispatch: does a host that owns the step simply not
   pass an environment on the embedded path?
8. **B1** asks to ride on `utils/cancellation` and `LLMRouter._complete_text_abandonable` (`router.py:998`) or say
   why not. Under the cut the host owns the call, so abandonment is the host's and the agent sees only
   `cancelled(prefix)`. Agreed, and does B1's reply shape leave room for our host-side record (§2)?
9. **HANDLE** (`deferred/reachy_app_maxim_seams.md`; `maxim_ui.md`, "embodied + headless flavors") embeds an agent
   that runs its own loop. Is OD-A10's host-driven entry a third flavor of it, or beside it? Either way `save()` would
   take HANDLE's stop contract, naming its consolidation (`"full"` or `"lightweight"`).
10. **`bounded_stop.md`:** our host owns each worker process and gives `save()` a deadline. Is the bounded stop's
    "save within the caller's deadline" the contract `save()` should keep on the embedded path?

Searched, nothing found: the model calls outside `think` in active plans; OD-EA7 and OD-EA9; a `DECISIONS.md`
entry for the host-driven mode (ours is proposed in Overdrive's `decisions_entry_DRAFT.md`).

## 8. What it argues against

Mode-based containment (`allowed_dirs`) as the security model when the prompt carries strangers' words, and the
process-wide data home. Both are right for one robot and its operator.
