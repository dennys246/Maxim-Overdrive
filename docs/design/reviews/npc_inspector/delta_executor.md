# NPC inspector design, v2 fold: Executor delta review

**Lens:** Executor (delta round). For each of my round-1 findings I set a status by reading the v2 tree, not `fold.md`. I checked every new or changed factual claim in the fold diff at its stated revision, and checked whether each test named in §9 can fail and is concrete enough to write. **Read:** `docs/design/npc_inspector.md` v1 (`bd0137d`, 2,874 words) and v2 (working-tree blob `20b6cbb1`, 4,038 words, under the 6,000-word limit for a new design); `git diff bd0137d -- docs/design/npc_inspector.md`; round 1's `executor.md`; the author's claims in `fold.md` (blob `5791d71e`). **Sources:** Overdrive `origin/main` `e6d6a7f` (`boundaries.md`, `npcs_and_sem.md`, `sem_stimuli.md`, `sim_core.md`, `inference_placement.md`, `inference_gateway.md`, `realtime_lanes_coop.md`, `tile_and_client.md`, `client_rendering.md`, `decisions/*.md`, `roadmap.md`, `src/simcore/core/schema.py`, `src/simcore/core/text.py`, `pyproject.toml`); Maxim `b90800e` in `<maxim-clone>`; pulse `a1ba1d4` in `<pulse-clone>`. **Ran:**
- `scripts/lint_standards.py` on the working tree (with `-B`): PASS, 0 findings.
- `player_text('[img]res://x.png[/img]', 'speech', max_chars=200)` and the same call with `'<img src=x>'`: both come back unchanged, which confirms §7's claim.
- import-linter 2.6 in the worktree venv ships a `protected` contract type, which `pyproject.toml` already uses, so §4's import rule can be expressed.

## Status of my round-1 findings

| Id | Status | Evidence in v2 |
|---|---|---|
| E-B1 | fixed | §2: `stimulus` is "one delivery as it crossed to the worker", meaning the `BoundFrame`: tick, bindings digest, values and receipts (all host-built, `sem_stimuli.md` §4.2). "A stimulus is not a percept" says that clamp, noise and transduction happen in the worker and that the view labels the value "delivered". No valence appears anywhere in the record. Stage-2 truth and the body frame are excluded by name. |
| E-S1 | fixed | §3 "The format" names the conflict with `schema.py`'s tick-field refusal. It names the amendment as one shared dependency, made in `schema.py` and `tile_and_client.md` §3.2 (the rule `schema.py` itself cites), and §8 lists it as a proposed edit to that owner. |
| E-S2 | fixed | The §2 table now has an "On replay" column. `stimulus` is re-derived and compared. `refusal` is recorded only, which is correct: stage-1 refusals never reach the log (`boundaries.md` §6.1 rule 1, and §6.2's "including refused intents" covers apply-time refusals). Lifecycle and thought cancels and failures are read from the log. Receipts are re-derived inside `stimulus`. |
| E-S3 | fixed | §6 "What exists" cites `NAc_RECOMMEND` (`nac.py:355-380`), `bio_telemetry.py` and `sim_nac`, and argues from them. See DE-N4 for one weak bullet. |
| E-S4 | fixed | §4: the import rule names the reader module and allows only the view's entry point and the save-copy path, enforceable as a `protected` contract. §9's on/off test runs through a save, a load and a continue, and adds a plant of "a restore path that reads the record". With the record off, that restore has nothing to read, so the digests diverge. |
| E-S5 | fixed | §5 joins `npcs_and_sem.md` §5.4's rule instead of claiming none exists. "Body-site tissue values never reach [the client]" is cited to `client_rendering.md` §4.2. The line-of-sight citation is gone. |
| E-S6 | fixed | §3 now has one record per agent per log segment, with own and parent segment in the header, citing `boundaries.md` §6.3 and `npcs_and_sem.md` §6.6. A restart from an earlier home becomes a `rewound` gap. |
| E-S7 | fixed | §2 says memory writes live only in OD-A15's audit record. `write_ref` points at it, and §8 proposes the per-write sequence number to `boundaries.md` §6.1. Who assigns that number is a new defect, DE-S3. |
| E-N1 | fixed | §5 cites `console/server.py:1872` for the epoch `ts` (checked: `"ts": time.time()`). `sim_logger` is no longer named for it. |
| E-N2 | fixed | The table has a channel per kind. `write` text is gone, so the labelling question is moot. The held reply is excluded by name. The double's home digest is defined in §9. With no text in the record, the purge and bug-report sentinels have nothing to test. |
| E-N3 | fixed | §9 "Stamps": the writer asserts that each stamp equals the world-time event it names. As written, though, the test can't be written for four of the seven kinds (DE-S1). |
| E-N4 | fixed | §3 "Size": the rate is set by deliveries and refusals. The meter is bytes per agent per world minute at 20 NPCs. Reader budgets are contract, measured at the build step. |
| E-N5 | fixed | §7: Michael et al. 2013 is now the meta-analysis and Farah & Hook 2013 the review, with Weisberg 2008's non-expert qualifier. I checked these from memory (*unverified*): PB&R 20, about 2,000 subjects over 10 experiments; JoCN 20; Turpin's "up to 36%, 13 BBH tasks, GPT-3.5 and Claude 1.0". All match. |
| E-N6 | fixed | §10 item 7: "It touches no record family; it edits `contracts.md`'s registry." |

## New and changed claims checked against their sources

**These hold at their stated revisions:**
- **Maxim:**
  - `Observer`'s docstring "snapshot-style (no mutations)" is at `simulation/introspection.py:27`.
  - Its non-keyword path calls `hippocampus.recall`, which touches every result under a write lock (`hippocampus_retrieval.py:217-221`). The touch fields are set at `hippocampus.py:2553-2554`.
  - `access_count` and `accessed_at` drive retention (`strategies.py:199`).
  - `SIMULATION_ENVIRONMENT_TEXT` and the `_sim_active` gate are at `prompt_builder.py:83-90, 217-222`, and "A human user is present and watching" is at `:230`.
  - `register_sim_sink` writes into a module-global list (`sim_logger.py:658`). The SENSOR gate's key is `(entity, sensor)` with `time.time()` (`:1702-1709`).
  - `nac.py:361` is a wall-based tick. `salience_map.py:227` defaults to `time.time()`, and its only caller in `src/` passes no time. `valence_signal.py:69` and `energy/signal.py:111` use `time.time()`.
  - `sim_nac` is at `tool_dispatch.py:197`. `ExplainTool` is registered at `agentic_runtime.py:757-759`. `InspectAUTTool` is at `tools.py:1180`.
  - Seams decisions 4 to 6 are at `reachy_app_maxim_seams.md:173-175`, and "Do NOT invent a new event system" is at `:100`. The console uses `register_sim_sink` (`server.py:2097`).
  - GL3 bio-faithful `:182-184` says "the producer stamps it as ground truth".
  - `bio_faithful_roadmap.md:29` lists dopamine-like broadcast as OPEN, with EARN, ANALOG and OPEN defined at `:12-15`.
  - `annotation_context_and_provenance.md:26` holds the "just copies whatever tool strings" quote. `world_clock_a_pre.md` exists.
- **Overdrive:**
  - The three tiers are `boundaries.md` §6.3's table. Tier 3's routes for wall time are `npcs_and_sem.md` §4.4 (floor-holding lateness) and §6.6 (`reply_landed` at `:781`, the per-park ceiling at `:725`).
  - The host-owned continuation header's fields match §2's `thought_state` (`npcs_and_sem.md:754-757`).
  - "0.2–0.8 wall seconds per second for 20 NPCs" is at `npcs_and_sem.md:739-740`.
  - `(actor_id, seq)` is at `boundaries.md:407`, and G17 at `:428`.
  - The §5.3 gate-table row "Scene files, saves, intent logs, bug reports" exists.
  - The response cache's "a load opens a child segment … as it stood at the save's header snapshot" is at `inference_placement.md` §4.2.
  - `sim_core.md` §14's intent-log pattern is as stated.
  - O10, O54 and O55 say what is cited.
  - `realtime_lanes_coop.md` §4.1 has a record lane.

**One citation is softer than stated.** `npcs_and_sem.md` §6.1's "cognition tools go through follow-ups" is marked *(proposed; not adopted)* (`:577`). §2's "When a report has read the recording" depends on it without saying so (DE-N5).

## New findings

None is a BLOCKER. All three SHOULD-FIX findings are in text the fold added: §1 "Its clock" and §3 "The lane" are new in v2, and the `write_ref` kind is new. DE-S1 and DE-S3 are contract findings (a format's stamps, and an interface between the host and the agent home). Under the stop rule they still fold, or the owner overrules them. DE-S2 is a sequencing and testability finding that can be deferred to the build step.

### DE-S1 (SHOULD-FIX). The stamp rule covers three events, but the record has seven kinds, and one stamp conflicts with whole-tick writing

**Location:** `npc_inspector.md::§1` "Its clock", `::§3` "The lane", `::§9` "Stamps".

**Defect.**
- **Four kinds have no stamp.** §1's closed list names only a delivery's tick, a barrier's tick for a refusal, and a thought's modelled landing tick or `reply_landed` tick. No stamp is given for:
  - `write_ref`: the settle tick?
  - `gap`: a span written "when it catches up", so under which tick's block?
  - `tick_end`;
  - a `thought_state` entry for a thought's request, a new cycle or a cancel.
- **The landing-tick stamp breaks whole-tick writing.** §3 writes "whole ticks, each closed by a tick end". A thought's modelled landing tick is in the future when the header is created. An entry stamped with it either lands in a block that hasn't opened yet, or has to be held back until that tick, and the header's counters and cancel status may have changed by then. Which header snapshot the entry holds is undefined.

**Failure scenario.** The implementer of §9's stamp assertion ("each stamp equals the world-time event it names") has nothing to assert for four kinds. They pick something per kind, for example arrival tick for a cancel. That is exactly the wall-in-integer stamp §1 forbids, and nothing catches it. Separately, a thought requested at tick 100 with landing tick 140 is written under tick 140 by one implementation and under tick 100 by another. Both pass every named test, and the reproducibility test compares only one writer against itself.

**Fix** (*unverified*): a stamp column in the §2 table naming, per kind, the event and the tick block it is written in (for a thought: one entry per header change, stamped at the tick of the change, with the landing tick as a field). §9's assertion reads that column.

### DE-S2 (SHOULD-FIX). The [agents] lane and the stalled-writer test depend on `phase1/lanes`, which comes after `phase1/agents`, and the test has no bar and runs on wall time

**Location:** `::§1` "What the invariant promises, by tier" (tier 3), `::§3` "The lane", `::§9` "A stalled writer", header tags.

**Defect.**
- **The record lane is tagged for a step that comes before its pattern exists.** §3's record lane, bounded queue and "the pattern of `realtime_lanes_coop.md` §4.1's record lane" are tagged buildable in `phase1/agents`. But `phase1/agents` comes before `phase1/lanes` (`npcs_and_sem.md:622`), and the lanes, backpressure and meters arrive with `phase1/lanes` (`realtime_lanes_coop.md:375`; `boundaries.md:798`).
- **The test can't fail now.** "A record lane that stalls for N wall seconds leaves the simulation lane's per-barrier time within the copy budget" has no N and no budget. "Copy budget" appears nowhere else in `docs/` (grepped), and the design says the test "gets a number" later.
- **The test breaks the testing standard.** As a measurement of wall-clock per-barrier time it is the kind of test CLAUDE.md's "Tests are deterministic and fast" excludes ("no sleeps, wall clock").

**Failure scenario.** `phase1/agents` either builds an ad-hoc record thread ahead of the lanes design, or writes synchronously on the simulation lane, which is the IO §1 forbids. In both cases the stalled-writer test is written with a placeholder budget, passes regardless, and is a guard that can't fail.

**Fix** (*unverified*): in `[agents]`, a structural test with no wall time. A record lane that never drains (a blocked consumer, released by an event) produces `dropped` gaps and leaves the world and home digests unchanged, and the producer's put is non-blocking by construction. The timing bar moves to `phase1/lanes`' B5 row, derived there, with that step as the trigger.

### DE-S3 (SHOULD-FIX). Who assigns `write_ref`'s sequence number is undefined, and the obvious route breaks §1

**Location:** `::§2` (`write_ref`), `::§8` (the OD-A15 bullet), `::§1` "never adds a codec kind or field".

**Defect.** The audit record is "agent-side … saved with the agent home" (`boundaries.md:397-399`). `settle(receipts, writes)` returns only `ack` (`npcs_and_sem.md` §6.6). §8 says the audit record "gets a sequence number per write, which `write_ref` points at", but not who assigns it.
- **If the worker assigns it,** the host never learns it without a new field on `ack`. That is E-B1's defect class again, and it contradicts §1.
- **If the host assigns it,** it has to send the number to the worker inside `settle`'s payload, which is also a new codec field. The alternative is a number both sides derive identically, which the design doesn't state.

**Failure scenario.** The implementer adds `seq` to `ack` to fill `write_ref`. Alternatively, the host numbers writes itself while the worker's audit record numbers them differently (for example, skipping a write the agent dropped). The explorer then joins write 7 in the record to a different write in the audit record. No named test compares the two.

**Fix** (*unverified*): define the pointer as host-derivable, for example `(settle tick, index in the host's canonical write order)`, which `npcs_and_sem.md` §6.6 already fixes ("orders them canonically"). Require the audit record's key to be that same pair, and add a test that joins the two after a save and load.

### DE-N1 (NIT). The order key puts `tick_end` before `readout`, and its actor id is constant

**Location:** `::§3` "The lane".

"Kind in the table's order" sorts `readout` (the last row) after `tick_end`, inside the tick that `tick_end` claims to close. Since the record is per agent, "then actor id" is constant. The fix is to name `tick_end` as last regardless of kind order (*unverified*).

### DE-N2 (NIT). The `off` gap reason has no defined way to occur

**Location:** `::§2` gap reasons, `::§3` "Whether the record was on is a field of the log header".

On or off is a per-run header field, so a mid-run "switched off" span has no defined trigger. If toggling mid-run is allowed, it needs a logged host control and a header field won't do. If it isn't allowed, `off` can never happen, and that should be said.

### DE-N3 (NIT). The replay comparison and the reproducibility test leave out their preconditions

**Location:** `::§9` "Replay against the record", "Reproducibility".
- **The delivery schedule isn't sourced.** A `stimulus` carries "every receipt since the last delivery" (`sem_stimuli.md` §4.2). Re-deriving a delivery byte for byte therefore needs the delivery schedule (the cognition divisor and dial changes, membership, and the rule that a restart's first delivery carries none of the previous life's receipts, `sem_stimuli.md` §4.5) to come from the log. The design asserts "re-derived" without naming that source.
- **Drops are wall-dependent.** `dropped` gaps depend on the record lane's wall speed, so "byte-identical records" holds only for runs without drops, and the test should say so.

### DE-N4 (NIT). The "process-global sink" bullet doesn't hold for Overdrive's own layout

**Location:** `::§6` "Why that stream can't serve…".

Under O13 each real agent runs in its own worker process, so a process-global sink in the worker is effectively per agent. The records also carry `agent_id` (`sim_logger.py:660-662`, `sim_agent_context` at `:186`). A Maxim reviewer can dismiss this bullet. The case rests on wall-time values and on observation changing the agent, which do hold. Say that the sink argument applies to multi-agent processes, Maxim's own included, and not to Overdrive's workers.

### DE-N5 (NIT). Citation precision

- **§1:** `hippocampus.py:2549-2554` is the touch helper. The recall call site that takes the write lock is `hippocampus_retrieval.py:217-221`. Cite both.
- **§2:** "cognition tools as follow-ups, `npcs_and_sem.md` §6.1" is *(proposed; not adopted)* there, and should be marked so.
- **§2:** the opening says the record "holds only what neither the world log nor the agent's own audit record holds". By the table's own replay column, `stimulus` is re-derivable from the log. It is a deliberate redundant copy, kept for comparison, and could be named as one.

## Round summary

All 14 of my round-1 findings are fixed in the v2 tree. The fold's new citations hold at `e6d6a7f`, `b90800e` and `a1ba1d4`, and the contract registration still passes. There are 3 new SHOULD-FIX findings and 5 new NITs. No new BLOCKER, from this lens, is in text the fold added. DE-S1 and DE-S3 are contract findings and should fold. DE-S2 can be deferred to `phase1/agents` and `phase1/lanes` as named above.
